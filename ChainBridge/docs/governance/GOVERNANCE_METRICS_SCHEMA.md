# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE METRICS SCHEMA v1.0.0
# Authority: PAC-BENSON-P37-AGENT-PERFORMANCE-METRICS-BASELINE-AND-ENFORCEMENT-01
# Mode: FAIL_CLOSED | Status: LOCKED
# ═══════════════════════════════════════════════════════════════════════════════

## Overview

This document defines the canonical schema for agent performance metrics.
All EXECUTABLE artifacts (PACs with TASKS/FILES, WRAPs documenting execution)
MUST include a valid METRICS block.

**Principle:** What isn't measured cannot be trusted.

---

## 1. METRICS Block Schema v1.0.0

```yaml
METRICS:
  # REQUIRED FIELDS
  execution_time_ms: <integer>           # Total execution time in milliseconds
  tasks_completed: <integer>             # Number of tasks completed
  tasks_total: <integer>                 # Total tasks in scope
  quality_score: <float 0.0-1.0>         # Self-assessed quality (0.0-1.0)
  scope_compliance: <boolean>            # Did execution stay within PAC scope?
  
  # OPTIONAL FIELDS
  files_created: <integer>               # Files created during execution
  files_modified: <integer>              # Files modified during execution
  lines_added: <integer>                 # Lines of code added
  lines_removed: <integer>               # Lines of code removed
  errors_encountered: <integer>          # Errors encountered during execution
  errors_resolved: <integer>             # Errors successfully resolved
  ci_validation_passed: <boolean>        # Did CI validation pass?
  
  # EXECUTION LANE SPECIFIC (optional)
  lane_specific:
    # UI Lane
    components_created: <integer>
    test_coverage_percent: <float>
    
    # SECURITY Lane
    vulnerabilities_found: <integer>
    vulnerabilities_fixed: <integer>
    
    # DEVOPS Lane
    pipeline_stages_added: <integer>
    deployment_time_ms: <integer>
    
    # SYSTEM_STATE Lane
    state_transitions: <integer>
    invariants_validated: <integer>
```

---

## 2. Required Fields Specification

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `execution_time_ms` | integer | >= 0 | Milliseconds from start to completion |
| `tasks_completed` | integer | >= 0 | Tasks successfully completed |
| `tasks_total` | integer | >= 1 | Total tasks assigned in PAC |
| `quality_score` | float | 0.0-1.0 | Self-assessed quality metric |
| `scope_compliance` | boolean | true/false | Stayed within PAC boundaries |

---

## 3. Quality Score Guidelines

```yaml
QUALITY_SCORE_RUBRIC:
  1.0: "Perfect execution — all requirements met, no issues"
  0.9: "Excellent — minor deviations, all critical requirements met"
  0.8: "Good — some non-critical issues, core functionality complete"
  0.7: "Acceptable — meets minimum requirements"
  0.6: "Below expectations — partial completion"
  0.5: "Needs improvement — significant gaps"
  < 0.5: "Unacceptable — major failures"
```

---

## 4. Scope Compliance Definition

```yaml
SCOPE_COMPLIANCE_RULES:
  true:
    - "All changes within PAC-defined FILE targets"
    - "No unauthorized artifact creation"
    - "No scope expansion beyond TASKS"
    - "No authority escalation"
    
  false:
    - "Modified files outside PAC scope"
    - "Created artifacts not in PAC plan"
    - "Expanded scope without authorization"
    - "Attempted actions in FORBIDDEN_ACTIONS"
```

---

## 5. Execution Lane Baselines

