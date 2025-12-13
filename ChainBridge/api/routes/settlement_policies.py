"""API routes for Settlement Policy management.

Provides CRUD operations for SettlementPolicy entities with multi-tenant isolation.
Settlement policies govern how money moves across milestones in ChainPay.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.settlement_policy import SettlementPolicy
from api.schemas.settlement_policy import SettlementPolicyCreate, SettlementPolicyListItem, SettlementPolicyRead, SettlementPolicyUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settlement-policies", tags=["Settlement Policies"])

# TODO: Replace with actual tenant extraction from auth context
DEFAULT_TENANT_ID = "default-tenant"


def get_tenant_id() -> str:
    """Extract tenant ID from request context."""
    return DEFAULT_TENANT_ID


@router.get("/", response_model=List[SettlementPolicyListItem])
def list_settlement_policies(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    policy_type: Optional[str] = Query(None, description="Filter by policy type"),
    effective_only: bool = Query(False, description="Only return currently effective policies"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all settlement policies for the current tenant."""
    query = db.query(SettlementPolicy).filter(SettlementPolicy.tenant_id == tenant_id)

    if currency:
        query = query.filter(SettlementPolicy.currency == currency)
    if policy_type:
        query = query.filter(SettlementPolicy.policy_type == policy_type)
    if effective_only:
        now = datetime.utcnow()
        query = query.filter(
            SettlementPolicy.effective_from <= now,
            (SettlementPolicy.effective_to.is_(None)) | (SettlementPolicy.effective_to >= now),
        )

    policies = query.order_by(SettlementPolicy.created_at.desc()).offset(skip).limit(limit).all()
    return policies


@router.get("/{policy_id}", response_model=SettlementPolicyRead)
def get_settlement_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific settlement policy by ID."""
    policy = db.query(SettlementPolicy).filter(SettlementPolicy.id == policy_id, SettlementPolicy.tenant_id == tenant_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Settlement policy not found")
    return policy


@router.post("/", response_model=SettlementPolicyRead, status_code=201)
def create_settlement_policy(
    payload: SettlementPolicyCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a new settlement policy."""
    # Convert curve milestones to dict format
    curve_data = [m.model_dump() for m in payload.curve] if payload.curve else []

    policy = SettlementPolicy(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        policy_type=payload.policy_type,
        curve=curve_data,
        conditions=payload.conditions,
        max_exposure=payload.max_exposure,
        min_transaction=payload.min_transaction,
        max_transaction=payload.max_transaction,
        currency=payload.currency,
        rails=payload.rails,
        preferred_rail=payload.preferred_rail,
        fallback_rails=payload.fallback_rails,
        settlement_delay_hours=payload.settlement_delay_hours,
        float_reduction_target=payload.float_reduction_target,
        effective_from=payload.effective_from or datetime.utcnow(),
        effective_to=payload.effective_to,
        version=payload.version,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    logger.info(f"Created settlement policy {policy.id} '{policy.name}' for tenant {tenant_id}")
    return policy


@router.patch("/{policy_id}", response_model=SettlementPolicyRead)
def update_settlement_policy(
    policy_id: str,
    payload: SettlementPolicyUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Update an existing settlement policy."""
    policy = db.query(SettlementPolicy).filter(SettlementPolicy.id == policy_id, SettlementPolicy.tenant_id == tenant_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Settlement policy not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Handle curve conversion
    if "curve" in update_data and update_data["curve"] is not None:
        update_data["curve"] = [m.model_dump() for m in payload.curve]

    for field, value in update_data.items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)

    logger.info(f"Updated settlement policy {policy.id} for tenant {tenant_id}")
    return policy


@router.post("/{policy_id}/approve", response_model=SettlementPolicyRead)
def approve_settlement_policy(
    policy_id: str,
    approver_id: str = Query(..., description="ID of the approving user"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Approve a settlement policy."""
    policy = db.query(SettlementPolicy).filter(SettlementPolicy.id == policy_id, SettlementPolicy.tenant_id == tenant_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Settlement policy not found")

    policy.approved_by = approver_id
    policy.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(policy)

    logger.info(f"Approved settlement policy {policy.id} by {approver_id}")
    return policy


@router.delete("/{policy_id}", status_code=204)
def delete_settlement_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a settlement policy (hard delete)."""
    policy = db.query(SettlementPolicy).filter(SettlementPolicy.id == policy_id, SettlementPolicy.tenant_id == tenant_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Settlement policy not found")

    db.delete(policy)
    db.commit()

    logger.info(f"Deleted settlement policy {policy_id} for tenant {tenant_id}")
    return None
