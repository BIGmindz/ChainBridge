"""Settlement webhook orchestrator."""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.chainpay import PaymentIntent
from api.services.settlement_events import append_settlement_event
from api.services.payment_intents import evaluate_readiness, compute_intent_hash
from api.events.bus import event_bus, EventType
from api.routes.chainpay import _serialize_settlement_event
from api.webhooks.security import enforce_rate_limit, verify_signature

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class PaymentStatusPayload(BaseModel):
    payment_intent_id: str
    external_status: str
    provider: str
    raw_payload: dict


class ProofAttachedPayload(BaseModel):
    payment_intent_id: str
    proof_id: str
    provider: str


_STATUS_MAP = {
    "AUTHORIZED": "AUTHORIZED",
    "CAPTURED": "CAPTURED",
    "SETTLED": "CAPTURED",
    "FAILED": "FAILED",
}


def _require_intent(db: Session, pid: str) -> PaymentIntent:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == pid).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    return intent


def _apply_readiness(db: Session, intent: PaymentIntent, *, actor: str = "system") -> None:
    ready, reason, blocks, ready_at = evaluate_readiness(intent, latest_snapshot=None, settlement_events=intent.settlement_events)
    intent.risk_gate_reason = reason
    intent.compliance_blocks = blocks
    intent.ready_at = ready_at
    intent.intent_hash = compute_intent_hash(intent)
    db.add(intent)
    db.commit()
    db.refresh(intent)
    event_bus.publish(
        EventType.PAYMENT_INTENT_UPDATED,
        {
            "id": intent.id,
            "shipment_id": intent.shipment_id,
            "status": intent.status,
            "risk_level": intent.risk_level,
            "ready_for_payment": len(blocks) == 0,
        },
        correlation_id=intent.id,
        actor=actor or "system",
    )


@router.post("/settlement/payment_status")
async def settlement_payment_status(payload: PaymentStatusPayload, request: Request, db: Session = Depends(get_db)) -> list[dict]:
    await verify_signature(request)
    enforce_rate_limit(payload.provider, payload.payment_intent_id)
    intent = _require_intent(db, payload.payment_intent_id)
    event_type = _STATUS_MAP.get(payload.external_status.upper())
    if not event_type:
        raise HTTPException(status_code=400, detail="Unsupported external_status")
    append_settlement_event(
        db,
        intent,
        event_type=event_type,
        status="SUCCESS" if event_type != "FAILED" else "FAILED",
        amount=intent.amount,
        currency=intent.currency,
        occurred_at=datetime.utcnow(),
        metadata={"provider": payload.provider, "raw": payload.raw_payload},
        actor="webhook",
    )
    actor = f"webhook:{payload.provider}"
    _apply_readiness(db, intent, actor=actor)
    webhook_payload = payload.model_dump()
    webhook_payload["shipment_id"] = intent.shipment_id
    event_bus.publish(
        EventType.WEBHOOK_RECEIVED,
        webhook_payload,
        correlation_id=payload.payment_intent_id,
        actor=actor,
    )
    events = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == intent.id)
        .first()
        .settlement_events
    )
    return [_serialize_settlement_event(evt).model_dump() for evt in events]


@router.post("/settlement/proof_attached")
async def settlement_proof_attached(payload: ProofAttachedPayload, request: Request, db: Session = Depends(get_db)) -> list[dict]:
    await verify_signature(request)
    enforce_rate_limit(payload.provider, payload.payment_intent_id)
    intent = _require_intent(db, payload.payment_intent_id)
    append_settlement_event(
        db,
        intent,
        event_type="PROOF_ATTACHED",
        status="SUCCESS",
        amount=intent.amount,
        currency=intent.currency,
        occurred_at=datetime.utcnow(),
        metadata={"provider": payload.provider, "proof_id": payload.proof_id},
        actor="webhook",
    )
    intent.proof_pack_id = intent.proof_pack_id or payload.proof_id
    actor = f"webhook:{payload.provider}"
    _apply_readiness(db, intent, actor=actor)
    webhook_payload = payload.model_dump()
    webhook_payload["shipment_id"] = intent.shipment_id
    event_bus.publish(
        EventType.WEBHOOK_RECEIVED,
        webhook_payload,
        correlation_id=payload.payment_intent_id,
        actor=actor,
    )
    events = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == intent.id)
        .first()
        .settlement_events
    )
    return [_serialize_settlement_event(evt).model_dump() for evt in events]
