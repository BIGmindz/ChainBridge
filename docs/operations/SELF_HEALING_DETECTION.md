# Self-Healing Detection Baseline

Version: 1.0
Status: LOCKED
Classification: CONTRACT (Immutable)

Contract Owner: BENSON (GID-00)
PAC Reference: PAC-BENSON-TRUST-CONSOLIDATION-01
Effective Date: 2025-12-18

---

## 1. Purpose

This document defines the **Self-Healing Detection Baseline** for ChainBridge. This baseline specifies what drift and corruption conditions are detected, how they are detected, and what response is mandated.

**CRITICAL: This is DETECTION ONLY. No auto-fix. No auto-repair. No mutation.**

**This is a contract, not an implementation plan.** Violations are defects.

---

## 2. Detection Posture

### 2.1 Alert-Only Mode

**HEAL-001: Self-healing operates in ALERT-ONLY mode.**

The system:
- DETECTS anomalies
- LOGS anomalies
- ALERTS operators
- DOES NOT mutate data
- DOES NOT repair data
- DOES NOT delete data

### 2.2 No Auto-Fix

**HEAL-002: Automatic repair is explicitly prohibited.**

Prohibited actions:
- Recomputing and overwriting hashes
- Deleting corrupted records
- Reconstructing missing artifacts
- Modifying timestamps
- Re-ordering data
- Any mutation of evidence

### 2.3 Human-In-Loop Mandate

**HEAL-003: All remediation requires human decision.**

Detection triggers alerts. Humans decide response. No automated remediation.

---

## 3. PDO Detection Baseline

### 3.1 Periodic PDO Hash Re-Scan

**HEAL-004: PDO hashes are re-verified periodically.**

Detection:
```
For each PDO in store:
    computed_hash = PDO.compute_hash()
    if computed_hash != PDO.hash:
        ALERT: "PDO hash drift detected"
        LOG: {pdo_id, expected_hash, computed_hash, detected_at}
```

Schedule: Configurable (recommended: daily)

### 3.2 PDO Load-Time Verification

**HEAL-005: PDO hashes are verified on store load.**

Detection is performed automatically when PDOStore initializes:
- Every record is hash-verified
- Any mismatch halts load
- Operator must intervene

### 3.3 PDO Read-Time Verification

**HEAL-006: PDO hashes are verified on read (by default).**

Detection:
- `PDOStore.get()` verifies hash by default
- Mismatch raises `PDOTamperDetectedError`
- Caller must handle exception

### 3.4 PDO Schema Validation

**HEAL-007: PDO schema is validated on load and read.**

Detection:
- Pydantic validates schema
- Invalid records fail to load
- Missing required fields are detected
- Invalid enum values are detected

---

## 4. ProofPack Detection Baseline

### 4.1 Periodic ProofPack Re-Verification

**HEAL-008: Archived ProofPacks are re-verified periodically.**

Detection:
```
For each archived ProofPack:
    result = verify_proofpack(proofpack_path)
    if result.outcome == "FAIL":
        ALERT: "ProofPack verification failed"
        LOG: {proofpack_id, failure_step, failure_reason, detected_at}
```

Schedule: Configurable (recommended: weekly)

### 4.2 ProofPack Export-Time Verification

**HEAL-009: ProofPacks are verified immediately after generation.**

Detection:
- After export, run full verification
- Verification must pass before archive
- Failure blocks archive and alerts operator

### 4.3 ProofPack Manifest Integrity

**HEAL-010: ProofPack manifests are checked for internal consistency.**

Detection:
- All paths in manifest must resolve to files
- All hashes in manifest must match file contents
- All references must match PDO references

---

## 5. Determinism Checks

### 5.1 Hash Determinism Verification

**HEAL-011: Hash computation determinism is verified.**

Detection:
```
For sample of PDOs:
    hash_1 = compute_hash(PDO)
    hash_2 = compute_hash(PDO)
    if hash_1 != hash_2:
        ALERT: "Hash computation non-determinism detected"
        CRITICAL: System may be compromised
```

This check verifies the hash algorithm produces consistent results.

### 5.2 JSON Serialization Determinism

**HEAL-012: JSON serialization determinism is verified.**

Detection:
```
For sample of records:
    json_1 = canonical_serialize(record)
    json_2 = canonical_serialize(record)
    if json_1 != json_2:
        ALERT: "JSON serialization non-determinism detected"
```

### 5.3 Timestamp Determinism

**HEAL-013: Timestamp format consistency is verified.**

Detection:
- All timestamps must be ISO 8601 UTC
- All timestamps must parse successfully
- Format variations are flagged

---

## 6. Drift Conditions

### 6.1 Definition of Drift

**HEAL-014: Drift is defined as unexpected change in stored data.**

Drift types:

| Type | Description | Severity |
|------|-------------|----------|
| Hash drift | Stored hash ≠ computed hash | CRITICAL |
| Schema drift | Record doesn't match schema | HIGH |
| Reference drift | References don't resolve | HIGH |
| Timestamp drift | Timestamps out of order | MEDIUM |
| Format drift | Encoding/format changed | MEDIUM |

### 6.2 Drift vs. Corruption

**HEAL-015: Drift and corruption are distinguished by cause.**

| Condition | Cause | Response |
|-----------|-------|----------|
| Drift | Unknown/unintentional change | Investigate |
| Corruption | Storage failure, bit rot | Restore from backup |
| Tampering | Intentional modification | Security incident |

