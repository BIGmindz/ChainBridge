"""
ChainIQ Drift Explainability Serializers

Pydantic models for serializing drift detection results to API responses.
Provides structured, typed output for drift scoring endpoints.

Author: Cody (GID-01) 🔵
PAC: CODY-PAC-NEXT-034
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE-LEVEL DRIFT SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class FeatureDriftResponse(BaseModel):
    """
    Drift analysis result for a single feature.

    Provides detailed metrics on how a feature's distribution has shifted
    from baseline to current window.
    """

    feature_name: str = Field(
        ...,
        description="Name of the feature being analyzed",
        examples=["eta_deviation_hours"],
    )
    baseline_mean: float = Field(
        ...,
        description="Mean value in baseline distribution",
        examples=[5.0],
    )
    current_mean: float = Field(
        ...,
        description="Mean value in current window",
        examples=[8.2],
    )
    baseline_std: float = Field(
        ...,
        description="Standard deviation in baseline distribution",
        examples=[2.0],
    )
    current_std: float = Field(
        ...,
        description="Standard deviation in current window",
        examples=[3.1],
    )
    shift_delta: float = Field(
        ...,
        ge=0.0,
        description="Normalized shift magnitude (0=no drift, >1=significant)",
        examples=[1.65],
    )
    shift_direction: Literal["INCREASING", "DECREASING", "STABLE"] = Field(
        ...,
        description="Direction of the mean shift",
        examples=["INCREASING"],
    )
    psi_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Population Stability Index approximation",
        examples=[0.23],
    )
    ks_statistic: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Kolmogorov-Smirnov statistic (if computed)",
        examples=[0.18],
    )
    drift_bucket: Literal["STABLE", "MINOR", "MODERATE", "SEVERE", "CRITICAL"] = Field(
        ...,
        description="Categorical drift severity bucket",
        examples=["MODERATE"],
    )
    contribution_rank: int = Field(
        ...,
        ge=1,
        description="Rank among all features (1=highest drift contributor)",
        examples=[1],
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of the drift",
        examples=["eta_deviation_hours: Moderate drift detected (increasing, delta=1.650)."],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "feature_name": "eta_deviation_hours",
                "baseline_mean": 5.0,
                "current_mean": 8.2,
                "baseline_std": 2.0,
                "current_std": 3.1,
                "shift_delta": 1.65,
                "shift_direction": "INCREASING",
                "psi_score": 0.23,
                "ks_statistic": None,
                "drift_bucket": "MODERATE",
                "contribution_rank": 1,
                "explanation": "eta_deviation_hours: Moderate drift detected (increasing, delta=1.650). Review recent data quality.",
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CORRIDOR-LEVEL DRIFT SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class CorridorDriftResponse(BaseModel):
    """
    Drift analysis result for a trade corridor.

    Aggregates feature-level drift into corridor-level metrics
    with risk multiplier and actionable recommendations.
    """

    corridor: str = Field(
        ...,
        description="Trade corridor identifier",
        examples=["US-CN"],
    )
    drift_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregate drift score (0=stable, 1=critical)",
        examples=[0.32],
    )
    drift_bucket: Literal["STABLE", "MINOR", "MODERATE", "SEVERE", "CRITICAL"] = Field(
        ...,
        description="Categorical drift severity bucket",
        examples=["MODERATE"],
    )
    risk_multiplier: float = Field(
        ...,
        ge=1.0,
        description="Risk adjustment multiplier derived from drift",
        examples=[1.45],
    )
    sample_count_baseline: int = Field(
        ...,
        ge=0,
        description="Number of samples in baseline distribution",
        examples=[10000],
    )
    sample_count_current: int = Field(
        ...,
        ge=0,
        description="Number of samples in current window",
        examples=[500],
    )
    top_drifting_features: List[str] = Field(
        default_factory=list,
        description="Top 5 features contributing to drift",
        examples=[["eta_deviation_hours", "num_route_deviations", "delay_flag"]],
    )
    feature_count: int = Field(
        ...,
        ge=0,
        description="Total number of features analyzed",
        examples=[15],
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable recommendations based on drift analysis",
    )
    window_start: Optional[datetime] = Field(
        None,
        description="Start of current analysis window",
    )
    window_end: Optional[datetime] = Field(
        None,
        description="End of current analysis window",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "corridor": "US-CN",
                "drift_score": 0.32,
                "drift_bucket": "MODERATE",
                "risk_multiplier": 1.45,
                "sample_count_baseline": 10000,
                "sample_count_current": 500,
                "top_drifting_features": [
                    "eta_deviation_hours",
                    "num_route_deviations",
                    "delay_flag",
                ],
                "feature_count": 15,
                "recommendations": [
                    "Schedule model retraining within 7 days.",
                    "Review top drifting features for data quality issues.",
                ],
                "window_start": "2025-12-01T00:00:00Z",
                "window_end": "2025-12-11T00:00:00Z",
            }
        }


class CorridorDriftDetailResponse(CorridorDriftResponse):
    """
    Extended corridor drift response with full feature breakdowns.

    Used for detailed analysis endpoints requiring per-feature metrics.
    """

    feature_drifts: List[FeatureDriftResponse] = Field(
        default_factory=list,
        description="Detailed drift analysis for each feature",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL DRIFT SUMMARY SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class GlobalDriftSummaryResponse(BaseModel):
    """
    System-wide drift summary across all corridors.

    Provides executive-level view of model health and drift status.
    """

    overall_drift_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average drift score across all corridors",
        examples=[0.18],
    )
    overall_bucket: Literal["STABLE", "MINOR", "MODERATE", "SEVERE", "CRITICAL"] = Field(
        ...,
        description="System-wide drift severity bucket",
        examples=["MINOR"],
    )
    corridors_analyzed: int = Field(
        ...,
        ge=0,
        description="Total corridors included in analysis",
        examples=[12],
    )
    corridors_drifting: int = Field(
        ...,
        ge=0,
        description="Corridors with drift above MINOR threshold",
        examples=[3],
    )
    top_drifting_corridors: List[str] = Field(
        default_factory=list,
        description="Top 5 corridors by drift score",
        examples=[["US-CN", "EU-IN", "US-MX"]],
    )
    top_drifting_features: List[str] = Field(
        default_factory=list,
        description="Top 10 features by total drift contribution",
        examples=[["eta_deviation_hours", "delay_flag"]],
    )
    computed_at: datetime = Field(
        ...,
        description="Timestamp when analysis was computed",
    )
    cache_ttl_seconds: int = Field(
        300,
        description="Cache time-to-live for this response",
        examples=[300],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "overall_drift_score": 0.18,
                "overall_bucket": "MINOR",
                "corridors_analyzed": 12,
                "corridors_drifting": 3,
                "top_drifting_corridors": ["US-CN", "EU-IN", "US-MX"],
                "top_drifting_features": ["eta_deviation_hours", "delay_flag"],
                "computed_at": "2025-12-11T10:30:00Z",
                "cache_ttl_seconds": 300,
            }
        }


class GlobalDriftDetailResponse(GlobalDriftSummaryResponse):
    """
    Extended global drift response with per-corridor breakdowns.

    Used for admin dashboards requiring full visibility.
    """

    corridor_results: List[CorridorDriftResponse] = Field(
        default_factory=list,
        description="Drift results for each corridor analyzed",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class DriftScoreRequest(BaseModel):
    """
    Request schema for computing drift score.

    Optionally specify corridor filter and time window.
    """

    corridor: Optional[str] = Field(
        None,
        description="Filter to specific corridor (None=all corridors)",
        examples=["US-CN"],
    )
    hours: int = Field(
        24,
        ge=1,
        le=720,
        description="Analysis window in hours (default: 24)",
        examples=[24],
    )
    include_features: bool = Field(
        False,
        description="Include per-feature drift breakdowns",
    )


class CorridorListRequest(BaseModel):
    """
    Request schema for listing corridor drift scores.
    """

    hours: int = Field(
        24,
        ge=1,
        le=720,
        description="Analysis window in hours",
        examples=[24],
    )
    min_samples: int = Field(
        10,
        ge=1,
        description="Minimum samples required for valid analysis",
        examples=[10],
    )
    drift_bucket_filter: Optional[Literal["STABLE", "MINOR", "MODERATE", "SEVERE", "CRITICAL"]] = Field(
        None,
        description="Filter to corridors matching this bucket or higher",
        examples=["MODERATE"],
    )


class FeatureListRequest(BaseModel):
    """
    Request schema for listing feature drift scores.
    """

    corridor: Optional[str] = Field(
        None,
        description="Filter to specific corridor (None=aggregate)",
        examples=["US-CN"],
    )
    hours: int = Field(
        24,
        ge=1,
        le=720,
        description="Analysis window in hours",
        examples=[24],
    )
    top_n: int = Field(
        10,
        ge=1,
        le=100,
        description="Return top N drifting features",
        examples=[10],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE STATUS SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════


class CacheStatsResponse(BaseModel):
    """
    IQCache statistics response.
    """

    total_entries: int = Field(
        ...,
        description="Total entries in cache (including expired)",
    )
    valid_entries: int = Field(
        ...,
        description="Non-expired entries in cache",
    )
    expired_entries: int = Field(
        ...,
        description="Expired entries pending cleanup",
    )
    hit_rate: Optional[float] = Field(
        None,
        description="Cache hit rate (if tracking enabled)",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def serialize_feature_drift(drift_result) -> FeatureDriftResponse:
    """
    Convert FeatureDriftResult dataclass to Pydantic response model.
    """
    return FeatureDriftResponse(
        feature_name=drift_result.feature_name,
        baseline_mean=drift_result.baseline_mean,
        current_mean=drift_result.current_mean,
        baseline_std=drift_result.baseline_std,
        current_std=drift_result.current_std,
        shift_delta=drift_result.shift_delta,
        shift_direction=drift_result.shift_direction.value,
        psi_score=drift_result.psi_score,
        ks_statistic=drift_result.ks_statistic,
        drift_bucket=drift_result.drift_bucket.value,
        contribution_rank=drift_result.contribution_rank,
        explanation=drift_result.explanation,
    )


def serialize_corridor_drift(
    drift_result,
    include_features: bool = False,
) -> CorridorDriftResponse | CorridorDriftDetailResponse:
    """
    Convert CorridorDriftResult dataclass to Pydantic response model.
    """
    base_response = dict(
        corridor=drift_result.corridor,
        drift_score=drift_result.drift_score,
        drift_bucket=drift_result.drift_bucket.value,
        risk_multiplier=drift_result.risk_multiplier,
        sample_count_baseline=drift_result.sample_count_baseline,
        sample_count_current=drift_result.sample_count_current,
        top_drifting_features=drift_result.top_drifting_features,
        feature_count=len(drift_result.feature_drifts),
        recommendations=drift_result.recommendations,
        window_start=drift_result.window_start,
        window_end=drift_result.window_end,
    )

    if include_features:
        return CorridorDriftDetailResponse(
            **base_response,
            feature_drifts=[serialize_feature_drift(fd) for fd in drift_result.feature_drifts],
        )

    return CorridorDriftResponse(**base_response)


def serialize_global_drift(
    summary,
    include_corridors: bool = False,
) -> GlobalDriftSummaryResponse | GlobalDriftDetailResponse:
    """
    Convert GlobalDriftSummary dataclass to Pydantic response model.
    """
    base_response = dict(
        overall_drift_score=summary.overall_drift_score,
        overall_bucket=summary.overall_bucket.value,
        corridors_analyzed=summary.corridors_analyzed,
        corridors_drifting=summary.corridors_drifting,
        top_drifting_corridors=summary.top_drifting_corridors,
        top_drifting_features=summary.top_drifting_features,
        computed_at=summary.computed_at,
        cache_ttl_seconds=summary.cache_ttl_seconds,
    )

    if include_corridors:
        return GlobalDriftDetailResponse(
            **base_response,
            corridor_results=[serialize_corridor_drift(cr, include_features=False) for cr in summary.corridor_results],
        )

    return GlobalDriftSummaryResponse(**base_response)
