"""API routes for Playbook management.

Provides CRUD operations for Playbook entities with multi-tenant isolation.
Playbooks encode remediation flows for exception handling.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.playbook import Playbook
from api.schemas.playbook import PlaybookCreate, PlaybookListItem, PlaybookRead, PlaybookUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playbooks", tags=["Playbooks"])

# TODO: Replace with actual tenant extraction from auth context
DEFAULT_TENANT_ID = "default-tenant"


def get_tenant_id() -> str:
    """Extract tenant ID from request context."""
    return DEFAULT_TENANT_ID


@router.get("/", response_model=List[PlaybookListItem])
def list_playbooks(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all playbooks for the current tenant."""
    query = db.query(Playbook).filter(Playbook.tenant_id == tenant_id)

    if active is not None:
        query = query.filter(Playbook.active == active)
    if category:
        query = query.filter(Playbook.category == category)

    playbooks = query.order_by(Playbook.created_at.desc()).offset(skip).limit(limit).all()
    return playbooks


@router.get("/{playbook_id}", response_model=PlaybookRead)
def get_playbook(
    playbook_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific playbook by ID."""
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.tenant_id == tenant_id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return playbook


@router.post("/", response_model=PlaybookRead, status_code=201)
def create_playbook(
    payload: PlaybookCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a new playbook."""
    # Convert steps to dict format for JSON storage
    steps_data = [step.model_dump() for step in payload.steps] if payload.steps else []

    playbook = Playbook(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        trigger_condition=payload.trigger_condition,
        steps=steps_data,
        version=1,
        active=payload.active,
        author_user_id=payload.author_user_id,
        tags=payload.tags,
        estimated_duration_minutes=payload.estimated_duration_minutes,
    )
    db.add(playbook)
    db.commit()
    db.refresh(playbook)

    logger.info(f"Created playbook {playbook.id} '{playbook.name}' for tenant {tenant_id}")
    return playbook


@router.patch("/{playbook_id}", response_model=PlaybookRead)
def update_playbook(
    playbook_id: str,
    payload: PlaybookUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Update an existing playbook."""
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.tenant_id == tenant_id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Handle steps conversion
    if "steps" in update_data and update_data["steps"] is not None:
        update_data["steps"] = [step.model_dump() for step in payload.steps]

    for field, value in update_data.items():
        setattr(playbook, field, value)

    db.commit()
    db.refresh(playbook)

    logger.info(f"Updated playbook {playbook.id} for tenant {tenant_id}")
    return playbook


@router.post("/{playbook_id}/new-version", response_model=PlaybookRead, status_code=201)
def create_playbook_version(
    playbook_id: str,
    payload: PlaybookUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a new version of an existing playbook."""
    old_playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.tenant_id == tenant_id).first()
    if not old_playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    # Convert steps if provided
    steps_data = old_playbook.steps
    if payload.steps is not None:
        steps_data = [step.model_dump() for step in payload.steps]

    # Create new version
    new_playbook = Playbook(
        tenant_id=tenant_id,
        name=payload.name or old_playbook.name,
        description=payload.description if payload.description is not None else old_playbook.description,
        category=payload.category if payload.category is not None else old_playbook.category,
        trigger_condition=payload.trigger_condition if payload.trigger_condition is not None else old_playbook.trigger_condition,
        steps=steps_data,
        version=old_playbook.version + 1,
        active=payload.active if payload.active is not None else True,
        supersedes_id=old_playbook.id,
        author_user_id=old_playbook.author_user_id,
        tags=payload.tags if payload.tags is not None else old_playbook.tags,
        estimated_duration_minutes=(
            payload.estimated_duration_minutes
            if payload.estimated_duration_minutes is not None
            else old_playbook.estimated_duration_minutes
        ),
    )

    # Deactivate old version
    old_playbook.active = False

    db.add(new_playbook)
    db.commit()
    db.refresh(new_playbook)

    logger.info(f"Created playbook version {new_playbook.version} from {playbook_id}")
    return new_playbook


@router.delete("/{playbook_id}", status_code=204)
def delete_playbook(
    playbook_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a playbook (hard delete)."""
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.tenant_id == tenant_id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    db.delete(playbook)
    db.commit()

    logger.info(f"Deleted playbook {playbook_id} for tenant {tenant_id}")
    return None
