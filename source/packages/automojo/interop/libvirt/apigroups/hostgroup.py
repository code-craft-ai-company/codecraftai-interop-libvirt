"""
    .. module:: hostgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Host / node information API group for the libvirt client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from automojo.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from automojo.interop.libvirt.apigroups.retrysupport import run_with_retry
from automojo.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)
from automojo.interop.libvirt.model.libvirthostinfo import LibvirtHostInfo
from automojo.interop.libvirt.model.libvirtnodeinfo import LibvirtNodeInfo


class HostGroup:
    """
        Host and node information operations for :class:`LibvirtClient`.
    """

    def __init__(self, *,
                 connection_manager: LibvirtConnectionManager) -> None:
        """
            Construct a HostGroup.

            :param connection_manager: The shared connection manager.
        """
        self._connection_manager: LibvirtConnectionManager = (
            connection_manager
        )
        return

    def host_info(self, *, aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                  ) -> LibvirtHostInfo:
        """
            Return a :class:`LibvirtHostInfo` summary for the host.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtHostInfo` record.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> LibvirtHostInfo:
            hostname = connection.getHostname()
            hypervisor_type = connection.getType()
            version = connection.getVersion()
            capabilities = connection.getCapabilities()
            summary = capabilities[:120]
            result = LibvirtHostInfo(hostname=hostname,
                                     hypervisor_type=hypervisor_type,
                                     version=version,
                                     capabilities_summary=summary)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="host_info")
        return rtnval

    def node_info(self, *, aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                  ) -> LibvirtNodeInfo:
        """
            Return a :class:`LibvirtNodeInfo` record for the host.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtNodeInfo` record.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> LibvirtNodeInfo:
            raw = connection.getInfo()
            model, memory_mib, cpus, _mhz, sockets, cores, _threads, \
                numa = (raw[0], raw[1], raw[2], raw[3], raw[4], raw[5],
                        raw[6], raw[7])
            result = LibvirtNodeInfo(model=str(model),
                                     memory_kib=int(memory_mib) * 1024,
                                     cpus=int(cpus),
                                     cores=int(cores),
                                     sockets=int(sockets),
                                     numa_nodes=int(numa))
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="node_info")
        return rtnval

    def capabilities_xml(self, *,
                         aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                         ) -> str:
        """
            Return the raw host capabilities XML.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The capabilities XML string.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> str:
            result = connection.getCapabilities()
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="capabilities_xml")
        return rtnval
