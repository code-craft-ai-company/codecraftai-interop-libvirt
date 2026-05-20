"""
    .. module:: libvirtclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: LibvirtClient — typed native-binding client for libvirt
               managed hypervisors (KVM / QEMU and friends).

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from automojo.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from automojo.interop.libvirt.apigroups.domainsgroup import DomainsGroup
from automojo.interop.libvirt.apigroups.hostgroup import HostGroup
from automojo.interop.libvirt.apigroups.networksgroup import NetworksGroup
from automojo.interop.libvirt.apigroups.snapshotsgroup import (
    SnapshotsGroup
)
from automojo.interop.libvirt.apigroups.storagepoolsgroup import (
    StoragePoolsGroup
)
from automojo.interop.libvirt.apigroups.volumesgroup import VolumesGroup
from automojo.interop.libvirt.connection.libvirtconnectioncredential import (
    LibvirtConnectionCredential
)
from automojo.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)


class LibvirtClient:
    """
        Typed client for a libvirt-managed hypervisor.

        ``LibvirtClient`` wraps the official ``libvirt-python`` native
        bindings.  libvirt's wire protocol is a binary RPC, not REST, so
        this client does **not** derive from ``RestClientBase`` — it is
        the suite's canonical native-binding client.  The "one transport
        per package" rule still holds: nothing here speaks HTTP or shells
        out to a CLI.

        The API surface is split into six groups — host, networks,
        storage pools, volumes, domains, and snapshots — each reachable
        through a public attribute.  Every behaviour-bearing call accepts
        ``aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS``.
    """

    def __init__(self, *,
                 credential: LibvirtConnectionCredential) -> None:
        """
            Construct a LibvirtClient.

            The libvirt connection is opened lazily on first use; merely
            constructing the client does not require a reachable
            hypervisor or the native bindings.

            :param credential: The :class:`LibvirtConnectionCredential`
                describing the libvirt URI and optional auth callback.
        """
        self._credential: LibvirtConnectionCredential = credential
        self._connection_manager: LibvirtConnectionManager = (
            LibvirtConnectionManager(credential=credential)
        )
        self._host: HostGroup = HostGroup(
            connection_manager=self._connection_manager
        )
        self._networks: NetworksGroup = NetworksGroup(
            connection_manager=self._connection_manager
        )
        self._storage_pools: StoragePoolsGroup = StoragePoolsGroup(
            connection_manager=self._connection_manager
        )
        self._volumes: VolumesGroup = VolumesGroup(
            connection_manager=self._connection_manager
        )
        self._domains: DomainsGroup = DomainsGroup(
            connection_manager=self._connection_manager
        )
        self._snapshots: SnapshotsGroup = SnapshotsGroup(
            connection_manager=self._connection_manager
        )
        return

    @property
    def host(self) -> HostGroup:
        """
            Return the host / node information API group.

            :returns: The :class:`HostGroup`.
        """
        rtnval = self._host
        return rtnval

    @property
    def networks(self) -> NetworksGroup:
        """
            Return the virtual-network API group.

            :returns: The :class:`NetworksGroup`.
        """
        rtnval = self._networks
        return rtnval

    @property
    def storage_pools(self) -> StoragePoolsGroup:
        """
            Return the storage-pool API group.

            :returns: The :class:`StoragePoolsGroup`.
        """
        rtnval = self._storage_pools
        return rtnval

    @property
    def volumes(self) -> VolumesGroup:
        """
            Return the storage-volume API group.

            :returns: The :class:`VolumesGroup`.
        """
        rtnval = self._volumes
        return rtnval

    @property
    def domains(self) -> DomainsGroup:
        """
            Return the domain (virtual machine) API group.

            :returns: The :class:`DomainsGroup`.
        """
        rtnval = self._domains
        return rtnval

    @property
    def snapshots(self) -> SnapshotsGroup:
        """
            Return the domain-snapshot API group.

            :returns: The :class:`SnapshotsGroup`.
        """
        rtnval = self._snapshots
        return rtnval

    def close(self, *,
              aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS) -> None:
        """
            Close the underlying libvirt connection.

            After ``close`` the client rejects further operations until a
            new client is constructed.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        self._connection_manager.close(aspects=aspects)
        return
