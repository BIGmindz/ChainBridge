"""
ChainBridge Transition Validator

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

PAC: PAC-ATLAS-A12-STATE-TRANSITION-GOVERNANCE-LOCK-01

This module provides deterministic transition validation.
All validation is READ-ONLY with no side effects.

INVARIANTS ENFORCED:
- INV-T01: All transitions must be declared
- INV-T02: Fail-closed on undefined transitions
- INV-T03: Proof required for governed transitions
- INV-T04: Authority required for governed transitions
- INV-T06: Terminal states immutable
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List

from .state_machine import (
    StateMachine,
    TransitionRule,
    get_state_machine,
    STATE_MACHINES,
)


# =============================================================================
# TRANSITION RESULT TYPES
# =============================================================================


class TransitionResult(str, Enum):
    """Possible results of a transition validation."""

    ALLOWED = "ALLOWED"
    REJECTED_UNDEFINED = "REJECTED_UNDEFINED"
    REJECTED_TERMINAL = "REJECTED_TERMINAL"
    REJECTED_INVALID_STATE = "REJECTED_INVALID_STATE"
    REJECTED_MISSING_PROOF = "REJECTED_MISSING_PROOF"
    REJECTED_MISSING_AUTHORITY = "REJECTED_MISSING_AUTHORITY"
    REJECTED_AUTHORITY_MISMATCH = "REJECTED_AUTHORITY_MISMATCH"
    REJECTED_SAME_STATE = "REJECTED_SAME_STATE"


@dataclass
class TransitionValidationResult:
    """Result of validating a state transition."""

    result: TransitionResult
    artifact_type: str
    artifact_id: str
    from_state: str
    to_state: str
    is_allowed: bool
    rejection_reason: Optional[str] = None
    required_authority: Optional[str] = None
    provided_authority: Optional[str] = None
    requires_proof: bool = False
    proof_provided: bool = False
    validated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging/reporting."""
        return {
            "result": self.result.value,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "is_allowed": self.is_allowed,
            "rejection_reason": self.rejection_reason,
            "required_authority": self.required_authority,
            "provided_authority": self.provided_authority,
            "requires_proof": self.requires_proof,
            "proof_provided": self.proof_provided,
            "validated_at": self.validated_at.isoformat(),
        }


# =============================================================================
# TRANSITION REQUEST
# =============================================================================


@dataclass
class TransitionRequest:
    """Request to transition an artifact's state."""

    artifact_type: str
    artifact_id: str
    from_state: str
    to_state: str
    authority_gid: Optional[str] = None
    proof_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# TRANSITION VALIDATOR
# =============================================================================


