"""
Color Gateway JSON-Spec Enforcement Tests - PAC-BENSON-COLOR-GATEWAY-ENFORCEMENT-IMPLEMENTATION-01

Test coverage for JSON-spec-based Color Gateway enforcement including:
- Exception-based stop-the-line enforcement
- JSON spec loading validation
- PAC header validation
- Negative cases for all violation types
"""
import pytest

from core.governance.color_gateway import (
    validate_execution,
    validate_pac_header,
    get_agent_color,
    get_color_agents,
    ColorGatewayViolation,
    ColorMismatchError,
    TealExecutionError,
    MissingFieldError,
    UnknownAgentError,
    UnknownColorError,
    SPEC_PATH,
    REGISTRY_PATH,
)


class TestSpecFilesExist:
    """Verify canonical spec files exist and are loadable."""

    def test_spec_path_exists(self):
        """color_gateway_spec.json exists."""
        assert SPEC_PATH.exists(), f"Spec file not found: {SPEC_PATH}"

    def test_registry_path_exists(self):
        """AGENT_REGISTRY.json exists."""
        assert REGISTRY_PATH.exists(), f"Registry file not found: {REGISTRY_PATH}"


class TestValidateExecutionPositive:
    """Test valid agent/color combinations via JSON spec."""

    def test_cody_blue_valid(self):
        """CODY (GID-01) is valid in BLUE lane."""
        result = validate_execution("GID-01", "BLUE", "PAC-TEST-01")
        assert result["valid"] is True
        assert result["agent_name"] == "CODY"
        assert result["gid"] == "GID-01"
        assert result["color"] == "BLUE"

    def test_atlas_blue_valid(self):
        """ATLAS (GID-11) is valid in BLUE lane."""
        result = validate_execution("GID-11", "BLUE", "PAC-TEST-02")
        assert result["valid"] is True
        assert result["agent_name"] == "ATLAS"
        assert result["color"] == "BLUE"

    def test_sonny_yellow_valid(self):
        """SONNY (GID-02) is valid in YELLOW lane."""
        result = validate_execution("GID-02", "YELLOW", "PAC-TEST-03")
        assert result["valid"] is True
        assert result["agent_name"] == "SONNY"

    def test_dan_green_valid(self):
        """DAN (GID-07) is valid in GREEN lane."""
        result = validate_execution("GID-07", "GREEN", "PAC-TEST-04")
        assert result["valid"] is True
        assert result["agent_name"] == "DAN"

    def test_alex_white_valid(self):
        """ALEX (GID-08) is valid in WHITE lane."""
        result = validate_execution("GID-08", "WHITE", "PAC-TEST-05")
        assert result["valid"] is True
        assert result["agent_name"] == "ALEX"

    def test_alex_grey_alias_valid(self):
        """ALEX (GID-08) is valid in GREY (alias for WHITE)."""
        result = validate_execution("GID-08", "GREY", "PAC-TEST-06")
        assert result["valid"] is True
        assert result["color"] == "WHITE"  # Normalized to WHITE

    def test_maggie_pink_valid(self):
        """MAGGIE (GID-10) is valid in PINK lane."""
        result = validate_execution("GID-10", "PINK", "PAC-TEST-07")
        assert result["valid"] is True

    def test_lira_pink_valid(self):
        """LIRA (GID-09) is valid in PINK lane."""
        result = validate_execution("GID-09", "PINK", "PAC-TEST-08")
        assert result["valid"] is True

    def test_sam_dark_red_valid(self):
        """SAM (GID-06) is valid in DARK_RED lane."""
        result = validate_execution("GID-06", "DARK_RED", "PAC-TEST-09")
        assert result["valid"] is True

    def test_pax_orange_valid(self):
        """PAX (GID-05) is valid in ORANGE lane."""
        result = validate_execution("GID-05", "ORANGE", "PAC-TEST-10")
        assert result["valid"] is True

    def test_mira_purple_valid(self):
        """MIRA_R (GID-03) is valid in PURPLE lane."""
        result = validate_execution("GID-03", "PURPLE", "PAC-TEST-11")
        assert result["valid"] is True

    def test_color_with_emoji_stripped(self):
        """Color with emoji prefix should be normalized."""
        result = validate_execution("GID-01", "🔵 BLUE", "PAC-TEST-12")
        assert result["valid"] is True
        assert result["color"] == "BLUE"

    def test_lowercase_gid_normalized(self):
        """GID should be case-normalized."""
        result = validate_execution("gid-01", "BLUE", "PAC-TEST-13")
        assert result["valid"] is True
        assert result["gid"] == "GID-01"


