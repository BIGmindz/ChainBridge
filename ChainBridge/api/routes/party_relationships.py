"""API routes for Party Relationship management.

Provides CRUD operations for PartyRelationship entities with multi-tenant isolation.
Party relationships model the multi-tier graph of business relationships.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.party import Party
from api.models.party_relationship import PartyRelationship
from api.schemas.party_relationship import (
    PartyRelationshipCreate,
    PartyRelationshipListItem,
    PartyRelationshipRead,
    PartyRelationshipUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/party-relationships", tags=["Party Relationships"])

# TODO: Replace with actual tenant extraction from auth context
DEFAULT_TENANT_ID = "default-tenant"


def get_tenant_id() -> str:
    """Extract tenant ID from request context."""
    return DEFAULT_TENANT_ID


@router.get("/", response_model=List[PartyRelationshipListItem])
def list_party_relationships(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    type: Optional[str] = Query(None, description="Filter by relationship type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    from_party_id: Optional[str] = Query(None, description="Filter by source party"),
    to_party_id: Optional[str] = Query(None, description="Filter by target party"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all party relationships for the current tenant."""
    query = db.query(PartyRelationship).filter(PartyRelationship.tenant_id == tenant_id)

    if type:
        query = query.filter(PartyRelationship.type == type)
    if status:
        query = query.filter(PartyRelationship.status == status)
    if from_party_id:
        query = query.filter(PartyRelationship.from_party_id == from_party_id)
    if to_party_id:
        query = query.filter(PartyRelationship.to_party_id == to_party_id)
    if tier:
        query = query.filter(PartyRelationship.tier == tier)

    relationships = query.order_by(PartyRelationship.created_at.desc()).offset(skip).limit(limit).all()
    return relationships


@router.get("/{relationship_id}", response_model=PartyRelationshipRead)
def get_party_relationship(
    relationship_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific party relationship by ID."""
    relationship = (
        db.query(PartyRelationship)
        .filter(
            PartyRelationship.id == relationship_id,
            PartyRelationship.tenant_id == tenant_id,
        )
        .first()
    )
    if not relationship:
        raise HTTPException(status_code=404, detail="Party relationship not found")
    return relationship


@router.post("/", response_model=PartyRelationshipRead, status_code=201)
def create_party_relationship(
    payload: PartyRelationshipCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a new party relationship."""
    # Verify both parties exist and belong to tenant
    from_party = db.query(Party).filter(Party.id == payload.from_party_id, Party.tenant_id == tenant_id).first()
    if not from_party:
        raise HTTPException(status_code=404, detail="Source party not found")

    to_party = db.query(Party).filter(Party.id == payload.to_party_id, Party.tenant_id == tenant_id).first()
    if not to_party:
        raise HTTPException(status_code=404, detail="Target party not found")

    relationship = PartyRelationship(
        tenant_id=tenant_id,
        from_party_id=payload.from_party_id,
        to_party_id=payload.to_party_id,
        type=payload.type,
        description=payload.description,
        role=payload.role,
        tier=payload.tier,
        status=payload.status,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        attributes=payload.attributes,
        verified=payload.verified,
        source=payload.source,
        source_document_id=payload.source_document_id,
    )
    db.add(relationship)
    db.commit()
    db.refresh(relationship)

    logger.info(
        f"Created party relationship {relationship.id} of type {relationship.type} "
        f"from {relationship.from_party_id} to {relationship.to_party_id}"
    )
    return relationship


@router.patch("/{relationship_id}", response_model=PartyRelationshipRead)
def update_party_relationship(
    relationship_id: str,
    payload: PartyRelationshipUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Update an existing party relationship."""
    relationship = (
        db.query(PartyRelationship)
        .filter(
            PartyRelationship.id == relationship_id,
            PartyRelationship.tenant_id == tenant_id,
        )
        .first()
    )
    if not relationship:
        raise HTTPException(status_code=404, detail="Party relationship not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(relationship, field, value)

    db.commit()
    db.refresh(relationship)

    logger.info(f"Updated party relationship {relationship.id} for tenant {tenant_id}")
    return relationship


@router.get("/party/{party_id}/outgoing", response_model=List[PartyRelationshipListItem])
def get_outgoing_relationships(
    party_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    type: Optional[str] = Query(None, description="Filter by relationship type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get all outgoing relationships from a party."""
    # Verify party exists and belongs to tenant
    party = db.query(Party).filter(Party.id == party_id, Party.tenant_id == tenant_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    query = db.query(PartyRelationship).filter(
        PartyRelationship.tenant_id == tenant_id,
        PartyRelationship.from_party_id == party_id,
    )

    if type:
        query = query.filter(PartyRelationship.type == type)

    relationships = query.order_by(PartyRelationship.created_at.desc()).offset(skip).limit(limit).all()
    return relationships


@router.get("/party/{party_id}/incoming", response_model=List[PartyRelationshipListItem])
def get_incoming_relationships(
    party_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    type: Optional[str] = Query(None, description="Filter by relationship type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get all incoming relationships to a party."""
    # Verify party exists and belongs to tenant
    party = db.query(Party).filter(Party.id == party_id, Party.tenant_id == tenant_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    query = db.query(PartyRelationship).filter(
        PartyRelationship.tenant_id == tenant_id,
        PartyRelationship.to_party_id == party_id,
    )

    if type:
        query = query.filter(PartyRelationship.type == type)

    relationships = query.order_by(PartyRelationship.created_at.desc()).offset(skip).limit(limit).all()
    return relationships


@router.delete("/{relationship_id}", status_code=204)
def delete_party_relationship(
    relationship_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a party relationship (hard delete)."""
    relationship = (
        db.query(PartyRelationship)
        .filter(
            PartyRelationship.id == relationship_id,
            PartyRelationship.tenant_id == tenant_id,
        )
        .first()
    )
    if not relationship:
        raise HTTPException(status_code=404, detail="Party relationship not found")

    db.delete(relationship)
    db.commit()

    logger.info(f"Deleted party relationship {relationship_id} for tenant {tenant_id}")
    return None
