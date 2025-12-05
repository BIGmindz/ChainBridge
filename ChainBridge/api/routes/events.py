"""Event feed endpoints for operator activity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.events.bus import EventType
from api.models.chainpay import SettlementEventAudit

router = APIRouter(prefix="/events", tags=["events"])


class EventListItem(BaseModel):
    id: int
    event_type: str
    source: str
    actor: str
    payment_intent_id: Optional[str]
    shipment_id: Optional[str]
    occurred_at: datetime
    payload_summary: Optional[dict]


class EventFeedResponse(BaseModel):
    items: List[EventListItem]
    next_cursor: Optional[str]


class HeartbeatResponse(BaseModel):
    last_event_at: Optional[datetime]
    last_worker_heartbeat_at: Optional[datetime]


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _encode_cursor(occurred_at: datetime, row_id: int) -> str:
    return f"{_as_utc(occurred_at).isoformat()}|{row_id}"


def _decode_cursor(cursor: str) -> Tuple[datetime, int]:
    try:
        occurred_str, row_id = cursor.split("|", 1)
        return datetime.fromisoformat(occurred_str), int(row_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


def _apply_cursor(query, occurred_at: datetime, row_id: int):
    marker = occurred_at.replace(tzinfo=None) if occurred_at.tzinfo else occurred_at
    return query.filter(
        or_(
            SettlementEventAudit.occurred_at < marker,
            and_(
                SettlementEventAudit.occurred_at == marker,
                SettlementEventAudit.id < row_id,
            ),
        )
    )


def _serialize_item(row: SettlementEventAudit) -> EventListItem:
    return EventListItem(
        id=row.id,
        event_type=row.event_type,
        source=row.source,
        actor=row.actor,
        payment_intent_id=row.payment_intent_id,
        shipment_id=row.shipment_id,
        occurred_at=_as_utc(row.occurred_at),
        payload_summary=row.payload_summary,
    )


@router.get("/settlement_feed", response_model=EventFeedResponse)
def settlement_feed(
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = None,
    payment_intent_id: Optional[str] = None,
    shipment_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> EventFeedResponse:
    query = db.query(SettlementEventAudit).filter(SettlementEventAudit.event_type != EventType.WORKER_HEARTBEAT.value)
    if payment_intent_id:
        query = query.filter(SettlementEventAudit.payment_intent_id == payment_intent_id)
    if shipment_id:
        query = query.filter(SettlementEventAudit.shipment_id == shipment_id)
    if cursor:
        occurred_at, row_id = _decode_cursor(cursor)
        query = _apply_cursor(query, occurred_at, row_id)

    rows = query.order_by(SettlementEventAudit.occurred_at.desc(), SettlementEventAudit.id.desc()).limit(limit + 1).all()
    items = [_serialize_item(row) for row in rows[:limit]]
    next_cursor = None
    if len(rows) > limit and items:
        last = items[-1]
        next_cursor = _encode_cursor(last.occurred_at, last.id)
    return EventFeedResponse(items=items, next_cursor=next_cursor)


@router.get("/heartbeat", response_model=HeartbeatResponse)
def heartbeat(db: Session = Depends(get_db)) -> HeartbeatResponse:
    latest_event = (
        db.query(SettlementEventAudit)
        .filter(SettlementEventAudit.event_type != EventType.WORKER_HEARTBEAT.value)
        .order_by(SettlementEventAudit.occurred_at.desc(), SettlementEventAudit.id.desc())
        .first()
    )
    last_worker = (
        db.query(SettlementEventAudit)
        .filter(SettlementEventAudit.event_type == EventType.WORKER_HEARTBEAT.value)
        .order_by(SettlementEventAudit.occurred_at.desc(), SettlementEventAudit.id.desc())
        .first()
    )
    return HeartbeatResponse(
        last_event_at=_as_utc(latest_event.occurred_at) if latest_event else None,
        last_worker_heartbeat_at=(_as_utc(last_worker.occurred_at) if last_worker else None),
    )
