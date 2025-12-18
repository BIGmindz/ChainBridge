"""Tests for Execution ↔ Governance Evidence Binding (PAC-CODY-OBS-BIND-01).

Verifies that execution fails when:
1. No evidence context is provided
2. Event emission fails
3. Event type mismatches
4. audit_ref mismatch
5. Attempted execution-before-emission

This is the negative enforcement test suite.
Zero execution without governance evidence.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.governance.telemetry import EvidenceEmissionError, create_execution_evidence_context, emit_tool_execution_evidence
from gateway.decision_envelope import CDE_VERSION, GatewayDecision, GatewayDecisionEnvelope, ReasonCode, create_allow_envelope
from gateway.execution_context import (
    TOOL_EXECUTION_ALLOWED_EVENT,
    AuditRefMismatchError,
    ExecutionEvidenceContext,
    ExecutionWithoutEvidenceError,
    InvalidEventTypeError,
    MissingGovernanceEventError,
)
from gateway.tool_executor import (
    DenialReasonCode,
    EvidenceBoundToolExecutor,
    ToolExecutionDenied,
    ToolExecutionResult,
    execute_tool_with_evidence,
)

# =============================================================================
# Test Fixtures
# =============================================================================


def sample_tool(x: int, y: int) -> int:
    """Simple test tool that adds two numbers."""
    return x + y


def failing_tool() -> None:
    """Tool that always raises an exception."""
    raise ValueError("Tool internal error")


@pytest.fixture
def allow_envelope() -> GatewayDecisionEnvelope:
    """Create an envelope that allows execution of 'sample_tool'."""
    return create_allow_envelope(
        agent_gid="GID-01",
        intent_verb="execute",
        intent_target="test_resource",
        allowed_tools=["sample_tool", "other_tool"],
    )


@pytest.fixture
def valid_evidence_context(allow_envelope) -> ExecutionEvidenceContext:
    """Create a valid evidence context."""
    return ExecutionEvidenceContext.create(
        envelope=allow_envelope,
        governance_event_id="gov-test123456",
        event_type=TOOL_EXECUTION_ALLOWED_EVENT,
    )


# =============================================================================
# Test 1: Execution fails when no evidence context is provided
# =============================================================================


class TestNoEvidenceContextDenied:
    """Verify execution fails without evidence context."""

    def test_none_context_denied(self, allow_envelope):
        """None context causes denial."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool_with_evidence(
                context=None,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.NO_EVIDENCE
        assert "No evidence context provided" in error.message

    def test_wrong_type_context_denied(self, allow_envelope):
        """Wrong type context causes denial."""
        fake_context = {"envelope": allow_envelope, "event_id": "fake"}

        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool_with_evidence(
                context=fake_context,  # type: ignore
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.INVALID_EVIDENCE
        assert "Invalid evidence context type" in error.message

    def test_tool_not_called_without_context(self):
        """Tool callable is never invoked without valid context."""
        call_count = {"count": 0}

        def tracked_tool():
            call_count["count"] += 1
            return "executed"

        with pytest.raises(ToolExecutionDenied):
            execute_tool_with_evidence(
                context=None,
                tool_name="tracked_tool",
                tool_callable=tracked_tool,
            )

        # Tool was never called
        assert call_count["count"] == 0


# =============================================================================
# Test 2: Execution fails when event emission fails
# =============================================================================


class TestEventEmissionFailureBlocks:
    """Verify that emission failure blocks execution."""

    def test_emission_error_blocks_context_creation(self, allow_envelope):
        """EvidenceEmissionError raised when emit_event fails."""
        with patch("core.governance.telemetry.emit_event") as mock_emit:
            mock_emit.side_effect = RuntimeError("Sink unavailable")

            with pytest.raises(EvidenceEmissionError) as exc_info:
                emit_tool_execution_evidence(allow_envelope, "sample_tool")

            assert "Evidence emission failed" in str(exc_info.value)
            assert "sample_tool" in str(exc_info.value)

    def test_context_creation_blocked_on_emission_failure(self, allow_envelope):
        """create_execution_evidence_context raises on emission failure."""
        with patch("core.governance.telemetry.emit_event") as mock_emit:
            mock_emit.side_effect = RuntimeError("Sink unavailable")

            with pytest.raises(EvidenceEmissionError):
                create_execution_evidence_context(allow_envelope, "sample_tool")

    def test_tool_never_executes_on_emission_failure(self, allow_envelope):
        """Tool is never called if evidence emission fails."""
        call_count = {"count": 0}

        def tracked_tool():
            call_count["count"] += 1
            return "executed"

        with patch("core.governance.telemetry.emit_event") as mock_emit:
            mock_emit.side_effect = RuntimeError("Sink unavailable")

            # Try to create context (will fail)
            try:
                create_execution_evidence_context(allow_envelope, "tracked_tool")
            except EvidenceEmissionError:
                pass

        # Tool was never called because context creation failed
        assert call_count["count"] == 0


# =============================================================================
# Test 3: Execution fails when event type mismatches
# =============================================================================


class TestEventTypeMismatchDenied:
    """Verify execution fails when event type is wrong."""

    def test_wrong_event_type_at_context_creation(self, allow_envelope):
        """Context creation fails with wrong event type."""
        with pytest.raises(InvalidEventTypeError) as exc_info:
            ExecutionEvidenceContext.create(
                envelope=allow_envelope,
                governance_event_id="gov-test123456",
                event_type="WRONG_EVENT_TYPE",
            )

        assert "TOOL_EXECUTION_ALLOWED" in str(exc_info.value)

    def test_wrong_event_type_execution_denied(self, allow_envelope):
        """Execution denied if context has wrong event type."""
        # Create a context bypassing validation (simulating tampering)
        # This requires direct instantiation with __new__
        context = object.__new__(ExecutionEvidenceContext)
        object.__setattr__(context, "envelope", allow_envelope)
        object.__setattr__(context, "governance_event_id", "gov-test123456")
        object.__setattr__(context, "audit_ref", allow_envelope.audit_ref)
        object.__setattr__(context, "event_type", "WRONG_TYPE")
        object.__setattr__(context, "created_at", datetime.now(timezone.utc))

        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool_with_evidence(
                context=context,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.EVIDENCE_EVENT_MISMATCH
        assert "event type mismatch" in error.message


# =============================================================================
# Test 4: Execution fails when audit_ref mismatches
# =============================================================================


class TestAuditRefMismatchDenied:
    """Verify execution fails when audit_ref doesn't match envelope."""

    def test_audit_ref_mismatch_at_context_creation(self, allow_envelope):
        """Context creation fails when audit_ref doesn't match."""
        # Try to create context with mismatched audit_ref
        with pytest.raises(AuditRefMismatchError):
            ExecutionEvidenceContext(
                envelope=allow_envelope,
                governance_event_id="gov-test123456",
                audit_ref="wrong-audit-ref",  # Doesn't match envelope
                event_type=TOOL_EXECUTION_ALLOWED_EVENT,
                created_at=datetime.now(timezone.utc),
            )

    def test_audit_ref_mismatch_execution_denied(self, allow_envelope):
        """Execution denied if audit_ref doesn't match."""
        # Create a context bypassing validation (simulating tampering)
        context = object.__new__(ExecutionEvidenceContext)
        object.__setattr__(context, "envelope", allow_envelope)
        object.__setattr__(context, "governance_event_id", "gov-test123456")
        object.__setattr__(context, "audit_ref", "tampered-audit-ref")  # Mismatch
        object.__setattr__(context, "event_type", TOOL_EXECUTION_ALLOWED_EVENT)
        object.__setattr__(context, "created_at", datetime.now(timezone.utc))

        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool_with_evidence(
                context=context,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.EVIDENCE_AUDIT_MISMATCH
        assert "audit_ref does not match" in error.message


# =============================================================================
# Test 5: Execution fails when governance_event_id is missing
# =============================================================================


class TestMissingGovernanceEventIdDenied:
    """Verify execution fails when governance_event_id is missing."""

    def test_empty_event_id_at_context_creation(self, allow_envelope):
        """Context creation fails with empty event ID."""
        with pytest.raises(MissingGovernanceEventError):
            ExecutionEvidenceContext.create(
                envelope=allow_envelope,
                governance_event_id="",
                event_type=TOOL_EXECUTION_ALLOWED_EVENT,
            )

    def test_none_event_id_at_context_creation(self, allow_envelope):
        """Context creation fails with None event ID."""
        with pytest.raises(MissingGovernanceEventError):
            ExecutionEvidenceContext.create(
                envelope=allow_envelope,
                governance_event_id=None,  # type: ignore
                event_type=TOOL_EXECUTION_ALLOWED_EVENT,
            )

    def test_missing_event_id_execution_denied(self, allow_envelope):
        """Execution denied if governance_event_id is missing."""
        # Create a context bypassing validation (simulating tampering)
        context = object.__new__(ExecutionEvidenceContext)
        object.__setattr__(context, "envelope", allow_envelope)
        object.__setattr__(context, "governance_event_id", "")  # Empty
        object.__setattr__(context, "audit_ref", allow_envelope.audit_ref)
        object.__setattr__(context, "event_type", TOOL_EXECUTION_ALLOWED_EVENT)
        object.__setattr__(context, "created_at", datetime.now(timezone.utc))

        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool_with_evidence(
                context=context,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.NO_EVIDENCE
        assert "Missing governance event ID" in error.message


# =============================================================================
# Test: Successful execution with valid evidence
# =============================================================================


class TestSuccessfulEvidenceBoundExecution:
    """Verify successful execution when evidence is valid."""

    def test_execution_succeeds_with_valid_context(self, valid_evidence_context):
        """Execution succeeds with valid evidence context."""
        result = execute_tool_with_evidence(
            context=valid_evidence_context,
            tool_name="sample_tool",
            tool_callable=sample_tool,
            x=2,
            y=3,
        )

        assert isinstance(result, ToolExecutionResult)
        assert result.result == 5
        assert result.tool_name == "sample_tool"

    def test_evidence_bound_executor_works(self, valid_evidence_context):
        """EvidenceBoundToolExecutor works with valid context."""
        executor = EvidenceBoundToolExecutor(valid_evidence_context)

        result = executor.execute(
            tool_name="sample_tool",
            tool_callable=sample_tool,
            x=10,
            y=20,
        )

        assert result.result == 30

    def test_full_flow_with_telemetry(self, allow_envelope):
        """Full flow: emit evidence → create context → execute."""
        with patch("core.governance.telemetry.emit_event") as mock_emit:
            # Create context (this emits evidence)
            context = create_execution_evidence_context(allow_envelope, "sample_tool")

            # Verify emission happened
            mock_emit.assert_called_once()

            # Execute with evidence
            result = execute_tool_with_evidence(
                context=context,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=5,
                y=7,
            )

            assert result.result == 12


# =============================================================================
# Test: Evidence context is immutable
# =============================================================================


class TestEvidenceContextImmutability:
    """Verify evidence context cannot be modified."""

    def test_context_is_frozen(self, valid_evidence_context):
        """Evidence context is immutable (frozen dataclass)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            valid_evidence_context.governance_event_id = "tampered"  # type: ignore

    def test_context_envelope_binding(self, valid_evidence_context):
        """Context audit_ref matches envelope."""
        assert valid_evidence_context.audit_ref == valid_evidence_context.envelope.audit_ref


# =============================================================================
# Test: Envelope validation still applies
# =============================================================================


class TestEnvelopeValidationStillApplies:
    """Verify that PAC-GATEWAY-02 envelope validation still applies."""

    def test_deny_envelope_still_blocked(self):
        """DENY envelope blocked even with valid evidence context."""
        from gateway.decision_envelope import create_deny_envelope

        deny_envelope = create_deny_envelope(
            agent_gid="GID-01",
            intent_verb="execute",
            intent_target="test",
            reason_code=ReasonCode.VERB_NOT_PERMITTED,
            reason_detail="Test denial",
        )

        # Create context bypassing evidence validation (to test envelope check)
        context = object.__new__(ExecutionEvidenceContext)
        object.__setattr__(context, "envelope", deny_envelope)
        object.__setattr__(context, "governance_event_id", "gov-test123456")
        object.__setattr__(context, "audit_ref", deny_envelope.audit_ref)
        object.__setattr__(context, "event_type", TOOL_EXECUTION_ALLOWED_EVENT)
        object.__setattr__(context, "created_at", datetime.now(timezone.utc))

        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool_with_evidence(
                context=context,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        # Should be denied by envelope check, not evidence check
        error = exc_info.value
        assert error.reason_code == DenialReasonCode.DECISION_NOT_ALLOW

    def test_tool_not_in_allowed_list_blocked(self, valid_evidence_context):
        """Tool not in allowed_tools blocked even with valid evidence."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool_with_evidence(
                context=valid_evidence_context,
                tool_name="unauthorized_tool",  # Not in allowed_tools
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.TOOL_NOT_ALLOWED


# =============================================================================
# Test: Evidence tracing
# =============================================================================


class TestEvidenceTracing:
    """Verify evidence context provides tracing information."""

    def test_trace_info_contains_required_fields(self, valid_evidence_context):
        """Trace info contains all required fields."""
        trace = valid_evidence_context.get_trace_info()

        assert "governance_event_id" in trace
        assert "audit_ref" in trace
        assert "event_type" in trace
        assert "envelope_decision" in trace
        assert "agent_gid" in trace
        assert "created_at" in trace

    def test_is_valid_returns_true_for_valid_context(self, valid_evidence_context):
        """is_valid() returns True for valid context."""
        assert valid_evidence_context.is_valid() is True
