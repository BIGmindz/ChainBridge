# Gold Standard WRAP Template — G0.2.0

> **Governance Document** — PAC-BENSON-G0-GOVERNANCE-CORRECTION-02
> **Version:** G0.2.0
> **Effective Date:** 2025-12-22
> **Authority:** Benson (GID-00)
> **Status:** LOCKED / CANONICAL / MACHINE-ENFORCED

---

## Purpose

This is the **single canonical WRAP template** for ChainBridge.

- There is no other valid WRAP structure
- All WRAPs must follow this exact structure, in this exact order
- All WRAPs must reference a validated PAC
- Deviation = INVALID

```
Governance is physics, not policy.
Invalid WRAPs cannot exist.
```

---

## WRAP Schema (LOCKED)

```yaml
GOLD_STANDARD_WRAP_SCHEMA:
  version: "G0.2.0"

  required_sections:
    1. HEADER (ID, Version, Status, Authority)
    2. RUNTIME_ACTIVATION_ACK
    3. AGENT_ACTIVATION_ACK
    4. SOURCE_REFERENCE (PAC or prior WRAP)
    5. SOURCE_DELTA (if correction)
    6. CONTEXT_OBJECTIVE
    7. SCOPE
    8. FORBIDDEN_ACTIONS
    9. ENFORCEMENT_DELIVERABLES
    10. ACCEPTANCE_CRITERIA
    11. TRAINING_SIGNAL
    12. FINAL_STATE
    13. SIGNATURE_END_BANNER

  section_order: STRICT
  missing_section: HARD_FAIL

  validation_mode: FAIL_CLOSED
  bypass_paths: 0
```

---

## Section 1: HEADER (MANDATORY FIRST)

```markdown
# [COLOR_BAR]
# WRAP-<AGENT>-<DOMAIN>-<SEQ>
# AGENT: <Name> (GID-XX)
# ROLE: <Role from registry>
# COLOR: <Icon> <COLOR_NAME>
# STATUS: GOVERNANCE-VALID
# [COLOR_BAR]

**Work Result and Attestation Proof**
```

**Validation Rules:**
- Must include agent identifier with GID
- Status must be GOVERNANCE-VALID
- Color bar must match agent's registered color

---

## Section 2: RUNTIME_ACTIVATION_ACK (MANDATORY)

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: STRING           # Required: "GitHub Copilot", etc.
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"                     # Required: Must be "N/A"
  authority: "DELEGATED"         # Required
  execution_lane: "EXECUTION"    # Required
  mode: "EXECUTABLE"             # Required
  executes_for_agent: STRING     # Required: "<Agent> (GID-XX)"
  status: "ACTIVE"               # Required
```

---

## Section 3: AGENT_ACTIVATION_ACK (MANDATORY)

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: STRING             # Required: From AGENT_REGISTRY
  gid: STRING                    # Required: "GID-XX" format
  role: STRING                   # Required: From AGENT_REGISTRY
  color: STRING                  # Required: From AGENT_REGISTRY
  icon: STRING                   # Required: From AGENT_REGISTRY
  execution_lane: STRING         # Required: From AGENT_REGISTRY
  mode: STRING                   # Required: AUTHORITATIVE | EXECUTABLE
  status: "ACTIVE"               # Required
```

---

## Section 4: SOURCE_REFERENCE (MANDATORY)

```markdown
## WRAP HEADER

| Field | Value |
|-------|-------|
| WRAP ID | WRAP-<AGENT>-<DOMAIN>-<SEQ> |
| PAC Reference | PAC-<AGENT>-<DOMAIN>-<SEQ> |
| Agent | <Name> (GID-XX) |
| Date | YYYY-MM-DD |
| Status | ✅ COMPLETED |
```

**Validation Rules:**
- PAC Reference MUST be a valid, previously emitted PAC
- Every WRAP MUST have a PAC reference

---

## Section 5: SOURCE_DELTA (IF CORRECTION)

```yaml
CORRECTION_DELTA:
  - <Change 1>
  - <Change 2>
  - <Change N>
```

**Validation Rules:**
- Required ONLY for correction WRAPs
- Must itemize specific changes from source

---

## Section 6: CONTEXT_OBJECTIVE (MANDATORY)

