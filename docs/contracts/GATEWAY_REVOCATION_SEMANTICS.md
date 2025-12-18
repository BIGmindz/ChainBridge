# ChainBridge Gateway Revocation Semantics Contract

**Document:** GATEWAY_REVOCATION_SEMANTICS.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Revocation Boundary Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GATEWAY-AUTHORITY-BOUNDARY-01
**Effective Date:** 2025-12-18
**Alignment:** GATEWAY_AUTHORITY_BOUNDARY.md, GOVERNANCE_INVARIANTS.md

---

## 1. Purpose

This document defines the **revocation semantics** for the ChainBridge Gateway:

- How authority is revoked
- What revocation affects (future only vs historical)
- What cannot be undone
- How revocation is proven and recorded

**Revocation is explicit, bounded, and auditable.** No silent revocation. No retroactive effects.

---

## 2. Revocation Definition

### 2.1 What Revocation Means

| Term | Definition |
|------|------------|
| **Revocation** | Withdrawal of previously granted authority |
| **Prospective** | Affects future evaluations only |
| **Retrospective** | Would affect past decisions (NOT supported) |
| **Irrevocable** | Cannot be undone or reversed |
| **Revocation Record** | Auditable evidence of revocation |

### 2.2 Revocation Scope

**Gateway revocation is prospective only.** Past decisions are immutable.

| Scope | Supported | Rationale |
|-------|-----------|-----------|
| Future evaluations | ✓ | ACM changes affect future intents |
| In-flight evaluations | ✓ | Denial registry blocks retries |
| Past decisions | ✗ | Immutability contract (INV-PDO-001) |
| Executed actions | ✗ | Downstream responsibility |
| Historical records | ✗ | Audit integrity |

---

## 3. How Authority Is Revoked

### 3.1 Revocation Mechanisms

| Mechanism | Scope | Trigger | Evidence |
|-----------|-------|---------|----------|
| **ACM Removal** | Agent capability | Remove agent from ACM manifest | ACM version change |
| **Verb Removal** | Specific verb | Remove verb from agent's capability list | ACM diff |
| **Target Restriction** | Scope narrowing | Narrow target scope in ACM | ACM diff |
| **ALEX Override** | Any agent | ALEX veto rule triggered | ALEX rule violation |
| **Denial Registry** | Specific intent | DENY decision recorded | Denial record in registry |
| **Human Escalation** | Specific execution | `human_required=True` set | Envelope flag |

### 3.2 Revocation Flow

```
Revocation Trigger
       │
       ▼
┌──────────────────┐
│  Revocation Type │
└────────┬─────────┘
         │
    ┌────┴────────────────┐
    │                     │
    ▼                     ▼
 ACM Change           Denial Registry
    │                     │
    ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│ Boot-time reload │  │ Runtime check    │
│ (next restart)   │  │ (immediate)      │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         └─────────┬───────────┘
                   │
                   ▼
         ┌──────────────────┐
         │ Future intents   │
         │ affected         │
         └──────────────────┘
```

### 3.3 Revocation Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| REV-001 | ACM changes require boot reload | ACM loaded at startup only |
| REV-002 | Denial registry is immediately effective | `is_denied()` checked per intent |
| REV-003 | ALEX override is runtime | `ALEXMiddleware` evaluates every intent |
| REV-004 | Revocation is auditable | Governance audit log |

---

## 4. What Revocation Affects

### 4.1 Future-Only Effects (Prospective)

| Affected | Mechanism | When Effective |
|----------|-----------|----------------|
| **New intents from revoked agent** | ACM capability check fails | Next boot (ACM) / Immediately (denial) |
| **New intents with revoked verb** | Verb not in capability list | Next boot |
| **New intents to revoked target** | Target not in scope | Next boot |
| **Retry of denied intent** | Denial registry check | Immediately |

### 4.2 Effects Timeline

