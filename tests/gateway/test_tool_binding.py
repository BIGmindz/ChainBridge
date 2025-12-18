"""Tests for Tool Binding Enforcement (PAC-GATEWAY-02).

Verifies that:
1. Tool executes when allowed
2. Tool denied when not in allowed_tools
3. Tool denied when decision = DENY
4. Tool denied when human_required = True
5. Envelope tampering causes denial
6. Audit reference preserved on error
7. No tool executes without envelope

Zero mocks of governance logic. Uses real envelopes from PAC-GATEWAY-01.
"""

from datetime import datetime, timezone

import pytest

from gateway.decision_envelope import (
    CDE_VERSION,
    GatewayDecision,
    GatewayDecisionEnvelope,
    ReasonCode,
    create_allow_envelope,
    create_deny_envelope,
)
from gateway.tool_executor import DenialReasonCode, ToolExecutionDenied, ToolExecutionResult, ToolExecutor, can_execute_tool, execute_tool

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
def deny_envelope() -> GatewayDecisionEnvelope:
    """Create an envelope with DENY decision."""
    return create_deny_envelope(
        agent_gid="GID-01",
        intent_verb="execute",
        intent_target="test_resource",
        reason_code=ReasonCode.VERB_NOT_PERMITTED,
        reason_detail="Test denial",
    )


@pytest.fixture
def human_required_envelope() -> GatewayDecisionEnvelope:
    """Create an envelope requiring human approval."""
    return GatewayDecisionEnvelope(
        version=CDE_VERSION,
        decision=GatewayDecision.ALLOW,
        reason_code=ReasonCode.NONE,
        reason_detail="",
        human_required=True,
        next_hop=None,
        allowed_tools=["sample_tool"],
        audit_ref="test-audit-human",
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent_gid="GID-01",
        intent_verb="execute",
        intent_target="test_resource",
    )


@pytest.fixture
def empty_tools_envelope() -> GatewayDecisionEnvelope:
    """Create an envelope with no allowed tools."""
    return create_allow_envelope(
        agent_gid="GID-01",
        intent_verb="execute",
        intent_target="test_resource",
        allowed_tools=[],
    )


@pytest.fixture
def escalate_envelope() -> GatewayDecisionEnvelope:
    """Create a DENY envelope with escalation routing."""
    return create_deny_envelope(
        agent_gid="GID-01",
        intent_verb="execute",
        intent_target="test_resource",
        reason_code=ReasonCode.VERB_NOT_PERMITTED,
        reason_detail="Needs escalation",
        next_hop="GID-08",
    )


# =============================================================================
# Test 1: Tool executes when allowed
# =============================================================================


class TestToolExecutesWhenAllowed:
    """Verify tools execute correctly when envelope permits."""

    def test_execute_tool_success(self, allow_envelope):
        """Tool executes and returns result when allowed."""
        result = execute_tool(
            envelope=allow_envelope,
            tool_name="sample_tool",
            tool_callable=sample_tool,
            x=2,
            y=3,
        )

        assert isinstance(result, ToolExecutionResult)
        assert result.result == 5
        assert result.tool_name == "sample_tool"
        assert result.envelope_id == allow_envelope.audit_ref
        assert result.agent_gid == "GID-01"
        assert isinstance(result.executed_at, datetime)

    def test_execute_other_allowed_tool(self, allow_envelope):
        """Can execute any tool in allowed_tools list."""
        # 'other_tool' is in allowed_tools
        result = execute_tool(
            envelope=allow_envelope,
            tool_name="other_tool",
            tool_callable=lambda: "other result",
        )
        assert result.result == "other result"
        assert result.tool_name == "other_tool"

    def test_can_execute_returns_true_when_allowed(self, allow_envelope):
        """Pre-check returns True for allowed tools."""
        assert can_execute_tool(allow_envelope, "sample_tool") is True
        assert can_execute_tool(allow_envelope, "other_tool") is True


# =============================================================================
# Test 2: Tool denied when not in allowed_tools
# =============================================================================


class TestToolDeniedNotInAllowedTools:
    """Verify denial when tool is not in allowed_tools."""

    def test_denied_tool_not_in_list(self, allow_envelope):
        """Tool not in allowed_tools is denied."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=allow_envelope,
                tool_name="unauthorized_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.TOOL_NOT_ALLOWED
        assert error.tool_name == "unauthorized_tool"
        assert "not in allowed_tools" in error.message
        assert error.envelope_id == allow_envelope.audit_ref
        assert error.agent_gid == "GID-01"

    def test_denied_empty_allowed_tools(self, empty_tools_envelope):
        """No tools allowed when allowed_tools is empty."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=empty_tools_envelope,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        assert exc_info.value.reason_code == DenialReasonCode.TOOL_NOT_ALLOWED

    def test_can_execute_returns_false_for_unlisted_tool(self, allow_envelope):
        """Pre-check returns False for tools not in list."""
        assert can_execute_tool(allow_envelope, "unauthorized_tool") is False


# =============================================================================
# Test 3: Tool denied when decision = DENY
# =============================================================================


class TestToolDeniedDecisionDeny:
    """Verify denial when envelope decision is DENY."""

    def test_denied_on_deny_decision(self, deny_envelope):
        """Tool denied when decision is DENY."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=deny_envelope,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.DECISION_NOT_ALLOW
        assert "decision is DENY" in error.message

    def test_denied_on_escalate_envelope(self, escalate_envelope):
        """Tool denied when envelope is DENY (even with next_hop)."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=escalate_envelope,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.DECISION_NOT_ALLOW
        assert "DENY" in error.message

    def test_can_execute_returns_false_for_deny_decision(self, deny_envelope):
        """Pre-check returns False when decision is DENY."""
        assert can_execute_tool(deny_envelope, "sample_tool") is False


# =============================================================================
# Test 4: Tool denied when human_required = True
# =============================================================================


class TestToolDeniedHumanRequired:
    """Verify denial when human approval is required."""

    def test_denied_when_human_required(self, human_required_envelope):
        """Tool denied when human_required is True."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=human_required_envelope,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.HUMAN_REQUIRED
        assert "Human approval required" in error.message
        assert error.envelope_id == human_required_envelope.audit_ref

    def test_can_execute_returns_false_when_human_required(self, human_required_envelope):
        """Pre-check returns False when human approval needed."""
        assert can_execute_tool(human_required_envelope, "sample_tool") is False


# =============================================================================
# Test 5: Envelope tampering causes denial
# =============================================================================


class TestEnvelopeTamperingDenied:
    """Verify that envelope integrity is enforced."""

    def test_envelope_is_immutable(self, allow_envelope):
        """Envelope cannot be mutated after creation (frozen dataclass)."""
        # GatewayDecisionEnvelope is frozen, should raise on mutation
        with pytest.raises(Exception):  # FrozenInstanceError
            allow_envelope.decision = GatewayDecision.DENY  # type: ignore

    def test_invalid_envelope_type_denied(self):
        """Non-envelope objects are denied."""
        fake_envelope = {"decision": "ALLOW", "allowed_tools": ["sample_tool"]}

        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=fake_envelope,  # type: ignore
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        assert exc_info.value.reason_code == DenialReasonCode.INVALID_ENVELOPE
        assert "Invalid envelope type" in exc_info.value.message

    def test_reconstructed_envelope_requires_full_validation(self):
        """Manually created envelopes still go through full validation."""
        # Even if someone creates a new envelope, it must pass all gates
        fake_envelope = create_allow_envelope(
            agent_gid="GID-FAKE",
            intent_verb="execute",
            intent_target="test",
            allowed_tools=[],  # Empty!
        )

        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=fake_envelope,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        # Tool not in allowed_tools
        assert exc_info.value.reason_code == DenialReasonCode.TOOL_NOT_ALLOWED


# =============================================================================
# Test 6: Audit reference preserved on error
# =============================================================================


class TestAuditReferencePreserved:
    """Verify audit trail information is preserved on errors."""

    def test_audit_ref_in_denial(self, allow_envelope):
        """Audit reference included in denial exception."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=allow_envelope,
                tool_name="unauthorized_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.audit_ref is not None
        assert error.audit_ref != ""
        # audit_ref from CDE starts with "cde-"
        assert "cde-" in error.audit_ref or error.audit_ref == allow_envelope.audit_ref

    def test_envelope_id_in_denial(self, deny_envelope):
        """Envelope ID preserved in denial for tracing."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=deny_envelope,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.envelope_id == deny_envelope.audit_ref
        assert error.agent_gid == deny_envelope.agent_gid

    def test_error_has_timestamp(self, deny_envelope):
        """Denial errors include timestamp."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=deny_envelope,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        assert exc_info.value.timestamp is not None
        assert isinstance(exc_info.value.timestamp, datetime)

    def test_success_result_has_audit_trail(self, allow_envelope):
        """Successful execution includes full audit trail."""
        result = execute_tool(
            envelope=allow_envelope,
            tool_name="sample_tool",
            tool_callable=sample_tool,
            x=1,
            y=2,
        )

        assert result.envelope_id == allow_envelope.audit_ref
        assert result.agent_gid == allow_envelope.agent_gid
        assert result.tool_name == "sample_tool"
        assert isinstance(result.executed_at, datetime)


