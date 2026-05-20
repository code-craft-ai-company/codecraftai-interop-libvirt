"""
    .. module:: libvirtconnectioncredential
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Typed credential carrying a libvirt connection URI and an
               optional authentication callback.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from typing import Optional


class LibvirtConnectionCredential:
    """
        Credential describing how to reach a libvirt daemon.

        libvirt connections are addressed by URI (``qemu:///system``,
        ``qemu+ssh://host/system``, ``qemu:///session``).  SASL / SSH
        transports may additionally require an authentication callback;
        that callback is supplied as an :class:`ILibvirtAuthCallback`.
    """

    def __init__(self, *, uri: str,
                 auth_callback: Optional[object] = None) -> None:
        """
            Construct a LibvirtConnectionCredential.

            :param uri: The libvirt connection URI.
            :param auth_callback: Optional ``ILibvirtAuthCallback`` used
                for SASL / SSH credential delivery.
        """
        if uri is None or len(uri) == 0:
            raise ValueError("LibvirtConnectionCredential.uri must not "
                             "be empty.")
        self._uri: str = uri
        self._auth_callback: Optional[object] = auth_callback
        return

    @property
    def uri(self) -> str:
        """
            Return the libvirt connection URI.

            :returns: The connection URI string.
        """
        rtnval = self._uri
        return rtnval

    @property
    def auth_callback(self) -> Optional[object]:
        """
            Return the optional authentication callback.

            :returns: The ``ILibvirtAuthCallback`` or ``None``.
        """
        rtnval = self._auth_callback
        return rtnval