```
         Past                   Now                   Future
           │                     │                     │
           │  Executed actions   │  In-flight intents  │  New intents
           │  (IMMUTABLE)        │  (denial registry)  │  (ACM changes)
           │                     │                     │
    ┌──────┴──────┐       ┌──────┴──────┐       ┌──────┴──────┐
    │ Cannot be   │       │ Blocked by  │       │ Blocked by  │
    │ revoked     │       │ denial      │       │ ACM removal │
    │             │       │ registry    │       │ or scope    │
    └─────────────┘       └─────────────┘       └─────────────┘
```

### 4.3 Effect Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| REV-EFF-001 | Past decisions are immutable | INV-PDO-001: Field Immutability |
| REV-EFF-002 | Denial registry blocks immediately | `is_denied()` per-intent check |
| REV-EFF-003 | ACM changes require restart | ACM loaded at boot only |
| REV-EFF-004 | Revocation scope is explicit | ACM manifest defines scope |

---

## 5. What Cannot Be Undone

### 5.1 Irrevocable Decisions

The following are irrevocable:

| Irrevocable | Why | Evidence |
|-------------|-----|----------|
| **ALLOW decisions** | Envelope already produced | Envelope is immutable |
| **Executed actions** | Downstream completed | Execution result exists |
| **Created PDOs** | PDO immutability | INV-PDO-001 to INV-PDO-010 |
| **Generated ProofPacks** | Hash sealing | ProofPack manifest sealed |
| **Denial records** | Denial irreversibility | INV-GOV-DENY invariants |
| **Audit trail entries** | Audit integrity | Append-only design |
| **Governance fingerprints** | Boot-time seal | INV-GOV-FP invariants |

### 5.2 Irrevocability Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| IRR-001 | PDO fields are immutable | `frozen=True`, no update method |
| IRR-002 | Denial cannot be reversed | `RETRY_AFTER_DENY_FORBIDDEN` |
| IRR-003 | ProofPack hash is sealed | Manifest hash binding |
| IRR-004 | Audit log is append-only | No delete/update operations |
| IRR-005 | Envelope is frozen | `@dataclass(frozen=True)` |

### 5.3 Reversal Attempts

| Attempt | Result | Evidence |
|---------|--------|----------|
| Update PDO | `PDOImmutabilityError` | INV-PDO-004 |
| Delete PDO | `PDOImmutabilityError` | INV-PDO-004 |
| Retry after denial | `RETRY_AFTER_DENY_FORBIDDEN` | INV-GOV-DENY-001 |
| Mutate envelope | `FrozenInstanceError` | `@dataclass(frozen=True)` |
| Edit audit log | No edit API exists | Append-only design |

---

## 6. How Revocation Is Proven

### 6.1 Revocation Evidence

| Revocation Type | Evidence | Location |
|-----------------|----------|----------|
| **ACM removal** | ACM manifest diff | `manifests/*.yaml` version change |
| **Verb removal** | Capability list diff | ACM manifest |
| **Scope narrowing** | Target scope diff | ACM manifest |
| **ALEX override** | Denial with ALEX rule | `envelope.reason_code` |
| **Denial registry** | Denial record | `logs/denial_registry.db` |
| **Human escalation** | Envelope with `human_required=True` | Envelope audit trail |

### 6.2 Revocation Record Schema

```json
{
  "revocation_type": "ACM_REMOVAL | VERB_REMOVAL | SCOPE_NARROW | ALEX_OVERRIDE | DENIAL | HUMAN_ESCALATION",
  "revoked_at": "2025-12-18T12:00:00+00:00",
  "affected_agent_gid": "GID-07",
  "affected_verb": "EXECUTE",
  "affected_target": "payment:*",
  "revocation_source": "ACM_v1.2.0 | denial_registry | ALEX_rule_9",
  "audit_ref": "rev-abc-123",
  "effective_from": "2025-12-18T12:00:00+00:00",
  "retrospective": false
}
```

### 6.3 Proof Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| REV-PRF-001 | ACM changes are versioned | Version field in manifest |
| REV-PRF-002 | Denial records are timestamped | `denied_at` field in record |
| REV-PRF-003 | ALEX override includes rule reference | Denial detail includes rule ID |
| REV-PRF-004 | Revocation is auditable | Governance audit log |

---

## 7. Revocation and Delegation

