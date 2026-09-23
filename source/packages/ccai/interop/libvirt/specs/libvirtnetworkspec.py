"""
    .. module:: libvirtnetworkspec
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec describing a libvirt virtual network to define.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from dataclasses import dataclass
from typing import Optional


@dataclass
class LibvirtNetworkSpec:
    """
        Spec describing a libvirt virtual network to define.

        :param name: The network name.
        :param forward_mode: nat, bridge, route, or none.
        :param bridge_name: Optional bridge device name.
        :param ip_address: Optional gateway IP for the network.
        :param netmask: Optional netmask for the gateway IP.
        :param dhcp_start: Optional DHCP range start address.
        :param dhcp_end: Optional DHCP range end address.
    """
    name: str
    forward_mode: str = "nat"
    bridge_name: Optional[str] = None
    ip_address: Optional[str] = None
    netmask: Optional[str] = None
    dhcp_start: Optional[str] = None
    dhcp_end: Optional[str] = None
