"""
Shadow Mode Discrepancy Analyzer

Computes statistical summaries of differences between dummy and real models.
Used for offline analysis and drift detection before promoting models to production.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models_shadow import RiskShadowEvent


def compute_shadow_statistics(db: Session, corridor: Optional[str] = None, limit: Optional[int] = None) -> Optional[dict]:
    """
    Compute statistical summary of shadow mode events.

    Calculates key metrics to assess real model performance vs dummy:
    - Total event count
    - Mean delta (average absolute difference)
    - P50, P95, P99 delta percentiles
    - Drift flag (P95 > 0.25 threshold)
    - Per-corridor breakdown if applicable

    Args:
        db: SQLAlchemy database session
        corridor: Optional filter by corridor
        limit: Optional limit on number of events to analyze (most recent)

    Returns:
        Dictionary with statistics, or None if no data available

    Example:
        >>> stats = compute_shadow_statistics(session)
        >>> print(f"Mean delta: {stats['mean_delta']:.4f}")
        >>> if stats['drift_flag']:
        ...     print("WARNING: High drift detected!")
    """
    try:
        import numpy as np

        # Query shadow events
        query = db.query(RiskShadowEvent)

        if corridor:
            query = query.filter(RiskShadowEvent.corridor == corridor)

        if limit:
            query = query.order_by(RiskShadowEvent.created_at.desc()).limit(limit)

        events = query.all()

        if not events:
            return None

        # Extract deltas
        deltas = [event.delta for event in events]

        # Compute statistics
        stats = {
            "count": len(deltas),
            "mean_delta": float(np.mean(deltas)),
            "median_delta": float(np.median(deltas)),
            "std_delta": float(np.std(deltas)),
            "p50_delta": float(np.percentile(deltas, 50)),
            "p95_delta": float(np.percentile(deltas, 95)),
            "p99_delta": float(np.percentile(deltas, 99)),
            "max_delta": float(np.max(deltas)),
            "drift_flag": np.percentile(deltas, 95) > 0.25,
            "corridor": corridor,
        }

        # Add per-corridor breakdown if not already filtered
        if not corridor:
            corridors = {}
            for event in events:
                if event.corridor:
                    if event.corridor not in corridors:
                        corridors[event.corridor] = []
                    corridors[event.corridor].append(event.delta)

            corridor_stats = {}
            for c, c_deltas in corridors.items():
                corridor_stats[c] = {
                    "count": len(c_deltas),
                    "mean_delta": float(np.mean(c_deltas)),
                    "p95_delta": float(np.percentile(c_deltas, 95)),
                }

            stats["by_corridor"] = corridor_stats

        return stats

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to compute shadow statistics: {e}", exc_info=True)
        return None


def get_high_delta_events(db: Session, threshold: float = 0.30, limit: int = 50) -> list[RiskShadowEvent]:
    """
    Retrieve shadow events with high deltas for investigation.

    Useful for identifying shipments where dummy and real models
    strongly disagree, indicating potential issues or edge cases.

    Args:
        db: SQLAlchemy database session
        threshold: Minimum delta to consider "high"
        limit: Maximum number of events to return

    Returns:
        List of RiskShadowEvent instances with delta >= threshold
    """
    try:
        events = (
            db.query(RiskShadowEvent).filter(RiskShadowEvent.delta >= threshold).order_by(RiskShadowEvent.delta.desc()).limit(limit).all()
        )

        return events

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to query high delta events: {e}", exc_info=True)
        return []


def analyze_model_drift(db: Session, lookback_hours: int = 24) -> dict:
    """
    Detect model drift by comparing recent vs historical performance.

    Args:
        db: SQLAlchemy database session
        lookback_hours: Hours of recent data to analyze

    Returns:
        Dictionary with drift analysis
    """
    try:
        from datetime import datetime, timedelta

        import numpy as np

        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)

        # Recent events
        recent = db.query(RiskShadowEvent).filter(RiskShadowEvent.created_at >= cutoff_time).all()

        # Historical events (prior to lookback window)
        historical = db.query(RiskShadowEvent).filter(RiskShadowEvent.created_at < cutoff_time).limit(1000).all()

        if not recent or not historical:
            return {"drift_detected": False, "reason": "Insufficient data"}

        recent_deltas = [e.delta for e in recent]
        historical_deltas = [e.delta for e in historical]

        recent_p95 = float(np.percentile(recent_deltas, 95))
        historical_p95 = float(np.percentile(historical_deltas, 95))

        drift_detected = recent_p95 > historical_p95 * 1.5  # 50% increase

        return {
            "drift_detected": drift_detected,
            "recent_p95": recent_p95,
            "historical_p95": historical_p95,
            "recent_count": len(recent_deltas),
            "historical_count": len(historical_deltas),
            "lookback_hours": lookback_hours,
        }

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to analyze drift: {e}", exc_info=True)
        return {"drift_detected": False, "reason": f"Error: {str(e)}"}
