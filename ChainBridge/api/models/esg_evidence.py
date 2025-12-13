"""SQLAlchemy models for ESG Evidence in ChainBridge.

ESG Evidence captures environmental, social, and governance facts tied to
parties in the logistics network - certifications, audits, reports, and scores.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, String, Text

from api.database import Base


class EsgEvidence(Base):
    """Represents ESG/ethics/compliance evidence tied to a Party.

    ESG Evidence can be certifications, audit results, NGO reports,
    self-attestations, or whistleblower reports that affect a party's
    ESG score and risk profile.
    """

    __tablename__ = "esg_evidence"
    __table_args__ = (
        Index("ix_esg_evidence_tenant_id", "tenant_id"),
        Index("ix_esg_evidence_party_id", "party_id"),
        Index("ix_esg_evidence_type", "type"),
        Index("ix_esg_evidence_tenant_party", "tenant_id", "party_id"),
        Index("ix_esg_evidence_expires", "expires_at"),
    )

    id = Column(String, primary_key=True, default=lambda: f"ESG-{uuid4()}")
    tenant_id = Column(String, nullable=False)

    # Linked party
    party_id = Column(String, ForeignKey("parties.id"), nullable=False)

    # Evidence classification
    type = Column(String, nullable=False)
    # Types: AUDIT, CERTIFICATION, NGO_REPORT, SELF_ATTESTATION, WHISTLEBLOWER,
    #        GOVERNMENT_SANCTION, MEDIA_REPORT, CUSTOMER_COMPLAINT, etc.
    category = Column(String, nullable=True)  # ENVIRONMENTAL, SOCIAL, GOVERNANCE
    subcategory = Column(String, nullable=True)  # CARBON_FOOTPRINT, LABOR_RIGHTS, CORRUPTION, etc.

    # Source information
    source = Column(String, nullable=False)  # Who provided/issued this evidence
    source_type = Column(String, nullable=True)  # CERTIFIER, NGO, GOVERNMENT, INTERNAL, MEDIA, etc.
    source_url = Column(String, nullable=True)  # Link to external source if applicable
    document_id = Column(String, nullable=True)  # Reference to attached document in ChainDocs

    # Validity period
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Null = no expiration
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)

    # Scoring impact
    score_impact = Column(Float, nullable=True)
    # Positive = improves ESG score, Negative = worsens score
    # Example: ISO 14001 cert = +15, labor violation = -30

    confidence = Column(Float, nullable=True)  # 0.0 to 1.0, how confident we are in this evidence
    weight = Column(Float, nullable=True)  # Weighting factor for score calculations

    # Content
    title = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)  # Structured details about the evidence

    # Status
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE, EXPIRED, DISPUTED, REVOKED

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<EsgEvidence(id={self.id}, party_id={self.party_id}, type={self.type})>"
