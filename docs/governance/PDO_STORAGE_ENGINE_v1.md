# PDO Storage Engine v1

**Document ID:** PDO-STORAGE-LAW-001  
**Version:** 1.0.0  
**Status:** ACTIVE  
**Effective:** 2025-12-26  
**Author:** Agent GID-07 (Dan)  
**PAC Reference:** PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-PROOF-LAYER-024

---

## 1. Purpose

This document establishes the **Proof-Addressed PDO Storage Engine** — a storage 
model where all PDO artifacts are indexed and retrieved by cryptographic hash, 
enabling verifiable, immutable governance record-keeping.

The storage engine implements the **Carvana Model**:
- **Proof-First Addressing** — All lookups start with proof hash
- **Metadata-Only Storage** — PDO metadata stored; artifacts stored externally
- **Immutable Writes** — Once written, never modified
- **Hash Collision Safety** — Multi-hash verification for integrity

---

## 2. Storage Architecture

### 2.1 Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PDO Storage Architecture                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  PDO Store   │───▶│  PDO Index   │───▶│   Proof      │              │
│  │  (Metadata)  │    │  (Hash→PDO)  │    │   Provider   │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                    │                      │
│         ▼                   ▼                    ▼                      │
│  ┌──────────────────────────────────────────────────────┐              │
│  │               External Artifact Store                │              │
│  │         (S3, IPFS, Blockchain, etc.)                │              │
│  └──────────────────────────────────────────────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Responsibilities

| Layer          | Responsibility                                    |
|----------------|---------------------------------------------------|
| PDO Store      | Store PDO metadata with proof references          |
| PDO Index      | Hash-based lookup for fast retrieval              |
| Proof Provider | Generate and verify proofs (see GIE_PROOF_LAYER)  |
| Artifact Store | External storage for full payloads                |

---

## 3. Proof-Addressed Model

### 3.1 Core Concept

Traditional storage: `id → record`  
Proof-addressed storage: `proof_hash → pdo_metadata → artifact_hashes`

Every PDO is addressed by:
1. **proof_hash** — Primary key (proof of PDO validity)
2. **pdo_hash** — Secondary key (hash of PDO content)
3. **artifact_hashes** — References to stored artifacts

### 3.2 Addressing Example

```python
# Store PDO
pdo_record = PDORecord(
    pdo_id="PDO-2025-12-26-001",
    proof_hash="sha256:abc123...",     # Primary address
    pdo_hash="sha256:def456...",        # Content hash
    artifact_hashes=[
        "sha256:ghi789...",             # Decision artifact
        "sha256:jkl012...",             # Outcome artifact
    ],
    created_at="2025-12-26T12:00:00Z",
)

# Retrieve by proof hash (primary)
pdo = store.get_by_proof_hash("sha256:abc123...")

# Retrieve by PDO hash (secondary)
pdo = index.lookup_by_pdo_hash("sha256:def456...")
```

---

## 4. Invariants

### INV-STORE-001 — Immutable Writes
Once a PDO record is written, it MUST NOT be modified. Updates create new records.

### INV-STORE-002 — Proof-First Addressing
All lookups MUST be possible via proof_hash. Other indices are secondary.

### INV-STORE-003 — Referential Integrity
All artifact_hashes MUST point to valid, stored artifacts.

### INV-STORE-004 — Hash Collision Safety
If two inputs produce same hash, store MUST detect and reject the collision.

### INV-STORE-005 — Audit Trail
All storage operations MUST be logged with:
- Operation type (WRITE, READ)
- Hash references
- Timestamp
- Requestor identity

### INV-STORE-006 — No Orphan Artifacts
Artifacts MUST NOT exist without a corresponding PDO record.

---

## 5. Data Structures

### 5.1 PDORecord

```python
@dataclass(frozen=True)
class PDORecord:
    """Immutable PDO storage record."""
    pdo_id: str                          # Human-readable identifier
    proof_hash: str                      # Primary key (proof reference)
    pdo_hash: str                        # Hash of PDO content
    artifact_hashes: Tuple[str, ...]     # References to artifacts
    
    # Metadata
    agent_gid: str                       # Creating agent
    pac_id: str                          # Source PAC
    created_at: str                      # ISO 8601 UTC
    
    # Proof metadata
    proof_class: str                     # P0, P1, P2, P3
    proof_provider: str                  # Provider ID
    
    # Optional blockchain anchor
    anchor_tx: Optional[str] = None      # Transaction hash if anchored
    anchor_chain: Optional[str] = None   # Chain identifier
```

### 5.2 IndexEntry

```python
@dataclass(frozen=True)
class IndexEntry:
    """Hash index entry for fast lookup."""
    hash_value: str                      # The hash being indexed
    hash_type: str                       # PROOF, PDO, or ARTIFACT
    pdo_id: str                          # Points to PDORecord
    created_at: str
```

### 5.3 StorageResult

```python
@dataclass(frozen=True)
class StorageResult:
    """Result of a storage operation."""
    success: bool
    operation: str                       # WRITE, READ, DELETE
    pdo_id: Optional[str]
    proof_hash: Optional[str]
    error: Optional[str]
    timestamp: str
```

---

## 6. Storage Operations

