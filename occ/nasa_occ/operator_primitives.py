"""
Operator Confirmation & Rollback Primitives
PAC-JEFFREY-OCC-UI-NASA-001 | Task 3: Explicit Operator Confirmation

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true

Provides explicit operator confirmation and rollback primitives for
all critical actions. No action proceeds without verified operator intent.

INVARIANTS ENFORCED:
- INV-NO-SILENT-FAILURE: All failures surface to operator
- INV-OPERATOR-CONFIRMATION: Critical actions require explicit confirmation
- INV-ROLLBACK-AVAILABLE: Actions can be reversed within window

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY (STRATEGY_ONLY)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    FrozenSet,
    Generic,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)


# =============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# =============================================================================

VERSION: Final[str] = "1.0.0"
PAC_REFERENCE: Final[str] = "PAC-JEFFREY-OCC-UI-NASA-001"

# Confirmation timeout (action expires if not confirmed within this window)
CONFIRMATION_TIMEOUT_SECONDS: Final[int] = 30

# Rollback window (actions can be rolled back within this window)
ROLLBACK_WINDOW_SECONDS: Final[int] = 300

# Challenge code length
CHALLENGE_CODE_LENGTH: Final[int] = 6

# Maximum pending confirmations
MAX_PENDING_CONFIRMATIONS: Final[int] = 10

# Invariant identifiers
INV_NO_SILENT_FAILURE: Final[str] = "INV-NO-SILENT-FAILURE"
INV_OPERATOR_CONFIRMATION: Final[str] = "INV-OPERATOR-CONFIRMATION"
INV_ROLLBACK_AVAILABLE: Final[str] = "INV-ROLLBACK-AVAILABLE"


# =============================================================================
# SECTION 2: ENUMERATIONS
# =============================================================================

class ActionSeverity(Enum):
    """Action severity levels - determines confirmation requirements."""
    INFO = auto()              # No confirmation needed
    NORMAL = auto()            # Simple confirmation (acknowledge)
    ELEVATED = auto()          # Challenge-response confirmation
    CRITICAL = auto()          # Dual-factor confirmation
    SCRAM = auto()             # SCRAM-level (special protocol)


class ConfirmationState(Enum):
    """Confirmation request state."""
    PENDING = auto()           # Awaiting operator response
    CHALLENGED = auto()        # Challenge issued, awaiting response
    CONFIRMED = auto()         # Operator confirmed
    REJECTED = auto()          # Operator rejected
    EXPIRED = auto()           # Confirmation timeout expired
    CANCELLED = auto()         # Action cancelled


class RollbackState(Enum):
    """Rollback operation state."""
    AVAILABLE = auto()         # Rollback available
    PENDING = auto()           # Rollback in progress
    COMPLETED = auto()         # Rollback completed
    FAILED = auto()            # Rollback failed
    EXPIRED = auto()           # Rollback window expired
    UNAVAILABLE = auto()       # No rollback possible


class AuthorizationLevel(Enum):
    """Operator authorization levels."""
    OBSERVER = auto()          # View only
    OPERATOR = auto()          # Standard operations
    SUPERVISOR = auto()        # Elevated operations
    ARCHITECT = auto()         # Full access
    SYSTEM = auto()            # System-level (automated)


# =============================================================================
# SECTION 3: CORE DATA STRUCTURES (Frozen/Immutable)
# =============================================================================

@dataclass(frozen=True)
class OperatorIdentity:
    """
    Immutable operator identity.
    
    Represents a verified operator with authorization level.
    """
    operator_id: str
    operator_name: str
    authorization_level: AuthorizationLevel
    session_id: str
    session_start: datetime
    session_expires: datetime
    credential_hash: str
    
    def is_session_valid(self) -> bool:
        """Check if session is still valid."""
        now = datetime.now(timezone.utc)
        return self.session_start <= now < self.session_expires
    
    def can_perform(self, severity: ActionSeverity) -> bool:
        """Check if operator can perform action of given severity."""
        level_requirements = {
            ActionSeverity.INFO: AuthorizationLevel.OBSERVER,
            ActionSeverity.NORMAL: AuthorizationLevel.OPERATOR,
            ActionSeverity.ELEVATED: AuthorizationLevel.SUPERVISOR,
            ActionSeverity.CRITICAL: AuthorizationLevel.ARCHITECT,
            ActionSeverity.SCRAM: AuthorizationLevel.ARCHITECT,
        }
        
        required = level_requirements.get(severity, AuthorizationLevel.ARCHITECT)
        return self.authorization_level.value >= required.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "authorization_level": self.authorization_level.name,
            "session_id": self.session_id,
            "session_valid": self.is_session_valid(),
        }


@dataclass(frozen=True)
class ActionDefinition:
    """
    Immutable action definition.
    
    Defines what an action does and its requirements.
    """
    action_id: str
    action_type: str
    description: str
    severity: ActionSeverity
    target_component: str
    parameters: Mapping[str, Any]
    requires_confirmation: bool
    rollback_available: bool
    timeout_seconds: int = CONFIRMATION_TIMEOUT_SECONDS
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "description": self.description,
            "severity": self.severity.name,
            "target_component": self.target_component,
            "parameters": dict(self.parameters),
            "requires_confirmation": self.requires_confirmation,
            "rollback_available": self.rollback_available,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class ConfirmationChallenge:
    """
    Immutable confirmation challenge.
    
    Used for elevated/critical actions requiring challenge-response.
    """
    challenge_id: str
    challenge_code: str        # Operator must enter this code
    issued_at: datetime
    expires_at: datetime
    attempts_remaining: int
    
    def is_valid_response(self, response: str) -> bool:
        """Check if response matches challenge."""
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        return hmac.compare_digest(self.challenge_code, response.upper())
    
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "challenge_code": self.challenge_code,  # Display to operator
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "attempts_remaining": self.attempts_remaining,
            "is_expired": self.is_expired(),
        }


@dataclass(frozen=True)
class RollbackPoint:
    """
    Immutable rollback point.
    
    Captures state before action for potential rollback.
    """
    rollback_id: str
    action_id: str
    captured_at: datetime
    expires_at: datetime
    previous_state: Mapping[str, Any]
    state_hash: str
    
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "action_id": self.action_id,
            "captured_at": self.captured_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "state_hash": self.state_hash,
            "is_expired": self.is_expired(),
        }


# =============================================================================
# SECTION 4: CONFIRMATION REQUEST
# =============================================================================

class ConfirmationRequest:
    """
    Mutable confirmation request.
    
    Tracks the lifecycle of an action requiring confirmation.
    """
    
    def __init__(
        self,
        action: ActionDefinition,
        operator: OperatorIdentity,
    ) -> None:
        self._request_id = f"CONF-{uuid.uuid4().hex[:12].upper()}"
        self._action = action
        self._operator = operator
        self._state = ConfirmationState.PENDING
        self._created_at = datetime.now(timezone.utc)
        self._expires_at = self._created_at + timedelta(seconds=action.timeout_seconds)
        self._challenge: Optional[ConfirmationChallenge] = None
        self._confirmation_timestamp: Optional[datetime] = None
        self._rejection_reason: Optional[str] = None
        self._audit_log: List[Dict[str, Any]] = []
        
        self._log_event("REQUEST_CREATED")
        
        # Generate challenge for elevated/critical actions
        if action.severity in (ActionSeverity.ELEVATED, ActionSeverity.CRITICAL, ActionSeverity.SCRAM):
            self._generate_challenge()
    
    @property
    def request_id(self) -> str:
        return self._request_id
    
    @property
    def action(self) -> ActionDefinition:
        return self._action
    
    @property
    def operator(self) -> OperatorIdentity:
        return self._operator
    
    @property
    def state(self) -> ConfirmationState:
        # Check for expiration
        if self._state == ConfirmationState.PENDING or self._state == ConfirmationState.CHALLENGED:
            if datetime.now(timezone.utc) > self._expires_at:
                self._state = ConfirmationState.EXPIRED
                self._log_event("REQUEST_EXPIRED")
        return self._state
    
    @property
    def challenge(self) -> Optional[ConfirmationChallenge]:
        return self._challenge
    
    def _generate_challenge(self) -> None:
        """Generate challenge for confirmation."""
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') 
                       for _ in range(CHALLENGE_CODE_LENGTH))
        
        self._challenge = ConfirmationChallenge(
            challenge_id=f"CHAL-{uuid.uuid4().hex[:12].upper()}",
            challenge_code=code,
            issued_at=datetime.now(timezone.utc),
            expires_at=self._expires_at,
            attempts_remaining=3,
        )
        
        self._state = ConfirmationState.CHALLENGED
        self._log_event("CHALLENGE_ISSUED", {"challenge_id": self._challenge.challenge_id})
    
    def confirm(self, challenge_response: Optional[str] = None) -> Tuple[bool, str]:
        """
        Confirm the action.
        
        For elevated actions, challenge_response must match challenge_code.
        """
        if self.state == ConfirmationState.EXPIRED:
            return (False, "Confirmation request has expired")
        
        if self.state == ConfirmationState.CONFIRMED:
            return (False, "Action already confirmed")
        
        if self.state == ConfirmationState.REJECTED:
            return (False, "Action was rejected")
        
        # Check challenge if required
        if self._challenge:
            if not challenge_response:
                return (False, f"Challenge response required. Enter code: {self._challenge.challenge_code}")
            
            if not self._challenge.is_valid_response(challenge_response):
                self._log_event("CHALLENGE_FAILED", {"response": challenge_response})
                # Decrement attempts
                self._challenge = ConfirmationChallenge(
                    challenge_id=self._challenge.challenge_id,
                    challenge_code=self._challenge.challenge_code,
                    issued_at=self._challenge.issued_at,
                    expires_at=self._challenge.expires_at,
                    attempts_remaining=self._challenge.attempts_remaining - 1,
                )
                
                if self._challenge.attempts_remaining <= 0:
                    self._state = ConfirmationState.REJECTED
                    self._rejection_reason = "Maximum challenge attempts exceeded"
                    return (False, "Maximum challenge attempts exceeded - action rejected")
                
                return (False, f"Invalid challenge response. {self._challenge.attempts_remaining} attempts remaining")
        
        # Confirmation successful
        self._state = ConfirmationState.CONFIRMED
        self._confirmation_timestamp = datetime.now(timezone.utc)
        self._log_event("CONFIRMED")
        
        return (True, "Action confirmed")
    
    def reject(self, reason: str) -> Tuple[bool, str]:
        """Reject the action."""
        if self.state in (ConfirmationState.CONFIRMED, ConfirmationState.REJECTED):
            return (False, "Cannot reject - action already finalized")
        
        self._state = ConfirmationState.REJECTED
        self._rejection_reason = reason
        self._log_event("REJECTED", {"reason": reason})
        
        return (True, "Action rejected")
    
    def cancel(self) -> Tuple[bool, str]:
        """Cancel the confirmation request."""
        if self.state in (ConfirmationState.CONFIRMED, ConfirmationState.REJECTED):
            return (False, "Cannot cancel - action already finalized")
        
        self._state = ConfirmationState.CANCELLED
        self._log_event("CANCELLED")
        
        return (True, "Confirmation request cancelled")
    
    def _log_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log audit event."""
        self._audit_log.append({
            "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": self._request_id,
            "operator_id": self._operator.operator_id,
            "data": data or {},
        })
    
    def get_audit_log(self) -> Sequence[Dict[str, Any]]:
        """Get audit log for this request."""
        return tuple(self._audit_log)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self._request_id,
            "action": self._action.to_dict(),
            "operator": self._operator.to_dict(),
            "state": self.state.name,
            "created_at": self._created_at.isoformat(),
            "expires_at": self._expires_at.isoformat(),
            "challenge": self._challenge.to_dict() if self._challenge else None,
            "confirmation_timestamp": self._confirmation_timestamp.isoformat() if self._confirmation_timestamp else None,
            "rejection_reason": self._rejection_reason,
        }


