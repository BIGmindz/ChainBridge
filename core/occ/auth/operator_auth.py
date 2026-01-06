"""
Operator Authentication — JEFFREY_INTERNAL Mode Implementation

PAC-BENSON-P42: OCC Operationalization & Defect Remediation

Provides operator authentication and authorization:
- Operator modes: JEFFREY_INTERNAL, PRODUCTION, READONLY
- Permission lattice for OCC operations
- Session management
- Shadow-PDO enforcement

INVARIANTS:
- INV-AUTH-001: No anonymous operator access
- INV-AUTH-002: Mode determines permission ceiling
- INV-AUTH-003: JEFFREY_INTERNAL cannot settle production PDOs
- INV-AUTH-004: All operator actions are audited

Author: CODY (GID-01) + ALEX (GID-08)
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Literal, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Session duration
SESSION_DURATION_HOURS = 8
MAX_SESSIONS_PER_OPERATOR = 3


class OperatorMode(str, Enum):
    """Operator access mode."""
    JEFFREY_INTERNAL = "JEFFREY_INTERNAL"  # Founder mode: Shadow-only, full OCC
    PRODUCTION = "PRODUCTION"               # Production: Full access with settlement
    READONLY = "READONLY"                   # View-only: No mutations


class OperatorPermission(str, Enum):
    """Granular operator permissions."""
    # OCC Permissions
    OCC_VIEW = "occ:view"
    OCC_AGENTS_VIEW = "occ:agents:view"
    OCC_DECISIONS_VIEW = "occ:decisions:view"
    OCC_TIMELINE_VIEW = "occ:timeline:view"
    OCC_GOVERNANCE_VIEW = "occ:governance:view"
    
    # Kill Switch Permissions
    KILL_SWITCH_VIEW = "kill_switch:view"
    KILL_SWITCH_ARM = "kill_switch:arm"
    KILL_SWITCH_ENGAGE = "kill_switch:engage"
    KILL_SWITCH_DISENGAGE = "kill_switch:disengage"
    
    # PDO Permissions
    PDO_VIEW = "pdo:view"
    PDO_CREATE = "pdo:create"
    PDO_CREATE_SHADOW = "pdo:create:shadow"
    PDO_CREATE_PRODUCTION = "pdo:create:production"
    
    # Agent Permissions
    AGENT_VIEW = "agent:view"
    AGENT_BIND = "agent:bind"
    AGENT_UNBIND = "agent:unbind"
    AGENT_HALT = "agent:halt"
    
    # Settlement Permissions
    SETTLEMENT_VIEW = "settlement:view"
    SETTLEMENT_INITIATE = "settlement:initiate"
    SETTLEMENT_APPROVE = "settlement:approve"


# Permission lattice by mode
PERMISSION_LATTICE: Dict[OperatorMode, Set[OperatorPermission]] = {
    OperatorMode.JEFFREY_INTERNAL: {
        # Full OCC access
        OperatorPermission.OCC_VIEW,
        OperatorPermission.OCC_AGENTS_VIEW,
        OperatorPermission.OCC_DECISIONS_VIEW,
        OperatorPermission.OCC_TIMELINE_VIEW,
        OperatorPermission.OCC_GOVERNANCE_VIEW,
        # Full kill switch
        OperatorPermission.KILL_SWITCH_VIEW,
        OperatorPermission.KILL_SWITCH_ARM,
        OperatorPermission.KILL_SWITCH_ENGAGE,
        OperatorPermission.KILL_SWITCH_DISENGAGE,
        # Shadow PDOs only
        OperatorPermission.PDO_VIEW,
        OperatorPermission.PDO_CREATE,
        OperatorPermission.PDO_CREATE_SHADOW,
        # Full agent control
        OperatorPermission.AGENT_VIEW,
        OperatorPermission.AGENT_BIND,
        OperatorPermission.AGENT_UNBIND,
        OperatorPermission.AGENT_HALT,
        # View settlement only (no production)
        OperatorPermission.SETTLEMENT_VIEW,
    },
    OperatorMode.PRODUCTION: {
        # Full OCC access
        OperatorPermission.OCC_VIEW,
        OperatorPermission.OCC_AGENTS_VIEW,
        OperatorPermission.OCC_DECISIONS_VIEW,
        OperatorPermission.OCC_TIMELINE_VIEW,
        OperatorPermission.OCC_GOVERNANCE_VIEW,
        # Full kill switch
        OperatorPermission.KILL_SWITCH_VIEW,
        OperatorPermission.KILL_SWITCH_ARM,
        OperatorPermission.KILL_SWITCH_ENGAGE,
        OperatorPermission.KILL_SWITCH_DISENGAGE,
        # All PDO operations
        OperatorPermission.PDO_VIEW,
        OperatorPermission.PDO_CREATE,
        OperatorPermission.PDO_CREATE_SHADOW,
        OperatorPermission.PDO_CREATE_PRODUCTION,
        # Full agent control
        OperatorPermission.AGENT_VIEW,
        OperatorPermission.AGENT_BIND,
        OperatorPermission.AGENT_UNBIND,
        OperatorPermission.AGENT_HALT,
        # Full settlement
        OperatorPermission.SETTLEMENT_VIEW,
        OperatorPermission.SETTLEMENT_INITIATE,
        OperatorPermission.SETTLEMENT_APPROVE,
    },
    OperatorMode.READONLY: {
        # View-only permissions
        OperatorPermission.OCC_VIEW,
        OperatorPermission.OCC_AGENTS_VIEW,
        OperatorPermission.OCC_DECISIONS_VIEW,
        OperatorPermission.OCC_TIMELINE_VIEW,
        OperatorPermission.OCC_GOVERNANCE_VIEW,
        OperatorPermission.KILL_SWITCH_VIEW,
        OperatorPermission.PDO_VIEW,
        OperatorPermission.AGENT_VIEW,
        OperatorPermission.SETTLEMENT_VIEW,
    },
}


class OperatorSession(BaseModel):
    """Active operator session."""
    
    session_id: UUID = Field(default_factory=uuid4)
    operator_id: str = Field(..., description="Operator identifier (e.g., 'JEFFREY')")
    mode: OperatorMode = Field(..., description="Active operator mode")
    permissions: Set[OperatorPermission] = Field(default_factory=set)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(...)
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class OperatorAuthResult(BaseModel):
    """Result of operator authentication."""
    
    success: bool
    session: Optional[OperatorSession] = None
    token: Optional[str] = None
    message: str
    permissions: List[str] = Field(default_factory=list)


class OperatorAuthError(Exception):
    """Operator authentication/authorization error."""
    
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class OperatorAuthService:
    """
    Operator authentication and session management.
    
    Provides:
    - Session creation and validation
    - Permission checking
    - Mode-based access control
    - Shadow-PDO enforcement
    """
    
    def __init__(self):
        """Initialize the auth service."""
        self._lock = threading.Lock()
        self._sessions: Dict[str, OperatorSession] = {}  # token -> session
        self._operator_sessions: Dict[str, List[str]] = {}  # operator_id -> [tokens]
        
        # Known operators (in production, this would be from a secure store)
        self._known_operators: Dict[str, Dict] = {
            "JEFFREY": {
                "name": "JEFFREY",
                "role": "CTO",
                "allowed_modes": [OperatorMode.JEFFREY_INTERNAL, OperatorMode.READONLY],
            },
            "OPERATOR": {
                "name": "OPERATOR",
                "role": "Operator",
                "allowed_modes": [OperatorMode.READONLY],
            },
        }
    
    def _generate_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)
    
    def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        now = datetime.now(timezone.utc)
        expired_tokens = [
            token for token, session in self._sessions.items()
            if session.expires_at < now
        ]
        for token in expired_tokens:
            session = self._sessions.pop(token, None)
            if session:
                operator_tokens = self._operator_sessions.get(session.operator_id, [])
                if token in operator_tokens:
                    operator_tokens.remove(token)
    
    def authenticate(
        self,
        operator_id: str,
        mode: OperatorMode,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> OperatorAuthResult:
        """
        Authenticate an operator and create a session.
        
        Args:
            operator_id: Operator identifier
            mode: Requested operator mode
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Authentication result with session token
        """
        with self._lock:
            self._cleanup_expired()
            
            # Check if operator is known
            operator_config = self._known_operators.get(operator_id)
            if not operator_config:
                logger.warning(f"Unknown operator attempted auth: {operator_id}")
                return OperatorAuthResult(
                    success=False,
                    message=f"Unknown operator: {operator_id}",
                )
            
            # Check if mode is allowed for this operator
            allowed_modes = operator_config.get("allowed_modes", [])
            if mode not in allowed_modes:
                logger.warning(
                    f"Operator {operator_id} requested unauthorized mode: {mode.value}"
                )
                return OperatorAuthResult(
                    success=False,
                    message=f"Mode {mode.value} not authorized for operator {operator_id}",
                )
            
            # Check session limit
            existing_tokens = self._operator_sessions.get(operator_id, [])
            if len(existing_tokens) >= MAX_SESSIONS_PER_OPERATOR:
                # Remove oldest session
                oldest_token = existing_tokens[0]
                self._sessions.pop(oldest_token, None)
                existing_tokens.remove(oldest_token)
            
            # Create session
            now = datetime.now(timezone.utc)
            expires = now + timedelta(hours=SESSION_DURATION_HOURS)
            permissions = PERMISSION_LATTICE.get(mode, set())
            
            session = OperatorSession(
                operator_id=operator_id,
                mode=mode,
                permissions=permissions,
                expires_at=expires,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            token = self._generate_token()
            self._sessions[token] = session
            
            if operator_id not in self._operator_sessions:
                self._operator_sessions[operator_id] = []
            self._operator_sessions[operator_id].append(token)
            
            logger.info(
                f"Operator {operator_id} authenticated in mode {mode.value} "
                f"(session expires: {expires.isoformat()})"
            )
            
            return OperatorAuthResult(
                success=True,
                session=session,
                token=token,
                message=f"Authenticated as {operator_id} in {mode.value} mode",
                permissions=[p.value for p in permissions],
            )
    
    def validate_session(self, token: str) -> Optional[OperatorSession]:
        """
        Validate a session token.
        
        Args:
            token: Session token
        
        Returns:
            Session if valid, None otherwise
        """
        with self._lock:
            self._cleanup_expired()
            
            session = self._sessions.get(token)
            if not session:
                return None
            
            now = datetime.now(timezone.utc)
            if session.expires_at < now:
                self._sessions.pop(token, None)
                return None
            
            # Update last activity
            session_dict = session.model_dump()
            session_dict["last_activity"] = now
            self._sessions[token] = OperatorSession.model_validate(session_dict)
            
            return self._sessions[token]
    
    def check_permission(
        self,
        token: str,
        permission: OperatorPermission,
    ) -> bool:
        """
        Check if session has a specific permission.
        
        Args:
            token: Session token
            permission: Permission to check
        
        Returns:
            True if permitted, False otherwise
        """
        session = self.validate_session(token)
        if not session:
            return False
        return permission in session.permissions
    
    def require_permission(
        self,
        token: str,
        permission: OperatorPermission,
    ) -> OperatorSession:
        """
        Require a specific permission, raising error if not present.
        
        Args:
            token: Session token
            permission: Required permission
        
        Returns:
            Valid session
        
        Raises:
            OperatorAuthError: If unauthorized or session invalid
        """
        session = self.validate_session(token)
        if not session:
            raise OperatorAuthError("Invalid or expired session", "INVALID_SESSION")
        
        if permission not in session.permissions:
            raise OperatorAuthError(
                f"Permission denied: {permission.value}",
                "PERMISSION_DENIED"
            )
        
        return session
    
    def can_create_production_pdo(self, token: str) -> bool:
        """Check if session can create production PDOs."""
        return self.check_permission(token, OperatorPermission.PDO_CREATE_PRODUCTION)
    
    def get_pdo_classification(self, token: str) -> Literal["SHADOW", "PRODUCTION"]:
        """
        Get the PDO classification for the session.
        
        JEFFREY_INTERNAL mode always produces SHADOW PDOs.
        PRODUCTION mode produces PRODUCTION PDOs.
        """
        session = self.validate_session(token)
        if not session:
            return "SHADOW"  # Default to SHADOW for safety
        
        if session.mode == OperatorMode.JEFFREY_INTERNAL:
            return "SHADOW"
        elif session.mode == OperatorMode.PRODUCTION:
            return "PRODUCTION"
        else:
            return "SHADOW"
    
    def get_kill_switch_auth_level(self, token: str):
        """Get kill switch authorization level from session."""
        from core.occ.store.kill_switch import KillSwitchAuthLevel
        
        session = self.validate_session(token)
        if not session:
            return KillSwitchAuthLevel.UNAUTHORIZED
        
        has_engage = OperatorPermission.KILL_SWITCH_ENGAGE in session.permissions
        has_arm = OperatorPermission.KILL_SWITCH_ARM in session.permissions
        
        if has_engage:
            return KillSwitchAuthLevel.FULL_ACCESS
        elif has_arm:
            return KillSwitchAuthLevel.ARM_ONLY
        else:
            return KillSwitchAuthLevel.UNAUTHORIZED
    
    def revoke_session(self, token: str) -> bool:
        """Revoke a session."""
        with self._lock:
            session = self._sessions.pop(token, None)
            if session:
                operator_tokens = self._operator_sessions.get(session.operator_id, [])
                if token in operator_tokens:
                    operator_tokens.remove(token)
                logger.info(f"Session revoked for operator {session.operator_id}")
                return True
            return False
    
    def revoke_all_sessions(self, operator_id: str) -> int:
        """Revoke all sessions for an operator."""
        with self._lock:
            tokens = self._operator_sessions.get(operator_id, [])
            count = 0
            for token in tokens.copy():
                if self._sessions.pop(token, None):
                    count += 1
            self._operator_sessions[operator_id] = []
            if count:
                logger.info(f"Revoked {count} sessions for operator {operator_id}")
            return count
    
    def list_sessions(self, operator_id: Optional[str] = None) -> List[OperatorSession]:
        """List active sessions."""
        with self._lock:
            self._cleanup_expired()
            
            if operator_id:
                tokens = self._operator_sessions.get(operator_id, [])
                return [self._sessions[t] for t in tokens if t in self._sessions]
            else:
                return list(self._sessions.values())


# Module-level singleton
_default_service: Optional[OperatorAuthService] = None


def get_operator_auth_service() -> OperatorAuthService:
    """Get the default operator auth service singleton."""
    global _default_service
    if _default_service is None:
        _default_service = OperatorAuthService()
    return _default_service


def reset_operator_auth_service() -> None:
    """Reset the default operator auth service (for testing only)."""
    global _default_service
    _default_service = None
