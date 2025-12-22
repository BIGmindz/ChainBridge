# A1 — Architecture Lock

> **Governance Document** — PAC-BENSON-A1-ARCHITECTURE-LOCK-01
> **Version:** A1
> **Effective Date:** 2025-12-22
> **Authority:** Benson (GID-00)
> **Status:** LOCKED / CANONICAL
> **Change Authority:** Benson (GID-00) — Requires new PAC

---

## 0. ACTIVATION CONTRACT (MANDATORY)

```yaml
AGENT_ACTIVATION_ACK {
  agent_name: "Benson"
  gid: "GID-00"
  role: "Chief Architect & Orchestrator"
  color: "TEAL"
  icon: "🟦🟩"
  authority: "ROOT"
  execution_lane: "ORCHESTRATION"
  mode: "CANONICAL_LOCK"
}
```

---

## 1. SYSTEM DEFINITION (WHAT CHAINBRIDGE IS)

```yaml
SYSTEM_CHAINBRIDGE {
  type: "Event-Native Trust & Settlement Platform"
  function: "Convert real-world events into provable decisions and enforceable outcomes"
  operating_model: "Control-plane / Execution-plane / Proof-plane separation"
}
```

### ChainBridge is NOT:

- ❌ A blockchain
- ❌ A workflow engine
- ❌ A model host
- ❌ A task runner
- ❌ An agent swarm

### ChainBridge IS:

- ✅ A decision control plane
- ✅ A trust enforcement layer
- ✅ A proof-producing system
- ✅ A settlement readiness engine

---

## 2. CANONICAL PLANES (NON-NEGOTIABLE)

```yaml
PLANES {
  CONTROL_PLANE,
  EXECUTION_PLANE,
  PROOF_PLANE
}
```

### 2.1 CONTROL PLANE (Benson / Governance)

**Responsibilities:**
- Decide what is allowed
- Decide what must be proven
- Decide what may execute

```yaml
CONTROL_PLANE {
  stateful: true
  authority: absolute
  executes_code: false
  holds_keys: false
  produces_decisions: true
}
```

**Control plane produces:** → PDO (Proof Decision Outcome)

---

### 2.2 EXECUTION PLANE (Services, Agents, Integrations)

**Responsibilities:**
- Perform actions only after authorization
- Never decide if something should happen

```yaml
EXECUTION_PLANE {
  authority: none
  decision_power: none
  key_material: none
  allowed_actions: "PDO-bound only"
}
```

**Execution plane consumes:** → Signed PDOs

---

### 2.3 PROOF PLANE (Cryptographic Trust)

**Responsibilities:**
- Prove who decided
- Prove what was decided
- Prove nothing was altered

```yaml
PROOF_PLANE {
  mutable: false
  interpretable: false
  discretionary_logic: none
}
```

---

## 3. THE ONLY LEGAL FLOW

```yaml
LEGAL_FLOW {
  Event
    → Control_Plane_Decision
    → PDO_Creation
    → Cryptographic_Signing
    → Enforcement_Gate
    → Execution
    → Settlement / Actuation
    → Audit / Proof
}
```

**Any other flow is INVALID.**

---

## 4. FORBIDDEN FLOWS (HARD FAIL)

```yaml
FORBIDDEN {
  execution_without_pdo,
  execution_with_unsigned_pdo,
  control_plane_execution,
  execution_plane_decisioning,
  proof_plane_logic,
  runtime_identity_claims,
  agent_identity_without_registry
}
```

```yaml
VIOLATION_ACTION {
  behavior: "FAIL_CLOSED"
  remediation: "BLOCK_EXECUTION"
}
```

---

## 5. PDO AS THE ATOMIC UNIT

```yaml
PDO {
  is_required: true
  mutable: false
  signed: true
  replayable: false
  human_override: false
}
```

**No PDO → Nothing happens.**

---

## 6. IDENTITY & AUTHORITY INVARIANTS

```yaml
IDENTITY_INVARIANTS {
  one_gid_per_agent: true
  registry_is_authoritative: true
  runtime_has_no_gid: true
  execution_without_identity: forbidden
}
```

**Runtime ≠ Agent**
**Agent ≠ Runtime**
**This is not negotiable.**

---

## 7. FAILURE SEMANTICS

```yaml
FAILURE_MODEL {
  missing_pdo: FAIL
  invalid_signature: FAIL
  unknown_agent: FAIL
  registry_mismatch: FAIL
  ambiguity: FAIL
}
```

**There are no warnings.**

---

## 8. NON-GOALS (EXPLICIT)

ChainBridge will **never**:

- ❌ Autonomously decide without proof
- ❌ Execute on "confidence"
- ❌ Trust humans to remember rules
- ❌ Allow "temporary bypasses"
- ❌ Optimize for convenience over correctness

---

## 9. ARCHITECTURE LOCK DECLARATION

```yaml
ARCHITECTURE_LOCK {
  version: "A1"
  status: "LOCKED"
  change_authority: "Benson (GID-00)"
  requires_new_pac: true
}
```

---

## CANONICAL PROMPTS (REUSE VERBATIM)

These are machine-control prompts, not chat prompts.

---

### 🔒 CANONICAL PROMPT — ARCHITECTURE CHECK

```
Benson, before proceeding:
- Does this change violate Control / Execution / Proof separation?
- Does this introduce a new decision path?
- Does this allow execution without a signed PDO?

If yes to any → STOP and issue a governance PAC.
```

---

### 🔒 CANONICAL PROMPT — AGENT TASK START

```
You are operating under A1 Architecture Lock.
Confirm:
- Which plane you are in
- What you are forbidden from doing
- What artifact you are allowed to produce

Do not proceed until confirmed.
```

---

### 🔒 CANONICAL PROMPT — EXECUTION REQUEST

```
Is there a signed PDO?
Is the signer in the registry?
Is the execution bound to the PDO?

If not → execution is illegal.
```

---

### 🔒 CANONICAL PROMPT — DRIFT DETECTION

```
Does this introduce ambiguity in identity, authority, or flow?
If yes → escalate to Benson immediately.
```

---

## FINAL STATE

```yaml
A1_ARCHITECTURE_LOCK {
  enforced: true
  drift_allowed: false
  foundation_ready: true
  next_step: "A2_RUNTIME_BOUNDARY_LOCK"
}
```

---

🟦🟩 **BENSON (GID-00)** — Chief Architect & Orchestrator
