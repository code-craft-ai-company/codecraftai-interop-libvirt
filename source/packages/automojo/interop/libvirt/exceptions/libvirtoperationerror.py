"""
    .. module:: libvirtoperationerror
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Exception raised when a libvirt operation fails after the
               aspects retry budget is exhausted.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


class LibvirtOperationError(RuntimeError):
    """
        Raised when a libvirt operation fails and the failure is not a
        connection drop — for example a domain that cannot be started or
        a storage pool that cannot be defined.
    """
