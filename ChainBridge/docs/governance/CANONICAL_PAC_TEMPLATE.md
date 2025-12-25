# Canonical PAC Template — G0 Phase 1

> **Governance Document** — PAC-BENSON-G0-GOVERNANCE-CORRECTION-02
> **Version:** G0.2.0
> **Effective Date:** 2025-12-22
> **Authority:** Benson (GID-00)
> **Status:** LOCKED / CANONICAL / MACHINE-ENFORCED

---

## Purpose

This is the **single canonical PAC template** for ChainBridge.

- There is no other valid PAC structure
- All PACs must pass validation against this template
- Validation occurs at: emission, pre-commit, and CI
- No exceptions. No overrides. No warnings.

```
Governance is physics, not policy.
Invalid PACs cannot exist.
```

---

## Template Schema (LOCKED)

```yaml
CANONICAL_PAC_SCHEMA:
  version: "G0.2.0"
  
  required_blocks:
    - RUNTIME_ACTIVATION_ACK
    - AGENT_ACTIVATION_ACK
    - PAC_HEADER
    - GATEWAY_CHECK
    - CONTEXT_AND_GOAL
    - SCOPE
    - FORBIDDEN_ACTIONS
    - CONSTRAINTS
    - TASKS
    - FILES
    - ACCEPTANCE
    - TRAINING_SIGNAL
    - FINAL_STATE
  
  block_order: STRICT
  missing_block: HARD_FAIL
  extra_blocks: ALLOWED_IF_AFTER_REQUIRED
  
  validation_mode: FAIL_CLOSED
  bypass_paths: 0
```

---

## Enforcement Chain (5 GATES)

```
GATE 0: TEMPLATE SELECTION (CANONICAL ONLY)
   ↓
GATE 1: PACK EMISSION VALIDATION (gate_pack.py)
   ↓
GATE 2: PRE-COMMIT HOOK (FAIL-CLOSED)
   ↓
GATE 3: CI MERGE BLOCKER
   ↓
GATE 4: WRAP AUTHORIZATION

No bypass paths exist.
```

---

## Block 0: RUNTIME_ACTIVATION_ACK (MANDATORY FIRST)

```yaml
RUNTIME_ACTIVATION_ACK {
  runtime_name: STRING           # Required: "GitHub Copilot", etc.
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"                     # Required: Must be "N/A"
  authority: "DELEGATED"         # Required: Must be "DELEGATED"
  execution_lane: "EXECUTION"    # Required: Must be "EXECUTION"
  mode: "EXECUTABLE"             # Required
  executes_for_agent: STRING     # Required: "<Agent> (GID-XX)"
  status: "ACTIVE"               # Required
}
```

**Validation Rules:**
- `gid` MUST be "N/A"
- `authority` MUST be "DELEGATED"
- `executes_for_agent` MUST reference valid GID

---

## Block 1: AGENT_ACTIVATION_ACK (MANDATORY SECOND)

```yaml
AGENT_ACTIVATION_ACK {
  agent_name: STRING             # Required: From AGENT_REGISTRY
  gid: STRING                    # Required: "GID-XX" format
  role: STRING                   # Required: From AGENT_REGISTRY
  color: STRING                  # Required: From AGENT_REGISTRY
  icon: STRING                   # Required: From AGENT_REGISTRY
  authority: STRING              # Required: Scope of authority
  execution_lane: STRING         # Required: From AGENT_REGISTRY
  mode: ENUM                     # Required: EXECUTABLE | READ_ONLY | CANONICAL_LOCK
}
```

**Validation Rules:**
- `gid` MUST exist in AGENT_REGISTRY.json
- `color` MUST match registry
- `icon` MUST match registry
- `execution_lane` MUST match registry

---

## Block 2: PAC_HEADER (MANDATORY)

```yaml
PAC_HEADER {
  pac_id: STRING                 # Required: PAC-<AGENT>-<DOMAIN>-<SEQ>
  agent: STRING                  # Required: Agent name
  gid: STRING                    # Required: GID-XX
  color: STRING                  # Required: From registry
  icon: STRING                   # Required: From registry
  authority: STRING              # Required
  execution_lane: STRING         # Required
  mode: ENUM                     # Required
  drift_tolerance: ENUM          # Required: ZERO | LOW | MODERATE
  funnel_stage: STRING           # Required
}
```

**Validation Rules:**
- `pac_id` MUST follow naming convention
- `gid` MUST match AGENT_ACTIVATION_ACK
- All identity fields MUST match registry

---

## Block 3: GATEWAY_CHECK (MANDATORY)

```yaml
GATEWAY_CHECK {
  constitution_exists: BOOLEAN   # Required
  registry_locked: BOOLEAN       # Required
  template_defined: BOOLEAN      # Required
  ci_enforcement: BOOLEAN        # Required
}
```

**Validation Rules:**
- All fields MUST be present
- All fields MUST be `true` for execution PACs

---

## Block 4: CONTEXT_AND_GOAL (MANDATORY)

```yaml
CONTEXT_AND_GOAL {
  context: STRING                # Required: Current state description
  goal: STRING                   # Required: Desired outcome
}
```

**Validation Rules:**
- Both fields MUST be non-empty

---

## Block 5: SCOPE (MANDATORY)

