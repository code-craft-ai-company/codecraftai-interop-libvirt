"""
    .. module:: virshdispatcher
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: ``virsh`` argv construction and dispatch through an
               :class:`ICommandRunner`.

    The dispatcher centralises argv prefix construction
    (``virsh --connect <uri> ...``), runner invocation, and the mapping of
    command failures onto the package's exception types.  It is the ONLY
    place in the package that executes commands — the "one transport per
    package" rule holds, with ``virsh`` over an injected command runner as
    the single transport.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import os

from typing import List, Optional

from ccai.interfaces.icommandrunner import ICommandRunner, RunResult

from ccai.interop.libvirt.exceptions.libvirtconnectionerror import (
    LibvirtConnectionError
)
from ccai.interop.libvirt.exceptions.libvirtoperationerror import (
    LibvirtOperationError
)


# stderr fragments that indicate the hypervisor could not be reached, as
# opposed to an operation the hypervisor rejected.  Connection-class
# failures raise LibvirtConnectionError, which the aspects retry budget
# treats as transient; everything else raises LibvirtOperationError.
_CONNECTION_FAILURE_MARKERS = (
    "failed to connect",
    "cannot recv data",
    "connection refused",
    "authentication failed",
    "end of file while reading data",
    "no connection driver available",
    "cannot read ca certificate",
)


def _is_connection_failure(*, stderr: str) -> bool:
    """
        Decide whether a failed ``virsh`` invocation was a connection-class
        failure.

        :param stderr: The captured stderr text.

        :returns: ``True`` when the failure indicates the hypervisor could
            not be reached.
    """
    lowered = stderr.lower()
    for marker in _CONNECTION_FAILURE_MARKERS:
        if marker in lowered:
            rtnval = True
            return rtnval
    rtnval = False
    return rtnval


class VirshDispatcher:
    """
        Builds ``virsh`` argv and dispatches it through an
        :class:`ICommandRunner`.

        The dispatcher is deliberately small: argv prefix + invocation +
        error mapping.  Output parsing belongs to the API groups (helped by
        :mod:`virshparsers`).

        The runner decides WHERE the command executes — a local runner
        drives a local libvirt daemon, an SSH-backed runner drives the
        daemon on a remote hypervisor host.  Either way ``virsh`` runs on a
        host where libvirt is installed; nothing native is required where
        this package runs.

        :param runner: The injected command runner.
        :param uri: The libvirt connection URI passed as ``--connect``
            (``qemu:///system``, ``qemu+ssh://host/system``, ...).
        :param virsh_path: Path to the ``virsh`` executable, or the bare
            name ``"virsh"`` to rely on ``$PATH`` resolution by the runner.
    """

    def __init__(self, *, runner: ICommandRunner, uri: str,
                 virsh_path: str = "virsh") -> None:
        """
            Construct a VirshDispatcher.

            :param runner: The injected command runner.
            :param uri: The libvirt connection URI.
            :param virsh_path: The ``virsh`` executable to invoke.
        """
        self._runner: ICommandRunner = runner
        self._uri: str = uri
        self._virsh_path: str = virsh_path
        return

    @property
    def uri(self) -> str:
        """
            Return the libvirt connection URI.

            :returns: The connection URI string.
        """
        rtnval = self._uri
        return rtnval

    def _build_argv(self, *, args: List[str]) -> List[str]:
        """
            Build the full argv for a ``virsh`` invocation.

            :param args: The virsh sub-command and its arguments.

            :returns: The complete argv list.
        """
        rtnval = [self._virsh_path, "--connect", self._uri] + list(args)
        return rtnval

    def dispatch(self, *, args: List[str],
                 stdin: Optional[str] = None,
                 timeout: Optional[float] = None) -> RunResult:
        """
            Run a ``virsh`` command and return the raw result without
            raising on failure.

            :param args: The virsh sub-command and its arguments.
            :param stdin: Optional text fed to the command's stdin — used
                with ``/dev/stdin`` file arguments to deliver XML without
                touching the remote filesystem.
            :param timeout: Optional command timeout in seconds.

            :returns: The raw :class:`RunResult`.
        """
        argv = self._build_argv(args=args)
        rtnval = self._runner.run(argv, stdin=stdin, timeout=timeout)
        return rtnval

    def run_checked(self, *, args: List[str],
                    stdin: Optional[str] = None,
                    timeout: Optional[float] = None,
                    description: str) -> str:
        """
            Run a ``virsh`` command, raising on failure.

            :param args: The virsh sub-command and its arguments.
            :param stdin: Optional text fed to the command's stdin.
            :param timeout: Optional command timeout in seconds.
            :param description: A human-readable operation description used
                in error messages.

            :returns: The captured stdout text.

            :raises: :class:`LibvirtConnectionError` when the hypervisor
                could not be reached; :class:`LibvirtOperationError` for
                every other failure.
        """
        result = self.dispatch(args=args, stdin=stdin, timeout=timeout)

        if result.timed_out is True:
            err_msg_lines = ["The virsh command timed out."]
            err_msg_lines.append("OPERATION: {}".format(description))
            err_msg_lines.append("ARGS: {}".format(" ".join(args)))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtConnectionError(err_msg)

        if result.exit_code != 0:
            err_msg_lines = ["The virsh command failed."]
            err_msg_lines.append("OPERATION: {}".format(description))
            err_msg_lines.append("URI: {}".format(self._uri))
            err_msg_lines.append("ARGS: {}".format(" ".join(args)))
            err_msg_lines.append("EXIT-CODE: {}".format(result.exit_code))
            err_msg_lines.append("STDERR: {}".format(result.stderr.strip()))
            err_msg = os.linesep.join(err_msg_lines)
            if _is_connection_failure(stderr=result.stderr) is True:
                raise LibvirtConnectionError(err_msg)
            raise LibvirtOperationError(err_msg)

        rtnval = result.stdout
        return rtnval

    def probe(self, *, args: List[str],
              stdin: Optional[str] = None) -> Optional[str]:
        """
            Run a ``virsh`` command, tolerating operation failures.

            Used for existence lookups where absence is an expected,
            non-error outcome.  Connection-class failures still raise so a
            dead hypervisor is never mistaken for an absent object.

            :param args: The virsh sub-command and its arguments.
            :param stdin: Optional text fed to the command's stdin.

            :returns: The captured stdout text, or ``None`` when the
                command failed for a non-connection reason.

            :raises: :class:`LibvirtConnectionError` when the hypervisor
                could not be reached.
        """
        result = self.dispatch(args=args, stdin=stdin)

        if result.timed_out is True or result.exit_code != 0:
            if result.timed_out is False and \
                    _is_connection_failure(stderr=result.stderr) is False:
                rtnval = None
                return rtnval
            err_msg_lines = ["The virsh probe could not reach the "
                             "hypervisor."]
            err_msg_lines.append("URI: {}".format(self._uri))
            err_msg_lines.append("ARGS: {}".format(" ".join(args)))
            err_msg_lines.append("STDERR: {}".format(result.stderr.strip()))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtConnectionError(err_msg)

        rtnval = result.stdout
        return rtnval
