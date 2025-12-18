# ProofPack Verification Invariants Contract

Version: 1.0
Status: LOCKED
Classification: CONTRACT (Immutable)

Contract Owner: BENSON (GID-00)
PAC Reference: PAC-BENSON-VERIFICATION-LOCK-01
Effective Date: 2025-12-18

---

## 1. Purpose

This document defines the **canonical verification semantics** for ProofPack verification in ChainBridge. These semantics are non-negotiable and govern:

- What is verified
- In what order
- What constitutes failure
- What errors are emitted

**This is a contract, not a specification.** Ambiguity is a defect. Drift is a defect.

---

## 2. Verification Step Order (CANONICAL)

Verification follows a **fixed, sequential** step order. Each step must pass before the next executes.

| Step ID | Step Name | Code Method | Failure Outcome |
|---------|-----------|-------------|-----------------|
| V-STEP-01 | PDO Record Hash | `_verify_pdo_hash()` | `INVALID_PDO_HASH` |
| V-STEP-02 | Artifact Hashes | `_verify_artifact_hashes()` | `INVALID_ARTIFACT_HASH` |
| V-STEP-03 | Manifest Hash | `_verify_manifest_hash()` | `INVALID_MANIFEST_HASH` |
| V-STEP-04 | Lineage Chain | `_verify_lineage()` | `INVALID_LINEAGE` |
| V-STEP-05 | Reference Consistency | `_verify_references()` | `INVALID_REFERENCES` |

---

## 3. Verification Outcomes (CANONICAL)

### 3.1 Outcome Enumeration

**V-OUT-001: Verification produces exactly these outcomes:**

| Outcome | Meaning | Step Reached |
|---------|---------|--------------|
| `VALID` | All steps passed | Step 5 completed |
| `INVALID_PDO_HASH` | PDO record hash mismatch | Failed at Step 1 |
| `INVALID_ARTIFACT_HASH` | Artifact file hash mismatch | Failed at Step 2 |
| `INVALID_MANIFEST_HASH` | Manifest hash mismatch | Failed at Step 3 |
| `INVALID_LINEAGE` | Lineage chain broken | Failed at Step 4 |
| `INVALID_REFERENCES` | Reference inconsistency | Failed at Step 5 |
| `INCOMPLETE` | Missing files or parse error | Pre-step failure |

### 3.2 Binary Result Property

**V-OUT-002: `is_valid` is TRUE if and only if outcome is `VALID`.**

```
is_valid = (outcome == VALID)
```

No other outcome produces `is_valid=True`.

---

## 4. Step Specifications

### 4.1 V-STEP-01: PDO Record Hash Verification

**Location:** `core/occ/proofpack/verifier.py:_verify_pdo_hash()` (lines 239-304)

#### What Is Checked

1. PDO record file exists at path specified in manifest
2. PDO record contains non-empty `hash` field
3. Computed hash matches stored hash

#### Hash Computation Algorithm

```python
canonical_data = {
    "pdo_id": str(pdo_id),
    "version": version,
    "input_refs": sorted(input_refs),
    "decision_ref": decision_ref,
    "outcome_ref": outcome_ref,
    "outcome": outcome,
    "source_system": source_system,
    "actor": actor,
    "actor_type": actor_type,
    "recorded_at": normalize_timestamp(recorded_at),  # Z → +00:00
    "previous_pdo_id": str(previous_pdo_id) if previous_pdo_id else None,
    "correlation_id": correlation_id,
}
canonical_json = json.dumps(canonical_data, sort_keys=True, separators=(",", ":"))
computed_hash = sha256(canonical_json.encode("utf-8")).hexdigest()
```

#### Failure Conditions

| Condition | Error Message |
|-----------|---------------|
| PDO file not found | `"PDO record file not found: {path}"` |
| Hash field missing | `"PDO record missing 'hash' field"` |
| Hash mismatch | `"PDO record hash mismatch - tampering detected"` |
| Parse error | `"PDO hash verification error: {e}"` |

#### Pass Condition

Computed hash equals stored hash exactly (case-sensitive, 64-char lowercase hex).

---

### 4.2 V-STEP-02: Artifact Hash Verification

**Location:** `core/occ/proofpack/verifier.py:_verify_artifact_hashes()` (lines 306-367)

#### What Is Checked

For each artifact in manifest.contents (pdo, inputs, decision, outcome, lineage):
1. File exists at specified path
2. SHA-256 of raw file bytes matches manifest hash

#### Hash Computation Algorithm

```python
file_bytes = file_content.encode("utf-8")
computed_hash = sha256(file_bytes).hexdigest()
```

#### Failure Conditions

| Condition | Error Message |
|-----------|---------------|
| File not found | `"Artifact hash verification failed: {path} (file not found)"` |
| Hash mismatch | `"Artifact hash verification failed: {path} (hash mismatch)"` |

#### Pass Condition

All artifact file hashes match their manifest entries exactly.

---

### 4.3 V-STEP-03: Manifest Hash Verification

**Location:** `core/occ/proofpack/verifier.py:_verify_manifest_hash()` (lines 369-419)

#### What Is Checked

