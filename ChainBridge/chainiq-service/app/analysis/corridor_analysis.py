"""
Corridor-Level Shadow Mode Analytics

Provides statistical analysis and monitoring tools for shadow mode events
segmented by trade corridor.

Use Cases:
- Identify corridors with high model disagreement
- Track corridor-specific model drift
- Monitor regional model performance
- Support corridor-level model retraining decisions
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
from sqlalchemy.orm import Session

from app.models_shadow import RiskShadowEvent
from app.repositories.shadow_repo import ShadowRepo

logger = logging.getLogger(__name__)


def analyze_all_corridors(session: Session, hours: int = 24, min_events: int = 10) -> List[Dict[str, Any]]:
    """
    Analyze shadow mode events across all corridors.

    Computes statistics for each corridor with sufficient data volume.
    Useful for identifying regional patterns and prioritizing retraining.

    Args:
        session: Database session
        hours: Time window for analysis
        min_events: Minimum events required for valid statistics

    Returns:
        List of corridor statistics dictionaries, sorted by P95 delta descending

    Example:
        >>> stats = analyze_all_corridors(session, hours=24)
        >>> for stat in stats[:3]:
        ...     print(f"{stat['corridor']}: P95={stat['p95_delta']:.3f}")
        US-CN: P95=0.287
        EU-IN: P95=0.241
        US-MX: P95=0.189
    """
    try:
        repo = ShadowRepo(session)

        # Get all unique corridors with recent events
        since = datetime.utcnow() - timedelta(hours=hours)
        query = session.query(RiskShadowEvent.corridor).distinct()
        query = query.filter(RiskShadowEvent.created_at >= since)
        corridors = [row[0] for row in query.all() if row[0]]

        logger.info(f"Analyzing {len(corridors)} corridors over {hours}h window")

        # Compute statistics for each corridor
        corridor_stats = []
        for corridor in corridors:
            stats = repo.get_corridor_statistics(corridor, hours)

            # Only include corridors with sufficient data
            if stats["event_count"] >= min_events:
                corridor_stats.append(stats)

        # Sort by P95 delta (highest drift first)
        corridor_stats.sort(key=lambda x: x["p95_delta"], reverse=True)

        return corridor_stats

    except Exception as e:
        logger.error(f"Failed to analyze corridors: {e}")
        return []


def identify_drift_corridors(session: Session, hours: int = 24, p95_threshold: float = 0.25, min_events: int = 10) -> List[Dict[str, Any]]:
    """
    Identify corridors with potential model drift.

    Returns corridors where P95 delta exceeds threshold, indicating
    systematic disagreement between dummy and real models.

    Args:
        session: Database session
        hours: Time window for analysis
        p95_threshold: P95 delta threshold for drift flag (default: 0.25)
        min_events: Minimum events required for valid detection

    Returns:
        List of corridor statistics with drift_flag=True

    Example:
        >>> drifting = identify_drift_corridors(session)
        >>> if drifting:
        ...     print(f"⚠️  {len(drifting)} corridors show drift:")
        ...     for c in drifting:
        ...         print(f"  - {c['corridor']}: P95={c['p95_delta']:.3f}")
    """
    all_stats = analyze_all_corridors(session, hours, min_events)
    drifting_corridors = [s for s in all_stats if s["drift_flag"]]

    logger.info(f"Drift detection: {len(drifting_corridors)}/{len(all_stats)} " f"corridors exceed P95 threshold {p95_threshold}")

    return drifting_corridors


def compare_corridors(session: Session, corridor_a: str, corridor_b: str, hours: int = 24) -> Dict[str, Any]:
    """
    Compare shadow mode statistics between two corridors.

    Useful for understanding regional model performance differences
    and validating corridor-specific model tuning.

    Args:
        session: Database session
        corridor_a: First corridor identifier
        corridor_b: Second corridor identifier
        hours: Time window for analysis

    Returns:
        Comparison dictionary with statistics for both corridors

    Example:
        >>> comp = compare_corridors(session, "US-CN", "US-MX")
        >>> print(f"P95 Delta: {comp['corridor_a']['p95_delta']:.3f} vs "
        ...       f"{comp['corridor_b']['p95_delta']:.3f}")
    """
    try:
        repo = ShadowRepo(session)

        stats_a = repo.get_corridor_statistics(corridor_a, hours)
        stats_b = repo.get_corridor_statistics(corridor_b, hours)

        # Compute relative differences
        if stats_a["event_count"] > 0 and stats_b["event_count"] > 0:
            delta_diff = abs(stats_a["p95_delta"] - stats_b["p95_delta"])
            relative_drift = delta_diff / max(stats_a["p95_delta"], stats_b["p95_delta"])
        else:
            delta_diff = 0.0
            relative_drift = 0.0

        return {
            "corridor_a": stats_a,
            "corridor_b": stats_b,
            "p95_delta_difference": delta_diff,
            "relative_drift_difference": relative_drift,
            "time_window_hours": hours,
        }

    except Exception as e:
        logger.error(f"Failed to compare corridors {corridor_a} vs {corridor_b}: {e}")
        return {
            "corridor_a": {"corridor": corridor_a, "event_count": 0},
            "corridor_b": {"corridor": corridor_b, "event_count": 0},
            "p95_delta_difference": 0.0,
            "relative_drift_difference": 0.0,
            "time_window_hours": hours,
        }


def get_top_discrepancies(session: Session, corridor: str, limit: int = 10, hours: int = 24) -> List[RiskShadowEvent]:
    """
    Get top scoring discrepancies for a specific corridor.

    Returns shadow events with highest deltas, useful for case-by-case
    investigation of model disagreements.

    Args:
        session: Database session
        corridor: Trade corridor to analyze
        limit: Number of top events to return
        hours: Time window for analysis

    Returns:
        List of RiskShadowEvent instances ordered by delta descending

    Example:
        >>> events = get_top_discrepancies(session, "US-CN", limit=5)
        >>> for e in events:
        ...     print(f"Shipment {e.shipment_id}: Δ={e.delta:.3f}")
    """
    try:
        repo = ShadowRepo(session)
        events = repo.get_by_corridor(corridor, limit=1000, hours=hours)

        # Sort by delta descending
        events.sort(key=lambda e: e.delta, reverse=True)

        return events[:limit]

    except Exception as e:
        logger.error(f"Failed to get top discrepancies for {corridor}: {e}")
        return []


def compute_corridor_trend(session: Session, corridor: str, window_hours: int = 24, num_windows: int = 7) -> Dict[str, Any]:
    """
    Compute time-series trend of corridor deltas.

    Divides time range into windows and computes P95 delta for each,
    enabling trend detection (improving vs degrading model alignment).

    Args:
        session: Database session
        corridor: Trade corridor to analyze
        window_hours: Hours per time window
        num_windows: Number of time windows to analyze

    Returns:
        Trend analysis with time-series P95 deltas and trend indicator

    Example:
        >>> trend = compute_corridor_trend(session, "US-CN", window_hours=24, num_windows=7)
        >>> if trend["trend"] == "improving":
        ...     print(f"✓ {corridor} model alignment improving over 7 days")
    """
    try:
        # repo = ShadowRepo(session)

        # Compute P95 for each time window
        p95_series = []
        for i in range(num_windows):
            window_start = window_hours * (i + 1)
            window_end = window_hours * i

            # Get events in this window
            since = datetime.utcnow() - timedelta(hours=window_start)
            until = datetime.utcnow() - timedelta(hours=window_end)

            events = (
                session.query(RiskShadowEvent)
                .filter(RiskShadowEvent.corridor == corridor, RiskShadowEvent.created_at >= since, RiskShadowEvent.created_at < until)
                .all()
            )

            if events:
                deltas = [e.delta for e in events]
                p95 = float(np.percentile(deltas, 95))
                p95_series.append(p95)
            else:
                p95_series.append(None)

        # Reverse to get chronological order (oldest first)
        p95_series.reverse()

        # Compute trend
        valid_p95 = [p for p in p95_series if p is not None]
        if len(valid_p95) >= 2:
            # Simple linear trend
            slope = (valid_p95[-1] - valid_p95[0]) / len(valid_p95)
            if slope < -0.02:
                trend = "improving"
            elif slope > 0.02:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "corridor": corridor,
            "p95_series": p95_series,
            "trend": trend,
            "window_hours": window_hours,
            "num_windows": num_windows,
        }

    except Exception as e:
        logger.error(f"Failed to compute corridor trend for {corridor}: {e}")
        return {
            "corridor": corridor,
            "p95_series": [],
            "trend": "error",
            "window_hours": window_hours,
            "num_windows": num_windows,
        }
