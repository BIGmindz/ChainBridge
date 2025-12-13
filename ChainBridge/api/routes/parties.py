"""API routes for Party management.

Provides CRUD operations for Party entities with multi-tenant isolation.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.party import Party
from api.schemas.party import PartyCreate, PartyListItem, PartyRead, PartyUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parties", tags=["Parties"])

# TODO: Replace with actual tenant extraction from auth context
# For now, use a header-based approach for testing
DEFAULT_TENANT_ID = "default-tenant"


def get_tenant_id() -> str:
    """Extract tenant ID from request context.

    TODO: Implement proper tenant extraction from JWT/auth context.
    """
    return DEFAULT_TENANT_ID


@router.get("/", response_model=List[PartyListItem])
def list_parties(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    type: Optional[str] = Query(None, description="Filter by party type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all parties for the current tenant."""
    query = db.query(Party).filter(Party.tenant_id == tenant_id)

    if type:
        query = query.filter(Party.type == type)
    if status:
        query = query.filter(Party.status == status)

    parties = query.order_by(Party.created_at.desc()).offset(skip).limit(limit).all()
    return parties


@router.get("/{party_id}", response_model=PartyRead)
def get_party(
    party_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific party by ID."""
    party = db.query(Party).filter(Party.id == party_id, Party.tenant_id == tenant_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    return party


@router.post("/", response_model=PartyRead, status_code=201)
def create_party(
    payload: PartyCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a new party."""
    party = Party(
        tenant_id=tenant_id,
        name=payload.name,
        type=payload.type,
        legal_name=payload.legal_name,
        tax_id=payload.tax_id,
        duns_number=payload.duns_number,
        country_code=payload.country_code,
        address=payload.address,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        status=payload.status,
    )
    db.add(party)
    db.commit()
    db.refresh(party)

    logger.info(f"Created party {party.id} for tenant {tenant_id}")
    return party


@router.patch("/{party_id}", response_model=PartyRead)
def update_party(
    party_id: str,
    payload: PartyUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Update an existing party."""
    party = db.query(Party).filter(Party.id == party_id, Party.tenant_id == tenant_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(party, field, value)

    db.commit()
    db.refresh(party)

    logger.info(f"Updated party {party.id} for tenant {tenant_id}")
    return party


@router.delete("/{party_id}", status_code=204)
def delete_party(
    party_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a party (hard delete)."""
    party = db.query(Party).filter(Party.id == party_id, Party.tenant_id == tenant_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    db.delete(party)
    db.commit()

    logger.info(f"Deleted party {party_id} for tenant {tenant_id}")
    return None
