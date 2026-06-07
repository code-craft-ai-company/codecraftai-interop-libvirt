"""
    .. module:: libvirtsnapshot
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Immutable record describing a libvirt domain snapshot.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LibvirtSnapshot:
    """
        Record describing a libvirt domain snapshot.

        :param name: The snapshot name.
        :param domain_name: The owning domain name.
        :param is_current: Whether this is the current snapshot.
    """
    name: str
    domain_name: str
    is_current: bool = False
