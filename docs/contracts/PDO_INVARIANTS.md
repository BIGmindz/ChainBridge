# PDO Invariants Contract

Version: 1.0
Status: LOCKED
Classification: CONTRACT (Immutable)

Contract Owner: BENSON (GID-00)
PAC Reference: PAC-BENSON-TRUST-CONSOLIDATION-01
Effective Date: 2025-12-18

---

## 1. Purpose

This document defines the **immutable invariants** for PDO (Proof Decision Object) records in ChainBridge. These invariants are non-negotiable constraints that the system must enforce at all times.

**This is a contract, not a specification.** Violations are defects.

---

## 2. Canonical PDORecord Schema Reference

Source: `core/occ/schemas/pdo.py`

The canonical PDORecord schema is the single source of truth for PDO structure. This contract does not redefine the schema; it defines the invariants that constrain the schema's behavior.

---

## 3. Immutable Fields

### 3.1 Field Immutability Invariant

**INV-PDO-001: All PDORecord fields are immutable after write.**

Once a PDORecord is persisted, no field may be modified. This is enforced by:
- Pydantic `frozen=True` model configuration
- PDOStore rejecting all update operations
- No update schema exists by design

**Immutable Fields (exhaustive list):**

| Field | Type | Immutability Rule |
|-------|------|-------------------|
| `pdo_id` | UUID | Set at write time, never changes |
| `version` | string | Set at write time, never changes |
| `input_refs` | list[string] | Frozen at write time |
| `decision_ref` | string | Frozen at write time |
| `outcome_ref` | string | Frozen at write time |
| `outcome` | enum | Frozen at write time |
| `source_system` | enum | Frozen at write time |
| `actor` | string | Frozen at write time |
| `actor_type` | string | Frozen at write time |
| `recorded_at` | datetime | Set at write time (UTC), never changes |
| `previous_pdo_id` | UUID | null | Frozen at write time |
| `correlation_id` | string | null | Frozen at write time |
| `hash` | string | Computed at write time, never recomputed |
| `hash_algorithm` | string | Frozen at write time |
| `metadata` | dict | Frozen at write time |
| `tags` | list[string] | Frozen at write time |

---

## 4. Canonical Hash Inputs

### 4.1 Hash Determinism Invariant

**INV-PDO-002: PDO hash computation is deterministic and reproducible.**

The hash is computed from the following fields only, in canonical order:

```
Canonical Hash Inputs (sorted by key):
1. actor
2. actor_type
3. correlation_id
4. decision_ref
5. input_refs (sorted)
6. outcome
7. outcome_ref
8. pdo_id
9. previous_pdo_id
10. recorded_at
11. source_system
12. version
```

### 4.2 Hash Computation Algorithm

**INV-PDO-003: Hash algorithm is SHA-256 with canonical JSON serialization.**

```
canonical_data = {
    "pdo_id": str(pdo_id),
    "version": version,
    "input_refs": sorted(input_refs),
    "decision_ref": decision_ref,
    "outcome_ref": outcome_ref,
    "outcome": outcome.value,
    "source_system": source_system.value,
    "actor": actor,
    "actor_type": actor_type,
    "recorded_at": recorded_at.isoformat(),
    "previous_pdo_id": str(previous_pdo_id) if previous_pdo_id else None,
    "correlation_id": correlation_id
}

canonical_json = json.dumps(canonical_data, sort_keys=True, separators=(",", ":"))
hash = sha256(canonical_json.encode("utf-8")).hexdigest()
```

### 4.3 Hash Exclusions

**INV-PDO-004: The following fields are excluded from hash computation:**

- `hash` (self-referential)
- `hash_algorithm` (metadata about hash, not content)
- `metadata` (extensibility field, not core identity)
- `tags` (categorization, not core identity)

---

## 5. Prohibited Operations

### 5.1 Write Operations

**INV-PDO-005: The only permitted write operation is CREATE (append).**

| Operation | Permitted | Enforcement |
|-----------|-----------|-------------|
| CREATE | YES | PDOStore.create() |
| UPDATE | NO | Raises `PDOImmutabilityError` |
| DELETE | NO | Raises `PDOImmutabilityError` |
| UPSERT | NO | Not implemented |
| PATCH | NO | Not implemented |

### 5.2 No Update Schema

**INV-PDO-006: No PDOUpdate schema exists or will be created.**

The absence of an update schema is intentional. Any request to add update capability is a violation of this contract.

### 5.3 No Delete Operations

**INV-PDO-007: PDO records cannot be deleted under any circumstance.**

