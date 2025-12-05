"""
Operator Console API Endpoints

Provides summarized and prioritized operator queue data for the Operator Console UI.
These endpoints aggregate at-risk shipments and snapshot export status into actionable
queues for front-line operators.

Sorting Rules:
1. Shipments needing snapshots first (latest_snapshot_status IS NULL or NOT SUCCESS)
2. Risk level: CRITICAL > HIGH > MEDIUM > LOW
3. Risk score DESC
4. Shipment ID (for stability)

TODO: Wire authentication/authorization checks once auth system is in place.
TODO: Add ChainPay hold counts once payment system is operational.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Integer, case, cast, func, or_
from sqlalchemy.orm import Session, aliased

from api.database import get_db
from api.models.canonical import RiskLevel, TransportMode
from api.models.chainiq import DocumentHealthSnapshot, SnapshotExportEvent
from api.models.chainfreight import ShipmentEvent

router = APIRouter(prefix="/chainiq/operator", tags=["operator-console"])

# ===== Constants & helpers =====

RISK_LEVEL_PRIORITY = {
    RiskLevel.CRITICAL.value: 4,
    RiskLevel.HIGH.value: 3,
    RiskLevel.MEDIUM.value: 2,
    RiskLevel.LOW.value: 1,
}
DEFAULT_INCLUDE_LEVELS = (RiskLevel.CRITICAL.value, RiskLevel.HIGH.value)


def _latest_snapshot_subquery(db: Session):
    """Return subquery selecting the most recent snapshot per shipment."""
    return (
        db.query(
            DocumentHealthSnapshot.shipment_id.label("shipment_id"),
            func.max(DocumentHealthSnapshot.created_at).label("max_created_at"),
        )
        .group_by(DocumentHealthSnapshot.shipment_id)
        .subquery()
    )


def _latest_events_subquery(db: Session):
    """Return subquery selecting the latest export event per shipment."""
    snapshot_alias = aliased(DocumentHealthSnapshot)
    ranked_events = (
        db.query(
            snapshot_alias.shipment_id.label("shipment_id"),
            SnapshotExportEvent.status.label("status"),
            SnapshotExportEvent.updated_at.label("updated_at"),
            func.row_number()
            .over(
                partition_by=snapshot_alias.shipment_id,
                order_by=(
                    SnapshotExportEvent.updated_at.desc(),
                    SnapshotExportEvent.id.desc(),
                ),
            )
            .label("event_rank"),
        )
        .join(SnapshotExportEvent, SnapshotExportEvent.snapshot_id == snapshot_alias.id)
        .subquery()
    )

    return (
        db.query(
            ranked_events.c.shipment_id,
            ranked_events.c.status,
            ranked_events.c.updated_at,
        )
        .filter(ranked_events.c.event_rank == 1)
        .subquery()
    )


def _latest_activity_subquery(db: Session):
    """Return subquery selecting the latest shipment event timestamp per shipment."""
    return (
        db.query(
            ShipmentEvent.shipment_id.label("shipment_id"),
            func.max(ShipmentEvent.recorded_at).label("last_event_at"),
        )
        .group_by(ShipmentEvent.shipment_id)
        .subquery()
    )


def _needs_snapshot_case(latest_events_subquery):
    """Build CASE expression indicating whether a shipment needs a snapshot export."""
    return case(
        (
            or_(
                latest_events_subquery.c.status.is_(None),
                latest_events_subquery.c.status != "SUCCESS",
            ),
            1,
        ),
        else_=0,
    )


def _risk_order_case():
    """CASE expression mapping risk level to numeric priority."""
    return case(
        (
            DocumentHealthSnapshot.risk_level == RiskLevel.CRITICAL.value,
            RISK_LEVEL_PRIORITY[RiskLevel.CRITICAL.value],
        ),
        (
            DocumentHealthSnapshot.risk_level == RiskLevel.HIGH.value,
            RISK_LEVEL_PRIORITY[RiskLevel.HIGH.value],
        ),
        (
            DocumentHealthSnapshot.risk_level == RiskLevel.MEDIUM.value,
            RISK_LEVEL_PRIORITY[RiskLevel.MEDIUM.value],
        ),
        (
            DocumentHealthSnapshot.risk_level == RiskLevel.LOW.value,
            RISK_LEVEL_PRIORITY[RiskLevel.LOW.value],
        ),
        else_=0,
    )


def _normalize_levels(include_levels: Optional[str]) -> List[str]:
    """Normalize include_levels query param into canonical risk levels."""
    if not include_levels:
        return list(DEFAULT_INCLUDE_LEVELS)

    normalized: List[str] = []
    for level in include_levels.split(","):
        candidate = level.strip().upper()
        if not candidate:
            continue
        if candidate == "ALL":
            return list(RISK_LEVEL_PRIORITY.keys())
        normalized.append(_canon_risk(candidate))

    # Fallback to defaults if nothing usable was provided.
    return normalized or list(DEFAULT_INCLUDE_LEVELS)


def _canon_risk(level: str) -> str:
    """Normalize and validate risk levels from query parameters."""
    try:
        return RiskLevel.normalize(level).value
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unsupported risk level '{level}'") from exc


def _canon_mode(mode: Optional[str]) -> Optional[str]:
    """Normalize mode strings to canonical transport modes when possible."""
    if not mode:
        return None
    candidate = mode.strip().upper()
    try:
        return TransportMode(candidate).value
    except ValueError:
        return candidate


def _canonical_risk_value(value: Optional[str]) -> str:
    """Normalize stored risk levels, defaulting to MEDIUM when missing/invalid."""
    if value:
        try:
            return RiskLevel.normalize(value).value
        except ValueError:
            pass
    return RiskLevel.MEDIUM.value


# ===== Pydantic Schemas =====


class OperatorSummaryResponse(BaseModel):
    """Aggregate summary for operator header bar."""

    total_at_risk: int = Field(..., description="Total count of at-risk shipments")
    critical_count: int = Field(..., description="Count of CRITICAL risk level shipments")
    high_count: int = Field(..., description="Count of HIGH risk level shipments")
    medium_count: int = Field(..., description="Count of MEDIUM risk level shipments")
    low_count: int = Field(..., description="Count of LOW risk level shipments")
    needs_snapshot_count: int = Field(
        ...,
        description="Count of shipments where latest_snapshot_status is NULL or not SUCCESS",
    )
    payment_holds_count: int = Field(
        ...,
        description="Count of active ChainPay holds (stub=0 for now; TODO: wire ChainPay)",
    )
    last_updated_at: datetime = Field(..., description="UTC timestamp of last update")

    class Config:
        json_schema_extra = {
            "example": {
                "total_at_risk": 42,
                "critical_count": 3,
                "high_count": 8,
                "medium_count": 12,
                "low_count": 19,
                "needs_snapshot_count": 5,
                "payment_holds_count": 0,
                "last_updated_at": "2025-11-19T12:00:00Z",
            }
        }


class OperatorQueueItem(BaseModel):
    """Single item in operator action queue."""

    shipment_id: str = Field(..., description="Unique shipment identifier")
    risk_level: str = Field(..., description="Risk level: CRITICAL, HIGH, MEDIUM, LOW")
    risk_score: float = Field(..., description="Risk score (0-100)")
    corridor_code: Optional[str] = Field(None, description="Trade lane corridor code")
    mode: Optional[str] = Field(None, description="Shipment mode: OCEAN, AIR, ROAD, RAIL")
    incoterm: Optional[str] = Field(None, description="Incoterm code: CIF, FOB, DAP, etc.")
    completeness_pct: int = Field(..., description="Document completeness percentage (0-100)")
    blocking_gap_count: int = Field(..., description="Number of blocking document gaps preventing settlement")
    template_name: Optional[str] = Field(None, description="Document template name")
    days_delayed: Optional[int] = Field(None, description="Days past ETA (if applicable)")
    facility_id: Optional[str] = Field(None, description="Last known facility identifier")
    latest_snapshot_status: Optional[str] = Field(
        None,
        description="Latest snapshot export status: SUCCESS, FAILED, IN_PROGRESS, PENDING, or None",
    )
    latest_snapshot_updated_at: Optional[datetime] = Field(None, description="Timestamp of latest snapshot event")
    needs_snapshot: bool = Field(
        ...,
        description="Derived: True if snapshot_status is NULL or not SUCCESS",
    )
    has_payment_hold: bool = Field(
        False,
        description="Stub: Always False for now; TODO: wire ChainPay integration",
    )
    last_event_at: Optional[datetime] = Field(
        None,
        description="Last relevant event timestamp (used for sorting within same priority)",
    )
    risk_last_updated_at: Optional[datetime] = Field(None, description="Timestamp when risk was last recalculated for this shipment")
    last_export_status: Optional[str] = Field(None, description="Most recent snapshot export status")
    iot_last_seen_at: Optional[datetime] = Field(None, description="Latest IoT heartbeat timestamp if available")

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-2025-0001",
                "risk_level": "CRITICAL",
                "risk_score": 95,
                "corridor_code": "IN_US",
                "mode": "OCEAN",
                "incoterm": "CIF",
                "completeness_pct": 65,
                "blocking_gap_count": 3,
                "template_name": "OCEAN_CIF",
                "days_delayed": 12,
                "facility_id": "USLAX",
                "latest_snapshot_status": None,
                "latest_snapshot_updated_at": None,
                "needs_snapshot": True,
                "has_payment_hold": False,
                "last_event_at": None,
                "risk_last_updated_at": "2025-11-18T23:00:00Z",
                "last_export_status": "IN_PROGRESS",
                "iot_last_seen_at": None,
            }
        }


# ===== Endpoints =====


@router.get("/summary", response_model=OperatorSummaryResponse)
async def get_operator_summary(
    db: Session = Depends(get_db),
) -> OperatorSummaryResponse:
    """
    Get aggregate operator summary for header/dashboard.

    Returns counts of:
    - Total at-risk shipments
    - Critical-level shipments
    - High-level shipments
    - Shipments needing snapshot exports
    - Active ChainPay holds (stub field, TODO integration)
    - Last update timestamp

    **Performance:** Single efficient aggregate query, no N+1 loops.

    TODO: Wire authorization checks once auth system is ready.
    """
    latest_snapshots = _latest_snapshot_subquery(db)
    latest_events = _latest_events_subquery(db)
    needs_snapshot_case = _needs_snapshot_case(latest_events)

    summary_row = (
        db.query(
            func.count(DocumentHealthSnapshot.id).label("total_at_risk"),
            func.sum(
                case(
                    (DocumentHealthSnapshot.risk_level == RiskLevel.CRITICAL.value, 1),
                    else_=0,
                )
            ).label("critical_count"),
            func.sum(
                case(
                    (DocumentHealthSnapshot.risk_level == RiskLevel.HIGH.value, 1),
                    else_=0,
                )
            ).label("high_count"),
            func.sum(
                case(
                    (DocumentHealthSnapshot.risk_level == RiskLevel.MEDIUM.value, 1),
                    else_=0,
                )
            ).label("medium_count"),
            func.sum(
                case(
                    (DocumentHealthSnapshot.risk_level == RiskLevel.LOW.value, 1),
                    else_=0,
                )
            ).label("low_count"),
            func.sum(needs_snapshot_case).label("needs_snapshot_count"),
        )
        .join(
            latest_snapshots,
            (DocumentHealthSnapshot.shipment_id == latest_snapshots.c.shipment_id)
            & (DocumentHealthSnapshot.created_at == latest_snapshots.c.max_created_at),
        )
        .outerjoin(
            latest_events,
            DocumentHealthSnapshot.shipment_id == latest_events.c.shipment_id,
        )
        .one()
    )

    return OperatorSummaryResponse(
        total_at_risk=summary_row.total_at_risk or 0,
        critical_count=summary_row.critical_count or 0,
        high_count=summary_row.high_count or 0,
        medium_count=summary_row.medium_count or 0,
        low_count=summary_row.low_count or 0,
        needs_snapshot_count=summary_row.needs_snapshot_count or 0,
        payment_holds_count=0,
        last_updated_at=datetime.now(timezone.utc),
    )


@router.get("/queue", response_model=List[OperatorQueueItem])
async def get_operator_queue(
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=200,
        description="Maximum items to return (preferred; defaults to 50).",
    ),
    offset: int = Query(0, ge=0, description="Number of matching records to skip"),
    max_results: Optional[int] = Query(
        None,
        ge=1,
        le=500,
        description="Deprecated alias for limit; kept for backwards compatibility.",
    ),
    include_levels: Optional[str] = Query(
        "CRITICAL,HIGH",
        description="Comma-separated list of risk levels to include. Default: CRITICAL,HIGH",
    ),
    needs_snapshot_only: bool = Query(False, description="If True, return only shipments needing snapshot exports"),
    db: Session = Depends(get_db),
) -> List[OperatorQueueItem]:
    """
    Get prioritized operator action queue.

    **Sorting rules** (applied in order):
    1. Shipments needing snapshots first (latest_snapshot_status IS NULL or NOT SUCCESS)
    2. Risk level (CRITICAL > HIGH > MEDIUM > LOW)
    3. Risk score DESC
    4. Days delayed DESC (if available)
    5. Shipment ID (for stability)

    **Query Parameters:**
    - `max_results`: Limit items returned (default=50, max=500)
    - `include_levels`: Comma-separated risk levels to include (default: CRITICAL,HIGH)
    - `needs_snapshot_only`: If True, filter to only items needing snapshots

    **Returns:**
    List of OperatorQueueItem, pre-sorted and paginated.

    **Performance:** Single efficient sorted query, no N+1 loops.

    **Example:**
    ```
    GET /chainiq/operator/queue?max_results=25&include_levels=CRITICAL,HIGH&needs_snapshot_only=false
    ```

    TODO: Wire authorization checks once auth system is ready.
    TODO: Add pagination cursor support for large queues.
    """
    latest_snapshots = _latest_snapshot_subquery(db)
    latest_events = _latest_events_subquery(db)
    latest_activity = _latest_activity_subquery(db)
    needs_snapshot_case = _needs_snapshot_case(latest_events)
    risk_order_case = _risk_order_case()
    days_delayed_expr = func.max(
        0,
        cast(
            func.julianday(func.current_timestamp()) - func.julianday(DocumentHealthSnapshot.created_at),
            Integer,
        ),
    )
    last_event_expr = func.coalesce(latest_activity.c.last_event_at, DocumentHealthSnapshot.created_at)

    levels = _normalize_levels(include_levels)
    page_size = limit or max_results or 50

    query = (
        db.query(
            DocumentHealthSnapshot,
            latest_events.c.status.label("latest_status"),
            latest_events.c.updated_at.label("latest_updated_at"),
            needs_snapshot_case.label("needs_snapshot"),
            risk_order_case.label("risk_order"),
            days_delayed_expr.label("days_delayed"),
            last_event_expr.label("last_event_at"),
        )
        .join(
            latest_snapshots,
            (DocumentHealthSnapshot.shipment_id == latest_snapshots.c.shipment_id)
            & (DocumentHealthSnapshot.created_at == latest_snapshots.c.max_created_at),
        )
        .outerjoin(
            latest_events,
            DocumentHealthSnapshot.shipment_id == latest_events.c.shipment_id,
        )
        .outerjoin(
            latest_activity,
            DocumentHealthSnapshot.shipment_id == latest_activity.c.shipment_id,
        )
    )

    if levels:
        query = query.filter(DocumentHealthSnapshot.risk_level.in_(levels))
    if needs_snapshot_only:
        query = query.filter(needs_snapshot_case == 1)

    rows = (
        query.order_by(
            needs_snapshot_case.desc(),
            risk_order_case.desc(),
            DocumentHealthSnapshot.risk_score.desc(),
            days_delayed_expr.desc(),
            DocumentHealthSnapshot.created_at.desc(),
            DocumentHealthSnapshot.shipment_id.asc(),
        )
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items: List[OperatorQueueItem] = []
    for (
        snapshot,
        latest_status,
        latest_updated_at,
        needs_snapshot_value,
        _,
        days_delayed_value,
        last_event_at,
    ) in rows:
        canonical_risk = _canonical_risk_value(snapshot.risk_level)
        items.append(
            OperatorQueueItem(
                shipment_id=snapshot.shipment_id,
                risk_level=canonical_risk,
                risk_score=(float(snapshot.risk_score) if snapshot.risk_score is not None else None),
                corridor_code=snapshot.corridor_code,
                mode=_canon_mode(snapshot.mode),
                incoterm=snapshot.incoterm,
                completeness_pct=snapshot.completeness_pct,
                blocking_gap_count=snapshot.blocking_gap_count,
                template_name=snapshot.template_name,
                days_delayed=(int(days_delayed_value) if days_delayed_value is not None else None),
                facility_id=None,
                latest_snapshot_status=latest_status,
                latest_snapshot_updated_at=latest_updated_at,
                needs_snapshot=bool(needs_snapshot_value),
                has_payment_hold=False,
                last_event_at=last_event_at,
                risk_last_updated_at=snapshot.created_at,
                last_export_status=latest_status,
                iot_last_seen_at=None,
            )
        )

    return items
