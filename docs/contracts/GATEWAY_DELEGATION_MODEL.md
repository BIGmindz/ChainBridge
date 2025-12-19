# ChainBridge Gateway Delegation Model Contract

**Document:** GATEWAY_DELEGATION_MODEL.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Delegation Boundary Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GATEWAY-AUTHORITY-BOUNDARY-01
**Effective Date:** 2025-12-18
**Alignment:** GATEWAY_AUTHORITY_BOUNDARY.md, GATEWAY_CAPABILITY_CONTRACT.md

---

## 1. Purpose

This document defines the **delegation model** for the ChainBridge Gateway:

- How authority is delegated downstream
- Required preconditions for delegation
- What delegation never implies
- Attribution rules for delegated execution

**Delegation is constrained, traceable, and reversible.** No unbounded delegation. No implicit authority expansion.

---

## 2. Delegation Definition

### 2.1 What Delegation Means

| Term | Definition |
|------|------------|
| **Delegation** | Transfer of bounded authority from Gateway to downstream system |
| **Delegated Authority** | The specific, limited authority a downstream system receives |
| **Delegation Token** | The GatewayDecisionEnvelope that carries delegated authority |
| **Delegate** | The downstream system receiving delegated authority |
| **Delegator** | The Gateway (sole source of delegation) |

### 2.2 Delegation Scope Limits

**Delegation is bounded by the envelope.** No delegate receives more authority than the envelope grants.

| Boundary | Enforcement |
|----------|-------------|
| Tool scope | `envelope.allowed_tools` list |
| Time scope | Envelope is single-use per evaluation |
| Action scope | Envelope authorizes one intent only |
| Target scope | `envelope.intent_target` specifies target |

---

## 3. Delegation Paths

### 3.1 Downstream Systems

The Gateway delegates to these downstream systems:

| Delegate | Authority Received | Delegation Token | Preconditions |
|----------|-------------------|------------------|---------------|
| **ChainPay** | Execute settlement | Envelope with `decision=ALLOW` | Risk score present, ProofPack ID present |
| **ChainIQ** | Compute risk score | Envelope with `decision=ALLOW` | Model ID valid, inputs validated |
| **OCC Operations** | Create PDO records | Envelope with `decision=ALLOW` | Schema valid, correlation ID present |
| **Tool Executor** | Execute tool | Envelope + Evidence Context | Tool in `allowed_tools`, governance event emitted |
| **ProofPack Generator** | Generate proof bundle | Envelope with `decision=ALLOW` | PDO hash sealed, artifacts present |

### 3.2 Delegation Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         GATEWAY                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   Authority Source                          │ │
│  │         (ALEX Evaluation → Envelope Production)             │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │                                    │
│                      Delegation Token                            │
│                    (GatewayDecisionEnvelope)                     │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   ChainPay   │  │   ChainIQ    │  │     OCC      │
    │  Settlement  │  │ Risk Scoring │  │  Operations  │
    └──────────────┘  └──────────────┘  └──────────────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Delegated Action │
                    │    Executed      │
                    └──────────────────┘
