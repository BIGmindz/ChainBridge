"""
🟢 DAN (GID-07) — Persistent Denial Registry
PAC-DAN-06: Persistent Denial Registry (Replay Protection)

SQLite-backed denial registry that survives process restarts.

Key properties:
- Fail-closed: If persistence fails, execution blocks
- Durable: Denials survive restarts
- Deterministic: Same inputs → same outputs
- Auditable: All denials recorded with timestamps
- No silent fallback: No in-memory degradation

NO NEW GOVERNANCE LOGIC. Persistence only.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.governance.event_sink import emit_event
from core.governance.events import GovernanceEvent, GovernanceEventType

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_DENIAL_DB_PATH = "logs/denial_registry.db"
SCHEMA_VERSION = "1.0.0"

# Error codes
PERSISTENCE_ERROR_CODE = "FAIL_CLOSED_PERSISTENCE_ERROR"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class DenialPersistenceError(Exception):
    """Raised when denial persistence fails.

    This is a fail-closed error — execution must block.
    """

    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DenialKey:
    """Key for denial lookup.

    The denial key uniquely identifies a denied action.
    """

    agent_gid: str
    verb: str
    target: str
    audit_ref: str = ""

    def to_hash(self) -> str:
        """Compute deterministic hash of the denial key."""
        key_string = f"{self.agent_gid}:{self.verb}:{self.target}:{self.audit_ref}"
        return hashlib.sha256(key_string.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# ABSTRACT BASE
# ═══════════════════════════════════════════════════════════════════════════════


class BaseDenialRegistry(ABC):
    """Abstract base class for denial registries.

    Implementations must be fail-closed.
    """

    @abstractmethod
    def register_denial(
        self,
        agent_gid: str,
        verb: str,
        target: str,
        denial_code: str,
        intent_id: str,
        audit_ref: str = "",
    ) -> str:
        """Register a denied intent.

        Args:
            agent_gid: The agent GID
            verb: The verb that was denied
            target: The target of the denied action
            denial_code: The denial reason code
            intent_id: The intent ID
            audit_ref: Optional audit reference

        Returns:
            The denial hash

        Raises:
            DenialPersistenceError: If persistence fails
        """
        pass

    @abstractmethod
    def is_denied(
        self,
        agent_gid: str,
        verb: str,
        target: str,
        audit_ref: str = "",
    ) -> bool:
        """Check if an action is denied.

        Args:
            agent_gid: The agent GID
            verb: The verb
            target: The target
            audit_ref: Optional audit reference

        Returns:
            True if the action is denied
        """
        pass

    @abstractmethod
    def get_denial_count(self) -> int:
        """Get the total number of denials.

        Returns:
            Number of registered denials
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all denials (for testing only)."""
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY REGISTRY (FOR TESTING)
# ═══════════════════════════════════════════════════════════════════════════════


class InMemoryDenialRegistry(BaseDenialRegistry):
    """In-memory denial registry for testing.

    This is NOT suitable for production use.
    """

    def __init__(self) -> None:
        """Initialize the in-memory registry."""
        self._denials: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register_denial(
        self,
        agent_gid: str,
        verb: str,
        target: str,
        denial_code: str,
        intent_id: str,
        audit_ref: str = "",
    ) -> str:
        """Register a denied intent."""
        key = DenialKey(agent_gid, verb, target, audit_ref)
        denial_hash = key.to_hash()

        with self._lock:
            self._denials[denial_hash] = {
                "agent_gid": agent_gid,
                "verb": verb,
                "target": target,
                "denial_code": denial_code,
                "intent_id": intent_id,
                "audit_ref": audit_ref,
                "denied_at": datetime.now(timezone.utc).isoformat(),
            }

        return denial_hash

    def is_denied(
        self,
        agent_gid: str,
        verb: str,
        target: str,
        audit_ref: str = "",
    ) -> bool:
        """Check if an action is denied."""
        key = DenialKey(agent_gid, verb, target, audit_ref)
        denial_hash = key.to_hash()

        with self._lock:
            return denial_hash in self._denials

    def get_denial_count(self) -> int:
        """Get the total number of denials."""
        with self._lock:
            return len(self._denials)

    def clear(self) -> None:
        """Clear all denials."""
        with self._lock:
            self._denials.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENT REGISTRY (SQLITE)
# ═══════════════════════════════════════════════════════════════════════════════


class PersistentDenialRegistry(BaseDenialRegistry):
    """SQLite-backed persistent denial registry.

    Fail-closed: If SQLite operations fail, raises DenialPersistenceError.

    Schema:
        denials (
            denial_hash TEXT PRIMARY KEY,
            agent_gid TEXT NOT NULL,
            verb TEXT NOT NULL,
            target TEXT NOT NULL,
            denial_code TEXT NOT NULL,
            intent_id TEXT NOT NULL,
            audit_ref TEXT,
            denied_at TEXT NOT NULL
        )
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DENIAL_DB_PATH,
        fail_closed: bool = True,
    ) -> None:
        """Initialize the persistent registry.

        Args:
            db_path: Path to the SQLite database
            fail_closed: If True, raise on persistence failures

        Raises:
            DenialPersistenceError: If database cannot be initialized
        """
        self._db_path = Path(db_path)
        self._fail_closed = fail_closed
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None

        # Ensure directory exists
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            if self._fail_closed:
                raise DenialPersistenceError(f"Failed to create denial registry directory: {e}")

        # Initialize database
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize the SQLite database.

        Raises:
            DenialPersistenceError: If initialization fails
        """
        try:
            self._conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                isolation_level="DEFERRED",
            )

            # Enable WAL mode for better concurrent read/write
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")

            # Create schema
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS denials (
                    denial_hash TEXT PRIMARY KEY,
                    agent_gid TEXT NOT NULL,
                    verb TEXT NOT NULL,
                    target TEXT NOT NULL,
                    denial_code TEXT NOT NULL,
                    intent_id TEXT NOT NULL,
                    audit_ref TEXT,
                    denied_at TEXT NOT NULL
                )
            """
            )

            # Create indices for common lookups
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_denials_agent
                ON denials(agent_gid)
            """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_denials_denied_at
                ON denials(denied_at)
            """
            )

            self._conn.commit()

        except sqlite3.Error as e:
            self._emit_persistence_error("initialize", str(e))
            if self._fail_closed:
                raise DenialPersistenceError(f"Failed to initialize denial registry: {e}")

    def _emit_persistence_error(self, operation: str, error: str) -> None:
        """Emit a persistence error event."""
        try:
            event = GovernanceEvent(
                event_type=GovernanceEventType.DECISION_DENIED,
                agent_gid="SYSTEM",
                verb="PERSIST",
                target="denial_registry",
                metadata={
                    "error_code": PERSISTENCE_ERROR_CODE,
                    "operation": operation,
                    "error": error,
                },
            )
            emit_event(event)
        except Exception:
            # Telemetry is fail-open
            pass

    def register_denial(
        self,
        agent_gid: str,
        verb: str,
        target: str,
        denial_code: str,
        intent_id: str,
        audit_ref: str = "",
    ) -> str:
        """Register a denied intent.

        Writes synchronously to SQLite before returning.

        Raises:
            DenialPersistenceError: If write fails and fail_closed is True
        """
        key = DenialKey(agent_gid, verb, target, audit_ref)
        denial_hash = key.to_hash()
        denied_at = datetime.now(timezone.utc).isoformat()

        with self._lock:
            try:
                if self._conn is None:
                    raise DenialPersistenceError("Database connection not available")

                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO denials
                    (denial_hash, agent_gid, verb, target, denial_code, intent_id, audit_ref, denied_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        denial_hash,
                        agent_gid,
                        verb,
                        target,
                        denial_code,
                        intent_id,
                        audit_ref,
                        denied_at,
                    ),
                )
                self._conn.commit()

            except sqlite3.Error as e:
                self._emit_persistence_error("register_denial", str(e))
                if self._fail_closed:
                    raise DenialPersistenceError(f"Failed to persist denial: {e}")

        return denial_hash

    def is_denied(
        self,
        agent_gid: str,
        verb: str,
        target: str,
        audit_ref: str = "",
    ) -> bool:
        """Check if an action is denied."""
        key = DenialKey(agent_gid, verb, target, audit_ref)
        denial_hash = key.to_hash()

        with self._lock:
            try:
                if self._conn is None:
                    # Fail-closed: assume denied if we can't check
                    return True

                cursor = self._conn.execute(
                    "SELECT 1 FROM denials WHERE denial_hash = ?",
                    (denial_hash,),
                )
                return cursor.fetchone() is not None

            except sqlite3.Error as e:
                self._emit_persistence_error("is_denied", str(e))
                # Fail-closed: assume denied if we can't check
                return True

    def get_denial_count(self) -> int:
        """Get the total number of denials."""
        with self._lock:
            try:
                if self._conn is None:
                    return 0

                cursor = self._conn.execute("SELECT COUNT(*) FROM denials")
                row = cursor.fetchone()
                return row[0] if row else 0

            except sqlite3.Error:
                return 0

    def get_denial(self, denial_hash: str) -> Optional[dict[str, Any]]:
        """Get a specific denial record.

        Args:
            denial_hash: The denial hash to look up

        Returns:
            Denial record dict or None
        """
        with self._lock:
            try:
                if self._conn is None:
                    return None

                cursor = self._conn.execute(
                    """
                    SELECT agent_gid, verb, target, denial_code, intent_id, audit_ref, denied_at
                    FROM denials WHERE denial_hash = ?
                    """,
                    (denial_hash,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "denial_hash": denial_hash,
                        "agent_gid": row[0],
                        "verb": row[1],
                        "target": row[2],
                        "denial_code": row[3],
                        "intent_id": row[4],
                        "audit_ref": row[5],
                        "denied_at": row[6],
                    }
                return None

            except sqlite3.Error:
                return None

    def clear(self) -> None:
        """Clear all denials (for testing only)."""
        with self._lock:
            try:
                if self._conn:
                    self._conn.execute("DELETE FROM denials")
                    self._conn.commit()
            except sqlite3.Error:
                pass

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════


# Module-level registry instance
_denial_registry: Optional[BaseDenialRegistry] = None
_registry_mode: str = "memory"  # "memory" or "persistent"


def configure_denial_registry(
    mode: str = "memory",
    db_path: str | Path = DEFAULT_DENIAL_DB_PATH,
) -> BaseDenialRegistry:
    """Configure the denial registry.

    Args:
        mode: "memory" for testing, "persistent" for production
        db_path: Path to SQLite database (for persistent mode)

    Returns:
        The configured registry

    Raises:
        DenialPersistenceError: If persistent mode fails to initialize
    """
    global _denial_registry, _registry_mode

    if mode == "persistent":
        _denial_registry = PersistentDenialRegistry(db_path=db_path)
        _registry_mode = "persistent"
    else:
        _denial_registry = InMemoryDenialRegistry()
        _registry_mode = "memory"

    return _denial_registry


def get_persistent_denial_registry() -> BaseDenialRegistry:
    """Get the denial registry singleton.

    Returns a configured registry. If not configured, defaults to in-memory
    for backward compatibility with tests.

    Returns:
        The denial registry instance
    """
    global _denial_registry

    if _denial_registry is None:
        # Default to in-memory for backward compatibility
        _denial_registry = InMemoryDenialRegistry()

    return _denial_registry


def reset_persistent_denial_registry() -> None:
    """Reset the denial registry (for testing).

    Clears the registry and resets the singleton.
    """
    global _denial_registry, _registry_mode

    if _denial_registry is not None:
        _denial_registry.clear()
        if isinstance(_denial_registry, PersistentDenialRegistry):
            _denial_registry.close()

    _denial_registry = None
    _registry_mode = "memory"


def is_persistent_mode() -> bool:
    """Check if the registry is in persistent mode.

    Returns:
        True if using persistent storage
    """
    return _registry_mode == "persistent"