class TestTealExecutionRejection:
    """TEAL lane is orchestration-only and must be rejected as executing lane."""

    def test_teal_execution_rejected(self):
        """TEAL lane cannot be used as executing lane."""
        with pytest.raises(TealExecutionError) as exc_info:
            validate_execution("GID-00", "TEAL", "PAC-TEST-TEAL-01")
        assert "orchestration-only" in str(exc_info.value)
        assert "PAC-TEST-TEAL-01" in str(exc_info.value)

    def test_teal_with_emoji_rejected(self):
        """TEAL with emoji still rejected."""
        with pytest.raises(TealExecutionError):
            validate_execution("GID-00", "🟦🟩 TEAL", "PAC-TEST-TEAL-02")

    def test_teal_lowercase_rejected(self):
        """TEAL lowercase still rejected."""
        with pytest.raises(TealExecutionError):
            validate_execution("GID-00", "teal", "PAC-TEST-TEAL-03")


class TestColorMismatchRejection:
    """Agent/color mismatches must raise ColorMismatchError."""

    def test_cody_yellow_mismatch(self):
        """CODY (GID-01) cannot execute in YELLOW lane."""
        with pytest.raises(ColorMismatchError) as exc_info:
            validate_execution("GID-01", "YELLOW", "PAC-TEST-MISMATCH-01")
        assert "CODY" in str(exc_info.value)
        assert "GID-01" in str(exc_info.value)
        assert "YELLOW" in str(exc_info.value)

    def test_sonny_blue_mismatch(self):
        """SONNY (GID-02) cannot execute in BLUE lane."""
        with pytest.raises(ColorMismatchError) as exc_info:
            validate_execution("GID-02", "BLUE", "PAC-TEST-MISMATCH-02")
        assert "SONNY" in str(exc_info.value)
        assert "BLUE" in str(exc_info.value)

    def test_dan_pink_mismatch(self):
        """DAN (GID-07) cannot execute in PINK lane."""
        with pytest.raises(ColorMismatchError):
            validate_execution("GID-07", "PINK", "PAC-TEST-MISMATCH-03")

    def test_alex_blue_mismatch(self):
        """ALEX (GID-08) cannot execute in BLUE lane."""
        with pytest.raises(ColorMismatchError):
            validate_execution("GID-08", "BLUE", "PAC-TEST-MISMATCH-04")

    def test_maggie_green_mismatch(self):
        """MAGGIE (GID-10) cannot execute in GREEN lane."""
        with pytest.raises(ColorMismatchError):
            validate_execution("GID-10", "GREEN", "PAC-TEST-MISMATCH-05")

    def test_sam_blue_mismatch(self):
        """SAM (GID-06) cannot execute in BLUE lane."""
        with pytest.raises(ColorMismatchError):
            validate_execution("GID-06", "BLUE", "PAC-TEST-MISMATCH-06")


class TestMissingFieldRejection:
    """Missing required fields must raise MissingFieldError."""

    def test_missing_gid(self):
        """Missing GID raises MissingFieldError."""
        with pytest.raises(MissingFieldError) as exc_info:
            validate_execution("", "BLUE", "PAC-TEST-MISSING-01")
        assert "GID" in str(exc_info.value)

    def test_missing_color(self):
        """Missing color raises MissingFieldError."""
        with pytest.raises(MissingFieldError) as exc_info:
            validate_execution("GID-01", "", "PAC-TEST-MISSING-02")
        assert "COLOR" in str(exc_info.value)

    def test_none_gid(self):
        """None GID raises MissingFieldError."""
        with pytest.raises(MissingFieldError):
            validate_execution(None, "BLUE", "PAC-TEST-MISSING-03")

    def test_none_color(self):
        """None color raises MissingFieldError."""
        with pytest.raises(MissingFieldError):
            validate_execution("GID-01", None, "PAC-TEST-MISSING-04")


class TestUnknownAgentColorRejection:
    """Unknown agents/colors must raise appropriate errors."""

    def test_unknown_gid(self):
        """Unknown GID raises UnknownAgentError."""
        with pytest.raises(UnknownAgentError) as exc_info:
            validate_execution("GID-99", "BLUE", "PAC-TEST-UNKNOWN-01")
        assert "GID-99" in str(exc_info.value)

    def test_unknown_color(self):
        """Unknown color raises UnknownColorError."""
        with pytest.raises(UnknownColorError) as exc_info:
            validate_execution("GID-01", "RAINBOW", "PAC-TEST-UNKNOWN-02")
        assert "RAINBOW" in str(exc_info.value)


