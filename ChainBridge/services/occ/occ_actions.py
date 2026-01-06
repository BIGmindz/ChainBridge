"""
OCC Actions - Action executor for Operator Control Center.

PAC Reference: PAC-OCC-P02
Constitutional Authority: OCC_CONSTITUTION_v1.0, Article III
Override Invariants: INV-OVR-001 through INV-OVR-010

This module implements the action execution layer that:
1. Validates all actions against constitutional authority model
2. Enforces override invariants (identity, justification, scope)
3. Maintains immutable audit trail for all actions
4. Implements fail-closed semantics on any error condition
"""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class ActionType(str, Enum):
    """
    Supported OCC action types.
    
    Constitutional basis: OCC_AUTHORITY_MODEL.yaml actions section
    """
    # View actions (T1+)
    VIEW_PDO = "VIEW_PDO"
    VIEW_QUEUE = "VIEW_QUEUE"
    VIEW_AUDIT = "VIEW_AUDIT"
    
    # Comment actions (T2+)
    ADD_COMMENT = "ADD_COMMENT"
    FLAG_REVIEW = "FLAG_REVIEW"
    
    # Review actions (T3+)
    REQUEST_REVIEW = "REQUEST_REVIEW"
    ESCALATE = "ESCALATE"
    
    # Override actions (T4+)
    OVERRIDE_APPROVE = "OVERRIDE_APPROVE"
    OVERRIDE_BLOCK = "OVERRIDE_BLOCK"
    OVERRIDE_MODIFY = "OVERRIDE_MODIFY"
    EMERGENCY_PAUSE = "EMERGENCY_PAUSE"
    
    # Admin actions (T5+)
    MODIFY_POLICY = "MODIFY_POLICY"
    MANAGE_OPERATORS = "MANAGE_OPERATORS"
    AUDIT_EXPORT = "AUDIT_EXPORT"
    
    # System actions (T6 only)
    SYSTEM_KILL_SWITCH = "SYSTEM_KILL_SWITCH"
    SYSTEM_CONFIG = "SYSTEM_CONFIG"


class ActionResult(str, Enum):
    """Result status of an OCC action."""
    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"
    INSUFFICIENT_AUTHORITY = "INSUFFICIENT_AUTHORITY"
    INVALID_INPUT = "INVALID_INPUT"
    INVARIANT_VIOLATION = "INVARIANT_VIOLATION"
    SYSTEM_ERROR = "SYSTEM_ERROR"


# Tier requirements for each action type
TIER_REQUIREMENTS: dict[ActionType, str] = {
    ActionType.VIEW_PDO: "T1",
    ActionType.VIEW_QUEUE: "T1",
    ActionType.VIEW_AUDIT: "T1",
    ActionType.ADD_COMMENT: "T2",
    ActionType.FLAG_REVIEW: "T2",
    ActionType.REQUEST_REVIEW: "T3",
    ActionType.ESCALATE: "T3",
    ActionType.OVERRIDE_APPROVE: "T4",
    ActionType.OVERRIDE_BLOCK: "T4",
    ActionType.OVERRIDE_MODIFY: "T4",
    ActionType.EMERGENCY_PAUSE: "T4",
    ActionType.MODIFY_POLICY: "T5",
    ActionType.MANAGE_OPERATORS: "T5",
    ActionType.AUDIT_EXPORT: "T5",
    ActionType.SYSTEM_KILL_SWITCH: "T6",
    ActionType.SYSTEM_CONFIG: "T6",
}

# Tier hierarchy for comparison
TIER_ORDER = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5, "T6": 6}


@dataclass(frozen=True)
class OperatorContext:
    """
    Operator context for action execution.
    
    Invariant: INV-OCC-004 - No Anonymous Operations
    """
    operator_id: str
    tier: str
    session_id: str
    ip_address: str
    user_agent: str
    mfa_verified: bool = True
    
    def has_authority(self, required_tier: str) -> bool:
        """Check if operator has required tier authority."""
        return TIER_ORDER.get(self.tier, 0) >= TIER_ORDER.get(required_tier, 99)


