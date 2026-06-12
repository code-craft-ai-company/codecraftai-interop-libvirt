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

from typing import Any, List, Optional

from ccai.interop.libvirt.aspectslibvirt import (
    AspectsNative, DEFAULT_LIBVIRT_ASPECTS
)
from ccai.interop.libvirt.apigroups.retrysupport import run_with_retry
from ccai.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
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


# Maps the integer libvirt domain state to a stable token.  Declared
# locally so the module imports without the native bindings.
_STATE_TOKENS = {
    0: "nostate",
    1: "running",
    2: "blocked",
    3: "paused",
    4: "shutdown",
    5: "shutoff",
    6: "crashed",
    7: "pmsuspended",
}


def _xml_attribute_present(haystack: str, attribute: str, value: str) -> bool:
    """
        Tests whether an XML document contains ``attribute="value"`` for either
        quote style.

        libvirt's ``XMLDesc`` is serialized by libxml2 with double-quoted
        attributes (``dev="vda"``), while the composer emits single quotes
        (``dev='vda'``). Idempotency checks must match both so they work against
        real libvirt output, not only the single-quoted mock.

        :param haystack: The XML text to search.
        :param attribute: The attribute name (e.g. ``dev`` or ``address``).
        :param value: The attribute value to look for.

        :returns: ``True`` when the attribute/value pair is present.
    """
    single_quoted = "{}='{}'".format(attribute, value)
    double_quoted = '{}="{}"'.format(attribute, value)
    rtnval = single_quoted in haystack or double_quoted in haystack
    return rtnval