Detection cannot determine cause. Human investigation required.

---

## 7. Alert Requirements

### 7.1 Alert Content

**HEAL-016: Alerts must contain sufficient detail for diagnosis.**

Required alert fields:
```json
{
    "alert_type": "hash_drift|schema_drift|reference_drift|...",
    "severity": "CRITICAL|HIGH|MEDIUM|LOW",
    "detected_at": "{iso8601_utc}",
    "subject": {
        "type": "pdo|proofpack|store",
        "id": "{identifier}"
    },
    "details": {
        "expected": "{value}",
        "actual": "{value}",
        "detection_method": "{method}"
    },
    "recommended_action": "{action}"
}
```

### 7.2 Alert Severity

**HEAL-017: Alert severity determines response urgency.**

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| CRITICAL | Immediate | On-call engineer |
| HIGH | 1 hour | Operations team |
| MEDIUM | 24 hours | Operations queue |
| LOW | 7 days | Regular review |

### 7.3 Alert Channels

**HEAL-018: Alerts are delivered via configured channels.**

Channels:
- Logging system (always)
- Operator dashboard (if available)
- External alerting (PagerDuty, etc., if configured)

---

## 8. Operator Response Requirements

### 8.1 CRITICAL Alert Response

**HEAL-019: CRITICAL alerts require immediate operator action.**

Required actions:
1. Acknowledge alert
2. Halt affected operations (if applicable)
3. Preserve evidence (do not modify)
4. Investigate root cause
5. Document findings
6. Decide remediation (human decision)
7. Execute remediation (human action)
8. Verify remediation
9. Close alert

### 8.2 Quarantine Procedure

**HEAL-020: Affected records may be quarantined pending investigation.**

Quarantine:
- Record is marked as quarantined
- Record is excluded from normal operations
- Record is NOT deleted
- Record is NOT modified
- Human must release from quarantine

### 8.3 Investigation Procedure

**HEAL-021: Investigation must preserve evidence.**

Investigation rules:
- Make copies, not modifications
- Log all investigation actions
- Preserve chain of custody
- Document findings

---

## 9. Scheduled Detection Jobs

### 9.1 Daily Jobs

**HEAL-022: The following detection runs daily:**

| Job | Description |
|-----|-------------|
| PDO Hash Scan | Re-verify all PDO hashes |
| Schema Validation | Validate all PDO schemas |
| Determinism Spot-Check | Sample determinism verification |

### 9.2 Weekly Jobs

**HEAL-023: The following detection runs weekly:**

| Job | Description |
|-----|-------------|
| ProofPack Verification | Re-verify archived ProofPacks |
| Reference Integrity | Check all reference resolutions |
| Lineage Chain Audit | Verify all lineage chains |

### 9.3 On-Demand Jobs

**HEAL-024: The following detection can be triggered manually:**

| Job | Trigger |
|-----|---------|
| Full Store Scan | Operator request |
| Specific PDO Verify | Incident investigation |
| ProofPack Re-export | Export verification failure |

---

## 10. Detection Reporting

### 10.1 Detection Reports

**HEAL-025: Detection results are reported in standard format.**

Report structure:
```json
{
    "report_type": "detection_scan",
    "scan_type": "pdo_hash|proofpack|full",
    "started_at": "{iso8601_utc}",
    "completed_at": "{iso8601_utc}",
    "records_scanned": 12345,
    "anomalies_detected": 0,
    "anomalies": [],
    "status": "CLEAN|ANOMALIES_DETECTED"
}
```

### 10.2 Report Retention

**HEAL-026: Detection reports are retained per retention policy.**

Retention:
- Daily reports: 90 days
- Weekly reports: 1 year
- Anomaly reports: Indefinite

### 10.3 Audit Trail

**HEAL-027: All detection activity is recorded in audit trail.**

Audit entries:
- Scan started
- Scan completed
- Anomaly detected
- Alert sent
- Operator response

---

## 11. Prohibited Actions

### 11.1 Explicitly Prohibited

**HEAL-028: The following actions are PROHIBITED:**

| Action | Reason |
|--------|--------|
| Auto-repair hash mismatch | Evidence destruction |
| Auto-delete corrupted record | Evidence destruction |
| Auto-restore from backup | Human decision required |
| Suppress alerts | Visibility required |
| Skip verification | Detection gap |
| Modify during investigation | Evidence tampering |

### 11.2 Requires Human Decision

**HEAL-029: The following require explicit human decision:**

| Action | Decision Required |
|--------|-------------------|
| Restore from backup | Which backup, verify integrity |
| Delete corrupted record | Confirm evidence preservation |
| Mark as irrecoverable | Confirm investigation complete |
| Release from quarantine | Confirm remediation complete |

---

## 12. Contract Violations

Any of the following constitute a contract violation:

1. Automated repair without human decision
2. Data mutation during detection
3. Alert suppression
4. Verification skipped
5. Evidence modified during investigation
6. Report not generated
7. Audit trail not recorded

**Contract violations are defects. They must be reported, not silently handled.**

---

## 13. Document Control

| Field | Value |
|-------|-------|
| Contract Owner | BENSON (GID-00) |
| Created | 2025-12-18 |
| Status | LOCKED |
| PAC | PAC-BENSON-TRUST-CONSOLIDATION-01 |
| Mode | Alert-only (no auto-fix) |
| Review Required | Any modification requires PAC approval |

---

**END OF CONTRACT — SELF_HEALING_DETECTION.md**
