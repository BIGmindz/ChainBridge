# Governance Agent Baselines

> **PAC Reference:** PAC-MAGGIE-P36-GOVERNANCE-METRICS-LEARNING-LOOP-AND-AGENT-PERFORMANCE-BASELINE-01
> **Author:** Maggie (GID-10) | 💗 MAGENTA
> **Authority:** BENSON (GID-00)
> **Date:** 2025-12-24
> **Status:** CANONICAL

---

## 1. Overview

This document establishes performance baselines for all ChainBridge agents. Baselines are:

- **Objective** — Derived from measurable metrics
- **Role-calibrated** — Different roles have different expectations
- **Evolutive** — Baselines improve as system matures
- **Non-punitive** — Below-baseline triggers learning, not punishment

---

## 2. Baseline Methodology

### 2.1 Statistical Targets

```yaml
BASELINE_METHODOLOGY:
  percentile_targets:
    P50: "Median expected performance (acceptable)"
    P75: "Above-average performance (proficient)"
    P90: "High performance (exemplary)"
    P95: "Exceptional performance (rare)"

  threshold_definitions:
    minimum_acceptable: "P25"
    target: "P50"
    stretch_goal: "P75"

  measurement_window: "Rolling 30 days"
  sample_size_minimum: 10  # PACs required for valid baseline
```

### 2.2 Baseline Calculation

```yaml
BASELINE_CALCULATION:
  formula: |
    For each metric M:
      baseline_P50[M] = median(M_values over last 30 days)
      baseline_P75[M] = percentile_75(M_values over last 30 days)
      baseline_P90[M] = percentile_90(M_values over last 30 days)

  recalculation_frequency: "Weekly"

  cold_start:
    description: "Initial baselines before sufficient data"
    approach: "Use role-based industry standards"
```

---

## 3. Role-Specific Baselines

### 3.1 BACKEND Role Baselines

```yaml
BACKEND_BASELINES:
  role_id: "BACKEND"
  representative_agent: "Cody (GID-01)"

  speed_metrics:
    pac_completion_time:
      P50: 300   # 5 minutes
      P75: 180   # 3 minutes
      P90: 120   # 2 minutes
      unit: "seconds"

    iterations_to_valid:
      P50: 2
      P75: 1
      P90: 1
      unit: "integer"

  accuracy_metrics:
    first_pass_validity:
      P50: 0.70
      P75: 0.85
      P90: 0.95
      unit: "ratio"

    deliverable_completeness:
      P50: 1.0
      P75: 1.0
      P90: 1.0
      unit: "ratio"
      minimum: 1.0  # Non-negotiable

    test_pass_rate:
      P50: 0.95
      P75: 0.98
      P90: 1.0
      unit: "ratio"

  scope_discipline_metrics:
    lane_violations:
      P50: 0
      P75: 0
      P90: 0
      unit: "integer"
      maximum: 0  # Zero tolerance

  governance_compliance_metrics:
    gold_standard_compliance:
      P50: 0.95
      P75: 1.0
      P90: 1.0
      unit: "ratio"
```

### 3.2 FRONTEND Role Baselines

```yaml
FRONTEND_BASELINES:
  role_id: "FRONTEND"
  representative_agent: "Dan (GID-07)"

  speed_metrics:
    pac_completion_time:
      P50: 240
      P75: 150
      P90: 90
      unit: "seconds"

    iterations_to_valid:
      P50: 2
      P75: 1
      P90: 1
      unit: "integer"

  accuracy_metrics:
    first_pass_validity:
      P50: 0.65
      P75: 0.80
      P90: 0.90
      unit: "ratio"

    deliverable_completeness:
      P50: 1.0
      P75: 1.0
      P90: 1.0
      unit: "ratio"
      minimum: 1.0

  scope_discipline_metrics:
    lane_violations:
      P50: 0
      P75: 0
      P90: 0
      unit: "integer"
      maximum: 0

  governance_compliance_metrics:
    gold_standard_compliance:
      P50: 0.90
      P75: 0.95
      P90: 1.0
      unit: "ratio"
```

### 3.3 SECURITY Role Baselines

