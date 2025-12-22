# ChainBridge Gateway Integration Patterns Contract

**Document:** GATEWAY_INTEGRATION_PATTERNS.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Integration Discipline Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GATEWAY-INTEGRATION-DISCIPLINE-01
**Effective Date:** 2025-12-18
**Alignment:** GATEWAY_CAPABILITY_CONTRACT.md, GATEWAY_DELEGATION_MODEL.md

---

## 1. Purpose

This document defines the **approved integration patterns** for consuming, composing, and interacting with the ChainBridge Gateway:

- How downstream systems must consume Gateway decisions
- How multi-system orchestration must route through Gateway
- Required artifacts and preconditions for each pattern
- Proof guarantees for each approved pattern

**Every pattern is a contract.** Deviation from approved patterns is forbidden. See `GATEWAY_ANTI_PATTERNS.md` for explicitly forbidden deviations.

---

## 2. Pattern Classification

### 2.1 Pattern Status

| Status | Meaning |
|--------|---------|
| **APPROVED** | Pattern is permitted and supported |
| **FORBIDDEN** | Pattern is explicitly blocked (see GATEWAY_ANTI_PATTERNS.md) |

**There is no "RECOMMENDED" or "DISCOURAGED" status.** Patterns are binary: approved or forbidden.

### 2.2 Pattern Components

Each approved pattern defines:

| Component | Description |
|-----------|-------------|
| **Pattern ID** | Unique identifier |
| **Preconditions** | Required state before pattern execution |
| **Data Flow** | Exact sequence of data movement |
| **Proof Guarantees** | What the pattern proves when executed correctly |
| **Violated If** | Conditions that invalidate the pattern |
| **Related Invariants** | Mapping to existing contract invariants |

---

## 3. Approved Patterns

### 3.1 INT-PAT-001: Gateway-First Actuation

**The Gateway is the single decision ingress point for all governed actions.**

#### Definition

All agent actions that mutate state or trigger downstream systems must route through the Gateway before execution.

#### Preconditions

| Precondition | Evidence |
|--------------|----------|
| Agent is registered in ACM | ACM manifest contains agent GID |
| Intent conforms to GatewayIntent schema | Pydantic validation passes |
| Intent includes correlation ID | `correlation_id` field non-empty |

#### Data Flow

```
Agent Intent
     │
     ▼
┌─────────────────┐
│    Gateway      │
│  (Evaluation)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 ALLOW      DENY
    │         │
    ▼         ▼
Envelope   Envelope
 (ALLOW)    (DENY)
    │         │
    ▼         X
Downstream  Blocked
 Execution
```

#### Proof Guarantees

| Guarantee | Evidence |
|-----------|----------|
| Intent was evaluated | Envelope exists with `audit_ref` |
| ALEX rules were applied | Envelope `decision` field populated |
| Decision is attributable | `audit_ref` links to governance log |

#### Violated If

- Action executes without Gateway evaluation
- Action executes before envelope production
- Action executes with invalid envelope

#### Related Invariants

- INV-GW-L4-001: Unknown agents are DENIED
- INV-GW-L3-001: Execution blocked if PDO is None
- AUTH-003: Authorization requires explicit envelope

---

### 3.2 INT-PAT-002: Envelope-Before-Execution

**No downstream system may execute until a valid envelope is received.**

#### Definition

Downstream systems must validate envelope presence and validity before executing delegated authority.

#### Preconditions

| Precondition | Evidence |
|--------------|----------|
| Envelope version is 1.0.0 | `envelope.version == "1.0.0"` |
| Decision is ALLOW | `envelope.decision == ALLOW` |
| audit_ref is non-empty | `envelope.audit_ref != ""` |
| human_required is False | `envelope.human_required == False` |

#### Data Flow

```
Gateway
   │
   ▼
Envelope
   │
   ▼
┌────────────────────────┐
│  Downstream System     │
│  ┌──────────────────┐  │
│  │ Envelope Check   │  │
│  │  - version?      │  │
│  │  - decision?     │  │
│  │  - audit_ref?    │  │
│  │  - human_req?    │  │
│  └────────┬─────────┘  │
│           │            │
│      ┌────┴────┐       │
│      │         │       │
│      ▼         ▼       │
│   Valid    Invalid     │
│      │         │       │
│      ▼         X       │
│   Execute   Reject     │
└────────────────────────┘
```

