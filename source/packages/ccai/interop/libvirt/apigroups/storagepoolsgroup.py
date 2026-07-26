"""
    .. module:: storagepoolsgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Storage-pool API group for the libvirt client.

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
    parse_key_value_block, parse_memory_kib, parse_name_lines
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

    def _find_info(self, *, name: str,
                   aspects: AspectsNative) -> Optional[dict]:
        """
            Look up a pool's ``pool-info`` fields, tolerating absence.

            :param name: The pool name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The parsed field dict or ``None``.
        """
        output = self._connection_manager.probe(
            args=["pool-info", "--bytes", name], aspects=aspects)
        if output is None:
            rtnval = None
            return rtnval
        rtnval = parse_key_value_block(output)
        return rtnval

    def _pool_record(self, *, name: str, fields: dict) -> LibvirtStoragePool:
        """
            Build a :class:`LibvirtStoragePool` from ``pool-info`` fields.

            :param name: The pool name.
            :param fields: The parsed ``pool-info`` field dict.

            :returns: A :class:`LibvirtStoragePool` record.
        """
        state = fields.get("State", "").strip().lower()
        rtnval = LibvirtStoragePool(
            name=name,
            uuid=fields.get("UUID", ""),
            pool_type="dir",
            active=state == "running",
            capacity_bytes=parse_memory_kib(fields.get("Capacity", "0")),
            available_bytes=parse_memory_kib(fields.get("Available", "0")),
        )
        return rtnval

    def list_storage_pools(self, *,
                           aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                           ) -> List[LibvirtStoragePool]:
        """
            List all defined storage pools.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A list of :class:`LibvirtStoragePool` records.
        """
        manager = self._connection_manager

        def _operation() -> List[LibvirtStoragePool]:
            output = manager.run(args=["pool-list", "--all", "--name"],
                                 aspects=aspects,
                                 description="list_storage_pools")
            records: List[LibvirtStoragePool] = []
            for name in parse_name_lines(output):
                fields = self._find_info(name=name, aspects=aspects)
                if fields is None:
                    continue
                records.append(self._pool_record(name=name, fields=fields))
            return records

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="list_storage_pools")
        return rtnval

    def define_storage_pool(self, *, spec: LibvirtStoragePoolSpec,
                            aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                            ) -> LibvirtStoragePool:
        """
            Define a storage pool from a spec, idempotently.

            When a pool with the same name already exists the existing
            record is returned and no redefinition occurs.

            :param spec: The :class:`LibvirtStoragePoolSpec`.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtStoragePool` record.
        """
        manager = self._connection_manager
        xml_document = self._composer.compose_pool(spec=spec)

        def _operation() -> LibvirtStoragePool:
            existing = self._find_info(name=spec.name, aspects=aspects)
            if existing is not None:
                result = self._pool_record(name=spec.name, fields=existing)
                return result
            manager.run(args=["pool-define", "/dev/stdin"],
                        stdin=xml_document, aspects=aspects,
                        description="define_storage_pool")
            fields = self._find_info(name=spec.name, aspects=aspects)
            if fields is None:
                fields = {}
            result = self._pool_record(name=spec.name, fields=fields)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="define_storage_pool")
        return rtnval

    def start_storage_pool(self, *, name: str,
                           aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                           ) -> None:
        """
            Start (activate) a defined storage pool.

            Starting an unknown or already-active pool is a no-op.

            :param name: The pool name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            fields = self._find_info(name=name, aspects=aspects)
            if fields is None:
                return None
            state = fields.get("State", "").strip().lower()
            if state != "running":
                manager.run(args=["pool-start", name], aspects=aspects,
                            description="start_storage_pool")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="start_storage_pool")
        return

    def stop_storage_pool(self, *, name: str,
                          aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                          ) -> None:
        """
            Stop (deactivate) a running storage pool.

            Stopping an unknown or inactive pool is a no-op.

            :param name: The pool name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            fields = self._find_info(name=name, aspects=aspects)
            if fields is None:
                return None
            state = fields.get("State", "").strip().lower()
            if state == "running":
                manager.run(args=["pool-destroy", name], aspects=aspects,
                            description="stop_storage_pool")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="stop_storage_pool")
        return

    def undefine_storage_pool(self, *, name: str,
                              aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                              ) -> None:
        """
            Undefine a storage pool, idempotently.

            Undefining an unknown pool is a no-op.  A running pool is
            stopped first.

            :param name: The pool name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            fields = self._find_info(name=name, aspects=aspects)
            if fields is None:
                return None
            state = fields.get("State", "").strip().lower()
            if state == "running":
                manager.run(args=["pool-destroy", name], aspects=aspects,
                            description="undefine_storage_pool")
            manager.run(args=["pool-undefine", name], aspects=aspects,
                        description="undefine_storage_pool")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="undefine_storage_pool")
        return
