# A2 — Runtime Boundary Lock

> **Governance Document** — PAC-BENSON-A2-RUNTIME-BOUNDARY-LOCK-01
> **Version:** A2
> **Effective Date:** 2025-12-22
> **Authority:** Benson (GID-00)
> **Status:** LOCKED / CANONICAL
> **Change Authority:** Benson (GID-00) — Requires new PAC
> **Prerequisite:** A1_ARCHITECTURE_LOCK

---

## 0. PURPOSE

Lock the runtime boundary permanently.

This document defines and enforces what execution runtimes can **never** do, regardless of prompt, context, automation, or future tooling.

```
Runtime is a dumb executor.
Agents decide. Governance authorizes. Runtime executes only.
```

---

## 1. DEFINITIONS (CANONICAL)

### 1.1 RUNTIME (EXECUTION SURFACE)

A runtime is:
- GitHub Copilot
- CLI automation
- CI runners
- Orchestration glue
- Any non-agent execution interface

A runtime:
- ❌ Has no GID
- ❌ Is not in AGENT_REGISTRY
- ❌ Has no color
- ❌ Has no icon
- ❌ Has no authority

---

### 1.2 AGENT (DECISION ENTITY)

An agent:
- ✅ Has a GID
- ✅ Is listed in AGENT_REGISTRY.json
- ✅ Owns decisions
- ✅ Owns reasoning
- ✅ Owns accountability

---

## 2. HARD RUNTIME PROHIBITIONS (NON-NEGOTIABLE)

A runtime **MUST NEVER**:

| # | Prohibition |
|---|-------------|
| 1 | Declare or imply a GID |
| 2 | Declare or imply an agent_name |
| 3 | Declare or imply a color or icon |
| 4 | Author or modify governance artifacts |
| 5 | Interpret policy or doctrine |
| 6 | Make decisions (risk, approval, denial) |
| 7 | Create or mutate PDOs |
| 8 | Sign anything (cryptographic or logical) |
| 9 | Escalate authority |
| 10 | Execute without an explicit PAC |

**Any violation = immediate halt.**

```yaml
RUNTIME_PROHIBITIONS {
  gid_declaration: FORBIDDEN
  agent_name_declaration: FORBIDDEN
  color_icon_declaration: FORBIDDEN
  governance_authorship: FORBIDDEN
  policy_interpretation: FORBIDDEN
  decision_making: FORBIDDEN
  pdo_creation: FORBIDDEN
  signing_authority: FORBIDDEN
  authority_escalation: FORBIDDEN
  execution_without_pac: FORBIDDEN
  violation_response: HALT
}
```

---

## 3. MANDATORY RUNTIME BLOCK (ONLY ALLOWED FORM)

Every executable interaction **MUST** begin with:

```yaml
RUNTIME_ACTIVATION_ACK {
  runtime_name: "<tool name>"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "<Agent Name> (GID-XX)"
}
```

**No other fields are permitted.**

### Allowed Fields (Exhaustive)

| Field | Required | Allowed Values |
|-------|----------|----------------|
| runtime_name | ✅ | String (tool name) |
| runtime_type | ✅ | "EXECUTION_RUNTIME" |
| gid | ✅ | "N/A" only |
| authority | ✅ | "DELEGATED" only |
| execution_lane | ✅ | "EXECUTION" only |
| mode | ✅ | "EXECUTABLE" only |
| executes_for_agent | ✅ | "<Agent> (GID-XX)" |

### FORBIDDEN Fields in Runtime Block

- ❌ agent_name
- ❌ color
- ❌ icon
- ❌ role (agent role)
- ❌ Any field implying agent identity

---

## 4. BLOCK ORDER INVARIANT

Mandatory order in all executable artifacts:

```
1. RUNTIME_ACTIVATION_ACK   ← Runtime declares itself first
2. AGENT_ACTIVATION_ACK     ← Agent identity second
3. PAC HEADER               ← PAC metadata third
4. Tasks                    ← Work follows
```

**Any deviation = CI FAIL.**

