"""
ChainIQ Drift Engine v1.2 - Fusion Layer

Unified scoring layer combining:
- Drift magnitude metrics (from drift_engine.py)
- Shadow mode real-vs-dummy deltas (from api_shadow.py)
- Corridor historical stability index

ALEX-compliant: p95 latency < 45ms via:
- LRU caching with 60s TTL
- Pre-computed corridor indices
- Vectorized numpy operations
- No model loading in request path

Author: Cody (GID-01) 🔵
PAC: PAC-CODY-NEXT-035
Version: 1.2.0
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Fusion scoring weights (must sum to 1.0)
FUSION_WEIGHTS = {
    "drift_magnitude": 0.40,  # Weight for drift engine score
    "shadow_delta": 0.35,  # Weight for shadow mode delta
    "stability_index": 0.25,  # Weight for corridor stability
}

# Latency budget (ALEX requirement)
MAX_LATENCY_MS = 45

# Cache configuration
CACHE_TTL_SECONDS = 60
CACHE_MAX_SIZE = 256

# Stability index thresholds
STABILITY_THRESHOLDS = {
    "highly_stable": 0.05,  # < 5% historical variance
    "stable": 0.10,  # 5-10% variance
    "moderate": 0.20,  # 10-20% variance
    "volatile": 0.35,  # 20-35% variance
    "highly_volatile": 1.0,  # > 35% variance
}

# Fusion score severity thresholds
FUSION_SEVERITY_THRESHOLDS = {
    "healthy": 0.15,
    "elevated": 0.30,
    "warning": 0.50,
    "critical": 0.75,
    "severe": 1.0,
}

# Feature importance defaults (for attribution)
DEFAULT_FEATURE_WEIGHTS = {
    "eta_deviation_hours": 0.15,
    "num_route_deviations": 0.12,
    "delay_flag": 0.10,
    "total_dwell_hours": 0.10,
    "shipper_on_time_pct_90d": 0.10,
    "carrier_on_time_pct_90d": 0.10,
    "missing_required_docs": 0.08,
    "max_custody_gap_hours": 0.08,
    "lane_sentiment_score": 0.07,
    "planned_transit_hours": 0.05,
    "temp_out_of_range_pct": 0.05,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class FusionSeverity(str, Enum):
    """Fusion score severity classification."""

    HEALTHY = "HEALTHY"
    ELEVATED = "ELEVATED"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    SEVERE = "SEVERE"


class StabilityClass(str, Enum):
    """Corridor stability classification."""

    HIGHLY_STABLE = "HIGHLY_STABLE"
    STABLE = "STABLE"
    MODERATE = "MODERATE"
    VOLATILE = "VOLATILE"
    HIGHLY_VOLATILE = "HIGHLY_VOLATILE"


class TrendDirection(str, Enum):
    """Score trend direction."""

    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DEGRADING = "DEGRADING"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DriftComponent:
    """Drift magnitude component of fusion score."""

    score: float  # Normalized drift score [0, 1]
    bucket: str  # STABLE/MINOR/MODERATE/SEVERE/CRITICAL
    top_features: List[str]  # Top drifting features
    feature_deltas: Dict[str, float]  # Feature-level drift magnitudes
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ShadowComponent:
    """Shadow mode delta component of fusion score."""

    mean_delta: float  # Mean real-dummy delta
    p95_delta: float  # 95th percentile delta
    max_delta: float  # Maximum delta observed
    event_count: int  # Number of shadow events
    drift_flag: bool  # True if p95 > threshold
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StabilityComponent:
    """Corridor stability component of fusion score."""

    stability_index: float  # Historical stability [0, 1] (lower = more stable)
    stability_class: StabilityClass
    variance_30d: float  # 30-day variance
    variance_7d: float  # 7-day variance
    trend: TrendDirection  # Recent trend
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FeatureAttribution:
    """Attribution of fusion score to individual features."""

    feature_name: str
    contribution_score: float  # Absolute contribution to fusion score
    contribution_pct: float  # Percentage of total score
    drift_delta: float  # Feature drift magnitude
    shadow_delta: float  # Feature shadow delta (if available)
    stability_delta: float  # Feature stability delta
    rank: int  # Rank by contribution (1 = highest)
    direction: Literal["positive", "negative", "neutral"]


@dataclass
class FusionScoreResult:
    """
    Complete fusion score result.

    Combines drift, shadow, and stability into unified scoring.
    """

    # Core scores
    fusion_score: float  # Combined score [0, 1]
    severity: FusionSeverity
    confidence: float  # Score confidence [0, 1]

    # Component scores
    drift_component: DriftComponent
    shadow_component: ShadowComponent
    stability_component: StabilityComponent

    # Attribution
    top_attributions: List[FeatureAttribution]

    # Metadata
    corridor: Optional[str] = None
    lookback_hours: int = 24
    model_version: str = "v1.2.0"
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = 0.0

    # Recommendations
    recommendations: List[str] = field(default_factory=list)


@dataclass
class CorridorFusionSummary:
    """Summary of fusion scores across corridors."""

    total_corridors: int
    healthy_count: int
    elevated_count: int
    warning_count: int
    critical_count: int
    severe_count: int
    avg_fusion_score: float
    max_fusion_score: float
    top_corridors: List[Tuple[str, float]]  # (corridor, score) pairs
    corridor_results: List[FusionScoreResult]
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE LAYER
# ═══════════════════════════════════════════════════════════════════════════════


class FusionCache:
    """
    LRU cache for fusion score components.

    Provides <5ms cache hits for repeated queries within TTL.
    """

    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl_seconds: int = CACHE_TTL_SECONDS):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_order: List[str] = []
        self._hits = 0
        self._misses = 0

    def _make_key(self, corridor: Optional[str], component: str, lookback: int) -> str:
        """Generate cache key."""
        return f"{corridor or 'global'}:{component}:{lookback}"

    def get(self, corridor: Optional[str], component: str, lookback: int) -> Optional[Any]:
        """Get cached value if not expired."""
        key = self._make_key(corridor, component, lookback)
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                self._hits += 1
                # Move to end of access order
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return value
            else:
                # Expired, remove
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
        self._misses += 1
        return None

    def set(self, corridor: Optional[str], component: str, lookback: int, value: Any) -> None:
        """Set cached value with current timestamp."""
        key = self._make_key(corridor, component, lookback)

        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)

        self._cache[key] = (value, time.time())
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def invalidate(self, corridor: Optional[str] = None) -> int:
        """Invalidate cache entries. Returns count of invalidated entries."""
        if corridor is None:
            count = len(self._cache)
            self._cache.clear()
            self._access_order.clear()
            return count

        # Invalidate specific corridor
        prefix = f"{corridor}:"
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
        return len(keys_to_remove)

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }


# Global cache instance
_fusion_cache = FusionCache()


def get_fusion_cache() -> FusionCache:
    """Get the global fusion cache instance."""
    return _fusion_cache


# ═══════════════════════════════════════════════════════════════════════════════
# SCORING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def classify_severity(score: float) -> FusionSeverity:
    """
    Classify fusion score into severity bucket.

    Args:
        score: Fusion score [0, 1]

    Returns:
        FusionSeverity enum value
    """
    if score < FUSION_SEVERITY_THRESHOLDS["healthy"]:
        return FusionSeverity.HEALTHY
    elif score < FUSION_SEVERITY_THRESHOLDS["elevated"]:
        return FusionSeverity.ELEVATED
    elif score < FUSION_SEVERITY_THRESHOLDS["warning"]:
        return FusionSeverity.WARNING
    elif score < FUSION_SEVERITY_THRESHOLDS["critical"]:
        return FusionSeverity.CRITICAL
    else:
        return FusionSeverity.SEVERE


def classify_stability(index: float) -> StabilityClass:
    """
    Classify stability index into stability class.

    Args:
        index: Stability index [0, 1] (lower = more stable)

    Returns:
        StabilityClass enum value
    """
    if index < STABILITY_THRESHOLDS["highly_stable"]:
        return StabilityClass.HIGHLY_STABLE
    elif index < STABILITY_THRESHOLDS["stable"]:
        return StabilityClass.STABLE
    elif index < STABILITY_THRESHOLDS["moderate"]:
        return StabilityClass.MODERATE
    elif index < STABILITY_THRESHOLDS["volatile"]:
        return StabilityClass.VOLATILE
    else:
        return StabilityClass.HIGHLY_VOLATILE


def compute_drift_component(
    baseline_stats: Dict[str, Dict[str, float]],
    current_stats: Dict[str, Dict[str, float]],
    feature_weights: Optional[Dict[str, float]] = None,
) -> DriftComponent:
    """
    Compute drift magnitude component from feature statistics.

    Uses normalized mean/std shift with feature importance weighting.
    Vectorized for <10ms computation.

    Args:
        baseline_stats: Baseline feature statistics {feature: {mean, std, count}}
        current_stats: Current window statistics
        feature_weights: Optional custom feature weights

    Returns:
        DriftComponent with score and attribution
    """
    weights = feature_weights or DEFAULT_FEATURE_WEIGHTS

    # Extract common features
    common_features = set(baseline_stats.keys()) & set(current_stats.keys())
    if not common_features:
        return DriftComponent(
            score=0.0,
            bucket="STABLE",
            top_features=[],
            feature_deltas={},
        )

    # Vectorized drift computation
    feature_names = list(common_features)
    n_features = len(feature_names)

    baseline_means = np.array([baseline_stats[f].get("mean", 0) for f in feature_names])
    baseline_stds = np.array([baseline_stats[f].get("std", 1) for f in feature_names])
    current_means = np.array([current_stats[f].get("mean", 0) for f in feature_names])
    current_stds = np.array([current_stats[f].get("std", 1) for f in feature_names])

    # Avoid division by zero
    baseline_stds = np.maximum(baseline_stds, 1e-6)

    # Normalized mean shift
    mean_shifts = np.abs(current_means - baseline_means) / baseline_stds

    # Std ratio (capped at 3x)
    std_ratios = np.clip(current_stds / baseline_stds, 0.33, 3.0)
    std_deltas = np.abs(std_ratios - 1.0)

    # Combined delta (weighted mean shift + std change)
    deltas = 0.7 * mean_shifts + 0.3 * std_deltas

    # Apply feature weights
    feature_weight_arr = np.array([weights.get(f, 0.05) for f in feature_names])
    feature_weight_arr = feature_weight_arr / feature_weight_arr.sum()  # Normalize

    # Weighted score
    weighted_score = float(np.sum(deltas * feature_weight_arr))

    # Normalize to [0, 1]
    normalized_score = min(1.0, weighted_score / 3.0)  # 3.0 std = max drift

    # Feature deltas dict
    feature_deltas = {f: float(d) for f, d in zip(feature_names, deltas)}

    # Top features
    sorted_features = sorted(feature_deltas.items(), key=lambda x: x[1], reverse=True)
    top_features = [f for f, _ in sorted_features[:5]]

    # Bucket classification
    if normalized_score < 0.05:
        bucket = "STABLE"
    elif normalized_score < 0.10:
        bucket = "MINOR"
    elif normalized_score < 0.20:
        bucket = "MODERATE"
    elif normalized_score < 0.35:
        bucket = "SEVERE"
    else:
        bucket = "CRITICAL"

    return DriftComponent(
        score=normalized_score,
        bucket=bucket,
        top_features=top_features,
        feature_deltas=feature_deltas,
    )


def compute_shadow_component(
    shadow_stats: Dict[str, Any],
) -> ShadowComponent:
    """
    Compute shadow mode delta component.

    Extracts metrics from shadow mode statistics.

    Args:
        shadow_stats: Shadow mode statistics from shadow API

    Returns:
        ShadowComponent with delta metrics
    """
    mean_delta = shadow_stats.get("mean_delta", 0.0)
    p95_delta = shadow_stats.get("p95_delta", 0.0)
    max_delta = shadow_stats.get("max_delta", 0.0)
    event_count = shadow_stats.get("count", 0)
    drift_flag = shadow_stats.get("drift_flag", False) or p95_delta > 0.25

    return ShadowComponent(
        mean_delta=mean_delta,
        p95_delta=p95_delta,
        max_delta=max_delta,
        event_count=event_count,
        drift_flag=drift_flag,
    )


def compute_stability_component(
    historical_scores: Sequence[float],
    lookback_days: int = 30,
) -> StabilityComponent:
    """
    Compute corridor stability index from historical scores.

    Uses variance and trend analysis for stability classification.

    Args:
        historical_scores: List of historical fusion scores (newest first)
        lookback_days: Days of history to consider

    Returns:
        StabilityComponent with stability metrics
    """
    if not historical_scores or len(historical_scores) < 2:
        return StabilityComponent(
            stability_index=0.0,
            stability_class=StabilityClass.HIGHLY_STABLE,
            variance_30d=0.0,
            variance_7d=0.0,
            trend=TrendDirection.STABLE,
        )

    scores = np.array(historical_scores[:lookback_days])

    # 30-day variance (full window)
    variance_30d = float(np.var(scores)) if len(scores) > 1 else 0.0

    # 7-day variance (recent window)
    recent_scores = scores[:7] if len(scores) >= 7 else scores
    variance_7d = float(np.var(recent_scores)) if len(recent_scores) > 1 else 0.0

    # Stability index (normalized variance)
    stability_index = min(1.0, np.sqrt(variance_30d) * 2)

    # Trend detection
    if len(scores) >= 7:
        recent_mean = float(np.mean(scores[:7]))
        older_mean = float(np.mean(scores[7:14])) if len(scores) >= 14 else recent_mean

        delta = recent_mean - older_mean
        if delta < -0.05:
            trend = TrendDirection.IMPROVING
        elif delta > 0.05:
            trend = TrendDirection.DEGRADING
        else:
            trend = TrendDirection.STABLE
    else:
        trend = TrendDirection.STABLE

    stability_class = classify_stability(stability_index)

    return StabilityComponent(
        stability_index=stability_index,
        stability_class=stability_class,
        variance_30d=variance_30d,
        variance_7d=variance_7d,
        trend=trend,
    )


def compute_feature_attributions(
    drift_component: DriftComponent,
    shadow_delta: float,
    stability_index: float,
    fusion_score: float,
    top_n: int = 10,
) -> List[FeatureAttribution]:
    """
    Compute feature-level attributions for fusion score.

    Distributes fusion score across features based on drift contributions.

    Args:
        drift_component: Drift component with feature deltas
        shadow_delta: Shadow mode p95 delta
        stability_index: Stability index
        fusion_score: Total fusion score
        top_n: Number of top features to return

    Returns:
        List of FeatureAttribution sorted by contribution
    """
    if not drift_component.feature_deltas or fusion_score == 0:
        return []

    attributions = []
    total_delta = sum(drift_component.feature_deltas.values())

    if total_delta == 0:
        total_delta = 1.0  # Avoid division by zero

    for feature, delta in drift_component.feature_deltas.items():
        # Contribution proportional to feature delta
        contribution_pct = (delta / total_delta) * 100
        contribution_score = (delta / total_delta) * fusion_score

        # Direction
        if delta > 0.1:
            direction = "positive"  # Positive drift = increases risk
        elif delta < -0.1:
            direction = "negative"
        else:
            direction = "neutral"

        attributions.append(
            FeatureAttribution(
                feature_name=feature,
                contribution_score=contribution_score,
                contribution_pct=contribution_pct,
                drift_delta=delta,
                shadow_delta=shadow_delta,  # Global, not per-feature
                stability_delta=stability_index,  # Global, not per-feature
                rank=0,  # Set below
                direction=direction,
            )
        )

    # Sort and rank
    attributions.sort(key=lambda x: x.contribution_score, reverse=True)
    for i, attr in enumerate(attributions[:top_n]):
        attr.rank = i + 1

    return attributions[:top_n]


def generate_recommendations(
    fusion_score: float,
    severity: FusionSeverity,
    drift_component: DriftComponent,
    shadow_component: ShadowComponent,
    stability_component: StabilityComponent,
) -> List[str]:
    """
    Generate actionable recommendations based on fusion analysis.

    Args:
        fusion_score: Combined fusion score
        severity: Severity classification
        drift_component: Drift analysis
        shadow_component: Shadow mode analysis
        stability_component: Stability analysis

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Severity-based recommendations
    if severity == FusionSeverity.SEVERE:
        recommendations.append(
            "🚨 SEVERE: Model reliability critically compromised. "
            "Recommend immediate investigation and potential fallback to rule-based scoring."
        )
    elif severity == FusionSeverity.CRITICAL:
        recommendations.append(
            "⚠️ CRITICAL: Significant model degradation detected. " "Schedule retraining within 24 hours and increase monitoring frequency."
        )
    elif severity == FusionSeverity.WARNING:
        recommendations.append(
            "⚡ WARNING: Model drift exceeds normal thresholds. " "Review feature distributions and consider partial retraining."
        )

    # Drift-specific recommendations
    if drift_component.bucket in ("SEVERE", "CRITICAL"):
        top_features_str = ", ".join(drift_component.top_features[:3])
        recommendations.append(
            f"📊 High drift in: {top_features_str}. " "Validate data pipelines and feature engineering for these features."
        )

    # Shadow mode recommendations
    if shadow_component.drift_flag:
        recommendations.append(
            f"🔮 Shadow mode P95 delta: {shadow_component.p95_delta:.1%}. "
            "Production model diverging from baseline. Review recent model updates."
        )

    # Stability recommendations
    if stability_component.stability_class == StabilityClass.HIGHLY_VOLATILE:
        recommendations.append(
            "📈 Corridor stability is HIGHLY VOLATILE. " "Consider implementing adaptive thresholds or corridor-specific models."
        )
    elif stability_component.trend == TrendDirection.DEGRADING:
        recommendations.append("📉 Performance trend is DEGRADING. " "Monitor closely and prepare retraining pipeline.")

    # General recommendation if healthy
    if not recommendations:
        recommendations.append("✅ Model health is good. Continue standard monitoring.")

    return recommendations


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FUSION SCORING
# ═══════════════════════════════════════════════════════════════════════════════


