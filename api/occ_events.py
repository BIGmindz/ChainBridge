"""
OCC Event Stream — PAC-BENSON-P33

Doctrine Law 4, §4.3: Read-only event stream for OCC replay.

Provides:
- WebSocket /ws/events — Real-time event stream
- Event types: decision, proof, settlement state changes

INVARIANTS:
- INV-OCC-001: Read-only (no write capability)
- INV-OCC-002: Events are immutable
- INV-OCC-003: All events include timestamp and source

Author: CODY (GID-01) — Backend Implementation
Security: SAM (GID-06) — Read-only enforcement
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["OCC Event Stream"])


# =============================================================================
# EVENT TYPES (Doctrine-aligned)
# =============================================================================


class OCCEventType(str, Enum):
    """OCC event types for the event stream."""
    # Decision events
    DECISION_CREATED = "decision.created"
    DECISION_APPROVED = "decision.approved"
    DECISION_REJECTED = "decision.rejected"
    DECISION_ESCALATED = "decision.escalated"

    # Proof events
    PROOF_GENERATED = "proof.generated"
    PROOF_SIGNED = "proof.signed"
    PROOF_VERIFIED = "proof.verified"
    PROOF_FAILED = "proof.failed"

    # Settlement events
    SETTLEMENT_INITIATED = "settlement.initiated"
    SETTLEMENT_PENDING = "settlement.pending"
    SETTLEMENT_COMPLETED = "settlement.completed"
    SETTLEMENT_FAILED = "settlement.failed"

    # Pipeline events
    PIPELINE_STAGE_ENTERED = "pipeline.stage.entered"
    PIPELINE_STAGE_COMPLETED = "pipeline.stage.completed"
    PIPELINE_BLOCKED = "pipeline.blocked"

    # Agent events
    AGENT_ACTIVATED = "agent.activated"
    AGENT_DEACTIVATED = "agent.deactivated"
    AGENT_TASK_STARTED = "agent.task.started"
    AGENT_TASK_COMPLETED = "agent.task.completed"

    # Governance events
    GOVERNANCE_VIOLATION = "governance.violation"
    GOVERNANCE_ALERT = "governance.alert"
    PAC_ISSUED = "pac.issued"
    WRAP_SUBMITTED = "wrap.submitted"
    BER_ISSUED = "ber.issued"

    # System events
    SYSTEM_HEARTBEAT = "system.heartbeat"
    SYSTEM_ERROR = "system.error"


class OCCEvent(BaseModel):
    """
    OCC Event schema — immutable event record.

    All events are read-only and include:
    - Unique event ID
    - Event type
    - Timestamp (UTC ISO-8601)
    - Source identifier
    - Payload data
    """
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: OCCEventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = Field(description="Source of the event (agent GID, system, etc.)")
    entity_id: Optional[str] = Field(default=None, description="Related entity ID if applicable")
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


# =============================================================================
# EVENT STREAM MANAGER
# =============================================================================


class OCCEventStreamManager:
    """
    Manages WebSocket connections and event broadcasting.

    Thread-safe manager for:
    - Connection tracking
    - Event broadcasting
    - Subscription filtering
    """

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._subscriptions: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()
        self._event_log: List[OCCEvent] = []
        self._max_log_size = 1000  # Keep last 1000 events for replay

    async def connect(self, websocket: WebSocket, event_types: Optional[List[str]] = None):
        """Register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
            # Set subscription filter (empty = all events)
            self._subscriptions[websocket] = set(event_types) if event_types else set()
        logger.info(f"WebSocket connected: {len(self._connections)} active connections")

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self._connections.discard(websocket)
            self._subscriptions.pop(websocket, None)
        logger.info(f"WebSocket disconnected: {len(self._connections)} active connections")

    async def broadcast(self, event: OCCEvent):
        """Broadcast an event to all subscribed connections."""
        # Add to event log for replay
        async with self._lock:
            self._event_log.append(event)
            # Trim log if too large
            if len(self._event_log) > self._max_log_size:
                self._event_log = self._event_log[-self._max_log_size:]

        # Serialize event
        event_json = event.model_dump_json()

        # Broadcast to all connections
        disconnected = []
        async with self._lock:
            connections = list(self._connections)
            subscriptions = dict(self._subscriptions)

        for ws in connections:
            # Check subscription filter
            filters = subscriptions.get(ws, set())
            if filters and event.event_type not in filters:
                continue  # Skip if not subscribed to this event type

            try:
                await ws.send_text(event_json)
            except Exception as e:
                logger.warning(f"Failed to send event to WebSocket: {e}")
                disconnected.append(ws)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws)

    async def get_recent_events(
        self,
        limit: int = 100,
        event_types: Optional[List[str]] = None,
        since: Optional[str] = None,
    ) -> List[OCCEvent]:
        """
        Get recent events from the log.

        Args:
            limit: Maximum number of events to return
            event_types: Filter by event types
            since: Return events after this ISO timestamp

        Returns:
            List of matching events (most recent last)
        """
        async with self._lock:
            events = list(self._event_log)

        # Apply filters
        if event_types:
            events = [e for e in events if e.event_type in event_types]

        if since:
            events = [e for e in events if e.timestamp > since]

        # Apply limit (from most recent)
        return events[-limit:]

    @property
    def connection_count(self) -> int:
        """Get current connection count."""
        return len(self._connections)