```

---

## 4. Delegation Preconditions

### 4.1 Universal Preconditions

**All delegation requires:**

| Precondition | Verification | Failure Mode |
|--------------|--------------|--------------|
| Valid envelope | Schema validation | `EnvelopeVersionError` |
| `decision=ALLOW` | Envelope check | `ToolExecutionDenied(DECISION_NOT_ALLOW)` |
| Non-empty `audit_ref` | `__post_init__` | `EnvelopeMalformedError` |
| `human_required=False` | Envelope check | `ToolExecutionDenied(HUMAN_REQUIRED)` |
| Governance event emitted | Evidence context | `MissingGovernanceEventError` |

### 4.2 Delegate-Specific Preconditions

| Delegate | Additional Preconditions | Evidence |
|----------|--------------------------|----------|
| **ChainPay** | Risk score in envelope metadata; ProofPack ID bound | ALEX rule_2 |
| **ChainIQ** | Model ID in ACM capability scope; Glass-box model type | ALEX rule_1 |
| **OCC Operations** | PDO schema valid; Correlation ID present | INV-PDO invariants |
| **Tool Executor** | Tool name in `allowed_tools`; Evidence context valid | INV-GW-L5 invariants |
| **ProofPack Generator** | PDO hash sealed; All artifacts present | INV-PP invariants |

### 4.3 Precondition Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| DEL-PRE-001 | No delegation without ALLOW decision | Envelope check at delegation point |
| DEL-PRE-002 | No delegation without audit_ref | Envelope validation |
| DEL-PRE-003 | No delegation with human_required=True | Tool executor check |
| DEL-PRE-004 | No delegation outside allowed_tools | Tool allowlist enforcement |
| DEL-PRE-005 | No delegation without governance event | Evidence context required |

---

## 5. What Delegation Never Implies

### 5.1 Non-Implications

**Delegation does NOT imply:**

| What Delegation Does Not Imply | Reality |
|--------------------------------|---------|
| **Correctness of action** | Delegate may execute incorrectly |
| **Success of execution** | Downstream may fail |
| **Data validity** | Gateway validated schema, not data |
| **Business appropriateness** | Business logic is delegate responsibility |
| **Outcome quality** | Quality is not governed by delegation |
| **Permanent authorization** | Delegation is single-use |
| **Expanded scope** | Delegation is bounded by envelope |
| **Endorsement of model** | Model quality is out of scope |

### 5.2 Non-Implication Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| DEL-NI-001 | Delegation does not validate content | See GW-NC-CORR in GATEWAY_NON_CLAIMS.md |
| DEL-NI-002 | Delegation does not guarantee outcomes | See GW-NC-CORR-001 |
| DEL-NI-003 | Delegation scope cannot expand | Envelope is immutable |
| DEL-NI-004 | Delegation is not endorsement | See GW-NC-CERT in GATEWAY_NON_CLAIMS.md |

---

## 6. Attribution Rules

### 6.1 Attribution Hierarchy

Delegated actions carry the following attribution:

| Attribution Layer | Source | Evidence Field |
|-------------------|--------|----------------|
| **Original intent** | Submitting agent | `envelope.agent_gid` |
| **Authorization decision** | ALEX (GID-08) | `envelope.decision`, `envelope.reason_code` |
| **Delegation** | Gateway | `envelope.audit_ref`, `envelope.version` |
| **Execution** | Delegate system | Execution result, timestamps |
| **Evidence binding** | Gateway | `ExecutionEvidenceContext.governance_event_id` |

### 6.2 Actor Attribution Types

| Actor Type | Attribution Marker | Example |
|------------|-------------------|---------|
| **Human** | `actor_type="human"` | Manual approval |
| **System** | `actor_type="system"` | Automated pipeline |
| **Agent** | `actor_type="agent"` | GID-01 through GID-11 |
| **Model** | `actor_type="model"` | LLM intent generation |

### 6.3 Attribution Chain Preservation

**Attribution chain must be preserved across delegation:**

```
Intent Submission (agent_gid)
         │
         ▼
ALEX Evaluation (GID-08)
         │
         ▼
Envelope Production (Gateway)
         │
         ├── audit_ref: "abc-123"
         ├── agent_gid: "GID-07"
         ├── intent_verb: "EXECUTE"
         ├── intent_target: "payment:settle"
         │
         ▼
Delegation to ChainPay
         │
         ├── envelope.audit_ref: "abc-123"
         ├── execution.timestamp: "2025-12-18T..."
         ├── execution.delegate: "chainpay"
         │
         ▼
ProofPack Generation
         │
         └── proofpack.audit_ref: "abc-123"
