"""Operator-focused endpoints for OC queue and timelines."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.chainpay import PaymentIntent, SettlementEvent
from api.models.chainiq import RiskDecision, DocumentHealthSnapshot
from api.schemas.operator import (
    OperatorQueueItem,
    OperatorQueueResponse,
    RiskSnapshotResponse,
    OperatorEvent,
    OperatorEventsResponse,
    OperatorEventKind,
    OperatorEventSeverity,
    IoTHealthSummaryResponse,
)
from api.chainsense.client import MockIoTDataProvider, IoTDataProvider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/operator", tags=["operator"])


def _compute_state(intent: PaymentIntent) -> str:
    if intent.compliance_blocks:
        return "BLOCKED"
    if intent.proof_pack_id:
        return "READY"
    return "WAITING_PROOF"


@router.get("/queue", response_model=OperatorQueueResponse)
def get_operator_queue(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> OperatorQueueResponse:
    query = (
        db.query(PaymentIntent, DocumentHealthSnapshot)
        .outerjoin(
            DocumentHealthSnapshot,
            (DocumentHealthSnapshot.id == PaymentIntent.latest_risk_snapshot_id)
            | (
                (DocumentHealthSnapshot.shipment_id == PaymentIntent.shipment_id)
                & (
                    DocumentHealthSnapshot.created_at
                    == (
                        db.query(func.max(DocumentHealthSnapshot.created_at))
                        .filter(DocumentHealthSnapshot.shipment_id == PaymentIntent.shipment_id)
                        .correlate(PaymentIntent)
                    )
                )
            ),
        )
        .order_by(PaymentIntent.created_at.desc())
    )
    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    items: List[OperatorQueueItem] = []
    now = datetime.now(timezone.utc)
    for intent, snapshot in rows:
        state = _compute_state(intent)
        age_seconds = (now - intent.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        items.append(
            OperatorQueueItem(
                id=intent.id,
                state=state,
                amount=intent.amount,
                pricing_breakdown=intent.pricing_breakdown,
                risk_score=snapshot.risk_score if snapshot else intent.risk_score,
                readiness_reason=intent.risk_gate_reason,
                event_age_seconds=age_seconds,
                p95_seconds=None,
                intent_hash=intent.intent_hash,
            )
        )

    return OperatorQueueResponse(items=items, total=total)


@router.get("/settlements/{intent_id}/risk_snapshot", response_model=RiskSnapshotResponse)
def get_risk_snapshot(intent_id: str, db: Session = Depends(get_db)) -> RiskSnapshotResponse:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")

    decision = (
        db.query(RiskDecision)
        .filter(RiskDecision.shipment_id == intent.shipment_id)
        .order_by(RiskDecision.decided_at.desc())
        .first()
    )
    if not decision:
        decision = (
            db.query(DocumentHealthSnapshot)
            .filter(DocumentHealthSnapshot.shipment_id == intent.shipment_id)
            .order_by(DocumentHealthSnapshot.created_at.desc())
            .first()
        )
        if decision:
            return RiskSnapshotResponse(
                intent_id=intent_id,
                risk_score=decision.risk_score,
                risk_level=decision.risk_level,
                features=None,
                decided_at=decision.created_at,
            )
    if not decision:
        return RiskSnapshotResponse(intent_id=intent_id, risk_score=None, risk_level=None, features=None, decided_at=None)
    return RiskSnapshotResponse(
        intent_id=intent_id,
        risk_score=decision.risk_score,
        risk_level=decision.risk_level,
        features=decision.features,
        decided_at=decision.decided_at,
    )


@router.get("/iot/health/summary", response_model=IoTHealthSummaryResponse)
def get_iot_health_summary() -> IoTHealthSummaryResponse:
    provider: IoTDataProvider = MockIoTDataProvider()
    health = provider.get_global_health()
    return IoTHealthSummaryResponse(
        device_count_active=health.active_sensors if hasattr(health, "active_sensors") else 0,
        device_count_offline=0,
        stale_gps_count=0,
        stale_env_count=0,
        last_ingest_age_seconds=0,
    )


@router.get(
    "/events/stream",
    response_model=OperatorEventsResponse,
)
def get_operator_events_stream(
    since: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> OperatorEventsResponse:
    query = db.query(SettlementEvent).order_by(SettlementEvent.occurred_at.asc())
    if since:
        query = query.filter(SettlementEvent.occurred_at > since)
    events = query.limit(limit).all()

    items: list[OperatorEvent] = []
    for evt in events:
        kind = OperatorEventKind.payment_confirmed if evt.event_type in {"CAPTURED", "CASH_RELEASED"} else OperatorEventKind.info
        severity = OperatorEventSeverity.info
        items.append(
            OperatorEvent(
                id=evt.id,
                kind=kind,
                settlement_id=evt.payment_intent_id,
                severity=severity,
                message=evt.event_type,
                created_at=evt.occurred_at,
            )
        )
    return OperatorEventsResponse(items=items)


@router.get("/settlements/{intent_id}/events", response_model=List[dict])
def get_settlement_events(
    intent_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[dict]:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")

    events = (
        db.query(SettlementEvent)
        .filter(SettlementEvent.payment_intent_id == intent_id)
        .order_by(SettlementEvent.occurred_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": evt.id,
            "event_type": evt.event_type,
            "status": evt.status,
            "amount": evt.amount,
            "currency": evt.currency,
            "occurred_at": evt.occurred_at,
            "metadata": evt.extra_metadata,
        }
        for evt in events
    ]
