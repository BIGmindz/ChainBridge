"""
END Banner Enforcement Tests — PAC-BENSON-CODY-END-BANNER-LINT-ENFORCEMENT-01

Test coverage for END banner validation in PAC linter:
- Missing END banner
- Wrong color emoji band
- Wrong agent name
- Wrong GID
- Mixed-color banner
- Valid canonical banner (PASS)
"""
import pytest
from pathlib import Path
from unittest.mock import Mock

from tools.pac_linter import (
    lint_end_banner_present,
    lint_end_banner_agent_match,
    lint_end_banner_gid_match,
    lint_end_banner_color_match,
    ViolationSeverity,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST DATA
# ═══════════════════════════════════════════════════════════════════════════════

VALID_CODY_PAC = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-CODY-TEST-01
EXECUTING AGENT: CODY (GID-01)
EXECUTING COLOR: 🔵 BLUE
════════════════════════════════════════════════════════════════════

Content here...

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — CODY (GID-01) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""

VALID_DAN_PAC = """
════════════════════════════════════════════════════════════════════
�🟩🟩🟩🟩🟩🟩🟩🟩🟩
PAC-DAN-TEST-01
EXECUTING AGENT: DAN (GID-07)
EXECUTING COLOR: 🟩 GREEN
════════════════════════════════════════════════════════════════════

Content here...

════════════════════════════════════════════════════════════════════
🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩
END — DAN (GID-07) — 🟩 GREEN
🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩
════════════════════════════════════════════════════════════════════
"""

VALID_ALEX_PAC = """
════════════════════════════════════════════════════════════════════
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
PAC-ALEX-TEST-01
EXECUTING AGENT: ALEX (GID-08)
EXECUTING COLOR: ⚪ WHITE
════════════════════════════════════════════════════════════════════

Content here...

════════════════════════════════════════════════════════════════════
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
END — ALEX (GID-08) — ⚪ WHITE
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
════════════════════════════════════════════════════════════════════
"""

MISSING_END_BANNER_PAC = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-CODY-TEST-01
EXECUTING AGENT: CODY (GID-01)
EXECUTING COLOR: 🔵 BLUE
════════════════════════════════════════════════════════════════════

Content here...

🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""

WRONG_AGENT_END_BANNER = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-CODY-TEST-01
EXECUTING AGENT: CODY (GID-01)
EXECUTING COLOR: 🔵 BLUE
════════════════════════════════════════════════════════════════════

Content here...

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — DAN (GID-01) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""

WRONG_GID_END_BANNER = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-CODY-TEST-01
EXECUTING AGENT: CODY (GID-01)
EXECUTING COLOR: 🔵 BLUE
════════════════════════════════════════════════════════════════════

Content here...

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — CODY (GID-07) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""

WRONG_COLOR_END_BANNER = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-CODY-TEST-01
EXECUTING AGENT: CODY (GID-01)
EXECUTING COLOR: 🔵 BLUE
════════════════════════════════════════════════════════════════════

Content here...

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — CODY (GID-01) — 🟢 GREEN
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""

WRONG_EMOJI_END_BANNER = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-CODY-TEST-01
EXECUTING AGENT: CODY (GID-01)
EXECUTING COLOR: 🔵 BLUE
════════════════════════════════════════════════════════════════════

Content here...

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — CODY (GID-01) — 🟢 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""

NOT_A_PAC_FILE = """
# Just a regular Python file

def hello():
    return "world"
"""


class TestEndBannerPresent:
    """Test lint_end_banner_present rule."""

    def test_valid_pac_has_end_banner(self):
        """Valid PAC with END banner passes."""
        violations = lint_end_banner_present(VALID_CODY_PAC, Path("test.py"))
        assert len(violations) == 0

    def test_missing_end_banner_fails(self):
        """PAC without END banner fails."""
        violations = lint_end_banner_present(MISSING_END_BANNER_PAC, Path("test.py"))
        assert len(violations) == 1
        assert violations[0].rule == "pac-end-banner-present"
        assert violations[0].severity == ViolationSeverity.ERROR

    def test_non_pac_file_skipped(self):
        """Non-PAC files are skipped."""
        violations = lint_end_banner_present(NOT_A_PAC_FILE, Path("test.py"))
        assert len(violations) == 0


class TestEndBannerAgentMatch:
    """Test lint_end_banner_agent_match rule."""

    def test_matching_agent_passes(self):
        """END banner with matching agent passes."""
        violations = lint_end_banner_agent_match(VALID_CODY_PAC, Path("test.py"))
        assert len(violations) == 0

    def test_wrong_agent_fails(self):
        """END banner with wrong agent fails."""
        violations = lint_end_banner_agent_match(WRONG_AGENT_END_BANNER, Path("test.py"))
        assert len(violations) == 1
        assert violations[0].rule == "pac-end-banner-agent-match"
        assert violations[0].severity == ViolationSeverity.ERROR
        assert "DAN" in violations[0].message
        assert "CODY" in violations[0].message


class TestEndBannerGidMatch:
    """Test lint_end_banner_gid_match rule."""

    def test_matching_gid_passes(self):
        """END banner with matching GID passes."""
        violations = lint_end_banner_gid_match(VALID_CODY_PAC, Path("test.py"))
        assert len(violations) == 0

    def test_wrong_gid_fails(self):
        """END banner with wrong GID fails."""
        violations = lint_end_banner_gid_match(WRONG_GID_END_BANNER, Path("test.py"))
        assert len(violations) == 1
        assert violations[0].rule == "pac-end-banner-gid-match"
        assert violations[0].severity == ViolationSeverity.ERROR
        assert "GID-07" in violations[0].message
        assert "GID-01" in violations[0].message


class TestEndBannerColorMatch:
    """Test lint_end_banner_color_match rule."""

    def test_matching_color_passes(self):
        """END banner with matching color passes."""
        violations = lint_end_banner_color_match(VALID_CODY_PAC, Path("test.py"))
        assert len(violations) == 0

    def test_wrong_color_fails(self):
        """END banner with wrong color fails."""
        violations = lint_end_banner_color_match(WRONG_COLOR_END_BANNER, Path("test.py"))
        # May produce 1 or 2 violations (emoji mismatch + color mismatch)
        assert len(violations) >= 1
        assert any(v.rule == "pac-end-banner-color-match" for v in violations)
        assert any(v.severity == ViolationSeverity.ERROR for v in violations)
        # At least one violation mentions the color mismatch
        assert any("GREEN" in v.message for v in violations)

    def test_wrong_emoji_fails(self):
        """END banner with wrong emoji fails."""
        violations = lint_end_banner_color_match(WRONG_EMOJI_END_BANNER, Path("test.py"))
        assert len(violations) == 1
        assert violations[0].rule == "pac-end-banner-color-match"
        assert violations[0].severity == ViolationSeverity.ERROR


class TestEndBannerAllAgents:
    """Test END banner validation for different agents."""

    def test_dan_valid_banner(self):
        """Valid DAN PAC passes all checks."""
        violations = []
        violations.extend(lint_end_banner_present(VALID_DAN_PAC, Path("test.py")))
        violations.extend(lint_end_banner_agent_match(VALID_DAN_PAC, Path("test.py")))
        violations.extend(lint_end_banner_gid_match(VALID_DAN_PAC, Path("test.py")))
        violations.extend(lint_end_banner_color_match(VALID_DAN_PAC, Path("test.py")))
        assert len(violations) == 0

    def test_alex_valid_banner(self):
        """Valid ALEX PAC passes all checks."""
        violations = []
        violations.extend(lint_end_banner_present(VALID_ALEX_PAC, Path("test.py")))
        violations.extend(lint_end_banner_agent_match(VALID_ALEX_PAC, Path("test.py")))
        violations.extend(lint_end_banner_gid_match(VALID_ALEX_PAC, Path("test.py")))
        violations.extend(lint_end_banner_color_match(VALID_ALEX_PAC, Path("test.py")))
        assert len(violations) == 0


class TestEndBannerHardFail:
    """Test that END banner violations are ERROR (not WARNING)."""

    def test_missing_banner_is_error(self):
        """Missing END banner is ERROR severity."""
        violations = lint_end_banner_present(MISSING_END_BANNER_PAC, Path("test.py"))
        assert all(v.severity == ViolationSeverity.ERROR for v in violations)

    def test_wrong_agent_is_error(self):
        """Wrong agent in END banner is ERROR severity."""
        violations = lint_end_banner_agent_match(WRONG_AGENT_END_BANNER, Path("test.py"))
        assert all(v.severity == ViolationSeverity.ERROR for v in violations)

    def test_wrong_gid_is_error(self):
        """Wrong GID in END banner is ERROR severity."""
        violations = lint_end_banner_gid_match(WRONG_GID_END_BANNER, Path("test.py"))
        assert all(v.severity == ViolationSeverity.ERROR for v in violations)

    def test_wrong_color_is_error(self):
        """Wrong color in END banner is ERROR severity."""
        violations = lint_end_banner_color_match(WRONG_COLOR_END_BANNER, Path("test.py"))
        assert all(v.severity == ViolationSeverity.ERROR for v in violations)
