"""
    .. module:: networkxmlcomposer
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Safe, deterministic libvirt network XML composer.

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
from automojo.interop.libvirt.specs.libvirtnetworkspec import (
    LibvirtNetworkSpec
)
from automojo.interop.libvirt.xml.xmlescape import (
    escape_attribute, escape_text
)


class NetworkXmlComposer:
    """
        Compose a libvirt virtual-network XML document from a
        :class:`LibvirtNetworkSpec`.

        User-supplied values are escaped before insertion and the
        composed document is checked for well-formedness.
    """

    def compose(self, *, spec: LibvirtNetworkSpec) -> str:
        """
            Compose the network XML document for the given spec.

            :param spec: The :class:`LibvirtNetworkSpec`.

            :returns: A well-formed network XML string.

            :raises: :class:`LibvirtXmlCompositionError`
        """
        if spec.name is None or len(spec.name) == 0:
            raise LibvirtXmlCompositionError(
                "LibvirtNetworkSpec.name must not be empty."
            )

        name = escape_text(value=spec.name)

        lines: List[str] = []
        lines.append("<network>")
        lines.append("  <name>{}</name>".format(name))

        if spec.forward_mode is not None and spec.forward_mode != "none":
            mode = escape_attribute(value=spec.forward_mode)
            lines.append("  <forward mode='{}'/>".format(mode))

        if spec.bridge_name is not None:
            bridge = escape_attribute(value=spec.bridge_name)
            lines.append("  <bridge name='{}'/>".format(bridge))

        if spec.ip_address is not None and spec.netmask is not None:
            ip_address = escape_attribute(value=spec.ip_address)
            netmask = escape_attribute(value=spec.netmask)
            lines.append(
                "  <ip address='{}' netmask='{}'>".format(
                    ip_address, netmask
                )
            )
            if spec.dhcp_start is not None and spec.dhcp_end is not None:
                start = escape_attribute(value=spec.dhcp_start)
                end = escape_attribute(value=spec.dhcp_end)
                lines.append("    <dhcp>")
                lines.append(
                    "      <range start='{}' end='{}'/>".format(start, end)
                )
                lines.append("    </dhcp>")
            lines.append("  </ip>")

        lines.append("</network>")

        document = os.linesep.join(lines) + os.linesep

        try:
            ElementTree.fromstring(document)
        except ElementTree.ParseError as xcpt:
            err_msg_lines = ["Composed network XML is not well-formed."]
            err_msg_lines.append("NETWORK: {}".format(spec.name))
            err_msg_lines.append("PARSE-ERROR: {}".format(xcpt))
            err_msg = os.linesep.join(err_msg_lines)
            raise LibvirtXmlCompositionError(err_msg) from None

        rtnval = document
        return rtnval
