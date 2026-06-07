"""
    .. module:: retrysupport
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Aspects-driven retry helper for libvirt operations.  The
               retry budget is supplied by the caller via aspects — there
               are no behaviour-modifying decorators.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import os
import time

from typing import Any, Callable

from ccai.errors.exceptions import SemanticError

from ccai.interop.libvirt.aspectslibvirt import AspectsNative
from ccai.interop.libvirt.exceptions.libvirtconnectionerror import (
    LibvirtConnectionError
)
from ccai.interop.libvirt.exceptions.libvirtoperationerror import (
    LibvirtOperationError
)


def _is_transient_libvirt_error(error: BaseException) -> bool:
    """
        Decide whether ``error`` is a transient libvirt failure that the
        aspects retry budget may legitimately retry.

        Only the native libvirt SDK error (class name ``libvirtError``) and
        :class:`LibvirtConnectionError` qualify. ``SemanticError`` — which
        must never be caught — and ordinary programming defects such as
        ``TypeError`` / ``ValueError`` are NOT transient: retrying them
        wastes the budget and masks the real fault, so they must bubble.

        :param error: The caught exception instance.

        :returns: ``True`` when the error is a transient libvirt failure.
    """
    if isinstance(error, LibvirtConnectionError) is True:
        rtnval = True
        return rtnval

    type_name = type(error).__name__
    rtnval = type_name == "libvirtError"
    return rtnval


def run_with_retry(*, operation: Callable[[], Any], aspects: AspectsNative,
                   description: str) -> Any:
    """
        Run a libvirt operation, retrying transient failures per aspects.

        The number of attempts is dictated by ``aspects.max_attempts`` and
        the delay between attempts by ``aspects.retry_interval``.  When
        the budget is exhausted a :class:`LibvirtOperationError` is
        raised carrying the last underlying error.

        :param operation: A zero-argument callable performing the work.
        :param aspects: The :class:`AspectsNative` carrier.
        :param description: A human-readable operation description used
            in the error message.

        :returns: Whatever ``operation`` returns on success.

        :raises: :class:`LibvirtOperationError`
    """
    attempts = aspects.max_attempts
    if attempts < 1:
        attempts = 1

    last_error: Any = None
    attempt_index = 0
    while attempt_index < attempts:
        try:
            rtnval = operation()
            return rtnval
        except SemanticError:
            raise
        except LibvirtOperationError:
            raise
        except Exception as xcpt:
            if _is_transient_libvirt_error(xcpt) is False:
                raise
            last_error = xcpt
            attempt_index = attempt_index + 1
            if attempt_index < attempts:
                time.sleep(aspects.retry_interval)

    err_msg_lines = ["A libvirt operation failed after exhausting the "
                     "aspects retry budget."]
    err_msg_lines.append("OPERATION: {}".format(description))
    err_msg_lines.append("ATTEMPTS: {}".format(attempts))
    err_msg_lines.append("LAST-ERROR: {}".format(last_error))
    err_msg = os.linesep.join(err_msg_lines)
    raise LibvirtOperationError(err_msg) from None
