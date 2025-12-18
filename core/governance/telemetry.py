"""
🟣 DAN (GID-07) — Governance Telemetry Integration
PAC-GOV-OBS-01: Governance Observability & Event Telemetry
PAC-CODY-OBS-BIND-01: Execution ↔ Governance Evidence Binding

This module provides integration points for emitting governance events
at key decision points. It wraps existing governance components to
emit telemetry without modifying their core logic.

Design:
- Non-blocking: All emissions are try/except wrapped (safe_emit)
- Non-invasive: Works with existing code, minimal changes
- Fail-tolerant: Emission failures never affect decisions (except evidence binding)

PAC-CODY-OBS-BIND-01 additions:
- Fail-closed evidence emission for tool execution
- Evidence context creation for execution binding
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar

from core.governance.event_sink import emit_event
from core.governance.events import (
    GovernanceEvent,
    acm_evaluated_event,
    artifact_verification_event,
    decision_allowed_event,
    decision_denied_event,
    decision_escalated_event,
    diggi_correction_event,
    drcp_triggered_event,
    scope_violation_event,
    tool_execution_event,
)

if TYPE_CHECKING:
    from core.governance.acm_evaluator import EvaluationResult
    from gateway.decision_envelope import GatewayDecisionEnvelope
    from gateway.execution_context import ExecutionEvidenceContext

logger = logging.getLogger("governance.telemetry")

T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════════════════════
# SAFE EMISSION WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════


def safe_emit(event: GovernanceEvent) -> None:
    """
    Emit an event safely, swallowing any errors.

    This ensures telemetry NEVER blocks or affects execution.
    """
    try:
        emit_event(event)
    except Exception as e:
        logger.debug("Telemetry emission failed (swallowed): %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# ACM EVALUATION TELEMETRY
# ═══════════════════════════════════════════════════════════════════════════════


def emit_acm_evaluation(result: EvaluationResult) -> None:
    """
    Emit telemetry for an ACM evaluation result.

    Called after every ACM evaluation (ALLOW or DENY).
    """
    try:
        from core.governance.acm_evaluator import ACMDecision

        decision_str = result.decision.value if result.decision else "UNKNOWN"

        event = acm_evaluated_event(
            agent_gid=result.agent_gid,
            verb=result.intent_verb,
            target=result.intent_target,
            decision=decision_str,
            reason_code=result.reason.value if result.reason else None,
            metadata={
                "acm_version": result.acm_version,
                "correlation_id": result.correlation_id,
            },
        )
        safe_emit(event)

        # Also emit decision-specific event
        if result.decision == ACMDecision.ALLOW:
            safe_emit(
                decision_allowed_event(
                    agent_gid=result.agent_gid,
                    verb=result.intent_verb,
                    target=result.intent_target,
                    audit_ref=result.correlation_id,
                )
            )
        elif result.decision == ACMDecision.DENY:
            safe_emit(
                decision_denied_event(
                    agent_gid=result.agent_gid,
                    verb=result.intent_verb,
                    target=result.intent_target,
                    reason_code=result.reason.value if result.reason else "UNKNOWN",
                    audit_ref=result.correlation_id,
                )
            )
    except Exception as e:
        logger.debug("ACM telemetry emission failed (swallowed): %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# DRCP TELEMETRY
# ═══════════════════════════════════════════════════════════════════════════════


def emit_drcp_triggered(
    agent_gid: str,
    verb: str,
    target: str,
    denial_code: str,
    *,
    intent_id: str | None = None,
) -> None:
    """
    Emit telemetry when DRCP is triggered.

    Called when a denial is routed to Diggi.
    """
    try:
        event = drcp_triggered_event(
            agent_gid=agent_gid,
            verb=verb,
            target=target,
            reason_code=denial_code,
            audit_ref=intent_id,
            metadata={"intent_id": intent_id} if intent_id else {},
        )
        safe_emit(event)
    except Exception as e:
        logger.debug("DRCP telemetry emission failed (swallowed): %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# DIGGI CORRECTION TELEMETRY
# ═══════════════════════════════════════════════════════════════════════════════


def emit_diggi_correction(
    agent_gid: str,
    target: str,
    correction_type: str,
    *,
    envelope_id: str | None = None,
    num_options: int | None = None,
) -> None:
    """
    Emit telemetry when Diggi issues a correction.

    Called when Diggi generates correction options.
    """
    try:
        event = diggi_correction_event(
            agent_gid=agent_gid,
            target=target,
            correction_type=correction_type,
            audit_ref=envelope_id,
            metadata=(
                {
                    "num_options": num_options,
                }
                if num_options
                else {}
            ),
        )
        safe_emit(event)
    except Exception as e:
        logger.debug("Diggi telemetry emission failed (swallowed): %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL EXECUTION TELEMETRY
# ═══════════════════════════════════════════════════════════════════════════════


def emit_tool_execution(
    agent_gid: str,
    tool_name: str,
    allowed: bool,
    *,
    envelope_id: str | None = None,
    reason_code: str | None = None,
) -> None:
    """
    Emit telemetry for tool execution decisions.

    Called for both allowed and denied tool executions.
    """
    try:
        event = tool_execution_event(
            agent_gid=agent_gid,
            tool_name=tool_name,
            allowed=allowed,
            reason_code=reason_code,
            audit_ref=envelope_id,
        )
        safe_emit(event)
    except Exception as e:
        logger.debug("Tool execution telemetry emission failed (swallowed): %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-CODY-OBS-BIND-01: FAIL-CLOSED EVIDENCE EMISSION
# ═══════════════════════════════════════════════════════════════════════════════


class EvidenceEmissionError(Exception):
    """Raised when evidence emission fails.

    PAC-CODY-OBS-BIND-01: This error MUST block execution.
    If evidence cannot be emitted, execution cannot proceed.
    """

    pass


def emit_tool_execution_evidence(
    envelope: "GatewayDecisionEnvelope",
    tool_name: str,
) -> str:
    """
    Emit TOOL_EXECUTION_ALLOWED event and return event_id for binding.

    PAC-CODY-OBS-BIND-01: FAIL-CLOSED

    This function MUST succeed for execution to proceed.
    If emission fails, this function raises EvidenceEmissionError.

    Args:
        envelope: The GatewayDecisionEnvelope authorizing execution.
        tool_name: The name of the tool being executed.

    Returns:
        The event_id of the emitted TOOL_EXECUTION_ALLOWED event.

    Raises:
        EvidenceEmissionError: If event emission fails for any reason.

    Note: Unlike safe_emit(), this function does NOT swallow exceptions.
    Evidence emission is a hard dependency for execution.
    """
    try:
        event = tool_execution_event(
            agent_gid=envelope.agent_gid,
            tool_name=tool_name,
            allowed=True,
            audit_ref=envelope.audit_ref,
            metadata={
                "envelope_decision": envelope.decision.value,
                "intent_verb": envelope.intent_verb,
                "intent_target": envelope.intent_target,
            },
        )

        # Emit event (this MUST succeed)
        emit_event(event)

        # Return event_id for binding
        return event.event_id

    except Exception as e:
        # PAC-CODY-OBS-BIND-01: Emission failure blocks execution
        raise EvidenceEmissionError(f"Evidence emission failed for tool '{tool_name}': {e}") from e


def create_execution_evidence_context(
    envelope: "GatewayDecisionEnvelope",
    tool_name: str,
) -> "ExecutionEvidenceContext":
    """
    Emit evidence and create ExecutionEvidenceContext in one operation.

    PAC-CODY-OBS-BIND-01: Convenience function that:
    1. Emits TOOL_EXECUTION_ALLOWED event
    2. Captures event_id
    3. Creates and returns ExecutionEvidenceContext

    Args:
        envelope: The GatewayDecisionEnvelope authorizing execution.
        tool_name: The name of the tool being executed.

    Returns:
        ExecutionEvidenceContext with bound governance event.

    Raises:
        EvidenceEmissionError: If event emission fails.
    """
    from gateway.execution_context import ExecutionEvidenceContext

    # Step 1: Emit evidence (MUST succeed)
    event_id = emit_tool_execution_evidence(envelope, tool_name)

    # Step 2: Create evidence context
    context = ExecutionEvidenceContext.create(
        envelope=envelope,
        governance_event_id=event_id,
        event_type="TOOL_EXECUTION_ALLOWED",
    )

    return context


# ═══════════════════════════════════════════════════════════════════════════════
# ARTIFACT VERIFICATION TELEMETRY
# ═══════════════════════════════════════════════════════════════════════════════


def emit_artifact_verification(
    passed: bool,
    aggregate_hash: str,
    *,
    file_count: int | None = None,
    mismatches: list[str] | None = None,
) -> None:
    """
    Emit telemetry for artifact verification.

    Called after artifact integrity check.
    """
    try:
        event = artifact_verification_event(
            passed=passed,
            artifact_hash=aggregate_hash,
            file_count=file_count,
            mismatches=mismatches,
        )
        safe_emit(event)
    except Exception as e:
        logger.debug("Artifact telemetry emission failed (swallowed): %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE VIOLATION TELEMETRY
# ═══════════════════════════════════════════════════════════════════════════════


def emit_scope_violation(
    file_path: str,
    violation_type: str,
    *,
    pattern: str | None = None,
) -> None:
    """
    Emit telemetry for scope violations.

    Called when scope guard detects a violation.
    """
    try:
        event = scope_violation_event(
            file_path=file_path,
            violation_type=violation_type,
            pattern=pattern,
        )
        safe_emit(event)
    except Exception as e:
        logger.debug("Scope violation telemetry emission failed (swallowed): %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# ENVELOPE DECISION TELEMETRY
# ═══════════════════════════════════════════════════════════════════════════════


def emit_envelope_decision(envelope: GatewayDecisionEnvelope) -> None:
    """
    Emit telemetry from a gateway decision envelope.

    Called after envelope is created.
    """
    try:
        from gateway.decision_envelope import GatewayDecision

        if envelope.decision == GatewayDecision.ALLOW:
            event = decision_allowed_event(
                agent_gid=envelope.agent_gid,
                verb=envelope.verb,
                target=envelope.target,
                audit_ref=envelope.audit_ref,
            )
        elif envelope.decision == GatewayDecision.ESCALATE:
            event = decision_escalated_event(
                agent_gid=envelope.agent_gid,
                verb=envelope.verb,
                target=envelope.target,
                reason_code=envelope.reason_code.value if envelope.reason_code else "ESCALATED",
                audit_ref=envelope.audit_ref,
            )
        else:  # DENY
            event = decision_denied_event(
                agent_gid=envelope.agent_gid,
                verb=envelope.verb,
                target=envelope.target,
                reason_code=envelope.reason_code.value if envelope.reason_code else "DENIED",
                audit_ref=envelope.audit_ref,
            )
        safe_emit(event)
    except Exception as e:
        logger.debug("Envelope telemetry emission failed (swallowed): %s", e)
