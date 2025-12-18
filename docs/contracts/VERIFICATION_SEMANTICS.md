# Verification Semantics Contract

Version: 1.0
Status: LOCKED
Classification: CONTRACT (Immutable)

Contract Owner: BENSON (GID-00)
PAC Reference: PAC-BENSON-TRUST-CONSOLIDATION-01
Effective Date: 2025-12-18

---

## 1. Purpose

This document defines the **verification semantics** for PDO and ProofPack integrity verification in ChainBridge. These semantics are non-negotiable and govern how verification results are interpreted and acted upon.

**This is a contract, not a specification.** Ambiguity is a defect.

---

## 2. Verification Outcome Model

### 2.1 Binary Outcomes Only

**SEM-VER-001: Verification produces exactly two outcomes: PASS or FAIL.**

There are no intermediate states:
- No warnings
- No soft failures
- No "pass with exceptions"
- No "conditional pass"

| Outcome | Meaning |
|---------|---------|
| PASS | All verification checks succeeded |
| FAIL | One or more verification checks failed |

### 2.2 No Warning State

**SEM-VER-002: Warnings are not a verification outcome.**

Verification does not produce warnings. Any anomaly that is not a failure is not reported. Any anomaly that affects integrity is a failure.

### 2.3 Fail-Fast Behavior

**SEM-VER-003: Verification halts on first failure.**

When a verification check fails:
1. Record the failure reason
2. Halt further verification
3. Return FAIL with reason

Verification does not continue to find "all" failures.

---

## 3. PDO Verification Semantics

### 3.1 PDO Hash Verification

**SEM-VER-004: PDO hash verification compares stored hash to computed hash.**

```
computed_hash = PDORecord.compute_hash()
stored_hash = PDORecord.hash

if computed_hash == stored_hash:
    PASS
else:
    FAIL: "PDO hash mismatch"
```

### 3.2 Conditions That Must Fail

**SEM-VER-005: The following conditions always produce FAIL for PDO verification:**

| Condition | Failure Reason |
|-----------|----------------|
| `hash` field is empty | "PDO hash is empty" |
| `hash` field is null | "PDO hash is null" |
| Computed hash ≠ stored hash | "PDO hash mismatch: expected {stored}, computed {computed}" |
| Required field is null | "Required field {field} is null" |
| Required field is missing | "Required field {field} is missing" |
| Invalid UUID format | "Invalid UUID format for {field}" |
| Invalid timestamp format | "Invalid timestamp format for {field}" |
| Invalid enum value | "Invalid {enum_type} value: {value}" |

### 3.3 PDO Verification Does Not Validate

**SEM-VER-006: PDO verification does not validate the following:**

| Not Validated | Reason |
|---------------|--------|
| Correctness of decision | Verification proves integrity, not correctness |
| Actor authorization | Verification proves who acted, not if they were authorized |
| Input completeness | Verification proves what was recorded, not what should have been recorded |
| Timestamp accuracy | Verification proves what was recorded, not that clocks were correct |

---

## 4. ProofPack Verification Semantics

### 4.1 Verification Step Order

**SEM-VER-007: ProofPack verification follows a fixed step order.**

```
Step 1: Verify PDO record hash
Step 2: Verify artifact file hashes (all)
Step 3: Verify manifest hash
Step 4: Verify lineage chain (if applicable)
Step 5: Verify reference consistency
```

Each step must pass before the next step executes.

### 4.2 Step 1: PDO Record Hash Verification

**SEM-VER-008: PDO record hash verification follows PDO verification semantics.**

Read `pdo/record.json`, apply SEM-VER-004.

Failure reason: `"PDO record hash mismatch"`

### 4.3 Step 2: Artifact Hash Verification

**SEM-VER-009: Each artifact file hash is verified against manifest hash.**

```
For each artifact in manifest.contents:
    file_bytes = read_binary(artifact.path)
    computed_hash = sha256(file_bytes).hexdigest()

    if computed_hash != artifact.hash:
        FAIL: "Artifact {path} hash mismatch"
```

