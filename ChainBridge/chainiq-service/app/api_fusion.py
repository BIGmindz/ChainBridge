"""
ChainIQ Fusion API v1.2

REST endpoints for Shadow/Drift fusion scoring and feature attribution.
Provides unified model health monitoring combining shadow mode deltas,
drift magnitude, and corridor stability metrics.

Endpoints:
- GET /iq/fusion/score - Global or corridor-specific fusion score
- GET /iq/fusion/corridors - Multi-corridor fusion summary
- GET /iq/fusion/attribution - Feature-level score attribution
- GET /iq/fusion/health - Quick health check with latency
- GET /iq/fusion/cache/stats - Cache statistics (admin)
- POST /iq/fusion/cache/invalidate - Clear fusion cache (admin)

ALEX-compliant: p95 latency < 45ms via caching and vectorization.

Author: Cody (GID-01) 🔵
PAC: PAC-CODY-NEXT-035
Version: 1.2.0
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.ml.fusion_engine import (
    FusionScoreResult,
    compute_fusion_score,
    compute_multi_corridor_fusion,
    get_fusion_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iq/fusion", tags=["ChainIQ Fusion v1.2"])


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class DriftComponentResponse(BaseModel):
    """Drift magnitude component of fusion score."""

    score: float = Field(..., ge=0.0, le=1.0, description="Normalized drift score [0, 1]")
    bucket: Literal["STABLE", "MINOR", "MODERATE", "SEVERE", "CRITICAL"] = Field(..., description="Drift severity bucket")
    top_features: List[str] = Field(..., description="Top drifting features")
    feature_deltas: Dict[str, float] = Field(..., description="Feature-level drift magnitudes")


class ShadowComponentResponse(BaseModel):
    """Shadow mode delta component of fusion score."""

    mean_delta: float = Field(..., ge=0.0, description="Mean real-dummy delta")
    p95_delta: float = Field(..., ge=0.0, description="95th percentile delta")
    max_delta: float = Field(..., ge=0.0, le=1.0, description="Maximum delta observed")
    event_count: int = Field(..., ge=0, description="Number of shadow events")
    drift_flag: bool = Field(..., description="True if p95 > 0.25 threshold")


class StabilityComponentResponse(BaseModel):
    """Corridor stability component of fusion score."""

    stability_index: float = Field(..., ge=0.0, le=1.0, description="Historical stability index")
    stability_class: Literal["HIGHLY_STABLE", "STABLE", "MODERATE", "VOLATILE", "HIGHLY_VOLATILE"] = Field(
        ..., description="Stability classification"
    )
    variance_30d: float = Field(..., ge=0.0, description="30-day variance")
    variance_7d: float = Field(..., ge=0.0, description="7-day variance")
    trend: Literal["IMPROVING", "STABLE", "DEGRADING"] = Field(..., description="Recent trend direction")


class FeatureAttributionResponse(BaseModel):
    """Feature-level attribution for fusion score."""

    feature_name: str = Field(..., description="Feature name")
    contribution_score: float = Field(..., description="Contribution to fusion score")
    contribution_pct: float = Field(..., description="Percentage of total score")
    drift_delta: float = Field(..., description="Feature drift magnitude")
    rank: int = Field(..., ge=1, description="Rank by contribution (1 = highest)")
    direction: Literal["positive", "negative", "neutral"] = Field(..., description="Contribution direction")


class FusionScoreResponse(BaseModel):
    """
    Complete fusion score response.

    Combines drift, shadow, and stability into unified scoring.
    """

    # Core scores
    fusion_score: float = Field(..., ge=0.0, le=1.0, description="Combined fusion score [0, 1]")
    severity: Literal["HEALTHY", "ELEVATED", "WARNING", "CRITICAL", "SEVERE"] = Field(..., description="Severity classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Score confidence")

    # Component scores
    drift_component: DriftComponentResponse = Field(..., description="Drift magnitude component")
    shadow_component: ShadowComponentResponse = Field(..., description="Shadow mode component")
    stability_component: StabilityComponentResponse = Field(..., description="Stability component")

    # Attribution
    top_attributions: List[FeatureAttributionResponse] = Field(..., description="Top feature attributions")

    # Metadata
    corridor: Optional[str] = Field(None, description="Corridor analyzed (null = global)")
    lookback_hours: int = Field(..., description="Analysis time window")
    model_version: str = Field(..., description="Fusion engine version")
    computed_at: datetime = Field(..., description="Computation timestamp (UTC)")
    latency_ms: float = Field(..., ge=0.0, description="Computation latency in ms")

    # Recommendations
    recommendations: List[str] = Field(..., description="Actionable recommendations")


class CorridorFusionResponse(BaseModel):
    """Summary of fusion scores across corridors."""

    total_corridors: int = Field(..., ge=0, description="Total corridors analyzed")
    healthy_count: int = Field(..., ge=0, description="Corridors with HEALTHY status")
    elevated_count: int = Field(..., ge=0, description="Corridors with ELEVATED status")
    warning_count: int = Field(..., ge=0, description="Corridors with WARNING status")
    critical_count: int = Field(..., ge=0, description="Corridors with CRITICAL status")
    severe_count: int = Field(..., ge=0, description="Corridors with SEVERE status")
    avg_fusion_score: float = Field(..., ge=0.0, le=1.0, description="Average fusion score")
    max_fusion_score: float = Field(..., ge=0.0, le=1.0, description="Maximum fusion score")
    top_corridors: List[Dict[str, Any]] = Field(..., description="Top corridors by score")
    model_version: str = Field(default="v1.2.0", description="Fusion engine version")
    computed_at: datetime = Field(..., description="Computation timestamp (UTC)")
    latency_ms: float = Field(..., ge=0.0, description="Total computation latency in ms")


class CorridorDetailResponse(BaseModel):
    """Detailed corridor fusion result."""

    corridor: str = Field(..., description="Corridor identifier")
    fusion_score: float = Field(..., ge=0.0, le=1.0, description="Fusion score")
    severity: str = Field(..., description="Severity classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Score confidence")
    drift_score: float = Field(..., ge=0.0, le=1.0, description="Drift component score")
    shadow_p95: float = Field(..., ge=0.0, description="Shadow P95 delta")
    stability_index: float = Field(..., ge=0.0, le=1.0, description="Stability index")
    top_features: List[str] = Field(..., description="Top drifting features")


class AttributionResponse(BaseModel):
    """Feature attribution response."""

    corridor: Optional[str] = Field(None, description="Corridor (null = global)")
    fusion_score: float = Field(..., ge=0.0, le=1.0, description="Total fusion score")
    attributions: List[FeatureAttributionResponse] = Field(..., description="Feature attributions")
    model_version: str = Field(default="v1.2.0", description="Fusion engine version")
    computed_at: datetime = Field(..., description="Computation timestamp")


class HealthCheckResponse(BaseModel):
    """Quick health check response."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Overall health status")
    fusion_score: float = Field(..., ge=0.0, le=1.0, description="Global fusion score")
    severity: str = Field(..., description="Severity classification")
    latency_ms: float = Field(..., ge=0.0, description="Computation latency")
    cache_hit: bool = Field(..., description="Whether result was cached")
    model_version: str = Field(default="v1.2.0", description="Fusion engine version")


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""

    size: int = Field(..., ge=0, description="Current cache size")
    max_size: int = Field(..., ge=0, description="Maximum cache size")
    ttl_seconds: int = Field(..., ge=0, description="Cache TTL in seconds")
    hits: int = Field(..., ge=0, description="Total cache hits")
    misses: int = Field(..., ge=0, description="Total cache misses")
    hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")