### 7.1 Effects on Delegated Authority

| Scenario | Effect | Timeline |
|----------|--------|----------|
| Agent revoked after delegation | Delegation still valid | Envelope is sealed |
| Agent revoked during evaluation | Denial issued | Immediate |
| Verb revoked after delegation | Delegation still valid | Envelope is sealed |
| Verb revoked during evaluation | Denial issued | Immediate |
| Target revoked after delegation | Delegation still valid | Envelope is sealed |
| Target revoked during evaluation | Denial issued | Immediate |

### 7.2 Delegation-Revocation Timeline

```
           Delegation Issued          Revocation Effective
                  │                          │
                  ▼                          ▼
    ──────────────┼──────────────────────────┼──────────────►
                  │                          │        Time
                  │                          │
           ┌──────┴──────┐            ┌──────┴──────┐
           │ Envelope    │            │ ACM reload  │
           │ sealed      │            │ effective   │
           │ (valid)     │            │             │
           └─────────────┘            └─────────────┘
                  │                          │
                  │                          │
    Delegated actions         New intents denied
    can complete              from revoked agent
```

### 7.3 Delegation-Revocation Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| REV-DEL-001 | Sealed envelope survives revocation | Envelope immutability |
| REV-DEL-002 | In-flight revocation causes denial | Real-time ACM check |
| REV-DEL-003 | Completed delegation is final | Execution result exists |

---

## 8. Containment After Revocation

### 8.1 What Revocation Prevents

| Prevented | How |
|-----------|-----|
| New intents from revoked agent | ACM capability check fails |
| Retry of denied intent | Denial registry check fails |
| Scope expansion | ACM scope check fails |
| Unauthorized tool execution | `allowed_tools` check fails |

### 8.2 What Revocation Does Not Prevent

| Not Prevented | Why |
|---------------|-----|
| Completion of in-progress execution | Envelope already sealed |
| Use of existing ProofPacks | ProofPacks are immutable evidence |
| Audit trail access | Read-only by design |
| Historical reporting | Past data is preserved |

---

## 9. Agent University: Revocation Certification

### 9.1 Required Understanding

Before an agent works on revocation-adjacent code:

| Topic | Required Knowledge |
|-------|-------------------|
| **Prospective vs retrospective** | Revocation affects future only |
| **Irrevocability** | What cannot be undone |
| **Evidence requirements** | How revocation is proven |
| **Delegation interaction** | How revocation affects delegated authority |

### 9.2 Certification Requirements

| Work Type | Revocation Certification Required |
|-----------|-----------------------------------|
| ACM manifest modification | Full revocation certification |
| Denial registry integration | Irrevocability certification |
| PDO operations | Irrevocability certification |
| Audit trail operations | Irrevocability certification |
| Governance fingerprinting | Full revocation certification |

---

## 10. Auditor Questions Answered

This contract provides clear answers to:

| Question | Answer | Evidence |
|----------|--------|----------|
| **Can this be undone?** | No — past decisions are immutable | Section 5 |
| **When does revocation take effect?** | ACM: next boot; Denial: immediately | Section 4 |
| **What proves revocation?** | ACM diff, denial record, audit trail | Section 6 |
| **Does revocation affect past actions?** | No — prospective only | Section 4.1 |
| **What survives revocation?** | Sealed envelopes, completed executions, PDOs | Section 7 |

---

## 11. Revocation Summary

| Category | Count |
|----------|-------|
| Revocation mechanisms | 6 |
| Future-only effects | 4 |
| Irrevocable decisions | 7 |
| Evidence types | 6 |
| Invariants | 18 |

---

## 12. Change Authority

This contract can only be modified by:

1. **BENSON (GID-00)** with new PAC reference
2. **ALEX (GID-08)** for governance rule alignment

All changes require:
- PAC with explicit rationale
- Cross-reference to GATEWAY_AUTHORITY_BOUNDARY.md
- Cross-reference to GOVERNANCE_INVARIANTS.md
- No contradiction with immutability invariants

---

**Document Hash:** `[To be computed on commit]`
**Last Verified:** 2025-12-18
