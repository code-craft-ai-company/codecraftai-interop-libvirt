"""
    .. module:: libvirtconnectioncredential
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Typed credential carrying a libvirt connection URI and an
               optional authentication callback.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []



class LibvirtConnectionCredential:
    """
        Credential describing how to reach a libvirt daemon.

        libvirt connections are addressed by URI (``qemu:///system``,
        ``qemu+ssh://host/system``, ``qemu:///session``).  Authentication
        is carried by the URI and the command runner's own transport
        (an SSH-backed runner authenticates with its SSH credential), so
        no callback machinery is required.
    """

    def __init__(self, *, uri: str) -> None:
        """
            Construct a LibvirtConnectionCredential.

            :param uri: The libvirt connection URI.
        """
        if uri is None or len(uri) == 0:
            raise ValueError("LibvirtConnectionCredential.uri must not "
                             "be empty.")
        self._uri: str = uri
        return

    @property
    def uri(self) -> str:
        """
            Return the libvirt connection URI.

            :returns: The connection URI string.
        """
        rtnval = self._uri
        return rtnval

