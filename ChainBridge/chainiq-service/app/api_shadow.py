"""
Shadow Mode API Endpoints

HTTP API for Shadow Mode monitoring and analytics.
ALEX-compliant: no model loading in request path, fast responses, strict validation.

Endpoints:
- GET /iq/shadow/stats - Aggregated statistics
- GET /iq/shadow/events - Recent shadow events
- GET /iq/shadow/corridors - Corridor-level analysis
- GET /iq/shadow/drift - Drift detection metrics
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analysis.corridor_analysis import analyze_all_corridors, identify_drift_corridors
from app.analysis.shadow_diff import analyze_model_drift, compute_shadow_statistics, get_high_delta_events
from app.database import get_db
from app.repositories.shadow_repo import ShadowRepo
from app.schemas_shadow import (
    ShadowCorridorsResponse,
    ShadowCorridorStatsResponse,
    ShadowDriftResponse,
    ShadowEventResponse,
    ShadowEventsResponse,
    ShadowStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iq/shadow", tags=["Shadow Mode"])


@router.get(
    "/stats",
    response_model=ShadowStatsResponse,
    summary="Get shadow mode statistics",
    description="Returns aggregated P50/P95/P99 metrics for model score deltas. ALEX-compliant fast query.",
)
def get_shadow_stats(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours (max: 7 days)"),
    db: Session = Depends(get_db),
) -> ShadowStatsResponse:
    """
    Get aggregated shadow mode statistics.

    Computes mean, median, P95, P99 deltas between dummy and real model scores.
    Includes drift detection (P95 > 0.25 threshold).

    Performance: O(log n) query with indexed timestamps.
    ALEX-compliant: no model loading, uses repository layer only.

    Args:
        hours: Time window for analysis (1-168 hours)
        db: Database session (injected)

    Returns:
        ShadowStatsResponse with aggregated metrics

    Raises:
        HTTPException: 500 if computation fails
    """
    try:
        logger.info(f"Computing shadow stats for {hours}h window")

        # compute_shadow_statistics doesn't have lookback_hours parameter
        # It returns most recent events by default
        stats = compute_shadow_statistics(db, corridor=None, limit=None)

        if not stats or stats["count"] == 0:
            # Return zero stats if no data
            return ShadowStatsResponse(
                count=0,
                mean_delta=0.0,
                median_delta=0.0,
                std_delta=0.0,
                p50_delta=0.0,
                p95_delta=0.0,
                p99_delta=0.0,
                max_delta=0.0,
                drift_flag=False,
                model_version="v0.2.0",
                time_window_hours=hours,
            )

        return ShadowStatsResponse(
            count=stats["count"],
            mean_delta=stats["mean_delta"],
            median_delta=stats["median_delta"],
            std_delta=stats["std_delta"],
            p50_delta=stats["p50_delta"],
            p95_delta=stats["p95_delta"],
            p99_delta=stats["p99_delta"],
            max_delta=stats["max_delta"],
            drift_flag=bool(stats["drift_flag"]),
            model_version="v0.2.0",
            time_window_hours=hours,
        )

    except Exception as e:
        logger.error(f"Failed to compute shadow stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compute shadow statistics")


@router.get(
    "/events",
    response_model=ShadowEventsResponse,
    summary="Get shadow mode events",
    description="Returns recent shadow events with optional corridor filter. ALEX-compliant paginated query.",
)
def get_shadow_events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    corridor: Optional[str] = Query(None, description="Filter by corridor (e.g., US-CN)"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    db: Session = Depends(get_db),
) -> ShadowEventsResponse:
    """
    Get recent shadow mode events.

    Returns list of shadow events with optional corridor filtering.
    Useful for detailed event inspection and debugging.

    Performance: O(log n) query with indexed timestamps and corridor.
    ALEX-compliant: no model loading, pure database query.

    Args:
        limit: Maximum number of events to return (1-1000)
        corridor: Optional corridor filter (e.g., "US-CN")
        hours: Time window for query (1-168 hours)
        db: Database session (injected)

    Returns:
        ShadowEventsResponse with event list and metadata

    Raises:
        HTTPException: 500 if query fails
    """
    try:
        logger.info(f"Fetching shadow events: limit={limit}, corridor={corridor}, hours={hours}")

        repo = ShadowRepo(db)

        if corridor:
            events = repo.get_by_corridor(corridor, limit=limit, hours=hours)
        else:
            events = repo.get_recent_events(limit=limit, corridor=None)

        # Convert ORM models to Pydantic schemas
        event_responses = [
            ShadowEventResponse(
                id=event.id,
                shipment_id=event.shipment_id,
                dummy_score=event.dummy_score,
                real_score=event.real_score,
                delta=event.delta,
                model_version=event.model_version,
                corridor=event.corridor,
                created_at=event.created_at,
            )
            for event in events
        ]

        # Get total count
        total_count = repo.count_events(corridor=corridor)

        return ShadowEventsResponse(
            events=event_responses,
            total_count=total_count,
            limit=limit,
            corridor=corridor,
            model_version="v0.2.0",
            time_window_hours=hours,
        )

    except Exception as e:
        logger.error(f"Failed to fetch shadow events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch shadow events")


@router.get(
    "/corridors",
    response_model=ShadowCorridorsResponse,
    summary="Get corridor-level statistics",
    description="Returns statistics for all corridors with drift detection. ALEX-compliant aggregation.",
)
def get_corridor_stats(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    min_events: int = Query(10, ge=1, le=100, description="Minimum events for valid statistics"),
    db: Session = Depends(get_db),
) -> ShadowCorridorsResponse:
    """
    Get corridor-level shadow mode statistics.

    Analyzes all corridors with sufficient data volume and identifies
    regions with model drift (P95 > 0.25).

    Useful for:
    - Prioritizing model retraining efforts
    - Regional performance monitoring
    - Corridor-specific model tuning validation

    Performance: O(k log n) where k = number of corridors
    ALEX-compliant: no model loading, aggregation only.

    Args:
        hours: Time window for analysis (1-168 hours)
        min_events: Minimum events required per corridor (1-100)
        db: Database session (injected)

    Returns:
        ShadowCorridorsResponse with per-corridor statistics

    Raises:
        HTTPException: 500 if analysis fails
    """
    try:
        logger.info(f"Analyzing corridors: hours={hours}, min_events={min_events}")

        all_corridors = analyze_all_corridors(db, hours=hours, min_events=min_events)
        drifting = identify_drift_corridors(db, hours=hours, min_events=min_events)

        corridor_responses = [
            ShadowCorridorStatsResponse(
                corridor=stats["corridor"],
                event_count=stats["event_count"],
                mean_delta=stats["mean_delta"],
                median_delta=stats["median_delta"],
                p95_delta=stats["p95_delta"],
                max_delta=stats["max_delta"],
                drift_flag=stats["drift_flag"],
                time_window_hours=stats["time_window_hours"],
            )
            for stats in all_corridors
        ]

        return ShadowCorridorsResponse(
            corridors=corridor_responses,
            total_corridors=len(corridor_responses),
            drifting_count=len(drifting),
            model_version="v0.2.0",
            time_window_hours=hours,
        )

    except Exception as e:
        logger.error(f"Failed to analyze corridors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze corridors")


@router.get(
    "/drift",
    response_model=ShadowDriftResponse,
    summary="Get drift detection metrics",
    description="Analyzes model drift using P95 threshold. ALEX-compliant fast computation.",
)
def get_drift_analysis(
    lookback_hours: int = Query(24, ge=1, le=168, description="Analysis time window"),
    threshold: float = Query(0.25, ge=0.0, le=1.0, description="P95 drift threshold"),
    db: Session = Depends(get_db),
) -> ShadowDriftResponse:
    """
    Get model drift analysis.

    Detects significant drift between dummy and real models using P95 threshold.
    Returns drift flag and high-delta event counts.

    Drift detection logic:
    - drift_detected = True if P95(delta) > threshold
    - Default threshold = 0.25 (25% score difference)

    Performance: O(log n) query with percentile computation
    ALEX-compliant: no model loading, statistical analysis only.

    Args:
        lookback_hours: Time window for analysis (1-168 hours)
        threshold: P95 threshold for drift detection (0.0-1.0)
        db: Database session (injected)

    Returns:
        ShadowDriftResponse with drift metrics

    Raises:
        HTTPException: 500 if analysis fails
    """
    try:
        logger.info(f"Analyzing drift: lookback={lookback_hours}h, threshold={threshold}")

        drift = analyze_model_drift(db, lookback_hours=lookback_hours)

        if not drift or not drift.get("drift_detected", False):
            # Get basic stats for P95
            stats = compute_shadow_statistics(db, corridor=None, limit=None)
            p95 = stats["p95_delta"] if stats else 0.0

            # Return no-drift response
            return ShadowDriftResponse(
                drift_detected=False,
                p95_delta=p95,
                high_delta_count=0,
                total_events=drift.get("recent_count", 0) if drift else 0,
                model_version="v0.2.0",
                lookback_hours=lookback_hours,
                drift_threshold=threshold,
            )

        # Drift detected - get P95 from recent data
        p95_delta = drift.get("recent_p95", 0.0)

        # Count high-delta events
        high_delta = get_high_delta_events(db, threshold=threshold, limit=1000)

        return ShadowDriftResponse(
            drift_detected=True,
            p95_delta=p95_delta,
            high_delta_count=len(high_delta),
            total_events=drift.get("recent_count", 0),
            model_version="v0.2.0",
            lookback_hours=lookback_hours,
            drift_threshold=threshold,
        )

    except Exception as e:
        logger.error(f"Failed to analyze drift: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze drift")