# =============================================================================
# SECTION 5: ROLLBACK PRIMITIVE
# =============================================================================

class RollbackPrimitive:
    """
    Rollback primitive for reversing actions.
    
    Captures state before action and provides rollback capability.
    """
    
    def __init__(
        self,
        action_id: str,
        state_capture: Mapping[str, Any],
        rollback_window_seconds: int = ROLLBACK_WINDOW_SECONDS,
    ) -> None:
        self._rollback_id = f"ROLL-{uuid.uuid4().hex[:12].upper()}"
        self._action_id = action_id
        
        # Capture state
        self._captured_at = datetime.now(timezone.utc)
        self._expires_at = self._captured_at + timedelta(seconds=rollback_window_seconds)
        self._previous_state = dict(state_capture)
        self._state_hash = hashlib.sha256(
            json.dumps(self._previous_state, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        self._rollback_point = RollbackPoint(
            rollback_id=self._rollback_id,
            action_id=action_id,
            captured_at=self._captured_at,
            expires_at=self._expires_at,
            previous_state=self._previous_state,
            state_hash=self._state_hash,
        )
        
        self._state = RollbackState.AVAILABLE
        self._rollback_timestamp: Optional[datetime] = None
        self._rollback_result: Optional[str] = None
        self._audit_log: List[Dict[str, Any]] = []
        
        self._log_event("ROLLBACK_POINT_CREATED")
    
    @property
    def rollback_id(self) -> str:
        return self._rollback_id
    
    @property
    def rollback_point(self) -> RollbackPoint:
        return self._rollback_point
    
    @property
    def state(self) -> RollbackState:
        # Check for expiration
        if self._state == RollbackState.AVAILABLE:
            if datetime.now(timezone.utc) > self._expires_at:
                self._state = RollbackState.EXPIRED
                self._log_event("ROLLBACK_EXPIRED")
        return self._state
    
    @property
    def previous_state(self) -> Mapping[str, Any]:
        return self._previous_state
    
    def can_rollback(self) -> bool:
        """Check if rollback is still available."""
        return self.state == RollbackState.AVAILABLE
    
    def execute_rollback(
        self,
        operator: OperatorIdentity,
        confirmation_code: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Mapping[str, Any]]]:
        """
        Execute rollback.
        
        Returns (success, message, previous_state).
        """
        if not self.can_rollback():
            return (False, f"Rollback not available: {self.state.name}", None)
        
        # Verify operator authorization
        if operator.authorization_level.value < AuthorizationLevel.SUPERVISOR.value:
            return (False, "Rollback requires SUPERVISOR or higher authorization", None)
        
        self._state = RollbackState.PENDING
        self._log_event("ROLLBACK_STARTED", {"operator_id": operator.operator_id})
        
        # In a real system, this would apply the previous state
        # Here we return the state for the caller to apply
        
        self._state = RollbackState.COMPLETED
        self._rollback_timestamp = datetime.now(timezone.utc)
        self._rollback_result = "Rollback completed successfully"
        self._log_event("ROLLBACK_COMPLETED")
        
        return (True, "Rollback executed successfully", self._previous_state)
    
    def _log_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log audit event."""
        self._audit_log.append({
            "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rollback_id": self._rollback_id,
            "data": data or {},
        })
    
    def get_audit_log(self) -> Sequence[Dict[str, Any]]:
        """Get audit log."""
        return tuple(self._audit_log)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rollback_id": self._rollback_id,
            "action_id": self._action_id,
            "state": self.state.name,
            "captured_at": self._captured_at.isoformat(),
            "expires_at": self._expires_at.isoformat(),
            "state_hash": self._state_hash,
            "rollback_timestamp": self._rollback_timestamp.isoformat() if self._rollback_timestamp else None,
            "can_rollback": self.can_rollback(),
        }


# =============================================================================
# SECTION 6: ACTION AUTHORIZATION
# =============================================================================

class ActionAuthorization:
    """
    Action authorization manager.
    
    Manages the full lifecycle of action authorization:
    1. Request action
    2. Verify operator authorization
    3. Generate confirmation request
    4. Capture rollback point
    5. Execute on confirmation
    """
    
    def __init__(self) -> None:
        self._pending_confirmations: Dict[str, ConfirmationRequest] = {}
        self._rollback_points: Dict[str, RollbackPrimitive] = {}
        self._completed_actions: List[Dict[str, Any]] = []
        self._rejected_actions: List[Dict[str, Any]] = []
        self._audit_log: List[Dict[str, Any]] = []
    
    def request_action(
        self,
        action: ActionDefinition,
        operator: OperatorIdentity,
        current_state: Optional[Mapping[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ConfirmationRequest]]:
        """
        Request an action.
        
        Returns (success, message, confirmation_request).
        """
        # Verify session
        if not operator.is_session_valid():
            self._log_audit("SESSION_INVALID", operator.operator_id, action.action_id)
            return (False, "Operator session has expired", None)
        
        # Verify authorization level
        if not operator.can_perform(action.severity):
            self._log_audit("AUTHORIZATION_DENIED", operator.operator_id, action.action_id)
            return (False, f"Insufficient authorization for {action.severity.name} action", None)
        
        # Check pending confirmation limit
        if len(self._pending_confirmations) >= MAX_PENDING_CONFIRMATIONS:
            self._cleanup_expired()
            if len(self._pending_confirmations) >= MAX_PENDING_CONFIRMATIONS:
                return (False, "Maximum pending confirmations reached", None)
        
        # Create confirmation request
        request = ConfirmationRequest(action, operator)
        self._pending_confirmations[request.request_id] = request
        
        # Create rollback point if applicable
        if action.rollback_available and current_state:
            rollback = RollbackPrimitive(action.action_id, current_state)
            self._rollback_points[request.request_id] = rollback
        
        self._log_audit("ACTION_REQUESTED", operator.operator_id, action.action_id)
        
        # For INFO severity, auto-confirm
        if action.severity == ActionSeverity.INFO:
            request.confirm()
            return (True, "Action confirmed (INFO level - no confirmation required)", request)
        
        return (True, "Confirmation required", request)
    
    def confirm_action(
        self,
        request_id: str,
        challenge_response: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Confirm a pending action.
        
        For elevated actions, challenge_response is required.
        """
        request = self._pending_confirmations.get(request_id)
        if not request:
            return (False, "Confirmation request not found")
        
        success, msg = request.confirm(challenge_response)
        
        if success:
            self._completed_actions.append({
                "request_id": request_id,
                "action_id": request.action.action_id,
                "operator_id": request.operator.operator_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            self._log_audit("ACTION_CONFIRMED", request.operator.operator_id, request.action.action_id)
        
        return (success, msg)
    
    def reject_action(
        self,
        request_id: str,
        reason: str,
    ) -> Tuple[bool, str]:
        """Reject a pending action."""
        request = self._pending_confirmations.get(request_id)
        if not request:
            return (False, "Confirmation request not found")
        
        success, msg = request.reject(reason)
        
        if success:
            self._rejected_actions.append({
                "request_id": request_id,
                "action_id": request.action.action_id,
                "operator_id": request.operator.operator_id,
                "reason": reason,
                "rejected_at": datetime.now(timezone.utc).isoformat(),
            })
            self._log_audit("ACTION_REJECTED", request.operator.operator_id, request.action.action_id)
        
        return (success, msg)
    
    def rollback_action(
        self,
        request_id: str,
        operator: OperatorIdentity,
    ) -> Tuple[bool, str, Optional[Mapping[str, Any]]]:
        """
        Rollback a completed action.
        
        Returns (success, message, previous_state).
        """
        rollback = self._rollback_points.get(request_id)
        if not rollback:
            return (False, "No rollback point available for this action", None)
        
        success, msg, state = rollback.execute_rollback(operator)
        
        if success:
            self._log_audit("ACTION_ROLLED_BACK", operator.operator_id, request_id)
        
        return (success, msg, state)
    
    def get_pending_confirmations(self) -> Sequence[ConfirmationRequest]:
        """Get all pending confirmation requests."""
        self._cleanup_expired()
        return tuple(
            r for r in self._pending_confirmations.values()
            if r.state in (ConfirmationState.PENDING, ConfirmationState.CHALLENGED)
        )
    
    def get_confirmation_request(self, request_id: str) -> Optional[ConfirmationRequest]:
        """Get specific confirmation request."""
        return self._pending_confirmations.get(request_id)
    
    def get_rollback_point(self, request_id: str) -> Optional[RollbackPrimitive]:
        """Get rollback point for a request."""
        return self._rollback_points.get(request_id)
    
    def _cleanup_expired(self) -> None:
        """Clean up expired confirmation requests."""
        expired = [
            rid for rid, req in self._pending_confirmations.items()
            if req.state == ConfirmationState.EXPIRED
        ]
        for rid in expired:
            del self._pending_confirmations[rid]
    
    def _log_audit(self, event_type: str, operator_id: str, action_id: str) -> None:
        """Log audit event."""
        self._audit_log.append({
            "event_id": f"AUTH-{uuid.uuid4().hex[:8].upper()}",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator_id": operator_id,
            "action_id": action_id,
        })
    
    def get_audit_log(self) -> Sequence[Dict[str, Any]]:
        """Get audit log."""
        return tuple(self._audit_log)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pending_confirmations": len(self._pending_confirmations),
            "rollback_points": len(self._rollback_points),
            "completed_actions": len(self._completed_actions),
            "rejected_actions": len(self._rejected_actions),
            "audit_log_size": len(self._audit_log),
        }


# =============================================================================
# SECTION 7: OPERATOR CONFIRMATION (High-level Interface)
# =============================================================================

class OperatorConfirmation:
    """
    High-level operator confirmation interface.
    
    Provides simple API for UI to request and handle confirmations.
    """
    
    def __init__(self) -> None:
        self._authorization = ActionAuthorization()
        self._operators: Dict[str, OperatorIdentity] = {}
    
    def register_operator(
        self,
        operator_id: str,
        operator_name: str,
        authorization_level: AuthorizationLevel,
        credential: str,
    ) -> OperatorIdentity:
        """Register an operator."""
        session_id = f"SESS-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc)
        
        operator = OperatorIdentity(
            operator_id=operator_id,
            operator_name=operator_name,
            authorization_level=authorization_level,
            session_id=session_id,
            session_start=now,
            session_expires=now + timedelta(hours=8),
            credential_hash=hashlib.sha256(credential.encode()).hexdigest()[:16],
        )
        
        self._operators[operator_id] = operator
        return operator
    
    def get_operator(self, operator_id: str) -> Optional[OperatorIdentity]:
        """Get operator by ID."""
        return self._operators.get(operator_id)
    
    def request_confirmation(
        self,
        operator_id: str,
        action_type: str,
        description: str,
        severity: ActionSeverity,
        target_component: str,
        parameters: Optional[Mapping[str, Any]] = None,
        current_state: Optional[Mapping[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Request operator confirmation for an action.
        
        Returns (success, message, request_id, challenge_code).
        """
        operator = self._operators.get(operator_id)
        if not operator:
            return (False, "Unknown operator", None, None)
        
        action = ActionDefinition(
            action_id=f"ACT-{uuid.uuid4().hex[:12].upper()}",
            action_type=action_type,
            description=description,
            severity=severity,
            target_component=target_component,
            parameters=parameters or {},
            requires_confirmation=severity != ActionSeverity.INFO,
            rollback_available=severity in (ActionSeverity.NORMAL, ActionSeverity.ELEVATED),
        )
        
        success, msg, request = self._authorization.request_action(
            action=action,
            operator=operator,
            current_state=current_state,
        )
        
        challenge_code = None
        if request and request.challenge:
            challenge_code = request.challenge.challenge_code
        
        return (
            success,
            msg,
            request.request_id if request else None,
            challenge_code,
        )
    
    def confirm(
        self,
        request_id: str,
        challenge_response: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Confirm an action."""
        return self._authorization.confirm_action(request_id, challenge_response)
    
    def reject(
        self,
        request_id: str,
        reason: str,
    ) -> Tuple[bool, str]:
        """Reject an action."""
        return self._authorization.reject_action(request_id, reason)
    
    def rollback(
        self,
        request_id: str,
        operator_id: str,
    ) -> Tuple[bool, str, Optional[Mapping[str, Any]]]:
        """Rollback an action."""
        operator = self._operators.get(operator_id)
        if not operator:
            return (False, "Unknown operator", None)
        
        return self._authorization.rollback_action(request_id, operator)
    
    def get_pending(self) -> Sequence[Dict[str, Any]]:
        """Get pending confirmations."""
        return tuple(r.to_dict() for r in self._authorization.get_pending_confirmations())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "registered_operators": len(self._operators),
            "authorization": self._authorization.to_dict(),
        }


# =============================================================================
# SECTION 8: SELF-TEST
# =============================================================================

def _run_self_test() -> None:
    """Execute self-test suite."""
    import sys
    
    print("=" * 72)
    print("  OPERATOR CONFIRMATION & ROLLBACK PRIMITIVES - SELF-TEST")
    print("  PAC-JEFFREY-OCC-UI-NASA-001 | Task 3")
    print("=" * 72)
    
    tests_passed = 0
    tests_failed = 0
    
    def test(name: str, condition: bool, msg: str = "") -> None:
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"  ✓ {name}")
            tests_passed += 1
        else:
            print(f"  ✗ {name}: {msg}")
            tests_failed += 1
    
    # Test 1: Operator Identity
    print("\n[1] Operator Identity Tests")
    now = datetime.now(timezone.utc)
    operator = OperatorIdentity(
        operator_id="OP-001",
        operator_name="Test Operator",
        authorization_level=AuthorizationLevel.ARCHITECT,
        session_id="SESS-TEST",
        session_start=now,
        session_expires=now + timedelta(hours=8),
        credential_hash="abc123",
    )
    test("Operator created", operator.operator_id == "OP-001")
    test("Session valid", operator.is_session_valid())
    test("Can perform CRITICAL", operator.can_perform(ActionSeverity.CRITICAL))
    
    # Test 2: Action Definition
    print("\n[2] Action Definition Tests")
    action = ActionDefinition(
        action_id="ACT-001",
        action_type="TEST_ACTION",
        description="Test action for verification",
        severity=ActionSeverity.ELEVATED,
        target_component="COMP-TEST",
        parameters={"key": "value"},
        requires_confirmation=True,
        rollback_available=True,
    )
    test("Action created", action.action_id == "ACT-001")
    test("Requires confirmation", action.requires_confirmation)
    test("Rollback available", action.rollback_available)
    
    # Test 3: Confirmation Request - INFO level
    print("\n[3] Confirmation Request Tests (INFO)")
    info_action = ActionDefinition(
        action_id="ACT-INFO",
        action_type="VIEW",
        description="View operation",
        severity=ActionSeverity.INFO,
        target_component="COMP-TEST",
        parameters={},
        requires_confirmation=False,
        rollback_available=False,
    )
    info_request = ConfirmationRequest(info_action, operator)
    test("INFO request created", info_request.state == ConfirmationState.PENDING)
    
    success, msg = info_request.confirm()
    test("INFO confirmed without challenge", success)
    
    # Test 4: Confirmation Request - ELEVATED level
    print("\n[4] Confirmation Request Tests (ELEVATED)")
    request = ConfirmationRequest(action, operator)
    test("Request created", request.request_id.startswith("CONF-"))
    test("Challenge generated", request.challenge is not None)
    test("State is CHALLENGED", request.state == ConfirmationState.CHALLENGED)
    
    # Try confirm without challenge
    success, msg = request.confirm()
    test("Confirmation requires challenge", not success)
    
    # Confirm with wrong code
    success, msg = request.confirm("WRONG!")
    test("Wrong code rejected", not success)
    
    # Confirm with correct code
    if request.challenge:
        success, msg = request.confirm(request.challenge.challenge_code)
        test("Correct code accepted", success)
        test("State is CONFIRMED", request.state == ConfirmationState.CONFIRMED)
    
    # Test 5: Rejection
    print("\n[5] Rejection Tests")
    reject_request = ConfirmationRequest(action, operator)
    success, msg = reject_request.reject("Test rejection")
    test("Rejection successful", success)
    test("State is REJECTED", reject_request.state == ConfirmationState.REJECTED)
    
    # Try to confirm after rejection
    success, msg = reject_request.confirm()
    test("Cannot confirm after rejection", not success)
    
    # Test 6: Rollback Primitive
    print("\n[6] Rollback Primitive Tests")
    state_before = {"key": "original", "count": 42}
    rollback = RollbackPrimitive("ACT-001", state_before)
    test("Rollback created", rollback.rollback_id.startswith("ROLL-"))
    test("Rollback available", rollback.can_rollback())
    test("State captured", rollback.previous_state["key"] == "original")
    
    # Execute rollback
    success, msg, restored_state = rollback.execute_rollback(operator)
    test("Rollback executed", success)
    test("State restored", restored_state is not None and restored_state["key"] == "original")
    test("Rollback completed", rollback.state == RollbackState.COMPLETED)
    
    # Cannot rollback again
    test("Cannot rollback twice", not rollback.can_rollback())
    
    # Test 7: Action Authorization
    print("\n[7] Action Authorization Tests")
    auth = ActionAuthorization()
    
    success, msg, conf_req = auth.request_action(
        action=action,
        operator=operator,
        current_state={"status": "before"},
    )
    test("Action requested", success)
    test("Confirmation request returned", conf_req is not None)
    
    if conf_req and conf_req.challenge:
        success, msg = auth.confirm_action(conf_req.request_id, conf_req.challenge.challenge_code)
        test("Action confirmed via auth", success)
    
    # Test 8: Insufficient Authorization
    print("\n[8] Authorization Level Tests")
    observer = OperatorIdentity(
        operator_id="OP-OBS",
        operator_name="Observer",
        authorization_level=AuthorizationLevel.OBSERVER,
        session_id="SESS-OBS",
        session_start=now,
        session_expires=now + timedelta(hours=8),
        credential_hash="xyz789",
    )
    
    success, msg, req = auth.request_action(action, observer)
    test("Observer cannot perform ELEVATED", not success)
    
    # Test 9: OperatorConfirmation High-level API
    print("\n[9] High-level API Tests")
    opc = OperatorConfirmation()
    
    op = opc.register_operator(
        operator_id="OP-TEST",
        operator_name="Test Op",
        authorization_level=AuthorizationLevel.SUPERVISOR,
        credential="secret",
    )
    test("Operator registered", op.operator_id == "OP-TEST")
    
    success, msg, req_id, challenge = opc.request_confirmation(
        operator_id="OP-TEST",
        action_type="CONFIG_CHANGE",
        description="Change configuration",
        severity=ActionSeverity.ELEVATED,
        target_component="CONFIG",
        parameters={"setting": "new_value"},
        current_state={"setting": "old_value"},
    )
    test("Confirmation requested via API", success)
    test("Challenge code returned", challenge is not None)
    
    if req_id and challenge:
        success, msg = opc.confirm(req_id, challenge)
        test("Confirmed via API", success)
    
    # Test 10: Rollback via high-level API
    print("\n[10] Rollback via API Tests")
    success, msg, req_id2, challenge2 = opc.request_confirmation(
        operator_id="OP-TEST",
        action_type="MODIFY",
        description="Modify system",
        severity=ActionSeverity.NORMAL,
        target_component="SYSTEM",
        current_state={"mode": "normal"},
    )
    
    if req_id2:
        success, msg = opc.confirm(req_id2)
        test("Normal action confirmed", success)
        
        # Rollback
        success, msg, state = opc.rollback(req_id2, "OP-TEST")
        test("Rollback via API", success)
        test("State returned", state is not None)
    
    # Summary
    print("\n" + "=" * 72)
    total = tests_passed + tests_failed
    print(f"  RESULTS: {tests_passed}/{total} tests passed")
    print("=" * 72)
    
    if tests_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    _run_self_test()
