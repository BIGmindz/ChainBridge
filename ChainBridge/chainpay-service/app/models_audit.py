# app/models_audit.py
"""
Audit Event and Decision Log models for ChainPay.

NOTE:
Fields and semantics are aligned with docs/product/CHAINBRIDGE_AUDIT_PROOFPACK_SPEC.md (v0).
See that spec for details on audit and ProofPack behavior.

AuditEvent -> "what happened" (append-only event log)
DecisionLog -> "why it happened" (decision trace with policy/model versions)
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from app.models import Base


class AuditEvent(Base):
    """
    Audit Event - records "what happened" in ChainPay.

    Each row is an immutable record of a significant system event.
    Events are append-only and should never be modified or deleted.
    """

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # What happened
    event_type = Column(String(64), nullable=False)  # e.g. payout_released, payment_approved
    actor_type = Column(String(64), nullable=False)  # e.g. "system", "user", "agent"
    actor_id = Column(String(128), nullable=True)  # user id, service id, agent GID
    source_system = Column(String(128), nullable=True)  # EDI, IoT, internal API, ChainIQ

    # Correlation IDs for cross-system traceability
    shipment_id = Column(String(128), nullable=True, index=True)
    payment_id = Column(String(128), nullable=True, index=True)
    customer_id = Column(String(128), nullable=True, index=True)
    correlation_id = Column(String(128), nullable=True, index=True)

    # Payload summary (not raw payload - just summary/hash for audit trail)
    payload_hash = Column(String(128), nullable=True)
    payload_meta = Column(JSON, nullable=True)  # summarized info, not raw payload

    # Relationship to decisions
    decisions = relationship("DecisionLog", back_populates="audit_event")


class DecisionLog(Base):
    """
    Decision Log - records "why it happened" in ChainPay.

    Each row captures the reasoning behind a decision, including:
    - Policy/model versions used
    - Input snapshot at decision time
    - Rules that fired
    - Human-readable explanation
    - Override information if applicable
    """

    __tablename__ = "decision_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Link back to triggering event (optional - some decisions may not have a direct event)
    audit_event_id = Column(Integer, ForeignKey("audit_events.id"), nullable=True)
    audit_event = relationship("AuditEvent", back_populates="decisions")

    # What decision was made
    decision_type = Column(String(64), nullable=False)  # e.g. "payout_decision", "risk_override"
    outcome = Column(String(64), nullable=False)  # e.g. "approve", "hold", "reject"

    # Policy and model versions for reproducibility
    risk_policy_version = Column(String(64), nullable=True)
    payment_policy_version = Column(String(64), nullable=True)
    model_version = Column(String(64), nullable=True)

    # Input snapshot and reasoning (lightweight JSON)
    input_snapshot = Column(JSON, nullable=True)  # key inputs at decision time
    rules_fired = Column(JSON, nullable=True)  # which rules triggered
    explanation = Column(JSON, nullable=True)  # human-readable reasoning

    # Override tracking (per spec: overrides must be separate records with justification)
    overridden = Column(Integer, nullable=False, default=0)  # 0 = no, 1 = yes
    override_actor_id = Column(String(128), nullable=True)
    override_reason = Column(String(512), nullable=True)
