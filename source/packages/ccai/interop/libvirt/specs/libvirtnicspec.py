"""
    .. module:: libvirtnicspec
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec describing a network interface to attach to a domain.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LibvirtNicSpec:
    """
        Spec describing a network interface to attach to a domain.

        :param network_name: The libvirt network to connect to.
        :param mac_address: Optional explicit MAC address.
        :param model: The NIC model (virtio, e1000...).
    """
    network_name: str
    mac_address: Optional[str] = None
    model: str = "virtio"
