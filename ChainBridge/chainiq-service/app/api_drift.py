"""
ChainIQ Drift API v1.1

REST endpoints for drift detection, scoring, and feature attribution.
Provides real-time model health monitoring for ChainIQ ML models.

Endpoints:
- GET /iq/drift/score - Global or corridor-specific drift score
- GET /iq/drift/corridors - List corridor drift scores
- GET /iq/drift/features - List feature drift contributions
- GET /iq/drift/cache/stats - Cache statistics (admin)
- POST /iq/drift/cache/invalidate - Clear drift cache (admin)

Author: Cody (GID-01) 🔵
PAC: CODY-PAC-NEXT-034
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from app.ml.drift_engine import categorical_drift_bucket, compute_global_drift_summary, corridor_drift_score, get_drift_cache
from app.serializers.drift_explain import (
    CacheStatsResponse,
    CorridorDriftDetailResponse,
    CorridorDriftResponse,
    FeatureDriftResponse,
    GlobalDriftSummaryResponse,
    serialize_corridor_drift,
    serialize_feature_drift,
    serialize_global_drift,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iq/drift", tags=["ChainIQ Drift"])


# ═══════════════════════════════════════════════════════════════════════════════
# SAMPLE DATA (Mock for development - replace with real data source)
# ═══════════════════════════════════════════════════════════════════════════════


def _get_baseline_stats() -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Return baseline statistics by corridor and feature.

    In production, this would query a feature store or database.
    """
    # Common features across corridors
    feature_baselines = {
        "eta_deviation_hours": {"mean": 5.0, "std": 2.0, "count": 10000},
        "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 10000},
        "planned_transit_hours": {"mean": 72.0, "std": 24.0, "count": 10000},
        "total_dwell_hours": {"mean": 8.0, "std": 4.0, "count": 10000},
        "delay_flag": {"mean": 0.15, "std": 0.36, "count": 10000},
        "shipper_on_time_pct_90d": {"mean": 88.0, "std": 8.0, "count": 10000},
        "carrier_on_time_pct_90d": {"mean": 85.0, "std": 10.0, "count": 10000},
        "missing_required_docs": {"mean": 0.3, "std": 0.7, "count": 10000},
        "max_custody_gap_hours": {"mean": 2.0, "std": 1.5, "count": 10000},
        "lane_sentiment_score": {"mean": 0.65, "std": 0.15, "count": 10000},
    }

    # Per-corridor baselines (with slight variations)
    corridors = ["US-CN", "EU-IN", "US-MX", "EU-UK", "APAC-US", "LATAM-EU"]

    baseline_stats = {}
    for corridor in corridors:
        baseline_stats[corridor] = {
            feat: {
                "mean": stats["mean"],
                "std": stats["std"],
                "count": stats["count"],
            }
            for feat, stats in feature_baselines.items()
        }

    return baseline_stats


