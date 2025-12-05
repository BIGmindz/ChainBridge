"""Ricardian legal instrument model binding documents to on-chain control."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Index, String, func

from api.database import Base


class RicardianInstrument(Base):
    __tablename__ = "ricardian_instruments"
    __table_args__ = (
        Index("ix_ricardian_instrument_type", "instrument_type"),
        Index("ix_ricardian_physical_reference", "physical_reference"),
        Index(
            "ix_ricardian_chain_address",
            "smart_contract_chain",
            "smart_contract_address",
        ),
        Index("ix_ricardian_status", "status"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    instrument_type = Column(String, nullable=False)
    physical_reference = Column(String, nullable=False)

    pdf_uri = Column(String, nullable=False)
    pdf_ipfs_uri = Column(String, nullable=True)
    pdf_hash = Column(String, nullable=False)

    ricardian_version = Column(String, nullable=False, default="v1.1")
    governing_law = Column(String, nullable=False)

    supremacy_enabled = Column(Boolean, nullable=False, default=True)
    traditional_arbitration_uri = Column(String, nullable=True)
    material_adverse_override = Column(Boolean, nullable=False, default=False)

    smart_contract_chain = Column(String, nullable=True)
    smart_contract_address = Column(String, nullable=True)
    last_signed_tx_hash = Column(String, nullable=True)

    status = Column(String, nullable=False, default="ACTIVE")
    freeze_reason = Column(String, nullable=True)

    ricardian_metadata = Column(JSON, nullable=True)

    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
