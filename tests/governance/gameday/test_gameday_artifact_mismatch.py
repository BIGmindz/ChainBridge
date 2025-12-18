"""
🧪 Gameday Test: G4 — Artifact Mismatch
PAC-GOV-GAMEDAY-01: Governance Failure Simulation

Simulate:
- Tampered artifact files (hash mismatch)
- Missing artifacts
- Corrupted manifest

Invariants:
- Operation denied (ArtifactIntegrityError raised)
- No state mutation
- Event emitted (ARTIFACT_VERIFICATION_FAILED)
- audit_ref present
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.governance.event_sink import GovernanceEventEmitter, InMemorySink
from core.governance.events import GovernanceEvent, GovernanceEventType, artifact_verification_event
from scripts.ci.artifact_verifier import (
    ArtifactIntegrityError,
    VerificationResult,
    compute_file_hash,
    verify_artifact_integrity,
    verify_files,
)


def _compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


# =============================================================================
# G4.1 — File Hash Mismatch
# =============================================================================


class TestFileHashMismatch:
    """
    G4.1: Simulate artifact file tampering.

    Attack scenario: An attacker modifies governed files
    to inject malicious code while bypassing detection.
    """

    @pytest.fixture
    def artifact_env(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a test environment with artifact manifest."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        build_dir = repo_root / "build"
        build_dir.mkdir()

        # Create a governed file
        core_dir = repo_root / "core" / "governance"
        core_dir.mkdir(parents=True)

        original_content = "# DRCP module - original content\n"
        drcp_file = core_dir / "drcp.py"
        drcp_file.write_text(original_content)

        # Compute correct hash
        correct_hash = _compute_hash(original_content)

        # Create manifest
        manifest = {
            "version": "1.0.0",
            "generated_at": "2024-01-01T00:00:00Z",
            "files": {
                "core/governance/drcp.py": correct_hash,
            },
            "aggregate_hash": correct_hash,
        }

        manifest_path = build_dir / "artifacts.json"
        manifest_path.write_text(json.dumps(manifest))

        return repo_root, manifest_path

    def test_tampered_file_detected(self, artifact_env: tuple[Path, Path]) -> None:
        """Tampered file should be detected via hash mismatch."""
        repo_root, manifest_path = artifact_env

        # First verify original passes
        result = verify_artifact_integrity(
            repo_root=repo_root,
            manifest_path=manifest_path,
            strict=False,
        )
        assert result.passed is True

        # Tamper the file
        drcp_file = repo_root / "core" / "governance" / "drcp.py"
        drcp_file.write_text("# DRCP module - BACKDOOR INJECTED\n")

        # Invariant 1: Operation denied
        with pytest.raises(ArtifactIntegrityError) as exc_info:
            verify_artifact_integrity(
                repo_root=repo_root,
                manifest_path=manifest_path,
                strict=True,
            )

        # Verify error contains mismatch details
        assert len(exc_info.value.mismatches) > 0
        assert "MISMATCH" in exc_info.value.mismatches[0]

    def test_non_strict_mode_returns_failure(self, artifact_env: tuple[Path, Path]) -> None:
        """Non-strict mode should return VerificationResult.passed=False."""
        repo_root, manifest_path = artifact_env

        # Tamper the file
        drcp_file = repo_root / "core" / "governance" / "drcp.py"
        drcp_file.write_text("# DRCP module - TAMPERED\n")

        result = verify_artifact_integrity(
            repo_root=repo_root,
            manifest_path=manifest_path,
            strict=False,
        )

        # Invariant 1: Operation denied (soft denial)
        assert result.passed is False
        assert len(result.mismatches) > 0

    def test_mismatch_includes_file_path(self, artifact_env: tuple[Path, Path]) -> None:
        """Mismatch error should include the affected file path."""
        repo_root, manifest_path = artifact_env

        # Tamper the file
        drcp_file = repo_root / "core" / "governance" / "drcp.py"
        drcp_file.write_text("# TAMPERED\n")

        result = verify_artifact_integrity(
            repo_root=repo_root,
            manifest_path=manifest_path,
            strict=False,
        )

        # Verify file path in mismatch
        assert "core/governance/drcp.py" in result.mismatches[0]


# =============================================================================
# G4.2 — Missing Artifact Files
# =============================================================================


class TestMissingArtifactFiles:
    """
    G4.2: Simulate missing artifact files.

    Attack scenario: An attacker deletes critical governance
    files to disable security controls.
    """

    @pytest.fixture
    def artifact_env(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create environment with manifest referencing files."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        build_dir = repo_root / "build"
        build_dir.mkdir()

        # Create files
        core_dir = repo_root / "core" / "governance"
        core_dir.mkdir(parents=True)

        drcp_content = "# DRCP module\n"
        acm_content = "# ACM module\n"

        (core_dir / "drcp.py").write_text(drcp_content)
        (core_dir / "acm.py").write_text(acm_content)

        # Manifest references both files
        manifest = {
            "version": "1.0.0",
            "files": {
                "core/governance/drcp.py": _compute_hash(drcp_content),
                "core/governance/acm.py": _compute_hash(acm_content),
            },
        }

        manifest_path = build_dir / "artifacts.json"
        manifest_path.write_text(json.dumps(manifest))

        return repo_root, manifest_path

    def test_deleted_file_detected(self, artifact_env: tuple[Path, Path]) -> None:
        """Deleted file should be detected as missing."""
        repo_root, manifest_path = artifact_env

        # Delete a file
        (repo_root / "core" / "governance" / "acm.py").unlink()

        # Invariant 1: Operation denied
        with pytest.raises(ArtifactIntegrityError) as exc_info:
            verify_artifact_integrity(
                repo_root=repo_root,
                manifest_path=manifest_path,
                strict=True,
            )

        # Verify "MISSING" in error
        assert any("MISSING" in m for m in exc_info.value.mismatches)

    def test_missing_file_in_results(self, artifact_env: tuple[Path, Path]) -> None:
        """Missing file should appear in result mismatches."""
        repo_root, manifest_path = artifact_env

        # Delete a file
        (repo_root / "core" / "governance" / "drcp.py").unlink()

        result = verify_artifact_integrity(
            repo_root=repo_root,
            manifest_path=manifest_path,
            strict=False,
        )

        assert result.passed is False
        assert any("MISSING" in m and "drcp.py" in m for m in result.mismatches)


# =============================================================================
# G4.3 — Missing/Corrupted Manifest
# =============================================================================


class TestMissingCorruptedManifest:
    """
    G4.3: Simulate missing or corrupted artifact manifest.

    Attack scenario: An attacker deletes or corrupts the manifest
    to prevent integrity verification.
    """

    def test_missing_manifest_fails_strict(self, tmp_path: Path) -> None:
        """Missing manifest should fail in strict mode."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()  # Git marker

        # No manifest file
        nonexistent = repo_root / "build" / "artifacts.json"

        # Invariant 1: Operation denied
        with pytest.raises(ArtifactIntegrityError) as exc_info:
            verify_artifact_integrity(
                repo_root=repo_root,
                manifest_path=nonexistent,
                strict=True,
            )

        assert "not found" in str(exc_info.value).lower()

    def test_missing_manifest_returns_failure(self, tmp_path: Path) -> None:
        """Missing manifest should return failure result in non-strict mode."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        nonexistent = repo_root / "build" / "artifacts.json"

        result = verify_artifact_integrity(
            repo_root=repo_root,
            manifest_path=nonexistent,
            strict=False,
        )

        assert result.passed is False
        assert "not found" in result.mismatches[0].lower()

    def test_corrupted_manifest_fails(self, tmp_path: Path) -> None:
        """Corrupted (non-JSON) manifest should fail."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        build_dir = repo_root / "build"
        build_dir.mkdir()

        # Write corrupted manifest
        manifest_path = build_dir / "artifacts.json"
        manifest_path.write_text("NOT VALID JSON {{{")

        # Should raise JSON decode error
        with pytest.raises((json.JSONDecodeError, ArtifactIntegrityError)):
            verify_artifact_integrity(
                repo_root=repo_root,
                manifest_path=manifest_path,
                strict=True,
            )


# =============================================================================
# G4.4 — Artifact Verification Events
# =============================================================================


class TestArtifactVerificationEvents:
    """
    G4.4: Verify artifact verification emits proper telemetry events.

    Invariant: ARTIFACT_VERIFICATION_FAILED event must be emitted.
    """

    def test_failed_verification_event_structure(self) -> None:
        """Test artifact_verification_event factory for failures."""
        event = artifact_verification_event(
            passed=False,
            artifact_hash="abc123",
            file_count=10,
            mismatches=["MISMATCH: core/acm.py"],
        )

        assert event.event_type == GovernanceEventType.ARTIFACT_VERIFICATION_FAILED.value
        assert event.decision == "FAIL"
        assert event.metadata["file_count"] == 10
        assert "MISMATCH" in event.metadata["mismatches"][0]

    def test_passed_verification_event_structure(self) -> None:
        """Test artifact_verification_event factory for success."""
        event = artifact_verification_event(
            passed=True,
            artifact_hash="abc123",
            file_count=10,
        )

        assert event.event_type == GovernanceEventType.ARTIFACT_VERIFIED.value
        assert event.decision == "PASS"
        assert event.metadata["file_count"] == 10

    def test_verification_event_has_audit_ref(self) -> None:
        """Verification event should support metadata."""
        event = artifact_verification_event(
            passed=False,
            artifact_hash="abc123",
            file_count=5,
            mismatches=["MISSING: file.py"],
            metadata={"audit_ref": "audit-2024-01-01-001"},
        )

        # Invariant 4: audit_ref info present in metadata
        assert event.metadata["audit_ref"] == "audit-2024-01-01-001"

    def test_verification_event_captured_by_sink(self) -> None:
        """Verification event should be captured by InMemorySink."""
        sink = InMemorySink()
        emitter = GovernanceEventEmitter()
        emitter.add_sink(sink)

        try:
            event = artifact_verification_event(
                passed=False,
                artifact_hash="abc123",
                file_count=5,
                mismatches=["MISMATCH: test.py"],
            )

            emitter.emit(event)

            # Invariant 3: Event emitted
            events = sink.get_events()
            assert len(events) == 1
            assert events[0].event_type == GovernanceEventType.ARTIFACT_VERIFICATION_FAILED.value
        finally:
            emitter.remove_sink(sink)


