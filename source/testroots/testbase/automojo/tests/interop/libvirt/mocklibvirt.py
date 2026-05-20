"""
    .. module:: mocklibvirt
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: An in-memory mock of the native ``libvirt`` Python module.

    The :class:`MockLibvirtModule` mirrors the subset of the official
    ``libvirt-python`` surface exercised by :class:`LibvirtClient`.  It
    lets the interop tests pass even on hosts where ``libvirt-python`` is
    not installed.  Tests inject an instance through ``sys.modules``.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from typing import Any, Dict, List, Optional


class libvirtError(Exception):
    """
        Mirror of the native ``libvirt.libvirtError`` exception type.
    """


class MockNetwork:
    """
        In-memory mock of a libvirt virtual network handle.
    """

    def __init__(self, *, name: str, uuid: str) -> None:
        self._name = name
        self._uuid = uuid
        self._active = False
        self.undefined = False

    def name(self) -> str:
        return self._name

    def UUIDString(self) -> str:
        return self._uuid

    def isActive(self) -> int:
        return 1 if self._active else 0

    def bridgeName(self) -> str:
        return "virbr-{}".format(self._name)

    def create(self) -> None:
        self._active = True

    def destroy(self) -> None:
        self._active = False

    def undefine(self) -> None:
        self.undefined = True


class MockStorageVolume:
    """
        In-memory mock of a libvirt storage-volume handle.
    """

    def __init__(self, *, name: str, capacity: int) -> None:
        self._name = name
        self._capacity = capacity
        self.deleted = False

    def name(self) -> str:
        return self._name

    def path(self) -> str:
        return "/var/lib/libvirt/images/{}".format(self._name)

    def info(self) -> List[int]:
        return [0, self._capacity, self._capacity]

    def delete(self, flags: int) -> None:
        self.deleted = True

    def resize(self, capacity: int, flags: int) -> None:
        self._capacity = capacity


class MockStoragePool:
    """
        In-memory mock of a libvirt storage-pool handle.
    """

    def __init__(self, *, name: str, uuid: str) -> None:
        self._name = name
        self._uuid = uuid
        self._active = False
        self.undefined = False
        self._volumes: Dict[str, MockStorageVolume] = {}

    def name(self) -> str:
        return self._name

    def UUIDString(self) -> str:
        return self._uuid

    def isActive(self) -> int:
        return 1 if self._active else 0

    def info(self) -> List[int]:
        return [0, 1000000, 0, 1000000]

    def create(self) -> None:
        self._active = True

    def destroy(self) -> None:
        self._active = False

    def undefine(self) -> None:
        self.undefined = True

    def listAllVolumes(self) -> List[MockStorageVolume]:
        return [v for v in self._volumes.values() if not v.deleted]

    def storageVolLookupByName(self, name: str) -> MockStorageVolume:
        vol = self._volumes.get(name, None)
        if vol is None or vol.deleted is True:
            raise libvirtError("no volume {}".format(name))
        return vol

    def createXML(self, xml: str, flags: int) -> MockStorageVolume:
        name = _extract_tag(xml=xml, tag="name")
        capacity = int(_extract_tag(xml=xml, tag="capacity") or "0")
        vol = MockStorageVolume(name=name, capacity=capacity)
        self._volumes[name] = vol
        return vol


class MockSnapshot:
    """
        In-memory mock of a libvirt domain-snapshot handle.
    """

    def __init__(self, *, name: str) -> None:
        self._name = name
        self.deleted = False

    def getName(self) -> str:
        return self._name

    def isCurrent(self, flags: int) -> int:
        return 1

    def delete(self, flags: int) -> None:
        self.deleted = True


class MockDomain:
    """
        In-memory mock of a libvirt domain handle.
    """

    def __init__(self, *, name: str, uuid: str, xml: str) -> None:
        self._name = name
        self._uuid = uuid
        self._xml = xml
        self._active = False
        self.undefined = False
        self._state = 5
        self._snapshots: Dict[str, MockSnapshot] = {}
        self.state_script: List[int] = []

    def name(self) -> str:
        return self._name

    def UUIDString(self) -> str:
        return self._uuid

    def isActive(self) -> int:
        return 1 if self._active else 0

    def XMLDesc(self, flags: int) -> str:
        return self._xml

    def info(self) -> List[int]:
        if len(self.state_script) > 0:
            state = self.state_script.pop(0)
        else:
            state = self._state
        return [state, 1048576, 1048576, 1, 0]

    def create(self) -> None:
        self._active = True
        self._state = 1

    def destroy(self) -> None:
        self._active = False
        self._state = 5

    def shutdown(self) -> None:
        self._state = 5

    def reboot(self, flags: int) -> None:
        self._state = 1

    def suspend(self) -> None:
        self._state = 3

    def resume(self) -> None:
        self._state = 1

    def undefine(self) -> None:
        self.undefined = True

    def attachDevice(self, xml: str) -> None:
        self._xml = self._xml.replace("</devices>",
                                      "  " + xml + "\n  </devices>")

    def detachDevice(self, xml: str) -> None:
        return None

    def snapshotLookupByName(self, name: str, flags: int) -> MockSnapshot:
        snap = self._snapshots.get(name, None)
        if snap is None or snap.deleted is True:
            raise libvirtError("no snapshot {}".format(name))
        return snap

    def snapshotCreateXML(self, xml: str, flags: int) -> MockSnapshot:
        name = _extract_tag(xml=xml, tag="name")
        snap = MockSnapshot(name=name)
        self._snapshots[name] = snap
        return snap

    def listAllSnapshots(self, flags: int) -> List[MockSnapshot]:
        return [s for s in self._snapshots.values() if not s.deleted]

    def revertToSnapshot(self, snapshot: MockSnapshot, flags: int) -> None:
        return None


def _extract_tag(*, xml: str, tag: str) -> Optional[str]:
    """
        Extract the inner text of the first ``<tag>`` from a document.

        :param xml: The XML document.
        :param tag: The tag name to search for.

        :returns: The inner text or ``None``.
    """
    open_token = "<{}".format(tag)
    start = xml.find(open_token)
    if start < 0:
        return None
    gt = xml.find(">", start)
    close = xml.find("</{}>".format(tag), gt)
    if gt < 0 or close < 0:
        return None
    rtnval = xml[gt + 1:close].strip()
    return rtnval


class MockConnection:
    """
        In-memory mock of a libvirt connection handle.
    """

    def __init__(self, *, uri: str) -> None:
        self._uri = uri
        self._alive = True
        self._networks: Dict[str, MockNetwork] = {}
        self._pools: Dict[str, MockStoragePool] = {}
        self._domains: Dict[str, MockDomain] = {}
        self._uuid_counter = 0

    def _next_uuid(self) -> str:
        self._uuid_counter = self._uuid_counter + 1
        return "0000-{:04d}".format(self._uuid_counter)

    def isAlive(self) -> int:
        return 1 if self._alive else 0

    def close(self) -> None:
        self._alive = False

    # --- host ---
    def getHostname(self) -> str:
        return "mock-hypervisor"

    def getType(self) -> str:
        return "QEMU"

    def getVersion(self) -> int:
        return 9000000

    def getCapabilities(self) -> str:
        return "<capabilities><host><cpu><arch>x86_64</arch></cpu>" \
               "</host></capabilities>"

    def getInfo(self) -> List[Any]:
        return ["x86_64", 16384, 8, 2400, 1, 4, 2, 1]

    # --- networks ---
    def listAllNetworks(self) -> List[MockNetwork]:
        return [n for n in self._networks.values() if not n.undefined]

    def networkLookupByName(self, name: str) -> MockNetwork:
        net = self._networks.get(name, None)
        if net is None or net.undefined is True:
            raise libvirtError("no network {}".format(name))
        return net

    def networkDefineXML(self, xml: str) -> MockNetwork:
        name = _extract_tag(xml=xml, tag="name")
        net = MockNetwork(name=name, uuid=self._next_uuid())
        self._networks[name] = net
        return net

    # --- storage pools ---
    def listAllStoragePools(self) -> List[MockStoragePool]:
        return [p for p in self._pools.values() if not p.undefined]

    def storagePoolLookupByName(self, name: str) -> MockStoragePool:
        pool = self._pools.get(name, None)
        if pool is None or pool.undefined is True:
            raise libvirtError("no pool {}".format(name))
        return pool

    def storagePoolDefineXML(self, xml: str, flags: int) -> MockStoragePool:
        name = _extract_tag(xml=xml, tag="name")
        pool = MockStoragePool(name=name, uuid=self._next_uuid())
        self._pools[name] = pool
        return pool

    # --- domains ---
    def listAllDomains(self) -> List[MockDomain]:
        return [d for d in self._domains.values() if not d.undefined]

    def lookupByName(self, name: str) -> MockDomain:
        dom = self._domains.get(name, None)
        if dom is None or dom.undefined is True:
            raise libvirtError("no domain {}".format(name))
        return dom

    def defineXML(self, xml: str) -> MockDomain:
        name = _extract_tag(xml=xml, tag="name")
        dom = MockDomain(name=name, uuid=self._next_uuid(), xml=xml)
        self._domains[name] = dom
        return dom


class MockLibvirtModule:
    """
        In-memory stand-in for the native ``libvirt`` module.
    """

    def __init__(self) -> None:
        self.libvirtError = libvirtError
        self.connections: List[MockConnection] = []
        self.fail_open = False

    def openAuth(self, uri: str, auth: Any, flags: int) -> MockConnection:
        if self.fail_open is True:
            raise libvirtError("cannot connect to {}".format(uri))
        connection = MockConnection(uri=uri)
        self.connections.append(connection)
        return connection
