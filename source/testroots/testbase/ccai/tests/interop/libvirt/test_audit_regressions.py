"""
    .. module:: test_audit_regressions
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Regression tests for the non-REST interop audit findings
               NR-H5 (metadata_xml XML injection) and NR-H6 (run_with_retry
               broad exception catch).

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from xml.etree import ElementTree

import pytest

from ccai.errors.exceptions import SemanticError

from ccai.interop.libvirt.apigroups.retrysupport import run_with_retry
from ccai.interop.libvirt.aspectslibvirt import AspectsNative
from ccai.interop.libvirt.exceptions.libvirtoperationerror import (
    LibvirtOperationError
)
from ccai.interop.libvirt.exceptions.libvirtxmlcompositionerror import (
    LibvirtXmlCompositionError
)
from ccai.interop.libvirt.specs.libvirtdomainspec import (
    LibvirtDomainSpec
)
from ccai.interop.libvirt.xml.domainxmlcomposer import DomainXmlComposer

from ccai.interop.libvirt.exceptions.libvirtconnectionerror import (
    LibvirtConnectionError
)


# ----------------------------------------------------------------------
# NR-H5: metadata_xml must not allow XML injection.
# ----------------------------------------------------------------------


def test_metadata_xml_well_formed_fragment_is_accepted():
    spec = LibvirtDomainSpec(
        name="vm-meta",
        metadata_xml="<vendor:info xmlns:vendor='urn:x'>ok</vendor:info>",
    )
    composer = DomainXmlComposer()
    document = composer.compose(spec=spec)
    parsed = ElementTree.fromstring(document)
    assert parsed.tag == "domain"
    return


def test_metadata_xml_injection_close_tag_is_rejected():
    # An attempt to break out of <metadata> and inject sibling elements.
    spec = LibvirtDomainSpec(
        name="vm-evil",
        metadata_xml="</metadata><evil/>",
    )
    composer = DomainXmlComposer()
    with pytest.raises(LibvirtXmlCompositionError):
        composer.compose(spec=spec)
    return


def test_metadata_xml_trailing_content_is_rejected():
    spec = LibvirtDomainSpec(
        name="vm-evil2",
        metadata_xml="<info/><sneaky/>",
    )
    composer = DomainXmlComposer()
    with pytest.raises(LibvirtXmlCompositionError):
        composer.compose(spec=spec)
    return


def test_metadata_xml_malformed_fragment_is_rejected():
    spec = LibvirtDomainSpec(
        name="vm-evil3",
        metadata_xml="<unclosed>",
    )
    composer = DomainXmlComposer()
    with pytest.raises(LibvirtXmlCompositionError):
        composer.compose(spec=spec)
    return


# ----------------------------------------------------------------------
# NR-H6: run_with_retry must not retry/mask non-transient errors.
# ----------------------------------------------------------------------


def _aspects() -> AspectsNative:
    rtnval = AspectsNative(max_attempts=3, retry_interval=0.0)
    return rtnval


def test_run_with_retry_lets_semantic_error_bubble():
    calls = []

    def _operation():
        calls.append(1)
        raise SemanticError("misused API")

    with pytest.raises(SemanticError):
        run_with_retry(operation=_operation, aspects=_aspects(),
                       description="op")
    # SemanticError must bubble on the first attempt without retrying.
    assert len(calls) == 1
    return


def test_run_with_retry_lets_type_error_bubble():
    calls = []

    def _operation():
        calls.append(1)
        raise TypeError("programming defect")

    with pytest.raises(TypeError):
        run_with_retry(operation=_operation, aspects=_aspects(),
                       description="op")
    assert len(calls) == 1
    return


def test_run_with_retry_retries_transient_connection_error():
    calls = []

    def _operation():
        calls.append(1)
        if len(calls) < 3:
            raise LibvirtConnectionError("transient")
        return "ok"

    result = run_with_retry(operation=_operation, aspects=_aspects(),
                            description="op")
    assert result == "ok"
    assert len(calls) == 3
    return


def test_run_with_retry_exhausts_budget_on_transient_error():
    def _operation():
        raise LibvirtConnectionError("always transient")

    with pytest.raises(LibvirtOperationError):
        run_with_retry(operation=_operation, aspects=_aspects(),
                       description="op")
    return
