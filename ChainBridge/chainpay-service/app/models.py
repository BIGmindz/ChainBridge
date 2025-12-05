"""
Database models for ChainPay Service.

This module contains SQLAlchemy models for payment intents and settlements,
including risk-based settlement logic tied to freight tokens.
"""

import enum
from datetime import datetime, timedelta

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class PaymentStatus(str, enum.Enum):
    """Enumeration of payment statuses."""

    PENDING = "pending"
    APPROVED = "approved"
    SETTLED = "settled"
    DELAYED = "delayed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RiskTier(str, enum.Enum):
    """Risk-based settlement tiers."""

    LOW = "low"  # Immediate settlement (0.0-0.33)
    MEDIUM = "medium"  # Delayed settlement with review (0.33-0.67)
    HIGH = "high"  # Requires manual review (0.67-1.0)


class ScheduleType(str, enum.Enum):
    """Payment schedule types."""

    FULL_ON_POD = "full_on_pod"  # 100% released at POD
    MILESTONE = "milestone"  # Split across multiple milestones
    CUSTOM = "custom"  # User-defined percentages


class PaymentIntent(Base):
    """
    Payment intent tied to a freight token.

    Represents a payment that needs to be settled based on shipment delivery
    and risk factors. Settlement is conditional on freight token status and
    risk scoring from ChainIQ.
    """

    __tablename__ = "payment_intents"

    id = Column(Integer, primary_key=True, index=True)

    # Freight token reference (external service)
    freight_token_id = Column(Integer, nullable=False, index=True)

    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    description = Column(String(255), nullable=True)

    # Risk information (cached from freight token at creation time)
    risk_score = Column(Float, nullable=True)  # 0.0-1.0
    risk_category = Column(String(20), nullable=True)  # low, medium, high
    risk_tier = Column(Enum(RiskTier), default=RiskTier.MEDIUM, nullable=False, index=True)


    # Payment status
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)

    # Settlement tracking
    settlement_approved_at = Column(DateTime, nullable=True)
    settlement_delayed_until = Column(DateTime, nullable=True)
    settlement_completed_at = Column(DateTime, nullable=True)

    # Settlement reason/notes
    settlement_reason = Column(Text, nullable=True)
    settlement_notes = Column(Text, nullable=True)

    # --- TOKENOMICS FIELDS ---
    token_reward = Column(Float, nullable=True, comment="Tokenomics: total token reward")
    token_burn = Column(Float, nullable=True, comment="Tokenomics: total token burn")
    token_net = Column(Float, nullable=True, comment="Tokenomics: net token after burn")
    governance_trace_id = Column(String(64), nullable=True, comment="Tokenomics: ALEX governance trace ID")

    # Relationships
    payment_schedule = relationship("PaymentSchedule", uselist=False, back_populates="payment_intent")
    milestone_settlements = relationship("MilestoneSettlement", back_populates="payment_intent")

    # Audit timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return (
            f"<PaymentIntent(id={self.id}, token={self.freight_token_id}, "
            f"amount={self.amount}, status={self.status}, risk={self.risk_tier})>"
        )

    def get_settlement_delay(self) -> timedelta:
        """
        Calculate settlement delay based on risk tier.

        Returns:
            timedelta for when payment should be settled
        """
        if self.risk_tier == RiskTier.LOW:
            return timedelta(hours=0)  # Immediate
        elif self.risk_tier == RiskTier.MEDIUM:
            return timedelta(hours=24)  # Next business day
        else:  # HIGH
            return timedelta(days=3)  # Manual review required

    def is_ready_to_settle(self) -> bool:
        """
        Check if payment is ready to settle based on status and delay.

        Returns:
            bool indicating if settlement can proceed
        """
        if self.status not in [PaymentStatus.PENDING, PaymentStatus.DELAYED]:
            return False

        if self.settlement_delayed_until is None:
            return True

        return datetime.utcnow() >= self.settlement_delayed_until


class SettlementLog(Base):
    """
    Audit log for payment settlements.

    Tracks all settlement decisions, approvals, delays, and rejections
    for compliance and debugging purposes.
    """

    __tablename__ = "settlement_logs"

    id = Column(Integer, primary_key=True, index=True)
    payment_intent_id = Column(Integer, ForeignKey("payment_intents.id"), nullable=False, index=True)

    # Settlement action
    action = Column(String(50), nullable=False)  # approved, delayed, rejected, settled
    reason = Column(String(255), nullable=True)
    risk_factors = Column(Text, nullable=True)  # JSON-encoded risk assessment

    # Actor information
    triggered_by = Column(String(50), default="system", nullable=False)  # system, manual
    approved_by = Column(String(255), nullable=True)  # User who approved

    # Timing
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<SettlementLog(payment={self.payment_intent_id}, " f"action={self.action}, reason={self.reason})>"


