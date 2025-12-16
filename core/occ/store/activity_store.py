"""
Agent Activity Store - Append-only, thread-safe store with JSON persistence.

Glass-box design: Nothing happens without a trace.

Features:
- APPEND-ONLY: Activities cannot be modified or deleted
- Thread-safe via Lock
- Monotonic sequence numbers for ordering
- JSON file persistence
- SSE subscriber support for real-time streaming
- Linked to artifact IDs for traceability
"""

import asyncio
import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from core.occ.schemas.activity import ActivityStats, ActivityStatus, ActivityType, AgentActivity, AgentActivityCreate

logger = logging.getLogger(__name__)

# Default storage path
DEFAULT_STORE_PATH = "./data/agent_activities.json"


def _enum_value(value: Any) -> Any:
    """Return raw value for enums (or passthrough for plain strings)."""
    return value.value if hasattr(value, "value") else value


class AgentActivityStore:
    """
    Append-only, thread-safe activity store.

    Key invariant: Activities are IMMUTABLE once created.
    - No update operations
    - No delete operations
    - Every activity gets a monotonic sequence number

    Usage:
        store = AgentActivityStore()
        activity = store.append(AgentActivityCreate(...))
        activities = store.list(agent_gid="GID-01")
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the store.

        Args:
            storage_path: Path to JSON persistence file. Defaults to
                          CHAINBRIDGE_ACTIVITY_STORE_PATH env var or ./data/agent_activities.json
        """
        self._lock = threading.Lock()
        self._activities: List[AgentActivity] = []
        self._sequence_counter: int = 0

        # SSE subscribers: set of async queues
        self._subscribers: Set[asyncio.Queue] = set()
        self._subscriber_lock = threading.Lock()

        # Resolve storage path
        self._storage_path = Path(storage_path or os.environ.get("CHAINBRIDGE_ACTIVITY_STORE_PATH", DEFAULT_STORE_PATH))

        # Load existing data
        self._load()

    def _load(self) -> None:
        """Load activities from JSON file if it exists."""
        if not self._storage_path.exists():
            logger.info(f"Activity store file not found at {self._storage_path}; starting fresh.")
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                # Expected format: {"activities": [...], "sequence": int}
                for item in data.get("activities", []):
                    activity = AgentActivity.model_validate(item)
                    self._activities.append(activity)
                self._sequence_counter = data.get("sequence", len(self._activities))
            elif isinstance(data, list):
                # Legacy format: just a list
                for item in data:
                    activity = AgentActivity.model_validate(item)
                    self._activities.append(activity)
                self._sequence_counter = len(self._activities)

            logger.info(f"Loaded {len(self._activities)} activities from {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to load activities: {e}")

    def _persist(self) -> None:
        """Persist activities to JSON file (atomic write)."""
        try:
            # Ensure directory exists
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize
            data = {
                "activities": [a.model_dump(mode="json") for a in self._activities],
                "sequence": self._sequence_counter,
            }

            # Atomic write: temp file then rename
            fd, tmp_path = tempfile.mkstemp(dir=self._storage_path.parent, prefix=".activities_", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                os.replace(tmp_path, self._storage_path)
            except Exception:
                # Clean up temp file on error
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
        except Exception as e:
            logger.error(f"Failed to persist activities: {e}")

    def append(self, activity_in: AgentActivityCreate) -> AgentActivity:
        """
        Append a new activity to the store.

        This is the ONLY write operation. Activities are immutable.

        Args:
            activity_in: Activity creation data

        Returns:
            The created AgentActivity with server-generated fields
        """
        with self._lock:
            # Increment sequence counter (monotonic)
            self._sequence_counter += 1

            # Create activity with server-generated fields
            activity = AgentActivity(
                agent_gid=activity_in.agent_gid,
                activity_type=activity_in.activity_type,
                artifact_id=activity_in.artifact_id,
                status=activity_in.status,
                summary=activity_in.summary,
                details=activity_in.details,
                correlation_id=activity_in.correlation_id,
                timestamp=datetime.now(timezone.utc),
                sequence=self._sequence_counter,
            )

            # Append (never modify, never delete)
            self._activities.append(activity)

            # Persist
            self._persist()

            type_label = _enum_value(activity.activity_type)
            logger.info(f"Activity appended: {activity.agent_gid}/{type_label} seq={activity.sequence}")

        # Notify SSE subscribers (outside lock to avoid blocking)
        self._notify_subscribers(activity)

        return activity

    def get(self, activity_id: UUID) -> Optional[AgentActivity]:
        """Get a specific activity by ID."""
        with self._lock:
            for activity in self._activities:
                if activity.id == activity_id:
                    return activity
        return None

    def list(
        self,
        agent_gid: Optional[str] = None,
        activity_type: Optional[ActivityType] = None,
        artifact_id: Optional[UUID] = None,
        status: Optional[ActivityStatus] = None,
        since_sequence: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[AgentActivity]:
        """
        List activities with optional filtering.

        Args:
            agent_gid: Filter by agent GID
            activity_type: Filter by activity type
            artifact_id: Filter by related artifact ID
            status: Filter by status
            since_sequence: Only return activities with sequence > this value
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            List of matching activities, ordered by sequence (oldest first)
        """
        with self._lock:
            # Start with all activities
            result = self._activities.copy()

        # Apply filters
        if agent_gid is not None:
            result = [a for a in result if a.agent_gid.upper() == agent_gid.upper()]

        if activity_type is not None:
            target_type = _enum_value(activity_type)
            result = [a for a in result if _enum_value(a.activity_type) == target_type]

        if artifact_id is not None:
            result = [a for a in result if a.artifact_id == artifact_id]

        if status is not None:
            target_status = _enum_value(status)
            result = [a for a in result if _enum_value(a.status) == target_status]

        if since_sequence is not None:
            result = [a for a in result if a.sequence > since_sequence]

        # Sort by sequence (ascending)
        result = sorted(result, key=lambda a: a.sequence)

        # Apply pagination
        if offset > 0:
            result = result[offset:]

        if limit is not None:
            result = result[:limit]

        return result

    def count(
        self,
        agent_gid: Optional[str] = None,
        activity_type: Optional[ActivityType] = None,
        artifact_id: Optional[UUID] = None,
    ) -> int:
        """Count activities matching filters."""
        return len(
            self.list(
                agent_gid=agent_gid,
                activity_type=activity_type,
                artifact_id=artifact_id,
            )
        )

    def stats(self) -> ActivityStats:
        """Get aggregate statistics about activities."""
        with self._lock:
            if not self._activities:
                return ActivityStats()

            by_type: Dict[str, int] = {}
            by_agent: Dict[str, int] = {}
            by_status: Dict[str, int] = {}

            for a in self._activities:
                # By type
                type_key = _enum_value(a.activity_type)
                by_type[type_key] = by_type.get(type_key, 0) + 1

                # By agent
                by_agent[a.agent_gid] = by_agent.get(a.agent_gid, 0) + 1

                # By status
                status_key = _enum_value(a.status)
                by_status[status_key] = by_status.get(status_key, 0) + 1

            # Timestamps
            sorted_activities = sorted(self._activities, key=lambda a: a.timestamp)

            return ActivityStats(
                total=len(self._activities),
                by_type=by_type,
                by_agent=by_agent,
                by_status=by_status,
                oldest_timestamp=sorted_activities[0].timestamp if sorted_activities else None,
                newest_timestamp=sorted_activities[-1].timestamp if sorted_activities else None,
            )

    def get_latest_sequence(self) -> int:
        """Get the latest sequence number."""
        with self._lock:
            return self._sequence_counter

    # =========================================================================
    # SSE SUBSCRIBER SUPPORT
    # =========================================================================

    def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to real-time activity updates.

        Returns an asyncio.Queue that will receive new activities.
        Caller must call unsubscribe() when done.
        """
        queue: asyncio.Queue = asyncio.Queue()
        with self._subscriber_lock:
            self._subscribers.add(queue)
        logger.info(f"SSE subscriber added (total: {len(self._subscribers)})")
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from real-time updates."""
        with self._subscriber_lock:
            self._subscribers.discard(queue)
        logger.info(f"SSE subscriber removed (total: {len(self._subscribers)})")

    def _notify_subscribers(self, activity: AgentActivity) -> None:
        """Notify all SSE subscribers of a new activity."""
        with self._subscriber_lock:
            dead_queues = []
            for queue in self._subscribers:
                try:
                    # Non-blocking put (will be processed by async handler)
                    queue.put_nowait(activity)
                except asyncio.QueueFull:
                    logger.warning("SSE subscriber queue full, dropping activity")
                except Exception as e:
                    logger.error(f"Failed to notify subscriber: {e}")
                    dead_queues.append(queue)

            # Clean up dead subscribers
            for q in dead_queues:
                self._subscribers.discard(q)


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

# Singleton instance
_activity_store: Optional[AgentActivityStore] = None
_store_lock = threading.Lock()


def get_activity_store() -> AgentActivityStore:
    """
    Get the singleton AgentActivityStore instance.

    Thread-safe lazy initialization.
    """
    global _activity_store

    if _activity_store is None:
        with _store_lock:
            if _activity_store is None:
                _activity_store = AgentActivityStore()

    return _activity_store


def reset_activity_store() -> None:
    """Reset the singleton store (useful for testing)."""
    global _activity_store
    with _store_lock:
        _activity_store = None
