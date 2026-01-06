# ═══════════════════════════════════════════════════════════════════════════════
# OCC Kill Switch Control API — Authenticated Mutation Endpoints
# PAC-BENSON-P42: OCC Operationalization & Defect Remediation
#
# Provides AUTHENTICATED mutation endpoints for kill switch control:
# - POST /occ/kill-switch/arm      - Arm the kill switch
# - POST /occ/kill-switch/engage   - Engage the kill switch (HALT ALL)
# - POST /occ/kill-switch/disengage - Disengage the kill switch
# - POST /occ/kill-switch/disarm   - Disarm the kill switch
# - GET  /occ/kill-switch/audit    - Get kill switch audit log
#
# INVARIANTS:
# - INV-KILL-001: Kill switch DISABLED unless explicitly authorized
# - INV-KILL-002: All actions require operator authentication
# - INV-KILL-003: ENGAGE requires FULL_ACCESS + reason
# - INV-KILL-004: All state changes produce PDO
#
# Authors:
# - CODY (GID-01) — Backend Lead
# - SAM (GID-06) — Security Hardener
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/kill-switch", tags=["OCC Kill Switch Control"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class KillSwitchArmRequest(BaseModel):
    """Request to arm the kill switch."""
    reason: str = Field(default="Operator initiated arm", min_length=1)


class KillSwitchEngageRequest(BaseModel):
    """Request to engage the kill switch."""
    reason: str = Field(..., min_length=10, description="Mandatory engagement reason")
    affected_pacs: List[str] = Field(default_factory=list, description="PACs to freeze")


class KillSwitchDisengageRequest(BaseModel):
    """Request to disengage the kill switch."""
    reason: str = Field(..., min_length=10, description="Mandatory disengagement reason")


class KillSwitchDisarmRequest(BaseModel):
    """Request to disarm the kill switch."""
    reason: str = Field(default="Operator initiated disarm", min_length=1)


class KillSwitchStatusResponse(BaseModel):
    """Kill switch status response."""
    state: str
    armed_by: Optional[str] = None
    armed_at: Optional[datetime] = None
    engaged_by: Optional[str] = None
    engaged_at: Optional[datetime] = None
    engagement_reason: Optional[str] = None
    affected_pacs: List[str] = Field(default_factory=list)
    cooldown_ends_at: Optional[datetime] = None
    message: str


class KillSwitchEngageResponse(BaseModel):
    """Kill switch engagement response."""
    success: bool
    state: str
    message: str
    agents_halted: int = 0
    pacs_frozen: int = 0
    snapshot_id: Optional[str] = None


class KillSwitchAuditEntry(BaseModel):
    """Kill switch audit log entry."""
    entry_id: str
    timestamp: datetime
    action: str
    from_state: str
    to_state: str
    operator_id: str
    reason: str
    affected_pacs: List[str] = Field(default_factory=list)


class KillSwitchAuditResponse(BaseModel):
    """Kill switch audit log response."""
    entries: List[KillSwitchAuditEntry]
    total: int


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════════


def get_operator_session(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """
    Extract and validate operator session from Authorization header.
    
    Returns (operator_id, auth_level) tuple.
    """
    from core.occ.auth.operator_auth import get_operator_auth_service
    from core.occ.store.kill_switch import KillSwitchAuthLevel
    
    if not authorization:
        return None, KillSwitchAuthLevel.UNAUTHORIZED
    
    # Extract token from "Bearer <token>"
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    auth_service = get_operator_auth_service()
    session = auth_service.validate_session(token)
    
    if not session:
        return None, KillSwitchAuthLevel.UNAUTHORIZED
    
    auth_level = auth_service.get_kill_switch_auth_level(token)
    return session.operator_id, auth_level


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/arm", response_model=KillSwitchStatusResponse)
async def arm_kill_switch(
    request: KillSwitchArmRequest,
    authorization: Optional[str] = Header(None),
) -> KillSwitchStatusResponse:
    """
    Arm the kill switch (prepare for engagement).
    
    Requires ARM_ONLY or FULL_ACCESS authorization.
    
    State transition: DISARMED/COOLDOWN -> ARMED
    """
    from core.occ.store.kill_switch import get_kill_switch_service, KillSwitchError
    
    operator_id, auth_level = get_operator_session(authorization)
    
    if not operator_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Bearer token in Authorization header.",
        )
    
    service = get_kill_switch_service()
    
    try:
        status = service.arm(
            operator_id=operator_id,
            auth_level=auth_level,
            reason=request.reason,
        )
        
        logger.info(f"Kill switch ARMED by {operator_id}: {request.reason}")
        
        return KillSwitchStatusResponse(
            state=status.state.value,
            armed_by=status.armed_by,
            armed_at=status.armed_at,
            message=f"Kill switch armed by {operator_id}",
        )
    
    except KillSwitchError as e:
        raise HTTPException(
            status_code=403 if e.code in ("UNAUTHORIZED", "INSUFFICIENT_AUTH") else 400,
            detail=str(e),
        )


