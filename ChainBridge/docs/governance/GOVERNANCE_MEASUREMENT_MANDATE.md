# Governance Measurement Mandate

> **Governance Document** — PAC-ALEX-P36  
> **Version:** 1.0.0  
> **Effective Date:** 2025-12-24  
> **Authority:** Benson (GID-00)  
> **Enforced By:** ALEX (GID-08)  
> **Status:** LOCKED / CANONICAL / MACHINE-ENFORCED

---

## Purpose

This document establishes the **Governance Measurement Mandate** — a mandatory requirement that all executable PACs and WRAPs must include measurement blocks.

```
No Metrics = No Completion
Execution without metrics is indistinguishable from guesswork.
```

---

## Core Doctrine

### 1. Measurement is Non-Optional

All executing agents must emit metrics. This is not a suggestion — it is a hard gate.

| Artifact Type | Metrics Required | Enforcement |
|---------------|------------------|-------------|
| Executable PAC | YES | HARD FAIL |
| WRAP | YES | HARD FAIL |
| Analysis-Only PAC | NO | N/A |
| Non-Executing Agent Work | NO | N/A |

### 2. The Execution-Training Loop

```
EXECUTION → MEASUREMENT → TRAINING_SIGNAL → IMPROVEMENT
     ↑                                            ↓
     ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

This loop must be closed. Metrics without training signals are orphaned data. Training signals without metrics are ungrounded assertions.

### 3. Fail-Closed Enforcement

Missing measurement blocks trigger **HARD FAIL** at:
- Gate 1: Pack emission validation (`gate_pack.py`)
- Gate 2: Pre-commit hooks
- Gate 3: CI merge blockers

No bypass paths exist.

---

## Mandatory Measurement Blocks

### EXECUTION_METRICS

Required for all executable PACs and WRAPs.

```yaml
EXECUTION_METRICS:
  tasks_planned: INTEGER        # Number of tasks in plan
  tasks_completed: INTEGER      # Number of tasks completed
  tasks_failed: INTEGER         # Number of tasks that failed
  completion_rate: FLOAT        # tasks_completed / tasks_planned
  files_created: INTEGER        # New files created
  files_modified: INTEGER       # Existing files modified
  lines_added: INTEGER          # Lines of code added
  lines_removed: INTEGER        # Lines of code removed
  tests_added: INTEGER          # New tests created
  tests_passing: INTEGER        # Tests passing after execution
  validation_passed: BOOLEAN    # gate_pack.py validation result
```

### FAILURE_QUALITY (Optional but Recommended)

For PACs involving stress testing or failure detection.

```yaml
FAILURE_QUALITY:
  failures_expected: INTEGER    # Failures that should have been caught
  failures_detected: INTEGER    # Failures actually caught
  false_positives: INTEGER      # Incorrect failure detections
  false_negatives: INTEGER      # Missed failures
  detection_rate: FLOAT         # failures_detected / failures_expected
```

### AGENT_BEHAVIOR (Optional but Recommended)

For tracking agent-level patterns.

```yaml
AGENT_BEHAVIOR:
  corrections_received: INTEGER # Corrections from review gates
  self_corrections: INTEGER     # Self-identified issues
  scope_drift_events: INTEGER   # Times agent drifted from scope
  gate_failures: INTEGER        # Hard gate failures
  gate_passes: INTEGER          # Successful gate passes
```

---

## Binding to TRAINING_SIGNAL

When metrics are present, at least one `TRAINING_SIGNAL` must be emitted.

```yaml
TRAINING_SIGNAL:
  signal_type: "POSITIVE_REINFORCEMENT" | "CORRECTIVE" | "BLOCKING"
  pattern: STRING               # The learned pattern
  lesson: STRING | LIST         # What was learned
  propagate: BOOLEAN            # Whether to share with other agents
  mandatory: BOOLEAN            # Whether signal is required
```

### Valid Bindings

| Metrics Present | Training Signal Required | Result |
|-----------------|--------------------------|--------|
| YES | YES | ✅ VALID |
| YES | NO | ❌ HARD FAIL (GS_072) |
| NO | YES | ⚠️ WARNING (ungrounded) |
| NO | NO | ✅ VALID (analysis-only) |

---

## Error Codes

| Code | Description | Response |
|------|-------------|----------|
| `GS_070` | EXECUTION_METRICS block missing from executable artifact | HARD FAIL |
| `GS_071` | Training loop incomplete (metrics without signal) | HARD FAIL |
| `GS_072` | TRAINING_SIGNAL missing when metrics present | HARD FAIL |
| `GS_073` | Metric key non-standard | WARNING |
| `GS_074` | Metric value type mismatch | HARD FAIL |

---

## Enforcement Implementation

### gate_pack.py Validation

```python
def validate_measurement_mandate(artifact: dict) -> list[str]:
    """Validate measurement mandate compliance."""
    errors = []
    
    # Check if executable
    is_executable = artifact.get("mode") == "EXECUTABLE"
    
    if is_executable:
        # EXECUTION_METRICS required
        if "EXECUTION_METRICS" not in artifact:
            errors.append("[GS_070] EXECUTION_METRICS block missing")
        
        # If metrics present, TRAINING_SIGNAL required
        has_metrics = "EXECUTION_METRICS" in artifact
        has_signal = "TRAINING_SIGNAL" in artifact
        
        if has_metrics and not has_signal:
            errors.append("[GS_072] TRAINING_SIGNAL required when metrics present")
    
    return errors
```

---

## Compliance Examples

### ✅ Compliant Executable PAC

```yaml
EXECUTION_METRICS:
  tasks_planned: 5
  tasks_completed: 5
  completion_rate: 1.0
  validation_passed: true

TRAINING_SIGNAL:
  signal_type: "POSITIVE_REINFORCEMENT"
  pattern: "TASK_COMPLETION_DISCIPLINE"
  lesson: "All planned tasks completed with validation"
  propagate: true
```

### ❌ Non-Compliant (Missing Metrics)

```yaml
# No EXECUTION_METRICS block
TRAINING_SIGNAL:
  signal_type: "POSITIVE_REINFORCEMENT"
  pattern: "UNGROUNDED_ASSERTION"
  lesson: "Trust me, it worked"
```

**Result:** `[GS_070] EXECUTION_METRICS block missing`

### ❌ Non-Compliant (Missing Training Signal)

```yaml
EXECUTION_METRICS:
  tasks_planned: 5
  tasks_completed: 5
  completion_rate: 1.0

# No TRAINING_SIGNAL block
```

**Result:** `[GS_072] TRAINING_SIGNAL required when metrics present`

---

## Canonical Statement

```
Governance is physics, not policy.
Measurement is oxygen, not decoration.
No Metrics = No Completion.
```

---

**Authority:** PAC-ALEX-P36-GOVERNANCE-MEASUREMENT-ENFORCEMENT-AND-AGENT-LEARNING-MANDATE-01  
**Enforced By:** gate_pack.py, pre-commit hooks, CI merge blockers  
**Status:** LOCKED — No amendments without BENSON (GID-00) authorization
