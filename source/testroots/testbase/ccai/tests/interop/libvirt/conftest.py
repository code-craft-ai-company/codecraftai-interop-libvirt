"""
    .. module:: conftest
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Shared fixtures for the libvirt interop client tests.

    Each test gets a fresh :class:`MockLibvirtModule` injected into
    ``sys.modules`` so the lazily-imported native ``libvirt`` module is
    fully replaced.  No real hypervisor is ever contacted.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import sys

import pytest

from ccai.interop.libvirt.aspectslibvirt import AspectsNative
from ccai.interop.libvirt.connection.libvirtconnectioncredential import (
    LibvirtConnectionCredential
)
from ccai.interop.libvirt.libvirtclient import LibvirtClient

from ccai.tests.interop.libvirt.mocklibvirt import MockLibvirtModule


@pytest.fixture
def mock_libvirt() -> MockLibvirtModule:
    """
        Inject a fresh mock ``libvirt`` module into ``sys.modules``.

        :returns: The :class:`MockLibvirtModule` instance.
    """
    module = MockLibvirtModule()
    saved = sys.modules.get("libvirt", None)
    sys.modules["libvirt"] = module
    yield module
    if saved is not None:
        sys.modules["libvirt"] = saved
    else:
        del sys.modules["libvirt"]
    return


@pytest.fixture
def credential() -> LibvirtConnectionCredential:
    """
        Return a deterministic libvirt connection credential.

        :returns: A :class:`LibvirtConnectionCredential`.
    """
    rtnval = LibvirtConnectionCredential(uri="qemu:///system")
    return rtnval


@pytest.fixture
def client(mock_libvirt: MockLibvirtModule,
           credential: LibvirtConnectionCredential) -> LibvirtClient:
    """
        Return a :class:`LibvirtClient` bound to the mock module.

        :param mock_libvirt: The injected mock module.
        :param credential: The connection credential.

        :returns: A :class:`LibvirtClient`.
    """
    rtnval = LibvirtClient(credential=credential)
    return rtnval


@pytest.fixture
def aspects() -> AspectsNative:
    """
        Return a fast :class:`AspectsNative` carrier for tests.

        :returns: An :class:`AspectsNative` with short intervals.
    """
    rtnval = AspectsNative(completion_interval=0.01,
                           completion_timeout=0.2,
                           retry_interval=0.01,
                           max_attempts=2)
    return rtnval