def _domain_info(*, native_domain: Any) -> LibvirtDomainInfo:
    """
        Build a :class:`LibvirtDomainInfo` from a native domain handle.

        :param native_domain: The native libvirt domain object.

        :returns: A :class:`LibvirtDomainInfo` record.
    """
    raw = native_domain.info()
    state_code, max_mem, _mem, vcpus, cpu_time = (raw[0], raw[1], raw[2],
                                                  raw[3], raw[4])
    state = _STATE_TOKENS.get(int(state_code), "unknown")
    rtnval = LibvirtDomainInfo(name=native_domain.name(),
                               uuid=native_domain.UUIDString(),
                               state=state,
                               vcpus=int(vcpus),
                               memory_kib=int(max_mem),
                               cpu_time_ns=int(cpu_time))
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

    def _find_native(self, *, connection: Any,
                     name: str) -> Optional[Any]:
        """
            Look up a native domain by name, tolerating absence.

            :param connection: The native libvirt connection.
            :param name: The domain name.

            :returns: The native domain handle or ``None``.
        """
        try:
            rtnval = connection.lookupByName(name)
        except Exception:
            rtnval = None
        return rtnval

    def _require_native(self, *, connection: Any, name: str) -> Any:
        """
            Look up a native domain, raising when it is absent.

            :param connection: The native libvirt connection.
            :param name: The domain name.

            :returns: The native domain handle.

            :raises: :class:`LibvirtOperationError`
        """
        from ccai.interop.libvirt.exceptions.libvirtoperationerror import (
            LibvirtOperationError
        )
        native = self._find_native(connection=connection, name=name)
        if native is None:
            err_msg_lines = ["The named domain was not found."]
            err_msg_lines.append("DOMAIN: {}".format(name))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtOperationError(err_msg)
        rtnval = native
        return rtnval

    def list_domains(self, *,
                     aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                     ) -> List[LibvirtDomainInfo]:
        """
            List all defined domains.

            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A list of :class:`LibvirtDomainInfo` records.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> List[LibvirtDomainInfo]:
            records: List[LibvirtDomainInfo] = []
            for native in connection.listAllDomains():
                records.append(_domain_info(native_domain=native))
            return records

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="list_domains")
        return rtnval

    def get_domain_info(self, *, name: str,
                        aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                        ) -> LibvirtDomainInfo:
        """
            Return the runtime info record for a domain.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtDomainInfo` record.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> LibvirtDomainInfo:
            native = self._require_native(connection=connection, name=name)
            result = _domain_info(native_domain=native)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="get_domain_info")
        return rtnval

    def get_domain_xml(self, *, name: str,
                       aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                       ) -> str:
        """
            Return the persistent XML description for a domain.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: The domain XML string.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> str:
            native = self._require_native(connection=connection, name=name)
            result = native.XMLDesc(0)
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
            record is returned without redefinition.

            :param spec: The :class:`LibvirtDomainSpec`.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: A :class:`LibvirtDomainInfo` record.
        """
        connection = self._connection_manager.connection(aspects=aspects)
        xml_document = self._composer.compose(spec=spec)

        def _operation() -> LibvirtDomainInfo:
            existing = self._find_native(connection=connection,
                                         name=spec.name)
            if existing is not None:
                result = _domain_info(native_domain=existing)
                return result
            native = connection.defineXML(xml_document)
            result = _domain_info(native_domain=native)
            return result

        rtnval = run_with_retry(operation=_operation, aspects=aspects,
                                description="define_domain")
        return rtnval

    def _simple_action(self, *, name: str, action_name: str,
                       aspects: AspectsNative) -> None:
        """
            Run a simple no-argument lifecycle action on a domain.

            :param name: The domain name.
            :param action_name: The native method to invoke.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            native = self._require_native(connection=connection, name=name)
            method = getattr(native, action_name)
            method()
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description=action_name)
        return

    def create_domain(self, *, name: str,
                       aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                       ) -> None:
        """
            Start a defined domain.  Already-running is a no-op.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            native = self._require_native(connection=connection, name=name)
            if bool(native.isActive()) is False:
                native.create()
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="create_domain")
        return

    def shutdown_domain(self, *, name: str,
                        aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                        ) -> None:
        """
            Gracefully shut down a domain.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        self._simple_action(name=name, action_name="shutdown",
                            aspects=aspects)
        return

    def destroy_domain(self, *, name: str,
                       aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                       ) -> None:
        """
            Forcefully power off a domain.  Already-off is a no-op.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            native = self._require_native(connection=connection, name=name)
            if bool(native.isActive()) is True:
                native.destroy()
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="destroy_domain")
        return

    def reboot_domain(self, *, name: str,
                      aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                      ) -> None:
        """
            Reboot a domain.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        connection = self._connection_manager.connection(aspects=aspects)

        def _operation() -> None:
            native = self._require_native(connection=connection, name=name)
            native.reboot(0)
            return None

        run_with_retry(operation=_operation, aspects=aspects,
                       description="reboot_domain")
        return

    def suspend_domain(self, *, name: str,
                       aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                       ) -> None:
        """
            Suspend a running domain.

            :param name: The domain name.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        self._simple_action(name=name, action_name="suspend",
                            aspects=aspects)
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
        self._simple_action(name=name, action_name="resume",
                            aspects=aspects)
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
                       description="undefine_domain")
        return

    # ------------------------------------------------------------------
    # Disk / NIC attach-detach
    # ------------------------------------------------------------------

    def attach_disk(self, *, domain_name: str, spec: LibvirtDiskSpec,
                    aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS
                    ) -> None:
        """
            Attach a disk device to a domain, idempotently.

            When a disk with the same target device is already attached
            the call is a no-op.

            :param domain_name: The domain name.
            :param spec: The :class:`LibvirtDiskSpec`.
            :param aspects: The :class:`AspectsNative` carrier.

            :returns: ``None``.
        """
        connection = self._connection_manager.connection(aspects=aspects)
        device_xml = os.linesep.join(
            self._composer._compose_disk(disk=spec)
        )

        def _operation() -> None:
            native = self._require_native(connection=connection,
                                          name=domain_name)
            current = native.XMLDesc(0)
            if _xml_attribute_present(current, "dev", spec.target_dev):
                return None
            native.attachDevice(device_xml)
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
        connection = self._connection_manager.connection(aspects=aspects)
        spec = LibvirtDiskSpec(source_path="", target_dev=target_dev)
        device_xml = os.linesep.join(
            self._composer._compose_disk(disk=spec)
        )

        def _operation() -> None:
            native = self._require_native(connection=connection,
                                          name=domain_name)
            current = native.XMLDesc(0)
            if not _xml_attribute_present(current, "dev", target_dev):
                return None
            native.detachDevice(device_xml)
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
        connection = self._connection_manager.connection(aspects=aspects)
        device_xml = os.linesep.join(
            self._composer._compose_nic(nic=spec)
        )

        def _operation() -> None:
            native = self._require_native(connection=connection,
                                          name=domain_name)
            current = native.XMLDesc(0)
            if spec.mac_address is not None:
                if _xml_attribute_present(current, "address", spec.mac_address):
                    return None
            native.attachDevice(device_xml)
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
        connection = self._connection_manager.connection(aspects=aspects)
        spec = LibvirtNicSpec(network_name="default", mac_address=mac)
        device_xml = os.linesep.join(
            self._composer._compose_nic(nic=spec)
        )

        def _operation() -> None:
            native = self._require_native(connection=connection,
                                          name=domain_name)
            current = native.XMLDesc(0)
            if not _xml_attribute_present(current, "address", mac):
                return None
            native.detachDevice(device_xml)
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
