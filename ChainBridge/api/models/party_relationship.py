"""SQLAlchemy models for Party Relationships in ChainBridge.

Party Relationships model the multi-tier graph of business relationships
between parties - supplier networks, subcontractor chains, ownership, etc.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text

from api.database import Base


class PartyRelationship(Base):
    """Represents a relationship between two parties in the network.

    This enables modeling of complex supply chains, subcontractor networks,
    ownership structures, and other multi-tier business relationships.
    """

    __tablename__ = "party_relationships"
    __table_args__ = (
        Index("ix_party_relationships_tenant_id", "tenant_id"),
        Index("ix_party_relationships_from_party", "from_party_id"),
        Index("ix_party_relationships_to_party", "to_party_id"),
        Index("ix_party_relationships_type", "type"),
        Index("ix_party_relationships_tenant_from", "tenant_id", "from_party_id"),
        Index("ix_party_relationships_tenant_to", "tenant_id", "to_party_id"),
    )

    id = Column(String, primary_key=True, default=lambda: f"REL-{uuid4()}")
    tenant_id = Column(String, nullable=False)

    # Relationship endpoints
    from_party_id = Column(String, ForeignKey("parties.id"), nullable=False)
    to_party_id = Column(String, ForeignKey("parties.id"), nullable=False)

    # Relationship classification
    type = Column(String, nullable=False)
    # Types: SUPPLIES, SUBCONTRACTS_FOR, OPERATES_AT, OWNS, PARTNERS_WITH,
    #        INSURES, FINANCES, AUDITS, CERTIFIES, etc.

    # Relationship details
    description = Column(Text, nullable=True)
    role = Column(String, nullable=True)  # Specific role in the relationship
    tier = Column(String, nullable=True)  # TIER_1, TIER_2, TIER_3 for supply chain depth

    # Validity & status
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE, INACTIVE, TERMINATED, PENDING
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)

    # Metrics & attributes
    attributes = Column(JSON, nullable=True)
    # Example: {
    #   "volume_share": 0.35,  # 35% of business
    #   "contract_value": 1000000,
    #   "payment_terms": "NET30",
    #   "exclusivity": false
    # }

    # Verification
    verified = Column(String, nullable=True)  # UNVERIFIED, SELF_REPORTED, VERIFIED, DISPUTED
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)

    # Source of relationship information
    source = Column(String, nullable=True)  # MANUAL, CONTRACT, INTEGRATION, PUBLIC_RECORD
    source_document_id = Column(String, nullable=True)  # Reference to supporting document

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<PartyRelationship(id={self.id}, from={self.from_party_id}, to={self.to_party_id}, type={self.type})>"
