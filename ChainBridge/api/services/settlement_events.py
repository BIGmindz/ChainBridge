"""SettlementEvent lifecycle utilities."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from api.events.bus import EventType, event_bus
from api.models.chainpay import PaymentIntent, SettlementEvent

logger = logging.getLogger(__name__)

EVENT_SEQUENCE = [
    "PAYMENT_INITIATED",
    "CREATED",
    "PROOF_ATTACHED",
    "PROOF_VALIDATED",
    "RISK_RECHECKED",
    "RECONCILED",
    "AUTHORIZED",
    "RELEASE_REQUESTED",
    "CASH_RELEASED",
    "CAPTURED",
    "FAILED_COMPLIANCE_CHECK",
    "FAILED_CLEARINGHOUSE",
    "FAILED",
    "REFUNDED",
    "SETTLEMENT_CLOSED",
    "STAKE_COMPLETED",
]
EVENT_INDEX = {etype: idx for idx, etype in enumerate(EVENT_SEQUENCE)}
TERMINAL_EVENTS = {
    "FAILED",
    "FAILED_COMPLIANCE_CHECK",
    "FAILED_CLEARINGHOUSE",
    "CASH_RELEASED",
    "SETTLEMENT_CLOSED",
    "REFUNDED",
    "CAPTURED",
}
ALLOWED_TRANSITIONS = {
    "PAYMENT_INITIATED": {"CREATED", "AUTHORIZED", "FAILED"},
    "CREATED": {
        "PROOF_ATTACHED",
        "PROOF_VALIDATED",
        "RISK_RECHECKED",
        "AUTHORIZED",
        "FAILED",
    },
    "PROOF_ATTACHED": {"PROOF_VALIDATED", "RISK_RECHECKED", "AUTHORIZED", "FAILED"},
    "PROOF_VALIDATED": {"RISK_RECHECKED", "AUTHORIZED", "FAILED"},
    "RISK_RECHECKED": {"AUTHORIZED", "FAILED", "FAILED_COMPLIANCE_CHECK"},
    "AUTHORIZED": {
        "RELEASE_REQUESTED",
        "CASH_RELEASED",
        "CAPTURED",
        "FAILED_CLEARINGHOUSE",
        "FAILED",
    },
    "RELEASE_REQUESTED": {
        "CASH_RELEASED",
        "CAPTURED",
        "FAILED_CLEARINGHOUSE",
        "FAILED",
    },
    "CASH_RELEASED": {"SETTLEMENT_CLOSED"},
    "CAPTURED": {"REFUNDED", "SETTLEMENT_CLOSED"},
    "REFUNDED": {"SETTLEMENT_CLOSED"},
}


def _normalize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return metadata or {}


def _validate_progression(last_event: Optional[SettlementEvent], new_event_type: str, occurred_at: datetime) -> None:
    if last_event:
        last_idx = EVENT_INDEX.get(last_event.event_type, -1)
        new_idx = EVENT_INDEX.get(new_event_type, -1)
        current_when = occurred_at.replace(tzinfo=None)
        last_when = last_event.occurred_at.replace(tzinfo=None) if last_event.occurred_at else current_when
        if current_when < last_when:
            raise ValueError("occurred_at must be >= previous event")
        if last_event.event_type in TERMINAL_EVENTS:
            raise ValueError("terminal event already reached")
        if new_idx < last_idx:
            raise ValueError("event_type regression not allowed")
        allowed = ALLOWED_TRANSITIONS.get(last_event.event_type, set())
        if allowed and new_event_type not in allowed:
            raise ValueError("transition not allowed")
    else:
        if new_event_type not in EVENT_INDEX:
            raise ValueError("unsupported event_type")


def _find_idempotent_match(
    db: Session,
    payment_intent_id: str,
    *,
    event_type: str,
    status: str,
    amount: float,
    currency: str,
    metadata: Dict[str, Any],
) -> Optional[SettlementEvent]:
    return (
        db.query(SettlementEvent)
        .filter(
            SettlementEvent.payment_intent_id == payment_intent_id,
            SettlementEvent.event_type == event_type,
            SettlementEvent.status == status,
            SettlementEvent.amount == amount,
            SettlementEvent.currency == currency,
            SettlementEvent.extra_metadata == metadata,
        )
        .order_by(SettlementEvent.occurred_at.desc())
        .first()
    )


def append_settlement_event(
    db: Session,
    intent: PaymentIntent,
    *,
    event_type: str,
    status: str,
    amount: float,
    currency: str,
    occurred_at: Optional[datetime],
    metadata: Optional[Dict[str, Any]],
    actor: Optional[str] = None,
) -> SettlementEvent:
    normalized_metadata = _normalize_metadata(metadata)
    existing = _find_idempotent_match(
        db,
        intent.id,
        event_type=event_type,
        status=status,
        amount=amount,
        currency=currency,
        metadata=normalized_metadata,
    )
    if existing:
        return existing

    occurred = occurred_at or datetime.utcnow()
    last_event = (
        db.query(SettlementEvent)
        .filter(SettlementEvent.payment_intent_id == intent.id)
        .order_by(SettlementEvent.sequence.desc(), SettlementEvent.occurred_at.desc())
        .first()
    )
    _validate_progression(last_event, event_type, occurred)
    next_sequence = (last_event.sequence + 1) if last_event else 1

    event = SettlementEvent(
        payment_intent_id=intent.id,
        event_type=event_type,
        status=status,
        amount=amount,
        currency=currency,
        occurred_at=occurred,
        extra_metadata=normalized_metadata,
        sequence=next_sequence,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info(
        "chainpay_settlement_event_appended",
        extra={
            "payment_intent_id": intent.id,
            "event_type": event_type,
            "status": status,
            "actor": actor or "system",
            "risk_level": intent.risk_level,
            "ready_for_payment": intent.status in {"PENDING", "AUTHORIZED"},
            "sequence": next_sequence,
        },
    )
    event_bus.publish(
        EventType.SETTLEMENT_EVENT_APPENDED,
        {
            "payment_intent_id": intent.id,
            "shipment_id": intent.shipment_id,
            "event_type": event_type,
            "status": status,
        },
        correlation_id=intent.id,
        actor=actor or "system",
        occurred_at=occurred,
    )
    return event


def replace_settlement_event(
    db: Session,
    event: SettlementEvent,
    *,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None,
    actor: Optional[str] = None,
) -> SettlementEvent:
    if event_type:
        event.event_type = event_type
    if status:
        event.status = status
    if amount is not None:
        event.amount = amount
    if currency:
        event.currency = currency
    if occurred_at:
        event.occurred_at = occurred_at
    if metadata is not None:
        event.extra_metadata = _normalize_metadata(metadata)

    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info(
        "chainpay_settlement_event_replaced",
        extra={
            "payment_intent_id": event.payment_intent_id,
            "event_id": event.id,
            "event_type": event.event_type,
            "status": event.status,
            "actor": actor or "system",
        },
    )
    return event


def delete_settlement_event(db: Session, event: SettlementEvent, *, actor: Optional[str] = None) -> None:
    db.delete(event)
    db.commit()
    logger.info(
        "chainpay_settlement_event_deleted",
        extra={
            "payment_intent_id": event.payment_intent_id,
            "event_id": event.id,
            "event_type": event.event_type,
            "actor": actor or "system",
        },
    )
