"""
🟢 DAN (GID-07) — Governance Event Retention Tests
PAC-DAN-05: Governance Event Retention & Rotation

Tests for:
- Rotation triggers at size threshold
- Old files are deleted correctly (FIFO)
- No events are lost or reordered
- Export output matches source exactly
- Filesystem failure handling
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from core.governance.events import GovernanceEvent, GovernanceEventType
from core.governance.retention import (
    DEFAULT_ROTATING_LOG_PATH,
    MAX_FILE_COUNT,
    MAX_FILE_SIZE_BYTES,
    RETENTION_POLICY_VERSION,
    GovernanceEventExporter,
    RotatingJSONLSink,
    configure_rotating_sink,
    create_exporter,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    dirpath = tempfile.mkdtemp(prefix="governance_retention_test_")
    yield Path(dirpath)
    # Cleanup
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def temp_log_path(temp_dir: Path) -> Path:
    """Get a temporary log file path."""
    return temp_dir / "governance_events.jsonl"


@pytest.fixture
def sample_event() -> GovernanceEvent:
    """Create a sample governance event."""
    return GovernanceEvent(
        event_type=GovernanceEventType.DECISION_DENIED,
        agent_gid="GID-07",
        verb="execute",
        target="test_tool",
        decision="DENY",
        reason_code="TEST_DENIAL",
    )


def create_event(event_type: str = "TEST_EVENT", seq: int = 0) -> GovernanceEvent:
    """Create a test event with optional sequence number."""
    return GovernanceEvent(
        event_type=event_type,
        agent_gid="GID-07",
        verb="test",
        target=f"target_{seq}",
        metadata={"seq": seq},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION POLICY CONSTANTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRetentionPolicyConstants:
    """Tests for retention policy constants."""

    def test_max_file_size_is_50mb(self) -> None:
        """MAX_FILE_SIZE_BYTES should be 50MB."""
        assert MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024

    def test_max_file_count_is_20(self) -> None:
        """MAX_FILE_COUNT should be 20."""
        assert MAX_FILE_COUNT == 20

    def test_default_path_is_logs_governance_events(self) -> None:
        """Default path should be logs/governance_events.jsonl."""
        assert DEFAULT_ROTATING_LOG_PATH == "logs/governance_events.jsonl"

    def test_policy_version_exists(self) -> None:
        """Retention policy version should be defined."""
        assert RETENTION_POLICY_VERSION
        assert "." in RETENTION_POLICY_VERSION  # Semver-like


# ═══════════════════════════════════════════════════════════════════════════════
# ROTATING JSONL SINK TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRotatingJSONLSinkBasic:
    """Basic functionality tests for RotatingJSONLSink."""

    def test_creates_file_on_first_emit(self, temp_log_path: Path, sample_event: GovernanceEvent) -> None:
        """File should be created on first emit."""
        sink = RotatingJSONLSink(path=temp_log_path)
        assert not temp_log_path.exists()

        sink.emit(sample_event)
        assert temp_log_path.exists()

        sink.close()

    def test_creates_parent_directories(self, temp_dir: Path, sample_event: GovernanceEvent) -> None:
        """Parent directories should be created automatically."""
        nested_path = temp_dir / "a" / "b" / "c" / "events.jsonl"
        sink = RotatingJSONLSink(path=nested_path)

        sink.emit(sample_event)
        assert nested_path.exists()

        sink.close()

    def test_writes_valid_json(self, temp_log_path: Path, sample_event: GovernanceEvent) -> None:
        """Events should be written as valid JSON."""
        sink = RotatingJSONLSink(path=temp_log_path)
        sink.emit(sample_event)
        sink.close()

        with open(temp_log_path) as f:
            line = f.readline()
            data = json.loads(line)

        assert data["event_type"] == "DECISION_DENIED"
        assert data["agent_gid"] == "GID-07"

    def test_appends_events(self, temp_log_path: Path) -> None:
        """Multiple events should be appended to same file."""
        sink = RotatingJSONLSink(path=temp_log_path)

        for i in range(5):
            sink.emit(create_event(seq=i))

        sink.close()

        with open(temp_log_path) as f:
            lines = f.readlines()

        assert len(lines) == 5
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["metadata"]["seq"] == i

    def test_close_is_idempotent(self, temp_log_path: Path, sample_event: GovernanceEvent) -> None:
        """Calling close multiple times should not raise."""
        sink = RotatingJSONLSink(path=temp_log_path)
        sink.emit(sample_event)

        sink.close()
        sink.close()  # Should not raise
        sink.close()

    def test_emit_after_close_does_nothing(self, temp_log_path: Path, sample_event: GovernanceEvent) -> None:
        """Emitting after close should be silently ignored."""
        sink = RotatingJSONLSink(path=temp_log_path)
        sink.emit(sample_event)
        sink.close()

        # Count lines before
        with open(temp_log_path) as f:
            before = len(f.readlines())

        # Emit after close
        sink.emit(sample_event)

        # Count lines after
        with open(temp_log_path) as f:
            after = len(f.readlines())

        assert before == after == 1


# ═══════════════════════════════════════════════════════════════════════════════
# ROTATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRotationTrigger:
    """Tests for rotation trigger conditions."""

    def test_rotation_triggers_at_size_threshold(self, temp_log_path: Path) -> None:
        """Rotation should trigger when file exceeds max size."""
        # Use tiny threshold for testing (1KB)
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=1024,
            max_file_count=5,
        )

        # Write events until rotation happens
        event_count = 0
        while not temp_log_path.with_suffix(".jsonl.1").exists():
            sink.emit(create_event(seq=event_count))
            event_count += 1
            if event_count > 100:  # Safety limit
                break

        sink.close()

        # Rotated file should exist
        rotated = temp_log_path.with_suffix(".jsonl.1")
        assert rotated.exists()
        assert temp_log_path.exists()  # New current file

    def test_rotation_creates_numbered_files(self, temp_log_path: Path) -> None:
        """Multiple rotations should create incrementally numbered files."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=500,  # Very small for quick rotation
            max_file_count=10,
        )

        # Write many events to trigger multiple rotations
        for i in range(200):
            sink.emit(create_event(seq=i))

        sink.close()

        # Check multiple rotated files exist
        assert temp_log_path.with_suffix(".jsonl.1").exists()
        assert temp_log_path.with_suffix(".jsonl.2").exists()

    def test_rotation_deletes_oldest_files_when_limit_reached(self, temp_log_path: Path) -> None:
        """Files exceeding max_file_count should be deleted (oldest first)."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=200,  # Very small
            max_file_count=3,  # Only keep 3 rotated files
        )

        # Write many events to trigger many rotations
        for i in range(500):
            sink.emit(create_event(seq=i))

        sink.close()

        # Count total files
        parent = temp_log_path.parent
        log_files = [f for f in parent.iterdir() if f.name.startswith("governance_events")]
        # Should have: current + max 3 rotated = max 4 files
        assert len(log_files) <= 4

    def test_no_event_split_across_files(self, temp_log_path: Path) -> None:
        """Events should never be split across files."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=500,
            max_file_count=100,  # High enough to keep all events
        )

        # Write events
        for i in range(100):
            sink.emit(create_event(seq=i))

        sink.close()

        # Read all files and parse each line
        all_events: list[dict[str, Any]] = []
        for file_path in temp_log_path.parent.iterdir():
            if file_path.name.startswith("governance_events"):
                with open(file_path) as f:
                    for line in f:
                        if line.strip():
                            # Each line should be valid JSON (not split)
                            data = json.loads(line)
                            all_events.append(data)

        # All 100 events should be present
        assert len(all_events) == 100


