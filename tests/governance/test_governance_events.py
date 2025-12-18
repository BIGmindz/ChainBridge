"""
🟣 DAN (GID-07) — Governance Event Tests
PAC-GOV-OBS-01: Governance Observability & Event Telemetry

Tests for:
- Event schema validation
- Event emission on ALLOW/DENY
- Event emission on Diggi correction
- Event emission on scope violation
- Failure tolerance (emission failures don't affect outcomes)
"""

import json
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.governance.event_sink import GovernanceEventEmitter, InMemorySink, JSONLFileSink, NullSink, emit_event, emitter
from core.governance.events import (
    GovernanceEvent,
    GovernanceEventType,
    acm_evaluated_event,
    artifact_verification_event,
    decision_allowed_event,
    decision_denied_event,
    decision_escalated_event,
    diggi_correction_event,
    drcp_triggered_event,
    governance_boot_event,
    scope_violation_event,
    tool_execution_event,
)
from core.governance.telemetry import (
    emit_acm_evaluation,
    emit_artifact_verification,
    emit_diggi_correction,
    emit_drcp_triggered,
    emit_scope_violation,
    emit_tool_execution,
    safe_emit,
)

# =============================================================================
# SCHEMA TESTS
# =============================================================================


class TestGovernanceEventSchema:
    """Tests for GovernanceEvent schema."""

    def test_event_has_required_fields(self) -> None:
        """Event should have required fields with defaults."""
        event = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)

        assert event.event_type == "ACM_EVALUATED"
        assert event.event_id.startswith("gov-")
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)

    def test_event_type_normalized_to_string(self) -> None:
        """Event type enum should be normalized to string."""
        event = GovernanceEvent(event_type=GovernanceEventType.DECISION_DENIED)
        assert event.event_type == "DECISION_DENIED"

    def test_event_type_accepts_string(self) -> None:
        """Event type should accept string directly."""
        event = GovernanceEvent(event_type="CUSTOM_EVENT")
        assert event.event_type == "CUSTOM_EVENT"

    def test_event_to_dict_serialization(self) -> None:
        """Event should serialize to dict correctly."""
        event = GovernanceEvent(
            event_type=GovernanceEventType.DECISION_ALLOWED,
            agent_gid="GID-07",
            verb="execute",
            target="test_tool",
            decision="ALLOW",
        )

        data = event.to_dict()

        assert data["event_type"] == "DECISION_ALLOWED"
        assert data["agent_gid"] == "GID-07"
        assert data["verb"] == "execute"
        assert data["target"] == "test_tool"
        assert data["decision"] == "ALLOW"
        assert "timestamp" in data
        assert "event_id" in data

    def test_event_to_dict_excludes_none_values(self) -> None:
        """Serialization should exclude None values."""
        event = GovernanceEvent(
            event_type=GovernanceEventType.ACM_EVALUATED,
            agent_gid="GID-07",
        )

        data = event.to_dict()

        assert "verb" not in data
        assert "target" not in data
        assert "reason_code" not in data

    def test_event_from_dict_deserialization(self) -> None:
        """Event should deserialize from dict correctly."""
        data = {
            "event_type": "DECISION_DENIED",
            "event_id": "gov-abc123",
            "timestamp": "2025-01-17T12:00:00+00:00",
            "agent_gid": "GID-05",
            "reason_code": "EXECUTE_NOT_PERMITTED",
        }

        event = GovernanceEvent.from_dict(data)

        assert event.event_type == "DECISION_DENIED"
        assert event.event_id == "gov-abc123"
        assert event.agent_gid == "GID-05"
        assert event.reason_code == "EXECUTE_NOT_PERMITTED"

    def test_event_metadata_dict(self) -> None:
        """Event should support arbitrary metadata."""
        event = GovernanceEvent(
            event_type=GovernanceEventType.SCOPE_VIOLATION,
            metadata={"pattern": "*.bot.py", "severity": "ERROR"},
        )

        data = event.to_dict()
        assert data["metadata"]["pattern"] == "*.bot.py"
        assert data["metadata"]["severity"] == "ERROR"


