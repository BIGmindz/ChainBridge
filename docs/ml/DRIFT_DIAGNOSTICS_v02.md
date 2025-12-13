# ML Drift Diagnostics Report v0.2

> **Legend**:
> 🩷 **MAGGIE** (GID-10) — Chief AI Architect
> 🟢 **ALEX** (GID-08) — Governance & Alignment
> 🔵 **ATLAS** — Infrastructure & Security

**Generated:** 2025-12-11T00:00:00Z
**Agent:** 🩷 Maggie (GID-10)
**PAC:** MAGGIE-NEXT-A02
**Model Version:** ChainIQ Shadow Mode v1.1

---

## Executive Summary

This report provides comprehensive drift analysis for 🟢 ALEX governance and 🔵 ATLAS infrastructure scaling, including:
- Feature attribution for model disagreement
- Monotonicity constraint validation
- Corridor-specific drift patterns
- Risk adjustment recommendations

This document defines the **v0.2 schema** for drift diagnostics and serves as both specification and template for automated report generation.

---

## 1. Overall Drift Statistics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| Average Delta | Mean absolute difference between dummy and real model scores | Warning: >0.15 |
| P95 Delta | 95th percentile delta - captures tail behavior | Critical: >0.25 |
| Max Delta | Maximum observed delta | Info only |
| Event Count | Number of shadow events analyzed | Min: 50 for valid stats |
| Drift Flag | Boolean indicator when P95 exceeds threshold | Auto-computed |

### Risk Adjustment Integration

The drift-aware risk multiplier adjusts model outputs based on detected drift:

```python
# Multiplier computation
base_multiplier = 1.0
drift_adjustment = min(p95_delta * 1.5, 0.5)  # Capped at +0.5
corridor_adjustment = corridor_drift * 0.5 if corridor_drift_flag else 0.0
final_multiplier = base + drift_adjustment + corridor_adjustment
```

**Risk Tiers:**
- NORMAL: multiplier < 1.1
- ELEVATED: 1.1 ≤ multiplier < 1.25
- HIGH: 1.25 ≤ multiplier < 1.5
- CRITICAL: multiplier ≥ 1.5

---

## 2. Feature Attribution Analysis

### 2.1 SHAP Baseline Method

The attribution engine uses a coefficient-based linear approximation for SHAP values:

1. **Baseline Computation**: Mean values from reference dataset (last 30 days)
2. **Attribution Formula**:
   ```
   shap_value(feature_i) = sign(monotone_direction) * (value - baseline) * scale_factor
   ```
3. **Contribution %**: Normalized by total absolute SHAP contribution

### 2.2 Drift-Weighted Importance

Combines base model importance with drift magnitude:

```python
drift_weighted_importance = (
    (1 - drift_weight) * base_importance +
    drift_weight * drift_magnitude * base_importance
)
```

Where:
- `drift_weight`: 0.5 (default)
- `drift_magnitude`: Normalized mean/std drift from reference period
- `base_importance`: Model coefficient magnitude or SHAP mean absolute value

### 2.3 Attribution Output Schema

| Field | Type | Description |
|-------|------|-------------|
| feature_name | string | Feature identifier |
| base_importance | float | Model-derived importance |
| drift_magnitude | float | Normalized drift (0-1+) |
| drift_direction | enum | positive/negative/stable |
| drift_severity | enum | negligible/minor/moderate/significant/severe/critical |
| drift_weighted_importance | float | Combined score |
| rank | int | 1-indexed importance rank |

---

## 3. Monotonicity Validation (v2)

### 3.1 Rule Sets by Feature Type

#### Distance Features
- **Direction**: Increasing (longer distance → higher risk)
- **Tolerance**: 5% violation allowed
- **Features**: max_route_deviation_km, total_route_distance_km

#### Time Features
- **Direction**: Increasing (longer duration → higher risk)
- **Tolerance**: 10% violation allowed
- **Features**: planned_transit_hours, actual_transit_hours, eta_deviation_hours, total_dwell_hours

#### Probability Features
- **Direction**: Per specification (some increase, some decrease risk)
- **Tolerance**: 5% violation allowed
- **Bounds**: Must be in [0, 1] or [0, 100] if percentage
- **Features**: shipper_on_time_pct_90d, carrier_on_time_pct_90d, lane_sentiment_score

#### Count Features
- **Direction**: Increasing (more events → higher risk)
- **Tolerance**: 0% (must be strictly monotonic)
- **Features**: num_route_deviations, handoff_count, missing_required_docs

### 3.2 Validation Method

Uses Spearman correlation to assess monotonicity:

```python
spearman_corr, p_value = spearmanr(feature_values, predictions)

if expected_direction == "increasing" and spearman_corr < -tolerance:
    violation = True
elif expected_direction == "decreasing" and spearman_corr > tolerance:
    violation = True
```

