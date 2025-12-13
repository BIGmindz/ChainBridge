"""SQLAlchemy models for Party entities in ChainBridge.

Parties represent all stakeholders in the logistics network: shippers, carriers,
brokers, facilities, financial institutions, etc.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, String, Text

from api.database import Base


class Party(Base):
    """Represents a participant (company or entity) in the logistics network.

    Parties can be shippers, carriers, brokers, facilities, banks, or any other
    stakeholder that participates in shipments, settlements, or risk assessments.
    """

    __tablename__ = "parties"
    __table_args__ = (
        Index("ix_parties_tenant_id", "tenant_id"),
        Index("ix_parties_type", "type"),
        Index("ix_parties_tenant_type", "tenant_id", "type"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, nullable=False)

    # Party identification
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # SHIPPER, CARRIER, BROKER, FACILITY, BANK, CUSTOMS, etc.
    legal_name = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)  # EIN, VAT, etc.
    duns_number = Column(String, nullable=True)

    # Contact & location
    country_code = Column(String(3), nullable=True)  # ISO 3166-1 alpha-3
    address = Column(Text, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)

    # Status & metadata
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE, SUSPENDED, INACTIVE
    extra_data = Column("party_metadata", Text, nullable=True)  # JSON string for extensibility

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<Party(id={self.id}, name={self.name}, type={self.type})>"
