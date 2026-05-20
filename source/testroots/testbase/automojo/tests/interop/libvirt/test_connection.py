"""
    .. module:: test_connection
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Connection open / close and error-reclassification tests.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


import pytest

from automojo.interop.libvirt.aspectslibvirt import AspectsNative
from automojo.interop.libvirt.connection.libvirtconnectioncredential import (
    LibvirtConnectionCredential
)
from automojo.interop.libvirt.connection.libvirtconnectionmanager import (
    LibvirtConnectionManager
)
from automojo.interop.libvirt.exceptions.libvirtconnectionerror import (
    LibvirtConnectionError
)
from automojo.interop.libvirt.libvirtclient import LibvirtClient


def test_lazy_open_caches_connection(mock_libvirt, credential):
    """
        The connection is opened lazily and then cached.
    """
    manager = LibvirtConnectionManager(credential=credential)
    first = manager.connection()
    second = manager.connection()

    assert first is second
    assert len(mock_libvirt.connections) == 1
    return


def test_open_failure_reclassified(mock_libvirt, credential):
    """
        A failed open raises LibvirtConnectionError naming the URI.
    """
    mock_libvirt.fail_open = True
    manager = LibvirtConnectionManager(credential=credential)

    with pytest.raises(LibvirtConnectionError) as caught:
        manager.connection()

    assert "qemu:///system" in str(caught.value)
    return


def test_close_rejects_further_operations(mock_libvirt, credential):
    """
        After close the manager rejects further connection requests.
    """
    manager = LibvirtConnectionManager(credential=credential)
    manager.connection()
    manager.close()

    with pytest.raises(LibvirtConnectionError):
        manager.connection()
    return


def test_dropped_connection_detected(mock_libvirt, credential):
    """
        A server-dropped connection is detected on the next call.
    """
    manager = LibvirtConnectionManager(credential=credential)
    connection = manager.connection()
    connection._alive = False

    with pytest.raises(LibvirtConnectionError) as caught:
        manager.connection()

    assert "dropped" in str(caught.value)
    return


def test_dropped_connection_reopened_when_aspects_allow(mock_libvirt,
                                                        credential):
    """
        reconnect_on_drop=True reopens a dropped connection.
    """
    manager = LibvirtConnectionManager(credential=credential)
    connection = manager.connection()
    connection._alive = False

    aspects = AspectsNative(reconnect_on_drop=True)
    reopened = manager.connection(aspects=aspects)

    assert reopened is not connection
    assert len(mock_libvirt.connections) == 2
    return


def test_missing_bindings_raise_connection_error(credential):
    """
        When the native bindings are absent the manager raises
        LibvirtConnectionError instead of a bare ImportError.
    """
    import sys

    saved = sys.modules.pop("libvirt", None)
    try:
        manager = LibvirtConnectionManager(credential=credential)
        with pytest.raises(LibvirtConnectionError) as caught:
            manager.connection()
        assert "libvirt-python" in str(caught.value)
    finally:
        if saved is not None:
            sys.modules["libvirt"] = saved
    return


def test_client_close_is_idempotent(client):
    """
        Closing a client twice does not raise.
    """
    client.close()
    client.close()
    return
