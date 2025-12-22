"""
Artifact Store - Thread-safe in-memory store with JSON file persistence.

Features:
- CRUD operations for Artifacts
- Append-only audit events per artifact
- Optional filtering on list operations
- Atomic JSON persistence (write to temp, then rename)
- Thread-safe via Lock
- Configurable storage path via CHAINBRIDGE_ARTIFACT_STORE_PATH env var
"""

import json
import logging
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.occ.schemas.artifact import Artifact, ArtifactCreate, ArtifactStatus, ArtifactType, ArtifactUpdate
from core.occ.schemas.audit_event import AuditEvent, AuditEventCreate, AuditEventType

logger = logging.getLogger(__name__)

# Default storage path (relative to working directory)
DEFAULT_STORE_PATH = "./data/artifacts.json"


class ArtifactStore:
    """
    Thread-safe artifact store with JSON file persistence and audit events.

    Usage:
        store = ArtifactStore()
        artifact = store.create(ArtifactCreate(name="My Plan", artifact_type=ArtifactType.PLAN))
        events = store.get_events(artifact.id)
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the store.

        Args:
            storage_path: Path to JSON persistence file. Defaults to
                          CHAINBRIDGE_ARTIFACT_STORE_PATH env var or ./data/artifacts.json
        """
        self._lock = threading.Lock()
        self._artifacts: Dict[UUID, Artifact] = {}
        self._events: Dict[UUID, List[AuditEvent]] = {}  # artifact_id -> list of events

        # Resolve storage path
        self._storage_path = Path(storage_path or os.environ.get("CHAINBRIDGE_ARTIFACT_STORE_PATH", DEFAULT_STORE_PATH))

        # Load existing data if file exists
        self._load()

    def _load(self) -> None:
        """Load artifacts and events from JSON file if it exists."""
        if not self._storage_path.exists():
            logger.info(f"Artifact store file not found at {self._storage_path}; starting fresh.")
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Support both old format (list of artifacts) and new format (dict with artifacts + events)
            if isinstance(data, list):
                # Old format: just artifacts
                for item in data:
                    artifact = Artifact.model_validate(item)
                    self._artifacts[artifact.id] = artifact
                    self._events[artifact.id] = []
            elif isinstance(data, dict):
                # New format: {"artifacts": [...], "events": {...}}
                for item in data.get("artifacts", []):
                    artifact = Artifact.model_validate(item)
                    self._artifacts[artifact.id] = artifact

                for artifact_id_str, event_list in data.get("events", {}).items():
                    artifact_id = UUID(artifact_id_str)
                    self._events[artifact_id] = [AuditEvent.model_validate(e) for e in event_list]

                # Ensure all artifacts have event lists
                for artifact_id in self._artifacts:
                    if artifact_id not in self._events:
                        self._events[artifact_id] = []

            logger.info(f"Loaded {len(self._artifacts)} artifacts from {self._storage_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse artifact store JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to load artifact store: {e}")

    def _persist(self) -> None:
        """Persist artifacts and events to JSON file atomically."""
        # Ensure directory exists
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize all artifacts and events
        data = {
            "artifacts": [artifact.model_dump(mode="json") for artifact in self._artifacts.values()],
            "events": {
                str(artifact_id): [event.model_dump(mode="json") for event in events] for artifact_id, events in self._events.items()
            },
        }

        # Atomic write: write to temp file, then rename
        fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="artifacts_", dir=self._storage_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            # Atomic rename (on POSIX systems)
            os.replace(tmp_path, self._storage_path)
            logger.debug(f"Persisted {len(data['artifacts'])} artifacts to {self._storage_path}")
        except Exception as e:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            logger.error(f"Failed to persist artifacts: {e}")
            raise

    def _emit_event(
        self,
        artifact_id: UUID,
        event_type: AuditEventType,
        actor: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Internal method to emit an audit event. Must be called within lock.

        Args:
            artifact_id: The artifact this event belongs to.
            event_type: Type of event.
            actor: Who/what triggered the event.
            details: Additional event details.

        Returns:
            The created AuditEvent.
        """
        event = AuditEvent(
            artifact_id=artifact_id,
            event_type=event_type,
            actor=actor or "system",
            details=details or {},
        )

        if artifact_id not in self._events:
            self._events[artifact_id] = []
        self._events[artifact_id].append(event)

        return event

    def create(self, artifact_create: ArtifactCreate, actor: Optional[str] = None) -> Artifact:
        """
        Create a new artifact with server-generated ID and timestamps.
        Automatically emits a CREATED audit event.

        Args:
            artifact_create: The artifact creation schema.
            actor: Who/what is creating the artifact.

        Returns:
            The created Artifact with all fields populated.
        """
        artifact = Artifact(
            **artifact_create.model_dump(),
        )

        with self._lock:
            self._artifacts[artifact.id] = artifact
            self._events[artifact.id] = []

            # Emit CREATED event
            self._emit_event(
                artifact_id=artifact.id,
                event_type=AuditEventType.CREATED,
                actor=actor,
                details={
                    "name": artifact.name,
                    "artifact_type": artifact.artifact_type,
                    "status": artifact.status,
                },
            )

            self._persist()

        logger.info(f"Created artifact: id={artifact.id}, name={artifact.name}, type={artifact.artifact_type}")
        return artifact

    def get(self, artifact_id: UUID) -> Optional[Artifact]:
        """
        Retrieve an artifact by ID.

        Args:
            artifact_id: The UUID of the artifact.

        Returns:
            The Artifact if found, None otherwise.
        """
        with self._lock:
            return self._artifacts.get(artifact_id)

    def list(
        self,
        artifact_type: Optional[ArtifactType] = None,
        status: Optional[ArtifactStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Artifact]:
        """
        List artifacts with optional filtering.

        Args:
            artifact_type: Filter by artifact type.
            status: Filter by status.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching Artifacts.
        """
        with self._lock:
            results = list(self._artifacts.values())

        # Apply filters
        if artifact_type is not None:
            # Handle both enum and string values
            type_value = artifact_type.value if isinstance(artifact_type, ArtifactType) else artifact_type
            results = [a for a in results if a.artifact_type == type_value]

        if status is not None:
            # Handle both enum and string values
            status_value = status.value if isinstance(status, ArtifactStatus) else status
            results = [a for a in results if a.status == status_value]

        # Sort by created_at descending (newest first)
        results.sort(key=lambda a: a.created_at, reverse=True)

        # Apply pagination
        if offset:
            results = results[offset:]
        if limit is not None:
            results = results[:limit]

        return results

    def update(
        self,
        artifact_id: UUID,
        update: ArtifactUpdate,
        actor: Optional[str] = None,
    ) -> Optional[Artifact]:
        """
        Update an artifact with partial data.
        Automatically emits an UPDATED audit event.

        Args:
            artifact_id: The UUID of the artifact to update.
            update: The partial update schema.
            actor: Who/what is performing the update.

        Returns:
            The updated Artifact if found, None otherwise.
        """
        with self._lock:
            existing = self._artifacts.get(artifact_id)
            if existing is None:
                return None

            # Capture changes for audit
            update_data = update.model_dump(exclude_unset=True)
            changes = {}
            for key, new_value in update_data.items():
                old_value = getattr(existing, key, None)
                if old_value != new_value:
                    changes[key] = {"old": old_value, "new": new_value}

            updated = existing.apply_update(update)
            self._artifacts[artifact_id] = updated

            # Emit UPDATED event with change details
            event_type = AuditEventType.UPDATED
            if "status" in changes:
                # Also emit specific status change event type
                new_status = changes["status"]["new"]
                if new_status == ArtifactStatus.APPROVED.value:
                    event_type = AuditEventType.APPROVED
                elif new_status == ArtifactStatus.REJECTED.value:
                    event_type = AuditEventType.REJECTED
                elif new_status == ArtifactStatus.LOCKED.value:
                    event_type = AuditEventType.LOCKED

            self._emit_event(
                artifact_id=artifact_id,
                event_type=event_type,
                actor=actor,
                details={"changes": changes},
            )

            self._persist()

        logger.info(f"Updated artifact: id={artifact_id}")
        return updated

    def delete(self, artifact_id: UUID, actor: Optional[str] = None) -> bool:
        """
        Delete an artifact by ID.
        Emits a DELETED event before removal (tombstone pattern).

        Args:
            artifact_id: The UUID of the artifact to delete.
            actor: Who/what is deleting the artifact.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            if artifact_id not in self._artifacts:
                return False

            artifact = self._artifacts[artifact_id]

            # Emit DELETED event before removal
            self._emit_event(
                artifact_id=artifact_id,
                event_type=AuditEventType.DELETED,
                actor=actor,
                details={
                    "name": artifact.name,
                    "artifact_type": artifact.artifact_type,
                    "final_status": artifact.status,
                },
            )

            del self._artifacts[artifact_id]
            # Keep events for deleted artifacts (tombstone/audit trail)
            self._persist()

        logger.info(f"Deleted artifact: id={artifact_id}")
        return True

    def clear(self) -> int:
        """
        Clear all artifacts. Useful for testing.

        Returns:
            Number of artifacts deleted.
        """
        with self._lock:
            count = len(self._artifacts)
            self._artifacts.clear()
            self._events.clear()
            self._persist()

        logger.info(f"Cleared {count} artifacts from store")
        return count

    # -------------------------------------------------------------------------
    # Audit Event Methods
    # -------------------------------------------------------------------------

    def get_events(self, artifact_id: UUID) -> List[AuditEvent]:
        """
        Get all audit events for an artifact, sorted by timestamp ascending.

        Args:
            artifact_id: The artifact ID.

        Returns:
            List of AuditEvent sorted oldest-first.
        """
        with self._lock:
            events = self._events.get(artifact_id, [])
            # Return a copy sorted by timestamp (oldest first for timeline)
            return sorted(events, key=lambda e: e.timestamp)

    def add_event(
        self,
        artifact_id: UUID,
        event_create: AuditEventCreate,
    ) -> Optional[AuditEvent]:
        """
        Manually append an audit event (for system/internal use).
        Events are append-only and cannot be modified.

        Args:
            artifact_id: The artifact ID.
            event_create: The event to add.

        Returns:
            The created AuditEvent, or None if artifact doesn't exist.
        """
        with self._lock:
            # Check artifact exists (or has event history for deleted artifacts)
            if artifact_id not in self._artifacts and artifact_id not in self._events:
                return None

            event = AuditEvent(
                artifact_id=artifact_id,
                **event_create.model_dump(),
            )

            if artifact_id not in self._events:
                self._events[artifact_id] = []
            self._events[artifact_id].append(event)
            self._persist()

        logger.info(f"Added audit event: artifact_id={artifact_id}, type={event.event_type}")
        return event

    def event_count(self, artifact_id: UUID) -> int:
        """Get the number of events for an artifact."""
        with self._lock:
            return len(self._events.get(artifact_id, []))

    def list_all_events(
        self,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        """
        Get recent audit events across ALL artifacts.

        Useful for real-time event streams and dashboards.

        Args:
            limit: Maximum number of events to return.
            since: Only return events after this timestamp.

        Returns:
            List of AuditEvent sorted by timestamp descending (newest first).
        """
        with self._lock:
            all_events: List[AuditEvent] = []
            for events in self._events.values():
                all_events.extend(events)

        # Filter by timestamp if provided
        if since is not None:
            all_events = [e for e in all_events if e.timestamp > since]

        # Sort by timestamp descending (newest first)
        all_events.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply limit
        return all_events[:limit]


# Singleton instance for dependency injection
_store_instance: Optional[ArtifactStore] = None
_store_lock = threading.Lock()


def get_artifact_store() -> ArtifactStore:
    """
    Get the singleton ArtifactStore instance.

    This is the recommended way to access the store in FastAPI dependencies.
    """
    global _store_instance
    if _store_instance is None:
        with _store_lock:
            if _store_instance is None:
                _store_instance = ArtifactStore()
    return _store_instance
