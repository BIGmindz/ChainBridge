# Canonical PAC Template — G0-G13 Canonical Gate Order

> **Governance Document** — PAC-JEFFREY-GOV-MULTIAGENT-TEMPLATE-UPDATE-001
> **Version:** G0.5.0
> **Effective Date:** 2025-12-30
> **Authority:** Jeffrey (CTO) / Benson (GID-00)
> **Status:** LOCKED / CANONICAL / MACHINE-ENFORCED
> **Amended By:** PAC-BENSON-GOV-GATE-ORDER-LOCK-001

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
Runtime validation is a precondition, not an execution detail.
```

---

## Canonical Gate Order (G0-G13) — IMMUTABLE

```yaml
CANONICAL_GATE_ORDER:
  # PAC-BENSON-GOV-GATE-ORDER-LOCK-001: LOCKED
  gates:
    G0:  "Canonical Preflight"
    G1:  "Runtime Activation & Execution Context (RAXC)"    # MUST PRECEDE G2
    G2:  "Agent Activation"                                  # BLOCKED UNTIL G1 PASS
    G3:  "Context & Objective"
    G4:  "Constraints & Guardrails"
    G5:  "Tasks & Execution Plan"
    G6:  "File & Scope Boundaries"
    G7:  "Execution Controls"
    G8:  "QA, WRAP, BER, Review Gates"
    G9:  "JSRG (Governance PACs only)"
    G10: "Ordering Attestation"
    G11: "Pack Immutability"
    G12: "Training Signal"
    G13: "Positive Closure"

  enforcement:
    raxc_precedes_activation: MANDATORY
    no_agent_without_raxc_pass: MANDATORY
    gate_order_violation: HARD_FAIL
    legacy_ordering_rejection: ACTIVE
```

---

## Template Schema (LOCKED)

```yaml
CANONICAL_PAC_SCHEMA:
  version: "G0.5.0"  # PAC-JEFFREY-GOV-MULTIAGENT-TEMPLATE-UPDATE-001

  required_blocks:
    # G0 — Canonical Preflight
    - CANONICAL_PREFLIGHT
    # G1 — Runtime Activation & Execution Context (RAXC)
    - RUNTIME_ACTIVATION_ACK        # MUST PRECEDE AGENT_ACTIVATION
    - EXECUTION_LANE_DECLARATION    # NEW: Explicit lane binding
    # G2 — Agent Activation
    - AGENT_ACTIVATION_ACK          # BLOCKED UNTIL RAXC PASS
    # G3 — Context & Objective
    - PAC_HEADER
    - CONTEXT_AND_GOAL
    # G4 — Constraints & Guardrails
    - FORBIDDEN_ACTIONS
    - CONSTRAINTS
    # G5 — Tasks & Execution Plan
    - TASKS
    # G6 — File & Scope Boundaries
    - SCOPE
    - FILES
    # G7 — Execution Controls
    - EXECUTION_LOOP_OVERRIDE
    # G8 — QA, WRAP, BER, Review Gates
    - REVIEW_GATE                   # NEW: Explicit review gate
    - ACCEPTANCE
    # G9 — JSRG (conditional)
    - JSRG_GATE                     # Governance PACs only
    # G10 — Ordering Attestation
    - ORDERING_ATTESTATION          # NEW: Gate order compliance
    # G11 — Pack Immutability
    - PACK_IMMUTABILITY             # NEW: Lock state
    # G12 — Training Signal
    - TRAINING_SIGNAL
    # G13 — Positive Closure
    - FINAL_STATE
    - GOLD_STANDARD_CHECKLIST

  block_order: STRICT
  missing_block: HARD_FAIL
  extra_blocks: ALLOWED_IF_AFTER_REQUIRED

  validation_mode: FAIL_CLOSED
  bypass_paths: 0

  # Gate ordering enforcement
  gate_order_enforcement:
    raxc_before_activation: MANDATORY
    activation_blocked_without_raxc: true
    legacy_ordering_rejection: true
    gate_sequence: "G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7 → G8 → G9 → G10 → G11 → G12 → G13"

  # Checklist enforcement
  checklist_enforcement:
    required: true
    item_count: 18                 # Updated for G0-G13 compliance
    pass_threshold: "18/18"
    partial_pass: false
    missing_checklist: HARD_FAIL

  # Execution loop enforcement
  execution_loop_enforcement:
    wrap_required: true
    ber_required: true
    bypass_authorized: false
    canonical_loop: "PAC → Cody Execution → WRAP → Benson Execution Review → BER → Jeffrey Review"

  # PDO enforcement (PAC-JEFFREY-GOV-PDO-MANDATORY-EXECUTION-GATE-001)
  pdo_enforcement:
    pdo_required: true
    gates:
      - GOV-PDO-001  # Ingress Gate
      - GOV-PDO-002  # Pre-Execution Gate
      - GOV-PDO-003  # Settlement Gate
      - GOV-PDO-004  # WRAP Attachment Gate
      - GOV-PDO-005  # BER PDO Binding Gate
    soft_enforcement: false
    implicit_pdo: false
    backfill_pdo: false
