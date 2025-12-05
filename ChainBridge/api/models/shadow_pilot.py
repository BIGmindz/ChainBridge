"""ORM models for Shadow Pilot runs and shipments."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from api.database import Base


class ShadowPilotRun(Base):
    __tablename__ = "shadow_pilot_runs"
    __table_args__ = (UniqueConstraint("run_id", name="uq_shadow_pilot_run_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(128), nullable=False)
    prospect_name = Column(String(255), nullable=False)
    period_months = Column(Integer, nullable=False)
    total_gmv_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    financeable_gmv_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    financed_gmv_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    protocol_revenue_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    working_capital_saved_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    losses_avoided_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    salvage_revenue_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    average_days_pulled_forward = Column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    shipments_evaluated = Column(Integer, nullable=False, default=0)
    shipments_financeable = Column(Integer, nullable=False, default=0)
    input_filename = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    shipments = relationship(
        "ShadowPilotShipment",
        back_populates="run",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ShadowPilotShipment(Base):
    __tablename__ = "shadow_pilot_shipments"
    __table_args__ = (
        Index("idx_shadow_pilot_shipments_run_id", "run_id"),
        Index("idx_shadow_pilot_shipments_corridor", "corridor"),
        Index("idx_shadow_pilot_shipments_customer_segment", "customer_segment"),
        Index("idx_shadow_pilot_shipments_shipment_id", "shipment_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(128), ForeignKey("shadow_pilot_runs.run_id"), nullable=False)
    shipment_id = Column(String(255), nullable=False)
    corridor = Column(String(255), nullable=True)
    mode = Column(String(64), nullable=True)
    customer_segment = Column(String(128), nullable=True)
    cargo_value_usd = Column(Numeric(20, 2), nullable=False)
    event_truth_score = Column(Numeric(5, 4), nullable=False)
    eligible_for_finance = Column(Boolean, nullable=False, default=False)
    financed_amount_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    days_pulled_forward = Column(Integer, nullable=False, default=0)
    wc_saved_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    protocol_revenue_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    avoided_loss_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    salvage_revenue_usd = Column(Numeric(20, 2), nullable=False, default=Decimal("0"))
    exception_flag = Column(Boolean, nullable=False, default=False)
    loss_flag = Column(Boolean, nullable=False, default=False)

    run = relationship("ShadowPilotRun", back_populates="shipments")
