# Trust Risk Feature Specification

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-TRUST-01
> **Status**: SPEC (Design Only — No Training, No Code)
> **Created**: 2025-12-17

---

## 1. BLUF

This document specifies **exact formulas** for every feature in the Trust Risk Index. No hidden transforms. No black boxes. Every feature is:

- **Explicit**: Formula documented with all parameters
- **Time-aware**: Window and decay specified
- **Fail-defined**: Behavior on missing data documented
- **Interpretable**: Human-readable meaning stated

---

## 2. Feature Naming Convention

```
{domain}_{signal_id}_{window}

Examples:
- gi_denial_rate_24h
- od_drcp_rate_7d
- sd_drift_count_30d
```

---

## 3. Domain 1: Governance Integrity Features

### GI-01: Denial Rate

| Property | Value |
|----------|-------|
| **Feature Name** | `gi_denial_rate_{window}` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
gi_denial_rate(window) =
    count(DECISION_DENIED, window) /
    (count(DECISION_DENIED, window) + count(DECISION_ALLOWED, window))
```

**Time Windows**:
- `gi_denial_rate_24h` — Last 24 hours
- `gi_denial_rate_7d` — Last 7 days
- `gi_denial_rate_30d` — Last 30 days

**Decay Function**: None (simple count in window)

**Failure Mode**:
```
IF (count(DECISION_DENIED) + count(DECISION_ALLOWED)) == 0:
    RETURN null  # No signal, not "low risk"
```

**Interpretation**:
- 0.00 = All decisions allowed (within bounds)
- 0.05 = 5% denial rate (normal operational friction)
- 0.20 = 20% denial rate (elevated, investigate)
- 0.50+ = Majority denied (severe issue)

---

### GI-02: Scope Violation Count

| Property | Value |
|----------|-------|
| **Feature Name** | `gi_scope_violations_{window}` |
| **Unit** | Count (integer ≥ 0) |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
gi_scope_violations(window) = count(SCOPE_VIOLATION, window)
```

**Time Windows**:
- `gi_scope_violations_24h`
- `gi_scope_violations_7d`
- `gi_scope_violations_30d`

**Decay Function**: Exponential decay for older violations
```
effective_count = Σ (1 × e^(-λ × age_hours))

Where:
    λ = ln(2) / half_life_hours
    half_life_hours = 168 (7 days)
```

**Failure Mode**:
```
IF no events in window:
    RETURN 0  # Zero violations is valid baseline
```

**Interpretation**:
- 0 = Clean (expected state)
- 1+ = Violations detected (any non-zero is concerning)

---

### GI-03: Forbidden Verb Attempt Rate

| Property | Value |
|----------|-------|
| **Feature Name** | `gi_forbidden_verb_rate_{window}` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
gi_forbidden_verb_rate(window) =
    count(DECISION_DENIED WHERE reason_code IN forbidden_reasons, window) /
    count(DECISION_DENIED, window)

forbidden_reasons = {
    'EXECUTE_NOT_PERMITTED',
    'BLOCK_NOT_PERMITTED',
    'APPROVE_NOT_PERMITTED',
    'DIGGY_EXECUTE_FORBIDDEN',
    'DIGGY_BLOCK_FORBIDDEN',
    'DIGGY_APPROVE_FORBIDDEN',
    'VERB_NOT_PERMITTED'
}
```

**Time Windows**:
- `gi_forbidden_verb_rate_24h`
- `gi_forbidden_verb_rate_7d`

**Decay Function**: None

**Failure Mode**:
```
IF count(DECISION_DENIED) == 0:
    RETURN null  # No denials, no rate
```

**Interpretation**:
- 0.00 = Denials are for other reasons (scope, target, etc.)
- 0.30 = 30% of denials are forbidden verb attempts
- 1.00 = All denials are forbidden verb attempts (probing)

---

### GI-04: Unknown Agent Attempt Rate

| Property | Value |
|----------|-------|
| **Feature Name** | `gi_unknown_agent_rate_{window}` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
gi_unknown_agent_rate(window) =
    count(DECISION_DENIED WHERE reason_code IN identity_reasons, window) /
    count(total_decisions, window)

identity_reasons = {
    'UNKNOWN_AGENT',
    'MALFORMED_GID'
}
```

**Time Windows**:
- `gi_unknown_agent_rate_24h`
- `gi_unknown_agent_rate_7d`

**Decay Function**: None

**Failure Mode**:
```
IF count(total_decisions) == 0:
    RETURN null
```

**Interpretation**:
- 0.00 = All requests from known agents
- 0.01 = 1% unknown (possible integration issues)
- 0.10+ = 10%+ unknown (security concern)

---

### GI-05: Tool Denial Rate

