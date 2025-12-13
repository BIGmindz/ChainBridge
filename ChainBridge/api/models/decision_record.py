"""SQLAlchemy models for Decision Records in ChainBridge.

Decision Records provide an immutable audit trail of risk and settlement
decisions made by users, applications, or automated systems.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Index, String, Text

from api.database import Base


class DecisionRecord(Base):
    """Represents an auditable record of a risk or settlement decision.

    Decision records capture who/what made a decision, what inputs were
    considered, what policy was applied, and what the outcome was.
    This enables regulatory compliance, dispute resolution, and ML training.
    """

    __tablename__ = "decision_records"
    __table_args__ = (
        Index("ix_decision_records_tenant_id", "tenant_id"),
        Index("ix_decision_records_type", "type"),
        Index("ix_decision_records_actor", "actor_type", "actor_id"),
        Index("ix_decision_records_created", "created_at"),
        Index("ix_decision_records_entity", "entity_type", "entity_id"),
    )

    id = Column(String, primary_key=True, default=lambda: f"DEC-{uuid4()}")
    tenant_id = Column(String, nullable=False)

    # Decision type classification
    type = Column(String, nullable=False)  # RISK_DECISION, SETTLEMENT_DECISION, APPROVAL, OVERRIDE, etc.
    subtype = Column(String, nullable=True)  # More specific classification

    # Who made the decision
    actor_type = Column(String, nullable=False)  # USER, APP, SYSTEM, AGENT
    actor_id = Column(String, nullable=False)  # User ID, app/service name, or system identifier
    actor_name = Column(String, nullable=True)  # Human-readable actor name

    # What entity the decision is about
    entity_type = Column(String, nullable=True)  # SHIPMENT, PAYMENT_INTENT, PARTY, EXCEPTION, etc.
    entity_id = Column(String, nullable=True)  # ID of the entity

    # Policy that governed the decision
    policy_id = Column(String, nullable=True)  # FK to SettlementPolicy or risk policy
    policy_type = Column(String, nullable=True)  # SETTLEMENT_POLICY, RISK_POLICY, COMPLIANCE_RULE
    policy_version = Column(String, nullable=True)

    # Decision inputs (for reproducibility)
    inputs_hash = Column(String, nullable=True)  # SHA-256 hash of inputs for tamper detection
    inputs_snapshot = Column(JSON, nullable=True)  # Partial or full snapshot of input data

    # Decision outputs
    outputs = Column(JSON, nullable=False)
    # Example: {
    #   "decision": "APPROVED",
    #   "score": 75,
    #   "confidence": 0.92,
    #   "flags": ["LOW_RISK", "TRUSTED_CARRIER"],
    #   "amount_approved": 50000.00
    # }

    # Explanation & rationale
    explanation = Column(Text, nullable=True)  # Human-readable explanation
    primary_factors = Column(JSON, nullable=True)  # Key factors that influenced decision

    # Override tracking
    overrides_decision_id = Column(String, nullable=True)  # If this overrides a previous decision
    override_reason = Column(Text, nullable=True)

    # Timestamps (created_at only - decisions are immutable)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DecisionRecord(id={self.id}, type={self.type}, actor={self.actor_type}:{self.actor_id})>"
