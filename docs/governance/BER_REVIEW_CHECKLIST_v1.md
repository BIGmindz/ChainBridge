# BER Review Checklist v1

> **PAC**: PAC-BENSON-EXEC-GOVERNANCE-JEFFREY-REVIEW-LAW-022  
> **Authority**: GID-00 (Benson Execution / ORCHESTRATION_ENGINE)  
> **Consumer**: Jeffrey (Drafting Surface)  
> **Discipline**: GOLD_STANDARD · FAIL-CLOSED

---

## 1. PURPOSE

This checklist defines the **canonical, machine-executable review criteria** for evaluating Benson Execution Receipts (BERs). Every BER received by Jeffrey or any review surface MUST pass ALL checks before a NEXT_PAC can be issued.

**FAIL-CLOSED**: Any failed check → CORRECTIVE_PAC

---

## 2. CHECKLIST STRUCTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    BER REVIEW CHECKLIST                        │
├─────────────────────────────────────────────────────────────────┤
│  □ CHK-001: Authority Verification                             │
│  □ CHK-002: Loop Closure Verification                          │
│  □ CHK-003: PDO Chain Verification                             │
│  □ CHK-004: Emission Verification                              │
│  □ CHK-005: Decision Validity                                  │
│  □ CHK-006: Training Signal Presence                           │
│  □ CHK-007: Artifact Integrity                                 │
│  □ CHK-008: Temporal Ordering                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. CHECK DEFINITIONS

### CHK-001: Authority Verification

**Question**: Was this BER issued by an authorized entity?

| Field | Required Value | Failure Mode |
|-------|----------------|--------------|
| `ber.issuer` | `"GID-00"` or `"ORCHESTRATION_ENGINE"` | `AUTHORITY_VIOLATION` |

```python
def check_authority(ber: BERArtifact) -> CheckResult:
    valid_issuers = {"GID-00", "ORCHESTRATION_ENGINE"}
    if ber.issuer not in valid_issuers:
        return CheckResult(
            passed=False,
            check_id="CHK-001",
            reason=f"Invalid issuer: {ber.issuer}, expected GID-00"
        )
    return CheckResult(passed=True, check_id="CHK-001")
```

---

### CHK-002: Loop Closure Verification

**Question**: Does this BER close a valid PAC→WRAP→BER loop?

| Field | Required | Failure Mode |
|-------|----------|--------------|
| `ber.pac_id` | Non-empty, matches pending PAC | `ORPHAN_BER` |
| `ber.wrap_id` | Non-empty, valid reference | `MISSING_WRAP` |

```python
def check_loop_closure(ber: BERArtifact, pending_pacs: Set[str]) -> CheckResult:
    if not ber.pac_id:
        return CheckResult(False, "CHK-002", "Missing PAC ID")
    if ber.pac_id not in pending_pacs:
        return CheckResult(False, "CHK-002", f"Orphan BER: PAC {ber.pac_id} not pending")
    if not ber.wrap_id:
        return CheckResult(False, "CHK-002", "Missing WRAP ID")
    return CheckResult(passed=True, check_id="CHK-002")
```

---

### CHK-003: PDO Chain Verification

**Question**: Is the PDO artifact valid and hash-bound?

| Field | Required | Failure Mode |
|-------|----------|--------------|
| `pdo` | Must exist | `PDO_MISSING` |
| `pdo.proof_hash` | Non-empty | `PDO_INCOMPLETE` |
| `pdo.decision_hash` | Non-empty | `PDO_INCOMPLETE` |
| `pdo.outcome_hash` | Non-empty | `PDO_INCOMPLETE` |
| `pdo.pdo_hash` | Non-empty, chain-valid | `PDO_HASH_MISMATCH` |

```python
def check_pdo_chain(pdo: Optional[PDOArtifact]) -> CheckResult:
    if pdo is None:
        return CheckResult(False, "CHK-003", "PDO artifact missing")
    
    required = ["proof_hash", "decision_hash", "outcome_hash", "pdo_hash"]
    for field in required:
        if not getattr(pdo, field, None):
            return CheckResult(False, "CHK-003", f"PDO missing {field}")
    
    # Verify hash chain integrity
    if not verify_pdo_chain(pdo):
        return CheckResult(False, "CHK-003", "PDO hash chain invalid")
    
    return CheckResult(passed=True, check_id="CHK-003")
```