```

---

## Enforcement Chain (G0-G13 GATE SEQUENCE)

```
G0:  CANONICAL PREFLIGHT
     ↓ [template, authority, hierarchy verified]
G1:  RUNTIME ACTIVATION & EXECUTION CONTEXT (RAXC)
     ↓ [runtime validated, context locked] ← MUST PASS BEFORE G2
G2:  AGENT ACTIVATION
     ↓ [agent identity confirmed, GID bound]
G3:  CONTEXT & OBJECTIVE
     ↓ [intent declared, goal scoped]
G4:  CONSTRAINTS & GUARDRAILS
     ↓ [boundaries locked, forbidden actions defined]
G5:  TASKS & EXECUTION PLAN
     ↓ [work items enumerated]
G6:  FILE & SCOPE BOUNDARIES
     ↓ [paths declared, scope bounded]
G7:  EXECUTION CONTROLS
     ↓ [loop override, mutation control]
G8:  QA, WRAP, BER, REVIEW GATES
     ↓ [obligations declared, review gates set]
G9:  JSRG (GOVERNANCE PACs ONLY)
     ↓ [Jeffrey self-review — conditional]
G10: ORDERING ATTESTATION
     ↓ [gate sequence compliance verified]
G11: PACK IMMUTABILITY
     ↓ [lock state declared]
G12: TRAINING SIGNAL
     ↓ [competencies registered]
G13: POSITIVE CLOSURE
     ↓ [final state, checklist complete]

