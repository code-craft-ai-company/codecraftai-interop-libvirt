=========================================
Code Craft AI Interop - libvirt / KVM
=========================================

The ``codecraftai-interop-libvirt`` package is the venue-specific client for libvirt-managed
hypervisors (KVM/QEMU primarily, with Xen, LXC, and VirtualBox reachable through the same
binding). libvirt's wire protocol is a custom binary RPC accessed through the official
``libvirt-python`` bindings, so ``RestClientBase`` does not apply — this package is the
canonical example of the "native bindings only when the protocol has no other option"
branch of the cross-cutting usability commitments.

Highlights
==========

- ``LibvirtClient`` — the venue client speaking libvirt-native RPC; connection lifecycle plus host capability and node-info queries.
- Network and storage management — NAT/bridged/isolated networks, storage pools, and volumes.
- Domain lifecycle — define/create/start/shutdown/destroy/undefine, domain XML templating with safe parameterisation, and disk/NIC attach-detach.
- Snapshots — snapshot management. (The libvirt operations exposed here are synchronous via the native binding; no asynchronous task-handle surface is provided.)
- Aspects-driven transport — authentication uses the libvirt connection URI plus an ``ILibvirtAuthCallback``; every behaviour-bearing call accepts ``aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS`` (a libvirt-flavoured ``Aspects`` object, not ``AspectsRest``).

Repository Structure
====================

- ``development/`` - Runtime environment scripts.
- ``repository-setup/`` - Repository homing and setup scripts.
- ``source/packages/ccai/interop/libvirt/`` - Package source code.
- ``source/testroots/testbase/ccai/tests/interop/libvirt/`` - TestBase test roots.
- ``specs/`` - Requirements, design, and task documentation (Kiro-style).
- ``userguide/`` - Standards, conventions, and documentation.

Environment Setup
=================

When working in a Codex container:

.. code-block:: bash

   ./development/setup-agent-container

For local development:

.. code-block:: bash

   ./repository-setup/rehome-repository
   ./development/setup-environment

Running Tests
=============

.. code-block:: bash

   source .venv/bin/activate
   testbase testing run --root ./source/testroots/testbase --includes=testbase.ccai.tests
Standards and Conventions
=========================

- Naming conventions: ``userguide/10-02-naming-conventions.rst``
- Code organization: ``userguide/10-01-code-organization.rst``
- Coding standards: ``userguide/10-00-coding-standards.rst``

Additional Resources
====================

- User guide entry point: ``userguide/userguide.rst``
