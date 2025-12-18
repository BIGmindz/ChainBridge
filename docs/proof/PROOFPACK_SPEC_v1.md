# ProofPack Specification v1

Version: 1.0
Status: DRAFT
Classification: SPECIFICATION (Design Only)

Authoring Agent:
- Agent: MIRA-R
- GID: GID-03
- Role: Research Lead — Proof Systems / Audit / Evidence Packaging
- Color: 🟣 Purple

PAC Reference: PAC-MIRA-PROOFPACK-01

---

## 1. Definition

A **ProofPack** is a deterministic, portable, audit-grade evidence bundle that:

1. Represents a single PDO (Proof Decision Object) and all linked evidence artifacts
2. Can be exported without interpretation or system access
3. Is verifiable offline using only the bundle contents and public algorithms
4. Preserves the immutability guarantees established at PDO write time
5. Contains no derived, summarized, or synthesized data

A ProofPack is an **export artifact**, not a storage format. It materializes evidence that already exists in ChainBridge systems into a form suitable for external parties.

---

## 2. Scope

### 2.1 What a ProofPack Contains

A ProofPack contains exactly:

| Artifact | Description | Source |
|----------|-------------|--------|
| PDO Record | The immutable Proof Decision Object | `core/occ/schemas/pdo.PDORecord` |
| Input Artifacts | Raw artifacts referenced by `input_refs` | As stored at PDO creation time |
| Decision Reference | The decision artifact referenced by `decision_ref` | As stored at PDO creation time |
| Outcome Reference | The outcome artifact referenced by `outcome_ref` | As stored at PDO creation time |
| Lineage Chain | Previous PDOs in chain (if `previous_pdo_id` is set) | PDO Store |
| Manifest | Hash manifest binding all artifacts | Generated at export time |

### 2.2 What a ProofPack Does NOT Contain

- Summaries or interpretations of evidence
- Computed analytics or derived metrics
- UI representations or formatting metadata
- Compliance assertions or legal conclusions
- Blockchain anchor references (external anchoring is a separate concern)
- Customer-specific redactions (handled at template layer, not ProofPack spec)

---

## 3. Deterministic Structure

### 3.1 Canonical File Layout

A ProofPack is a directory structure with the following canonical layout:

```
proofpack-{pdo_id}/
├── manifest.json           # Root manifest (required)
├── pdo/
│   └── record.json         # PDO record (required)
├── inputs/
│   └── {ref_hash}.json     # Input artifacts (0..n)
├── decision/
│   └── {ref_hash}.json     # Decision artifact (required)
├── outcome/
│   └── {ref_hash}.json     # Outcome artifact (required)
├── lineage/
│   └── {pdo_id}.json       # Previous PDOs in chain (0..n)
└── VERIFICATION.txt        # Human-readable verification instructions
```

### 3.2 Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Root directory | `proofpack-{pdo_id}` | `proofpack-a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| Artifact files | `{sha256_first_16_chars}.json` | `3a7f92e1b4c8d5f0.json` |
| Lineage files | `{pdo_id}.json` | `prev-a1b2c3d4-....json` |

### 3.3 Ordering Rules

1. All JSON objects use **lexicographic key ordering** (sorted alphabetically)
2. Arrays maintain their original order (order is semantically meaningful)
3. Lineage files are ordered by `recorded_at` timestamp (oldest first)
4. Input artifacts are ordered by their position in `input_refs` array

### 3.4 Encoding

- Character encoding: UTF-8 (no BOM)
- JSON separators: `(",", ":")` (compact, no whitespace)
- Timestamps: ISO 8601 with UTC timezone suffix (`Z`)
- UUIDs: Lowercase with hyphens (`a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
- Hashes: Lowercase hexadecimal

---

## 4. Manifest Schema

### 4.1 Root Manifest (`manifest.json`)

```json
{
  "proofpack_version": "1.0",
  "pdo_id": "{uuid}",
  "exported_at": "{iso8601_utc}",
  "exporter": {
    "system": "chainbridge",
    "component": "proofpack-exporter",
    "version": "{semver}"
  },
  "contents": {
    "pdo": {
      "path": "pdo/record.json",
      "hash": "{sha256}",
      "hash_algorithm": "sha256"
    },
    "inputs": [
      {
        "ref": "{original_ref}",
        "path": "inputs/{hash}.json",
        "hash": "{sha256}",
        "hash_algorithm": "sha256"
      }
    ],
    "decision": {
      "ref": "{decision_ref}",
      "path": "decision/{hash}.json",
      "hash": "{sha256}",
      "hash_algorithm": "sha256"
    },
    "outcome": {
      "ref": "{outcome_ref}",
      "path": "outcome/{hash}.json",
      "hash": "{sha256}",
      "hash_algorithm": "sha256"
    },
    "lineage": [
      {
        "pdo_id": "{uuid}",
        "path": "lineage/{pdo_id}.json",
        "hash": "{sha256}",
        "hash_algorithm": "sha256"
      }
    ]
  },
  "integrity": {
    "manifest_hash": "{sha256}",
    "hash_algorithm": "sha256",
    "hash_inputs": ["proofpack_version", "pdo_id", "exported_at", "contents"]
  }
}
```

### 4.2 Manifest Hash Computation

The `manifest_hash` is computed as:

1. Construct canonical JSON of manifest **excluding** the `integrity` block
2. Compute SHA-256 of the UTF-8 encoded canonical JSON bytes
3. Encode as lowercase hexadecimal

Pseudocode:
```
manifest_data = {proofpack_version, pdo_id, exported_at, exporter, contents}
canonical_json = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"))
manifest_hash = sha256(canonical_json.encode("utf-8")).hexdigest()
```

---

## 5. Artifact Schemas

### 5.1 PDO Record (`pdo/record.json`)

The PDO record is serialized exactly as stored, with no transformation.

Required fields (from `PDORecord` schema):
```json
{
  "pdo_id": "{uuid}",
  "version": "1.0",
  "input_refs": ["{ref}", ...],
  "decision_ref": "{ref}",
  "outcome_ref": "{ref}",
  "outcome": "approved|rejected|deferred|escalated",
  "source_system": "gateway|occ|chainiq|chainpay|manual",
  "actor": "{actor_identifier}",
  "actor_type": "agent|human|system",
  "recorded_at": "{iso8601_utc}",
  "previous_pdo_id": "{uuid}|null",
  "correlation_id": "{string}|null",
  "hash": "{sha256}",
  "hash_algorithm": "sha256",
  "metadata": {},
  "tags": []
}
```

### 5.2 Input Artifacts (`inputs/{hash}.json`)

Each input artifact is stored as:
```json
{
  "ref": "{original_ref_from_input_refs}",
  "artifact_type": "{type_identifier}",
  "content": { ... },
  "content_hash": "{sha256}",
  "acquired_at": "{iso8601_utc}|null"
}
```

If an input artifact cannot be resolved, the file contains:
```json
{
  "ref": "{original_ref}",
  "artifact_type": "unresolved",
  "content": null,
  "content_hash": null,
  "resolution_status": "not_found|access_denied|expired",
  "resolution_attempted_at": "{iso8601_utc}"
}
```

### 5.3 Decision Artifact (`decision/{hash}.json`)

```json
{
  "ref": "{decision_ref}",
  "artifact_type": "decision",
  "content": { ... },
  "content_hash": "{sha256}",
  "decision_timestamp": "{iso8601_utc}"
}
```

### 5.4 Outcome Artifact (`outcome/{hash}.json`)

```json
{
  "ref": "{outcome_ref}",
  "artifact_type": "outcome",
  "content": { ... },
  "content_hash": "{sha256}",
  "outcome_timestamp": "{iso8601_utc}"
}
```

### 5.5 Lineage PDOs (`lineage/{pdo_id}.json`)

Each lineage PDO is a full `PDORecord` serialization, identical to [5.1](#51-pdo-record-pdorecordjson).

---

## 6. Integrity & Verification Model

### 6.1 Hash Verification Algorithm

To verify a ProofPack offline:

**Step 1: Verify PDO Record Hash**
```
1. Read pdo/record.json
2. Extract "hash" field from record
3. Compute hash using PDORecord.compute_hash() algorithm
4. Compare computed hash to stored hash
5. If mismatch → FAIL: "PDO record tampered"
```

**Step 2: Verify Artifact Hashes**
```
For each artifact in contents.{inputs, decision, outcome, lineage}:
    1. Read artifact file at specified path
    2. Compute SHA-256 of raw file bytes
    3. Compare to hash in manifest
    4. If mismatch → FAIL: "Artifact {path} tampered"
```

**Step 3: Verify Manifest Hash**
```
1. Read manifest.json
2. Extract integrity.manifest_hash
3. Reconstruct manifest_data (excluding integrity block)
4. Compute SHA-256 of canonical JSON
5. Compare to stored manifest_hash
6. If mismatch → FAIL: "Manifest tampered"
```

**Step 4: Verify Lineage Chain**
```
For each lineage PDO (oldest to newest):
    1. Verify PDO hash (Step 1)
    2. Verify previous_pdo_id matches prior PDO's pdo_id
    3. Verify recorded_at is after prior PDO's recorded_at
    4. If chain broken → FAIL: "Lineage chain invalid"
```

**Step 5: Verify Reference Consistency**
```
1. Verify manifest.pdo_id matches pdo/record.json.pdo_id
2. Verify manifest.contents.inputs refs match pdo.input_refs
3. Verify manifest.contents.decision ref matches pdo.decision_ref
4. Verify manifest.contents.outcome ref matches pdo.outcome_ref
5. If mismatch → FAIL: "Reference inconsistency"
```

### 6.2 Verification Outcomes

| Outcome | Meaning |
|---------|---------|
| `VALID` | All hashes match, all references consistent, lineage intact |
| `INVALID_PDO_HASH` | PDO record hash does not match computed hash |
| `INVALID_ARTIFACT_HASH` | One or more artifact hashes do not match |
| `INVALID_MANIFEST_HASH` | Manifest hash does not match computed hash |
| `INVALID_LINEAGE` | Lineage chain is broken or inconsistent |
| `INVALID_REFERENCES` | Manifest references do not match PDO references |
| `INCOMPLETE` | Required artifacts are missing |

### 6.3 Verification Requirements

- Verification **MUST NOT** require network access
- Verification **MUST NOT** require ChainBridge systems to be online
- Verification **MUST** use only:
  - Standard SHA-256 implementation
  - Standard JSON parser
  - Standard UTF-8 encoding
  - The ProofPack contents itself

---

## 7. Provenance & Attribution

### 7.1 Actor Attribution

Every PDO records:

| Field | Description | Example |
|-------|-------------|---------|
| `actor` | Identifier of actor that created the PDO | `GID-01`, `user:jsmith`, `system:chainpay` |
| `actor_type` | Classification of actor | `agent`, `human`, `system` |

Actor values are opaque strings. No anonymization is permitted.

### 7.2 Source System Attribution

| Value | Description |
|-------|-------------|
| `gateway` | ChainBridge API Gateway |
| `occ` | Operator Control Center |
| `chainiq` | Risk scoring service |
| `chainpay` | Payment orchestration service |
| `manual` | Manual/human-initiated |

### 7.3 Timestamp Semantics

| Timestamp | Location | Semantics |
|-----------|----------|-----------|
| `recorded_at` | PDO Record | UTC time when PDO was committed to store (write-time) |
| `exported_at` | Manifest | UTC time when ProofPack was generated |
| `acquired_at` | Input artifacts | UTC time when input data was captured (may be null) |
| `decision_timestamp` | Decision artifact | UTC time of decision (may differ from recorded_at) |
| `outcome_timestamp` | Outcome artifact | UTC time of outcome (may differ from recorded_at) |

All timestamps are:
- UTC timezone
- ISO 8601 format
- Precision to milliseconds minimum
- Immutable after write

### 7.4 Correlation Handling

The `correlation_id` field links related operations across systems.

Rules:
- If present, `correlation_id` is included in the PDO record
- ProofPacks do not aggregate by correlation (one ProofPack = one PDO)
- Correlation relationships are preserved via `previous_pdo_id` lineage

---

## 8. Non-Claims (Mandatory)

### 8.1 What ProofPacks Do NOT Assert

| Non-Claim | Clarification |
|-----------|---------------|
| Correctness of decision | ProofPack proves what decision was recorded, not that the decision was correct |
| Completeness of inputs | ProofPack contains inputs that were referenced; it does not assert no other inputs existed |
| Legal compliance | ProofPack is evidence, not a compliance certification |
| Authorization validity | ProofPack records the actor; it does not validate the actor had authority |
| External anchoring | ProofPack contains no blockchain or ledger anchors (external anchoring is out of scope) |
| Data accuracy | ProofPack preserves data as recorded; it does not validate the data was accurate |
| Timestamp authenticity | Timestamps reflect system time at write; ProofPack does not provide trusted timestamping |

### 8.2 What Verification Does NOT Prove

| Non-Proof | Clarification |
|-----------|---------------|
| Original authenticity | Verification proves the ProofPack has not been modified since export; it does not prove the original data was authentic |
| Chain of custody | Verification does not prove who had access to the ProofPack or how it was transmitted |
| System integrity | Verification does not prove ChainBridge systems were operating correctly at decision time |
| Actor identity | Verification does not prove the recorded actor was who they claimed to be |

### 8.3 What Is Outside Scope

| Out of Scope | Rationale |
|--------------|-----------|
| External anchoring | Blockchain/ledger anchoring is a separate layer |
| Customer-specific templates | Template-based redaction is governance policy, not ProofPack spec |
| Signature verification | Digital signatures require PKI infrastructure not defined here |
| Encryption | ProofPacks are plaintext evidence bundles |
| Compression | Archive format (zip, tar) is a packaging concern |
| Delivery mechanism | How ProofPacks are transmitted is out of scope |

---

## 9. Verification Instructions (`VERIFICATION.txt`)

Every ProofPack includes a human-readable verification file:

```
PROOFPACK VERIFICATION INSTRUCTIONS
===================================

This ProofPack contains audit evidence for PDO: {pdo_id}
Exported: {exported_at} UTC

VERIFICATION STEPS:

1. PDO Record Hash Verification
   - Open: pdo/record.json
   - Locate the "hash" field
   - Compute SHA-256 of the canonical PDO content (see Section 6.1)
   - Compare to the stored hash value

2. Artifact Hash Verification
   - Open: manifest.json
   - For each entry in "contents", verify:
     - Read the file at the specified "path"
     - Compute SHA-256 of the file bytes
     - Compare to the "hash" value in manifest

3. Manifest Hash Verification
   - Open: manifest.json
   - Locate integrity.manifest_hash
   - Reconstruct manifest data (exclude integrity block)
   - Compute SHA-256 of canonical JSON
   - Compare to manifest_hash

4. Lineage Verification (if applicable)
   - For each file in lineage/:
     - Verify PDO hash as in Step 1
     - Verify chain continuity via previous_pdo_id

HASH ALGORITHM: SHA-256
ENCODING: UTF-8
JSON FORMAT: Compact, sorted keys, separators (",", ":")

If all hashes match, the ProofPack is VALID.
Any mismatch indicates tampering or corruption.

This verification can be performed offline without ChainBridge access.
```

---

## 10. Schema Version

### 10.1 Version Field

The `proofpack_version` field in the manifest identifies the specification version.

| Version | Status | Changes |
|---------|--------|---------|
| `1.0` | DRAFT | Initial specification |

### 10.2 Compatibility Rules

- Major version changes (e.g., `1.x` → `2.x`) may break verification
- Minor version changes (e.g., `1.0` → `1.1`) must be backward compatible
- Verifiers must check `proofpack_version` before attempting verification

---

## 11. Open Questions

| ID | Question | Impact |
|----|----------|--------|
| OQ-1 | Should ProofPacks support optional digital signatures? | Requires PKI infrastructure definition |
| OQ-2 | Should lineage be bounded (e.g., max 100 PDOs)? | Affects export size for long chains |
| OQ-3 | Should unresolved artifacts be included or omitted? | Completeness vs. export success |
| OQ-4 | Should metadata be included in hash computation? | Affects hash determinism |

---

## 12. Assumptions

| ID | Assumption | Justification |
|----|------------|---------------|
| A-1 | PDO records exist and are accessible at export time | Export is a pull operation from live store |
| A-2 | Input artifacts are stored and resolvable by ref | Refs must be dereferenceable URIs or IDs |
| A-3 | SHA-256 is sufficient for integrity verification | Industry standard, widely available |
| A-4 | UTF-8 encoding is universal | Standard encoding for JSON |
| A-5 | Auditors have JSON parsing capability | Reasonable tooling assumption |

---

## 13. Risks & Ambiguities

| ID | Risk/Ambiguity | Mitigation |
|----|----------------|------------|
| R-1 | Large lineage chains may produce oversized ProofPacks | Define bounded export options |
| R-2 | Artifact resolution may fail for deleted/expired data | Include resolution status in artifact file |
| R-3 | Clock skew may affect timestamp ordering | Use recorded_at from store, not export time |
| R-4 | JSON serialization differences across implementations | Mandate canonical JSON specification |
| R-5 | Hash collision (theoretical) | SHA-256 collision resistance is sufficient |

---

## 14. Acceptance Criteria

This specification is accepted only if:

- [ ] ProofPack contents are exhaustively defined (Sections 2, 5)
- [ ] Structure is deterministic (Section 3)
- [ ] Verification can be performed offline (Section 6)
- [ ] No interpretive language exists in artifact schemas
- [ ] Non-claims are explicit and unambiguous (Section 8)
- [ ] Specification can be handed to an auditor without explanation

---

## Document Control

| Field | Value |
|-------|-------|
| Author | MIRA-R (GID-03) |
| Created | 2025-12-18 |
| Status | DRAFT |
| PAC | PAC-MIRA-PROOFPACK-01 |
| Review Required | Yes |
| Implementation PAC | TBD (future) |
