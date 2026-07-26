"""
    .. module:: mockvirshrunner
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: An in-memory :class:`ICommandRunner` that emulates the
               ``virsh`` command surface exercised by
               :class:`LibvirtClient`.

    The mock maintains domain / network / pool / volume / snapshot state
    in dictionaries and answers ``virsh`` invocations from it, so the
    interop tests run without a hypervisor, without ``virsh``, and
    without any native bindings.  Failure injection knobs let the
    connection and retry tests exercise the error paths.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import re
import uuid

from typing import Callable, Dict, List, Optional

from ccai.interfaces.icommandrunner import RunResult


_CONNECT_FAILURE_STDERR = "error: failed to connect to the hypervisor"


def _name_from_xml(xml_text: str) -> str:
    """
        Extract the ``<name>`` element text from a definition document.

        :param xml_text: The XML text.

        :returns: The name, or an empty string.
    """
    match = re.search(r"<name>([^<]*)</name>", xml_text)
    rtnval = match.group(1) if match is not None else ""
    return rtnval


def _stable_uuid(name: str) -> str:
    """
        Produce a deterministic UUID for a named object.

        :param name: The object name.

        :returns: A UUID string.
    """
    rtnval = str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
    return rtnval


class MockVirshRunner:
    """
        Stateful ``virsh`` emulator satisfying :class:`ICommandRunner`.
    """

    def __init__(self) -> None:
        self.domains: Dict[str, dict] = {}
        self.networks: Dict[str, dict] = {}
        self.pools: Dict[str, dict] = {}
        self.snapshots: Dict[str, Dict[str, dict]] = {}
        self.calls: List[List[str]] = []
        # Failure injection: when set, every invocation fails as a
        # connection failure.  fail_next_n fails only the next N calls.
        self.fail_connect: bool = False
        self.fail_next_n: int = 0
        return

    def run(self, args: List[str], *, elevated: bool = False,
            cwd: Optional[str] = None,
            env: Optional[Dict[str, str]] = None,
            stdin: Optional[str] = None,
            timeout: Optional[float] = None,
            on_output: Optional[Callable[[str], None]] = None,
            on_error: Optional[Callable[[str], None]] = None,
            capture_output: bool = True) -> RunResult:
        """
            Emulate a ``virsh`` invocation.

            :param args: The full argv (virsh --connect URI subcmd ...).
            :param stdin: Optional stdin text (XML documents).

            :returns: A :class:`RunResult`.
        """
        self.calls.append(list(args))

        if self.fail_connect is True or self.fail_next_n > 0:
            if self.fail_next_n > 0:
                self.fail_next_n = self.fail_next_n - 1
            rtnval = RunResult(exit_code=1, stdout="",
                               stderr=_CONNECT_FAILURE_STDERR)
            return rtnval

        # Strip "virsh --connect <uri>" — tolerate a bare argv too.
        work = list(args)
        if len(work) > 0 and work[0].endswith("virsh"):
            work = work[1:]
        if len(work) >= 2 and work[0] == "--connect":
            work = work[2:]

        if len(work) == 0:
            rtnval = self._fail("missing sub-command")
            return rtnval

        handler_name = "_cmd_" + work[0].replace("-", "_")
        handler = getattr(self, handler_name, None)
        if handler is None:
            rtnval = self._fail("unsupported command: {}".format(work[0]))
            return rtnval

        rtnval = handler(work[1:], stdin)
        return rtnval

    def _ok(self, stdout: str = "") -> RunResult:
        rtnval = RunResult(exit_code=0, stdout=stdout, stderr="")
        return rtnval

    def _fail(self, message: str) -> RunResult:
        rtnval = RunResult(exit_code=1, stdout="",
                           stderr="error: {}".format(message))
        return rtnval

    # -------------------------------------------------- host commands

    def _cmd_hostname(self, args: List[str],
                      stdin: Optional[str]) -> RunResult:
        rtnval = self._ok("mock-hypervisor\n")
        return rtnval

    def _cmd_version(self, args: List[str],
                     stdin: Optional[str]) -> RunResult:
        lines = [
            "Compiled against library: libvirt 8.0.0",
            "Using library: libvirt 8.0.0",
            "Using API: QEMU 8.0.0",
            "Running hypervisor: QEMU 6.2.0",
            "",
        ]
        rtnval = self._ok("\n".join(lines))
        return rtnval

    def _cmd_capabilities(self, args: List[str],
                          stdin: Optional[str]) -> RunResult:
        rtnval = self._ok("<capabilities><host><cpu/></host>"
                          "</capabilities>\n")
        return rtnval

    def _cmd_nodeinfo(self, args: List[str],
                      stdin: Optional[str]) -> RunResult:
        lines = [
            "CPU model:           x86_64",
            "CPU(s):              8",
            "CPU frequency:       2400 MHz",
            "CPU socket(s):       1",
            "Core(s) per socket:  8",
            "Thread(s) per core:  1",
            "NUMA cell(s):        1",
            "Memory size:         16777216 KiB",
            "",
        ]
        rtnval = self._ok("\n".join(lines))
        return rtnval

    # ------------------------------------------------ domain commands

    def _cmd_list(self, args: List[str],
                  stdin: Optional[str]) -> RunResult:
        names = sorted(self.domains.keys())
        rtnval = self._ok("\n".join(names) + ("\n" if names else ""))
        return rtnval

    def _cmd_dominfo(self, args: List[str],
                     stdin: Optional[str]) -> RunResult:
        name = args[0] if len(args) > 0 else ""
        record = self.domains.get(name)
        if record is None:
            rtnval = self._fail("failed to get domain '{}'".format(name))
            return rtnval
        script = record.get("state_script")
        if script is not None and len(script) > 0:
            record["state"] = script.pop(0)
        state_text = {"running": "running", "shutoff": "shut off",
                      "paused": "paused"}.get(record["state"],
                                              record["state"])
        lines = [
            "Id:             1",
            "Name:           {}".format(name),
            "UUID:           {}".format(record["uuid"]),
            "OS Type:        hvm",
            "State:          {}".format(state_text),
            "CPU(s):         {}".format(record.get("vcpus", 2)),
            "CPU time:       12.3s",
            "Max memory:     {} KiB".format(record.get("memory_kib",
                                                       2097152)),
            "Used memory:    1048576 KiB",
            "Persistent:     yes",
            "Autostart:      disable",
            "",
        ]
        rtnval = self._ok("\n".join(lines))
        return rtnval

    def _cmd_dumpxml(self, args: List[str],
                     stdin: Optional[str]) -> RunResult:
        name = args[0] if len(args) > 0 else ""
        record = self.domains.get(name)
        if record is None:
            rtnval = self._fail("failed to get domain '{}'".format(name))
            return rtnval
        base = record["xml"]
        devices = "".join(record.get("attached", []))
        if "</domain>" in base:
            document = base.replace("</domain>",
                                    devices + "</domain>")
        else:
            document = base + devices
        rtnval = self._ok(document)
        return rtnval

    def _cmd_define(self, args: List[str],
                    stdin: Optional[str]) -> RunResult:
        xml_text = stdin if stdin is not None else ""
        name = _name_from_xml(xml_text)
        if len(name) == 0:
            rtnval = self._fail("invalid domain XML")
            return rtnval
        self.domains[name] = {
            "uuid": _stable_uuid(name),
            "state": "shutoff",
            "xml": xml_text,
            "attached": [],
        }
        self.snapshots.setdefault(name, {})
        rtnval = self._ok("Domain '{}' defined\n".format(name))
        return rtnval

    def _set_domain_state(self, name: str, state: str) -> RunResult:
        record = self.domains.get(name)
        if record is None:
            rtnval = self._fail("failed to get domain '{}'".format(name))
            return rtnval
        record["state"] = state
        rtnval = self._ok()
        return rtnval

    def _cmd_start(self, args: List[str],
                   stdin: Optional[str]) -> RunResult:
        rtnval = self._set_domain_state(args[0], "running")
        return rtnval

    def _cmd_shutdown(self, args: List[str],
                      stdin: Optional[str]) -> RunResult:
        rtnval = self._set_domain_state(args[0], "shutoff")
        return rtnval

    def _cmd_destroy(self, args: List[str],
                     stdin: Optional[str]) -> RunResult:
        rtnval = self._set_domain_state(args[0], "shutoff")
        return rtnval

    def _cmd_reboot(self, args: List[str],
                    stdin: Optional[str]) -> RunResult:
        rtnval = self._set_domain_state(args[0], "running")
        return rtnval

    def _cmd_suspend(self, args: List[str],
                     stdin: Optional[str]) -> RunResult:
        rtnval = self._set_domain_state(args[0], "paused")
        return rtnval

    def _cmd_resume(self, args: List[str],
                    stdin: Optional[str]) -> RunResult:
        rtnval = self._set_domain_state(args[0], "running")
        return rtnval

    def _cmd_undefine(self, args: List[str],
                      stdin: Optional[str]) -> RunResult:
        name = args[0] if len(args) > 0 else ""
        if name not in self.domains:
            rtnval = self._fail("failed to get domain '{}'".format(name))
            return rtnval
        del self.domains[name]
        self.snapshots.pop(name, None)
        rtnval = self._ok()
        return rtnval

    def _cmd_attach_device(self, args: List[str],
                           stdin: Optional[str]) -> RunResult:
        name = args[0] if len(args) > 0 else ""
        record = self.domains.get(name)
        if record is None:
            rtnval = self._fail("failed to get domain '{}'".format(name))
            return rtnval
        record.setdefault("attached", []).append(
            stdin if stdin is not None else "")
        rtnval = self._ok()
        return rtnval

    def _cmd_detach_device(self, args: List[str],
                           stdin: Optional[str]) -> RunResult:
        name = args[0] if len(args) > 0 else ""
        record = self.domains.get(name)
        if record is None:
            rtnval = self._fail("failed to get domain '{}'".format(name))
            return rtnval
        incoming = stdin if stdin is not None else ""
        markers = re.findall(r"(?:dev|address)=['\"]([^'\"]+)['\"]",
                             incoming)
        attached = record.get("attached", [])
        for index, existing in enumerate(attached):
            for marker in markers:
                if marker in existing:
                    del attached[index]
                    rtnval = self._ok()
                    return rtnval
        rtnval = self._fail("device not found")
        return rtnval

    # ----------------------------------------------- network commands

    def _cmd_net_list(self, args: List[str],
                      stdin: Optional[str]) -> RunResult:
        names = sorted(self.networks.keys())
        rtnval = self._ok("\n".join(names) + ("\n" if names else ""))
        return rtnval

    def _cmd_net_info(self, args: List[str],
                      stdin: Optional[str]) -> RunResult:
        name = args[0] if len(args) > 0 else ""
        record = self.networks.get(name)
        if record is None:
            rtnval = self._fail("failed to get network '{}'".format(name))
            return rtnval
        lines = [
            "Name:           {}".format(name),
            "UUID:           {}".format(record["uuid"]),
            "Active:         {}".format("yes" if record["active"]
                                        else "no"),
            "Persistent:     yes",
            "Autostart:      no",
            "Bridge:         virbr-{}".format(name),
            "",
        ]
        rtnval = self._ok("\n".join(lines))
        return rtnval

    def _cmd_net_define(self, args: List[str],
                        stdin: Optional[str]) -> RunResult:
        xml_text = stdin if stdin is not None else ""
        name = _name_from_xml(xml_text)
        if len(name) == 0:
            rtnval = self._fail("invalid network XML")
            return rtnval
        self.networks[name] = {"uuid": _stable_uuid(name),
                               "active": False, "xml": xml_text}
        rtnval = self._ok()
        return rtnval

    def _cmd_net_start(self, args: List[str],
                       stdin: Optional[str]) -> RunResult:
        record = self.networks.get(args[0] if args else "")
        if record is None:
            rtnval = self._fail("network not found")
            return rtnval
        record["active"] = True
        rtnval = self._ok()
        return rtnval

    def _cmd_net_destroy(self, args: List[str],
                         stdin: Optional[str]) -> RunResult:
        record = self.networks.get(args[0] if args else "")
        if record is None:
            rtnval = self._fail("network not found")
            return rtnval
        record["active"] = False
        rtnval = self._ok()
        return rtnval

    def _cmd_net_undefine(self, args: List[str],
                          stdin: Optional[str]) -> RunResult:
        name = args[0] if len(args) > 0 else ""
        if name not in self.networks:
            rtnval = self._fail("network not found")
            return rtnval
        del self.networks[name]
        rtnval = self._ok()
        return rtnval

    # -------------------------------------------------- pool commands

    def _cmd_pool_list(self, args: List[str],
                       stdin: Optional[str]) -> RunResult:
        names = sorted(self.pools.keys())
        rtnval = self._ok("\n".join(names) + ("\n" if names else ""))
        return rtnval

    def _cmd_pool_info(self, args: List[str],
                       stdin: Optional[str]) -> RunResult:
        positional = [a for a in args if not a.startswith("--")]
        name = positional[0] if len(positional) > 0 else ""
        record = self.pools.get(name)
        if record is None:
            rtnval = self._fail("failed to get pool '{}'".format(name))
            return rtnval
        lines = [
            "Name:           {}".format(name),
            "UUID:           {}".format(record["uuid"]),
            "State:          {}".format("running" if record["active"]
                                        else "inactive"),
            "Persistent:     yes",
            "Autostart:      no",
            "Capacity:       42949672960",
            "Allocation:     10737418240",
            "Available:      32212254720",
            "",
        ]
        rtnval = self._ok("\n".join(lines))
        return rtnval

    def _cmd_pool_define(self, args: List[str],
                         stdin: Optional[str]) -> RunResult:
        xml_text = stdin if stdin is not None else ""
        name = _name_from_xml(xml_text)
        if len(name) == 0:
            rtnval = self._fail("invalid pool XML")
            return rtnval
        self.pools[name] = {"uuid": _stable_uuid(name), "active": False,
                            "xml": xml_text, "volumes": {}}
        rtnval = self._ok()
        return rtnval

    def _cmd_pool_start(self, args: List[str],
                        stdin: Optional[str]) -> RunResult:
        record = self.pools.get(args[0] if args else "")
        if record is None:
            rtnval = self._fail("pool not found")
            return rtnval
        record["active"] = True
        rtnval = self._ok()
        return rtnval

    def _cmd_pool_destroy(self, args: List[str],
                          stdin: Optional[str]) -> RunResult:
        record = self.pools.get(args[0] if args else "")
        if record is None:
            rtnval = self._fail("pool not found")
            return rtnval
        record["active"] = False
        rtnval = self._ok()
        return rtnval

    def _cmd_pool_undefine(self, args: List[str],
                           stdin: Optional[str]) -> RunResult:
        name = args[0] if len(args) > 0 else ""
        if name not in self.pools:
            rtnval = self._fail("pool not found")
            return rtnval
        del self.pools[name]
        rtnval = self._ok()
        return rtnval

    # ------------------------------------------------ volume commands

    def _pool_for_args(self, args: List[str]) -> Optional[dict]:
        if "--pool" in args:
            pool_name = args[args.index("--pool") + 1]
        elif len(args) > 0:
            pool_name = args[0]
        else:
            pool_name = ""
        rtnval = self.pools.get(pool_name)
        return rtnval

    def _cmd_vol_list(self, args: List[str],
                      stdin: Optional[str]) -> RunResult:
        pool = self._pool_for_args(args)
        if pool is None:
            rtnval = self._fail("pool not found")
            return rtnval
        lines = [" Name   Path",
                 "--------------------------------------------"]
        for name, record in sorted(pool["volumes"].items()):
            lines.append(" {}   {}".format(name, record["path"]))
        lines.append("")
        rtnval = self._ok("\n".join(lines))
        return rtnval

    def _cmd_vol_info(self, args: List[str],
                      stdin: Optional[str]) -> RunResult:
        pool = self._pool_for_args(args)
        if pool is None:
            rtnval = self._fail("pool not found")
            return rtnval
        positional = [a for a in args if not a.startswith("--")]
        # positional may carry [pool?] name — the volume name is last
        name = positional[-1] if len(positional) > 0 else ""
        record = pool["volumes"].get(name)
        if record is None:
            rtnval = self._fail("failed to get vol '{}'".format(name))
            return rtnval
        lines = [
            "Name:           {}".format(name),
            "Type:           file",
            "Capacity:       {}".format(record["capacity"]),
            "Allocation:     {}".format(record["allocation"]),
            "",
        ]
        rtnval = self._ok("\n".join(lines))
        return rtnval

    def _cmd_vol_path(self, args: List[str],
                      stdin: Optional[str]) -> RunResult:
        pool = self._pool_for_args(args)
        if pool is None:
            rtnval = self._fail("pool not found")
            return rtnval
        positional = [a for a in args if not a.startswith("--")]
        name = positional[-1] if len(positional) > 0 else ""
        record = pool["volumes"].get(name)
        if record is None:
            rtnval = self._fail("failed to get vol '{}'".format(name))
            return rtnval
        rtnval = self._ok(record["path"] + "\n")
        return rtnval

    def _cmd_vol_create(self, args: List[str],
                        stdin: Optional[str]) -> RunResult:
        pool = self._pool_for_args(args)
        if pool is None:
            rtnval = self._fail("pool not found")
            return rtnval
        xml_text = stdin if stdin is not None else ""
        name = _name_from_xml(xml_text)
        if len(name) == 0:
            rtnval = self._fail("invalid volume XML")
            return rtnval
        capacity_match = re.search(
            r"<capacity[^>]*>(\d+)</capacity>", xml_text)
        capacity = int(capacity_match.group(1)) if capacity_match else 0
        pool["volumes"][name] = {
            "path": "/var/lib/libvirt/images/{}".format(name),
            "capacity": capacity,
            "allocation": 0,
        }
        rtnval = self._ok()
        return rtnval

    def _cmd_vol_delete(self, args: List[str],
                        stdin: Optional[str]) -> RunResult:
        pool = self._pool_for_args(args)
        if pool is None:
            rtnval = self._fail("pool not found")
            return rtnval
        positional = [a for a in args if not a.startswith("--")]
        name = positional[-1] if len(positional) > 0 else ""
        if name not in pool["volumes"]:
            rtnval = self._fail("vol not found")
            return rtnval
        del pool["volumes"][name]
        rtnval = self._ok()
        return rtnval

    def _cmd_vol_resize(self, args: List[str],
                        stdin: Optional[str]) -> RunResult:
        pool = self._pool_for_args(args)
        if pool is None:
            rtnval = self._fail("pool not found")
            return rtnval
        positional = [a for a in args if not a.startswith("--")]
        if len(positional) < 2:
            rtnval = self._fail("vol-resize needs a volume and capacity")
            return rtnval
        name = positional[-2]
        capacity = int(positional[-1])
        record = pool["volumes"].get(name)
        if record is None:
            rtnval = self._fail("vol not found")
            return rtnval
        record["capacity"] = capacity
        rtnval = self._ok()
        return rtnval

    # ---------------------------------------------- snapshot commands

    def _cmd_snapshot_create(self, args: List[str],
                             stdin: Optional[str]) -> RunResult:
        domain = args[0] if len(args) > 0 else ""
        if domain not in self.domains:
            rtnval = self._fail("domain not found")
            return rtnval
        xml_text = stdin if stdin is not None else ""
        name = _name_from_xml(xml_text)
        if len(name) == 0:
            rtnval = self._fail("invalid snapshot XML")
            return rtnval
        table = self.snapshots.setdefault(domain, {})
        table[name] = {"xml": xml_text}
        self.domains[domain]["current_snapshot"] = name
        rtnval = self._ok()
        return rtnval

    def _snapshot_name_from_args(self, args: List[str]) -> str:
        if "--snapshotname" in args:
            rtnval = args[args.index("--snapshotname") + 1]
            return rtnval
        positional = [a for a in args if not a.startswith("--")]
        rtnval = positional[-1] if len(positional) > 1 else ""
        return rtnval

    def _cmd_snapshot_info(self, args: List[str],
                           stdin: Optional[str]) -> RunResult:
        domain = args[0] if len(args) > 0 else ""
        name = self._snapshot_name_from_args(args)
        table = self.snapshots.get(domain, {})
        if name not in table:
            rtnval = self._fail("snapshot not found")
            return rtnval
        rtnval = self._ok("Name:           {}\nDomain:         {}\n".format(
            name, domain))
        return rtnval

    def _cmd_snapshot_list(self, args: List[str],
                           stdin: Optional[str]) -> RunResult:
        domain = args[0] if len(args) > 0 else ""
        if domain not in self.domains:
            rtnval = self._fail("domain not found")
            return rtnval
        names = sorted(self.snapshots.get(domain, {}).keys())
        rtnval = self._ok("\n".join(names) + ("\n" if names else ""))
        return rtnval

    def _cmd_snapshot_current(self, args: List[str],
                              stdin: Optional[str]) -> RunResult:
        domain = args[0] if len(args) > 0 else ""
        record = self.domains.get(domain)
        if record is None or "current_snapshot" not in record:
            rtnval = self._fail("no current snapshot")
            return rtnval
        rtnval = self._ok(record["current_snapshot"] + "\n")
        return rtnval

    def _cmd_snapshot_revert(self, args: List[str],
                             stdin: Optional[str]) -> RunResult:
        domain = args[0] if len(args) > 0 else ""
        name = self._snapshot_name_from_args(args)
        table = self.snapshots.get(domain, {})
        if name not in table:
            rtnval = self._fail("snapshot not found")
            return rtnval
        self.domains[domain]["current_snapshot"] = name
        rtnval = self._ok()
        return rtnval

    def _cmd_snapshot_delete(self, args: List[str],
                             stdin: Optional[str]) -> RunResult:
        domain = args[0] if len(args) > 0 else ""
        name = self._snapshot_name_from_args(args)
        table = self.snapshots.get(domain, {})
        if name not in table:
            rtnval = self._fail("snapshot not found")
            return rtnval
        del table[name]
        if self.domains[domain].get("current_snapshot") == name:
            self.domains[domain].pop("current_snapshot", None)
        rtnval = self._ok()
        return rtnval
