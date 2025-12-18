# ProofPack Invariants Contract

Version: 1.0
Status: LOCKED
Classification: CONTRACT (Immutable)

Contract Owner: BENSON (GID-00)
PAC Reference: PAC-BENSON-TRUST-CONSOLIDATION-01
Effective Date: 2025-12-18

---

## 1. Purpose

This document defines the **immutable invariants** for ProofPack evidence bundles in ChainBridge. These invariants are non-negotiable constraints that the system must enforce at all times.

**This is a contract, not a specification.** Violations are defects.

Specification Reference: `docs/proof/PROOFPACK_SPEC_v1.md`

---

## 2. Artifact Set Invariants

### 2.1 Fixed Artifact Set

**INV-PP-001: The ProofPack artifact set is fixed and cannot be extended.**

A ProofPack contains exactly these artifacts (no more, no less):

| Artifact | Path | Required | Description |
|----------|------|----------|-------------|
| Manifest | `manifest.json` | YES | Root manifest binding all artifacts |
| PDO Record | `pdo/record.json` | YES | The immutable PDO |
| Input Artifacts | `inputs/{hash}.json` | 0..n | Referenced input artifacts |
| Decision Artifact | `decision/{hash}.json` | YES | The decision artifact |
| Outcome Artifact | `outcome/{hash}.json` | YES | The outcome artifact |
| Lineage PDOs | `lineage/{pdo_id}.json` | 0..n | Previous PDOs in chain |
| Verification | `VERIFICATION.txt` | YES | Human-readable instructions |

### 2.2 No Additional Artifacts

**INV-PP-002: No artifacts may be added to a ProofPack beyond the defined set.**

Prohibited additions:
- Summary files
- Analytics or metrics
- UI assets or formatting
- Compliance assertions
- External anchoring references
- Customer-specific redactions
- Derived or computed data

### 2.3 No Artifact Removal

**INV-PP-003: Required artifacts cannot be omitted from a ProofPack.**

A ProofPack missing any required artifact is invalid.

---

## 3. Canonical Ordering Invariants

### 3.1 JSON Key Ordering

**INV-PP-004: All JSON objects use lexicographic (alphabetical) key ordering.**

Keys must be sorted alphabetically when serializing JSON. This is non-negotiable for hash determinism.

### 3.2 Array Ordering

**INV-PP-005: Arrays maintain their semantic order.**

- `input_refs`: Order from PDO is preserved
- `contents.inputs`: Order matches `input_refs`
- `lineage`: Ordered by `recorded_at` (oldest first)

### 3.3 Lineage Ordering

**INV-PP-006: Lineage files are ordered by recorded_at timestamp, oldest first.**

The lineage chain must be traversable from oldest ancestor to the current PDO.

---

## 4. Canonical Serialization Invariants

### 4.1 JSON Serialization

**INV-PP-007: JSON serialization uses compact format with specific separators.**

```
Separator rule: (",", ":")  (no spaces)
```

Example:
```json
{"key":"value","number":123}
```

NOT:
```json
{ "key": "value", "number": 123 }
```

### 4.2 Character Encoding

**INV-PP-008: All files are UTF-8 encoded without BOM.**

- Encoding: UTF-8
- BOM: Not permitted
- Line endings: LF only (no CRLF)

### 4.3 Timestamp Format

**INV-PP-009: All timestamps are ISO 8601 with UTC timezone suffix.**

Format: `YYYY-MM-DDTHH:MM:SS.sssZ` or `YYYY-MM-DDTHH:MM:SS.sss+00:00`

Examples:
- `2025-12-18T14:30:00.000Z` ✓
- `2025-12-18T14:30:00Z` ✓
- `2025-12-18T14:30:00` ✗ (missing timezone)
- `2025-12-18 14:30:00` ✗ (wrong format)

### 4.4 UUID Format

**INV-PP-010: All UUIDs are lowercase with hyphens.**

Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

NOT: `A1B2C3D4-E5F6-7890-ABCD-EF1234567890` (uppercase)

### 4.5 Hash Format

**INV-PP-011: All hash values are lowercase hexadecimal.**

Example: `3a7f92e1b4c8d5f0a9e2c3d4b5f6a7e8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4`

NOT: `3A7F92E1B4C8D5F0...` (uppercase)

---

## 5. Manifest Binding Invariants

### 5.1 PDO ID Binding

**INV-PP-012: Manifest pdo_id must exactly match pdo/record.json pdo_id.**

```
manifest.json.pdo_id == pdo/record.json.pdo_id
```

### 5.2 Input Reference Binding

**INV-PP-013: Manifest input refs must exactly match PDO input_refs.**

```
manifest.contents.inputs[].ref == pdo.input_refs[]
```

Order must be preserved.

### 5.3 Decision Reference Binding

**INV-PP-014: Manifest decision ref must exactly match PDO decision_ref.**

```
manifest.contents.decision.ref == pdo.decision_ref
```

### 5.4 Outcome Reference Binding

**INV-PP-015: Manifest outcome ref must exactly match PDO outcome_ref.**

```
manifest.contents.outcome.ref == pdo.outcome_ref
```

### 5.5 Path Binding

**INV-PP-016: All manifest paths must resolve to actual files.**

Every `path` in the manifest must point to a file that exists in the ProofPack. Missing files invalidate the ProofPack.

