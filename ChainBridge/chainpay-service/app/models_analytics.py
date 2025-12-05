from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
)

from .models import Base

# Avoid duplicate table definition when the module is re-imported in tests
if "chainpay_settlement_outcomes" in Base.metadata.tables:
    Base.metadata.remove(Base.metadata.tables["chainpay_settlement_outcomes"])


class SettlementOutcome(Base):
    __tablename__ = "chainpay_settlement_outcomes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)

    shipment_id = Column(String, index=True, nullable=False)
    corridor_id = Column(String, index=True, nullable=True)

    risk_score_initial = Column(Float, nullable=True)
    risk_tier_initial = Column(String, nullable=True)

    payout_pickup_percent = Column(Float, nullable=True)
    payout_delivered_percent = Column(Float, nullable=True)
    payout_claim_percent = Column(Float, nullable=True)
    claim_window_days = Column(Integer, nullable=True)
    payout_policy_version = Column(String, nullable=True)

    cb_usd_total = Column(Float, nullable=False)
    cb_usd_reserved_initial = Column(Float, nullable=True)
    cb_usd_loss_realized = Column(Float, nullable=True)
    cb_usd_reserved_unused = Column(Float, nullable=True)

    pickup_timestamp = Column(DateTime(timezone=True), nullable=True)
    delivered_timestamp = Column(DateTime(timezone=True), nullable=True)
    first_payment_timestamp = Column(DateTime(timezone=True), nullable=True)
    final_payment_timestamp = Column(DateTime(timezone=True), nullable=True)
    claim_window_close_timestamp = Column(DateTime(timezone=True), nullable=True)

    had_claim = Column(Boolean, nullable=False, default=False)
    had_dispute = Column(Boolean, nullable=False, default=False)
    settlement_status = Column(String, nullable=True)

    analytics_version = Column(String, nullable=False, default="v1")
    created_at_utc = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "shipment_id",
            "analytics_version",
            "payout_policy_version",
            name="uq_outcome_shipment_policy_analytics",
        ),
    )
