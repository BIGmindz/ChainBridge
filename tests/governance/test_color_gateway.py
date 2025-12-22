"""
Color Gateway Enforcement Tests — PAC-BENSON-COLOR-GATEWAY-ENFORCEMENT-CODE-01

Tests verify:
1. PAC header field validation (agent, GID, color)
2. Agent ↔ color consistency
3. TEAL reservation for GID-00 only
4. Emoji ↔ color matching
5. Non-bypassable failure modes
"""

import pytest

from core.governance.agent_roster import (
    AGENT_CANONICAL_COLORS,
    COLOR_LANES,
    EMOJI_TO_COLOR,
    TEAL_RESERVED_GIDS,
    get_agent_color,
    is_teal_allowed,
    validate_agent_color,
    validate_color_gateway,
    validate_teal_usage,
)


class TestAgentColorMapping:
    """Test canonical agent → color mapping."""

    def test_benson_is_teal(self):
        """Benson (GID-00) is TEAL."""
        assert get_agent_color("BENSON") == "TEAL"

    def test_dan_is_green(self):
        """Dan (GID-07) is GREEN."""
        assert get_agent_color("DAN") == "GREEN"

    def test_sam_is_dark_red(self):
        """Sam (GID-06) is DARK RED."""
        assert get_agent_color("SAM") == "DARK RED"

    def test_alex_is_white(self):
        """Alex (GID-08) is WHITE."""
        assert get_agent_color("ALEX") == "WHITE"

    def test_cody_is_blue(self):
        """Cody (GID-01) is BLUE."""
        assert get_agent_color("CODY") == "BLUE"

    def test_all_agents_have_colors(self):
        """Every registered agent has a canonical color."""
        expected_agents = [
            "BENSON", "CODY", "SONNY", "MIRA-R", "CINDY",
            "PAX", "SAM", "DAN", "ALEX", "LIRA", "MAGGIE", "ATLAS"
        ]
        for agent in expected_agents:
            color = get_agent_color(agent)
            assert color is not None, f"Agent {agent} missing color"
            assert color in COLOR_LANES, f"Color {color} not in lanes"


class TestTealReservation:
    """Test TEAL color reservation for Benson only."""

    def test_teal_allowed_for_gid_00(self):
        """TEAL is allowed for GID-00."""
        assert is_teal_allowed("GID-00") is True

    def test_teal_forbidden_for_gid_01(self):
        """TEAL is forbidden for GID-01 (Cody)."""
        assert is_teal_allowed("GID-01") is False

    def test_teal_forbidden_for_gid_07(self):
        """TEAL is forbidden for GID-07 (Dan)."""
        assert is_teal_allowed("GID-07") is False

    def test_teal_forbidden_for_gid_08(self):
        """TEAL is forbidden for GID-08 (Alex)."""
        assert is_teal_allowed("GID-08") is False

    def test_validate_teal_usage_benson_passes(self):
        """Benson using TEAL passes validation."""
        valid, error = validate_teal_usage("BENSON", "GID-00", "TEAL")
        assert valid is True
        assert error == ""

    def test_validate_teal_usage_dan_fails(self):
        """Dan using TEAL fails validation."""
        valid, error = validate_teal_usage("DAN", "GID-07", "TEAL")
        assert valid is False
        assert "TEAL" in error
        assert "GID-00" in error

    def test_validate_teal_usage_non_teal_passes(self):
        """Non-TEAL colors pass for any agent."""
        valid, error = validate_teal_usage("DAN", "GID-07", "GREEN")
        assert valid is True


class TestAgentColorValidation:
    """Test agent ↔ color consistency validation."""

    def test_dan_green_passes(self):
        """Dan declaring GREEN passes."""
        valid, error = validate_agent_color("DAN", "GREEN")
        assert valid is True
        assert error == ""

    def test_dan_blue_fails(self):
        """Dan declaring BLUE fails."""
        valid, error = validate_agent_color("DAN", "BLUE")
        assert valid is False
        assert "DAN" in error
        assert "GREEN" in error

    def test_benson_teal_passes(self):
        """Benson declaring TEAL passes."""
        valid, error = validate_agent_color("BENSON", "TEAL")
        assert valid is True

    def test_alex_white_passes(self):
        """Alex declaring WHITE passes."""
        valid, error = validate_agent_color("ALEX", "WHITE")
        assert valid is True

    def test_alex_teal_fails(self):
        """Alex declaring TEAL fails (wrong color)."""
        valid, error = validate_agent_color("ALEX", "TEAL")
        assert valid is False
        assert "WHITE" in error

    def test_unknown_agent_fails(self):
        """Unknown agent fails validation."""
        valid, error = validate_agent_color("UNKNOWN_AGENT", "BLUE")
        assert valid is False
        assert "Unknown" in error


