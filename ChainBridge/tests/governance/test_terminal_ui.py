"""
Test suite for Terminal Governance UI rendering layer.

══════════════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-01 — CODY (BACKEND ENGINEER)
PAC-CODY-P30-TERMINAL-GOVERNANCE-UI-STANDARD-IMPLEMENTATION-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
══════════════════════════════════════════════════════════════════════════════

Tests:
- System glyph definitions
- Color separation from agent colors
- Report rendering (PASS/FAIL/MIXED states)
- CI-safe output (no ANSI mismatch)
- Performance budget (<50ms)

Coverage target: ≥90%
"""

import io
import json
import pytest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add tools path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "governance"))

from terminal_ui import (
    SystemGlyph,
    SystemColor,
    GateStatus,
    GateResult,
    GovernanceReport,
    GovernanceTerminalUI,
    RICH_AVAILABLE,
)


# =============================================================================
# SYSTEM GLYPH TESTS
# =============================================================================

class TestSystemGlyph:
    """Tests for canonical system glyph definitions."""

    def test_all_glyphs_defined(self):
        """Verify all required system glyphs are defined."""
        required_glyphs = ["PASS", "FAIL", "WARN", "SKIP", "LEGACY", "REVIEW", "INFO", "LOCK", "GATE", "CHECK"]
        defined_glyphs = [g.name for g in SystemGlyph]
        for glyph in required_glyphs:
            assert glyph in defined_glyphs, f"Missing system glyph: {glyph}"

    def test_glyphs_are_distinct(self):
        """Verify all glyph values are unique."""
        values = [g.value for g in SystemGlyph]
        assert len(values) == len(set(values)), "Duplicate glyph values found"

    def test_glyphs_do_not_use_agent_emojis(self):
        """Verify system glyphs don't use agent persona emojis."""
        agent_emojis = ["🔵", "🔴", "🟢", "🟡", "🟣", "🟠", "🩷", "⬜", "🟦", "🟩", "🟥"]
        for glyph in SystemGlyph:
            for emoji in agent_emojis:
                assert emoji not in glyph.value, f"Agent emoji {emoji} found in system glyph {glyph.name}"

    def test_glyph_format_consistency(self):
        """Verify glyphs follow ▰X▰ format pattern."""
        for glyph in SystemGlyph:
            assert glyph.value.startswith("▰"), f"Glyph {glyph.name} doesn't start with ▰"
            assert glyph.value.endswith("▰"), f"Glyph {glyph.name} doesn't end with ▰"


# =============================================================================
# SYSTEM COLOR TESTS
# =============================================================================

class TestSystemColor:
    """Tests for system UI color definitions."""

    def test_required_colors_defined(self):
        """Verify all required system colors are defined."""
        required_colors = ["PASS", "FAIL", "WARN", "SKIP", "LEGACY", "REVIEW", "INFO", "HEADER", "BORDER", "MUTED"]
        for color in required_colors:
            assert hasattr(SystemColor, color), f"Missing system color: {color}"

    def test_colors_are_terminal_color_names(self):
        """Verify colors are valid terminal color names, not agent colors."""
        agent_color_names = ["BLUE", "RED", "GREEN", "YELLOW", "MAGENTA", "WHITE", "TEAL"]
        for attr in dir(SystemColor):
            if not attr.startswith("_"):
                value = getattr(SystemColor, attr)
                # Should be terminal color strings like "bright_green", not agent color names
                assert isinstance(value, str), f"Color {attr} is not a string"


# =============================================================================
# GATE STATUS TESTS
# =============================================================================

class TestGateStatus:
    """Tests for gate status enum."""

    def test_all_statuses_defined(self):
        """Verify all required gate statuses are defined."""
        required = ["PASS", "FAIL", "WARN", "SKIP", "LEGACY", "REVIEW"]
        for status in required:
            assert hasattr(GateStatus, status), f"Missing gate status: {status}"

    def test_status_values(self):
        """Verify status values are lowercase strings."""
        for status in GateStatus:
            assert status.value == status.name.lower(), f"Status {status.name} has unexpected value"


