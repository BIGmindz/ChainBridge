"""API routes for ESG Evidence management.

Provides CRUD operations for EsgEvidence entities with multi-tenant isolation.
ESG Evidence captures environmental, social, and governance facts tied to parties.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.esg_evidence import EsgEvidence
from api.models.party import Party
from api.schemas.esg_evidence import EsgEvidenceCreate, EsgEvidenceListItem, EsgEvidenceRead, EsgEvidenceUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/esg-evidence", tags=["ESG Evidence"])

# TODO: Replace with actual tenant extraction from auth context
DEFAULT_TENANT_ID = "default-tenant"


def get_tenant_id() -> str:
    """Extract tenant ID from request context."""
    return DEFAULT_TENANT_ID


@router.get("/", response_model=List[EsgEvidenceListItem])
def list_esg_evidence(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    party_id: Optional[str] = Query(None, description="Filter by party"),
    type: Optional[str] = Query(None, description="Filter by evidence type"),
    category: Optional[str] = Query(None, description="Filter by category (ENVIRONMENTAL, SOCIAL, GOVERNANCE)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all ESG evidence for the current tenant."""
    query = db.query(EsgEvidence).filter(EsgEvidence.tenant_id == tenant_id)

    if party_id:
        query = query.filter(EsgEvidence.party_id == party_id)
    if type:
        query = query.filter(EsgEvidence.type == type)
    if category:
        query = query.filter(EsgEvidence.category == category)
    if status:
        query = query.filter(EsgEvidence.status == status)

    evidence = query.order_by(EsgEvidence.created_at.desc()).offset(skip).limit(limit).all()
    return evidence


@router.get("/{evidence_id}", response_model=EsgEvidenceRead)
def get_esg_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific ESG evidence record by ID."""
    evidence = db.query(EsgEvidence).filter(EsgEvidence.id == evidence_id, EsgEvidence.tenant_id == tenant_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="ESG evidence not found")
    return evidence


@router.post("/", response_model=EsgEvidenceRead, status_code=201)
def create_esg_evidence(
    payload: EsgEvidenceCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a new ESG evidence record."""
    # Verify party exists and belongs to tenant
    party = db.query(Party).filter(Party.id == payload.party_id, Party.tenant_id == tenant_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    evidence = EsgEvidence(
        tenant_id=tenant_id,
        party_id=payload.party_id,
        type=payload.type,
        category=payload.category,
        subcategory=payload.subcategory,
        source=payload.source,
        source_type=payload.source_type,
        source_url=payload.source_url,
        document_id=payload.document_id,
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
        score_impact=payload.score_impact,
        confidence=payload.confidence,
        weight=payload.weight,
        title=payload.title,
        notes=payload.notes,
        details=payload.details,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    logger.info(f"Created ESG evidence {evidence.id} of type {evidence.type} " f"for party {evidence.party_id} in tenant {tenant_id}")
    return evidence


@router.patch("/{evidence_id}", response_model=EsgEvidenceRead)
def update_esg_evidence(
    evidence_id: str,
    payload: EsgEvidenceUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Update an existing ESG evidence record."""
    evidence = db.query(EsgEvidence).filter(EsgEvidence.id == evidence_id, EsgEvidence.tenant_id == tenant_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="ESG evidence not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(evidence, field, value)

    db.commit()
    db.refresh(evidence)

    logger.info(f"Updated ESG evidence {evidence.id} for tenant {tenant_id}")
    return evidence


@router.get("/party/{party_id}", response_model=List[EsgEvidenceListItem])
def get_evidence_for_party(
    party_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    active_only: bool = Query(False, description="Only return active evidence"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get all ESG evidence for a specific party."""
    # Verify party exists and belongs to tenant
    party = db.query(Party).filter(Party.id == party_id, Party.tenant_id == tenant_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    query = db.query(EsgEvidence).filter(
        EsgEvidence.tenant_id == tenant_id,
        EsgEvidence.party_id == party_id,
    )

    if active_only:
        query = query.filter(EsgEvidence.status == "ACTIVE")

    evidence = query.order_by(EsgEvidence.issued_at.desc()).offset(skip).limit(limit).all()
    return evidence


@router.delete("/{evidence_id}", status_code=204)
def delete_esg_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete an ESG evidence record (hard delete)."""
    evidence = db.query(EsgEvidence).filter(EsgEvidence.id == evidence_id, EsgEvidence.tenant_id == tenant_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="ESG evidence not found")

    db.delete(evidence)
    db.commit()

    logger.info(f"Deleted ESG evidence {evidence_id} for tenant {tenant_id}")
    return None
