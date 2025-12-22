"""API routes for Decision Record management.

Provides CRUD operations for DecisionRecord entities with multi-tenant isolation.
Decision records are immutable audit trails of risk and settlement decisions.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.decision_record import DecisionRecord
from api.schemas.decision_record import DecisionRecordCreate, DecisionRecordListItem, DecisionRecordRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/decision-records", tags=["Decision Records"])

# TODO: Replace with actual tenant extraction from auth context
DEFAULT_TENANT_ID = "default-tenant"


def get_tenant_id() -> str:
    """Extract tenant ID from request context."""
    return DEFAULT_TENANT_ID


@router.get("/", response_model=List[DecisionRecordListItem])
def list_decision_records(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    type: Optional[str] = Query(None, description="Filter by decision type"),
    actor_type: Optional[str] = Query(None, description="Filter by actor type"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all decision records for the current tenant."""
    query = db.query(DecisionRecord).filter(DecisionRecord.tenant_id == tenant_id)

    if type:
        query = query.filter(DecisionRecord.type == type)
    if actor_type:
        query = query.filter(DecisionRecord.actor_type == actor_type)
    if actor_id:
        query = query.filter(DecisionRecord.actor_id == actor_id)
    if entity_type:
        query = query.filter(DecisionRecord.entity_type == entity_type)
    if entity_id:
        query = query.filter(DecisionRecord.entity_id == entity_id)

    records = query.order_by(DecisionRecord.created_at.desc()).offset(skip).limit(limit).all()
    return records


@router.get("/{record_id}", response_model=DecisionRecordRead)
def get_decision_record(
    record_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific decision record by ID."""
    record = db.query(DecisionRecord).filter(DecisionRecord.id == record_id, DecisionRecord.tenant_id == tenant_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Decision record not found")
    return record


@router.post("/", response_model=DecisionRecordRead, status_code=201)
def create_decision_record(
    payload: DecisionRecordCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a new decision record.

    Decision records are immutable - once created, they cannot be modified.
    """
    record = DecisionRecord(
        tenant_id=tenant_id,
        type=payload.type,
        subtype=payload.subtype,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        actor_name=payload.actor_name,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        policy_id=payload.policy_id,
        policy_type=payload.policy_type,
        policy_version=payload.policy_version,
        inputs_hash=payload.inputs_hash,
        inputs_snapshot=payload.inputs_snapshot,
        outputs=payload.outputs,
        explanation=payload.explanation,
        primary_factors=payload.primary_factors,
        overrides_decision_id=payload.overrides_decision_id,
        override_reason=payload.override_reason,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        f"Created decision record {record.id} of type {record.type} " f"by {record.actor_type}:{record.actor_id} for tenant {tenant_id}"
    )
    return record


@router.get("/entity/{entity_type}/{entity_id}", response_model=List[DecisionRecordListItem])
def get_decisions_for_entity(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get all decision records for a specific entity."""
    records = (
        db.query(DecisionRecord)
        .filter(
            DecisionRecord.tenant_id == tenant_id,
            DecisionRecord.entity_type == entity_type,
            DecisionRecord.entity_id == entity_id,
        )
        .order_by(DecisionRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return records


# Note: Decision records are immutable - no update or delete endpoints
# If a decision needs to be overridden, create a new record with overrides_decision_id set
