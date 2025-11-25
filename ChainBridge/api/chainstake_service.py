"""ChainStake v1 skeleton service."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.events.bus import EventType, event_bus
from api.models.chainpay import PaymentIntent, StakeJob
from api.models.chaindocs import Shipment
from api.services.settlement_events import append_settlement_event

STAKE_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"}


def _require_shipment(db: Session, shipment_id: str) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise ValueError("Shipment not found")
    return shipment


def _find_payment_intent(db: Session, payment_intent_id: Optional[str]) -> Optional[PaymentIntent]:
    if not payment_intent_id:
        return None
    return db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()


def create_stake_job(
    db: Session,
    *,
    shipment_id: str,
    requested_amount: float,
    payment_intent_id: Optional[str] = None,
) -> StakeJob:
    _require_shipment(db, shipment_id)
    job = StakeJob(
        shipment_id=shipment_id,
        payment_intent_id=payment_intent_id,
        status="PENDING",
        requested_amount=requested_amount,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    event_bus.publish(
        EventType.STAKE_CREATED,
        {"stake_job_id": job.id, "shipment_id": shipment_id, "payment_intent_id": payment_intent_id},
        correlation_id=payment_intent_id or shipment_id,
        actor="system:stake",
        occurred_at=job.created_at,
    )
    return job


def execute_stake_job(db: Session, job: StakeJob) -> StakeJob:
    job.status = "IN_PROGRESS"
    db.add(job)
    db.commit()
    db.refresh(job)

    job.status = "COMPLETED"
    job.settled_amount = job.requested_amount
    job.updated_at = datetime.utcnow()
    db.add(job)
    db.commit()
    db.refresh(job)

    intent = _find_payment_intent(db, job.payment_intent_id)
    currency = intent.currency if intent else "USD"
    if intent:
        append_settlement_event(
            db,
            intent,
            event_type="STAKE_COMPLETED",
            status="SUCCESS",
            amount=job.settled_amount or job.requested_amount,
            currency=currency,
            occurred_at=job.updated_at,
            metadata={"stake_job_id": job.id},
            actor="system:stake",
        )
    event_bus.publish(
        EventType.STAKE_COMPLETED,
        {
            "stake_job_id": job.id,
            "shipment_id": job.shipment_id,
            "payment_intent_id": job.payment_intent_id,
            "settled_amount": job.settled_amount,
        },
        correlation_id=job.payment_intent_id or job.shipment_id,
        actor="system:stake",
        occurred_at=job.updated_at,
    )
    return job
