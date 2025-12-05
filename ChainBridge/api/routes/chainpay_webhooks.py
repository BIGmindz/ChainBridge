"""Webhook stubs for ChainPay integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.events.bus import EventType, event_bus
from api.models.chainpay import PaymentIntent
from api.routes.chainpay import _serialize_settlement_event
from api.services.payment_intents import compute_intent_hash, evaluate_readiness
from api.services.settlement_events import append_settlement_event
from api.sla.metrics import update_metric
from api.webhooks.security import enforce_rate_limit, verify_signature

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chainpay/hooks", tags=["chainpay-webhooks"])


class WebhookPayload(BaseModel):
    payment_intent_id: str
    external_ref: str
    timestamp: Optional[datetime] = None


def _handle_event(db: Session, intent: PaymentIntent, event_type: str, *, actor: str = "webhook") -> dict:
    occurred_at = datetime.utcnow()
    event = append_settlement_event(
        db,
        intent,
        event_type=event_type,
        status="SUCCESS",
        amount=intent.amount,
        currency=intent.currency,
        occurred_at=occurred_at,
        metadata={"source": "webhook"},
        actor=actor,
    )
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
        actor=actor,
    )
    update_metric("webhooks")
    return _serialize_settlement_event(event).model_dump()


@router.post("/chaindocs/validated")
async def chaindocs_validated(payload: WebhookPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    await verify_signature(request)
    enforce_rate_limit("chaindocs", payload.payment_intent_id)
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payload.payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    actor = "webhook:chaindocs"
    webhook_payload = payload.model_dump()
    webhook_payload["shipment_id"] = intent.shipment_id
    event_bus.publish(
        EventType.WEBHOOK_RECEIVED,
        webhook_payload,
        correlation_id=payload.payment_intent_id,
        actor=actor,
    )
    return _handle_event(db, intent, "PROOF_VALIDATED", actor=actor)


@router.post("/chaindocs/flagged")
async def chaindocs_flagged(payload: WebhookPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    await verify_signature(request)
    enforce_rate_limit("chaindocs", payload.payment_intent_id)
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payload.payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    actor = "webhook:chaindocs"
    webhook_payload = payload.model_dump()
    webhook_payload["shipment_id"] = intent.shipment_id
    event_bus.publish(
        EventType.WEBHOOK_RECEIVED,
        webhook_payload,
        correlation_id=payload.payment_intent_id,
        actor=actor,
    )
    return _handle_event(db, intent, "FAILED_COMPLIANCE_CHECK", actor=actor)


@router.post("/clearinghouse/authorized")
async def clearinghouse_authorized(payload: WebhookPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    await verify_signature(request)
    enforce_rate_limit("clearinghouse", payload.payment_intent_id)
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payload.payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    actor = "webhook:clearinghouse"
    webhook_payload = payload.model_dump()
    webhook_payload["shipment_id"] = intent.shipment_id
    event_bus.publish(
        EventType.WEBHOOK_RECEIVED,
        webhook_payload,
        correlation_id=payload.payment_intent_id,
        actor=actor,
    )
    return _handle_event(db, intent, "AUTHORIZED", actor=actor)


@router.post("/clearinghouse/settled")
async def clearinghouse_settled(payload: WebhookPayload, request: Request, db: Session = Depends(get_db)) -> dict:
    await verify_signature(request)
    enforce_rate_limit("clearinghouse", payload.payment_intent_id)
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payload.payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    actor = "webhook:clearinghouse"
    webhook_payload = payload.model_dump()
    webhook_payload["shipment_id"] = intent.shipment_id
    event_bus.publish(
        EventType.WEBHOOK_RECEIVED,
        webhook_payload,
        correlation_id=payload.payment_intent_id,
        actor=actor,
    )
    return _handle_event(db, intent, "CAPTURED", actor=actor)
