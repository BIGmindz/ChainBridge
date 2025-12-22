# PAC Template V1 — Canonical Structure

> **Governance Document** — PAC-BENSON-CANONICAL-PACK-TEMPLATE-LOCK-01
> **Version:** 1.1.0
> **Effective Date:** 2025-12-22
> **Authority:** BENSON (GID-00)
> **Status:** LOCKED / CANONICAL
> **Amended By:** PAC-BENSON-IDENTITY-DRIFT-ELIMINATION-01

---

## Identity Resolution — REGISTRY BINDING (MANDATORY)

```yaml
REGISTRY_BINDING {
  source_of_truth: "docs/governance/AGENT_REGISTRY.json"
  lookup_required: true
  cache_allowed: false
  mismatch_action: "EXECUTION_ABORT"
}

IDENTITY_RESOLUTION {
  agent_name: RESOLVED_FROM_REGISTRY
  color: RESOLVED_FROM_REGISTRY
  icon: RESOLVED_FROM_REGISTRY
  execution_lane: RESOLVED_FROM_REGISTRY
  manual_override: FORBIDDEN
  free_text_identity: FORBIDDEN
}
```

**All identity fields MUST match AGENT_REGISTRY.json exactly. No exceptions.**

---

## Identity Invariants (HARD FAIL)

```yaml
INVARIANT_SET IDENTITY_RESOLUTION {
  INVARIANT_01: "AGENT_COLOR_MUST_MATCH_REGISTRY" → HARD_FAIL
  INVARIANT_02: "AGENT_ICON_MUST_MATCH_REGISTRY" → HARD_FAIL
  INVARIANT_03: "NO_FREE_TEXT_AGENT_IDENTITY_FIELDS" → HARD_FAIL
  INVARIANT_04: "AUTHORITY_DOES_NOT_IMPLY_NEW_COLOR" → HARD_FAIL
  INVARIANT_05: "BLACK_RESERVED_FOR_UI_ONLY" → HARD_FAIL
}
```

---

## Template Enforcement

```
ENFORCEMENT {
  missing_activation_block: HALT
  missing_color_or_gid: HALT
  ambiguous_mode: HALT
  implied_authority: HALT
  section_omitted: HALT
  section_reordered: HALT
  registry_mismatch: HALT
  free_text_identity: HALT
}
```

**Violation of any rule → IMMEDIATE HALT**

---

## PAC_TEMPLATE_V1 (LOCKED)

```yaml
PAC_TEMPLATE_V1:
  sections:
    - 0: AGENT_ACTIVATION_ACK   # REQUIRED, FIRST BLOCK
    - 1: PAC_HEADER
    - 2: CONTEXT_AND_GOAL
    - 3: CONSTRAINTS_AND_GUARDRAILS
    - 4: TASKS_AND_PLAN
    - 5: FILE_AND_CODE_TARGETS
    - 6: EXECUTION_RULES
    - 7: QA_AND_ACCEPTANCE_CRITERIA
    - 8: OUTPUT_AND_HANDOFF
    - 9: LOCK_STATEMENT
  
  rules:
    - no_section_may_be_omitted: true
    - no_section_may_be_reordered: true
    - activation_block_must_be_first: true
```

---

## Section 0: AGENT_ACTIVATION_ACK (MANDATORY FIRST)

**IDENTITY FUNNEL:**
```
stage_1: "PAC declares GID"
stage_2: "Registry lookup"
stage_3: "Color/Icon resolved FROM REGISTRY"
stage_4: "Invariant check"
stage_5: "Execution allowed"
bypass: NONE
```

```
AGENT_ACTIVATION_ACK {
  agent_name: "<RESOLVED_FROM_REGISTRY>"     # Must match registry
  gid: "<GID-XX>"                            # Lookup key
  role: "<RESOLVED_FROM_REGISTRY>"           # Must match registry
  color: "<RESOLVED_FROM_REGISTRY>"          # Must match registry
  icon: "<RESOLVED_FROM_REGISTRY>"           # Must match registry
  authority: "<AUTHORITY>"
  execution_lane: "<RESOLVED_FROM_REGISTRY>" # Must match registry
  mode: "<EXECUTABLE | READ_ONLY | DOCTRINE_LOCK>"
  permissions: [<EXPLICIT_LIST>]
  prohibitions: [<EXPLICIT_LIST>]
  status: "ACTIVE"
}
```

### Required Fields — REGISTRY BOUND

| Field | Required | Source | Description |
|-------|----------|--------|-------------|
| agent_name | ✅ | REGISTRY | Canonical agent name |
| gid | ✅ | INPUT | GID-XX format (lookup key) |
| role | ✅ | REGISTRY | Agent role description |
| color | ✅ | REGISTRY | Primary color (NO FREE TEXT) |
| icon | ✅ | REGISTRY | Emoji icon (NO FREE TEXT) |
| authority | ✅ | PAC | Authority source |
| execution_lane | ✅ | REGISTRY | Execution domain |
| mode | ✅ | PAC | EXACTLY ONE of: EXECUTABLE, READ_ONLY, DOCTRINE_LOCK |
| permissions | ✅ | PAC | Explicit list |
| prohibitions | ✅ | PAC | Explicit list |
| status | ✅ | PAC | ACTIVE |