# Global event stream manager
_event_manager = OCCEventStreamManager()


def get_event_manager() -> OCCEventStreamManager:
    """Get the global event stream manager."""
    return _event_manager


# =============================================================================
# EVENT EMISSION API (for internal use)
# =============================================================================


async def emit_occ_event(
    event_type: OCCEventType,
    source: str,
    entity_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> OCCEvent:
    """
    Emit an OCC event to all subscribers.

    This is the internal API for emitting events from other modules.

    Args:
        event_type: Type of event
        source: Source identifier (agent GID, system, etc.)
        entity_id: Related entity ID if applicable
        payload: Event payload data

    Returns:
        The emitted event
    """
    event = OCCEvent(
        event_type=event_type,
        source=source,
        entity_id=entity_id,
        payload=payload or {},
    )
    await _event_manager.broadcast(event)
    logger.debug(f"Emitted OCC event: {event_type} from {source}")
    return event


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================


@router.websocket("/ws/events")
async def occ_event_stream(
    websocket: WebSocket,
    event_types: Optional[str] = Query(
        None,
        description="Comma-separated list of event types to subscribe to (empty = all)"
    ),
    replay_count: int = Query(
        0,
        description="Number of recent events to replay on connect (0 = none)"
    ),
):
    """
    WebSocket endpoint for real-time OCC event stream.

    Doctrine Law 4, §4.3: Read-only event stream for OCC replay.

    Connection Parameters:
    - event_types: Comma-separated filter (e.g., "decision.created,proof.generated")
    - replay_count: Number of recent events to replay on connect

    Event Format (JSON):
    {
        "event_id": "uuid",
        "event_type": "decision.created",
        "timestamp": "2026-01-02T12:00:00Z",
        "source": "GID-01",
        "entity_id": "optional-entity-id",
        "payload": { ... }
    }

    INVARIANT: This is a READ-ONLY stream. No write operations are accepted.
    """
    # Parse event type filter
    filter_types = None
    if event_types:
        filter_types = [t.strip() for t in event_types.split(",")]

    # Connect
    manager = get_event_manager()
    await manager.connect(websocket, filter_types)

    try:
        # Replay recent events if requested
        if replay_count > 0:
            recent = await manager.get_recent_events(
                limit=replay_count,
                event_types=filter_types,
            )
            for event in recent:
                await websocket.send_text(event.model_dump_json())

        # Keep connection alive and listen for disconnect
        while True:
            try:
                # Wait for any message (we ignore it — read-only)
                message = await websocket.receive_text()

                # Log but ignore — this is a read-only stream
                logger.debug(f"Received message on read-only stream (ignored): {message[:100]}")

                # Send acknowledgment that we're read-only
                await websocket.send_json({
                    "type": "warning",
                    "message": "This is a read-only event stream. Messages are ignored.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)


# =============================================================================
# REST ENDPOINTS (for non-WebSocket access)
# =============================================================================


@router.get("/events/recent")
async def get_recent_events(
    limit: int = Query(100, le=1000, description="Maximum events to return"),
    event_types: Optional[str] = Query(None, description="Comma-separated event type filter"),
    since: Optional[str] = Query(None, description="Return events after this ISO timestamp"),
) -> dict:
    """
    Get recent OCC events via REST.

    Doctrine Law 4, §4.3: Decision history with filtering.

    This is an alternative to the WebSocket stream for polling-based access.
    """
    manager = get_event_manager()

    filter_types = None
    if event_types:
        filter_types = [t.strip() for t in event_types.split(",")]

    events = await manager.get_recent_events(
        limit=limit,
        event_types=filter_types,
        since=since,
    )

    return {
        "events": [e.model_dump() for e in events],
        "count": len(events),
        "has_more": len(events) == limit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/events/types")
async def get_event_types() -> dict:
    """
    Get all available event types.

    Useful for UI dropdowns and subscription configuration.
    """
    return {
        "event_types": [
            {
                "type": e.value,
                "category": e.value.split(".")[0],
                "action": e.value.split(".")[1] if "." in e.value else e.value,
            }
            for e in OCCEventType
        ],
        "categories": list(set(e.value.split(".")[0] for e in OCCEventType)),
    }


@router.get("/events/stream/status")
async def get_stream_status() -> dict:
    """
    Get event stream status.

    Returns connection count and stream health.
    """
    manager = get_event_manager()
    return {
        "active_connections": manager.connection_count,
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
