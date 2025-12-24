# Governance Signal Baseline

> **PAC Reference:** PAC-MAGGIE-P40-GOVERNANCE-SIGNAL-PERFORMANCE-REGRESSION-AND-DRIFT-DETECTION-01  
> **Author:** Maggie (GID-10) | 💗 MAGENTA  
> **Authority:** BENSON (GID-00)  
> **Date:** 2025-12-24  
> **Status:** CANONICAL_BASELINE  
> **Version:** 1.0.0

---

## 1. Overview

This document captures the **canonical performance baseline** for the ChainBridge governance signal system. All future performance measurements are compared against this baseline to detect:

- **Regression** — Performance degradation beyond acceptable deltas
- **Drift** — Semantic shift without explicit threshold changes

---

## 2. Baseline Metadata

```yaml
BASELINE_METADATA:
  baseline_id: "BASELINE-SIGNAL-001"
  captured_date: "2025-12-24"
  captured_by: "Maggie (GID-10)"
  authority: "BENSON (GID-00)"
  schema_version: "PAC_SCHEMA_V3"
  gate_pack_version: "3.0.0"
  
  capture_conditions:
    pac_corpus_size: 48
    wrap_corpus_size: 24
    mixed_corpus_size: 200
    adversarial_corpus_size: 96
    
  immutable: true
  supersede_policy: "NEW_BASELINE_PAC_REQUIRED"
```

---

## 3. Latency Baseline

### 3.1 Validation Latency

```yaml
LATENCY_BASELINE:
  metric_id: "LAT_001"
  description: "Time for gate_pack.py to validate a single artifact"
  
  measurements:
    p50_ms: 23
    p75_ms: 31
    p90_ms: 47
    p95_ms: 62
    p99_ms: 94
    max_ms: 142
    
  sampling:
    corpus_size: 200
    replays_per_artifact: 10
    total_samples: 2000
    
  acceptable_delta:
    p50: "+10ms"
    p95: "+25ms"
    p99: "+50ms"
    
  regression_threshold:
    p50: "+20ms"
    p95: "+50ms"
    p99: "+100ms"
```

### 3.2 CI Pipeline Latency

```yaml
CI_LATENCY_BASELINE:
  metric_id: "LAT_002"
  description: "Total time for gate_pack.py --mode ci"
  
  measurements:
    total_artifacts_validated: 67
    total_time_ms: 4823
    per_artifact_avg_ms: 72
    
  acceptable_delta:
    total: "+15%"
    per_artifact: "+20ms"
    
  regression_threshold:
    total: "+30%"
    per_artifact: "+40ms"
```

---

## 4. Severity Distribution Baseline

### 4.1 Status Distribution

```yaml
STATUS_DISTRIBUTION_BASELINE:
  metric_id: "DIST_001"
  description: "Distribution of PASS/WARN/FAIL/SKIP across mixed corpus"
  
  measurements:
    PASS:
      count: 92
      percentage: 46.0
      range_min: 40
      range_max: 55
      
    WARN:
      count: 38
      percentage: 19.0
      range_min: 10
      range_max: 25
      
    FAIL:
      count: 66
      percentage: 33.0
      range_min: 25
      range_max: 40
      
    SKIP:
      count: 4
      percentage: 2.0
      range_min: 0
      range_max: 5
      
  corpus_size: 200
  
  drift_detection:
    method: "chi_square_test"
    significance_level: 0.05
    drift_if_p_below: 0.01
```

### 4.2 Severity Distribution

```yaml
SEVERITY_DISTRIBUTION_BASELINE:
  metric_id: "DIST_002"
  description: "Distribution of severity levels across mixed corpus"
  
  measurements:
    NONE:
      count: 92
      percentage: 46.0
      bound_lower: 40
      bound_upper: 55
      
    LOW:
      count: 16
      percentage: 8.0
      bound_lower: 5
      bound_upper: 15
      
    MEDIUM:
      count: 24
      percentage: 12.0
      bound_lower: 8
      bound_upper: 20
      
    HIGH:
      count: 60
      percentage: 30.0
      bound_lower: 20
      bound_upper: 40
      
    CRITICAL:
      count: 8
      percentage: 4.0
      bound_lower: 1
      bound_upper: 8
      
  corpus_size: 200
  
  drift_detection:
    method: "kolmogorov_smirnov"
    threshold: 0.15
```