All artifacts must be verified. Any mismatch is FAIL.

### 4.4 Step 3: Manifest Hash Verification

**SEM-VER-010: Manifest hash is verified by recomputing from manifest content.**

```
manifest_data = {
    proofpack_version,
    pdo_id,
    exported_at,
    exporter,
    contents
}
# Note: integrity block is excluded

canonical_json = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"))
computed_hash = sha256(canonical_json.encode("utf-8")).hexdigest()

if computed_hash != manifest.integrity.manifest_hash:
    FAIL: "Manifest hash mismatch"
```

### 4.5 Step 4: Lineage Chain Verification

**SEM-VER-011: Lineage chain verification validates chain integrity.**

```
For each lineage PDO (oldest to newest):
    1. Verify PDO hash (SEM-VER-004)
    2. Verify previous_pdo_id matches prior PDO's pdo_id
    3. Verify recorded_at > prior PDO's recorded_at

    if any check fails:
        FAIL: "Lineage chain broken at {pdo_id}"
```

### 4.6 Step 5: Reference Consistency Verification

**SEM-VER-012: Reference consistency verifies manifest references match PDO references.**

```
Verify: manifest.pdo_id == pdo.pdo_id
Verify: manifest.contents.inputs[].ref == pdo.input_refs[] (ordered)
Verify: manifest.contents.decision.ref == pdo.decision_ref
Verify: manifest.contents.outcome.ref == pdo.outcome_ref

if any mismatch:
    FAIL: "Reference inconsistency: {field}"
```

---

## 5. Conditions That Must Fail

### 5.1 ProofPack Structure Failures

**SEM-VER-013: The following structural conditions always produce FAIL:**

| Condition | Failure Reason |
|-----------|----------------|
| Missing `manifest.json` | "Missing manifest.json" |
| Missing `pdo/record.json` | "Missing pdo/record.json" |
| Missing `decision/{hash}.json` | "Missing decision artifact" |
| Missing `outcome/{hash}.json` | "Missing outcome artifact" |
| Missing `VERIFICATION.txt` | "Missing VERIFICATION.txt" |
| Missing referenced input artifact | "Missing input artifact: {ref}" |
| Missing referenced lineage PDO | "Missing lineage PDO: {pdo_id}" |

### 5.2 Hash Failures

**SEM-VER-014: The following hash conditions always produce FAIL:**

| Condition | Failure Reason |
|-----------|----------------|
| PDO hash mismatch | "PDO record hash mismatch" |
| Artifact hash mismatch | "Artifact {path} hash mismatch" |
| Manifest hash mismatch | "Manifest hash mismatch" |
| Empty hash field | "Hash field is empty" |
| Null hash field | "Hash field is null" |
| Non-hexadecimal hash | "Invalid hash format: {value}" |
| Wrong hash length | "Invalid hash length: expected 64, got {length}" |

### 5.3 Reference Failures

**SEM-VER-015: The following reference conditions always produce FAIL:**

| Condition | Failure Reason |
|-----------|----------------|
| pdo_id mismatch | "Manifest pdo_id does not match PDO" |
| input_refs mismatch | "Manifest inputs do not match PDO input_refs" |
| decision_ref mismatch | "Manifest decision ref does not match PDO" |
| outcome_ref mismatch | "Manifest outcome ref does not match PDO" |
| Path does not exist | "Artifact path does not exist: {path}" |

### 5.4 Lineage Failures

**SEM-VER-016: The following lineage conditions always produce FAIL:**

| Condition | Failure Reason |
|-----------|----------------|
| Lineage PDO hash mismatch | "Lineage PDO {pdo_id} hash mismatch" |
| Chain discontinuity | "Lineage chain broken: {pdo_id} does not reference {expected_id}" |
| Timestamp ordering violation | "Lineage timestamp violation: {pdo_id} recorded before predecessor" |
| Circular reference | "Lineage contains circular reference" |
| Missing predecessor | "Lineage predecessor not found: {pdo_id}" |