class CacheInvalidateResponse(BaseModel):
    """Cache invalidation response."""

    invalidated_count: int = Field(..., ge=0, description="Number of entries invalidated")
    corridor: Optional[str] = Field(None, description="Corridor invalidated (null = all)")


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA FUNCTIONS (Replace with real data sources in production)
# ═══════════════════════════════════════════════════════════════════════════════


def _get_mock_drift_stats(corridor: Optional[str] = None) -> Dict[str, Any]:
    """Get mock drift statistics for development."""
    corridors_data = {
        "US-CN": {
            "baseline": {
                "eta_deviation_hours": {"mean": 5.0, "std": 2.0, "count": 10000},
                "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 10000},
                "delay_flag": {"mean": 0.15, "std": 0.36, "count": 10000},
                "shipper_on_time_pct_90d": {"mean": 88.0, "std": 8.0, "count": 10000},
                "carrier_on_time_pct_90d": {"mean": 85.0, "std": 10.0, "count": 10000},
                "total_dwell_hours": {"mean": 8.0, "std": 4.0, "count": 10000},
                "lane_sentiment_score": {"mean": 0.65, "std": 0.15, "count": 10000},
            },
            "current": {
                "eta_deviation_hours": {"mean": 8.2, "std": 3.1, "count": 500},  # Drifted
                "num_route_deviations": {"mean": 2.1, "std": 1.5, "count": 500},
                "delay_flag": {"mean": 0.22, "std": 0.41, "count": 500},
                "shipper_on_time_pct_90d": {"mean": 84.0, "std": 9.0, "count": 500},
                "carrier_on_time_pct_90d": {"mean": 82.0, "std": 11.0, "count": 500},
                "total_dwell_hours": {"mean": 10.5, "std": 5.0, "count": 500},
                "lane_sentiment_score": {"mean": 0.58, "std": 0.18, "count": 500},
            },
        },
        "EU-IN": {
            "baseline": {
                "eta_deviation_hours": {"mean": 5.0, "std": 2.0, "count": 8000},
                "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 8000},
                "delay_flag": {"mean": 0.15, "std": 0.36, "count": 8000},
                "shipper_on_time_pct_90d": {"mean": 88.0, "std": 8.0, "count": 8000},
                "carrier_on_time_pct_90d": {"mean": 85.0, "std": 10.0, "count": 8000},
                "total_dwell_hours": {"mean": 8.0, "std": 4.0, "count": 8000},
                "lane_sentiment_score": {"mean": 0.65, "std": 0.15, "count": 8000},
            },
            "current": {
                "eta_deviation_hours": {"mean": 5.5, "std": 2.2, "count": 300},  # Minor drift
                "num_route_deviations": {"mean": 1.6, "std": 1.3, "count": 300},
                "delay_flag": {"mean": 0.16, "std": 0.37, "count": 300},
                "shipper_on_time_pct_90d": {"mean": 87.0, "std": 8.5, "count": 300},
                "carrier_on_time_pct_90d": {"mean": 84.0, "std": 10.5, "count": 300},
                "total_dwell_hours": {"mean": 8.5, "std": 4.2, "count": 300},
                "lane_sentiment_score": {"mean": 0.63, "std": 0.16, "count": 300},
            },
        },
        "US-MX": {
            "baseline": {
                "eta_deviation_hours": {"mean": 5.0, "std": 2.0, "count": 12000},
                "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 12000},
                "delay_flag": {"mean": 0.15, "std": 0.36, "count": 12000},
                "shipper_on_time_pct_90d": {"mean": 88.0, "std": 8.0, "count": 12000},
                "carrier_on_time_pct_90d": {"mean": 85.0, "std": 10.0, "count": 12000},
                "total_dwell_hours": {"mean": 8.0, "std": 4.0, "count": 12000},
                "lane_sentiment_score": {"mean": 0.65, "std": 0.15, "count": 12000},
            },
            "current": {
                "eta_deviation_hours": {"mean": 5.1, "std": 2.0, "count": 800},  # Stable
                "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 800},
                "delay_flag": {"mean": 0.15, "std": 0.36, "count": 800},
                "shipper_on_time_pct_90d": {"mean": 88.0, "std": 8.0, "count": 800},
                "carrier_on_time_pct_90d": {"mean": 85.0, "std": 10.0, "count": 800},
                "total_dwell_hours": {"mean": 8.1, "std": 4.0, "count": 800},
                "lane_sentiment_score": {"mean": 0.65, "std": 0.15, "count": 800},
            },
        },
        "APAC-US": {
            "baseline": {
                "eta_deviation_hours": {"mean": 6.0, "std": 2.5, "count": 6000},
                "num_route_deviations": {"mean": 2.0, "std": 1.5, "count": 6000},
                "delay_flag": {"mean": 0.18, "std": 0.38, "count": 6000},
                "shipper_on_time_pct_90d": {"mean": 85.0, "std": 9.0, "count": 6000},
                "carrier_on_time_pct_90d": {"mean": 82.0, "std": 11.0, "count": 6000},
                "total_dwell_hours": {"mean": 10.0, "std": 5.0, "count": 6000},
                "lane_sentiment_score": {"mean": 0.60, "std": 0.18, "count": 6000},
            },
            "current": {
                "eta_deviation_hours": {"mean": 9.5, "std": 4.0, "count": 400},  # Severe drift
                "num_route_deviations": {"mean": 3.2, "std": 2.0, "count": 400},
                "delay_flag": {"mean": 0.32, "std": 0.47, "count": 400},
                "shipper_on_time_pct_90d": {"mean": 78.0, "std": 12.0, "count": 400},
                "carrier_on_time_pct_90d": {"mean": 75.0, "std": 14.0, "count": 400},
                "total_dwell_hours": {"mean": 14.0, "std": 7.0, "count": 400},
                "lane_sentiment_score": {"mean": 0.48, "std": 0.22, "count": 400},
            },
        },
    }

    if corridor:
        return {corridor: corridors_data.get(corridor, corridors_data["US-MX"])}
    return corridors_data