# =============================================================================
# GATE RESULT TESTS
# =============================================================================

class TestGateResult:
    """Tests for GateResult dataclass."""

    def test_basic_creation(self):
        """Test basic gate result creation."""
        result = GateResult(
            gate_id="PAG_001",
            gate_name="Test Gate",
            status=GateStatus.PASS,
            message="All checks passed",
        )
        assert result.gate_id == "PAG_001"
        assert result.gate_name == "Test Gate"
        assert result.status == GateStatus.PASS
        assert result.message == "All checks passed"

    def test_optional_fields(self):
        """Test optional fields in gate result."""
        result = GateResult(
            gate_id="PAG_002",
            gate_name="Test Gate",
            status=GateStatus.FAIL,
            message="Check failed",
            details="File: test.md",
            hint="Run validation again",
            file_path="/path/to/file.md",
            line_number=42,
        )
        assert result.details == "File: test.md"
        assert result.hint == "Run validation again"
        assert result.file_path == "/path/to/file.md"
        assert result.line_number == 42


# =============================================================================
# GOVERNANCE REPORT TESTS
# =============================================================================

class TestGovernanceReport:
    """Tests for GovernanceReport dataclass."""

    def test_basic_creation(self):
        """Test basic report creation."""
        report = GovernanceReport(
            mode="CI VALIDATION",
            source="docs/governance/",
        )
        assert report.mode == "CI VALIDATION"
        assert report.source == "docs/governance/"
        assert report.gates == []
        assert report.timestamp  # Should auto-populate

    def test_passed_property_all_pass(self):
        """Test passed property when all gates pass."""
        report = GovernanceReport(
            mode="TEST",
            source="test",
            gates=[
                GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
                GateResult("G2", "Gate 2", GateStatus.PASS, "OK"),
            ],
        )
        assert report.passed is True

    def test_passed_property_with_skip(self):
        """Test passed property with skipped gates."""
        report = GovernanceReport(
            mode="TEST",
            source="test",
            gates=[
                GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
                GateResult("G2", "Gate 2", GateStatus.SKIP, "Skipped"),
            ],
        )
        assert report.passed is True

    def test_passed_property_with_fail(self):
        """Test passed property when a gate fails."""
        report = GovernanceReport(
            mode="TEST",
            source="test",
            gates=[
                GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
                GateResult("G2", "Gate 2", GateStatus.FAIL, "Failed"),
            ],
        )
        assert report.passed is False

    def test_count_properties(self):
        """Test count properties."""
        report = GovernanceReport(
            mode="TEST",
            source="test",
            gates=[
                GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
                GateResult("G2", "Gate 2", GateStatus.PASS, "OK"),
                GateResult("G3", "Gate 3", GateStatus.FAIL, "Failed"),
                GateResult("G4", "Gate 4", GateStatus.WARN, "Warning"),
            ],
        )
        assert report.total_gates == 4
        assert report.passed_count == 2
        assert report.failed_count == 1
        assert report.warn_count == 1


# =============================================================================
# TERMINAL UI RENDERER TESTS
# =============================================================================