```yaml
SCOPE {
  in_scope: LIST[STRING]         # Required: What IS included
  out_of_scope: LIST[STRING]     # Required: What is NOT included
}
```

**Validation Rules:**
- `in_scope` MUST be a non-empty list
- `out_of_scope` MUST be a non-empty list

---

## Block 6: FORBIDDEN_ACTIONS (MANDATORY)

```yaml
FORBIDDEN_ACTIONS {
  prohibited: LIST[STRING]       # Required: What is STRICTLY PROHIBITED
  failure_mode: "FAIL_CLOSED"    # Required: Fixed value
}
```

**Validation Rules:**
- `prohibited` MUST be a non-empty list
- `failure_mode` MUST be "FAIL_CLOSED"
- No manual overrides of governance gates
- No "near-complete" artifacts

---

## Block 7: CONSTRAINTS (MANDATORY)

```yaml
CONSTRAINTS {
  forbidden: LIST[STRING]        # Required: What is NOT allowed
}
```

**Validation Rules:**
- `forbidden` MUST be a non-empty list

---

## Block 6: TASKS (MANDATORY)

```yaml
TASKS {
  items: LIST[TASK]              # Required: Numbered task list
}

TASK {
  number: INTEGER                # Required: Sequential
  description: STRING            # Required
  owner: STRING                  # Optional: Agent or "RUNTIME"
}
```

**Validation Rules:**
- At least one task MUST exist
- Tasks MUST be numbered sequentially

---

## Block 8: FILES (MANDATORY)

```yaml
FILES {
  create: LIST[STRING]           # Paths to create
  modify: LIST[STRING]           # Paths to modify
  delete: LIST[STRING]           # Paths to delete
}
```

**Validation Rules:**
- At least one of `create`, `modify`, or `delete` MUST be non-empty
- All paths MUST be relative to repo root

---

## Block 9: ACCEPTANCE (MANDATORY)

```yaml
ACCEPTANCE {
  criteria: LIST[CRITERION]      # Required
}

CRITERION {
  description: STRING            # Required
  type: ENUM                     # Required: BINARY | METRIC
}
```

**Validation Rules:**
- At least one criterion MUST exist
- All criteria MUST be verifiable

---

## Block 10: TRAINING_SIGNAL (MANDATORY)

```yaml
TRAINING_SIGNAL {
  program: "Agent University"    # Required: Fixed value
  level: STRING                  # Required: L1-L10
  domain: STRING                 # Required
  competencies: LIST[STRING]     # Required
  evaluation: "Binary"           # Required: Fixed value
  retention: "PERMANENT"         # Required: Fixed value
}
```

**Validation Rules:**
- `program` MUST be "Agent University"
- `level` MUST be L1-L10
- `evaluation` MUST be "Binary"
- `competencies` MUST be non-empty list
- `retention` MUST be "PERMANENT"

---

## Block 11: FINAL_STATE (MANDATORY)

```yaml
FINAL_STATE {
  pac_id: STRING                 # Required: PAC reference
  agent: STRING                  # Required: Agent name
  gid: STRING                    # Required: GID-XX
  governance_compliant: BOOLEAN  # Required: Must be true
  hard_gates: "ENFORCED"         # Required
  execution_complete: BOOLEAN    # Required for WRAPs
  ready_for_next_pac: BOOLEAN    # Required
  blocking_issues: LIST[STRING]  # Required (may be empty)
  authority: "FINAL"             # Required
}
```

**Validation Rules:**
- All fields MUST be present
- `governance_compliant` MUST be true
- `hard_gates` MUST be "ENFORCED"

---

## Validation Modes

| Mode | Trigger | Failure Response |
|------|---------|------------------|
| EMISSION | Agent produces PAC | BLOCK OUTPUT |
| PRE-COMMIT | `git commit` | ABORT COMMIT |
| CI | Pull request | BLOCK MERGE |

---

## Error Codes

| Code | Meaning |
|------|---------|
| `G0-001` | Missing required block |
| `G0-002` | Block order violation |
| `G0-003` | Invalid GID |
| `G0-004` | Registry mismatch |
| `G0-005` | Invalid field value |
| `G0-006` | Missing required field |
| `G0-007` | Runtime has GID |
| `G0-008` | Invalid PAC ID format |
| `G0-009` | Training signal invalid |
| `G0-010` | Constraint violation |
| `G0-011` | Missing FORBIDDEN_ACTIONS |
| `G0-012` | Missing SCOPE |

---

## Correction Protocol

When a correction is issued:

1. Agent is **BLOCKED**
2. Agent must **ACK** deficiencies
3. Agent must **REISSUE** corrected artifact
4. Benson validates
5. Only then is agent **UNBLOCKED**

This protocol is mandatory for every agent.

---

## Validation Command

```bash
# Pre-commit validation
python tools/governance/gate_pack.py --mode precommit

# CI validation
python tools/governance/gate_pack.py --mode ci

# Single file validation
python tools/governance/gate_pack.py --file <path>
```

---

## Lock Declaration

```yaml
CANONICAL_PAC_TEMPLATE_LOCK {
  version: "G0.2.0"
  status: "LOCKED"
  enforcement: "PHYSICS"
  override_allowed: false
  warning_mode: false
  single_template: true
  bypass_paths: 0
  gold_standard: true
}
```

---

🟦🟩 **BENSON (GID-00)** — Chief Architect & Orchestrator