| Property | Value |
|----------|-------|
| **Feature Name** | `gi_tool_denial_rate_{window}` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
gi_tool_denial_rate(window) =
    count(TOOL_EXECUTION_DENIED, window) /
    (count(TOOL_EXECUTION_DENIED, window) + count(TOOL_EXECUTION_ALLOWED, window))
```

**Time Windows**:
- `gi_tool_denial_rate_24h`
- `gi_tool_denial_rate_7d`

**Decay Function**: None

**Failure Mode**:
```
IF (count(TOOL_*) == 0):
    RETURN null  # No tool activity
```

**Interpretation**:
- 0.00 = All tool executions authorized
- 0.05 = 5% denied (some boundary pressure)
- 0.25+ = 25%+ denied (significant control friction)

---

## 4. Domain 2: Operational Discipline Features

### OD-01: DRCP Escalation Rate

| Property | Value |
|----------|-------|
| **Feature Name** | `od_drcp_rate_{window}` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk (high correction needs) |

**Formula**:
```
od_drcp_rate(window) =
    count(DRCP_TRIGGERED, window) /
    count(DECISION_DENIED, window)
```

**Time Windows**:
- `od_drcp_rate_24h`
- `od_drcp_rate_7d`

**Decay Function**: None

**Failure Mode**:
```
IF count(DECISION_DENIED) == 0:
    RETURN 0.0  # No denials = no DRCP triggering
```

**Interpretation**:
- 0.00 = Denials don't trigger DRCP (simple denials)
- 0.50 = Half of denials route to correction
- 1.00 = All denials trigger correction protocol

---

### OD-02: Diggi Correction Frequency

| Property | Value |
|----------|-------|
| **Feature Name** | `od_diggi_corrections_{window}` |
| **Unit** | Count (integer ≥ 0) |
| **Monotonicity** | Context-dependent |

**Formula**:
```
od_diggi_corrections(window) = count(DIGGI_CORRECTION_ISSUED, window)
```

**Time Windows**:
- `od_diggi_corrections_24h`
- `od_diggi_corrections_7d`

**Decay Function**: None

**Failure Mode**:
```
IF no events:
    RETURN 0
```

**Interpretation**:
- 0 = No corrections issued
- N = N correction plans issued
- Context: Corrections can be positive (system working) or negative (frequent failures)

**Note**: This feature is used as a **context signal**, not directly in risk scoring.

---

### OD-03: Escalation to Human Rate

| Property | Value |
|----------|-------|
| **Feature Name** | `od_human_escalation_rate_{window}` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk (less automation confidence) |

**Formula**:
```
od_human_escalation_rate(window) =
    count(DECISION_ESCALATED, window) /
    count(total_decisions, window)
```

**Time Windows**:
- `od_human_escalation_rate_24h`
- `od_human_escalation_rate_7d`

**Decay Function**: None

**Failure Mode**:
```
IF count(total_decisions) == 0:
    RETURN null
```

**Interpretation**:
- 0.00 = Fully automated
- 0.05 = 5% require human
- 0.20+ = 20%+ require human (high friction)

---

### OD-04: Artifact Verification Failure Rate

| Property | Value |
|----------|-------|
| **Feature Name** | `od_artifact_failure_rate_{window}` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
od_artifact_failure_rate(window) =
    count(ARTIFACT_VERIFICATION_FAILED, window) /
    (count(ARTIFACT_VERIFIED, window) + count(ARTIFACT_VERIFICATION_FAILED, window))
```

**Time Windows**:
- `od_artifact_failure_rate_24h`
- `od_artifact_failure_rate_7d`
- `od_artifact_failure_rate_30d`

**Decay Function**: None

**Failure Mode**:
```
IF count(ARTIFACT_*) == 0:
    RETURN null  # No verification activity
```

**Interpretation**:
- 0.00 = All artifacts verified successfully
- 0.01 = 1% failure (investigate)
- 0.10+ = 10%+ failure (critical issue)

---

### OD-05: Retry-After-Deny Rate

| Property | Value |
|----------|-------|
| **Feature Name** | `od_retry_after_deny_rate_{window}` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
od_retry_after_deny_rate(window) =
    count(DECISION_DENIED WHERE reason_code = 'RETRY_AFTER_DENY_FORBIDDEN', window) /
    count(DECISION_DENIED, window)
```

**Time Windows**:
- `od_retry_after_deny_rate_24h`
- `od_retry_after_deny_rate_7d`

**Decay Function**: None

**Failure Mode**:
```
IF count(DECISION_DENIED) == 0:
    RETURN 0.0  # No denials, no retries possible
```

**Interpretation**:
- 0.00 = Agents respect denials
- 0.05 = 5% retry attempts (misconfigured agents?)
- 0.20+ = 20%+ retrying (protocol violation)

---

## 5. Domain 3: System Drift Features

### SD-01: Governance Drift Detection Count

| Property | Value |
|----------|-------|
| **Feature Name** | `sd_drift_count_{window}` |
| **Unit** | Count (integer ≥ 0) |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
sd_drift_count(window) = count(GOVERNANCE_DRIFT_DETECTED, window)
```