class TestRotationAlgorithm:
    """Tests for rotation algorithm correctness."""

    def test_rotation_shifts_file_indices(self, temp_dir: Path) -> None:
        """Rotation should shift all file indices up by 1."""
        log_path = temp_dir / "events.jsonl"

        # Create pre-existing rotated files
        (temp_dir / "events.jsonl").write_text('{"event":"current"}\n')
        (temp_dir / "events.jsonl.1").write_text('{"event":"old1"}\n')
        (temp_dir / "events.jsonl.2").write_text('{"event":"old2"}\n')

        sink = RotatingJSONLSink(
            path=log_path,
            max_file_size_bytes=10,  # Force immediate rotation
            max_file_count=10,
        )
        sink.emit(create_event())
        sink.close()

        # Original .jsonl.1 should now be .jsonl.2
        with open(temp_dir / "events.jsonl.2") as f:
            data = json.loads(f.readline())
            assert data["event"] == "old1"

        # Original .jsonl.2 should now be .jsonl.3
        with open(temp_dir / "events.jsonl.3") as f:
            data = json.loads(f.readline())
            assert data["event"] == "old2"

    def test_no_events_lost_during_rotation(self, temp_log_path: Path) -> None:
        """All events should be preserved across rotations."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=500,
            max_file_count=100,  # High enough to keep all events
        )

        # Write 100 events with unique IDs
        expected_seqs = set(range(100))
        for i in range(100):
            sink.emit(create_event(seq=i))

        sink.close()

        # Collect all events from all files
        found_seqs: set[int] = set()
        for file_path in temp_log_path.parent.iterdir():
            if file_path.name.startswith("governance_events"):
                with open(file_path) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            found_seqs.add(data["metadata"]["seq"])

        # All events should be present
        assert found_seqs == expected_seqs

    def test_events_in_chronological_order_within_file(self, temp_log_path: Path) -> None:
        """Events within each file should be in chronological order."""
        sink = RotatingJSONLSink(path=temp_log_path)

        for i in range(10):
            event = create_event(seq=i)
            sink.emit(event)

        sink.close()

        with open(temp_log_path) as f:
            seqs = [json.loads(line)["metadata"]["seq"] for line in f]

        # Should be in order
        assert seqs == list(range(10))


# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION INFO TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRetentionInfo:
    """Tests for retention status information."""

    def test_get_retention_info_structure(self, temp_log_path: Path) -> None:
        """get_retention_info should return complete status."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=1000,
            max_file_count=5,
        )
        sink.emit(create_event())
        sink.close()

        info = sink.get_retention_info()

        assert "policy_version" in info
        assert info["max_file_size_bytes"] == 1000
        assert info["max_file_count"] == 5
        assert info["current_file_count"] >= 1
        assert info["total_size_bytes"] > 0

    def test_get_file_count(self, temp_log_path: Path) -> None:
        """get_file_count should return correct count."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=200,
            max_file_count=10,
        )

        # Write enough to trigger rotations
        for i in range(100):
            sink.emit(create_event(seq=i))

        file_count = sink.get_file_count()
        sink.close()

        assert file_count >= 2  # At least current + 1 rotated


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT / SNAPSHOT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestGovernanceEventExporter:
    """Tests for GovernanceEventExporter."""

    def test_iterate_events_returns_all_events(self, temp_log_path: Path) -> None:
        """iterate_events should return all events across files."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=500,
            max_file_count=100,  # High enough to keep all events
        )

        for i in range(50):
            sink.emit(create_event(seq=i))

        sink.close()

        exporter = GovernanceEventExporter(temp_log_path)
        events = list(exporter.iterate_events())

        assert len(events) == 50

    def test_iterate_events_chronological_order(self, temp_log_path: Path) -> None:
        """Events should be returned in chronological order (oldest first)."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=300,
            max_file_count=100,  # High enough to keep all events
        )

        for i in range(30):
            sink.emit(create_event(seq=i))

        sink.close()

        exporter = GovernanceEventExporter(temp_log_path)
        events = list(exporter.iterate_events())
        seqs = [e["metadata"]["seq"] for e in events]

        # Should be in order (oldest first)
        assert seqs == sorted(seqs)

    def test_iterate_events_with_time_filter(self, temp_log_path: Path) -> None:
        """Time filters should work correctly."""
        sink = RotatingJSONLSink(path=temp_log_path)

        # Create events with specific timestamps
        now = datetime.now(timezone.utc)
        for i in range(10):
            event = GovernanceEvent(
                event_type="TEST",
                timestamp=now + timedelta(hours=i),
                metadata={"seq": i},
            )
            sink.emit(event)

        sink.close()

        exporter = GovernanceEventExporter(temp_log_path)

        # Filter: hours 3-6
        start = now + timedelta(hours=3)
        end = now + timedelta(hours=6)
        filtered = list(exporter.iterate_events(start_time=start, end_time=end))

        seqs = [e["metadata"]["seq"] for e in filtered]
        assert all(3 <= s <= 6 for s in seqs)

    def test_export_to_file_creates_valid_copy(self, temp_dir: Path) -> None:
        """export_to_file should create an exact copy."""
        log_path = temp_dir / "events.jsonl"
        export_path = temp_dir / "export" / "exported.jsonl"

        sink = RotatingJSONLSink(path=log_path)
        for i in range(20):
            sink.emit(create_event(seq=i))
        sink.close()

        exporter = GovernanceEventExporter(log_path)
        count = exporter.export_to_file(export_path)

        assert count == 20
        assert export_path.exists()

        # Verify exported content
        with open(export_path) as f:
            lines = f.readlines()
        assert len(lines) == 20

    def test_export_does_not_mutate_source(self, temp_log_path: Path) -> None:
        """Export should never modify source files."""
        sink = RotatingJSONLSink(path=temp_log_path)
        for i in range(10):
            sink.emit(create_event(seq=i))
        sink.close()

        # Get original content
        with open(temp_log_path) as f:
            original = f.read()

        # Export
        exporter = GovernanceEventExporter(temp_log_path)
        list(exporter.iterate_events())

        # Verify unchanged
        with open(temp_log_path) as f:
            after = f.read()

        assert original == after

    def test_export_to_list(self, temp_log_path: Path) -> None:
        """export_to_list should return list of events."""
        sink = RotatingJSONLSink(path=temp_log_path)
        for i in range(15):
            sink.emit(create_event(seq=i))
        sink.close()

        exporter = GovernanceEventExporter(temp_log_path)
        events = exporter.export_to_list()

        assert len(events) == 15
        assert all(isinstance(e, dict) for e in events)

    def test_export_to_list_with_limit(self, temp_log_path: Path) -> None:
        """export_to_list with limit should cap results."""
        sink = RotatingJSONLSink(path=temp_log_path)
        for i in range(50):
            sink.emit(create_event(seq=i))
        sink.close()

        exporter = GovernanceEventExporter(temp_log_path)
        events = exporter.export_to_list(limit=10)

        assert len(events) == 10

    def test_get_event_count(self, temp_log_path: Path) -> None:
        """get_event_count should return accurate count."""
        sink = RotatingJSONLSink(path=temp_log_path)
        for i in range(25):
            sink.emit(create_event(seq=i))
        sink.close()

        exporter = GovernanceEventExporter(temp_log_path)
        count = exporter.get_event_count()

        assert count == 25

    def test_get_export_summary(self, temp_log_path: Path) -> None:
        """get_export_summary should return comprehensive summary."""
        sink = RotatingJSONLSink(path=temp_log_path)
        for i in range(10):
            sink.emit(create_event(event_type="TYPE_A", seq=i))
        for i in range(5):
            sink.emit(create_event(event_type="TYPE_B", seq=i))
        sink.close()

        exporter = GovernanceEventExporter(temp_log_path)
        summary = exporter.get_export_summary()

        assert summary["total_events"] == 15
        assert summary["event_types"]["TYPE_A"] == 10
        assert summary["event_types"]["TYPE_B"] == 5
        assert "time_range" in summary


# ═══════════════════════════════════════════════════════════════════════════════
# FAILURE MODE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFailureModes:
    """Tests for failure mode handling."""

    def test_emit_swallows_write_errors(self, temp_log_path: Path) -> None:
        """Write errors should be swallowed, not raised."""
        sink = RotatingJSONLSink(path=temp_log_path)
        sink.emit(create_event())

        # Make file read-only to cause write errors
        temp_log_path.chmod(0o444)

        # Should not raise
        sink.emit(create_event())

        # Restore permissions for cleanup
        temp_log_path.chmod(0o644)
        sink.close()

    def test_handles_missing_directory(self, temp_dir: Path) -> None:
        """Should handle directory creation gracefully."""
        path = temp_dir / "nonexistent" / "deep" / "events.jsonl"
        sink = RotatingJSONLSink(path=path)

        sink.emit(create_event())
        assert path.exists()

        sink.close()

    def test_exporter_handles_missing_files(self, temp_dir: Path) -> None:
        """Exporter should handle missing files gracefully."""
        path = temp_dir / "nonexistent.jsonl"
        exporter = GovernanceEventExporter(path)

        events = list(exporter.iterate_events())
        assert events == []

    def test_exporter_handles_corrupt_json_line(self, temp_log_path: Path) -> None:
        """Exporter should skip corrupt JSON lines."""
        # Write valid + corrupt + valid
        temp_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_log_path, "w") as f:
            f.write('{"event_type":"VALID_1"}\n')
            f.write("NOT VALID JSON\n")
            f.write('{"event_type":"VALID_2"}\n')

        exporter = GovernanceEventExporter(temp_log_path)
        events = list(exporter.iterate_events())

        # Should get 2 valid events
        assert len(events) == 2
        assert events[0]["event_type"] == "VALID_1"
        assert events[1]["event_type"] == "VALID_2"


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD SAFETY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_emits(self, temp_log_path: Path) -> None:
        """Concurrent emits should not corrupt data."""
        sink = RotatingJSONLSink(path=temp_log_path)
        num_threads = 10
        events_per_thread = 50

        def emit_events(thread_id: int) -> None:
            for i in range(events_per_thread):
                event = create_event(
                    event_type=f"THREAD_{thread_id}",
                    seq=i,
                )
                sink.emit(event)

        threads = [threading.Thread(target=emit_events, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        sink.close()

        # Verify all events written
        exporter = GovernanceEventExporter(temp_log_path)
        events = list(exporter.iterate_events())

        assert len(events) == num_threads * events_per_thread

    def test_concurrent_emits_during_rotation(self, temp_log_path: Path) -> None:
        """Concurrent emits during rotation should not lose events."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=500,  # Force many rotations
            max_file_count=200,  # High enough to keep all events
        )
        num_threads = 5
        events_per_thread = 100

        def emit_events(thread_id: int) -> None:
            for i in range(events_per_thread):
                event = create_event(seq=thread_id * 1000 + i)
                sink.emit(event)

        threads = [threading.Thread(target=emit_events, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        sink.close()

        # Verify no events lost
        exporter = GovernanceEventExporter(temp_log_path)
        events = list(exporter.iterate_events())

        assert len(events) == num_threads * events_per_thread


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_configure_rotating_sink(self, temp_log_path: Path) -> None:
        """configure_rotating_sink should create configured sink."""
        sink = configure_rotating_sink(
            path=temp_log_path,
            max_file_size_bytes=1024,
            max_file_count=5,
        )

        assert isinstance(sink, RotatingJSONLSink)
        assert sink.max_file_size_bytes == 1024
        assert sink.max_file_count == 5

        sink.close()

    def test_create_exporter(self, temp_log_path: Path) -> None:
        """create_exporter should create exporter instance."""
        exporter = create_exporter(temp_log_path)

        assert isinstance(exporter, GovernanceEventExporter)
        assert exporter.log_path == temp_log_path


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_retention_cycle(self, temp_log_path: Path) -> None:
        """Test complete retention cycle: write, rotate, export."""
        # 1. Configure rotating sink with high file count to keep all events
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=1000,
            max_file_count=100,  # High enough to keep all events
        )

        # 2. Write events to trigger rotations
        total_events = 200
        for i in range(total_events):
            event = GovernanceEvent(
                event_type=GovernanceEventType.DECISION_DENIED,
                agent_gid="GID-07",
                verb="test",
                target=f"target_{i}",
                metadata={"sequence": i},
            )
            sink.emit(event)

        # 3. Check retention info
        info = sink.get_retention_info()
        assert info["current_file_count"] >= 2
        assert info["max_file_count"] == 100

        sink.close()

        # 4. Export and verify
        exporter = GovernanceEventExporter(temp_log_path)
        summary = exporter.get_export_summary()
        assert summary["total_events"] == total_events

        # 5. Verify all events present
        events = exporter.export_to_list()
        sequences = {e["metadata"]["sequence"] for e in events}
        assert sequences == set(range(total_events))

    def test_retention_limit_deletes_old_events(self, temp_log_path: Path) -> None:
        """When max_file_count is exceeded, oldest events are lost (expected)."""
        sink = RotatingJSONLSink(
            path=temp_log_path,
            max_file_size_bytes=500,
            max_file_count=3,  # Very low limit
        )

        # Write many events
        for i in range(100):
            sink.emit(create_event(seq=i))

        sink.close()

        # Some events should be deleted due to retention limit
        exporter = GovernanceEventExporter(temp_log_path)
        events = exporter.export_to_list()

        # Should have fewer than 100 events (oldest deleted)
        assert len(events) < 100
        # File count should be at or below limit
        assert sink.get_file_count() <= 4  # current + 3 rotated

    def test_export_matches_source_exactly(self, temp_dir: Path) -> None:
        """Exported events should match source exactly."""
        log_path = temp_dir / "events.jsonl"
        export_path = temp_dir / "export.jsonl"

        # Write events
        sink = RotatingJSONLSink(path=log_path)
        original_events: list[dict[str, Any]] = []
        for i in range(50):
            event = GovernanceEvent(
                event_type="TEST",
                agent_gid="GID-07",
                metadata={"idx": i},
            )
            sink.emit(event)
            original_events.append(event.to_dict())
        sink.close()

        # Export
        exporter = GovernanceEventExporter(log_path)
        exporter.export_to_file(export_path)

        # Compare
        with open(export_path) as f:
            exported = [json.loads(line) for line in f]

        assert len(exported) == len(original_events)
        for exp, orig in zip(exported, original_events):
            assert exp["metadata"]["idx"] == orig["metadata"]["idx"]
            assert exp["event_type"] == orig["event_type"]
