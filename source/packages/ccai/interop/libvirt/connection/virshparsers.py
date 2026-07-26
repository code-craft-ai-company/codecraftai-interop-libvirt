"""
    .. module:: virshparsers
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Parsers for the stable ``virsh`` output formats consumed by
               the API groups.

    ``virsh`` emits three shapes this package consumes: ``Key: value``
    blocks (``dominfo`` / ``net-info`` / ``pool-info`` / ``nodeinfo``),
    name-per-line lists (``list --all --name``), and XML documents
    (``dumpxml`` and friends).  Everything here is a pure function over
    text.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import re

from typing import Dict, List, Optional


# Maps the state strings printed by virsh (``domstate`` and the ``State:``
# field of ``dominfo``) to the stable state tokens this package reports.
_STATE_FROM_VIRSH = {
    "no state": "nostate",
    "running": "running",
    "idle": "blocked",
    "blocked": "blocked",
    "paused": "paused",
    "in shutdown": "shutdown",
    "shut off": "shutoff",
    "crashed": "crashed",
    "pmsuspended": "pmsuspended",
    "suspended": "pmsuspended",
}


def parse_key_value_block(text: str) -> Dict[str, str]:
    """
        Parse a ``Key: value`` block such as ``dominfo`` output.

        :param text: The block text.

        :returns: A dict of stripped key to stripped value.
    """
    rtnval: Dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if len(key) == 0:
            continue
        rtnval[key] = value.strip()
    return rtnval


def parse_name_lines(text: str) -> List[str]:
    """
        Parse name-per-line output such as ``virsh list --all --name``.

        :param text: The command output.

        :returns: The non-empty names, in order.
    """
    rtnval: List[str] = []
    for line in text.splitlines():
        name = line.strip()
        if len(name) > 0:
            rtnval.append(name)
    return rtnval


def parse_state_token(virsh_state: str) -> str:
    """
        Map a virsh state string onto the package's stable state token.

        :param virsh_state: The state text printed by virsh.

        :returns: The stable token, or ``"unknown"``.
    """
    rtnval = _STATE_FROM_VIRSH.get(virsh_state.strip().lower(), "unknown")
    return rtnval


def parse_yes_no(value: str) -> bool:
    """
        Parse a virsh ``yes`` / ``no`` field value.

        :param value: The field text.

        :returns: ``True`` for yes.
    """
    rtnval = value.strip().lower() == "yes"
    return rtnval


def parse_memory_kib(value: str) -> int:
    """
        Parse a memory field such as ``4194304 KiB``.

        :param value: The field text.

        :returns: The value in KiB, or 0 when unparseable.
    """
    match = re.match(r"\s*(\d+)", value)
    if match is None:
        rtnval = 0
        return rtnval
    rtnval = int(match.group(1))
    return rtnval


def parse_cpu_time_ns(value: str) -> int:
    """
        Parse a ``CPU time`` field such as ``1234.5s`` into nanoseconds.

        :param value: The field text.

        :returns: The value in nanoseconds, or 0 when unparseable.
    """
    match = re.match(r"\s*([\d.]+)\s*s", value)
    if match is None:
        rtnval = 0
        return rtnval
    rtnval = int(float(match.group(1)) * 1_000_000_000)
    return rtnval


def parse_version_number(version_text: str) -> int:
    """
        Parse an ``X.Y.Z`` version into libvirt's packed integer form
        (``X * 1_000_000 + Y * 1_000 + Z``), matching the value the native
        bindings reported so consumers see an unchanged field.

        :param version_text: Text containing a dotted version.

        :returns: The packed version integer, or 0 when unparseable.
    """
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version_text)
    if match is None:
        rtnval = 0
        return rtnval
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3)) if match.group(3) is not None else 0
    rtnval = (major * 1_000_000) + (minor * 1_000) + patch
    return rtnval


def parse_version_field(version_output: str, *, label: str) -> str:
    """
        Extract a labelled line from ``virsh version`` output.

        :param version_output: The full ``virsh version`` output.
        :param label: The line prefix, e.g. ``"Running hypervisor"``.

        :returns: The remainder of the matching line, or an empty string.
    """
    for line in version_output.splitlines():
        stripped = line.strip()
        if stripped.startswith(label):
            _, _, value = stripped.partition(":")
            rtnval = value.strip()
            return rtnval
    rtnval = ""
    return rtnval


def parse_xml_attribute(xml_text: str, *, element: str,
                        attribute: str) -> Optional[str]:
    """
        Extract a single attribute value from the FIRST occurrence of an
        element in an XML document.  Handles both quote styles.

        :param xml_text: The XML text.
        :param element: The element name, e.g. ``"forward"``.
        :param attribute: The attribute name, e.g. ``"mode"``.

        :returns: The attribute value, or ``None`` when absent.
    """
    pattern = r"<{}\b[^>]*\b{}=['\"]([^'\"]*)['\"]".format(
        re.escape(element), re.escape(attribute))
    match = re.search(pattern, xml_text)
    if match is None:
        rtnval = None
        return rtnval
    rtnval = match.group(1)
    return rtnval


def parse_volume_table(text: str) -> List[Dict[str, str]]:
    """
        Parse ``virsh vol-list <pool>`` table output into records.

        The table has a two-line header (column names and a dash rule)
        followed by ``name path`` rows.

        :param text: The table text.

        :returns: A list of ``{"name": ..., "path": ...}`` dicts.
    """
    rtnval: List[Dict[str, str]] = []
    lines = [ln for ln in text.splitlines() if len(ln.strip()) > 0]
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("-"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) == 0:
            continue
        if parts[0].lower() == "name":
            continue
        record = {"name": parts[0],
                  "path": parts[1].strip() if len(parts) > 1 else ""}
        rtnval.append(record)
    return rtnval