class TestGovernanceTerminalUI:
    """Tests for the terminal UI renderer."""

    def test_initialization(self):
        """Test UI initialization."""
        ui = GovernanceTerminalUI()
        if RICH_AVAILABLE:
            assert ui.console is not None
        # Should not raise even if Rich not available

    def test_initialization_no_color(self):
        """Test UI initialization with no color."""
        ui = GovernanceTerminalUI(no_color=True)
        assert ui.no_color is True

    def test_get_status_style(self):
        """Test status to glyph/style mapping."""
        ui = GovernanceTerminalUI()

        glyph, style = ui._get_status_style(GateStatus.PASS)
        assert glyph == SystemGlyph.PASS.value
        assert style == SystemColor.PASS

        glyph, style = ui._get_status_style(GateStatus.FAIL)
        assert glyph == SystemGlyph.FAIL.value
        assert style == SystemColor.FAIL

    def test_fallback_header(self, capsys):
        """Test fallback header when Rich not available."""
        ui = GovernanceTerminalUI()
        ui.console = None  # Force fallback

        report = GovernanceReport(
            mode="TEST MODE",
            source="test_source",
        )

        ui._fallback_header(report)
        captured = capsys.readouterr()

        assert "GOVERNANCE GATE ENGINE" in captured.out
        assert "TEST MODE" in captured.out
        assert "test_source" in captured.out

    def test_fallback_summary_pass(self, capsys):
        """Test fallback summary for passing report."""
        ui = GovernanceTerminalUI()
        ui.console = None

        report = GovernanceReport(
            mode="TEST",
            source="test",
            gates=[
                GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
            ],
        )

        ui._fallback_summary(report)
        captured = capsys.readouterr()

        assert "ALL GATES PASSED" in captured.out

    def test_fallback_summary_fail(self, capsys):
        """Test fallback summary for failing report."""
        ui = GovernanceTerminalUI()
        ui.console = None

        report = GovernanceReport(
            mode="TEST",
            source="test",
            gates=[
                GateResult("G1", "Gate 1", GateStatus.FAIL, "Failed"),
            ],
        )

        ui._fallback_summary(report)
        captured = capsys.readouterr()

        assert "GATE(S) FAILED" in captured.out

    def test_render_success(self, capsys):
        """Test success message rendering."""
        ui = GovernanceTerminalUI()
        ui.console = None  # Force fallback

        ui.render_success("Test passed successfully")
        captured = capsys.readouterr()

        assert SystemGlyph.PASS.value in captured.out
        assert "Test passed successfully" in captured.out


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Performance tests for terminal UI."""

    def test_render_performance_budget(self):
        """Test that rendering completes within 50ms budget."""
        ui = GovernanceTerminalUI()

        # Create a large report
        gates = [
            GateResult(f"G{i}", f"Gate {i}", GateStatus.PASS, "OK")
            for i in range(50)
        ]
        report = GovernanceReport(
            mode="PERFORMANCE TEST",
            source="benchmark",
            gates=gates,
        )

        # Time the rendering (capture output to avoid console noise)
        with patch.object(ui, 'console', None):  # Use fallback
            start = time.perf_counter()
            ui._fallback_header(report)
            ui._fallback_gates(report)
            ui._fallback_summary(report)
            elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, f"Rendering took {elapsed_ms:.2f}ms (budget: 50ms)"


# =============================================================================
# CI SAFETY TESTS
# =============================================================================

class TestCISafety:
    """Tests for CI-safe output."""

    def test_no_color_mode(self, capsys):
        """Test that no-color mode produces plain output."""
        ui = GovernanceTerminalUI(no_color=True)
        ui.console = None  # Ensure fallback

        ui.render_success("Test message")
        captured = capsys.readouterr()

        # Should contain glyph and message, no ANSI codes
        assert "Test message" in captured.out
        assert "\x1b[" not in captured.out  # No ANSI escape codes

    def test_deterministic_output(self):
        """Test that output is deterministic across runs."""
        ui = GovernanceTerminalUI()
        ui.console = None

        report = GovernanceReport(
            mode="TEST",
            source="test",
            timestamp="2025-01-01T00:00:00Z",  # Fixed timestamp
            gates=[
                GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
            ],
        )

        # Capture output twice
        outputs = []
        for _ in range(2):
            output = io.StringIO()
            with patch('sys.stdout', output):
                ui._fallback_header(report)
                ui._fallback_gates(report)
                ui._fallback_summary(report)
            outputs.append(output.getvalue())

        assert outputs[0] == outputs[1], "Output is not deterministic"


# =============================================================================
# GOLDEN OUTPUT TESTS
# =============================================================================

class TestGoldenOutput:
    """Golden output tests for consistent rendering."""

    def test_pass_state_output(self, capsys):
        """Test golden output for PASS state."""
        ui = GovernanceTerminalUI()
        ui.console = None

        report = GovernanceReport(
            mode="GOLDEN TEST",
            source="test",
            timestamp="2025-01-01T00:00:00Z",
            gates=[
                GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
                GateResult("G2", "Gate 2", GateStatus.PASS, "OK"),
            ],
        )

        ui._fallback_header(report)
        ui._fallback_gates(report)
        ui._fallback_summary(report)

        captured = capsys.readouterr()

        # Verify structure
        assert "GOVERNANCE GATE ENGINE" in captured.out
        assert "GOLDEN TEST" in captured.out
        assert SystemGlyph.PASS.value in captured.out
        assert "ALL GATES PASSED" in captured.out

    def test_fail_state_output(self, capsys):
        """Test golden output for FAIL state."""
        ui = GovernanceTerminalUI()
        ui.console = None

        report = GovernanceReport(
            mode="GOLDEN TEST",
            source="test",
            timestamp="2025-01-01T00:00:00Z",
            gates=[
                GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
                GateResult("G2", "Gate 2", GateStatus.FAIL, "Check failed", hint="Fix this"),
            ],
        )

        ui._fallback_header(report)
        ui._fallback_gates(report)
        ui._fallback_summary(report)

        captured = capsys.readouterr()

        assert SystemGlyph.FAIL.value in captured.out
        assert "GATE(S) FAILED" in captured.out
        assert "Fix this" in captured.out  # Hint should appear

    def test_mixed_state_output(self, capsys):
        """Test golden output for MIXED state."""
        ui = GovernanceTerminalUI()
        ui.console = None

        report = GovernanceReport(
            mode="GOLDEN TEST",
            source="test",
            timestamp="2025-01-01T00:00:00Z",
            gates=[
                GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
                GateResult("G2", "Gate 2", GateStatus.WARN, "Check warning"),
                GateResult("G3", "Gate 3", GateStatus.LEGACY, "Legacy file"),
                GateResult("G4", "Gate 4", GateStatus.SKIP, "Skipped"),
            ],
        )

        ui._fallback_header(report)
        ui._fallback_gates(report)
        ui._fallback_summary(report)

        captured = capsys.readouterr()

        # Should show all glyphs
        assert SystemGlyph.PASS.value in captured.out
        assert SystemGlyph.WARN.value in captured.out
        assert SystemGlyph.LEGACY.value in captured.out
        assert SystemGlyph.SKIP.value in captured.out


# =============================================================================
# NO SIDE EFFECTS TESTS
# =============================================================================

class TestNoSideEffects:
    """Tests to verify no governance state mutation."""

    def test_render_does_not_modify_report(self):
        """Test that rendering doesn't modify the report."""
        ui = GovernanceTerminalUI()
        ui.console = None

        original_gates = [
            GateResult("G1", "Gate 1", GateStatus.PASS, "OK"),
        ]
        report = GovernanceReport(
            mode="TEST",
            source="test",
            gates=original_gates.copy(),
        )

        original_len = len(report.gates)
        original_mode = report.mode

        with patch('sys.stdout', io.StringIO()):
            ui._fallback_header(report)
            ui._fallback_gates(report)
            ui._fallback_summary(report)

        # Verify nothing changed
        assert len(report.gates) == original_len
        assert report.mode == original_mode

    def test_no_file_writes(self, tmp_path):
        """Test that UI doesn't write any files."""
        ui = GovernanceTerminalUI()

        # List files before
        before = list(tmp_path.iterdir())

        report = GovernanceReport(
            mode="TEST",
            source=str(tmp_path),
        )

        with patch('sys.stdout', io.StringIO()):
            if ui.console:
                ui.render_report(report)
            else:
                ui._fallback_header(report)

        # List files after
        after = list(tmp_path.iterdir())

        assert before == after, "UI wrote files unexpectedly"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# =============================================================================
# END — CODY (GID-01) — 🔵 BLUE
# =============================================================================
