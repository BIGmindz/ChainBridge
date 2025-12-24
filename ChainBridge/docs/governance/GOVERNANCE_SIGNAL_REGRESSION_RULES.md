# Governance Signal Regression Rules

> **PAC Reference:** PAC-MAGGIE-P40-GOVERNANCE-SIGNAL-PERFORMANCE-REGRESSION-AND-DRIFT-DETECTION-01  
> **Author:** Maggie (GID-10) | 💗 MAGENTA  
> **Authority:** BENSON (GID-00)  
> **Date:** 2025-12-24  
> **Status:** ENFORCED

---

## 1. Overview

This document defines the **regression detection rules** for the ChainBridge governance signal system. Regression is any measurable degradation from the established baseline that exceeds acceptable tolerances.

**Core Principle:** `REGRESSION_IS_A_BUG` — If performance degrades silently, governance has already failed.

---

## 2. Regression Classification

### 2.1 Regression Severity Levels

```yaml
REGRESSION_SEVERITY:
  MINOR:
    description: "Metric exceeds acceptable delta but below regression threshold"
    blocking: false
    action: LOG_AND_MONITOR
    escalation: NONE
    
  MODERATE:
    description: "Metric exceeds regression threshold"
    blocking: true
    action: FAIL_CLOSED
    escalation: AGENT_LEAD
    
  CRITICAL:
    description: "Metric indicates fundamental system degradation"
    blocking: true
    action: EMERGENCY_HALT
    escalation: BENSON
    
  CATASTROPHIC:
    description: "Core invariant violated (determinism, accuracy)"
    blocking: true
    action: SYSTEM_LOCKDOWN
    escalation: EXECUTIVE
```

### 2.2 Regression Categories

```yaml
REGRESSION_CATEGORIES:
  LATENCY_REGRESSION:
    id: "REG_LAT"
    affects: ["validation_time", "ci_pipeline_time"]
    detection: AUTOMATED
    
  DISTRIBUTION_REGRESSION:
    id: "REG_DIST"
    affects: ["status_distribution", "severity_distribution", "error_codes"]
    detection: STATISTICAL
    
  ACCURACY_REGRESSION:
    id: "REG_ACC"
    affects: ["false_positive_rate", "false_negative_rate", "severity_accuracy"]
    detection: AUTOMATED
    
  DETERMINISM_REGRESSION:
    id: "REG_DET"
    affects: ["replay_consistency", "hash_stability"]
    detection: AUTOMATED
    
  ROBUSTNESS_REGRESSION:
    id: "REG_ROB"
    affects: ["adversarial_resistance", "boundary_stability"]
    detection: ADVERSARIAL_TESTING
```

---

## 3. Latency Regression Rules

### 3.1 Validation Latency Rules

```yaml
VALIDATION_LATENCY_RULES:
  rule_id: "RUL_LAT_001"
  metric: "LAT_001"
  
  thresholds:
    p50:
      baseline_ms: 23
      acceptable_delta_ms: 10
      regression_threshold_ms: 20
      formula: "current_p50 - baseline_p50"
      
    p95:
      baseline_ms: 62
      acceptable_delta_ms: 25
      regression_threshold_ms: 50
      formula: "current_p95 - baseline_p95"
      
    p99:
      baseline_ms: 94
      acceptable_delta_ms: 50
      regression_threshold_ms: 100
      formula: "current_p99 - baseline_p99"
      
  evaluation:
    if: "delta <= acceptable_delta"
    then: PASS
    
    if: "acceptable_delta < delta <= regression_threshold"
    then: MINOR_REGRESSION
    
    if: "delta > regression_threshold"
    then: MODERATE_REGRESSION
    
  blocking: true
  
  machine_readable_rule: |
    def check_latency_regression(current, baseline):
        for percentile in ['p50', 'p95', 'p99']:
            delta = current[percentile] - baseline[percentile]
            acceptable = baseline.acceptable_delta[percentile]
            threshold = baseline.regression_threshold[percentile]
            
            if delta > threshold:
                return RegressionResult(
                    severity=MODERATE,
                    metric=f"LAT_001.{percentile}",
                    delta=delta,
                    threshold=threshold
                )
        return RegressionResult(severity=NONE)
```

### 3.2 CI Pipeline Latency Rules

