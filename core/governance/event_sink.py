"""
🟣 DAN (GID-07) — Governance Event Sink
PAC-GOV-OBS-01: Governance Observability & Event Telemetry

Transport abstraction for governance events.
Provides non-blocking, failure-tolerant event emission.

Key properties:
- Non-blocking: Never alters execution flow
- Failure-tolerant: Emission failures are swallowed and logged
- Append-only: Events are never modified or deleted
- Pluggable: Protocol-based sink abstraction
"""

from __future__ import annotations

import json
import logging
import threading
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable, Optional

if TYPE_CHECKING:
    from core.governance.events import GovernanceEvent

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SINK_VERSION = "1.0.0"
DEFAULT_EVENT_LOG = "logs/governance_events.jsonl"

logger = logging.getLogger("governance.events")


# ═══════════════════════════════════════════════════════════════════════════════
# SINK PROTOCOL
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class GovernanceEventSink(Protocol):
    """
    Protocol for governance event sinks.

    Implementations must:
    - Be non-blocking
    - Swallow failures (log but don't raise)
    - Support append-only semantics
    """

    @abstractmethod
    def emit(self, event: GovernanceEvent) -> None:
        """
        Emit a governance event.

        This method MUST NOT raise exceptions.
        Failures should be logged but swallowed.
        """
        ...

    def close(self) -> None:
        """Close the sink and release resources."""
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# JSONL FILE SINK
# ═══════════════════════════════════════════════════════════════════════════════


class JSONLFileSink:
    """
    Append-only JSONL file sink for governance events.

    Writes events as newline-delimited JSON to a file.
    Thread-safe with lock-based synchronization.

    Attributes:
        path: Path to the JSONL file
        _lock: Threading lock for write synchronization
        _file: File handle (lazy opened)
    """

    def __init__(self, path: str | Optional[Path] = None):
        """
        Initialize JSONL file sink.

        Args:
            path: Path to JSONL file (default: logs/governance_events.jsonl)
        """
        self.path = Path(path) if path else Path(DEFAULT_EVENT_LOG)
        self._lock = threading.Lock()
        self._file: Any = None
        self._closed = False

    def _ensure_file(self) -> Any:
        """Ensure file is open for writing."""
        if self._file is None and not self._closed:
            # Create parent directories
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.path, "a", encoding="utf-8")
        return self._file

    def emit(self, event: GovernanceEvent) -> None:
        """
        Emit event to JSONL file.

        Non-blocking, failure-tolerant.
        """
        if self._closed:
            return

        try:
            with self._lock:
                f = self._ensure_file()
                if f:
                    line = json.dumps(event.to_dict(), separators=(",", ":"))
                    f.write(line + "\n")
                    f.flush()
        except Exception as e:
            # Swallow failures, log only
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


# ═══════════════════════════════════════════════════════════════════════════════
# NULL SINK (FOR TESTING / DISABLED MODE)
# ═══════════════════════════════════════════════════════════════════════════════


class NullSink:
    """
    No-op sink that discards all events.

    Used for testing or when telemetry is disabled.
    """

    def emit(self, event: GovernanceEvent) -> None:
        """Discard event."""
        pass

    def close(self) -> None:
        """No-op close."""
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY SINK (FOR TESTING)
# ═══════════════════════════════════════════════════════════════════════════════


class InMemorySink:
    """
    In-memory sink that stores events in a list.

    Used for testing to capture and assert on emitted events.
    """

    def __init__(self) -> None:
        self.events: list[GovernanceEvent] = []
        self._lock = threading.Lock()

    def emit(self, event: GovernanceEvent) -> None:
        """Store event in memory."""
        with self._lock:
            self.events.append(event)

    def close(self) -> None:
        """Clear events."""
        with self._lock:
            self.events.clear()

    def get_events(self, event_type: Optional[str] = None) -> list[GovernanceEvent]:
        """
        Get captured events, optionally filtered by type.

        Args:
            event_type: Filter by event type (optional)

        Returns:
            List of captured events
        """
        with self._lock:
            if event_type:
                return [e for e in self.events if e.event_type == event_type]
            return list(self.events)

    def clear(self) -> None:
        """Clear all captured events."""
        with self._lock:
            self.events.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL EMITTER
# ═══════════════════════════════════════════════════════════════════════════════


class GovernanceEventEmitter:
    """
    Global governance event emitter.

    Singleton-like pattern for application-wide event emission.
    Supports multiple sinks (fan-out).

    Usage:
        from core.governance.event_sink import emitter
        emitter.emit(event)
    """

    def __init__(self) -> None:
        self._sinks: list[GovernanceEventSink] = []
        self._lock = threading.Lock()
        self._enabled = True

    def add_sink(self, sink: GovernanceEventSink) -> None:
        """Add a sink to receive events."""
        with self._lock:
            self._sinks.append(sink)

    def remove_sink(self, sink: GovernanceEventSink) -> None:
        """Remove a sink."""
        with self._lock:
            if sink in self._sinks:
                self._sinks.remove(sink)

    def clear_sinks(self) -> None:
        """Remove all sinks."""
        with self._lock:
            for sink in self._sinks:
                try:
                    sink.close()
                except Exception:
                    pass
            self._sinks.clear()

    def emit(self, event: GovernanceEvent) -> None:
        """
        Emit event to all registered sinks.

        Non-blocking, failure-tolerant.
        """
        if not self._enabled:
            return

        with self._lock:
            sinks = list(self._sinks)

        for sink in sinks:
            try:
                sink.emit(event)
            except Exception as e:
                logger.warning("Sink emission failed: %s", e)

    def enable(self) -> None:
        """Enable event emission."""
        self._enabled = True

    def disable(self) -> None:
        """Disable event emission (events are discarded)."""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """Check if emission is enabled."""
        return self._enabled

    @contextmanager
    def capture(self) -> InMemorySink:
        """
        Context manager to capture events in memory.

        Useful for testing.

        Usage:
            with emitter.capture() as sink:
                # ... code that emits events ...
                assert len(sink.events) == 1
        """
        sink = InMemorySink()
        self.add_sink(sink)
        try:
            yield sink
        finally:
            self.remove_sink(sink)


# Global emitter instance
emitter = GovernanceEventEmitter()


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def emit_event(event: GovernanceEvent) -> None:
    """
    Emit a governance event via the global emitter.

    This is the primary entry point for event emission.
    """
    emitter.emit(event)


def configure_default_sink(path: str | Optional[Path] = None) -> JSONLFileSink:
    """
    Configure the default JSONL file sink.

    Returns the sink for optional further configuration.
    """
    sink = JSONLFileSink(path)
    emitter.add_sink(sink)
    return sink


def configure_null_sink() -> NullSink:
    """
    Configure a null sink (discard all events).

    Useful for testing or when telemetry should be disabled.
    """
    sink = NullSink()
    emitter.add_sink(sink)
    return sink
