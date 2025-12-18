# ChainBridge Gateway Capability Contract

**Document:** GATEWAY_CAPABILITY_CONTRACT.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Gateway Root Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GATEWAY-CONTRACT-01
**Effective Date:** 2025-12-18
**Source Snapshot:** ChainBridge-exec-snapshot_2025-12-18.zip

---

## 1. Purpose

This document is the **canonical capability contract** for the ChainBridge Gateway. It defines:

- What the Gateway is
- What the Gateway does
- What the Gateway enforces
- What the Gateway refuses to do

**This is a contract, not documentation.** Every statement maps to code behavior, an invariant, or an explicit non-claim.

---

## 2. Gateway Definition

### 2.1 Formal Definition

**The Gateway is the deterministic enforcement chokepoint between intent and execution.**

| Property | Definition |
|----------|------------|
| **Scope** | All agent actions that mutate state or trigger downstream systems |
| **Function** | Evaluate intents against governance rules; emit decision envelopes |
| **Authority** | ALEX (GID-08) for governance evaluation; Gateway for envelope production |
| **Mode** | Fail-closed — missing authorization blocks execution |

### 2.2 Gateway Is Not

| What Gateway Is Not | Why |
|---------------------|-----|
| An inference engine | Gateway does not interpret or predict intent |
| A model router | Model selection happens before Gateway evaluation |
| A business logic layer | Gateway enforces governance, not business rules |
| A security perimeter | Gateway enforces access control, not network security |
| An audit system | Gateway produces evidence; other systems store it |

---

## 3. Capability Layers

The Gateway operates in six sequential layers. Each layer has explicit invariants.

### 3.1 Layer Architecture

| Layer ID | Layer Name | Module | Entry Point |
|----------|------------|--------|-------------|
| GW-L1 | Intake | `gateway/validator.py` | `validate_intent()` |
| GW-L2 | Envelope Production | `gateway/decision_envelope.py` | `create_envelope_from_result()` |
| GW-L3 | PDO Gate | `gateway/pdo_gate.py` | `require_pdo()` |
| GW-L4 | Governance Evaluation | `gateway/alex_middleware.py` | `evaluate_intent()` |
| GW-L5 | Tool Binding | `gateway/tool_executor.py` | `execute_tool()` |
| GW-L6 | Boundary Enforcement | `gateway/execution_context.py` | `ExecutionEvidenceContext` |

---

## 4. Layer Specifications

### 4.1 GW-L1: Intake Layer

**Purpose:** Validate incoming intent structure and transition state.

| Capability | Code Location |
|------------|---------------|
| Schema validation | `gateway/validator.py:validate_intent()` |
| State machine enforcement | `gateway/validator.py:assert_transition()` |
| Intent normalization | `gateway/intent_schema.py:GatewayIntent` |

#### Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-GW-L1-001 | Intent must conform to `GatewayIntent` schema | Pydantic validation raises `ValidationError` |
| INV-GW-L1-002 | State transitions follow FSM: RECEIVED → VALIDATED → DECIDED | `assert_transition()` raises `InvalidTransitionError` |
| INV-GW-L1-003 | Unknown fields are rejected | `extra='forbid'` on Pydantic model |

---

### 4.2 GW-L2: Envelope Production Layer

**Purpose:** Produce immutable decision envelopes for downstream consumption.

| Capability | Code Location |
|------------|---------------|
| Envelope creation | `gateway/decision_envelope.py:GatewayDecisionEnvelope` |
| Version locking | `CDE_VERSION = "1.0.0"` constant |
| Reason code mapping | `map_denial_reason()` |

#### Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-GW-L2-001 | Envelope version is always `1.0.0` | `__post_init__` raises `EnvelopeVersionError` |
| INV-GW-L2-002 | All fields populated in all paths | No `Optional` on required fields; explicit defaults |
| INV-GW-L2-003 | Decision is exactly ALLOW or DENY | `GatewayDecision` enum with two values only |
| INV-GW-L2-004 | Envelope is frozen after creation | `@dataclass(frozen=True)` |
| INV-GW-L2-005 | `audit_ref` cannot be empty | `__post_init__` raises `EnvelopeMalformedError` |

---

### 4.3 GW-L3: PDO Gate Layer

**Purpose:** Enforce "No PDO → No execution" at all execution entry points.

| Capability | Code Location |
|------------|---------------|
| PDO existence check | `gateway/pdo_gate.py:require_pdo()` |
| State validation | PDO must be in `DECIDED` state |
| Outcome validation | PDO must have `APPROVED` outcome |

#### Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-GW-L3-001 | Execution blocked if PDO is None | `PDOGateError("No PDO provided")` |
| INV-GW-L3-002 | Execution blocked if PDO type is invalid | `PDOGateError("Invalid PDO type")` |
| INV-GW-L3-003 | Execution blocked if PDO state is not DECIDED | `PDOGateError("PDO not in terminal state")` |
| INV-GW-L3-004 | Execution blocked if PDO outcome is not APPROVED | `PDOGateError("PDO rejected")` |

---

### 4.4 GW-L4: Governance Evaluation Layer

**Purpose:** Evaluate intent against ACM capabilities and ALEX hard constraints.

| Capability | Code Location |
|------------|---------------|
| ACM capability check | `core/governance/acm_evaluator.py:ACMEvaluator` |
| ALEX rule enforcement | `gateway/alex_middleware.py:ALEXMiddleware` |
| Denial routing (DRCP) | `core/governance/drcp.py` |
| Audit logging | `GovernanceAuditLogger.log_decision()` |

#### Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-GW-L4-001 | Unknown agents are DENIED | `UNKNOWN_AGENT` denial code |
| INV-GW-L4-002 | Verbs not in ACM capability list are DENIED | `VERB_NOT_PERMITTED` denial code |
| INV-GW-L4-003 | Targets outside scope are DENIED | `TARGET_NOT_IN_SCOPE` denial code |
| INV-GW-L4-004 | EXECUTE/BLOCK/APPROVE require chain-of-command | `CHAIN_OF_COMMAND_VIOLATION` denial code |
| INV-GW-L4-005 | Diggy (GID-00) cannot EXECUTE/BLOCK/APPROVE | `DIGGY_*_FORBIDDEN` denial codes |
| INV-GW-L4-006 | Retry after DENY is DENIED | `RETRY_AFTER_DENY_FORBIDDEN` denial code |
| INV-GW-L4-007 | Atlas (GID-11) domain violations are DENIED | `ATLAS_DOMAIN_VIOLATION` denial code |
| INV-GW-L4-008 | Every decision is logged before returning | `GovernanceAuditLogger` write-then-return |

---

### 4.5 GW-L5: Tool Binding Layer

**Purpose:** Bind tool execution to envelope authorization.

| Capability | Code Location |
|------------|---------------|
| Envelope validation | `gateway/tool_executor.py:_validate_envelope()` |
| Tool allowlist enforcement | Check `envelope.allowed_tools` |
| Execution telemetry | `emit_tool_execution()` |

#### Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-GW-L5-001 | No envelope → execution blocked | `ToolExecutionDenied(NO_ENVELOPE)` |
| INV-GW-L5-002 | Invalid envelope → execution blocked | `ToolExecutionDenied(INVALID_ENVELOPE)` |
| INV-GW-L5-003 | Envelope decision not ALLOW → execution blocked | `ToolExecutionDenied(DECISION_NOT_ALLOW)` |
| INV-GW-L5-004 | Tool not in allowed_tools → execution blocked | `ToolExecutionDenied(TOOL_NOT_ALLOWED)` |
| INV-GW-L5-005 | human_required=True → execution blocked | `ToolExecutionDenied(HUMAN_REQUIRED)` |

---

### 4.6 GW-L6: Boundary Enforcement Layer

**Purpose:** Causally bind governance evidence to execution.

| Capability | Code Location |
|------------|---------------|
| Evidence context creation | `gateway/execution_context.py:ExecutionEvidenceContext` |
| Event ID validation | `governance_event_id` must be non-empty |
| Audit ref binding | Must match envelope `audit_ref` |

#### Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-GW-L6-001 | Missing governance_event_id blocks execution | `MissingGovernanceEventError` |
| INV-GW-L6-002 | audit_ref must match envelope | `AuditRefMismatchError` |
| INV-GW-L6-003 | Event type must be TOOL_EXECUTION_ALLOWED | `InvalidEventTypeError` |
| INV-GW-L6-004 | Context is frozen after creation | `@dataclass(frozen=True)` |

---

## 5. Actor Responsibility Matrix

### 5.1 Intelligence vs Authority Separation

