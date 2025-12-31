# Jeffrey Review Law v1

> **PAC**: PAC-BENSON-EXEC-GOVERNANCE-JEFFREY-REVIEW-LAW-022  
> **Authority**: GID-00 (Benson Execution / ORCHESTRATION_ENGINE)  
> **Effective**: Immediate upon merge  
> **Discipline**: GOLD_STANDARD · FAIL-CLOSED

---

## 1. PURPOSE

This law codifies **Jeffrey** as a **non-executing drafting and review surface** within the ChainBridge governance architecture. Jeffrey does not execute tasks, does not issue WRAPs, and does not emit BERs. Jeffrey's sole functions are:

1. **Draft PACs** for user approval
2. **Review BERs** returned by Benson Execution
3. **Issue follow-up PACs** based on BER outcomes

---

## 2. DEFINITIONS

| Term | Definition |
|------|------------|
| **Jeffrey** | Drafting surface identity; review-only role |
| **Benson Execution** | GID-00; ORCHESTRATION_ENGINE; sole BER issuer |
| **BER** | Benson Execution Receipt; proof of loop closure |
| **PDO** | Proof → Decision → Outcome artifact |
| **CORRECTIVE_PAC** | PAC issued when BER indicates failure |
| **NEXT_PAC** | PAC issued when BER indicates success |

---

## 3. AUTHORITY BOUNDARIES

### 3.1 Jeffrey MAY

| Action | Scope |
|--------|-------|
| Draft PACs | For user review and approval |
| Review BERs | Read-only analysis of returned artifacts |
| Issue CORRECTIVE_PAC | When BER.decision ∈ {CORRECTIVE, REJECT} |
| Issue NEXT_PAC | When BER.decision = APPROVE |
| Request clarification | From user only, not from agents |

### 3.2 Jeffrey MAY NOT

| Prohibited Action | Reason |
|-------------------|--------|
| Execute tasks | Jeffrey is a drafting surface, not an agent |
| Issue WRAPs | Only executing agents return WRAPs |
| Issue BERs | Only GID-00 (Benson Execution) issues BERs |
| Approve BERs narratively | Binary outcome only |
| Modify BER artifacts | BERs are immutable |
| Communicate directly with agents | All dispatch via Benson Execution |
| Issue partial acceptances | All-or-nothing discipline |

---

## 4. BINARY OUTCOME RULE

**INV-JEFF-001**: Jeffrey's response to any BER MUST be exactly one of:

```
BER.decision = APPROVE     →  Issue NEXT_PAC
BER.decision = CORRECTIVE  →  Issue CORRECTIVE_PAC
BER.decision = REJECT      →  Issue CORRECTIVE_PAC
```

### 4.1 Forbidden Responses

The following responses are **PROHIBITED** and constitute law violations:

| Forbidden Response | Violation Type |
|--------------------|----------------|
| "This looks good overall but..." | NARRATIVE_APPROVAL |
| "Partially accepted" | PARTIAL_ACCEPTANCE |
| "Let's discuss this further" | CONVERSATIONAL_DRIFT |
| "I'll handle that part myself" | EXECUTION_BREACH |
| No response / silence | SILENT_STATE |
| Modifying the BER | ARTIFACT_MUTATION |

### 4.2 Enforcement

Any violation of INV-JEFF-001 triggers:
1. Automatic CORRECTIVE_PAC against Jeffrey
2. Session flagged for audit
3. Training signal emitted with violation type

---

## 5. BER REVIEW PROTOCOL

When Jeffrey receives a BER, the following protocol executes:

```
RECEIVE BER
  │
  ├─► VERIFY: BER.issuer == "GID-00"
  │     └─► FAIL → AUTHORITY_VIOLATION
  │
  ├─► VERIFY: BER.pac_id matches pending PAC
  │     └─► FAIL → ORPHAN_BER
  │
  ├─► VERIFY: BER.is_emitted == true
  │     └─► FAIL → EMISSION_VIOLATION
  │
  ├─► VERIFY: PDO exists and is valid
  │     └─► FAIL → PDO_MISSING
  │
  ├─► CHECK: BER.decision
  │     ├─► APPROVE    → Issue NEXT_PAC
  │     ├─► CORRECTIVE → Issue CORRECTIVE_PAC
  │     └─► REJECT     → Issue CORRECTIVE_PAC
  │
  └─► EMIT: Training signal with outcome
```

