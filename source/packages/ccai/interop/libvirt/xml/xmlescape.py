"""
    .. module:: xmlescape
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Defensive XML escaping helpers for safe libvirt XML
               composition.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


def escape_text(*, value: str) -> str:
    """
        Escape a string for safe placement inside an XML text node.

        Replaces ``&``, ``<`` and ``>`` with their entity references.
        ``&`` must be replaced first so that the entities emitted for the
        other characters are not double-escaped.

        :param value: The untrusted string value.

        :returns: The escaped string.
    """
    escaped = value.replace("&", "&amp;")
    escaped = escaped.replace("<", "&lt;")
    escaped = escaped.replace(">", "&gt;")
    rtnval = escaped
    return rtnval


def escape_attribute(*, value: str) -> str:
    """
        Escape a string for safe placement inside an XML attribute value.

        Builds on :func:`escape_text` and additionally escapes the double
        and single quote characters so the value may be wrapped in either
        quoting style.

        :param value: The untrusted string value.

        :returns: The escaped string.
    """
    escaped = escape_text(value=value)
    escaped = escaped.replace("\"", "&quot;")
    escaped = escaped.replace("'", "&apos;")
    rtnval = escaped
    return rtnval
