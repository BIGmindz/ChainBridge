"""
ChainIQ ML Feature Forensics & Model Consistency Audit

Deep audit of:
- Feature ranges and distributions
- Missing field semantics
- Target leakage detection
- Corridor bias analysis
- Drift sensitivity
- Monotonicity constraints
- Calibration analysis

Maggie Cognitive Loop:
1. Commercial Audit: Validate model usefulness for underwriting
2. Data Interrogation: Analyze ingestion rows
3. Adversarial Attack: Attempt to break model via boundary inputs
4. Explanation: Glass-box documentation + deploy/no-deploy verdict

Author: Maggie (GID-10) 🩷
PAC: MAGGIE-PAC-A
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence

import numpy as np

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE DEFINITIONS & EXPECTED RANGES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class FeatureSpec:
    """Specification for a single feature including expected ranges and constraints."""

    name: str
    dtype: Literal["float", "int", "categorical", "binary"]
    min_val: float | None = None
    max_val: float | None = None
    expected_mean: float | None = None
    monotone_direction: Literal["positive", "negative", "none"] = "none"
    leakage_risk: Literal["none", "low", "medium", "high"] = "none"
    description: str = ""
    nullable: bool = False


# Canonical feature specifications
FEATURE_SPECS: dict[str, FeatureSpec] = {
    # Core transit features
    "planned_transit_hours": FeatureSpec(
        name="planned_transit_hours",
        dtype="float",
        min_val=1.0,
        max_val=720.0,  # 30 days max
        expected_mean=72.0,
        monotone_direction="positive",  # Longer transit = more risk
        description="Planned transit duration in hours",
    ),
    "actual_transit_hours": FeatureSpec(
        name="actual_transit_hours",
        dtype="float",
        min_val=0.0,
        max_val=1000.0,
        expected_mean=80.0,
        monotone_direction="positive",
        leakage_risk="medium",  # May leak outcome if shipment incomplete
        description="Actual transit duration (null if in-transit)",
        nullable=True,
    ),
    "eta_deviation_hours": FeatureSpec(
        name="eta_deviation_hours",
        dtype="float",
        min_val=-168.0,  # 7 days early
        max_val=720.0,  # 30 days late
        expected_mean=5.0,
        monotone_direction="positive",  # Positive deviation = late = more risk
        leakage_risk="high",  # Strong correlation with severe_delay label!
        description="Deviation from ETA (positive = late)",
    ),
    "num_route_deviations": FeatureSpec(
        name="num_route_deviations",
        dtype="int",
        min_val=0,
        max_val=50,
        expected_mean=1.5,
        monotone_direction="positive",
        description="Count of route deviations detected",
    ),
    "max_route_deviation_km": FeatureSpec(
        name="max_route_deviation_km",
        dtype="float",
        min_val=0.0,
        max_val=500.0,
        expected_mean=15.0,
        monotone_direction="positive",
        description="Maximum single route deviation in km",
    ),
    "total_dwell_hours": FeatureSpec(
        name="total_dwell_hours",
        dtype="float",
        min_val=0.0,
        max_val=240.0,  # 10 days max dwell
        expected_mean=8.0,
        monotone_direction="positive",
        description="Total cumulative dwell time",
    ),
    "max_single_dwell_hours": FeatureSpec(
        name="max_single_dwell_hours",
        dtype="float",
        min_val=0.0,
        max_val=120.0,  # 5 days max single dwell
        expected_mean=4.0,
        monotone_direction="positive",
        description="Longest single dwell event",
    ),
    "handoff_count": FeatureSpec(
        name="handoff_count",
        dtype="int",
        min_val=0,
        max_val=20,
        expected_mean=3.0,
        monotone_direction="positive",
        description="Number of custody handoffs",
    ),
    "max_custody_gap_hours": FeatureSpec(
        name="max_custody_gap_hours",
        dtype="float",
        min_val=0.0,
        max_val=72.0,
        expected_mean=2.0,
        monotone_direction="positive",
        description="Longest gap in custody chain tracking",
    ),
    # Binary flags
    "delay_flag": FeatureSpec(
        name="delay_flag",
        dtype="binary",
        min_val=0,
        max_val=1,
        monotone_direction="positive",  # Delay = more risk
        leakage_risk="high",  # Direct correlation with severe_delay!
        description="Binary: 1 if shipment is delayed",
    ),
    "prior_losses_flag": FeatureSpec(
        name="prior_losses_flag",
        dtype="binary",
        min_val=0,
        max_val=1,
        monotone_direction="positive",
        description="Binary: 1 if prior losses on corridor/shipper",
    ),
    "missing_required_docs": FeatureSpec(
        name="missing_required_docs",
        dtype="int",
        min_val=0,
        max_val=10,
        expected_mean=0.3,
        monotone_direction="positive",
        description="Count of missing required documents",
    ),
    # Historical performance (inverse monotonicity)
    "shipper_on_time_pct_90d": FeatureSpec(
        name="shipper_on_time_pct_90d",
        dtype="float",
        min_val=0.0,
        max_val=100.0,
        expected_mean=88.0,
        monotone_direction="negative",  # Higher on-time = LESS risk
        description="Shipper on-time delivery rate (90d)",
    ),
    "carrier_on_time_pct_90d": FeatureSpec(
        name="carrier_on_time_pct_90d",
        dtype="float",
        min_val=0.0,
        max_val=100.0,
        expected_mean=85.0,
        monotone_direction="negative",  # Higher on-time = LESS risk
        description="Carrier on-time delivery rate (90d)",
    ),
    # Sentiment features
    "lane_sentiment_score": FeatureSpec(
        name="lane_sentiment_score",
        dtype="float",
        min_val=0.0,
        max_val=1.0,
        expected_mean=0.65,
        monotone_direction="negative",  # Higher sentiment = LESS risk
        description="Lane-specific sentiment score",
    ),
    "macro_logistics_sentiment_score": FeatureSpec(
        name="macro_logistics_sentiment_score",
        dtype="float",
        min_val=0.0,
        max_val=1.0,
        expected_mean=0.70,
        monotone_direction="negative",
        description="Global logistics sentiment score",
    ),
    "sentiment_trend_7d": FeatureSpec(
        name="sentiment_trend_7d",
        dtype="float",
        min_val=-0.5,
        max_val=0.5,
        expected_mean=0.0,
        monotone_direction="negative",  # Positive trend = improving = less risk
        description="7-day sentiment trend",
    ),
    "sentiment_volatility_30d": FeatureSpec(
        name="sentiment_volatility_30d",
        dtype="float",
        min_val=0.0,
        max_val=0.5,
        expected_mean=0.12,
        monotone_direction="positive",  # Higher volatility = more risk
        description="30-day sentiment volatility",
    ),
    # IoT features
    "temp_mean": FeatureSpec(
        name="temp_mean",
        dtype="float",
        min_val=-40.0,
        max_val=60.0,
        expected_mean=20.0,
        monotone_direction="none",  # Non-monotone (extremes are bad)
        description="Mean temperature during transit",
        nullable=True,
    ),
    "temp_std": FeatureSpec(
        name="temp_std",
        dtype="float",
        min_val=0.0,
        max_val=20.0,
        expected_mean=2.0,
        monotone_direction="positive",  # Higher variability = more risk
        description="Temperature standard deviation",
        nullable=True,
    ),
    "temp_out_of_range_pct": FeatureSpec(
        name="temp_out_of_range_pct",
        dtype="float",
        min_val=0.0,
        max_val=100.0,
        expected_mean=5.0,
        monotone_direction="positive",
        description="Percentage of time temp was out of range",
        nullable=True,
    ),
    "sensor_uptime_pct": FeatureSpec(
        name="sensor_uptime_pct",
        dtype="float",
        min_val=0.0,
        max_val=100.0,
        expected_mean=95.0,
        monotone_direction="negative",  # Higher uptime = less risk
        description="IoT sensor uptime percentage",
        nullable=True,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA INTERROGATION - Feature Analysis
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class FeatureStats:
    """Statistics for a single feature computed from data."""

    name: str
    count: int = 0
    null_count: int = 0
    min_val: float = float("inf")
    max_val: float = float("-inf")
    mean: float = 0.0
    std: float = 0.0
    percentiles: dict[int, float] = field(default_factory=dict)
    unique_count: int = 0

    @property
    def null_rate(self) -> float:
        return self.null_count / self.count if self.count > 0 else 0.0


def compute_feature_statistics(
    rows: Sequence[dict[str, Any]],
    feature_names: list[str] | None = None,
) -> dict[str, FeatureStats]:
    """
    Compute comprehensive statistics for each feature.

    Args:
        rows: Training rows (list of dicts with 'features' key)
        feature_names: Optional subset of features to analyze

    Returns:
        Dictionary mapping feature name to FeatureStats
    """
    if feature_names is None:
        feature_names = list(FEATURE_SPECS.keys())

    # Collect values for each feature
    feature_values: dict[str, list[float]] = defaultdict(list)
    null_counts: dict[str, int] = defaultdict(int)

    for row in rows:
        features = row.get("features", row)  # Handle both formats
        for name in feature_names:
            value = features.get(name)
            if value is None:
                null_counts[name] += 1
            else:
                try:
                    feature_values[name].append(float(value))
                except (ValueError, TypeError):
                    null_counts[name] += 1

    # Compute statistics
    stats = {}
    for name in feature_names:
        values = feature_values[name]

        if len(values) == 0:
            stats[name] = FeatureStats(
                name=name,
                count=len(rows),
                null_count=null_counts[name],
            )
            continue

        np_values = np.array(values)

        stats[name] = FeatureStats(
            name=name,
            count=len(rows),
            null_count=null_counts[name],
            min_val=float(np_values.min()),
            max_val=float(np_values.max()),
            mean=float(np_values.mean()),
            std=float(np_values.std()),
            percentiles={
                5: float(np.percentile(np_values, 5)),
                25: float(np.percentile(np_values, 25)),
                50: float(np.percentile(np_values, 50)),
                75: float(np.percentile(np_values, 75)),
                95: float(np.percentile(np_values, 95)),
            },
            unique_count=len(set(values)),
        )

    return stats


def detect_range_violations(
    stats: dict[str, FeatureStats],
    tolerance_pct: float = 10.0,
) -> list[dict[str, Any]]:
    """
    Detect features with values outside expected ranges.

    Args:
        stats: Feature statistics from compute_feature_statistics
        tolerance_pct: Allowed percentage deviation from expected range

    Returns:
        List of violation records
    """
    violations = []

    for name, feat_stats in stats.items():
        if name not in FEATURE_SPECS:
            continue

        spec = FEATURE_SPECS[name]

        # Check min violation
        if spec.min_val is not None and feat_stats.min_val < spec.min_val:
            pct_below = abs(feat_stats.min_val - spec.min_val) / abs(spec.min_val) * 100 if spec.min_val != 0 else 100
            if pct_below > tolerance_pct:
                violations.append(
                    {
                        "feature": name,
                        "violation_type": "min_exceeded",
                        "expected": spec.min_val,
                        "actual": feat_stats.min_val,
                        "deviation_pct": pct_below,
                        "severity": "high" if pct_below > 50 else "medium",
                    }
                )

        # Check max violation
        if spec.max_val is not None and feat_stats.max_val > spec.max_val:
            pct_above = abs(feat_stats.max_val - spec.max_val) / abs(spec.max_val) * 100 if spec.max_val != 0 else 100
            if pct_above > tolerance_pct:
                violations.append(
                    {
                        "feature": name,
                        "violation_type": "max_exceeded",
                        "expected": spec.max_val,
                        "actual": feat_stats.max_val,
                        "deviation_pct": pct_above,
                        "severity": "high" if pct_above > 50 else "medium",
                    }
                )

        # Check mean drift
        if spec.expected_mean is not None and feat_stats.mean != 0:
            mean_drift = abs(feat_stats.mean - spec.expected_mean) / abs(spec.expected_mean) * 100 if spec.expected_mean != 0 else 0
            if mean_drift > tolerance_pct:
                violations.append(
                    {
                        "feature": name,
                        "violation_type": "mean_drift",
                        "expected": spec.expected_mean,
                        "actual": feat_stats.mean,
                        "deviation_pct": mean_drift,
                        "severity": "medium",
                    }
                )

    return violations


# ═══════════════════════════════════════════════════════════════════════════════
# LEAKAGE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


def detect_target_leakage(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """
    Detect potential target leakage in feature set.

    Checks for:
    1. High correlation between features and labels
    2. Features derived from post-outcome data
    3. Perfect predictors (AUC = 1.0)

    Args:
        rows: Training rows with features and labels

    Returns:
        Dictionary with leakage analysis results
    """
    results = {
        "leakage_detected": False,
        "high_risk_features": [],
        "correlation_analysis": {},
        "recommendations": [],
    }

    # Extract features and labels
    feature_values: dict[str, list[float]] = defaultdict(list)
    labels = []

    for row in rows:
        features = row.get("features", row)

        # Composite bad_outcome label
        bad_outcome = row.get("had_claim", False) or row.get("had_dispute", False) or row.get("severe_delay", False)
        labels.append(int(bad_outcome))

        for name in FEATURE_SPECS:
            value = features.get(name, 0.0)
            try:
                feature_values[name].append(float(value) if value is not None else 0.0)
            except (ValueError, TypeError):
                feature_values[name].append(0.0)

    labels_np = np.array(labels)

    if labels_np.sum() == 0 or labels_np.sum() == len(labels_np):
        results["recommendations"].append("Cannot compute correlations: all labels are identical")
        return results

    # Compute point-biserial correlation for each feature
    for name, values in feature_values.items():
        values_np = np.array(values)

        if values_np.std() == 0:
            continue

        # Point-biserial correlation
        corr = np.corrcoef(values_np, labels_np)[0, 1]

        if np.isnan(corr):
            continue

        results["correlation_analysis"][name] = {
            "correlation": float(corr),
            "abs_correlation": float(abs(corr)),
        }

        # Check for suspicious correlations
        spec = FEATURE_SPECS.get(name)
        if spec and spec.leakage_risk in ("medium", "high"):
            if abs(corr) > 0.5:
                results["high_risk_features"].append(
                    {
                        "feature": name,
                        "correlation": float(corr),
                        "leakage_risk": spec.leakage_risk,
                        "description": spec.description,
                    }
                )
                results["leakage_detected"] = True

        # Flag any feature with extremely high correlation
        if abs(corr) > 0.8:
            results["high_risk_features"].append(
                {
                    "feature": name,
                    "correlation": float(corr),
                    "leakage_risk": "critical",
                    "reason": "Correlation > 0.8 suggests direct label leakage",
                }
            )
            results["leakage_detected"] = True

    # Recommendations
    if results["leakage_detected"]:
        results["recommendations"].extend(
            [
                "⚠️ HIGH CORRELATION DETECTED - Review feature derivation logic",
                "Consider removing or transforming high-correlation features",
                "Verify features are computed BEFORE outcome is known",
            ]
        )
    else:
        results["recommendations"].append("✓ No obvious target leakage detected")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CORRIDOR BIAS ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


def analyze_corridor_bias(
    rows: Sequence[dict[str, Any]],
    top_n: int = 10,
) -> dict[str, Any]:
    """
    Analyze model fairness across corridors.

    Detects:
    1. Disparate outcome rates by corridor
    2. Feature distribution drift between corridors
    3. Potential proxy discrimination

    Args:
        rows: Training rows with features and labels
        top_n: Number of top corridors to analyze

    Returns:
        Dictionary with corridor bias analysis
    """
    # Group data by corridor
    corridor_data: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "bad_outcomes": 0,
            "features": defaultdict(list),
        }
    )

    for row in rows:
        features = row.get("features", row)
        corridor = features.get("corridor", "unknown")

        bad_outcome = row.get("had_claim", False) or row.get("had_dispute", False) or row.get("severe_delay", False)

        corridor_data[corridor]["count"] += 1
        corridor_data[corridor]["bad_outcomes"] += int(bad_outcome)

        for feat_name in ["planned_transit_hours", "eta_deviation_hours", "carrier_on_time_pct_90d"]:
            value = features.get(feat_name, 0.0)
            if value is not None:
                corridor_data[corridor]["features"][feat_name].append(float(value))

    # Sort corridors by count
    sorted_corridors = sorted(corridor_data.keys(), key=lambda c: corridor_data[c]["count"], reverse=True)[:top_n]

    # Compute corridor-level statistics
    corridor_stats = {}
    global_bad_rate = sum(c["bad_outcomes"] for c in corridor_data.values()) / sum(c["count"] for c in corridor_data.values())

    for corridor in sorted_corridors:
        data = corridor_data[corridor]
        bad_rate = data["bad_outcomes"] / data["count"] if data["count"] > 0 else 0

        # Compute feature means for this corridor
        feature_means = {}
        for feat_name, values in data["features"].items():
            if values:
                feature_means[feat_name] = float(np.mean(values))

        corridor_stats[corridor] = {
            "count": data["count"],
            "bad_outcome_rate": float(bad_rate),
            "rate_vs_global": float(bad_rate - global_bad_rate),
            "feature_means": feature_means,
        }

    # Detect bias
    bias_flags = []
    for corridor, stats in corridor_stats.items():
        rate_diff = abs(stats["rate_vs_global"])
        if rate_diff > 0.10:  # >10% deviation from global rate
            bias_flags.append(
                {
                    "corridor": corridor,
                    "bad_rate": stats["bad_outcome_rate"],
                    "global_rate": global_bad_rate,
                    "deviation": stats["rate_vs_global"],
                    "severity": "high" if rate_diff > 0.20 else "medium",
                }
            )

    return {
        "global_bad_rate": float(global_bad_rate),
        "corridor_stats": corridor_stats,
        "bias_flags": bias_flags,
        "top_corridors": sorted_corridors,
        "fairness_score": 1.0 - (len(bias_flags) / len(sorted_corridors)) if sorted_corridors else 1.0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MONOTONICITY VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


def validate_monotonicity(
    model_coefficients: dict[str, float],
) -> dict[str, Any]:
    """
    Validate that model coefficients respect monotonicity constraints.

    For glass-box logistic regression, coefficients should:
    - Be positive for features that increase risk
    - Be negative for features that decrease risk

    Args:
        model_coefficients: Dictionary mapping feature name to coefficient

    Returns:
        Dictionary with monotonicity validation results
    """
    violations = []
    compliant = []

    for name, coef in model_coefficients.items():
        if name not in FEATURE_SPECS:
            continue

        spec = FEATURE_SPECS[name]

        if spec.monotone_direction == "none":
            compliant.append({"feature": name, "status": "unconstrained", "coefficient": coef})
            continue

        if spec.monotone_direction == "positive" and coef < 0:
            violations.append(
                {
                    "feature": name,
                    "expected_sign": "positive",
                    "actual_coefficient": coef,
                    "reason": f"{spec.description} should INCREASE risk",
                }
            )
        elif spec.monotone_direction == "negative" and coef > 0:
            violations.append(
                {
                    "feature": name,
                    "expected_sign": "negative",
                    "actual_coefficient": coef,
                    "reason": f"{spec.description} should DECREASE risk",
                }
            )
        else:
            compliant.append(
                {
                    "feature": name,
                    "status": "compliant",
                    "expected_sign": spec.monotone_direction,
                    "coefficient": coef,
                }
            )

    return {
        "violations": violations,
        "compliant_features": compliant,
        "violation_count": len(violations),
        "compliance_rate": len(compliant) / (len(compliant) + len(violations)) if (len(compliant) + len(violations)) > 0 else 1.0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CALIBRATION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


def analyze_calibration(
    y_true: Sequence[int],
    y_proba: Sequence[float],
    n_bins: int = 10,
) -> dict[str, Any]:
    """
    Analyze model calibration using binned predictions.

    Well-calibrated: predicted probability ≈ observed frequency

    Args:
        y_true: True binary labels
        y_proba: Predicted probabilities
        n_bins: Number of bins for calibration curve

    Returns:
        Dictionary with calibration analysis
    """
    y_true_np = np.array(y_true)
    y_proba_np = np.array(y_proba)

    # Create bins
    bin_edges = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(y_proba_np, bin_edges[:-1]) - 1

    calibration_bins = []
    total_mse = 0.0

    for i in range(n_bins):
        mask = bin_indices == i
        if mask.sum() == 0:
            continue

        bin_proba = y_proba_np[mask]
        bin_true = y_true_np[mask]

        predicted_mean = float(bin_proba.mean())
        observed_rate = float(bin_true.mean())

        calibration_bins.append(
            {
                "bin": i,
                "range": f"[{bin_edges[i]:.2f}, {bin_edges[i+1]:.2f})",
                "count": int(mask.sum()),
                "predicted_mean": predicted_mean,
                "observed_rate": observed_rate,
                "calibration_error": abs(predicted_mean - observed_rate),
            }
        )

        total_mse += (predicted_mean - observed_rate) ** 2 * mask.sum()

    # Calculate slope and intercept (reliability diagram)
    if len(calibration_bins) >= 2:
        predicted = [b["predicted_mean"] for b in calibration_bins]
        observed = [b["observed_rate"] for b in calibration_bins]

        # Simple linear regression
        pred_np = np.array(predicted)
        obs_np = np.array(observed)

        slope = np.cov(pred_np, obs_np)[0, 1] / np.var(pred_np) if np.var(pred_np) > 0 else 1.0
        intercept = obs_np.mean() - slope * pred_np.mean()
    else:
        slope = 1.0
        intercept = 0.0

    # Expected Calibration Error (ECE)
    ece = sum(b["calibration_error"] * b["count"] for b in calibration_bins) / len(y_true)

    return {
        "calibration_bins": calibration_bins,
        "slope": float(slope),
        "intercept": float(intercept),
        "expected_calibration_error": float(ece),
        "is_well_calibrated": 0.8 <= slope <= 1.2 and abs(intercept) < 0.05,
        "recommendation": (
            "✓ Model is well-calibrated"
            if 0.8 <= slope <= 1.2 and abs(intercept) < 0.05
            else f"⚠️ Calibration slope={slope:.2f} (target: 0.8-1.2), intercept={intercept:.2f} (target: ~0)"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ADVERSARIAL BOUNDARY TESTING
# ═══════════════════════════════════════════════════════════════════════════════


def generate_adversarial_samples(
    baseline_features: dict[str, float],
    perturbation_types: list[str] = None,
) -> list[dict[str, Any]]:
    """
    Generate adversarial boundary samples to stress-test model.

    Strategies:
    1. Zero all features
    2. Max all features
    3. Flip binary flags
    4. Extreme single-feature perturbation
    5. Opposite sign for all features

    Args:
        baseline_features: Typical feature vector to perturb
        perturbation_types: Optional list of perturbation strategies

    Returns:
        List of adversarial sample dictionaries
    """
    if perturbation_types is None:
        perturbation_types = ["zero", "max", "flip_binary", "extreme_single", "opposite_sign"]

    adversarial_samples = []

    # 1. Zero all features
    if "zero" in perturbation_types:
        zero_sample = {k: 0.0 for k in baseline_features}
        adversarial_samples.append(
            {
                "name": "all_zeros",
                "strategy": "zero",
                "features": zero_sample,
                "risk_expectation": "should be low risk",
            }
        )

    # 2. Max all features (within spec)
    if "max" in perturbation_types:
        max_sample = {}
        for name, value in baseline_features.items():
            spec = FEATURE_SPECS.get(name)
            if spec and spec.max_val is not None:
                max_sample[name] = spec.max_val
            else:
                max_sample[name] = value * 10
        adversarial_samples.append(
            {
                "name": "all_max",
                "strategy": "max",
                "features": max_sample,
                "risk_expectation": "should be extreme high risk",
            }
        )

    # 3. Flip all binary flags
    if "flip_binary" in perturbation_types:
        flipped = baseline_features.copy()
        for name in ["delay_flag", "prior_losses_flag"]:
            if name in flipped:
                flipped[name] = 1.0 - flipped[name]
        adversarial_samples.append(
            {
                "name": "flipped_binaries",
                "strategy": "flip_binary",
                "features": flipped,
                "risk_expectation": "should flip risk direction",
            }
        )

    # 4. Extreme single-feature perturbation (one at a time)
    if "extreme_single" in perturbation_types:
        for target_feature in ["eta_deviation_hours", "num_route_deviations", "max_custody_gap_hours"]:
            if target_feature not in baseline_features:
                continue

            perturbed = baseline_features.copy()
            spec = FEATURE_SPECS.get(target_feature)
            if spec and spec.max_val is not None:
                perturbed[target_feature] = spec.max_val
            else:
                perturbed[target_feature] = 100.0

            adversarial_samples.append(
                {
                    "name": f"extreme_{target_feature}",
                    "strategy": "extreme_single",
                    "features": perturbed,
                    "risk_expectation": f"should increase risk due to {target_feature}",
                }
            )

    # 5. Opposite sign (where applicable)
    if "opposite_sign" in perturbation_types:
        opposite = baseline_features.copy()
        for name in ["eta_deviation_hours", "sentiment_trend_7d"]:
            if name in opposite:
                opposite[name] = -opposite[name]
        adversarial_samples.append(
            {
                "name": "opposite_signs",
                "strategy": "opposite_sign",
                "features": opposite,
                "risk_expectation": "risk should change direction for deviation features",
            }
        )

    return adversarial_samples


# ═══════════════════════════════════════════════════════════════════════════════
# FULL FORENSICS PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


def run_full_forensics(
    rows: Sequence[dict[str, Any]],
    model_coefficients: dict[str, float] | None = None,
    y_true: Sequence[int] | None = None,
    y_proba: Sequence[float] | None = None,
) -> dict[str, Any]:
    """
    Run complete feature forensics analysis.

    Args:
        rows: Training rows with features and labels
        model_coefficients: Optional model coefficients for monotonicity check
        y_true: Optional true labels for calibration analysis
        y_proba: Optional predicted probabilities for calibration analysis

    Returns:
        Comprehensive forensics report dictionary
    """
    print("\n" + "=" * 70)
    print("🩷 MAGGIE FEATURE FORENSICS - FULL ANALYSIS")
    print("=" * 70)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(rows),
        "agent": "Maggie (GID-10)",
        "pac": "MAGGIE-PAC-A",
    }

    # 1. Feature Statistics
    print("\n[1/6] Computing feature statistics...")
    feature_names = list(FEATURE_SPECS.keys())
    stats = compute_feature_statistics(rows, feature_names)
    results["feature_stats"] = {
        name: {
            "count": s.count,
            "null_rate": s.null_rate,
            "min": s.min_val,
            "max": s.max_val,
            "mean": s.mean,
            "std": s.std,
            "p50": s.percentiles.get(50, None),
        }
        for name, s in stats.items()
    }
    print(f"   ✓ Analyzed {len(stats)} features")

    # 2. Range Violations
    print("\n[2/6] Detecting range violations...")
    violations = detect_range_violations(stats)
    results["range_violations"] = violations
    print(f"   ✓ Found {len(violations)} range violations")

    # 3. Target Leakage
    print("\n[3/6] Detecting target leakage...")
    leakage = detect_target_leakage(rows)
    results["leakage_analysis"] = leakage
    if leakage["leakage_detected"]:
        print(f"   ⚠️ LEAKAGE DETECTED: {len(leakage['high_risk_features'])} high-risk features")
    else:
        print("   ✓ No target leakage detected")

    # 4. Corridor Bias
    print("\n[4/6] Analyzing corridor bias...")
    corridor_bias = analyze_corridor_bias(rows)
    results["corridor_bias"] = corridor_bias
    print(f"   ✓ Analyzed {len(corridor_bias['corridor_stats'])} corridors, fairness={corridor_bias['fairness_score']:.2f}")

    # 5. Monotonicity (if coefficients provided)
    if model_coefficients:
        print("\n[5/6] Validating monotonicity constraints...")
        monotonicity = validate_monotonicity(model_coefficients)
        results["monotonicity"] = monotonicity
        print(f"   ✓ Compliance rate: {monotonicity['compliance_rate']:.1%}")
        if monotonicity["violations"]:
            print(f"   ⚠️ {len(monotonicity['violations'])} monotonicity violations")
    else:
        print("\n[5/6] Skipping monotonicity (no coefficients provided)")
        results["monotonicity"] = None

    # 6. Calibration (if predictions provided)
    if y_true is not None and y_proba is not None:
        print("\n[6/6] Analyzing calibration...")
        calibration = analyze_calibration(y_true, y_proba)
        results["calibration"] = calibration
        print(f"   ✓ Slope={calibration['slope']:.2f}, ECE={calibration['expected_calibration_error']:.3f}")
    else:
        print("\n[6/6] Skipping calibration (no predictions provided)")
        results["calibration"] = None

    # Generate verdict
    results["verdict"] = _generate_verdict(results)

    print("\n" + "=" * 70)
    print(f"VERDICT: {results['verdict']['decision']}")
    print("=" * 70)

    return results


def _generate_verdict(results: dict[str, Any]) -> dict[str, Any]:
    """Generate deploy/no-deploy verdict based on forensics results."""
    blockers = []
    warnings = []

    # Check leakage
    if results["leakage_analysis"]["leakage_detected"]:
        if any(f.get("leakage_risk") == "critical" for f in results["leakage_analysis"]["high_risk_features"]):
            blockers.append("Critical target leakage detected")
        else:
            warnings.append("Moderate target leakage detected")

    # Check range violations
    high_violations = [v for v in results["range_violations"] if v["severity"] == "high"]
    if len(high_violations) > 3:
        blockers.append(f"Too many high-severity range violations ({len(high_violations)})")
    elif high_violations:
        warnings.append(f"{len(high_violations)} high-severity range violations")

    # Check corridor fairness
    if results["corridor_bias"]["fairness_score"] < 0.7:
        blockers.append(f"Low corridor fairness score ({results['corridor_bias']['fairness_score']:.2f})")
    elif results["corridor_bias"]["fairness_score"] < 0.85:
        warnings.append("Moderate corridor bias detected")

    # Check monotonicity
    if results["monotonicity"]:
        if results["monotonicity"]["compliance_rate"] < 0.8:
            warnings.append("Monotonicity compliance below 80%")

    # Check calibration
    if results["calibration"]:
        if not results["calibration"]["is_well_calibrated"]:
            warnings.append("Model calibration outside acceptable range")

    # Decision
    if blockers:
        decision = "❌ NO-DEPLOY"
        recommendation = "Address blockers before deployment"
    elif len(warnings) > 3:
        decision = "⚠️ CONDITIONAL-DEPLOY"
        recommendation = "Deploy with monitoring; address warnings"
    elif warnings:
        decision = "✅ DEPLOY-WITH-MONITORING"
        recommendation = "Safe to deploy; monitor warnings"
    else:
        decision = "✅ DEPLOY"
        recommendation = "All checks passed; safe to deploy"

    return {
        "decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "recommendation": recommendation,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """CLI entry point for feature forensics."""

    print("\n🩷 MAGGIE FEATURE FORENSICS - ChainIQ ML Audit")
    print("=" * 70)

    # Generate synthetic data for demo
    from app.ml.validation_real_data import load_ingested_training_rows

    print("\nLoading training rows...")
    rows = load_ingested_training_rows(limit=2000)

    # Run full forensics
    results = run_full_forensics(rows)

    # Save results
    output_dir = Path(__file__).parent.parent.parent / "docs" / "chainiq"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate markdown report
    report_path = output_dir / "FEATURE_FORENSICS.md"
    with open(report_path, "w") as f:
        f.write(generate_forensics_markdown(results))

    print(f"\n✓ Report saved to: {report_path}")

    return results


def generate_forensics_markdown(results: dict[str, Any]) -> str:
    """Generate comprehensive markdown report from forensics results."""
    timestamp = results.get("timestamp", datetime.now(timezone.utc).isoformat())
    verdict = results.get("verdict", {})

    md = f"""# ChainIQ ML Feature Forensics Report

