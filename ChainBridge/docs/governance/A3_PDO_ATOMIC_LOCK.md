# A3 — PDO Atomic Lock

> **Governance Document** — PAC-BENSON-A3-PDO-ATOMIC-LOCK-01
> **Version:** A3
> **Effective Date:** 2025-12-22
> **Authority:** Benson (GID-00)
> **Status:** LOCKED / CANONICAL
> **Change Authority:** Benson (GID-00) — Requires new PAC
> **Prerequisites:** A1_ARCHITECTURE_LOCK, A2_RUNTIME_BOUNDARY_LOCK

---

## 0. PURPOSE

Lock PDO (Proof Decision Outcome) as the **only valid atomic unit** for:
- Decision
- Proof
- Enforcement
- Settlement readiness
- Auditability

**No execution, payment, or actuation may occur outside a PDO.**

```
If PDO does not exist → nothing happens
```

---

## 1. CONTEXT

A1 (Architecture Lock) and A2 (Runtime Boundary Lock) are enforced.
The system now requires a single, indivisible execution primitive.

| Lock | Scope | Status |
|------|-------|--------|
| A1 | Three-plane architecture | ✅ ENFORCED |
| A2 | Runtime boundary | ✅ ENFORCED |
| A3 | PDO atomic unit | 🔒 THIS DOCUMENT |

---

## 2. NON-NEGOTIABLE INVARIANTS (HARD)

```yaml
INVARIANTS {
  one_decision_equals_one_pdo: true
  pdo_required_for_execution: true
  pdo_required_for_settlement: true
  pdo_required_for_audit: true
  partial_pdo_allowed: false
  unsigned_pdo_allowed: false
  mutable_pdo_allowed: false
  side_channel_execution_allowed: false
  post_signature_mutation_allowed: false
}
```

**Violation of any invariant = FAIL-CLOSED SYSTEM HALT**

### Invariant Breakdown

| Invariant | Rule | Violation Response |
|-----------|------|-------------------|
| ONE_DECISION_ONE_PDO | Every decision produces exactly one PDO | HALT |
| PDO_REQUIRED_EXECUTION | No execution without signed PDO | HALT |
| PDO_REQUIRED_SETTLEMENT | No settlement without PDO | HALT |
| PDO_REQUIRED_AUDIT | All audits reference PDO | HALT |
| NO_PARTIAL_PDO | PDO must be complete | HALT |
| NO_UNSIGNED_PDO | PDO must be signed | HALT |
| NO_MUTABLE_PDO | PDO is immutable after creation | HALT |
| NO_SIDE_CHANNEL | No execution paths bypass PDO | HALT |
| NO_POST_SIGN_MUTATION | Nothing changes after signature | HALT |

---

## 3. PDO CANONICAL DEFINITION (LOCKED)

```yaml
PDO {
  pdo_id: UUID                          # Immutable identifier
  decision_type: ENUM                   # Classification
  decision_payload: HASHED              # Content hash
  risk_context: ChainIQ_output          # Risk assessment
  cro_override: OPTIONAL                # Ruby (GID-12) only
  execution_target: ENUM                # ChainPay | Chainlink | External
  settlement_eligibility: BOOLEAN       # Can this settle?
  issued_at: ISO-8601                   # Timestamp
  signature: REQUIRED                   # Cryptographic signature
  signer_gid: REQUIRED                  # Who signed
}
```

### Required Fields

| Field | Required | Immutable | Description |
|-------|----------|-----------|-------------|
| pdo_id | ✅ | ✅ | Unique identifier (UUID) |
| decision_type | ✅ | ✅ | Type classification |
| decision_payload | ✅ | ✅ | Hashed content |
| risk_context | ✅ | ✅ | ChainIQ risk output |
| cro_override | ⚪ | ✅ | Optional CRO decision |
| execution_target | ✅ | ✅ | Target system |
| settlement_eligibility | ✅ | ✅ | Settlement flag |
| issued_at | ✅ | ✅ | ISO-8601 timestamp |
| signature | ✅ | ✅ | Cryptographic proof |
| signer_gid | ✅ | ✅ | Signer identity |

**Anything missing → PDO INVALID**

---

## 4. FORBIDDEN PATTERNS (EXPLICIT)

```yaml
FORBIDDEN {
  "helper_decisions"
  "pre_pdo_execution"
  "soft_settlement_flags"
  "unsigned_decision_paths"
  "risk_only_outputs"
  "execution_without_pdo"
  "pdo_after_execution"
  "mutable_execution_metadata"
}
```

| Pattern | Why Forbidden | Detection |
|---------|---------------|-----------|
| helper_decisions | Creates non-PDO decision paths | Static analysis |
| pre_pdo_execution | Execution before PDO exists | Runtime gate |
| soft_settlement_flags | Bypass settlement gate | Schema validation |
| unsigned_decision_paths | No proof of authority | Signature check |
| risk_only_outputs | Risk without decision | Flow analysis |
| execution_without_pdo | Core violation | Enforcement gate |
| pdo_after_execution | Retroactive legitimization | Timestamp validation |
| mutable_execution_metadata | Post-hoc changes | Immutability check |

