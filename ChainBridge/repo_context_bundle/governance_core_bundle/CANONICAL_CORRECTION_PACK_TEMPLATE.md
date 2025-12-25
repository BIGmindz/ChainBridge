# Canonical Correction Pack Template (CCPT) — G2

> **Governance Document** — PAC-ATLAS-G2-GOVERNANCE-CORRECTION-HARD-GATE-IMPLEMENTATION-01
> **Version:** G2.0.0
> **Effective Date:** 2025-12-23
> **Authority:** Benson (GID-00)
> **Enforced By:** Atlas (GID-11)
> **Status:** LOCKED / CANONICAL / MACHINE-ENFORCED

---

## Purpose

This is the **single canonical template for all Correction Packs** in ChainBridge.

- All correction artifacts MUST conform to this template
- Machine validation occurs at: emission, pre-commit, and CI
- No exceptions. No overrides. No warnings.
- Incomplete checklists result in **HARD FAIL (G0_020)**

```
Governance is physics, not policy.
Invalid correction packs cannot exist.
```

---

## Template Schema (LOCKED)

```yaml
CANONICAL_CORRECTION_SCHEMA:
  version: "G2.0.0"
  artifact_type: "CORRECTION_PACK"
  
  required_blocks:
    - RUNTIME_ACTIVATION_ACK
    - AGENT_ACTIVATION_ACK
    - PAC_HEADER
    - OBJECTIVE
    - SCOPE
    - VIOLATIONS_ADDRESSED
    - FORBIDDEN_ACTIONS
    - TRAINING_SIGNAL
    - FINAL_STATE
    - GOLD_STANDARD_CHECKLIST
    - SELF_CERTIFICATION
  
  block_order: STRICT
  missing_block: HARD_FAIL
  checklist_enforcement: MANDATORY
  all_items_checked: REQUIRED
  
  validation_mode: FAIL_CLOSED
  bypass_paths: 0
```

---

## Enforcement Chain (5 GATES)

```
GATE 0: TEMPLATE SELECTION (CCPT ONLY FOR CORRECTIONS)
   ↓
GATE 1: PACK EMISSION VALIDATION (gate_pack.py)
   ↓
GATE 2: PRE-COMMIT HOOK (FAIL-CLOSED)
   ↓
GATE 3: CI MERGE BLOCKER
   ↓
GATE 4: WRAP AUTHORIZATION

No bypass paths exist.
Checklist validation is physics.
```

---

## Required Block: VIOLATIONS_ADDRESSED (MANDATORY)

```yaml
VIOLATIONS_ADDRESSED {
  original_pac_id: STRING        # Required: PAC that contained violations
  violation_codes: LIST[STRING]  # Required: G0_XXX codes
  correction_type: ENUM          # Required: REISSUE | AMENDMENT | INVALIDATION
  affected_artifacts: LIST[STRING]
}
```

**Validation Rules:**
- `violation_codes` MUST contain at least one valid G0_XXX code
- `correction_type` MUST be one of the defined enums
- `original_pac_id` MUST reference an existing PAC

---

## Required Block: GOLD_STANDARD_CHECKLIST (MANDATORY — HARD GATE)

This block MUST be present **verbatim** with ALL items checked.

```yaml
GOLD_STANDARD_CHECKLIST:
  identity_correct: { checked: true }
  agent_color_correct: { checked: true }
  execution_lane_correct: { checked: true }
  canonical_headers_present: { checked: true }
  block_order_correct: { checked: true }
  forbidden_actions_section_present: { checked: true }
  scope_lock_present: { checked: true }
  training_signal_present: { checked: true }
  final_state_declared: { checked: true }
  wrap_schema_valid: { checked: true }
  no_extra_content: { checked: true }
  no_scope_drift: { checked: true }
  self_certification_present: { checked: true }
```

**Validation Rules (HARD FAIL):**
- Block MUST be present
- ALL 13 keys MUST be present
- ALL values MUST be `{ checked: true }`
- ANY unchecked item → **G0_020: GOLD_STANDARD_CHECKLIST_INCOMPLETE**
- Missing block → **G0_020: GOLD_STANDARD_CHECKLIST_INCOMPLETE**

---

## Required Block: SELF_CERTIFICATION (MANDATORY)

```yaml
SELF_CERTIFICATION {
  agent: STRING           # Required: Agent name
  gid: STRING             # Required: GID-XX
  statement: STRING       # Required: Certification statement
  timestamp: ISO8601      # Required: When certified
}
```

**Example:**
```
SELF_CERTIFICATION

I, ATLAS (GID-11), certify that this correction pack fully complies with 
the Canonical Correction Pack Template, all governance hard gates, and 
Gold Standard requirements. No deviations exist.

Timestamp: 2025-12-23T00:00:00Z
```

**Validation Rules:**
- Section MUST be present
- Agent name and GID MUST match AGENT_ACTIVATION_ACK
- Statement MUST include compliance assertion

---

## Checklist Item Definitions

| Checklist Item | Requirement |
|----------------|-------------|
| `identity_correct` | Agent name and GID match registry |
| `agent_color_correct` | Color matches registry |
| `execution_lane_correct` | Lane matches registry |
| `canonical_headers_present` | All required headers exist |
| `block_order_correct` | Blocks appear in mandated order |
| `forbidden_actions_section_present` | FORBIDDEN_ACTIONS block exists |
| `scope_lock_present` | SCOPE block with IN/OUT defined |
| `training_signal_present` | TRAINING_SIGNAL block exists |
| `final_state_declared` | FINAL_STATE block exists |
| `wrap_schema_valid` | If WRAP, follows WRAP schema |
| `no_extra_content` | No unauthorized sections |
| `no_scope_drift` | Work stays within declared scope |
| `self_certification_present` | SELF_CERTIFICATION exists |

---

## Error Codes (Correction-Specific)

| Code | Meaning | Response |
|------|---------|----------|
| `G0_020` | GOLD_STANDARD_CHECKLIST_INCOMPLETE | HARD FAIL — Reject immediately |
| `G0_021` | SELF_CERTIFICATION_MISSING | HARD FAIL — Reject immediately |
| `G0_022` | VIOLATIONS_ADDRESSED_MISSING | HARD FAIL — Reject immediately |
| `G0_023` | CHECKLIST_ITEM_UNCHECKED | HARD FAIL — Reject immediately |
| `G0_024` | CHECKLIST_KEY_MISSING | HARD FAIL — Reject immediately |

---

## Correction Workflow

```
1. VIOLATION DETECTED
   ↓
2. AGENT BLOCKED
   ↓
3. AGENT ACKNOWLEDGES DEFICIENCIES
   ↓
4. AGENT REISSUES USING THIS TEMPLATE
   ↓
5. GATE_PACK.PY VALIDATES
   ↓
6. CHECKLIST VERIFIED (ALL TRUE)
   ↓
7. SELF_CERTIFICATION VERIFIED
   ↓
8. BENSON RATIFIES
   ↓
9. AGENT UNBLOCKED
```

---

## Validation Command

```bash
# Validate correction pack
python tools/governance/gate_pack.py --file <correction_pack.md>

# Pre-commit validation (automatic)
git commit  # Triggers gate_pack.py

# CI validation (automatic)
# Runs on PR via governance-pack-gate.yml
```

---

## Training Signal for Corrections

All correction packs MUST emit:

```yaml
TRAINING_SIGNAL:
  type: GOVERNANCE_CORRECTION
  original_failure: STRING       # What went wrong
  correction_applied: STRING     # What was fixed
  lesson_learned: STRING         # Future prevention
  program: "Agent University"
  level: "L9"                    # Corrections are advanced
  evaluation: "Binary"
  retention: "PERMANENT"
```

---

## Lock Declaration

```yaml
CANONICAL_CORRECTION_PACK_TEMPLATE_LOCK {
  version: "G2.0.0"
  status: "LOCKED"
  enforcement: "PHYSICS"
  override_allowed: false
  warning_mode: false
  checklist_mandatory: true
  bypass_paths: 0
  gold_standard: true
  self_certification_required: true
}
```

---

## Example Correction Pack Structure

```
══════════════════════════════════════════════════════════════════════════════
🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
GID-XX — AGENT_NAME
CORRECTION-PAC-AGENT-ORIGINAL-VIOLATION-01
🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
══════════════════════════════════════════════════════════════════════════════

RUNTIME_ACTIVATION_ACK { ... }

AGENT_ACTIVATION_ACK { ... }

I. OBJECTIVE
...

II. SCOPE
...

III. VIOLATIONS_ADDRESSED
...

IV. FORBIDDEN_ACTIONS
...

V. TRAINING_SIGNAL
...

VI. FINAL_STATE
...

VII. GOLD_STANDARD_CHECKLIST
...

VIII. SELF_CERTIFICATION
...

══════════════════════════════════════════════════════════════════════════════
END — AGENT_NAME (GID-XX) — CORRECTION COMPLETE
══════════════════════════════════════════════════════════════════════════════
```

---

🟦 **ATLAS (GID-11)** — System State & Governance Engine  
🟦 **PAC-ATLAS-G2-GOVERNANCE-CORRECTION-HARD-GATE-IMPLEMENTATION-01**