def _get_current_stats() -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Return current window statistics by corridor and feature.

    In production, this would query recent data from the warehouse.
    """
    # Simulate drift in some corridors
    current_stats = {}

    # US-CN: Moderate drift in delay-related features
    current_stats["US-CN"] = {
        "eta_deviation_hours": {"mean": 8.2, "std": 3.1, "count": 500},  # Drifted
        "num_route_deviations": {"mean": 2.1, "std": 1.5, "count": 500},  # Drifted
        "planned_transit_hours": {"mean": 74.0, "std": 25.0, "count": 500},
        "total_dwell_hours": {"mean": 10.5, "std": 5.0, "count": 500},  # Drifted
        "delay_flag": {"mean": 0.22, "std": 0.41, "count": 500},  # Drifted
        "shipper_on_time_pct_90d": {"mean": 84.0, "std": 9.0, "count": 500},
        "carrier_on_time_pct_90d": {"mean": 82.0, "std": 11.0, "count": 500},
        "missing_required_docs": {"mean": 0.35, "std": 0.8, "count": 500},
        "max_custody_gap_hours": {"mean": 2.5, "std": 2.0, "count": 500},
        "lane_sentiment_score": {"mean": 0.58, "std": 0.18, "count": 500},  # Drifted
    }

    # EU-IN: Minor drift
    current_stats["EU-IN"] = {
        "eta_deviation_hours": {"mean": 5.5, "std": 2.2, "count": 300},
        "num_route_deviations": {"mean": 1.6, "std": 1.3, "count": 300},
        "planned_transit_hours": {"mean": 73.0, "std": 24.5, "count": 300},
        "total_dwell_hours": {"mean": 8.5, "std": 4.2, "count": 300},
        "delay_flag": {"mean": 0.16, "std": 0.37, "count": 300},
        "shipper_on_time_pct_90d": {"mean": 87.0, "std": 8.5, "count": 300},
        "carrier_on_time_pct_90d": {"mean": 84.0, "std": 10.5, "count": 300},
        "missing_required_docs": {"mean": 0.32, "std": 0.72, "count": 300},
        "max_custody_gap_hours": {"mean": 2.1, "std": 1.6, "count": 300},
        "lane_sentiment_score": {"mean": 0.63, "std": 0.16, "count": 300},
    }

    # US-MX: Stable
    current_stats["US-MX"] = {
        "eta_deviation_hours": {"mean": 5.1, "std": 2.0, "count": 800},
        "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 800},
        "planned_transit_hours": {"mean": 72.5, "std": 24.0, "count": 800},
        "total_dwell_hours": {"mean": 8.1, "std": 4.0, "count": 800},
        "delay_flag": {"mean": 0.15, "std": 0.36, "count": 800},
        "shipper_on_time_pct_90d": {"mean": 88.0, "std": 8.0, "count": 800},
        "carrier_on_time_pct_90d": {"mean": 85.0, "std": 10.0, "count": 800},
        "missing_required_docs": {"mean": 0.30, "std": 0.70, "count": 800},
        "max_custody_gap_hours": {"mean": 2.0, "std": 1.5, "count": 800},
        "lane_sentiment_score": {"mean": 0.65, "std": 0.15, "count": 800},
    }

    # EU-UK: Stable
    current_stats["EU-UK"] = {
        "eta_deviation_hours": {"mean": 4.9, "std": 1.9, "count": 600},
        "num_route_deviations": {"mean": 1.4, "std": 1.1, "count": 600},
        "planned_transit_hours": {"mean": 71.0, "std": 23.0, "count": 600},
        "total_dwell_hours": {"mean": 7.8, "std": 3.8, "count": 600},
        "delay_flag": {"mean": 0.14, "std": 0.35, "count": 600},
        "shipper_on_time_pct_90d": {"mean": 89.0, "std": 7.5, "count": 600},
        "carrier_on_time_pct_90d": {"mean": 86.0, "std": 9.5, "count": 600},
        "missing_required_docs": {"mean": 0.28, "std": 0.68, "count": 600},
        "max_custody_gap_hours": {"mean": 1.9, "std": 1.4, "count": 600},
        "lane_sentiment_score": {"mean": 0.67, "std": 0.14, "count": 600},
    }

    # APAC-US: Severe drift
    current_stats["APAC-US"] = {
        "eta_deviation_hours": {"mean": 12.0, "std": 5.0, "count": 200},  # Severe
        "num_route_deviations": {"mean": 3.2, "std": 2.1, "count": 200},  # Severe
        "planned_transit_hours": {"mean": 80.0, "std": 30.0, "count": 200},
        "total_dwell_hours": {"mean": 15.0, "std": 7.0, "count": 200},  # Severe
        "delay_flag": {"mean": 0.35, "std": 0.48, "count": 200},  # Severe
        "shipper_on_time_pct_90d": {"mean": 78.0, "std": 12.0, "count": 200},
        "carrier_on_time_pct_90d": {"mean": 75.0, "std": 14.0, "count": 200},
        "missing_required_docs": {"mean": 0.6, "std": 1.0, "count": 200},  # Drifted
        "max_custody_gap_hours": {"mean": 4.0, "std": 3.0, "count": 200},  # Drifted
        "lane_sentiment_score": {"mean": 0.45, "std": 0.22, "count": 200},  # Severe
    }

    # LATAM-EU: Minor drift
    current_stats["LATAM-EU"] = {
        "eta_deviation_hours": {"mean": 5.8, "std": 2.3, "count": 150},
        "num_route_deviations": {"mean": 1.7, "std": 1.3, "count": 150},
        "planned_transit_hours": {"mean": 74.0, "std": 25.0, "count": 150},
        "total_dwell_hours": {"mean": 9.0, "std": 4.5, "count": 150},
        "delay_flag": {"mean": 0.18, "std": 0.38, "count": 150},
        "shipper_on_time_pct_90d": {"mean": 86.0, "std": 9.0, "count": 150},
        "carrier_on_time_pct_90d": {"mean": 83.0, "std": 11.0, "count": 150},
        "missing_required_docs": {"mean": 0.35, "std": 0.75, "count": 150},
        "max_custody_gap_hours": {"mean": 2.3, "std": 1.8, "count": 150},
        "lane_sentiment_score": {"mean": 0.62, "std": 0.16, "count": 150},
    }

    return current_stats


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/score",
    response_model=GlobalDriftSummaryResponse | CorridorDriftDetailResponse,
    summary="Get drift score",
    description="Compute global or corridor-specific drift score with optional feature breakdown.",
)
async def get_drift_score(
    corridor: Optional[str] = Query(
        None,
        description="Filter to specific corridor (None=global summary)",
        examples=["US-CN"],
    ),
    hours: int = Query(
        24,
        ge=1,
        le=720,
        description="Analysis window in hours",
    ),
    include_features: bool = Query(
        False,
        description="Include per-feature drift breakdowns",
    ),
) -> GlobalDriftSummaryResponse | CorridorDriftDetailResponse:
    """
    Get drift score for a specific corridor or global summary.

    Business Purpose:
    Monitor model health and detect when retraining is needed.

    Decision Context:
    "Is our ML model still reliable, or has data drift degraded performance?"

    Returns:
    - drift_score: 0-1 (higher = more drift)
    - drift_bucket: STABLE, MINOR, MODERATE, SEVERE, CRITICAL
    - risk_multiplier: Adjustment factor for predictions
    - recommendations: Actionable next steps

    Example:
        GET /iq/drift/score?corridor=US-CN&include_features=true
    """
    try:
        # Check cache first
        cache = get_drift_cache()
        cache_key = f"drift_score:{corridor or 'global'}:{hours}:{include_features}"

        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for drift score: {cache_key}")
            return cached

        # Load statistics (in production, query from database/feature store)
        baseline_stats = _get_baseline_stats()
        current_stats = _get_current_stats()

        if corridor:
            # Corridor-specific analysis
            if corridor not in baseline_stats or corridor not in current_stats:
                raise HTTPException(
                    status_code=404,
                    detail=f"Corridor '{corridor}' not found",
                )

            result = corridor_drift_score(
                baseline_stats=baseline_stats[corridor],
                current_stats=current_stats[corridor],
            )
            result.corridor = corridor
            result.window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
            result.window_end = datetime.now(timezone.utc)

            response = serialize_corridor_drift(result, include_features=include_features)
        else:
            # Global analysis
            summary = compute_global_drift_summary(
                corridor_baselines=baseline_stats,
                corridor_currents=current_stats,
            )

            response = serialize_global_drift(summary, include_corridors=include_features)

        # Cache result
        cache.set(cache_key, response, ttl_seconds=300)

        logger.info(
            f"Drift score computed: corridor={corridor or 'global'}, "
            f"score={getattr(response, 'drift_score', getattr(response, 'overall_drift_score', 0)):.3f}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compute drift score: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Drift score computation failed: {str(e)}",
        ) from e


@router.get(
    "/corridors",
    response_model=List[CorridorDriftResponse],
    summary="List corridor drift scores",
    description="Get drift scores for all corridors, optionally filtered by severity.",
)
async def list_corridor_drifts(
    hours: int = Query(
        24,
        ge=1,
        le=720,
        description="Analysis window in hours",
    ),
    min_samples: int = Query(
        10,
        ge=1,
        description="Minimum samples required for valid analysis",
    ),
    drift_bucket_filter: Optional[Literal["STABLE", "MINOR", "MODERATE", "SEVERE", "CRITICAL"]] = Query(
        None,
        description="Filter to corridors at or above this drift bucket",
    ),
) -> List[CorridorDriftResponse]:
    """
    List drift scores for all monitored corridors.

    Business Purpose:
    Prioritize corridors for model retraining and investigation.

    Returns:
    - List of corridor drift scores sorted by severity (highest first)

    Example:
        GET /iq/drift/corridors?drift_bucket_filter=MODERATE
    """
    try:
        # Check cache
        cache = get_drift_cache()
        cache_key = f"drift_corridors:{hours}:{min_samples}:{drift_bucket_filter}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Load statistics
        baseline_stats = _get_baseline_stats()
        current_stats = _get_current_stats()

        # Compute drift for all corridors
        results = []
        for corridor in baseline_stats.keys():
            if corridor not in current_stats:
                continue

            # Check sample count
            sample_count = current_stats[corridor].get(list(current_stats[corridor].keys())[0], {}).get("count", 0)

            if sample_count < min_samples:
                continue

            result = corridor_drift_score(
                baseline_stats=baseline_stats[corridor],
                current_stats=current_stats[corridor],
            )
            result.corridor = corridor
            result.window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
            result.window_end = datetime.now(timezone.utc)

            # Apply bucket filter
            if drift_bucket_filter:
                bucket_order = ["STABLE", "MINOR", "MODERATE", "SEVERE", "CRITICAL"]
                min_idx = bucket_order.index(drift_bucket_filter)
                result_idx = bucket_order.index(result.drift_bucket.value)

                if result_idx < min_idx:
                    continue

            results.append(serialize_corridor_drift(result, include_features=False))

        # Sort by drift score descending
        results.sort(key=lambda x: x.drift_score, reverse=True)

        # Cache results
        cache.set(cache_key, results, ttl_seconds=300)

        logger.info(f"Corridor drift list returned {len(results)} corridors")

        return results

    except Exception as e:
        logger.error(f"Failed to list corridor drifts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Corridor drift listing failed: {str(e)}",
        ) from e


@router.get(
    "/features",
    response_model=List[FeatureDriftResponse],
    summary="List feature drift contributions",
    description="Get drift scores for individual features, ranked by contribution.",
)
async def list_feature_drifts(
    corridor: Optional[str] = Query(
        None,
        description="Filter to specific corridor (None=aggregate across all)",
        examples=["US-CN"],
    ),
    hours: int = Query(
        24,
        ge=1,
        le=720,
        description="Analysis window in hours",
    ),
    top_n: int = Query(
        10,
        ge=1,
        le=100,
        description="Return top N drifting features",
    ),
) -> List[FeatureDriftResponse]:
    """
    List feature drift contributions for attribution analysis.

    Business Purpose:
    Identify which features are causing model drift for targeted investigation.

    Returns:
    - List of feature drift scores ranked by contribution (highest first)

    Example:
        GET /iq/drift/features?corridor=US-CN&top_n=5
    """
    try:
        # Check cache
        cache = get_drift_cache()
        cache_key = f"drift_features:{corridor or 'global'}:{hours}:{top_n}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Load statistics
        baseline_stats = _get_baseline_stats()
        current_stats = _get_current_stats()

        if corridor:
            # Corridor-specific feature analysis
            if corridor not in baseline_stats or corridor not in current_stats:
                raise HTTPException(
                    status_code=404,
                    detail=f"Corridor '{corridor}' not found",
                )

            result = corridor_drift_score(
                baseline_stats=baseline_stats[corridor],
                current_stats=current_stats[corridor],
            )

            feature_responses = [serialize_feature_drift(fd) for fd in result.feature_drifts[:top_n]]
        else:
            # Aggregate feature analysis across corridors
            summary = compute_global_drift_summary(
                corridor_baselines=baseline_stats,
                corridor_currents=current_stats,
            )

            # Aggregate feature drifts across all corridors
            feature_totals: Dict[str, List] = {}
            for cr in summary.corridor_results:
                for fd in cr.feature_drifts:
                    if fd.feature_name not in feature_totals:
                        feature_totals[fd.feature_name] = []
                    feature_totals[fd.feature_name].append(fd)

            # Average feature drifts
            aggregated_features = []
            for feat_name, drifts in feature_totals.items():
                avg_drift = drifts[0]  # Use first as template
                avg_drift.shift_delta = sum(d.shift_delta for d in drifts) / len(drifts)
                avg_drift.psi_score = sum(d.psi_score for d in drifts) / len(drifts)
                avg_drift.drift_bucket = categorical_drift_bucket(avg_drift.shift_delta)
                aggregated_features.append(avg_drift)

            # Sort by drift and re-rank
            aggregated_features.sort(key=lambda x: x.shift_delta, reverse=True)
            for rank, fd in enumerate(aggregated_features, start=1):
                fd.contribution_rank = rank

            feature_responses = [serialize_feature_drift(fd) for fd in aggregated_features[:top_n]]

        # Cache results
        cache.set(cache_key, feature_responses, ttl_seconds=300)

        logger.info(f"Feature drift list returned {len(feature_responses)} features")

        return feature_responses

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list feature drifts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Feature drift listing failed: {str(e)}",
        ) from e


@router.get(
    "/cache/stats",
    response_model=CacheStatsResponse,
    summary="Get cache statistics",
    description="Admin endpoint for monitoring IQCache health.",
    tags=["Admin"],
)
async def get_cache_stats() -> CacheStatsResponse:
    """
    Get IQCache statistics for monitoring.

    Admin endpoint for cache health monitoring.
    """
    cache = get_drift_cache()
    stats = cache.stats()

    return CacheStatsResponse(
        total_entries=stats["total_entries"],
        valid_entries=stats["valid_entries"],
        expired_entries=stats["expired_entries"],
    )


@router.post(
    "/cache/invalidate",
    summary="Invalidate drift cache",
    description="Admin endpoint to clear drift cache entries.",
    tags=["Admin"],
)
async def invalidate_cache(
    pattern: Optional[str] = Query(
        None,
        description="Invalidate entries matching this prefix (None=all)",
        examples=["drift_score:US-CN"],
    ),
) -> Dict[str, Any]:
    """
    Invalidate drift cache entries.

    Admin endpoint for cache management.
    """
    cache = get_drift_cache()

    if pattern:
        count = cache.invalidate_pattern(pattern)
        return {"invalidated": count, "pattern": pattern}
    else:
        cache.clear()
        return {"invalidated": "all", "pattern": None}
