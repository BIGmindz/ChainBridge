"""
OCC Audit Events API

Endpoints for viewing and adding audit events on artifacts.
Mounted at /occ/artifacts/{id}/events
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.occ.schemas.audit_event import AuditEvent, AuditEventCreate, AuditEventList
from core.occ.store.artifact_store import ArtifactStore, get_artifact_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/artifacts", tags=["OCC Audit Events"])


@router.get("/{artifact_id}/events", response_model=AuditEventList)
async def get_artifact_events(
    artifact_id: UUID,
    store: ArtifactStore = Depends(get_artifact_store),
) -> AuditEventList:
    """
    Get the audit event timeline for an artifact.

    Returns events sorted by timestamp ascending (oldest first).
    Events are available even for deleted artifacts (tombstone pattern).
    """
    # Check if artifact exists or has event history
    artifact = store.get(artifact_id)
    events = store.get_events(artifact_id)

    if artifact is None and not events:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    return AuditEventList(
        artifact_id=artifact_id,
        events=events,
        count=len(events),
    )


@router.post("/{artifact_id}/events", response_model=AuditEvent, status_code=201)
async def add_artifact_event(
    artifact_id: UUID,
    event_in: AuditEventCreate,
    store: ArtifactStore = Depends(get_artifact_store),
) -> AuditEvent:
    """
    Append an audit event to an artifact (system/internal use).

    Events are append-only and cannot be modified or deleted.
    """
    event = store.add_event(artifact_id, event_in)

    if event is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    return event