```markdown
## EXECUTION SUMMARY

### Objective
<What the PAC set out to accomplish>

### Completion Status
| Task | Status | Evidence |
|------|--------|----------|
| Task 1 | ✅ DONE | <Link or reference> |
```

---

## Section 7: SCOPE (MANDATORY)

```markdown
## SCOPE

### IN SCOPE
- <Item 1>
- <Item 2>

### OUT OF SCOPE
- <Item 1>
- <Item 2>
```

---

## Section 8: FORBIDDEN_ACTIONS (MANDATORY)

```markdown
## FORBIDDEN ACTIONS

The following were STRICTLY PROHIBITED:
- <Prohibition 1>
- <Prohibition 2>

FAILURE MODE: FAIL_CLOSED
```

**Validation Rules:**
- Must list specific prohibitions
- Must declare FAIL_CLOSED mode

---

## Section 9: ENFORCEMENT_DELIVERABLES (MANDATORY)

```markdown
## FILES CREATED / MODIFIED

### Files Created
| File | Purpose |
|------|---------|
| <path> | <description> |

### Validation Evidence
<Test results, gate outputs, etc.>
```

---

## Section 10: ACCEPTANCE_CRITERIA (MANDATORY)

```markdown
## ACCEPTANCE CRITERIA

| Criterion | Status |
|-----------|--------|
| <Criterion 1> | ✅ MET |
| <Criterion 2> | ✅ MET |
```

**Validation Rules:**
- All criteria must show status
- All criteria must be MET for valid WRAP

---

## Section 11: TRAINING_SIGNAL (MANDATORY)

```yaml
TRAINING_SIGNAL:
  program: "Agent University"
  level: "L<N>"
  domain: STRING
  competencies:
    - <Competency 1>
    - <Competency 2>
  evaluation: "BINARY"
  retention: "PERMANENT"
  outcome: "PASS"
```

**Validation Rules:**
- `program` MUST be "Agent University"
- `level` MUST be L1-L10
- `evaluation` MUST be "BINARY"
- `retention` MUST be "PERMANENT"
- `outcome` MUST be "PASS" for valid WRAP

---

## Section 12: FINAL_STATE (MANDATORY)

```yaml
FINAL_STATE:
  wrap_id: STRING
  pac_id: STRING
  agent: STRING
  gid: STRING
  status: "COMPLETED"
  governance_compliant: true
  hard_gates: "ENFORCED"
  bypass_paths: 0
  attestation: |
    I, <Agent> (GID-XX), attest that:
    - <Attestation point 1>
    - <Attestation point 2>
```

**Validation Rules:**
- `governance_compliant` MUST be true
- `hard_gates` MUST be "ENFORCED"
- `bypass_paths` MUST be 0
- Attestation MUST be present

---

## Section 13: SIGNATURE_END_BANNER (MANDATORY)

```markdown
---

[COLOR_BAR]
**END WRAP-<AGENT>-<DOMAIN>-<SEQ>**
**STATUS: ✅ COMPLETED**
**GOVERNANCE: PHYSICS, NOT POLICY**
[COLOR_BAR]
```

---

## Enforcement Chain

```
GATE 0: TEMPLATE SELECTION (THIS TEMPLATE ONLY)
   ↓
GATE 1: WRAP EMISSION VALIDATION (gate_pack.py)
   ↓
GATE 2: PRE-COMMIT HOOK (FAIL-CLOSED)
   ↓
GATE 3: CI MERGE BLOCKER
   ↓
GATE 4: WRAP AUTHORIZATION (requires valid PAC)

No bypass paths exist.
```

---

## Error Codes (WRAP-specific)

| Code | Meaning |
|------|---------|
| `W0-001` | Missing required section |
| `W0-002` | Section order violation |
| `W0-003` | Invalid PAC reference |
| `W0-004` | Registry mismatch |
| `W0-005` | Missing FORBIDDEN_ACTIONS |
| `W0-006` | Missing TRAINING_SIGNAL |
| `W0-007` | Missing FINAL_STATE |
| `W0-008` | Invalid attestation |
| `W0-009` | Training signal invalid |
| `W0-010` | Governance compliance false |

---

## Lock Declaration

```yaml
GOLD_STANDARD_WRAP_TEMPLATE_LOCK {
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
