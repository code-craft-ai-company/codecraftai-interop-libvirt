"""
    .. module:: libvirtxmlcompositionerror
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Exception raised when domain / network / storage-pool XML
               composition fails or produces a malformed document.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


class LibvirtXmlCompositionError(ValueError):
    """
        Raised when XML composed from a libvirt spec is not well-formed,
        or when a spec carries values that cannot be safely rendered.
    """
