"""API routes for Exception management.

Provides CRUD operations for Exception entities with multi-tenant isolation.
Exceptions are work items for operators in the manage-by-exception workflow.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.exception import Exception as ExceptionModel
from api.schemas.exception import ExceptionCreate, ExceptionListItem, ExceptionRead, ExceptionResolve, ExceptionUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exceptions", tags=["Exceptions"])

# TODO: Replace with actual tenant/user extraction from auth context
DEFAULT_TENANT_ID = "default-tenant"


def get_tenant_id() -> str:
    """Extract tenant ID from request context."""
    return DEFAULT_TENANT_ID


def get_current_user_id() -> Optional[str]:
    """Extract current user ID from request context."""
    return None  # TODO: Implement


@router.get("/", response_model=List[ExceptionListItem])
def list_exceptions(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    type: Optional[str] = Query(None, description="Filter by exception type"),
    shipment_id: Optional[str] = Query(None, description="Filter by shipment"),
    owner_user_id: Optional[str] = Query(None, description="Filter by owner"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all exceptions for the current tenant."""
    query = db.query(ExceptionModel).filter(ExceptionModel.tenant_id == tenant_id)

    if status:
        query = query.filter(ExceptionModel.status == status)
    if severity:
        query = query.filter(ExceptionModel.severity == severity)
    if type:
        query = query.filter(ExceptionModel.type == type)
    if shipment_id:
        query = query.filter(ExceptionModel.shipment_id == shipment_id)
    if owner_user_id:
        query = query.filter(ExceptionModel.owner_user_id == owner_user_id)

    exceptions = query.order_by(ExceptionModel.created_at.desc()).offset(skip).limit(limit).all()
    return exceptions


@router.get("/{exception_id}", response_model=ExceptionRead)
def get_exception(
    exception_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get a specific exception by ID."""
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exception_id, ExceptionModel.tenant_id == tenant_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    return exc


@router.post("/", response_model=ExceptionRead, status_code=201)
def create_exception(
    payload: ExceptionCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a new exception."""
    exc = ExceptionModel(
        tenant_id=tenant_id,
        shipment_id=payload.shipment_id,
        playbook_id=payload.playbook_id,
        payment_intent_id=payload.payment_intent_id,
        type=payload.type,
        severity=payload.severity,
        status=payload.status,
        owner_user_id=payload.owner_user_id,
        escalated_to=payload.escalated_to,
        summary=payload.summary,
        details=payload.details,
        notes=payload.notes,
        source=payload.source,
        source_event_id=payload.source_event_id,
    )
    db.add(exc)
    db.commit()
    db.refresh(exc)

    logger.info(f"Created exception {exc.id} of type {exc.type} for tenant {tenant_id}")
    return exc


@router.patch("/{exception_id}", response_model=ExceptionRead)
def update_exception(
    exception_id: str,
    payload: ExceptionUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Update an existing exception."""
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exception_id, ExceptionModel.tenant_id == tenant_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(exc, field, value)

    db.commit()
    db.refresh(exc)

    logger.info(f"Updated exception {exc.id} for tenant {tenant_id}")
    return exc


@router.post("/{exception_id}/resolve", response_model=ExceptionRead)
def resolve_exception(
    exception_id: str,
    payload: ExceptionResolve,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user_id: Optional[str] = Depends(get_current_user_id),
):
    """Mark an exception as resolved."""
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exception_id, ExceptionModel.tenant_id == tenant_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    if exc.status == "RESOLVED":
        raise HTTPException(status_code=400, detail="Exception is already resolved")

    exc.status = "RESOLVED"
    exc.resolution_type = payload.resolution_type
    exc.resolution_notes = payload.resolution_notes
    exc.resolved_at = datetime.utcnow()
    exc.resolved_by = current_user_id

    db.commit()
    db.refresh(exc)

    logger.info(f"Resolved exception {exc.id} with type {payload.resolution_type}")
    return exc


@router.delete("/{exception_id}", status_code=204)
def delete_exception(
    exception_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete an exception (hard delete)."""
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exception_id, ExceptionModel.tenant_id == tenant_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    db.delete(exc)
    db.commit()

    logger.info(f"Deleted exception {exception_id} for tenant {tenant_id}")
    return None
