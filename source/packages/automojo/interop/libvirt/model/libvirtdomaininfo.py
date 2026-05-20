"""
    .. module:: libvirtdomaininfo
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Immutable record describing a libvirt domain's runtime state.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LibvirtDomainInfo:
    """
        Record describing a libvirt domain's runtime state.

        :param name: The domain name.
        :param uuid: The domain UUID string.
        :param state: The domain state token (running, shutoff...).
        :param vcpus: The number of virtual CPUs.
        :param memory_kib: The memory allocation in kibibytes.
        :param cpu_time_ns: Accumulated CPU time in nanoseconds.
    """
    name: str
    uuid: str
    state: str
    vcpus: int
    memory_kib: int
    cpu_time_ns: int