```yaml
BLOCK_ORDER_INVARIANT {
  position_1: "RUNTIME_ACTIVATION_ACK"
  position_2: "AGENT_ACTIVATION_ACK"
  position_3: "PAC_HEADER"
  position_4: "TASKS"
  enforcement: "CI_GATE"
  deviation_response: "FAIL"
}
```

---

## 5. CI ENFORCEMENT (REQUIRED)

The following **MUST** be enforced at CI:

| Check | Enforcement |
|-------|-------------|
| Runtime block has no GID | HARD_FAIL |
| Runtime block has no agent_name | HARD_FAIL |
| Runtime block appears before agent block | HARD_FAIL |
| Agent block must include valid GID | HARD_FAIL |
| GID must exist in AGENT_REGISTRY.json | HARD_FAIL |
| Runtime cannot modify governance paths | HARD_FAIL |

```yaml
CI_ENFORCEMENT {
  runtime_gid_check: FAIL_IF_PRESENT
  runtime_agent_name_check: FAIL_IF_PRESENT
  block_order_check: FAIL_IF_WRONG
  agent_gid_validation: FAIL_IF_MISSING
  registry_lookup: FAIL_IF_NOT_FOUND
  governance_path_protection: FAIL_IF_RUNTIME_MODIFIES
  mode: FAIL_CLOSED
  warnings: NONE
  overrides: NONE
}
```

---

## 6. FORBIDDEN ESCAPE HATCHES

Explicitly forbidden patterns:

| Pattern | Status |
|---------|--------|
| "I am acting as Agent X" | ❌ FORBIDDEN |
| "On behalf of GID-XX" | ❌ FORBIDDEN |
| "Temporary authority" | ❌ FORBIDDEN |
| "Assumed role" | ❌ FORBIDDEN |
| "Implicit approval" | ❌ FORBIDDEN |
| "Human-in-the-loop exception" | ❌ FORBIDDEN |

**There are no exceptions.**

---

## 7. CANONICAL PROMPTS (REUSE VERBATIM)

### 7.1 Canonical Runtime Prompt

```yaml
RUNTIME_ACTIVATION_ACK {
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "Benson (GID-00)"
}
```

### 7.2 Canonical Agent Prompt

```yaml
AGENT_ACTIVATION_ACK {
  agent_name: "<AGENT>"
  gid: "<GID>"
  color: "<COLOR>"
  icon: "<ICON>"
  role: "<ROLE>"
  execution_lane: "<LANE>"
  authority: "<SCOPE>"
  mode: "EXECUTABLE"
}
```

### 7.3 Runtime Boundary Check Prompt

```
Before executing:
1. Is there a RUNTIME_ACTIVATION_ACK with gid: "N/A"?
2. Is there an AGENT_ACTIVATION_ACK with valid GID?
3. Is the agent in AGENT_REGISTRY.json?
4. Is the runtime block BEFORE the agent block?

If any check fails → HALT
```

---

## 8. ACCEPTANCE CRITERIA

| Check | Status |
|-------|--------|
| Runtime has no GID | ✅ REQUIRED |
| Runtime has no identity | ✅ REQUIRED |
| Agent identity explicit | ✅ REQUIRED |
| Order enforced | ✅ REQUIRED |
| CI fail-closed | ✅ REQUIRED |
| Automation-safe | ✅ REQUIRED |

---

## 9. LOCK STATEMENT

```yaml
A2_RUNTIME_BOUNDARY_LOCK {
  version: "A2"
  status: "LOCKED"
  immutable: true
  violation_type: "STRUCTURAL_ERROR"
  weakening_allowed: false
  foundation_for: "ALL_AUTOMATION"
  next_step: "A3_PDO_ATOMIC_LOCK"
}
```

Once ratified:
- Runtime boundary is immutable
- Violations are structural errors
- No future PAC may weaken this boundary
- All automation builds on this invariant

---

## RELATIONSHIP TO A1

| Lock | Scope | Dependency |
|------|-------|------------|
| A1 | Architecture (three planes) | Foundation |
| A2 | Runtime boundary (execution surface) | Builds on A1 |

A2 enforces the **Execution Plane** boundary defined in A1.

---

🟦🟩 **BENSON (GID-00)** — Chief Architect & Orchestrator
