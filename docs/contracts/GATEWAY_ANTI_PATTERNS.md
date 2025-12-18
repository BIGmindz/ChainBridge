# ChainBridge Gateway Anti-Patterns Contract

**Document:** GATEWAY_ANTI_PATTERNS.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Integration Discipline Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GATEWAY-INTEGRATION-DISCIPLINE-01
**Effective Date:** 2025-12-18
**Alignment:** GATEWAY_INTEGRATION_PATTERNS.md, GATEWAY_CAPABILITY_CONTRACT.md

---

## 1. Purpose

This document explicitly defines **forbidden integration patterns** for the ChainBridge Gateway:

- Patterns that bypass proof guarantees
- Patterns that weaken authority boundaries
- Patterns that break containment
- Patterns that create audit gaps

**Every anti-pattern is forbidden.** There is no "discouraged" status. Implementing any anti-pattern is a contract violation.

---

## 2. Anti-Pattern Classification

### 2.1 Severity Levels

| Severity | Meaning | Consequence |
|----------|---------|-------------|
| **CRITICAL** | Breaks proof chain or authority boundary | Immediate remediation required |
| **HIGH** | Creates audit gap or containment breach | Remediation within 24 hours |
| **MEDIUM** | Weakens proof guarantees | Remediation within sprint |

### 2.2 Anti-Pattern Components

Each anti-pattern defines:

| Component | Description |
|-----------|-------------|
| **Anti-Pattern ID** | Unique identifier |
| **Severity** | CRITICAL, HIGH, or MEDIUM |
| **Description** | What the pattern does |
| **Why Forbidden** | Specific invariant(s) violated |
| **Detection** | How to identify this pattern |
| **Correct Pattern** | Reference to approved pattern |

---

## 3. Critical Anti-Patterns

### 3.1 ANTI-001: Direct Model-to-Actuation

**Severity:** CRITICAL

#### Description

A model or agent executes actions directly without Gateway evaluation.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Model/Agent ──────────────▶ Downstream System                │
│         │                           │                           │
│         │    (No Gateway)           │                           │
│         │                           ▼                           │
│         X                      Execution                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| INV-GW-L3-001 | Execution blocked if PDO is None |
| INV-GW-L4-001 | Unknown agents are DENIED |
| AUTH-003 | Authorization requires explicit envelope |
| INT-COMP-001 | Gateway-First must precede all other patterns |

#### Detection

- Code path from model to actuation without `ALEXMiddleware.evaluate_intent()`
- Missing `GatewayDecisionEnvelope` in execution flow
- Downstream system accepts requests without envelope validation

#### Correct Pattern

- INT-PAT-001: Gateway-First Actuation

---

### 3.2 ANTI-002: Log-Only Decision

**Severity:** CRITICAL

#### Description

A system logs that it "would have" checked governance but proceeds without actual evaluation.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Intent ──▶ Log("Governance check") ──▶ Execution             │
│         │              │                                        │
│         │    (Log only, no actual check)                        │
│         X                                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| INV-GW-L2-003 | Decision is exactly ALLOW or DENY |
| INV-GW-L3-001 | Execution blocked if PDO is None |
| REC-001 | Gateway records do not imply endorsement |

**A log entry is not authorization.** Only a valid envelope constitutes authorization.

#### Detection

- Log statements mentioning "governance" without corresponding `evaluate_intent()` call
- Execution proceeds regardless of log content
- No envelope in downstream request

#### Correct Pattern

- INT-PAT-002: Envelope-Before-Execution

---

### 3.3 ANTI-003: Side-Effect Without PDO

**Severity:** CRITICAL

#### Description

A side-effect (database write, API call, state mutation) executes without a PDO in DECIDED/APPROVED state.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Action ──────────────▶ Side-Effect                           │
│         │                      │                                │
│         │    (No PDO check)    │                                │
│         X                      ▼                                │
│                           State Mutated                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| INV-GW-L3-001 | Execution blocked if PDO is None |
| INV-GW-L3-003 | Execution blocked if PDO state is not DECIDED |
| INV-GW-L3-004 | Execution blocked if PDO outcome is not APPROVED |

#### Detection

