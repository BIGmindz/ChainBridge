"""
🟢 DAN (GID-07) — Audit Bundle Export Tests
PAC-GOV-AUDIT-01: External Audit Export & Proof Bundle Contract

Tests for:
- Audit bundle creation and structure
- Manifest generation with hashes
- Bundle hash verification
- Deterministic export
- Read-only behavior (no source mutation)
- Verification script correctness
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from core.governance.audit_exporter import (
    AUDIT_BUNDLE_SCHEMA_VERSION,
    AuditBundleConfig,
    AuditBundleExporter,
    AuditBundleResult,
    export_audit_bundle,
)
from core.governance.events import GovernanceEvent, GovernanceEventType
from core.governance.retention import RotatingJSONLSink

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_project_dir() -> Path:
    """Create a temporary project directory with governance structure."""
    dirpath = tempfile.mkdtemp(prefix="audit_bundle_test_")
    project_root = Path(dirpath)

    # Create minimal governance structure
    (project_root / "logs").mkdir()
    (project_root / "config").mkdir()
    (project_root / "manifests").mkdir()
    (project_root / "core" / "governance").mkdir(parents=True)
    (project_root / "docs" / "governance").mkdir(parents=True)
    (project_root / ".github").mkdir()

    # Create minimal governance files
    (project_root / "config" / "agents.json").write_text('{"agents": []}')
    (project_root / ".github" / "ALEX_RULES.json").write_text('{"rules": []}')
    (project_root / "manifests" / "acm_gid00.yaml").write_text("version: 1")
    (project_root / "core" / "governance" / "drcp.py").write_text("# DRCP")
    (project_root / "docs" / "governance" / "REPO_SCOPE_MANIFEST.md").write_text("# Scope")

    yield project_root

    # Cleanup
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def project_with_events(temp_project_dir: Path) -> Path:
    """Create project directory with sample governance events."""
    log_path = temp_project_dir / "logs" / "governance_events.jsonl"

    sink = RotatingJSONLSink(path=log_path)
    for i in range(20):
        event = GovernanceEvent(
            event_type=GovernanceEventType.DECISION_DENIED,
            agent_gid="GID-07",
            verb="test",
            target=f"target_{i}",
            metadata={"seq": i},
        )
        sink.emit(event)
    sink.close()

    return temp_project_dir


@pytest.fixture
def project_with_artifacts(project_with_events: Path) -> Path:
    """Create project with events and artifact manifest."""
    build_dir = project_with_events / "build"
    build_dir.mkdir(exist_ok=True)

    artifacts = {
        "aggregate_hash": "abc123",
        "artifact_type": "python-service",
        "artifact_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": "abc123def456",
        "git_branch": "main",
        "files": {"api/server.py": "hash1", "core/main.py": "hash2"},
        "file_count": 2,
    }
    (build_dir / "artifacts.json").write_text(json.dumps(artifacts, indent=2))

    return project_with_events


# ═══════════════════════════════════════════════════════════════════════════════
# BASIC EXPORT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditBundleExport:
    """Tests for basic audit bundle export."""

    def test_export_creates_bundle_directory(self, project_with_events: Path) -> None:
        """Export should create bundle directory with correct structure."""
        output_path = project_with_events / "audit_bundle_test"

        config = AuditBundleConfig(
            source_log_path="logs/governance_events.jsonl",
            project_root=str(project_with_events),
        )
        exporter = AuditBundleExporter(config)
        result = exporter.export(output_path)

        assert result.success
        assert output_path.exists()
        assert (output_path / "AUDIT_MANIFEST.json").exists()
        assert (output_path / "governance_events" / "events.jsonl").exists()
        assert (output_path / "fingerprint" / "governance_fingerprint.json").exists()
        assert (output_path / "scope" / "scope_declaration.json").exists()
        assert (output_path / "VERIFY.md").exists()

    def test_export_returns_valid_result(self, project_with_events: Path) -> None:
        """Export should return AuditBundleResult with correct data."""
        output_path = project_with_events / "audit_bundle_test"

        result = export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        assert result.success
        assert result.bundle_id.startswith("audit-")
        assert result.bundle_hash
        assert result.created_at
        assert result.event_count == 20
        assert result.file_count >= 3  # events, fingerprint, scope

    def test_export_with_artifacts(self, project_with_artifacts: Path) -> None:
        """Export should include artifact manifest when present."""
        output_path = project_with_artifacts / "audit_bundle_test"

        result = export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_artifacts,
        )

        assert result.success
        assert (output_path / "artifacts" / "artifacts.json").exists()


# ═══════════════════════════════════════════════════════════════════════════════
# MANIFEST TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditManifest:
    """Tests for AUDIT_MANIFEST.json generation."""

    def test_manifest_has_required_fields(self, project_with_events: Path) -> None:
        """Manifest should contain all required fields."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        manifest = json.loads((output_path / "AUDIT_MANIFEST.json").read_text())

        assert manifest["schema_version"] == AUDIT_BUNDLE_SCHEMA_VERSION
        assert "bundle_id" in manifest
        assert "created_at" in manifest
        assert "created_by" in manifest
        assert "export_parameters" in manifest
        assert "contents" in manifest
        assert "bundle_hash" in manifest
        assert "governance_fingerprint_hash" in manifest
        assert "retention_policy_version" in manifest

    def test_manifest_contents_have_hashes(self, project_with_events: Path) -> None:
        """Each file in contents should have sha256 and size_bytes."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        manifest = json.loads((output_path / "AUDIT_MANIFEST.json").read_text())

        for rel_path, meta in manifest["contents"].items():
            assert "sha256" in meta, f"Missing sha256 for {rel_path}"
            assert "size_bytes" in meta, f"Missing size_bytes for {rel_path}"
            assert len(meta["sha256"]) == 64  # SHA-256 hex length

    def test_manifest_hashes_are_correct(self, project_with_events: Path) -> None:
        """File hashes in manifest should match actual file contents."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        manifest = json.loads((output_path / "AUDIT_MANIFEST.json").read_text())

        for rel_path, meta in manifest["contents"].items():
            file_path = output_path / rel_path
            actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
            assert actual_hash == meta["sha256"], f"Hash mismatch for {rel_path}"


