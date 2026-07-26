"""
    .. module:: domainsgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Domain (virtual machine) API group for the libvirt client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import os
import time

from typing import Dict, List, Optional

from ccai.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from ccai.interop.libvirt.apigroups.retrysupport import run_with_retry
from ccai.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)
from ccai.interop.libvirt.connection.virshparsers import (
    parse_cpu_time_ns, parse_key_value_block, parse_memory_kib,
    parse_name_lines, parse_state_token
)
from ccai.interop.libvirt.exceptions.libvirtoperationerror import (
    LibvirtOperationError
)
from ccai.interop.libvirt.model.libvirtdomaininfo import (
    LibvirtDomainInfo
)
from ccai.interop.libvirt.specs.libvirtdiskspec import LibvirtDiskSpec
from ccai.interop.libvirt.specs.libvirtdomainspec import (
    LibvirtDomainSpec
)
from ccai.interop.libvirt.specs.libvirtnicspec import LibvirtNicSpec
from ccai.interop.libvirt.xml.domainxmlcomposer import (
    DomainXmlComposer
)


def _xml_attribute_present(haystack: str, attribute: str, value: str) -> bool:
    """
        Tests whether an XML document contains ``attribute="value"`` for either
        quote style.

        ``virsh dumpxml`` output is serialized by libxml2 with double-quoted
        attributes (``dev="vda"``), while the composer emits single quotes
        (``dev='vda'``). Idempotency checks must match both so they work against
        real libvirt output, not only single-quoted fixtures.

        :param haystack: The XML text to search.
        :param attribute: The attribute name (e.g. ``dev`` or ``address``).
        :param value: The attribute value to look for.

        :returns: ``True`` when the attribute/value pair is present.
    """
    single_quoted = "{}='{}'".format(attribute, value)
    double_quoted = '{}="{}"'.format(attribute, value)
    rtnval = single_quoted in haystack or double_quoted in haystack
    return rtnval


def _domain_info(*, name: str, fields: Dict[str, str]) -> LibvirtDomainInfo:
    """
        Build a :class:`LibvirtDomainInfo` from ``dominfo`` fields.

        :param name: The domain name.
        :param fields: The parsed ``dominfo`` field dict.

        :returns: A :class:`LibvirtDomainInfo` record.
    """
    rtnval = LibvirtDomainInfo(
        name=fields.get("Name", name),
        uuid=fields.get("UUID", ""),
        state=parse_state_token(fields.get("State", "")),
        vcpus=int(fields.get("CPU(s)", "0")),
        memory_kib=parse_memory_kib(fields.get("Max memory", "0")),
        cpu_time_ns=parse_cpu_time_ns(fields.get("CPU time", "0s")),
    )
    return rtnval


class DomainsGroup:
    """
        Domain (virtual machine) operations for :class:`LibvirtClient`.

        ``define_domain``, ``undefine_domain``, attach / detach, and the
        device operations are idempotent.
    """

    def __init__(self, *,
                 connection_manager: LibvirtConnectionManager) -> None:
        """
            Construct a DomainsGroup.

            :param connection_manager: The shared connection manager.
        """
        self._connection_manager: LibvirtConnectionManager = (
            connection_manager
        )
        self._composer: DomainXmlComposer = DomainXmlComposer()
        return

    def _find_fields(self, *, name: str,
                     aspects: AspectsNative) -> Optional[Dict[str, str]]:
        """
            Look up a domain's ``dominfo`` fields, tolerating absence.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The parsed field dict or ``None``.
        """
        output = self._connection_manager.probe(
            args=["dominfo", name], aspects=aspects)
        if output is None:
            rtnval = None
            return rtnval
        rtnval = parse_key_value_block(output)
        return rtnval

    def _require_fields(self, *, name: str,
                        aspects: AspectsNative) -> Dict[str, str]:
        """
            Look up a domain's ``dominfo`` fields, raising when absent.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The parsed field dict.

            :raises: :class:`LibvirtOperationError`
        """
        fields = self._find_fields(name=name, aspects=aspects)
        if fields is None:
            err_msg_lines = ["The named domain was not found."]
            err_msg_lines.append("DOMAIN: {}".format(name))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtOperationError(err_msg)
        rtnval = fields
        return rtnval

    def _domain_state(self, *, fields: Dict[str, str]) -> str:
        """
            Extract the stable state token from ``dominfo`` fields.

            :param fields: The parsed ``dominfo`` field dict.

            :returns: The stable state token.
        """
        rtnval = parse_state_token(fields.get("State", ""))
        return rtnval

    def list_domains(self, *,
                     aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                     ) -> List[LibvirtDomainInfo]:
        """
            List all defined domains.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A list of :class:`LibvirtDomainInfo` records.
        """
        manager = self._connection_manager

        def _operation() -> List[LibvirtDomainInfo]:
            output = manager.run(args=["list", "--all", "--name"],
                                 aspects=aspects,
                                 description="list_domains")
            records: List[LibvirtDomainInfo] = []
            for name in parse_name_lines(output):
                fields = self._find_fields(name=name, aspects=aspects)
                if fields is None:
                    continue
                records.append(_domain_info(name=name, fields=fields))
            return records

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="list_domains")
        return rtnval

    def get_domain_info(self, *, name: str,
                        aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                        ) -> LibvirtDomainInfo:
        """
            Return a :class:`LibvirtDomainInfo` for a named domain.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtDomainInfo` record.

            :raises: :class:`LibvirtOperationError` when the domain is
                absent.
        """

        def _operation() -> LibvirtDomainInfo:
            fields = self._require_fields(name=name, aspects=aspects)
            result = _domain_info(name=name, fields=fields)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="get_domain_info")
        return rtnval

    def get_domain_xml(self, *, name: str,
                       aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                       ) -> str:
        """
            Return the domain definition XML.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The domain XML string.
        """
        manager = self._connection_manager

        def _operation() -> str:
            self._require_fields(name=name, aspects=aspects)
            result = manager.run(args=["dumpxml", name], aspects=aspects,
                                 description="get_domain_xml")
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="get_domain_xml")
        return rtnval

    def define_domain(self, *, spec: LibvirtDomainSpec,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> LibvirtDomainInfo:
        """
            Define a domain from a spec, idempotently.

            When a domain with the same name already exists the existing
            record is returned and no redefinition occurs.

            :param spec: The :class:`LibvirtDomainSpec`.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtDomainInfo` record.
        """
        manager = self._connection_manager
        xml_document = self._composer.compose(spec=spec)

        def _operation() -> LibvirtDomainInfo:
            existing = self._find_fields(name=spec.name, aspects=aspects)
            if existing is not None:
                result = _domain_info(name=spec.name, fields=existing)
                return result
            manager.run(args=["define", "/dev/stdin"],
                        stdin=xml_document, aspects=aspects,
                        description="define_domain")
            fields = self._require_fields(name=spec.name, aspects=aspects)
            result = _domain_info(name=spec.name, fields=fields)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="define_domain")
        return rtnval

    def create_domain(self, *, name: str,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> None:
        """
            Start a defined domain.  Already-running is a no-op.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            fields = self._require_fields(name=name, aspects=aspects)
            if self._domain_state(fields=fields) != "running":
                manager.run(args=["start", name], aspects=aspects,
                            description="create_domain")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="create_domain")
        return

    def shutdown_domain(self, *, name: str,
                        aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                        ) -> None:
        """
            Request a graceful guest shutdown.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            self._require_fields(name=name, aspects=aspects)
            manager.run(args=["shutdown", name], aspects=aspects,
                        description="shutdown_domain")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="shutdown_domain")
        return

    def destroy_domain(self, *, name: str,
                       aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                       ) -> None:
        """
            Forcefully stop a domain.  Already-stopped is a no-op.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            fields = self._require_fields(name=name, aspects=aspects)
            if self._domain_state(fields=fields) == "running":
                manager.run(args=["destroy", name], aspects=aspects,
                            description="destroy_domain")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="destroy_domain")
        return

    def reboot_domain(self, *, name: str,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> None:
        """
            Request a guest reboot.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            self._require_fields(name=name, aspects=aspects)
            manager.run(args=["reboot", name], aspects=aspects,
                        description="reboot_domain")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="reboot_domain")
        return

    def suspend_domain(self, *, name: str,
                       aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                       ) -> None:
        """
            Suspend (pause) a running domain.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            self._require_fields(name=name, aspects=aspects)
            manager.run(args=["suspend", name], aspects=aspects,
                        description="suspend_domain")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="suspend_domain")
        return

    def resume_domain(self, *, name: str,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> None:
        """
            Resume a suspended domain.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            self._require_fields(name=name, aspects=aspects)
            manager.run(args=["resume", name], aspects=aspects,
                        description="resume_domain")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="resume_domain")
        return

    def undefine_domain(self, *, name: str,
                        aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                        ) -> None:
        """
            Undefine a domain, idempotently.

            Undefining an unknown domain is a no-op.  A running domain
            is destroyed first.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager

        def _operation() -> None:
            fields = self._find_fields(name=name, aspects=aspects)
            if fields is None:
                return None
            if self._domain_state(fields=fields) == "running":
                manager.run(args=["destroy", name], aspects=aspects,
                            description="undefine_domain")
            manager.run(args=["undefine", name], aspects=aspects,
                        description="undefine_domain")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="undefine_domain")
        return

    # ------------------------------------------------------------------
    # Device operations
    # ------------------------------------------------------------------

    def _current_xml(self, *, name: str, aspects: AspectsNative) -> str:
        """
            Return the current domain XML for idempotency checks.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The domain XML string.
        """
        rtnval = self._connection_manager.run(
            args=["dumpxml", name], aspects=aspects,
            description="dumpxml")
        return rtnval

    def attach_disk(self, *, domain_name: str, spec: LibvirtDiskSpec,
                    aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                    ) -> None:
        """
            Attach a disk device to a domain, idempotently.

            When a device with the same target is already attached the
            call is a no-op.

            :param domain_name: The domain name.
            :param spec: The :class:`LibvirtDiskSpec`.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager
        device_xml = os.linesep.join(
            self._composer._compose_disk(disk=spec)
        )

        def _operation() -> None:
            self._require_fields(name=domain_name, aspects=aspects)
            current = self._current_xml(name=domain_name, aspects=aspects)
            if _xml_attribute_present(current, "dev", spec.target_dev):
                return None
            manager.run(args=["attach-device", domain_name, "/dev/stdin"],
                        stdin=device_xml, aspects=aspects,
                        description="attach_disk")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="attach_disk")
        return

    def detach_disk(self, *, domain_name: str, target_dev: str,
                    aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                    ) -> None:
        """
            Detach a disk device from a domain, idempotently.

            When the named device is not attached the call is a no-op.

            :param domain_name: The domain name.
            :param target_dev: The guest device name to detach.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager
        spec = LibvirtDiskSpec(source_path="", target_dev=target_dev)
        device_xml = os.linesep.join(
            self._composer._compose_disk(disk=spec)
        )

        def _operation() -> None:
            self._require_fields(name=domain_name, aspects=aspects)
            current = self._current_xml(name=domain_name, aspects=aspects)
            if not _xml_attribute_present(current, "dev", target_dev):
                return None
            manager.run(args=["detach-device", domain_name, "/dev/stdin"],
                        stdin=device_xml, aspects=aspects,
                        description="detach_disk")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="detach_disk")
        return

    def attach_nic(self, *, domain_name: str, spec: LibvirtNicSpec,
                   aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                   ) -> None:
        """
            Attach a network interface to a domain, idempotently.

            When an interface with the same MAC is already attached the
            call is a no-op.

            :param domain_name: The domain name.
            :param spec: The :class:`LibvirtNicSpec`.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager
        device_xml = os.linesep.join(
            self._composer._compose_nic(nic=spec)
        )

        def _operation() -> None:
            self._require_fields(name=domain_name, aspects=aspects)
            current = self._current_xml(name=domain_name, aspects=aspects)
            if spec.mac_address is not None:
                if _xml_attribute_present(current, "address",
                                          spec.mac_address):
                    return None
            manager.run(args=["attach-device", domain_name, "/dev/stdin"],
                        stdin=device_xml, aspects=aspects,
                        description="attach_nic")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="attach_nic")
        return

    def detach_nic(self, *, domain_name: str, mac: str,
                   aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                   ) -> None:
        """
            Detach a network interface from a domain, idempotently.

            When no interface with the given MAC is attached the call is
            a no-op.

            :param domain_name: The domain name.
            :param mac: The MAC address of the interface to detach.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        manager = self._connection_manager
        spec = LibvirtNicSpec(network_name="default", mac_address=mac)
        device_xml = os.linesep.join(
            self._composer._compose_nic(nic=spec)
        )

        def _operation() -> None:
            self._require_fields(name=domain_name, aspects=aspects)
            current = self._current_xml(name=domain_name, aspects=aspects)
            if not _xml_attribute_present(current, "address", mac):
                return None
            manager.run(args=["detach-device", domain_name, "/dev/stdin"],
                        stdin=device_xml, aspects=aspects,
                        description="detach_nic")
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="detach_nic")
        return

    # ------------------------------------------------------------------
    # Waiter
    # ------------------------------------------------------------------

    def wait_for_domain_state(self, *, name: str, desired_state: str,
                              aspects: AspectsNative =
                              DEFAULT_LIBVIRT_ASPECTS) -> LibvirtDomainInfo:
        """
            Poll a domain until it reaches the desired state.

            Polls at ``aspects.completion_interval`` and raises
            :class:`TimeoutError` when ``aspects.completion_timeout``
            elapses.

            :param name: The domain name.
            :param desired_state: The target state token (running,
                shutoff...).
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The :class:`LibvirtDomainInfo` once the desired
                state is observed.

            :raises: :class:`TimeoutError`
        """
        deadline = time.monotonic() + aspects.completion_timeout
        last_info: Optional[LibvirtDomainInfo] = None

        while True:
            info = self.get_domain_info(name=name, aspects=aspects)
            last_info = info
            if info.state == desired_state:
                rtnval = info
                return rtnval
            if time.monotonic() >= deadline:
                break
            time.sleep(aspects.completion_interval)

        observed = last_info.state if last_info is not None else "unknown"
        err_msg_lines = ["Timed out waiting for a domain state."]
        err_msg_lines.append("DOMAIN: {}".format(name))
        err_msg_lines.append("DESIRED: {}".format(desired_state))
        err_msg_lines.append("OBSERVED: {}".format(observed))
        err_msg_lines.append("TIMEOUT-SECONDS: {}".format(
            aspects.completion_timeout
        ))
        err_msg = os.linesep.join(err_msg_lines)
        raise TimeoutError(err_msg)