class TestFullColorGatewayValidation:
    """Test full color gateway validation."""

    def test_valid_dan_pac(self):
        """Valid Dan PAC passes all checks."""
        valid, errors = validate_color_gateway(
            agent_name="DAN",
            gid="GID-07",
            declared_color="GREEN",
            declared_emoji="🟢",
        )
        assert valid is True
        assert len(errors) == 0

    def test_valid_benson_pac(self):
        """Valid Benson PAC passes all checks."""
        valid, errors = validate_color_gateway(
            agent_name="BENSON",
            gid="GID-00",
            declared_color="TEAL",
            declared_emoji="🟦🟩",
        )
        assert valid is True
        assert len(errors) == 0

    def test_gid_mismatch_fails(self):
        """Mismatched GID fails."""
        valid, errors = validate_color_gateway(
            agent_name="DAN",
            gid="GID-01",  # Wrong! Dan is GID-07
            declared_color="GREEN",
        )
        assert valid is False
        assert any("GID mismatch" in e for e in errors)

    def test_color_mismatch_fails(self):
        """Mismatched color fails."""
        valid, errors = validate_color_gateway(
            agent_name="DAN",
            gid="GID-07",
            declared_color="BLUE",  # Wrong! Dan is GREEN
        )
        assert valid is False
        assert any("GREEN" in e for e in errors)

    def test_unauthorized_teal_fails(self):
        """Unauthorized TEAL usage fails."""
        valid, errors = validate_color_gateway(
            agent_name="ALEX",
            gid="GID-08",
            declared_color="TEAL",  # Forbidden!
        )
        assert valid is False
        # Should fail for both wrong color AND teal reservation
        assert len(errors) >= 1

    def test_emoji_color_mismatch_fails(self):
        """Emoji ↔ color mismatch fails."""
        valid, errors = validate_color_gateway(
            agent_name="DAN",
            gid="GID-07",
            declared_color="GREEN",
            declared_emoji="🔵",  # Wrong! This is BLUE
        )
        assert valid is False
        assert any("🔵" in e for e in errors)

    def test_unknown_agent_fails(self):
        """Unknown agent fails immediately."""
        valid, errors = validate_color_gateway(
            agent_name="FAKE_AGENT",
            gid="GID-99",
            declared_color="GREEN",
        )
        assert valid is False
        assert any("Unknown" in e for e in errors)


class TestEmojiToColorMapping:
    """Test emoji → color mapping."""

    def test_green_emoji_is_green(self):
        """🟢 maps to GREEN."""
        assert EMOJI_TO_COLOR.get("🟢") == "GREEN"

    def test_blue_emoji_is_blue(self):
        """🔵 maps to BLUE."""
        assert EMOJI_TO_COLOR.get("🔵") == "BLUE"

    def test_teal_dual_emoji(self):
        """🟦🟩 maps to TEAL."""
        assert EMOJI_TO_COLOR.get("🟦🟩") == "TEAL"

    def test_white_emoji_is_white(self):
        """⚪ maps to WHITE."""
        assert EMOJI_TO_COLOR.get("⚪") == "WHITE"

    def test_red_emoji_is_dark_red(self):
        """🔴 maps to DARK RED."""
        assert EMOJI_TO_COLOR.get("🔴") == "DARK RED"


class TestColorLanes:
    """Test color → lane mapping."""

    def test_teal_is_orchestration(self):
        """TEAL lane is Orchestration."""
        assert COLOR_LANES.get("TEAL") == "Orchestration"

    def test_green_is_devops(self):
        """GREEN lane is DevOps."""
        assert COLOR_LANES.get("GREEN") == "DevOps"

    def test_blue_is_backend(self):
        """BLUE lane is Backend Engineering."""
        assert COLOR_LANES.get("BLUE") == "Backend Engineering"

    def test_white_is_governance(self):
        """WHITE lane is Governance."""
        assert COLOR_LANES.get("WHITE") == "Governance"

    def test_dark_red_is_security(self):
        """DARK RED lane is Security."""
        assert COLOR_LANES.get("DARK RED") == "Security"