class TransitionValidator:
    """
    Deterministic transition validator.

    This validator is READ-ONLY. It does not modify any state.
    All validation methods return results without side effects.

    Implements fail-closed semantics:
    - Undefined transition → REJECT
    - Missing proof when required → REJECT
    - Missing authority when required → REJECT
    - Terminal state source → REJECT
    """

    def __init__(self) -> None:
        """Initialize the validator."""
        self._validation_count = 0

    def validate_transition(
        self,
        request: TransitionRequest,
    ) -> TransitionValidationResult:
        """
        Validate a transition request.

        Returns TransitionValidationResult with detailed rejection reason
        if the transition is not allowed.

        This method has NO SIDE EFFECTS.
        """
        self._validation_count += 1

        # Get the state machine for this artifact type
        machine = get_state_machine(request.artifact_type)
        if machine is None:
            return TransitionValidationResult(
                result=TransitionResult.REJECTED_UNDEFINED,
                artifact_type=request.artifact_type,
                artifact_id=request.artifact_id,
                from_state=request.from_state,
                to_state=request.to_state,
                is_allowed=False,
                rejection_reason=f"No state machine defined for artifact type: {request.artifact_type}",
            )

        # Check for same-state transition (no-op)
        if request.from_state == request.to_state:
            return TransitionValidationResult(
                result=TransitionResult.REJECTED_SAME_STATE,
                artifact_type=request.artifact_type,
                artifact_id=request.artifact_id,
                from_state=request.from_state,
                to_state=request.to_state,
                is_allowed=False,
                rejection_reason="Cannot transition to the same state",
            )

        # Validate states exist in machine
        if request.from_state not in machine.states:
            return TransitionValidationResult(
                result=TransitionResult.REJECTED_INVALID_STATE,
                artifact_type=request.artifact_type,
                artifact_id=request.artifact_id,
                from_state=request.from_state,
                to_state=request.to_state,
                is_allowed=False,
                rejection_reason=f"Invalid from_state: {request.from_state}",
            )

        if request.to_state not in machine.states:
            return TransitionValidationResult(
                result=TransitionResult.REJECTED_INVALID_STATE,
                artifact_type=request.artifact_type,
                artifact_id=request.artifact_id,
                from_state=request.from_state,
                to_state=request.to_state,
                is_allowed=False,
                rejection_reason=f"Invalid to_state: {request.to_state}",
            )

        # Check if from_state is terminal (no outgoing transitions)
        if machine.is_terminal(request.from_state):
            return TransitionValidationResult(
                result=TransitionResult.REJECTED_TERMINAL,
                artifact_type=request.artifact_type,
                artifact_id=request.artifact_id,
                from_state=request.from_state,
                to_state=request.to_state,
                is_allowed=False,
                rejection_reason=f"Cannot transition from terminal state: {request.from_state}",
            )

        # Check if transition is declared (fail-closed on undefined)
        if not machine.is_valid_transition(request.from_state, request.to_state):
            allowed = machine.get_allowed_transitions(request.from_state)
            return TransitionValidationResult(
                result=TransitionResult.REJECTED_UNDEFINED,
                artifact_type=request.artifact_type,
                artifact_id=request.artifact_id,
                from_state=request.from_state,
                to_state=request.to_state,
                is_allowed=False,
                rejection_reason=(
                    f"Transition {request.from_state} → {request.to_state} not declared. "
                    f"Allowed: {allowed or 'none'}"
                ),
            )

        # Get transition rule (may be None for transitions without explicit rules)
        rule = machine.get_transition_rule(request.from_state, request.to_state)
        requires_proof = rule.requires_proof if rule else True  # Default: require proof
        required_authority = rule.required_authority if rule else None

        # Check proof requirement
        if requires_proof and not request.proof_id:
            return TransitionValidationResult(
                result=TransitionResult.REJECTED_MISSING_PROOF,
                artifact_type=request.artifact_type,
                artifact_id=request.artifact_id,
                from_state=request.from_state,
                to_state=request.to_state,
                is_allowed=False,
                rejection_reason="Transition requires proof_id but none provided",
                requires_proof=True,
                proof_provided=False,
            )

        # Check authority requirement
        if required_authority and not request.authority_gid:
            return TransitionValidationResult(
                result=TransitionResult.REJECTED_MISSING_AUTHORITY,
                artifact_type=request.artifact_type,
                artifact_id=request.artifact_id,
                from_state=request.from_state,
                to_state=request.to_state,
                is_allowed=False,
                rejection_reason=f"Transition requires authority: {required_authority}",
                required_authority=required_authority,
                requires_proof=requires_proof,
                proof_provided=bool(request.proof_id),
            )

        # Validate authority matches (if specific GID required)
        if required_authority and request.authority_gid:
            if not self._authority_matches(required_authority, request.authority_gid):
                return TransitionValidationResult(
                    result=TransitionResult.REJECTED_AUTHORITY_MISMATCH,
                    artifact_type=request.artifact_type,
                    artifact_id=request.artifact_id,
                    from_state=request.from_state,
                    to_state=request.to_state,
                    is_allowed=False,
                    rejection_reason=(
                        f"Authority mismatch: required {required_authority}, "
                        f"provided {request.authority_gid}"
                    ),
                    required_authority=required_authority,
                    provided_authority=request.authority_gid,
                    requires_proof=requires_proof,
                    proof_provided=bool(request.proof_id),
                )

        # All checks passed
        return TransitionValidationResult(
            result=TransitionResult.ALLOWED,
            artifact_type=request.artifact_type,
            artifact_id=request.artifact_id,
            from_state=request.from_state,
            to_state=request.to_state,
            is_allowed=True,
            required_authority=required_authority,
            provided_authority=request.authority_gid,
            requires_proof=requires_proof,
            proof_provided=bool(request.proof_id),
        )

    def _authority_matches(self, required: str, provided: str) -> bool:
        """
        Check if provided authority matches required authority.

        Handles special authority types:
        - SYSTEM: Any system authority
        - GID-XX: Specific agent
        - ROLE_NAME: Role-based authority (resolved externally)
        """
        # Direct GID match
        if required == provided:
            return True

        # SYSTEM authority can be satisfied by any GID
        if required == "SYSTEM":
            return True

        # Role-based authorities (placeholder for external resolution)
        role_authorities = {
            "CRO": ["GID-00"],  # Chief Risk Officer
            "VERIFIER": ["GID-00", "GID-01", "GID-06"],  # Benson, Cody, Sam
            "RISK_ENGINE": ["GID-10", "SYSTEM"],  # Maggie or system
            "RISK_AGENT": ["GID-10"],  # Maggie
            "HUMAN_PLUS_2_AGENTS": [],  # External verification required
        }

        if required in role_authorities:
            return provided in role_authorities[required] or provided == "SYSTEM"

        return False

    def validate_batch(
        self,
        requests: List[TransitionRequest],
    ) -> List[TransitionValidationResult]:
        """Validate multiple transitions in batch."""
        return [self.validate_transition(req) for req in requests]

    @property
    def validation_count(self) -> int:
        """Number of validations performed by this instance."""
        return self._validation_count


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def validate_transition(
    artifact_type: str,
    artifact_id: str,
    from_state: str,
    to_state: str,
    authority_gid: Optional[str] = None,
    proof_id: Optional[str] = None,
) -> TransitionValidationResult:
    """Convenience function for single transition validation."""
    validator = TransitionValidator()
    request = TransitionRequest(
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        from_state=from_state,
        to_state=to_state,
        authority_gid=authority_gid,
        proof_id=proof_id,
    )
    return validator.validate_transition(request)


def is_transition_allowed(
    artifact_type: str,
    from_state: str,
    to_state: str,
) -> bool:
    """Quick check if a transition is structurally allowed (ignores proof/authority)."""
    machine = get_state_machine(artifact_type)
    if machine is None:
        return False
    return machine.is_valid_transition(from_state, to_state)


def get_allowed_transitions(artifact_type: str, from_state: str) -> set[str]:
    """Get all allowed target states from a given state."""
    machine = get_state_machine(artifact_type)
    if machine is None:
        return set()
    return machine.get_allowed_transitions(from_state)
