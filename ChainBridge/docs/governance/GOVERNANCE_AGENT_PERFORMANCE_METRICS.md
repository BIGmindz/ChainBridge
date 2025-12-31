# Governance Agent Performance Metrics

> **PAC Reference:** PAC-MAGGIE-P36-GOVERNANCE-METRICS-LEARNING-LOOP-AND-AGENT-PERFORMANCE-BASELINE-01
> **Author:** Maggie (GID-10) | 💗 MAGENTA
> **Authority:** BENSON (GID-00)
> **Date:** 2025-12-24
> **Status:** CANONICAL

---

## 1. Overview

This document defines the canonical performance metrics for all ChainBridge agents. These metrics are:

- **Deterministic** — Computed from objective, observable data
- **Glass-box** — No opaque ML scores; all calculations are transparent
- **Role-specific** — Different agent roles have different metric weights
- **Replayable** — Same inputs produce same metric outputs
- **Non-judgmental** — Metrics are signals, not verdicts

---

## 2. Core Metric Categories

### 2.1 Metric Taxonomy

```yaml
METRIC_TAXONOMY:
  categories:
    - id: "SPEED"
      description: "Time efficiency of task completion"
      unit: "seconds | iterations"

    - id: "ACCURACY"
      description: "Correctness of deliverables"
      unit: "percentage | ratio"

    - id: "CORRECTION_RATE"
      description: "Frequency of self-corrections needed"
      unit: "corrections_per_pac"

    - id: "SCOPE_DISCIPLINE"
      description: "Adherence to declared execution lane"
      unit: "violations_count"

    - id: "FAILURE_QUALITY"
      description: "Actionability and clarity of failure signals"
      unit: "quality_score (0-100)"

    - id: "GOVERNANCE_COMPLIANCE"
      description: "Adherence to PAC/WRAP structure requirements"
      unit: "compliance_rate"
```

---

## 3. Metric Definitions

### 3.1 SPEED Metrics

```yaml
SPEED_METRICS:
  pac_completion_time:
    id: "SPD_001"
    description: "Wall-clock time from PAC receipt to commit"
    formula: "commit_timestamp - pac_received_timestamp"
    unit: "seconds"
    measurement: "AUTOMATED"

  iterations_to_valid:
    id: "SPD_002"
    description: "Number of gate_pack.py runs until VALID"
    formula: "count(validation_attempts until status=VALID)"
    unit: "integer"
    measurement: "AUTOMATED"

  correction_cycles:
    id: "SPD_003"
    description: "Number of edit-validate cycles per PAC"
    formula: "count(file_edits between pac_start and commit)"
    unit: "integer"
    measurement: "AUTOMATED"
```

### 3.2 ACCURACY Metrics

```yaml
ACCURACY_METRICS:
  first_pass_validity:
    id: "ACC_001"
    description: "PAC passes gate_pack.py on first attempt"
    formula: "1 if first_validation=VALID else 0"
    unit: "boolean (0|1)"
    measurement: "AUTOMATED"

  deliverable_completeness:
    id: "ACC_002"
    description: "All declared deliverables are present"
    formula: "delivered_files / declared_files"
    unit: "ratio (0.0-1.0)"
    measurement: "AUTOMATED"

  test_pass_rate:
    id: "ACC_003"
    description: "Percentage of tests passing (if applicable)"
    formula: "passed_tests / total_tests"
    unit: "percentage"
    measurement: "AUTOMATED"

  regression_introduction:
    id: "ACC_004"
    description: "New failures introduced by PAC execution"
    formula: "count(new_failures_post_commit)"
    unit: "integer"
    measurement: "AUTOMATED"
```

### 3.3 CORRECTION_RATE Metrics

```yaml
CORRECTION_RATE_METRICS:
  self_corrections:
    id: "COR_001"
    description: "Corrections made before external feedback"
    formula: "count(self_initiated_edits)"
    unit: "integer"
    measurement: "AUTOMATED"

  external_corrections:
    id: "COR_002"
    description: "Corrections required after human/system feedback"
    formula: "count(feedback_triggered_edits)"
    unit: "integer"
    measurement: "AUTOMATED"

  correction_ratio:
    id: "COR_003"
    description: "Ratio of corrections to total edits"
    formula: "total_corrections / total_edits"
    unit: "ratio (0.0-1.0)"
    measurement: "COMPUTED"
```

### 3.4 SCOPE_DISCIPLINE Metrics

