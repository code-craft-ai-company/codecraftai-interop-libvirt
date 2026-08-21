"""
    Originates the libvirt test resources into this scope.

    Replaces conftest.py, which testbase does not read.

    Only the resources that accumulate no state are originated here.
    The stateful doubles are attached to the test cases themselves, so
    each test gets a fresh instance; a scope origination is one
    instance for the whole package.
"""

from ccai import testbase

from .factories import (
    create_libvirt_credential,
    create_libvirt_aspects,
)

testbase.originate.parameter(create_libvirt_credential, identifier="credential")
testbase.originate.parameter(create_libvirt_aspects, identifier="aspects")