```yaml
CI_LATENCY_RULES:
  rule_id: "RUL_LAT_002"
  metric: "LAT_002"
  
  thresholds:
    total_time:
      baseline_ms: 4823
      acceptable_delta_percent: 15
      regression_threshold_percent: 30
      
    per_artifact:
      baseline_ms: 72
      acceptable_delta_ms: 20
      regression_threshold_ms: 40
      
  evaluation:
    total_regression_if: "current_total > baseline_total * 1.30"
    per_artifact_regression_if: "current_per > baseline_per + 40"
    
  blocking: true
```

---

## 4. Distribution Regression Rules

### 4.1 Status Distribution Rules

```yaml
STATUS_DISTRIBUTION_RULES:
  rule_id: "RUL_DIST_001"
  metric: "DIST_001"
  
  method: "chi_square_test"
  
  thresholds:
    acceptable_shift: 5.0  # percentage points
    regression_threshold: 10.0  # percentage points
    statistical_significance: 0.05
    
  per_status_rules:
    PASS:
      baseline_percent: 46.0
      min_acceptable: 40.0
      max_acceptable: 55.0
      
    WARN:
      baseline_percent: 19.0
      min_acceptable: 10.0
      max_acceptable: 25.0
      
    FAIL:
      baseline_percent: 33.0
      min_acceptable: 25.0
      max_acceptable: 40.0
      
    SKIP:
      baseline_percent: 2.0
      min_acceptable: 0.0
      max_acceptable: 5.0
      
  evaluation:
    if: "any_status_outside_range"
    then: MODERATE_REGRESSION
    
    if: "chi_square_p_value < 0.01"
    then: DISTRIBUTION_DRIFT_DETECTED
    
  machine_readable_rule: |
    def check_status_distribution_regression(current, baseline):
        for status in ['PASS', 'WARN', 'FAIL', 'SKIP']:
            current_pct = current.status_distribution[status]
            min_bound = baseline.per_status_rules[status].min_acceptable
            max_bound = baseline.per_status_rules[status].max_acceptable
            
            if current_pct < min_bound or current_pct > max_bound:
                return RegressionResult(
                    severity=MODERATE,
                    metric="DIST_001",
                    status=status,
                    current=current_pct,
                    bounds=(min_bound, max_bound)
                )
        return RegressionResult(severity=NONE)
```

### 4.2 Severity Distribution Rules

```yaml
SEVERITY_DISTRIBUTION_RULES:
  rule_id: "RUL_DIST_002"
  metric: "DIST_002"
  
  method: "kolmogorov_smirnov"
  
  thresholds:
    ks_statistic_warn: 0.10
    ks_statistic_fail: 0.15
    
  monotonicity_check:
    rule: "severity_ordering_must_hold"
    order: [NONE, LOW, MEDIUM, HIGH, CRITICAL]
    violation_severity: CRITICAL
    
  per_severity_bounds:
    NONE:
      baseline: 46.0
      min: 40.0
      max: 55.0
      
    LOW:
      baseline: 8.0
      min: 5.0
      max: 15.0
      
    MEDIUM:
      baseline: 12.0
      min: 8.0
      max: 20.0
      
    HIGH:
      baseline: 30.0
      min: 20.0
      max: 40.0
      
    CRITICAL:
      baseline: 4.0
      min: 1.0
      max: 8.0
      
  critical_escalation_rule:
    if: "CRITICAL_percentage > 8.0"
    then: CRITICAL_REGRESSION
    reason: "Excessive CRITICAL signals indicate system degradation"
```

---

## 5. Accuracy Regression Rules

### 5.1 False Positive/Negative Rules

```yaml
ACCURACY_REGRESSION_RULES:
  rule_id: "RUL_ACC_001"
  metric: "ACC_001"
  
  thresholds:
    false_positive_rate:
      baseline: 0.0
      acceptable: 0.01
      critical: 0.05
      
    false_negative_rate:
      baseline: 0.0
      acceptable: 0.00  # ZERO TOLERANCE
      critical: 0.01
      
    precision:
      baseline: 1.0
      acceptable_min: 0.99
      critical_min: 0.95
      
    recall:
      baseline: 1.0
      acceptable_min: 1.00  # ZERO TOLERANCE on recall
      critical_min: 0.99
      
  evaluation:
    false_negative_any: CRITICAL_REGRESSION
    false_positive_above_acceptable: MODERATE_REGRESSION
    precision_below_critical: CRITICAL_REGRESSION
    recall_below_acceptable: CRITICAL_REGRESSION
    
  blocking: true
  zero_tolerance_on_false_negative: true
  
  machine_readable_rule: |
    def check_accuracy_regression(current, baseline):
        # ZERO TOLERANCE on false negatives
        if current.false_negative_rate > 0:
            return RegressionResult(
                severity=CRITICAL,
                metric="ACC_001.false_negative_rate",
                value=current.false_negative_rate,
                threshold=0.0,
                message="FALSE NEGATIVE DETECTED - CRITICAL REGRESSION"
            )
        
        # Check false positives
        if current.false_positive_rate > baseline.thresholds.false_positive_rate.acceptable:
            return RegressionResult(
                severity=MODERATE,
                metric="ACC_001.false_positive_rate",
                value=current.false_positive_rate,
                threshold=baseline.thresholds.false_positive_rate.acceptable
            )
        
        return RegressionResult(severity=NONE)
```