- State mutation without preceding `require_pdo()` call
- Database writes outside ExecutionEvidenceContext
- API calls without PDO validation

#### Correct Pattern

- INT-PAT-003: PDO-Gated Execution

---

### 3.4 ANTI-004: Dual-Write (Gateway + Shadow)

**Severity:** CRITICAL

#### Description

A system writes to both the governed path (through Gateway) and an ungoverned "shadow" path simultaneously.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│                   ┌──▶ Gateway ──▶ Governed Path                │
│    Intent ────────┤                                             │
│                   └──▶ Shadow System ──▶ Ungoverned Path        │
│                              │                                  │
│         X                    │                                  │
│                              ▼                                  │
│                       Proof Divergence                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| INT-COMP-001 | Gateway-First must precede all other patterns |
| AUTH-003 | Authorization requires explicit envelope |
| INV-PP-001 | ProofPack must contain all PDOs |

**Shadow writes create unauditable actions.** If an action exists without a PDO, proof is impossible.

#### Detection

- Parallel writes to governed and ungoverned systems
- Data in downstream system without corresponding ProofPack
- Correlation IDs that don't appear in governance logs

#### Correct Pattern

- INT-PAT-001: Gateway-First Actuation
- INT-PAT-005: Chained PDO Orchestration

---

### 3.5 ANTI-005: Retrofit Proof After Execution

**Severity:** CRITICAL

#### Description

A system executes first, then creates a PDO or envelope after the fact to "document" the action.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Action ──▶ Execution ──▶ Create PDO                          │
│         │          │              │                             │
│         │          │    (Proof created after action)            │
│         X          ▼              ▼                             │
│               Side-Effect    Fake Proof                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| INV-GW-L2-004 | Envelope is frozen after creation |
| INV-PDO-001 | PDO is immutable after creation |
| INT-COMP-001 | Gateway-First must precede all other patterns |

**Proof must precede execution.** A PDO created after execution is fraud, not proof.

#### Detection

- PDO creation timestamp after execution timestamp
- Envelope audit_ref points to governance log entry after execution
- Correlation ID generated after side-effect

#### Correct Pattern

- INT-PAT-001: Gateway-First Actuation
- INT-PAT-003: PDO-Gated Execution

---

### 3.6 ANTI-006: Envelope Forgery

**Severity:** CRITICAL

#### Description

A system creates or modifies a GatewayDecisionEnvelope outside the Gateway.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Downstream ──▶ Create Envelope ──▶ Self-Authorize            │
│         │               │                                       │
│         │    (Not from Gateway)                                 │
│         X               ▼                                       │
│                   Forged Authorization                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| INV-GW-L2-004 | Envelope is frozen after creation |
| AUTH-001 | Only ALEX rules determine ALLOW/DENY |
| AUTH-002 | Gateway cannot override ALEX decision |

**Only the Gateway produces valid envelopes.** Any other source is forgery.

#### Detection

- Envelope creation outside `gateway/decision_envelope.py`
- Envelope without corresponding governance log entry
- audit_ref that doesn't resolve to real governance record

#### Correct Pattern

- INT-PAT-001: Gateway-First Actuation
- INT-PAT-002: Envelope-Before-Execution

---

## 4. High Severity Anti-Patterns

### 4.1 ANTI-007: Human Escalation Bypass

**Severity:** HIGH

#### Description

A system ignores the `human_required=True` flag and proceeds with execution.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Envelope (human_required=True) ──▶ Execution                 │
│         │                                │                      │
│         │    (Human not consulted)       │                      │
│         X                                ▼                      │
│                                    Unauthorized Action          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| ESC-002 | Human escalation blocks execution |
| DEL-PRE-003 | No delegation with human_required=True |

#### Detection

- Execution proceeds with envelope where `human_required=True`
- No OCC escalation record for human-required intent
- Timestamp analysis shows execution before human decision

#### Correct Pattern

- INT-PAT-004: Human-in-the-Loop Escalation

---

### 4.2 ANTI-008: Denial Swallowing

**Severity:** HIGH

#### Description