```

### 6.4 Attribution Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| DEL-ATT-001 | audit_ref preserved across delegation | Delegate must include in all records |
| DEL-ATT-002 | Original agent_gid traceable | Never overwritten by delegate |
| DEL-ATT-003 | Actor type explicit | `actor_type` field required |
| DEL-ATT-004 | Delegation timestamp recorded | UTC timestamp at delegation point |

---

## 7. Delegation Constraints

### 7.1 Scope Constraints

| Constraint | Description | Enforcement |
|------------|-------------|-------------|
| **Single-use** | Envelope authorizes one action | No replay mechanism |
| **Tool-bounded** | Only `allowed_tools` permitted | Tool executor check |
| **Target-bounded** | Only `intent_target` permitted | Envelope validation |
| **Time-bounded** | Envelope valid for evaluation only | No persistence |

### 7.2 Delegation Cannot

| Delegation Cannot | Why | Alternative |
|-------------------|-----|-------------|
| Expand tool scope | Envelope is immutable | Re-evaluation required |
| Transfer to other delegate | Delegation token is envelope-specific | New intent required |
| Authorize multiple actions | Single-use design | Multiple evaluations required |
| Override denial | DENY is final | DRCP correction flow |
| Bypass human_required | Escalation is mandatory | Human approval required |

### 7.3 Constraint Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| DEL-CON-001 | No delegation expansion | Envelope immutable after creation |
| DEL-CON-002 | No delegation transfer | Delegate cannot re-delegate |
| DEL-CON-003 | No multi-action delegation | One intent per envelope |
| DEL-CON-004 | No denial override | DENY → DRCP only path |

---

## 8. Delegation to Specific Systems

### 8.1 ChainPay Delegation

| Aspect | Specification |
|--------|---------------|
| **Authority delegated** | Execute settlement transaction |
| **Preconditions** | Risk score present, ProofPack ID bound, amount validated |
| **Attribution** | `envelope.audit_ref` → `settlement.audit_ref` |
| **Failure handling** | Settlement failure does not invalidate delegation |

### 8.2 ChainIQ Delegation

| Aspect | Specification |
|--------|---------------|
| **Authority delegated** | Compute risk score |
| **Preconditions** | Glass-box model, inputs in schema, model ID valid |
| **Attribution** | `envelope.audit_ref` → `risk_score.audit_ref` |
| **Failure handling** | Score computation failure does not invalidate delegation |

### 8.3 OCC Delegation

| Aspect | Specification |
|--------|---------------|
| **Authority delegated** | Create PDO record, ProofPack artifact |
| **Preconditions** | PDO schema valid, correlation ID present |
| **Attribution** | `envelope.audit_ref` → `pdo.audit_ref` |
| **Failure handling** | PDO creation failure raises error |

---

## 9. Agent University: Delegation Certification

### 9.1 Required Understanding

Before an agent works on delegation-adjacent code:

| Topic | Required Knowledge |
|-------|-------------------|
| **Delegation bounds** | What envelope authorizes and does not authorize |
| **Attribution preservation** | How audit_ref flows through delegation |
| **Precondition enforcement** | What must be true before delegation |
| **Non-implication** | What delegation does not mean |

### 9.2 Certification Requirements

| Work Type | Delegation Certification Required |
|-----------|-----------------------------------|
| ChainPay settlement logic | Full delegation certification |
| ChainIQ model integration | Delegation preconditions certification |
| OCC PDO operations | Attribution preservation certification |
| Tool executor modification | Full delegation certification |
| ProofPack generation | Attribution chain certification |

---

## 10. Delegation Summary

| Category | Count |
|----------|-------|
| Delegation paths | 5 |
| Universal preconditions | 5 |
| Non-implications | 8 |
| Attribution layers | 5 |
| Scope constraints | 4 |
| Invariants | 16 |

---

## 11. Change Authority

This contract can only be modified by:

1. **BENSON (GID-00)** with new PAC reference
2. **ALEX (GID-08)** for governance rule alignment

All changes require:
- PAC with explicit rationale
- Cross-reference to GATEWAY_AUTHORITY_BOUNDARY.md
- No contradiction with CANONICAL_INVARIANTS.md

---

**Document Hash:** `[To be computed on commit]`
**Last Verified:** 2025-12-18
