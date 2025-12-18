"""
🟢 DAN (GID-07) — CI Governance Tests
PAC-DAN-01: Governance-Aware CI/CD & Repo Scope Lock

Tests for:
- Repo scope validation (forbidden path detection)
- Governance file immutability checking
- Build provenance generation
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts/ci to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))

from check_governance_immutability import GovernanceImmutabilityChecker
from check_repo_scope import RepoScopeValidator
from generate_provenance import ProvenanceGenerator

# =============================================================================
# REPO SCOPE VALIDATION TESTS
# =============================================================================


class TestRepoScopeValidator:
    """Tests for repo scope validation."""

    @pytest.fixture
    def validator(self, tmp_path: Path) -> RepoScopeValidator:
        """Create validator with temp repo root."""
        return RepoScopeValidator(tmp_path)

    def test_allowed_path_passes(self, validator: RepoScopeValidator) -> None:
        """Allowed paths should not return violations."""
        allowed_paths = [
            "api/server.py",
            "core/occ/decision.py",
            "gateway/gatekeeper.py",
            "tests/test_foo.py",
            "scripts/ci/check.py",
            "docs/README.md",
            ".github/workflows/ci.yml",
        ]

        for path in allowed_paths:
            result = validator.check_path(path)
            assert result is None, f"Path {path} should be allowed"

    def test_forbidden_path_fails(self, validator: RepoScopeValidator) -> None:
        """Forbidden paths should return ERROR violations."""
        forbidden_paths = [
            "benson_rsi_bot.py",
            "dynamic_crypto_selector.py",
            "multi_signal_bot.py",
            "legacy-rsi-bot/test.py",
            "legacy-benson-bot/main.py",
        ]

        for path in forbidden_paths:
            result = validator.check_path(path)
            assert result is not None, f"Path {path} should be forbidden"
            assert result["type"] == "FORBIDDEN"
            assert result["severity"] == "ERROR"

    def test_archived_legacy_allowed(self, validator: RepoScopeValidator) -> None:
        """Legacy artifacts in archive/ should be allowed (quarantine zone)."""
        archived_paths = [
            "archive/legacy-rsi-bot/benson_rsi_bot.py",
            "archive/legacy-benson-bot/old_code.py",
        ]

        for path in archived_paths:
            result = validator.check_path(path)
            assert result is None, f"Archived path {path} should be allowed"

    def test_scan_repository_finds_violations(self, tmp_path: Path) -> None:
        """Full repo scan should find forbidden files."""
        # Create forbidden file
        forbidden_file = tmp_path / "benson_rsi_bot.py"
        forbidden_file.write_text("# Legacy bot")

        # Create allowed file
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "server.py").write_text("# API server")

        validator = RepoScopeValidator(tmp_path)
        errors, warnings = validator.scan_repository()

        assert len(errors) >= 1
        assert any("benson_rsi_bot.py" in e["path"] for e in errors)

    def test_scan_repository_clean_passes(self, tmp_path: Path) -> None:
        """Clean repo should pass with no errors."""
        # Create only allowed structure
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "server.py").write_text("# API server")
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "logic.py").write_text("# Core logic")

        validator = RepoScopeValidator(tmp_path)
        errors, warnings = validator.scan_repository()

        assert len(errors) == 0


class TestRepoScopeValidatorWithConfig:
    """Tests with custom config file."""

    def test_custom_config_loading(self, tmp_path: Path) -> None:
        """Custom config should override defaults."""
        config = {
            "allowed_paths": ["custom/"],
            "allowed_root_files": ["custom.txt"],
            "forbidden_patterns": ["bad_file.py"],
            "archive_path": "quarantine/",
        }

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))

        validator = RepoScopeValidator(tmp_path, config_path)

        # Custom allowed path should pass
        result = validator.check_path("custom/file.py")
        assert result is None

        # Custom forbidden should fail
        result = validator.check_path("bad_file.py")
        assert result is not None
        assert result["type"] == "FORBIDDEN"


# =============================================================================
# GOVERNANCE IMMUTABILITY TESTS
# =============================================================================


class TestGovernanceImmutabilityChecker:
    """Tests for governance file immutability checking."""

    @pytest.fixture
    def checker(self, tmp_path: Path) -> GovernanceImmutabilityChecker:
        """Create checker with temp repo root."""
        # Create minimal governance structure
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "agents.json").write_text('{"version": "1.0"}')

        (tmp_path / "manifests").mkdir()
        (tmp_path / "manifests" / "GID-00_Diggy.yaml").write_text("name: Diggy")

        (tmp_path / "docs" / "governance").mkdir(parents=True)
        (tmp_path / "docs" / "governance" / "README.md").write_text("# Governance")

        return GovernanceImmutabilityChecker(tmp_path)

    def test_compute_file_hash(self, checker: GovernanceImmutabilityChecker, tmp_path: Path) -> None:
        """Hash computation should be deterministic."""
        hash1 = checker._compute_file_hash(tmp_path / "config" / "agents.json")
        hash2 = checker._compute_file_hash(tmp_path / "config" / "agents.json")

        assert hash1 is not None
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_missing_file_returns_none(self, checker: GovernanceImmutabilityChecker, tmp_path: Path) -> None:
        """Missing file hash should return None."""
        result = checker._compute_file_hash(tmp_path / "nonexistent.txt")
        assert result is None

    def test_override_env_detection(self, tmp_path: Path) -> None:
        """Override environment variable should be detected."""
        with patch.dict(os.environ, {"GOVERNANCE_OVERRIDE": "true"}):
            checker = GovernanceImmutabilityChecker(tmp_path)
            assert checker.override_enabled is True

        with patch.dict(os.environ, {"GOVERNANCE_OVERRIDE": "false"}):
            checker = GovernanceImmutabilityChecker(tmp_path)
            assert checker.override_enabled is False

    def test_hash_manifest_generation(self, checker: GovernanceImmutabilityChecker) -> None:
        """Hash manifest should include all protected files."""
        manifest = checker.generate_hash_manifest()

        assert isinstance(manifest, dict)
        # Should have entries for existing files
        assert any("agents.json" in k for k in manifest.keys())


# =============================================================================
# PROVENANCE GENERATION TESTS
# =============================================================================


class TestProvenanceGenerator:
    """Tests for build provenance generation."""

    @pytest.fixture
    def generator(self, tmp_path: Path) -> ProvenanceGenerator:
        """Create generator with temp repo root."""
        # Create minimal governance structure for hash computation
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "agents.json").write_text('{"version": "1.0"}')

        return ProvenanceGenerator(tmp_path)

    def test_provenance_has_required_fields(self, generator: ProvenanceGenerator) -> None:
        """Generated provenance should have all required fields."""
        provenance = generator.generate()

        # Required top-level fields
        assert "schema_version" in provenance
        assert "generator" in provenance
        assert "timestamp" in provenance
        assert "git" in provenance
        assert "governance" in provenance
        assert "ci" in provenance
        assert "environment" in provenance

    def test_provenance_git_section(self, generator: ProvenanceGenerator) -> None:
        """Git section should have commit info."""
        provenance = generator.generate()

        git = provenance["git"]
        assert "commit_sha" in git
        assert "commit_short" in git
        assert "branch" in git

    def test_provenance_governance_section(self, generator: ProvenanceGenerator) -> None:
        """Governance section should have hash and versions."""
        provenance = generator.generate()

        gov = provenance["governance"]
        assert "hash" in gov
        assert "acm_version" in gov
        assert "checklist_version" in gov

    def test_provenance_header_format(self, generator: ProvenanceGenerator) -> None:
        """Header format should be human-readable."""
        provenance = generator.generate()
        header = generator.format_header(provenance)

        assert "DAN (GID-07)" in header
        assert "BUILD PROVENANCE" in header
        assert "Commit:" in header
        assert "Governance Hash:" in header

    def test_provenance_generator_field(self, generator: ProvenanceGenerator) -> None:
        """Generator should be identified as DAN."""
        provenance = generator.generate()
        assert provenance["generator"] == "DAN (GID-07)"


# =============================================================================
# INTEGRATION TESTS (CI BEHAVIOR)
# =============================================================================


class TestCIBehavior:
    """Integration tests for CI behavior."""

    def test_forbidden_artifact_fails_ci(self, tmp_path: Path) -> None:
        """
        CI must fail when forbidden artifacts are present.
        This is the core enforcement behavior.
        """
        # Create forbidden file
        (tmp_path / "benson_rsi_bot.py").write_text("# Legacy")

        validator = RepoScopeValidator(tmp_path)
        errors, _ = validator.scan_repository()

        # CI would return exit code 1 on errors
        assert len(errors) > 0, "CI must fail on forbidden artifacts"

    def test_clean_repo_passes_ci(self, tmp_path: Path) -> None:
        """CI must pass when repo is clean."""
        # Create only allowed structure
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "__init__.py").write_text("")

        validator = RepoScopeValidator(tmp_path)
        errors, _ = validator.scan_repository()

        assert len(errors) == 0, "CI must pass on clean repo"

    def test_override_allows_governance_changes(self, tmp_path: Path) -> None:
        """
        Governance override should allow changes when properly set.
        This is the explicit, auditable override path.
        """
        with patch.dict(os.environ, {"GOVERNANCE_OVERRIDE": "true", "GOVERNANCE_OVERRIDE_REASON": "Authorized governance update"}):
            checker = GovernanceImmutabilityChecker(tmp_path)

            assert checker.override_enabled is True
            assert checker.override_reason == "Authorized governance update"


# =============================================================================
# WRAP: Test Coverage Summary
# =============================================================================


def test_dan_ci_wrap() -> None:
    """
    🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢
    DAN (GID-07) — CI GOVERNANCE TESTS

    Test Coverage:
    - Repo scope validation (PASS/FAIL paths)
    - Forbidden artifact detection
    - Archive quarantine zone behavior
    - Governance file immutability
    - Override mechanism
    - Build provenance generation
    - CI behavior integration

    All tests must pass for CI integrity.
    🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢
    """
    assert True  # Marker test for WRAP visibility