### 5.2 Severity Calibration Rules

```yaml
SEVERITY_CALIBRATION_RULES:
  rule_id: "RUL_ACC_002"
  metric: "ACC_002"
  
  thresholds:
    severity_accuracy:
      baseline: 1.0
      acceptable_min: 0.98
      critical_min: 0.95
      
    over_escalation_rate:
      baseline: 0.0
      acceptable_max: 0.02
      
    under_escalation_rate:
      baseline: 0.0
      acceptable_max: 0.01
      
  critical_calibration:
    missed_critical: CATASTROPHIC_REGRESSION
    false_critical: MODERATE_REGRESSION
    
  evaluation:
    severity_accuracy_below_critical: CRITICAL_REGRESSION
    under_escalation_above_acceptable: MODERATE_REGRESSION
    any_missed_critical: CATASTROPHIC_REGRESSION
```

---

## 6. Determinism Regression Rules

### 6.1 Replay Consistency Rules

```yaml
DETERMINISM_RULES:
  rule_id: "RUL_DET_001"
  metric: "DET_001"
  
  requirements:
    determinism_rate: 1.0  # Must be exactly 1.0
    any_mismatch: CATASTROPHIC_REGRESSION
    
  evaluation:
    if: "determinism_rate < 1.0"
    then: CATASTROPHIC_REGRESSION
    action: SYSTEM_LOCKDOWN
    reason: "Non-deterministic governance violates core invariant"
    
  testing_protocol:
    replays_per_input: 50
    minimum_unique_inputs: 100
    
  machine_readable_rule: |
    def check_determinism_regression(current, baseline):
        if current.determinism_rate < 1.0:
            return RegressionResult(
                severity=CATASTROPHIC,
                metric="DET_001",
                value=current.determinism_rate,
                threshold=1.0,
                message="NON-DETERMINISTIC BEHAVIOR DETECTED - CATASTROPHIC"
            )
        return RegressionResult(severity=NONE)
```

---

## 7. Robustness Regression Rules

### 7.1 Adversarial Resistance Rules

```yaml
ROBUSTNESS_RULES:
  rule_id: "RUL_ROB_001"
  metric: "ADV_001"
  
  per_class_requirements:
    boundary_jitter:
      required_robustness: 1.0
      any_bypass: CRITICAL_REGRESSION
      
    conflicting_authorities:
      required_robustness: 1.0
      any_bypass: CRITICAL_REGRESSION
      
    stale_fresh_conflict:
      required_robustness: 1.0
      any_bypass: MODERATE_REGRESSION
      
    ml_feature_spoofing:
      required_robustness: 1.0
      any_bypass: CRITICAL_REGRESSION
      
    replay_attack:
      required_robustness: 1.0
      any_bypass: CRITICAL_REGRESSION
      
    override_pressure:
      required_robustness: 1.0
      any_bypass: CRITICAL_REGRESSION
      
  aggregate_requirements:
    total_robustness: 1.0
    any_class_compromised: CRITICAL_REGRESSION
    
  evaluation:
    any_adversarial_bypass: CRITICAL_REGRESSION
    new_adversarial_class_fails: MUST_DOCUMENT_AND_FIX
```

---

## 8. Boundary Stability Rules

### 8.1 PASS/WARN Boundary Rules

```yaml
BOUNDARY_STABILITY_RULES:
  rule_id: "RUL_BND_001"
  metric: "BND_001"
  
  stability_requirements:
    oscillation_tolerance: 0
    
  evaluation:
    if: "oscillations_detected > 0"
    then: CRITICAL_REGRESSION
    reason: "Boundary oscillation indicates non-deterministic behavior"
    
  monitoring:
    boundary_tests_per_ci: 100
    required_stability_rate: 1.0
```

