"""Execution Evidence Context — PAC-CODY-OBS-BIND-01

This module defines the ExecutionEvidenceContext that causally binds
governance evidence to tool execution.

Design Principles:
- Frozen: Cannot be mutated after creation
- No defaults: All fields must be explicitly provided
- Validation: Cannot be constructed without valid governance event ID
- Fail-closed: Invalid context blocks execution

If evidence emission fails → execution must fail.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gateway.decision_envelope import GatewayDecisionEnvelope


class ExecutionEvidenceError(Exception):
    """Base exception for execution evidence errors."""

    pass


class MissingGovernanceEventError(ExecutionEvidenceError):
    """Raised when governance event ID is missing or invalid."""

    pass


class AuditRefMismatchError(ExecutionEvidenceError):
    """Raised when audit_ref does not match envelope."""

    pass


class InvalidEventTypeError(ExecutionEvidenceError):
    """Raised when event type is not TOOL_EXECUTION_ALLOWED."""

    pass


class ExecutionWithoutEvidenceError(ExecutionEvidenceError):
    """Raised when tool execution is attempted without bound governance event."""

    def __init__(self, message: str = "Tool execution attempted without bound governance event.") -> None:
        super().__init__(message)


# Expected event type for tool execution evidence
TOOL_EXECUTION_ALLOWED_EVENT = "TOOL_EXECUTION_ALLOWED"


@dataclass(frozen=True)
class ExecutionEvidenceContext:
    """Execution Evidence Context — binds governance evidence to tool execution.

    This context is REQUIRED for tool execution. It causally binds:
    - The GatewayDecisionEnvelope (authorization)
    - The governance_event_id (proof of telemetry emission)
    - The audit_ref (traceability)

    Constraints:
    - Frozen: Immutable after creation
    - No defaults: All fields must be explicitly provided
    - Validation: Cannot be constructed with invalid data

    Usage:
        # Create context after evidence emission
        context = ExecutionEvidenceContext(
            envelope=envelope,
            governance_event_id="gov-abc123",
            audit_ref=envelope.audit_ref,
            event_type="TOOL_EXECUTION_ALLOWED",
        )

        # Pass to tool executor
        execute_tool_with_evidence(context=context, ...)
    """

    envelope: "GatewayDecisionEnvelope"
    governance_event_id: str
    audit_ref: str
    event_type: str
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate context integrity."""
        # Validation 1: governance_event_id must exist and be non-empty
        if not self.governance_event_id:
            raise MissingGovernanceEventError("ExecutionEvidenceContext requires a valid governance_event_id")

        # Validation 2: event_type must be TOOL_EXECUTION_ALLOWED
        if self.event_type != TOOL_EXECUTION_ALLOWED_EVENT:
            raise InvalidEventTypeError(
                f"ExecutionEvidenceContext requires event_type={TOOL_EXECUTION_ALLOWED_EVENT}, " f"got {self.event_type}"
            )

        # Validation 3: audit_ref must match envelope
        if self.envelope.audit_ref != self.audit_ref:
            raise AuditRefMismatchError(f"audit_ref mismatch: context has '{self.audit_ref}', " f"envelope has '{self.envelope.audit_ref}'")

    @classmethod
    def create(
        cls,
        envelope: "GatewayDecisionEnvelope",
        governance_event_id: str,
        event_type: str,
    ) -> "ExecutionEvidenceContext":
        """Factory method to create a validated ExecutionEvidenceContext.

        Args:
            envelope: The GatewayDecisionEnvelope authorizing execution.
            governance_event_id: The ID of the emitted governance event.
            event_type: The type of the governance event (must be TOOL_EXECUTION_ALLOWED).

        Returns:
            ExecutionEvidenceContext with validated bindings.

        Raises:
            MissingGovernanceEventError: If governance_event_id is empty.
            InvalidEventTypeError: If event_type is not TOOL_EXECUTION_ALLOWED.
            AuditRefMismatchError: If audit_ref doesn't match envelope.
        """
        return cls(
            envelope=envelope,
            governance_event_id=governance_event_id,
            audit_ref=envelope.audit_ref,
            event_type=event_type,
            created_at=datetime.now(timezone.utc),
        )

    def is_valid(self) -> bool:
        """Check if context is valid for execution.

        Returns:
            True if all validations pass, False otherwise.

        Note: This should always return True for successfully constructed contexts,
        but is provided for defensive programming.
        """
        return (
            bool(self.governance_event_id) and self.event_type == TOOL_EXECUTION_ALLOWED_EVENT and self.envelope.audit_ref == self.audit_ref
        )

    def get_trace_info(self) -> dict:
        """Get tracing information for audit logs.

        Returns:
            Dict with governance_event_id, audit_ref, and envelope details.
        """
        return {
            "governance_event_id": self.governance_event_id,
            "audit_ref": self.audit_ref,
            "event_type": self.event_type,
            "envelope_decision": self.envelope.decision.value,
            "agent_gid": self.envelope.agent_gid,
            "created_at": self.created_at.isoformat(),
        }