1. Manifest contains `integrity.manifest_hash` field
2. Recomputed manifest hash matches stored hash

#### Hash Computation Algorithm

```python
manifest_data = {
    "proofpack_version": manifest["proofpack_version"],
    "pdo_id": manifest["pdo_id"],
    "exported_at": manifest["exported_at"],
    "exporter": manifest["exporter"],
    "contents": manifest["contents"],
}
# Note: integrity block is EXCLUDED from hash
canonical_json = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"))
computed_hash = sha256(canonical_json.encode("utf-8")).hexdigest()
```

#### Failure Conditions

| Condition | Error Message |
|-----------|---------------|
| Hash field missing | `"Manifest missing integrity.manifest_hash"` |
| Hash mismatch | `"Manifest hash mismatch - tampering detected"` |

#### Pass Condition

Computed manifest hash equals stored `integrity.manifest_hash` exactly.

---

### 4.4 V-STEP-04: Lineage Chain Verification

**Location:** `core/occ/proofpack/verifier.py:_verify_lineage()` (lines 421-519)

#### What Is Checked

For each lineage PDO (oldest to newest):
1. Lineage file exists at specified path
2. Lineage PDO hash is valid (same algorithm as V-STEP-01)
3. `previous_pdo_id` matches prior PDO's `pdo_id`
4. `recorded_at` is after prior PDO's `recorded_at`

#### Failure Conditions

| Condition | Error Message |
|-----------|---------------|
| File not found | `"Lineage file not found: {path}"` |
| Hash mismatch | `"Lineage PDO hash mismatch: {pdo_id}"` |
| Chain broken | `"Lineage chain broken at {pdo_id}"` |
| Timestamp invalid | `"Lineage timestamp order invalid at {pdo_id}"` |
| Parse error | `"Lineage verification error: {e}"` |

#### Pass Condition (No Lineage)

If `lineage` array is empty, step passes with message `"No lineage to verify"`.

#### Pass Condition (With Lineage)

All lineage PDOs have valid hashes, correct chain linkage, and ascending timestamps.

---

### 4.5 V-STEP-05: Reference Consistency Verification

**Location:** `core/occ/proofpack/verifier.py:_verify_references()` (lines 521-608)

#### What Is Checked

1. `manifest.pdo_id` == `pdo/record.json.pdo_id`
2. `manifest.contents.inputs[].ref` == `pdo.input_refs[]` (set equality)
3. `manifest.contents.decision.ref` == `pdo.decision_ref`
4. `manifest.contents.outcome.ref` == `pdo.outcome_ref`

#### Failure Conditions

| Condition | Error Message |
|-----------|---------------|
| PDO not found | `"PDO record not found for reference verification"` |
| PDO ID mismatch | `"PDO ID mismatch: manifest={m}, record={r}"` |
| Input refs mismatch | `"Input refs mismatch between manifest and PDO"` |
| Decision ref mismatch | `"Decision ref mismatch: manifest={m}, pdo={p}"` |
| Outcome ref mismatch | `"Outcome ref mismatch: manifest={m}, pdo={p}"` |
| Parse error | `"Reference verification error: {e}"` |

#### Pass Condition

All reference bindings match exactly.

---

## 5. Fail-Fast Behavior

### 5.1 Halt on First Failure

**V-HALT-001: Verification halts on first failure.**

```
if not step.passed:
    return FAIL with outcome
    # DO NOT continue to next step
```

### 5.2 No Warning State

**V-HALT-002: There is no warning outcome.**

Verification produces PASS or FAIL only. Anomalies that do not affect integrity are not reported.

### 5.3 No Partial Results

**V-HALT-003: Partial verification is not a valid outcome.**

If any step fails, the entire verification fails. There is no "3 of 5 steps passed" result.

---

## 6. Pre-Step Failures

### 6.1 Missing Manifest

**V-PRE-001: Missing manifest.json produces INCOMPLETE.**

```
if manifest_content is None:
    return INCOMPLETE: "manifest.json not found"
```

### 6.2 JSON Parse Error

**V-PRE-002: JSON parse failure produces INCOMPLETE.**

```
except json.JSONDecodeError:
    return INCOMPLETE: "JSON parse error: {e}"
```

### 6.3 General Error

**V-PRE-003: Unexpected errors produce INCOMPLETE.**

```
except Exception:
    return INCOMPLETE: "Verification error: {e}"
```

---

## 7. Verification Result Schema

### 7.1 Canonical Result Structure

```json
{
    "outcome": "VALID | INVALID_* | INCOMPLETE",
    "pdo_id": "{pdo_uuid}",
    "verified_at": "{iso8601_utc}",
    "steps": [
        {
            "step": "{step_name}",
            "passed": true | false,
            "message": "{human_readable}",
            "expected": "{hash}" | null,
            "actual": "{hash}" | null
        }
    ],
    "is_valid": true | false,
    "error_message": "{message}" | null
}
```

### 7.2 Step Result Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step` | string | YES | Step name (e.g., `verify_pdo_hash`) |
| `passed` | boolean | YES | Whether step passed |
| `message` | string | YES | Human-readable result |
| `expected` | string | NO | Expected hash value |
| `actual` | string | NO | Computed hash value |

