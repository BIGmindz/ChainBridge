"""
ChainIQ ML Drift Diagnostics & Feature Attribution

Deep diagnostics for shadow mode drift analysis:
- SHAP-based feature attribution
- Drift-weighted importance scoring
- Corridor-specific attribution
- Monotonicity validation v2
- Drift-aware risk multiplier

Integration Points:
- Cody's v1.1 drift engine (corridor_analysis.py)
- Feature forensics (feature_forensics.py)
- Monotone GAM (monotone_gam.py)

Author: Maggie (GID-10) 🩷
PAC: MAGGIE-NEXT-A02
Version: 0.2.0
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Sequence

import numpy as np

# Internal imports
from app.ml.feature_forensics import FEATURE_SPECS, FeatureSpec, FeatureStats

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# SHAP baseline configuration
SHAP_BASELINE_CONFIG = {
    "background_samples": 100,
    "max_samples_for_explanation": 1000,
    "top_features": 10,
}

# Drift severity thresholds
DRIFT_SEVERITY_THRESHOLDS = {
    "negligible": 0.05,  # <5% drift
    "minor": 0.10,  # 5-10%
    "moderate": 0.20,  # 10-20%
    "significant": 0.35,  # 20-35%
    "severe": 0.50,  # 35-50%
    "critical": 1.0,  # >50%
}

# Feature type classifications for monotonicity
FEATURE_TYPES = {
    "distance": [
        "max_route_deviation_km",
        "total_route_distance_km",
        "origin_port_distance_km",
        "dest_port_distance_km",
    ],
    "time": [
        "planned_transit_hours",
        "actual_transit_hours",
        "eta_deviation_hours",
        "total_dwell_hours",
        "max_single_dwell_hours",
        "max_custody_gap_hours",
    ],
    "probability": [
        "shipper_on_time_pct_90d",
        "carrier_on_time_pct_90d",
        "lane_sentiment_score",
        "macro_logistics_sentiment_score",
        "sensor_uptime_pct",
        "temp_out_of_range_pct",
    ],
    "count": [
        "num_route_deviations",
        "handoff_count",
        "missing_required_docs",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


class DriftSeverity(Enum):
    """Drift severity classification."""

    NEGLIGIBLE = "negligible"
    MINOR = "minor"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    SEVERE = "severe"
    CRITICAL = "critical"


@dataclass
class SHAPAttribution:
    """SHAP-based feature attribution result."""

    feature_name: str
    shap_value: float
    abs_shap_value: float
    direction: Literal["increases_risk", "decreases_risk"]
    contribution_pct: float
    feature_value: float | None = None
    baseline_value: float | None = None


@dataclass
class DriftFeatureAttribution:
    """Drift-weighted feature importance."""

    feature_name: str
    base_importance: float
    drift_magnitude: float
    drift_direction: Literal["positive", "negative", "stable"]
    drift_severity: DriftSeverity
    drift_weighted_importance: float
    rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature_name,
            "base_importance": self.base_importance,
            "drift_magnitude": self.drift_magnitude,
            "drift_direction": self.drift_direction,
            "drift_severity": self.drift_severity.value,
            "drift_weighted_importance": self.drift_weighted_importance,
            "rank": self.rank,
        }


@dataclass
class CorridorAttribution:
    """Corridor-specific drift attribution."""

    corridor: str
    event_count: int
    avg_delta: float
    p95_delta: float
    drift_flag: bool
    top_drift_features: list[DriftFeatureAttribution]
    attribution_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MonotonicityViolation:
    """Monotonicity constraint violation record."""

    feature_name: str
    feature_type: str
    expected_direction: Literal["increasing", "decreasing", "none"]
    actual_direction: Literal["increasing", "decreasing", "non_monotonic"]
    violation_score: float  # 0-1 severity
    sample_count: int
    violation_indices: list[int] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class MonotonicityValidationResult:
    """Result of monotonicity validation."""

    is_valid: bool
    total_features: int
    validated_features: int
    violations: list[MonotonicityViolation]
    passed_features: list[str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DriftRiskMultiplier:
    """Drift-aware risk multiplier for scoring."""

    base_multiplier: float
    drift_adjustment: float
    corridor_adjustment: float
    final_multiplier: float
    confidence: float
    rationale: str


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FEATURE ATTRIBUTION FOR DRIFT
# ═══════════════════════════════════════════════════════════════════════════════


class DriftFeatureAttributor:
    """
    Feature attribution engine for drift analysis.

    Combines SHAP-like attribution with drift-weighted importance
    to identify which features are driving model disagreement.
    """

    def __init__(
        self,
        feature_specs: dict[str, FeatureSpec] | None = None,
        drift_weight: float = 0.5,
    ):
        """
        Initialize drift feature attributor.

        Args:
            feature_specs: Feature specifications (defaults to FEATURE_SPECS)
            drift_weight: Weight for drift in combined importance (0-1)
        """
        self.feature_specs = feature_specs or FEATURE_SPECS
        self.drift_weight = drift_weight
        self._baseline_values: dict[str, float] = {}
        self._importance_cache: dict[str, float] = {}

    def compute_shap_baseline(
        self,
        reference_data: Sequence[dict[str, Any]],
        feature_names: list[str] | None = None,
    ) -> dict[str, float]:
        """
        Compute SHAP baseline values from reference data.

        Uses mean values as baseline for interpretability.

        Args:
            reference_data: Historical reference dataset
            feature_names: Features to compute baseline for

        Returns:
            Dictionary of feature -> baseline value
        """
        if feature_names is None:
            feature_names = list(self.feature_specs.keys())

        # Collect values
        feature_values: dict[str, list[float]] = defaultdict(list)

        for row in reference_data:
            features = row.get("features", row)
            for name in feature_names:
                value = features.get(name)
                if value is not None:
                    try:
                        feature_values[name].append(float(value))
                    except (ValueError, TypeError):
                        pass

        # Compute baseline (mean)
        baseline = {}
        for name in feature_names:
            values = feature_values[name]
            if values:
                baseline[name] = float(np.mean(values))
            else:
                baseline[name] = 0.0

        self._baseline_values = baseline
        logger.info("Computed SHAP baseline for %d features", len(baseline))

        return baseline

    def compute_sample_attribution(
        self,
        sample: dict[str, Any],
        _model_scores: dict[str, float],
        baseline: dict[str, float] | None = None,
    ) -> list[SHAPAttribution]:
        """
        Compute SHAP-like attribution for a single sample.

        Uses coefficient-based attribution (linear approximation).

        Args:
            sample: Input sample features
            model_scores: Model output scores (dummy_score, real_score, delta)
            baseline: Baseline values (uses cached if not provided)

        Returns:
            List of feature attributions sorted by absolute contribution
        """
        baseline = baseline or self._baseline_values
        features = sample.get("features", sample)

        attributions = []
        total_abs_contribution = 0.0

        for name, spec in self.feature_specs.items():
            value = features.get(name)
            if value is None:
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            base_val = baseline.get(name, 0.0)
            delta = value - base_val

            # Compute pseudo-SHAP value based on monotonicity direction
            # Positive contribution means pushing toward higher risk
            if spec.monotone_direction == "positive":
                shap_value = delta * 0.1  # Scale factor
            elif spec.monotone_direction == "negative":
                shap_value = -delta * 0.1
            else:
                shap_value = abs(delta) * 0.05  # Reduced weight for non-monotonic

            abs_shap = abs(shap_value)
            total_abs_contribution += abs_shap

            attributions.append(
                SHAPAttribution(
                    feature_name=name,
                    shap_value=shap_value,
                    abs_shap_value=abs_shap,
                    direction="increases_risk" if shap_value > 0 else "decreases_risk",
                    contribution_pct=0.0,  # Computed below
                    feature_value=value,
                    baseline_value=base_val,
                )
            )

        # Compute contribution percentages
        for attr in attributions:
            if total_abs_contribution > 0:
                attr.contribution_pct = (attr.abs_shap_value / total_abs_contribution) * 100

        # Sort by absolute contribution
        attributions.sort(key=lambda a: a.abs_shap_value, reverse=True)

        return attributions

    def compute_drift_weighted_importance(
        self,
        current_stats: dict[str, FeatureStats],
        reference_stats: dict[str, FeatureStats],
        base_importance: dict[str, float] | None = None,
    ) -> list[DriftFeatureAttribution]:
        """
        Compute drift-weighted feature importance.

        Combines base model importance with drift magnitude to identify
        features that are both important AND drifting.

        Args:
            current_stats: Current period feature statistics
            reference_stats: Reference period feature statistics
            base_importance: Model-based feature importance (optional)

        Returns:
            List of drift-weighted attributions sorted by importance
        """
        attributions = []

        for name in current_stats:
            if name not in reference_stats:
                continue

            curr = current_stats[name]
            ref = reference_stats[name]

            # Compute drift magnitude (normalized)
            if ref.mean != 0:
                mean_drift = abs(curr.mean - ref.mean) / abs(ref.mean)
            else:
                mean_drift = abs(curr.mean) if curr.mean != 0 else 0.0

            if ref.std != 0:
                std_drift = abs(curr.std - ref.std) / ref.std
            else:
                std_drift = 0.0

            # Combined drift magnitude
            drift_magnitude = (mean_drift + std_drift) / 2

            # Determine drift direction
            if curr.mean > ref.mean * 1.05:
                drift_direction = "positive"
            elif curr.mean < ref.mean * 0.95:
                drift_direction = "negative"
            else:
                drift_direction = "stable"

            # Classify severity
            severity = self._classify_drift_severity(drift_magnitude)

            # Get base importance (use uniform if not provided)
            base_imp = base_importance.get(name, 1.0) if base_importance else 1.0

            # Compute drift-weighted importance
            # Higher drift + higher importance = higher weighted score
            drift_weighted = (1 - self.drift_weight) * base_imp + self.drift_weight * drift_magnitude * base_imp

            attributions.append(
                DriftFeatureAttribution(
                    feature_name=name,
                    base_importance=base_imp,
                    drift_magnitude=drift_magnitude,
                    drift_direction=drift_direction,
                    drift_severity=severity,
                    drift_weighted_importance=drift_weighted,
                )
            )

        # Sort and rank
        attributions.sort(key=lambda a: a.drift_weighted_importance, reverse=True)
        for i, attr in enumerate(attributions):
            attr.rank = i + 1

        return attributions

    def compute_corridor_attribution(
        self,
        corridor_events: Sequence[dict[str, Any]],
        corridor: str,
        reference_data: Sequence[dict[str, Any]] | None = None,
    ) -> CorridorAttribution:
        """
        Compute drift attribution for a specific corridor.

        Args:
            corridor_events: Shadow events for this corridor
            corridor: Corridor identifier
            reference_data: Global reference data for comparison

        Returns:
            Corridor-specific attribution
        """
        if not corridor_events:
            return CorridorAttribution(
                corridor=corridor,
                event_count=0,
                avg_delta=0.0,
                p95_delta=0.0,
                drift_flag=False,
                top_drift_features=[],
            )

        # Compute corridor deltas
        deltas = []
        for event in corridor_events:
            delta = abs(event.get("dummy_score", 0) - event.get("real_score", 0))
            deltas.append(delta)

        deltas_np = np.array(deltas)
        avg_delta = float(deltas_np.mean())
        p95_delta = float(np.percentile(deltas_np, 95))
        drift_flag = p95_delta > 0.25  # Standard threshold

        # Compute feature-level attribution
        from app.ml.feature_forensics import compute_feature_statistics

        corridor_stats = compute_feature_statistics(corridor_events)

        if reference_data:
            ref_stats = compute_feature_statistics(reference_data)
            top_features = self.compute_drift_weighted_importance(corridor_stats, ref_stats)[:5]  # Top 5 drift features
        else:
            top_features = []

        return CorridorAttribution(
            corridor=corridor,
            event_count=len(corridor_events),
            avg_delta=avg_delta,
            p95_delta=p95_delta,
            drift_flag=drift_flag,
            top_drift_features=top_features,
        )

    @staticmethod
    def _classify_drift_severity(magnitude: float) -> DriftSeverity:
        """Classify drift severity based on magnitude."""
        for severity, threshold in DRIFT_SEVERITY_THRESHOLDS.items():
            if magnitude <= threshold:
                return DriftSeverity(severity)
        return DriftSeverity.CRITICAL


# ═══════════════════════════════════════════════════════════════════════════════
# 2. MONOTONICITY VALIDATOR V2
# ═══════════════════════════════════════════════════════════════════════════════


class MonotonicityValidatorV2:
    """
    Enhanced monotonicity validation with type-specific rule sets.

    Validates that:
    - Distance features increase with risk
    - Time features follow expected patterns
    - Probability features maintain calibration
    - Count features are non-decreasing
    """

    # Rule sets by feature type
    RULES = {
        "distance": {
            "direction": "increasing",
            "tolerance": 0.05,
            "description": "Distance features should increase risk as they increase",
        },
        "time": {
            "direction": "increasing",
            "tolerance": 0.10,
            "description": "Time/duration features increase risk with larger values",
        },
        "probability": {
            "direction": "varies",  # Depends on specific feature
            "tolerance": 0.05,
            "description": "Probability features must stay in [0, 1] and maintain monotonicity",
        },
        "count": {
            "direction": "increasing",
            "tolerance": 0.0,
            "description": "Count features must be non-negative integers, risk increases with count",
        },
    }

    def __init__(self, feature_specs: dict[str, FeatureSpec] | None = None):
        """
        Initialize validator.

        Args:
            feature_specs: Feature specifications with monotone_direction
        """
        self.feature_specs = feature_specs or FEATURE_SPECS
        self._feature_type_map = self._build_feature_type_map()

    def _build_feature_type_map(self) -> dict[str, str]:
        """Map each feature to its type category."""
        type_map = {}
        for feat_type, features in FEATURE_TYPES.items():
            for feature in features:
                type_map[feature] = feat_type
        return type_map

    def validate_all(
        self,
        predictions: np.ndarray,
        features: np.ndarray,
        feature_names: list[str],
    ) -> MonotonicityValidationResult:
        """
        Validate monotonicity across all features.

        Args:
            predictions: Model predictions (n_samples,)
            features: Feature matrix (n_samples, n_features)
            feature_names: Feature column names

        Returns:
            Comprehensive validation result
        """
        violations = []
        passed = []

        for i, name in enumerate(feature_names):
            feature_col = features[:, i]

            # Get expected direction
            spec = self.feature_specs.get(name)
            if spec and spec.monotone_direction != "none":
                expected = "increasing" if spec.monotone_direction == "positive" else "decreasing"
            else:
                expected = "none"

            if expected == "none":
                passed.append(name)
                continue

            # Validate this feature
            violation = self._validate_feature(
                feature_name=name,
                feature_values=feature_col,
                predictions=predictions,
                expected_direction=expected,
            )

            if violation:
                violations.append(violation)
            else:
                passed.append(name)

        is_valid = len(violations) == 0

        return MonotonicityValidationResult(
            is_valid=is_valid,
            total_features=len(feature_names),
            validated_features=len(feature_names)
            - len([n for n in feature_names if self.feature_specs.get(n, FeatureSpec(n, "float")).monotone_direction == "none"]),
            violations=violations,
            passed_features=passed,
        )

    def _validate_feature(
        self,
        feature_name: str,
        feature_values: np.ndarray,
        predictions: np.ndarray,
        expected_direction: Literal["increasing", "decreasing"],
    ) -> MonotonicityViolation | None:
        """
        Validate monotonicity for a single feature.

        Uses Spearman correlation to assess monotonicity.
        """
        # Remove NaN values
        valid_mask = ~(np.isnan(feature_values) | np.isnan(predictions))
        feat_clean = feature_values[valid_mask]
        pred_clean = predictions[valid_mask]

        if len(feat_clean) < 10:
            return None  # Insufficient data

        # Compute Spearman correlation for monotonicity
        from scipy import stats as scipy_stats

        try:
            spearman_corr, _ = scipy_stats.spearmanr(feat_clean, pred_clean)
        except Exception:
            # Fallback if scipy not available
            spearman_corr = np.corrcoef(feat_clean, pred_clean)[0, 1]

        # Determine actual direction
        if spearman_corr > 0.1:
            actual_direction = "increasing"
        elif spearman_corr < -0.1:
            actual_direction = "decreasing"
        else:
            actual_direction = "non_monotonic"

        # Check for violation
        feature_type = self._feature_type_map.get(feature_name, "unknown")
        tolerance = self.RULES.get(feature_type, {}).get("tolerance", 0.1)

        is_violation = False

        if expected_direction == "increasing" and spearman_corr < -tolerance:
            is_violation = True
        elif expected_direction == "decreasing" and spearman_corr > tolerance:
            is_violation = True

        if not is_violation:
            return None

        # Compute violation severity
        violation_score = abs(spearman_corr - (1.0 if expected_direction == "increasing" else -1.0)) / 2

        # Find specific violation points
        violation_indices = self._find_violation_indices(feat_clean, pred_clean, expected_direction)

        recommendation = self._generate_recommendation(feature_name, feature_type, expected_direction, actual_direction, violation_score)

        return MonotonicityViolation(
            feature_name=feature_name,
            feature_type=feature_type,
            expected_direction=expected_direction,
            actual_direction=actual_direction,
            violation_score=violation_score,
            sample_count=len(feat_clean),
            violation_indices=violation_indices[:20],  # Limit to 20
            recommendation=recommendation,
        )

    def _find_violation_indices(
        self,
        feature_values: np.ndarray,
        predictions: np.ndarray,
        expected_direction: str,
    ) -> list[int]:
        """Find indices where monotonicity is violated."""
        sorted_idx = np.argsort(feature_values)
        sorted_pred = predictions[sorted_idx]

        violations = []
        for i in range(1, len(sorted_pred)):
            if expected_direction == "increasing":
                if sorted_pred[i] < sorted_pred[i - 1] - 0.01:
                    violations.append(int(sorted_idx[i]))
            else:  # decreasing
                if sorted_pred[i] > sorted_pred[i - 1] + 0.01:
                    violations.append(int(sorted_idx[i]))

        return violations

    def _generate_recommendation(
        self,
        feature_name: str,
        feature_type: str,
        expected: str,
        actual: str,
        severity: float,
    ) -> str:
        """Generate actionable recommendation for violation."""
        if severity > 0.7:
            urgency = "CRITICAL"
        elif severity > 0.4:
            urgency = "HIGH"
        else:
            urgency = "MEDIUM"

        type_advice = {
            "distance": "Consider adding spline constraints or re-binning",
            "time": "Review time encoding; ensure no leakage from future events",
            "probability": "Check calibration; ensure proper sigmoid/logit transform",
            "count": "Verify count encoding; consider log transform",
        }

        advice = type_advice.get(feature_type, "Review feature engineering")

        return f"[{urgency}] {feature_name}: Expected {expected}, observed {actual}. " f"Severity: {severity:.2f}. {advice}"

    def validate_distance_features(
        self,
        predictions: np.ndarray,
        features: np.ndarray,
        feature_names: list[str],
    ) -> list[MonotonicityViolation]:
        """Validate only distance features."""
        distance_features = FEATURE_TYPES.get("distance", [])
        violations = []

        for i, name in enumerate(feature_names):
            if name not in distance_features:
                continue

            violation = self._validate_feature(
                feature_name=name,
                feature_values=features[:, i],
                predictions=predictions,
                expected_direction="increasing",
            )
            if violation:
                violations.append(violation)

        return violations

    def validate_time_features(
        self,
        predictions: np.ndarray,
        features: np.ndarray,
        feature_names: list[str],
    ) -> list[MonotonicityViolation]:
        """Validate only time/duration features."""
        time_features = FEATURE_TYPES.get("time", [])
        violations = []

        for i, name in enumerate(feature_names):
            if name not in time_features:
                continue

            spec = self.feature_specs.get(name)
            expected = "increasing" if spec and spec.monotone_direction == "positive" else "decreasing"

            violation = self._validate_feature(
                feature_name=name,
                feature_values=features[:, i],
                predictions=predictions,
                expected_direction=expected,
            )
            if violation:
                violations.append(violation)

        return violations

    def validate_probability_features(
        self,
        predictions: np.ndarray,
        features: np.ndarray,
        feature_names: list[str],
    ) -> list[MonotonicityViolation]:
        """Validate probability-like features with bounds checking."""
        prob_features = FEATURE_TYPES.get("probability", [])
        violations = []

        for i, name in enumerate(feature_names):
            if name not in prob_features:
                continue

            feat_col = features[:, i]

            # Check bounds (0-1 or 0-100)
            is_percentage = np.nanmax(feat_col) > 1.0
            upper_bound = 100.0 if is_percentage else 1.0

            out_of_bounds = ((feat_col < 0) | (feat_col > upper_bound)).sum()
            if out_of_bounds > 0:
                logger.warning("Probability feature %s has %d out-of-bounds values", name, out_of_bounds)

            # Validate monotonicity
            spec = self.feature_specs.get(name)
            if spec and spec.monotone_direction != "none":
                expected = "increasing" if spec.monotone_direction == "positive" else "decreasing"

                violation = self._validate_feature(
                    feature_name=name,
                    feature_values=feat_col,
                    predictions=predictions,
                    expected_direction=expected,
                )
                if violation:
                    violations.append(violation)

        return violations


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DRIFT-AWARE RISK MULTIPLIER
# ═══════════════════════════════════════════════════════════════════════════════


class DriftAwareRiskMultiplier:
    """
    Integrates with Cody's v1.1 drift engine to adjust risk scores
    based on detected drift.

    Higher drift = more uncertainty = higher risk multiplier (more conservative).
    """

    # Default configuration
    DEFAULT_CONFIG = {
        "base_multiplier": 1.0,
        "max_drift_adjustment": 0.5,  # Cap on drift adjustment
        "max_corridor_adjustment": 0.3,
        "drift_threshold_for_adjustment": 0.15,
        "high_drift_multiplier": 1.25,
        "critical_drift_multiplier": 1.5,
    }

    def __init__(self, config: dict[str, float] | None = None):
        """
        Initialize risk multiplier engine.

        Args:
            config: Override configuration parameters
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

    def compute_multiplier(
        self,
        drift_stats: dict[str, Any],
        corridor_stats: dict[str, Any] | None = None,
    ) -> DriftRiskMultiplier:
        """
        Compute risk multiplier based on drift statistics.

        Args:
            drift_stats: Global drift statistics (avg_delta, p95_delta, etc.)
            corridor_stats: Optional corridor-specific statistics

        Returns:
            Risk multiplier with explanation
        """
        base = self.config["base_multiplier"]

        # Drift adjustment
        p95_delta = drift_stats.get("p95_delta", 0)

        drift_adjustment = 0.0
        rationale_parts = []

        if p95_delta > self.config["drift_threshold_for_adjustment"]:
            # Scale adjustment based on P95 delta
            if p95_delta > 0.35:
                drift_adjustment = self.config["max_drift_adjustment"]
                rationale_parts.append(f"Critical drift (P95={p95_delta:.3f})")
            elif p95_delta > 0.25:
                drift_adjustment = self.config["max_drift_adjustment"] * 0.7
                rationale_parts.append(f"High drift (P95={p95_delta:.3f})")
            else:
                drift_adjustment = (p95_delta - self.config["drift_threshold_for_adjustment"]) * self.config["max_drift_adjustment"] / 0.20
                rationale_parts.append(f"Moderate drift (P95={p95_delta:.3f})")
        else:
            rationale_parts.append(f"Normal drift levels (P95={p95_delta:.3f})")

        # Corridor adjustment
        corridor_adjustment = 0.0
        if corridor_stats:
            corridor_drift_flag = corridor_stats.get("drift_flag", False)
            corridor_p95 = corridor_stats.get("p95_delta", 0)

            if corridor_drift_flag:
                corridor_adjustment = min(corridor_p95 * 0.5, self.config["max_corridor_adjustment"])
                rationale_parts.append(f"Corridor drift detected ({corridor_stats.get('corridor', 'unknown')})")

        # Final multiplier
        final_multiplier = base + drift_adjustment + corridor_adjustment

        # Confidence based on sample size and consistency
        event_count = drift_stats.get("event_count", 0)
        if event_count >= 100:
            confidence = 0.9
        elif event_count >= 50:
            confidence = 0.75
        elif event_count >= 20:
            confidence = 0.6
        else:
            confidence = 0.4

        return DriftRiskMultiplier(
            base_multiplier=base,
            drift_adjustment=drift_adjustment,
            corridor_adjustment=corridor_adjustment,
            final_multiplier=final_multiplier,
            confidence=confidence,
            rationale="; ".join(rationale_parts),
        )

    def apply_to_score(
        self,
        raw_score: float,
        drift_stats: dict[str, Any],
        corridor_stats: dict[str, Any] | None = None,
    ) -> tuple[float, DriftRiskMultiplier]:
        """
        Apply drift-aware multiplier to a raw risk score.

        Args:
            raw_score: Original model risk score (0-1)
            drift_stats: Drift statistics
            corridor_stats: Optional corridor statistics

        Returns:
            (adjusted_score, multiplier_info)
        """
        multiplier = self.compute_multiplier(drift_stats, corridor_stats)

        # Apply multiplier while keeping score in valid range
        # Use log-odds transformation for better behavior at extremes
        if 0 < raw_score < 1:
            log_odds = np.log(raw_score / (1 - raw_score))
            adjusted_log_odds = log_odds + (multiplier.final_multiplier - 1) * 2
            adjusted_score = 1 / (1 + np.exp(-adjusted_log_odds))
        else:
            adjusted_score = raw_score

        return float(adjusted_score), multiplier

    def get_tier_from_multiplier(self, multiplier: DriftRiskMultiplier) -> str:
        """Map multiplier to risk tier."""
        final = multiplier.final_multiplier

        if final >= self.config["critical_drift_multiplier"]:
            return "CRITICAL"
        elif final >= self.config["high_drift_multiplier"]:
            return "HIGH"
        elif final > self.config["base_multiplier"] + 0.1:
            return "ELEVATED"
        else:
            return "NORMAL"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DRIFT DIAGNOSTICS REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════


