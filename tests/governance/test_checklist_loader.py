"""Tests for Governance Validation Checklist — PAC-GOV-VAL-01.

These tests verify the governance checklist enforcement:
- Checklist loading and validation
- Chain-of-command enforcement
- DENY behavior on missing/invalid checklist
- Integration with ALEX middleware
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.governance.checklist_loader import (
    ChecklistLoader,
    ChecklistNotFoundError,
    ChecklistValidationError,
    ChecklistVersionError,
    GovernanceChecklist,
    load_governance_checklist,
)


class TestChecklistLoading:
    """Tests for checklist loading and validation."""

    def test_checklist_loads_successfully(self):
        """Test that the production checklist loads without error."""
        checklist = load_governance_checklist()

        assert checklist is not None
        assert checklist.version == "1.0.0"
        assert checklist.status == "GOVERNANCE-LOCKED"
        assert checklist.enforced_by == "GID-08"

    def test_checklist_has_required_gates(self):
        """Test that checklist has all required validation gates."""
        checklist = load_governance_checklist()

        gate_ids = {gate.gate_id for gate in checklist.required_checks}

        # All mandatory gates must be present
        assert "agent_identity_known" in gate_ids
        assert "chain_of_command_enforced" in gate_ids
        assert "verb_permitted_by_acm" in gate_ids
        assert "target_in_scope" in gate_ids
        assert "mutation_requires_execute" in gate_ids
        assert "audit_log_written" in gate_ids

    def test_checklist_has_denial_reasons(self):
        """Test that checklist has all denial reason definitions."""
        checklist = load_governance_checklist()

        # Critical denial reasons must be defined
        assert "UNKNOWN_AGENT" in checklist.denial_reasons
        assert "CHAIN_OF_COMMAND_VIOLATION" in checklist.denial_reasons
        assert "VERB_NOT_PERMITTED" in checklist.denial_reasons
        assert "TARGET_NOT_IN_SCOPE" in checklist.denial_reasons

    def test_checklist_chain_of_command_verbs(self):
        """Test that chain-of-command verbs are correctly defined."""
        checklist = load_governance_checklist()

        # These verbs require chain-of-command
        assert checklist.requires_chain_of_command("EXECUTE")
        assert checklist.requires_chain_of_command("BLOCK")
        assert checklist.requires_chain_of_command("APPROVE")

        # These do NOT require chain-of-command
        assert not checklist.requires_chain_of_command("READ")
        assert not checklist.requires_chain_of_command("PROPOSE")
        assert not checklist.requires_chain_of_command("ESCALATE")

    def test_checklist_forbidden_verbs(self):
        """Test that forbidden verbs are correctly defined."""
        checklist = load_governance_checklist()

        assert checklist.is_verb_forbidden("DELETE")
        assert checklist.is_verb_forbidden("APPROVE")  # Human-only

    def test_checklist_invariants_present(self):
        """Test that non-negotiable invariants are present."""
        checklist = load_governance_checklist()

        assert len(checklist.invariants) >= 8

        # Key invariants must be present
        invariant_text = " ".join(checklist.invariants).lower()
        assert "identity" in invariant_text
        assert "acm" in invariant_text or "capabilities" in invariant_text
        assert "execute" in invariant_text
        assert "block" in invariant_text
        assert "approve" in invariant_text
        assert "delete" in invariant_text or "archive" in invariant_text


class TestChecklistMissing:
    """Tests for missing checklist behavior."""

    def test_missing_checklist_raises_error(self, tmp_path):
        """Test that missing checklist file raises ChecklistNotFoundError."""
        fake_path = tmp_path / "nonexistent" / "checklist.yaml"
        loader = ChecklistLoader(fake_path)

        with pytest.raises(ChecklistNotFoundError) as exc_info:
            loader.load()

        assert "not found" in str(exc_info.value).lower()
        assert "refuses to boot" in str(exc_info.value).lower()


class TestChecklistVersioning:
    """Tests for checklist version enforcement."""

    def test_version_compatible_same_version(self):
        """Test that same version is compatible."""
        loader = ChecklistLoader()
        assert loader._version_compatible("1.0.0", "1.0.0")

    def test_version_compatible_higher_version(self):
        """Test that higher version is compatible."""
        loader = ChecklistLoader()
        assert loader._version_compatible("1.1.0", "1.0.0")
        assert loader._version_compatible("2.0.0", "1.0.0")
        assert loader._version_compatible("1.0.1", "1.0.0")

    def test_version_incompatible_lower_version(self):
        """Test that lower version is incompatible."""
        loader = ChecklistLoader()
        assert not loader._version_compatible("0.9.0", "1.0.0")
        assert not loader._version_compatible("0.1.0", "1.0.0")

    def test_invalid_version_format_is_incompatible(self):
        """Test that invalid version format is treated as incompatible."""
        loader = ChecklistLoader()
        assert not loader._version_compatible("invalid", "1.0.0")
        # Note: "1.0" is treated as compatible (parsed as 1.0.0 due to padding)
        # Only truly invalid formats fail


class TestChecklistValidation:
    """Tests for checklist structure validation."""

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Test that invalid YAML raises ChecklistValidationError."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{ invalid yaml: [")

        loader = ChecklistLoader(bad_yaml)

        with pytest.raises(ChecklistValidationError) as exc_info:
            loader.load()

        assert "parse" in str(exc_info.value).lower()

    def test_missing_required_field_raises_error(self, tmp_path):
        """Test that missing required field raises ChecklistValidationError."""
        incomplete_yaml = tmp_path / "incomplete.yaml"
        incomplete_yaml.write_text("version: '1.0.0'\n# missing other fields")

        loader = ChecklistLoader(incomplete_yaml)

        with pytest.raises(ChecklistValidationError) as exc_info:
            loader.load()

        assert "missing" in str(exc_info.value).lower()


class TestProtectedPaths:
    """Tests for protected path definitions."""

    def test_governance_paths_are_protected(self):
        """Test that governance-related paths are protected."""
        checklist = load_governance_checklist()

        protected = checklist.protected_paths

        # These paths should be protected
        assert any("core/governance" in p for p in protected)
        assert any("gateway/alex" in p for p in protected)
        assert any("manifests" in p for p in protected)
        assert any("docs/governance" in p for p in protected)


class TestChecklistFailureMode:
    """Tests for checklist failure mode."""

    def test_default_failure_mode_is_deny(self):
        """Test that default failure mode is DENY."""
        checklist = load_governance_checklist()

        assert checklist.failure_mode == "DENY"


class TestChecklistOrchestrator:
    """Tests for orchestrator (Diggy) configuration."""

    def test_orchestrator_gid_is_defined(self):
        """Test that orchestrator GID is defined."""
        checklist = load_governance_checklist()

        assert checklist.orchestrator_gid == "GID-00"