A system receives a DENY decision and discards it without routing through DRCP.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Gateway DENY ──▶ System ──▶ /dev/null                        │
│         │               │                                       │
│         │    (Denial not routed)                                │
│         X               ▼                                       │
│                   Denial Lost                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| ESC-001 | All DENY decisions route through DRCP |
| ESC-003 | Escalation is recorded before handoff |

#### Detection

- DENY envelope without corresponding denial registry entry
- Diggy not notified of denial
- Denial count mismatch between Gateway and registry

#### Correct Pattern

- INT-PAT-006: Denial Routing via DRCP

---

### 4.3 ANTI-009: Broken PDO Chain

**Severity:** HIGH

#### Description

A multi-system workflow creates PDOs without proper parent references, breaking the proof chain.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    PDO-1 (Gateway)     PDO-2 (ChainIQ)     PDO-3 (ChainPay)     │
│         │                   │                    │              │
│         │    (No parent_pdo_id references)       │              │
│         X                   X                    X              │
│                                                                 │
│                       Unlinked PDOs                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| INV-PP-001 | ProofPack must contain all PDOs in chain |
| INT-COMP-002 | Envelope validation must precede PDO validation |

#### Detection

- PDO without `parent_pdo_id` when created by downstream system
- Correlation ID mismatch across workflow
- ProofPack missing PDOs from chain

#### Correct Pattern

- INT-PAT-005: Chained PDO Orchestration

---

### 4.4 ANTI-010: Correlation ID Mutation

**Severity:** HIGH

#### Description

A system changes the correlation ID mid-workflow, breaking traceability.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Intent (corr=A) ──▶ Gateway (corr=A) ──▶ Downstream (corr=B) │
│         │                   │                      │            │
│         │    (Correlation changed)                 │            │
│         X                                          ▼            │
│                                             Untraceable         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| INT-COMP-001 | Gateway-First must precede all other patterns |
| INV-PP-001 | ProofPack must contain all PDOs in chain |

**Correlation ID is the proof link.** Changing it severs the chain.

#### Detection

- Different correlation IDs in parent and child PDOs
- Correlation ID not present in all governance logs for workflow
- ProofPack assembly fails due to correlation mismatch

#### Correct Pattern

- INT-PAT-005: Chained PDO Orchestration

---

### 4.5 ANTI-011: Evidence Context Leak

**Severity:** HIGH

#### Description

Evidence is collected outside the ExecutionEvidenceContext or context is shared across unrelated executions.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Context-1 ─────────────────┐                                 │
│         │                     │                                 │
│    Execution-1   Evidence-1   ├──▶ Shared Evidence Store        │
│         │                     │                                 │
│    Context-2 ─────────────────┘                                 │
│         │                                                       │
│         X    (Evidence from multiple contexts mixed)            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| INV-GW-L5-001 | Tool execution requires evidence context |
| DEL-PRE-005 | No delegation without governance event |

#### Detection

- Evidence not bound to specific context
- Same evidence appearing in multiple contexts
- Context reused across executions

#### Correct Pattern

- INT-PAT-007: Evidence Context Binding

---

## 5. Medium Severity Anti-Patterns

### 5.1 ANTI-012: Retry After Deny

**Severity:** MEDIUM

#### Description

A system automatically retries an intent after receiving a DENY decision without material change.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Intent ──▶ DENY ──▶ Retry Same Intent ──▶ DENY ──▶ Retry...  │
│         │         │              │                              │
│         │    (Retry loop without change)                        │
│         X                                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| RETRY_AFTER_DENY_FORBIDDEN | Denial registry blocks retries |

#### Detection

- Same intent hash submitted multiple times after DENY
- Denial registry shows repeated attempts
- No material difference between retry intents

#### Correct Pattern

- INT-PAT-006: Denial Routing via DRCP (denial is final)

---

### 5.2 ANTI-013: Tool Scope Expansion

**Severity:** MEDIUM

#### Description

A downstream system executes tools not in the envelope's `allowed_tools` list.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Envelope (allowed_tools=[A,B]) ──▶ Execute Tool C            │
│         │                                  │                    │
│         │    (Tool C not in allowed list)  │                    │
│         X                                  ▼                    │
│                                      Scope Violation            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| DEL-PRE-004 | No delegation outside allowed_tools |

#### Detection