```yaml
SCOPE_DISCIPLINE_METRICS:
  lane_violations:
    id: "SCP_001"
    description: "Attempts to access paths outside execution lane"
    formula: "count(path_access where path not in allowed_paths)"
    unit: "integer"
    measurement: "AUTOMATED"

  tool_violations:
    id: "SCP_002"
    description: "Attempts to use blocked tools"
    formula: "count(tool_use where tool in tools_blocked)"
    unit: "integer"
    measurement: "AUTOMATED"

  scope_drift_events:
    id: "SCP_003"
    description: "Work performed outside declared PAC scope"
    formula: "count(actions where action not in declared_scope)"
    unit: "integer"
    measurement: "AUTOMATED"

  authority_overreach:
    id: "SCP_004"
    description: "Attempts to claim unauthorized authority"
    formula: "count(authority_claims where claim > assigned_authority)"
    unit: "integer"
    measurement: "AUTOMATED"
```

### 3.5 FAILURE_QUALITY Metrics

```yaml
FAILURE_QUALITY_METRICS:
  failure_explainability:
    id: "FQL_001"
    description: "Failures include actionable resolution steps"
    formula: "failures_with_resolution / total_failures"
    unit: "ratio (0.0-1.0)"
    measurement: "AUTOMATED"

  failure_evidence:
    id: "FQL_002"
    description: "Failures include specific evidence"
    formula: "failures_with_evidence / total_failures"
    unit: "ratio (0.0-1.0)"
    measurement: "AUTOMATED"

  silent_failure_rate:
    id: "FQL_003"
    description: "Failures that emit no signal"
    formula: "silent_failures / total_failures"
    unit: "ratio (0.0-1.0)"
    measurement: "AUTOMATED"
    target: "0.0"
```

### 3.6 GOVERNANCE_COMPLIANCE Metrics

```yaml
GOVERNANCE_COMPLIANCE_METRICS:
  pag01_compliance:
    id: "GOV_001"
    description: "PAG-01 blocks present and valid"
    formula: "1 if pag01_valid else 0"
    unit: "boolean (0|1)"
    measurement: "AUTOMATED"

  gold_standard_compliance:
    id: "GOV_002"
    description: "All Gold Standard checklist items pass"
    formula: "passed_gs_items / total_gs_items"
    unit: "ratio (0.0-1.0)"
    measurement: "AUTOMATED"

  training_signal_present:
    id: "GOV_003"
    description: "TRAINING_SIGNAL block present and valid"
    formula: "1 if training_signal_valid else 0"
    unit: "boolean (0|1)"
    measurement: "AUTOMATED"
```

---

## 4. Role-Specific Metric Weights

Different agent roles have different performance priorities.

### 4.1 Weight Matrix

```yaml
ROLE_METRIC_WEIGHTS:
  BACKEND:
    agent_example: "Cody (GID-01)"
    weights:
      SPEED: 0.15
      ACCURACY: 0.30
      CORRECTION_RATE: 0.15
      SCOPE_DISCIPLINE: 0.20
      FAILURE_QUALITY: 0.10
      GOVERNANCE_COMPLIANCE: 0.10
    priority: "ACCURACY > SCOPE_DISCIPLINE > SPEED"

  FRONTEND:
    agent_example: "Dan (GID-07)"
    weights:
      SPEED: 0.20
      ACCURACY: 0.25
      CORRECTION_RATE: 0.10
      SCOPE_DISCIPLINE: 0.15
      FAILURE_QUALITY: 0.10
      GOVERNANCE_COMPLIANCE: 0.20
    priority: "ACCURACY > GOVERNANCE_COMPLIANCE > SPEED"

  SECURITY:
    agent_example: "Sam (GID-06)"
    weights:
      SPEED: 0.05
      ACCURACY: 0.35
      CORRECTION_RATE: 0.10
      SCOPE_DISCIPLINE: 0.25
      FAILURE_QUALITY: 0.15
      GOVERNANCE_COMPLIANCE: 0.10
    priority: "ACCURACY > SCOPE_DISCIPLINE > FAILURE_QUALITY"

  ML_AI:
    agent_example: "Maggie (GID-10)"
    weights:
      SPEED: 0.10
      ACCURACY: 0.30
      CORRECTION_RATE: 0.15
      SCOPE_DISCIPLINE: 0.15
      FAILURE_QUALITY: 0.15
      GOVERNANCE_COMPLIANCE: 0.15
    priority: "ACCURACY > FAILURE_QUALITY > GOVERNANCE_COMPLIANCE"

  STRATEGY:
    agent_example: "Atlas (GID-05)"
    weights:
      SPEED: 0.10
      ACCURACY: 0.25
      CORRECTION_RATE: 0.15
      SCOPE_DISCIPLINE: 0.20
      FAILURE_QUALITY: 0.10
      GOVERNANCE_COMPLIANCE: 0.20
    priority: "ACCURACY > SCOPE_DISCIPLINE > GOVERNANCE_COMPLIANCE"

  QUALITY_ASSURANCE:
    agent_example: "Alex (GID-08)"
    weights:
      SPEED: 0.10
      ACCURACY: 0.35
      CORRECTION_RATE: 0.10
      SCOPE_DISCIPLINE: 0.15
      FAILURE_QUALITY: 0.20
      GOVERNANCE_COMPLIANCE: 0.10
    priority: "ACCURACY > FAILURE_QUALITY > SCOPE_DISCIPLINE"
```

