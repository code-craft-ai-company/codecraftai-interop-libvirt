"""
    .. module:: libvirtconnectionerror
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Exception raised when a libvirt connection cannot be
               established or has been dropped.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


class LibvirtConnectionError(RuntimeError):
    """
        Raised when a libvirt connection cannot be opened, has been
        dropped by the server, or an operation is attempted against a
        closed connection.
    """