# ═══════════════════════════════════════════════════════════════════════════════
# BUNDLE HASH TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBundleHash:
    """Tests for bundle hash verification."""

    def test_bundle_hash_is_correct(self, project_with_events: Path) -> None:
        """Bundle hash should be SHA-256 of sorted content hashes."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        manifest = json.loads((output_path / "AUDIT_MANIFEST.json").read_text())

        # Recompute bundle hash
        sorted_hashes = sorted(meta["sha256"] for meta in manifest["contents"].values())
        computed_hash = hashlib.sha256("".join(sorted_hashes).encode("utf-8")).hexdigest()

        assert computed_hash == manifest["bundle_hash"]

    def test_bundle_hash_changes_on_file_modification(self, project_with_events: Path) -> None:
        """Modifying any file should change the bundle hash."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        manifest = json.loads((output_path / "AUDIT_MANIFEST.json").read_text())
        original_bundle_hash = manifest["bundle_hash"]

        # Modify a file
        events_path = output_path / "governance_events" / "events.jsonl"
        with open(events_path, "a") as f:
            f.write('{"tampered": true}\n')

        # Recompute file hashes
        new_hashes = []
        for rel_path in manifest["contents"]:
            file_path = output_path / rel_path
            new_hashes.append(hashlib.sha256(file_path.read_bytes()).hexdigest())

        new_bundle_hash = hashlib.sha256("".join(sorted(new_hashes)).encode("utf-8")).hexdigest()

        assert new_bundle_hash != original_bundle_hash