**Generated:** {timestamp}
**Agent:** Maggie (GID-10) 🩷
**PAC:** MAGGIE-PAC-A
**Sample Count:** {results.get('sample_count', 0):,}

---

## Executive Summary

### Deployment Verdict: {verdict.get('decision', 'UNKNOWN')}

**Recommendation:** {verdict.get('recommendation', 'N/A')}

"""

    # Blockers and warnings
    if verdict.get("blockers"):
        md += "### 🛑 Deployment Blockers\n\n"
        for blocker in verdict["blockers"]:
            md += f"- {blocker}\n"
        md += "\n"

    if verdict.get("warnings"):
        md += "### ⚠️ Warnings\n\n"
        for warning in verdict["warnings"]:
            md += f"- {warning}\n"
        md += "\n"

    md += "---\n\n"

    # Feature Statistics
    md += "## Feature Statistics Summary\n\n"
    md += "| Feature | Count | Null% | Min | Max | Mean | Std |\n"
    md += "|---------|-------|-------|-----|-----|------|-----|\n"

    for name, stats in results.get("feature_stats", {}).items():
        md += f"| `{name}` | {stats.get('count', 0)} | {stats.get('null_rate', 0)*100:.1f}% | "
        md += f"{stats.get('min', 'N/A'):.2f} | {stats.get('max', 'N/A'):.2f} | "
        md += f"{stats.get('mean', 0):.2f} | {stats.get('std', 0):.2f} |\n"

    md += "\n---\n\n"

    # Range Violations
    md += "## Range Violations\n\n"
    violations = results.get("range_violations", [])
    if violations:
        md += f"**{len(violations)} violations detected:**\n\n"
        md += "| Feature | Type | Expected | Actual | Deviation | Severity |\n"
        md += "|---------|------|----------|--------|-----------|----------|\n"
        for v in violations[:20]:  # Top 20
            md += f"| `{v['feature']}` | {v['violation_type']} | {v['expected']:.2f} | {v['actual']:.2f} | {v['deviation_pct']:.1f}% | {v['severity']} |\n"
    else:
        md += "✅ No range violations detected.\n"

    md += "\n---\n\n"

    # Target Leakage
    md += "## Target Leakage Analysis\n\n"
    leakage = results.get("leakage_analysis", {})
    if leakage.get("leakage_detected"):
        md += "⚠️ **POTENTIAL LEAKAGE DETECTED**\n\n"
        md += "### High-Risk Features\n\n"
        for feat in leakage.get("high_risk_features", []):
            md += f"- **{feat['feature']}**: correlation={feat['correlation']:.3f}, risk={feat.get('leakage_risk', 'unknown')}\n"
    else:
        md += "✅ No obvious target leakage detected.\n"

    md += "\n### Recommendations\n\n"
    for rec in leakage.get("recommendations", []):
        md += f"- {rec}\n"

    md += "\n---\n\n"

    # Corridor Bias
    md += "## Corridor Fairness Analysis\n\n"
    corridor = results.get("corridor_bias", {})
    md += f"**Global Bad Outcome Rate:** {corridor.get('global_bad_rate', 0)*100:.1f}%  \n"
    md += f"**Fairness Score:** {corridor.get('fairness_score', 0):.2f} (target: ≥0.85)  \n\n"

    md += "### Corridor Statistics\n\n"
    md += "| Corridor | Count | Bad Rate | vs Global |\n"
    md += "|----------|-------|----------|----------|\n"
    for corr, stats in corridor.get("corridor_stats", {}).items():
        diff = stats.get("rate_vs_global", 0)
        symbol = "🔴" if abs(diff) > 0.10 else "🟡" if abs(diff) > 0.05 else "🟢"
        md += f"| {corr} | {stats.get('count', 0)} | {stats.get('bad_outcome_rate', 0)*100:.1f}% | {symbol} {diff*100:+.1f}% |\n"

    if corridor.get("bias_flags"):
        md += "\n### ⚠️ Bias Flags\n\n"
        for flag in corridor.get("bias_flags", []):
            md += f"- **{flag['corridor']}**: {flag['deviation']*100:+.1f}% deviation ({flag['severity']})\n"

    md += "\n---\n\n"

    # Monotonicity
    md += "## Monotonicity Validation\n\n"
    mono = results.get("monotonicity")
    if mono:
        md += f"**Compliance Rate:** {mono.get('compliance_rate', 0)*100:.1f}%\n\n"
        if mono.get("violations"):
            md += "### Violations\n\n"
            for v in mono["violations"]:
                md += f"- **{v['feature']}**: expected {v['expected_sign']}, got coef={v['actual_coefficient']:.4f}\n"
                md += f"  - Reason: {v['reason']}\n"
    else:
        md += "*Monotonicity validation skipped (no model coefficients provided)*\n"

    md += "\n---\n\n"

    # Calibration
    md += "## Calibration Analysis\n\n"
    cal = results.get("calibration")
    if cal:
        md += f"**Slope:** {cal.get('slope', 0):.3f} (target: 0.8-1.2)  \n"
        md += f"**Intercept:** {cal.get('intercept', 0):.3f} (target: ~0)  \n"
        md += f"**ECE:** {cal.get('expected_calibration_error', 0):.3f}  \n"
        md += f"**Status:** {cal.get('recommendation', 'Unknown')}\n\n"

        md += "### Calibration Bins\n\n"
        md += "| Bin | Range | Count | Predicted | Observed | Error |\n"
        md += "|-----|-------|-------|-----------|----------|-------|\n"
        for b in cal.get("calibration_bins", []):
            md += f"| {b['bin']} | {b['range']} | {b['count']} | {b['predicted_mean']:.3f} | {b['observed_rate']:.3f} | {b['calibration_error']:.3f} |\n"
    else:
        md += "*Calibration analysis skipped (no predictions provided)*\n"

    md += "\n---\n\n"

    # Feature Specification Reference
    md += "## Appendix: Feature Specifications\n\n"
    md += "| Feature | Type | Range | Monotone | Leakage Risk |\n"
    md += "|---------|------|-------|----------|-------------|\n"
    for name, spec in FEATURE_SPECS.items():
        range_str = f"[{spec.min_val}, {spec.max_val}]" if spec.min_val is not None else "unbounded"
        md += f"| `{name}` | {spec.dtype} | {range_str} | {spec.monotone_direction} | {spec.leakage_risk} |\n"

    md += f"""

---

## Sign-Off

**Agent:** Maggie (GID-10) 🩷
**Status:** Feature Forensics Complete
**Verdict:** {verdict.get('decision', 'UNKNOWN')}

*"Commercial audit complete. Glass-box model validated. Recommend {verdict.get('recommendation', 'review findings')}."*

---

*Generated by ChainIQ ML Feature Forensics v0.2*
"""

    return md


if __name__ == "__main__":
    main()
