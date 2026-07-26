"""
    .. module:: libvirtconnectionmanager
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Lifecycle gateway between the API groups and the
               :class:`VirshDispatcher` transport.

    ``virsh`` invocations are stateless — there is no persistent wire
    connection to cache, probe, or reopen, so the manager's job reduces to
    owning the dispatcher, enforcing the closed-rejects contract, and
    offering the checked / probing execution surface the API groups use.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import os

from typing import List, Optional

from ccai.interfaces.icommandrunner import ICommandRunner

from ccai.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from ccai.interop.libvirt.connection.libvirtconnectioncredential import (
    LibvirtConnectionCredential
)
from ccai.interop.libvirt.connection.virshdispatcher import VirshDispatcher
from ccai.interop.libvirt.exceptions.libvirtconnectionerror import (
    LibvirtConnectionError
)


class LibvirtConnectionManager:
    """
        Owns the ``virsh`` transport for one hypervisor connection.

        After :meth:`close` the manager rejects further operations until a
        new manager is constructed — the same contract the native-binding
        implementation enforced for its cached connection.
    """

    def __init__(self, *, credential: LibvirtConnectionCredential,
                 runner: ICommandRunner,
                 virsh_path: str = "virsh") -> None:
        """
            Construct a LibvirtConnectionManager.

            :param credential: The :class:`LibvirtConnectionCredential`
                describing the libvirt URI.
            :param runner: The injected command runner deciding where
                ``virsh`` executes (locally, or on a remote host over the
                suite's own SSH implementation).
            :param virsh_path: The ``virsh`` executable to invoke.
        """
        self._credential: LibvirtConnectionCredential = credential
        self._dispatcher: VirshDispatcher = VirshDispatcher(
            runner=runner, uri=credential.uri, virsh_path=virsh_path
        )
        self._closed: bool = False
        return

    @property
    def uri(self) -> str:
        """
            Return the libvirt connection URI.

            :returns: The connection URI string.
        """
        rtnval = self._credential.uri
        return rtnval

    def _require_open(self) -> None:
        """
            Raise when the manager has been closed.

            :raises: :class:`LibvirtConnectionError`
        """
        if self._closed is True:
            err_msg_lines = ["The libvirt connection has been closed."]
            err_msg_lines.append("URI: {}".format(self._credential.uri))
            err_msg_lines.append("Construct a new manager to reopen it.")
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtConnectionError(err_msg)
        return

    def run(self, *, args: List[str], description: str,
            stdin: Optional[str] = None,
            aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS) -> str:
        """
            Run a ``virsh`` command, raising on failure.

            :param args: The virsh sub-command and its arguments.
            :param description: A human-readable operation description used
                in error messages.
            :param stdin: Optional text fed to the command's stdin.
            :param aspects: The :class:`AspectsNative` carrier; its
                ``connection_timeout`` bounds the command execution.

            :returns: The captured stdout text.

            :raises: :class:`LibvirtConnectionError`,
                :class:`LibvirtOperationError`
        """
        self._require_open()
        rtnval = self._dispatcher.run_checked(
            args=args, stdin=stdin, timeout=aspects.connection_timeout,
            description=description
        )
        return rtnval

    def probe(self, *, args: List[str],
              stdin: Optional[str] = None,
              aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
              ) -> Optional[str]:
        """
            Run a ``virsh`` command, tolerating operation failures.

            Used for existence lookups where absence is expected.  A
            connection-class failure still raises so a dead hypervisor is
            never mistaken for an absent object.

            :param args: The virsh sub-command and its arguments.
            :param stdin: Optional text fed to the command's stdin.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The captured stdout, or ``None`` on operation
                failure.

            :raises: :class:`LibvirtConnectionError`
        """
        self._require_open()
        rtnval = self._dispatcher.probe(args=args, stdin=stdin)
        return rtnval

    def close(self, *,
              aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS) -> None:
        """
            Close the manager and reject further operations.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        self._closed = True
        return
