"""
🟢 DAN (GID-07) — Persistent Denial Registry Tests
PAC-DAN-06: Persistent Denial Registry (Replay Protection)

Tests for:
- Denial survives process restart
- Replay blocked after restart
- Registry corruption → fail closed
- No silent downgrade to memory-only
- No performance regression
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest

from core.governance.denial_registry import (
    DEFAULT_DENIAL_DB_PATH,
    BaseDenialRegistry,
    DenialKey,
    DenialPersistenceError,
    InMemoryDenialRegistry,
    PersistentDenialRegistry,
    configure_denial_registry,
    get_persistent_denial_registry,
    is_persistent_mode,
    reset_persistent_denial_registry,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Create a temporary database path."""
    temp_dir = tempfile.mkdtemp(prefix="denial_registry_test_")
    db_path = Path(temp_dir) / "test_denials.db"

    yield db_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def persistent_registry(temp_db_path: Path) -> Generator[PersistentDenialRegistry, None, None]:
    """Create a persistent registry with temporary database."""
    registry = PersistentDenialRegistry(db_path=temp_db_path)

    yield registry

    registry.close()


@pytest.fixture
def memory_registry() -> InMemoryDenialRegistry:
    """Create an in-memory registry."""
    return InMemoryDenialRegistry()


@pytest.fixture(autouse=True)
def reset_global_registry() -> Generator[None, None, None]:
    """Reset global registry before and after each test."""
    reset_persistent_denial_registry()
    yield
    reset_persistent_denial_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# DENIAL KEY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDenialKey:
    """Tests for DenialKey hashing."""

    def test_key_hash_is_deterministic(self) -> None:
        """Same key inputs should produce same hash."""
        key1 = DenialKey("GID-07", "EXECUTE", "api/deploy.py")
        key2 = DenialKey("GID-07", "EXECUTE", "api/deploy.py")

        assert key1.to_hash() == key2.to_hash()

    def test_different_keys_produce_different_hashes(self) -> None:
        """Different key inputs should produce different hashes."""
        key1 = DenialKey("GID-07", "EXECUTE", "api/deploy.py")
        key2 = DenialKey("GID-07", "EXECUTE", "api/server.py")

        assert key1.to_hash() != key2.to_hash()

    def test_audit_ref_affects_hash(self) -> None:
        """Different audit_ref should produce different hash."""
        key1 = DenialKey("GID-07", "EXECUTE", "target", audit_ref="ref1")
        key2 = DenialKey("GID-07", "EXECUTE", "target", audit_ref="ref2")

        assert key1.to_hash() != key2.to_hash()


# ═══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestInMemoryRegistry:
    """Tests for in-memory denial registry."""

    def test_register_and_check_denial(self, memory_registry: InMemoryDenialRegistry) -> None:
        """Should register and detect denial."""
        memory_registry.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="api/deploy.py",
            denial_code="NOT_PERMITTED",
            intent_id="test-001",
        )

        assert memory_registry.is_denied("GID-07", "EXECUTE", "api/deploy.py")
        assert not memory_registry.is_denied("GID-07", "READ", "api/deploy.py")

    def test_clear_removes_all_denials(self, memory_registry: InMemoryDenialRegistry) -> None:
        """Clear should remove all denials."""
        memory_registry.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="target1",
            denial_code="TEST",
            intent_id="test-001",
        )
        memory_registry.register_denial(
            agent_gid="GID-07",
            verb="BLOCK",
            target="target2",
            denial_code="TEST",
            intent_id="test-002",
        )

        assert memory_registry.get_denial_count() == 2

        memory_registry.clear()

        assert memory_registry.get_denial_count() == 0

    def test_memory_registry_does_not_persist(self, memory_registry: InMemoryDenialRegistry) -> None:
        """In-memory registry should lose data when recreated."""
        memory_registry.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="target",
            denial_code="TEST",
            intent_id="test-001",
        )

        assert memory_registry.is_denied("GID-07", "EXECUTE", "target")

        # Create new registry
        new_registry = InMemoryDenialRegistry()

        # New registry should NOT have the denial
        assert not new_registry.is_denied("GID-07", "EXECUTE", "target")


# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENT REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPersistentRegistry:
    """Tests for SQLite-backed persistent denial registry."""

    def test_register_and_check_denial(self, persistent_registry: PersistentDenialRegistry) -> None:
        """Should register and detect denial."""
        persistent_registry.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="api/deploy.py",
            denial_code="NOT_PERMITTED",
            intent_id="test-001",
        )

        assert persistent_registry.is_denied("GID-07", "EXECUTE", "api/deploy.py")
        assert not persistent_registry.is_denied("GID-07", "READ", "api/deploy.py")

    def test_denial_survives_close_and_reopen(self, temp_db_path: Path) -> None:
        """Denial should persist across registry close and reopen."""
        # Register denial
        registry1 = PersistentDenialRegistry(db_path=temp_db_path)
        registry1.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="api/deploy.py",
            denial_code="NOT_PERMITTED",
            intent_id="test-001",
        )
        registry1.close()

        # Reopen registry (simulates process restart)
        registry2 = PersistentDenialRegistry(db_path=temp_db_path)

        # Denial should still be present
        assert registry2.is_denied("GID-07", "EXECUTE", "api/deploy.py")
        registry2.close()

    def test_replay_blocked_after_restart(self, temp_db_path: Path) -> None:
        """Replay attack should be blocked after process restart."""
        # First "process": register a denial
        registry1 = PersistentDenialRegistry(db_path=temp_db_path)
        registry1.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="api/deploy.py",
            denial_code="NOT_PERMITTED",
            intent_id="attack-001",
        )
        registry1.close()

        # Second "process": check if replay is blocked
        registry2 = PersistentDenialRegistry(db_path=temp_db_path)

        # The same action should be detected as previously denied
        is_blocked = registry2.is_denied("GID-07", "EXECUTE", "api/deploy.py")

        assert is_blocked, "Replay attack should be blocked after restart"
        registry2.close()

    def test_get_denial_returns_record(self, persistent_registry: PersistentDenialRegistry) -> None:
        """Should return denial record details."""
        denial_hash = persistent_registry.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="api/deploy.py",
            denial_code="NOT_PERMITTED",
            intent_id="test-001",
            audit_ref="audit-123",
        )

        record = persistent_registry.get_denial(denial_hash)

        assert record is not None
        assert record["agent_gid"] == "GID-07"
        assert record["verb"] == "EXECUTE"
        assert record["target"] == "api/deploy.py"
        assert record["denial_code"] == "NOT_PERMITTED"
        assert record["intent_id"] == "test-001"
        assert record["audit_ref"] == "audit-123"

    def test_denial_count_increments(self, persistent_registry: PersistentDenialRegistry) -> None:
        """Denial count should increment with each denial."""
        assert persistent_registry.get_denial_count() == 0

        persistent_registry.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="target1",
            denial_code="TEST",
            intent_id="test-001",
        )
        assert persistent_registry.get_denial_count() == 1

        persistent_registry.register_denial(
            agent_gid="GID-07",
            verb="BLOCK",
            target="target2",
            denial_code="TEST",
            intent_id="test-002",
        )
        assert persistent_registry.get_denial_count() == 2


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFailClosed:
    """Tests for fail-closed behavior."""

    def test_corrupted_database_fails_on_init(self, temp_db_path: Path) -> None:
        """Corrupted database should fail closed on initialization."""
        # Create a corrupted database file
        temp_db_path.parent.mkdir(parents=True, exist_ok=True)
        temp_db_path.write_text("this is not a valid sqlite database")

        with pytest.raises(DenialPersistenceError):
            PersistentDenialRegistry(db_path=temp_db_path)

    def test_is_denied_returns_true_on_connection_failure(self, persistent_registry: PersistentDenialRegistry) -> None:
        """is_denied should return True (fail-closed) if connection is lost."""
        # Force close the connection
        persistent_registry._conn = None

        # Should return True (assume denied) when we can't check
        assert persistent_registry.is_denied("GID-07", "EXECUTE", "target")

    def test_no_silent_fallback_to_memory(self) -> None:
        """Should not silently fall back to memory mode on failure."""
        # Try to create persistent registry with invalid path
        # (e.g., a directory that can't be created)
        with pytest.raises(DenialPersistenceError):
            PersistentDenialRegistry(db_path="/nonexistent/impossible/path/db.sqlite")


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFactory:
    """Tests for registry factory functions."""

    def test_configure_memory_mode(self) -> None:
        """configure_denial_registry should create in-memory registry."""
        registry = configure_denial_registry(mode="memory")

        assert isinstance(registry, InMemoryDenialRegistry)
        assert not is_persistent_mode()

    def test_configure_persistent_mode(self, temp_db_path: Path) -> None:
        """configure_denial_registry should create persistent registry."""
        registry = configure_denial_registry(mode="persistent", db_path=temp_db_path)

        assert isinstance(registry, PersistentDenialRegistry)
        assert is_persistent_mode()

    def test_get_registry_defaults_to_memory(self) -> None:
        """get_persistent_denial_registry should default to in-memory."""
        reset_persistent_denial_registry()

        registry = get_persistent_denial_registry()

        assert isinstance(registry, InMemoryDenialRegistry)

    def test_reset_clears_registry(self, temp_db_path: Path) -> None:
        """reset_persistent_denial_registry should clear and reset."""
        registry = configure_denial_registry(mode="persistent", db_path=temp_db_path)
        registry.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="target",
            denial_code="TEST",
            intent_id="test-001",
        )

        assert registry.get_denial_count() > 0

        reset_persistent_denial_registry()

        new_registry = get_persistent_denial_registry()
        assert new_registry.get_denial_count() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPerformance:
    """Basic performance tests (not benchmarks)."""

    def test_register_denial_is_fast(self, persistent_registry: PersistentDenialRegistry) -> None:
        """Denial registration should complete quickly."""
        start = time.perf_counter()

        for i in range(100):
            persistent_registry.register_denial(
                agent_gid="GID-07",
                verb="EXECUTE",
                target=f"target_{i}",
                denial_code="TEST",
                intent_id=f"test-{i}",
            )

        elapsed = time.perf_counter() - start

        # 100 denials should complete in under 1 second
        assert elapsed < 1.0, f"Registration too slow: {elapsed:.2f}s for 100 denials"

    def test_is_denied_lookup_is_fast(self, persistent_registry: PersistentDenialRegistry) -> None:
        """Denial lookup should be fast."""
        # Seed with denials
        for i in range(100):
            persistent_registry.register_denial(
                agent_gid="GID-07",
                verb="EXECUTE",
                target=f"target_{i}",
                denial_code="TEST",
                intent_id=f"test-{i}",
            )

        start = time.perf_counter()

        for i in range(100):
            persistent_registry.is_denied("GID-07", "EXECUTE", f"target_{i}")

        elapsed = time.perf_counter() - start

        # 100 lookups should complete in under 0.5 seconds
        assert elapsed < 0.5, f"Lookup too slow: {elapsed:.2f}s for 100 lookups"


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Integration tests for denial registry."""

    def test_multiple_agents_tracked_separately(self, persistent_registry: PersistentDenialRegistry) -> None:
        """Denials for different agents should be tracked separately."""
        persistent_registry.register_denial(
            agent_gid="GID-01",
            verb="EXECUTE",
            target="target",
            denial_code="TEST",
            intent_id="test-001",
        )
        persistent_registry.register_denial(
            agent_gid="GID-02",
            verb="EXECUTE",
            target="target",
            denial_code="TEST",
            intent_id="test-002",
        )

        assert persistent_registry.is_denied("GID-01", "EXECUTE", "target")
        assert persistent_registry.is_denied("GID-02", "EXECUTE", "target")
        assert not persistent_registry.is_denied("GID-03", "EXECUTE", "target")

    def test_audit_ref_isolation(self, persistent_registry: PersistentDenialRegistry) -> None:
        """Different audit_ref should be tracked separately."""
        persistent_registry.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="target",
            denial_code="TEST",
            intent_id="test-001",
            audit_ref="ref-A",
        )

        # Same action with different audit_ref should not be denied
        assert not persistent_registry.is_denied("GID-07", "EXECUTE", "target", audit_ref="ref-B")
        # Same action with same audit_ref should be denied
        assert persistent_registry.is_denied("GID-07", "EXECUTE", "target", audit_ref="ref-A")


# ═══════════════════════════════════════════════════════════════════════════════
# RESTART SIMULATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRestartSimulation:
    """Tests that simulate process restart scenarios."""

    def test_denial_persists_across_simulated_restart(self, temp_db_path: Path) -> None:
        """
        Simulate a process restart and verify denial persists.

        This is the core PAC-DAN-06 requirement.
        """
        # === FIRST PROCESS ===
        registry1 = PersistentDenialRegistry(db_path=temp_db_path)

        # Agent attempts forbidden action, gets denied
        registry1.register_denial(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="production/deploy.py",
            denial_code="EXECUTE_NOT_PERMITTED",
            intent_id="original-attack-001",
        )

        # Verify denial is recorded
        assert registry1.is_denied("GID-07", "EXECUTE", "production/deploy.py")
        denial_count_before = registry1.get_denial_count()

        # Close registry (simulates process shutdown)
        registry1.close()

        # === SECOND PROCESS (AFTER RESTART) ===
        registry2 = PersistentDenialRegistry(db_path=temp_db_path)

        # Verify denial count is preserved
        assert registry2.get_denial_count() == denial_count_before

        # Verify the same action is STILL denied (replay blocked)
        assert registry2.is_denied("GID-07", "EXECUTE", "production/deploy.py")

        registry2.close()

    def test_multiple_restarts_accumulate_denials(self, temp_db_path: Path) -> None:
        """Denials should accumulate across multiple restarts."""
        # First process
        r1 = PersistentDenialRegistry(db_path=temp_db_path)
        r1.register_denial("GID-01", "EXECUTE", "target1", "TEST", "id-1")
        r1.close()

        # Second process
        r2 = PersistentDenialRegistry(db_path=temp_db_path)
        r2.register_denial("GID-02", "EXECUTE", "target2", "TEST", "id-2")
        r2.close()

        # Third process
        r3 = PersistentDenialRegistry(db_path=temp_db_path)
        r3.register_denial("GID-03", "EXECUTE", "target3", "TEST", "id-3")

        # All three denials should be present
        assert r3.get_denial_count() == 3
        assert r3.is_denied("GID-01", "EXECUTE", "target1")
        assert r3.is_denied("GID-02", "EXECUTE", "target2")
        assert r3.is_denied("GID-03", "EXECUTE", "target3")

        r3.close()