**No warnings. No exceptions.**

---

## 5. EXECUTION FLOW (LOCKED)

```
EVENT
  ↓
DECISION ENGINE
  ↓
PDO CREATED
  ↓
PDO SIGNED
  ↓
PDO VALIDATED
  ↓
EXECUTION / SETTLEMENT / ACTUATION
```

### Flow Invariants

```yaml
FLOW_INVARIANTS {
  event_triggers_decision: true
  decision_creates_pdo: true
  pdo_requires_signature: true
  signature_enables_validation: true
  validation_enables_execution: true
  bypass_allowed: false
}
```

**If PDO does not exist → nothing happens**

---

## 6. AGENT AUTHORITY BINDING

| Agent | GID | PDO Scope |
|-------|-----|-----------|
| **Benson** | GID-00 | PDO schema, lifecycle, orchestration |
| **Ruby** | GID-12 | CRO override inside PDO only |
| **Sam** | GID-06 | Threat validation on PDO only |
| **Dan** | GID-07 | CI/CD enforcement of PDO gates |
| **Atlas** | GID-05 | Read-only PDO state inspection |

```yaml
AGENT_PDO_BINDING {
  BENSON: {
    scope: ["schema", "lifecycle", "orchestration"]
    can_create_pdo: true
    can_sign_pdo: true
  }
  RUBY: {
    scope: ["cro_override"]
    can_create_pdo: false
    can_override_risk: true
  }
  SAM: {
    scope: ["threat_validation"]
    can_create_pdo: false
    can_block_pdo: true
  }
  DAN: {
    scope: ["ci_enforcement"]
    can_create_pdo: false
    can_gate_deployment: true
  }
  ATLAS: {
    scope: ["state_inspection"]
    can_create_pdo: false
    write_access: false
  }
}
```

**No agent may bypass PDO.**

---

## 7. CI / GOVERNANCE ENFORCEMENT

Required gates (FAIL-CLOSED):

| Gate | Check | Failure Response |
|------|-------|------------------|
| Schema validation | PDO matches canonical schema | BLOCK |
| Signature presence | signature field exists and valid | BLOCK |
| Immutability check | No post-creation mutations | BLOCK |
| Execution reference | All executions reference PDO | BLOCK |
| Settlement hash | Settlement includes PDO hash | BLOCK |

```yaml
CI_GATES {
  pdo_schema_validation: REQUIRED
  pdo_signature_check: REQUIRED
  pdo_immutability_check: REQUIRED
  execution_pdo_reference: REQUIRED
  settlement_pdo_hash: REQUIRED
  mode: FAIL_CLOSED
}
```

---

## 8. ACCEPTANCE CRITERIA

| Criterion | Status |
|-----------|--------|
| PDO is sole execution unit | ✅ REQUIRED |
| Partial decisions blocked | ✅ REQUIRED |
| Post-sign mutation impossible | ✅ REQUIRED |
| Settlement gated by PDO | ✅ REQUIRED |
| Audit trace = PDO | ✅ REQUIRED |

---

## 9. LOCK DECLARATION

```yaml
A3_PDO_ATOMIC_LOCK {
  version: "A3"
  status: "LOCKED"
  enforced: true
  mutable: false
  scope: "GLOBAL"
  rollback_allowed: false
  next_step: "A4_SETTLEMENT_GATE_LOCK"
}
```

---

## CANONICAL PROMPTS (REUSE VERBATIM)

### 🔒 PDO Existence Check

```
Before any execution:
1. Does a PDO exist for this action?
2. Is the PDO signed?
3. Is the signer in AGENT_REGISTRY?
4. Is the PDO immutable?

If any check fails → HALT
```

### 🔒 PDO Creation Prompt

```
Creating PDO:
- pdo_id: [generated UUID]
- decision_type: [ENUM value]
- decision_payload: [hash]
- risk_context: [ChainIQ output]
- execution_target: [target]
- settlement_eligibility: [true/false]
- issued_at: [ISO-8601]
- signature: [pending]
- signer_gid: [pending]

PDO incomplete until signed.
```

### 🔒 PDO Validation Prompt

```
Validating PDO:
1. All required fields present?
2. pdo_id is valid UUID?
3. signature is cryptographically valid?
4. signer_gid exists in registry?
5. issued_at is valid ISO-8601?
6. No mutations since signing?

All checks must pass.
```

---

## RELATIONSHIP TO A1/A2

| Lock | Scope | Relationship |
|------|-------|--------------|
| A1 | Architecture (three planes) | PDO is the Control Plane output |
| A2 | Runtime boundary | Runtime consumes signed PDOs |
| A3 | PDO atomic unit | Defines the atomic artifact |

A3 defines **what** flows between planes (A1) and **what** runtimes execute (A2).

---

🟦🟩 **BENSON (GID-00)** — Chief Architect & Orchestrator
