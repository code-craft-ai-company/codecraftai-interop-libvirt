"""
    .. module:: libvirtnodeinfo
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Immutable record of libvirt node hardware information.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LibvirtNodeInfo:
    """
        Record of libvirt node hardware information.

        :param model: The CPU model string.
        :param memory_kib: Total host memory in kibibytes.
        :param cpus: The number of active CPUs.
        :param cores: Cores per socket.
        :param sockets: Number of CPU sockets.
        :param numa_nodes: Number of NUMA cells.
    """
    model: str
    memory_kib: int
    cpus: int
    cores: int
    sockets: int
    numa_nodes: int
