"""
🟢 DAN (GID-07) — Artifact Integrity Tests
PAC-DAN-04: Build Artifact Immutability & Hash Attestation

Tests for:
- Artifact hash generation
- Runtime verification
- Tamper detection
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts/ci to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))

from artifact_verifier import ArtifactIntegrityError, VerificationResult, get_artifact_info, verify_artifact_integrity, verify_files
from build_artifacts import compute_content_hash, compute_file_hash, generate_artifact_manifest

# =============================================================================
# HASH FUNCTION TESTS
# =============================================================================


class TestHashFunctions:
    """Tests for hash computation functions."""

    def test_compute_file_hash_deterministic(self, tmp_path: Path) -> None:
        """File hash should be deterministic."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        hash1 = compute_file_hash(test_file)
        hash2 = compute_file_hash(test_file)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_compute_file_hash_different_content(self, tmp_path: Path) -> None:
        """Different content should produce different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content A")
        file2.write_text("Content B")

        assert compute_file_hash(file1) != compute_file_hash(file2)

    def test_compute_content_hash(self) -> None:
        """Content hash should match expected SHA-256."""
        content = b"test content"
        expected = hashlib.sha256(content).hexdigest()

        assert compute_content_hash(content) == expected

    def test_file_hash_matches_content_hash(self, tmp_path: Path) -> None:
        """File hash should match content hash of same data."""
        content = b"test data"
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(content)

        file_hash = compute_file_hash(test_file)
        content_hash = compute_content_hash(content)

        assert file_hash == content_hash


# =============================================================================
# MANIFEST GENERATION TESTS
# =============================================================================


class TestManifestGeneration:
    """Tests for artifact manifest generation."""

    def test_generate_manifest_structure(self, tmp_path: Path) -> None:
        """Generated manifest should have required structure."""
        # Create minimal file structure
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "server.py").write_text("# API")
        (tmp_path / "api" / "__init__.py").write_text("")
        (tmp_path / ".git").mkdir()  # Fake git dir for root detection

        manifest = generate_artifact_manifest(tmp_path)

        assert "artifact_version" in manifest
        assert "artifact_type" in manifest
        assert "generated_at" in manifest
        assert "files" in manifest
        assert "aggregate_hash" in manifest
        assert "file_count" in manifest

        assert manifest["artifact_type"] == "python-service"

    def test_generate_manifest_tracks_files(self, tmp_path: Path) -> None:
        """Manifest should track existing files."""
        # Create tracked file
        (tmp_path / "api").mkdir()
        api_server = tmp_path / "api" / "server.py"
        api_server.write_text("# Server code")
        (tmp_path / ".git").mkdir()

        manifest = generate_artifact_manifest(tmp_path)

        assert "api/server.py" in manifest["files"]
        assert len(manifest["files"]["api/server.py"]) == 64

    def test_generate_manifest_reports_missing(self, tmp_path: Path) -> None:
        """Manifest should report missing tracked files."""
        (tmp_path / ".git").mkdir()

        manifest = generate_artifact_manifest(tmp_path)

        # Some tracked files should be missing
        assert "missing_files" in manifest or manifest["file_count"] == 0

    def test_aggregate_hash_deterministic(self, tmp_path: Path) -> None:
        """Aggregate hash should be deterministic."""
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "server.py").write_text("# Test")
        (tmp_path / ".git").mkdir()

        manifest1 = generate_artifact_manifest(tmp_path)
        manifest2 = generate_artifact_manifest(tmp_path)

        assert manifest1["aggregate_hash"] == manifest2["aggregate_hash"]


# =============================================================================
# VERIFICATION TESTS
# =============================================================================


class TestArtifactVerification:
    """Tests for artifact verification."""

    def test_verification_passes_with_matching_files(self, tmp_path: Path) -> None:
        """Verification should pass when files match manifest."""
        # Create file
        (tmp_path / "api").mkdir()
        test_file = tmp_path / "api" / "server.py"
        test_file.write_text("# Server")

        # Create manifest
        file_hash = compute_file_hash(test_file)
        manifest = {
            "files": {"api/server.py": file_hash},
            "aggregate_hash": "test",
        }

        manifest_path = tmp_path / "artifacts.json"
        manifest_path.write_text(json.dumps(manifest))

        result = verify_artifact_integrity(
            repo_root=tmp_path,
            manifest_path=manifest_path,
            strict=False,
        )

        assert result.passed
        assert result.files_verified == 1
        assert len(result.mismatches) == 0

    def test_verification_fails_with_tampered_file(self, tmp_path: Path) -> None:
        """Verification should fail when file is modified."""
        # Create file
        (tmp_path / "api").mkdir()
        test_file = tmp_path / "api" / "server.py"
        test_file.write_text("# Original")

        # Create manifest with original hash
        original_hash = compute_file_hash(test_file)
        manifest = {
            "files": {"api/server.py": original_hash},
            "aggregate_hash": "test",
        }

        manifest_path = tmp_path / "artifacts.json"
        manifest_path.write_text(json.dumps(manifest))

        # Tamper with file
        test_file.write_text("# Modified")

        result = verify_artifact_integrity(
            repo_root=tmp_path,
            manifest_path=manifest_path,
            strict=False,
        )

        assert not result.passed
        assert len(result.mismatches) == 1
        assert "MISMATCH" in result.mismatches[0]

    def test_verification_fails_with_missing_file(self, tmp_path: Path) -> None:
        """Verification should fail when tracked file is missing."""
        manifest = {
            "files": {"nonexistent.py": "abc123"},
            "aggregate_hash": "test",
        }

        manifest_path = tmp_path / "artifacts.json"
        manifest_path.write_text(json.dumps(manifest))

        result = verify_artifact_integrity(
            repo_root=tmp_path,
            manifest_path=manifest_path,
            strict=False,
        )

        assert not result.passed
        assert any("MISSING" in m for m in result.mismatches)

    def test_strict_mode_raises_on_failure(self, tmp_path: Path) -> None:
        """Strict mode should raise ArtifactIntegrityError on failure."""
        manifest = {
            "files": {"missing.py": "abc123"},
            "aggregate_hash": "test",
        }

        manifest_path = tmp_path / "artifacts.json"
        manifest_path.write_text(json.dumps(manifest))

        with pytest.raises(ArtifactIntegrityError) as exc_info:
            verify_artifact_integrity(
                repo_root=tmp_path,
                manifest_path=manifest_path,
                strict=True,
            )

        assert "failed" in str(exc_info.value).lower()
        assert len(exc_info.value.mismatches) > 0

    def test_verification_fails_without_manifest(self, tmp_path: Path) -> None:
        """Verification should fail if manifest doesn't exist."""
        result = verify_artifact_integrity(
            repo_root=tmp_path,
            manifest_path=tmp_path / "nonexistent.json",
            strict=False,
        )

        assert not result.passed
        assert any("not found" in m.lower() for m in result.mismatches)