# =============================================================================
# G4.5 — No State Mutation on Failure
# =============================================================================


class TestNoStateMutationOnFailure:
    """
    G4.5: Verify artifact verification failure does not mutate state.

    Invariant: Failed verification leaves no side effects.
    """

    @pytest.fixture
    def artifact_env(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a test environment."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        build_dir = repo_root / "build"
        build_dir.mkdir()

        core_dir = repo_root / "core" / "governance"
        core_dir.mkdir(parents=True)

        content = "# Original\n"
        drcp_file = core_dir / "drcp.py"
        drcp_file.write_text(content)

        manifest = {
            "version": "1.0.0",
            "files": {
                "core/governance/drcp.py": _compute_hash(content),
            },
        }

        manifest_path = build_dir / "artifacts.json"
        manifest_path.write_text(json.dumps(manifest))

        return repo_root, manifest_path

    def test_failed_verification_no_file_changes(self, artifact_env: tuple[Path, Path]) -> None:
        """Failed verification should not change any files."""
        repo_root, manifest_path = artifact_env

        # Read manifest before
        manifest_before = manifest_path.read_text()

        # Tamper file
        drcp_file = repo_root / "core" / "governance" / "drcp.py"
        drcp_file.write_text("# TAMPERED\n")
        tampered_content = drcp_file.read_text()

        # Run verification (should fail)
        with pytest.raises(ArtifactIntegrityError):
            verify_artifact_integrity(
                repo_root=repo_root,
                manifest_path=manifest_path,
                strict=True,
            )

        # Invariant 2: No state mutation
        # Manifest should be unchanged
        assert manifest_path.read_text() == manifest_before

        # Tampered file should still be tampered (not "fixed")
        assert drcp_file.read_text() == tampered_content

    def test_verification_is_idempotent(self, artifact_env: tuple[Path, Path]) -> None:
        """Multiple verification runs should produce same result."""
        repo_root, manifest_path = artifact_env

        # Run multiple times
        results = []
        for _ in range(3):
            result = verify_artifact_integrity(
                repo_root=repo_root,
                manifest_path=manifest_path,
                strict=False,
            )
            results.append(result.passed)

        # All results should be consistent
        assert all(r == results[0] for r in results)