def _get_mock_shadow_stats(corridor: Optional[str] = None) -> Dict[str, Any]:
    """Get mock shadow mode statistics for development."""
    corridor_shadow = {
        "US-CN": {
            "count": 500,
            "mean_delta": 0.12,
            "p95_delta": 0.28,
            "max_delta": 0.45,
            "drift_flag": True,
        },
        "EU-IN": {
            "count": 300,
            "mean_delta": 0.08,
            "p95_delta": 0.18,
            "max_delta": 0.32,
            "drift_flag": False,
        },
        "US-MX": {
            "count": 800,
            "mean_delta": 0.05,
            "p95_delta": 0.12,
            "max_delta": 0.22,
            "drift_flag": False,
        },
        "APAC-US": {
            "count": 400,
            "mean_delta": 0.18,
            "p95_delta": 0.38,
            "max_delta": 0.55,
            "drift_flag": True,
        },
    }

    if corridor:
        return corridor_shadow.get(corridor, corridor_shadow["US-MX"])
    return corridor_shadow


def _get_mock_historical_scores(corridor: Optional[str] = None) -> List[float]:
    """Get mock historical fusion scores for stability computation."""
    # Simulate 30 days of historical scores
    import random

    random.seed(hash(corridor) if corridor else 42)

    base_score = 0.25 if corridor in ("US-CN", "APAC-US") else 0.15
    return [base_score + random.uniform(-0.08, 0.08) for _ in range(30)]


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALIZATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _serialize_fusion_result(result: FusionScoreResult) -> FusionScoreResponse:
    """Convert FusionScoreResult to API response."""
    return FusionScoreResponse(
        fusion_score=result.fusion_score,
        severity=result.severity.value,
        confidence=result.confidence,
        drift_component=DriftComponentResponse(
            score=result.drift_component.score,
            bucket=result.drift_component.bucket,
            top_features=result.drift_component.top_features,
            feature_deltas=result.drift_component.feature_deltas,
        ),
        shadow_component=ShadowComponentResponse(
            mean_delta=result.shadow_component.mean_delta,
            p95_delta=result.shadow_component.p95_delta,
            max_delta=result.shadow_component.max_delta,
            event_count=result.shadow_component.event_count,
            drift_flag=result.shadow_component.drift_flag,
        ),
        stability_component=StabilityComponentResponse(
            stability_index=result.stability_component.stability_index,
            stability_class=result.stability_component.stability_class.value,
            variance_30d=result.stability_component.variance_30d,
            variance_7d=result.stability_component.variance_7d,
            trend=result.stability_component.trend.value,
        ),
        top_attributions=[
            FeatureAttributionResponse(
                feature_name=attr.feature_name,
                contribution_score=attr.contribution_score,
                contribution_pct=attr.contribution_pct,
                drift_delta=attr.drift_delta,
                rank=attr.rank,
                direction=attr.direction,
            )
            for attr in result.top_attributions
        ],
        corridor=result.corridor,
        lookback_hours=result.lookback_hours,
        model_version=result.model_version,
        computed_at=result.computed_at,
        latency_ms=result.latency_ms,
        recommendations=result.recommendations,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/score",
    response_model=FusionScoreResponse,
    summary="Get fusion score",
    description="Returns unified fusion score combining drift, shadow mode, and stability metrics. " "ALEX-compliant: p95 latency < 45ms.",
)
def get_fusion_score(
    corridor: Optional[str] = Query(
        None,
        description="Filter by corridor (e.g., US-CN). Null returns global score.",
        examples=["US-CN", "EU-IN", "US-MX"],
    ),
    lookback_hours: int = Query(
        24,
        ge=1,
        le=168,
        description="Time window for analysis (1-168 hours)",
    ),
) -> FusionScoreResponse:
    """
    Get unified fusion score.

    Combines three components:
    1. **Drift Magnitude**: Feature distribution shift from baseline
    2. **Shadow Delta**: Real vs dummy model score differences
    3. **Stability Index**: Historical corridor stability

    Performance: Optimized for p95 < 45ms via caching and vectorization.

    Args:
        corridor: Optional corridor filter (null = global)
        lookback_hours: Time window for analysis

    Returns:
        FusionScoreResponse with unified scoring and attribution
    """
    try:
        logger.info(f"Computing fusion score: corridor={corridor}, lookback={lookback_hours}h")

        # Get data (mock for development)
        drift_stats = _get_mock_drift_stats(corridor)
        shadow_stats = _get_mock_shadow_stats(corridor)
        historical = _get_mock_historical_scores(corridor)

        # Compute fusion score
        result = compute_fusion_score(
            drift_stats=drift_stats,
            shadow_stats=shadow_stats,
            historical_scores=historical,
            corridor=corridor,
            lookback_hours=lookback_hours,
            use_cache=True,
        )

        return _serialize_fusion_result(result)

    except Exception as e:
        logger.error(f"Failed to compute fusion score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute fusion score: {str(e)}")


