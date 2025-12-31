# Governance Signal Semantics and Explainability

> **Canonical Reference:** PAC-MAGGIE-P30-GOVERNANCE-SIGNAL-SEMANTICS-AND-EXPLAINABILITY-01
> **Author:** Maggie (GID-10) | 💗 MAGENTA
> **Authority:** BENSON (GID-00)
> **Version:** 1.0.0
> **Status:** CANONICAL

---

## 1. Overview

This document defines the canonical semantics for all governance signals emitted by ChainBridge's governance layer. All signals are:

- **Deterministic** — Same input always produces same output
- **Explainable** — Every signal includes human-readable rationale
- **Glass-box** — No opaque scores or black-box ML outputs permitted
- **Business-aligned** — Severity reflects business impact, not technical noise

---

## 2. Canonical Signal Taxonomy

### 2.1 Signal Status Codes

| Status | Code | Meaning | Business Impact |
|--------|------|---------|-----------------|
| **PASS** | `0` | All checks satisfied | None — proceed |
| **WARN** | `1` | Advisory condition detected | Low — review recommended |
| **FAIL** | `2` | Blocking condition detected | High — action required |
| **SKIP** | `3` | Check not applicable | None — excluded from scope |

### 2.2 Signal Severity Levels

```yaml
SEVERITY_TAXONOMY:
  CRITICAL:
    level: 4
    description: "System-wide governance violation; blocks all operations"
    business_impact: "Complete halt; executive escalation required"
    examples:
      - "Registry tampering detected"
      - "FAIL_CLOSED mode breached"
      - "Unauthorized agent execution"

  HIGH:
    level: 3
    description: "Gate-level failure; blocks specific operation"
    business_impact: "Operation blocked; immediate correction required"
    examples:
      - "PAG-01 activation missing"
      - "BSRG checklist failed"
      - "Review gate rejected"

  MEDIUM:
    level: 2
    description: "Compliance warning; does not block but must be addressed"
    business_impact: "Technical debt; must resolve before next release"
    examples:
      - "Deprecated schema version"
      - "Optional field missing"
      - "Non-canonical ordering"

  LOW:
    level: 1
    description: "Advisory notice; informational only"
    business_impact: "Minimal; address at convenience"
    examples:
      - "Style recommendation"
      - "Documentation suggestion"
      - "Performance hint"

  NONE:
    level: 0
    description: "No issue detected"
    business_impact: "None"
    examples:
      - "All checks passed"
```

### 2.3 Confidence Classification

All governance signals are **deterministic**. Confidence is always 100% for rule-based checks.

```yaml
CONFIDENCE_CLASSIFICATION:
  DETERMINISTIC:
    value: 1.0
    description: "Rule-based check with binary outcome"
    applicable_to:
      - PAG-01 validation
      - Schema validation
      - Block ordering checks
      - Registry binding verification

  HEURISTIC:
    value: 0.95
    description: "Pattern-based check with deterministic rules"
    applicable_to:
      - Code smell detection
      - Naming convention checks
      - Documentation completeness

  ML_ASSISTED:
    value: null
    description: "NOT PERMITTED in governance layer"
    constraint: "All ML signals must be wrapped in glass-box explainer"
    fallback: "If ML confidence < 0.99, emit WARN and require human review"
```

---

## 3. Explanation Schema

Every governance signal MUST include an explanation conforming to this schema:

```yaml
EXPLANATION_SCHEMA:
  version: "1.0.0"
  required_fields:
    - signal_id        # Unique identifier for the signal type
    - status           # PASS | WARN | FAIL | SKIP
    - severity         # CRITICAL | HIGH | MEDIUM | LOW | NONE
    - code             # Machine-readable error/warning code
    - title            # Human-readable one-line summary
    - description      # Detailed explanation (2-3 sentences)
    - evidence         # Specific data that triggered the signal
    - resolution       # Actionable steps to resolve (if applicable)
    - documentation    # Link to relevant documentation

  optional_fields:
    - context          # Additional context about the check
    - related_signals  # Other signals that may be relevant
    - timestamp        # When the signal was generated
    - source           # Which validator/gate generated the signal
```

### 3.1 Explanation Template

