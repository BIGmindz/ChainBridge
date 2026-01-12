# PAC-SEC-P819: Interface Analysis

## Executive Summary

This document analyzes the current `modules/mesh/identity.py` API surface to define the hybrid ED25519 + ML-DSA-65 migration path. The goal is 100% backward compatibility while adding quantum-resistant signing capabilities.

---

## Current API Surface

### Module: `modules/mesh/identity.py`

**Version:** 3.0.0  
**LOC:** 630 lines  
**Primary Classes:** `NodeIdentity`, `IdentityManager`  
**Crypto Backend:** `cryptography.hazmat.primitives.asymmetric.ed25519`

---

## Class: `NodeIdentity`

### Data Attributes

| Attribute | Type | Description | PQC Impact |
|-----------|------|-------------|------------|
| `node_id` | `str` | SHA256(public_key)[:32] hex | Must accommodate larger PQC keys |
| `node_name` | `str` | Human-readable identifier | No change |
| `public_key_bytes` | `bytes` | 32-byte ED25519 public key | Expand to hybrid (32 + 1952 bytes) |
| `private_key_bytes` | `Optional[bytes]` | 32-byte ED25519 private key | Expand to hybrid (32 + 4032 bytes) |
| `created_at` | `str` | ISO 8601 timestamp | No change |
| `federation_id` | `str` | Federation identifier | No change |
| `capabilities` | `list` | Node capabilities | Add "PQC" capability |

### Properties

| Property | Return Type | Description | PQC Impact |
|----------|-------------|-------------|------------|
| `public_key_b64` | `str` | Base64-encoded public key | Returns hybrid key |
| `has_private_key` | `bool` | Can sign check | No change |

### Class Methods

| Method | Signature | Description | PQC Impact |
|--------|-----------|-------------|------------|
| `generate()` | `(node_name, federation_id) -> NodeIdentity` | Generate new identity | Generate both key pairs |
| `from_public_key()` | `(public_key_bytes, node_name) -> NodeIdentity` | Create from public key | Support hybrid format |
| `load()` | `(path) -> NodeIdentity` | Load from disk | Support hybrid format |

### Instance Methods

| Method | Signature | Description | PQC Impact |
|--------|-----------|-------------|------------|
| `sign()` | `(message: bytes) -> bytes` | Sign message | Return hybrid signature |
| `sign_dict()` | `(data: dict) -> str` | Sign JSON dict | Return hybrid signature |
| `verify()` | `(message, signature) -> bool` | Verify signature | Verify hybrid signature |
| `verify_dict()` | `(data, signature_b64) -> bool` | Verify signed dict | Verify hybrid signature |
| `verify_peer()` | `(pk, msg, sig) -> bool` | Static peer verify | Support hybrid |
| `create_challenge()` | `() -> dict` | Create auth challenge | No change |
| `respond_to_challenge()` | `(challenge) -> dict` | Sign challenge | Hybrid signature |
| `verify_challenge_response()` | `(challenge, response) -> (bool, str)` | Verify response | Hybrid verify |
| `save()` | `(path, include_private_key) -> None` | Save to disk | Save hybrid keys |
| `to_public_dict()` | `() -> dict` | Export public data | Include hybrid info |

---

## Class: `IdentityManager`

### Methods

| Method | Signature | Description | PQC Impact |
|--------|-----------|-------------|------------|
| `__init__()` | `(identity_path) -> None` | Initialize manager | No change |
| `identity` | Property -> `NodeIdentity` | Get self identity | No change |
| `node_id` | Property -> `str` | Get node ID | No change |
| `initialize()` | `(node_name, federation_id) -> NodeIdentity` | Init identity | No change |
| `add_peer_identity()` | `(peer) -> None` | Cache peer | No change |
| `get_peer_identity()` | `(node_id) -> NodeIdentity` | Get cached peer | No change |
| `verify_peer_signature()` | `(node_id, msg, sig) -> bool` | Verify peer sig | Hybrid verify |
| `get_peer_count()` | `() -> int` | Count peers | No change |
| `get_all_peer_ids()` | `() -> list` | List peer IDs | No change |

---

## Key Size Analysis

### Current (ED25519)

| Component | Size | Notes |
|-----------|------|-------|
| Public Key | 32 bytes | Compact |
| Private Key | 32 bytes | Seed form |
| Signature | 64 bytes | Fixed size |
| Node ID | 32 hex chars | SHA256[:32] |

### Hybrid (ED25519 + ML-DSA-65)

| Component | ED25519 | ML-DSA-65 | Total | Growth |
|-----------|---------|-----------|-------|--------|
| Public Key | 32 | 1,952 | 1,984 bytes | 62x |
| Private Key | 32 | 4,032 | 4,064 bytes | 127x |
| Signature | 64 | 3,309 | 3,373 bytes | 53x |

