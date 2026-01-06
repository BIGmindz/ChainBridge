# ═══════════════════════════════════════════════════════════════════════════════
# OCC EMERGENCY KILL SWITCH (PAC-OCC-P16)
# EU AI Act Art. 14 Compliance Gate
#
# FILE-BASED PHYSICAL LOCK SYSTEM
# - ON:  File `KILL_SWITCH.lock` exists → ALL EXECUTION BLOCKED
# - OFF: File does not exist → Normal operation
#
# WHY FILE-BASED?
# Works even if Database crashes, Redis fails, or Network is down.
# If the file is on the disk, the system STOPS.
#
# GOVERNANCE:
# - SAM (GID-06) Security Design
# - LAW TIER: EU AI Act Art. 14 (Human Override)
# - FAIL-CLOSED: TRUE
#
# Authors:
# - SAM (GID-06) — Security Hardener
# - BENSON (GID-00) — Implementation
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICAL LOCK FILE
# ═══════════════════════════════════════════════════════════════════════════════

_PROJECT_ROOT = Path(__file__).parent.parent
KILL_SWITCH_FILE = _PROJECT_ROOT / "KILL_SWITCH.lock"

# Admin key for authorization (env override or default)
EMERGENCY_ADMIN_KEY = os.getenv("EMERGENCY_ADMIN_KEY", "CHAINBRIDGE_EMERGENCY_2026")


# ═══════════════════════════════════════════════════════════════════════════════
# CORE FUNCTIONS (Used by Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════


def is_kill_switch_active() -> bool:
    """
    Check if the emergency kill switch is active.
    
    This is the FIRST check before ANY LLM instantiation.
    If KILL_SWITCH.lock exists, ALL execution is BLOCKED.
    
    SAM (GID-06) Law: "If Kill Switch is ACTIVE, NO Execution is permitted."
    EU AI Act Art. 14: Human override MUST be immediate and unconditional.
    """
    return KILL_SWITCH_FILE.exists()


def activate_kill_switch(reason: str = "Manual emergency stop") -> bool:
    """
    Activate the kill switch by creating KILL_SWITCH.lock file.
    
    Returns True if successful, False if failed.
    """
    try:
        KILL_SWITCH_FILE.write_text(
            f"╔═══════════════════════════════════════════════════════════════════╗\n"
            f"║           🔴 KILL SWITCH ACTIVE — SYSTEM HALTED 🔴               ║\n"
            f"╠═══════════════════════════════════════════════════════════════════╣\n"
            f"║ Timestamp: {datetime.now(timezone.utc).isoformat():<52} ║\n"
            f"║ Reason: {reason[:54]:<54} ║\n"
            f"║ Authority: EU AI Act Art. 14 (Human Override)                    ║\n"
            f"╠═══════════════════════════════════════════════════════════════════╣\n"
            f"║ To resume: POST /occ/emergency/resume                            ║\n"
            f"║ Or manually delete this file: KILL_SWITCH.lock                   ║\n"
            f"╚═══════════════════════════════════════════════════════════════════╝\n"
        )
        logger.critical(f"🔴 KILL SWITCH ACTIVATED: {reason}")
        return True
    except Exception as e:
        logger.error(f"Failed to activate kill switch: {e}")
        return False


def deactivate_kill_switch() -> bool:
    """
    Deactivate the kill switch by removing KILL_SWITCH.lock file.
    
    Returns True if successful, False if failed.
    """
    try:
        if KILL_SWITCH_FILE.exists():
            KILL_SWITCH_FILE.unlink()
            logger.warning("🟢 KILL SWITCH DEACTIVATED — Execution resumed")
        return True
    except Exception as e:
        logger.error(f"Failed to deactivate kill switch: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class EmergencyStopRequest(BaseModel):
    """Request to activate the kill switch."""
    reason: str = Field(default="Manual emergency stop", min_length=1)
    admin_key: str = Field(..., description="Admin authorization key")


class EmergencyResumeRequest(BaseModel):
    """Request to deactivate the kill switch."""
    admin_key: str = Field(..., description="Admin authorization key")


class EmergencyStatusResponse(BaseModel):
    """Kill switch status response."""
    killed: bool
    lock_file: str
    message: str
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER — /occ/emergency/*
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/occ/emergency", tags=["Emergency Kill Switch (Art. 14)"])


@router.post("/stop", response_model=EmergencyStatusResponse)
async def emergency_stop(request: EmergencyStopRequest) -> EmergencyStatusResponse:
    """
    🔴 KILL SWITCH — Immediately halt ALL Benson execution.
    
    Creates KILL_SWITCH.lock file which blocks ALL execution paths.
    
    This is the EU AI Act Art. 14 "Human Override" — immediate, unconditional,
    works even if Database/Redis/Network is down.
    
    **Response:** "SYSTEM HALTED"
    """
    if request.admin_key != EMERGENCY_ADMIN_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin key. Emergency stop requires proper authorization.",
        )
    
    success = activate_kill_switch(request.reason)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to activate kill switch. Check file permissions.",
        )
    
    return EmergencyStatusResponse(
        killed=True,
        lock_file=str(KILL_SWITCH_FILE),
        message="SYSTEM HALTED",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/resume", response_model=EmergencyStatusResponse)
async def emergency_resume(request: EmergencyResumeRequest) -> EmergencyStatusResponse:
    """
    🟢 RESUME — Deactivate the kill switch.
    
    Removes the KILL_SWITCH.lock file, allowing execution to resume.
    
    **Requires:** Admin authorization key.
    """
    if request.admin_key != EMERGENCY_ADMIN_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin key. Resume requires proper authorization.",
        )
    
    success = deactivate_kill_switch()
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to deactivate kill switch.",
        )
    
    return EmergencyStatusResponse(
        killed=False,
        lock_file=str(KILL_SWITCH_FILE),
        message="SYSTEM RESUMED — Execution enabled",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status", response_model=EmergencyStatusResponse)
async def emergency_status() -> EmergencyStatusResponse:
    """
    Check the current kill switch status.
    
    **No authentication required** — status is public for monitoring/alerting.
    
    Returns: `{"killed": bool, "timestamp": str}`
    """
    killed = is_kill_switch_active()
    
    return EmergencyStatusResponse(
        killed=killed,
        lock_file=str(KILL_SWITCH_FILE),
        message="🔴 SYSTEM HALTED — Kill switch active" if killed else "🟢 System operational",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
