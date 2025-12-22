"""ChainStake analytics models."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Float, String, Index

from api.database import Base


class StakePosition(Base):
    """Aggregated stake position captured for analytics/visibility."""

    __tablename__ = "stake_positions"
    __table_args__ = (
        Index("ix_stake_positions_pool", "pool_id"),
        Index("ix_stake_positions_status", "status"),
        Index("ix_stake_positions_corridor", "corridor"),
        Index("ix_stake_positions_staked_at", "staked_at"),
    )

    id = Column(String, primary_key=True, default=lambda: f"STPOS-{uuid4()}")
    shipment_id = Column(String, nullable=False, index=True)
    payment_intent_id = Column(String, nullable=True, index=True)
    pool_id = Column(String, nullable=False)
    corridor = Column(String, nullable=True)
    notional_usd = Column(Float, nullable=False, default=0.0)
    staked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expected_maturity_at = Column(DateTime, nullable=True)
    realized_apy = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="QUEUED")
    risk_level = Column(String, nullable=True)
    payout_confidence = Column(Float, nullable=True)
    final_payout_amount = Column(Float, nullable=True)
