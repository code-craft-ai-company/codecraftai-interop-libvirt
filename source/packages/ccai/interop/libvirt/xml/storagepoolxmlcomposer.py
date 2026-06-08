"""
    .. module:: storagepoolxmlcomposer
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Safe, deterministic libvirt storage-pool and volume XML
               composer.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import os

from xml.etree import ElementTree
from typing import List

from ccai.interop.libvirt.exceptions.libvirtxmlcompositionerror import (
    LibvirtXmlCompositionError
)
from ccai.interop.libvirt.specs.libvirtstoragepoolspec import (
    LibvirtStoragePoolSpec
)
from ccai.interop.libvirt.specs.libvirtvolumespec import (
    LibvirtVolumeSpec
)
from ccai.interop.libvirt.xml.xmlescape import (
    escape_attribute, escape_text
)


def _validate(*, document: str, kind: str, name: str) -> None:
    """
        Validate that a composed document is well-formed.

        :param document: The composed XML string.
        :param kind: A human-readable kind label for errors.
        :param name: The resource name for errors.

        :raises: :class:`LibvirtXmlCompositionError`
    """
    try:
        ElementTree.fromstring(document)
    except ElementTree.ParseError as xcpt:
        err_msg_lines = ["Composed {} XML is not well-formed.".format(kind)]
        err_msg_lines.append("NAME: {}".format(name))
        err_msg_lines.append("PARSE-ERROR: {}".format(xcpt))
        err_msg = os.linesep.join(err_msg_lines)
        raise LibvirtXmlCompositionError(err_msg) from None
    return


class StoragePoolXmlComposer:
    """
        Compose libvirt storage-pool and volume XML documents.

        User-supplied values are escaped before insertion and composed
        documents are checked for well-formedness.
    """

    def compose_pool(self, *, spec: LibvirtStoragePoolSpec) -> str:
        """
            Compose the storage-pool XML document.

            :param spec: The :class:`LibvirtStoragePoolSpec`.

            :returns: A well-formed storage-pool XML string.

            :raises: :class:`LibvirtXmlCompositionError`
        """
        if spec.name is None or len(spec.name) == 0:
            raise LibvirtXmlCompositionError(
                "LibvirtStoragePoolSpec.name must not be empty."
            )

        name = escape_text(value=spec.name)
        pool_type = escape_attribute(value=spec.pool_type)
        target = escape_text(value=spec.target_path)

        lines: List[str] = []
        lines.append("<pool type='{}'>".format(pool_type))
        lines.append("  <name>{}</name>".format(name))
        if spec.source_host is not None and spec.source_path is not None:
            host = escape_attribute(value=spec.source_host)
            path = escape_attribute(value=spec.source_path)
            lines.append("  <source>")
            lines.append("    <host name='{}'/>".format(host))
            lines.append("    <dir path='{}'/>".format(path))
            lines.append("  </source>")
        lines.append("  <target>")
        lines.append("    <path>{}</path>".format(target))
        lines.append("  </target>")
        lines.append("</pool>")

        document = os.linesep.join(lines) + os.linesep
        _validate(document=document, kind="storage-pool", name=spec.name)
        rtnval = document
        return rtnval

    def compose_volume(self, *, spec: LibvirtVolumeSpec) -> str:
        """
            Compose the storage-volume XML document.

            :param spec: The :class:`LibvirtVolumeSpec`.

            :returns: A well-formed volume XML string.

            :raises: :class:`LibvirtXmlCompositionError`
        """
        if spec.name is None or len(spec.name) == 0:
            raise LibvirtXmlCompositionError(
                "LibvirtVolumeSpec.name must not be empty."
            )
        if spec.capacity_bytes <= 0:
            raise LibvirtXmlCompositionError(
                "LibvirtVolumeSpec.capacity_bytes must be positive."
            )

        name = escape_text(value=spec.name)
        fmt = escape_attribute(value=spec.volume_format)

        lines: List[str] = []
        lines.append("<volume>")
        lines.append("  <name>{}</name>".format(name))
        lines.append(
            "  <capacity unit='bytes'>{}</capacity>".format(
                spec.capacity_bytes
            )
        )
        lines.append("  <target>")
        lines.append("    <format type='{}'/>".format(fmt))
        lines.append("  </target>")
        if spec.backing_volume_path is not None:
            backing_path = escape_text(value=spec.backing_volume_path)
            backing_format = spec.backing_format
            if backing_format is None:
                backing_format = "qcow2"
            backing_format = escape_attribute(value=backing_format)
            lines.append("  <backingStore>")
            lines.append(
                "    <path>{}</path>".format(backing_path)
            )
            lines.append(
                "    <format type='{}'/>".format(backing_format)
            )
            lines.append("  </backingStore>")
        lines.append("</volume>")

        document = os.linesep.join(lines) + os.linesep
        _validate(document=document, kind="volume", name=spec.name)
        rtnval = document
        return rtnval