```markdown
## Signal: {signal_id}

**Status:** {status} | **Severity:** {severity} | **Code:** {code}

### {title}

{description}

**Evidence:**
{evidence}

**Resolution:**
{resolution}

**Documentation:** {documentation}
```

---

## 4. Gate Failure Mappings

### 4.1 PAG-01 (Persona Activation Gate) Failures

| Code | Title | Description | Resolution |
|------|-------|-------------|------------|
| `PAG_001` | Missing Activation Block | The AGENT_ACTIVATION_ACK block is missing from the document | Add AGENT_ACTIVATION_ACK block with all required fields |
| `PAG_002` | Missing Runtime Block | The RUNTIME_ACTIVATION_ACK block is missing | Add RUNTIME_ACTIVATION_ACK block before AGENT_ACTIVATION_ACK |
| `PAG_003` | Registry Mismatch | Agent identity does not match AGENT_REGISTRY.md | Correct agent_name, gid, color, or icon to match registry |
| `PAG_004` | Invalid GID Format | GID does not follow GID-XX pattern | Use format GID-00 through GID-99 |
| `PAG_005` | Block Ordering Violation | RUNTIME_ACTIVATION_ACK must precede AGENT_ACTIVATION_ACK | Reorder blocks to canonical sequence |
| `PAG_006` | Missing Execution Lane | EXECUTION_LANE block not declared | Add EXECUTION_LANE with lane_id and permissions |
| `PAG_007` | Lane Permission Violation | Agent accessed path outside allowed_paths | Restrict operation to declared execution lane |
| `PAG_008` | Tool Access Violation | Agent used tool in tools_blocked list | Use only tools in tools_enabled list |
| `PAG_009` | Mode Mismatch | Declared mode conflicts with operation type | Set mode to EXECUTABLE, INFORMATIONAL, or ADVISORY |
| `PAG_010` | Authority Not Declared | authority field missing or invalid | Declare valid authority (e.g., BENSON (GID-00)) |

### 4.2 Review Gate Failures

| Code | Title | Description | Resolution |
|------|-------|-------------|------------|
| `RG_001` | Gate Not Declared | REVIEW_GATE block missing | Add REVIEW_GATE block with gate_id and mode |
| `RG_002` | Gate Failed | Review gate returned FAIL status | Address all review gate checklist items |
| `RG_003` | Override Without Justification | override_used=true but no justification provided | Add override_justification with valid reason |
| `RG_004` | Invalid Gate ID | gate_id does not match known gate versions | Use valid gate_id (e.g., REVIEW-GATE-v1.1) |
| `RG_005` | Mode Violation | Gate mode must be FAIL_CLOSED | Set mode to FAIL_CLOSED |

### 4.3 BSRG (Benson Self-Review Gate) Failures

| Code | Title | Description | Resolution |
|------|-------|-------------|------------|
| `BSRG_001` | Gate Not Declared | BENSON_SELF_REVIEW_GATE block missing | Add BSRG block with full checklist |
| `BSRG_002` | Checklist Item Failed | One or more checklist items returned FAIL | Review and address each failed item |
| `BSRG_003` | Unauthorized Override | Override used without GID-00 authority | Only BENSON (GID-00) may authorize overrides |
| `BSRG_004` | Incomplete Checklist | Required checklist items missing | Include all required checklist items |
| `BSRG_005` | Policy Violation | issuance_policy not set to FAIL_CLOSED | Set issuance_policy to FAIL_CLOSED |

### 4.4 Gold Standard Failures

| Code | Title | Description | Resolution |
|------|-------|-------------|------------|
| `GS_001` | Missing TRAINING_SIGNAL | Document lacks TRAINING_SIGNAL block | Add TRAINING_SIGNAL with signal_type and lesson |
| `GS_002` | Missing SELF_CERTIFICATION | Document lacks SELF_CERTIFICATION block | Add SELF_CERTIFICATION with certified_by and certifies list |
| `GS_003` | Missing FINAL_STATE | Document lacks FINAL_STATE block | Add FINAL_STATE with status declarations |
| `GS_010` | Schema Version Mismatch | Document references invalid schema version | Update SCHEMA_REFERENCE to valid version |
| `GS_020` | Immutability Violation | Attempt to modify immutable document | Create superseding document instead |
| `GS_030` | Closure Without Authority | POSITIVE_CLOSURE lacks valid authority | Declare authority as BENSON (GID-00) |
| `GS_040` | Ledger Attestation Missing | LEDGER_COMMIT_ATTESTATION not present | Add ledger attestation block |
| `GS_045` | Invalid Signal Type | TRAINING_SIGNAL.signal_type invalid for closure type | Use POSITIVE_REINFORCEMENT for POSITIVE_CLOSURE |

