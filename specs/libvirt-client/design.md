# Design

## Overview

`LibvirtClient` is a typed client built on the official `libvirt-python`
bindings. The package does NOT use `RestClientBase` because libvirt is
not REST; it is the suite's canonical native-binding client. The "one
transport per package" rule still applies: no REST calls, no CLI
shell-outs. Domain XML is composed by a safe templating helper that
escapes user values and validates well-formedness before submission.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│  automojo-provisioning / venues / libvirt              │
└──────────┬─────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  LibvirtClient (this package)                          │
│   native libvirt-python bindings                       │
│   AspectsNative on every op                            │
│   API groups: host, networks, storage-pools,           │
│     volumes, domains, snapshots                        │
│   safe domain-XML composer                             │
└──────────┬─────────────────────────────────────────────┘
           │ libvirt RPC (qemu+ssh:// , qemu:///system, etc.)
           ▼
┌────────────────────────────────────────────────────────┐
│  libvirtd on hypervisor host                           │
└────────────────────────────────────────────────────────┘
```

---

## Data Model

`model/`: `libvirthostinfo.py`, `libvirtnodeinfo.py`, `libvirtnetwork.py`,
`libvirtstoragepool.py`, `libvirtvolume.py`, `libvirtdomaininfo.py`,
`libvirtsnapshot.py`.

`specs/`: `libvirtnetworkspec.py`, `libvirtstoragepoolspec.py`,
`libvirtvolumespec.py`, `libvirtdomainspec.py`, `libvirtdiskspec.py`,
`libvirtnicspec.py`.

Exceptions: `LibvirtConnectionError`, `LibvirtXmlCompositionError`.

---

## Module Layout

```
source/packages/automojo/interop/libvirt/
├── libvirtclient.py
├── aspectslibvirt.py            # AspectsNative + DEFAULT_LIBVIRT_ASPECTS
├── connection/
│   ├── libvirtauthcallback.py
│   └── libvirtconnectionmanager.py
├── apigroups/
│   ├── hostgroup.py
│   ├── networksgroup.py
│   ├── storagepoolsgroup.py
│   ├── volumesgroup.py
│   ├── domainsgroup.py
│   └── snapshotsgroup.py
├── xml/
│   ├── domainxmlcomposer.py
│   ├── networkxmlcomposer.py
│   ├── storagepoolxmlcomposer.py
│   └── xmlescape.py
├── model/
├── specs/
└── exceptions/
```

---

## See Also

- `automojo-provisioning/specs/venue-libvirt/`
- Cross-cutting usability commitment §8.1: one transport per package — this is the
  canonical native-binding example.

---

## Testing Strategy

Example-based tests cover connection open/close error paths, idempotent
define-then-create on networks/pools/domains, attach-detach idempotency,
and snapshot lifecycle, using a mock `libvirt` module (the official
bindings have a documented stub-friendly surface).

Property-based tests (hypothesis) are **required** for:
1. **Safe XML composition.** For any randomly-generated `LibvirtDomainSpec`
   with embedded special characters (`<`, `>`, `&`, `"`, `'`), the composed
   XML is well-formed and parseable; no escape character produces a
   malformed document.
2. **Idempotent operations.** Define-then-define, attach-then-attach,
   detach-then-detach, undefine-then-undefine all converge to the same
   state and emit at most one effective libvirt call.
3. **Idempotent retry semantics** within and beyond the aspects budget.
4. **`wait_for_domain_state` waiter** terminal-state correctness against
   arbitrary monotonic mock state streams.

Live-libvirt integration tests run under `multihost` against a sandbox
qemu:///session host and are gated by an env var.
