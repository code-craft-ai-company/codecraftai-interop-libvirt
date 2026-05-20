"""
    .. module:: snapshotsgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Domain-snapshot API group for the libvirt client.

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
from automojo.interop.libvirt.model.libvirtsnapshot import LibvirtSnapshot
from automojo.interop.libvirt.xml.xmlescape import escape_text


class SnapshotsGroup:
    """
        Domain-snapshot operations for :class:`LibvirtClient`.

        ``delete_snapshot`` is idempotent.
    """

    def __init__(self, *,
                 connection_manager: LibvirtConnectionManager) -> None:
        """
            Construct a SnapshotsGroup.

            :param connection_manager: The shared connection manager.
        """
        self._connection_manager: LibvirtConnectionManager = (
            connection_manager
        )
        return

    def _require_domain(self, *, connection: Any,
                        domain_name: str) -> Any:
        """
            Look up a native domain, raising when it is absent.

            :param connection: The native libvirt connection.
            :param domain_name: The domain name.

            :returns: The native domain handle.

            :raises: :class:`LibvirtOperationError`
        """
        try:
            rtnval = connection.lookupByName(domain_name)
        except Exception as xcpt:
            err_msg_lines = ["The named domain was not found."]
            err_msg_lines.append("DOMAIN: {}".format(domain_name))
            err_msg_lines.append("CAUSE: {}".format(xcpt))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtOperationError(err_msg) from None
        return rtnval

    def _find_snapshot(self, *, native_domain: Any,
                       name: str) -> Optional[Any]:
        """
            Look up a snapshot by name, tolerating absence.

            :param native_domain: The native domain handle.
            :param name: The snapshot name.

            :returns: The native snapshot handle or ``None``.
        """
        try:
            rtnval = native_domain.snapshotLookupByName(name, 0)
        except Exception:
            rtnval = None
        return rtnval

    def create_snapshot(self, *, domain_name: str, name: str,
                        aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                        ) -> LibvirtSnapshot:
        """
            Create a domain snapshot, idempotently.

            When a snapshot with the same name already exists the
            existing record is returned.

            :param domain_name: The domain name.
            :param name: The snapshot name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtSnapshot` record.
        """
        connection = self._connection_manager.connection(aspects=aspects)
        escaped_name = escape_text(value=name)
        snapshot_xml = os.linesep.join([
            "<domainsnapshot>",
            "  <name>{}</name>".format(escaped_name),
            "</domainsnapshot>",
        ]) + os.linesep

        def _operation() -> LibvirtSnapshot:
            native_domain = self._require_domain(connection=connection,
                                                 domain_name=domain_name)
            existing = self._find_snapshot(native_domain=native_domain,
                                           name=name)
            if existing is not None:
                result = LibvirtSnapshot(name=name,
                                         domain_name=domain_name,
                                         is_current=True)
                return result
            native_domain.snapshotCreateXML(snapshot_xml, 0)
            result = LibvirtSnapshot(name=name, domain_name=domain_name,
                                     is_current=True)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="create_snapshot")
        return rtnval

    def list_snapshots(self, *, domain_name: str,
                       aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                       ) -> List[LibvirtSnapshot]:
        """
            List all snapshots of a domain.

            :param domain_name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A list of :class:`LibvirtSnapshot` records.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> List[LibvirtSnapshot]:
            native_domain = self._require_domain(connection=connection,
                                                 domain_name=domain_name)
            records: List[LibvirtSnapshot] = []
            for native in native_domain.listAllSnapshots(0):
                is_current = False
                try:
                    is_current = bool(native.isCurrent(0))
                except Exception:
                    is_current = False
                records.append(LibvirtSnapshot(name=native.getName(),
                                               domain_name=domain_name,
                                               is_current=is_current))
            return records

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="list_snapshots")
        return rtnval

    def revert_snapshot(self, *, domain_name: str, name: str,
                        aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                        ) -> None:
        """
            Revert a domain to a named snapshot.

            :param domain_name: The domain name.
            :param name: The snapshot name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.

            :raises: :class:`LibvirtOperationError` when the snapshot is
                absent.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            native_domain = self._require_domain(connection=connection,
                                                 domain_name=domain_name)
            native = self._find_snapshot(native_domain=native_domain,
                                         name=name)
            if native is None:
                err_msg_lines = ["Cannot revert to an absent snapshot."]
                err_msg_lines.append("DOMAIN: {}".format(domain_name))
                err_msg_lines.append("SNAPSHOT: {}".format(name))
                err_msg = os.linesep.join(err_msg_lines)
                raise LibvirtOperationError(err_msg)
            native_domain.revertToSnapshot(native, 0)
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="revert_snapshot")
        return

    def delete_snapshot(self, *, domain_name: str, name: str,
                        aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                        ) -> None:
        """
            Delete a domain snapshot, idempotently.

            Deleting an unknown snapshot is a no-op.

            :param domain_name: The domain name.
            :param name: The snapshot name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            native_domain = self._require_domain(connection=connection,
                                                 domain_name=domain_name)
            native = self._find_snapshot(native_domain=native_domain,
                                         name=name)
            if native is None:
                return None
            native.delete(0)
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="delete_snapshot")
        return