- Tool execution for tool not in envelope's allowed_tools
- Execution evidence shows tool not listed in envelope

#### Correct Pattern

- INT-PAT-007: Evidence Context Binding

---

### 5.3 ANTI-014: Silent Downstream Failure

**Severity:** MEDIUM

#### Description

A downstream system fails but doesn't record the failure in the evidence context.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORBIDDEN                                 │
│                                                                 │
│    Execution ──▶ Failure ──▶ (No record)                        │
│         │            │                                          │
│         │    (Failure not captured in evidence)                 │
│         X            ▼                                          │
│                 Lost Failure                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Forbidden

| Violated Invariant | Rationale |
|--------------------|-----------|
| DEL-PRE-005 | No delegation without governance event |
| INV-GW-L5-001 | Tool execution requires evidence context |

**Failures are evidence.** Unrecorded failures create audit gaps.

#### Detection

- Downstream system errors without evidence context entry
- ToolExecutionResult missing for failed execution
- ProofPack missing failure evidence

#### Correct Pattern

- INT-PAT-007: Evidence Context Binding

---

## 6. Anti-Pattern Detection Checklist

### 6.1 Code Review Checklist

| Check | Anti-Patterns Detected |
|-------|------------------------|
| Path from model to action without Gateway? | ANTI-001 |
| Execution without envelope validation? | ANTI-001, ANTI-002 |
| State mutation without PDO check? | ANTI-003 |
| Parallel writes to governed and ungoverned? | ANTI-004 |
| PDO creation after execution? | ANTI-005 |
| Envelope creation outside Gateway? | ANTI-006 |
| human_required flag ignored? | ANTI-007 |
| DENY decision not routed? | ANTI-008 |
| PDO missing parent_pdo_id? | ANTI-009 |
| Correlation ID changed? | ANTI-010 |
| Evidence outside context? | ANTI-011 |
| Automatic retry after DENY? | ANTI-012 |
| Tool not in allowed_tools? | ANTI-013 |
| Failure not recorded? | ANTI-014 |

### 6.2 Automated Detection

| Anti-Pattern | Automated Check |
|--------------|-----------------|
| ANTI-001 | Static analysis: execution without Gateway import |
| ANTI-002 | Log analysis: "governance" log without evaluate_intent call |
| ANTI-003 | Coverage: PDO Gate coverage < 100% |
| ANTI-004 | Correlation: data without matching ProofPack |
| ANTI-005 | Timestamp: PDO timestamp > execution timestamp |
| ANTI-006 | Static analysis: GatewayDecisionEnvelope outside gateway/ |
| ANTI-007 | Audit: execution with human_required=True |
| ANTI-008 | Count: DENY envelopes > denial registry entries |
| ANTI-009 | Validation: PDO without parent_pdo_id in chain |
| ANTI-010 | Validation: correlation ID mismatch in workflow |
| ANTI-011 | Coverage: evidence not bound to context |
| ANTI-012 | Denial registry: repeated intent hash |
| ANTI-013 | Audit: tool execution outside allowed_tools |
| ANTI-014 | Audit: downstream errors without evidence |

---

## 7. Remediation Requirements

### 7.1 By Severity

| Severity | Remediation Timeline | Required Actions |
|----------|----------------------|------------------|
| CRITICAL | Immediate | Stop deployment, fix, re-review |
| HIGH | 24 hours | Hotfix, post-incident review |
| MEDIUM | Within sprint | Standard fix, test coverage |

### 7.2 Remediation Artifacts

| Artifact | Purpose |
|----------|---------|
| Root cause analysis | Document how anti-pattern was introduced |
| Fix PR with tests | Demonstrate anti-pattern is blocked |
| Regression test | Prevent future introduction |
| Team training | If pattern suggests knowledge gap |

---

## 8. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | BENSON (GID-00) | Initial contract |

---

## 9. References

- GATEWAY_INTEGRATION_PATTERNS.md — Approved patterns
- GATEWAY_CAPABILITY_CONTRACT.md — Gateway layer definitions
- GATEWAY_AUTHORITY_BOUNDARY.md — Authority scope
- GATEWAY_EXTENSION_RULES.md — Extension constraints
