"""
Dual Control Enforcement — T4 Single Point Authority Hardening

PAC: PAC-OCC-P07
Lane: EX1 — T4 Dual Control Hardening
Agent: Sam (GID-06)

Addresses existential failure EX1: "T4 Single Point Authority"
BER-P05 finding: Kill switch engage, T4 settlement have no dual approval

MECHANICAL ENFORCEMENT:
- T4 actions require TWO distinct operators
- Hardware token simulation (TOTP-style) for T4 authority
- Time-bounded approval windows
- No single operator can complete T4 action alone

INVARIANTS:
- INV-DUAL-001: T4 actions MUST have 2 distinct approvers
- INV-DUAL-002: Approvers cannot be the same identity
- INV-DUAL-003: Approval window expires after T4_APPROVAL_WINDOW_SECONDS
- INV-DUAL-004: All dual control attempts are audited
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import struct
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Approval window in seconds (default 5 minutes)
T4_APPROVAL_WINDOW_SECONDS = int(os.environ.get("T4_APPROVAL_WINDOW_SECONDS", "300"))

# TOTP parameters for hardware token simulation
TOTP_DIGITS = 6
TOTP_INTERVAL = 30  # 30-second intervals


class T4Action(str, Enum):
    """Actions requiring T4 dual control."""
    
    KILL_SWITCH_ENGAGE = "kill_switch:engage"
    KILL_SWITCH_DISENGAGE = "kill_switch:disengage"
    SETTLEMENT_T4 = "settlement:t4"
    AGENT_HALT_ALL = "agent:halt_all"
    GOVERNANCE_OVERRIDE = "governance:override"
    CONSTITUTION_MODIFY = "constitution:modify"


class ApprovalStatus(str, Enum):
    """Status of a dual control approval request."""
    
    PENDING = "pending"
    FIRST_APPROVED = "first_approved"
    FULLY_APPROVED = "fully_approved"
    EXPIRED = "expired"
    REJECTED = "rejected"


# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE TOKEN SIMULATION (TOTP-style)
# ═══════════════════════════════════════════════════════════════════════════════


class HardwareTokenSimulator:
    """
    Simulates hardware token (TOTP-style) for T4 authority.
    
    In production, this would integrate with actual hardware tokens
    (YubiKey, RSA SecurID, etc.). This provides the mechanical interface.
    """
    
    def __init__(self, secret_key: Optional[bytes] = None):
        """Initialize with a secret key (or generate one)."""
        self._secret = secret_key or secrets.token_bytes(32)
        
    def generate_code(self, operator_id: str, timestamp: Optional[float] = None) -> str:
        """
        Generate a time-based code for the operator.
        
        Args:
            operator_id: The operator's identity
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            6-digit TOTP-style code
        """
        ts = timestamp or time.time()
        counter = int(ts // TOTP_INTERVAL)
        
        # Combine secret with operator ID for operator-specific codes
        key = hmac.new(
            self._secret,
            operator_id.encode("utf-8"),
            hashlib.sha256
        ).digest()
        
        # Generate HOTP
        counter_bytes = struct.pack(">Q", counter)
        h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        
        # Dynamic truncation
        offset = h[-1] & 0x0F
        code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
        code = code % (10 ** TOTP_DIGITS)
        
        return str(code).zfill(TOTP_DIGITS)
    
    def verify_code(
        self,
        operator_id: str,
        code: str,
        tolerance: int = 1,
        timestamp: Optional[float] = None
    ) -> bool:
        """
        Verify a TOTP code with time tolerance.
        
        Args:
            operator_id: The operator's identity
            code: The code to verify
            tolerance: Number of intervals to check before/after
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            True if code is valid
        """
        ts = timestamp or time.time()
        
        for offset in range(-tolerance, tolerance + 1):
            check_ts = ts + (offset * TOTP_INTERVAL)
            expected = self.generate_code(operator_id, check_ts)
            if hmac.compare_digest(code, expected):
                return True
        
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# DUAL CONTROL REQUEST
# ═══════════════════════════════════════════════════════════════════════════════


class DualControlRequest(BaseModel):
    """A request for T4 dual control approval."""
    
    request_id: UUID = Field(default_factory=uuid4)
    action: T4Action
    initiated_by: str
    initiated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    
    # First approval
    first_approver: Optional[str] = None
    first_approved_at: Optional[datetime] = None
    first_approver_token_verified: bool = False
    
    # Second approval
    second_approver: Optional[str] = None
    second_approved_at: Optional[datetime] = None
    second_approver_token_verified: bool = False
    
    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    rejection_reason: Optional[str] = None
    
    # Context
    action_context: Dict[str, Any] = Field(default_factory=dict)
    audit_entries: List[Dict[str, Any]] = Field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if the request has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def add_audit(self, event: str, operator: str, details: Optional[Dict] = None) -> None:
        """Add an audit entry."""
        self.audit_entries.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "operator": operator,
            "details": details or {},
        })


class DualControlResult(BaseModel):
    """Result of a dual control operation."""
    
    success: bool
    request_id: UUID
    status: ApprovalStatus
    message: str
    approvers: List[str] = Field(default_factory=list)
    execution_authorized: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# DUAL CONTROL ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════


class DualControlEnforcer:
    """
    Enforces dual control for T4 actions.
    
    INVARIANT ENFORCEMENT:
    - INV-DUAL-001: Two distinct approvers required
    - INV-DUAL-002: Same identity cannot approve twice
    - INV-DUAL-003: Time-bounded approval window
    - INV-DUAL-004: Full audit trail
    """
    
    def __init__(self, token_simulator: Optional[HardwareTokenSimulator] = None):
        """Initialize the dual control enforcer."""
        self._lock = threading.Lock()
        self._pending_requests: Dict[UUID, DualControlRequest] = {}
        self._completed_requests: List[DualControlRequest] = []
        self._token_sim = token_simulator or HardwareTokenSimulator()
        
        # Track operator approvals to prevent rapid re-use
        self._recent_approvals: Dict[str, List[datetime]] = {}
        
        logger.info("DualControlEnforcer initialized — T4 actions require dual approval")
    
    def _normalize_operator_id(self, operator_id: str) -> str:
        """Normalize operator ID for comparison (prevent identity spoofing)."""
        return operator_id.strip().lower()
    
    def _audit(self, request: DualControlRequest, event: str, operator: str, details: Optional[Dict] = None) -> None:
        """Record audit entry."""
        request.add_audit(event, operator, details)
        logger.info(
            f"DUAL_CONTROL_AUDIT [{request.request_id}]: {event} by {operator} "
            f"for {request.action.value}"
        )
    
    def _cleanup_expired(self) -> None:
        """Clean up expired requests."""
        now = datetime.now(timezone.utc)
        expired_ids = [
            rid for rid, req in self._pending_requests.items()
            if req.is_expired()
        ]
        for rid in expired_ids:
            req = self._pending_requests.pop(rid)
            req.status = ApprovalStatus.EXPIRED
            self._audit(req, "REQUEST_EXPIRED", "system")
            self._completed_requests.append(req)
            logger.warning(f"Dual control request {rid} expired for {req.action.value}")
    
    def initiate_request(
        self,
        action: T4Action,
        operator_id: str,
        context: Optional[Dict[str, Any]] = None,
        approval_window_seconds: Optional[int] = None
    ) -> DualControlRequest:
        """
        Initiate a dual control request for a T4 action.
        
        Args:
            action: The T4 action requiring dual control
            operator_id: The operator initiating the request
            context: Optional context for the action
            approval_window_seconds: Custom approval window (default: T4_APPROVAL_WINDOW_SECONDS)
            
        Returns:
            The created request
        """
        with self._lock:
            self._cleanup_expired()
            
            window = approval_window_seconds or T4_APPROVAL_WINDOW_SECONDS
            now = datetime.now(timezone.utc)
            
            request = DualControlRequest(
                action=action,
                initiated_by=operator_id,
                initiated_at=now,
                expires_at=now + timedelta(seconds=window),
                action_context=context or {},
            )
            
            self._pending_requests[request.request_id] = request
            self._audit(request, "REQUEST_INITIATED", operator_id, {
                "action": action.value,
                "expires_at": request.expires_at.isoformat(),
            })
            
            logger.info(
                f"Dual control request {request.request_id} initiated for {action.value} "
                f"by {operator_id}, expires at {request.expires_at.isoformat()}"
            )
            
            return request
    
    def approve(
        self,
        request_id: UUID,
        approver_id: str,
        hardware_token_code: Optional[str] = None,
    ) -> DualControlResult:
        """
        Approve a dual control request.
        
        Args:
            request_id: The request to approve
            approver_id: The operator providing approval
            hardware_token_code: Optional hardware token code for enhanced security
            
        Returns:
            Result of the approval attempt
            
        INVARIANT ENFORCEMENT:
        - INV-DUAL-001: Checks for 2 distinct approvers
        - INV-DUAL-002: Prevents same identity from approving twice
        """
        with self._lock:
            self._cleanup_expired()
            
            if request_id not in self._pending_requests:
                return DualControlResult(
                    success=False,
                    request_id=request_id,
                    status=ApprovalStatus.EXPIRED,
                    message="Request not found or expired",
                )
            
            request = self._pending_requests[request_id]
            
            # Check expiry
            if request.is_expired():
                request.status = ApprovalStatus.EXPIRED
                self._pending_requests.pop(request_id)
                self._completed_requests.append(request)
                return DualControlResult(
                    success=False,
                    request_id=request_id,
                    status=ApprovalStatus.EXPIRED,
                    message="Request has expired",
                )
            
            normalized_approver = self._normalize_operator_id(approver_id)
            normalized_initiator = self._normalize_operator_id(request.initiated_by)
            
            # INV-DUAL-002: Same identity cannot approve twice
            if request.first_approver:
                normalized_first = self._normalize_operator_id(request.first_approver)
                if normalized_approver == normalized_first:
                    self._audit(request, "DUPLICATE_APPROVER_REJECTED", approver_id)
                    return DualControlResult(
                        success=False,
                        request_id=request_id,
                        status=request.status,
                        message="INV-DUAL-002 VIOLATION: Same operator cannot provide both approvals",
                    )
            
            # Verify hardware token if provided
            token_verified = False
            if hardware_token_code:
                token_verified = self._token_sim.verify_code(approver_id, hardware_token_code)
                if not token_verified:
                    self._audit(request, "HARDWARE_TOKEN_FAILED", approver_id)
                    return DualControlResult(
                        success=False,
                        request_id=request_id,
                        status=request.status,
                        message="Hardware token verification failed",
                    )
            
            now = datetime.now(timezone.utc)
            
            # First approval
            if request.status == ApprovalStatus.PENDING:
                request.first_approver = approver_id
                request.first_approved_at = now
                request.first_approver_token_verified = token_verified
                request.status = ApprovalStatus.FIRST_APPROVED
                
                self._audit(request, "FIRST_APPROVAL", approver_id, {
                    "token_verified": token_verified,
                })
                
                return DualControlResult(
                    success=True,
                    request_id=request_id,
                    status=ApprovalStatus.FIRST_APPROVED,
                    message="First approval recorded. Awaiting second approver.",
                    approvers=[approver_id],
                    execution_authorized=False,
                )
            
            # Second approval
            elif request.status == ApprovalStatus.FIRST_APPROVED:
                request.second_approver = approver_id
                request.second_approved_at = now
                request.second_approver_token_verified = token_verified
                request.status = ApprovalStatus.FULLY_APPROVED
                
                self._audit(request, "SECOND_APPROVAL", approver_id, {
                    "token_verified": token_verified,
                })
                self._audit(request, "DUAL_CONTROL_SATISFIED", "system", {
                    "first_approver": request.first_approver,
                    "second_approver": request.second_approver,
                })
                
                # Move to completed
                self._pending_requests.pop(request_id)
                self._completed_requests.append(request)
                
                logger.info(
                    f"DUAL_CONTROL_SATISFIED: Request {request_id} for {request.action.value} "
                    f"approved by [{request.first_approver}, {request.second_approver}]"
                )
                
                return DualControlResult(
                    success=True,
                    request_id=request_id,
                    status=ApprovalStatus.FULLY_APPROVED,
                    message="Dual control satisfied. Action authorized.",
                    approvers=[request.first_approver, request.second_approver],
                    execution_authorized=True,
                )
            
            # Already fully approved
            return DualControlResult(
                success=False,
                request_id=request_id,
                status=request.status,
                message=f"Request already in status: {request.status.value}",
            )
    
    def reject(
        self,
        request_id: UUID,
        rejector_id: str,
        reason: str,
    ) -> DualControlResult:
        """
        Reject a dual control request.
        
        Args:
            request_id: The request to reject
            rejector_id: The operator rejecting
            reason: Reason for rejection
            
        Returns:
            Result of the rejection
        """
        with self._lock:
            if request_id not in self._pending_requests:
                return DualControlResult(
                    success=False,
                    request_id=request_id,
                    status=ApprovalStatus.EXPIRED,
                    message="Request not found or expired",
                )
            
            request = self._pending_requests.pop(request_id)
            request.status = ApprovalStatus.REJECTED
            request.rejection_reason = reason
            
            self._audit(request, "REQUEST_REJECTED", rejector_id, {"reason": reason})
            self._completed_requests.append(request)
            
            return DualControlResult(
                success=True,
                request_id=request_id,
                status=ApprovalStatus.REJECTED,
                message=f"Request rejected: {reason}",
            )
    
    def get_pending_requests(self, action: Optional[T4Action] = None) -> List[DualControlRequest]:
        """Get all pending dual control requests, optionally filtered by action."""
        with self._lock:
            self._cleanup_expired()
            
            if action:
                return [r for r in self._pending_requests.values() if r.action == action]
            return list(self._pending_requests.values())
    
    def get_request(self, request_id: UUID) -> Optional[DualControlRequest]:
        """Get a specific request by ID."""
        with self._lock:
            self._cleanup_expired()
            
            if request_id in self._pending_requests:
                return self._pending_requests[request_id]
            
            # Check completed
            for req in self._completed_requests:
                if req.request_id == request_id:
                    return req
            
            return None
    
    def requires_dual_control(self, action: str) -> bool:
        """Check if an action requires dual control."""
        try:
            T4Action(action)
            return True
        except ValueError:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dual control statistics."""
        with self._lock:
            pending_by_action = {}
            for req in self._pending_requests.values():
                pending_by_action[req.action.value] = pending_by_action.get(req.action.value, 0) + 1
            
            completed_by_status = {}
            for req in self._completed_requests[-100:]:  # Last 100
                completed_by_status[req.status.value] = completed_by_status.get(req.status.value, 0) + 1
            
            return {
                "pending_count": len(self._pending_requests),
                "pending_by_action": pending_by_action,
                "completed_by_status": completed_by_status,
                "total_completed": len(self._completed_requests),
            }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_dual_control_enforcer: Optional[DualControlEnforcer] = None