---

## 5. Example Explanations

### 5.1 Terminal Output Format

```
══════════════════════════════════════════════════════════════════════════════
  GOVERNANCE VALIDATION RESULT
══════════════════════════════════════════════════════════════════════════════

File: docs/governance/pacs/PAC-EXAMPLE-01.md

┌─────────────────────────────────────────────────────────────────────────────┐
│ ✗ FAIL | HIGH | PAG_001                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Missing Activation Block                                                    │
│                                                                             │
│ The AGENT_ACTIVATION_ACK block is missing from the document. This block    │
│ is required by PAG-01 (Persona Activation Gate) to establish agent         │
│ identity and authorization before any governance operation.                 │
│                                                                             │
│ Evidence:                                                                   │
│   • Searched for: AGENT_ACTIVATION_ACK                                      │
│   • Found: Not present in document                                          │
│   • Location: Expected in document header                                   │
│                                                                             │
│ Resolution:                                                                 │
│   Add AGENT_ACTIVATION_ACK block with required fields:                      │
│   - agent_name, gid, color, icon, role, execution_lane, authority, mode    │
│                                                                             │
│ Documentation: docs/governance/PAG-01-PERSONA-ACTIVATION-GATE.md            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ✓ PASS | NONE | PAG_003                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Registry Binding Verified                                                   │
│                                                                             │
│ Agent identity matches AGENT_REGISTRY.md entry.                             │
│                                                                             │
│ Evidence:                                                                   │
│   • Agent: MAGGIE (GID-10)                                                  │
│   • Registry Color: MAGENTA ✓                                               │
│   • Registry Icon: 💗 ✓                                                     │
│   • Registry Role: ML & Applied AI Lead ✓                                   │
└─────────────────────────────────────────────────────────────────────────────┘

══════════════════════════════════════════════════════════════════════════════
  SUMMARY: 1 FAIL | 0 WARN | 1 PASS | 0 SKIP
  STATUS: ✗ INVALID
══════════════════════════════════════════════════════════════════════════════
```

### 5.2 JSON Output Format (for CI/Operator Console)

```json
{
  "validation_result": {
    "file": "docs/governance/pacs/PAC-EXAMPLE-01.md",
    "status": "INVALID",
    "timestamp": "2025-12-24T00:00:00Z",
    "validator": "gate_pack.py v1.0.0",
    "signals": [
      {
        "signal_id": "PAG_001",
        "status": "FAIL",
        "severity": "HIGH",
        "code": "PAG_001",
        "title": "Missing Activation Block",
        "description": "The AGENT_ACTIVATION_ACK block is missing from the document. This block is required by PAG-01 (Persona Activation Gate) to establish agent identity and authorization before any governance operation.",
        "evidence": {
          "searched_for": "AGENT_ACTIVATION_ACK",
          "found": null,
          "expected_location": "document header"
        },
        "resolution": "Add AGENT_ACTIVATION_ACK block with required fields: agent_name, gid, color, icon, role, execution_lane, authority, mode",
        "documentation": "docs/governance/PAG-01-PERSONA-ACTIVATION-GATE.md"
      },
      {
        "signal_id": "PAG_003",
        "status": "PASS",
        "severity": "NONE",
        "code": "PAG_003",
        "title": "Registry Binding Verified",
        "description": "Agent identity matches AGENT_REGISTRY.md entry.",
        "evidence": {
          "agent": "MAGGIE",
          "gid": "GID-10",
          "color_match": true,
          "icon_match": true,
          "role_match": true
        },
        "resolution": null,
        "documentation": null
      }
    ],
    "summary": {
      "fail": 1,
      "warn": 0,
      "pass": 1,
      "skip": 0,
      "total": 2
    }
  }
}
```

### 5.3 UI Card Format (Operator Console)

