"""
    .. module:: libvirtstoragepool
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Immutable record describing a libvirt storage pool.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from dataclasses import dataclass


@dataclass
class LibvirtStoragePool:
    """
        Record describing a libvirt storage pool.

        :param name: The pool name.
        :param uuid: The pool UUID string.
        :param pool_type: The pool type (dir, nfs, logical...).
        :param active: Whether the pool is currently active.
        :param capacity_bytes: Total pool capacity in bytes.
        :param available_bytes: Available pool space in bytes.
    """
    name: str
    uuid: str
    pool_type: str
    active: bool
    capacity_bytes: int
    available_bytes: int
