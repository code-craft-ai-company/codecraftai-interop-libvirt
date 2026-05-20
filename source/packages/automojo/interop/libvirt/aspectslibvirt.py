"""
    .. module:: aspectslibvirt
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Behaviour-modifying parameters for the libvirt interop
               client.  libvirt is a native-binding transport, so the
               Aspects flavour here is ``AspectsNative`` — not
               ``AspectsRest``.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from dataclasses import dataclass

from automojo.aspects.aspects import Aspects


@dataclass
class AspectsNative(Aspects):
    """
        libvirt-flavoured behaviour carrier.

        Inherits the generic completion / timeout / attempt fields from
        :class:`Aspects`.  libvirt is reached over native bindings, not
        REST, so the additional fields describe native-transport
        behaviour rather than HTTP behaviour.

        :param reconnect_on_drop: When True, the connection manager is
            permitted to transparently reopen a dropped connection
            within the ``max_attempts`` budget.
        :param retry_interval: Seconds slept between retry attempts when
            a transient libvirt error is encountered.
        :param validate_xml: When True, composed XML is validated for
            well-formedness before submission.
    """
    reconnect_on_drop: bool = False
    retry_interval: float = 1.0
    validate_xml: bool = True


DEFAULT_LIBVIRT_ASPECTS = AspectsNative()


__all__ = [
    "AspectsNative",
    "DEFAULT_LIBVIRT_ASPECTS",
]
