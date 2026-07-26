"""
    .. module:: networksgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Virtual-network API group for the libvirt client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import List, Optional

from ccai.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from ccai.interop.libvirt.apigroups.retrysupport import run_with_retry
from ccai.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)
from ccai.interop.libvirt.connection.virshparsers import (
    parse_key_value_block, parse_name_lines, parse_yes_no
)
from ccai.interop.libvirt.model.libvirtnetwork import LibvirtNetwork
from ccai.interop.libvirt.specs.libvirtnetworkspec import (
    LibvirtNetworkSpec
)
from ccai.interop.libvirt.xml.networkxmlcomposer import (
    NetworkXmlComposer
)


class NetworksGroup:
    """
        Virtual-network operations for :class:`LibvirtClient`.

        ``define_network`` and ``undefine_network`` are idempotent.
    """

    def __init__(self, *,
                 connection_manager: LibvirtConnectionManager) -> None:
        """
            Construct a NetworksGroup.

            :param connection_manager: The shared connection manager.
        """
        self._connection_manager: LibvirtConnectionManager = (
            connection_manager
        )
        self._composer: NetworkXmlComposer = NetworkXmlComposer()
        return

    def _find_info(self, *, name: str,
                   aspects: AspectsNative) -> Optional[dict]:
        """
            Look up a network's ``net-info`` fields, tolerating absence.

            :param name: The network name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The parsed field dict or ``None``.
        """
        output = self._connection_manager.probe(
            args=["net-info", name], aspects=aspects)
        if output is None:
            rtnval = None
            return rtnval
        rtnval = parse_key_value_block(output)
        return rtnval

    def _network_record(self, *, name: str, fields: dict) -> LibvirtNetwork:
        """
            Build a :class:`LibvirtNetwork` from ``net-info`` fields.

            :param name: The network name.
            :param fields: The parsed ``net-info`` field dict.

            :returns: A :class:`LibvirtNetwork` record.
        """
        bridge = fields.get("Bridge", "").strip()
        if len(bridge) == 0:
            bridge = None
        rtnval = LibvirtNetwork(name=name,
                                uuid=fields.get("UUID", ""),
                                active=parse_yes_no(
                                    fields.get("Active", "no")),
                                forward_mode="",
                                bridge=bridge)
        return rtnval

    def list_networks(self, *,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> List[LibvirtNetwork]:
        """
            List all defined virtual networks.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A list of :class:`LibvirtNetwork` records.
        """
        manager = self._connection_manager

        def _operation() -> List[LibvirtNetwork]:
            output = manager.run(args=["net-list", "--all", "--name"],
                                 aspects=aspects,
                                 description="list_networks")
            records: List[LibvirtNetwork] = []
            for name in parse_name_lines(output):
                fields = self._find_info(name=name, aspects=aspects)
                if fields is None:
                    continue
                records.append(self._network_record(name=name,
                                                    fields=fields))
            return records

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="list_networks")
        return rtnval

    def define_network(self, *, spec: LibvirtNetworkSpec,
                       aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                       ) -> LibvirtNetwork:
        """
            Define a virtual network from a spec, idempotently.

            When a network with the same name already exists the existing
            record is returned and no redefinition occurs.

            :param spec: The :class:`LibvirtNetworkSpec`.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtNetwork` record.
        """
        manager = self._connection_manager
        xml_document = self._composer.compose(spec=spec)

        def _operation() -> LibvirtNetwork:
            existing = self._find_info(name=spec.name, aspects=aspects)
            if existing is not None:
                result = self._network_record(name=spec.name,
                                              fields=existing)
                return result
            manager.run(args=["net-define", "/dev/stdin"],
                        stdin=xml_document, aspects=aspects,
                        description="define_network")
            fields = self._find_info(name=spec.name, aspects=aspects)
            if fields is None:
                fields = {}
            result = self._network_record(name=spec.name, fields=fields)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="define_network")
        return rtnval

    def start_network(self, *, name: str,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> None:
        """
            Start (activate) a defined virtual network.

            Starting an unknown or already-active network is a no-op.

            :param name: The network name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            fields = self._find_info(name=name, aspects=aspects)
            if fields is None:
                return None
            if parse_yes_no(fields.get("Active", "no")) is False:
                manager.run(args=["net-start", name], aspects=aspects,
                            description="start_network")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="start_network")
        return

    def stop_network(self, *, name: str,
                     aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                     ) -> None:
        """
            Stop (deactivate) a running virtual network.

            Stopping an unknown or inactive network is a no-op.

            :param name: The network name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            fields = self._find_info(name=name, aspects=aspects)
            if fields is None:
                return None
            if parse_yes_no(fields.get("Active", "no")) is True:
                manager.run(args=["net-destroy", name], aspects=aspects,
                            description="stop_network")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="stop_network")
        return

    def undefine_network(self, *, name: str,
                         aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                         ) -> None:
        """
            Undefine a virtual network, idempotently.

            Undefining an unknown network is a no-op.  A running network
            is stopped first.

            :param name: The network name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            fields = self._find_info(name=name, aspects=aspects)
            if fields is None:
                return None
            if parse_yes_no(fields.get("Active", "no")) is True:
                manager.run(args=["net-destroy", name], aspects=aspects,
                            description="undefine_network")
            manager.run(args=["net-undefine", name], aspects=aspects,
                        description="undefine_network")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="undefine_network")
        return