def compute_fusion_score(
    drift_stats: Dict[str, Dict[str, Dict[str, float]]],
    shadow_stats: Dict[str, Any],
    historical_scores: Optional[Sequence[float]] = None,
    corridor: Optional[str] = None,
    lookback_hours: int = 24,
    use_cache: bool = True,
) -> FusionScoreResult:
    """
    Compute unified fusion score combining drift, shadow, and stability.

    ALEX-compliant: Optimized for p95 < 45ms via caching and vectorization.

    Args:
        drift_stats: Drift statistics {corridor: {baseline: {...}, current: {...}}}
                    or {feature: {mean, std, count}} for single corridor
        shadow_stats: Shadow mode statistics from shadow API
        historical_scores: Optional historical fusion scores for stability
        corridor: Corridor filter (None = global)
        lookback_hours: Time window for analysis
        use_cache: Whether to use caching

    Returns:
        FusionScoreResult with combined scoring and attribution
    """
    start_time = time.perf_counter()
    cache = get_fusion_cache()

    # Check cache for pre-computed result
    if use_cache:
        cached = cache.get(corridor, "fusion", lookback_hours)
        if cached is not None:
            logger.debug(f"Cache hit for fusion score: {corridor}")
            cached.latency_ms = (time.perf_counter() - start_time) * 1000
            return cached

    # Extract baseline/current from drift_stats
    if corridor and corridor in drift_stats:
        corridor_data = drift_stats[corridor]
        baseline = corridor_data.get("baseline", {})
        current = corridor_data.get("current", {})
    else:
        # Assume direct feature stats format
        baseline = drift_stats.get("baseline", drift_stats)
        current = drift_stats.get("current", drift_stats)

    # Compute components
    drift_component = compute_drift_component(baseline, current)
    shadow_component = compute_shadow_component(shadow_stats)
    stability_component = compute_stability_component(
        historical_scores or [],
        lookback_days=lookback_hours // 24 or 7,
    )

    # Weighted fusion
    drift_contribution = drift_component.score * FUSION_WEIGHTS["drift_magnitude"]
    shadow_contribution = shadow_component.p95_delta * FUSION_WEIGHTS["shadow_delta"]
    stability_contribution = stability_component.stability_index * FUSION_WEIGHTS["stability_index"]

    fusion_score = drift_contribution + shadow_contribution + stability_contribution
    fusion_score = min(1.0, max(0.0, fusion_score))  # Clamp to [0, 1]

    # Severity classification
    severity = classify_severity(fusion_score)

    # Confidence (based on sample sizes)
    event_count = shadow_component.event_count
    if event_count >= 1000:
        confidence = 0.95
    elif event_count >= 500:
        confidence = 0.85
    elif event_count >= 100:
        confidence = 0.70
    elif event_count >= 50:
        confidence = 0.50
    else:
        confidence = 0.30

    # Feature attributions
    attributions = compute_feature_attributions(
        drift_component,
        shadow_component.p95_delta,
        stability_component.stability_index,
        fusion_score,
        top_n=10,
    )

    # Recommendations
    recommendations = generate_recommendations(
        fusion_score,
        severity,
        drift_component,
        shadow_component,
        stability_component,
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    result = FusionScoreResult(
        fusion_score=fusion_score,
        severity=severity,
        confidence=confidence,
        drift_component=drift_component,
        shadow_component=shadow_component,
        stability_component=stability_component,
        top_attributions=attributions,
        corridor=corridor,
        lookback_hours=lookback_hours,
        model_version="v1.2.0",
        latency_ms=latency_ms,
        recommendations=recommendations,
    )

    # Cache result
    if use_cache:
        cache.set(corridor, "fusion", lookback_hours, result)

    # Log latency warning if over budget
    if latency_ms > MAX_LATENCY_MS:
        logger.warning(f"Fusion score latency {latency_ms:.1f}ms exceeds budget {MAX_LATENCY_MS}ms")

    return result


def compute_multi_corridor_fusion(
    corridor_drift_stats: Dict[str, Dict[str, Dict[str, float]]],
    corridor_shadow_stats: Dict[str, Dict[str, Any]],
    corridor_histories: Optional[Dict[str, Sequence[float]]] = None,
    lookback_hours: int = 24,
) -> CorridorFusionSummary:
    """
    Compute fusion scores across multiple corridors.

    Optimized for batch processing with aggregation.

    Args:
        corridor_drift_stats: {corridor: {baseline: {...}, current: {...}}}
        corridor_shadow_stats: {corridor: shadow_stats}
        corridor_histories: Optional {corridor: [historical_scores]}
        lookback_hours: Time window

    Returns:
        CorridorFusionSummary with per-corridor results
    """
    start_time = time.perf_counter()

    corridor_results = []
    severity_counts = {
        FusionSeverity.HEALTHY: 0,
        FusionSeverity.ELEVATED: 0,
        FusionSeverity.WARNING: 0,
        FusionSeverity.CRITICAL: 0,
        FusionSeverity.SEVERE: 0,
    }

    corridors = set(corridor_drift_stats.keys()) | set(corridor_shadow_stats.keys())
    histories = corridor_histories or {}

    for corridor in corridors:
        drift_data = corridor_drift_stats.get(corridor, {})
        shadow_data = corridor_shadow_stats.get(corridor, {})
        history = histories.get(corridor, [])

        # Format drift data for compute_fusion_score
        formatted_drift = {corridor: drift_data} if drift_data else {}

        result = compute_fusion_score(
            drift_stats=formatted_drift or {"baseline": {}, "current": {}},
            shadow_stats=shadow_data,
            historical_scores=history,
            corridor=corridor,
            lookback_hours=lookback_hours,
            use_cache=True,
        )

        corridor_results.append(result)
        severity_counts[result.severity] += 1

    # Sort by score descending
    corridor_results.sort(key=lambda x: x.fusion_score, reverse=True)

    # Compute aggregates
    scores = [r.fusion_score for r in corridor_results]
    avg_score = float(np.mean(scores)) if scores else 0.0
    max_score = float(np.max(scores)) if scores else 0.0

    top_corridors = [(r.corridor or "unknown", r.fusion_score) for r in corridor_results[:5]]

    latency_ms = (time.perf_counter() - start_time) * 1000

    return CorridorFusionSummary(
        total_corridors=len(corridors),
        healthy_count=severity_counts[FusionSeverity.HEALTHY],
        elevated_count=severity_counts[FusionSeverity.ELEVATED],
        warning_count=severity_counts[FusionSeverity.WARNING],
        critical_count=severity_counts[FusionSeverity.CRITICAL],
        severe_count=severity_counts[FusionSeverity.SEVERE],
        avg_fusion_score=avg_score,
        max_fusion_score=max_score,
        top_corridors=top_corridors,
        corridor_results=corridor_results,
        latency_ms=latency_ms,
    )
