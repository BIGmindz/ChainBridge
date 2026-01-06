# ═══════════════════════════════════════════════════════════════════════════════
# OCC Operator Auth API — Authentication & Session Management
# PAC-BENSON-P42: OCC Operationalization & Defect Remediation
#
# Provides authentication endpoints for OCC operators:
# - POST /occ/auth/login    - Authenticate and get session token
# - POST /occ/auth/logout   - Revoke session
# - GET  /occ/auth/session  - Get current session info
# - GET  /occ/auth/modes    - List available operator modes
#
# INVARIANTS:
# - INV-AUTH-001: No anonymous operator access
# - INV-AUTH-002: Mode determines permission ceiling
# - INV-AUTH-003: JEFFREY_INTERNAL cannot settle production PDOs
#
# Authors:
# - CODY (GID-01) — Backend Lead
# - ALEX (GID-08) — Governance Enforcer
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/auth", tags=["OCC Auth"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class LoginRequest(BaseModel):
    """Login request."""
    operator_id: str = Field(..., description="Operator identifier (e.g., 'JEFFREY')")
    mode: str = Field(..., description="Operator mode (JEFFREY_INTERNAL, PRODUCTION, READONLY)")


class LoginResponse(BaseModel):
    """Login response."""
    success: bool
    token: Optional[str] = None
    operator_id: Optional[str] = None
    mode: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    message: str


class SessionResponse(BaseModel):
    """Session info response."""
    operator_id: str
    mode: str
    permissions: List[str]
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    pdo_classification: str = Field(description="SHADOW or PRODUCTION based on mode")


class ModeInfo(BaseModel):
    """Operator mode information."""
    mode: str
    description: str
    permissions: List[str]
    pdo_classification: str


class ModesResponse(BaseModel):
    """Available modes response."""
    modes: List[ModeInfo]


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """
    Authenticate operator and create session.
    
    Returns a Bearer token for use in Authorization header.
    
    Available modes:
    - JEFFREY_INTERNAL: Founder mode, Shadow PDOs only
    - PRODUCTION: Full production access
    - READONLY: View-only access
    """
    from core.occ.auth.operator_auth import get_operator_auth_service, OperatorMode
    
    try:
        mode = OperatorMode(request.mode)
    except ValueError:
        return LoginResponse(
            success=False,
            message=f"Invalid mode: {request.mode}. Valid modes: JEFFREY_INTERNAL, PRODUCTION, READONLY",
        )
    
    auth_service = get_operator_auth_service()
    result = auth_service.authenticate(
        operator_id=request.operator_id,
        mode=mode,
    )
    
    if result.success:
        logger.info(f"Operator {request.operator_id} authenticated in mode {request.mode}")
        return LoginResponse(
            success=True,
            token=result.token,
            operator_id=request.operator_id,
            mode=request.mode,
            permissions=result.permissions,
            expires_at=result.session.expires_at if result.session else None,
            message=result.message,
        )
    else:
        logger.warning(f"Authentication failed for {request.operator_id}: {result.message}")
        return LoginResponse(
            success=False,
            message=result.message,
        )


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)) -> dict:
    """
    Revoke current session.
    """
    from core.occ.auth.operator_auth import get_operator_auth_service
    
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    
    auth_service = get_operator_auth_service()
    revoked = auth_service.revoke_session(token)
    
    if revoked:
        return {"success": True, "message": "Session revoked"}
    else:
        return {"success": False, "message": "Session not found or already expired"}


@router.get("/session", response_model=SessionResponse)
async def get_session(authorization: Optional[str] = Header(None)) -> SessionResponse:
    """
    Get current session information.
    """
    from core.occ.auth.operator_auth import get_operator_auth_service
    
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    
    auth_service = get_operator_auth_service()
    session = auth_service.validate_session(token)
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    pdo_classification = auth_service.get_pdo_classification(token)
    
    return SessionResponse(
        operator_id=session.operator_id,
        mode=session.mode.value,
        permissions=[p.value for p in session.permissions],
        created_at=session.created_at,
        expires_at=session.expires_at,
        last_activity=session.last_activity,
        pdo_classification=pdo_classification,
    )


@router.get("/modes", response_model=ModesResponse)
async def get_available_modes() -> ModesResponse:
    """
    List available operator modes and their permissions.
    """
    from core.occ.auth.operator_auth import OperatorMode, PERMISSION_LATTICE
    
    modes = []
    
    mode_descriptions = {
        OperatorMode.JEFFREY_INTERNAL: "Founder mode: Full OCC access, Shadow PDOs only, no production settlement",
        OperatorMode.PRODUCTION: "Production mode: Full access including production PDOs and settlement",
        OperatorMode.READONLY: "Read-only mode: View access only, no mutations",
    }
    
    mode_pdo_class = {
        OperatorMode.JEFFREY_INTERNAL: "SHADOW",
        OperatorMode.PRODUCTION: "PRODUCTION",
        OperatorMode.READONLY: "N/A",
    }
    
    for mode in OperatorMode:
        permissions = PERMISSION_LATTICE.get(mode, set())
        modes.append(ModeInfo(
            mode=mode.value,
            description=mode_descriptions.get(mode, ""),
            permissions=[p.value for p in permissions],
            pdo_classification=mode_pdo_class.get(mode, "SHADOW"),
        ))
    
    return ModesResponse(modes=modes)
