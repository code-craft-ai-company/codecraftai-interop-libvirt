"""
    .. module:: libvirthostinfo
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Immutable record of libvirt host information.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LibvirtHostInfo:
    """
        Record of libvirt host information.

        :param hostname: The hypervisor host name.
        :param hypervisor_type: The hypervisor type (qemu, xen, lxc...).
        :param version: The libvirt library version as an integer.
        :param capabilities_summary: A short capabilities summary string.
    """
    hostname: str
    hypervisor_type: str
    version: int
    capabilities_summary: str
