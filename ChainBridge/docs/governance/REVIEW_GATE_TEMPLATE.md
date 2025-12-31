# ═══════════════════════════════════════════════════════════════════════════════
# REVIEW GATE TEMPLATE v1.1
# PAC-BENSON-G0-REVIEW-GATE-V1-1-IMPLEMENTATION-01
# Authority: Benson (GID-00)
# Mode: STRICT | Discretionary Override: FORBIDDEN | Bypass: IMPOSSIBLE
# ═══════════════════════════════════════════════════════════════════════════════

## Template Overview

This template is MANDATORY for all PAC/WRAP reviews. No exceptions.

**Scope:**
- ALL_PAC_REVIEWS
- ALL_WRAP_REVIEWS
- ALL_CORRECTION_PACK_REVIEWS
- ALL_POSITIVE_CLOSURE_REVIEWS

**FORBIDDEN_ACTIONS:**
- Implicit approval
- Narrative-only review
- Partial checklist acceptance
- Discretionary override
- Approval without self-certification
- Approval without training signal

---

## 0. Runtime & Agent Activation

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "[RUNTIME_NAME]"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "[AGENT_NAME] ([GID])"
  status: "ACTIVE"
```

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "[AGENT_NAME]"
  gid: "[GID]"
  role: "[ROLE]"
  color: "[COLOR]"
  icon: "[ICON]"
  execution_lane: "[LANE]"
  mode: "AUTHORITATIVE"
  status: "ACTIVE"
```

---

## I. REVIEW METADATA

```yaml
REVIEW_METADATA:
  review_id: "REVIEW-[AGENT]-[PAC_OR_WRAP_ID]"
  artifact_under_review: "[PAC_ID or WRAP_ID]"
  reviewer: "[AGENT_NAME]"
  reviewer_gid: "[GID]"
  review_date: "[YYYY-MM-DD]"
  review_type: "[PAC | WRAP | CORRECTION | POSITIVE_CLOSURE]"
```

---

## II. REVIEW_GATE_DECLARATION

```yaml
REVIEW_GATE_DECLARATION:
  name: "BENSON_REVIEW_GATE"
  version: "1.1"
  mode: "STRICT"
  mirrors_gate_pack: true
  discretionary_review: false
  fail_closed: true
  ci_enforced: true
  pre_commit_enforced: true
```

---

## III. SCOPE_LOCK

```yaml
SCOPE_LOCK:
  applies_to:
    - ALL_PAC_REVIEWS
    - ALL_WRAP_REVIEWS
    - ALL_CORRECTION_PACK_REVIEWS
    - ALL_POSITIVE_CLOSURE_REVIEWS
  exclusions: NONE
```

---

## IV. FORBIDDEN_ACTIONS

```yaml
FORBIDDEN_ACTIONS:
  - Implicit approval
  - Narrative-only review
  - Partial checklist acceptance
  - Discretionary override
  - Approval without self-certification
  - Approval without training signal
```

---

## V. REVIEW_GATE_ERROR_CODES

```yaml
REVIEW_GATE_ERROR_CODES:
  RG_001: "Missing ReviewGate declaration"
  RG_002: "Missing terminal Gold Standard Checklist"
  RG_003: "Missing reviewer self-certification"
  RG_004: "Missing training signal"
  RG_005: "Incomplete checklist"
  RG_006: "Missing activation acknowledgements"
  RG_007: "Missing runtime enforcement"
```

---

## VI. ARTIFACT_SUMMARY

**Artifact Under Review:** [PAC_ID or WRAP_ID]

| Section | Present | Valid |
|---------|---------|-------|
| RUNTIME_ACTIVATION_ACK | ☐ | ☐ |
| AGENT_ACTIVATION_ACK | ☐ | ☐ |
| SCOPE | ☐ | ☐ |
| FORBIDDEN_ACTIONS | ☐ | ☐ |
| TRAINING_SIGNAL | ☐ | ☐ |
| FINAL_STATE | ☐ | ☐ |

---

## VII. GOLD_STANDARD_CHECKLIST (TERMINAL — MUST PASS ALL)

**This checklist is TERMINAL. All items must be marked `true` for approval.**

```yaml
GOLD_STANDARD_CHECKLIST:
  # Identity Validation
  identity_correct: [true/false]
  agent_color_correct: [true/false]
  execution_lane_correct: [true/false]

  # Structure Validation
  canonical_headers_present: [true/false]
  block_order_correct: [true/false]

  # Required Blocks
  agent_activation_ack_present: [true/false]
  runtime_activation_ack_present: [true/false]

  # Review Gate Requirements
  review_gate_declared: [true/false]
  scope_lock_present: [true/false]
  forbidden_actions_declared: [true/false]
  error_codes_declared: [true/false]

  # Governance Requirements
  training_signal_present: [true/false]
  final_state_declared: [true/false]

  # Self-Certification Requirements
  self_certification_present: [true/false]

  # Terminal Requirements
  checklist_terminal: [true/false]
  checklist_all_items_passed: [true/false]
```

---

## VIII. SELF_CERTIFICATION

```yaml
SELF_CERTIFICATION:
  reviewer: "[AGENT_NAME]"
  gid: "[GID]"
  certification:
    - "All required sections are present"
    - "ReviewGate mirrors gate_pack exactly"
    - "No discretionary logic exists"
    - "Checklist is terminal and enforced"
    - "Artifact meets Gold Standard requirements"
  certified: [true/false]
```

---

## IX. TRAINING_SIGNAL

```yaml
TRAINING_SIGNAL:
  signal_type: "GOVERNANCE_PATTERN_REINFORCEMENT"
  pattern: "REVIEW_GATE_V1_1_STRICT"
  program: "Agent University"
  level: "[L1-L10]"
  domain: "Governance Review"
  propagate: true
  applies_to: "ALL_AGENTS"
  evaluation: "BINARY"
  retention: "PERMANENT"
```

---

## X. REVIEW_DECISION

```yaml
REVIEW_DECISION:
  decision: "[APPROVED | REJECTED | REQUIRES_CORRECTION]"
  reason: "[EXPLANATION]"
  violations: []  # List any RG_xxx violations
  next_action: "[NONE | CORRECTION_REQUIRED | RE-REVIEW]"
```

---

## XI. FINAL_STATE

```yaml
FINAL_STATE:
  review_id: "REVIEW-[AGENT]-[PAC_OR_WRAP_ID]"
  artifact_reviewed: "[PAC_ID or WRAP_ID]"
  reviewer: "[AGENT_NAME]"
  gid: "[GID]"
  decision: "[APPROVED | REJECTED | REQUIRES_CORRECTION]"
  review_gate_active: true
  effective_immediately: true
  bypass_possible: false
  governance_level: "PHYSICS"
  hard_gates: "ENFORCED"
  governance_compliant: [true/false]
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# END REVIEW_GATE_TEMPLATE v1.1
# STATUS: CANONICAL
# ENFORCEMENT: MACHINE-FIRST, HUMAN-READABLE
# ═══════════════════════════════════════════════════════════════════════════════