### 6.1 Write (Store PDO)

```python
def store_pdo(pdo_record: PDORecord) -> StorageResult:
    """
    Store a PDO record.
    
    INVARIANT: Immutable — will FAIL if record exists.
    """
    # 1. Verify proof_hash doesn't exist
    if exists(pdo_record.proof_hash):
        return StorageResult(success=False, error="DUPLICATE_PROOF_HASH")
    
    # 2. Verify all artifact_hashes are valid
    for artifact_hash in pdo_record.artifact_hashes:
        if not artifact_exists(artifact_hash):
            return StorageResult(success=False, error="MISSING_ARTIFACT")
    
    # 3. Verify hash collision safety
    if content_differs_for_hash(pdo_record.pdo_hash):
        return StorageResult(success=False, error="HASH_COLLISION")
    
    # 4. Write record
    write_record(pdo_record)
    
    # 5. Update indices
    update_index(pdo_record)
    
    # 6. Log audit trail
    log_operation("WRITE", pdo_record)
    
    return StorageResult(success=True, pdo_id=pdo_record.pdo_id)
```

### 6.2 Read (Retrieve PDO)

```python
def get_by_proof_hash(proof_hash: str) -> Optional[PDORecord]:
    """
    Retrieve PDO by proof hash (primary lookup).
    
    This is the canonical retrieval method.
    """
    record = lookup_by_proof_hash(proof_hash)
    
    if record:
        log_operation("READ", record)
    
    return record
```

### 6.3 Index Lookup

```python
def lookup_by_pdo_hash(pdo_hash: str) -> List[PDORecord]:
    """
    Retrieve PDOs by content hash.
    
    May return multiple records if same content was proven multiple times.
    """
    entries = index.query(hash_type="PDO", hash_value=pdo_hash)
    return [get_by_proof_hash(e.proof_hash) for e in entries]
```

---

## 7. Hash Collision Safety

### 7.1 Problem Statement

SHA-256 collisions are computationally infeasible but not impossible. Storage 
engine MUST handle the theoretical case.

### 7.2 Detection Strategy

```python
def detect_collision(new_record: PDORecord) -> bool:
    """Check if hash collision exists."""
    existing = get_by_pdo_hash(new_record.pdo_hash)
    
    if not existing:
        return False
    
    # Same hash, check if same content
    if serialize(existing) != serialize(new_record):
        alert_collision(new_record.pdo_hash)
        return True
    
    return False  # Duplicate, not collision
```

### 7.3 Mitigation

1. **Dual-Hash Verification** — Store SHA-256 + SHA-3 for critical records
2. **Content Fingerprinting** — Additional lightweight hash for collision detection
3. **Alert Pipeline** — Immediate notification on suspected collision

---

## 8. Blockchain Anchor Compatibility

### 8.1 Purpose

Anchoring PDO proof hashes to blockchain provides:
- External timestamp verification
- Tamper evidence
- Regulatory compliance

### 8.2 Anchor Flow

```
PDORecord.proof_hash
        │
        ▼
┌───────────────────┐
│  Batch Aggregator │ ← Collect multiple hashes
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Merkle Root      │ ← Compute tree root
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  On-Chain Anchor  │ ← Ethereum/Bitcoin tx
└─────────┬─────────┘
          │
          ▼
PDORecord.anchor_tx = "0x..."
PDORecord.anchor_chain = "ethereum"
```

### 8.3 Supported Chains

| Chain    | Status    | Anchor Contract                    |
|----------|-----------|-------------------------------------|
| Ethereum | Supported | GovernanceAnchor.sol               |
| Polygon  | Supported | GovernanceAnchor.sol (L2)          |
| Bitcoin  | Planned   | OP_RETURN                          |

---

## 9. Error Handling

### 9.1 Error Codes

| Code                   | Description                          | Recovery             |
|------------------------|--------------------------------------|----------------------|
| DUPLICATE_PROOF_HASH   | Proof hash already exists            | Use existing record  |
| MISSING_ARTIFACT       | Referenced artifact not found        | Store artifact first |
| HASH_COLLISION         | Different content, same hash         | Alert, investigate   |
| STORAGE_UNAVAILABLE    | Backend storage offline              | Retry with backoff   |
| INDEX_CORRUPT          | Index inconsistent with store        | Rebuild index        |

### 9.2 Fail-Closed Behavior

- NEVER return partial data
- NEVER proceed with unverified reads
- ALWAYS log failures with full context

---

## 10. Performance Considerations

### 10.1 Index Strategy

```yaml
primary_index:
  key: proof_hash
  type: hash_table
  lookup: O(1)

secondary_indices:
  - key: pdo_hash
    type: hash_table
  - key: pdo_id
    type: btree
  - key: created_at
    type: btree
```

### 10.2 Caching

```yaml
cache:
  enabled: true
  ttl_seconds: 300
  max_entries: 10000
  eviction: LRU
```

---

## 11. Changelog

| Version | Date       | Author  | Changes                        |
|---------|------------|---------|--------------------------------|
| 1.0.0   | 2025-12-26 | GID-07  | Initial specification          |

---

**END OF DOCUMENT — PDO_STORAGE_ENGINE_v1.md**