@router.get(
    "/corridors",
    response_model=CorridorFusionResponse,
    summary="Get multi-corridor fusion summary",
    description="Returns fusion scores for all corridors with aggregated statistics.",
)
def get_corridor_fusion(
    lookback_hours: int = Query(
        24,
        ge=1,
        le=168,
        description="Time window for analysis (1-168 hours)",
    ),
    min_events: int = Query(
        50,
        ge=1,
        le=1000,
        description="Minimum shadow events required for corridor inclusion",
    ),
) -> CorridorFusionResponse:
    """
    Get fusion scores across all corridors.

    Provides aggregated view of model health across trade corridors.
    Useful for identifying problematic regions requiring attention.

    Args:
        lookback_hours: Time window for analysis
        min_events: Minimum events for corridor inclusion

    Returns:
        CorridorFusionResponse with per-corridor scores and aggregates
    """
    try:
        logger.info(f"Computing multi-corridor fusion: lookback={lookback_hours}h")

        # Get data for all corridors
        drift_stats = _get_mock_drift_stats()
        shadow_stats = _get_mock_shadow_stats()

        # Filter by min_events
        filtered_shadow = {k: v for k, v in shadow_stats.items() if v.get("count", 0) >= min_events}

        # Get historical scores for each corridor
        histories = {corridor: _get_mock_historical_scores(corridor) for corridor in filtered_shadow.keys()}

        # Compute multi-corridor fusion
        summary = compute_multi_corridor_fusion(
            corridor_drift_stats=drift_stats,
            corridor_shadow_stats=filtered_shadow,
            corridor_histories=histories,
            lookback_hours=lookback_hours,
        )

        return CorridorFusionResponse(
            total_corridors=summary.total_corridors,
            healthy_count=summary.healthy_count,
            elevated_count=summary.elevated_count,
            warning_count=summary.warning_count,
            critical_count=summary.critical_count,
            severe_count=summary.severe_count,
            avg_fusion_score=summary.avg_fusion_score,
            max_fusion_score=summary.max_fusion_score,
            top_corridors=[{"corridor": c, "fusion_score": s} for c, s in summary.top_corridors],
            model_version="v1.2.0",
            computed_at=summary.computed_at,
            latency_ms=summary.latency_ms,
        )

    except Exception as e:
        logger.error(f"Failed to compute corridor fusion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute corridor fusion: {str(e)}")