#### Proof Guarantees

| Guarantee | Evidence |
|-----------|----------|
| Authorization was granted | `decision == ALLOW` |
| Decision is traceable | `audit_ref` points to governance record |
| No human escalation pending | `human_required == False` |

#### Violated If

- Downstream executes without envelope
- Downstream executes with DENY envelope
- Downstream ignores human_required flag
- Downstream accepts envelope with empty audit_ref

#### Related Invariants

- INV-GW-L2-001: Envelope version is always 1.0.0
- INV-GW-L2-005: audit_ref cannot be empty
- DEL-PRE-001: No delegation without ALLOW decision
- DEL-PRE-003: No delegation with human_required=True

---

### 3.3 INT-PAT-003: PDO-Gated Execution

**All execution entry points must validate PDO state before proceeding.**

#### Definition

The PDO Gate pattern requires that execution is blocked unless a valid PDO exists in the correct terminal state.

#### Preconditions

| Precondition | Evidence |
|--------------|----------|
| PDO exists | `pdo is not None` |
| PDO type is valid | `isinstance(pdo, ProvableDecisionObject)` |
| PDO state is DECIDED | `pdo.state == PDOState.DECIDED` |
| PDO outcome is APPROVED | `pdo.outcome == PDOOutcome.APPROVED` |

#### Data Flow

```
Execution Request
        │
        ▼
┌──────────────────┐
│    PDO Gate      │
│  require_pdo()   │
└────────┬─────────┘
         │
    ┌────┴────────────────────┐
    │         │               │
    ▼         ▼               ▼
PDO Valid  PDO Missing   PDO Invalid
    │         │               │
    ▼         X               X
 Proceed   PDOGateError   PDOGateError
```

#### Proof Guarantees

| Guarantee | Evidence |
|-----------|----------|
| Decision was made | PDO in DECIDED state |
| Decision was APPROVED | PDO outcome field |
| Decision is immutable | PDO frozen after creation |

#### Violated If

- Execution proceeds without PDO check
- Execution proceeds with None PDO
- Execution proceeds with PDO in non-terminal state
- Execution proceeds with REJECTED PDO

#### Related Invariants

- INV-GW-L3-001: Execution blocked if PDO is None
- INV-GW-L3-002: Execution blocked if PDO type is invalid
- INV-GW-L3-003: Execution blocked if PDO state is not DECIDED
- INV-GW-L3-004: Execution blocked if PDO outcome is not APPROVED

---

### 3.4 INT-PAT-004: Human-in-the-Loop Escalation

**Human approval is enforced via envelope escalation, blocking execution until resolved.**

#### Definition

When human oversight is required, the Gateway sets `human_required=True` in the envelope, blocking downstream execution until a human operator approves.

#### Preconditions

| Precondition | Evidence |
|--------------|----------|
| ALEX rule requires human approval | ALEX rule evaluation triggers escalation |
| Envelope produced with human_required=True | `envelope.human_required == True` |
| Human operator is available | OCC escalation path configured |

#### Data Flow

```
Intent (requires human approval)
        │
        ▼
┌──────────────────┐
│    Gateway       │
│   (Evaluation)   │
└────────┬─────────┘
         │
         ▼
    ALLOW (with human_required=True)
         │
         ▼
┌──────────────────┐
│  OCC Escalation  │
│  (Human Review)  │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 Approve    Reject
    │         │
    ▼         ▼
Update    Execution
Envelope   Blocked
    │
    ▼
Downstream
Execution
```

#### Proof Guarantees

| Guarantee | Evidence |
|-----------|----------|
| Human was notified | OCC escalation record |
| Human made decision | OCC audit log entry |
| Execution waited for human | Timestamp delta between envelope and execution |

#### Violated If

- Downstream ignores human_required flag
- Execution proceeds before human decision
- Human decision is not recorded

#### Related Invariants

- ESC-002: Human escalation blocks execution
- DEL-PRE-003: No delegation with human_required=True
- AUTH-003: Authorization requires explicit envelope

---

### 3.5 INT-PAT-005: Chained PDO Orchestration

**Multi-system workflows use chained PDOs where each system produces its own PDO referencing the parent.**

#### Definition

When a workflow spans multiple governed systems (e.g., Gateway → ChainIQ → ChainPay), each system produces its own PDO with a reference to the parent PDO, creating a verifiable chain.

