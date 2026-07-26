"""
    .. module:: volumesgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Storage-volume API group for the libvirt client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import os

from typing import List, Optional

from ccai.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from ccai.interop.libvirt.apigroups.retrysupport import run_with_retry
from ccai.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)
from ccai.interop.libvirt.connection.virshparsers import (
    parse_key_value_block, parse_memory_kib, parse_volume_table
)
from ccai.interop.libvirt.exceptions.libvirtoperationerror import (
    LibvirtOperationError
)
from ccai.interop.libvirt.model.libvirtvolume import LibvirtVolume
from ccai.interop.libvirt.specs.libvirtvolumespec import (
    LibvirtVolumeSpec
)
from ccai.interop.libvirt.xml.storagepoolxmlcomposer import (
    StoragePoolXmlComposer
)


class VolumesGroup:
    """
        Storage-volume operations for :class:`LibvirtClient`.

        ``create_volume`` and ``delete_volume`` are idempotent.
    """

    def __init__(self, *,
                 connection_manager: LibvirtConnectionManager) -> None:
        """
            Construct a VolumesGroup.

            :param connection_manager: The shared connection manager.
        """
        self._connection_manager: LibvirtConnectionManager = (
            connection_manager
        )
        self._composer: StoragePoolXmlComposer = StoragePoolXmlComposer()
        return

    def _require_pool(self, *, pool_name: str,
                      aspects: AspectsNative) -> None:
        """
            Verify a storage pool exists, raising when it is absent.

            :param pool_name: The pool name.
            :param aspects: The :class:`AspectsNative` carrier.

            :raises: :class:`LibvirtOperationError`
        """
        output = self._connection_manager.probe(
            args=["pool-info", pool_name], aspects=aspects)
        if output is None:
            err_msg_lines = ["The named storage pool was not found."]
            err_msg_lines.append("POOL: {}".format(pool_name))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtOperationError(err_msg)
        return

    def _find_volume_fields(self, *, pool_name: str, name: str,
                            aspects: AspectsNative) -> Optional[dict]:
        """
            Look up a volume's ``vol-info`` fields, tolerating absence.

            :param pool_name: The owning pool name.
            :param name: The volume name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The parsed field dict or ``None``.
        """
        output = self._connection_manager.probe(
            args=["vol-info", "--pool", pool_name, "--bytes", name],
            aspects=aspects)
        if output is None:
            rtnval = None
            return rtnval
        rtnval = parse_key_value_block(output)
        return rtnval

    def _volume_record(self, *, pool_name: str, name: str, fields: dict,
                       aspects: AspectsNative) -> LibvirtVolume:
        """
            Build a :class:`LibvirtVolume` from ``vol-info`` fields.

            :param pool_name: The owning pool name.
            :param name: The volume name.
            :param fields: The parsed ``vol-info`` field dict.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtVolume` record.
        """
        path_output = self._connection_manager.probe(
            args=["vol-path", "--pool", pool_name, name], aspects=aspects)
        path = path_output.strip() if path_output is not None else ""
        rtnval = LibvirtVolume(
            name=name,
            pool_name=pool_name,
            path=path,
            capacity_bytes=parse_memory_kib(fields.get("Capacity", "0")),
            allocation_bytes=parse_memory_kib(fields.get("Allocation", "0")),
            volume_format="qcow2",
        )
        return rtnval

    def list_volumes(self, *, pool_name: str,
                     aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                     ) -> List[LibvirtVolume]:
        """
            List all volumes in a storage pool.

            :param pool_name: The pool name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A list of :class:`LibvirtVolume` records.
        """
        manager = self._connection_manager

        def _operation() -> List[LibvirtVolume]:
            self._require_pool(pool_name=pool_name, aspects=aspects)
            output = manager.run(args=["vol-list", pool_name],
                                 aspects=aspects,
                                 description="list_volumes")
            records: List[LibvirtVolume] = []
            for row in parse_volume_table(output):
                fields = self._find_volume_fields(
                    pool_name=pool_name, name=row["name"], aspects=aspects)
                if fields is None:
                    continue
                records.append(self._volume_record(
                    pool_name=pool_name, name=row["name"], fields=fields,
                    aspects=aspects))
            return records

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="list_volumes")
        return rtnval

    def create_volume(self, *, pool_name: str, spec: LibvirtVolumeSpec,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> LibvirtVolume:
        """
            Create a volume in a pool, idempotently.

            When a volume with the same name already exists the existing
            record is returned.

            :param pool_name: The pool name.
            :param spec: The :class:`LibvirtVolumeSpec`.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtVolume` record.
        """
        manager = self._connection_manager
        xml_document = self._composer.compose_volume(spec=spec)

        def _operation() -> LibvirtVolume:
            self._require_pool(pool_name=pool_name, aspects=aspects)
            existing = self._find_volume_fields(
                pool_name=pool_name, name=spec.name, aspects=aspects)
            if existing is not None:
                result = self._volume_record(
                    pool_name=pool_name, name=spec.name, fields=existing,
                    aspects=aspects)
                return result
            manager.run(args=["vol-create", pool_name, "/dev/stdin"],
                        stdin=xml_document, aspects=aspects,
                        description="create_volume")
            fields = self._find_volume_fields(
                pool_name=pool_name, name=spec.name, aspects=aspects)
            if fields is None:
                fields = {}
            result = self._volume_record(
                pool_name=pool_name, name=spec.name, fields=fields,
                aspects=aspects)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="create_volume")
        return rtnval

    def delete_volume(self, *, pool_name: str, name: str,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> None:
        """
            Delete a volume, idempotently.

            Deleting an unknown volume is a no-op.

            :param pool_name: The pool name.
            :param name: The volume name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            self._require_pool(pool_name=pool_name, aspects=aspects)
            existing = self._find_volume_fields(
                pool_name=pool_name, name=name, aspects=aspects)
            if existing is None:
                return None
            manager.run(args=["vol-delete", "--pool", pool_name, name],
                        aspects=aspects, description="delete_volume")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="delete_volume")
        return

    def resize_volume(self, *, pool_name: str, name: str,
                      capacity_bytes: int,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> None:
        """
            Resize a volume to a new capacity.

            :param pool_name: The pool name.
            :param name: The volume name.
            :param capacity_bytes: The new capacity in bytes.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            self._require_pool(pool_name=pool_name, aspects=aspects)
            manager.run(args=["vol-resize", "--pool", pool_name, name,
                              str(capacity_bytes)],
                        aspects=aspects, description="resize_volume")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="resize_volume")
        return