_enforcer_lock = threading.Lock()


def get_dual_control_enforcer() -> DualControlEnforcer:
    """Get the singleton dual control enforcer instance."""
    global _dual_control_enforcer
    
    if _dual_control_enforcer is None:
        with _enforcer_lock:
            if _dual_control_enforcer is None:
                _dual_control_enforcer = DualControlEnforcer()
    
    return _dual_control_enforcer


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATOR FOR T4 PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════


def require_dual_control(action: T4Action):
    """
    Decorator to require dual control for a function.
    
    The decorated function must accept `dual_control_result` as a keyword argument.
    It will only be called if dual control is satisfied.
    
    Usage:
        @require_dual_control(T4Action.KILL_SWITCH_ENGAGE)
        def engage_kill_switch(operator_id: str, dual_control_result: DualControlResult):
            # Only called if dual control is satisfied
            pass
    """
    def decorator(func):
        def wrapper(*args, dual_control_result: Optional[DualControlResult] = None, **kwargs):
            if dual_control_result is None:
                raise ValueError(
                    f"INV-DUAL-001 VIOLATION: {action.value} requires dual control. "
                    "Call approve() on a DualControlRequest first."
                )
            
            if not dual_control_result.execution_authorized:
                raise ValueError(
                    f"INV-DUAL-001 VIOLATION: {action.value} dual control not satisfied. "
                    f"Status: {dual_control_result.status.value}"
                )
            
            return func(*args, dual_control_result=dual_control_result, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator
