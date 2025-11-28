"""FastAPI router exposing ChainIQ shipment health intelligence."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.chainiq_service.export_worker import (
    SnapshotExportEventNotFound,
    SnapshotExportInvalidState,
    enqueue_snapshot_export_events,
    mark_event_failed,
    mark_event_success,
)
from api.chainiq_service.intel_engine import compute_shipment_health, get_at_risk_shipments
from api.chainiq_service.schemas import (
    AtRiskShipmentSummary,
    ShipmentHealthResponse,
    SnapshotExportEventCreateRequest,
    SnapshotExportEventSummary,
    SnapshotExportEventUpdateRequest,
)
from api.database import get_db
from api.models.canonical import RiskLevel
from api.models.chainiq import DocumentHealthSnapshot, SnapshotExportEvent
from api.security import AdminUser, get_current_admin_user

router = APIRouter(prefix="/chainiq", tags=["chainiq"])
MANUAL_EXPORT_TARGET = "CHAINBOARD_UI"


def _serialize_event(event: SnapshotExportEvent) -> SnapshotExportEventSummary:
    """Convert ORM object to API schema."""
    return SnapshotExportEventSummary(
        id=event.id,
        snapshot_id=event.snapshot_id,
        target_system=event.target_system,
        status=event.status,
        claimed_by=event.claimed_by,
        claimed_at=event.claimed_at,
        retry_count=event.retry_count,
        created_at=event.created_at,
        updated_at=event.updated_at,
        reason=event.reason,
        last_error=event.last_error,
    )


@router.get("/shipments/{shipment_id}/health", response_model=ShipmentHealthResponse)
def get_shipment_health(shipment_id: str, db: Session = Depends(get_db)) -> ShipmentHealthResponse:
    """
    Return combined document + settlement health and a risk summary for this shipment.

    Never raises 404; always returns a well-formed response, even if data is sparse.
    """
    return compute_shipment_health(db=db, shipment_id=shipment_id)


@router.get("/shipments/at_risk", response_model=list[AtRiskShipmentSummary])
def get_at_risk_shipments_endpoint(
    min_risk_score: int = Query(70, ge=0, le=100),
    max_results: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    corridor_code: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    incoterm: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> list[AtRiskShipmentSummary]:
    """Return a list of at-risk shipments based on the latest health snapshots."""
    normalized_level = None
    if risk_level:
        try:
            normalized_level = RiskLevel.normalize(risk_level).value
        except ValueError:
            normalized_level = risk_level

    snapshot_rows = get_at_risk_shipments(
        db,
        min_risk_score=min_risk_score,
        max_results=max_results,
        corridor_code=corridor_code,
        mode=mode,
        incoterm=incoterm,
        risk_level=normalized_level,
        offset=offset,
    )
    summaries: List[AtRiskShipmentSummary] = []
    for snapshot, latest_status, latest_updated in snapshot_rows:
        summaries.append(
            AtRiskShipmentSummary(
                shipment_id=snapshot.shipment_id,
                corridor_code=snapshot.corridor_code,
                mode=snapshot.mode,
                incoterm=snapshot.incoterm,
                template_name=snapshot.template_name,
                completeness_pct=snapshot.completeness_pct,
                blocking_gap_count=snapshot.blocking_gap_count,
                risk_score=snapshot.risk_score,
                risk_level=snapshot.risk_level,
                last_snapshot_at=snapshot.created_at,
                latest_snapshot_status=latest_status,
                latest_snapshot_updated_at=latest_updated,
            )
        )
    return summaries


@router.get("/admin/snapshot_exports", response_model=list[SnapshotExportEventSummary])
def list_snapshot_export_events(
    status: Optional[str] = Query(None),
    target_system: Optional[str] = Query(None),
    shipment_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_admin: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> list[SnapshotExportEventSummary]:
    """
    List snapshot export events for operational visibility.

    TODO: add authentication/authorization hooks before production rollout.
    """
    query = db.query(SnapshotExportEvent)
    if status:
        query = query.filter(SnapshotExportEvent.status == status)
    if target_system:
        query = query.filter(SnapshotExportEvent.target_system == target_system)
    if shipment_id:
        query = query.join(DocumentHealthSnapshot).filter(
            DocumentHealthSnapshot.shipment_id == shipment_id
        )

    events = (
        query.order_by(SnapshotExportEvent.created_at.desc())
        .limit(limit)
        .all()
    )

    return [_serialize_event(event) for event in events]


@router.post("/admin/snapshot_exports", response_model=SnapshotExportEventSummary)
def create_snapshot_export_event(
    body: SnapshotExportEventCreateRequest,
    current_admin: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> SnapshotExportEventSummary:
    """Create a manual snapshot export event for a shipment."""
    snapshot = (
        db.query(DocumentHealthSnapshot)
        .filter(DocumentHealthSnapshot.shipment_id == body.shipment_id)
        .order_by(
            DocumentHealthSnapshot.created_at.desc(),
            DocumentHealthSnapshot.id.desc(),
        )
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="No snapshot found for shipment")

    try:
        event = enqueue_snapshot_export_events(
            db,
            snapshot,
            target_systems=[MANUAL_EXPORT_TARGET],
            reason=body.reason,
        )[0]
    except Exception as exc:  # pragma: no cover - guardrail
        raise HTTPException(status_code=500, detail="Failed to create snapshot export") from exc

    return _serialize_event(event)


@router.post(
    "/admin/snapshot_exports/{event_id}/status",
    response_model=SnapshotExportEventSummary,
)
def update_snapshot_export_event_status(
    event_id: int,
    body: SnapshotExportEventUpdateRequest,
    current_admin: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> SnapshotExportEventSummary:
    """Allow a worker to mark an export event processed."""
    try:
        if body.status == "SUCCESS":
            updated = mark_event_success(db, event_id)
        elif body.status == "FAILED":
            updated = mark_event_failed(
                db,
                event_id,
                reason=body.last_error,
                retryable=body.retryable,
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported status")
    except SnapshotExportEventNotFound:
        raise HTTPException(status_code=404, detail="SnapshotExportEvent not found") from None
    except SnapshotExportInvalidState as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return _serialize_event(updated)