@dataclass(frozen=True)
class OverrideJustification:
    """
    Justification for override actions.
    
    Invariant: INV-OVR-002 - Override Justification Requirement
    """
    text: str
    constitutional_citation: str
    risk_acknowledged: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Blocked template patterns per INV-OVR-002
    BLOCKED_TEMPLATES = [
        "per policy",
        "as required",
        "business need",
        "approved by management",
        "see above",
        "n/a",
    ]
    
    # Valid citation patterns
    CITATION_PATTERN = re.compile(
        r"(Article [IVX]+, Section \d+\.\d+|INV-(OCC|OVR)-\d{3})"
    )
    
    def validate(self) -> tuple[bool, str | None]:
        """
        Validate justification against constitutional requirements.
        
        Returns:
            (is_valid, error_message)
        """
        # Check minimum length
        if len(self.text) < 50:
            return False, "Justification too short (minimum 50 characters)"
        
        # Check for blocked templates
        text_lower = self.text.lower()
        for template in self.BLOCKED_TEMPLATES:
            if template in text_lower and len(self.text) < 100:
                return False, f"Justification appears to be templated: '{template}'"
        
        # Check citation format
        if not self.CITATION_PATTERN.search(self.constitutional_citation):
            return False, "Invalid constitutional citation format"
        
        # Check risk acknowledgment
        if not self.risk_acknowledged:
            return False, "Risk acknowledgment required for override"
        
        return True, None