class TestValidatePacHeader:
    """Test validate_pac_header function for PAC ingress enforcement."""

    def test_valid_header(self):
        """Valid PAC header passes validation."""
        header = {
            "EXECUTING AGENT": "CODY",
            "EXECUTING GID": "GID-01",
            "EXECUTING COLOR": "BLUE",
            "PAC ID": "PAC-CODY-TEST-01",
        }
        result = validate_pac_header(header)
        assert result["valid"] is True
        assert result["agent_name"] == "CODY"

    def test_missing_executing_agent(self):
        """Missing EXECUTING AGENT raises MissingFieldError."""
        header = {
            "EXECUTING GID": "GID-01",
            "EXECUTING COLOR": "BLUE",
        }
        with pytest.raises(MissingFieldError) as exc_info:
            validate_pac_header(header)
        assert "EXECUTING AGENT" in str(exc_info.value)

    def test_missing_executing_gid(self):
        """Missing EXECUTING GID raises MissingFieldError."""
        header = {
            "EXECUTING AGENT": "CODY",
            "EXECUTING COLOR": "BLUE",
        }
        with pytest.raises(MissingFieldError) as exc_info:
            validate_pac_header(header)
        assert "EXECUTING GID" in str(exc_info.value)

    def test_missing_executing_color(self):
        """Missing EXECUTING COLOR raises MissingFieldError."""
        header = {
            "EXECUTING AGENT": "CODY",
            "EXECUTING GID": "GID-01",
        }
        with pytest.raises(MissingFieldError) as exc_info:
            validate_pac_header(header)
        assert "EXECUTING COLOR" in str(exc_info.value)

    def test_header_with_mismatch(self):
        """Header with color mismatch raises ColorMismatchError."""
        header = {
            "EXECUTING AGENT": "CODY",
            "EXECUTING GID": "GID-01",
            "EXECUTING COLOR": "YELLOW",  # Wrong color for CODY
            "PAC ID": "PAC-INVALID-01",
        }
        with pytest.raises(ColorMismatchError):
            validate_pac_header(header)

    def test_header_with_teal(self):
        """Header with TEAL as executing color raises TealExecutionError."""
        header = {
            "EXECUTING AGENT": "BENSON",
            "EXECUTING GID": "GID-00",
            "EXECUTING COLOR": "TEAL",
            "PAC ID": "PAC-TEAL-01",
        }
        with pytest.raises(TealExecutionError):
            validate_pac_header(header)


class TestExceptionHierarchy:
    """Test exception class hierarchy for catch-all handling."""

    def test_color_mismatch_is_violation(self):
        """ColorMismatchError is a ColorGatewayViolation."""
        assert issubclass(ColorMismatchError, ColorGatewayViolation)

    def test_teal_execution_is_violation(self):
        """TealExecutionError is a ColorGatewayViolation."""
        assert issubclass(TealExecutionError, ColorGatewayViolation)

    def test_missing_field_is_violation(self):
        """MissingFieldError is a ColorGatewayViolation."""
        assert issubclass(MissingFieldError, ColorGatewayViolation)

    def test_unknown_agent_is_violation(self):
        """UnknownAgentError is a ColorGatewayViolation."""
        assert issubclass(UnknownAgentError, ColorGatewayViolation)

    def test_unknown_color_is_violation(self):
        """UnknownColorError is a ColorGatewayViolation."""
        assert issubclass(UnknownColorError, ColorGatewayViolation)

    def test_catch_all_violations(self):
        """All violations can be caught with base ColorGatewayViolation."""
        caught = False
        try:
            validate_execution("GID-01", "YELLOW", "PAC-TEST")
        except ColorGatewayViolation:
            caught = True
        assert caught, "ColorMismatchError should be caught by ColorGatewayViolation"


class TestGetAgentColor:
    """Test get_agent_color function."""

    def test_cody_is_blue(self):
        """CODY's canonical color is BLUE."""
        assert get_agent_color("GID-01") == "BLUE"

    def test_benson_is_teal(self):
        """BENSON's canonical color is TEAL."""
        assert get_agent_color("GID-00") == "TEAL"

    def test_dan_is_green(self):
        """DAN's canonical color is GREEN."""
        assert get_agent_color("GID-07") == "GREEN"

    def test_unknown_gid_raises(self):
        """Unknown GID raises UnknownAgentError."""
        with pytest.raises(UnknownAgentError):
            get_agent_color("GID-99")


class TestGetColorAgents:
    """Test get_color_agents function."""

    def test_blue_agents(self):
        """BLUE lane has CODY and ATLAS."""
        agents = get_color_agents("BLUE")
        assert "GID-01" in agents
        assert "GID-11" in agents

    def test_yellow_agents(self):
        """YELLOW lane has SONNY only."""
        agents = get_color_agents("YELLOW")
        assert "GID-02" in agents

    def test_unknown_color_raises(self):
        """Unknown color raises UnknownColorError."""
        with pytest.raises(UnknownColorError):
            get_color_agents("RAINBOW")