# =============================================================================
# Test 7: No tool executes without envelope
# =============================================================================


class TestNoExecutionWithoutEnvelope:
    """Verify that execution is impossible without envelope."""

    def test_none_envelope_denied(self):
        """None envelope causes denial."""
        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=None,
                tool_name="sample_tool",
                tool_callable=sample_tool,
                x=1,
                y=2,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.NO_ENVELOPE
        assert "No envelope provided" in error.message
        assert error.audit_ref == "NO_ENVELOPE"

    def test_can_execute_returns_false_without_envelope(self):
        """Pre-check returns False when envelope is None."""
        assert can_execute_tool(None, "sample_tool") is False

    def test_tool_not_called_without_envelope(self):
        """Tool callable is never invoked without valid envelope."""
        call_count = {"count": 0}

        def tracked_tool():
            call_count["count"] += 1
            return "executed"

        with pytest.raises(ToolExecutionDenied):
            execute_tool(
                envelope=None,
                tool_name="tracked_tool",
                tool_callable=tracked_tool,
            )

        # Tool was never called
        assert call_count["count"] == 0

    def test_tool_not_called_on_deny(self, deny_envelope):
        """Tool callable not invoked when decision is DENY."""
        call_count = {"count": 0}

        def tracked_tool():
            call_count["count"] += 1
            return "executed"

        with pytest.raises(ToolExecutionDenied):
            execute_tool(
                envelope=deny_envelope,
                tool_name="sample_tool",
                tool_callable=tracked_tool,
            )

        assert call_count["count"] == 0


# =============================================================================
# Additional Tests: Tool Executor Class
# =============================================================================


class TestToolExecutorClass:
    """Test the stateful ToolExecutor class."""

    def test_executor_with_fixed_envelope(self, allow_envelope):
        """ToolExecutor uses fixed envelope for all executions."""
        executor = ToolExecutor(allow_envelope)

        result = executor.execute(
            tool_name="sample_tool",
            tool_callable=sample_tool,
            x=10,
            y=20,
        )

        assert result.result == 30
        assert result.envelope_id == allow_envelope.audit_ref

    def test_executor_exposes_envelope(self, allow_envelope):
        """Executor provides read access to envelope."""
        executor = ToolExecutor(allow_envelope)
        assert executor.envelope is allow_envelope

    def test_executor_can_execute_check(self, allow_envelope):
        """Executor provides can_execute pre-check."""
        executor = ToolExecutor(allow_envelope)
        assert executor.can_execute("sample_tool") is True
        assert executor.can_execute("unauthorized_tool") is False


# =============================================================================
# Additional Tests: Execution Errors
# =============================================================================


class TestToolExecutionErrors:
    """Test handling of tool execution failures."""

    def test_tool_exception_wrapped(self):
        """Exceptions from tools are wrapped in ToolExecutionDenied."""
        # Create envelope that allows failing_tool
        envelope = create_allow_envelope(
            agent_gid="GID-01",
            intent_verb="execute",
            intent_target="test",
            allowed_tools=["failing_tool"],
        )

        with pytest.raises(ToolExecutionDenied) as exc_info:
            execute_tool(
                envelope=envelope,
                tool_name="failing_tool",
                tool_callable=failing_tool,
            )

        error = exc_info.value
        assert error.reason_code == DenialReasonCode.EXECUTION_ERROR
        assert "Tool internal error" in error.message


# =============================================================================
# Additional Tests: CDE Integration
# =============================================================================


class TestCDEIntegration:
    """Test integration with PAC-GATEWAY-01 CDE."""

    def test_cde_version_is_valid(self, allow_envelope):
        """CDE has valid version."""
        assert allow_envelope.version == CDE_VERSION

    def test_cde_audit_ref_format(self, allow_envelope):
        """CDE audit_ref has expected format."""
        # CDE audit refs start with "cde-"
        assert allow_envelope.audit_ref.startswith("cde-")

    def test_deny_envelope_has_empty_tools(self, deny_envelope):
        """DENY envelopes always have empty allowed_tools."""
        # This is enforced by create_deny_envelope
        assert deny_envelope.allowed_tools == []

    def test_multiple_envelopes_unique_audit_refs(self):
        """Each envelope gets a unique audit reference."""
        env1 = create_allow_envelope(
            agent_gid="GID-01",
            intent_verb="execute",
            intent_target="test",
            allowed_tools=["tool"],
        )
        env2 = create_allow_envelope(
            agent_gid="GID-01",
            intent_verb="execute",
            intent_target="test",
            allowed_tools=["tool"],
        )
        assert env1.audit_ref != env2.audit_ref
