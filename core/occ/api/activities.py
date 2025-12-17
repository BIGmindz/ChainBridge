"""
OCC Agent Activity API

Endpoints for agent activity logging and real-time streaming.
Mounted at /occ/activities

Glass-box design: Nothing happens without a trace.

Endpoints:
- POST /occ/activities - Log a new activity (append-only)
- GET /occ/activities - List activities with filters
- GET /occ/activities/stream - SSE stream for real-time feed
- GET /occ/activities/stats - Activity statistics
- GET /occ/activities/{id} - Get specific activity

All endpoints require authentication. No auth bypass.
"""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.oc.auth import Principal, get_current_principal
from core.occ.api.pdo_deps import require_pdo_header
from core.occ.schemas.activity import ActivityStats, ActivityStatus, ActivityType, AgentActivity, AgentActivityCreate, AgentActivityList
from core.occ.store.activity_store import AgentActivityStore, get_activity_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/activities", tags=["OCC Activities"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class ActivityCreateResponse(BaseModel):
    """Response for activity creation."""

    activity: AgentActivity
    message: str = Field(default="Activity logged successfully")


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("", response_model=ActivityCreateResponse, status_code=201, dependencies=[Depends(require_pdo_header)])
async def create_activity(
    activity_in: AgentActivityCreate,
    store: AgentActivityStore = Depends(get_activity_store),
    principal: Principal = Depends(get_current_principal),
) -> ActivityCreateResponse:
    """
    Log a new agent activity.

    Requires: Valid PDO (X-PDO-ID and X-PDO-Approved headers) + authenticated principal.

    This is an append-only operation. Once logged, activities cannot be
    modified or deleted. Every activity gets a monotonic sequence number
    for reliable ordering.
    """
    try:
        activity = store.append(activity_in)
        activity_type = getattr(activity.activity_type, "value", activity.activity_type)
        logger.info(f"Activity logged by {principal.id}: " f"{activity.agent_gid}/{activity_type}")
        return ActivityCreateResponse(activity=activity)
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log activity: {str(e)}")


@router.get("", response_model=AgentActivityList)
async def list_activities(
    agent_gid: Optional[str] = Query(None, description="Filter by agent GID"),
    activity_type: Optional[ActivityType] = Query(None, description="Filter by activity type"),
    artifact_id: Optional[UUID] = Query(None, description="Filter by artifact ID"),
    status: Optional[ActivityStatus] = Query(None, description="Filter by status"),
    since_sequence: Optional[int] = Query(None, ge=0, description="Only activities after this sequence"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    store: AgentActivityStore = Depends(get_activity_store),
    principal: Principal = Depends(get_current_principal),
) -> AgentActivityList:
    """
    List activities with optional filtering.

    Requires: Any authenticated principal.

    Activities are returned in sequence order (oldest first).
    Use `since_sequence` for efficient polling of new activities.
    """
    activities = store.list(
        agent_gid=agent_gid,
        activity_type=activity_type,
        artifact_id=artifact_id,
        status=status,
        since_sequence=since_sequence,
        limit=limit + 1,  # Fetch one extra to check has_more
        offset=offset,
    )

    # Check if there are more results
    has_more = len(activities) > limit
    if has_more:
        activities = activities[:limit]

    # Get total count (without pagination)
    total = store.count(
        agent_gid=agent_gid,
        activity_type=activity_type,
        artifact_id=artifact_id,
    )

    return AgentActivityList(
        items=activities,
        count=len(activities),
        total=total,
        has_more=has_more,
    )


@router.get("/stats", response_model=ActivityStats)
async def get_activity_stats(
    store: AgentActivityStore = Depends(get_activity_store),
    principal: Principal = Depends(get_current_principal),
) -> ActivityStats:
    """
    Get aggregate statistics about activities.

    Requires: Any authenticated principal.

    Returns counts by type, agent, and status, plus timestamp range.
    """
    return store.stats()


@router.get("/stream")
async def stream_activities(
    request: Request,
    since_sequence: Optional[int] = Query(None, ge=0, description="Start streaming from this sequence"),
    test_mode: bool = Query(False, description="If true, close the stream after replay/keepalive (testing convenience)"),
    store: AgentActivityStore = Depends(get_activity_store),
    principal: Principal = Depends(get_current_principal),
):
    """
    Server-Sent Events (SSE) stream for real-time activity feed.

    Requires: Any authenticated principal.

    This endpoint streams activities in real-time as they occur.
    Use `since_sequence` to replay missed activities first.

    Event format:
    ```
    data: {"id": "...", "agent_gid": "GID-01", ...}

    ```

    Connection will stay open until client disconnects.
    """

    async def event_generator():
        # First, send any missed activities (replay)
        if since_sequence is not None:
            missed = store.list(since_sequence=since_sequence)
            for activity in missed:
                yield activity.to_sse_event()

        # Send initial keepalive
        yield ": keepalive\n\n"

        # In test mode we short-circuit after the initial replay/keepalive
        # so that synchronous test clients don't hang on an infinite stream.
        if test_mode:
            return

        # Subscribe to real-time updates
        queue = store.subscribe()
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"SSE client disconnected: {principal.id}")
                    break

                try:
                    # Wait for new activity with timeout (for keepalive)
                    activity = await asyncio.wait_for(queue.get(), timeout=30.0)  # Send keepalive every 30s
                    yield activity.to_sse_event()
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
        finally:
            store.unsubscribe(queue)
            logger.info(f"SSE stream ended for {principal.id}")

    logger.info(f"SSE stream started for {principal.id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/{activity_id}", response_model=AgentActivity)
async def get_activity(
    activity_id: UUID,
    store: AgentActivityStore = Depends(get_activity_store),
    principal: Principal = Depends(get_current_principal),
) -> AgentActivity:
    """
    Get a specific activity by ID.

    Requires: Any authenticated principal.
    """
    activity = store.get(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail=f"Activity not found: {activity_id}")
    return activity