---

### CHK-004: Emission Verification

**Question**: Was this BER properly emitted (not just issued)?

| Field | Required Value | Failure Mode |
|-------|----------------|--------------|
| `ber.is_emitted` | `True` | `EMISSION_VIOLATION` |
| `ber.emitted_at` | Non-None timestamp | `EMISSION_VIOLATION` |

```python
def check_emission(ber: BERArtifact) -> CheckResult:
    if not ber.is_emitted:
        return CheckResult(False, "CHK-004", "BER not emitted")
    if ber.emitted_at is None:
        return CheckResult(False, "CHK-004", "Missing emission timestamp")
    return CheckResult(passed=True, check_id="CHK-004")
```

---

### CHK-005: Decision Validity

**Question**: Is the BER decision a valid enum value?

| Field | Required Value | Failure Mode |
|-------|----------------|--------------|
| `ber.decision` | `"APPROVE"`, `"CORRECTIVE"`, or `"REJECT"` | `INVALID_DECISION` |

```python
def check_decision_validity(ber: BERArtifact) -> CheckResult:
    valid_decisions = {"APPROVE", "CORRECTIVE", "REJECT"}
    if ber.decision not in valid_decisions:
        return CheckResult(
            False, "CHK-005", 
            f"Invalid decision: {ber.decision}"
        )
    return CheckResult(passed=True, check_id="CHK-005")
```

---

### CHK-006: Training Signal Presence

**Question**: Does this BER carry a training signal?

| Field | Required | Failure Mode |
|-------|----------|--------------|
| `ber.training_signal` | Non-None if CORRECTIVE | `MISSING_TRAINING_SIGNAL` |

```python
def check_training_signal(ber: BERArtifact) -> CheckResult:
    # Training signal mandatory for CORRECTIVE BERs
    if ber.decision == "CORRECTIVE" and not ber.training_signal:
        return CheckResult(
            False, "CHK-006",
            "CORRECTIVE BER missing training signal"
        )
    return CheckResult(passed=True, check_id="CHK-006")
```

---

### CHK-007: Artifact Integrity

**Question**: Is the BER artifact unmodified?

| Check | Method | Failure Mode |
|-------|--------|--------------|
| Hash verification | Recompute and compare | `ARTIFACT_TAMPERED` |

```python
def check_artifact_integrity(ber: BERArtifact) -> CheckResult:
    expected_hash = compute_ber_hash(ber)
    if hasattr(ber, 'ber_hash') and ber.ber_hash != expected_hash:
        return CheckResult(
            False, "CHK-007",
            "BER artifact hash mismatch - possible tampering"
        )
    return CheckResult(passed=True, check_id="CHK-007")
```

---

### CHK-008: Temporal Ordering

**Question**: Are timestamps in valid chronological order?

| Constraint | Failure Mode |
|------------|--------------|
| `wrap_received_at` < `ber_issued_at` | `TEMPORAL_VIOLATION` |
| `ber_issued_at` ≤ `ber_emitted_at` | `TEMPORAL_VIOLATION` |

```python
def check_temporal_ordering(ber: BERArtifact) -> CheckResult:
    if ber.issued_at and ber.emitted_at:
        if ber.issued_at > ber.emitted_at:
            return CheckResult(
                False, "CHK-008",
                "BER issued after emission timestamp"
            )
    return CheckResult(passed=True, check_id="CHK-008")
```

---

## 4. GOLD STANDARD MAPPING

| Check | Gold Standard Rule |
|-------|-------------------|
| CHK-001 | Only GID-00 issues BERs |
| CHK-002 | Every BER closes exactly one loop |
| CHK-003 | PDO is the canonical proof artifact |
| CHK-004 | BER must be emitted, not just issued |
| CHK-005 | Decisions are enumerated, not narrative |
| CHK-006 | Failures produce training signals |
| CHK-007 | Artifacts are immutable |
| CHK-008 | Causality is preserved |

---

## 5. REJECT CONDITIONS

