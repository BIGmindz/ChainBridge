# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE NAMING CANON v1.0.0
# Authority: PAC-BENSON-P36-NONEXECUTING-AGENT-ENFORCEMENT-AND-PAC-NAMING-CANONICALIZATION-01
# Mode: FAIL_CLOSED | Status: LOCKED
# ═══════════════════════════════════════════════════════════════════════════════

## Overview

This document canonicalizes PAC naming rules and agent role enforcement.
It eliminates ambiguity caused by:
- PAC naming referencing non-executing agents
- Footer semantics not matching executor
- Implicit persona carryover from retired agents

---

## 1. Agent Role Classification

```yaml
AGENT_ROLE_CLASSES:
  EXECUTING:
    description: "Agents authorized to execute PACs and emit artifacts"
    can_appear_in_pac_id: true
    can_emit_artifacts: true
    examples:
      - BENSON (GID-00)
      - CODY (GID-01)
      - SONNY (GID-02)
      - MIRA (GID-03)
      - CINDY (GID-04)
      - ATLAS (GID-05)
      - SAM (GID-06)
      - DAN (GID-07)
      - ALEX (GID-08)
      - LIRA (GID-09)
      - MAGGIE (GID-10)
      - RUBY (GID-12)

  NON_EXECUTING:
    description: "Agents that CANNOT execute PACs or emit artifacts"
    can_appear_in_pac_id: false
    can_emit_artifacts: false
    examples:
      - PAX (RETIRED)
      - DANA (RETIRED)

  CONSTRAINED:
    description: "Agents with execution restrictions"
    can_appear_in_pac_id: true
    restrictions_apply: true
    examples:
      - ATLAS (GID-05) — FACTS_ONLY, no write access
```

---

## 2. PAC Naming Rules (EXECUTOR_ONLY)

```yaml
PAC_NAMING_CANON:
  rule_1: "PAC ID MUST reference the EXECUTING agent"
  rule_2: "PAC ID CANNOT reference NON_EXECUTING agents"
  rule_3: "PAC ID CANNOT reference forbidden aliases"
  rule_4: "Footer color MUST match executing agent"

  pattern: "PAC-<EXECUTING_AGENT>-<TYPE>-<SEQUENCE>-<VERSION>"

  valid_examples:
    - "PAC-BENSON-P36-NONEXECUTING-AGENT-ENFORCEMENT-01"
    - "PAC-ATLAS-P33-STRESS-ORCHESTRATION-01"
    - "PAC-SAM-P32-SECURITY-GATE-HARDENING-01"

  invalid_examples:
    - "PAC-PAX-P32-GOVERNANCE-ECONOMIC-STRESS-01"  # PAX is NON_EXECUTING
    - "PAC-DANA-GOV-001-POLICY-UPDATE-01"          # DANA is RETIRED
```

---

## 3. Forbidden Agent Aliases

```yaml
FORBIDDEN_AGENT_ALIASES:
  - PAX:
      status: "RETIRED"
      reason: "Consolidated/deprecated in registry v4.0.0"
      error_code: "GS_073"

  - DANA:
      status: "RETIRED"
      reason: "Deprecated — no longer a valid agent"
      error_code: "GS_073"
```

---

## 4. Footer Color Enforcement

```yaml
FOOTER_COLOR_RULES:
  rule: "Footer color MUST match executing agent from AGENT_ACTIVATION_ACK"
  enforcement: "GS_072"

  valid_footer_example: |
    ╔══════════════════════════════════════════════════════════════════════════════════════╗
    ║ 🟦🟩 TEAL — BENSON (GID-00) — Governance Runtime                                     ║
    ╚══════════════════════════════════════════════════════════════════════════════════════╝

  invalid_footer_example: |
    # PAC executed by BENSON but footer shows SAM's color
    ╔══════════════════════════════════════════════════════════════════════════════════════╗
    ║ 🔴 DARK_RED — SAM (GID-06) — Security                                                ║
    ╚══════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 5. Persona Memory Override

```yaml
PERSONA_MEMORY_POLICY:
  rule: "Registry role is AUTHORITATIVE over persona memory"
  explanation: |
    If an agent's persona memory contains capabilities or roles
    that conflict with AGENT_REGISTRY.md, the registry wins.

  override_order:
    1: "AGENT_REGISTRY.md (CANONICAL)"
    2: "PAC explicit constraints"
    3: "Persona memory (SUBORDINATE)"

  example: |
    If persona memory says "Pax can execute strategy PACs"
    but AGENT_REGISTRY says "PAX — Retired (NON_EXECUTING)"
    → Registry wins. PAC-PAX-* is FORBIDDEN.
```

---

## 6. Error Codes

```yaml
ERROR_CODES:
  GS_071:
    name: "PAC ID references non-executing or retired agent"
    severity: "HARD_FAIL"
    example: "PAC-PAX-P32-..." triggers GS_071

  GS_072:
    name: "Footer color mismatch — must match executing agent"
    severity: "HARD_FAIL"
    example: "BENSON PAC with SAM footer color"

  GS_073:
    name: "Forbidden agent alias detected in PAC ID"
    severity: "HARD_FAIL"
    example: "PAC-DANA-..." triggers GS_073
```

---

## 7. CI Enforcement

```yaml
CI_ENFORCEMENT:
  validator: "tools/governance/gate_pack.py"
  function: "validate_pac_naming_and_roles()"
  mode: "FAIL_CLOSED"

  checks:
    - "PAC ID agent extraction"
    - "Forbidden alias detection"
    - "Non-executing agent detection"
    - "Footer color validation"
```

---

## 8. Migration Notes

```yaml
MIGRATION_NOTES:
  legacy_pacs:
    - "PAC-PAX-* files MUST be archived or reassigned"
    - "Footer colors MUST be updated to match executor"

  action_required:
    - "Audit all PAC-PAX-* files in docs/governance/"
    - "Reassign to appropriate executing agent or archive"
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# END GOVERNANCE_NAMING_CANON v1.0.0
# STATUS: LOCKED | ENFORCEMENT: FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║ 🟦🟩 TEAL — BENSON (GID-00) — Governance Runtime                                     ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ GOVERNANCE_NAMING_CANON v1.0.0: LOCKED                                               ║
║ Authority > Helpfulness | Registry > Persona Memory                                  ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
```