---

## 5. Composite Score Calculation

### 5.1 Normalized Score Formula

Each metric is normalized to a 0-100 scale before weighting:

```yaml
NORMALIZATION_RULES:
  count_metrics:
    formula: "max(0, 100 - (value * penalty_per_unit))"
    example: "violations=2, penalty=10 → score=80"

  ratio_metrics:
    formula: "value * 100"
    example: "ratio=0.95 → score=95"

  time_metrics:
    formula: "max(0, 100 - ((value - target) / target * 100))"
    example: "time=120s, target=60s → score=0"
    bounds: "[0, 100]"
```

### 5.2 Composite Score Formula

```yaml
COMPOSITE_SCORE:
  formula: |
    composite = Σ(category_score * category_weight)

    where:
      category_score = Σ(metric_score) / count(metrics_in_category)
      category_weight = ROLE_METRIC_WEIGHTS[role][category]

  output_range: "[0, 100]"
  interpretation:
    "90-100": "EXEMPLARY"
    "75-89": "PROFICIENT"
    "60-74": "ACCEPTABLE"
    "40-59": "NEEDS_IMPROVEMENT"
    "0-39": "CRITICAL_REVIEW_REQUIRED"
```

---

## 6. Metric Collection Points

### 6.1 Automated Collection

```yaml
AUTOMATED_COLLECTION_POINTS:
  pac_start:
    triggers: "PAC receipt acknowledged"
    collects:
      - "timestamp"
      - "agent_id"
      - "pac_id"
      - "declared_scope"

  validation_attempt:
    triggers: "gate_pack.py execution"
    collects:
      - "attempt_number"
      - "validation_result"
      - "error_codes"
      - "duration"

  file_edit:
    triggers: "File modification"
    collects:
      - "file_path"
      - "edit_type"
      - "in_allowed_paths"
      - "correction_flag"

  pac_complete:
    triggers: "Git commit"
    collects:
      - "commit_hash"
      - "files_changed"
      - "total_duration"
      - "final_validation_status"
```

### 6.2 Metric Persistence

```yaml
METRIC_PERSISTENCE:
  storage: "metrics/agent_performance/"
  format: "JSON"
  retention: "365 days"
  aggregation: "daily, weekly, monthly"

  file_naming:
    pattern: "{agent_gid}_{pac_id}_{timestamp}.json"
    example: "GID-10_PAC-MAGGIE-P36_2025-12-24T00-00-00Z.json"
```

---

## 7. Metric Constraints

### 7.1 Glass-Box Requirements

```yaml
GLASS_BOX_CONSTRAINTS:
  - constraint: "All metric formulas must be published"
    enforcement: "MANDATORY"

  - constraint: "No ML-derived metrics without explainer"
    enforcement: "MANDATORY"

  - constraint: "Metric weights must be role-documented"
    enforcement: "MANDATORY"

  - constraint: "Score components must be individually visible"
    enforcement: "MANDATORY"

  - constraint: "No aggregation that hides individual failures"
    enforcement: "MANDATORY"
```

### 7.2 Anti-Gaming Constraints

```yaml
ANTI_GAMING_CONSTRAINTS:
  - constraint: "Speed cannot offset accuracy failures"
    rule: "if ACCURACY < 60, composite capped at 59"

  - constraint: "Scope violations are multiplicative penalties"
    rule: "if lane_violations > 0, composite *= 0.8"

  - constraint: "Silent failures zero FAILURE_QUALITY score"
    rule: "if silent_failures > 0, FQL_score = 0"

  - constraint: "First-pass validity bonus cannot exceed 10%"
    rule: "max_bonus = 10"
```

---

## 8. Metric Evolution

### 8.1 Metric Change Process

```yaml
METRIC_CHANGE_PROCESS:
  steps:
    1: "Propose new metric or modification via PAC"
    2: "Document formula, collection point, and rationale"
    3: "Baseline against historical data (if available)"
    4: "BENSON (GID-00) approval required"
    5: "30-day observation period before enforcement"

  prohibited_changes:
    - "Removing metrics retroactively"
    - "Changing formulas without re-baselining"
    - "Adding opaque or non-deterministic metrics"
```

---

## 9. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-24 | Maggie (GID-10) | Initial canonical definition |

---

**END — GOVERNANCE_AGENT_PERFORMANCE_METRICS.md**
