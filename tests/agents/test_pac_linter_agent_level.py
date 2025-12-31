"""
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
ATLAS — GID-11 — REPOSITORY INTEGRITY
PAC-ATLAS-AGENT-REGISTRY-ENFORCEMENT-01: PAC Linter Agent Level Tests
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵

Tests for PAC linter agent_level and deprecated agent enforcement.
Enforces HARD RULES:
- PACs with invalid agent_level fail
- PACs referencing deprecated agents fail
- No silent coercion or defaults
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.pac_linter import (
    LintViolation,
    ViolationSeverity,
    lint_agent_level_valid,
    lint_deprecated_agent,
)


# =============================================================================
# AGENT LEVEL VALIDATION TESTS
# =============================================================================


class TestAgentLevelValidation:
    """Test PAC linter agent_level rule."""

    def test_valid_l3_agent_passes(self):
        """Valid L3 agent (BENSON) passes validation."""
        content = """
════════════════════════════════════════════════════════════════════
🟦🟩🟦🟩🟦🟩🟦🟩🟦🟩
GID-00 — BENSON (ORCHESTRATOR)
PAC-BENSON-TEST-01 — Test PAC
🟦🟩🟦🟩🟦🟩🟦🟩🟦🟩
════════════════════════════════════════════════════════════════════

EXECUTING AGENT:
BENSON (GID-00) — 🟦🟩 TEAL

EXECUTING COLOR:
🟦🟩 TEAL — Orchestration Lane
"""
        violations = lint_agent_level_valid(content, Path("test.py"))
        assert len(violations) == 0

    def test_valid_l2_agent_passes(self):
        """Valid L2 agent (CODY) passes validation."""
        content = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-01 — CODY (BACKEND)
PAC-CODY-TEST-01 — Test PAC
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

EXECUTING AGENT:
CODY (GID-01) — 🔵 BLUE

EXECUTING COLOR:
🔵 BLUE — Backend Engineering
"""
        violations = lint_agent_level_valid(content, Path("test.py"))
        assert len(violations) == 0

    def test_valid_l1_agent_passes(self):
        """Valid L1 agent (ATLAS) passes validation."""
        content = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS (BUILD/REPAIR)
PAC-ATLAS-TEST-01 — Test PAC
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

EXECUTING AGENT:
ATLAS (GID-11) — 🔵 BLUE

EXECUTING COLOR:
🔵 BLUE — Repository Integrity Lane
"""
        violations = lint_agent_level_valid(content, Path("test.py"))
        assert len(violations) == 0

    def test_non_pac_file_skipped(self):
        """Non-PAC files are skipped."""
        content = """
def hello():
    print("Hello world")
"""
        violations = lint_agent_level_valid(content, Path("test.py"))
        assert len(violations) == 0


# =============================================================================
# DEPRECATED AGENT DETECTION TESTS
# =============================================================================


class TestDeprecatedAgentLinting:
    """Test PAC linter deprecated agent rule."""

    def test_valid_agent_passes(self):
        """Valid registered agent passes."""
        content = """
════════════════════════════════════════════════════════════════════
EXECUTING AGENT:
CODY (GID-01) — 🔵 BLUE
"""
        violations = lint_deprecated_agent(content, Path("test.py"))
        assert len(violations) == 0

    def test_deprecated_agent_fails(self):
        """Deprecated/unknown agent fails validation."""
        content = """
════════════════════════════════════════════════════════════════════
EXECUTING AGENT:
DANA (GID-99) — 🔵 BLUE
"""
        violations = lint_deprecated_agent(content, Path("test.py"))
        assert len(violations) == 1
        assert violations[0].severity == ViolationSeverity.ERROR
        assert violations[0].rule == "pac-deprecated-agent"
        assert "DANA" in violations[0].message

    def test_unknown_agent_fails(self):
        """Unknown agent fails validation."""
        content = """
════════════════════════════════════════════════════════════════════
EXECUTING AGENT:
FAKE_AGENT (GID-99) — 🔵 BLUE
"""
        violations = lint_deprecated_agent(content, Path("test.py"))
        assert len(violations) == 1
        assert "FAKE_AGENT" in violations[0].message

    def test_alias_passes(self):
        """Valid alias passes validation."""
        content = """
════════════════════════════════════════════════════════════════════
EXECUTING AGENT:
MIRA (GID-03) — 🟣 PURPLE
"""
        violations = lint_deprecated_agent(content, Path("test.py"))
        assert len(violations) == 0

    def test_non_pac_file_skipped(self):
        """Non-PAC files are skipped."""
        content = """
# Just a comment mentioning FAKE_AGENT
def hello():
    print("Hello world")
"""
        violations = lint_deprecated_agent(content, Path("test.py"))
        assert len(violations) == 0


# =============================================================================
# COMBINED RULE TESTS
# =============================================================================


class TestCombinedRules:
    """Test multiple rules working together."""

    def test_full_pac_header_valid(self):
        """Full valid PAC header passes all rules."""
        content = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS (REPO INTEGRITY & TOOLING)
PAC-ATLAS-AGENT-REGISTRY-ENFORCEMENT-01 — GOVERNANCE TOOLING
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

EXECUTING AGENT:
ATLAS (GID-11) — 🔵 BLUE

EXECUTING COLOR:
🔵 BLUE — Repository Integrity Lane

OBJECTIVE:
Test PAC for validation
"""
        level_violations = lint_agent_level_valid(content, Path("test.py"))
        deprecated_violations = lint_deprecated_agent(content, Path("test.py"))

        assert len(level_violations) == 0
        assert len(deprecated_violations) == 0

    def test_violation_includes_line_number(self):
        """Violations include line numbers for debugging."""
        content = """Line 1
Line 2
Line 3
EXECUTING AGENT:
FAKE_AGENT (GID-99) — 🔵 BLUE
Line 6
"""
        violations = lint_deprecated_agent(content, Path("test.py"))
        assert len(violations) == 1
        # Line number should be > 1 (where EXECUTING AGENT appears)
        assert violations[0].line >= 4

    def test_violation_is_error_severity(self):
        """Agent violations are ERROR severity (blocks merge)."""
        content = """
════════════════════════════════════════════════════════════════════
EXECUTING AGENT:
DANA (GID-99) — 🔵 BLUE
"""
        violations = lint_deprecated_agent(content, Path("test.py"))
        assert all(v.severity == ViolationSeverity.ERROR for v in violations)
