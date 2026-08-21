"""
    .. module:: test_properties
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Property-based (hypothesis) tests for safe XML composition,
               idempotent operation convergence, retry equivalence and
               the wait_for_domain_state waiter.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from xml.etree import ElementTree

from ccai.testbase.properties import given
from ccai.testbase.properties import strategies as st

from ccai.interop.libvirt.aspectslibvirt import AspectsNative
from ccai.interop.libvirt.connection.libvirtconnectioncredential import (
    LibvirtConnectionCredential
)
from ccai.interop.libvirt.libvirtclient import LibvirtClient
from ccai.interop.libvirt.specs.libvirtdiskspec import LibvirtDiskSpec
from ccai.interop.libvirt.specs.libvirtdomainspec import (
    LibvirtDomainSpec
)
from ccai.interop.libvirt.specs.libvirtnetworkspec import (
    LibvirtNetworkSpec
)
from ccai.interop.libvirt.xml.domainxmlcomposer import (
    DomainXmlComposer
)


# Names that may carry XML-significant characters.
_HOSTILE_TEXT = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
    min_size=1, max_size=24,
)


@given(name=_HOSTILE_TEXT, source=_HOSTILE_TEXT)
def test_domain_xml_is_always_well_formed(name, source):
    """
        For any hostile name / source-path the composed domain XML is
        well-formed and parseable.
    """
    disk = LibvirtDiskSpec(source_path=source, target_dev="vda")
    spec = LibvirtDomainSpec(name=name, disks=[disk])
    composer = DomainXmlComposer()

    document = composer.compose(spec=spec)
    parsed = ElementTree.fromstring(document)

    assert parsed.tag == "domain"
    return


@given(name=_HOSTILE_TEXT, constraints={"max_examples": 120})
def test_domain_xml_is_deterministic(name):
    """
        The same spec produces byte-identical XML.
    """
    spec = LibvirtDomainSpec(name=name)
    composer = DomainXmlComposer()

    first = composer.compose(spec=spec)
    second = composer.compose(spec=spec)

    assert first == second
    return


def _fresh_client(module_holder):
    """
        Build a client bound to a fresh mock module.

        :param module_holder: List used to retain the mock runner.

        :returns: A LibvirtClient.
    """
    from .mockvirshrunner import (
        MockVirshRunner
    )

    runner = MockVirshRunner()
    module_holder.append(runner)
    credential = LibvirtConnectionCredential(uri="qemu:///system")
    rtnval = LibvirtClient(credential=credential, runner=runner)
    return rtnval


@given(repeats=st.integers(min_value=1, max_value=5), constraints={"max_examples": 60})
def test_define_network_converges(repeats):
    """
        Defining a network N times converges to one network.
    """
    holder = []
    try:
        client = _fresh_client(module_holder=holder)
        spec = LibvirtNetworkSpec(name="lab-net")
        index = 0
        while index < repeats:
            client.networks.define_network(spec=spec)
            index = index + 1
        networks = client.networks.list_networks()
        assert len(networks) == 1
    finally:
        pass
    return


@given(repeats=st.integers(min_value=1, max_value=5), constraints={"max_examples": 30})
def test_attach_disk_converges(repeats):
    """
        Attaching the same disk N times attaches it exactly once.
    """
    holder = []
    try:
        client = _fresh_client(module_holder=holder)
        domain = LibvirtDomainSpec(name="vm-alpha")
        client.domains.define_domain(spec=domain)
        disk = LibvirtDiskSpec(source_path="/data/d.qcow2",
                               target_dev="vdb")
        index = 0
        while index < repeats:
            client.domains.attach_disk(domain_name="vm-alpha", spec=disk)
            index = index + 1
        xml = client.domains.get_domain_xml(name="vm-alpha")
        assert xml.count("dev='vdb'") == 1
    finally:
        pass
    return


@given(budget=st.integers(min_value=1, max_value=4), constraints={"max_examples": 30})
def test_retry_budget_yields_same_result(budget):
    """
        An idempotent operation returns the same result regardless of
        the aspects retry budget.
    """
    holder = []
    try:
        client = _fresh_client(module_holder=holder)
        spec = LibvirtNetworkSpec(name="lab-net")
        aspects = AspectsNative(max_attempts=budget, retry_interval=0.0)
        first = client.networks.define_network(spec=spec, aspects=aspects)
        second = client.networks.define_network(spec=spec,
                                                aspects=aspects)
        assert first.uuid == second.uuid
    finally:
        pass
    return


@given(prefix_len=st.integers(min_value=0, max_value=6), constraints={"max_examples": 20})
def test_wait_for_domain_state_terminal_correctness(prefix_len):
    """
        For any monotonic mock state stream that eventually reaches the
        target, the waiter returns the target state.
    """
    holder = []
    try:
        client = _fresh_client(module_holder=holder)
        domain = LibvirtDomainSpec(name="vm-alpha")
        client.domains.define_domain(spec=domain)
        runner = holder[0]
        runner.domains["vm-alpha"]["state_script"] = (
            ["shutoff"] * prefix_len) + ["running"]

        aspects = AspectsNative(completion_interval=0.0,
                                completion_timeout=5.0)
        info = client.domains.wait_for_domain_state(
            name="vm-alpha", desired_state="running", aspects=aspects
        )
        assert info.state == "running"
    finally:
        pass
    return
