# ChainBridge Gateway Authority Boundary Contract

**Document:** GATEWAY_AUTHORITY_BOUNDARY.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Authority Boundary Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GATEWAY-AUTHORITY-BOUNDARY-01
**Effective Date:** 2025-12-18
**Alignment:** GATEWAY_CAPABILITY_CONTRACT.md

---

## 1. Purpose

This document defines the **authority boundary** for the ChainBridge Gateway:

- What decisions the Gateway authorizes
- What decisions it records but does not authorize
- What decisions it escalates
- What decisions it is forbidden from making

**Authority is explicit, bounded, and attributable.** No implicit trust. No hidden authority.

---

## 2. Authority Definition

### 2.1 What Authority Means

| Term | Definition |
|------|------------|
| **Authority** | The right to make a binding decision that downstream systems must honor |
| **Authorization** | The act of granting permission for execution |
| **Attribution** | The traceable source of a decision |
| **Delegation** | Transfer of bounded authority to another actor |
| **Revocation** | Withdrawal of previously granted authority |

### 2.2 Gateway Authority Scope

**The Gateway holds authority over the ALLOW/DENY decision for governance-governed intents.**

| Authority Type | Gateway Holds | Evidence |
|----------------|---------------|----------|
| Governance evaluation | Yes | `ALEXMiddleware.evaluate_intent()` |
| Envelope production | Yes | `create_envelope_from_result()` |
| PDO gate enforcement | Yes | `require_pdo()` |
| Business logic evaluation | No | Downstream responsibility |
| Data correctness | No | Application responsibility |
| Execution outcome | No | Downstream responsibility |

---

## 3. Decisions Gateway Authorizes

### 3.1 Authorization Authority

The Gateway authorizes the following decision types:

| Decision Type | Authority Holder | Mechanism | Evidence |
|---------------|------------------|-----------|----------|
| **ALLOW intent** | ALEX (via Gateway) | ACM capability check passed | Envelope with `decision=ALLOW` |
| **DENY intent** | ALEX (via Gateway) | ACM capability check failed | Envelope with `decision=DENY` |
| **Tool execution** | Gateway | Envelope validation passed | `ToolExecutionResult` |
| **Execution context binding** | Gateway | Evidence context created | `ExecutionEvidenceContext` |

### 3.2 Authorization Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| AUTH-001 | Only ALEX rules determine ALLOW/DENY | `ACMEvaluator.evaluate()` |
| AUTH-002 | Gateway cannot override ALEX decision | No bypass path in `ALEXMiddleware` |
| AUTH-003 | Authorization requires explicit envelope | `require_pdo()` blocks without PDO |
| AUTH-004 | Authorization is binary (ALLOW/DENY only) | `GatewayDecision` enum |

---

## 4. Decisions Gateway Records But Does Not Authorize

### 4.1 Recording Without Authority

The Gateway records the following but has no authority over them:

| Decision Type | Why Gateway Records | Why No Authority |
|---------------|---------------------|------------------|
| **Intent content** | Audit trail | Gateway validates schema, not content correctness |
| **Downstream success/failure** | Observability | Execution outcome is downstream responsibility |
| **Model outputs** | Traceability | Model quality is not Gateway's domain |
| **Business metrics** | Telemetry | Business logic is out of scope |

### 4.2 Recording Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| REC-001 | Gateway records do not imply endorsement | Envelope includes `decision` field only |
| REC-002 | Recording does not validate content | Schema validation ≠ content validation |
| REC-003 | Recorded data may be incorrect | See GW-NC-CORR-001 in GATEWAY_NON_CLAIMS.md |

---

## 5. Decisions Gateway Escalates

### 5.1 Escalation Triggers

The Gateway escalates the following decisions:

| Trigger | Escalation Target | Mechanism | Envelope Field |
|---------|-------------------|-----------|----------------|
| **DENY decision** | Diggy (GID-00) | DRCP protocol | `next_hop="GID-00"` |
| **Human approval required** | Human operator | Escalation flag | `human_required=True` |
| **Unknown agent** | None (blocked) | Immediate denial | `reason_code=UNKNOWN_AGENT` |
| **Chain-of-command violation** | Diggy (GID-00) | DRCP routing | `reason_code=CHAIN_OF_COMMAND_VIOLATION` |

### 5.2 Escalation Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| ESC-001 | All DENY decisions route through DRCP | `DenialRecord.next_hop = DIGGY_GID` |
| ESC-002 | Human escalation blocks execution | `human_required=True` → `ToolExecutionDenied` |
| ESC-003 | Escalation is recorded before handoff | `GovernanceAuditLogger` write-then-route |
| ESC-004 | Escalation path is explicit in envelope | `next_hop` field in envelope |

### 5.3 Escalation Path Diagram

