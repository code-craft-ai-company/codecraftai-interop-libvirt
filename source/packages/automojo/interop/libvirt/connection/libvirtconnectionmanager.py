"""
    .. module:: libvirtconnectionmanager
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Connection-lifecycle manager wrapping ``libvirt.openAuth``
               with caching, drop-detection, and aspects-driven reopen.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


import importlib
import os

from typing import Any, Optional

from automojo.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from automojo.interop.libvirt.connection.libvirtauthcallback import (
    LibvirtAuthCallback
)
from automojo.interop.libvirt.connection.libvirtconnectioncredential import (
    LibvirtConnectionCredential
)
from automojo.interop.libvirt.exceptions.libvirtconnectionerror import (
    LibvirtConnectionError
)


def _import_libvirt() -> Any:
    """
        Import the native ``libvirt`` module lazily.

        Importing lazily keeps the package usable (and testable) on
        hosts where ``libvirt-python`` is not installed.

        :returns: The imported ``libvirt`` module.

        :raises: :class:`LibvirtConnectionError` when the module is
            not importable.
    """
    try:
        module = importlib.import_module("libvirt")
    except ImportError as xcpt:
        err_msg_lines = ["The native 'libvirt' Python bindings are not "
                         "installed."]
        err_msg_lines.append("Install 'libvirt-python' on the host that "
                             "runs the interop client.")
        err_msg_lines.append("IMPORT-ERROR: {}".format(xcpt))
        err_msg = os.linesep.join(err_msg_lines)
        raise LibvirtConnectionError(err_msg) from None
    rtnval = module
    return rtnval


class LibvirtConnectionManager:
    """
        Owns the lifecycle of a single cached libvirt connection.

        The connection is opened lazily on first use via
        ``libvirt.openAuth`` and cached.  A connection dropped by the
        server is detected on the next access; whether the manager
        transparently reopens is governed by
        ``aspects.reconnect_on_drop`` — never by built-in behaviour.
    """

    def __init__(self, *,
                 credential: LibvirtConnectionCredential) -> None:
        """
            Construct a LibvirtConnectionManager.

            :param credential: The :class:`LibvirtConnectionCredential`
                describing the libvirt URI and optional auth callback.
        """
        self._credential: LibvirtConnectionCredential = credential
        self._connection: Optional[Any] = None
        self._closed: bool = False
        return

    def _open(self) -> Any:
        """
            Open a fresh libvirt connection via ``openAuth``.

            :returns: The opened connection handle.

            :raises: :class:`LibvirtConnectionError`
        """
        libvirt_module = _import_libvirt()

        auth_callback = self._credential.auth_callback
        if auth_callback is None:
            auth_callback = LibvirtAuthCallback()

        auth_argument = auth_callback.as_openauth_argument()

        try:
            connection = libvirt_module.openAuth(
                self._credential.uri, auth_argument, 0
            )
        except Exception as xcpt:
            err_msg_lines = ["Failed to open a libvirt connection."]
            err_msg_lines.append("URI: {}".format(self._credential.uri))
            err_msg_lines.append("CAUSE: {}".format(xcpt))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtConnectionError(err_msg) from None

        if connection is None:
            err_msg_lines = ["libvirt.openAuth returned no connection."]
            err_msg_lines.append("URI: {}".format(self._credential.uri))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtConnectionError(err_msg)

        rtnval = connection
        return rtnval

    def _is_alive(self, *, connection: Any) -> bool:
        """
            Probe whether a cached connection is still alive.

            :param connection: The connection handle to probe.

            :returns: True when the connection answers ``isAlive``.
        """
        try:
            alive = connection.isAlive()
        except Exception:
            rtnval = False
            return rtnval
        rtnval = bool(alive)
        return rtnval

    def connection(self, *,
                   aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS) -> Any:
        """
            Return a live libvirt connection, opening or reopening as
            governed by aspects.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A live libvirt connection handle.

            :raises: :class:`LibvirtConnectionError` when the manager is
                closed or when the connection cannot be (re)opened.
        """
        if self._closed is True:
            err_msg_lines = ["The libvirt connection has been closed."]
            err_msg_lines.append("URI: {}".format(self._credential.uri))
            err_msg_lines.append("Construct a new manager to reopen it.")
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtConnectionError(err_msg)

        if self._connection is not None:
            if self._is_alive(connection=self._connection) is True:
                rtnval = self._connection
                return rtnval

            # The connection was dropped by the server.
            if aspects.reconnect_on_drop is not True:
                self._connection = None
                err_msg_lines = ["The libvirt connection was dropped by "
                                 "the server."]
                err_msg_lines.append("URI: {}".format(self._credential.uri))
                err_msg_lines.append("Set aspects.reconnect_on_drop=True "
                                     "to reopen transparently.")
                err_msg = os.linesep.join(err_msg_lines)
                raise LibvirtConnectionError(err_msg)

            self._connection = None

        self._connection = self._open()
        rtnval = self._connection
        return rtnval

    def close(self, *,
              aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS) -> None:
        """
            Close the cached connection and reject further operations.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
        self._closed = True
        return
