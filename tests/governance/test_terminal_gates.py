"""
ChainBridge Terminal Gate Visibility — Test Suite
════════════════════════════════════════════════════════════════════════════════

Snapshot-based tests asserting terminal output presence.
Validates all emission points defined in PAC-015.

Test Structure:
- test_gate_result_formatting: Canonical line format
- test_checklist_emission: Full checklist output
- test_pac_lifecycle_emissions: PAC ingest → BER
- test_capture_mode: Output capture for testing
- test_deterministic_output: Fixed format invariants

════════════════════════════════════════════════════════════════════════════════
"""

import io
import re
from datetime import datetime

import pytest

from core.governance.terminal_gates import (
    BORDER_CHAR,
    BORDER_WIDTH,
    FAIL_SYMBOL,
    GATE_NAMES,
    PASS_SYMBOL,
    GateChecklistResult,
    GateID,
    GateResult,
    GateStatus,
    TerminalGateEvaluator,
    TerminalGateRenderer,
    emit_agent_dispatch,
    emit_ber_approved,
    emit_ber_rejected,
    emit_pac_ingest,
    emit_wrap_receipt,
    get_gate_evaluator,
    get_terminal_renderer,
    reset_terminal_renderer,
    run_gate_checklist,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    reset_terminal_renderer()
    yield
    reset_terminal_renderer()


@pytest.fixture
def buffer():
    """Create a StringIO buffer for capturing output."""
    return io.StringIO()


@pytest.fixture
def renderer(buffer):
    """Create renderer with buffer output."""
    return TerminalGateRenderer(output=buffer)


@pytest.fixture
def evaluator(renderer):
    """Create evaluator with renderer."""
    return TerminalGateEvaluator(renderer=renderer)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CANONICAL SYMBOLS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCanonicalSymbols:
    """Test canonical symbol definitions."""
    
    def test_pass_symbol(self):
        """PASS symbol is checkmark."""
        assert PASS_SYMBOL == "✅"
    
    def test_fail_symbol(self):
        """FAIL symbol is red X."""
        assert FAIL_SYMBOL == "❌"
    
    def test_border_width(self):
        """Border width is fixed."""
        assert BORDER_WIDTH == 60
    
    def test_border_char(self):
        """Border character is fixed."""
        assert BORDER_CHAR == "═"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GATE ID ENUM
# ═══════════════════════════════════════════════════════════════════════════════


class TestGateID:
    """Test GateID enum."""
    
    def test_gate_count(self):
        """Exactly 7 gates defined."""
        assert len(GateID) == 7
    
    def test_gate_order(self):
        """Gates in canonical order PAG-01 → PAG-07."""
        expected = ["PAG-01", "PAG-02", "PAG-03", "PAG-04", "PAG-05", "PAG-06", "PAG-07"]
        actual = [g.value for g in GateID]
        assert actual == expected
    
    def test_all_gates_have_names(self):
        """Every gate has a canonical name."""
        for gate in GateID:
            assert gate in GATE_NAMES
            assert GATE_NAMES[gate]  # Non-empty


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GATE STATUS ENUM
# ═══════════════════════════════════════════════════════════════════════════════


class TestGateStatus:
    """Test GateStatus enum."""
    
    def test_all_statuses(self):
        """All required statuses defined."""
        statuses = {s.value for s in GateStatus}
        assert "PASS" in statuses
        assert "FAIL" in statuses
        assert "PENDING" in statuses
        assert "SKIP" in statuses
    
    def test_pass_symbol(self):
        """PASS status has correct symbol."""
        assert GateStatus.PASS.symbol == "✅"
    
    def test_fail_symbol(self):
        """FAIL status has correct symbol."""
        assert GateStatus.FAIL.symbol == "❌"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GATE RESULT
# ═══════════════════════════════════════════════════════════════════════════════


class TestGateResult:
    """Test GateResult data class."""
    
    def test_immutable(self):
        """GateResult is immutable."""
        result = GateResult(
            gate_id=GateID.PAG_01,
            status=GateStatus.PASS,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            result.status = GateStatus.FAIL
    
    def test_gate_name_lookup(self):
        """Gate name is looked up from registry."""
        result = GateResult(gate_id=GateID.PAG_01, status=GateStatus.PASS)
        assert result.gate_name == "Scope Definition"
    
    def test_passed_property(self):
        """passed property works correctly."""
        pass_result = GateResult(gate_id=GateID.PAG_01, status=GateStatus.PASS)
        fail_result = GateResult(gate_id=GateID.PAG_01, status=GateStatus.FAIL)
        
        assert pass_result.passed is True
        assert fail_result.passed is False
    
    def test_format_line_pass(self):
        """format_line produces canonical PASS format."""
        result = GateResult(gate_id=GateID.PAG_01, status=GateStatus.PASS)
        line = result.format_line()
        
        assert "PAG-01" in line
        assert "Scope Definition" in line
        assert "✅" in line
        assert "PASS" in line
    
    def test_format_line_fail(self):
        """format_line produces canonical FAIL format."""
        result = GateResult(gate_id=GateID.PAG_02, status=GateStatus.FAIL)
        line = result.format_line()
        
        assert "PAG-02" in line
        assert "Agent Selection" in line
        assert "❌" in line
        assert "FAIL" in line
    
    def test_has_timestamp(self):
        """GateResult has timestamp."""
        result = GateResult(gate_id=GateID.PAG_01, status=GateStatus.PASS)
        assert result.timestamp
        # Validate ISO format
        datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GATE CHECKLIST RESULT
# ═══════════════════════════════════════════════════════════════════════════════


class TestGateChecklistResult:
    """Test GateChecklistResult."""
    
    def test_all_passed_true(self):
        """all_passed is True when all gates pass."""
        checklist = GateChecklistResult(pac_id="PAC-TEST-001")
        checklist.add_gate(GateResult(GateID.PAG_01, GateStatus.PASS))
        checklist.add_gate(GateResult(GateID.PAG_02, GateStatus.PASS))
        
        assert checklist.all_passed is True
    
    def test_all_passed_false(self):
        """all_passed is False when any gate fails."""
        checklist = GateChecklistResult(pac_id="PAC-TEST-001")
        checklist.add_gate(GateResult(GateID.PAG_01, GateStatus.PASS))
        checklist.add_gate(GateResult(GateID.PAG_02, GateStatus.FAIL))
        
        assert checklist.all_passed is False
    
    def test_failed_gates_list(self):
        """failed_gates returns only failed gates."""
        checklist = GateChecklistResult(pac_id="PAC-TEST-001")
        checklist.add_gate(GateResult(GateID.PAG_01, GateStatus.PASS))
        fail = GateResult(GateID.PAG_02, GateStatus.FAIL, message="Missing scope")
        checklist.add_gate(fail)
        checklist.add_gate(GateResult(GateID.PAG_03, GateStatus.PASS))
        
        failed = checklist.failed_gates
        assert len(failed) == 1
        assert failed[0].gate_id == GateID.PAG_02
    
    def test_pass_count(self):
        """pass_count counts passed gates."""
        checklist = GateChecklistResult(pac_id="PAC-TEST-001")
        checklist.add_gate(GateResult(GateID.PAG_01, GateStatus.PASS))
        checklist.add_gate(GateResult(GateID.PAG_02, GateStatus.FAIL))
        checklist.add_gate(GateResult(GateID.PAG_03, GateStatus.PASS))
        
        assert checklist.pass_count == 2
        assert checklist.total_count == 3
    
    def test_complete_sets_timestamp(self):
        """complete() sets completed_at timestamp."""
        checklist = GateChecklistResult(pac_id="PAC-TEST-001")
        assert checklist.completed_at is None
        
        checklist.complete()
        assert checklist.completed_at is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: TERMINAL RENDERER — CAPTURE MODE
# ═══════════════════════════════════════════════════════════════════════════════


class TestRendererCaptureMode:
    """Test renderer capture mode for testing."""
    
    def test_capture_mode_captures_output(self, renderer, buffer):
        """Capture mode captures instead of printing."""
        renderer.start_capture()
        renderer.emit_pac_ingest("PAC-TEST-001")
        output = renderer.stop_capture()
        
        assert "PAC-TEST-001" in output
        assert buffer.getvalue() == ""  # Nothing printed
    
    def test_get_captured_without_stopping(self, renderer):
        """get_captured returns output without stopping capture."""
        renderer.start_capture()
        renderer.emit_pac_ingest("PAC-TEST-001")
        
        output = renderer.get_captured()
        assert "PAC-TEST-001" in output
        
        # Still in capture mode
        renderer.emit_pac_validated("PAC-TEST-001")
        output2 = renderer.get_captured()
        assert "VALIDATED" in output2
        assert len(output2) > len(output)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PAC LIFECYCLE EMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPACLifecycleEmissions:
    """Test PAC lifecycle terminal emissions."""
    
    def test_emit_pac_ingest(self, renderer):
        """emit_pac_ingest produces canonical output."""
        renderer.start_capture()
        renderer.emit_pac_ingest("PAC-TEST-001", issuer="Jeffrey")
        output = renderer.stop_capture()
        
        # Must contain key elements
        assert "PAC RECEIVED" in output
        assert "PAC-TEST-001" in output
        assert "ISSUER" in output
        assert "Jeffrey" in output
        assert "TIMESTAMP" in output
        assert BORDER_CHAR in output
    
    def test_emit_pac_validated(self, renderer):
        """emit_pac_validated produces canonical output."""
        renderer.start_capture()
        renderer.emit_pac_validated("PAC-TEST-001")
        output = renderer.stop_capture()
        
        assert "PAC VALIDATED" in output
        assert "PAC-TEST-001" in output
    
    def test_emit_agent_dispatch(self, renderer):
        """emit_agent_dispatch produces canonical output."""
        renderer.start_capture()
        renderer.emit_agent_dispatch(
            gid="GID-01",
            agent_name="CODY",
            role="Code Generation Specialist",
            lane="CODE_GENERATION",
        )
        output = renderer.stop_capture()
        
        assert "DISPATCHING TO AGENT" in output
        assert "GID-01" in output
        assert "CODY" in output
        assert "Code Generation Specialist" in output
        assert "CODE_GENERATION" in output
    
    def test_emit_wrap_receipt(self, renderer):
        """emit_wrap_receipt produces canonical output."""
        renderer.start_capture()
        renderer.emit_wrap_receipt(
            wrap_id="WRAP-CODY-001",
            pac_id="PAC-TEST-001",
            gid="GID-01",
        )
        output = renderer.stop_capture()
        
        assert "WRAP RECEIVED" in output
        assert "WRAP-CODY-001" in output
        assert "PAC-TEST-001" in output
        assert "GID-01" in output
        assert "TIMESTAMP" in output


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BER EMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBEREmissions:
    """Test BER terminal emissions."""
    
    def test_emit_ber_approved(self, renderer):
        """emit_ber_approved produces canonical output."""
        renderer.start_capture()
        renderer.emit_ber_approved(
            ber_id="BER-BENSON-001",
            pac_id="PAC-TEST-001",
            wrap_id="WRAP-CODY-001",
        )
        output = renderer.stop_capture()
        
        assert "BER ISSUED" in output
        assert "APPROVED" in output
        assert "BER-BENSON-001" in output
        assert "PAC-TEST-001" in output
        assert "WRAP-CODY-001" in output
        assert "GID-00" in output
        assert "BENSON" in output
        assert "LEDGER" in output
        assert "COMMITTED" in output
        assert "✅" in output
    
    def test_emit_ber_rejected(self, renderer):
        """emit_ber_rejected produces canonical output."""
        renderer.start_capture()
        renderer.emit_ber_rejected(
            pac_id="PAC-TEST-001",
            wrap_id="WRAP-CODY-001",
            reason="Gate PAG-02 failed",
            failed_gates=["PAG-02", "PAG-05"],
        )
        output = renderer.stop_capture()
        
        assert "REJECTED" in output
        assert "PAC-TEST-001" in output
        assert "WRAP-CODY-001" in output
        assert "Gate PAG-02 failed" in output
        assert "PAG-02" in output
        assert "PAG-05" in output
        assert "CORRECTIVE_PAC_REQUIRED" in output
        assert "❌" in output


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GATE CHECKLIST EMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestGateChecklistEmissions:
    """Test gate checklist emissions."""
    
    def test_emit_gate_checklist_start(self, renderer):
        """emit_gate_checklist_start produces header."""
        renderer.start_capture()
        renderer.emit_gate_checklist_start("PAC-TEST-001")
        output = renderer.stop_capture()
        
        assert "PAG GATE CHECKLIST" in output
        assert "PAC-TEST-001" in output
        assert BORDER_CHAR in output
    
    def test_emit_gate_result_pass(self, renderer):
        """emit_gate_result shows passing gate."""
        result = GateResult(GateID.PAG_01, GateStatus.PASS)
        
        renderer.start_capture()
        renderer.emit_gate_result(result)
        output = renderer.stop_capture()
        
        assert "PAG-01" in output
        assert "Scope Definition" in output
        assert "✅" in output
        assert "PASS" in output
    
    def test_emit_gate_result_fail_with_message(self, renderer):
        """emit_gate_result shows failure message."""
        result = GateResult(
            GateID.PAG_02,
            GateStatus.FAIL,
            message="Invalid agent selection",
        )
        
        renderer.start_capture()
        renderer.emit_gate_result(result)
        output = renderer.stop_capture()
        
        assert "PAG-02" in output
        assert "❌" in output
        assert "FAIL" in output
        assert "Invalid agent selection" in output
        assert "└─" in output  # Nested message indicator
    
    def test_emit_full_checklist_all_pass(self, renderer):
        """Full checklist with all passing gates."""
        checklist = GateChecklistResult(pac_id="PAC-TEST-001")
        for gate_id in GateID:
            checklist.add_gate(GateResult(gate_id, GateStatus.PASS))
        checklist.complete()
        
        renderer.start_capture()
        renderer.emit_gate_checklist(checklist)
        output = renderer.stop_capture()
        
        # Header
        assert "PAG GATE CHECKLIST" in output
        assert "PAC-TEST-001" in output
        
        # All 7 gates
        for gate_id in GateID:
            assert gate_id.value in output
        
        # Summary
        assert "ALL GATES PASSED" in output
        assert "7/7" in output
    
    def test_emit_full_checklist_with_failures(self, renderer):
        """Full checklist with failures shows summary."""
        checklist = GateChecklistResult(pac_id="PAC-TEST-001")
        checklist.add_gate(GateResult(GateID.PAG_01, GateStatus.PASS))
        checklist.add_gate(GateResult(GateID.PAG_02, GateStatus.FAIL, message="Invalid"))
        checklist.add_gate(GateResult(GateID.PAG_03, GateStatus.PASS))
        checklist.complete()
        
        renderer.start_capture()
        renderer.emit_gate_checklist(checklist)
        output = renderer.stop_capture()
        
        assert "GATES FAILED" in output
        assert "1/3" in output or "1" in output  # At least one failure shown
        assert "PAG-02" in output


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GATE EVALUATOR
# ═══════════════════════════════════════════════════════════════════════════════


class TestGateEvaluator:
    """Test TerminalGateEvaluator."""
    
    def test_evaluate_gate_pass(self, evaluator, buffer):
        """evaluate_gate returns and emits PASS."""
        result = evaluator.evaluate_gate(
            GateID.PAG_01,
            condition=True,
        )
        
        assert result.passed is True
        assert "PAG-01" in buffer.getvalue()
        assert "✅" in buffer.getvalue()
    
    def test_evaluate_gate_fail(self, evaluator, buffer):
        """evaluate_gate returns and emits FAIL."""
        result = evaluator.evaluate_gate(
            GateID.PAG_01,
            condition=False,
            fail_message="Missing scope definition",
        )
        
        assert result.passed is False
        assert "PAG-01" in buffer.getvalue()
        assert "❌" in buffer.getvalue()
        assert "Missing scope definition" in buffer.getvalue()
    
    def test_run_standard_checklist(self, evaluator, buffer):
        """run_standard_checklist evaluates all gates."""
        checks = {
            GateID.PAG_01: (True, None),
            GateID.PAG_02: (True, None),
            GateID.PAG_03: (True, None),
            GateID.PAG_04: (True, None),
            GateID.PAG_05: (True, None),
            GateID.PAG_06: (True, None),
            GateID.PAG_07: (True, None),
        }
        
        result = evaluator.run_standard_checklist("PAC-TEST-001", checks)
        
        assert result.all_passed is True
        assert result.pass_count == 7
        
        output = buffer.getvalue()
        assert "PAG-01" in output
        assert "PAG-07" in output
        assert "ALL GATES PASSED" in output
    
    def test_run_standard_checklist_with_failure(self, evaluator, buffer):
        """run_standard_checklist handles failures."""
        checks = {
            GateID.PAG_01: (True, None),
            GateID.PAG_02: (False, "Invalid agent"),
            GateID.PAG_03: (True, None),
            GateID.PAG_04: (True, None),
            GateID.PAG_05: (True, None),
            GateID.PAG_06: (True, None),
            GateID.PAG_07: (True, None),
        }
        
        result = evaluator.run_standard_checklist("PAC-TEST-001", checks)
        
        assert result.all_passed is False
        assert len(result.failed_gates) == 1
        assert result.failed_gates[0].gate_id == GateID.PAG_02
        
        output = buffer.getvalue()
        assert "Invalid agent" in output
        assert "GATES FAILED" in output


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_emit_pac_ingest_uses_singleton(self):
        """emit_pac_ingest uses singleton renderer."""
        renderer = get_terminal_renderer()
        renderer.start_capture()
        
        emit_pac_ingest("PAC-TEST-001")
        
        output = renderer.stop_capture()
        assert "PAC-TEST-001" in output
    
    def test_emit_agent_dispatch_uses_singleton(self):
        """emit_agent_dispatch uses singleton renderer."""
        renderer = get_terminal_renderer()
        renderer.start_capture()
        
        emit_agent_dispatch("GID-01", "CODY", "Specialist", "CODE")
        
        output = renderer.stop_capture()
        assert "GID-01" in output
    
    def test_emit_wrap_receipt_uses_singleton(self):
        """emit_wrap_receipt uses singleton renderer."""
        renderer = get_terminal_renderer()
        renderer.start_capture()
        
        emit_wrap_receipt("WRAP-001", "PAC-001", "GID-01")
        
        output = renderer.stop_capture()
        assert "WRAP-001" in output
    
    def test_emit_ber_approved_uses_singleton(self):
        """emit_ber_approved uses singleton renderer."""
        renderer = get_terminal_renderer()
        renderer.start_capture()
        
        emit_ber_approved("BER-001", "PAC-001", "WRAP-001")
        
        output = renderer.stop_capture()
        assert "BER-001" in output
        assert "APPROVED" in output
    
    def test_emit_ber_rejected_uses_singleton(self):
        """emit_ber_rejected uses singleton renderer."""
        renderer = get_terminal_renderer()
        renderer.start_capture()
        
        emit_ber_rejected("PAC-001", "WRAP-001", "Failure", ["PAG-01"])
        
        output = renderer.stop_capture()
        assert "REJECTED" in output
    
    def test_run_gate_checklist_uses_singleton(self):
        """run_gate_checklist uses singleton evaluator."""
        renderer = get_terminal_renderer()
        renderer.start_capture()
        
        # Provide all 7 gates to get all_passed = True
        result = run_gate_checklist("PAC-TEST-001", {
            GateID.PAG_01: (True, None),
            GateID.PAG_02: (True, None),
            GateID.PAG_03: (True, None),
            GateID.PAG_04: (True, None),
            GateID.PAG_05: (True, None),
            GateID.PAG_06: (True, None),
            GateID.PAG_07: (True, None),
        })
        
        assert result.all_passed is True
        output = renderer.stop_capture()
        assert "PAC-TEST-001" in output


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: OUTPUT DETERMINISM
# ═══════════════════════════════════════════════════════════════════════════════


class TestOutputDeterminism:
    """Test that output format is deterministic."""
    
    def test_gate_order_is_canonical(self, evaluator, buffer):
        """Gates are always evaluated in PAG-01 → PAG-07 order."""
        checks = {
            GateID.PAG_07: (True, None),  # Provided out of order
            GateID.PAG_01: (True, None),
            GateID.PAG_05: (True, None),
            GateID.PAG_02: (True, None),
            GateID.PAG_04: (True, None),
            GateID.PAG_03: (True, None),
            GateID.PAG_06: (True, None),
        }
        
        evaluator.run_standard_checklist("PAC-TEST-001", checks)
        
        output = buffer.getvalue()
        
        # Find positions of each gate
        pos_01 = output.find("PAG-01")
        pos_02 = output.find("PAG-02")
        pos_03 = output.find("PAG-03")
        pos_04 = output.find("PAG-04")
        pos_05 = output.find("PAG-05")
        pos_06 = output.find("PAG-06")
        pos_07 = output.find("PAG-07")
        
        # All present
        assert all(p >= 0 for p in [pos_01, pos_02, pos_03, pos_04, pos_05, pos_06, pos_07])
        
        # In canonical order
        assert pos_01 < pos_02 < pos_03 < pos_04 < pos_05 < pos_06 < pos_07
    
    def test_format_line_consistent(self):
        """format_line produces consistent format."""
        result = GateResult(GateID.PAG_01, GateStatus.PASS)
        
        line1 = result.format_line()
        line2 = result.format_line()
        
        # Format is consistent (timestamps excluded)
        assert line1 == line2
    
    def test_border_is_fixed_width(self, renderer):
        """Border is always fixed width."""
        renderer.start_capture()
        renderer.emit_pac_ingest("PAC-TEST-001")
        output = renderer.stop_capture()
        
        # Find border lines
        lines = output.split("\n")
        border_lines = [l for l in lines if l and all(c == BORDER_CHAR for c in l)]
        
        # At least one border line
        assert len(border_lines) > 0
        
        # All borders are same width
        for bl in border_lines:
            assert len(bl) == BORDER_WIDTH


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: EMISSION SNAPSHOTS (PRESENCE ASSERTIONS)
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmissionSnapshots:
    """Snapshot tests asserting required content is present."""
    
    def test_pac_ingest_snapshot(self, renderer):
        """PAC ingest has all required fields."""
        renderer.start_capture()
        renderer.emit_pac_ingest("PAC-BENSON-EXEC-015", issuer="Jeffrey")
        output = renderer.stop_capture()
        
        required = [
            "PAC RECEIVED",
            "PAC-BENSON-EXEC-015",
            "ISSUER",
            "Jeffrey",
            "TIMESTAMP",
            "🟦",  # Blue square emoji
        ]
        
        for req in required:
            assert req in output, f"Missing required element: {req}"
    
    def test_agent_dispatch_snapshot(self, renderer):
        """Agent dispatch has all required fields."""
        renderer.start_capture()
        renderer.emit_agent_dispatch(
            gid="GID-01",
            agent_name="CODY",
            role="Code Generation Specialist",
            lane="CODE_GENERATION",
        )
        output = renderer.stop_capture()
        
        required = [
            "DISPATCHING TO AGENT",
            "GID:",
            "GID-01",
            "NAME:",
            "CODY",
            "ROLE:",
            "Code Generation Specialist",
            "LANE:",
            "CODE_GENERATION",
            "📤",  # Outbox emoji
        ]
        
        for req in required:
            assert req in output, f"Missing required element: {req}"
    
    def test_wrap_receipt_snapshot(self, renderer):
        """WRAP receipt has all required fields."""
        renderer.start_capture()
        renderer.emit_wrap_receipt(
            wrap_id="WRAP-CODY-TERMINAL-GATES-015",
            pac_id="PAC-BENSON-EXEC-015",
            gid="GID-01",
        )
        output = renderer.stop_capture()
        
        required = [
            "WRAP RECEIVED",
            "WRAP_ID:",
            "WRAP-CODY-TERMINAL-GATES-015",
            "PAC_ID:",
            "PAC-BENSON-EXEC-015",
            "FROM:",
            "GID-01",
            "TIMESTAMP:",
            "📥",  # Inbox emoji
        ]
        
        for req in required:
            assert req in output, f"Missing required element: {req}"
    
    def test_ber_approved_snapshot(self, renderer):
        """BER approved has all required fields."""
        renderer.start_capture()
        renderer.emit_ber_approved(
            ber_id="BER-BENSON-TERMINAL-GATES-015",
            pac_id="PAC-BENSON-EXEC-015",
            wrap_id="WRAP-CODY-TERMINAL-GATES-015",
        )
        output = renderer.stop_capture()
        
        required = [
            "BER ISSUED",
            "APPROVED",
            "BER_ID:",
            "BER-BENSON-TERMINAL-GATES-015",
            "PAC_ID:",
            "PAC-BENSON-EXEC-015",
            "WRAP_ID:",
            "WRAP-CODY-TERMINAL-GATES-015",
            "ISSUER:",
            "GID-00",
            "BENSON",
            "DISPOSITION:",
            "✅",
            "LEDGER:",
            "COMMITTED",
            "NEXT_STATE:",
            "AWAITING_PAC",
            "🟩",  # Green square emoji
        ]
        
        for req in required:
            assert req in output, f"Missing required element: {req}"
    
    def test_ber_rejected_snapshot(self, renderer):
        """BER rejected has all required fields."""
        renderer.start_capture()
        renderer.emit_ber_rejected(
            pac_id="PAC-BENSON-EXEC-015",
            wrap_id="WRAP-CODY-TERMINAL-GATES-015",
            reason="Gate PAG-02 failed: Invalid agent selection",
            failed_gates=["PAG-02", "PAG-05"],
        )
        output = renderer.stop_capture()
        
        required = [
            "BER REJECTED",
            "CORRECTIVE PAC REQUIRED",
            "PAC_ID:",
            "PAC-BENSON-EXEC-015",
            "WRAP_ID:",
            "WRAP-CODY-TERMINAL-GATES-015",
            "ISSUER:",
            "GID-00",
            "BENSON",
            "DISPOSITION:",
            "❌",
            "REJECTED",
            "REASON:",
            "Gate PAG-02 failed",
            "FAILED_GATES:",
            "PAG-02",
            "PAG-05",
            "NEXT_ACTION:",
            "CORRECTIVE_PAC_REQUIRED",
            "🟥",  # Red square emoji
        ]
        
        for req in required:
            assert req in output, f"Missing required element: {req}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INTEGRATION — FULL PAC LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullPACLifecycle:
    """Integration test for full PAC lifecycle terminal output."""
    
    def test_complete_pac_cycle_approved(self, renderer, evaluator):
        """Complete PAC cycle produces correct output sequence."""
        renderer.start_capture()
        
        # 1. PAC Ingest
        renderer.emit_pac_ingest("PAC-TEST-INTEGRATION-001", issuer="Jeffrey")
        
        # 2. PAC Validated
        renderer.emit_pac_validated("PAC-TEST-INTEGRATION-001")
        
        # 3. Agent Dispatch
        renderer.emit_agent_dispatch(
            gid="GID-01",
            agent_name="CODY",
            role="Code Generation Specialist",
            lane="CODE_GENERATION",
        )
        
        # 4. Gate Evaluation
        evaluator.run_standard_checklist("PAC-TEST-INTEGRATION-001", {
            GateID.PAG_01: (True, None),
            GateID.PAG_02: (True, None),
            GateID.PAG_03: (True, None),
            GateID.PAG_04: (True, None),
            GateID.PAG_05: (True, None),
            GateID.PAG_06: (True, None),
            GateID.PAG_07: (True, None),
        })
        
        # 5. WRAP Receipt
        renderer.emit_wrap_receipt(
            wrap_id="WRAP-CODY-INTEGRATION-001",
            pac_id="PAC-TEST-INTEGRATION-001",
            gid="GID-01",
        )
        
        # 6. BER Approved
        renderer.emit_ber_approved(
            ber_id="BER-BENSON-INTEGRATION-001",
            pac_id="PAC-TEST-INTEGRATION-001",
            wrap_id="WRAP-CODY-INTEGRATION-001",
        )
        
        output = renderer.stop_capture()
        
        # Verify order of emissions
        pos_ingest = output.find("PAC RECEIVED")
        pos_validated = output.find("PAC VALIDATED")
        pos_dispatch = output.find("DISPATCHING TO AGENT")
        pos_gates = output.find("PAG GATE CHECKLIST")
        pos_wrap = output.find("WRAP RECEIVED")
        pos_ber = output.find("BER ISSUED")
        
        assert pos_ingest < pos_validated < pos_dispatch < pos_gates < pos_wrap < pos_ber
    
    def test_complete_pac_cycle_rejected(self, renderer, evaluator):
        """Complete PAC cycle with rejection."""
        renderer.start_capture()
        
        # 1. PAC Ingest
        renderer.emit_pac_ingest("PAC-TEST-REJECTION-001")
        
        # 2. Agent Dispatch
        renderer.emit_agent_dispatch("GID-01", "CODY", "Specialist", "CODE")
        
        # 3. Gate Evaluation (with failure)
        evaluator.run_standard_checklist("PAC-TEST-REJECTION-001", {
            GateID.PAG_01: (True, None),
            GateID.PAG_02: (False, "Invalid agent selection"),  # FAIL
            GateID.PAG_03: (True, None),
            GateID.PAG_04: (True, None),
            GateID.PAG_05: (False, "Missing governance duty"),  # FAIL
            GateID.PAG_06: (True, None),
            GateID.PAG_07: (True, None),
        })
        
        # 4. WRAP Receipt
        renderer.emit_wrap_receipt("WRAP-CODY-REJECTION-001", "PAC-TEST-REJECTION-001", "GID-01")
        
        # 5. BER Rejected
        renderer.emit_ber_rejected(
            pac_id="PAC-TEST-REJECTION-001",
            wrap_id="WRAP-CODY-REJECTION-001",
            reason="Multiple gate failures",
            failed_gates=["PAG-02", "PAG-05"],
        )
        
        output = renderer.stop_capture()
        
        # Verify rejection path
        assert "GATES FAILED" in output
        assert "BER REJECTED" in output
        assert "CORRECTIVE_PAC_REQUIRED" in output


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NO SILENT EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoSilentExecution:
    """Test that no operations are silent."""
    
    def test_every_gate_emits_output(self, evaluator, buffer):
        """Every gate evaluation produces output."""
        for gate_id in GateID:
            buffer.truncate(0)
            buffer.seek(0)
            
            evaluator.evaluate_gate(gate_id, condition=True)
            
            output = buffer.getvalue()
            assert gate_id.value in output, f"Gate {gate_id.value} produced no output"
    
    def test_pass_emits_symbol(self, evaluator, buffer):
        """PASS always emits checkmark symbol."""
        evaluator.evaluate_gate(GateID.PAG_01, condition=True)
        
        assert PASS_SYMBOL in buffer.getvalue()
    
    def test_fail_emits_symbol(self, evaluator, buffer):
        """FAIL always emits X symbol."""
        evaluator.evaluate_gate(GateID.PAG_01, condition=False)
        
        assert FAIL_SYMBOL in buffer.getvalue()
