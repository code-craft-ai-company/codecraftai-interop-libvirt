"""
    .. module:: factories
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Shared fixtures for the libvirt interop client tests.

    Each test gets a fresh :class:`MockVirshRunner` injected as the
    client's command runner, so ``virsh`` is fully emulated in memory.
    No real hypervisor, ``virsh`` binary, or native binding is ever
    touched.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from collections.abc import Generator

from ccai import testbase

from ccai.interop.libvirt.aspectslibvirt import AspectsNative
from ccai.interop.libvirt.connection.libvirtconnectioncredential import (
    LibvirtConnectionCredential
)
from ccai.interop.libvirt.libvirtclient import LibvirtClient

from ccai.tests.interop.libvirt.mockvirshrunner import MockVirshRunner

@testbase.register.resource_factory()
def create_libvirt_mock_virsh(constraints=None) -> Generator[MockVirshRunner, None, None]:
    """
        Return a fresh in-memory ``virsh`` emulator.

        :returns: The :class:`MockVirshRunner` instance.
    """
    rtnval = MockVirshRunner()
    yield rtnval


@testbase.register.resource_factory()
def create_libvirt_credential(constraints=None) -> Generator[LibvirtConnectionCredential, None, None]:
    """
        Return a deterministic libvirt connection credential.

        :returns: A :class:`LibvirtConnectionCredential`.
    """
    rtnval = LibvirtConnectionCredential(uri="qemu:///system")
    yield rtnval


@testbase.register.resource_factory()
def create_libvirt_client(mock_virsh: MockVirshRunner,
           credential: LibvirtConnectionCredential, constraints=None) -> Generator[LibvirtClient, None, None]:
    """
        Return a :class:`LibvirtClient` bound to the mock runner.

        :param mock_virsh: The injected mock runner.
        :param credential: The connection credential.

        :returns: A :class:`LibvirtClient`.
    """
    rtnval = LibvirtClient(credential=credential, runner=mock_virsh)
    yield rtnval


@testbase.register.resource_factory()
def create_libvirt_aspects(constraints=None) -> Generator[AspectsNative, None, None]:
    """
        Return a fast :class:`AspectsNative` carrier for tests.

        :returns: An :class:`AspectsNative` with short intervals.
    """
    rtnval = AspectsNative(completion_interval=0.01,
                           completion_timeout=0.2,
                           retry_interval=0.01,
                           max_attempts=2)
    yield rtnval
