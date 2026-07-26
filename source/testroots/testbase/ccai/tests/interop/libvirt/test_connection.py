"""
    .. module:: test_connection
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Tests for the virsh transport gateway — argv shape, error
               classification, and lifecycle semantics.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import pytest

from ccai.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)
from ccai.interop.libvirt.exceptions.libvirtconnectionerror import (
    LibvirtConnectionError
)
from ccai.interop.libvirt.exceptions.libvirtoperationerror import (
    LibvirtOperationError
)


def test_commands_carry_the_connection_uri(mock_virsh, credential):
    """
        Every dispatched command addresses the credential's URI via
        ``--connect``.
    """
    manager = LibvirtConnectionManager(credential=credential,
                                       runner=mock_virsh)
    manager.run(args=["hostname"], description="probe")

    assert len(mock_virsh.calls) == 1
    argv = mock_virsh.calls[0]
    assert argv[0] == "virsh"
    assert argv[1] == "--connect"
    assert argv[2] == "qemu:///system"
    assert argv[3] == "hostname"
    return


def test_connection_failure_reclassified(mock_virsh, credential):
    """
        A connection-class failure raises LibvirtConnectionError naming
        the URI.
    """
    mock_virsh.fail_connect = True
    manager = LibvirtConnectionManager(credential=credential,
                                       runner=mock_virsh)

    with pytest.raises(LibvirtConnectionError) as caught:
        manager.run(args=["hostname"], description="probe")
    assert "qemu:///system" in str(caught.value)
    return


def test_operation_failure_raises_operation_error(mock_virsh, credential):
    """
        A hypervisor-rejected operation raises LibvirtOperationError,
        not a connection error.
    """
    manager = LibvirtConnectionManager(credential=credential,
                                       runner=mock_virsh)

    with pytest.raises(LibvirtOperationError):
        manager.run(args=["dominfo", "absent-domain"],
                    description="probe")
    return


def test_probe_tolerates_operation_failure(mock_virsh, credential):
    """
        probe() returns None for an operation failure so absence checks
        do not raise.
    """
    manager = LibvirtConnectionManager(credential=credential,
                                       runner=mock_virsh)

    result = manager.probe(args=["dominfo", "absent-domain"])
    assert result is None
    return


def test_probe_still_raises_on_connection_failure(mock_virsh, credential):
    """
        probe() must never mistake a dead hypervisor for an absent
        object.
    """
    mock_virsh.fail_connect = True
    manager = LibvirtConnectionManager(credential=credential,
                                       runner=mock_virsh)

    with pytest.raises(LibvirtConnectionError):
        manager.probe(args=["dominfo", "absent-domain"])
    return


def test_close_rejects_further_operations(mock_virsh, credential):
    """
        After close the manager rejects further operations.
    """
    manager = LibvirtConnectionManager(credential=credential,
                                       runner=mock_virsh)
    manager.run(args=["hostname"], description="probe")
    manager.close()

    with pytest.raises(LibvirtConnectionError):
        manager.run(args=["hostname"], description="probe")
    return


def test_client_close_is_idempotent(client):
    """
        Closing the client twice is not an error.
    """
    client.close()
    client.close()
    return