**Time Windows**:
- `sd_drift_count_24h`
- `sd_drift_count_7d`
- `sd_drift_count_30d`

**Decay Function**: Exponential decay
```
effective_count = Σ (1 × e^(-λ × age_hours))
half_life_hours = 72 (3 days)
```

**Failure Mode**:
```
IF no events:
    RETURN 0  # Zero drift is valid baseline
```

**Interpretation**:
- 0 = No drift detected (stable)
- 1+ = Drift events (any is concerning)

---

### SD-02: Boot Failure Rate

| Property | Value |
|----------|-------|
| **Feature Name** | `sd_boot_failure_rate_{window}` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
sd_boot_failure_rate(window) =
    count(GOVERNANCE_BOOT_FAILED, window) /
    (count(GOVERNANCE_BOOT_PASSED, window) + count(GOVERNANCE_BOOT_FAILED, window))
```

**Time Windows**:
- `sd_boot_failure_rate_7d`
- `sd_boot_failure_rate_30d`

**Decay Function**: None

**Failure Mode**:
```
IF count(GOVERNANCE_BOOT_*) == 0:
    RETURN null  # No boot events recorded
```

**Interpretation**:
- 0.00 = All boots successful
- 0.05 = 5% boot failures
- 0.20+ = Frequent boot failures (deployment issues)

---

### SD-03: Fingerprint Change Count

| Property | Value |
|----------|-------|
| **Feature Name** | `sd_fingerprint_changes_{window}` |
| **Unit** | Count (integer ≥ 0) |
| **Monotonicity** | ↑ value → ↑ risk (instability) |

**Formula**:
```
sd_fingerprint_changes(window) =
    count(distinct composite_hash values in window) - 1

Note: Subtract 1 because a stable system has 1 hash value (no changes)
```

**Time Windows**:
- `sd_fingerprint_changes_7d`
- `sd_fingerprint_changes_30d`

**Decay Function**: None

**Failure Mode**:
```
IF no fingerprint records:
    RETURN null
```

**Interpretation**:
- 0 = No changes (stable configuration)
- 1-2 = Few changes (planned updates)
- 5+ = Frequent changes (unstable)

---

### SD-04: Freshness Violation Flag

| Property | Value |
|----------|-------|
| **Feature Name** | `sd_freshness_violation` |
| **Unit** | Boolean (0 or 1) |
| **Monotonicity** | 1 → ↑ risk |

**Formula**:
```
sd_freshness_violation =
    1 IF (now - audit_bundle.generated_at) > freshness_threshold_hours
    0 OTHERWISE

freshness_threshold_hours = 24 (default, configurable)
```

**Time Windows**: N/A (point-in-time check)

**Decay Function**: N/A

**Failure Mode**:
```
IF no audit bundle exists:
    RETURN 1  # Missing bundle = stale by definition
```

**Interpretation**:
- 0 = Audit bundle is fresh
- 1 = Audit bundle is stale (cannot prove current state)

---

### SD-05: Gameday Coverage Gap

| Property | Value |
|----------|-------|
| **Feature Name** | `sd_gameday_coverage_gap` |
| **Unit** | Ratio [0.0, 1.0] |
| **Monotonicity** | ↑ value → ↑ risk |

**Formula**:
```
sd_gameday_coverage_gap =
    1 - (tested_scenarios / defined_scenarios)

Where:
    tested_scenarios = count of passing gameday tests
    defined_scenarios = count of threats in THREAT_COVERAGE.md
```

**Time Windows**: N/A (point-in-time check)

**Decay Function**: N/A

**Failure Mode**:
```
IF defined_scenarios == 0:
    RETURN 1.0  # No threat model = no coverage
```

**Interpretation**:
- 0.00 = All scenarios tested (full coverage)
- 0.10 = 10% gap (some untested scenarios)
- 0.50+ = 50%+ untested (significant blind spots)

**Current State**: 109 scenarios, 6 threat classes → gap ≈ 0.00

---

## 6. Trust Weight Features

### TW-01: Audit Bundle Freshness Weight

| Property | Value |
|----------|-------|
| **Feature Name** | `tw_freshness_weight` |
| **Unit** | Multiplier [1.0, 2.0] |
| **Monotonicity** | Stale → higher multiplier |

**Formula**:
```
tw_freshness_weight =
    1.0 + min(1.0, bundle_age_hours / max_acceptable_age_hours)

Where:
    bundle_age_hours = now - audit_bundle.generated_at
    max_acceptable_age_hours = 168 (7 days)