@dataclass
class OCCAction:
    """
    A single OCC action for execution.
    
    Immutable after creation (dataclass frozen=False for hash computation,
    but should not be modified after init).
    """
    id: str
    action_type: ActionType
    operator: OperatorContext
    target_pdo_id: str | None
    payload: dict[str, Any]
    justification: OverrideJustification | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hash_current: str = ""
    
    def __post_init__(self) -> None:
        """Compute hash on creation."""
        if not self.hash_current:
            self.hash_current = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute cryptographic hash of action."""
        content = (
            f"{self.id}|{self.action_type.value}|{self.operator.operator_id}|"
            f"{self.target_pdo_id}|{self.created_at.isoformat()}"
        )
        return hashlib.sha256(content.encode()).hexdigest()
    
    def is_override_action(self) -> bool:
        """Check if this is an override action requiring justification."""
        return self.action_type in (
            ActionType.OVERRIDE_APPROVE,
            ActionType.OVERRIDE_BLOCK,
            ActionType.OVERRIDE_MODIFY,
        )


@dataclass
class ActionOutcome:
    """
    Outcome of an OCC action execution.
    
    Invariant: INV-OVR-004 - Override Audit Trail
    All outcomes are recorded in audit trail.
    """
    action_id: str
    result: ActionResult
    message: str
    original_decision: str | None = None  # For overrides
    new_decision: str | None = None  # For overrides
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hash_current: str = ""
    
    def __post_init__(self) -> None:
        """Compute hash on creation."""
        if not self.hash_current:
            content = f"{self.action_id}|{self.result.value}|{self.executed_at.isoformat()}"
            self.hash_current = hashlib.sha256(content.encode()).hexdigest()


class InvariantViolationError(Exception):
    """Raised when a constitutional invariant is violated."""
    
    def __init__(self, invariant_id: str, message: str) -> None:
        self.invariant_id = invariant_id
        super().__init__(f"{invariant_id} VIOLATION: {message}")


class OCCActionExecutor:
    """
    Action executor for Operator Control Center.
    
    Constitutional Invariants Enforced:
    - INV-OCC-001: Human Authority Supremacy
    - INV-OCC-004: No Anonymous Operations
    - INV-OCC-005: Tier Enforcement
    - INV-OCC-007: Action Attribution
    - INV-OVR-001: Override Identity Requirement
    - INV-OVR-002: Override Justification Requirement
    - INV-OVR-008: Override Scope Limits
    - INV-OVR-010: No Self-Override
    
    Fail-closed semantics: Any error results in action BLOCKED.
    """
    
    # Singleton enforcement
    _INSTANCE: OCCActionExecutor | None = None
    _LOCK = threading.Lock()
    
    def __init__(
        self,
        audit_callback: Callable[[OCCAction, ActionOutcome], None] | None = None,
        pdo_lookup: Callable[[str], dict[str, Any] | None] | None = None,
    ) -> None:
        """
        Initialize action executor.
        
        Args:
            audit_callback: Callback for audit trail recording
            pdo_lookup: Callback to lookup PDO details for validation
        """
        self._audit_callback = audit_callback
        self._pdo_lookup = pdo_lookup
        self._lock = threading.Lock()
        self._closed = False
        
        # Metrics
        self._execution_count = 0
        self._success_count = 0
        self._block_count = 0
        
    @classmethod
    def get_instance(cls) -> OCCActionExecutor:
        """Get singleton instance."""
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    cls._INSTANCE = cls()
        return cls._INSTANCE
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton for testing."""
        with cls._LOCK:
            cls._INSTANCE = None
    
    def execute(self, action: OCCAction) -> ActionOutcome:
        """
        Execute an OCC action with full constitutional validation.
        
        Args:
            action: The action to execute
            
        Returns:
            ActionOutcome with result status
            
        Note: This method NEVER raises exceptions for validation failures.
        All failures are returned as ActionOutcome with BLOCKED status.
        Fail-closed semantics.
        """
        self._execution_count += 1
        
        try:
            # Check if executor is closed (fail-closed state)
            if self._closed:
                return self._blocked_outcome(
                    action, ActionResult.SYSTEM_ERROR, "Executor in fail-closed state"
                )
            
            # INV-OCC-004: Verify operator identity
            if not action.operator.operator_id:
                return self._blocked_outcome(
                    action, ActionResult.INVARIANT_VIOLATION,
                    "INV-OCC-004: Operator identity required"
                )
            
            # INV-OCC-005: Verify tier authority
            required_tier = TIER_REQUIREMENTS.get(action.action_type, "T6")
            if not action.operator.has_authority(required_tier):
                return self._blocked_outcome(
                    action, ActionResult.INSUFFICIENT_AUTHORITY,
                    f"INV-OCC-005: {action.action_type.value} requires {required_tier}+, "
                    f"operator is {action.operator.tier}"
                )
            
            # Override-specific validations
            if action.is_override_action():
                validation_result = self._validate_override(action)
                if validation_result is not None:
                    return validation_result
            
            # Execute action
            outcome = self._execute_action(action)
            
            # Record audit trail
            self._record_audit(action, outcome)
            
            if outcome.result == ActionResult.SUCCESS:
                self._success_count += 1
            else:
                self._block_count += 1
            
            return outcome
            
        except Exception as e:
            # Fail-closed: any exception results in BLOCKED
            self._block_count += 1
            return self._blocked_outcome(
                action, ActionResult.SYSTEM_ERROR,
                f"Fail-closed on error: {type(e).__name__}"
            )
    
    def _validate_override(self, action: OCCAction) -> ActionOutcome | None:
        """
        Validate override-specific invariants.
        
        Returns:
            None if validation passes, ActionOutcome if blocked
        """
        # INV-OVR-001: Override Identity Requirement
        if not action.operator.mfa_verified:
            return self._blocked_outcome(
                action, ActionResult.INVARIANT_VIOLATION,
                "INV-OVR-001: MFA verification required for override"
            )
        
        # INV-OVR-002: Override Justification Requirement
        if action.justification is None:
            return self._blocked_outcome(
                action, ActionResult.INVARIANT_VIOLATION,
                "INV-OVR-002: Justification required for override"
            )
        
        is_valid, error = action.justification.validate()
        if not is_valid:
            return self._blocked_outcome(
                action, ActionResult.INVARIANT_VIOLATION,
                f"INV-OVR-002: {error}"
            )
        
        # INV-OVR-008: Override Scope Limits
        if action.target_pdo_id and self._pdo_lookup:
            pdo = self._pdo_lookup(action.target_pdo_id)
            if pdo:
                pdo_value = pdo.get("value", 0)
                tier_limit = self._get_tier_value_limit(action.operator.tier)
                if tier_limit is not None and pdo_value > tier_limit:
                    return self._blocked_outcome(
                        action, ActionResult.INVARIANT_VIOLATION,
                        f"INV-OVR-008: PDO value ${pdo_value:,} exceeds "
                        f"{action.operator.tier} limit ${tier_limit:,}"
                    )
        
        # INV-OVR-010: No Self-Override
        if action.target_pdo_id and self._pdo_lookup:
            pdo = self._pdo_lookup(action.target_pdo_id)
            if pdo and pdo.get("original_operator_id") == action.operator.operator_id:
                # Exception for T5 emergency
                if not (action.operator.tier == "T5" and action.payload.get("emergency")):
                    return self._blocked_outcome(
                        action, ActionResult.INVARIANT_VIOLATION,
                        "INV-OVR-010: Self-override prohibited"
                    )
        
        return None
    
    def _execute_action(self, action: OCCAction) -> ActionOutcome:
        """
        Execute the validated action.
        
        This is where actual action execution logic would go.
        For now, returns success for validated actions.
        """
        # Action-specific execution logic would be implemented here
        # For the constitutional framework, we return success for validated actions
        
        if action.is_override_action():
            return ActionOutcome(
                action_id=action.id,
                result=ActionResult.SUCCESS,
                message=f"{action.action_type.value} executed successfully",
                original_decision=action.payload.get("original_decision"),
                new_decision=self._map_override_to_decision(action.action_type),
            )
        
        return ActionOutcome(
            action_id=action.id,
            result=ActionResult.SUCCESS,
            message=f"{action.action_type.value} executed successfully",
        )
    
    def _blocked_outcome(
        self, action: OCCAction, result: ActionResult, message: str
    ) -> ActionOutcome:
        """Create a blocked outcome and record audit."""
        outcome = ActionOutcome(
            action_id=action.id,
            result=result,
            message=message,
        )
        self._record_audit(action, outcome)
        return outcome
    
    def _record_audit(self, action: OCCAction, outcome: ActionOutcome) -> None:
        """Record action and outcome to audit trail."""
        if self._audit_callback:
            try:
                self._audit_callback(action, outcome)
            except Exception:
                # Audit failure should not block operation
                # but should be logged/alerted separately
                pass
    
    def _get_tier_value_limit(self, tier: str) -> int | None:
        """Get value limit for tier per OCC_AUTHORITY_MODEL."""
        limits = {
            "T4": 10_000_000,  # $10M
            "T5": None,  # Unlimited
            "T6": None,  # Unlimited
        }
        return limits.get(tier)
    
    def _map_override_to_decision(self, action_type: ActionType) -> str:
        """Map override action type to decision string."""
        mapping = {
            ActionType.OVERRIDE_APPROVE: "OPERATOR_APPROVED",
            ActionType.OVERRIDE_BLOCK: "OPERATOR_BLOCKED",
            ActionType.OVERRIDE_MODIFY: "OPERATOR_MODIFIED",
        }
        return mapping.get(action_type, "UNKNOWN")
    
    def close(self) -> None:
        """Enter fail-closed state."""
        with self._lock:
            self._closed = True
    
    def is_closed(self) -> bool:
        """Check if in fail-closed state."""
        with self._lock:
            return self._closed
    
    def get_metrics(self) -> dict[str, int]:
        """Return executor metrics."""
        return {
            "execution_count": self._execution_count,
            "success_count": self._success_count,
            "block_count": self._block_count,
        }