No bypass paths exist.
Legacy G0-G7 ordering: REJECTED AT INGRESS
```

---

## G0 — CANONICAL PREFLIGHT (Block 0)

```yaml
CANONICAL_PREFLIGHT {
  template_loaded: ENUM          # Required: VERIFIED | FAILED
  gate_order_verified: ENUM      # Required: VERIFIED | FAILED
  single_container: ENUM         # Required: SATISFIED | FAILED
  persona_hierarchy: STRING      # Required: "Alex → Jeffrey → Benson → Agents"
  drift_tolerance: ENUM          # Required: ZERO
  gold_standard_required: BOOLEAN # Required: true
}
```

**Validation Rules:**
- `template_loaded` MUST be VERIFIED
- `gate_order_verified` MUST be VERIFIED
- `persona_hierarchy` MUST match canonical hierarchy
- `drift_tolerance` MUST be ZERO

---

## G1 — RUNTIME ACTIVATION & EXECUTION CONTEXT (RAXC) (Block 1)

> **PAC-BENSON-GOV-GATE-ORDER-LOCK-001:** RAXC MUST precede Agent Activation.
> No agent MAY activate unless RAXC = PASS.

```yaml
RUNTIME_ACTIVATION_ACK {
  # Runtime Identity
  runtime_name: STRING           # Required: "GitHub Copilot", etc.
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"                     # Required: Must be "N/A"
  authority: "DELEGATED"         # Required: Must be "DELEGATED"
  
  # Execution Context (RAXC)
  execution_context: {
    execution_lane: ENUM         # Required: GOVERNANCE | EXECUTION | READ_ONLY
    mode: ENUM                   # Required: EXECUTABLE | READ_ONLY | CANONICAL_LOCK
    runtime_mutation: ENUM       # Required: ALLOWED | FORBIDDEN
    decision_authority: ENUM     # Required: NONE | LIMITED | FULL
    environment: ENUM            # Required: LOCKED | UNLOCKED
  }
  
  executes_for_agent: STRING     # Required: "<Agent> (GID-XX)"
  raxc_status: ENUM              # Required: ACTIVE | FAILED
}
```

**Validation Rules:**
- `gid` MUST be "N/A"
- `authority` MUST be "DELEGATED"
- `executes_for_agent` MUST reference valid GID
- `raxc_status` MUST be ACTIVE for agent activation to proceed
- **HARD GATE:** If `raxc_status` ≠ ACTIVE → Block G2 entirely

---

## G1.1 — EXECUTION_LANE DECLARATION (Block 1.1)

> **NEW BLOCK:** Explicit lane binding required for all PACs.

```yaml
EXECUTION_LANE_DECLARATION {
  lane: ENUM                     # Required: GOVERNANCE | EXECUTION | READ_ONLY
  
  permitted_actions: LIST[STRING] # Required: What IS allowed in this lane
  forbidden_actions: LIST[STRING] # Required: What is NOT allowed in this lane
  cross_lane_effects: ENUM       # Required: FORBIDDEN | CONTROLLED | ALLOWED
  
  mutation_scope: {
    template_mutation: BOOLEAN   # Required
    schema_mutation: BOOLEAN     # Required
    registry_mutation: BOOLEAN   # Required
    runtime_mutation: BOOLEAN    # Required
  }
}
```

**Validation Rules:**
- `lane` MUST be one of: GOVERNANCE, EXECUTION, READ_ONLY
- `permitted_actions` MUST be non-empty
- `forbidden_actions` MUST be non-empty
- `cross_lane_effects` defaults to FORBIDDEN unless explicitly authorized

**Lane Enforcement:**
| Lane | Permitted | Forbidden |
|------|-----------|-----------|
| GOVERNANCE | Template/schema modification, registry updates | Execution logic, runtime behavior |
| EXECUTION | Code execution, file modification | Schema mutation, governance changes |
| READ_ONLY | Read operations, validation | All mutations |

---

## G2 — AGENT ACTIVATION (Block 2)

> **BLOCKED UNTIL G1 (RAXC) = PASS**

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
  
  # Gate dependency
  raxc_gate_passed: BOOLEAN      # Required: Must be true (validated from G1)
}
```

**Validation Rules:**
- `gid` MUST exist in AGENT_REGISTRY.json
- `color` MUST match registry
- `icon` MUST match registry
- `execution_lane` MUST match registry
- `raxc_gate_passed` MUST be true — **HARD FAIL if false**

---

## G3 — CONTEXT & OBJECTIVE (Blocks 3-4)

### PAC_HEADER (Block 3)

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

### CONTEXT_AND_GOAL (Block 4)

```yaml
CONTEXT_AND_GOAL {
  context: STRING                # Required: Current state description
  goal: STRING                   # Required: Desired outcome
  objective: STRING              # Optional: More specific objective
}
```

**Validation Rules:**
- `context` and `goal` MUST be non-empty

---

## G4 — CONSTRAINTS & GUARDRAILS (Blocks 5-6)

### FORBIDDEN_ACTIONS (Block 5)

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

### CONSTRAINTS (Block 6)

```yaml
CONSTRAINTS {
  forbidden: LIST[STRING]        # Required: What is NOT allowed
  required: LIST[STRING]         # Required: What MUST be done
  guardrails: LIST[STRING]       # Optional: Additional boundaries
}
```

**Validation Rules:**
- `forbidden` MUST be a non-empty list
- `required` MUST be a non-empty list

---

## G5 — TASKS & EXECUTION PLAN (Block 7)

```yaml
TASKS {
  items: LIST[TASK]              # Required: Numbered task list
  stop_on_failure: BOOLEAN       # Required: Default true
}

TASK {
  number: INTEGER                # Required: Sequential (T1, T2, ...)
  description: STRING            # Required
  owner: STRING                  # Required: Agent GID or "RUNTIME"
  authority: ENUM                # Required: EXECUTE | ATTEST | REJECT
}
```