class PaymentSchedule(Base):
    """
    Milestone-based payment schedule for a freight token.

    Defines what percentage of the total payment is released at each shipment milestone.
    For example, a LOW-risk shipment might release 20% at PICKUP_CONFIRMED, 70% at POD_CONFIRMED,
    and 10% at CLAIM_WINDOW_CLOSED.

    There is exactly one schedule per payment intent.
    """

    __tablename__ = "payment_schedules"

    id = Column(Integer, primary_key=True, index=True)
    payment_intent_id = Column(
        Integer,
        ForeignKey("payment_intents.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Schedule configuration
    schedule_type = Column(
        Enum(ScheduleType),
        default=ScheduleType.MILESTONE,
        nullable=False,
        index=True,
        comment="Type of payment schedule (full_on_pod, milestone, custom)",
    )
    description = Column(String(255), nullable=True, comment="Human-readable description of the schedule")

    # Risk tier determines default schedule percentages
    risk_tier = Column(
        Enum(RiskTier),
        nullable=False,
        index=True,
        comment="Risk tier used to compute default schedule",
    )

    # Relationships
    payment_intent = relationship("PaymentIntent", back_populates="payment_schedule")
    items = relationship("PaymentScheduleItem", back_populates="schedule", cascade="all, delete-orphan")

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<PaymentSchedule(id={self.id}, payment_intent_id={self.payment_intent_id}, schedule_type={self.schedule_type}, risk_tier={self.risk_tier})>"


class PaymentScheduleItem(Base):
    """
    Individual milestone and its payment percentage in a schedule.

    For example, one item might be:
      event_type='POD_CONFIRMED', percentage=0.70, sequence=2

    This means 70% of the total payment is released when POD_CONFIRMED event occurs.
    """

    __tablename__ = "payment_schedule_items"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("payment_schedules.id"), nullable=False, index=True)

    # Milestone definition
    event_type = Column(
        String(50),
        nullable=False,
        comment="Shipment event type that triggers payment (e.g., 'pod_confirmed')",
    )
    percentage = Column(
        Float,
        nullable=False,
        comment="Percentage of total payment for this milestone (0.0-1.0)",
    )
    sequence = Column(
        Integer,
        nullable=False,
        comment="Sequence order of this milestone in the schedule",
    )

    # Relationship
    schedule = relationship("PaymentSchedule", back_populates="items")

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<PaymentScheduleItem(id={self.id}, event_type={self.event_type}, percentage={self.percentage}, sequence={self.sequence})>"


class MilestoneSettlement(Base):
    """
    Record of a partial settlement tied to a shipment event milestone.

    When a shipment event (e.g., POD_CONFIRMED) occurs, a MilestoneSettlement record
    is created for the corresponding scheduled payment. This prevents double-payment
    via a unique constraint on (payment_intent_id, event_type).

    The amount is computed as: payment_intent.amount * schedule_item.percentage
    """

    __tablename__ = "milestone_settlements"

    id = Column(Integer, primary_key=True, index=True)
    payment_intent_id = Column(Integer, ForeignKey("payment_intents.id"), nullable=False, index=True)
    schedule_item_id = Column(Integer, ForeignKey("payment_schedule_items.id"), nullable=True, index=True)

    # Milestone identification
    milestone_identifier = Column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        comment="Canonical milestone identifier '<shipment_reference>-M<index>'",
    )
    shipment_reference = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Canonical shipment reference derived from freight token",
    )
    freight_token_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="Freight token ID cached at milestone creation time",
    )
    event_type = Column(
        String(50),
        nullable=False,
        comment="Shipment event type that triggered this settlement",
    )

    # Amount and currency
    amount = Column(Float, nullable=False, comment="Amount to settle for this milestone")
    currency = Column(String(10), default="USD", nullable=False, comment="Currency for the settlement")

    # Status and timing
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    occurred_at = Column(DateTime, nullable=True, comment="When the triggering shipment event occurred")
    settled_at = Column(DateTime, nullable=True, comment="When the settlement was completed")

    # Payment processing details
    provider = Column(
        String(50),
        default="INTERNAL_LEDGER",
        nullable=False,
        comment="Payment provider (INTERNAL_LEDGER, STRIPE, ACH, etc.)",
    )
    reference = Column(
        String(255),
        nullable=True,
        comment="External reference ID from payment provider",
    )

    # Relationships
    payment_intent = relationship("PaymentIntent", back_populates="milestone_settlements")

    # Unique constraint: no double-paying for the same event
    __table_args__ = (UniqueConstraint("payment_intent_id", "event_type", name="uq_milestone_payment_event"),)

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return (
            f"<MilestoneSettlement(id={self.id}, payment_intent={self.payment_intent_id}, "
            f"event_type={self.event_type}, amount={self.amount}, status={self.status})>"
        )
