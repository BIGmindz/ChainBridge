"""
Shadow Mode Repository

Handles persistence of shadow mode scoring events to the database.
Provides atomic, safe writes with no blocking of production scoring paths.

Version 0.3 Enhancements:
- Corridor-level filtering and statistics
- Model version tracking and comparison
- High delta event identification
- Time-series analysis support
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.models_shadow import RiskShadowEvent

logger = logging.getLogger(__name__)


class ShadowRepo:
    """
    Repository for shadow mode event persistence.

    Responsibilities:
    - Log shadow scoring events to database
    - Ensure atomic writes (commit or rollback)
    - Handle errors gracefully without breaking production paths
    - Provide query interface for analysis
    """

    def __init__(self, db: Session):
        """
        Initialize the repository.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def log_event(
        self,
        shipment_id: str,
        dummy_score: float,
        real_score: float,
        model_version: str,
        corridor: Optional[str] = None,
    ) -> Optional[RiskShadowEvent]:
        """
        Log a shadow scoring event to the database.

        Computes the delta (absolute difference) and persists the event.
        Uses atomic commit - if write fails, rolls back without exception.

        Args:
            shipment_id: Unique shipment identifier
            dummy_score: Score from DummyRiskModel [0,1]
            real_score: Score from RealRiskModel_v0.2 [0,1]
            model_version: Version identifier (e.g., 'v0.2.0')
            corridor: Optional trade corridor for segmented analysis

        Returns:
            RiskShadowEvent instance if successful, None if failed

        Example:
            >>> repo = ShadowRepo(session)
            >>> event = repo.log_event(
            ...     shipment_id="SH-001",
            ...     dummy_score=0.75,
            ...     real_score=0.82,
            ...     model_version="v0.2.0",
            ...     corridor="US-MX"
            ... )
            >>> print(f"Delta: {event.delta:.4f}")
            Delta: 0.0700
        """
        try:
            delta = abs(dummy_score - real_score)

            event = RiskShadowEvent(
                shipment_id=shipment_id,
                dummy_score=dummy_score,
                real_score=real_score,
                delta=delta,
                model_version=model_version,
                corridor=corridor,
            )

            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)

            logger.debug(f"Shadow event logged: shipment={shipment_id}, " f"delta={delta:.4f}, version={model_version}")

            return event

        except Exception as e:
            logger.error(f"Failed to log shadow event: {e}", exc_info=True)
            self.db.rollback()
            return None

    def get_recent_events(self, limit: int = 100, corridor: Optional[str] = None) -> list[RiskShadowEvent]:
        """
        Retrieve recent shadow events for analysis.

        Args:
            limit: Maximum number of events to return
            corridor: Optional filter by corridor

        Returns:
            List of RiskShadowEvent instances, ordered by created_at DESC
        """
        try:
            query = self.db.query(RiskShadowEvent)

            if corridor:
                query = query.filter(RiskShadowEvent.corridor == corridor)

            events = query.order_by(RiskShadowEvent.created_at.desc()).limit(limit).all()

            return events

        except Exception as e:
            logger.error(f"Failed to query shadow events: {e}", exc_info=True)
            return []

    def count_events(self, corridor: Optional[str] = None) -> int:
        """
        Count total shadow events, optionally filtered by corridor.

        Args:
            corridor: Optional filter by corridor

        Returns:
            Total event count
        """
        try:
            query = self.db.query(RiskShadowEvent)

            if corridor:
                query = query.filter(RiskShadowEvent.corridor == corridor)

            return query.count()

        except Exception as e:
            logger.error(f"Failed to count shadow events: {e}", exc_info=True)
            return 0

    def get_by_corridor(self, corridor: str, limit: int = 100, hours: int = 24) -> list[RiskShadowEvent]:
        """
        Get shadow events filtered by corridor.

        Args:
            corridor: Trade corridor (e.g., "US-CN")
            limit: Maximum number of events to return
            hours: Time window in hours

        Returns:
            List of shadow events for the specified corridor
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            events = (
                self.db.query(RiskShadowEvent)
                .filter(and_(RiskShadowEvent.corridor == corridor, RiskShadowEvent.created_at >= since))
                .order_by(desc(RiskShadowEvent.created_at))
                .limit(limit)
                .all()
            )
            return events

        except Exception as e:
            logger.error(f"Failed to get events by corridor {corridor}: {e}")
            return []

    def get_by_model_version(self, model_version: str, limit: int = 100, hours: int = 24) -> list[RiskShadowEvent]:
        """
        Get shadow events filtered by model version.

        Args:
            model_version: Model version identifier (e.g., "v0.2.0")
            limit: Maximum number of events to return
            hours: Time window in hours

        Returns:
            List of shadow events for the specified model version
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            events = (
                self.db.query(RiskShadowEvent)
                .filter(and_(RiskShadowEvent.model_version == model_version, RiskShadowEvent.created_at >= since))
                .order_by(desc(RiskShadowEvent.created_at))
                .limit(limit)
                .all()
            )
            return events

        except Exception as e:
            logger.error(f"Failed to get events by model version {model_version}: {e}")
            return []

    def get_high_delta_events(
        self, threshold: float = 0.15, corridor: Optional[str] = None, limit: int = 50, hours: int = 24
    ) -> list[RiskShadowEvent]:
        """
        Get events with high score deltas between dummy and real models.

        Useful for identifying cases where models disagree significantly,
        which may indicate model drift or edge cases.

        Args:
            threshold: Minimum delta to consider "high" (default: 0.15)
            corridor: Optional corridor filter
            limit: Maximum number of events to return
            hours: Time window in hours

        Returns:
            List of high-delta shadow events, ordered by delta descending
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = self.db.query(RiskShadowEvent).filter(and_(RiskShadowEvent.delta >= threshold, RiskShadowEvent.created_at >= since))

            if corridor:
                query = query.filter(RiskShadowEvent.corridor == corridor)

            events = query.order_by(desc(RiskShadowEvent.delta)).limit(limit).all()
            return events

        except Exception as e:
            logger.error(f"Failed to get high delta events: {e}")
            return []

    def get_corridor_statistics(self, corridor: str, hours: int = 24) -> Dict[str, Any]:
        """
        Compute statistics for a specific corridor.

        Returns aggregated metrics like count, mean delta, P50/P95 deltas,
        and drift indicators for corridor-level monitoring.

        Args:
            corridor: Trade corridor (e.g., "US-CN")
            hours: Time window in hours

        Returns:
            Dictionary with corridor statistics:
            {
                "corridor": str,
                "event_count": int,
                "mean_delta": float,
                "median_delta": float,
                "p95_delta": float,
                "max_delta": float,
                "drift_flag": bool,
                "time_window_hours": int
            }
        """
        try:
            import numpy as np

            events = self.get_by_corridor(corridor, limit=1000, hours=hours)

            if not events:
                return {
                    "corridor": corridor,
                    "event_count": 0,
                    "mean_delta": 0.0,
                    "median_delta": 0.0,
                    "p95_delta": 0.0,
                    "max_delta": 0.0,
                    "drift_flag": False,
                    "time_window_hours": hours,
                }

            deltas = [e.delta for e in events]

            stats = {
                "corridor": corridor,
                "event_count": len(deltas),
                "mean_delta": float(np.mean(deltas)),
                "median_delta": float(np.percentile(deltas, 50)),
                "p95_delta": float(np.percentile(deltas, 95)),
                "max_delta": float(np.max(deltas)),
                "drift_flag": bool(np.percentile(deltas, 95) > 0.25),
                "time_window_hours": hours,
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to compute corridor statistics for {corridor}: {e}")
            return {
                "corridor": corridor,
                "event_count": 0,
                "mean_delta": 0.0,
                "median_delta": 0.0,
                "p95_delta": 0.0,
                "max_delta": 0.0,
                "drift_flag": False,
                "time_window_hours": hours,
            }
            return 0