---

## 6. Conditions That Must Halt Downstream Systems

### 6.1 Tamper Detection Halts Processing

**SEM-VER-017: Any tamper detection must halt downstream processing.**

When `PDOTamperDetectedError` is raised:
1. Halt all operations using the affected PDO
2. Do not propagate the PDO to other systems
3. Do not include the PDO in exports
4. Log the tamper detection event

### 6.2 Invalid ProofPack Halts Export

**SEM-VER-018: An invalid ProofPack must not be exported or transmitted.**

When ProofPack verification fails:
1. Do not transmit the ProofPack
2. Do not archive the ProofPack
3. Log the verification failure
4. Return error to requester

### 6.3 Store Load Halts on Corruption

**SEM-VER-019: PDOStore load halts entirely if any record is corrupted.**

When a corrupted PDO is detected during store initialization:
1. Halt the load process
2. Do not load any records (not even valid ones)
3. Log the corruption
4. Require manual intervention

---

## 7. Verification Result Schema

### 7.1 Result Structure

**SEM-VER-020: Verification results follow a canonical structure.**

```json
{
    "outcome": "PASS" | "FAIL",
    "verified_at": "{iso8601_utc}",
    "subject": {
        "type": "pdo" | "proofpack",
        "id": "{identifier}"
    },
    "failure": {
        "step": "{step_name}",
        "reason": "{failure_reason}",
        "details": {}
    } | null
}
```

### 7.2 Failure Detail Requirements

**SEM-VER-021: Failure results must include sufficient detail for diagnosis.**

Required failure details:
- `step`: Which verification step failed
- `reason`: Human-readable failure reason
- `details`: Machine-readable failure context

Example:
```json
{
    "outcome": "FAIL",
    "verified_at": "2025-12-18T14:30:00.000Z",
    "subject": {
        "type": "pdo",
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    },
    "failure": {
        "step": "hash_verification",
        "reason": "PDO hash mismatch",
        "details": {
            "expected_hash": "3a7f92e1...",
            "computed_hash": "9c8d7e6f..."
        }
    }
}
```

---

## 8. What Verification Proves

### 8.1 Verification Proves

**SEM-VER-022: Successful verification proves the following:**

| Proof | Description |
|-------|-------------|
| Integrity | The data has not been modified since hash was computed |
| Completeness | All required artifacts are present |
| Consistency | References between artifacts are valid |
| Lineage | The PDO chain is intact (if applicable) |

### 8.2 Verification Does Not Prove

**SEM-VER-023: Verification does not prove the following:**

| Non-Proof | Clarification |
|-----------|---------------|
| Correctness | Data may be intact but incorrect |
| Authorization | Actor may be recorded but unauthorized |
| Authenticity | Original data may have been fraudulent |
| Completeness of inputs | Inputs may be incomplete |
| Clock accuracy | Timestamps may be from incorrect clocks |
| System integrity | System may have been compromised at decision time |

---

## 9. Contract Violations

Any of the following constitute a contract violation:

1. Verification produces a warning instead of PASS/FAIL
2. Verification continues after a failure
3. A tamper detection does not halt downstream processing
4. A corrupted store loads partially
5. Failure reasons are omitted or vague
6. Verification claims to prove something outside scope

**Contract violations are defects. They must be reported, not silently handled.**

---

## 10. Document Control

| Field | Value |
|-------|-------|
| Contract Owner | BENSON (GID-00) |
| Created | 2025-12-18 |
| Status | LOCKED |
| PAC | PAC-BENSON-TRUST-CONSOLIDATION-01 |
| Source of Truth | `core/occ/schemas/pdo.py`, `docs/proof/PROOFPACK_SPEC_v1.md` |
| Review Required | Any modification requires PAC approval |

---

**END OF CONTRACT — VERIFICATION_SEMANTICS.md**
