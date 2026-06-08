# Implementation Plan — libvirt Client

## Package Skeleton

- [x] 1. Create `source/packages/ccai/interop/libvirt/` package tree with `connection/`, `apigroups/`, `xml/`, `model/`, `specs/`, `exceptions/` subpackages.
- [x] 2. Add `aspectslibvirt.py` defining `AspectsNative` and `DEFAULT_LIBVIRT_ASPECTS`.

## Connection Lifecycle

- [x] 3. Implement `LibvirtConnectionManager` wrapping `libvirt.openAuth` with caching, drop-detection, and aspects-driven reopen.
- [x] 4. Implement `LibvirtAuthCallback` adapter for SASL/SSH credential delivery.

## XML Composition

- [x] 5. Implement `xmlescape.py` (defensive escaping of `<>&"'`).
- [x] 6. Implement `DomainXmlComposer.compose(spec)` with well-formedness validation and deterministic output.
- [x] 7. Implement `NetworkXmlComposer.compose(spec)` and `StoragePoolXmlComposer.compose(spec)`.

## API Groups

- [x] 8. Implement `HostGroup.host_info / node_info / capabilities_xml`.
- [x] 9. Implement `NetworksGroup.list / define / start / stop / undefine` with idempotency.
- [x] 10. Implement `StoragePoolsGroup.list / define / start / stop / undefine` with idempotency.
- [x] 11. Implement `VolumesGroup.create / list / delete / resize` with idempotent delete.
- [x] 12. Implement `DomainsGroup.define / create / shutdown / destroy / reboot / suspend / resume / undefine / get_info / list` with idempotency.
- [x] 13. Implement disk/NIC attach-detach on `DomainsGroup` with idempotent semantics.
- [x] 14. Implement `SnapshotsGroup.create / list / revert / delete` with idempotent delete.

## Waiters

- [x] 15. Implement `wait_for_domain_state(name, desired_state, aspects)`.

## Data Model & Specs

- [x] 16. Implement model dataclasses for host info, node info, network, storage pool, volume, domain info, snapshot.
- [x] 17. Implement spec dataclasses for network/storage-pool/volume/domain/disk/NIC.

## Tests — Example-Based

- [x] 18. Connection open/close + error reclassification tests using a mock `libvirt` module.
- [x] 19. Idempotent define/create tests across networks, pools, domains.
- [x] 20. Snapshot lifecycle tests.
- [x] 21. Attach-detach idempotency tests.

## Tests — Property-Based (hypothesis)

- [x] 22. Safe XML composition well-formedness over arbitrary spec inputs.
- [x] 23. Idempotent operation convergence (define-then-define, attach-then-attach, etc.).
- [x] 24. Idempotent-retry equivalence within budget.
- [x] 25. `wait_for_domain_state` terminal-state correctness.

## Integration

- [ ] 26. Live-libvirt smoke-test fixture against `qemu:///session`, gated by env var.