@router.post("/engage", response_model=KillSwitchEngageResponse)
async def engage_kill_switch(
    request: KillSwitchEngageRequest,
    authorization: Optional[str] = Header(None),
) -> KillSwitchEngageResponse:
    """
    ENGAGE the kill switch — HALT ALL EXECUTION.
    
    Requires FULL_ACCESS authorization and mandatory reason.
    
    State transition: ARMED -> ENGAGED
    
    ⚠️ WARNING: This will immediately halt all agent execution.
    """
    from core.occ.store.kill_switch import get_kill_switch_service, KillSwitchError
    
    operator_id, auth_level = get_operator_session(authorization)
    
    if not operator_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Bearer token in Authorization header.",
        )
    
    service = get_kill_switch_service()
    
    try:
        result = service.engage(
            operator_id=operator_id,
            auth_level=auth_level,
            reason=request.reason,
            affected_pacs=request.affected_pacs,
        )
        
        logger.critical(
            f"KILL SWITCH ENGAGED by {operator_id}: {request.reason} "
            f"(halted {result.agents_halted} agents)"
        )
        
        return KillSwitchEngageResponse(
            success=result.success,
            state=result.state.value,
            message=result.message,
            agents_halted=result.agents_halted,
            pacs_frozen=result.pacs_frozen,
            snapshot_id=result.snapshot_id,
        )
    
    except KillSwitchError as e:
        raise HTTPException(
            status_code=403 if e.code in ("UNAUTHORIZED", "INSUFFICIENT_AUTH") else 400,
            detail=str(e),
        )


@router.post("/disengage", response_model=KillSwitchStatusResponse)
async def disengage_kill_switch(
    request: KillSwitchDisengageRequest,
    authorization: Optional[str] = Header(None),
) -> KillSwitchStatusResponse:
    """
    Disengage the kill switch (resume operations).
    
    Requires FULL_ACCESS authorization.
    
    State transition: ENGAGED -> COOLDOWN
    
    A cooldown period will be active before the switch can be re-armed.
    """
    from core.occ.store.kill_switch import get_kill_switch_service, KillSwitchError
    
    operator_id, auth_level = get_operator_session(authorization)
    
    if not operator_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Bearer token in Authorization header.",
        )
    
    service = get_kill_switch_service()
    
    try:
        status = service.disengage(
            operator_id=operator_id,
            auth_level=auth_level,
            reason=request.reason,
        )
        
        logger.warning(f"Kill switch DISENGAGED by {operator_id}: {request.reason}")
        
        return KillSwitchStatusResponse(
            state=status.state.value,
            cooldown_ends_at=status.cooldown_ends_at,
            message=f"Kill switch disengaged. Cooldown until {status.cooldown_ends_at}",
        )
    
    except KillSwitchError as e:
        raise HTTPException(
            status_code=403 if e.code in ("UNAUTHORIZED", "INSUFFICIENT_AUTH") else 400,
            detail=str(e),
        )


@router.post("/disarm", response_model=KillSwitchStatusResponse)
async def disarm_kill_switch(
    request: KillSwitchDisarmRequest,
    authorization: Optional[str] = Header(None),
) -> KillSwitchStatusResponse:
    """
    Disarm the kill switch (return to normal from ARMED).
    
    Requires ARM_ONLY or FULL_ACCESS authorization.
    
    State transition: ARMED -> DISARMED
    """
    from core.occ.store.kill_switch import get_kill_switch_service, KillSwitchError
    
    operator_id, auth_level = get_operator_session(authorization)
    
    if not operator_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Bearer token in Authorization header.",
        )
    
    service = get_kill_switch_service()
    
    try:
        status = service.disarm(
            operator_id=operator_id,
            auth_level=auth_level,
            reason=request.reason,
        )
        
        logger.info(f"Kill switch DISARMED by {operator_id}: {request.reason}")
        
        return KillSwitchStatusResponse(
            state=status.state.value,
            message=f"Kill switch disarmed by {operator_id}",
        )
    
    except KillSwitchError as e:
        raise HTTPException(
            status_code=403 if e.code in ("UNAUTHORIZED", "INSUFFICIENT_AUTH") else 400,
            detail=str(e),
        )


