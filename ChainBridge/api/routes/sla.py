"""SLA status endpoint."""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.events.bus import EventType
from api.models.chainiq import SnapshotExportEvent
from api.models.chainpay import PaymentIntent, SettlementEventAudit
from api.models.chainstake import StakePosition
from api.sla.metrics import get_metric, get_sla_snapshot
from app.models.marketplace import BuyIntent, Listing, SettlementRecord

router = APIRouter(prefix="/sla", tags=["sla"])

DATA_WINDOW = timedelta(hours=24)
WORKER_STALE_THRESHOLD = timedelta(minutes=10)
ACTIVE_STATUSES = {"PENDING", "CLAIMED", "IN_PROGRESS"}


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/status")
def sla_status() -> dict:
    snapshot = get_sla_snapshot(now=datetime.now(timezone.utc), window_seconds=int(DATA_WINDOW.total_seconds()))
    snapshot["data_window"] = "24h"
    return snapshot


@router.get("/operator")
def sla_operator(db: Session = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    window_start = now - DATA_WINDOW

    queue_depth = (
        db.query(SnapshotExportEvent)
        .filter(SnapshotExportEvent.status.in_(ACTIVE_STATUSES))
        .filter(SnapshotExportEvent.created_at >= window_start)
        .count()
    )

    durations = []
    events = (
        db.query(SnapshotExportEvent)
        .filter(SnapshotExportEvent.created_at >= window_start)
        .filter(SnapshotExportEvent.status.notin_(ACTIVE_STATUSES))
        .all()
    )
    for evt in events:
        if evt.updated_at and evt.created_at:
            durations.append((evt.updated_at - evt.created_at).total_seconds())
    p95: Optional[float] = None
    if durations:
        durations.sort()
        idx = max(0, math.ceil(0.95 * len(durations)) - 1)
        p95 = durations[idx]

    recent_intents = db.query(PaymentIntent).filter(
        or_(
            PaymentIntent.updated_at >= window_start,
            PaymentIntent.created_at >= window_start,
        )
    )
    payment_intents_ready = recent_intents.filter(
        (PaymentIntent.compliance_blocks.is_(None)) | (func.json_array_length(PaymentIntent.compliance_blocks) == 0)
    ).count()
    payment_intents_blocked = recent_intents.filter(
        (PaymentIntent.compliance_blocks.isnot(None)) & (func.json_array_length(PaymentIntent.compliance_blocks) > 0)
    ).count()

    chainstake_tvl = (
        db.query(func.coalesce(func.sum(StakePosition.notional_usd), 0.0))
        .filter(StakePosition.status.in_(ACTIVE_STATUSES | {"CLOSED"}))
        .scalar()
    )
    chainstake_active = db.query(func.count(StakePosition.id)).filter(~StakePosition.status.in_(["FAILED", "CLOSED"])).scalar()
    marketplace_active = db.query(func.count(Listing.id)).filter(Listing.status == "ACTIVE").scalar()
    marketplace_settled = db.query(func.count(SettlementRecord.id)).filter(SettlementRecord.created_at >= window_start).scalar()
    marketplace_failed_intents = (
        db.query(func.count(BuyIntent.id)).filter(BuyIntent.created_at >= window_start).filter(BuyIntent.status == "FAILED").scalar()
    )

    worker_event = (
        db.query(SettlementEventAudit)
        .filter(
            or_(
                SettlementEventAudit.actor.ilike("worker%"),
                SettlementEventAudit.event_type == EventType.WORKER_HEARTBEAT.value,
            )
        )
        .order_by(SettlementEventAudit.occurred_at.desc(), SettlementEventAudit.id.desc())
        .first()
    )
    last_worker_ts = _as_utc(worker_event.occurred_at) if worker_event else _as_utc(get_metric("worker_heartbeat"))
    worker_stale = True
    if last_worker_ts:
        worker_stale = (now - last_worker_ts).total_seconds() > WORKER_STALE_THRESHOLD.total_seconds()

    return {
        "snapshot_queue_depth": queue_depth,
        "snapshot_p95_processing_seconds": p95,
        "payment_intents_ready": payment_intents_ready,
        "payment_intents_blocked": payment_intents_blocked,
        "latest_worker_heartbeat_at": last_worker_ts,
        "worker_stale": worker_stale,
        "data_window": "24h",
        "chainstake_tvl_usd": float(chainstake_tvl or 0.0),
        "chainstake_active_positions": int(chainstake_active or 0),
        "marketplace_active_listings": int(marketplace_active or 0),
        "marketplace_settlements_24h": int(marketplace_settled or 0),
        "marketplace_failed_intents_24h": int(marketplace_failed_intents or 0),
        "dutch_latency_ms": 0,
    }