### FORBIDDEN

- ❌ Free-text color values (e.g., "Black", "Navy", "Aqua")
- ❌ Implied colors from authority level
- ❌ Runtime using agent identity fields
- ❌ Manual color/icon override

---

## Section 1: PAC HEADER

```
PAC-<AGENT>-<DOMAIN>-<SEQUENCE>

| Field | Value |
|-------|-------|
| PAC ID | PAC-<AGENT>-<DOMAIN>-<SEQUENCE> |
| Agent | <NAME> |
| GID | <GID-XX> |
| Color | <COLOR> |
| Icon | <ICON> |
| Authority | <AUTHORITY> |
| Execution Lane | <LANE> |
| Mode | <EXECUTABLE | READ_ONLY | DOCTRINE_LOCK> |
| Drift Tolerance | <ZERO | LOW | MODERATE> |
```

---

## Section 2: CONTEXT & GOAL

```
CONTEXT {
  current_state: "<description>"
  problem: "<what needs to change>"
  trigger: "<what initiated this PAC>"
}

GOAL {
  desired_state: "<description>"
  success_criteria: "<measurable outcome>"
  scope_boundary: "<what is NOT in scope>"
}
```

---

## Section 3: CONSTRAINTS & GUARDRAILS

```
CONSTRAINTS {
  technical: [<list>]
  governance: [<list>]
  timeline: [<list>]
  dependencies: [<list>]
}

GUARDRAILS {
  must_not: [<list>]
  must_preserve: [<list>]
  requires_approval: [<list>]
}
```

---

## Section 4: TASKS & PLAN

Tasks must be:
- **Numbered** (1, 2, 3...)
- **Deterministic** (clear completion criteria)
- **Ordered** (execution sequence matters)

```
TASKS {
  1: {
    description: "<action>"
    owner: "<agent or runtime>"
    depends_on: [<task_numbers>]
    completion_criteria: "<binary pass/fail>"
  }
  2: { ... }
  3: { ... }
}
```

---

## Section 5: FILE & CODE TARGETS

All paths must be **explicit** and **absolute from repo root**.

```
FILE_TARGETS {
  create: [
    "path/to/new/file.py"
  ]
  modify: [
    "path/to/existing/file.py"
  ]
  delete: [
    "path/to/deprecated/file.py"
  ]
}
```

---

## Section 6: EXECUTION RULES

```
EXECUTION_RULES {
  order: "SEQUENTIAL | PARALLEL_ALLOWED"
  rollback_on_failure: true
  test_before_commit: true
  ci_must_pass: true
}
```

---

## Section 7: QA & ACCEPTANCE CRITERIA

All criteria must be **binary** (PASS/FAIL only).

```
ACCEPTANCE_CRITERIA {
  1: {
    criterion: "<description>"
    test_method: "<how to verify>"
    status: "PENDING | PASS | FAIL"
  }
  2: { ... }
}
```

---

## Section 8: OUTPUT / HANDOFF

```
OUTPUT {
  artifacts: [
    "<path/to/artifact1>",
    "<path/to/artifact2>"
  ]
  handoff_to: "<next agent or BENSON>"
  blocks_until_complete: true | false
}
```

---

## Section 9: LOCK STATEMENT

```
LOCK_STATEMENT {
  pac_id: "<PAC-ID>"
  authority: "<AGENT (GID-XX)>"
  scope: "<what is locked>"
  drift_allowed: false
  supersedes: "<prior PAC or NONE>"
}
```

---

## Runtime Execution Block (For Runtimes Only)

When a **runtime** (e.g., GitHub Copilot) executes a PAC, it must use:

```
RUNTIME_EXECUTION {
  runtime_name: "<GitHub Copilot | ChatGPT | etc.>"
  executing_for_agent: "<AGENT (GID-XX)>"
  has_gid: false
  has_color: false
  mode: "DELEGATED_EXECUTION"
}
```

---

## Validation Checklist

| Check | Required |
|-------|----------|
| Section 0 (Activation) present and first | ✅ |
| All sections 1-9 present | ✅ |
| Sections in correct order | ✅ |
| GID present | ✅ |
| Color present | ✅ |
| Icon present | ✅ |
| Mode is exactly one of allowed values | ✅ |
| Tasks are numbered and deterministic | ✅ |
| File paths are explicit | ✅ |
| Acceptance criteria are binary | ✅ |

---

🟦 **BENSON (GID-00)** — Chief Architect & Orchestrator
