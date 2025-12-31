# Governance Execution Metrics Schema

> **Schema Document** — PAC-ALEX-P36
> **Version:** 1.0.0
> **Effective Date:** 2025-12-24
> **Authority:** Benson (GID-00)
> **Status:** LOCKED / CANONICAL

---

## Purpose

This document defines the **canonical schema** for all execution metrics in ChainBridge governance artifacts.

All metric keys must conform to this schema. Non-standard keys trigger `GS_073` warnings.

---

## Schema Definition

```yaml
GOVERNANCE_EXECUTION_METRICS_SCHEMA:
  version: "1.0.0"
  enforcement: "MANDATORY"
  validation: "DETERMINISTIC"
```

---

## EXECUTION_METRICS Block

### Required Fields (Executable Artifacts)

| Key | Type | Description | Required |
|-----|------|-------------|----------|
| `tasks_planned` | INTEGER | Number of tasks in execution plan | YES |
| `tasks_completed` | INTEGER | Number of tasks successfully completed | YES |
| `validation_passed` | BOOLEAN | Whether gate_pack.py validation passed | YES |

### Recommended Fields

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `tasks_failed` | INTEGER | Number of tasks that failed | 0 |
| `completion_rate` | FLOAT | tasks_completed / tasks_planned | calculated |
| `files_created` | INTEGER | New files created | 0 |
| `files_modified` | INTEGER | Existing files modified | 0 |
| `lines_added` | INTEGER | Lines of code added | 0 |
| `lines_removed` | INTEGER | Lines of code removed | 0 |
| `tests_added` | INTEGER | New tests created | 0 |
| `tests_passing` | INTEGER | Tests passing after execution | 0 |
| `execution_time_seconds` | FLOAT | Wall-clock execution time | null |

### Example

```yaml
EXECUTION_METRICS:
  # Required
  tasks_planned: 5
  tasks_completed: 5
  validation_passed: true

  # Recommended
  tasks_failed: 0
  completion_rate: 1.0
  files_created: 3
  files_modified: 2
  lines_added: 450
  lines_removed: 12
  tests_added: 8
  tests_passing: 8
```

---

## FAILURE_QUALITY Block

For stress testing, adversarial analysis, and failure detection PACs.

| Key | Type | Description | Required |
|-----|------|-------------|----------|
| `failures_expected` | INTEGER | Failures that should be caught | YES |
| `failures_detected` | INTEGER | Failures actually caught | YES |
| `false_positives` | INTEGER | Incorrect failure flags | NO |
| `false_negatives` | INTEGER | Missed failures | NO |
| `detection_rate` | FLOAT | failures_detected / failures_expected | calculated |
| `stress_vectors_tested` | LIST[STRING] | Categories of stress applied | NO |

### Example

```yaml
FAILURE_QUALITY:
  failures_expected: 33
  failures_detected: 33
  false_positives: 0
  false_negatives: 0
  detection_rate: 1.0
  stress_vectors_tested:
    - "ORDERING"
    - "LEGACY"
    - "AUTHORITY"
    - "RACE"
    - "PARITY"
```

---

## AGENT_BEHAVIOR Block

For tracking agent-level patterns and learning signals.

| Key | Type | Description | Required |
|-----|------|-------------|----------|
| `corrections_received` | INTEGER | Corrections from review gates | NO |
| `self_corrections` | INTEGER | Self-identified issues fixed | NO |
| `scope_drift_events` | INTEGER | Times agent drifted from scope | NO |
| `gate_failures` | INTEGER | Hard gate failures encountered | NO |
| `gate_passes` | INTEGER | Successful gate passes | NO |
| `pacs_completed` | INTEGER | PACs completed in session | NO |
| `wraps_issued` | INTEGER | WRAPs issued in session | NO |

### Example

```yaml
AGENT_BEHAVIOR:
  corrections_received: 2
  self_corrections: 1
  scope_drift_events: 0
  gate_failures: 2
  gate_passes: 15
  pacs_completed: 5
  wraps_issued: 3
```

---

## Type Validation Rules

| Type | Validation Rule |
|------|-----------------|
| INTEGER | Must be non-negative whole number |
| FLOAT | Must be decimal, 0.0 ≤ value ≤ 1.0 for rates |
| BOOLEAN | Must be `true` or `false` |
| STRING | Must be non-empty |
| LIST | Must contain at least one element |

### Type Mismatch Error

```
[GS_074] Metric value type mismatch: 'tasks_completed' expected INTEGER, got STRING
```

---

## Metric Key Naming Conventions

1. **snake_case** — All metric keys use snake_case
2. **Descriptive** — Keys should be self-documenting
3. **No Abbreviations** — Avoid cryptic abbreviations
4. **Consistent Prefixes** — Use consistent prefixes for related metrics

### Valid Keys

```yaml
tasks_planned: 5          # ✅ snake_case, descriptive
completion_rate: 1.0      # ✅ clear meaning
files_created: 3          # ✅ action_noun pattern
```

### Invalid Keys

```yaml
TasksPlanned: 5           # ❌ PascalCase
comp_rt: 1.0              # ❌ abbreviation
numFiles: 3               # ❌ camelCase
```

---

## Cross-Block Consistency

When multiple metric blocks are present, certain values must be consistent:

| Block A | Block B | Consistency Rule |
|---------|---------|------------------|
| EXECUTION_METRICS.tasks_failed | AGENT_BEHAVIOR.gate_failures | tasks_failed ≤ gate_failures |
| EXECUTION_METRICS.tests_passing | EXECUTION_METRICS.tests_added | tests_passing ≤ tests_added |
| FAILURE_QUALITY.detection_rate | Calculated | Must equal failures_detected / failures_expected |

---

## Schema Enforcement

### gate_pack.py Implementation

```python
EXECUTION_METRICS_SCHEMA = {
    "required": ["tasks_planned", "tasks_completed", "validation_passed"],
    "types": {
        "tasks_planned": int,
        "tasks_completed": int,
        "tasks_failed": int,
        "completion_rate": float,
        "files_created": int,
        "files_modified": int,
        "lines_added": int,
        "lines_removed": int,
        "tests_added": int,
        "tests_passing": int,
        "validation_passed": bool,
        "execution_time_seconds": float,
    }
}

def validate_metrics_schema(metrics: dict) -> list[str]:
    """Validate EXECUTION_METRICS against schema."""
    errors = []

    # Check required fields
    for field in EXECUTION_METRICS_SCHEMA["required"]:
        if field not in metrics:
            errors.append(f"[GS_070] Missing required metric: {field}")

    # Check types
    for key, value in metrics.items():
        expected_type = EXECUTION_METRICS_SCHEMA["types"].get(key)
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"[GS_074] Type mismatch: '{key}' expected {expected_type.__name__}")

    return errors
```

---

## Versioning

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-24 | Initial schema release |

Future versions will maintain backward compatibility. New fields may be added but existing fields will not be removed or renamed without major version bump.

---

**Authority:** PAC-ALEX-P36-GOVERNANCE-MEASUREMENT-ENFORCEMENT-AND-AGENT-LEARNING-MANDATE-01
**Status:** LOCKED — Schema changes require BENSON (GID-00) authorization