```
┌──────────────────────────────────────────────────────────────────┐
│  🔴 PAG_001 — Missing Activation Block                           │
│  ──────────────────────────────────────────────────────────────  │
│  Severity: HIGH                                                  │
│  Status: FAIL                                                    │
│  ──────────────────────────────────────────────────────────────  │
│  The AGENT_ACTIVATION_ACK block is missing from the document.    │
│                                                                  │
│  📋 Evidence                                                     │
│  • Searched for: AGENT_ACTIVATION_ACK                            │
│  • Found: Not present                                            │
│                                                                  │
│  🔧 Resolution                                                   │
│  Add AGENT_ACTIVATION_ACK block with required fields.            │
│                                                                  │
│  [View Documentation] [View File] [Auto-Fix]                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. ML Signal Constraints

### 6.1 Prohibited Patterns

The following patterns are **FORBIDDEN** in governance signals:

```yaml
FORBIDDEN_ML_PATTERNS:
  - pattern: "Opaque confidence scores"
    example: "confidence: 0.73"
    reason: "Score without explanation provides no actionable insight"

  - pattern: "Black-box classification"
    example: "risk_level: HIGH (model output)"
    reason: "Model output without feature attribution is unexplainable"

  - pattern: "Aggregated scores"
    example: "governance_score: 85/100"
    reason: "Aggregation obscures individual signal failures"

  - pattern: "Relative rankings"
    example: "better than 73% of documents"
    reason: "Relative comparison provides no absolute quality measure"

  - pattern: "Threshold-only decisions"
    example: "FAIL: score below 0.5"
    reason: "Threshold without feature explanation is not actionable"
```

### 6.2 Required ML Signal Wrapper

Any ML-assisted signal MUST be wrapped in a glass-box explainer:

```yaml
ML_SIGNAL_WRAPPER:
  required_fields:
    - model_id: "Identifier of the model producing the signal"
    - model_version: "Semantic version of the model"
    - input_features: "List of features used in decision"
    - feature_contributions: "Contribution of each feature to output"
    - decision_boundary: "Threshold or rule applied"
    - confidence_interval: "Uncertainty bounds (if applicable)"
    - fallback_rule: "Deterministic fallback if confidence < threshold"
    - human_override: "Whether human review is required"

  example:
    model_id: "drift_detector_v1"
    model_version: "1.2.0"
    input_features:
      - feature: "psi_score"
        value: 0.32
        contribution: 0.65
      - feature: "ks_statistic"
        value: 0.18
        contribution: 0.25
      - feature: "missing_rate_delta"
        value: 0.02
        contribution: 0.10
    decision_boundary: "psi_score > 0.25 OR ks_statistic > 0.15"
    confidence_interval: null  # Deterministic rule, no confidence interval
    fallback_rule: "If any feature unavailable, emit WARN and require human review"
    human_override: false
```

### 6.3 Glass-Box Requirements

All governance signals must satisfy these glass-box requirements:

| Requirement | Description | Validation |
|-------------|-------------|------------|
| **Feature Transparency** | All input features must be listed | Check: input_features.length > 0 |
| **Attribution** | Each feature must have contribution weight | Check: all features have contribution |
| **Reproducibility** | Same input must produce same output | Check: deterministic flag = true |
| **Boundary Clarity** | Decision rule must be explicit | Check: decision_boundary is parseable |
| **Fallback Defined** | Uncertainty case must have fallback | Check: fallback_rule is non-empty |
| **Version Tracked** | Model version must be specified | Check: model_version matches semver |

---

## 7. Implementation Checklist

When implementing governance signals:

- [ ] Signal has unique code (e.g., PAG_001, RG_002)
- [ ] Status is one of: PASS, WARN, FAIL, SKIP
- [ ] Severity is one of: CRITICAL, HIGH, MEDIUM, LOW, NONE
- [ ] Title is human-readable (< 50 characters)
- [ ] Description explains the "what" and "why"
- [ ] Evidence shows specific triggering data
- [ ] Resolution provides actionable steps
- [ ] Documentation links to relevant guide
- [ ] No opaque scores or black-box outputs
- [ ] Terminal and UI formats are consistent

---

## 8. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-24 | Maggie (GID-10) | Initial canonical definition |

---

**END — GOVERNANCE_SIGNAL_SEMANTICS.md**
