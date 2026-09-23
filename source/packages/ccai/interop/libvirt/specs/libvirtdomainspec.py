"""
    .. module:: libvirtdomainspec
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec describing a libvirt domain (virtual machine) to define.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import List, Optional

from ccai.interop.libvirt.specs.libvirtdiskspec import LibvirtDiskSpec
from ccai.interop.libvirt.specs.libvirtnicspec import LibvirtNicSpec


@dataclass
class LibvirtDomainSpec:
    """
        Spec describing a libvirt domain (virtual machine) to define.

        :param name: The domain name.
        :param memory_kib: Memory allocation in kibibytes.
        :param vcpus: Number of virtual CPUs.
        :param disks: List of :class:`LibvirtDiskSpec` boot/data disks.
        :param nics: List of :class:`LibvirtNicSpec` interfaces.
        :param cdrom_path: Optional path to a CD-ROM ISO (cloud-init
            seed datasource).
        :param os_type: The guest OS type element value.
        :param arch: The guest architecture.
        :param machine: The guest machine type.
        :param metadata_xml: Optional pre-rendered ``<metadata>`` inner
            XML to embed verbatim (already trusted / escaped).
    """
    name: str
    memory_kib: int = 1048576
    vcpus: int = 1
    disks: List[LibvirtDiskSpec] = field(default_factory=list)
    nics: List[LibvirtNicSpec] = field(default_factory=list)
    cdrom_path: Optional[str] = None
    os_type: str = "hvm"
    arch: str = "x86_64"
    machine: str = "pc"
    metadata_xml: Optional[str] = None