```
Intent Received
      │
      ▼
┌─────────────────┐
│  ALEX Evaluate  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 ALLOW      DENY
    │         │
    │         ▼
    │    ┌─────────┐
    │    │  DRCP   │
    │    │ Routing │
    │    └────┬────┘
    │         │
    │    ┌────┴────┐
    │    │         │
    │    ▼         ▼
    │  Diggy    Human
    │ (GID-00)  Escalation
    │    │         │
    │    ▼         ▼
    │ Correction  Manual
    │ Proposal    Review
    │
    ▼
 Execute
```

---

## 6. Decisions Gateway Is Forbidden From Making

### 6.1 Forbidden Authority

The Gateway is explicitly forbidden from:

| Forbidden Decision | Why Forbidden | Enforcement |
|--------------------|---------------|-------------|
| **Execute without PDO** | Fail-closed design | `PDOGateError` raised |
| **Override ALEX decision** | ALEX is sole authority | No bypass code path |
| **Interpret intent** | Gateway validates, not interprets | See GW-NC-INT-001 |
| **Infer missing data** | Explicit data only | Schema validation rejects |
| **Certify models** | Out of scope | See GW-NC-CERT-001 |
| **Guarantee outcomes** | Out of scope | See GW-NC-CORR-001 |
| **Approve as Diggy** | DRCP forbidden verbs | `DIGGY_APPROVE_FORBIDDEN` |
| **Bypass denial registry** | Irreversibility contract | `RETRY_AFTER_DENY_FORBIDDEN` |

### 6.2 Forbidden Authority Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| FRB-001 | No execution without explicit authorization | `require_pdo()` at all entry points |
| FRB-002 | No authority expansion at runtime | ACM is loaded at boot, not modified |
| FRB-003 | No implicit trust assumptions | Every intent evaluated from scratch |
| FRB-004 | No silent authority degradation | Fail-closed on any uncertainty |

---

## 7. Authority Attribution

### 7.1 Attribution Hierarchy

Every decision has traceable attribution:

| Decision | Attributed To | Evidence Field |
|----------|---------------|----------------|
| ALLOW decision | ALEX (GID-08) | `envelope.agent_gid` (evaluated agent), `audit_ref` |
| DENY decision | ALEX (GID-08) | `envelope.reason_code`, `denial_record` |
| Envelope production | Gateway | `envelope.version`, `envelope.audit_ref` |
| Tool execution | Envelope authority | `envelope.audit_ref`, `execution_result` |
| Correction proposal | Diggy (GID-00) | `DiggyResponse.original_intent_id` |

### 7.2 Attribution Chain

```
Intent → ALEX Evaluation → Envelope → Tool Execution → Result
  │           │               │            │            │
  └───────────┴───────────────┴────────────┴────────────┘
                          │
                    Attribution Chain
                          │
            ┌─────────────┴─────────────┐
            │       audit_ref           │
            │  (links all artifacts)    │
            └───────────────────────────┘
```

### 7.3 Attribution Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| ATT-001 | Every envelope has non-empty audit_ref | `__post_init__` validation |
| ATT-002 | audit_ref is unique per evaluation | UUID generation |
| ATT-003 | Attribution survives serialization | `envelope.to_dict()` preserves all fields |
| ATT-004 | Attribution is immutable | `@dataclass(frozen=True)` |

---

## 8. Authority Types Summary

| Category | Count | Scope |
|----------|-------|-------|
| Authorized decisions | 4 | ALLOW, DENY, tool execution, evidence binding |
| Recorded (no authority) | 4 | Intent content, downstream outcomes, model outputs, metrics |
| Escalated decisions | 4 | DENY, human approval, unknown agent, chain-of-command |
| Forbidden decisions | 8 | Execution without PDO, override ALEX, interpret, infer, certify, guarantee, approve as Diggy, bypass denial |
| **Total boundary definitions** | **20** | |

---

## 9. Auditor Questions Answered

This contract provides clear answers to:

| Question | Answer | Evidence |
|----------|--------|----------|
| **Who authorized this?** | ALEX (GID-08) via Gateway evaluation | `envelope.audit_ref` |
| **What authority was exercised?** | ALLOW or DENY for governance-governed intent | `envelope.decision` |
| **What was not authorized?** | Content correctness, business logic, outcomes | Section 4 |
| **Who gets escalation?** | Diggy (GID-00) for DENY; human for `human_required` | Section 5 |
| **What is forbidden?** | 8 explicit forbidden decisions | Section 6 |

---

## 10. Change Authority

This contract can only be modified by:

1. **BENSON (GID-00)** with new PAC reference
2. **ALEX (GID-08)** for governance rule alignment

All changes require:
- PAC with explicit rationale
- Cross-reference to GATEWAY_CAPABILITY_CONTRACT.md
- No contradiction with CANONICAL_INVARIANTS.md

---

**Document Hash:** `[To be computed on commit]`
**Last Verified:** 2025-12-18
