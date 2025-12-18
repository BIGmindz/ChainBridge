"""Tests for Governance Fingerprint — PAC-ALEX-02.

These tests verify:
- Deterministic hashing of governance roots
- Boot-time enforcement (fail closed on missing/invalid files)
- Audit log enrichment with fingerprint
- Drift detection at runtime
"""

import hashlib
import json
from pathlib import Path

import pytest

from core.governance.governance_fingerprint import (
    FINGERPRINT_VERSION,
    GOVERNANCE_ROOTS,
    FileHash,
    GovernanceBootError,
    GovernanceDriftError,
    GovernanceFingerprint,
    GovernanceFingerprintEngine,
    compute_governance_fingerprint,
    get_fingerprint_engine,
    verify_governance_integrity,
)


@pytest.fixture
def project_root():
    """Return the project root path."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def temp_governance_root(tmp_path):
    """Create a temporary governance root with valid files."""
    # Create required directory structure
    (tmp_path / "config").mkdir()
    (tmp_path / ".github").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "core" / "governance").mkdir(parents=True)
    (tmp_path / "docs" / "governance").mkdir(parents=True)

    # Create required files
    (tmp_path / "config" / "agents.json").write_text('{"agents": []}')
    (tmp_path / ".github" / "ALEX_RULES.json").write_text('{"rules": []}')
    (tmp_path / "manifests" / "GID-01_Test.yaml").write_text("agent_id: Test\ngid: GID-01")
    (tmp_path / "core" / "governance" / "drcp.py").write_text("# DRCP module\n")
    (tmp_path / "core" / "governance" / "diggi_corrections.py").write_text("# Diggi corrections\n")
    (tmp_path / "docs" / "governance" / "REPO_SCOPE_MANIFEST.md").write_text("# Repo Scope\n")

    return tmp_path


class TestGovernanceFingerprintEngine:
    """Test the GovernanceFingerprintEngine."""

    def test_compute_fingerprint_from_real_project(self, project_root):
        """Test computing fingerprint from real project files."""
        engine = GovernanceFingerprintEngine(project_root)
        fingerprint = engine.compute_fingerprint()

        assert fingerprint.version == FINGERPRINT_VERSION
        assert fingerprint.composite_hash is not None
        assert len(fingerprint.composite_hash) == 64  # SHA-256 hex
        assert len(fingerprint.file_hashes) > 0
        assert fingerprint.computed_at is not None

    def test_fingerprint_is_deterministic(self, project_root):
        """Test that fingerprint is deterministic across multiple runs."""
        engine1 = GovernanceFingerprintEngine(project_root)
        fp1 = engine1.compute_fingerprint()

        engine2 = GovernanceFingerprintEngine(project_root)
        fp2 = engine2.compute_fingerprint()

        assert fp1.composite_hash == fp2.composite_hash
        assert len(fp1.file_hashes) == len(fp2.file_hashes)

        # File hashes should match
        hashes1 = {fh.path: fh.hash for fh in fp1.file_hashes}
        hashes2 = {fh.path: fh.hash for fh in fp2.file_hashes}
        assert hashes1 == hashes2

    def test_compute_fingerprint_with_temp_files(self, temp_governance_root):
        """Test computing fingerprint from temporary governance files."""
        engine = GovernanceFingerprintEngine(temp_governance_root)
        fingerprint = engine.compute_fingerprint()

        assert fingerprint.version == FINGERPRINT_VERSION
        assert len(fingerprint.file_hashes) >= 6  # All required files

    def test_fingerprint_to_dict_format(self, temp_governance_root):
        """Test fingerprint.to_dict() produces correct format."""
        engine = GovernanceFingerprintEngine(temp_governance_root)
        fingerprint = engine.compute_fingerprint()

        result = fingerprint.to_dict()

        assert "governance_version" in result
        assert "composite_hash" in result
        assert "computed_at" in result
        assert "inputs" in result
        assert "categories" in result
        assert "file_count" in result

        assert result["governance_version"] == FINGERPRINT_VERSION
        assert len(result["composite_hash"]) == 64

    def test_fingerprint_to_audit_extension(self, temp_governance_root):
        """Test to_audit_extension() returns minimal format."""
        engine = GovernanceFingerprintEngine(temp_governance_root)
        fingerprint = engine.compute_fingerprint()

        audit_ext = fingerprint.to_audit_extension()

        assert "composite_hash" in audit_ext
        assert "version" in audit_ext
        assert len(audit_ext) == 2  # Only these two fields


class TestGovernanceFingerprintFailClosed:
    """Test fail-closed behavior of governance fingerprint."""

    def test_missing_required_file_fails(self, tmp_path):
        """Test that missing required governance file fails boot."""
        # Create partial structure (missing agents.json)
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "ALEX_RULES.json").write_text("{}")

        engine = GovernanceFingerprintEngine(tmp_path)

        with pytest.raises(GovernanceBootError) as exc_info:
            engine.compute_fingerprint()

        assert "Missing required governance file" in str(exc_info.value)

    def test_get_fingerprint_before_compute_fails(self, temp_governance_root):
        """Test get_fingerprint() fails if not computed."""
        engine = GovernanceFingerprintEngine(temp_governance_root)

        with pytest.raises(GovernanceBootError) as exc_info:
            engine.get_fingerprint()

        assert "not computed" in str(exc_info.value).lower()

    def test_is_initialized_flag(self, temp_governance_root):
        """Test is_initialized() returns correct state."""
        engine = GovernanceFingerprintEngine(temp_governance_root)

        assert not engine.is_initialized()

        engine.compute_fingerprint()

        assert engine.is_initialized()


class TestGovernanceDriftDetection:
    """Test drift detection at runtime."""

    def test_verify_no_drift_passes_when_unchanged(self, temp_governance_root):
        """Test verify_no_drift() passes when files unchanged."""
        engine = GovernanceFingerprintEngine(temp_governance_root)
        engine.compute_fingerprint()

        # Should pass without raising
        result = engine.verify_no_drift()
        assert result is True

    def test_drift_detected_when_file_modified(self, temp_governance_root):
        """Test drift is detected when governance file changes."""
        engine = GovernanceFingerprintEngine(temp_governance_root)
        engine.compute_fingerprint()

        # Modify a governance file
        agents_file = temp_governance_root / "config" / "agents.json"
        agents_file.write_text('{"agents": ["modified"]}')

        with pytest.raises(GovernanceDriftError) as exc_info:
            engine.verify_no_drift()

        assert "drift detected" in str(exc_info.value).lower()
        assert exc_info.value.original_hash != exc_info.value.current_hash

    def test_drift_detected_when_file_added(self, temp_governance_root):
        """Test drift is detected when new governance file added."""
        engine = GovernanceFingerprintEngine(temp_governance_root)
        engine.compute_fingerprint()

        # Add a new manifest file
        (temp_governance_root / "manifests" / "GID-02_New.yaml").write_text("agent_id: New")

        with pytest.raises(GovernanceDriftError):
            engine.verify_no_drift()

    def test_verify_drift_before_compute_fails(self, temp_governance_root):
        """Test verify_no_drift() fails if fingerprint not computed."""
        engine = GovernanceFingerprintEngine(temp_governance_root)

        with pytest.raises(GovernanceBootError) as exc_info:
            engine.verify_no_drift()

        assert "not computed" in str(exc_info.value).lower()


class TestFileHashNormalization:
    """Test file content normalization for deterministic hashing."""

    def test_whitespace_normalization(self, temp_governance_root):
        """Test trailing whitespace is normalized."""
        engine = GovernanceFingerprintEngine(temp_governance_root)

        # Write file with trailing whitespace
        agents_file = temp_governance_root / "config" / "agents.json"
        agents_file.write_text('{"agents": []}   \n\n')

        fp1 = engine.compute_fingerprint()
        hash1 = fp1.composite_hash

        # Rewrite without trailing whitespace
        agents_file.write_text('{"agents": []}')

        # Need new engine to reset cache
        engine2 = GovernanceFingerprintEngine(temp_governance_root)
        fp2 = engine2.compute_fingerprint()
        hash2 = fp2.composite_hash

        # Hashes should match after normalization
        assert hash1 == hash2

    def test_line_ending_normalization(self, temp_governance_root):
        """Test line endings are normalized to LF."""
        engine = GovernanceFingerprintEngine(temp_governance_root)

        # Write file with CRLF
        agents_file = temp_governance_root / "config" / "agents.json"
        agents_file.write_bytes(b'{"agents": []}\r\n')

        fp1 = engine.compute_fingerprint()
        hash1 = fp1.composite_hash

        # Rewrite with LF only
        agents_file.write_bytes(b'{"agents": []}\n')

        engine2 = GovernanceFingerprintEngine(temp_governance_root)
        fp2 = engine2.compute_fingerprint()
        hash2 = fp2.composite_hash

        # Hashes should match after normalization
        assert hash1 == hash2


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_compute_governance_fingerprint(self, project_root):
        """Test compute_governance_fingerprint() convenience function."""
        fingerprint = compute_governance_fingerprint(project_root)

        assert fingerprint.version == FINGERPRINT_VERSION
        assert fingerprint.composite_hash is not None

    def test_get_fingerprint_engine_singleton(self, project_root):
        """Test get_fingerprint_engine() returns singleton."""
        engine1 = get_fingerprint_engine(project_root)
        engine2 = get_fingerprint_engine()

        # Should be same instance (singleton pattern)
        assert engine1 is engine2


class TestGovernanceRootsConfiguration:
    """Test governance roots configuration."""

    def test_all_categories_defined(self):
        """Test all required governance categories are defined."""
        expected_categories = {
            "agent_authority",
            "governance_rules",
            "acm_manifests",
            "drcp_logic",
            "diggi_corrections",
            "repo_scope",
        }

        assert set(GOVERNANCE_ROOTS.keys()) == expected_categories

    def test_fingerprint_version_format(self):
        """Test fingerprint version has correct format."""
        assert FINGERPRINT_VERSION.startswith("v")
        # Should be simple version like "v1"
        assert FINGERPRINT_VERSION == "v1"


class TestFileHashDataclass:
    """Test FileHash dataclass."""

    def test_file_hash_immutable(self):
        """Test FileHash is immutable (frozen dataclass)."""
        fh = FileHash(path="test.py", hash="abc123", size=100)

        with pytest.raises(Exception):  # FrozenInstanceError
            fh.path = "modified.py"

    def test_file_hash_equality(self):
        """Test FileHash equality comparison."""
        fh1 = FileHash(path="test.py", hash="abc123", size=100)
        fh2 = FileHash(path="test.py", hash="abc123", size=100)

        assert fh1 == fh2


class TestGovernanceFingerprintIntegration:
    """Integration tests with real project files."""

    def test_real_project_has_all_categories(self, project_root):
        """Test real project includes all governance categories."""
        engine = GovernanceFingerprintEngine(project_root)
        fingerprint = engine.compute_fingerprint()

        # Should have files from multiple categories
        assert len(fingerprint.input_categories) >= 4

    def test_real_project_manifests_included(self, project_root):
        """Test real project includes ACM manifests."""
        engine = GovernanceFingerprintEngine(project_root)
        fingerprint = engine.compute_fingerprint()

        manifest_files = [fh for fh in fingerprint.file_hashes if "manifests/" in fh.path]
        assert len(manifest_files) >= 1

    def test_composite_hash_reproducible(self, project_root):
        """Test composite hash is reproducible across engine instances."""
        hashes = []
        for _ in range(3):
            engine = GovernanceFingerprintEngine(project_root)
            fp = engine.compute_fingerprint()
            hashes.append(fp.composite_hash)

        # All hashes should be identical
        assert len(set(hashes)) == 1