class DriftDiagnosticsReporter:
    """
    Generates comprehensive drift diagnostics reports.

    Produces ML Drift Report v0.2 as markdown documentation.
    """

    def __init__(
        self,
        attributor: DriftFeatureAttributor | None = None,
        validator: MonotonicityValidatorV2 | None = None,
        risk_multiplier: DriftAwareRiskMultiplier | None = None,
    ):
        """Initialize reporter with component engines."""
        self.attributor = attributor or DriftFeatureAttributor()
        self.validator = validator or MonotonicityValidatorV2()
        self.risk_multiplier = risk_multiplier or DriftAwareRiskMultiplier()

    def generate_report(
        self,
        drift_stats: dict[str, Any],
        feature_attributions: list[DriftFeatureAttribution],
        monotonicity_result: MonotonicityValidationResult | None = None,
        corridor_attributions: list[CorridorAttribution] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate comprehensive drift diagnostics report.

        Args:
            drift_stats: Overall drift statistics
            feature_attributions: Per-feature drift attribution
            monotonicity_result: Monotonicity validation results
            corridor_attributions: Per-corridor drift analysis
            metadata: Additional report metadata

        Returns:
            Markdown-formatted report
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata = metadata or {}

        md = f"""# ML Drift Diagnostics Report v0.2

**Generated:** {timestamp}
**Agent:** Maggie (GID-10) 🩷
**PAC:** MAGGIE-NEXT-A02
**Model Version:** {metadata.get("model_version", "Unknown")}

---

## Executive Summary

This report provides comprehensive drift analysis including:
- Feature attribution for model disagreement
- Monotonicity constraint validation
- Corridor-specific drift patterns
- Risk adjustment recommendations

---

## 1. Overall Drift Statistics

| Metric | Value |
|--------|-------|
| Average Delta | {drift_stats.get("avg_delta", 0):.4f} |
| P95 Delta | {drift_stats.get("p95_delta", 0):.4f} |
| Max Delta | {drift_stats.get("max_delta", 0):.4f} |
| Event Count | {drift_stats.get("event_count", 0):,} |
| Drift Flag | {"⚠️ YES" if drift_stats.get("drift_flag", False) else "✅ NO"} |

"""

        # Risk Multiplier Section
        multiplier = self.risk_multiplier.compute_multiplier(drift_stats)
        tier = self.risk_multiplier.get_tier_from_multiplier(multiplier)

        md += f"""### Risk Adjustment

| Parameter | Value |
|-----------|-------|
| Base Multiplier | {multiplier.base_multiplier:.2f} |
| Drift Adjustment | +{multiplier.drift_adjustment:.2f} |
| Final Multiplier | **{multiplier.final_multiplier:.2f}** |
| Risk Tier | **{tier}** |
| Confidence | {multiplier.confidence:.0%} |

**Rationale:** {multiplier.rationale}

---

## 2. Feature Attribution Analysis

Top features contributing to model drift:

| Rank | Feature | Base Importance | Drift Magnitude | Severity | Weighted Score |
|------|---------|-----------------|-----------------|----------|----------------|
"""

        for attr in feature_attributions[:10]:
            md += (
                f"| {attr.rank} | `{attr.feature_name}` | "
                f"{attr.base_importance:.3f} | {attr.drift_magnitude:.3f} | "
                f"{attr.drift_severity.value} | **{attr.drift_weighted_importance:.3f}** |\n"
            )

        md += "\n"

        # Monotonicity Section
        if monotonicity_result:
            status = "✅ PASS" if monotonicity_result.is_valid else "❌ FAIL"
            md += f"""---

## 3. Monotonicity Validation (v2)

**Status:** {status}
**Features Validated:** {monotonicity_result.validated_features}/{monotonicity_result.total_features}
**Violations:** {len(monotonicity_result.violations)}

"""
            if monotonicity_result.violations:
                md += "### Violations Detected\n\n"
                md += "| Feature | Type | Expected | Actual | Severity | Recommendation |\n"
                md += "|---------|------|----------|--------|----------|----------------|\n"

                for v in monotonicity_result.violations:
                    md += (
                        f"| `{v.feature_name}` | {v.feature_type} | "
                        f"{v.expected_direction} | {v.actual_direction} | "
                        f"{v.violation_score:.2f} | {v.recommendation[:50]}... |\n"
                    )
            else:
                md += "✓ All monotonicity constraints satisfied.\n"

        # Corridor Section
        if corridor_attributions:
            md += """---

## 4. Corridor-Specific Analysis

"""
            drifting = [c for c in corridor_attributions if c.drift_flag]
            stable = [c for c in corridor_attributions if not c.drift_flag]

            md += f"**Drifting Corridors:** {len(drifting)}  \n"
            md += f"**Stable Corridors:** {len(stable)}  \n\n"

            if drifting:
                md += "### Drifting Corridors\n\n"
                md += "| Corridor | Events | Avg Δ | P95 Δ | Top Drift Feature |\n"
                md += "|----------|--------|-------|-------|------------------|\n"

                for c in drifting:
                    top_feat = c.top_drift_features[0].feature_name if c.top_drift_features else "N/A"
                    md += f"| {c.corridor} | {c.event_count:,} | " f"{c.avg_delta:.3f} | {c.p95_delta:.3f} | `{top_feat}` |\n"

        # Recommendations
        md += """---

## 5. Recommendations

"""
        recommendations = self._generate_recommendations(drift_stats, feature_attributions, monotonicity_result, corridor_attributions)

        for i, rec in enumerate(recommendations, 1):
            md += f"{i}. {rec}\n"

        # Footer
        md += f"""
---

## Appendix: Methodology

### SHAP Baseline
- Background samples: {SHAP_BASELINE_CONFIG["background_samples"]}
- Attribution method: Coefficient-based linear approximation

### Monotonicity Rules
- Distance features: Must increase risk with distance
- Time features: Duration increases correlate with risk
- Probability features: Bounded [0,1], direction per specification
- Count features: Non-negative integers, risk increases with count

### Drift Thresholds
"""
        for severity, threshold in DRIFT_SEVERITY_THRESHOLDS.items():
            md += f"- {severity.upper()}: ≤{threshold:.0%}\n"

        md += """
---

🩷 **MAGGIE — GID-10 — MACHINE LEARNING LEAD**
*Signals before sophistication.*
🩷🩷🩷 END OF REPORT 🩷🩷🩷
"""

        return md

    def _generate_recommendations(
        self,
        drift_stats: dict[str, Any],
        feature_attributions: list[DriftFeatureAttribution],
        monotonicity_result: MonotonicityValidationResult | None,
        corridor_attributions: list[CorridorAttribution] | None,
    ) -> list[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Drift-based recommendations
        p95_delta = drift_stats.get("p95_delta", 0)
        if p95_delta > 0.35:
            recommendations.append(
                "🔴 **CRITICAL:** P95 delta exceeds 0.35. Initiate immediate model review and "
                "consider halting automated decisions pending investigation."
            )
        elif p95_delta > 0.25:
            recommendations.append("🟠 **HIGH:** P95 delta exceeds drift threshold. Schedule model recalibration " "within 7 days.")
        elif p95_delta > 0.15:
            recommendations.append(
                "🟡 **MODERATE:** Elevated drift detected. Monitor closely and prepare " "recalibration if trend continues."
            )
        else:
            recommendations.append("🟢 **STABLE:** Drift levels within acceptable bounds. Continue normal monitoring.")

        # Feature-based recommendations
        high_drift_features = [a for a in feature_attributions if a.drift_severity in (DriftSeverity.SEVERE, DriftSeverity.CRITICAL)]
        if high_drift_features:
            feature_list = ", ".join(f.feature_name for f in high_drift_features[:3])
            recommendations.append(
                f"Investigate high-drift features: {feature_list}. Consider feature " "re-engineering or adding drift-robust alternatives."
            )

        # Monotonicity recommendations
        if monotonicity_result and not monotonicity_result.is_valid:
            recommendations.append(
                f"Address {len(monotonicity_result.violations)} monotonicity violations. "
                "Review feature transforms and consider monotonic model constraints."
            )

        # Corridor recommendations
        if corridor_attributions:
            drifting = [c for c in corridor_attributions if c.drift_flag]
            if len(drifting) > 3:
                recommendations.append(
                    f"Multiple corridors ({len(drifting)}) show drift. Consider " "corridor-stratified modeling or regional recalibration."
                )
            elif drifting:
                corridors = ", ".join(c.corridor for c in drifting[:3])
                recommendations.append(f"Monitor drifting corridors: {corridors}. May require corridor-specific " "threshold adjustments.")

        return recommendations

    def save_report(
        self,
        report: str,
        output_path: str | Path | None = None,
    ) -> Path:
        """
        Save report to file.

        Args:
            report: Generated markdown report
            output_path: Target path (defaults to docs/ml/DRIFT_DIAGNOSTICS_v02.md)

        Returns:
            Path to saved report
        """
        if output_path is None:
            output_path = Path("docs/ml/DRIFT_DIAGNOSTICS_v02.md")
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

        logger.info("Saved drift diagnostics report to %s", output_path)
        return output_path


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def run_drift_diagnostics(
    shadow_events: Sequence[dict[str, Any]],
    reference_data: Sequence[dict[str, Any]] | None = None,
    model_predictions: np.ndarray | None = None,
    feature_matrix: np.ndarray | None = None,
    feature_names: list[str] | None = None,
    save_report: bool = True,
    output_path: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Run complete drift diagnostics pipeline.

    Args:
        shadow_events: Recent shadow mode events
        reference_data: Historical reference data
        model_predictions: Optional model predictions for monotonicity check
        feature_matrix: Optional feature matrix for monotonicity check
        feature_names: Feature column names
        save_report: Whether to save report to file
        output_path: Custom output path

    Returns:
        (markdown_report, summary_dict)
    """
    print("\n" + "=" * 60)
    print("🩷 MAGGIE DRIFT DIAGNOSTICS v0.2")
    print("=" * 60)

    # Initialize components
    attributor = DriftFeatureAttributor()
    validator = MonotonicityValidatorV2()
    risk_multiplier = DriftAwareRiskMultiplier()
    reporter = DriftDiagnosticsReporter(attributor, validator, risk_multiplier)

    # Compute baseline from reference or shadow events
    print("\n[1/5] Computing SHAP baseline...")
    baseline_data = reference_data or shadow_events
    attributor.compute_shap_baseline(baseline_data)

    # Compute drift statistics
    print("\n[2/5] Computing drift statistics...")
    deltas = []
    for event in shadow_events:
        delta = abs(event.get("dummy_score", 0) - event.get("real_score", 0))
        deltas.append(delta)

    deltas_np = np.array(deltas) if deltas else np.array([0])
    drift_stats = {
        "avg_delta": float(deltas_np.mean()),
        "p95_delta": float(np.percentile(deltas_np, 95)) if len(deltas_np) > 0 else 0,
        "max_delta": float(deltas_np.max()) if len(deltas_np) > 0 else 0,
        "event_count": len(shadow_events),
        "drift_flag": float(np.percentile(deltas_np, 95)) > 0.25 if len(deltas_np) > 0 else False,
    }

    # Compute feature attribution
    print("\n[3/5] Computing feature attribution...")
    from app.ml.feature_forensics import compute_feature_statistics

    current_stats = compute_feature_statistics(shadow_events)
    ref_stats = compute_feature_statistics(reference_data) if reference_data else current_stats
    feature_attributions = attributor.compute_drift_weighted_importance(current_stats, ref_stats)

    # Validate monotonicity (if data provided)
    print("\n[4/5] Validating monotonicity...")
    monotonicity_result = None
    if model_predictions is not None and feature_matrix is not None and feature_names:
        monotonicity_result = validator.validate_all(model_predictions, feature_matrix, feature_names)

    # Compute corridor attribution
    print("\n[5/5] Computing corridor attribution...")
    corridor_events: dict[str, list] = defaultdict(list)
    for event in shadow_events:
        corridor = event.get("corridor", "unknown")
        corridor_events[corridor].append(event)

    corridor_attributions = []
    for corridor, events in corridor_events.items():
        attr = attributor.compute_corridor_attribution(events, corridor, reference_data)
        corridor_attributions.append(attr)

    # Sort by P95 delta
    corridor_attributions.sort(key=lambda c: c.p95_delta, reverse=True)

    # Generate report
    print("\n[FINAL] Generating report...")
    report = reporter.generate_report(
        drift_stats=drift_stats,
        feature_attributions=feature_attributions,
        monotonicity_result=monotonicity_result,
        corridor_attributions=corridor_attributions,
    )

    # Save if requested
    if save_report:
        saved_path = reporter.save_report(report, output_path)
        print(f"\n✓ Report saved to {saved_path}")

    # Summary
    summary = {
        "drift_stats": drift_stats,
        "top_drift_features": [a.to_dict() for a in feature_attributions[:5]],
        "monotonicity_valid": monotonicity_result.is_valid if monotonicity_result else None,
        "drifting_corridors": [c.corridor for c in corridor_attributions if c.drift_flag],
        "risk_tier": risk_multiplier.get_tier_from_multiplier(risk_multiplier.compute_multiplier(drift_stats)),
    }

    print("\n" + "=" * 60)
    print("✓ DRIFT DIAGNOSTICS COMPLETE")
    print("=" * 60)

    return report, summary


# Export public API
__all__ = [
    "DriftSeverity",
    "SHAPAttribution",
    "DriftFeatureAttribution",
    "CorridorAttribution",
    "MonotonicityViolation",
    "MonotonicityValidationResult",
    "DriftRiskMultiplier",
    "DriftFeatureAttributor",
    "MonotonicityValidatorV2",
    "DriftAwareRiskMultiplier",
    "DriftDiagnosticsReporter",
    "run_drift_diagnostics",
    "DRIFT_SEVERITY_THRESHOLDS",
    "FEATURE_TYPES",
]
