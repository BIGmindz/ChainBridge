# api/routes/chainboard.py
"""
FastAPI Router for ChainBoard
=============================

This module defines the FastAPI router that exposes all endpoints for the
ChainBoard UI. It follows production-best-practices, including clean
separation of concerns, dependency injection, and alignment with the
canonical schemas defined in `api.schemas.chainboard`.

Router Design:
- **Prefix**: All routes are prefixed with `/chainboard`.
- **Tags**: Grouped under "ChainBoard" in OpenAPI docs for clarity.
- **Data Source**: Backed by realistic mock data from `api.mock.chainboard_fixtures`.
- **Error Handling**: Uses FastAPI's built-in HTTP exceptions for standard error responses.

Author: ChainBridge Platform Team
Version: 1.0.0 (Production-Ready)
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.chainsense.client import IoTDataProvider, MockIoTDataProvider
from api.database import get_db
from api.mock.chainboard_fixtures import (
    build_mock_alerts,
    build_mock_risk_stories,
    build_mock_shipment_events,
    get_mock_risk_overview,
    mock_corridor_metrics,
    mock_exceptions,
    mock_global_summary,
    mock_shipments,
)
from api.realtime.bus import publish_event
from api.schemas.chainboard import (
    AddAlertNoteRequest,
    AlertDetailResponse,
    AlertSeverity,
    AlertSource,
    AlertsResponse,
    AlertStatus,
    AlertWorkQueueResponse,
    CorridorMetricsResponse,
    ExceptionsResponse,
    GlobalSummaryResponse,
    IoTHealthSummaryResponse,
    LivePositionsResponse,
    LiveShipmentPosition,
    PaymentQueueResponse,
    RiskCategory,
    RiskOverviewResponse,
    RiskStoryResponse,
    Shipment,
    ShipmentIoTSnapshotResponse,
    ShipmentIoTSnapshotsResponse,
    ShipmentsResponse,
    ShipmentStatus,
    TimelineEventResponse,
    UpdateAlertAssignmentRequest,
    UpdateAlertStatusRequest,
)
from api.security import get_current_admin_user
from api.services.live_positions import live_positions

router = APIRouter(
    prefix="/chainboard",
    tags=["ChainBoard"],
)

logger = logging.getLogger(__name__)

# IoT data provider (singleton pattern)
_iot_provider: Optional[IoTDataProvider] = None


def get_iot_provider() -> IoTDataProvider:
    """Get the configured IoT data provider (singleton)."""
    global _iot_provider
    if _iot_provider is None:
        # For now, always use mock. In future, check env var to use real provider.
        _iot_provider = MockIoTDataProvider()
    return _iot_provider


# ============================================================================
# METRICS ENDPOINTS
# ============================================================================


@router.get("/metrics/summary", response_model=GlobalSummaryResponse)
async def get_global_summary():
    """
    Retrieve a top-level dashboard summary combining all domain metrics.
    This is the primary API response for the ChainBoard Overview page.
    """
    return GlobalSummaryResponse(
        summary=mock_global_summary,
        generated_at=datetime.utcnow(),
    )


@router.get("/metrics/corridors", response_model=CorridorMetricsResponse)
async def get_corridor_metrics():
    """
    Retrieve corridor-level intelligence metrics for all major trade lanes.
    """
    return CorridorMetricsResponse(
        corridors=mock_corridor_metrics,
        total=len(mock_corridor_metrics),
    )


@router.get("/metrics/iot/summary", response_model=IoTHealthSummaryResponse)
async def get_iot_health_summary():
    """
    Retrieve network-wide IoT health metrics, including sensor status and
    alert counts.
    """
    provider = get_iot_provider()
    health_summary = provider.get_global_health()

    return IoTHealthSummaryResponse(
        iot_health=health_summary,
        generated_at=datetime.utcnow(),
    )


@router.get("/metrics/iot/shipments", response_model=ShipmentIoTSnapshotsResponse)
async def list_shipment_iot_snapshots(
    shipment_ids: Optional[List[str]] = Query(None, description="Optional list of shipment IDs to include"),
    has_alerts: Optional[bool] = Query(None, description="Filter shipments that have any alerts in the last 24h"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of snapshots to return"),
):
    """Retrieve aggregated IoT snapshots for shipments with optional filtering."""
    # Get all snapshots from provider's data source
    from api.mock.chainboard_fixtures import mock_iot_snapshots

    snapshots = list(mock_iot_snapshots.values())

    filtered = False
    if shipment_ids:
        filtered = True
        requested = {sid for sid in shipment_ids}
        snapshots = [s for s in snapshots if s.shipment_id in requested]

    if has_alerts is not None:
        filtered = True
        snapshots = [s for s in snapshots if (s.alert_count_24h > 0 or s.critical_alerts_24h > 0) == has_alerts]

    limited_snapshots = snapshots[:limit]
    limited_count = len(limited_snapshots)

    return ShipmentIoTSnapshotsResponse(
        snapshots=limited_snapshots,
        total=limited_count,
        available=len(mock_iot_snapshots),
        filtered=filtered or limited_count != len(mock_iot_snapshots),
        generated_at=datetime.utcnow(),
    )


@router.get("/metrics/iot/shipments/{shipment_id}", response_model=ShipmentIoTSnapshotResponse)
async def get_shipment_iot_snapshot(shipment_id: str):
    """
    Retrieve the latest IoT telemetry snapshot for a single shipment.
    """
    provider = get_iot_provider()
    snapshot = provider.get_shipment_snapshot(shipment_id)

    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"IoT snapshot for shipment '{shipment_id}' not found.",
        )

    return ShipmentIoTSnapshotResponse(
        snapshot=snapshot,
        retrieved_at=datetime.utcnow(),
    )


# ============================================================================
# SHIPMENT ENDPOINTS
# ============================================================================


@router.get("/shipments", response_model=ShipmentsResponse)
async def get_shipments(
    status: Optional[List[ShipmentStatus]] = Query(None, description="Filter by shipment status"),
    risk: Optional[List[RiskCategory]] = Query(None, description="Filter by risk category"),
    corridor: Optional[str] = Query(None, description="Filter by corridor (e.g., 'Shanghai → Los Angeles')"),
    search: Optional[str] = Query(None, description="Search by reference, customer, or carrier"),
):
    """
    Retrieve a list of all shipments, with optional filtering.
    """
    filtered_shipments = mock_shipments
    is_filtered = False

    if status:
        is_filtered = True
        filtered_shipments = [s for s in filtered_shipments if s.status in status]

    if risk:
        is_filtered = True
        filtered_shipments = [s for s in filtered_shipments if s.risk.category in risk]

    if corridor:
        is_filtered = True
        corridor_lower = corridor.lower()
        filtered_shipments = [s for s in filtered_shipments if corridor_lower in s.corridor.lower()]

    if search:
        is_filtered = True
        search_lower = search.lower()
        filtered_shipments = [
            s
            for s in filtered_shipments
            if search_lower in s.reference.lower() or search_lower in s.customer.lower() or search_lower in s.carrier.lower()
        ]

    return ShipmentsResponse(
        shipments=filtered_shipments,
        total=len(filtered_shipments),
        filtered=is_filtered,
    )


@router.get("/live-positions", response_model=LivePositionsResponse)
async def get_live_positions(db: Session = Depends(get_db), user=Depends(get_current_admin_user)) -> LivePositionsResponse:
    """Enriched live positions with finance, risk, and nearest-port overlays."""

    try:
        positions = live_positions(db)
    except Exception as exc:
        logger.exception(
            "chainboard_live_positions_failed",
            extra={"endpoint": "/api/chainboard/live-positions"},
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LIVE_POSITIONS_ERROR",
                "message": "Unable to load live positions. Please retry shortly.",
            },
        ) from exc
    enriched = [LiveShipmentPosition.model_validate(p) for p in positions]
    return LivePositionsResponse(positions=enriched, generated_at=datetime.utcnow())


@router.get("/shipments/{shipment_id}", response_model=Shipment)
async def get_shipment_by_id(shipment_id: str):
    """
    Retrieve a single shipment by its unique ID.
    """
    shipment = next((s for s in mock_shipments if s.id == shipment_id), None)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found.")
    return shipment


# ============================================================================
# EXCEPTION ENDPOINTS
# ============================================================================


@router.get("/exceptions", response_model=ExceptionsResponse)
async def get_exceptions():
    """
    Retrieve a list of all shipments with active exceptions for triage.
    """
    critical_count = sum(
        1 for e in mock_exceptions if RiskCategory.HIGH in [s.risk.category for s in mock_shipments if s.id == e.shipment_id]
    )

    return ExceptionsResponse(
        exceptions=mock_exceptions,
        total=len(mock_exceptions),
        critical_count=critical_count,
    )


# ============================================================================
# RISK ENDPOINTS
# ============================================================================


@router.get("/risk/overview", response_model=RiskOverviewResponse)
async def get_risk_overview():
    """Aggregate ChainIQ risk KPIs for the overview tile."""

    return get_mock_risk_overview()


@router.get("/pay/queue", response_model=PaymentQueueResponse)
async def get_payment_queue(limit: int = Query(20, ge=1, le=100)):
    """
    ChainPay payment hold queue.
    Returns shipments with payment holds, sorted by hold amount.
    """
    from api.mock.chainboard_fixtures import build_mock_payment_queue

    queue = build_mock_payment_queue()

    # Apply limit if needed
    if limit < len(queue.items):
        queue.items = queue.items[:limit]
        queue.total_items = len(queue.items)

    return queue


@router.get("/iq/risk-stories", response_model=RiskStoryResponse)
async def get_risk_stories(limit: int = Query(20, ge=1, le=100)):
    """
    ChainIQ Risk Stories - human-readable narratives explaining why shipments are risky.
    Returns risk intelligence with recommended actions, sorted by risk score.
    """
    stories = build_mock_risk_stories()

    # Apply limit if needed
    if limit < len(stories.stories):
        stories.stories = stories.stories[:limit]
        stories.total = len(stories.stories)

    return stories


@router.get("/events", response_model=TimelineEventResponse)
async def list_events(limit: int = Query(50, ge=1, le=200)):
    """
    Get timeline events for all shipments, sorted by most recent first.
    Provides a global event feed showing all activity across the platform.
    """
    events = build_mock_shipment_events()

    # Apply limit if needed
    if limit < len(events.events):
        events.events = events.events[:limit]
        events.total = len(events.events)

    return events


@router.get("/shipments/{reference}/events", response_model=TimelineEventResponse)
async def get_shipment_events(reference: str, limit: int = Query(50, ge=1, le=200)):
    """
    Get timeline events for a specific shipment by reference number.
    Shows the complete event history for a single shipment.
    """
    # Verify shipment exists
    shipment = next((s for s in mock_shipments if s.reference == reference), None)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {reference} not found")

    # Get events for this shipment only
    events = build_mock_shipment_events(reference=reference)

    # Apply limit if needed
    if limit < len(events.events):
        events.events = events.events[:limit]
        events.total = len(events.events)
    return events


# ============================================================================
# ALERTS & TRIAGE ENDPOINTS
# ============================================================================


@router.get("/alerts", response_model=AlertsResponse)
async def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[AlertStatus] = Query(None),
    source: Optional[AlertSource] = Query(None),
    severity: Optional[AlertSeverity] = Query(None),
):
    """
    List all alerts with optional filtering by status, source, and severity.
    Returns alerts sorted by created_at descending (most recent first).
    """
    alerts = build_mock_alerts()

    # Apply filters
    if status:
        alerts = [a for a in alerts if a.status == status]
    if source:
        alerts = [a for a in alerts if a.source == source]
    if severity:
        alerts = [a for a in alerts if a.severity == severity]

    # Apply limit
    total = len(alerts)
    alerts = alerts[:limit]

    return AlertsResponse(
        alerts=alerts,
        total=total,
        generated_at=datetime.utcnow(),
    )


@router.get("/alerts/work-queue", response_model=AlertWorkQueueResponse)
async def get_alert_work_queue(
    owner_id: Optional[str] = Query(None, description="Filter by assigned owner ID"),
    status: Optional[AlertStatus] = Query(None, description="Filter by alert status"),
    source: Optional[AlertSource] = Query(None, description="Filter by alert source"),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
):
    """
    Get alert work queue with optional filters.
    Returns alerts enriched with triage context (owner, notes, actions).
    """
    from api.triage import storage

    alerts = build_mock_alerts()
    items = storage.get_work_queue(
        alerts=alerts,
        owner_id=owner_id,
        status=status,
        source=source,
        severity=severity,
    )

    total = len(items)
    items = items[:limit]

    return AlertWorkQueueResponse(items=items, total=total)


@router.get("/alerts/{alert_id}", response_model=AlertDetailResponse)
async def get_alert(alert_id: str):
    """
    Get a single alert by ID.
    Returns 404 if alert not found.
    """
    alerts = build_mock_alerts()

    for alert in alerts:
        if alert.id == alert_id:
            return AlertDetailResponse(alert=alert)

    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@router.post("/alerts/{alert_id}/assign")
async def assign_alert_route(alert_id: str, body: UpdateAlertAssignmentRequest):
    """
    Assign or unassign alert to an owner.
    If owner_id is null, unassigns the alert.
    """
    from api.schemas.chainboard import AlertOwner, AlertWorkItem
    from api.triage import storage

    # Verify alert exists
    alerts = build_mock_alerts()
    alert = None
    for a in alerts:
        if a.id == alert_id:
            alert = a
            break

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    # Build actor (person performing the assignment)
    actor = AlertOwner(
        id=body.owner_id or "system",
        name=body.owner_name or "System",
        email=body.owner_email,
        team=body.owner_team,
    )

    # Build owner (person being assigned, or None to unassign)
    owner = actor if body.owner_id else None

    storage.assign_alert(alert_id=alert_id, owner=owner, actor=actor)

    # Publish real-time event
    await publish_event(
        type="alert_updated",
        source="alerts",
        key=alert_id,
        payload={"action": "assigned", "owner_id": body.owner_id, "actor_id": actor.id},
    )

    # Return updated work item
    work_item = storage.get_work_item(alert)
    return AlertWorkItem(
        alert=work_item.alert,
        owner=work_item.owner,
        notes=work_item.notes,
        actions=work_item.actions,
    )


@router.post("/alerts/{alert_id}/notes")
async def add_note_route(alert_id: str, body: AddAlertNoteRequest):
    """
    Add a note to an alert.
    """
    from uuid import uuid4

    from api.schemas.chainboard import AlertNote, AlertOwner, AlertWorkItem
    from api.triage import storage

    # Verify alert exists
    alerts = build_mock_alerts()
    alert = None
    for a in alerts:
        if a.id == alert_id:
            alert = a
            break

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    # Build note
    note = AlertNote(
        id=str(uuid4()),
        alert_id=alert_id,
        author=AlertOwner(
            id=body.author_id,
            name=body.author_name,
            email=body.author_email,
            team=body.author_team,
        ),
        message=body.message,
        created_at=datetime.utcnow(),
    )

    storage.add_note(alert_id=alert_id, note=note)

    # Publish real-time event
    await publish_event(
        type="alert_note_added",
        source="alerts",
        key=alert_id,
        payload={
            "note_id": note.id,
            "author_id": body.author_id,
            "message": body.message,
        },
    )

    # Return updated work item
    work_item = storage.get_work_item(alert)
    return AlertWorkItem(
        alert=work_item.alert,
        owner=work_item.owner,
        notes=work_item.notes,
        actions=work_item.actions,
    )


@router.post("/alerts/{alert_id}/status")
async def update_status_route(alert_id: str, body: UpdateAlertStatusRequest):
    """
    Update alert status (acknowledge, resolve, etc.).
    """
    from api.schemas.chainboard import AlertOwner, AlertWorkItem
    from api.triage import storage

    # Verify alert exists
    alerts = build_mock_alerts()
    alert = None
    for a in alerts:
        if a.id == alert_id:
            alert = a
            break

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    # Build actor
    actor = AlertOwner(
        id=body.actor_id,
        name=body.actor_name,
        email=body.actor_email,
        team=body.actor_team,
    )

    storage.update_status(alert_id=alert_id, new_status=body.status, actor=actor)

    # Publish real-time event
    await publish_event(
        type="alert_status_changed",
        source="alerts",
        key=alert_id,
        payload={"new_status": body.status, "actor_id": body.actor_id},
    )

    # Return updated work item
    work_item = storage.get_work_item(alert)
    return AlertWorkItem(
        alert=work_item.alert,
        owner=work_item.owner,
        notes=work_item.notes,
        actions=work_item.actions,
    )