**Validation Rules:**
- At least one task MUST exist
- Tasks MUST be numbered sequentially
- Each task MUST have an owner
- `stop_on_failure` SHOULD be true for fail-closed semantics

---

## G6 — FILE & SCOPE BOUNDARIES (Blocks 8-9)

### SCOPE (Block 8)

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

### FILES (Block 9)

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

## G7 — EXECUTION CONTROLS (Block 10)

```yaml
EXECUTION_LOOP_OVERRIDE {
  default_execution_loop: STRING # Required: Canonical loop declaration

  enforcement_rules: {
    cody_must_return_wrap: BOOLEAN       # Required: true
    cody_cannot_declare_closure: BOOLEAN # Required: true
    benson_must_receive_wrap: BOOLEAN    # Required: true
    benson_must_emit_ber: BOOLEAN        # Required: true
    ber_is_sole_closure: BOOLEAN         # Required: true
    no_ber_means_incomplete: BOOLEAN     # Required: true
  }

  benson_execution_bypass: {
    bypass_authorized: BOOLEAN   # Required: Default false
    canonical_loop_required: BOOLEAN # Required: Default true
  }

  wrap_obligation: {
    wrap_required: BOOLEAN       # Required
    wrap_schema: STRING          # Required: Schema reference
    failure_to_wrap: "HARD_FAIL" # Required: Fixed value
  }

  ber_obligation: {
    ber_required: BOOLEAN        # Required
    ber_is_authoritative: BOOLEAN # Required: true
    positive_closure_via_ber_only: BOOLEAN # Required: true
  }
}
```

**Validation Rules:**
- `default_execution_loop` MUST be: "PAC → Cody Execution → WRAP → Benson Execution Review → BER → Jeffrey Review"
- All `enforcement_rules` fields MUST be `true`
- `bypass_authorized` MUST be `false` unless explicit override
- `canonical_loop_required` MUST be `true`
- `wrap_required` MUST be `true`
- `failure_to_wrap` MUST be "HARD_FAIL"

---

## G8 — QA, WRAP, BER, & REVIEW GATES (Blocks 11-12)

### REVIEW_GATE (Block 11) — NEW

> **NEW BLOCK:** Explicit review gate declaration required.

```yaml
REVIEW_GATE {
  reviewer: STRING               # Required: "<Agent> (GID-XX)"
  reviewer_authority: ENUM       # Required: ATTEST | REJECT | ACKNOWLEDGE
  
  permitted_outcomes: LIST[ENUM] # Required: [ACKNOWLEDGE, REJECT, DEFER]
  
  wrap_required: BOOLEAN         # Required
  ber_required: BOOLEAN          # Required
  human_review_required: BOOLEAN # Required
  
  fail_closed: BOOLEAN           # Required: Default true
  
  final_state: {
    wrap_required: BOOLEAN       # Required
    ber_required: BOOLEAN        # Required
    human_review_required: BOOLEAN # Required
  }
}
```

**Validation Rules:**
- `reviewer` MUST reference valid GID
- `fail_closed` MUST be true unless explicitly authorized
- `permitted_outcomes` MUST be non-empty

---

### ACCEPTANCE (Block 12)

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

## G9 — JSRG (Governance PACs Only) (Block 13)

> **Conditional:** Required for GOVERNANCE lane PACs only.

```yaml
JSRG_GATE {
  # Jeffrey Self-Review Gate (JSRG-01)
  gate_id: "JSRG-01"             # Required: Fixed value
  reviewer: "Jeffrey (CTO)"      # Required: Fixed value
  
  attestations: {
    canon_compliance: ENUM       # Required: VERIFIED | FAILED
    mandatory_blocks_enforced: ENUM # Required: VERIFIED | FAILED
    authority_boundaries_intact: ENUM # Required: VERIFIED | FAILED
    gate_ordering_sound: ENUM    # Required: VERIFIED | FAILED
    drift_risk: ENUM             # Required: NONE | LOW | HIGH
  }
  
  jsrg_result: ENUM              # Required: PASS | FAIL
}
```

**Validation Rules:**
- Required ONLY when `execution_lane` = GOVERNANCE
- All attestations MUST be VERIFIED for `jsrg_result` = PASS
- `drift_risk` MUST be NONE for governance PACs
- Missing JSRG on governance PAC = HARD_FAIL

