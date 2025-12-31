"""
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
ATLAS — GID-11 — REPOSITORY INTEGRITY
PAC-ATLAS-AGENT-REGISTRY-ENFORCEMENT-01: Registry Schema Validation Tests
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵

Tests for the extended canonical agent registry schema validation.
Enforces HARD RULES:
- Invalid schema fails hard
- Missing required fields fail hard
- Illegal mutations are detected
- No backward compatibility acceptance
"""

import copy
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.governance.agent_roster import (
    ALWAYS_IMMUTABLE_FIELDS,
    REQUIRED_AGENT_FIELDS,
    REQUIRED_REGISTRY_FIELDS,
    VALID_AGENT_LEVELS,
    _REGISTRY_DATA,
    get_agent_diversity_profile,
    get_agent_level,
    get_registry_version,
    is_deprecated_agent,
    is_field_mutable,
    validate_mutability,
    validate_registry_schema,
)


# =============================================================================
# SCHEMA VALIDATION — REQUIRED FIELDS
# =============================================================================


class TestRequiredTopLevelFields:
    """Test that required top-level registry fields are enforced."""

    def test_registry_has_all_required_fields(self):
        """Current registry has all required top-level fields."""
        for field in REQUIRED_REGISTRY_FIELDS:
            assert field in _REGISTRY_DATA, f"Missing required field: {field}"

    def test_missing_registry_version_fails(self):
        """Missing registry_version fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["registry_version"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("registry_version" in e for e in errors)

    def test_missing_agents_fails(self):
        """Missing agents section fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["agents"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("agents" in e for e in errors)

    def test_missing_schema_metadata_fails(self):
        """Missing schema_metadata fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["schema_metadata"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("schema_metadata" in e for e in errors)

    def test_missing_governance_invariants_fails(self):
        """Missing governance_invariants fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["governance_invariants"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("governance_invariants" in e for e in errors)


class TestRegistryVersionValidation:
    """Test registry version field validation."""

    def test_valid_semver_accepted(self):
        """Valid semver format is accepted."""
        valid, errors = validate_registry_schema(_REGISTRY_DATA)
        # Filter to version-specific errors
        version_errors = [e for e in errors if "registry_version" in e.lower()]
        assert len(version_errors) == 0, f"Unexpected version errors: {version_errors}"

    def test_invalid_semver_fails(self):
        """Invalid semver format fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        bad_registry["registry_version"] = "3.0"  # Missing patch version

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("semver" in e.lower() for e in errors)

    def test_empty_version_fails(self):
        """Empty version string fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        bad_registry["registry_version"] = ""

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False

    def test_non_string_version_fails(self):
        """Non-string version fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        bad_registry["registry_version"] = 3.0  # Number, not string

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False


# =============================================================================
# SCHEMA VALIDATION — REQUIRED AGENT FIELDS
# =============================================================================


class TestRequiredAgentFields:
    """Test that required agent fields are enforced."""

    def test_all_agents_have_required_fields(self):
        """All agents in current registry have required fields."""
        valid, errors = validate_registry_schema(_REGISTRY_DATA)
        agent_field_errors = [e for e in errors if "missing required field" in e.lower()]
        assert len(agent_field_errors) == 0, f"Agent field errors: {agent_field_errors}"

    def test_missing_gid_fails(self):
        """Agent missing gid fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["agents"]["BENSON"]["gid"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("gid" in e.lower() and "BENSON" in e for e in errors)

    def test_missing_agent_level_fails(self):
        """Agent missing agent_level fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["agents"]["CODY"]["agent_level"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("agent_level" in e and "CODY" in e for e in errors)

    def test_missing_diversity_profile_fails(self):
        """Agent missing diversity_profile fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["agents"]["DAN"]["diversity_profile"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("diversity_profile" in e and "DAN" in e for e in errors)

    def test_missing_emoji_primary_fails(self):
        """Agent missing emoji_primary fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["agents"]["ALEX"]["emoji_primary"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("emoji_primary" in e and "ALEX" in e for e in errors)

    def test_missing_mutable_fields_fails(self):
        """Agent missing mutable_fields fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["agents"]["SAM"]["mutable_fields"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("mutable_fields" in e and "SAM" in e for e in errors)

    def test_missing_immutable_fields_fails(self):
        """Agent missing immutable_fields fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        del bad_registry["agents"]["PAX"]["immutable_fields"]

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("immutable_fields" in e and "PAX" in e for e in errors)


class TestAgentLevelValidation:
    """Test agent_level field validation."""

    def test_valid_levels_accepted(self):
        """Valid agent levels (L0-L3) are accepted."""
        for level in VALID_AGENT_LEVELS:
            assert level in {"L0", "L1", "L2", "L3"}

    def test_invalid_level_fails(self):
        """Invalid agent level fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        bad_registry["agents"]["CODY"]["agent_level"] = "L4"  # Invalid

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("agent_level" in e and "L4" in e for e in errors)

    def test_numeric_level_fails(self):
        """Numeric agent level (not string) is detected."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        bad_registry["agents"]["CODY"]["agent_level"] = 2  # Should be "L2"

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False


class TestGIDFormatValidation:
    """Test GID format validation."""

    def test_valid_gid_format(self):
        """Valid GID format (GID-NN) accepted."""
        # All agents in registry should have valid GIDs
        for name, data in _REGISTRY_DATA["agents"].items():
            gid = data["gid"]
            assert gid.startswith("GID-"), f"Agent {name} GID doesn't start with GID-"
            assert len(gid) == 6, f"Agent {name} GID wrong length: {gid}"

    def test_invalid_gid_format_fails(self):
        """Invalid GID format fails validation."""
        bad_registry = copy.deepcopy(_REGISTRY_DATA)
        bad_registry["agents"]["CODY"]["gid"] = "GID-1"  # Should be GID-01

        valid, errors = validate_registry_schema(bad_registry)
        assert valid is False
        assert any("GID" in e and "CODY" in e for e in errors)


# =============================================================================
# MUTABILITY ENFORCEMENT
# =============================================================================


class TestMutabilityEnforcement:
    """Test immutable field mutation detection."""

    def test_immutable_gid_change_detected(self):
        """Changing GID without version bump is detected."""
        old_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry["agents"]["CODY"]["gid"] = "GID-99"

        valid, violations = validate_mutability(old_registry, new_registry)
        assert valid is False
        assert any("gid" in v.lower() and "CODY" in v for v in violations)

    def test_immutable_lane_change_detected(self):
        """Changing lane without version bump is detected."""
        old_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry["agents"]["CODY"]["lane"] = "PINK"

        valid, violations = validate_mutability(old_registry, new_registry)
        assert valid is False
        assert any("lane" in v.lower() for v in violations)

    def test_immutable_color_change_detected(self):
        """Changing color without version bump is detected."""
        old_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry["agents"]["DAN"]["color"] = "PURPLE"

        valid, violations = validate_mutability(old_registry, new_registry)
        assert valid is False
        assert any("color" in v.lower() for v in violations)

    def test_agent_removal_detected(self):
        """Removing agent without version bump is detected."""
        old_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry = copy.deepcopy(_REGISTRY_DATA)
        del new_registry["agents"]["ATLAS"]

        valid, violations = validate_mutability(old_registry, new_registry)
        assert valid is False
        assert any("ATLAS" in v and "removed" in v.lower() for v in violations)

    def test_mutable_field_change_allowed(self):
        """Changing mutable fields without version bump is allowed."""
        old_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry = copy.deepcopy(_REGISTRY_DATA)
        # role is in mutable_fields for most agents
        new_registry["agents"]["CODY"]["role"] = "Updated Role Title"

        valid, violations = validate_mutability(old_registry, new_registry)
        # role changes should not cause violations
        role_violations = [v for v in violations if "role" in v.lower()]
        assert len(role_violations) == 0

    def test_version_bump_allows_changes(self):
        """Version bump allows all field changes."""
        old_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry = copy.deepcopy(_REGISTRY_DATA)
        new_registry["registry_version"] = "99.0.0"  # Bumped version
        new_registry["agents"]["CODY"]["gid"] = "GID-99"  # Would be invalid

        # With version bump, even GID changes pass mutability check
        # (schema validation would still fail for duplicate GID, but that's separate)
        valid, violations = validate_mutability(old_registry, new_registry)
        assert valid is True


class TestFieldMutabilityChecks:
    """Test individual field mutability checking."""

    def test_gid_never_mutable(self):
        """GID is never mutable for any agent."""
        for agent_name in _REGISTRY_DATA["agents"]:
            assert is_field_mutable(agent_name, "gid") is False

    def test_lane_never_mutable(self):
        """Lane is never mutable for any agent."""
        for agent_name in _REGISTRY_DATA["agents"]:
            assert is_field_mutable(agent_name, "lane") is False

    def test_color_never_mutable(self):
        """Color is never mutable for any agent."""
        for agent_name in _REGISTRY_DATA["agents"]:
            assert is_field_mutable(agent_name, "color") is False

    def test_role_is_mutable(self):
        """Role is mutable for agents that declare it."""
        # CODY has role in mutable_fields
        assert is_field_mutable("CODY", "role") is True

    def test_unknown_agent_not_mutable(self):
        """Unknown agent returns False for mutability."""
        assert is_field_mutable("FAKE_AGENT", "role") is False


# =============================================================================
# AGENT LEVEL LOOKUPS
# =============================================================================


class TestAgentLevelLookups:
    """Test agent level lookup functions."""

    def test_benson_is_l3(self):
        """BENSON is L3 (Principal)."""
        assert get_agent_level("BENSON") == "L3"

    def test_cody_is_l2(self):
        """CODY is L2 (Senior)."""
        assert get_agent_level("CODY") == "L2"

    def test_lira_is_l1(self):
        """LIRA is L1 (Specialist)."""
        assert get_agent_level("LIRA") == "L1"

    def test_atlas_is_l1(self):
        """ATLAS is L1 (Specialist)."""
        assert get_agent_level("ATLAS") == "L1"

    def test_unknown_agent_returns_none(self):
        """Unknown agent returns None for level."""
        assert get_agent_level("FAKE_AGENT") is None

    def test_alias_lookup_works(self):
        """Agent level lookup via alias works."""
        # MIRA is an alias for MIRA-R
        assert get_agent_level("MIRA") == "L2"


class TestDiversityProfileLookups:
    """Test diversity profile lookup functions."""

    def test_benson_diversity_profile(self):
        """BENSON has orchestration in diversity_profile."""
        profile = get_agent_diversity_profile("BENSON")
        assert profile is not None
        assert "Orchestration" in profile

    def test_maggie_diversity_profile(self):
        """MAGGIE has ML in diversity_profile."""
        profile = get_agent_diversity_profile("MAGGIE")
        assert profile is not None
        assert "ML" in profile

    def test_unknown_agent_returns_none(self):
        """Unknown agent returns None for diversity_profile."""
        assert get_agent_diversity_profile("FAKE_AGENT") is None


# =============================================================================
# DEPRECATED AGENT DETECTION
# =============================================================================


class TestDeprecatedAgentDetection:
    """Test deprecated/unknown agent detection."""

    def test_registered_agents_not_deprecated(self):
        """All registered agents are not deprecated."""
        for agent_name in _REGISTRY_DATA["agents"]:
            assert is_deprecated_agent(agent_name) is False

    def test_unknown_agent_is_deprecated(self):
        """Unknown agent is detected as deprecated."""
        assert is_deprecated_agent("DANA") is True
        assert is_deprecated_agent("FAKE_AGENT") is True

    def test_alias_not_deprecated(self):
        """Valid alias is not deprecated."""
        # MIRA is an alias for MIRA-R
        assert is_deprecated_agent("MIRA") is False

    def test_forbidden_alias_is_deprecated(self):
        """Forbidden aliases are detected as deprecated."""
        # DANA is in forbidden_aliases
        assert is_deprecated_agent("DANA") is True


# =============================================================================
# REGISTRY VERSION
# =============================================================================


class TestRegistryVersion:
    """Test registry version accessor."""

    def test_get_registry_version(self):
        """Registry version is accessible."""
        version = get_registry_version()
        assert version is not None
        assert version != "unknown"
        # Should be semver format
        parts = version.split(".")
        assert len(parts) == 3


# =============================================================================
# BACKWARDS COMPATIBILITY REJECTION
# =============================================================================


class TestBackwardsCompatibilityRejection:
    """Test that backwards compatibility is explicitly rejected."""

    def test_legacy_emoji_field_not_required(self):
        """Legacy 'emoji' field is not in required fields."""
        # v3.0.0 uses emoji_primary, not emoji
        assert "emoji" not in REQUIRED_AGENT_FIELDS
        assert "emoji_primary" in REQUIRED_AGENT_FIELDS

    def test_schema_metadata_required(self):
        """schema_metadata is required (v3.0.0+)."""
        assert "schema_metadata" in REQUIRED_REGISTRY_FIELDS

    def test_agent_level_required(self):
        """agent_level is required for all agents (v3.0.0+)."""
        assert "agent_level" in REQUIRED_AGENT_FIELDS

    def test_diversity_profile_required(self):
        """diversity_profile is required for all agents (v3.0.0+)."""
        assert "diversity_profile" in REQUIRED_AGENT_FIELDS
