"""
    .. module:: hostgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Host / node information API group for the libvirt client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from ccai.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from ccai.interop.libvirt.apigroups.retrysupport import run_with_retry
from ccai.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)
from ccai.interop.libvirt.connection.virshparsers import (
    parse_key_value_block, parse_memory_kib, parse_version_field,
    parse_version_number
)
from ccai.interop.libvirt.model.libvirthostinfo import LibvirtHostInfo
from ccai.interop.libvirt.model.libvirtnodeinfo import LibvirtNodeInfo


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
        manager = self._connection_manager

        def _operation() -> LibvirtHostInfo:
            hostname = manager.run(args=["hostname"], aspects=aspects,
                                   description="host_info").strip()
            version_output = manager.run(args=["version"], aspects=aspects,
                                         description="host_info")
            hypervisor_line = parse_version_field(
                version_output, label="Running hypervisor")
            if len(hypervisor_line) > 0:
                hypervisor_type = hypervisor_line.split()[0]
            else:
                hypervisor_type = "unknown"
            version = parse_version_number(hypervisor_line)
            capabilities = manager.run(args=["capabilities"],
                                       aspects=aspects,
                                       description="host_info")
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
        manager = self._connection_manager

        def _operation() -> LibvirtNodeInfo:
            output = manager.run(args=["nodeinfo"], aspects=aspects,
                                 description="node_info")
            fields = parse_key_value_block(output)
            result = LibvirtNodeInfo(
                model=fields.get("CPU model", "unknown"),
                memory_kib=parse_memory_kib(fields.get("Memory size", "0")),
                cpus=int(fields.get("CPU(s)", "0")),
                cores=int(fields.get("Core(s) per socket", "0")),
                sockets=int(fields.get("CPU socket(s)", "0")),
                numa_nodes=int(fields.get("NUMA cell(s)", "0")),
            )
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
        manager = self._connection_manager

        def _operation() -> str:
            result = manager.run(args=["capabilities"], aspects=aspects,
                                 description="capabilities_xml")
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="capabilities_xml")
        return rtnval