# =============================================================================
# ARTIFACT INFO TESTS
# =============================================================================


class TestArtifactInfo:
    """Tests for artifact info retrieval."""

    def test_get_artifact_info_returns_data(self, tmp_path: Path) -> None:
        """Should return artifact info from manifest."""
        manifest = {
            "artifact_version": "1.0.0",
            "git_commit": "abc123",
            "git_branch": "main",
            "generated_at": "2025-01-01T00:00:00Z",
            "aggregate_hash": "def456",
            "file_count": 5,
            "files": {},
        }

        manifest_path = tmp_path / "artifacts.json"
        manifest_path.write_text(json.dumps(manifest))

        info = get_artifact_info(
            repo_root=tmp_path,
            manifest_path=manifest_path,
        )

        assert info is not None
        assert info["artifact_version"] == "1.0.0"
        assert info["git_commit"] == "abc123"
        assert info["file_count"] == 5

    def test_get_artifact_info_returns_none_without_manifest(self, tmp_path: Path) -> None:
        """Should return None if manifest doesn't exist."""
        info = get_artifact_info(
            repo_root=tmp_path,
            manifest_path=tmp_path / "nonexistent.json",
        )

        assert info is None


# =============================================================================
# VERIFICATION RESULT TESTS
# =============================================================================


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_result_to_dict(self) -> None:
        """Result should serialize to dict."""
        result = VerificationResult(
            passed=True,
            manifest_path="/path/to/manifest.json",
            files_verified=10,
            mismatches=[],
            aggregate_hash="abc123",
        )

        data = result.to_dict()

        assert data["passed"] is True
        assert data["manifest_path"] == "/path/to/manifest.json"
        assert data["files_verified"] == 10
        assert data["aggregate_hash"] == "abc123"

    def test_result_with_mismatches(self) -> None:
        """Result should include mismatches."""
        result = VerificationResult(
            passed=False,
            manifest_path="/path",
            mismatches=["MISMATCH: file.py", "MISSING: other.py"],
        )

        assert not result.passed
        assert len(result.mismatches) == 2


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestArtifactIntegration:
    """Integration tests for full artifact workflow."""

    def test_generate_and_verify_roundtrip(self, tmp_path: Path) -> None:
        """Full roundtrip: generate manifest, then verify."""
        # Create file structure
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "server.py").write_text("# API Server")
        (tmp_path / "api" / "__init__.py").write_text("")
        (tmp_path / ".git").mkdir()

        # Generate manifest
        manifest = generate_artifact_manifest(tmp_path)
        manifest_path = tmp_path / "build" / "artifacts.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # Verify
        result = verify_artifact_integrity(
            repo_root=tmp_path,
            manifest_path=manifest_path,
            strict=False,
        )

        assert result.passed
        assert result.aggregate_hash == manifest["aggregate_hash"]

    def test_modification_detection(self, tmp_path: Path) -> None:
        """Should detect file modification after manifest creation."""
        # Create file
        (tmp_path / "api").mkdir()
        test_file = tmp_path / "api" / "server.py"
        test_file.write_text("# Original content")
        (tmp_path / ".git").mkdir()

        # Generate manifest
        manifest = generate_artifact_manifest(tmp_path)
        manifest_path = tmp_path / "artifacts.json"
        manifest_path.write_text(json.dumps(manifest))

        # Verify passes initially
        result1 = verify_artifact_integrity(
            repo_root=tmp_path,
            manifest_path=manifest_path,
            strict=False,
        )
        assert result1.passed

        # Modify file
        test_file.write_text("# Modified content")

        # Verify fails after modification
        result2 = verify_artifact_integrity(
            repo_root=tmp_path,
            manifest_path=manifest_path,
            strict=False,
        )
        assert not result2.passed
        assert len(result2.mismatches) >= 1
