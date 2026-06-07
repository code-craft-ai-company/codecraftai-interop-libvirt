"""
    .. module:: storagepoolsgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Storage-pool API group for the libvirt client.

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
from ccai.interop.libvirt.model.libvirtstoragepool import (
    LibvirtStoragePool
)
from ccai.interop.libvirt.specs.libvirtstoragepoolspec import (
    LibvirtStoragePoolSpec
)
from ccai.interop.libvirt.xml.storagepoolxmlcomposer import (
    StoragePoolXmlComposer
)


def _pool_record(*, native_pool: Any) -> LibvirtStoragePool:
    """
        Build a :class:`LibvirtStoragePool` from a native pool handle.

        :param native_pool: The native libvirt storage-pool object.

        :returns: A :class:`LibvirtStoragePool` record.
    """
    capacity = 0
    available = 0
    try:
        info = native_pool.info()
        capacity = int(info[1])
        available = int(info[3])
    except Exception:
        capacity = 0
        available = 0
    rtnval = LibvirtStoragePool(name=native_pool.name(),
                                uuid=native_pool.UUIDString(),
                                pool_type="dir",
                                active=bool(native_pool.isActive()),
                                capacity_bytes=capacity,
                                available_bytes=available)
    return rtnval


class StoragePoolsGroup:
    """
        Storage-pool operations for :class:`LibvirtClient`.

        ``define_storage_pool`` and ``undefine_storage_pool`` are
        idempotent.
    """

    def __init__(self, *,
                 connection_manager: LibvirtConnectionManager) -> None:
        """
            Construct a StoragePoolsGroup.

            :param connection_manager: The shared connection manager.
        """
        self._connection_manager: LibvirtConnectionManager = (
            connection_manager
        )
        self._composer: StoragePoolXmlComposer = StoragePoolXmlComposer()
        return

    def _find_native(self, *, connection: Any,
                     name: str) -> Optional[Any]:
        """
            Look up a native storage pool by name, tolerating absence.

            :param connection: The native libvirt connection.
            :param name: The pool name.

            :returns: The native pool handle or ``None``.
        """
        try:
            rtnval = connection.storagePoolLookupByName(name)
        except Exception:
            rtnval = None
        return rtnval

    def list_storage_pools(self, *,
                           aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                           ) -> List[LibvirtStoragePool]:
        """
            List all defined storage pools.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A list of :class:`LibvirtStoragePool` records.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> List[LibvirtStoragePool]:
            records: List[LibvirtStoragePool] = []
            for native in connection.listAllStoragePools():
                records.append(_pool_record(native_pool=native))
            return records

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="list_storage_pools")
        return rtnval

    def define_storage_pool(self, *, spec: LibvirtStoragePoolSpec,
                            aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                            ) -> LibvirtStoragePool:
        """
            Define a storage pool from a spec, idempotently.

            :param spec: The :class:`LibvirtStoragePoolSpec`.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtStoragePool` record.
        """
        connection = self._connection_manager.connection(aspects=aspects)
        xml_document = self._composer.compose_pool(spec=spec)

        def _operation() -> LibvirtStoragePool:
            existing = self._find_native(connection=connection,
                                         name=spec.name)
            if existing is not None:
                result = _pool_record(native_pool=existing)
                return result
            native = connection.storagePoolDefineXML(xml_document, 0)
            result = _pool_record(native_pool=native)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="define_storage_pool")
        return rtnval

    def start_storage_pool(self, *, name: str,
                           aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                           ) -> None:
        """
            Start (activate) a defined storage pool.

            :param name: The pool name.
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
                       description="start_storage_pool")
        return

    def stop_storage_pool(self, *, name: str,
                          aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                          ) -> None:
        """
            Stop (deactivate) a running storage pool.

            :param name: The pool name.
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
                       description="stop_storage_pool")
        return

    def undefine_storage_pool(self, *, name: str,
                              aspects: AspectsNative =
                              DEFAULT_LIBVIRT_ASPECTS) -> None:
        """
            Undefine a storage pool, idempotently.

            Undefining an unknown pool is a no-op.

            :param name: The pool name.
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
                       description="undefine_storage_pool")
        return