There is no soft delete, hard delete, archive, or expiration mechanism for PDOs. PDOs are permanent.

---

## 6. Corruption Conditions

A PDO is considered **corrupted** if any of the following conditions are detected:

### 6.1 Hash Mismatch

**CORRUPTION-001: Stored hash does not match computed hash.**

Detection: `PDORecord.verify_hash()` returns `False`
Response: Raise `PDOTamperDetectedError`

### 6.2 Invalid Schema

**CORRUPTION-002: Record fails PDORecord schema validation.**

Detection: Pydantic validation failure on load
Response: Raise validation error, halt load

### 6.3 Missing Required Fields

**CORRUPTION-003: Required fields are null or missing.**

Required fields (must not be null/empty):
- `pdo_id`
- `decision_ref`
- `outcome_ref`
- `outcome`
- `source_system`
- `actor`
- `recorded_at`
- `hash`

Detection: Pydantic validation
Response: Reject record

### 6.4 Invalid Timestamp

**CORRUPTION-004: Timestamp is malformed or not UTC.**

Detection: ISO 8601 parsing failure, missing timezone
Response: Reject record

### 6.5 Invalid UUID

**CORRUPTION-005: pdo_id or previous_pdo_id is malformed.**

Detection: UUID parsing failure
Response: Reject record

---

## 7. Store Behavior Invariants

### 7.1 Atomic Persistence

**INV-PDO-008: PDO writes are atomic.**

The PDOStore uses atomic write pattern:
1. Write to temporary file
2. Rename to target (atomic on POSIX)

Partial writes are not possible.

### 7.2 Hash Verification on Read

**INV-PDO-009: PDO hash is verified on read by default.**

`PDOStore.get()` verifies hash integrity unless explicitly disabled:
- `verify_integrity=True` (default): Verify hash, raise on mismatch
- `verify_integrity=False`: Skip verification (use only for diagnostics)

### 7.3 Hash Verification on Load

**INV-PDO-010: All PDOs are verified on store initialization.**

When PDOStore loads from disk, every record is hash-verified. Any tamper detection halts the load process entirely.

### 7.4 Thread Safety

**INV-PDO-011: All PDOStore operations are thread-safe.**

All read/write operations are protected by mutex lock.

---

## 8. Lineage Invariants

### 8.1 Lineage Chain Integrity

**INV-PDO-012: Lineage chains are immutable and append-only.**

If `previous_pdo_id` is set:
- The referenced PDO must exist
- The referenced PDO must have `recorded_at` earlier than this PDO
- The chain cannot be modified after creation

### 8.2 No Circular Lineage

**INV-PDO-013: Lineage chains cannot be circular.**

A PDO cannot reference itself or any PDO that eventually references it.

---

## 9. Timestamp Invariants

### 9.1 Write-Time Only

**INV-PDO-014: recorded_at is set at write time only.**

The `recorded_at` timestamp is set by PDOStore.create() at the moment of write. It cannot be:
- Provided by the caller
- Modified after write
- Back-dated or forward-dated

### 9.2 UTC Only

**INV-PDO-015: All timestamps are UTC with timezone suffix.**

Format: ISO 8601 with `+00:00` or `Z` suffix.

---

## 10. Enforcement Mechanisms

| Invariant | Enforcement Layer | Failure Mode |
|-----------|-------------------|--------------|
| Field immutability | Pydantic frozen model | TypeError on mutation |
| No updates | PDOStore (no method) | Method does not exist |
| No deletes | PDOStore (no method) | Method does not exist |
| Hash integrity | PDOStore.get() | PDOTamperDetectedError |
| Schema validation | Pydantic | ValidationError |
| Thread safety | threading.Lock | Blocking |

---

## 11. Contract Violations

Any of the following constitute a contract violation:

1. A PDO field is modified after write
2. A PDO is deleted
3. An update method is added to PDOStore
4. Hash verification is removed or made optional by default
5. A non-UTC timestamp is accepted
6. The hash algorithm is changed without versioning
7. The canonical hash inputs are modified without versioning

**Contract violations are defects. They must be reported, not silently handled.**

---

## 12. Document Control

| Field | Value |
|-------|-------|
| Contract Owner | BENSON (GID-00) |
| Created | 2025-12-18 |
| Status | LOCKED |
| PAC | PAC-BENSON-TRUST-CONSOLIDATION-01 |
| Source of Truth | `core/occ/schemas/pdo.py`, `core/occ/store/pdo_store.py` |
| Review Required | Any modification requires PAC approval |

---

**END OF CONTRACT — PDO_INVARIANTS.md**
