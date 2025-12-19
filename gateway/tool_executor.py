"""Tool Executor with Envelope-Based Binding Enforcement.

PAC-GATEWAY-02: Tool Binding Enforcement (TBE) v1

This module provides the SOLE execution path for tools. No tool may execute
unless explicitly allowed by a GatewayDecisionEnvelope.

Design principles:
- Fail-closed: If anything is wrong, execution is denied
- Immutable envelopes: Cannot be mutated, reconstructed, or inferred
- No fallback paths: Denial is final
- Audit trail: Every execution attempt is traceable

The gateway decides. This module enforces.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

# Telemetry import (PAC-GOV-OBS-01)
from core.governance.telemetry import emit_tool_execution
from gateway.decision_envelope import GatewayDecision, GatewayDecisionEnvelope

# Evidence binding (PAC-CODY-OBS-BIND-01)
from gateway.execution_context import TOOL_EXECUTION_ALLOWED_EVENT, ExecutionEvidenceContext

# Activation Block enforcement (PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01)
from core.governance.activation_block import (
    ActivationBlock,
    ActivationBlockViolationError,
    validate_activation_block,
)


class DenialReasonCode(str, Enum):
    """Explicit reason codes for tool execution denial."""

    NO_ENVELOPE = "NO_ENVELOPE"
    INVALID_ENVELOPE = "INVALID_ENVELOPE"
    DECISION_NOT_ALLOW = "DECISION_NOT_ALLOW"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    ENVELOPE_TAMPERED = "ENVELOPE_TAMPERED"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    # PAC-CODY-OBS-BIND-01: Evidence binding failures
    NO_EVIDENCE = "NO_EVIDENCE"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    EVIDENCE_EVENT_MISMATCH = "EVIDENCE_EVENT_MISMATCH"
    EVIDENCE_AUDIT_MISMATCH = "EVIDENCE_AUDIT_MISMATCH"
    # PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01: Activation Block failures
    NO_ACTIVATION_BLOCK = "NO_ACTIVATION_BLOCK"
    INVALID_ACTIVATION_BLOCK = "INVALID_ACTIVATION_BLOCK"


@dataclass(frozen=True)
class ToolExecutionDenied(Exception):
    """Raised when tool execution is denied.

    This exception provides explicit, auditable information about why
    execution was blocked. All fields are immutable for audit integrity.
    """

    reason_code: DenialReasonCode
    audit_ref: str
    tool_name: str
    message: str
    envelope_id: Optional[str] = None
    agent_gid: Optional[str] = None
    timestamp: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        # Set timestamp if not provided (workaround for frozen dataclass)
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc))

        # PAC-GOV-OBS-01: Emit telemetry (fail-open)
        emit_tool_execution(
            agent_gid=self.agent_gid or "UNKNOWN",
            tool_name=self.tool_name,
            allowed=False,
            envelope_id=self.envelope_id,
            reason_code=self.reason_code.value,
        )

    def __str__(self) -> str:
        return f"ToolExecutionDenied[{self.reason_code.value}]: {self.message} " f"(tool={self.tool_name}, audit_ref={self.audit_ref})"


@dataclass(frozen=True)
class ToolExecutionResult:
    """Result of a successful tool execution.

    Includes audit trail information alongside the actual result.
    """

    result: Any
    tool_name: str
    envelope_id: str
    agent_gid: str
    executed_at: datetime


T = TypeVar("T")


def _validate_envelope(
    envelope: Optional[GatewayDecisionEnvelope],
    tool_name: str,
) -> GatewayDecisionEnvelope:
    """Validate envelope exists and is properly formed.

    Args:
        envelope: The envelope to validate.
        tool_name: Name of the tool being executed (for error messages).

    Returns:
        The validated envelope.

    Raises:
        ToolExecutionDenied: If envelope is missing or invalid.
    """
    # Gate 1: Envelope must exist
    if envelope is None:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.NO_ENVELOPE,
            audit_ref="NO_ENVELOPE",
            tool_name=tool_name,
            message="Execution blocked: No envelope provided",
        )

    # Gate 2: Envelope must be correct type
    if not isinstance(envelope, GatewayDecisionEnvelope):
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.INVALID_ENVELOPE,
            audit_ref="INVALID_ENVELOPE",
            tool_name=tool_name,
            message=f"Execution blocked: Invalid envelope type ({type(envelope).__name__})",
        )

    return envelope


def _enforce_tool_binding(
    envelope: GatewayDecisionEnvelope,
    tool_name: str,
) -> None:
    """Enforce that the tool is allowed by the envelope.

    Args:
        envelope: The validated envelope.
        tool_name: Name of the tool being executed.

    Raises:
        ToolExecutionDenied: If tool execution is not permitted.
    """
    audit_ref = envelope.audit_ref

    # Gate 3: Decision must be ALLOW
    if envelope.decision != GatewayDecision.ALLOW:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.DECISION_NOT_ALLOW,
            audit_ref=audit_ref,
            tool_name=tool_name,
            message=f"Execution blocked: Envelope decision is {envelope.decision.value}",
            envelope_id=envelope.audit_ref,
            agent_gid=envelope.agent_gid,
        )

    # Gate 4: Human approval must not be required
    if envelope.human_required:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.HUMAN_REQUIRED,
            audit_ref=audit_ref,
            tool_name=tool_name,
            message="Execution blocked: Human approval required",
            envelope_id=envelope.audit_ref,
            agent_gid=envelope.agent_gid,
        )

    # Gate 5: Tool must be in allowed_tools
    if tool_name not in envelope.allowed_tools:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.TOOL_NOT_ALLOWED,
            audit_ref=audit_ref,
            tool_name=tool_name,
            message=f"Execution blocked: Tool '{tool_name}' not in allowed_tools",
            envelope_id=envelope.audit_ref,
            agent_gid=envelope.agent_gid,
        )


def execute_tool(
    *,
    envelope: Optional[GatewayDecisionEnvelope],
    tool_name: str,
    tool_callable: Callable[..., T],
    activation_block: Optional[ActivationBlock] = None,
    **kwargs: Any,
) -> ToolExecutionResult:
    """Execute a tool ONLY if explicitly allowed by the envelope.

    This is the SOLE execution path for tools. No bypass allowed.

    Args:
        envelope: The GatewayDecisionEnvelope authorizing execution.
        tool_name: The canonical name of the tool being executed.
        tool_callable: The function/method to execute.
        activation_block: Optional ActivationBlock for identity enforcement.
        **kwargs: Arguments to pass to the tool_callable.

    Returns:
        ToolExecutionResult containing the result and audit trail.

    Raises:
        ToolExecutionDenied: If execution is not permitted for any reason.

    Rules:
        - If activation_block provided, it MUST validate → DENY if invalid
        - If envelope.decision != "ALLOW" → DENY
        - If tool_name not in envelope.allowed_tools → DENY
        - If envelope.human_required is True → DENY
        - If envelope is malformed → DENY
        - No fallback paths. Denial is final.
    """
    # Validate envelope
    validated_envelope = _validate_envelope(envelope, tool_name)

    # === ACTIVATION BLOCK GATE (PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01) ===
    # If activation_block is provided, validate it BEFORE tool binding
    if activation_block is not None:
        try:
            validate_activation_block(activation_block)
        except ActivationBlockViolationError as e:
            raise ToolExecutionDenied(
                reason_code=DenialReasonCode.INVALID_ACTIVATION_BLOCK,
                audit_ref=validated_envelope.audit_ref,
                tool_name=tool_name,
                message=f"Activation Block validation failed: {e.message}",
                envelope_id=validated_envelope.audit_ref,
                agent_gid=validated_envelope.agent_gid,
            ) from e

    # Enforce tool binding
    _enforce_tool_binding(validated_envelope, tool_name)

    # Execute the tool
    try:
        result = tool_callable(**kwargs)
    except Exception as e:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.EXECUTION_ERROR,
            audit_ref=validated_envelope.audit_ref,
            tool_name=tool_name,
            message=f"Tool execution failed: {e}",
            envelope_id=validated_envelope.audit_ref,
            agent_gid=validated_envelope.agent_gid,
        ) from e

    return ToolExecutionResult(
        result=result,
        tool_name=tool_name,
        envelope_id=validated_envelope.audit_ref,
        agent_gid=validated_envelope.agent_gid,
        executed_at=datetime.now(timezone.utc),
    )


def can_execute_tool(
    envelope: Optional[GatewayDecisionEnvelope],
    tool_name: str,
) -> bool:
    """Check if a tool would be allowed to execute without actually executing.

    This is a lightweight pre-check. Does NOT execute the tool.

    Args:
        envelope: The envelope to check.
        tool_name: The tool name to check.

    Returns:
        True if execute_tool would succeed, False otherwise.
    """
    try:
        validated = _validate_envelope(envelope, tool_name)
        _enforce_tool_binding(validated, tool_name)
        return True
    except ToolExecutionDenied:
        return False


class ToolExecutor:
    """Stateful tool executor for repeated use.

    This class wraps the execute_tool function with consistent envelope handling.
    Useful when the same envelope applies to multiple tool calls.
    """

    def __init__(self, envelope: GatewayDecisionEnvelope) -> None:
        """Initialize with a fixed envelope.

        Args:
            envelope: The envelope governing all executions through this executor.
        """
        self._envelope = envelope

    @property
    def envelope(self) -> GatewayDecisionEnvelope:
        """The envelope governing this executor (immutable)."""
        return self._envelope

    def execute(
        self,
        tool_name: str,
        tool_callable: Callable[..., T],
        **kwargs: Any,
    ) -> ToolExecutionResult:
        """Execute a tool under this executor's envelope.

        Args:
            tool_name: The canonical name of the tool.
            tool_callable: The function to execute.
            **kwargs: Arguments to pass to the tool.

        Returns:
            ToolExecutionResult with result and audit trail.

        Raises:
            ToolExecutionDenied: If execution is not permitted.
        """
        return execute_tool(
            envelope=self._envelope,
            tool_name=tool_name,
            tool_callable=tool_callable,
            **kwargs,
        )

    def can_execute(self, tool_name: str) -> bool:
        """Check if a tool can be executed under this envelope.

        Args:
            tool_name: The tool to check.

        Returns:
            True if execution would be allowed.
        """
        return can_execute_tool(self._envelope, tool_name)


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-CODY-OBS-BIND-01: Evidence-Bound Execution
# ═══════════════════════════════════════════════════════════════════════════════


def _validate_evidence_context(
    context: Optional[ExecutionEvidenceContext],
    tool_name: str,
) -> ExecutionEvidenceContext:
    """Validate evidence context exists and is valid.

    Args:
        context: The evidence context to validate.
        tool_name: Name of the tool being executed (for error messages).

    Returns:
        The validated context.

    Raises:
        ToolExecutionDenied: If context is missing or invalid.
    """
    # Gate E1: Evidence context must exist
    if context is None:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.NO_EVIDENCE,
            audit_ref="NO_EVIDENCE",
            tool_name=tool_name,
            message="Execution blocked: No evidence context provided",
        )

    # Gate E2: Evidence context must be correct type
    if not isinstance(context, ExecutionEvidenceContext):
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.INVALID_EVIDENCE,
            audit_ref="INVALID_EVIDENCE",
            tool_name=tool_name,
            message=f"Execution blocked: Invalid evidence context type ({type(context).__name__})",
        )

    # Gate E3: Event type must be TOOL_EXECUTION_ALLOWED
    if context.event_type != TOOL_EXECUTION_ALLOWED_EVENT:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.EVIDENCE_EVENT_MISMATCH,
            audit_ref=context.audit_ref,
            tool_name=tool_name,
            message=f"Execution blocked: Evidence event type mismatch (got {context.event_type})",
            envelope_id=context.envelope.audit_ref,
            agent_gid=context.envelope.agent_gid,
        )

    # Gate E4: Audit ref must match envelope
    if context.audit_ref != context.envelope.audit_ref:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.EVIDENCE_AUDIT_MISMATCH,
            audit_ref=context.audit_ref,
            tool_name=tool_name,
            message="Execution blocked: Evidence audit_ref does not match envelope",
            envelope_id=context.envelope.audit_ref,
            agent_gid=context.envelope.agent_gid,
        )

    # Gate E5: Governance event ID must exist
    if not context.governance_event_id:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.NO_EVIDENCE,
            audit_ref=context.audit_ref,
            tool_name=tool_name,
            message="Execution blocked: Missing governance event ID",
            envelope_id=context.envelope.audit_ref,
            agent_gid=context.envelope.agent_gid,
        )

    return context


def execute_tool_with_evidence(
    *,
    context: Optional[ExecutionEvidenceContext],
    tool_name: str,
    tool_callable: Callable[..., T],
    **kwargs: Any,
) -> ToolExecutionResult:
    """Execute a tool ONLY if evidence context is valid and bound.

    PAC-CODY-OBS-BIND-01: This is the fail-closed execution path that requires
    governance evidence to be emitted BEFORE execution can occur.

    Args:
        context: The ExecutionEvidenceContext with bound governance event.
        tool_name: The canonical name of the tool being executed.
        tool_callable: The function/method to execute.
        **kwargs: Arguments to pass to the tool_callable.

    Returns:
        ToolExecutionResult containing the result and audit trail.

    Raises:
        ToolExecutionDenied: If evidence context is missing or invalid.
        ExecutionWithoutEvidenceError: If execution is attempted without evidence.

    Execution Flow:
        1. Validate evidence context exists and is correct type
        2. Validate event_type == TOOL_EXECUTION_ALLOWED
        3. Validate audit_ref matches envelope
        4. Validate governance_event_id exists
        5. Validate envelope allows execution (delegate to existing gates)
        6. Execute tool

    If ANY validation fails → execution is blocked. No exceptions.
    """
    # Validate evidence context (Gates E1-E5)
    validated_context = _validate_evidence_context(context, tool_name)

    # Delegate to existing envelope validation (Gates 1-5 from PAC-GATEWAY-02)
    # This ensures all envelope validations still apply
    validated_envelope = _validate_envelope(validated_context.envelope, tool_name)
    _enforce_tool_binding(validated_envelope, tool_name)

    # All gates passed — execute the tool
    try:
        result = tool_callable(**kwargs)
    except Exception as e:
        raise ToolExecutionDenied(
            reason_code=DenialReasonCode.EXECUTION_ERROR,
            audit_ref=validated_context.audit_ref,
            tool_name=tool_name,
            message=f"Tool execution failed: {e}",
            envelope_id=validated_envelope.audit_ref,
            agent_gid=validated_envelope.agent_gid,
        ) from e

    return ToolExecutionResult(
        result=result,
        tool_name=tool_name,
        envelope_id=validated_envelope.audit_ref,
        agent_gid=validated_envelope.agent_gid,
        executed_at=datetime.now(timezone.utc),
    )


class EvidenceBoundToolExecutor:
    """Evidence-bound tool executor (PAC-CODY-OBS-BIND-01).

    This executor requires an ExecutionEvidenceContext for all executions,
    ensuring that governance evidence is emitted BEFORE execution can occur.
    """

    def __init__(self, context: ExecutionEvidenceContext) -> None:
        """Initialize with evidence context.

        Args:
            context: The evidence context binding envelope to governance event.
        """
        self._context = context

    @property
    def context(self) -> ExecutionEvidenceContext:
        """The evidence context governing this executor (immutable)."""
        return self._context

    @property
    def envelope(self) -> GatewayDecisionEnvelope:
        """The envelope from the evidence context."""
        return self._context.envelope

    def execute(
        self,
        tool_name: str,
        tool_callable: Callable[..., T],
        **kwargs: Any,
    ) -> ToolExecutionResult:
        """Execute a tool under this executor's evidence context.

        Args:
            tool_name: The canonical name of the tool.
            tool_callable: The function to execute.
            **kwargs: Arguments to pass to the tool.

        Returns:
            ToolExecutionResult with result and audit trail.

        Raises:
            ToolExecutionDenied: If execution is not permitted.
        """
        return execute_tool_with_evidence(
            context=self._context,
            tool_name=tool_name,
            tool_callable=tool_callable,
            **kwargs,
        )

    def can_execute(self, tool_name: str) -> bool:
        """Check if a tool can be executed under this context.

        Args:
            tool_name: The tool to check.

        Returns:
            True if execution would be allowed.
        """
        return can_execute_tool(self._context.envelope, tool_name)