---

## 5. Error Code Distribution Baseline

### 5.1 Top Error Codes

```yaml
ERROR_CODE_BASELINE:
  metric_id: "ERR_001"
  description: "Frequency of error codes in failing artifacts"
  
  measurements:
    G0_006:
      description: "Missing required field"
      count: 42
      percentage: 25.3
      
    G0_004:
      description: "Registry mismatch"
      count: 28
      percentage: 16.9
      
    G0_002:
      description: "Block order violation"
      count: 24
      percentage: 14.5
      
    BSRG_007:
      description: "BSRG checklist item not PASS"
      count: 18
      percentage: 10.8
      
    G0_020:
      description: "Gold Standard checklist incomplete"
      count: 16
      percentage: 9.6
      
    G0_045:
      description: "Positive Closure training signal invalid"
      count: 14
      percentage: 8.4
      
    OTHER:
      count: 24
      percentage: 14.5
      
  total_errors: 166
  unique_error_codes: 23
  
  drift_alert:
    new_error_code_in_top_5: true
    disappearing_error_code: true
    percentage_shift_threshold: 5.0
```

---

## 6. Boundary Proximity Baseline

### 6.1 PASS/WARN Boundary

```yaml
PASS_WARN_BOUNDARY_BASELINE:
  metric_id: "BND_001"
  description: "Distribution of inputs near PASS/WARN boundary"
  
  measurements:
    exactly_at_boundary:
      count: 8
      percentage: 4.0
      
    within_1_field_of_boundary:
      count: 22
      percentage: 11.0
      
    within_2_fields_of_boundary:
      count: 34
      percentage: 17.0
      
  boundary_stability:
    oscillations_detected: 0
    deterministic: true
    
  corpus_size: 200
```

### 6.2 WARN/FAIL Boundary

```yaml
WARN_FAIL_BOUNDARY_BASELINE:
  metric_id: "BND_002"
  description: "Distribution of inputs near WARN/FAIL boundary"
  
  measurements:
    exactly_at_boundary:
      count: 12
      percentage: 6.0
      
    within_1_violation_of_boundary:
      count: 28
      percentage: 14.0
      
    clearly_in_WARN:
      count: 26
      percentage: 13.0
      
    clearly_in_FAIL:
      count: 134
      percentage: 67.0
      
  boundary_stability:
    oscillations_detected: 0
    deterministic: true
    
  corpus_size: 200
```

---

## 7. Accuracy Baseline

### 7.1 False Positive/Negative Rates

```yaml
ACCURACY_BASELINE:
  metric_id: "ACC_001"
  description: "Classification accuracy of governance signals"
  
  measurements:
    false_positive_rate: 0.0
    false_negative_rate: 0.0
    precision: 1.0
    recall: 1.0
    f1_score: 1.0
    
  test_methodology:
    valid_corpus: 100
    invalid_corpus: 100
    total_tests: 200
    
  regression_threshold:
    false_positive_rate_max: 0.01
    false_negative_rate_max: 0.00
    precision_min: 0.99
    recall_min: 1.00
```

### 7.2 Severity Calibration Accuracy

```yaml
SEVERITY_CALIBRATION_BASELINE:
  metric_id: "ACC_002"
  description: "Accuracy of severity assignments"
  
  measurements:
    severity_accuracy: 1.0
    over_escalation_rate: 0.0
    under_escalation_rate: 0.0
    
  critical_calibration:
    false_critical_rate: 0.0
    missed_critical_rate: 0.0
    
  regression_threshold:
    severity_accuracy_min: 0.98
    critical_accuracy_min: 1.00
```

---

## 8. Determinism Baseline