# ═══════════════════════════════════════════════════════════════════════════════
# DETERMINISM TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDeterminism:
    """Tests for deterministic export behavior."""

    def test_same_input_same_content_hashes(self, project_with_events: Path) -> None:
        """Same source should produce same content hashes for static content."""
        output1 = project_with_events / "bundle1"
        output2 = project_with_events / "bundle2"

        export_audit_bundle(
            output_path=output1,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )
        export_audit_bundle(
            output_path=output2,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        manifest1 = json.loads((output1 / "AUDIT_MANIFEST.json").read_text())
        manifest2 = json.loads((output2 / "AUDIT_MANIFEST.json").read_text())

        # Events should be identical (byte-for-byte copy)
        events_path = "governance_events/events.jsonl"
        assert (
            manifest1["contents"][events_path]["sha256"] == manifest2["contents"][events_path]["sha256"]
        ), "Event hashes should be identical"

        # Note: fingerprint/governance_fingerprint.json contains computed_at
        # timestamp, so hashes will differ between runs. This is expected.
        # The important invariant is that the composite_hash of the governance
        # roots is deterministic.

    def test_events_not_reordered(self, project_with_events: Path) -> None:
        """Events should maintain original order."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        events_path = output_path / "governance_events" / "events.jsonl"
        seqs = []
        with open(events_path) as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    seqs.append(event["metadata"]["seq"])

        # Should be in original order
        assert seqs == list(range(20))


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestReadOnly:
    """Tests for read-only behavior."""

    def test_source_log_not_modified(self, project_with_events: Path) -> None:
        """Export should not modify source log file."""
        source_path = project_with_events / "logs" / "governance_events.jsonl"
        original_content = source_path.read_bytes()
        original_mtime = source_path.stat().st_mtime

        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        # Source should be unchanged
        assert source_path.read_bytes() == original_content
        assert source_path.stat().st_mtime == original_mtime


# ═══════════════════════════════════════════════════════════════════════════════
# TIME FILTERING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestTimeFiltering:
    """Tests for time-based event filtering."""

    def test_export_with_time_range(self, temp_project_dir: Path) -> None:
        """Export should filter events by time range."""
        log_path = temp_project_dir / "logs" / "governance_events.jsonl"

        # Create events with specific timestamps
        now = datetime.now(timezone.utc)
        sink = RotatingJSONLSink(path=log_path)

        for i in range(10):
            event = GovernanceEvent(
                event_type=GovernanceEventType.DECISION_DENIED,
                timestamp=now - timedelta(hours=10 - i),
                metadata={"seq": i},
            )
            sink.emit(event)
        sink.close()

        # Export only middle events (hours 3-6)
        start_time = now - timedelta(hours=7)
        end_time = now - timedelta(hours=4)

        output_path = temp_project_dir / "audit_bundle_test"
        result = export_audit_bundle(
            start_time=start_time,
            end_time=end_time,
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=temp_project_dir,
        )

        # Should have filtered subset
        assert result.success
        assert result.event_count < 10


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION SCRIPT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVerificationScript:
    """Tests for verify_audit_bundle.py script."""

    def test_verification_passes_valid_bundle(self, project_with_events: Path) -> None:
        """Verification should pass for valid bundle."""
        # Import verification module
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))
        from verify_audit_bundle import verify_audit_bundle

        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        success, messages = verify_audit_bundle(output_path)

        assert success, f"Verification failed: {messages}"
        assert any("✓" in msg for msg in messages)

    def test_verification_fails_tampered_file(self, project_with_events: Path) -> None:
        """Verification should fail if file is tampered."""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))
        from verify_audit_bundle import verify_audit_bundle

        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        # Tamper with events file
        events_path = output_path / "governance_events" / "events.jsonl"
        with open(events_path, "a") as f:
            f.write('{"tampered": true}\n')

        success, messages = verify_audit_bundle(output_path)

        assert not success
        assert any("mismatch" in msg.lower() for msg in messages)

    def test_verification_fails_missing_manifest(self, project_with_events: Path) -> None:
        """Verification should fail if manifest is missing."""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))
        from verify_audit_bundle import verify_audit_bundle

        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        # Remove manifest
        (output_path / "AUDIT_MANIFEST.json").unlink()

        success, messages = verify_audit_bundle(output_path)

        assert not success


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_export_audit_bundle_function(self, project_with_events: Path) -> None:
        """export_audit_bundle should work as standalone function."""
        output_path = project_with_events / "audit_bundle_test"

        result = export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        assert isinstance(result, AuditBundleResult)
        assert result.success
        assert output_path.exists()


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE DECLARATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestScopeDeclaration:
    """Tests for scope declaration document."""

    def test_scope_declaration_structure(self, project_with_events: Path) -> None:
        """Scope declaration should have required sections."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        scope = json.loads((output_path / "scope" / "scope_declaration.json").read_text())

        assert "schema_version" in scope
        assert "included" in scope
        assert "excluded" in scope
        assert "assumptions" in scope
        assert "limitations" in scope

    def test_scope_declaration_lists_exclusions(self, project_with_events: Path) -> None:
        """Scope declaration should explicitly list what's excluded."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        scope = json.loads((output_path / "scope" / "scope_declaration.json").read_text())

        assert "raw_source_code" in scope["excluded"]
        assert "runtime_secrets" in scope["excluded"]
        assert "user_data" in scope["excluded"]


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Tests for error handling."""

    def test_export_handles_missing_source_log(self, temp_project_dir: Path) -> None:
        """Export should handle missing source log gracefully."""
        output_path = temp_project_dir / "audit_bundle_test"

        result = export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/nonexistent.jsonl",
            project_root=temp_project_dir,
        )

        # Should still succeed (empty events)
        assert result.success
        assert result.event_count == 0

    def test_export_handles_missing_artifacts(self, project_with_events: Path) -> None:
        """Export should succeed even without artifact manifest."""
        output_path = project_with_events / "audit_bundle_test"

        result = export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        assert result.success
        # Artifacts should not be in bundle
        assert not (output_path / "artifacts" / "artifacts.json").exists()


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-GOV-FRESHNESS-01: FRESHNESS CONTRACT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFreshnessManifest:
    """Tests for freshness manifest generation."""

    def test_export_creates_freshness_manifest(self, project_with_events: Path) -> None:
        """Export should create FRESHNESS_MANIFEST.json."""
        output_path = project_with_events / "audit_bundle_test"

        result = export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        assert result.success
        freshness_path = output_path / "FRESHNESS_MANIFEST.json"
        assert freshness_path.exists()

    def test_freshness_manifest_has_required_fields(self, project_with_events: Path) -> None:
        """Freshness manifest should contain all required fields."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        freshness = json.loads((output_path / "FRESHNESS_MANIFEST.json").read_text())

        assert "schema_version" in freshness
        assert "generated_at" in freshness
        assert "max_staleness_seconds" in freshness
        assert "source_timestamps" in freshness

    def test_freshness_manifest_has_source_timestamps(self, project_with_events: Path) -> None:
        """Freshness manifest should include timestamps for all sources."""
        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        freshness = json.loads((output_path / "FRESHNESS_MANIFEST.json").read_text())

        sources = freshness["source_timestamps"]
        assert "governance_events" in sources
        assert "governance_fingerprint" in sources
        assert "audit_bundle" in sources

        # Each source should have timestamp and description
        for source, info in sources.items():
            assert "timestamp" in info
            assert "description" in info

    def test_freshness_manifest_respects_custom_staleness(self, project_with_events: Path) -> None:
        """Export should respect custom max_staleness_seconds."""
        output_path = project_with_events / "audit_bundle_test"
        custom_staleness = 3600  # 1 hour

        config = AuditBundleConfig(
            source_log_path="logs/governance_events.jsonl",
            project_root=str(project_with_events),
            max_staleness_seconds=custom_staleness,
        )
        exporter = AuditBundleExporter(config)
        exporter.export(output_path)

        freshness = json.loads((output_path / "FRESHNESS_MANIFEST.json").read_text())

        assert freshness["max_staleness_seconds"] == custom_staleness


class TestFreshnessVerification:
    """Tests for freshness verification (fail-closed)."""

    def test_fresh_bundle_verifies(self, project_with_events: Path) -> None:
        """Fresh bundle should pass verification."""
        from core.governance.freshness import load_freshness_manifest, verify_freshness

        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        manifest = load_freshness_manifest(output_path)
        assert manifest is not None

        result = verify_freshness(manifest)
        assert result.is_fresh
        assert len(result.stale_sources) == 0

    def test_stale_source_fails_verification(self, project_with_events: Path) -> None:
        """Stale source should fail verification."""
        from core.governance.freshness import FreshnessManifest, SourceTimestamp, verify_freshness

        # Create manifest with old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        check_time = datetime.now(timezone.utc)

        manifest = FreshnessManifest(
            generated_at=check_time,
            max_staleness_seconds=86400,  # 24 hours
            source_timestamps=[
                SourceTimestamp(
                    source="governance_events",
                    timestamp=old_time,
                    description="Test old timestamp",
                ),
            ],
        )

        result = verify_freshness(manifest, check_time=check_time)

        assert not result.is_fresh
        assert len(result.stale_sources) == 1
        assert result.stale_sources[0]["source"] == "governance_events"
        assert result.stale_sources[0]["exceeded_by_seconds"] > 0

    def test_verification_reports_staleness_amount(self, project_with_events: Path) -> None:
        """Verification should report how stale the source is."""
        from core.governance.freshness import FreshnessManifest, SourceTimestamp, verify_freshness

        # Create manifest with old timestamp (25 hours old, max 24 hours)
        max_staleness = 86400  # 24 hours
        age_seconds = 90000  # 25 hours
        old_time = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
        check_time = datetime.now(timezone.utc)

        manifest = FreshnessManifest(
            generated_at=check_time,
            max_staleness_seconds=max_staleness,
            source_timestamps=[
                SourceTimestamp(
                    source="governance_events",
                    timestamp=old_time,
                    description="Test",
                ),
            ],
        )

        result = verify_freshness(manifest, check_time=check_time)

        assert not result.is_fresh
        stale = result.stale_sources[0]
        # Should have exceeded by approximately 3600 seconds (1 hour)
        assert stale["exceeded_by_seconds"] >= 3500  # Allow some tolerance

    def test_missing_freshness_manifest_fails_verification(self, project_with_events: Path) -> None:
        """Missing freshness manifest should fail verification."""
        # Import the verification script's verify_freshness
        import sys

        sys.path.insert(0, str(project_with_events.parent.parent / "scripts"))

        # Create a bundle without freshness manifest
        output_path = project_with_events / "audit_bundle_test"
        output_path.mkdir()
        (output_path / "AUDIT_MANIFEST.json").write_text("{}")
        (output_path / "governance_events").mkdir()
        (output_path / "governance_events" / "events.jsonl").write_text("")

        # Use script's verify_freshness directly
        from scripts.verify_audit_bundle import verify_freshness as script_verify

        success, messages = script_verify(output_path)

        assert not success
        assert any("Missing FRESHNESS_MANIFEST.json" in m for m in messages)

    def test_tampered_timestamp_fails_verification(self, project_with_events: Path) -> None:
        """Tampered timestamp should cause staleness failure."""
        from core.governance.freshness import FreshnessManifest, SourceTimestamp, verify_freshness

        # Simulate tampering: timestamp claims to be in the future
        # but when verified against current time, it's actually stale
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        check_time = datetime.now(timezone.utc)

        # Even if someone tries to tamper, the staleness check is based
        # on the actual timestamp value
        manifest = FreshnessManifest(
            generated_at=check_time,
            max_staleness_seconds=86400,
            source_timestamps=[
                SourceTimestamp(
                    source="governance_events",
                    timestamp=old_time,  # Stale timestamp
                    description="Test",
                ),
            ],
        )

        result = verify_freshness(manifest, check_time=check_time)

        # Should still fail because the timestamp is old
        assert not result.is_fresh

    def test_verification_script_checks_freshness(self, project_with_events: Path) -> None:
        """Verification script should include freshness check by default."""
        from scripts.verify_audit_bundle import verify_audit_bundle

        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        success, messages = verify_audit_bundle(output_path)

        assert success
        assert any("fresh" in m.lower() for m in messages)

    def test_verification_script_skip_freshness(self, project_with_events: Path) -> None:
        """Verification script should allow skipping freshness check."""
        from scripts.verify_audit_bundle import verify_audit_bundle

        output_path = project_with_events / "audit_bundle_test"
        export_audit_bundle(
            output_path=output_path,
            source_log_path="logs/governance_events.jsonl",
            project_root=project_with_events,
        )

        success, messages = verify_audit_bundle(output_path, skip_freshness=True)

        assert success
        assert any("skipped" in m.lower() for m in messages)

    def test_verification_with_injected_check_time(self, project_with_events: Path) -> None:
        """Verification should use injected check_time for testing."""
        from core.governance.freshness import FreshnessManifest, SourceTimestamp, verify_freshness

        now = datetime.now(timezone.utc)
        source_time = now - timedelta(hours=12)

        manifest = FreshnessManifest(
            generated_at=now,
            max_staleness_seconds=86400,  # 24 hours
            source_timestamps=[
                SourceTimestamp(
                    source="governance_events",
                    timestamp=source_time,
                    description="Test",
                ),
            ],
        )

        # With check_time = now, should be fresh (12 hours < 24 hours)
        result = verify_freshness(manifest, check_time=now)
        assert result.is_fresh

        # With check_time = now + 15 hours, should be stale (27 hours > 24 hours)
        future_time = now + timedelta(hours=15)
        result = verify_freshness(manifest, check_time=future_time)
        assert not result.is_fresh