```yaml
EXECUTION_LANE_BASELINES:
  ORCHESTRATION:
    expected_quality_score: 0.95
    max_execution_time_ms: 300000  # 5 minutes
    scope_compliance_required: true
    
  GOVERNANCE:
    expected_quality_score: 0.98
    max_execution_time_ms: 180000  # 3 minutes
    scope_compliance_required: true
    
  SECURITY:
    expected_quality_score: 0.95
    max_execution_time_ms: 600000  # 10 minutes
    scope_compliance_required: true
    
  DEVOPS:
    expected_quality_score: 0.90
    max_execution_time_ms: 900000  # 15 minutes
    scope_compliance_required: true
    
  SYSTEM_STATE:
    expected_quality_score: 0.95
    max_execution_time_ms: 300000  # 5 minutes
    scope_compliance_required: true
    
  BACKEND:
    expected_quality_score: 0.90
    max_execution_time_ms: 1200000  # 20 minutes
    scope_compliance_required: true
    
  FRONTEND:
    expected_quality_score: 0.90
    max_execution_time_ms: 1200000  # 20 minutes
    scope_compliance_required: true
    
  ML_AI:
    expected_quality_score: 0.85
    max_execution_time_ms: 1800000  # 30 minutes
    scope_compliance_required: true
```

---

## 6. Error Codes

```yaml
ERROR_CODES:
  GS_080:
    name: "Missing METRICS block in EXECUTABLE artifact"
    severity: "HARD_FAIL"
    trigger: "EXECUTABLE artifact without METRICS block"
    
  GS_081:
    name: "METRICS block missing required field"
    severity: "HARD_FAIL"
    trigger: "Missing execution_time_ms, tasks_completed, tasks_total, quality_score, or scope_compliance"
    
  GS_082:
    name: "METRICS block contains invalid or unparseable value"
    severity: "HARD_FAIL"
    trigger: "YAML parse error or type mismatch"
    
  GS_083:
    name: "METRICS execution_time_ms must be numeric"
    severity: "HARD_FAIL"
    trigger: "Non-numeric value for execution_time_ms"
    
  GS_084:
    name: "METRICS quality_score out of valid range (0.0-1.0)"
    severity: "HARD_FAIL"
    trigger: "quality_score < 0.0 or > 1.0"
    
  GS_085:
    name: "METRICS scope_compliance must be boolean"
    severity: "HARD_FAIL"
    trigger: "Non-boolean value for scope_compliance"
```

---

## 7. Enforcement Rules

```yaml
ENFORCEMENT_RULES:
  executable_artifacts:
    - "PACs with TASKS and/or FILES blocks"
    - "WRAPs documenting execution completion"
    
  exempt_artifacts:
    - "Doctrinal PACs (constraints only, no TASKS)"
    - "Template files"
    - "Registry files"
    - "Legacy artifacts (grandfathered, flagged)"
    
  validation_mode: "FAIL_CLOSED"
  
  grandfathering:
    enabled: true
    cutoff_date: "2025-12-24"
    legacy_marker: "Pre-METRICS_SCHEMA_v1"
```

---

## 8. Example METRICS Blocks

### Minimal Valid Block

```yaml
METRICS:
  execution_time_ms: 45000
  tasks_completed: 3
  tasks_total: 3
  quality_score: 0.95
  scope_compliance: true
```

### Full Block with Optional Fields

```yaml
METRICS:
  execution_time_ms: 120000
  tasks_completed: 5
  tasks_total: 5
  quality_score: 0.92
  scope_compliance: true
  files_created: 3
  files_modified: 2
  lines_added: 450
  lines_removed: 120
  errors_encountered: 2
  errors_resolved: 2
  ci_validation_passed: true
  lane_specific:
    components_created: 2
    test_coverage_percent: 85.5
```

---

## 9. Ledger Integration

```yaml
LEDGER_INTEGRATION:
  enabled: true
  fields_recorded:
    - artifact_id
    - agent_gid
    - execution_time_ms
    - quality_score
    - scope_compliance
    - timestamp
    
  aggregation:
    - "Per-agent averages"
    - "Per-lane baselines"
    - "System-wide trends"
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# END GOVERNANCE_METRICS_SCHEMA v1.0.0
# STATUS: LOCKED | ENFORCEMENT: FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║ 🟦🟩 TEAL — BENSON (GID-00) — Governance Runtime                                     ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ METRICS_SCHEMA v1.0.0: LOCKED                                                        ║
║ Principle: What isn't measured cannot be trusted                                     ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
```
