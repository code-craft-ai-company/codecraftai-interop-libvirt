"""
    .. module:: volumesgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Storage-volume API group for the libvirt client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


import os

from typing import Any, List, Optional

from automojo.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from automojo.interop.libvirt.apigroups.retrysupport import run_with_retry
from automojo.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)
from automojo.interop.libvirt.exceptions.libvirtoperationerror import (
    LibvirtOperationError
)
from automojo.interop.libvirt.model.libvirtvolume import LibvirtVolume
from automojo.interop.libvirt.specs.libvirtvolumespec import (
    LibvirtVolumeSpec
)
from automojo.interop.libvirt.xml.storagepoolxmlcomposer import (
    StoragePoolXmlComposer
)


def _volume_record(*, native_volume: Any,
                    pool_name: str) -> LibvirtVolume:
    """
        Build a :class:`LibvirtVolume` from a native volume handle.

        :param native_volume: The native libvirt volume object.
        :param pool_name: The owning pool name.

        :returns: A :class:`LibvirtVolume` record.
    """
    capacity = 0
    allocation = 0
    try:
        info = native_volume.info()
        capacity = int(info[1])
        allocation = int(info[2])
    except Exception:
        capacity = 0
        allocation = 0
    rtnval = LibvirtVolume(name=native_volume.name(),
                           pool_name=pool_name,
                           path=native_volume.path(),
                           capacity_bytes=capacity,
                           allocation_bytes=allocation,
                           volume_format="qcow2")
    return rtnval


class VolumesGroup:
    """
        Storage-volume operations for :class:`LibvirtClient`.

        ``delete_volume`` is idempotent.
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

    def _require_pool(self, *, connection: Any, pool_name: str) -> Any:
        """
            Look up a storage pool, raising when it is absent.

            :param connection: The native libvirt connection.
            :param pool_name: The pool name.

            :returns: The native pool handle.

            :raises: :class:`LibvirtOperationError`
        """
        try:
            rtnval = connection.storagePoolLookupByName(pool_name)
        except Exception as xcpt:
            err_msg_lines = ["The named storage pool was not found."]
            err_msg_lines.append("POOL: {}".format(pool_name))
            err_msg_lines.append("CAUSE: {}".format(xcpt))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtOperationError(err_msg) from None
        return rtnval

    def _find_volume(self, *, pool: Any,
                     name: str) -> Optional[Any]:
        """
            Look up a volume within a pool, tolerating absence.

            :param pool: The native pool handle.
            :param name: The volume name.

            :returns: The native volume handle or ``None``.
        """
        try:
            rtnval = pool.storageVolLookupByName(name)
        except Exception:
            rtnval = None
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
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> List[LibvirtVolume]:
            pool = self._require_pool(connection=connection,
                                      pool_name=pool_name)
            records: List[LibvirtVolume] = []
            for native in pool.listAllVolumes():
                records.append(_volume_record(native_volume=native,
                                               pool_name=pool_name))
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
        connection = self._connection_manager.connection(aspects=aspects)
        xml_document = self._composer.compose_volume(spec=spec)

        def _operation() -> LibvirtVolume:
            pool = self._require_pool(connection=connection,
                                      pool_name=pool_name)
            existing = self._find_volume(pool=pool, name=spec.name)
            if existing is not None:
                result = _volume_record(native_volume=existing,
                                        pool_name=pool_name)
                return result
            native = pool.createXML(xml_document, 0)
            result = _volume_record(native_volume=native,
                                    pool_name=pool_name)
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
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            pool = self._require_pool(connection=connection,
                                      pool_name=pool_name)
            native = self._find_volume(pool=pool, name=name)
            if native is None:
                return None
            native.delete(0)
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

            :raises: :class:`LibvirtOperationError` when the volume is
                absent.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            pool = self._require_pool(connection=connection,
                                      pool_name=pool_name)
            native = self._find_volume(pool=pool, name=name)
            if native is None:
                err_msg_lines = ["Cannot resize an absent volume."]
                err_msg_lines.append("POOL: {}".format(pool_name))
                err_msg_lines.append("VOLUME: {}".format(name))
                err_msg = os.linesep.join(err_msg_lines)
                raise LibvirtOperationError(err_msg)
            native.resize(capacity_bytes, 0)
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="resize_volume")
        return