# =============================================================================
# EVENT FACTORY TESTS
# =============================================================================


class TestEventFactories:
    """Tests for event factory functions."""

    def test_acm_evaluated_event(self) -> None:
        """ACM evaluated event factory should work."""
        event = acm_evaluated_event(
            agent_gid="GID-05",
            verb="EXECUTE",
            target="deploy_tool",
            decision="ALLOW",
        )

        assert event.event_type == "ACM_EVALUATED"
        assert event.agent_gid == "GID-05"
        assert event.verb == "EXECUTE"
        assert event.target == "deploy_tool"
        assert event.decision == "ALLOW"

    def test_decision_allowed_event(self) -> None:
        """Decision allowed event factory should work."""
        event = decision_allowed_event(
            agent_gid="GID-07",
            verb="READ",
            target="config.yaml",
            audit_ref="audit-123",
        )

        assert event.event_type == "DECISION_ALLOWED"
        assert event.decision == "ALLOW"
        assert event.audit_ref == "audit-123"

    def test_decision_denied_event(self) -> None:
        """Decision denied event factory should work."""
        event = decision_denied_event(
            agent_gid="GID-03",
            verb="EXECUTE",
            target="dangerous_tool",
            reason_code="EXECUTE_NOT_PERMITTED",
        )

        assert event.event_type == "DECISION_DENIED"
        assert event.decision == "DENY"
        assert event.reason_code == "EXECUTE_NOT_PERMITTED"

    def test_decision_escalated_event(self) -> None:
        """Decision escalated event factory should work."""
        event = decision_escalated_event(
            agent_gid="GID-02",
            verb="APPROVE",
            target="payment",
            reason_code="REQUIRES_HUMAN",
        )

        assert event.event_type == "DECISION_ESCALATED"
        assert event.decision == "ESCALATE"

    def test_drcp_triggered_event(self) -> None:
        """DRCP triggered event factory should work."""
        event = drcp_triggered_event(
            agent_gid="GID-05",
            verb="EXECUTE",
            target="blocked_tool",
            reason_code="EXECUTE_NOT_PERMITTED",
        )

        assert event.event_type == "DRCP_TRIGGERED"
        assert event.reason_code == "EXECUTE_NOT_PERMITTED"

    def test_diggi_correction_event(self) -> None:
        """Diggi correction event factory should work."""
        event = diggi_correction_event(
            agent_gid="GID-00",
            target="original_intent",
            correction_type="PROPOSE_ALTERNATIVE",
        )

        assert event.event_type == "DIGGI_CORRECTION_ISSUED"
        assert event.metadata["correction_type"] == "PROPOSE_ALTERNATIVE"

    def test_tool_execution_allowed_event(self) -> None:
        """Tool execution allowed event factory should work."""
        event = tool_execution_event(
            agent_gid="GID-07",
            tool_name="deploy_service",
            allowed=True,
        )

        assert event.event_type == "TOOL_EXECUTION_ALLOWED"
        assert event.decision == "ALLOW"

    def test_tool_execution_denied_event(self) -> None:
        """Tool execution denied event factory should work."""
        event = tool_execution_event(
            agent_gid="GID-03",
            tool_name="delete_database",
            allowed=False,
            reason_code="NOT_IN_ALLOWED_TOOLS",
        )

        assert event.event_type == "TOOL_EXECUTION_DENIED"
        assert event.decision == "DENY"
        assert event.reason_code == "NOT_IN_ALLOWED_TOOLS"

    def test_artifact_verification_passed_event(self) -> None:
        """Artifact verification passed event factory should work."""
        event = artifact_verification_event(
            passed=True,
            artifact_hash="abc123def456",
            file_count=10,
        )

        assert event.event_type == "ARTIFACT_VERIFIED"
        assert event.decision == "PASS"
        assert event.artifact_hash == "abc123def456"
        assert event.metadata["file_count"] == 10

    def test_artifact_verification_failed_event(self) -> None:
        """Artifact verification failed event factory should work."""
        event = artifact_verification_event(
            passed=False,
            artifact_hash="abc123def456",
            mismatches=["file1.py", "file2.py"],
        )

        assert event.event_type == "ARTIFACT_VERIFICATION_FAILED"
        assert event.decision == "FAIL"
        assert event.metadata["mismatches"] == ["file1.py", "file2.py"]

    def test_scope_violation_event(self) -> None:
        """Scope violation event factory should work."""
        event = scope_violation_event(
            file_path="trading_bot.py",
            violation_type="FORBIDDEN_FILE",
            pattern=".*bot.*\\.py$",
        )

        assert event.event_type == "SCOPE_VIOLATION"
        assert event.target == "trading_bot.py"
        assert event.metadata["violation_type"] == "FORBIDDEN_FILE"
        assert event.metadata["pattern"] == ".*bot.*\\.py$"

    def test_governance_boot_passed_event(self) -> None:
        """Governance boot passed event factory should work."""
        event = governance_boot_event(
            passed=True,
            checks_passed=5,
        )

        assert event.event_type == "GOVERNANCE_BOOT_PASSED"
        assert event.decision == "PASS"
        assert event.metadata["checks_passed"] == 5

    def test_governance_boot_failed_event(self) -> None:
        """Governance boot failed event factory should work."""
        event = governance_boot_event(
            passed=False,
            checks_failed=2,
            failures=["check1", "check2"],
        )

        assert event.event_type == "GOVERNANCE_BOOT_FAILED"
        assert event.decision == "FAIL"
        assert event.metadata["failures"] == ["check1", "check2"]


# =============================================================================
# SINK TESTS
# =============================================================================


class TestJSONLFileSink:
    """Tests for JSONL file sink."""

    def test_sink_creates_file(self, tmp_path: Path) -> None:
        """Sink should create output file."""
        output_path = tmp_path / "events.jsonl"
        sink = JSONLFileSink(output_path)

        event = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)
        sink.emit(event)
        sink.close()

        assert output_path.exists()

    def test_sink_writes_jsonl(self, tmp_path: Path) -> None:
        """Sink should write valid JSONL."""
        output_path = tmp_path / "events.jsonl"
        sink = JSONLFileSink(output_path)

        event = GovernanceEvent(
            event_type=GovernanceEventType.DECISION_DENIED,
            agent_gid="GID-05",
        )
        sink.emit(event)
        sink.close()

        lines = output_path.read_text().strip().split("\n")
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["event_type"] == "DECISION_DENIED"
        assert data["agent_gid"] == "GID-05"

    def test_sink_appends_multiple_events(self, tmp_path: Path) -> None:
        """Sink should append multiple events."""
        output_path = tmp_path / "events.jsonl"
        sink = JSONLFileSink(output_path)

        for i in range(3):
            event = GovernanceEvent(
                event_type=GovernanceEventType.ACM_EVALUATED,
                metadata={"index": i},
            )
            sink.emit(event)

        sink.close()

        lines = output_path.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_sink_creates_parent_directories(self, tmp_path: Path) -> None:
        """Sink should create parent directories if needed."""
        output_path = tmp_path / "nested" / "path" / "events.jsonl"
        sink = JSONLFileSink(output_path)

        event = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)
        sink.emit(event)
        sink.close()

        assert output_path.exists()

    def test_sink_thread_safe(self, tmp_path: Path) -> None:
        """Sink should be thread-safe."""
        output_path = tmp_path / "events.jsonl"
        sink = JSONLFileSink(output_path)

        def emit_events():
            for _ in range(10):
                event = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)
                sink.emit(event)

        threads = [threading.Thread(target=emit_events) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        sink.close()

        lines = output_path.read_text().strip().split("\n")
        assert len(lines) == 50


class TestNullSink:
    """Tests for null sink."""

    def test_null_sink_discards_events(self) -> None:
        """Null sink should discard all events."""
        sink = NullSink()

        # Should not raise
        event = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)
        sink.emit(event)
        sink.close()


class TestInMemorySink:
    """Tests for in-memory sink."""

    def test_in_memory_sink_captures_events(self) -> None:
        """In-memory sink should capture events."""
        sink = InMemorySink()

        event1 = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)
        event2 = GovernanceEvent(event_type=GovernanceEventType.DECISION_DENIED)

        sink.emit(event1)
        sink.emit(event2)

        assert len(sink.events) == 2
        assert sink.events[0].event_type == "ACM_EVALUATED"
        assert sink.events[1].event_type == "DECISION_DENIED"

    def test_in_memory_sink_filter_by_type(self) -> None:
        """In-memory sink should filter by event type."""
        sink = InMemorySink()

        sink.emit(GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED))
        sink.emit(GovernanceEvent(event_type=GovernanceEventType.DECISION_DENIED))
        sink.emit(GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED))

        deny_events = sink.get_events("DECISION_DENIED")
        assert len(deny_events) == 1

        acm_events = sink.get_events("ACM_EVALUATED")
        assert len(acm_events) == 2

    def test_in_memory_sink_clear(self) -> None:
        """In-memory sink should support clearing."""
        sink = InMemorySink()

        sink.emit(GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED))
        sink.emit(GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED))

        sink.clear()

        assert len(sink.events) == 0


# =============================================================================
# EMITTER TESTS
# =============================================================================


class TestGovernanceEventEmitter:
    """Tests for global event emitter."""

    def test_emitter_fans_out_to_multiple_sinks(self) -> None:
        """Emitter should send events to all registered sinks."""
        test_emitter = GovernanceEventEmitter()
        sink1 = InMemorySink()
        sink2 = InMemorySink()

        test_emitter.add_sink(sink1)
        test_emitter.add_sink(sink2)

        event = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)
        test_emitter.emit(event)

        assert len(sink1.events) == 1
        assert len(sink2.events) == 1

        test_emitter.clear_sinks()

    def test_emitter_capture_context_manager(self) -> None:
        """Emitter capture context manager should work."""
        test_emitter = GovernanceEventEmitter()

        with test_emitter.capture() as sink:
            test_emitter.emit(GovernanceEvent(event_type=GovernanceEventType.DECISION_DENIED))
            test_emitter.emit(GovernanceEvent(event_type=GovernanceEventType.DECISION_ALLOWED))

            assert len(sink.events) == 2

    def test_emitter_disable_suppresses_events(self) -> None:
        """Disabled emitter should suppress events."""
        test_emitter = GovernanceEventEmitter()
        sink = InMemorySink()
        test_emitter.add_sink(sink)

        test_emitter.disable()
        test_emitter.emit(GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED))

        assert len(sink.events) == 0

        test_emitter.enable()
        test_emitter.emit(GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED))

        assert len(sink.events) == 1

        test_emitter.clear_sinks()


# =============================================================================
# FAILURE TOLERANCE TESTS
# =============================================================================


class TestFailureTolerance:
    """Tests that emission failures don't affect outcomes."""

    def test_safe_emit_swallows_errors(self) -> None:
        """safe_emit should swallow errors."""
        # Create a broken event that will fail serialization
        event = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)

        # Mock emit_event to raise
        with patch("core.governance.telemetry.emit_event") as mock_emit:
            mock_emit.side_effect = RuntimeError("Emission failed!")

            # Should not raise
            safe_emit(event)

    def test_jsonl_sink_swallows_write_errors(self, tmp_path: Path) -> None:
        """JSONL sink should swallow write errors."""
        # Create sink with invalid path (directory instead of file)
        sink = JSONLFileSink(tmp_path)  # tmp_path is a directory

        event = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)

        # Should not raise, even though writing to a directory will fail
        sink.emit(event)

    def test_emitter_continues_on_sink_failure(self) -> None:
        """Emitter should continue to other sinks if one fails."""
        test_emitter = GovernanceEventEmitter()

        # Create a failing sink
        failing_sink = MagicMock()
        failing_sink.emit.side_effect = RuntimeError("Sink failed!")

        # Create a working sink
        working_sink = InMemorySink()

        test_emitter.add_sink(failing_sink)
        test_emitter.add_sink(working_sink)

        event = GovernanceEvent(event_type=GovernanceEventType.ACM_EVALUATED)

        # Should not raise, and working sink should still receive event
        test_emitter.emit(event)

        assert len(working_sink.events) == 1

        test_emitter.clear_sinks()