### 5.6 Hash Binding

**INV-PP-017: All manifest hashes must match computed hashes of referenced files.**

For each artifact in manifest:
```
sha256(file_bytes) == manifest.hash
```

---

## 6. Verification Algorithm Invariants

### 6.1 Algorithm Requirement

**INV-PP-018: The verification algorithm is SHA-256 only.**

No other hash algorithms are permitted for ProofPack verification.

### 6.2 Algorithm Availability

**INV-PP-019: Verification requires only standard cryptographic primitives.**

Required primitives:
- SHA-256 hash function
- UTF-8 encoder
- JSON parser

No proprietary or ChainBridge-specific components required.

### 6.3 Offline Verification

**INV-PP-020: Verification must be possible without network access.**

A ProofPack must be verifiable using only:
- The ProofPack contents
- Standard cryptographic libraries
- The verification algorithm (documented in VERIFICATION.txt)

### 6.4 Verification Order

**INV-PP-021: Verification follows a fixed step order.**

1. Verify PDO record hash
2. Verify artifact file hashes
3. Verify manifest hash
4. Verify lineage chain (if applicable)
5. Verify reference consistency

Order cannot be changed. Early failure halts subsequent steps.

---

## 7. Content Invariants

### 7.1 PDO Record Integrity

**INV-PP-022: The PDO record in a ProofPack is an exact copy of the stored PDO.**

No transformation, filtering, or summarization is permitted.

### 7.2 Artifact Immutability

**INV-PP-023: Artifacts are stored exactly as they existed at PDO creation time.**

Artifacts must not be:
- Modified
- Transformed
- Summarized
- Redacted (at the ProofPack spec level)

### 7.3 No Derived Data

**INV-PP-024: ProofPacks contain no derived, computed, or synthesized data.**

Prohibited:
- Summaries
- Analytics
- Interpretations
- Compliance conclusions
- Risk assessments computed at export time

### 7.4 No Future Claims

**INV-PP-025: ProofPacks make no claims about future events or conditions.**

A ProofPack represents evidence at a point in time. It does not assert:
- Future validity
- Continued compliance
- Ongoing accuracy

---

## 8. Naming Invariants

### 8.1 Root Directory

**INV-PP-026: Root directory is named `proofpack-{pdo_id}`.**

Example: `proofpack-a1b2c3d4-e5f6-7890-abcd-ef1234567890`

### 8.2 Artifact File Names

**INV-PP-027: Artifact files are named by SHA-256 hash prefix (16 chars) + .json.**

Example: `3a7f92e1b4c8d5f0.json`

### 8.3 Lineage File Names

**INV-PP-028: Lineage files are named by PDO ID + .json.**

Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890.json`

---

## 9. Version Invariants

### 9.1 Version Field Required

**INV-PP-029: The proofpack_version field is required in manifest.json.**

### 9.2 Version Compatibility

**INV-PP-030: Major version changes may break verification.**

- `1.x` → `1.y`: Backward compatible
- `1.x` → `2.x`: May break verification

### 9.3 Current Version

**INV-PP-031: The current locked version is 1.0.**

Version 1.0 is the canonical version. Changes require a new PAC.

---

## 10. Prohibited Operations

### 10.1 No Post-Export Modification

**INV-PP-032: ProofPacks cannot be modified after export.**

Once a ProofPack is generated, it is immutable. Any modification invalidates the manifest hash.

### 10.2 No Selective Export

**INV-PP-033: ProofPacks cannot exclude required artifacts.**

All required artifacts must be present. There is no "partial" or "summary" mode.

### 10.3 No Aggregation

**INV-PP-034: One ProofPack = One PDO.**

ProofPacks do not aggregate multiple PDOs. Correlation relationships are expressed via lineage chains.

---

## 11. Corruption Conditions

A ProofPack is considered **corrupted** if:

| Condition | Detection |
|-----------|-----------|
| Missing manifest.json | File existence check |
| Missing required artifact | Path resolution failure |
| PDO hash mismatch | PDO.verify_hash() fails |
| Artifact hash mismatch | sha256(file) != manifest.hash |
| Manifest hash mismatch | Recompute vs stored |
| Reference inconsistency | Manifest refs != PDO refs |
| Lineage chain broken | previous_pdo_id not found |
| Invalid JSON | Parse failure |
| Invalid timestamp | ISO 8601 parse failure |
| Invalid UUID | UUID parse failure |

---

## 12. Contract Violations

Any of the following constitute a contract violation:

1. An artifact type is added to the ProofPack structure
2. JSON serialization format is changed
3. Hash algorithm is changed without version bump
4. Offline verification becomes impossible
5. Reference binding rules are relaxed
6. Derived data is added to ProofPacks
7. Multiple PDOs are aggregated into one ProofPack

**Contract violations are defects. They must be reported, not silently handled.**

---

## 13. Document Control

| Field | Value |
|-------|-------|
| Contract Owner | BENSON (GID-00) |
| Created | 2025-12-18 |
| Status | LOCKED |
| PAC | PAC-BENSON-TRUST-CONSOLIDATION-01 |
| Specification Reference | `docs/proof/PROOFPACK_SPEC_v1.md` |
| Review Required | Any modification requires PAC approval |

---

**END OF CONTRACT — PROOFPACK_INVARIANTS.md**
