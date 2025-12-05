"""SQLAlchemy models for ChainPay storage."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from api.database import Base


class StakeJob(Base):
    """Stake job pipeline placeholder for future Web3 execution."""

    __tablename__ = "stake_jobs"
    __table_args__ = (
        Index("ix_stake_jobs_shipment", "shipment_id"),
        Index("ix_stake_jobs_status", "status"),
    )

    id = Column(String, primary_key=True, default=lambda: f"STAKE-{uuid4()}")
    shipment_id = Column(String, nullable=False, index=True)
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"), nullable=True, index=True)
    status = Column(String, nullable=False, default="PENDING")
    requested_amount = Column(Float, nullable=False)
    settled_amount = Column(Float, nullable=True)
    failure_reason = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class SettlementPlan(Base):
    """Represents a settlement plan for a shipment."""

    __tablename__ = "settlement_plans"

    id = Column(String, primary_key=True, index=True)
    shipment_id = Column(String, index=True)
    template_id = Column(String)
    total_value = Column(Float)
    float_reduction_estimate = Column(Float, default=0.99)

    milestones = relationship(
        "SettlementMilestone",
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class SettlementMilestone(Base):
    """Represents a milestone payout in a settlement plan."""

    __tablename__ = "settlement_milestones"

    id = Column(String, primary_key=True, index=True)
    plan_id = Column(String, ForeignKey("settlement_plans.id"), index=True)
    event = Column(String)
    payout_pct = Column(Float)
    status = Column(String)
    paid_at = Column(String, nullable=True)

    plan = relationship("SettlementPlan", back_populates="milestones")


class PaymentIntent(Base):
    """Represents a payment hold/intent anchored to a shipment and risk snapshot."""

    __tablename__ = "payment_intents"
    __table_args__ = (
        UniqueConstraint(
            "shipment_id",
            "latest_risk_snapshot_id",
            name="uq_payment_intent_shipment_snapshot",
        ),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: f"PAY-{uuid4()}")
    shipment_id = Column(String, index=True, nullable=False)
    latest_risk_snapshot_id = Column(Integer, ForeignKey("document_health_snapshots.id"), nullable=True, index=True)
    freight_reference = Column(String, nullable=True)
    counterparty = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING", index=True)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)
    proof_pack_id = Column(String, nullable=True)
    proof_hash = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    clearing_partner = Column(String, nullable=True)
    intent_hash = Column(String, nullable=True)
    risk_gate_reason = Column(String, nullable=True)
    compliance_blocks = Column(JSON, nullable=True)
    payout_confidence = Column(Float, nullable=True)
    auto_adjusted_amount = Column(Float, nullable=True)
    final_payout_amount = Column(Float, nullable=True)
    adjustment_reason = Column(String, nullable=True)
    reconciliation_explanation = Column(JSON, nullable=True)
    ready_at = Column(DateTime, nullable=True)
    calculated_amount = Column(Float, nullable=True)
    pricing_breakdown = Column(JSON, nullable=True)
    recon_state = Column(String, nullable=True, index=True)
    recon_score = Column(Float, nullable=True)
    recon_policy_id = Column(String, nullable=True)
    approved_amount = Column(Float, nullable=True)
    held_amount = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    settlement_events = relationship(
        "SettlementEvent",
        back_populates="payment_intent",
        cascade="all, delete-orphan",
        order_by="SettlementEvent.occurred_at.asc()",
    )


class SettlementEvent(Base):
    """Represents a settlement lifecycle event for a PaymentIntent."""

    __tablename__ = "settlement_events"
    __table_args__ = (
        Index("ix_settlement_events_intent_occurred", "payment_intent_id", "occurred_at"),
        Index("ix_settlement_events_intent_sequence", "payment_intent_id", "sequence"),
        Index("ix_settlement_events_type", "event_type"),
        Index("ix_settlement_events_type_occurred", "event_type", "occurred_at"),
        Index("ix_settlement_events_status", "status"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: f"SET-{uuid4()}")
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"), index=True, nullable=False)
    event_type = Column(String, nullable=False)  # CREATED | AUTHORIZED | CAPTURED | FAILED | REFUNDED
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING")  # PENDING | SUCCESS | FAILED
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    extra_metadata = Column("metadata", JSON, nullable=True)
    sequence = Column(Integer, nullable=False, default=0)

    payment_intent = relationship("PaymentIntent", back_populates="settlement_events")


class SettlementEventAudit(Base):
    """UI-facing audit log for settlement-related events."""

    __tablename__ = "settlement_event_audit"
    __table_args__ = (
        Index("ix_settlement_event_audit_payment_intent", "payment_intent_id"),
        Index("ix_settlement_event_audit_shipment", "shipment_id"),
        Index("ix_settlement_event_audit_occurred_at_desc", sa.text("occurred_at DESC")),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    payment_intent_id = Column(String, nullable=True)
    shipment_id = Column(String, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    payload_summary = Column(JSON, nullable=True)