@router.get(
    "/corridors/{corridor}",
    response_model=FusionScoreResponse,
    summary="Get corridor-specific fusion score",
    description="Returns detailed fusion score for a specific corridor.",
)
def get_corridor_detail(
    corridor: str,
    lookback_hours: int = Query(24, ge=1, le=168),
) -> FusionScoreResponse:
    """
    Get detailed fusion score for specific corridor.

    Args:
        corridor: Corridor identifier (e.g., US-CN)
        lookback_hours: Time window for analysis

    Returns:
        FusionScoreResponse with full corridor details
    """
    return get_fusion_score(corridor=corridor, lookback_hours=lookback_hours)


@router.get(
    "/attribution",
    response_model=AttributionResponse,
    summary="Get feature attribution",
    description="Returns feature-level attribution for fusion score.",
)
def get_attribution(
    corridor: Optional[str] = Query(None, description="Corridor filter"),
    lookback_hours: int = Query(24, ge=1, le=168),
    top_n: int = Query(10, ge=1, le=50, description="Number of features to return"),
) -> AttributionResponse:
    """
    Get feature-level attribution for fusion score.

    Shows which features contribute most to the fusion score,
    useful for understanding and debugging model drift.

    Args:
        corridor: Optional corridor filter
        lookback_hours: Time window for analysis
        top_n: Number of top features to return

    Returns:
        AttributionResponse with feature contributions
    """
    try:
        # Get fusion score (includes attributions)
        drift_stats = _get_mock_drift_stats(corridor)
        shadow_stats = _get_mock_shadow_stats(corridor)
        historical = _get_mock_historical_scores(corridor)

        result = compute_fusion_score(
            drift_stats=drift_stats,
            shadow_stats=shadow_stats,
            historical_scores=historical,
            corridor=corridor,
            lookback_hours=lookback_hours,
            use_cache=True,
        )

        return AttributionResponse(
            corridor=corridor,
            fusion_score=result.fusion_score,
            attributions=[
                FeatureAttributionResponse(
                    feature_name=attr.feature_name,
                    contribution_score=attr.contribution_score,
                    contribution_pct=attr.contribution_pct,
                    drift_delta=attr.drift_delta,
                    rank=attr.rank,
                    direction=attr.direction,
                )
                for attr in result.top_attributions[:top_n]
            ],
            model_version=result.model_version,
            computed_at=result.computed_at,
        )

    except Exception as e:
        logger.error(f"Failed to compute attribution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute attribution: {str(e)}")


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Quick health check",
    description="Returns quick health status with latency measurement.",
)
def health_check() -> HealthCheckResponse:
    """
    Quick health check endpoint.

    Provides rapid model health assessment for monitoring systems.
    Optimized for minimal latency with cache-first approach.

    Returns:
        HealthCheckResponse with status and latency
    """
    try:
        start_time = time.perf_counter()
        cache = get_fusion_cache()

        # Try cache first
        cached = cache.get(None, "fusion", 24)
        cache_hit = cached is not None

        if cached:
            fusion_score = cached.fusion_score
            severity = cached.severity.value
        else:
            # Compute fresh
            drift_stats = _get_mock_drift_stats()
            shadow_stats = _get_mock_shadow_stats()

            result = compute_fusion_score(
                drift_stats=drift_stats,
                shadow_stats=shadow_stats,
                historical_scores=_get_mock_historical_scores(),
                corridor=None,
                lookback_hours=24,
                use_cache=True,
            )
            fusion_score = result.fusion_score
            severity = result.severity.value

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Determine health status
        if severity in ("HEALTHY", "ELEVATED"):
            status = "healthy"
        elif severity == "WARNING":
            status = "degraded"
        else:
            status = "unhealthy"

        return HealthCheckResponse(
            status=status,
            fusion_score=fusion_score,
            severity=severity,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            model_version="v1.2.0",
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthCheckResponse(
            status="unhealthy",
            fusion_score=1.0,
            severity="SEVERE",
            latency_ms=0.0,
            cache_hit=False,
            model_version="v1.2.0",
        )


@router.get(
    "/cache/stats",
    response_model=CacheStatsResponse,
    summary="Get cache statistics",
    description="Returns fusion cache statistics for monitoring.",
)
def get_cache_stats() -> CacheStatsResponse:
    """
    Get cache statistics.

    Useful for monitoring cache performance and tuning.

    Returns:
        CacheStatsResponse with cache metrics
    """
    cache = get_fusion_cache()
    stats = cache.stats()

    return CacheStatsResponse(
        size=stats["size"],
        max_size=stats["max_size"],
        ttl_seconds=stats["ttl_seconds"],
        hits=stats["hits"],
        misses=stats["misses"],
        hit_rate=stats["hit_rate"],
    )


@router.post(
    "/cache/invalidate",
    response_model=CacheInvalidateResponse,
    summary="Invalidate cache",
    description="Invalidate fusion cache entries. Admin endpoint.",
)
def invalidate_cache(
    corridor: Optional[str] = Query(None, description="Corridor to invalidate (null = all)"),
) -> CacheInvalidateResponse:
    """
    Invalidate fusion cache.

    Use after model updates or data corrections to force recomputation.

    Args:
        corridor: Optional corridor filter (null = invalidate all)

    Returns:
        CacheInvalidateResponse with invalidation count
    """
    cache = get_fusion_cache()
    count = cache.invalidate(corridor)

    logger.info(f"Invalidated {count} cache entries for corridor={corridor}")

    return CacheInvalidateResponse(
        invalidated_count=count,
        corridor=corridor,
    )
