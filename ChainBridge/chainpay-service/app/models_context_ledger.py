"""Context Ledger models for ChainPay governance decisions."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from .models import Base

# Avoid duplicate table definition when the module is re-imported in tests
if "context_ledger_entries" in Base.metadata.tables:
    Base.metadata.remove(Base.metadata.tables["context_ledger_entries"])


class ContextLedgerEntry(Base):
    __tablename__ = "context_ledger_entries"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    agent_id = Column(String(100), nullable=False)
    gid = Column(String(50), nullable=False)
    role_tier = Column(Integer, nullable=False)
    gid_hgp_version = Column(String(20), nullable=False)

    decision_type = Column(String(100), nullable=False, index=True)
    decision_status = Column(String(20), nullable=False, index=True)

    shipment_id = Column(String(100), nullable=True, index=True)
    payer_id = Column(String(100), nullable=True, index=True)
    payee_id = Column(String(100), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    corridor = Column(String(50), nullable=True)

    risk_score = Column(Float, nullable=False)
    reason_codes = Column(Text, nullable=False)
    policies_applied = Column(Text, nullable=False)
    economic_justification = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ContextLedgerEntry(id={self.id}, decision_status={self.decision_status}, "
            f"shipment_id={self.shipment_id}, risk_score={self.risk_score})>"
        )
