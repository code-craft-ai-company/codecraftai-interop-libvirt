"""
    .. module:: domainxmlcomposer
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Safe, deterministic libvirt domain XML composer.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


import os

from xml.etree import ElementTree
from typing import List

from automojo.interop.libvirt.exceptions.libvirtxmlcompositionerror import (
    LibvirtXmlCompositionError
)
from automojo.interop.libvirt.specs.libvirtdiskspec import LibvirtDiskSpec
from automojo.interop.libvirt.specs.libvirtdomainspec import LibvirtDomainSpec
from automojo.interop.libvirt.specs.libvirtnicspec import LibvirtNicSpec
from automojo.interop.libvirt.xml.xmlescape import (
    escape_attribute, escape_text
)


class DomainXmlComposer:
    """
        Compose a libvirt domain XML document from a
        :class:`LibvirtDomainSpec`.

        All user-supplied string values are escaped before insertion so
        the document cannot be subverted by XML injection.  Output is
        deterministic — the same spec produces a byte-identical string —
        and the composed document is checked for well-formedness before
        being returned.
    """

    def _compose_disk(self, *, disk: LibvirtDiskSpec) -> List[str]:
        """
            Compose the XML lines for a single disk device.

            :param disk: The :class:`LibvirtDiskSpec`.

            :returns: A list of XML text lines.
        """
        device = "cdrom" if disk.readonly is True else "disk"
        source = escape_attribute(value=disk.source_path)
        target = escape_attribute(value=disk.target_dev)
        fmt = escape_attribute(value=disk.disk_format)
        bus = escape_attribute(value=disk.bus)

        lines: List[str] = []
        lines.append(
            "    <disk type='file' device='{}'>".format(device)
        )
        lines.append(
            "      <driver name='qemu' type='{}'/>".format(fmt)
        )
        lines.append(
            "      <source file='{}'/>".format(source)
        )
        lines.append(
            "      <target dev='{}' bus='{}'/>".format(target, bus)
        )
        if disk.readonly is True:
            lines.append("      <readonly/>")
        lines.append("    </disk>")
        rtnval = lines
        return rtnval

    def _compose_nic(self, *, nic: LibvirtNicSpec) -> List[str]:
        """
            Compose the XML lines for a single network interface.

            :param nic: The :class:`LibvirtNicSpec`.

            :returns: A list of XML text lines.
        """
        network = escape_attribute(value=nic.network_name)
        model = escape_attribute(value=nic.model)

        lines: List[str] = []
        lines.append("    <interface type='network'>")
        lines.append(
            "      <source network='{}'/>".format(network)
        )
        if nic.mac_address is not None:
            mac = escape_attribute(value=nic.mac_address)
            lines.append("      <mac address='{}'/>".format(mac))
        lines.append("      <model type='{}'/>".format(model))
        lines.append("    </interface>")
        rtnval = lines
        return rtnval

    def compose(self, *, spec: LibvirtDomainSpec) -> str:
        """
            Compose the domain XML document for the given spec.

            :param spec: The :class:`LibvirtDomainSpec`.

            :returns: A well-formed domain XML string.

            :raises: :class:`LibvirtXmlCompositionError` when the spec
                carries values that cannot be rendered or when the
                composed document is not well-formed.
        """
        if spec.name is None or len(spec.name) == 0:
            raise LibvirtXmlCompositionError(
                "LibvirtDomainSpec.name must not be empty."
            )
        if spec.memory_kib <= 0:
            raise LibvirtXmlCompositionError(
                "LibvirtDomainSpec.memory_kib must be positive."
            )
        if spec.vcpus <= 0:
            raise LibvirtXmlCompositionError(
                "LibvirtDomainSpec.vcpus must be positive."
            )

        name = escape_text(value=spec.name)
        os_type = escape_text(value=spec.os_type)
        arch = escape_attribute(value=spec.arch)
        machine = escape_attribute(value=spec.machine)

        lines: List[str] = []
        lines.append("<domain type='kvm'>")
        lines.append("  <name>{}</name>".format(name))
        lines.append(
            "  <memory unit='KiB'>{}</memory>".format(spec.memory_kib)
        )
        lines.append("  <vcpu>{}</vcpu>".format(spec.vcpus))
        lines.append("  <os>")
        lines.append(
            "    <type arch='{}' machine='{}'>{}</type>".format(
                arch, machine, os_type
            )
        )
        lines.append("    <boot dev='hd'/>")
        if spec.cdrom_path is not None:
            lines.append("    <boot dev='cdrom'/>")
        lines.append("  </os>")

        if spec.metadata_xml is not None and len(spec.metadata_xml) > 0:
            lines.append("  <metadata>")
            lines.append("    {}".format(spec.metadata_xml))
            lines.append("  </metadata>")

        lines.append("  <devices>")
        for disk in spec.disks:
            lines.extend(self._compose_disk(disk=disk))
        if spec.cdrom_path is not None:
            cdrom_path = escape_attribute(value=spec.cdrom_path)
            lines.append(
                "    <disk type='file' device='cdrom'>"
            )
            lines.append(
                "      <driver name='qemu' type='raw'/>"
            )
            lines.append(
                "      <source file='{}'/>".format(cdrom_path)
            )
            lines.append(
                "      <target dev='hdc' bus='ide'/>"
            )
            lines.append("      <readonly/>")
            lines.append("    </disk>")
        for nic in spec.nics:
            lines.extend(self._compose_nic(nic=nic))
        lines.append("  </devices>")
        lines.append("</domain>")

        document = os.linesep.join(lines) + os.linesep

        try:
            ElementTree.fromstring(document)
        except ElementTree.ParseError as xcpt:
            err_msg_lines = ["Composed domain XML is not well-formed."]
            err_msg_lines.append("DOMAIN: {}".format(spec.name))
            err_msg_lines.append("PARSE-ERROR: {}".format(xcpt))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtXmlCompositionError(err_msg) from None

        rtnval = document
        return rtnval