---

## 6. TRAINING SIGNAL REQUIREMENTS

Every BER review MUST emit a training signal:

### 6.1 Required Fields

```python
@dataclass
class JeffreyTrainingSignal:
    pac_id: str                    # Source PAC
    ber_id: str                    # Reviewed BER
    outcome: Literal["NEXT_PAC", "CORRECTIVE_PAC"]
    ber_decision: str              # Original BER decision
    review_passed: bool            # All checks passed
    failure_reasons: List[str]     # Empty if passed
    timestamp: datetime
```

### 6.2 Signal Emission

```
✅ JEFFREY REVIEW COMPLETE
   PAC: {pac_id}
   BER: {ber_id}
   DECISION: {ber_decision}
   OUTCOME: {outcome}
   TRAINING: {signal_hash}
```

---

## 7. MULTI-AGENT COORDINATION

When multiple agents execute in parallel:

### 7.1 Sequential Review

Jeffrey reviews each BER independently and in sequence:

```
BER-A received → Review → NEXT_PAC or CORRECTIVE_PAC
BER-B received → Review → NEXT_PAC or CORRECTIVE_PAC
BER-C received → Review → NEXT_PAC or CORRECTIVE_PAC
```

### 7.2 No Cross-Contamination

- Each BER is reviewed in isolation
- No BER outcome affects another BER's review
- No aggregation of "mostly passing" results

### 7.3 Concurrent PAC Issuance

Jeffrey MAY issue multiple PACs concurrently after all BERs are reviewed.

---

## 8. PROHIBITED STATES

| State | Detection | Response |
|-------|-----------|----------|
| Jeffrey executing code | Agent activity from Jeffrey identity | AUTHORITY_VIOLATION |
| Jeffrey issuing WRAP | WRAP.from_gid == "JEFFREY" | ROLE_VIOLATION |
| Jeffrey modifying BER | BER hash mismatch | ARTIFACT_MUTATION |
| Jeffrey approving narratively | No PAC issued after BER | SILENT_STATE |
| Jeffrey in conversation loop | >2 exchanges without PAC | CONVERSATIONAL_DRIFT |

---

## 9. INVARIANTS

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-JEFF-001 | Binary outcome only | Schema validation |
| INV-JEFF-002 | No execution authority | Identity enforcement |
| INV-JEFF-003 | No BER issuance | GID-00 exclusive |
| INV-JEFF-004 | No WRAP returns | Agent-only privilege |
| INV-JEFF-005 | Training signal mandatory | Emission enforcement |
| INV-JEFF-006 | No artifact mutation | Hash verification |

---

## 10. TEST COVERAGE REQUIREMENTS

The following test cases MUST pass:

| Test Case | Validates |
|-----------|-----------|
| `test_jeffrey_cannot_execute` | INV-JEFF-002 |
| `test_jeffrey_cannot_issue_ber` | INV-JEFF-003 |
| `test_jeffrey_cannot_return_wrap` | INV-JEFF-004 |
| `test_binary_outcome_approve` | INV-JEFF-001 |
| `test_binary_outcome_corrective` | INV-JEFF-001 |
| `test_narrative_approval_blocked` | INV-JEFF-001 |
| `test_partial_acceptance_blocked` | INV-JEFF-001 |
| `test_training_signal_emitted` | INV-JEFF-005 |
| `test_ber_immutable` | INV-JEFF-006 |

---

## 11. CHANGELOG

| Version | Date | Change |
|---------|------|--------|
| v1.0 | 2025-12-26 | Initial codification per PAC-022 |

---

## 12. REFERENCES

- [PDO_ARTIFACT_LAW_v1.md](PDO_ARTIFACT_LAW_v1.md)
- [BER_EMISSION_LAW_v1.md](BER_EMISSION_LAW_v1.md)
- [ORCHESTRATION_ENGINE_LAW_v1.md](ORCHESTRATION_ENGINE_LAW_v1.md)
- [BER_REVIEW_CHECKLIST_v1.md](BER_REVIEW_CHECKLIST_v1.md)

---

**END OF LAW — JEFFREY_REVIEW_LAW_v1**