---

## G10 — ORDERING ATTESTATION (Block 14) — NEW

> **NEW BLOCK:** Gate order compliance verification.

```yaml
ORDERING_ATTESTATION {
  raxc_precedes_activation: BOOLEAN  # Required: true
  gate_sequence_compliant: BOOLEAN   # Required: true
  fail_closed_preserved: BOOLEAN     # Required: true
  replay_ambiguity_eliminated: BOOLEAN # Required: true
  
  gate_order_hash: STRING        # Optional: Hash of gate sequence
}
```

**Validation Rules:**
- All boolean fields MUST be true
- Attestation MUST be present for all PACs
- False attestation = HARD_FAIL

---

## G11 — PACK IMMUTABILITY (Block 15) — NEW

> **NEW BLOCK:** Lock state declaration.

```yaml
PACK_IMMUTABILITY {
  state: ENUM                    # Required: LOCKED | UNLOCKED
  lock_type: ENUM                # Required: CANONICAL | SESSION | NONE
  mutation_allowed: BOOLEAN      # Required: false for LOCKED
}
```

**Validation Rules:**
- `state` = LOCKED for canonical/governance PACs
- `mutation_allowed` MUST be false when `state` = LOCKED

---

## G12 — TRAINING SIGNAL (Block 16)

```yaml
TRAINING_SIGNAL {
  program: "Agent University"    # Required: Fixed value
  level: STRING                  # Required: L1-L10
  domain: STRING                 # Required
  competencies: LIST[STRING]     # Required
  evaluation: "Binary"           # Required: Fixed value
  retention: "PERMANENT"         # Required: Fixed value
  
  signal_id: STRING              # Required: TS-XX format
  signal_text: STRING            # Required: Training signal content
}
```

**Validation Rules:**
- `program` MUST be "Agent University"
- `level` MUST be L1-L10
- `evaluation` MUST be "Binary"
- `competencies` MUST be non-empty list
- `retention` MUST be "PERMANENT"
- `signal_id` MUST follow TS-XX format

---

## G13 — POSITIVE CLOSURE (Blocks 17-18)

### FINAL_STATE (Block 17)

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

### GOLD_STANDARD_CHECKLIST (Block 18) — MANDATORY TERMINAL

```yaml
GOLD_STANDARD_CHECKLIST {
  # PAC-JEFFREY-GOV-MULTIAGENT-TEMPLATE-UPDATE-001: Updated for G0-G13
  # All 18 items must be checked [✓] for PAC to be valid

  items: [
    "[✓] Canonical PAC template used",
    "[✓] G0: Canonical preflight verified",
    "[✓] G1: RAXC validated before agent activation",
    "[✓] G1.1: Execution lane explicitly declared",
    "[✓] G2: Agent activation confirmed (after RAXC pass)",
    "[✓] G3: Context and objective declared",
    "[✓] G4: Constraints & guardrails locked",
    "[✓] G5: Tasks scoped and non-expansive",
    "[✓] G6: File scope explicitly bounded",
    "[✓] G7: Execution controls configured",
    "[✓] G8: WRAP/BER/Review gates declared",
    "[✓] G9: JSRG gate present (if governance)",
    "[✓] G10: Ordering attestation verified",
    "[✓] G11: Pack immutability declared",
    "[✓] G12: Training signal registered",
    "[✓] G13: Positive closure achieved",
    "[✓] Fail-closed posture enforced",
    "[✓] Gate sequence G0→G13 followed"
  ]

  status: "PASS (18/18)"         # Required: Must be PASS (18/18)
}
```

**Validation Rules:**
- All 18 checklist items MUST be present
- All 18 items MUST be checked [✓]
- `status` MUST be "PASS (18/18)"
- No items may be removed or modified
- No partial compliance (17/18 = FAIL)

**Enforcement:**
- Missing checklist: HARD_FAIL
- Missing items: HARD_FAIL
- Wrong count: HARD_FAIL
- Unchecked items: HARD_FAIL

---

## Validation Modes

