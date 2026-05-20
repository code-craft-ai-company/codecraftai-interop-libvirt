"""
    .. module:: libvirtnetwork
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Immutable record describing a libvirt virtual network.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LibvirtNetwork:
    """
        Record describing a libvirt virtual network.

        :param name: The network name.
        :param uuid: The network UUID string.
        :param active: Whether the network is currently active.
        :param forward_mode: The forward mode (nat, bridge, route, none).
        :param bridge: The bridge device name, when present.
    """
    name: str
    uuid: str
    active: bool
    forward_mode: str
    bridge: Optional[str] = None
