"""
    .. module:: libvirtdiskspec
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec describing a disk device to attach to a domain.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LibvirtDiskSpec:
    """
        Spec describing a disk device to attach to a domain.

        :param source_path: The host-side disk image path.
        :param target_dev: The guest device name (vda, vdb...).
        :param disk_format: The image format (qcow2, raw...).
        :param bus: The device bus (virtio, sata, scsi...).
        :param readonly: Whether the disk is read-only.
    """
    source_path: str
    target_dev: str
    disk_format: str = "qcow2"
    bus: str = "virtio"
    readonly: bool = False