@router.get("/audit", response_model=KillSwitchAuditResponse)
async def get_kill_switch_audit(
    limit: int = 100,
    operator_id: Optional[str] = None,
    action: Optional[str] = None,
    authorization: Optional[str] = Header(None),
) -> KillSwitchAuditResponse:
    """
    Get kill switch audit log.
    
    Requires authentication to view audit log.
    """
    from core.occ.store.kill_switch import get_kill_switch_service, KillSwitchAction
    
    session_operator, _ = get_operator_session(authorization)
    
    if not session_operator:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to view audit log.",
        )
    
    service = get_kill_switch_service()
    
    action_filter = None
    if action:
        try:
            action_filter = KillSwitchAction(action)
        except ValueError:
            pass
    
    entries = service.get_audit_log(
        limit=limit,
        operator_id=operator_id,
        action=action_filter,
    )
    
    return KillSwitchAuditResponse(
        entries=[
            KillSwitchAuditEntry(
                entry_id=str(e.entry_id),
                timestamp=e.timestamp,
                action=e.action.value,
                from_state=e.from_state.value,
                to_state=e.to_state.value,
                operator_id=e.operator_id,
                reason=e.reason,
                affected_pacs=e.affected_pacs,
            )
            for e in entries
        ],
        total=len(entries),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EMERGENCY FILE-BASED KILL SWITCH (PAC-OCC-P16)
# SAM (GID-06) Design: Works even if DB/Auth is down
# ═══════════════════════════════════════════════════════════════════════════════

import os
from pathlib import Path

# File-based lock location (works even if DB is down)
_PROJECT_ROOT = Path(__file__).parent.parent
EMERGENCY_STOP_FILE = _PROJECT_ROOT / "STOP.lock"


def is_emergency_stop_active() -> bool:
    """
    Check if the emergency stop is active (file-based).
    This is the ULTIMATE kill switch - works without DB/Auth.
    """
    return EMERGENCY_STOP_FILE.exists()


def activate_emergency_stop(reason: str = "Emergency stop activated") -> bool:
    """Activate the emergency stop by creating STOP.lock file."""
    try:
        EMERGENCY_STOP_FILE.write_text(
            f"EMERGENCY STOP ACTIVE\n"
            f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
            f"Reason: {reason}\n"
        )
        logger.critical(f"🔴 EMERGENCY STOP ACTIVATED: {reason}")
        return True
    except Exception as e:
        logger.error(f"Failed to activate emergency stop: {e}")
        return False


def deactivate_emergency_stop() -> bool:
    """Deactivate the emergency stop by removing STOP.lock file."""
    try:
        if EMERGENCY_STOP_FILE.exists():
            EMERGENCY_STOP_FILE.unlink()
            logger.warning("🟢 EMERGENCY STOP DEACTIVATED")
        return True
    except Exception as e:
        logger.error(f"Failed to deactivate emergency stop: {e}")
        return False


class EmergencyStopRequest(BaseModel):
    """Request to activate emergency stop."""
    reason: str = Field(default="Manual emergency stop", min_length=1)
    admin_key: str = Field(..., description="Admin authorization key")


class EmergencyResumeRequest(BaseModel):
    """Request to deactivate emergency stop."""
    admin_key: str = Field(..., description="Admin authorization key")


class EmergencyStatusResponse(BaseModel):
    """Emergency stop status response."""
    killed: bool
    stop_file: str
    message: str
    timestamp: str


# Simple admin key check (in production, use proper auth)
EMERGENCY_ADMIN_KEY = os.getenv("EMERGENCY_ADMIN_KEY", "CHAINBRIDGE_EMERGENCY_2026")


@router.post("/emergency/stop", response_model=EmergencyStatusResponse, tags=["Emergency"])
async def emergency_stop(request: EmergencyStopRequest) -> EmergencyStatusResponse:
    """
    🔴 EMERGENCY STOP — Immediately halt ALL Benson execution.
    
    This is the file-based "Red Button" that works even if:
    - Database is down
    - Auth services are unavailable
    - Network is degraded
    
    Creates STOP.lock file which the orchestrator checks before every execution.
    """
    if request.admin_key != EMERGENCY_ADMIN_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin key. Emergency stop requires proper authorization.",
        )
    
    success = activate_emergency_stop(request.reason)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to activate emergency stop. Check file permissions.",
        )
    
    return EmergencyStatusResponse(
        killed=True,
        stop_file=str(EMERGENCY_STOP_FILE),
        message=f"🔴 EMERGENCY STOP ACTIVE: {request.reason}",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/emergency/resume", response_model=EmergencyStatusResponse, tags=["Emergency"])
async def emergency_resume(request: EmergencyResumeRequest) -> EmergencyStatusResponse:
    """
    🟢 EMERGENCY RESUME — Deactivate the emergency stop.
    
    Removes the STOP.lock file, allowing Benson execution to resume.
    """
    if request.admin_key != EMERGENCY_ADMIN_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin key. Resume requires proper authorization.",
        )
    
    success = deactivate_emergency_stop()
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to deactivate emergency stop.",
        )
    
    return EmergencyStatusResponse(
        killed=False,
        stop_file=str(EMERGENCY_STOP_FILE),
        message="🟢 EMERGENCY STOP DEACTIVATED — Execution resumed",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/emergency/status", response_model=EmergencyStatusResponse, tags=["Emergency"])
async def emergency_status() -> EmergencyStatusResponse:
    """
    Check the current emergency stop status.
    
    No authentication required — status is public for monitoring.
    """
    killed = is_emergency_stop_active()
    
    return EmergencyStatusResponse(
        killed=killed,
        stop_file=str(EMERGENCY_STOP_FILE),
        message="🔴 EMERGENCY STOP ACTIVE — Execution blocked" if killed else "🟢 System operational",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
