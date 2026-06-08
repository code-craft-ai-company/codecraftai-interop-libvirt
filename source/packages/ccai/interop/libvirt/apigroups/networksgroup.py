"""
    .. module:: networksgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Virtual-network API group for the libvirt client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, List, Optional

from ccai.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from ccai.interop.libvirt.apigroups.retrysupport import run_with_retry
from ccai.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)
from ccai.interop.libvirt.model.libvirtnetwork import LibvirtNetwork
from ccai.interop.libvirt.specs.libvirtnetworkspec import (
    LibvirtNetworkSpec
)
from ccai.interop.libvirt.xml.networkxmlcomposer import (
    NetworkXmlComposer
)


def _network_record(*, native_network: Any) -> LibvirtNetwork:
    """
        Build a :class:`LibvirtNetwork` from a native network handle.

        :param native_network: The native libvirt network object.

        :returns: A :class:`LibvirtNetwork` record.
    """
    try:
        bridge = native_network.bridgeName()
    except Exception:
        bridge = None
    rtnval = LibvirtNetwork(name=native_network.name(),
                            uuid=native_network.UUIDString(),
                            active=bool(native_network.isActive()),
                            forward_mode="",
                            bridge=bridge)
    return rtnval


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

    def _find_native(self, *, connection: Any,
                     name: str) -> Optional[Any]:
        """
            Look up a native network by name, tolerating absence.

            :param connection: The native libvirt connection.
            :param name: The network name.

            :returns: The native network handle or ``None``.
        """
        try:
            rtnval = connection.networkLookupByName(name)
        except Exception:
            rtnval = None
        return rtnval

    def list_networks(self, *,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> List[LibvirtNetwork]:
        """
            List all defined virtual networks.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A list of :class:`LibvirtNetwork` records.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> List[LibvirtNetwork]:
            records: List[LibvirtNetwork] = []
            for native in connection.listAllNetworks():
                records.append(_network_record(native_network=native))
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
        connection = self._connection_manager.connection(aspects=aspects)
        xml_document = self._composer.compose(spec=spec)

        def _operation() -> LibvirtNetwork:
            existing = self._find_native(connection=connection,
                                         name=spec.name)
            if existing is not None:
                result = _network_record(native_network=existing)
                return result
            native = connection.networkDefineXML(xml_document)
            result = _network_record(native_network=native)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="define_network")
        return rtnval

    def start_network(self, *, name: str,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> None:
        """
            Start (activate) a defined virtual network.

            :param name: The network name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            native = self._find_native(connection=connection, name=name)
            if native is None:
                return None
            if bool(native.isActive()) is False:
                native.create()
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="start_network")
        return

    def stop_network(self, *, name: str,
                     aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                     ) -> None:
        """
            Stop (deactivate) a running virtual network.

            :param name: The network name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            native = self._find_native(connection=connection, name=name)
            if native is None:
                return None
            if bool(native.isActive()) is True:
                native.destroy()
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="stop_network")
        return

    def undefine_network(self, *, name: str,
                         aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                         ) -> None:
        """
            Undefine a virtual network, idempotently.

            Undefining an unknown network is a no-op.

            :param name: The network name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            native = self._find_native(connection=connection, name=name)
            if native is None:
                return None
            if bool(native.isActive()) is True:
                native.destroy()
            native.undefine()
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="undefine_network")
        return
