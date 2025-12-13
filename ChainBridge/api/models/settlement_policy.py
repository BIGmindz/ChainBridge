"""SQLAlchemy models for Settlement Policies in ChainBridge.

Settlement Policies define how money moves across milestones, with risk hooks
and conditional logic for automated and semi-automated payment flows.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Float, Index, String, Text

from api.database import Base


class SettlementPolicy(Base):
    """Represents a settlement policy governing payment flows.

    Settlement policies define milestone-based payment curves, risk conditions,
    payment rails, and exposure limits for automated settlement execution.
    """

    __tablename__ = "settlement_policies"
    __table_args__ = (
        Index("ix_settlement_policies_tenant_id", "tenant_id"),
        Index("ix_settlement_policies_effective", "effective_from", "effective_to"),
        Index("ix_settlement_policies_tenant_currency", "tenant_id", "currency"),
    )

    id = Column(String, primary_key=True, default=lambda: f"SPOL-{uuid4()}")
    tenant_id = Column(String, nullable=False)

    # Policy identification
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    policy_type = Column(String, nullable=True)  # STANDARD, EXPRESS, MILESTONE, ESCROW, etc.

    # Payment curve - defines milestone-based payout percentages
    curve = Column(JSON, nullable=False, default=list)
    # Example: [
    #   {"name": "Booking Confirmed", "event_type": "BOOKING_CONFIRMED", "percent": 10},
    #   {"name": "BOL Issued", "event_type": "BOL_ISSUED", "percent": 40},
    #   {"name": "Customs Cleared", "event_type": "CUSTOMS_CLEARED", "percent": 30},
    #   {"name": "POD Received", "event_type": "POD_RECEIVED", "percent": 20}
    # ]

    # Risk & compliance conditions
    conditions = Column(JSON, nullable=True)
    # Example: {
    #   "min_risk_score": 0, "max_risk_score": 70,
    #   "required_esg_score": 50,
    #   "blocked_countries": ["XX", "YY"],
    #   "requires_proof_pack": true
    # }

    # Financial limits
    max_exposure = Column(Float, nullable=True)  # Maximum total exposure under this policy
    min_transaction = Column(Float, nullable=True)
    max_transaction = Column(Float, nullable=True)
    currency = Column(String(3), nullable=False, default="USD")  # ISO 4217 currency code

    # Payment rails configuration
    rails = Column(JSON, nullable=True)  # List of supported rails: ["ACH", "WIRE", "XRPL", "USDC"]
    preferred_rail = Column(String, nullable=True)
    fallback_rails = Column(JSON, nullable=True)

    # Float & timing
    settlement_delay_hours = Column(Float, nullable=True)  # Minimum hold time before release
    float_reduction_target = Column(Float, nullable=True)  # Target float reduction (0.0 to 1.0)

    # Validity period
    effective_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    effective_to = Column(DateTime, nullable=True)  # Null = no expiration

    # Metadata
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    version = Column(String, nullable=True)  # For tracking policy versions

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<SettlementPolicy(id={self.id}, name={self.name}, currency={self.currency})>"