```yaml
SECURITY_BASELINES:
  role_id: "SECURITY"
  representative_agent: "Sam (GID-06)"

  speed_metrics:
    pac_completion_time:
      P50: 600   # Security work requires thoroughness
      P75: 400
      P90: 240
      unit: "seconds"

    iterations_to_valid:
      P50: 3     # More iteration expected for complex security
      P75: 2
      P90: 1
      unit: "integer"

  accuracy_metrics:
    first_pass_validity:
      P50: 0.60
      P75: 0.75
      P90: 0.90
      unit: "ratio"
      note: "Security thoroughness prioritized over speed"

    deliverable_completeness:
      P50: 1.0
      P75: 1.0
      P90: 1.0
      unit: "ratio"
      minimum: 1.0

  scope_discipline_metrics:
    lane_violations:
      P50: 0
      P75: 0
      P90: 0
      unit: "integer"
      maximum: 0
      note: "CRITICAL for security role"

  failure_quality_metrics:
    failure_explainability:
      P50: 1.0   # Security failures MUST be explainable
      P75: 1.0
      P90: 1.0
      unit: "ratio"
      minimum: 1.0
```

### 3.4 ML_AI Role Baselines

```yaml
ML_AI_BASELINES:
  role_id: "ML_AI"
  representative_agent: "Maggie (GID-10)"

  speed_metrics:
    pac_completion_time:
      P50: 480
      P75: 300
      P90: 180
      unit: "seconds"

    iterations_to_valid:
      P50: 2
      P75: 1
      P90: 1
      unit: "integer"

  accuracy_metrics:
    first_pass_validity:
      P50: 0.70
      P75: 0.85
      P90: 0.95
      unit: "ratio"

    deliverable_completeness:
      P50: 1.0
      P75: 1.0
      P90: 1.0
      unit: "ratio"
      minimum: 1.0

  scope_discipline_metrics:
    lane_violations:
      P50: 0
      P75: 0
      P90: 0
      unit: "integer"
      maximum: 0

  failure_quality_metrics:
    failure_explainability:
      P50: 1.0   # ML outputs MUST be glass-box
      P75: 1.0
      P90: 1.0
      unit: "ratio"
      minimum: 1.0
```

### 3.5 STRATEGY Role Baselines

```yaml
STRATEGY_BASELINES:
  role_id: "STRATEGY"
  representative_agent: "Atlas (GID-05)"

  speed_metrics:
    pac_completion_time:
      P50: 360
      P75: 240
      P90: 150
      unit: "seconds"

    iterations_to_valid:
      P50: 2
      P75: 1
      P90: 1
      unit: "integer"

  accuracy_metrics:
    first_pass_validity:
      P50: 0.75
      P75: 0.85
      P90: 0.95
      unit: "ratio"

    deliverable_completeness:
      P50: 1.0
      P75: 1.0
      P90: 1.0
      unit: "ratio"
      minimum: 1.0

  scope_discipline_metrics:
    lane_violations:
      P50: 0
      P75: 0
      P90: 0
      unit: "integer"
      maximum: 0
```

### 3.6 QUALITY_ASSURANCE Role Baselines

```yaml
QUALITY_ASSURANCE_BASELINES:
  role_id: "QUALITY_ASSURANCE"
  representative_agent: "Alex (GID-08)"

  speed_metrics:
    pac_completion_time:
      P50: 420
      P75: 270
      P90: 180
      unit: "seconds"

    iterations_to_valid:
      P50: 2
      P75: 1
      P90: 1
      unit: "integer"

  accuracy_metrics:
    first_pass_validity:
      P50: 0.80   # QA expected to have high accuracy
      P75: 0.90
      P90: 0.98
      unit: "ratio"

    deliverable_completeness:
      P50: 1.0
      P75: 1.0
      P90: 1.0
      unit: "ratio"
      minimum: 1.0

  failure_quality_metrics:
    failure_explainability:
      P50: 1.0   # QA failures MUST be explainable
      P75: 1.0
      P90: 1.0
      unit: "ratio"
      minimum: 1.0
```

---

## 4. Metrics → Learning Actions

### 4.1 Drift Detection

```yaml
DRIFT_DETECTION:
  definition: "Performance deviation from baseline"

  drift_levels:
    MINOR:
      threshold: "Below P50 for 3 consecutive PACs"
      action: "TRAINING_SIGNAL emitted (BEHAVIORAL_ADJUSTMENT)"
      blocking: false

    MODERATE:
      threshold: "Below P25 for 2 consecutive PACs"
      action: "TRAINING_SIGNAL emitted + agent-specific review"
      blocking: false

    SEVERE:
      threshold: "Below P10 for any PAC"
      action: "Immediate BENSON review required"
      blocking: true
```

### 4.2 Learning Actions Matrix

