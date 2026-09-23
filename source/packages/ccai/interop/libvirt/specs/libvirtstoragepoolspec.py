"""
    .. module:: libvirtstoragepoolspec
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec describing a libvirt storage pool to define.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from dataclasses import dataclass
from typing import Optional


@dataclass
class LibvirtStoragePoolSpec:
    """
        Spec describing a libvirt storage pool to define.

        :param name: The pool name.
        :param pool_type: The pool type (dir, nfs, logical...).
        :param target_path: The on-host target directory path.
        :param source_host: Optional source host (nfs pools).
        :param source_path: Optional source export path (nfs pools).
    """
    name: str
    pool_type: str = "dir"
    target_path: str = "/var/lib/libvirt/images"
    source_host: Optional[str] = None
    source_path: Optional[str] = None
