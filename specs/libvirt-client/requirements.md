# Requirements

## Introduction

The `libvirt-client` feature provides a typed Python client for libvirt
on top of the official `libvirt-python` bindings. Because libvirt's wire
protocol is not REST, this client does **not** use `RestClientBase` — it
is the suite's canonical example of a native-binding client. The "one
transport per package" rule still applies: this package SHALL NOT mix
native libvirt calls with REST or CLI transports.

The client covers connection lifecycle, host/node info, networks,
storage pools and volumes, domain (VM) lifecycle and XML templating,
disk/NIC attach-detach, and snapshots. Every behaviour-bearing method
accepts `aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS`. Credentials
enter as a typed `LibvirtConnectionCredential` carrying the connection
URI and (optionally) an `ILibvirtAuthCallback`.

---

## Requirements

### Requirement 1: Open and Close a Libvirt Connection

#### Acceptance Criteria

1. WHEN the client is constructed with a `LibvirtConnectionCredential`
   THE SYSTEM SHALL call `libvirt.openAuth(uri, auth, flags)` on first
   use and cache the connection.
2. WHEN the connection cannot be opened THE SYSTEM SHALL raise
   `LibvirtConnectionError` with the URI and the underlying error.
3. WHEN the caller invokes `close(aspects)` THE SYSTEM SHALL close the
   connection and reject further operations until reopened.
4. WHEN the connection is dropped by the server THE SYSTEM SHALL detect
   it on the next call and raise `LibvirtConnectionError`; transparent
   reconnect SHALL be governed by aspects, not by built-in behaviour.

### Requirement 2: Query Host and Node Information

#### Acceptance Criteria

1. WHEN the caller invokes `host_info(aspects)` THE SYSTEM SHALL return
   a `LibvirtHostInfo` record (hostname, hypervisor type, version,
   capabilities summary).
2. WHEN the caller invokes `node_info(aspects)` THE SYSTEM SHALL return
   a `LibvirtNodeInfo` record (CPU count, memory, NUMA topology).
3. WHEN the caller invokes `capabilities_xml(aspects)` THE SYSTEM SHALL
   return the raw capabilities XML for callers that need fine-grained
   inspection.

### Requirement 3: Manage Networks

#### Acceptance Criteria

1. WHEN the caller invokes `list_networks(aspects)` THE SYSTEM SHALL
   return a list of `LibvirtNetwork` records (name, uuid, active state,
   forward mode, bridge).
2. WHEN the caller invokes `define_network(spec, aspects)` THE SYSTEM
   SHALL compose the network XML and call `networkDefineXML`. WHEN a
   network with the same name already exists THE SYSTEM SHALL return
   the existing record (idempotent).
3. WHEN the caller invokes `start_network(name, aspects)`,
   `stop_network(name, aspects)`, or `undefine_network(name, aspects)`
   THE SYSTEM SHALL perform the corresponding libvirt action.
   `undefine_network` against an unknown name SHALL be a no-op.

### Requirement 4: Manage Storage Pools and Volumes

#### Acceptance Criteria

1. WHEN the caller invokes `list_storage_pools(aspects)` THE SYSTEM
   SHALL return `LibvirtStoragePool` records.
2. WHEN the caller invokes `define_storage_pool(spec, aspects)`,
   `start_storage_pool(name, aspects)`, `stop_storage_pool(name, aspects)`,
   or `undefine_storage_pool(name, aspects)` THE SYSTEM SHALL perform
   the corresponding libvirt action with idempotent define and undefine.
3. WHEN the caller invokes `create_volume(pool_name, spec, aspects)`,
   `list_volumes(pool_name, aspects)`, `delete_volume(pool_name, name, aspects)`,
   or `resize_volume(pool_name, name, capacity_bytes, aspects)` THE SYSTEM
   SHALL operate on the named pool with idempotent delete.

### Requirement 5: Manage Domains (Virtual Machines)

#### Acceptance Criteria

1. WHEN the caller invokes `define_domain(spec, aspects)` THE SYSTEM
   SHALL compose the domain XML and call `defineXML`. A domain with the
   same name SHALL be returned without redefinition (idempotent).
2. WHEN the caller invokes `create_domain(name, aspects)` (start),
   `shutdown_domain(name, aspects)` (graceful), `destroy_domain(name, aspects)`
   (force), `reboot_domain(name, aspects)`, `suspend_domain(name, aspects)`,
   `resume_domain(name, aspects)`, or `undefine_domain(name, aspects)` THE
   SYSTEM SHALL perform the corresponding libvirt action.
3. WHEN `undefine_domain` is called against an unknown name THE SYSTEM
   SHALL succeed as a no-op.
4. WHEN the caller invokes `get_domain_info(name, aspects)` THE SYSTEM
   SHALL return a `LibvirtDomainInfo` record (state, vcpus, memory,
   cpu_time).
5. WHEN the caller invokes `list_domains(aspects)` THE SYSTEM SHALL
   return all defined domains.

### Requirement 6: Domain XML Composition Helper

#### Acceptance Criteria

1. WHEN composing domain XML from a `LibvirtDomainSpec` THE SYSTEM SHALL
   escape all user-supplied string values to prevent XML injection.
2. THE SYSTEM SHALL validate that the composed XML is well-formed
   before submission and SHALL raise `LibvirtXmlCompositionError`
   otherwise.
3. THE SYSTEM SHALL render deterministically: the same spec produces
   byte-identical XML.

### Requirement 7: Attach and Detach Disks and NICs

#### Acceptance Criteria

1. WHEN the caller invokes `attach_disk(domain_name, spec, aspects)`,
   `detach_disk(domain_name, target_dev, aspects)`,
   `attach_nic(domain_name, spec, aspects)`, or
   `detach_nic(domain_name, mac, aspects)` THE SYSTEM SHALL update the
   domain device list.
2. WHEN the device is already attached with identical config THE SYSTEM
   SHALL be a no-op (idempotent).
3. WHEN the device is not attached and the caller invokes `detach_*`
   THE SYSTEM SHALL be a no-op (idempotent).

### Requirement 8: Manage Snapshots

#### Acceptance Criteria

1. WHEN the caller invokes `create_snapshot(domain_name, name, aspects)`,
   `list_snapshots(domain_name, aspects)`,
   `revert_snapshot(domain_name, name, aspects)`, or
   `delete_snapshot(domain_name, name, aspects)` THE SYSTEM SHALL perform
   the corresponding libvirt action.
2. Idempotent delete on unknown snapshot name.

### Requirement 9: Wait For Domain State

#### Acceptance Criteria

1. WHEN the caller invokes `wait_for_domain_state(name, desired_state, aspects)`
   THE SYSTEM SHALL poll `get_domain_info` at the interval dictated by
   aspects.
2. WHEN the aspects timeout elapses THE SYSTEM SHALL raise
   `TimeoutError`.

### Requirement 10: Aspects on Every Behaviour-Bearing Call

#### Acceptance Criteria

1. THE SYSTEM SHALL accept `aspects: AspectsNative = DEFAULT_LIBVIRT_ASPECTS`
   on every operation that talks to libvirt.
2. THE SYSTEM SHALL NOT use behaviour-modifying decorators.
3. WHEN a transient libvirt error occurs THE SYSTEM SHALL retry per
   `aspects` policy.
