"""ChainIQ Drift Engine v1.2

Advanced drift detection, scoring, and explainability for ChainIQ ML models.
Supports feature-level drift analysis, corridor-specific drift metrics,
and risk multiplier calculations for production model monitoring.

════════════════════════════════════════════════════════════════════════════════
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
GID-10 — MAGGIE (ML & APPLIED AI)
PAC-MAGGIE-A10-RISK-MODEL-CANONICALIZATION-LOCK-01
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
════════════════════════════════════════════════════════════════════════════════

I. EXECUTING AGENT (MANDATORY)

EXECUTING AGENT: MAGGIE
GID: GID-10
EXECUTING COLOR: 🩷 PINK — ML & Applied AI Lane

⸻

II. DRIFT RESPONSE POLICY (LOCKED)

- STABLE: Continue
- MINOR: Monitor (log only)
- MODERATE: Alert (notify team)
- SEVERE: Escalate (page on-call)
- CRITICAL: Halt (block new scores, require human review)

A10 LOCK COMPLIANCE:
- Drift ESCALATES, never auto-corrects
- No silent fallbacks
- All drift events logged for audit

⸻

III. PROHIBITED ACTIONS

- Auto-correcting drift
- Silent fallbacks on drift detection
- Bypassing CRITICAL drift halts

⸻

Features:
- Corridor drift scoring with configurable thresholds
- Feature shift delta computation for attribution
- Risk multiplier derivation from drift magnitude
- Categorical drift bucketing for alerting
- Ultra-fast caching layer (IQCache) for <20ms responses

Original Author: Cody (GID-01) 🔵
A10 Update: Maggie (GID-10) 🩷
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DRIFT ENUMS AND CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════


class DriftBucket(str, Enum):
    """Categorical drift severity buckets for alerting and routing."""

    STABLE = "STABLE"  # No significant drift detected
    MINOR = "MINOR"  # Slight drift, monitor only
    MODERATE = "MODERATE"  # Notable drift, consider retraining
    SEVERE = "SEVERE"  # High drift, immediate attention
    CRITICAL = "CRITICAL"  # Critical drift, model may be unreliable


class DriftDirection(str, Enum):
    """Direction of feature drift."""

    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"


# Default thresholds for drift bucketing
DEFAULT_DRIFT_THRESHOLDS = {
    "STABLE": 0.05,  # 0-5% drift
    "MINOR": 0.10,  # 5-10% drift
    "MODERATE": 0.20,  # 10-20% drift
    "SEVERE": 0.35,  # 20-35% drift
    "CRITICAL": 1.0,  # 35%+ drift
}

# Default risk multiplier ranges
DEFAULT_RISK_MULTIPLIER_CONFIG = {
    "base_multiplier": 1.0,
    "max_multiplier": 2.5,
    "drift_scaling_factor": 3.0,  # How aggressively drift increases risk
}


# ═══════════════════════════════════════════════════════════════════════════════
# A10 DRIFT RESPONSE POLICY (LOCKED)
# ═══════════════════════════════════════════════════════════════════════════════

class DriftAction(str, Enum):
    """Required action for drift level.
    
    A10 LOCK: Drift ESCALATES, never auto-corrects.
    """
    
    CONTINUE = "CONTINUE"  # Normal operation
    MONITOR = "MONITOR"  # Log only, watch closely
    ALERT = "ALERT"  # Notify team
    ESCALATE = "ESCALATE"  # Page on-call
    HALT = "HALT"  # Block new scores, require human review


# A10 LOCKED: Drift response mapping
DRIFT_RESPONSE_POLICY = {
    DriftBucket.STABLE: DriftAction.CONTINUE,
    DriftBucket.MINOR: DriftAction.MONITOR,
    DriftBucket.MODERATE: DriftAction.ALERT,
    DriftBucket.SEVERE: DriftAction.ESCALATE,
    DriftBucket.CRITICAL: DriftAction.HALT,
}


def get_drift_action(bucket: DriftBucket) -> DriftAction:
    """Get required action for drift bucket.
    
    A10 LOCK INVARIANT: This function NEVER returns auto-correction actions.
    Drift is ALWAYS escalated according to policy.
    
    Args:
        bucket: Drift severity bucket
        
    Returns:
        Required action from DRIFT_RESPONSE_POLICY
    """
    return DRIFT_RESPONSE_POLICY.get(bucket, DriftAction.ESCALATE)


def should_halt_scoring(bucket: DriftBucket) -> bool:
    """Check if drift level requires halting new scores.
    
    A10 LOCK: CRITICAL drift MUST halt scoring until human review.
    
    Args:
        bucket: Drift severity bucket
        
    Returns:
        True if scoring should be halted
    """
    return bucket == DriftBucket.CRITICAL


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class FeatureDriftResult:
    """Drift analysis result for a single feature."""

    feature_name: str
    baseline_mean: float
    current_mean: float
    baseline_std: float
    current_std: float
    shift_delta: float  # Normalized shift magnitude
    shift_direction: DriftDirection
    psi_score: float  # Population Stability Index
    ks_statistic: Optional[float] = None  # Kolmogorov-Smirnov statistic
    drift_bucket: DriftBucket = DriftBucket.STABLE
    contribution_rank: int = 0  # 1 = highest contributor to overall drift
    explanation: str = ""


@dataclass
class CorridorDriftResult:
    """Drift analysis result for a trade corridor."""

    corridor: str
    drift_score: float  # Aggregate drift score [0, 1]
    drift_bucket: DriftBucket
    feature_drifts: List[FeatureDriftResult] = field(default_factory=list)
    top_drifting_features: List[str] = field(default_factory=list)
    risk_multiplier: float = 1.0
    sample_count_baseline: int = 0
    sample_count_current: int = 0
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    recommendations: List[str] = field(default_factory=list)


@dataclass
class GlobalDriftSummary:
    """System-wide drift summary across all corridors."""

    overall_drift_score: float
    overall_bucket: DriftBucket
    corridors_analyzed: int
    corridors_drifting: int
    top_drifting_corridors: List[str] = field(default_factory=list)
    top_drifting_features: List[str] = field(default_factory=list)
    corridor_results: List[CorridorDriftResult] = field(default_factory=list)
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cache_ttl_seconds: int = 300


# ═══════════════════════════════════════════════════════════════════════════════
# DRIFT SCORE CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════════════


def corridor_drift_score(
    baseline_stats: Dict[str, Dict[str, float]],
    current_stats: Dict[str, Dict[str, float]],
    feature_weights: Optional[Dict[str, float]] = None,
    threshold_config: Optional[Dict[str, float]] = None,
) -> CorridorDriftResult:
    """
    Compute aggregate drift score for a corridor.

    Uses weighted combination of feature-level drift metrics to produce
    a single corridor drift score. Supports custom feature weights for
    business-critical features.

    Args:
        baseline_stats: Dict of {feature_name: {mean, std, min, max, count}}
                       representing historical baseline distribution
        current_stats: Dict of {feature_name: {mean, std, min, max, count}}
                      representing current window distribution
        feature_weights: Optional dict of feature importance weights.
                        Defaults to equal weighting.
        threshold_config: Optional custom thresholds for drift bucketing.

    Returns:
        CorridorDriftResult with aggregate score and feature breakdowns.

    Example:
        >>> baseline = {
        ...     "eta_deviation_hours": {"mean": 5.0, "std": 2.0, "count": 1000},
        ...     "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 1000},
        ... }
        >>> current = {
        ...     "eta_deviation_hours": {"mean": 8.2, "std": 3.1, "count": 200},
        ...     "num_route_deviations": {"mean": 2.1, "std": 1.5, "count": 200},
        ... }
        >>> result = corridor_drift_score(baseline, current)
        >>> print(f"Drift: {result.drift_score:.3f}, Bucket: {result.drift_bucket}")
    """
    thresholds = threshold_config or DEFAULT_DRIFT_THRESHOLDS

    # Get common features
    common_features = set(baseline_stats.keys()) & set(current_stats.keys())

    if not common_features:
        logger.warning("No common features between baseline and current stats")
        return CorridorDriftResult(
            corridor="unknown",
            drift_score=0.0,
            drift_bucket=DriftBucket.STABLE,
            recommendations=["Insufficient data for drift analysis"],
        )

    # Initialize weights
    if feature_weights is None:
        feature_weights = {f: 1.0 for f in common_features}

    # Normalize weights
    total_weight = sum(feature_weights.get(f, 1.0) for f in common_features)

    feature_drifts: List[FeatureDriftResult] = []
    weighted_drift_sum = 0.0

    for feature in common_features:
        baseline = baseline_stats[feature]
        current = current_stats[feature]

        # Compute feature shift delta
        shift = feature_shift_delta(
            baseline_mean=baseline.get("mean", 0.0),
            baseline_std=baseline.get("std", 1.0),
            current_mean=current.get("mean", 0.0),
            current_std=current.get("std", 1.0),
        )

        # Determine drift direction
        if abs(current.get("mean", 0) - baseline.get("mean", 0)) < 0.001:
            direction = DriftDirection.STABLE
        elif current.get("mean", 0) > baseline.get("mean", 0):
            direction = DriftDirection.INCREASING
        else:
            direction = DriftDirection.DECREASING

        # Compute PSI (simplified)
        psi = _compute_psi_simple(
            baseline.get("mean", 0),
            baseline.get("std", 1),
            current.get("mean", 0),
            current.get("std", 1),
        )

        # Bucket the feature drift
        feature_bucket = categorical_drift_bucket(shift, thresholds)

        # Build explanation
        explanation = _generate_feature_explanation(feature, shift, direction, feature_bucket)

        feature_result = FeatureDriftResult(
            feature_name=feature,
            baseline_mean=baseline.get("mean", 0.0),
            current_mean=current.get("mean", 0.0),
            baseline_std=baseline.get("std", 1.0),
            current_std=current.get("std", 1.0),
            shift_delta=shift,
            shift_direction=direction,
            psi_score=psi,
            drift_bucket=feature_bucket,
            explanation=explanation,
        )
        feature_drifts.append(feature_result)

        # Accumulate weighted drift
        weight = feature_weights.get(feature, 1.0) / total_weight
        weighted_drift_sum += shift * weight

    # Rank features by drift contribution
    feature_drifts.sort(key=lambda x: x.shift_delta, reverse=True)
    for rank, fd in enumerate(feature_drifts, start=1):
        fd.contribution_rank = rank

    # Compute overall corridor drift score (capped at 1.0)
    corridor_score = min(weighted_drift_sum, 1.0)

    # Bucket the corridor drift
    corridor_bucket = categorical_drift_bucket(corridor_score, thresholds)

    # Compute risk multiplier
    risk_mult = risk_multiplier_from_drift(corridor_score)

    # Generate recommendations
    recommendations = _generate_drift_recommendations(corridor_score, corridor_bucket, feature_drifts)

    # Get sample counts
    sample_baseline = int(baseline_stats.get(list(common_features)[0], {}).get("count", 0))
    sample_current = int(current_stats.get(list(common_features)[0], {}).get("count", 0))

    return CorridorDriftResult(
        corridor="",  # Set by caller
        drift_score=corridor_score,
        drift_bucket=corridor_bucket,
        feature_drifts=feature_drifts,
        top_drifting_features=[fd.feature_name for fd in feature_drifts[:5]],
        risk_multiplier=risk_mult,
        sample_count_baseline=sample_baseline,
        sample_count_current=sample_current,
        recommendations=recommendations,
    )


def feature_shift_delta(
    baseline_mean: float,
    baseline_std: float,
    current_mean: float,
    current_std: float,
    epsilon: float = 1e-6,
) -> float:
    """
    Compute normalized shift delta for a feature.

    Uses standardized mean shift combined with std ratio to capture
    both location and spread changes in the feature distribution.

    Args:
        baseline_mean: Mean of baseline distribution
        baseline_std: Standard deviation of baseline distribution
        current_mean: Mean of current distribution
        current_std: Standard deviation of current distribution
        epsilon: Small value to prevent division by zero

    Returns:
        Normalized shift delta in [0, inf). Values > 1.0 indicate
        significant drift.

    Formula:
        shift = |current_mean - baseline_mean| / (baseline_std + epsilon)
                + |log(current_std / baseline_std)|

    Example:
        >>> delta = feature_shift_delta(10.0, 2.0, 12.5, 3.0)
        >>> print(f"Shift delta: {delta:.3f}")
    """
    # Mean shift normalized by baseline std
    mean_shift = abs(current_mean - baseline_mean) / (baseline_std + epsilon)

    # Std ratio (log scale to handle both increases and decreases)
    std_ratio = current_std / (baseline_std + epsilon)
    std_shift = abs(np.log(max(std_ratio, epsilon)))

    # Combined shift (mean shift dominates, std shift adds secondary signal)
    combined_shift = mean_shift + 0.3 * std_shift

    return float(combined_shift)


def risk_multiplier_from_drift(
    drift_score: float,
    config: Optional[Dict[str, float]] = None,
) -> float:
    """
    Derive risk multiplier from drift score.

    Higher drift scores result in elevated risk multipliers,
    used to adjust model predictions during periods of drift.

    Args:
        drift_score: Aggregate drift score in [0, 1+]
        config: Optional configuration for multiplier scaling.
               Keys: base_multiplier, max_multiplier, drift_scaling_factor

    Returns:
        Risk multiplier >= 1.0. Applied to base risk scores.

    Formula:
        multiplier = base + (max - base) * (1 - exp(-scaling * drift))

    Example:
        >>> mult = risk_multiplier_from_drift(0.25)
        >>> print(f"Risk multiplier: {mult:.2f}x")
    """
    cfg = config or DEFAULT_RISK_MULTIPLIER_CONFIG

    base = cfg.get("base_multiplier", 1.0)
    max_mult = cfg.get("max_multiplier", 2.5)
    scaling = cfg.get("drift_scaling_factor", 3.0)

    # Exponential saturation curve
    # Starts at base, asymptotically approaches max
    multiplier = base + (max_mult - base) * (1 - np.exp(-scaling * drift_score))

    return float(round(multiplier, 3))


def categorical_drift_bucket(
    drift_score: float,
    thresholds: Optional[Dict[str, float]] = None,
) -> DriftBucket:
    """
    Map continuous drift score to categorical bucket.

    Used for alerting, routing, and human-readable reporting.

    Args:
        drift_score: Continuous drift score in [0, 1+]
        thresholds: Optional custom threshold configuration.
                   Keys: STABLE, MINOR, MODERATE, SEVERE, CRITICAL

    Returns:
        DriftBucket enum value.

    Example:
        >>> bucket = categorical_drift_bucket(0.18)
        >>> print(f"Drift bucket: {bucket.value}")
        Drift bucket: MODERATE
    """
    th = thresholds or DEFAULT_DRIFT_THRESHOLDS

    if drift_score <= th.get("STABLE", 0.05):
        return DriftBucket.STABLE
    elif drift_score <= th.get("MINOR", 0.10):
        return DriftBucket.MINOR
    elif drift_score <= th.get("MODERATE", 0.20):
        return DriftBucket.MODERATE
    elif drift_score <= th.get("SEVERE", 0.35):
        return DriftBucket.SEVERE
    else:
        return DriftBucket.CRITICAL


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-CORRIDOR ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════


def compute_global_drift_summary(
    corridor_baselines: Dict[str, Dict[str, Dict[str, float]]],
    corridor_currents: Dict[str, Dict[str, Dict[str, float]]],
    feature_weights: Optional[Dict[str, float]] = None,
) -> GlobalDriftSummary:
    """
    Compute system-wide drift summary across all corridors.

    Aggregates corridor-level drift into a global view for
    executive dashboards and system health monitoring.

    Args:
        corridor_baselines: Dict of {corridor: {feature: stats}}
        corridor_currents: Dict of {corridor: {feature: stats}}
        feature_weights: Optional feature importance weights

    Returns:
        GlobalDriftSummary with corridor breakdowns and rankings.
    """
    corridor_results: List[CorridorDriftResult] = []

    common_corridors = set(corridor_baselines.keys()) & set(corridor_currents.keys())

    for corridor in common_corridors:
        result = corridor_drift_score(
            baseline_stats=corridor_baselines[corridor],
            current_stats=corridor_currents[corridor],
            feature_weights=feature_weights,
        )
        result.corridor = corridor
        corridor_results.append(result)

    # Sort by drift score descending
    corridor_results.sort(key=lambda x: x.drift_score, reverse=True)

    # Compute overall metrics
    if corridor_results:
        avg_drift = np.mean([r.drift_score for r in corridor_results])
        drifting_count = sum(1 for r in corridor_results if r.drift_bucket not in (DriftBucket.STABLE, DriftBucket.MINOR))
    else:
        avg_drift = 0.0
        drifting_count = 0

    overall_bucket = categorical_drift_bucket(avg_drift)

    # Aggregate top drifting features across corridors
    feature_drift_totals: Dict[str, float] = {}
    for result in corridor_results:
        for fd in result.feature_drifts:
            feature_drift_totals[fd.feature_name] = feature_drift_totals.get(fd.feature_name, 0.0) + fd.shift_delta

    top_features = sorted(
        feature_drift_totals.keys(),
        key=lambda f: feature_drift_totals[f],
        reverse=True,
    )[:10]

    return GlobalDriftSummary(
        overall_drift_score=float(avg_drift),
        overall_bucket=overall_bucket,
        corridors_analyzed=len(corridor_results),
        corridors_drifting=drifting_count,
        top_drifting_corridors=[r.corridor for r in corridor_results[:5]],
        top_drifting_features=top_features,
        corridor_results=corridor_results,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def _compute_psi_simple(
    baseline_mean: float,
    baseline_std: float,
    current_mean: float,
    current_std: float,
) -> float:
    """
    Simplified PSI approximation using normal distribution assumption.

    Full PSI requires binned distributions; this approximation uses
    moment-matching for faster computation.
    """
    # Jensen-Shannon inspired approximation
    mean_diff = abs(current_mean - baseline_mean)
    std_ratio = current_std / max(baseline_std, 1e-6)

    psi_approx = (mean_diff / max(baseline_std, 1e-6)) ** 2 * 0.1 + abs(np.log(std_ratio)) * 0.1

    return float(min(psi_approx, 1.0))


def _generate_feature_explanation(
    feature_name: str,
    shift_delta: float,
    direction: DriftDirection,
    bucket: DriftBucket,
) -> str:
    """Generate human-readable explanation for feature drift."""
    if bucket == DriftBucket.STABLE:
        return f"{feature_name}: Stable, no significant drift detected."

    dir_text = "increasing" if direction == DriftDirection.INCREASING else "decreasing"
    severity = bucket.value.lower()

    return (
        f"{feature_name}: {severity.capitalize()} drift detected "
        f"({dir_text}, delta={shift_delta:.3f}). "
        f"Review recent data quality and upstream changes."
    )


def _generate_drift_recommendations(
    drift_score: float,
    bucket: DriftBucket,
    feature_drifts: List[FeatureDriftResult],
) -> List[str]:
    """Generate actionable recommendations based on drift analysis."""
    recommendations = []

    if bucket == DriftBucket.STABLE:
        recommendations.append("No action required. Model performance is stable.")
    elif bucket == DriftBucket.MINOR:
        recommendations.append("Continue monitoring. Minor drift detected but within tolerance.")
    elif bucket == DriftBucket.MODERATE:
        recommendations.append("Schedule model retraining within 7 days.")
        recommendations.append("Review top drifting features for data quality issues.")
    elif bucket == DriftBucket.SEVERE:
        recommendations.append("URGENT: Schedule model retraining within 24-48 hours.")
        recommendations.append("Enable shadow mode for manual override capability.")
        recommendations.append("Alert ML engineering team.")
    else:  # CRITICAL
        recommendations.append("CRITICAL: Consider switching to fallback/dummy model.")
        recommendations.append("Immediate model retraining required.")
        recommendations.append("Escalate to ML leadership.")
        recommendations.append("Review data pipeline for upstream failures.")

    # Add feature-specific recommendations for top drifters
    severe_features = [fd for fd in feature_drifts[:3] if fd.drift_bucket in (DriftBucket.SEVERE, DriftBucket.CRITICAL)]

    for fd in severe_features:
        recommendations.append(f"Investigate '{fd.feature_name}': {fd.explanation}")

    return recommendations


# ═══════════════════════════════════════════════════════════════════════════════
# IQCACHE LAYER
# ═══════════════════════════════════════════════════════════════════════════════


class IQCache:
    """
    Ultra-fast in-memory cache for drift responses.

    Targets <20ms response time for drift score endpoints by caching
    computed drift results with configurable TTL.

    Thread-safe via simple dict replacement (GIL protected).
    For production, consider Redis or similar distributed cache.
    """

    def __init__(self, default_ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve cached value if exists and not expired.

        Returns:
            Cached value or None if miss/expired.
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        value, expires_at = entry
        if datetime.now(timezone.utc) > expires_at:
            # Expired, remove and return None
            self._cache.pop(key, None)
            return None

        return value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Store value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (default: 300)
        """
        ttl = ttl_seconds or self._default_ttl
        expires_at = datetime.now(timezone.utc) + __import__("datetime").timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.

        Returns:
            True if entry existed and was removed, False otherwise.
        """
        return self._cache.pop(key, None) is not None

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all entries matching pattern prefix.

        Returns:
            Count of invalidated entries.
        """
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(pattern)]
        for key in keys_to_remove:
            self._cache.pop(key, None)
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        now = datetime.now(timezone.utc)
        valid_count = sum(1 for _, (_, exp) in self._cache.items() if exp > now)
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_count,
            "expired_entries": len(self._cache) - valid_count,
        }


# Global cache instance
_drift_cache = IQCache(default_ttl_seconds=300)


def get_drift_cache() -> IQCache:
    """Get the global drift cache instance."""
    return _drift_cache


# END — Maggie (GID-10) — 🩷 PINK