#### Preconditions

| Precondition | Evidence |
|--------------|----------|
| Parent PDO exists | `parent_pdo_id` is non-empty |
| Parent PDO is APPROVED | Parent PDO outcome check |
| Child system has delegation | Envelope received from Gateway |
| Correlation ID preserved | Same `correlation_id` across chain |

#### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Chained PDO Workflow                        │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │
│  │ Gateway  │───▶│ ChainIQ  │───▶│ ChainPay │                   │
│  │  PDO-1   │    │  PDO-2   │    │  PDO-3   │                   │
│  └──────────┘    └──────────┘    └──────────┘                   │
│       │              │               │                          │
│       │              │               │                          │
│       ▼              ▼               ▼                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    ProofPack                             │   │
│  │  PDO-1 (Gateway)                                         │   │
│  │    └── PDO-2 (ChainIQ)  [parent_pdo_id = PDO-1]          │   │
│  │          └── PDO-3 (ChainPay) [parent_pdo_id = PDO-2]    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### Proof Guarantees

| Guarantee | Evidence |
|-----------|----------|
| Complete chain is traceable | All PDOs linked via parent_pdo_id |
| Each step was authorized | Each PDO has APPROVED outcome |
| Correlation preserved | Single correlation_id across chain |
| No gaps in chain | ProofPack contains all PDOs |

#### Violated If

- Child PDO created without parent reference
- Correlation ID changes mid-chain
- Any PDO in chain is missing
- PDO created without Gateway delegation

#### Related Invariants

- DEL-PRE-005: No delegation without governance event
- INV-PP-001: ProofPack must contain all PDOs in chain
- AUTH-003: Authorization requires explicit envelope

---

### 3.6 INT-PAT-006: Denial Routing via DRCP

**All DENY decisions route through the Denial Routing and Compliance Protocol (DRCP).**

#### Definition

When the Gateway issues a DENY decision, the envelope is routed through DRCP to Diggy (GID-00) for handling. No DENY decision is silently discarded.

#### Preconditions

| Precondition | Evidence |
|--------------|----------|
| Gateway evaluated intent | Envelope exists |
| Decision is DENY | `envelope.decision == DENY` |
| DRCP routing configured | Diggy endpoint available |
| Denial reason code present | `envelope.reason_code` populated |

#### Data Flow

```
Intent (fails governance)
        │
        ▼
┌──────────────────┐
│    Gateway       │
│   (Evaluation)   │
└────────┬─────────┘
         │
         ▼
      DENY
         │
         ▼
┌──────────────────┐
│      DRCP        │
│  (Denial Router) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Diggy (GID-00)  │
│  Denial Handler  │
└────────┬─────────┘
         │
         ▼
   Denial Record
   (Immutable)
```

#### Proof Guarantees

| Guarantee | Evidence |
|-----------|----------|
| Denial was recorded | Denial record in registry |
| Diggy was notified | DRCP routing log |
| Reason is explicit | `reason_code` in envelope |
| Retry is blocked | Denial registry entry |

#### Violated If

- DENY decision not routed to DRCP
- Denial discarded without recording
- Diggy not notified
- Reason code missing

#### Related Invariants

- ESC-001: All DENY decisions route through DRCP
- ESC-003: Escalation is recorded before handoff
- ESC-004: Escalation path is explicit in envelope

---

### 3.7 INT-PAT-007: Evidence Context Binding

**All tool execution occurs within an ExecutionEvidenceContext that binds evidence to the execution lifecycle.**

#### Definition

Before tool execution, an ExecutionEvidenceContext is created that binds the envelope, PDO, and all execution evidence to a single traceable context.

#### Preconditions

| Precondition | Evidence |
|--------------|----------|
| Valid envelope exists | Envelope validation passed |
| PDO Gate passed | `require_pdo()` returned success |
| Tool is in allowed_tools | `tool_name in envelope.allowed_tools` |
| Governance event emitted | GovernanceEventEmitter.emit() called |

#### Data Flow