---

## 8. Test Coverage Mapping

| Step ID | Test Class | Test Method | Coverage |
|---------|------------|-------------|----------|
| V-STEP-01 | `TestTamperDetection` | `test_pdo_tamper_fails` | ✅ |
| V-STEP-01 | `TestMissingFiles` | `test_missing_pdo_fails` | ✅ |
| V-STEP-02 | `TestTamperDetection` | `test_input_artifact_tamper_fails` | ✅ |
| V-STEP-03 | `TestTamperDetection` | `test_manifest_tamper_fails` | ✅ |
| V-STEP-03 | `TestMissingFiles` | `test_missing_manifest_fails` | ✅ |
| V-STEP-04 | — | — | ⚠️ Implicit (no lineage test) |
| V-STEP-05 | — | — | ⚠️ Implicit (no explicit ref test) |
| Pre-step | `TestEdgeCases` | `test_empty_proofpack_fails` | ✅ |
| Pre-step | `TestEdgeCases` | `test_no_files_fails` | ✅ |
| Pre-step | `TestEdgeCases` | `test_malformed_json_fails` | ✅ |
| All steps | `TestVerificationSuccess` | `test_verify_all_steps_pass` | ✅ |
| Round-trip | `TestRoundTrip` | `test_generated_proofpack_verifies` | ✅ |
| Offline | `TestRoundTrip` | `test_offline_verification` | ✅ |

---

## 9. Identified Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|----------|----------------|
| GAP-V-01 | V-STEP-04 (lineage) has no explicit failure test | Medium | Add `test_lineage_tamper_fails` |
| GAP-V-02 | V-STEP-05 (references) has no explicit failure test | Medium | Add `test_reference_mismatch_fails` |
| GAP-V-03 | Decision artifact tamper not explicitly tested | Low | Add `test_decision_artifact_tamper_fails` |
| GAP-V-04 | Outcome artifact tamper not explicitly tested | Low | Add `test_outcome_artifact_tamper_fails` |

---

## 10. Invariants Summary

| Invariant ID | Statement |
|--------------|-----------|
| **V-INV-001** | Verification follows fixed 5-step order |
| **V-INV-002** | Each step halts on failure (fail-fast) |
| **V-INV-003** | Outcomes are VALID, INVALID_*, or INCOMPLETE only |
| **V-INV-004** | `is_valid=True` only when `outcome=VALID` |
| **V-INV-005** | PDO hash uses canonical JSON with sorted keys |
| **V-INV-006** | Artifact hashes use raw UTF-8 byte SHA-256 |
| **V-INV-007** | Manifest hash excludes integrity block |
| **V-INV-008** | Lineage requires ascending timestamps |
| **V-INV-009** | Reference verification is set equality for inputs |
| **V-INV-010** | Verification requires no network access |

---

## 11. Code Location References

| Component | File | Lines |
|-----------|------|-------|
| Verifier class | `core/occ/proofpack/verifier.py` | 56-608 |
| `_verify_pdo_hash()` | `core/occ/proofpack/verifier.py` | 239-304 |
| `_verify_artifact_hashes()` | `core/occ/proofpack/verifier.py` | 306-367 |
| `_verify_manifest_hash()` | `core/occ/proofpack/verifier.py` | 369-419 |
| `_verify_lineage()` | `core/occ/proofpack/verifier.py` | 421-519 |
| `_verify_references()` | `core/occ/proofpack/verifier.py` | 521-608 |
| VerificationOutcome enum | `core/occ/proofpack/schemas.py` | 82-92 |
| VerificationStep schema | `core/occ/proofpack/schemas.py` | 264-274 |
| ProofPackVerificationResult | `core/occ/proofpack/schemas.py` | 277-291 |
| Test file | `tests/occ/test_proofpack_verification.py` | 1-312 |

---

## 12. Contract Violations

Any of the following constitute a contract violation:

1. Verification step order is changed
2. A new step is added without version bump
3. A step is removed without version bump
4. Failure produces a warning instead of FAIL
5. Verification continues after step failure
6. `is_valid=True` is returned for non-VALID outcome
7. Offline verification becomes impossible
8. Hash algorithm changes without version bump

**Contract violations are defects. They must be reported, not silently handled.**

---

## 13. Next Hardening PAC Recommendation

**PAC-CODY-VERIFICATION-TEST-01**: Verification Test Coverage Completion

Scope:
1. Add explicit lineage chain failure test
2. Add explicit reference consistency failure test
3. Add explicit decision/outcome artifact tamper tests
4. Add timestamp ordering violation test

Priority: Medium
Assigned: CODY (GID-01)

---

## 14. Document Control

| Field | Value |
|-------|-------|
| Contract Owner | BENSON (GID-00) |
| Created | 2025-12-18 |
| Status | LOCKED |
| PAC | PAC-BENSON-VERIFICATION-LOCK-01 |
| Source of Truth | `core/occ/proofpack/verifier.py` |
| Review Required | Any modification requires PAC approval |

---

**END OF CONTRACT — VERIFICATION_INVARIANTS.md**
