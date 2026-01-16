"""
OCC Governance API Routes

Exposes governance state, enforcement, and approval gates via REST API.
All endpoints bind to the DOCTRINE_FULL_SWARM_EXECUTION doctrine.

DOCTRINE REFERENCE: DOCTRINE-FULL-SWARM-EXECUTION-001
PAC REFERENCE: PAC-JEFFREY-OCC-GOVERNANCE-INTEGRATION-01

Authors:
- CODY (GID-01) - Backend OCC Integration
- SONNY (GID-02) - OCC UI Enforcement
- DAN (GID-07) - OCC CI / Runtime Hooks

INVARIANTS:
- INV-OCC-001: Control > Autonomy
- INV-OCC-002: Proof > Execution
- INV-OCC-003: Human authority final

CONSTRAINTS:
- CONS-OCC-001: No OCC action without proof display
- CONS-OCC-002: No override without Architect authority
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

# Import governance enforcement
import sys
from pathlib import Path

# Add parent paths for import resolution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.orchestration.governance import (  # type: ignore[import-not-found]
    get_enforcer,
    get_gate,
    GovernanceContext,
    GovernanceTier
)


# Create router
router = APIRouter(prefix="/governance", tags=["governance"])


# Request/Response Models
class GovernanceStateResponse(BaseModel):
    """Response model for governance state."""
    doctrine_id: str
    doctrine_locked: bool
    principles: List[str]
    invariants: List[str]
    constraints: List[str]
    enforcement_mode: str
    audit_entries: int
    last_check: str


class ActionRequest(BaseModel):
    """Request model for governance-controlled action."""
    operator_gid: str = Field(..., description="GID of the requesting operator")
    action_type: str = Field(..., description="Type of action being requested")
    target_resource: str = Field(..., description="Resource being acted upon")
    proof_hash: Optional[str] = Field(None, description="SHA-256 hash of proof artifact")
    tier: str = Field("PROCEDURE_TIER", description="Governance tier: LAW_TIER, POLICY_TIER, PROCEDURE_TIER")


class ApprovalRequest(BaseModel):
    """Request model for action approval."""
    request_id: str = Field(..., description="ID of pending request")
    authority_gid: str = Field(..., description="GID of approving authority")


class RejectionRequest(BaseModel):
    """Request model for action rejection."""
    request_id: str = Field(..., description="ID of pending request")
    authority_gid: str = Field(..., description="GID of rejecting authority")
    reason: str = Field(..., description="Reason for rejection")


class EnforcementResponse(BaseModel):
    """Response model for enforcement result."""
    allowed: bool
    status: str
    reason: str
    proof_required: bool = False
    authority_required: bool = False
    request_id: Optional[str] = None
    audit_hash: Optional[str] = None


class PendingApprovalResponse(BaseModel):
    """Response model for pending approval."""
    request_id: str
    operator_gid: str
    action_type: str
    target_resource: str
    requested_at: str


# API Endpoints

@router.get("/state", response_model=GovernanceStateResponse)
async def get_governance_state():
    """
    Get current governance state.
    
    Returns the current doctrine enforcement state including:
    - Doctrine lock status
    - Active principles and invariants
    - Enforcement mode
    - Audit entry count
    
    CONS-OCC-001: This endpoint displays proof state to operators.
    """
    enforcer = get_enforcer()
    state = enforcer.get_governance_state()
    return GovernanceStateResponse(**state)


@router.post("/enforce", response_model=EnforcementResponse)
async def enforce_action(request: ActionRequest):
    """
    Request an action through governance enforcement.
    
    All operator actions MUST pass through this endpoint.
    Actions are validated against:
    - Doctrine lock state
    - GID validity
    - Proof requirements
    - Authority requirements
    
    INV-OCC-001: Control > Autonomy
    INV-OCC-002: Proof > Execution
    """
    gate = get_gate()
    
    # Map tier string to enum
    tier_map = {
        "LAW_TIER": GovernanceTier.LAW,
        "POLICY_TIER": GovernanceTier.POLICY,
        "PROCEDURE_TIER": GovernanceTier.PROCEDURE
    }
    tier = tier_map.get(request.tier, GovernanceTier.PROCEDURE)
    
    context = GovernanceContext(
        operator_gid=request.operator_gid,
        action_type=request.action_type,
        target_resource=request.target_resource,
        proof_hash=request.proof_hash
    )
    
    result = gate.request_action(context, tier)
    
    response = EnforcementResponse(
        allowed=result.allowed,
        status=result.status.value,
        reason=result.reason,
        proof_required=result.proof_required,
        authority_required=result.authority_required
    )
    
    if result.audit_entry:
        response.request_id = result.audit_entry.get("request_id")
        response.audit_hash = result.audit_entry.get("entry_hash")
    
    return response


@router.post("/approve", response_model=EnforcementResponse)
async def approve_action(request: ApprovalRequest):
    """
    Approve a pending action.
    
    Only authorized GIDs can approve actions.
    
    CONS-OCC-002: No override without Architect authority
    INV-OCC-003: Human authority final
    """
    gate = get_gate()
    result = gate.approve_action(request.request_id, request.authority_gid)
    
    return EnforcementResponse(
        allowed=result.allowed,
        status=result.status.value,
        reason=result.reason,
        proof_required=result.proof_required,
        authority_required=result.authority_required
    )


@router.post("/reject", response_model=EnforcementResponse)
async def reject_action(request: RejectionRequest):
    """
    Reject a pending action.
    
    Provides audit trail for rejected actions.
    """
    gate = get_gate()
    result = gate.reject_action(request.request_id, request.authority_gid, request.reason)
    
    return EnforcementResponse(
        allowed=result.allowed,
        status=result.status.value,
        reason=result.reason
    )


@router.get("/pending", response_model=List[PendingApprovalResponse])
async def get_pending_approvals():
    """
    Get list of pending approval requests.
    
    Returns all actions awaiting authority approval.
    Used by OCC UI to display approval queue.
    """
    gate = get_gate()
    pending = gate.get_pending_approvals()
    
    return [PendingApprovalResponse(**p) for p in pending]


@router.get("/audit", response_model=List[Dict[str, Any]])
async def get_audit_log(limit: int = 100):
    """
    Get governance audit log.
    
    Returns immutable audit entries for governance actions.
    Entries include cryptographic hashes for integrity verification.
    """
    enforcer = get_enforcer()
    # Return most recent entries
    return enforcer.audit_log[-limit:]


@router.get("/health")
async def governance_health():
    """
    Health check for governance subsystem.
    
    Returns:
    - Doctrine lock status
    - Enforcement mode
    - System ready state
    """
    enforcer = get_enforcer()
    locked = enforcer.check_doctrine_locked()
    
    return {
        "status": "healthy" if locked else "degraded",
        "doctrine_locked": locked,
        "enforcement_mode": "HARD",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Governance enforcement operational" if locked else "WARNING: Doctrine not locked - fail-closed active"
    }


# Router registration helper
def register_governance_routes(app):
    """Register governance routes with FastAPI app."""
    app.include_router(router)
    return router
