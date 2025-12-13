"""SQLAlchemy models for Exception management in ChainBridge.

Exceptions represent work items for operators - manage-by-exception workflow
for handling anomalies, delays, missing documents, claims, and other issues.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text

from api.database import Base


class Exception(Base):
    """Represents an operational exception requiring attention.

    Exceptions are the core work items in the manage-by-exception paradigm.
    They can be created by system automation (risk triggers, SLA breaches)
    or manually by operators.
    """

    __tablename__ = "exceptions"
    __table_args__ = (
        Index("ix_exceptions_tenant_id", "tenant_id"),
        Index("ix_exceptions_shipment_id", "shipment_id"),
        Index("ix_exceptions_status", "status"),
        Index("ix_exceptions_severity", "severity"),
        Index("ix_exceptions_tenant_status", "tenant_id", "status"),
        Index("ix_exceptions_owner", "owner_user_id"),
    )

    id = Column(String, primary_key=True, default=lambda: f"EXC-{uuid4()}")
    tenant_id = Column(String, nullable=False)

    # Linked entities
    shipment_id = Column(String, nullable=True)  # FK to shipments when available
    playbook_id = Column(String, ForeignKey("playbooks.id"), nullable=True)
    payment_intent_id = Column(String, nullable=True)  # Link to ChainPay if relevant

    # Exception classification
    type = Column(String, nullable=False)  # DELAY, MISSING_POD, CLAIM_RISK, DOCUMENT_GAP, SLA_BREACH, etc.
    severity = Column(String, nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String, nullable=False, default="OPEN")  # OPEN, IN_PROGRESS, RESOLVED, WONT_FIX, ESCALATED

    # Ownership
    owner_user_id = Column(String, nullable=True)  # User currently assigned
    escalated_to = Column(String, nullable=True)  # User/role escalated to

    # Description
    summary = Column(String(500), nullable=False)
    details = Column(JSON, nullable=True)  # Structured details (machine-readable context)
    notes = Column(Text, nullable=True)  # Human-readable notes

    # Resolution
    resolution_type = Column(String, nullable=True)  # MANUAL_FIX, AUTO_RESOLVED, WAIVED, etc.
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)

    # Source tracking
    source = Column(String, nullable=True)  # SYSTEM, USER, INTEGRATION, CHAINIQ, etc.
    source_event_id = Column(String, nullable=True)  # ID of triggering event

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<Exception(id={self.id}, type={self.type}, status={self.status})>"
