"""
    .. module:: snapshotsgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Domain-snapshot API group for the libvirt client.

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
from ccai.interop.libvirt.connection.virshparsers import parse_name_lines
from ccai.interop.libvirt.exceptions.libvirtoperationerror import (
    LibvirtOperationError
)
from ccai.interop.libvirt.model.libvirtsnapshot import LibvirtSnapshot
from ccai.interop.libvirt.xml.xmlescape import escape_text


class SnapshotsGroup:
    """
        Domain-snapshot operations for :class:`LibvirtClient`.

        ``create_snapshot`` and ``delete_snapshot`` are idempotent.
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

    def _require_domain(self, *, domain_name: str,
                        aspects: AspectsNative) -> None:
        """
            Verify a domain exists, raising when it is absent.

            :param domain_name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :raises: :class:`LibvirtOperationError`
        """
        output = self._connection_manager.probe(
            args=["dominfo", domain_name], aspects=aspects)
        if output is None:
            err_msg_lines = ["The named domain was not found."]
            err_msg_lines.append("DOMAIN: {}".format(domain_name))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtOperationError(err_msg)
        return

    def _snapshot_exists(self, *, domain_name: str, name: str,
                         aspects: AspectsNative) -> bool:
        """
            Test whether a named snapshot exists, tolerating absence.

            :param domain_name: The domain name.
            :param name: The snapshot name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``True`` when the snapshot exists.
        """
        output = self._connection_manager.probe(
            args=["snapshot-info", domain_name, "--snapshotname", name],
            aspects=aspects)
        rtnval = output is not None
        return rtnval

    def _current_snapshot_name(self, *, domain_name: str,
                               aspects: AspectsNative) -> Optional[str]:
        """
            Return the current snapshot's name, tolerating absence.

            :param domain_name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The current snapshot name or ``None``.
        """
        output = self._connection_manager.probe(
            args=["snapshot-current", domain_name, "--name"],
            aspects=aspects)
        if output is None:
            rtnval = None
            return rtnval
        rtnval = output.strip()
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
        manager = self._connection_manager
        escaped_name = escape_text(value=name)
        snapshot_xml = os.linesep.join([
            "<domainsnapshot>",
            "  <name>{}</name>".format(escaped_name),
            "</domainsnapshot>",
        ]) + os.linesep

        def _operation() -> LibvirtSnapshot:
            self._require_domain(domain_name=domain_name, aspects=aspects)
            if self._snapshot_exists(domain_name=domain_name, name=name,
                                     aspects=aspects) is True:
                result = LibvirtSnapshot(name=name,
                                         domain_name=domain_name,
                                         is_current=True)
                return result
            manager.run(args=["snapshot-create", domain_name,
                              "/dev/stdin"],
                        stdin=snapshot_xml, aspects=aspects,
                        description="create_snapshot")
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
        manager = self._connection_manager

        def _operation() -> List[LibvirtSnapshot]:
            self._require_domain(domain_name=domain_name, aspects=aspects)
            output = manager.run(args=["snapshot-list", domain_name,
                                       "--name"],
                                 aspects=aspects,
                                 description="list_snapshots")
            current = self._current_snapshot_name(
                domain_name=domain_name, aspects=aspects)
            records: List[LibvirtSnapshot] = []
            for snap_name in parse_name_lines(output):
                records.append(LibvirtSnapshot(
                    name=snap_name,
                    domain_name=domain_name,
                    is_current=snap_name == current))
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
        manager = self._connection_manager

        def _operation() -> None:
            self._require_domain(domain_name=domain_name, aspects=aspects)
            if self._snapshot_exists(domain_name=domain_name, name=name,
                                     aspects=aspects) is False:
                err_msg_lines = ["Cannot revert to an absent snapshot."]
                err_msg_lines.append("DOMAIN: {}".format(domain_name))
                err_msg_lines.append("SNAPSHOT: {}".format(name))
                err_msg = os.linesep.join(err_msg_lines)
                raise LibvirtOperationError(err_msg)
            manager.run(args=["snapshot-revert", domain_name,
                              "--snapshotname", name],
                        aspects=aspects, description="revert_snapshot")
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
        manager = self._connection_manager

        def _operation() -> None:
            self._require_domain(domain_name=domain_name, aspects=aspects)
            if self._snapshot_exists(domain_name=domain_name, name=name,
                                     aspects=aspects) is False:
                return None
            manager.run(args=["snapshot-delete", domain_name,
                              "--snapshotname", name],
                        aspects=aspects, description="delete_snapshot")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="delete_snapshot")
        return
