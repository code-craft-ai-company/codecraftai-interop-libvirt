"""
    .. module:: libvirtvolumespec
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec describing a libvirt storage volume to create.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LibvirtVolumeSpec:
    """
        Spec describing a libvirt storage volume to create.

        :param name: The volume name.
        :param capacity_bytes: The declared capacity in bytes.
        :param volume_format: The volume format (qcow2, raw...).
        :param backing_volume_path: Optional backing-file path for a
            copy-on-write backing chain.
        :param backing_format: Optional backing-file format.
    """
    name: str
    capacity_bytes: int
    volume_format: str = "qcow2"
    backing_volume_path: Optional[str] = None
    backing_format: Optional[str] = None
