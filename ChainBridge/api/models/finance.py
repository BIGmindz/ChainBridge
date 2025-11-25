"""Finance models for inventory stakes backed by Ricardian instruments."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Index

from api.database import Base


class InventoryStake(Base):
    __tablename__ = "inventory_stakes"
    __table_args__ = (
        Index("ix_inventory_stakes_physical", "physical_reference"),
        Index("ix_inventory_stakes_status", "status"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    physical_reference = Column(String, nullable=False, index=True)
    ricardian_instrument_id = Column(String, ForeignKey("ricardian_instruments.id"), nullable=True, index=True)
    principal_amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    max_advance_rate = Column(Float, nullable=False)
    applied_advance_rate = Column(Float, nullable=False)
    base_apr = Column(Float, nullable=False)
    risk_adjusted_apr = Column(Float, nullable=False)
    notional_value = Column(Float, nullable=False)
    lender_name = Column(String, nullable=True)
    borrower_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE | REPAID | LIQUIDATED | CANCELLED | PENDING
    reason_code = Column(String, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)
    repaid_at = Column(DateTime, nullable=True)
    liquidated_at = Column(DateTime, nullable=True)