A BER is **REJECTED** and triggers CORRECTIVE_PAC if ANY of these conditions are true:

| Condition | Check | Severity |
|-----------|-------|----------|
| Issuer is not GID-00 | CHK-001 | CRITICAL |
| No matching PAC | CHK-002 | CRITICAL |
| No WRAP reference | CHK-002 | CRITICAL |
| PDO missing or invalid | CHK-003 | CRITICAL |
| Not emitted | CHK-004 | CRITICAL |
| Invalid decision value | CHK-005 | CRITICAL |
| Missing training signal on CORRECTIVE | CHK-006 | WARNING* |
| Hash mismatch | CHK-007 | CRITICAL |
| Temporal paradox | CHK-008 | WARNING* |

*WARNING checks emit alerts but may not block in v1

---

## 6. EXECUTION RESULT

The checklist produces a single result:

```python
@dataclass
class BERReviewResult:
    """Result of BER review checklist execution."""
    
    ber_id: str
    pac_id: str
    passed: bool                      # ALL checks passed
    outcome: Literal["PASS", "FAIL"]  # Binary only
    checks: List[CheckResult]         # Individual results
    failure_reasons: List[str]        # Empty if passed
    review_timestamp: datetime
    
    @property
    def requires_corrective_pac(self) -> bool:
        return not self.passed
    
    @property
    def allows_next_pac(self) -> bool:
        return self.passed
```

---

## 7. TERMINAL OUTPUT

On checklist completion:

```
══════════════════════════════════════════════════════════════════
🔍 BER REVIEW CHECKLIST COMPLETE
══════════════════════════════════════════════════════════════════
BER-ID:   {ber_id}
PAC-ID:   {pac_id}
DECISION: {ber.decision}
══════════════════════════════════════════════════════════════════
  ✅ CHK-001: Authority Verification      PASS
  ✅ CHK-002: Loop Closure Verification   PASS
  ✅ CHK-003: PDO Chain Verification      PASS
  ✅ CHK-004: Emission Verification       PASS
  ✅ CHK-005: Decision Validity           PASS
  ✅ CHK-006: Training Signal Presence    PASS
  ✅ CHK-007: Artifact Integrity          PASS
  ✅ CHK-008: Temporal Ordering           PASS
══════════════════════════════════════════════════════════════════
RESULT:   ✅ PASS
ACTION:   → NEXT_PAC eligible
══════════════════════════════════════════════════════════════════
```

Or on failure:

```
══════════════════════════════════════════════════════════════════
🔍 BER REVIEW CHECKLIST COMPLETE
══════════════════════════════════════════════════════════════════
BER-ID:   {ber_id}
PAC-ID:   {pac_id}
DECISION: {ber.decision}
══════════════════════════════════════════════════════════════════
  ✅ CHK-001: Authority Verification      PASS
  ❌ CHK-002: Loop Closure Verification   FAIL
     └─ Reason: Orphan BER: PAC PAC-XXX not pending
  ✅ CHK-003: PDO Chain Verification      PASS
  ...
══════════════════════════════════════════════════════════════════
RESULT:   ❌ FAIL
ACTION:   → CORRECTIVE_PAC required
══════════════════════════════════════════════════════════════════
```

---

## 8. PROHIBITED REVIEWER BEHAVIORS

| Behavior | Detection | Response |
|----------|-----------|----------|
| Skipping checks | Check count < 8 | Review rejected |
| Partial pass | Some checks skipped | Review rejected |
| Narrative override | No CheckResult objects | Review rejected |
| Manual approval | Bypassing checklist | Audit flag |

---

## 9. CHANGELOG

| Version | Date | Change |
|---------|------|--------|
| v1.0 | 2025-12-26 | Initial codification per PAC-022 |

---

## 10. REFERENCES

- [JEFFREY_REVIEW_LAW_v1.md](JEFFREY_REVIEW_LAW_v1.md)
- [PDO_ARTIFACT_LAW_v1.md](PDO_ARTIFACT_LAW_v1.md)
- [BER_EMISSION_LAW_v1.md](BER_EMISSION_LAW_v1.md)

---

**END OF CHECKLIST — BER_REVIEW_CHECKLIST_v1**