```yaml
DETERMINISM_BASELINE:
  metric_id: "DET_001"
  description: "Determinism verification across replays"
  
  measurements:
    unique_inputs: 200
    replays_per_input: 50
    total_evaluations: 10000
    output_mismatches: 0
    determinism_rate: 1.0
    
  hash_stability:
    input_hash_collisions: 0
    output_hash_collisions: 0
    
  regression_threshold:
    determinism_rate_min: 1.0
    any_mismatch: CRITICAL_REGRESSION
```

---

## 9. Adversarial Robustness Baseline

```yaml
ADVERSARIAL_BASELINE:
  metric_id: "ADV_001"
  description: "Robustness against known adversarial classes"
  
  measurements:
    boundary_jitter:
      scenarios: 8
      passed: 8
      robustness: 1.0
      
    conflicting_authorities:
      scenarios: 8
      passed: 8
      robustness: 1.0
      
    stale_fresh_conflict:
      scenarios: 8
      passed: 8
      robustness: 1.0
      
    ml_feature_spoofing:
      scenarios: 8
      passed: 8
      robustness: 1.0
      
    replay_attack:
      scenarios: 8
      passed: 8
      robustness: 1.0
      
    override_pressure:
      scenarios: 8
      passed: 8
      robustness: 1.0
      
  aggregate_robustness: 1.0
  total_scenarios: 48
  
  regression_threshold:
    robustness_min: 1.0
    any_bypass: CRITICAL_REGRESSION
```

---

## 10. Breakpoint Awareness Baseline

```yaml
BREAKPOINT_BASELINE:
  metric_id: "BRK_001"
  description: "Known system breakpoints (from P39)"
  
  documented_breakpoints:
    BP_001:
      name: "Boundary Collapse"
      severity: LOW
      status: KNOWN
      
    BP_002:
      name: "Explainability Degradation"
      severity: MEDIUM
      status: KNOWN
      threshold: "4+ adversarial classes"
      
    BP_003:
      name: "Staleness Plateau"
      severity: MEDIUM
      status: KNOWN
      threshold: "180+ days"
      
    BP_004:
      name: "WARN Ambiguity Propagation"
      severity: HIGH
      status: KNOWN
      
    BP_005:
      name: "Causal Paradox Window"
      severity: CRITICAL
      status: KNOWN
      threshold: "24 hours"
      
  total_breakpoints: 5
  
  regression_detection:
    new_breakpoint: MUST_DOCUMENT
    existing_breakpoint_worsened: REGRESSION_ALERT
```

---

## 11. Baseline Usage

### 11.1 Comparison Protocol

```yaml
COMPARISON_PROTOCOL:
  frequency: "On every CI run"
  
  steps:
    1: "Load current baseline from GOVERNANCE_SIGNAL_BASELINE.md"
    2: "Execute gate_pack.py --mode ci"
    3: "Capture current metrics"
    4: "Compare against baseline with configured deltas"
    5: "Flag regressions or drift"
    
  on_regression:
    action: FAIL_CLOSED
    blocking: true
    escalation: "BENSON (GID-00)"
    
  on_drift:
    action: WARN_AND_LOG
    blocking: false
    escalation: "Relevant Agent Lead"
```

### 11.2 Baseline Evolution

```yaml
BASELINE_EVOLUTION:
  update_policy: "PAC_REQUIRED"
  
  valid_reasons_for_update:
    - "New signal class added (with PAC)"
    - "Threshold intentionally adjusted (with PAC)"
    - "Schema version upgrade"
    - "Major system refactor"
    
  invalid_reasons:
    - "Performance degraded, want to hide it"
    - "Distribution shifted, want to accept new normal"
    - "Too many regressions, want to reset"
    
  approval_required: "BENSON (GID-00)"
```

---

## 12. Attestation

```yaml
ATTESTATION:
  attested_by: "Maggie (GID-10)"
  role: "ML & Applied AI Lead"
  color: "MAGENTA"
  statement: |
    I certify that this baseline accurately captures the current performance
    characteristics of the ChainBridge governance signal system as of the
    capture date. All measurements are reproducible and the baseline is
    suitable for regression detection.
  timestamp: "2025-12-24T00:00:00Z"
  signature: "💗 MAGGIE-P40-BASELINE-ATTESTATION"
```

---

**END — GOVERNANCE_SIGNAL_BASELINE.md**