### Storage Impact

| Scenario | Current | Hybrid | Impact |
|----------|---------|--------|--------|
| Identity file (w/ private) | ~0.5 KB | ~8 KB | +7.5 KB |
| Identity file (public only) | ~0.3 KB | ~3 KB | +2.7 KB |
| Message + signature | 64 B overhead | 3,373 B overhead | +3,309 B |

---

## Serialization Format

### Current JSON Format

```json
{
  "version": "3.0.0",
  "node_id": "abc123...",
  "node_name": "NODE-ALPHA",
  "federation_id": "CHAINBRIDGE-FEDERATION",
  "capabilities": ["ATTEST", "RELAY", "GOSSIP"],
  "created_at": "2026-01-11T00:00:00Z",
  "public_key": "<base64-32-bytes>",
  "private_key": "<base64-32-bytes>"
}
```

### Proposed Hybrid JSON Format

```json
{
  "version": "4.0.0",
  "format": "HYBRID_ED25519_MLDSA65",
  "node_id": "abc123...",
  "node_name": "NODE-ALPHA",
  "federation_id": "CHAINBRIDGE-FEDERATION",
  "capabilities": ["ATTEST", "RELAY", "GOSSIP", "PQC"],
  "created_at": "2026-01-11T00:00:00Z",
  "keys": {
    "ed25519": {
      "public": "<base64-32-bytes>",
      "private": "<base64-32-bytes>"
    },
    "mldsa65": {
      "public": "<base64-1952-bytes>",
      "private": "<base64-4032-bytes>"
    }
  },
  "signature_mode": "HYBRID"
}
```

---

## Signature Format

### Current

```
signature = ED25519_SIGN(private_key, message)
# 64 bytes
```

### Proposed Hybrid

```
hybrid_signature = {
  "version": 1,
  "ed25519": ED25519_SIGN(ed_sk, message),      # 64 bytes
  "mldsa65": MLDSA65_SIGN(ml_sk, message),      # 3309 bytes
}
# Total: 3373 bytes + envelope overhead
```

### Binary Format (Compact)

```
[VERSION:1][ED25519_SIG:64][MLDSA65_SIG:3309]
# Total: 3374 bytes
```

---

## Backward Compatibility Requirements

### MUST Support

1. **Legacy Identity Loading**: Old v3.0.0 identity files must load correctly
2. **Legacy Signature Verification**: ED25519-only signatures from existing nodes
3. **Legacy Key Export**: `to_public_dict()` must work for non-PQC consumers
4. **Gradual Migration**: Nodes can upgrade independently

### Migration Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `LEGACY` | ED25519 only | Pre-migration nodes |
| `HYBRID` | Both signatures required | Migration period |
| `PQC_ONLY` | ML-DSA-65 only | Post-quantum future |

---

## Consumer Analysis

### Files Importing `identity.py`

| File | Usage | Migration Impact |
|------|-------|------------------|
| `modules/mesh/networking.py` | Peer authentication | Medium |
| `modules/mesh/trust.py` | Trust attestations | Medium |
| `modules/mesh/consensus.py` | Vote signing | Medium |
| `modules/mesh/discovery.py` | Node announcement | Low |
| `api/server.py` | API authentication | Low |
| `tests/` | Test fixtures | Low |

### Required Interface Stability

The following must remain unchanged:

1. `NodeIdentity.generate(node_name, federation_id)`
2. `NodeIdentity.sign(message) -> bytes`
3. `NodeIdentity.verify(message, signature) -> bool`
4. `NodeIdentity.save(path)`
5. `NodeIdentity.load(path)`
6. `IdentityManager` full API

---

## Recommendations

### 1. New Module Structure

Create `modules/mesh/identity_pqc/` with clean implementation, then provide adapter layer.

### 2. Version Tagging

All serialized data must include version tag for format evolution.

### 3. Pluggable Backend

Abstract crypto operations to swap `dilithium-py` → `liboqs` in future.

### 4. Signature Size Handling

Consumers must handle 53x larger signatures - review all buffers and protocols.

### 5. Node ID Stability

Node ID must remain stable during migration. Compute from ED25519 key only for continuity.

---

## Phase 1 Deliverable Checklist

- [x] Current API surface documented
- [x] Key size analysis complete
- [x] Serialization format defined
- [x] Backward compatibility requirements listed
- [x] Consumer impact assessed
- [x] Recommendations provided

**Phase 1 Status: COMPLETE**

---

*Generated by Atlas (GID-09) | PAC-SEC-P819 Phase 1*
