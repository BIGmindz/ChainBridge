# WRAP Template V1 — Canonical Structure

> **Governance Document** — PAC-BENSON-CANONICAL-PACK-TEMPLATE-LOCK-01
> **Version:** 1.1.0
> **Effective Date:** 2025-12-22
> **Authority:** BENSON (GID-00)
> **Status:** LOCKED / CANONICAL
> **Amended By:** PAC-BENSON-IDENTITY-DRIFT-ELIMINATION-01

---

## Identity Resolution — REGISTRY BINDING (MANDATORY)

```yaml
WRAP_IDENTITY_RULES {
  agent_identity: RESOLVED_STRICTLY_FROM_REGISTRY
  fallback_identity: DISALLOWED
  runtime_identity: SEPARATE_BLOCK_ONLY
  free_text_color: FORBIDDEN
  implied_color: FORBIDDEN
}
```

**WRAP must echo agent identity EXACTLY as resolved from AGENT_REGISTRY.json.**

---

## Template Enforcement

```
ENFORCEMENT {
  missing_activation_block: HALT
  narrative_prose: FORBIDDEN
  section_omitted: HALT
  section_reordered: HALT
  ambiguous_status: HALT
  registry_mismatch: HALT
  identity_drift: HALT
}
```

**Narrative prose is FORBIDDEN inside WRAPs.**

---

## WRAP_TEMPLATE_V1 (LOCKED)

```yaml
WRAP_TEMPLATE_V1:
  sections:
    - 0: AGENT_ACTIVATION_ACK   # REQUIRED, FIRST BLOCK
    - 1: EXECUTION_SUMMARY
    - 2: TASK_STATUS
    - 3: ARTIFACTS_TOUCHED
    - 4: TESTS_RUN
    - 5: DEVIATIONS
    - 6: TRAINING_SIGNAL
    - 7: FINAL_STATE

  rules:
    - no_section_may_be_omitted: true
    - no_section_may_be_reordered: true
    - activation_block_must_be_first: true
    - narrative_prose_forbidden: true
    - status_must_be_binary: true
```

---

## Section 0: AGENT_ACTIVATION_ACK (MANDATORY FIRST)

For **Agents** — ALL IDENTITY FIELDS RESOLVED FROM REGISTRY:
```
AGENT_ACTIVATION_ACK {
  agent_name: "<RESOLVED_FROM_REGISTRY>"     # Must match registry
  gid: "<GID-XX>"                            # Lookup key
  role: "<RESOLVED_FROM_REGISTRY>"           # Must match registry
  color: "<RESOLVED_FROM_REGISTRY>"          # Must match registry (NO FREE TEXT)
  icon: "<RESOLVED_FROM_REGISTRY>"           # Must match registry (NO FREE TEXT)
  authority: "<AUTHORITY>"
  execution_lane: "<RESOLVED_FROM_REGISTRY>" # Must match registry
  mode: "EXECUTABLE"
  permissions: [<EXPLICIT_LIST>]
  prohibitions: [<EXPLICIT_LIST>]
  status: "ACTIVE"
}
```

For **Runtimes** — SEPARATE BLOCK, NO AGENT IDENTITY:
```
RUNTIME_ACTIVATION_ACK {
  runtime_name: "<NAME>"                     # e.g., "GitHub Copilot"
  gid: "N/A (RUNTIME)"                       # Runtimes have NO GID
  role: "Execution Runtime"
  color: "N/A (RUNTIME)"                     # Runtimes have NO color
  icon: "N/A (RUNTIME)"                      # Runtimes have NO icon
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executing_for_agent: "<AGENT (GID-XX)>"   # Must reference valid agent
  permissions: [<EXPLICIT_LIST>]
  prohibitions: [<EXPLICIT_LIST>]
  status: "ACTIVE"
}
```

### FORBIDDEN in WRAP Identity

- ❌ Free-text color values
- ❌ Fallback identity when registry lookup fails
- ❌ Runtime claiming agent identity fields
- ❌ Color/icon drift from originating PAC

---

## Section 1: EXECUTION SUMMARY

```
EXECUTION_SUMMARY {
  pac_id: "<PAC-ID>"
  agent: "<NAME>"
  gid: "<GID-XX>"
  color: "<COLOR>"
  icon: "<ICON>"
  mode: "<MODE>"
  drift_detected: true | false
  execution_status: "COMPLETE | PARTIAL | FAILED"
}
```

---

## Section 2: TASK-BY-TASK STATUS

Status must be **PASS or FAIL only**. No partial, no narrative.

```
TASK_STATUS {
  1: {
    description: "<task description>"
    status: "PASS | FAIL"
    evidence: "<commit hash | test output | file path>"
  }
  2: {
    description: "<task description>"
    status: "PASS | FAIL"
    evidence: "<evidence>"
  }
  ...
}
```

---

## Section 3: ARTIFACTS TOUCHED

All paths must be **explicit**.

```
ARTIFACTS_TOUCHED {
  created: [
    "path/to/new/file.py"
  ]
  modified: [
    "path/to/modified/file.py"
  ]
  deleted: [
    "path/to/deleted/file.py"
  ]
}
```

---

## Section 4: TESTS RUN

```
TESTS_RUN {
  command: "<exact command>"
  result: "PASS | FAIL"
  summary: "<X passed, Y failed, Z skipped>"
  evidence: "<output snippet or reference>"
}
```

Example:
```
TESTS_RUN {
  command: "python -m pytest tests/ -v --tb=line"
  result: "PASS"
  summary: "619 passed, 1 skipped"
  evidence: "CI log: https://..."
}
```

---

## Section 5: DEVIATIONS

If none, state explicitly. No empty section.

```
DEVIATIONS {
  count: 0 | <N>
  items: [] | [
    {
      description: "<what deviated>"
      reason: "<why>"
      impact: "<consequence>"
      remediation: "<fix applied or PAC needed>"
    }
  ]
}
```

---

## Section 6: TRAINING SIGNAL

```
TRAINING_SIGNAL {
  program: "Agent University"
  level: "<L1 | L2 | L3 | L4>"
  domain: "<competency domain>"
  competencies: [<list>]
  evaluation: "Binary"
}
```

### Level Definitions

| Level | Scope |
|-------|-------|
| L1 | Execution hygiene, task correctness |
| L2 | Governance, enforcement, system discipline |
| L3 | Orchestration, executive control, platform safety |
| L4 | Canonical identity, funnel enforcement, substrate |

---

## Section 7: FINAL STATE

```
FINAL_STATE {
  execution_complete: true | false
  ready_for_next_pac: true | false
  blocking_issues: [] | [<list>]
  next_action: "<AWAIT_GATEWAY | PROCEED | HALT>"
}
```

---

## Validation Checklist

| Check | Required |
|-------|----------|
| Section 0 (Activation) present and first | ✅ |
| All sections 1-7 present | ✅ |
| Sections in correct order | ✅ |
| No narrative prose | ✅ |
| Task status is PASS/FAIL only | ✅ |
| Deviations explicitly stated (even if none) | ✅ |
| Training signal present | ✅ |
| Final state declared | ✅ |

---

## Anti-Patterns (FORBIDDEN)

❌ **Narrative prose:**
```
"The work went well and we completed most of the tasks..."
```

❌ **Ambiguous status:**
```
status: "mostly done"
status: "in progress"
```

❌ **Missing deviation section:**
```
# (section omitted because no deviations)
```

❌ **Implied completion:**
```
# (no final state because it's obvious)
```

---

🟦 **BENSON (GID-00)** — Chief Architect & Orchestrator