# =============================================================================
# TELEMETRY INTEGRATION TESTS
# =============================================================================


class TestTelemetryIntegration:
    """Tests for telemetry helper functions."""

    def test_emit_acm_evaluation_on_allow(self) -> None:
        """Should emit events for ALLOW decision."""
        from core.governance.acm_evaluator import ACMDecision

        # Create mock EvaluationResult
        mock_result = MagicMock()
        mock_result.decision = ACMDecision.ALLOW
        mock_result.agent_gid = "GID-07"
        mock_result.intent_verb = "READ"
        mock_result.intent_target = "config.yaml"
        mock_result.reason = None
        mock_result.acm_version = "1.0.0"
        mock_result.correlation_id = "test-123"

        with patch("core.governance.telemetry.safe_emit") as mock_emit:
            emit_acm_evaluation(mock_result)

            # Should emit at least one event
            assert mock_emit.called

    def test_emit_drcp_triggered(self) -> None:
        """Should emit DRCP triggered event."""
        with patch("core.governance.telemetry.safe_emit") as mock_emit:
            emit_drcp_triggered(
                agent_gid="GID-05",
                verb="EXECUTE",
                target="blocked_tool",
                denial_code="EXECUTE_NOT_PERMITTED",
            )

            mock_emit.assert_called()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "DRCP_TRIGGERED"

    def test_emit_diggi_correction(self) -> None:
        """Should emit Diggi correction event."""
        with patch("core.governance.telemetry.safe_emit") as mock_emit:
            emit_diggi_correction(
                agent_gid="GID-00",
                target="original_intent",
                correction_type="PROPOSE_ALTERNATIVE",
            )

            mock_emit.assert_called()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "DIGGI_CORRECTION_ISSUED"

    def test_emit_tool_execution_allowed(self) -> None:
        """Should emit tool execution allowed event."""
        with patch("core.governance.telemetry.safe_emit") as mock_emit:
            emit_tool_execution(
                agent_gid="GID-07",
                tool_name="deploy_service",
                allowed=True,
            )

            mock_emit.assert_called()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "TOOL_EXECUTION_ALLOWED"

    def test_emit_tool_execution_denied(self) -> None:
        """Should emit tool execution denied event."""
        with patch("core.governance.telemetry.safe_emit") as mock_emit:
            emit_tool_execution(
                agent_gid="GID-03",
                tool_name="delete_database",
                allowed=False,
                reason_code="NOT_IN_ALLOWED_TOOLS",
            )

            mock_emit.assert_called()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "TOOL_EXECUTION_DENIED"

    def test_emit_artifact_verification(self) -> None:
        """Should emit artifact verification event."""
        with patch("core.governance.telemetry.safe_emit") as mock_emit:
            emit_artifact_verification(
                passed=True,
                aggregate_hash="abc123",
                file_count=10,
            )

            mock_emit.assert_called()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "ARTIFACT_VERIFIED"

    def test_emit_scope_violation(self) -> None:
        """Should emit scope violation event."""
        with patch("core.governance.telemetry.safe_emit") as mock_emit:
            emit_scope_violation(
                file_path="trading_bot.py",
                violation_type="FORBIDDEN_FILE",
            )

            mock_emit.assert_called()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "SCOPE_VIOLATION"
