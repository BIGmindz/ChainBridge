"""API routes for The OC (Exception Cockpit).

This module provides endpoints specifically designed for the OC frontend,
matching the response shapes expected by exceptionsApi.ts and related hooks.

Endpoints:
- GET /api/v1/oc/exceptions - List exceptions with pagination
- GET /api/v1/oc/exceptions/stats - Exception statistics for KPIs
- GET /api/v1/oc/exceptions/{id} - Full exception detail with playbook & decisions
- PATCH /api/v1/oc/exceptions/{id}/status - Update exception status
- GET /api/v1/oc/decisions - Recent decision records
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.decision_record import DecisionRecord as DecisionRecordModel
from api.models.exception import Exception as ExceptionModel
from api.models.playbook import Playbook as PlaybookModel
from api.schemas.decision_record import DecisionRecordOC, DecisionRecordsListResponse
from api.schemas.exception import (
    DecisionRecordSummary,
    ExceptionDetailResponse,
    ExceptionRead,
    ExceptionsListResponse,
    ExceptionStats,
    PlaybookSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oc", tags=["OC - Exception Cockpit"])

# TODO: Replace with actual tenant/user extraction from auth context
DEFAULT_TENANT_ID = "default-tenant"


def get_tenant_id() -> str:
    """Extract tenant ID from request context."""
    return DEFAULT_TENANT_ID


def get_current_user_id() -> Optional[str]:
    """Extract current user ID from request context."""
    return "operator-default"


def _exception_to_read(exc: ExceptionModel) -> ExceptionRead:
    """Convert an Exception model to the OC-expected ExceptionRead format."""
    return ExceptionRead(
        id=exc.id,
        type=exc.type,
        severity=exc.severity,
        status=exc.status,
        summary=exc.summary,
        description=exc.notes,  # Map notes -> description
        shipment_id=exc.shipment_id,
        shipment_reference=exc.shipment_id,  # TODO: Lookup actual reference
        playbook_id=exc.playbook_id,
        owner_id=exc.owner_user_id,
        owner_name=exc.owner_user_id,  # TODO: Lookup actual name
        created_at=exc.created_at,
        updated_at=exc.updated_at,
        resolved_at=exc.resolved_at,
        metadata=exc.details,
    )


def _decision_to_oc(dec: DecisionRecordModel) -> DecisionRecordOC:
    """Convert a DecisionRecord model to the OC-expected format."""
    # Determine exception_id and shipment_id from entity_type/entity_id
    exception_id = dec.entity_id if dec.entity_type == "EXCEPTION" else None
    shipment_id = dec.entity_id if dec.entity_type == "SHIPMENT" else None

    # Map actor_type: USER -> OPERATOR for frontend compatibility
    actor_type = dec.actor_type
    if actor_type == "USER":
        actor_type = "OPERATOR"

    return DecisionRecordOC(
        id=dec.id,
        type=dec.type,
        actor=dec.actor_name or dec.actor_id,
        actor_type=actor_type,
        policy_id=dec.policy_id,
        policy_name=None,  # TODO: Lookup policy name
        exception_id=exception_id,
        shipment_id=shipment_id,
        summary=dec.explanation or f"Decision: {dec.type}",
        details=dec.outputs,
        created_at=dec.created_at,
    )


def _decision_to_summary(dec: DecisionRecordModel) -> DecisionRecordSummary:
    """Convert a DecisionRecord model to a summary for exception detail."""
    exception_id = dec.entity_id if dec.entity_type == "EXCEPTION" else None
    shipment_id = dec.entity_id if dec.entity_type == "SHIPMENT" else None

    actor_type = dec.actor_type
    if actor_type == "USER":
        actor_type = "OPERATOR"

    return DecisionRecordSummary(
        id=dec.id,
        type=dec.type,
        actor=dec.actor_name or dec.actor_id,
        actor_type=actor_type,
        policy_id=dec.policy_id,
        policy_name=None,
        exception_id=exception_id,
        shipment_id=shipment_id,
        summary=dec.explanation or f"Decision: {dec.type}",
        created_at=dec.created_at,
    )


def _playbook_to_summary(pb: PlaybookModel) -> PlaybookSummary:
    """Convert a Playbook model to a summary for exception detail."""
    # Transform backend steps format to frontend format
    frontend_steps = []
    if pb.steps:
        for step in pb.steps:
            frontend_steps.append(
                {
                    "id": f"s{step.get('order', 0)}",
                    "order": step.get("order", 0),
                    "title": step.get("action", "Step"),
                    "description": step.get("description", ""),
                    "status": "PENDING",  # Default status
                }
            )

    return PlaybookSummary(
        id=pb.id,
        name=pb.name,
        description=pb.description,
        exception_type=pb.category,
        steps=frontend_steps,
        is_active=pb.active,
    )


# =============================================================================
# EXCEPTIONS ENDPOINTS
# =============================================================================


@router.get("/exceptions", response_model=ExceptionsListResponse)
def list_exceptions(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    status: Optional[str] = Query(None, description="Filter by status (OPEN, IN_PROGRESS, RESOLVED, DISMISSED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    List exceptions for the OC with pagination and filtering.

    Returns exceptions sorted by severity (CRITICAL first), then by created_at (newest first).
    """
    query = db.query(ExceptionModel).filter(ExceptionModel.tenant_id == tenant_id)

    if status:
        query = query.filter(ExceptionModel.status == status)
    if severity:
        query = query.filter(ExceptionModel.severity == severity)

    # Get total count
    total = query.count()

    # Sort by severity (CRITICAL > HIGH > MEDIUM > LOW), then by created_at desc
    severity_order = case(
        (ExceptionModel.severity == "CRITICAL", 0),
        (ExceptionModel.severity == "HIGH", 1),
        (ExceptionModel.severity == "MEDIUM", 2),
        (ExceptionModel.severity == "LOW", 3),
        else_=4,
    )

    exceptions = query.order_by(severity_order, ExceptionModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return ExceptionsListResponse(
        exceptions=[_exception_to_read(exc) for exc in exceptions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/exceptions/stats", response_model=ExceptionStats)
def get_exception_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get exception statistics for KPI display.

    Returns counts by severity and status for the tenant.
    """
    # Count open exceptions (not RESOLVED or DISMISSED)
    open_query = db.query(ExceptionModel).filter(
        ExceptionModel.tenant_id == tenant_id, ExceptionModel.status.notin_(["RESOLVED", "DISMISSED", "WONT_FIX"])
    )

    total_open = open_query.count()
    critical_count = open_query.filter(ExceptionModel.severity == "CRITICAL").count()
    high_count = open_query.filter(ExceptionModel.severity == "HIGH").count()
    medium_count = open_query.filter(ExceptionModel.severity == "MEDIUM").count()
    low_count = open_query.filter(ExceptionModel.severity == "LOW").count()

    # Count resolved today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = (
        db.query(ExceptionModel)
        .filter(
            ExceptionModel.tenant_id == tenant_id,
            ExceptionModel.status == "RESOLVED",
            ExceptionModel.resolved_at >= today_start,
        )
        .count()
    )

    # Calculate average resolution time (for exceptions resolved in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    resolved_recently = (
        db.query(ExceptionModel)
        .filter(
            ExceptionModel.tenant_id == tenant_id,
            ExceptionModel.status == "RESOLVED",
            ExceptionModel.resolved_at >= thirty_days_ago,
            ExceptionModel.resolved_at.isnot(None),
        )
        .all()
    )

    avg_resolution_hours = None
    if resolved_recently:
        total_hours = 0.0
        count = 0
        for exc in resolved_recently:
            if exc.resolved_at and exc.created_at:
                delta = exc.resolved_at - exc.created_at
                total_hours += delta.total_seconds() / 3600
                count += 1
        if count > 0:
            avg_resolution_hours = round(total_hours / count, 1)

    return ExceptionStats(
        total_open=total_open,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        resolved_today=resolved_today,
        avg_resolution_time_hours=avg_resolution_hours,
    )


@router.get("/exceptions/{exception_id}", response_model=ExceptionDetailResponse)
def get_exception_detail(
    exception_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get full exception detail with related playbook and recent decisions.

    Returns the exception, its associated playbook (if any), and recent
    decision records related to the exception or its shipment.
    """
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exception_id, ExceptionModel.tenant_id == tenant_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    # Get associated playbook
    playbook = None
    if exc.playbook_id:
        pb = db.query(PlaybookModel).filter(PlaybookModel.id == exc.playbook_id).first()
        if pb:
            playbook = _playbook_to_summary(pb)

    # Get recent decisions related to this exception or its shipment
    decisions_query = (
        db.query(DecisionRecordModel)
        .filter(
            DecisionRecordModel.tenant_id == tenant_id,
            or_(
                (DecisionRecordModel.entity_type == "EXCEPTION") & (DecisionRecordModel.entity_id == exception_id),
                (
                    (DecisionRecordModel.entity_type == "SHIPMENT") & (DecisionRecordModel.entity_id == exc.shipment_id)
                    if exc.shipment_id
                    else False
                ),
            ),
        )
        .order_by(DecisionRecordModel.created_at.desc())
        .limit(10)
    )

    recent_decisions = [_decision_to_summary(d) for d in decisions_query.all()]

    return ExceptionDetailResponse(
        exception=_exception_to_read(exc),
        playbook=playbook,
        recent_decisions=recent_decisions,
    )


@router.patch("/exceptions/{exception_id}/status")
def update_exception_status(
    exception_id: str,
    status: str = Query(..., description="New status (OPEN, IN_PROGRESS, RESOLVED, DISMISSED)"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Update an exception's status and log a decision record.

    Creates an audit trail by recording a STATUS_CHANGE decision.
    """
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exception_id, ExceptionModel.tenant_id == tenant_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    old_status = exc.status
    valid_statuses = ["OPEN", "IN_PROGRESS", "RESOLVED", "DISMISSED", "ESCALATED", "WONT_FIX"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    # Update exception
    exc.status = status
    if status == "RESOLVED":
        exc.resolved_at = datetime.utcnow()
        exc.resolved_by = current_user_id

    # Log decision record for audit trail
    decision = DecisionRecordModel(
        tenant_id=tenant_id,
        type="STATUS_CHANGE",
        subtype=f"{old_status}_TO_{status}",
        actor_type="USER",
        actor_id=current_user_id,
        actor_name=current_user_id,  # TODO: Lookup actual name
        entity_type="EXCEPTION",
        entity_id=exception_id,
        outputs={
            "old_status": old_status,
            "new_status": status,
            "exception_id": exception_id,
        },
        explanation=f"Exception status changed from {old_status} to {status}",
    )
    db.add(decision)

    db.commit()
    db.refresh(exc)

    logger.info(f"Updated exception {exception_id} status from {old_status} to {status}")
    return _exception_to_read(exc)


# =============================================================================
# DECISION RECORDS ENDPOINTS
# =============================================================================


@router.get("/decisions", response_model=DecisionRecordsListResponse)
def list_decisions(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    shipment_id: Optional[str] = Query(None, description="Filter by shipment ID"),
    exception_id: Optional[str] = Query(None, description="Filter by exception ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum records to return"),
    page: int = Query(1, ge=1, description="Page number"),
):
    """
    List recent decision records for the OC.

    Can filter by shipment_id or exception_id to show relevant decisions.
    """
    query = db.query(DecisionRecordModel).filter(DecisionRecordModel.tenant_id == tenant_id)

    if shipment_id:
        query = query.filter(
            DecisionRecordModel.entity_type == "SHIPMENT",
            DecisionRecordModel.entity_id == shipment_id,
        )
    if exception_id:
        query = query.filter(
            DecisionRecordModel.entity_type == "EXCEPTION",
            DecisionRecordModel.entity_id == exception_id,
        )

    total = query.count()

    records = query.order_by(DecisionRecordModel.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return DecisionRecordsListResponse(
        records=[_decision_to_oc(d) for d in records],
        total=total,
        page=page,
        page_size=limit,
    )