| Actor | Role | Authority | Responsibility |
|-------|------|-----------|----------------|
| **Model (LLM)** | Intent formulation | None | Propose intents; accept/retry on denial |
| **Gateway** | Enforcement chokepoint | Envelope production, PDO gate | Evaluate governance rules; emit envelopes |
| **ALEX (GID-08)** | Governance evaluation | ALLOW/DENY decision | ACM evaluation; checklist enforcement |
| **Diggy (GID-00)** | Denial routing | Correction proposal | Route denials; propose corrections |
| **Downstream Systems** | Execution | Action execution | Honor envelope decision; execute on ALLOW |

### 5.2 Responsibility Boundaries

| Responsibility | Model | Gateway | ALEX | Diggy | Downstream |
|----------------|-------|---------|------|-------|------------|
| Intent correctness | ✓ | ✗ | ✗ | ✗ | ✗ |
| Schema validation | ✗ | ✓ | ✗ | ✗ | ✗ |
| Governance evaluation | ✗ | ✗ | ✓ | ✗ | ✗ |
| Envelope production | ✗ | ✓ | ✗ | ✗ | ✗ |
| Denial routing | ✗ | ✗ | ✗ | ✓ | ✗ |
| Correction proposal | ✗ | ✗ | ✗ | ✓ | ✗ |
| Action execution | ✗ | ✗ | ✗ | ✗ | ✓ |
| Audit trail storage | ✗ | ✗ | ✗ | ✗ | ✓ |

---

## 6. Gateway Guarantees (Provable)

These guarantees are enforceable from code:

| ID | Guarantee | Evidence |
|----|-----------|----------|
| GW-G-001 | Gateway produces an envelope for every evaluation | `create_envelope_from_result()` always returns |
| GW-G-002 | Envelopes are immutable | `@dataclass(frozen=True)` |
| GW-G-003 | Decision is exactly ALLOW or DENY | `GatewayDecision` enum |
| GW-G-004 | Every execution requires an approved PDO | `require_pdo()` at all entry points |
| GW-G-005 | Denial codes are exhaustive | `ReasonCode` enum with `UNKNOWN` fallback |
| GW-G-006 | Audit ref is present in all envelopes | `__post_init__` validation |

---

## 7. Gateway Refusals (Explicit)

The Gateway explicitly refuses to:

| Refusal | Rationale |
|---------|-----------|
| Execute without PDO | Fail-closed design |
| Execute with rejected PDO | Governance boundary |
| Infer missing intent fields | No defaults; explicit data only |
| Bypass ALEX evaluation | Chokepoint enforcement |
| Mutate envelope after creation | Immutability contract |
| Retry after denial without Diggy | DRCP protocol |
| Allow Atlas to modify runtime code | Domain boundary |

---

## 8. Agent University Requirements

### 8.1 Gateway Literacy Certification

Before an agent touches the following domains, they must demonstrate Gateway literacy:

| Domain | Required Understanding |
|--------|------------------------|
| **ProofPack** | GW-L2 (Envelope), GW-L3 (PDO Gate), GW-L6 (Evidence Binding) |
| **ChainPay** | All layers — financial execution requires full Gateway path |
| **ChainIQ** | GW-L4 (Governance Evaluation) — model output is governed |
| **OCC Operations** | GW-L3 (PDO Gate), GW-L4 (Governance), GW-L5 (Tool Binding) |

### 8.2 Disallowed Work Without Gateway Certification

| Task | Certification Required |
|------|------------------------|
| Implement PDO creation | GW-L3 certification |
| Implement tool execution | GW-L5, GW-L6 certification |
| Modify governance rules | GW-L4 certification + ALEX approval |
| Implement ProofPack generation | Full Gateway certification |
| Implement settlement logic | Full Gateway certification |

---

## 9. Invariant Summary

| Layer | Invariant Count |
|-------|-----------------|
| GW-L1 (Intake) | 3 |
| GW-L2 (Envelope) | 5 |
| GW-L3 (PDO Gate) | 4 |
| GW-L4 (Governance) | 8 |
| GW-L5 (Tool Binding) | 5 |
| GW-L6 (Boundary) | 4 |
| **Total** | **29** |

---

## 10. Change Authority

This contract can only be modified by:

1. **BENSON (GID-00)** with new PAC reference
2. **ATLAS (GID-11)** for structural/scaffolding updates ONLY

All changes require:
- PAC with explicit rationale
- No regression to invariant coverage
- Cross-reference update to CANONICAL_INVARIANTS.md

---

**Document Hash:** `[To be computed on commit]`
**Last Verified:** 2025-12-18