---

## 9. Error Code Regression Rules

```yaml
ERROR_CODE_RULES:
  rule_id: "RUL_ERR_001"
  metric: "ERR_001"
  
  monitoring:
    new_error_code_in_top_5:
      action: INVESTIGATE
      severity: MINOR
      
    existing_error_code_disappeared:
      action: VERIFY_NOT_MASKED
      severity: MODERATE if masked
      
    error_code_percentage_shift:
      threshold: 5.0  # percentage points
      action: DRIFT_ALERT if exceeded
      
  machine_readable_rule: |
    def check_error_code_regression(current, baseline):
        # Check for new error codes in top 5
        current_top_5 = set(current.error_codes.top_5())
        baseline_top_5 = set(baseline.error_codes.top_5())
        
        new_in_top_5 = current_top_5 - baseline_top_5
        if new_in_top_5:
            return RegressionResult(
                severity=MINOR,
                metric="ERR_001",
                message=f"New error codes in top 5: {new_in_top_5}"
            )
        
        return RegressionResult(severity=NONE)
```

---

## 10. Regression Response Protocol

### 10.1 Response Matrix

```yaml
RESPONSE_MATRIX:
  MINOR_REGRESSION:
    blocking: false
    actions:
      - "Log to regression audit"
      - "Add to monitoring dashboard"
      - "Review in next retrospective"
    escalation: NONE
    
  MODERATE_REGRESSION:
    blocking: true
    actions:
      - "Fail CI pipeline"
      - "Create regression ticket"
      - "Notify agent lead"
      - "Block merge until fixed"
    escalation: AGENT_LEAD
    
  CRITICAL_REGRESSION:
    blocking: true
    actions:
      - "Fail CI pipeline immediately"
      - "Page on-call"
      - "Block all deployments"
      - "Escalate to BENSON"
    escalation: BENSON
    
  CATASTROPHIC_REGRESSION:
    blocking: true
    actions:
      - "System lockdown"
      - "All deployments halted"
      - "Emergency review"
      - "Executive notification"
    escalation: EXECUTIVE
```

### 10.2 Regression Fix Protocol

```yaml
FIX_PROTOCOL:
  steps:
    1: "Identify regression source via git bisect"
    2: "Create regression test that reproduces issue"
    3: "Implement fix"
    4: "Verify fix against baseline"
    5: "Document in GOVERNANCE_SIGNAL_DRIFT_REPORT.md if applicable"
    6: "Create PAC if systemic change needed"
    
  prohibited_fixes:
    - "Adjust baseline to accept degradation"
    - "Increase thresholds to hide regression"
    - "Disable regression check"
    
  acceptable_resolutions:
    - "Fix root cause"
    - "Revert offending change"
    - "Create PAC for intentional threshold change (with justification)"
```

---

## 11. Execution Rules

### 11.1 CI Integration

```yaml
CI_INTEGRATION:
  trigger: "On every push to main/protected branches"
  
  checks:
    - rule: "RUL_LAT_001"
      weight: 1
      
    - rule: "RUL_LAT_002"
      weight: 1
      
    - rule: "RUL_DIST_001"
      weight: 2
      
    - rule: "RUL_ACC_001"
      weight: 3
      
    - rule: "RUL_DET_001"
      weight: 5
      
    - rule: "RUL_ROB_001"
      weight: 4
      
  fail_condition: "Any rule returns MODERATE or higher"
  
  output_format: |
    REGRESSION_CHECK_RESULT:
      status: PASS | FAIL
      rules_checked: N
      regressions_found: N
      highest_severity: NONE | MINOR | MODERATE | CRITICAL | CATASTROPHIC
      details: [...]
```

---

## 12. Attestation

```yaml
ATTESTATION:
  attested_by: "Maggie (GID-10)"
  role: "ML & Applied AI Lead"
  color: "MAGENTA"
  statement: |
    I certify that these regression detection rules are correctly configured
    to detect performance degradation in the governance signal system. The
    rules are machine-readable, enforceable via CI, and aligned with the
    principle that regression must block the build.
  timestamp: "2025-12-24T00:00:00Z"
  signature: "💗 MAGGIE-P40-REGRESSION-ATTESTATION"
```

---

**END — GOVERNANCE_SIGNAL_REGRESSION_RULES.md**
