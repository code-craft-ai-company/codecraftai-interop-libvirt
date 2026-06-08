"""
    .. module:: test_apigroups
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Example-based tests for the libvirt client API groups —
               host, networks, storage pools, volumes, domains and
               snapshots — covering idempotent define / create.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import pytest

from ccai.interop.libvirt.specs.libvirtdiskspec import LibvirtDiskSpec
from ccai.interop.libvirt.specs.libvirtdomainspec import (
    LibvirtDomainSpec
)
from ccai.interop.libvirt.specs.libvirtnetworkspec import (
    LibvirtNetworkSpec
)
from ccai.interop.libvirt.specs.libvirtnicspec import LibvirtNicSpec
from ccai.interop.libvirt.specs.libvirtstoragepoolspec import (
    LibvirtStoragePoolSpec
)
from ccai.interop.libvirt.specs.libvirtvolumespec import (
    LibvirtVolumeSpec
)


def test_host_info(client, aspects):
    """
        host_info / node_info / capabilities_xml return populated records.
    """
    host = client.host.host_info(aspects=aspects)
    node = client.host.node_info(aspects=aspects)
    caps = client.host.capabilities_xml(aspects=aspects)

    assert host.hostname == "mock-hypervisor"
    assert host.hypervisor_type == "QEMU"
    assert node.cpus == 8
    assert node.memory_kib == 16384 * 1024
    assert "capabilities" in caps
    return


def test_define_network_is_idempotent(client, aspects):
    """
        Defining a network twice yields one network.
    """
    spec = LibvirtNetworkSpec(name="lab-net")
    first = client.networks.define_network(spec=spec, aspects=aspects)
    second = client.networks.define_network(spec=spec, aspects=aspects)

    networks = client.networks.list_networks(aspects=aspects)
    assert first.uuid == second.uuid
    assert len(networks) == 1
    return


def test_network_lifecycle(client, aspects):
    """
        start / stop / undefine drive the network through its states.
    """
    spec = LibvirtNetworkSpec(name="lab-net")
    client.networks.define_network(spec=spec, aspects=aspects)

    client.networks.start_network(name="lab-net", aspects=aspects)
    started = client.networks.list_networks(aspects=aspects)[0]
    assert started.active is True

    client.networks.stop_network(name="lab-net", aspects=aspects)
    stopped = client.networks.list_networks(aspects=aspects)[0]
    assert stopped.active is False

    client.networks.undefine_network(name="lab-net", aspects=aspects)
    assert len(client.networks.list_networks(aspects=aspects)) == 0
    return


def test_undefine_unknown_network_is_noop(client, aspects):
    """
        Undefining a network that does not exist is a no-op.
    """
    client.networks.undefine_network(name="ghost", aspects=aspects)
    return


def test_storage_pool_and_volume_lifecycle(client, aspects):
    """
        Define a pool, create volumes, list, resize and delete.
    """
    pool_spec = LibvirtStoragePoolSpec(name="images")
    client.storage_pools.define_storage_pool(spec=pool_spec,
                                             aspects=aspects)
    client.storage_pools.start_storage_pool(name="images",
                                            aspects=aspects)

    vol_spec = LibvirtVolumeSpec(name="disk0.qcow2",
                                 capacity_bytes=10737418240)
    client.volumes.create_volume(pool_name="images", spec=vol_spec,
                                 aspects=aspects)
    again = client.volumes.create_volume(pool_name="images",
                                         spec=vol_spec, aspects=aspects)
    assert again.name == "disk0.qcow2"

    volumes = client.volumes.list_volumes(pool_name="images",
                                          aspects=aspects)
    assert len(volumes) == 1

    client.volumes.resize_volume(pool_name="images", name="disk0.qcow2",
                                 capacity_bytes=21474836480,
                                 aspects=aspects)
    client.volumes.delete_volume(pool_name="images", name="disk0.qcow2",
                                 aspects=aspects)
    assert len(client.volumes.list_volumes(pool_name="images",
                                           aspects=aspects)) == 0
    return


def test_delete_unknown_volume_is_noop(client, aspects):
    """
        Deleting an absent volume is a no-op.
    """
    pool_spec = LibvirtStoragePoolSpec(name="images")
    client.storage_pools.define_storage_pool(spec=pool_spec,
                                             aspects=aspects)
    client.volumes.delete_volume(pool_name="images", name="ghost.qcow2",
                                 aspects=aspects)
    return


def _domain_spec(name: str) -> LibvirtDomainSpec:
    """
        Build a small domain spec for tests.
    """
    disk = LibvirtDiskSpec(source_path="/var/lib/libvirt/images/d.qcow2",
                           target_dev="vda")
    nic = LibvirtNicSpec(network_name="default")
    rtnval = LibvirtDomainSpec(name=name, disks=[disk], nics=[nic])
    return rtnval


def test_define_domain_is_idempotent(client, aspects):
    """
        Defining a domain twice yields one domain.
    """
    spec = _domain_spec("vm-alpha")
    first = client.domains.define_domain(spec=spec, aspects=aspects)
    second = client.domains.define_domain(spec=spec, aspects=aspects)

    assert first.uuid == second.uuid
    assert len(client.domains.list_domains(aspects=aspects)) == 1
    return


def test_domain_lifecycle(client, aspects):
    """
        create / shutdown / destroy / undefine drive a domain.
    """
    spec = _domain_spec("vm-alpha")
    client.domains.define_domain(spec=spec, aspects=aspects)

    client.domains.create_domain(name="vm-alpha", aspects=aspects)
    info = client.domains.get_domain_info(name="vm-alpha", aspects=aspects)
    assert info.state == "running"

    client.domains.suspend_domain(name="vm-alpha", aspects=aspects)
    assert client.domains.get_domain_info(
        name="vm-alpha", aspects=aspects).state == "paused"
    client.domains.resume_domain(name="vm-alpha", aspects=aspects)

    client.domains.destroy_domain(name="vm-alpha", aspects=aspects)
    client.domains.undefine_domain(name="vm-alpha", aspects=aspects)
    assert len(client.domains.list_domains(aspects=aspects)) == 0
    return


def test_undefine_unknown_domain_is_noop(client, aspects):
    """
        Undefining an absent domain is a no-op.
    """
    client.domains.undefine_domain(name="ghost", aspects=aspects)
    return


def test_attach_disk_idempotent(client, aspects):
    """
        Attaching the same disk twice attaches it once.
    """
    spec = _domain_spec("vm-alpha")
    client.domains.define_domain(spec=spec, aspects=aspects)

    disk = LibvirtDiskSpec(source_path="/data/extra.qcow2",
                           target_dev="vdb")
    client.domains.attach_disk(domain_name="vm-alpha", spec=disk,
                               aspects=aspects)
    client.domains.attach_disk(domain_name="vm-alpha", spec=disk,
                               aspects=aspects)

    xml = client.domains.get_domain_xml(name="vm-alpha", aspects=aspects)
    assert xml.count("dev='vdb'") == 1
    return


def test_detach_unattached_disk_is_noop(client, aspects):
    """
        Detaching a disk that is not present is a no-op.
    """
    spec = _domain_spec("vm-alpha")
    client.domains.define_domain(spec=spec, aspects=aspects)
    client.domains.detach_disk(domain_name="vm-alpha", target_dev="vdz",
                               aspects=aspects)
    return


def test_snapshot_lifecycle(client, aspects):
    """
        create / list / revert / delete snapshots.
    """
    spec = _domain_spec("vm-alpha")
    client.domains.define_domain(spec=spec, aspects=aspects)

    client.snapshots.create_snapshot(domain_name="vm-alpha",
                                     name="snap1", aspects=aspects)
    client.snapshots.create_snapshot(domain_name="vm-alpha",
                                     name="snap1", aspects=aspects)
    snapshots = client.snapshots.list_snapshots(domain_name="vm-alpha",
                                                aspects=aspects)
    assert len(snapshots) == 1

    client.snapshots.revert_snapshot(domain_name="vm-alpha",
                                     name="snap1", aspects=aspects)
    client.snapshots.delete_snapshot(domain_name="vm-alpha",
                                     name="snap1", aspects=aspects)
    assert len(client.snapshots.list_snapshots(domain_name="vm-alpha",
                                               aspects=aspects)) == 0
    return


def test_delete_unknown_snapshot_is_noop(client, aspects):
    """
        Deleting an absent snapshot is a no-op.
    """
    spec = _domain_spec("vm-alpha")
    client.domains.define_domain(spec=spec, aspects=aspects)
    client.snapshots.delete_snapshot(domain_name="vm-alpha",
                                     name="ghost", aspects=aspects)
    return


def test_wait_for_domain_state_reaches_target(client, aspects):
    """
        wait_for_domain_state returns once the target state is observed.
    """
    spec = _domain_spec("vm-alpha")
    client.domains.define_domain(spec=spec, aspects=aspects)
    native = client.domains._connection_manager.connection(
    )._domains["vm-alpha"]
    native.state_script = [5, 5, 1]

    info = client.domains.wait_for_domain_state(
        name="vm-alpha", desired_state="running", aspects=aspects
    )
    assert info.state == "running"
    return


def test_wait_for_domain_state_times_out(client, aspects):
    """
        wait_for_domain_state raises TimeoutError when the state never
        converges.
    """
    spec = _domain_spec("vm-alpha")
    client.domains.define_domain(spec=spec, aspects=aspects)

    with pytest.raises(TimeoutError):
        client.domains.wait_for_domain_state(
            name="vm-alpha", desired_state="running", aspects=aspects
        )
    return
