# CODEX SYSTEM BRIEFING - CHAINBRIDGE SETTLEMENT ACTION LOGGING V1.0
# You are upgrading stub action endpoints into a simple, persistent audit log.
#
# Constraints:
# - Still NO changes to ChainPay core business logic.
# - All new behavior is append-only logging, safe to run in dev/prod.
#
# Objectives:
# 1) Persist operator actions (escalate, mark-reviewed, request-docs) into a dedicated table.
# 2) Expose a read-only API to fetch recent actions for UI display.
# 3) Cover everything with tests.

"""
Settlement Operator Action Endpoints
=====================================

Stub endpoints for operator actions on payment milestones.
These are UI-only for now - no business logic side effects.

TODO: Wire these into ChainPay/ChainIQ for real settlement actions.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.storage.settlement_actions import (
    list_recent_actions,
    log_action,
)
from core.payments.identity import is_valid_milestone_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class SettlementActionRequest(BaseModel):
    """
    Request body for settlement operator actions.
    """

    reason: Optional[str] = Field(None, description="Reason for the action")
    requested_by: Optional[str] = Field(None, description="Operator who requested the action")


class SettlementActionResponse(BaseModel):
    """
    Response for settlement operator actions.
    """

    status: str = Field(..., description="Action status (accepted/rejected)")
    milestone_id: str = Field(..., description="The milestone ID acted upon")
    action: str = Field(..., description="The action type performed")
    note: str = Field(..., description="Additional context for the operator")
    requested_by: Optional[str] = Field(None, description="Operator who requested the action")
    created_at: datetime = Field(..., description="Timestamp when the action was logged")


class LoggedSettlementAction(BaseModel):
    """Response item for the recent actions feed."""

    milestone_id: str
    action: str
    reason: Optional[str] = None
    requested_by: Optional[str] = None
    created_at: datetime


# ============================================================================
# Helper Functions
# ============================================================================


def validate_milestone_id(milestone_id: str) -> None:
    """
    Validate milestone ID format.

    Expected format: SHP-YYYY-NNN-N or similar shipment-milestone pattern.
    """
    if not milestone_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="milestone_id is required")

    if not is_valid_milestone_id(milestone_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid milestone_id format: {milestone_id}",
        )


# ============================================================================
# Settlement Action Endpoints (Stubs)
# ============================================================================


@router.post(
    "/settlements/{milestone_id}/actions/escalate",
    response_model=SettlementActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def escalate_to_risk(
    milestone_id: str,
    request: SettlementActionRequest,
):
    """
    Escalate a payment milestone to Risk team.

    **STUB ENDPOINT**: No business logic side-effects. Logs action only.

    TODO: Wire this into ChainPay/ChainIQ for real escalation workflow.
    """
    validate_milestone_id(milestone_id)

    record = log_action(
        milestone_id=milestone_id,
        action="escalate_to_risk",
        reason=request.reason,
        requested_by=request.requested_by,
    )

    return SettlementActionResponse(
        status="accepted",
        milestone_id=milestone_id,
        action="escalate_to_risk",
        note="action logged",
        requested_by=request.requested_by,
        created_at=record.created_at,
    )


@router.post(
    "/settlements/{milestone_id}/actions/mark-reviewed",
    response_model=SettlementActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def mark_manually_reviewed(
    milestone_id: str,
    request: SettlementActionRequest,
):
    """
    Mark a payment milestone as manually reviewed by an operator.

    **STUB ENDPOINT**: No business logic side-effects. Logs action only.

    TODO: Wire this into ChainPay/ChainIQ to update milestone state.
    """
    validate_milestone_id(milestone_id)

    record = log_action(
        milestone_id=milestone_id,
        action="mark_manually_reviewed",
        reason=request.reason,
        requested_by=request.requested_by,
    )

    return SettlementActionResponse(
        status="accepted",
        milestone_id=milestone_id,
        action="mark_manually_reviewed",
        note="action logged",
        requested_by=request.requested_by,
        created_at=record.created_at,
    )


@router.post(
    "/settlements/{milestone_id}/actions/request-docs",
    response_model=SettlementActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_documentation(
    milestone_id: str,
    request: SettlementActionRequest,
):
    """
    Request additional documentation for a payment milestone.

    **STUB ENDPOINT**: No business logic side-effects. Logs action only.

    TODO: Wire this into ChainPay/ChainIQ to trigger document request workflow.
    """
    validate_milestone_id(milestone_id)

    record = log_action(
        milestone_id=milestone_id,
        action="request_documentation",
        reason=request.reason,
        requested_by=request.requested_by,
    )

    return SettlementActionResponse(
        status="accepted",
        milestone_id=milestone_id,
        action="request_documentation",
        note="action logged",
        requested_by=request.requested_by,
        created_at=record.created_at,
    )


@router.get(
    "/settlements/actions/recent",
    response_model=List[LoggedSettlementAction],
    status_code=status.HTTP_200_OK,
)
async def list_recent_settlement_actions(limit: int = Query(20, ge=1)):
    """Return recent settlement actions for UI consumption."""
    sanitized_limit = min(max(limit, 1), 100)
    records = list_recent_actions(sanitized_limit)
    return [
        LoggedSettlementAction(
            milestone_id=record.milestone_id,
            action=record.action,
            reason=record.reason,
            requested_by=record.requested_by,
            created_at=record.created_at,
        )
        for record in records
    ]