### 3.3 Violation Output Schema

| Field | Type | Description |
|-------|------|-------------|
| feature_name | string | Violating feature |
| feature_type | string | distance/time/probability/count |
| expected_direction | string | increasing/decreasing |
| actual_direction | string | observed correlation direction |
| violation_score | float | Severity 0-1 |
| sample_count | int | Data points analyzed |
| recommendation | string | Actionable fix guidance |

---

## 4. Corridor-Specific Analysis

### 4.1 Corridor Attribution

Each corridor receives individual drift analysis:

| Field | Type | Description |
|-------|------|-------------|
| corridor | string | Corridor identifier (e.g., "US-CN") |
| event_count | int | Shadow events in time window |
| avg_delta | float | Mean delta for corridor |
| p95_delta | float | P95 delta for corridor |
| drift_flag | bool | True if p95_delta > 0.25 |
| top_drift_features | array | Top 5 drift-contributing features |

### 4.2 Cross-Corridor Comparison

Useful for identifying regional model performance differences:

```python
compare_corridors(session, "US-CN", "US-MX", hours=24)
# Returns: p95_delta_difference, relative_drift_difference
```

---

## 5. Integration with Cody's v1.1 Drift Engine

### 5.1 Connection Points

The drift diagnostics module integrates with existing infrastructure:

1. **corridor_analysis.py**: Uses `identify_drift_corridors()` for corridor flagging
2. **feature_forensics.py**: Leverages `FEATURE_SPECS` and `compute_feature_statistics()`
3. **monotone_gam.py**: Aligns with monotonicity definitions

### 5.2 API Usage

```python
from app.ml.drift_diagnostics import run_drift_diagnostics

# Run full diagnostics pipeline
report, summary = run_drift_diagnostics(
    shadow_events=shadow_events,
    reference_data=reference_data,
    model_predictions=predictions,
    feature_matrix=X,
    feature_names=feature_names,
    save_report=True,
)

# Access summary
print(f"Risk Tier: {summary['risk_tier']}")
print(f"Drifting Corridors: {summary['drifting_corridors']}")
```

---

## 6. Severity Thresholds

| Severity | Drift Magnitude | Action |
|----------|-----------------|--------|
| NEGLIGIBLE | ≤5% | Continue normal monitoring |
| MINOR | 5-10% | Log for awareness |
| MODERATE | 10-20% | Schedule review |
| SIGNIFICANT | 20-35% | Prioritize investigation |
| SEVERE | 35-50% | Immediate attention required |
| CRITICAL | >50% | 🟢 ALEX halts automated decisions |

---

## 7. Recommendations Template

Based on analysis, the report generator produces actionable recommendations:

1. **Drift-based**: Based on P95 delta severity
2. **Feature-based**: Based on high-drift individual features
3. **Monotonicity-based**: Based on constraint violations
4. **Corridor-based**: Based on regional drift patterns

---

## Appendix A: Configuration

### Default Parameters

```python
SHAP_BASELINE_CONFIG = {
    "background_samples": 100,
    "max_samples_for_explanation": 1000,
    "top_features": 10,
}

DRIFT_SEVERITY_THRESHOLDS = {
    "negligible": 0.05,
    "minor": 0.10,
    "moderate": 0.20,
    "significant": 0.35,
    "severe": 0.50,
    "critical": 1.0,
}

RISK_MULTIPLIER_CONFIG = {
    "base_multiplier": 1.0,
    "max_drift_adjustment": 0.5,
    "max_corridor_adjustment": 0.3,
    "drift_threshold_for_adjustment": 0.15,
}
```

---

## Appendix B: File Locations

| Component | Path |
|-----------|------|
| Drift Diagnostics Module | `chainiq-service/app/ml/drift_diagnostics.py` |
| Feature Forensics | `chainiq-service/app/ml/feature_forensics.py` |
| Monotone GAM | `chainiq-service/app/ml/monotone_gam.py` |
| Corridor Analysis | `chainiq-service/app/analysis/corridor_analysis.py` |
| This Specification | `docs/ml/DRIFT_DIAGNOSTICS_v02.md` |

---

## Appendix C: Changelog

### v0.2.0 (2025-12-11)
- Added SHAP-based feature attribution
- Added drift-weighted importance scoring
- Added corridor-specific attribution
- Added Monotonicity Validator v2 with type-specific rules
- Added drift-aware risk multiplier integration
- Integration with Cody's v1.1 drift engine

### v0.1.0 (Prior)
- Basic drift monitoring (AT02_DRIFT_MONITORING.md)

---

🩷 **MAGGIE** — Chief AI Architect
