"""
ChainBoard API - Projection Layer over OCC Artifacts & Audit Events

This module provides ChainBoard-specific views over the OCC data:
- GET /api/chainboard/alerts -> Projects OCC artifacts as alerts
- GET /api/chainboard/events/stream -> SSE stream of audit events

This is a READ-ONLY projection layer - no data duplication.
All mutations go through the canonical /occ/artifacts API.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.occ.schemas.artifact import Artifact, ArtifactStatus, ArtifactType
from core.occ.schemas.audit_event import AuditEvent
from core.occ.store.artifact_store import ArtifactStore, get_artifact_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chainboard", tags=["ChainBoard"])


# =============================================================================
# Alert Status Mapping
# =============================================================================

# Map ChainBoard alert statuses to OCC artifact statuses
ALERT_STATUS_MAP = {
    "open": [ArtifactStatus.DRAFT, ArtifactStatus.PENDING],
    "blocked": [ArtifactStatus.REJECTED],
    "resolved": [ArtifactStatus.APPROVED, ArtifactStatus.LOCKED],
    "all": None,  # No filter
}

# Artifact types that qualify as "alerts" for ChainBoard
ALERT_ARTIFACT_TYPES = [
    ArtifactType.DECISION,
    ArtifactType.COMPLIANCE_RECORD,
    ArtifactType.EXECUTION_RESULT,
]


# =============================================================================
# Response Schemas
# =============================================================================


class ChainBoardAlert(BaseModel):
    """Alert representation for ChainBoard UI."""

    id: UUID
    title: str
    description: Optional[str]
    severity: str  # Derived from artifact_type
    status: str  # Mapped from OCC status
    artifact_type: str
    created_at: datetime
    updated_at: datetime
    owner: Optional[str]
    tags: List[str]
    payload: Dict[str, Any]

    @classmethod
    def from_artifact(cls, artifact: Artifact) -> "ChainBoardAlert":
        """Project an OCC Artifact as a ChainBoard Alert."""
        # Map OCC status to ChainBoard alert status
        status_str = artifact.status if isinstance(artifact.status, str) else artifact.status.value
        if status_str in ["Draft", "Pending"]:
            alert_status = "open"
        elif status_str == "Rejected":
            alert_status = "blocked"
        else:
            alert_status = "resolved"

        # Map artifact type to severity
        type_str = artifact.artifact_type if isinstance(artifact.artifact_type, str) else artifact.artifact_type.value
        severity_map = {
            "Decision": "medium",
            "ComplianceRecord": "high",
            "ExecutionResult": "low",
        }
        severity = severity_map.get(type_str, "info")

        return cls(
            id=artifact.id,
            title=artifact.name,
            description=artifact.description,
            severity=severity,
            status=alert_status,
            artifact_type=type_str,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
            owner=artifact.owner,
            tags=artifact.tags,
            payload=artifact.payload,
        )


class AlertsResponse(BaseModel):
    """Response model for alerts endpoint."""

    items: List[ChainBoardAlert]
    count: int
    total: int
    status: str
    limit: int


# =============================================================================
# Alerts Endpoint (Projection over OCC Artifacts)
# =============================================================================


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    status: str = Query("open", description="Alert status filter: open, blocked, resolved, all"),
    limit: int = Query(50, ge=1, le=500, description="Maximum alerts to return"),
    store: ArtifactStore = Depends(get_artifact_store),
) -> AlertsResponse:
    """
    Get alerts for ChainBoard dashboard.

    Projects OCC artifacts (Decision, ComplianceRecord, ExecutionResult)
    as alerts with mapped status values.

    Status mapping:
    - open: Draft, Pending artifacts
    - blocked: Rejected artifacts
    - resolved: Approved, Locked artifacts
    - all: No status filter
    """
    # Get all artifacts of alert-eligible types
    all_alerts: List[ChainBoardAlert] = []

    for artifact_type in ALERT_ARTIFACT_TYPES:
        artifacts = store.list(artifact_type=artifact_type)
        for artifact in artifacts:
            all_alerts.append(ChainBoardAlert.from_artifact(artifact))

    # Filter by status if not "all"
    if status != "all" and status in ALERT_STATUS_MAP:
        target_statuses = ALERT_STATUS_MAP[status]
        if target_statuses:
            target_status_values = [s.value for s in target_statuses]
            all_alerts = [a for a in all_alerts if a.status == status]

    # Sort by updated_at descending (most recent first)
    all_alerts.sort(key=lambda a: a.updated_at, reverse=True)

    total = len(all_alerts)
    items = all_alerts[:limit]

    logger.debug(f"ChainBoard alerts: status={status}, returned={len(items)}, total={total}")

    return AlertsResponse(
        items=items,
        count=len(items),
        total=total,
        status=status,
        limit=limit,
    )


# =============================================================================
# SSE Events Stream (Projection over OCC Audit Events)
# =============================================================================


class SSEEventData(BaseModel):
    """Data structure for SSE event payload."""

    event_id: str
    artifact_id: str
    event_type: str
    actor: Optional[str]
    timestamp: str
    details: Dict[str, Any]


def format_sse_event(event_type: str, data: dict) -> str:
    """Format data as SSE event string."""
    json_data = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {json_data}\n\n"


async def audit_event_generator(store: ArtifactStore, max_events: int | None = None):
    """
    Generate SSE events from OCC audit events.

    Polls for new events and streams them to connected clients.
    Includes heartbeat to keep connection alive.

    Args:
        store: Artifact store to poll for events
        max_events: If set, stop after emitting this many events (for testing)
    """
    # Track last seen events per artifact to avoid duplicates
    seen_event_ids: set = set()
    last_check = datetime.now(timezone.utc)
    events_emitted = 0

    try:
        # Send initial connection event
        yield format_sse_event(
            "connected",
            {
                "status": "ok",
                "message": "ChainBoard event stream connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        events_emitted += 1

        # Check if we should stop after initial event
        if max_events is not None and events_emitted >= max_events:
            return

        while True:
            # Get all artifacts and their events
            new_events: List[AuditEvent] = []

            artifacts = store.list()
            for artifact in artifacts:
                events = store.get_events(artifact.id)
                for event in events:
                    if str(event.id) not in seen_event_ids:
                        # Check if event is newer than last check (with some buffer)
                        if event.timestamp >= last_check:
                            new_events.append(event)
                        seen_event_ids.add(str(event.id))

            # Also check events for deleted artifacts (tombstones)
            # This requires accessing the internal _events dict
            # For now, we only stream events for existing artifacts

            # Sort new events by timestamp
            new_events.sort(key=lambda e: e.timestamp)

            # Emit new events
            for event in new_events:
                event_data = SSEEventData(
                    event_id=str(event.id),
                    artifact_id=str(event.artifact_id),
                    event_type=event.event_type if isinstance(event.event_type, str) else event.event_type.value,
                    actor=event.actor,
                    timestamp=event.timestamp.isoformat(),
                    details=event.details,
                )
                yield format_sse_event("audit", event_data.model_dump())

            last_check = datetime.now(timezone.utc)

            # Heartbeat every 15 seconds
            await asyncio.sleep(15)
            yield ": heartbeat\n\n"

    except asyncio.CancelledError:
        logger.debug("ChainBoard SSE stream cancelled (client disconnected)")
        raise


@router.get("/events/stream")
async def events_stream(
    store: ArtifactStore = Depends(get_artifact_store),
    max_events: int | None = None,
) -> StreamingResponse:
    """
    Server-Sent Events stream for ChainBoard real-time updates.

    Streams OCC audit events as they occur. Events include:
    - CREATED: New artifact created
    - UPDATED: Artifact modified
    - APPROVED/REJECTED/LOCKED: Status changes
    - DELETED: Artifact removed
    - COMMENT: Manual annotations

    Connection emits heartbeat every ~15 seconds to stay alive.

    Query params:
        max_events: If set, stop after emitting N events (for testing)
    """
    logger.debug("ChainBoard SSE stream connected")
    return StreamingResponse(
        audit_event_generator(store, max_events=max_events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
