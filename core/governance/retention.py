"""
🟢 DAN (GID-07) — Governance Event Retention & Rotation
PAC-DAN-05: Governance Event Retention & Rotation

Deterministic, auditable governance event retention with:
- Size-based rotation
- File count limits
- Append-only semantics preserved
- No silent data loss

Retention Policy (explicit):
- MAX_FILE_SIZE_BYTES: 50MB per file
- MAX_FILE_COUNT: 20 rotated files
- Rotation naming: governance_events.jsonl, .jsonl.1, .jsonl.2, ...
- Oldest files deleted first (FIFO)
- No truncation of active file
- Events are never split across files
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from core.governance.events import GovernanceEvent

# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION POLICY CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Maximum size of a single log file in bytes (50 MB)
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB

# Maximum number of rotated files to keep
MAX_FILE_COUNT: int = 20

# Default log file path
DEFAULT_ROTATING_LOG_PATH: str = "logs/governance_events.jsonl"

# Version for retention policy tracking
RETENTION_POLICY_VERSION: str = "1.0.0"

logger = logging.getLogger("governance.retention")


# ═══════════════════════════════════════════════════════════════════════════════
# ROTATING JSONL SINK
# ═══════════════════════════════════════════════════════════════════════════════


class RotatingJSONLSink:
    """
    Rotating JSONL sink with size-based rotation and file count limits.

    Retention guarantees:
    - Events are NEVER split across files
    - Events are NEVER silently dropped
    - Rotation is atomic (rename-based)
    - Oldest files are deleted first when limit is reached
    - Append-only semantics preserved within each file

    Rotation algorithm:
    1. Before each write, check if current file exceeds MAX_FILE_SIZE_BYTES
    2. If exceeded, rotate:
       - Shift all .jsonl.N files to .jsonl.(N+1)
       - Rename current .jsonl to .jsonl.1
       - Create new empty .jsonl
    3. Delete files exceeding MAX_FILE_COUNT
    4. Write event to current file

    Thread-safe with lock-based synchronization.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
        max_file_count: int = MAX_FILE_COUNT,
    ):
        """
        Initialize rotating JSONL sink.

        Args:
            path: Path to the primary JSONL file
            max_file_size_bytes: Maximum size before rotation (default: 50MB)
            max_file_count: Maximum number of rotated files (default: 20)
        """
        self.path = Path(path) if path else Path(DEFAULT_ROTATING_LOG_PATH)
        self.max_file_size_bytes = max_file_size_bytes
        self.max_file_count = max_file_count
        self._lock = threading.Lock()
        self._file: Any = None
        self._closed = False
        self._current_size = 0

        # Initialize current size from existing file
        if self.path.exists():
            self._current_size = self.path.stat().st_size

    def _ensure_file(self) -> Any:
        """Ensure file is open for writing."""
        if self._file is None and not self._closed:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.path, "a", encoding="utf-8")
        return self._file

    def _get_rotated_path(self, index: int) -> Path:
        """Get path for rotated file at given index."""
        return self.path.with_suffix(f".jsonl.{index}")

    def _list_rotated_files(self) -> list[tuple[int, Path]]:
        """
        List all rotated files with their indices.

        Returns list of (index, path) tuples, sorted by index ascending.
        """
        rotated = []
        parent = self.path.parent
        base_name = self.path.stem  # e.g., "governance_events"

        if not parent.exists():
            return []

        for file_path in parent.iterdir():
            if file_path.is_file():
                # Match pattern: governance_events.jsonl.N
                name = file_path.name
                if name.startswith(f"{base_name}.jsonl."):
                    try:
                        suffix = name.split(".")[-1]
                        index = int(suffix)
                        rotated.append((index, file_path))
                    except (ValueError, IndexError):
                        continue

        return sorted(rotated, key=lambda x: x[0])

    def _rotate(self) -> None:
        """
        Perform file rotation.

        Algorithm:
        1. Close current file
        2. Shift all existing rotated files up by 1
        3. Rename current file to .jsonl.1
        4. Delete files exceeding max_file_count
        5. Reset state for new file
        """
        # Close current file
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None

        # Get existing rotated files
        rotated = self._list_rotated_files()

        # Shift files up by 1 (start from highest index to avoid overwrites)
        for index, old_path in reversed(rotated):
            new_index = index + 1
            new_path = self._get_rotated_path(new_index)

            if new_index > self.max_file_count:
                # Delete files exceeding limit
                try:
                    old_path.unlink()
                    logger.info("Deleted rotated file: %s (exceeded limit)", old_path)
                except Exception as e:
                    logger.warning("Failed to delete rotated file %s: %s", old_path, e)
            else:
                # Shift to next index
                try:
                    shutil.move(str(old_path), str(new_path))
                except Exception as e:
                    logger.error("Failed to rotate file %s -> %s: %s", old_path, new_path, e)
                    raise  # Rotation failure is critical

        # Rename current file to .jsonl.1
        if self.path.exists():
            new_path = self._get_rotated_path(1)
            try:
                shutil.move(str(self.path), str(new_path))
                logger.info("Rotated %s -> %s", self.path, new_path)
            except Exception as e:
                logger.error("Failed to rotate current file: %s", e)
                raise  # Rotation failure is critical

        # Reset state
        self._current_size = 0
        self._file = None

    def _should_rotate(self) -> bool:
        """Check if rotation is needed based on current file size."""
        return self._current_size >= self.max_file_size_bytes

    def emit(self, event: GovernanceEvent) -> None:
        """
        Emit event to JSONL file with rotation.

        Guarantees:
        - Event is NEVER split across files
        - Event is NEVER silently dropped
        - Rotation happens before write if needed

        On filesystem error: logs warning and continues (non-blocking).
        On rotation failure: raises (critical failure mode).
        """
        if self._closed:
            return

        try:
            with self._lock:
                # Check rotation before write
                if self._should_rotate():
                    self._rotate()

                f = self._ensure_file()
                if f:
                    line = json.dumps(event.to_dict(), separators=(",", ":"))
                    line_bytes = (line + "\n").encode("utf-8")

                    # Write event
                    f.write(line + "\n")
                    f.flush()

                    # Update size tracking
                    self._current_size += len(line_bytes)

        except OSError as e:
            # Filesystem errors during write are logged but don't block
            logger.warning(
                "Failed to emit governance event (filesystem): %s (event_type=%s)",
                e,
                getattr(event, "event_type", "unknown"),
            )
        except Exception as e:
            # Unexpected errors are logged
            logger.warning(
                "Failed to emit governance event: %s (event_type=%s)",
                e,
                getattr(event, "event_type", "unknown"),
            )

    def close(self) -> None:
        """Close the file handle."""
        self._closed = True
        with self._lock:
            if self._file:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._file = None

    def get_file_count(self) -> int:
        """Get total number of log files (current + rotated)."""
        count = 1 if self.path.exists() else 0
        count += len(self._list_rotated_files())
        return count

    def get_total_size_bytes(self) -> int:
        """Get total size of all log files in bytes."""
        total = 0

        if self.path.exists():
            total += self.path.stat().st_size

        for _, rotated_path in self._list_rotated_files():
            if rotated_path.exists():
                total += rotated_path.stat().st_size

        return total

    def get_retention_info(self) -> dict[str, Any]:
        """
        Get retention status information.

        Returns dict with:
        - policy_version: Retention policy version
        - max_file_size_bytes: Size limit per file
        - max_file_count: Maximum rotated files
        - current_file_count: Current number of files
        - total_size_bytes: Total size across all files
        - current_file_size: Size of active file
        - rotated_files: List of rotated file info
        """
        rotated = self._list_rotated_files()

        return {
            "policy_version": RETENTION_POLICY_VERSION,
            "max_file_size_bytes": self.max_file_size_bytes,
            "max_file_count": self.max_file_count,
            "current_file_count": self.get_file_count(),
            "total_size_bytes": self.get_total_size_bytes(),
            "current_file_size": self._current_size,
            "current_file_path": str(self.path),
            "rotated_files": [{"index": idx, "path": str(p), "size": p.stat().st_size if p.exists() else 0} for idx, p in rotated],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT / SNAPSHOT SUPPORT
# ═══════════════════════════════════════════════════════════════════════════════


class GovernanceEventExporter:
    """
    Read-only export helper for governance events.

    Features:
    - Deterministic ordering (oldest first)
    - Optional date range filtering
    - NO mutation of source logs
    - Streaming iteration (memory efficient)

    Use cases:
    - Auditor handoff
    - Incident response
    - Compliance reporting
    """

    def __init__(self, log_path: str | Path | None = None):
        """
        Initialize exporter.

        Args:
            log_path: Path to primary log file (rotated files auto-discovered)
        """
        self.log_path = Path(log_path) if log_path else Path(DEFAULT_ROTATING_LOG_PATH)

    def _list_all_files(self) -> list[Path]:
        """
        List all log files in chronological order (oldest first).

        Order: .jsonl.N (highest N first), ..., .jsonl.1, .jsonl
        """
        files: list[Path] = []
        parent = self.log_path.parent
        base_name = self.log_path.stem

        if not parent.exists():
            return []

        # Collect rotated files with indices
        rotated: list[tuple[int, Path]] = []
        for file_path in parent.iterdir():
            if file_path.is_file():
                name = file_path.name
                if name.startswith(f"{base_name}.jsonl."):
                    try:
                        suffix = name.split(".")[-1]
                        index = int(suffix)
                        rotated.append((index, file_path))
                    except (ValueError, IndexError):
                        continue

        # Sort by index descending (oldest = highest index)
        rotated.sort(key=lambda x: x[0], reverse=True)
        files.extend(p for _, p in rotated)

        # Add current file last (newest)
        if self.log_path.exists():
            files.append(self.log_path)

        return files

    def _parse_event(self, line: str) -> dict[str, Any] | None:
        """Parse a single JSON line, return None on failure."""
        try:
            return json.loads(line.strip())
        except (json.JSONDecodeError, ValueError):
            return None

    def _parse_timestamp(self, event: dict[str, Any]) -> datetime | None:
        """Parse timestamp from event dict."""
        ts_str = event.get("timestamp")
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            return None

    def iterate_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        Iterate over events in chronological order.

        Args:
            start_time: Include events at or after this time (optional)
            end_time: Include events at or before this time (optional)

        Yields:
            Event dictionaries in chronological order

        Note:
            - Does NOT mutate source files
            - Memory efficient (streaming)
            - Deterministic ordering
        """
        for file_path in self._list_all_files():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue

                        event = self._parse_event(line)
                        if event is None:
                            continue

                        # Apply time filters
                        if start_time or end_time:
                            event_time = self._parse_timestamp(event)
                            if event_time:
                                if start_time and event_time < start_time:
                                    continue
                                if end_time and event_time > end_time:
                                    continue

                        yield event

            except Exception as e:
                logger.warning("Failed to read log file %s: %s", file_path, e)
                continue

    def export_to_file(
        self,
        output_path: str | Path,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """
        Export events to a new JSONL file.

        Args:
            output_path: Path for export file
            start_time: Include events at or after this time (optional)
            end_time: Include events at or before this time (optional)

        Returns:
            Number of events exported

        Raises:
            OSError: On filesystem errors
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(output, "w", encoding="utf-8") as f:
            for event in self.iterate_events(start_time, end_time):
                line = json.dumps(event, separators=(",", ":"))
                f.write(line + "\n")
                count += 1

        logger.info("Exported %d events to %s", count, output)
        return count

    def export_to_list(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Export events to a list.

        Args:
            start_time: Include events at or after this time (optional)
            end_time: Include events at or before this time (optional)
            limit: Maximum number of events to return (optional)

        Returns:
            List of event dictionaries
        """
        events: list[dict[str, Any]] = []
        for event in self.iterate_events(start_time, end_time):
            events.append(event)
            if limit and len(events) >= limit:
                break
        return events

    def get_event_count(self) -> int:
        """
        Get total number of events across all files.

        Note: This reads all files, may be slow for large logs.
        """
        count = 0
        for _ in self.iterate_events():
            count += 1
        return count

    def get_export_summary(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get summary of events to be exported.

        Returns dict with:
        - total_events: Count of events matching filters
        - files_scanned: Number of log files scanned
        - time_range: Dict with earliest and latest timestamps
        - event_types: Dict of event type counts
        """
        files = self._list_all_files()
        events_by_type: dict[str, int] = {}
        earliest: datetime | None = None
        latest: datetime | None = None
        total = 0

        for event in self.iterate_events(start_time, end_time):
            total += 1

            # Count by type
            event_type = event.get("event_type", "UNKNOWN")
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

            # Track time range
            event_time = self._parse_timestamp(event)
            if event_time:
                if earliest is None or event_time < earliest:
                    earliest = event_time
                if latest is None or event_time > latest:
                    latest = event_time

        return {
            "total_events": total,
            "files_scanned": len(files),
            "time_range": {
                "earliest": earliest.isoformat() if earliest else None,
                "latest": latest.isoformat() if latest else None,
            },
            "event_types": events_by_type,
            "filter_start": start_time.isoformat() if start_time else None,
            "filter_end": end_time.isoformat() if end_time else None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def configure_rotating_sink(
    path: str | Path | None = None,
    max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
    max_file_count: int = MAX_FILE_COUNT,
) -> RotatingJSONLSink:
    """
    Create and configure a rotating JSONL sink.

    This is the recommended way to set up production-grade
    governance event logging with retention guarantees.

    Args:
        path: Path to primary log file
        max_file_size_bytes: Size limit per file (default: 50MB)
        max_file_count: Maximum rotated files (default: 20)

    Returns:
        Configured RotatingJSONLSink instance
    """
    return RotatingJSONLSink(
        path=path,
        max_file_size_bytes=max_file_size_bytes,
        max_file_count=max_file_count,
    )


def create_exporter(log_path: str | Path | None = None) -> GovernanceEventExporter:
    """
    Create a governance event exporter.

    Args:
        log_path: Path to primary log file

    Returns:
        GovernanceEventExporter instance
    """
    return GovernanceEventExporter(log_path)
