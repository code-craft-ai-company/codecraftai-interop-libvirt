"""
    .. module:: libvirtvolume
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Immutable record describing a libvirt storage volume.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LibvirtVolume:
    """
        Record describing a libvirt storage volume.

        :param name: The volume name.
        :param pool_name: The owning storage-pool name.
        :param path: The volume path on the host.
        :param capacity_bytes: The declared volume capacity in bytes.
        :param allocation_bytes: The on-disk allocation in bytes.
        :param volume_format: The volume format (qcow2, raw...).
    """
    name: str
    pool_name: str
    path: str
    capacity_bytes: int
    allocation_bytes: int
    volume_format: str