```

**Interpretation**:
- 1.0 = Fresh bundle (0 hours old)
- 1.5 = ~3.5 day old bundle
- 2.0 = ≥7 day old bundle (maximum penalty)

---

### TW-02: Gameday Coverage Weight

| Property | Value |
|----------|-------|
| **Feature Name** | `tw_gameday_weight` |
| **Unit** | Multiplier [1.0, 2.0] |
| **Monotonicity** | Lower coverage → higher multiplier |

**Formula**:
```
tw_gameday_weight = 1.0 + sd_gameday_coverage_gap
```

**Interpretation**:
- 1.0 = Full coverage (0% gap)
- 1.5 = 50% coverage gap
- 2.0 = 100% coverage gap (no tests)

---

### TW-03: Evidence Binding Weight

| Property | Value |
|----------|-------|
| **Feature Name** | `tw_evidence_weight` |
| **Unit** | Multiplier [1.0, 2.0] |
| **Monotonicity** | Lower success rate → higher multiplier |

**Formula**:
```
tw_evidence_weight =
    1.0 + od_artifact_failure_rate_30d

IF od_artifact_failure_rate_30d is null:
    tw_evidence_weight = 1.5  # Penalty for no verification data
```

**Interpretation**:
- 1.0 = 0% artifact failures
- 1.1 = 10% artifact failures
- 2.0 = 100% artifact failures

---

### TW-04: Observation Density Confidence

| Property | Value |
|----------|-------|
| **Feature Name** | `tw_density_confidence` |
| **Unit** | Multiplier [1.0, 2.0] |
| **Monotonicity** | Sparse data → higher multiplier (less confidence) |

**Formula**:
```
events_per_day = total_events_30d / 30

tw_density_confidence =
    1.0 IF events_per_day >= min_events_per_day
    1.0 + (1.0 - (events_per_day / min_events_per_day)) OTHERWISE

Where:
    min_events_per_day = 100 (configurable)
```

**Interpretation**:
- 1.0 = High event density (confident)
- 1.5 = 50% of expected density
- 2.0 = Very sparse data (low confidence)

---

## 7. Feature Summary Table

| Feature ID | Feature Name | Type | Window | Decay | Risk Direction |
|------------|--------------|------|--------|-------|----------------|
| GI-01 | `gi_denial_rate_{window}` | ratio | 24h/7d/30d | none | ↑ |
| GI-02 | `gi_scope_violations_{window}` | count | 24h/7d/30d | exp | ↑ |
| GI-03 | `gi_forbidden_verb_rate_{window}` | ratio | 24h/7d | none | ↑ |
| GI-04 | `gi_unknown_agent_rate_{window}` | ratio | 24h/7d | none | ↑ |
| GI-05 | `gi_tool_denial_rate_{window}` | ratio | 24h/7d | none | ↑ |
| OD-01 | `od_drcp_rate_{window}` | ratio | 24h/7d | none | ↑ |
| OD-02 | `od_diggi_corrections_{window}` | count | 24h/7d | none | context |
| OD-03 | `od_human_escalation_rate_{window}` | ratio | 24h/7d | none | ↑ |
| OD-04 | `od_artifact_failure_rate_{window}` | ratio | 24h/7d/30d | none | ↑ |
| OD-05 | `od_retry_after_deny_rate_{window}` | ratio | 24h/7d | none | ↑ |
| SD-01 | `sd_drift_count_{window}` | count | 24h/7d/30d | exp | ↑ |
| SD-02 | `sd_boot_failure_rate_{window}` | ratio | 7d/30d | none | ↑ |
| SD-03 | `sd_fingerprint_changes_{window}` | count | 7d/30d | none | ↑ |
| SD-04 | `sd_freshness_violation` | bool | n/a | n/a | 1=↑ |
| SD-05 | `sd_gameday_coverage_gap` | ratio | n/a | n/a | ↑ |
| TW-01 | `tw_freshness_weight` | mult | n/a | n/a | ↑ |
| TW-02 | `tw_gameday_weight` | mult | n/a | n/a | ↑ |
| TW-03 | `tw_evidence_weight` | mult | n/a | n/a | ↑ |
| TW-04 | `tw_density_confidence` | mult | n/a | n/a | ↑ |

---

## 8. Acceptance Criteria

- [x] All formulas explicit with no hidden transforms
- [x] Time windows documented for each feature
- [x] Decay functions specified where applicable
- [x] Failure modes defined for missing data
- [x] Interpretation ranges documented
- [x] All features traceable to source events
- [x] Trust weights apply as multipliers

---

## 9. References

- [TRUST_RISK_TAXONOMY.md](./TRUST_RISK_TAXONOMY.md) — Signal definitions
- [core/governance/events.py](../../core/governance/events.py) — Event types
- [core/governance/acm_evaluator.py](../../core/governance/acm_evaluator.py) — Denial reasons