```
Tool Execution Request
        │
        ▼
┌────────────────────────────────────────┐
│  ExecutionEvidenceContext Creation     │
│  ┌──────────────────────────────────┐  │
│  │  envelope:    GatewayDecisionEnvelope  │
│  │  pdo:         ProvableDecisionObject   │
│  │  correlation: correlation_id           │
│  │  tools:       allowed_tools list       │
│  │  evidence:    []                       │
│  └──────────────────────────────────┘  │
└────────────────┬───────────────────────┘
                 │
                 ▼
        Tool Execution
                 │
                 ▼
┌────────────────────────────────────────┐
│  Evidence Accumulation                 │
│  - Input hash                          │
│  - Output hash                         │
│  - Duration                            │
│  - Status                              │
└────────────────┬───────────────────────┘
                 │
                 ▼
        ToolExecutionResult
        (bound to context)
```

#### Proof Guarantees

| Guarantee | Evidence |
|-----------|----------|
| Execution is bound to decision | Context contains envelope |
| All evidence captured | Evidence list in context |
| Tool was authorized | Tool in allowed_tools |

#### Violated If

- Tool executes outside context
- Evidence not bound to context
- Context created without envelope
- Tool not in allowed_tools executes

#### Related Invariants

- INV-GW-L5-001: Tool execution requires evidence context
- DEL-PRE-004: No delegation outside allowed_tools
- DEL-PRE-005: No delegation without governance event

---

## 4. Pattern Composition Rules

### 4.1 Pattern Ordering

**Patterns must be applied in a specific order:**

| Order | Pattern | Rationale |
|-------|---------|-----------|
| 1 | INT-PAT-001 (Gateway-First) | Establishes governance evaluation |
| 2 | INT-PAT-002 (Envelope-Before-Execution) | Validates authorization |
| 3 | INT-PAT-003 (PDO-Gated) | Validates decision state |
| 4 | INT-PAT-004 (Human Escalation) | If required, blocks for human |
| 5 | INT-PAT-007 (Evidence Context) | Binds execution to evidence |
| 6 | INT-PAT-005 (Chained PDO) | If multi-system, creates chain |
| 7 | INT-PAT-006 (Denial Routing) | If DENY, routes to Diggy |

### 4.2 Composition Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INT-COMP-001 | Gateway-First must precede all other patterns | No execution path bypasses Gateway |
| INT-COMP-002 | Envelope validation must precede PDO validation | Envelope contains PDO reference |
| INT-COMP-003 | Human escalation must block before Evidence Context | human_required checked before context creation |
| INT-COMP-004 | Denial routing is terminal | DENY path never proceeds to execution |

---

## 5. Integration Checklist

### 5.1 New Downstream System Integration

| Step | Requirement | Evidence |
|------|-------------|----------|
| 1 | Register in ACM manifest | Agent GID in ACM |
| 2 | Implement envelope validation | Code review shows envelope checks |
| 3 | Implement PDO Gate check | `require_pdo()` called |
| 4 | Respect human_required flag | Block if True |
| 5 | Create child PDO with parent reference | `parent_pdo_id` populated |
| 6 | Preserve correlation_id | Same ID through chain |
| 7 | Emit evidence to context | Evidence accumulator called |

### 5.2 Integration Validation

| Validation | Method |
|------------|--------|
| Pattern compliance | Code review against this document |
| Invariant enforcement | Automated tests for each INV-* |
| Proof guarantee verification | ProofPack inspection |

---

## 6. Agent University Binding

### 6.1 Training Requirements

| Agent Role | Required Pattern Knowledge |
|------------|---------------------------|
| All agents | INT-PAT-001, INT-PAT-002 |
| Downstream services | INT-PAT-003, INT-PAT-005, INT-PAT-007 |
| Orchestration systems | INT-PAT-005, INT-PAT-006 |
| Human oversight systems | INT-PAT-004 |

### 6.2 Certification Criteria

To be certified for Gateway integration, an agent or system must demonstrate:

| Criterion | Evidence |
|-----------|----------|
| Pattern knowledge | Exam on pattern definitions |
| Implementation compliance | Code implements all applicable patterns |
| Test coverage | Tests cover all pattern invariants |
| Failure handling | Graceful degradation when pattern violated |

---

## 7. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | BENSON (GID-00) | Initial contract |

---

## 8. References

- GATEWAY_CAPABILITY_CONTRACT.md — Gateway layer definitions
- GATEWAY_DELEGATION_MODEL.md — Delegation preconditions
- GATEWAY_AUTHORITY_BOUNDARY.md — Authority scope
- GATEWAY_ANTI_PATTERNS.md — Forbidden patterns
- GATEWAY_EXTENSION_RULES.md — Extension constraints
