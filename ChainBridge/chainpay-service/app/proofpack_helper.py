"""
Utilities for resolving real milestone data for ProofPack generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import MilestoneSettlement, PaymentStatus


@dataclass
class MilestoneSnapshot:
    """Serializable snapshot of a milestone's state for ProofPack assembly."""

    milestone_id: str
    shipment_reference: str
    amount: float
    currency: str
    state: str
    freight_token_id: Optional[int]
    last_updated: datetime


def get_milestone_snapshot(db: Session, milestone_id: str) -> Optional[MilestoneSnapshot]:
    """
    Look up a milestone by canonical identifier.
    """
    if not milestone_id:
        return None

    milestone: MilestoneSettlement | None = (
        db.query(MilestoneSettlement).filter(MilestoneSettlement.milestone_identifier == milestone_id).first()
    )
    if not milestone:
        return None

    state = milestone.status.value if milestone.status else PaymentStatus.PENDING.value

    return MilestoneSnapshot(
        milestone_id=milestone.milestone_identifier or milestone_id,
        shipment_reference=milestone.shipment_reference or "UNKNOWN",
        amount=milestone.amount,
        currency=milestone.currency,
        state=state,
        freight_token_id=milestone.freight_token_id,
        last_updated=milestone.updated_at or milestone.created_at or datetime.utcnow(),
    )


def fetch_milestone_snapshot(milestone_id: str) -> Optional[MilestoneSnapshot]:
    """
    Convenience wrapper that manages its own DB session.
    """
    db = SessionLocal()
    try:
        return get_milestone_snapshot(db, milestone_id)
    finally:
        db.close()