| Mode | Trigger | Failure Response |
|------|---------|------------------|
| EMISSION | Agent produces PAC | BLOCK OUTPUT |
| PRE-COMMIT | `git commit` | ABORT COMMIT |
| CI | Pull request | BLOCK MERGE |
| INGRESS | PAC received by Benson | HARD_FAIL + REJECT |

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
| `G0-013` | Missing GOLD_STANDARD_CHECKLIST |
| `G0-014` | Checklist incomplete (not 18/18) |
| `G0-015` | Checklist item unchecked |
| `G0-016` | CHECKLIST_STATUS missing or invalid |
| `G0-017` | Missing RAXC block |
| `G0-018` | RAXC placed after Agent Activation |
| `G0-019` | Missing EXECUTION_LANE_DECLARATION |
| `G0-020` | Missing EXECUTION_LOOP_OVERRIDE |
| `G0-021` | WRAP obligation not declared |
| `G0-022` | BER obligation not declared |
| `G0-023` | Missing REVIEW_GATE block |
| `G0-024` | Missing ORDERING_ATTESTATION |
| `G0-025` | Missing PACK_IMMUTABILITY |
| `G0-026` | Missing JSRG_GATE (governance PAC) |
| `G0-027` | Gate sequence violation (G0-G13) |
| `G0-028` | Legacy gate order (G0-G7) rejected |
| `G0-029` | RAXC status not ACTIVE |
| `G0-030` | Agent activation before RAXC pass |
| `PDO_INGRESS_001` | Execution rejected: No valid PDO_ID |
| `PDO_EXEC_001` | Dispatch blocked: PDO not in valid state |
| `PDO_SETTLE_001` | Settlement halted: PDO outcome required |
| `PDO_WRAP_001` | WRAP rejected: PDO reference required |
| `PDO_BER_001` | BER rejected: PDO decision binding required |

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

# Gate order validation
python tools/governance/gate_pack.py --validate-gate-order <path>
```

---

## Lock Declaration

```yaml
CANONICAL_PAC_TEMPLATE_LOCK {
  version: "G0.5.1"
  status: "LOCKED"
  enforcement: "PHYSICS"
  override_allowed: false
  warning_mode: false
  single_template: true
  bypass_paths: 0
  gold_standard: true
  
  # PAC-BENSON-GOV-GATE-ORDER-LOCK-001
  gate_order_locked: true
  canonical_gate_sequence: "G0→G1→G2→G3→G4→G5→G6→G7→G8→G9→G10→G11→G12→G13"
  raxc_before_activation: MANDATORY
  legacy_ordering_rejected: true
  
  # PAC-JEFFREY-GOV-MULTIAGENT-TEMPLATE-UPDATE-001
  execution_lane_declared: true
  review_gate_enforced: true
  ordering_attestation_required: true
  pack_immutability_required: true
  jsrg_required_for_governance: true
  
  # PAC-JEFFREY-GOV-PDO-MANDATORY-EXECUTION-GATE-001
  pdo_enforcement_active: true
  pdo_gates:
    - GOV-PDO-001
    - GOV-PDO-002
    - GOV-PDO-003
    - GOV-PDO-004
    - GOV-PDO-005
  pdo_soft_enforcement: false
  
  checklist_items: 18
  checklist_threshold: "18/18"
}
```

---

## Amendment History

| Version | PAC Reference | Change |
|---------|---------------|--------|
| G0.4.0 | PAC-BENSON-034 | Added PRE_FLIGHT_GOVERNANCE_STAMP, EXECUTION_LOOP_OVERRIDE |
| G0.5.0 | PAC-BENSON-GOV-GATE-ORDER-LOCK-001 | Locked G0-G13 gate ordering |
| G0.5.0 | PAC-JEFFREY-GOV-MULTIAGENT-TEMPLATE-UPDATE-001 | Added RAXC, EXECUTION_LANE_DECLARATION, REVIEW_GATE, ORDERING_ATTESTATION, PACK_IMMUTABILITY, JSRG_GATE blocks |
| G0.5.1 | PAC-JEFFREY-GOV-PDO-MANDATORY-EXECUTION-GATE-001 | Added PDO enforcement gates (GOV-PDO-001 through GOV-PDO-005) |

---

🟦🟩 **BENSON (GID-00)** — Chief Architect & Orchestrator  
🟩 **JEFFREY (CTO)** — PAC Author