```yaml
LEARNING_ACTIONS_MATRIX:
  speed_drift:
    minor:
      signal_type: "BEHAVIORAL_ADJUSTMENT"
      lesson: "Review reference PACs before starting"
      action: "Add pre-execution checklist review"

    moderate:
      signal_type: "BEHAVIORAL_ADJUSTMENT"
      lesson: "Break complex PACs into smaller units"
      action: "Mandate scope decomposition"

    severe:
      signal_type: "ERROR_CORRECTION"
      lesson: "Root cause analysis required"
      action: "Human review of process"

  accuracy_drift:
    minor:
      signal_type: "NEGATIVE_REINFORCEMENT"
      lesson: "Validate early and often"
      action: "Mandate mid-PAC validation"

    moderate:
      signal_type: "ERROR_CORRECTION"
      lesson: "Review Gold Standard checklist before submit"
      action: "Pre-submit checklist enforcement"

    severe:
      signal_type: "ERROR_CORRECTION"
      lesson: "Pattern review required"
      action: "Full execution log review"

  scope_violation:
    any:
      signal_type: "NEGATIVE_REINFORCEMENT"
      lesson: "Execution lane boundaries are absolute"
      action: "Mandatory lane review before PAC start"
      blocking: true
```

---

## 5. Governance Enforcement Hooks

### 5.1 Current Enforcement (Immediate)

```yaml
CURRENT_ENFORCEMENT:
  scope_violations:
    metric: "lane_violations, tool_violations"
    threshold: "> 0"
    enforcement: "BLOCK"
    implemented_in: "gate_pack.py"

  deliverable_completeness:
    metric: "deliverable_completeness"
    threshold: "< 1.0"
    enforcement: "BLOCK"
    implemented_in: "gate_pack.py"

  governance_compliance:
    metric: "pag01_compliance, gold_standard_compliance"
    threshold: "< 1.0"
    enforcement: "BLOCK"
    implemented_in: "gate_pack.py"
```

### 5.2 Future Enforcement (Planned)

```yaml
FUTURE_ENFORCEMENT:
  first_pass_validity:
    metric: "first_pass_validity"
    threshold: "< P25 for 5 consecutive PACs"
    enforcement: "WARN → BLOCK (after observation)"
    timeline: "Q2 2026"

  iterations_to_valid:
    metric: "iterations_to_valid"
    threshold: "> 5"
    enforcement: "WARN"
    timeline: "Q1 2026"

  failure_quality:
    metric: "failure_explainability"
    threshold: "< 1.0"
    enforcement: "BLOCK"
    timeline: "Q1 2026"
```

---

## 6. Baseline Evolution

### 6.1 Baseline Improvement Targets

```yaml
BASELINE_IMPROVEMENT_TARGETS:
  quarterly_improvement:
    P50_target: "+5% per quarter"
    P75_target: "+3% per quarter"
    P90_target: "+2% per quarter"

  ceiling_definition:
    first_pass_validity: 0.98
    lane_violations: 0
    gold_standard_compliance: 1.0

  floor_raising:
    description: "Minimum acceptable raises over time"
    mechanism: "P25 becomes new P10 after 6 months of data"
```

### 6.2 Baseline Review Process

```yaml
BASELINE_REVIEW_PROCESS:
  frequency: "Monthly"
  reviewer: "BENSON (GID-00)"

  review_checklist:
    - "Are current baselines achievable?"
    - "Has system maturity warranted raising floors?"
    - "Are any baselines creating perverse incentives?"
    - "Do role-specific adjustments remain appropriate?"

  change_process:
    - "Propose via PAC"
    - "30-day observation period"
    - "BENSON approval required"
    - "Communicate to all affected agents"
```

---

## 7. Composite Baseline Summary

### 7.1 Universal Baselines (All Roles)

```yaml
UNIVERSAL_BASELINES:
  non_negotiable:
    lane_violations: 0
    tool_violations: 0
    deliverable_completeness: 1.0
    pag01_compliance: 1.0
    silent_failures: 0

  target:
    gold_standard_compliance: 0.95
    first_pass_validity: 0.70
    iterations_to_valid: 2
```

### 7.2 Role Priority Summary

| Role | Primary Focus | Secondary Focus | Speed Priority |
|------|---------------|-----------------|----------------|
| BACKEND | Accuracy | Scope Discipline | Medium |
| FRONTEND | Accuracy | Governance | High |
| SECURITY | Accuracy | Scope Discipline | Low |
| ML_AI | Accuracy | Failure Quality | Medium |
| STRATEGY | Accuracy | Governance | Medium |
| QA | Accuracy | Failure Quality | Medium |

---

## 8. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-24 | Maggie (GID-10) | Initial baseline definition |

---

**END — GOVERNANCE_AGENT_BASELINES.md**
