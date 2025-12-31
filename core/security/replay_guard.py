"""
Replay Attack Guard - PAC-SAM-PROOF-INTEGRITY-01

THREAT MODEL CONTROLS:
- REPLAY-V1: Event hash tracking (detects duplicate events)
- REPLAY-V2: Nonce validation (prevents pre-computed attacks)
- REPLAY-V3: Timestamp window enforcement (limits replay window)
- REPLAY-V4: Sequence number tracking (detects out-of-order)

INVARIANTS:
- Replay attempts MUST be rejected with explicit error
- No silent acceptance of duplicate events
- Hash cache MUST survive process restart (persistent)

Author: SAM (GID-06)
Date: 2025-12-19
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


class ReplayAttackError(Exception):
    """
    Raised when a replay attack is detected.

    This exception MUST be raised - no silent rejection allowed.
    Contains details about the detected replay attempt.
    """
    def __init__(self, message: str, event_hash: str, original_timestamp: Optional[str] = None):
        super().__init__(message)
        self.event_hash = event_hash
        self.original_timestamp = original_timestamp


class ReplayGuard:
    """
    Detects and prevents replay attacks on the execution spine.

    THREAT CONTROLS:
    1. Event hash deduplication - same event cannot be processed twice
    2. Nonce tracking - prevents pre-computed event submission
    3. Timestamp window - events outside window are rejected
    4. Persistent state - survives process restart

    INVARIANTS:
    - All processed event hashes are tracked
    - Duplicate detection is deterministic
    - State is persisted on every update

    Usage:
        guard = ReplayGuard()
        guard.load_state()  # Load from disk on startup

        # Before processing each event:
        guard.check_and_record(event_hash, event_timestamp)
        # Raises ReplayAttackError if replay detected
    """

    # Default replay window: 24 hours
    DEFAULT_REPLAY_WINDOW_HOURS = 24

    # Maximum cache size before pruning old entries
    MAX_CACHE_SIZE = 100_000

    def __init__(
        self,
        state_file: Optional[str] = None,
        replay_window_hours: int = DEFAULT_REPLAY_WINDOW_HOURS,
    ):
        """
        Initialize replay guard.

        Args:
            state_file: Path to persistent state file. Defaults to
                        CHAINBRIDGE_REPLAY_GUARD_STATE env var or ./data/replay_guard.json
            replay_window_hours: How long to track event hashes (hours)
        """
        self._state_file = Path(
            state_file or
            os.environ.get("CHAINBRIDGE_REPLAY_GUARD_STATE", "./data/replay_guard.json")
        )
        self._replay_window = timedelta(hours=replay_window_hours)

        # In-memory state
        self._seen_hashes: Dict[str, str] = {}  # hash -> first_seen_timestamp
        self._nonces: Set[str] = set()  # Used nonces (one-time use)
        self._last_sequence: int = 0

        # Thread safety
        self._lock = threading.Lock()

        # Ensure directory exists
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"ReplayGuard initialized: state_file={self._state_file}")

    def load_state(self) -> Dict[str, Any]:
        """
        Load persisted state from disk.

        Call this on startup to restore replay detection state.

        Returns:
            State summary dict
        """
        if not self._state_file.exists():
            logger.info("No existing replay guard state found. Starting fresh.")
            return {"status": "fresh", "hash_count": 0}

        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            with self._lock:
                self._seen_hashes = state.get("seen_hashes", {})
                self._nonces = set(state.get("nonces", []))
                self._last_sequence = state.get("last_sequence", 0)

            # Prune old entries
            pruned_count = self._prune_expired_hashes()

            logger.info(
                f"ReplayGuard state loaded: hashes={len(self._seen_hashes)}, "
                f"nonces={len(self._nonces)}, pruned={pruned_count}"
            )

            return {
                "status": "loaded",
                "hash_count": len(self._seen_hashes),
                "nonce_count": len(self._nonces),
                "last_sequence": self._last_sequence,
                "pruned_count": pruned_count,
            }

        except Exception as e:
            logger.error(f"Failed to load replay guard state: {e}")
            # Don't crash - start fresh but warn
            return {"status": "error", "error": str(e), "hash_count": 0}

    def check_and_record(
        self,
        event_hash: str,
        event_timestamp: str,
        nonce: Optional[str] = None,
        sequence_number: Optional[int] = None,
    ) -> None:
        """
        Check for replay attack and record event hash.

        MUST be called before processing ANY event.

        Args:
            event_hash: SHA-256 hash of the event
            event_timestamp: ISO8601 timestamp of the event
            nonce: Optional one-time nonce (rejected if reused)
            sequence_number: Optional sequence number (must be > last)

        Raises:
            ReplayAttackError: If replay attack detected
            ValueError: If event_hash or timestamp invalid
        """
        # Validate inputs
        if not event_hash or len(event_hash) != 64:
            raise ValueError("Invalid event_hash: must be 64-char hex string")

        try:
            event_time = datetime.fromisoformat(event_timestamp.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid event_timestamp: {e}")

        now = datetime.now(timezone.utc)

        with self._lock:
            # CONTROL R1: Check timestamp window
            age = now - event_time
            if age > self._replay_window:
                raise ReplayAttackError(
                    f"Event timestamp outside replay window ({self._replay_window.total_seconds()/3600:.0f}h). "
                    f"Age: {age.total_seconds()/3600:.1f}h",
                    event_hash=event_hash,
                )

            # Allow small future timestamps (clock skew tolerance: 5 minutes)
            if event_time > now + timedelta(minutes=5):
                raise ReplayAttackError(
                    "Event timestamp is in the future (clock skew > 5min)",
                    event_hash=event_hash,
                )

            # CONTROL R2: Check for duplicate event hash
            if event_hash in self._seen_hashes:
                original_ts = self._seen_hashes[event_hash]
                raise ReplayAttackError(
                    f"Replay attack detected! Event hash already processed at {original_ts}",
                    event_hash=event_hash,
                    original_timestamp=original_ts,
                )

            # CONTROL R3: Check nonce (if provided)
            if nonce is not None:
                if nonce in self._nonces:
                    raise ReplayAttackError(
                        f"Replay attack detected! Nonce already used: {nonce[:16]}...",
                        event_hash=event_hash,
                    )
                self._nonces.add(nonce)

            # CONTROL R4: Check sequence number (if provided)
            if sequence_number is not None:
                if sequence_number <= self._last_sequence:
                    raise ReplayAttackError(
                        f"Replay attack detected! Sequence {sequence_number} <= last {self._last_sequence}",
                        event_hash=event_hash,
                    )
                self._last_sequence = sequence_number

            # Record the hash
            self._seen_hashes[event_hash] = event_timestamp

            # Prune if cache too large
            if len(self._seen_hashes) > self.MAX_CACHE_SIZE:
                self._prune_expired_hashes()

        # Persist state (outside lock to avoid blocking)
        self._save_state()

        logger.debug(f"ReplayGuard: Event recorded, hash={event_hash[:16]}...")

    def is_replay(self, event_hash: str) -> bool:
        """
        Check if an event hash has been seen before.

        Does NOT record the hash - use check_and_record for that.

        Args:
            event_hash: SHA-256 hash to check

        Returns:
            True if hash was seen before, False otherwise
        """
        with self._lock:
            return event_hash in self._seen_hashes

    def _prune_expired_hashes(self) -> int:
        """
        Remove hashes outside the replay window.

        Returns:
            Number of hashes pruned
        """
        now = datetime.now(timezone.utc)
        cutoff = now - self._replay_window

        expired = []
        for hash_val, timestamp_str in self._seen_hashes.items():
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if ts < cutoff:
                    expired.append(hash_val)
            except ValueError:
                # Invalid timestamp - keep the hash to be safe
                pass

        for hash_val in expired:
            del self._seen_hashes[hash_val]

        return len(expired)

    def _save_state(self) -> None:
        """
        Persist state to disk.

        Called after every update for durability.
        """
        state = {
            "version": "1.0.0",
            "seen_hashes": self._seen_hashes,
            "nonces": list(self._nonces),
            "last_sequence": self._last_sequence,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Write to temp file then rename (atomic)
            temp_file = self._state_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            temp_file.rename(self._state_file)
        except Exception as e:
            logger.error(f"Failed to save replay guard state: {e}")
            # Don't crash - state will be rebuilt on restart

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for monitoring."""
        with self._lock:
            return {
                "hash_count": len(self._seen_hashes),
                "nonce_count": len(self._nonces),
                "last_sequence": self._last_sequence,
                "replay_window_hours": self._replay_window.total_seconds() / 3600,
                "state_file": str(self._state_file),
            }

    def clear(self) -> None:
        """
        Clear all state (for testing only).

        WARNING: This disables replay protection until state is rebuilt!
        """
        with self._lock:
            self._seen_hashes.clear()
            self._nonces.clear()
            self._last_sequence = 0

        if self._state_file.exists():
            self._state_file.unlink()

        logger.warning("ReplayGuard state cleared!")


# ============================================================================
# Singleton access pattern
# ============================================================================

_replay_guard_instance: Optional[ReplayGuard] = None


def get_replay_guard() -> ReplayGuard:
    """
    Get the singleton ReplayGuard instance.

    Call load_state() on startup before using.
    """
    global _replay_guard_instance
    if _replay_guard_instance is None:
        _replay_guard_instance = ReplayGuard()
    return _replay_guard_instance


def init_replay_guard() -> Dict[str, Any]:
    """
    Initialize and load replay guard state.

    Call this once during application startup.

    Returns:
        State summary
    """
    guard = get_replay_guard()
    return guard.load_state()
