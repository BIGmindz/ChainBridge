"""
ChainBridge Bootstrap Protocol — Test Suite
════════════════════════════════════════════════════════════════════════════════

Tests for bootstrap enforcement per PAC-016.

Test Categories:
- Missing bootstrap → FAIL
- Partial bootstrap → FAIL
- Re-bootstrap mid-session → FAIL
- Valid bootstrap → PASS
- Terminal visibility

════════════════════════════════════════════════════════════════════════════════
"""

import io
from datetime import datetime

import pytest

from core.governance.bootstrap_state import (
    LOCK_NAMES,
    BootstrapBuilder,
    BootstrapError,
    BootstrapIncompleteError,
    BootstrapLock,
    BootstrapRequiredError,
    BootstrapState,
    BootstrapStatus,
    LockAlreadyAcquiredError,
    LockState,
    RebootstrapForbiddenError,
    clear_current_session,
    get_current_session,
    require_sealed_session,
    set_current_session,
)
from core.governance.bootstrap_enforcer import (
    BootstrapEnforcer,
    BootstrapResult,
    BootstrapTerminalRenderer,
    bootstrap,
    bootstrap_session,
    get_bootstrap_enforcer,
    is_session_bootstrapped,
    require_bootstrap_before_pac,
    requires_bootstrap,
    reset_bootstrap_enforcer,
)
from core.governance.terminal_gates import (
    FAIL_SYMBOL,
    PASS_SYMBOL,
    TerminalGateRenderer,
)
from core.governance.snapshot_enforcer import (
    ingest_snapshot,
    reset_snapshot_enforcer,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

# Standard test hash for snapshot ingestion
TEST_SNAPSHOT_HASH = "sha256:test1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"


@pytest.fixture(autouse=True)
def reset_state():
    """Reset all singletons before each test and provide locked snapshot."""
    reset_bootstrap_enforcer()
    reset_snapshot_enforcer()
    
    # Provide locked snapshot as prerequisite for bootstrap (PAC-018)
    ingest_snapshot(
        source="test",
        archive_hash=TEST_SNAPSHOT_HASH,
        file_count=10,
    )
    
    yield
    
    reset_bootstrap_enforcer()
    reset_snapshot_enforcer()


@pytest.fixture
def buffer():
    """Create StringIO buffer for output capture."""
    return io.StringIO()


@pytest.fixture
def renderer(buffer):
    """Create terminal renderer with buffer."""
    return TerminalGateRenderer(output=buffer)


@pytest.fixture
def bootstrap_renderer(renderer):
    """Create bootstrap renderer."""
    return BootstrapTerminalRenderer(renderer=renderer)


@pytest.fixture
def enforcer(bootstrap_renderer):
    """Create enforcer with renderer."""
    return BootstrapEnforcer(renderer=bootstrap_renderer)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: LOCK STATE
# ═══════════════════════════════════════════════════════════════════════════════


class TestLockState:
    """Test LockState immutability and acquisition."""
    
    def test_lock_starts_unacquired(self):
        """Lock starts in unacquired state."""
        lock = LockState(lock_id=BootstrapLock.BOOT_01)
        
        assert lock.acquired is False
        assert lock.value is None
        assert lock.acquired_at is None
    
    def test_acquire_returns_new_state(self):
        """Acquiring lock returns new LockState."""
        original = LockState(lock_id=BootstrapLock.BOOT_01)
        acquired = original.acquire("GID-01:Cody")
        
        # Original unchanged
        assert original.acquired is False
        
        # New state is acquired
        assert acquired.acquired is True
        assert acquired.value == "GID-01:Cody"
        assert acquired.acquired_at is not None
    
    def test_cannot_acquire_twice(self):
        """Cannot acquire already-acquired lock."""
        lock = LockState(lock_id=BootstrapLock.BOOT_01)
        acquired = lock.acquire("GID-01:Cody")
        
        with pytest.raises(LockAlreadyAcquiredError):
            acquired.acquire("GID-02:Other")
    
    def test_lock_name_lookup(self):
        """Lock name is looked up correctly."""
        for lock in BootstrapLock:
            state = LockState(lock_id=lock)
            assert state.lock_name == LOCK_NAMES[lock]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BOOTSTRAP STATE
# ═══════════════════════════════════════════════════════════════════════════════


class TestBootstrapState:
    """Test BootstrapState immutability and transitions."""
    
    def test_initial_state(self):
        """Initial state has no locks acquired."""
        state = BootstrapState()
        
        assert state.identity_locked is False
        assert state.mode_locked is False
        assert state.lane_locked is False
        assert state.tools_locked is False
        assert state.handshake_complete is False
        assert state.all_locks_acquired is False
        assert state.is_sealed is False
        assert state.status == BootstrapStatus.NOT_STARTED
    
    def test_acquire_identity(self):
        """acquire_identity locks identity."""
        state = BootstrapState()
        new_state = state.acquire_identity("GID-01", "Cody")
        
        # Original unchanged
        assert state.identity_locked is False
        
        # New state has identity
        assert new_state.identity_locked is True
        assert new_state.gid == "GID-01"
        assert new_state.role == "Cody"
        assert new_state.status == BootstrapStatus.IN_PROGRESS
    
    def test_acquire_mode(self):
        """acquire_mode locks mode."""
        state = BootstrapState().acquire_identity("GID-01", "Cody")
        new_state = state.acquire_mode("EXECUTION")
        
        assert new_state.mode_locked is True
        assert new_state.mode == "EXECUTION"
    
    def test_acquire_lane(self):
        """acquire_lane locks lane."""
        state = BootstrapState().acquire_identity("GID-01", "Cody").acquire_mode("EXECUTION")
        new_state = state.acquire_lane("GOVERNANCE")
        
        assert new_state.lane_locked is True
        assert new_state.lane == "GOVERNANCE"
    
    def test_acquire_tools(self):
        """acquire_tools locks tools."""
        state = (
            BootstrapState()
            .acquire_identity("GID-01", "Cody")
            .acquire_mode("EXECUTION")
            .acquire_lane("GOVERNANCE")
        )
        new_state = state.acquire_tools(
            permitted=frozenset(["read_file", "write_file"]),
            stripped=frozenset(["delete_file"]),
        )
        
        assert new_state.tools_locked is True
        assert "read_file" in new_state.permitted_tools
        assert "delete_file" in new_state.stripped_tools
    
    def test_complete_handshake(self):
        """complete_handshake locks handshake."""
        state = (
            BootstrapState()
            .acquire_identity("GID-01", "Cody")
            .acquire_mode("EXECUTION")
            .acquire_lane("GOVERNANCE")
            .acquire_tools(frozenset(["read_file"]), frozenset())
        )
        new_state = state.complete_handshake("GID-01 | EXECUTION | GOVERNANCE")
        
        assert new_state.handshake_complete is True
        assert new_state.echo_handshake == "GID-01 | EXECUTION | GOVERNANCE"
    
    def test_all_locks_acquired(self):
        """all_locks_acquired is True when all 5 locks acquired."""
        state = (
            BootstrapState()
            .acquire_identity("GID-01", "Cody")
            .acquire_mode("EXECUTION")
            .acquire_lane("GOVERNANCE")
            .acquire_tools(frozenset(), frozenset())
            .complete_handshake("test")
        )
        
        assert state.all_locks_acquired is True
    
    def test_missing_locks(self):
        """missing_locks returns list of unacquired locks."""
        state = BootstrapState().acquire_identity("GID-01", "Cody")
        
        missing = state.missing_locks
        assert BootstrapLock.BOOT_01 not in missing  # Identity acquired
        assert BootstrapLock.BOOT_02 in missing  # Mode not acquired
        assert BootstrapLock.BOOT_03 in missing  # Lane not acquired
        assert BootstrapLock.BOOT_04 in missing  # Tools not acquired
        assert BootstrapLock.BOOT_05 in missing  # Handshake not acquired


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BOOTSTRAP SEAL
# ═══════════════════════════════════════════════════════════════════════════════


class TestBootstrapSeal:
    """Test bootstrap sealing behavior."""
    
    def test_seal_with_all_locks(self):
        """Can seal when all locks acquired."""
        state = (
            BootstrapState()
            .acquire_identity("GID-01", "Cody")
            .acquire_mode("EXECUTION")
            .acquire_lane("GOVERNANCE")
            .acquire_tools(frozenset(), frozenset())
            .complete_handshake("test")
        )
        
        sealed = state.seal()
        
        assert sealed.is_sealed is True
        assert sealed.status == BootstrapStatus.SEALED
        assert sealed.bootstrap_token is not None
        assert sealed.sealed_at is not None
        assert "boot_" in sealed.bootstrap_token
        assert "GID-01" in sealed.bootstrap_token
    
    def test_cannot_seal_incomplete(self):
        """Cannot seal with missing locks."""
        state = BootstrapState().acquire_identity("GID-01", "Cody")
        
        with pytest.raises(BootstrapIncompleteError) as exc_info:
            state.seal()
        
        assert "missing locks" in str(exc_info.value).lower()
    
    def test_cannot_seal_twice(self):
        """Cannot seal already-sealed session."""
        state = (
            BootstrapState()
            .acquire_identity("GID-01", "Cody")
            .acquire_mode("EXECUTION")
            .acquire_lane("GOVERNANCE")
            .acquire_tools(frozenset(), frozenset())
            .complete_handshake("test")
            .seal()
        )
        
        with pytest.raises(RebootstrapForbiddenError):
            state.seal()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RE-BOOTSTRAP FORBIDDEN
# ═══════════════════════════════════════════════════════════════════════════════


class TestRebootstrapForbidden:
    """Test that re-bootstrap is forbidden."""
    
    def test_cannot_reacquire_identity_after_seal(self):
        """Cannot re-acquire identity in sealed session."""
        state = (
            BootstrapState()
            .acquire_identity("GID-01", "Cody")
            .acquire_mode("EXECUTION")
            .acquire_lane("GOVERNANCE")
            .acquire_tools(frozenset(), frozenset())
            .complete_handshake("test")
            .seal()
        )
        
        with pytest.raises(RebootstrapForbiddenError):
            state.acquire_identity("GID-02", "Other")
    
    def test_cannot_reacquire_mode_after_seal(self):
        """Cannot re-acquire mode in sealed session."""
        state = (
            BootstrapState()
            .acquire_identity("GID-01", "Cody")
            .acquire_mode("EXECUTION")
            .acquire_lane("GOVERNANCE")
            .acquire_tools(frozenset(), frozenset())
            .complete_handshake("test")
            .seal()
        )
        
        with pytest.raises(RebootstrapForbiddenError):
            state.acquire_mode("REVIEW")
    
    def test_terminate_on_rebootstrap(self):
        """Session terminates on re-bootstrap attempt."""
        state = (
            BootstrapState()
            .acquire_identity("GID-01", "Cody")
            .acquire_mode("EXECUTION")
            .acquire_lane("GOVERNANCE")
            .acquire_tools(frozenset(), frozenset())
            .complete_handshake("test")
            .seal()
        )
        
        terminated = state.terminate()
        
        assert terminated.status == BootstrapStatus.TERMINATED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BOOTSTRAP BUILDER
# ═══════════════════════════════════════════════════════════════════════════════


class TestBootstrapBuilder:
    """Test fluent bootstrap builder."""
    
    def test_builder_fluent_api(self):
        """Builder provides fluent API."""
        sealed = (
            BootstrapBuilder()
            .with_identity("GID-01", "Cody")
            .with_mode("EXECUTION")
            .with_lane("GOVERNANCE")
            .with_tools(frozenset(["read_file"]))
            .with_handshake()
            .seal()
        )
        
        assert sealed.is_sealed is True
        assert sealed.gid == "GID-01"
        assert sealed.mode == "EXECUTION"
        assert sealed.lane == "GOVERNANCE"
    
    def test_builder_auto_handshake(self):
        """Builder auto-generates handshake if not specified."""
        sealed = (
            BootstrapBuilder()
            .with_identity("GID-01", "Cody")
            .with_mode("EXECUTION")
            .with_lane("GOVERNANCE")
            .with_tools(frozenset())
            .with_handshake()  # Auto-generated
            .seal()
        )
        
        assert sealed.echo_handshake == "GID-01 | EXECUTION | GOVERNANCE"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestSessionManagement:
    """Test session singleton management."""
    
    def test_no_session_initially(self):
        """No session exists initially."""
        assert get_current_session() is None
    
    def test_set_and_get_session(self):
        """Can set and get session."""
        state = BootstrapState().acquire_identity("GID-01", "Test")
        set_current_session(state)
        
        assert get_current_session() is state
    
    def test_clear_session(self):
        """clear_current_session clears session."""
        set_current_session(BootstrapState())
        clear_current_session()
        
        assert get_current_session() is None
    
    def test_require_sealed_raises_without_session(self):
        """require_sealed_session raises without session."""
        with pytest.raises(BootstrapRequiredError) as exc_info:
            require_sealed_session()
        
        assert "no bootstrap session" in str(exc_info.value).lower()
    
    def test_require_sealed_raises_without_seal(self):
        """require_sealed_session raises if not sealed."""
        state = BootstrapState().acquire_identity("GID-01", "Test")
        set_current_session(state)
        
        with pytest.raises(BootstrapRequiredError) as exc_info:
            require_sealed_session()
        
        assert "not complete" in str(exc_info.value).lower()
    
    def test_require_sealed_returns_sealed_session(self):
        """require_sealed_session returns sealed session."""
        sealed = (
            BootstrapBuilder()
            .with_identity("GID-01", "Cody")
            .with_mode("EXECUTION")
            .with_lane("GOVERNANCE")
            .with_tools(frozenset())
            .with_handshake()
            .seal()
        )
        set_current_session(sealed)
        
        result = require_sealed_session()
        assert result is sealed


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BOOTSTRAP ENFORCER — MISSING BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════════════════


class TestMissingBootstrap:
    """Test: Missing bootstrap → FAIL."""
    
    def test_require_bootstrap_fails_without_session(self, enforcer):
        """require_bootstrap fails without any session."""
        with pytest.raises(BootstrapRequiredError):
            enforcer.require_bootstrap()
    
    def test_is_bootstrapped_false_without_session(self, enforcer):
        """is_bootstrapped returns False without session."""
        assert enforcer.is_bootstrapped() is False
    
    def test_decorator_fails_without_bootstrap(self):
        """@requires_bootstrap decorator fails without bootstrap."""
        @requires_bootstrap
        def protected_function():
            return "success"
        
        with pytest.raises(BootstrapRequiredError):
            protected_function()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BOOTSTRAP ENFORCER — PARTIAL BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════════════════


class TestPartialBootstrap:
    """Test: Partial bootstrap → FAIL."""
    
    def test_partial_bootstrap_not_sealed(self, enforcer):
        """Partial bootstrap does not seal."""
        state = BootstrapState().acquire_identity("GID-01", "Test")
        set_current_session(state)
        
        assert enforcer.is_bootstrapped() is False
    
    def test_require_bootstrap_fails_with_partial(self, enforcer):
        """require_bootstrap fails with partial bootstrap."""
        state = (
            BootstrapState()
            .acquire_identity("GID-01", "Test")
            .acquire_mode("EXECUTION")
            # Missing lane, tools, handshake
        )
        set_current_session(state)
        
        with pytest.raises(BootstrapRequiredError) as exc_info:
            enforcer.require_bootstrap()
        
        assert "missing locks" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BOOTSTRAP ENFORCER — RE-BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════════════════


class TestRebootstrapEnforcer:
    """Test: Re-bootstrap mid-session → FAIL."""
    
    def test_rebootstrap_terminates_session(self, enforcer, buffer):
        """Re-bootstrap attempt terminates session."""
        # First bootstrap
        result1 = enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        assert result1.success is True
        
        # Second bootstrap attempt
        with pytest.raises(RebootstrapForbiddenError):
            enforcer.bootstrap("GID-01", "REVIEW", "GOVERNANCE")
        
        # Session should be terminated
        session = get_current_session()
        assert session.status == BootstrapStatus.TERMINATED
        
        # Output should show blocked
        output = buffer.getvalue()
        assert "RE-BOOTSTRAP FORBIDDEN" in output
        assert "SESSION TERMINATED" in output


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BOOTSTRAP ENFORCER — VALID BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidBootstrap:
    """Test: Valid bootstrap → PASS."""
    
    def test_valid_bootstrap_succeeds(self, enforcer):
        """Valid bootstrap with correct GID/mode/lane succeeds."""
        result = enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        assert result.success is True
        assert result.state.is_sealed is True
        assert result.token is not None
        assert "GID-01" in result.token
    
    def test_valid_bootstrap_sets_session(self, enforcer):
        """Valid bootstrap sets current session."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        session = get_current_session()
        assert session is not None
        assert session.is_sealed is True
    
    def test_is_bootstrapped_true_after_valid(self, enforcer):
        """is_bootstrapped returns True after valid bootstrap."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        assert enforcer.is_bootstrapped() is True
    
    def test_require_bootstrap_succeeds_after_valid(self, enforcer):
        """require_bootstrap succeeds after valid bootstrap."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        state = enforcer.require_bootstrap()
        assert state.is_sealed is True
    
    def test_decorator_succeeds_after_bootstrap(self, enforcer):
        """@requires_bootstrap succeeds after valid bootstrap."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        @requires_bootstrap
        def protected_function():
            return "success"
        
        result = protected_function()
        assert result == "success"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BOOTSTRAP ENFORCER — INVALID INPUTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvalidInputs:
    """Test bootstrap with invalid inputs."""
    
    def test_invalid_gid_fails(self, enforcer, buffer):
        """Invalid GID fails bootstrap."""
        result = enforcer.bootstrap("INVALID-GID", "EXECUTION", "CODE_GENERATION")
        
        assert result.success is False
        assert BootstrapLock.BOOT_01 in result.failed_locks
        
        output = buffer.getvalue()
        assert "BOOT-01" in output
        assert FAIL_SYMBOL in output
    
    def test_invalid_mode_fails(self, enforcer, buffer):
        """Invalid mode for GID fails bootstrap."""
        # GID-01 exists but may not have INVALID_MODE
        result = enforcer.bootstrap("GID-01", "INVALID_MODE", "CODE_GENERATION")
        
        assert result.success is False
        assert BootstrapLock.BOOT_02 in result.failed_locks
    
    def test_invalid_lane_fails(self, enforcer, buffer):
        """Invalid lane for GID fails bootstrap."""
        # Use lane that exists but is not permitted for GID-01
        result = enforcer.bootstrap("GID-01", "EXECUTION", "FRONTEND")
        
        assert result.success is False
        assert BootstrapLock.BOOT_03 in result.failed_locks


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: TERMINAL OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════


class TestTerminalOutput:
    """Test terminal visibility of bootstrap operations."""
    
    def test_bootstrap_start_emitted(self, enforcer, buffer):
        """Bootstrap start emits terminal output."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        output = buffer.getvalue()
        assert "BOOTSTRAP SEQUENCE INITIATED" in output
        assert "🔐" in output
    
    def test_lock_acquisition_emitted(self, enforcer, buffer):
        """Lock acquisitions emit terminal output."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        output = buffer.getvalue()
        assert "BOOT-01" in output
        assert "BOOT-02" in output
        assert "BOOT-03" in output
        assert "BOOT-04" in output
        assert "BOOT-05" in output
        assert PASS_SYMBOL in output
        assert "LOCKED" in output
    
    def test_bootstrap_complete_emitted(self, enforcer, buffer):
        """Bootstrap complete emits terminal output."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        output = buffer.getvalue()
        assert "BOOTSTRAP COMPLETE" in output
        assert "SESSION SEALED" in output
        assert "🟩" in output
        assert "TOKEN:" in output
        assert "READY_FOR_PAC" in output
    
    def test_bootstrap_failed_emitted(self, enforcer, buffer):
        """Bootstrap failure emits terminal output."""
        enforcer.bootstrap("INVALID-GID", "EXECUTION", "CODE_GENERATION")
        
        output = buffer.getvalue()
        assert "BOOTSTRAP FAILED" in output
        assert "🟥" in output
        assert FAIL_SYMBOL in output
    
    def test_pac_blocked_emitted(self, enforcer, buffer):
        """PAC blocked emits terminal output."""
        try:
            enforcer.require_bootstrap()
        except BootstrapRequiredError:
            pass
        
        output = buffer.getvalue()
        assert "PAC EXECUTION BLOCKED" in output
        assert "BOOTSTRAP REQUIRED" in output


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════


class TestContextManager:
    """Test bootstrap_session context manager."""
    
    def test_context_manager_bootstraps(self):
        """Context manager bootstraps on enter."""
        with bootstrap_session("GID-01", "EXECUTION", "GOVERNANCE") as state:
            assert state.is_sealed is True
            assert is_session_bootstrapped() is True
    
    def test_context_manager_clears_on_exit(self):
        """Context manager clears session on exit."""
        with bootstrap_session("GID-01", "EXECUTION", "GOVERNANCE"):
            pass
        
        assert get_current_session() is None
    
    def test_context_manager_raises_on_failure(self):
        """Context manager raises if bootstrap fails."""
        with pytest.raises(BootstrapError):
            with bootstrap_session("INVALID-GID", "EXECUTION", "GOVERNANCE"):
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_bootstrap_function(self):
        """bootstrap() function works."""
        result = bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        assert result.success is True
    
    def test_require_bootstrap_before_pac_function(self):
        """require_bootstrap_before_pac() function works."""
        bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        state = require_bootstrap_before_pac()
        assert state.is_sealed is True
    
    def test_is_session_bootstrapped_function(self):
        """is_session_bootstrapped() function works."""
        assert is_session_bootstrapped() is False
        
        bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        assert is_session_bootstrapped() is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INTEGRATION — FULL BOOTSTRAP FLOW
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegrationFlow:
    """Integration tests for full bootstrap flow."""
    
    def test_full_bootstrap_to_pac_execution(self, enforcer, buffer):
        """Full flow: bootstrap → PAC execution."""
        # 1. Bootstrap
        result = enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        assert result.success is True
        
        # 2. Verify bootstrapped
        assert enforcer.is_bootstrapped() is True
        
        # 3. Execute "PAC" (protected function)
        @requires_bootstrap
        def execute_pac():
            return "PAC executed successfully"
        
        pac_result = execute_pac()
        assert pac_result == "PAC executed successfully"
        
        # 4. Verify output shows full flow
        output = buffer.getvalue()
        assert "BOOTSTRAP SEQUENCE INITIATED" in output
        assert "BOOTSTRAP COMPLETE" in output
    
    def test_bootstrap_fail_blocks_pac(self, enforcer, buffer):
        """Failed bootstrap blocks PAC execution."""
        # 1. Failed bootstrap
        result = enforcer.bootstrap("INVALID-GID", "EXECUTION", "GOVERNANCE")
        assert result.success is False
        
        # 2. PAC execution should fail
        @requires_bootstrap
        def execute_pac():
            return "PAC executed"
        
        with pytest.raises(BootstrapRequiredError):
            execute_pac()
        
        # 3. Output shows failure
        output = buffer.getvalue()
        assert "BOOTSTRAP FAILED" in output
    
    def test_multiple_pacs_after_single_bootstrap(self, enforcer):
        """Multiple PACs can execute after single bootstrap."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        @requires_bootstrap
        def pac_one():
            return "PAC-001"
        
        @requires_bootstrap
        def pac_two():
            return "PAC-002"
        
        assert pac_one() == "PAC-001"
        assert pac_two() == "PAC-002"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: OUTPUT DETERMINISM
# ═══════════════════════════════════════════════════════════════════════════════


class TestOutputDeterminism:
    """Test that output format is deterministic."""
    
    def test_lock_order_is_canonical(self, enforcer, buffer):
        """Locks are always output in BOOT-01 → BOOT-05 order."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        output = buffer.getvalue()
        
        pos_01 = output.find("BOOT-01")
        pos_02 = output.find("BOOT-02")
        pos_03 = output.find("BOOT-03")
        pos_04 = output.find("BOOT-04")
        pos_05 = output.find("BOOT-05")
        
        assert pos_01 < pos_02 < pos_03 < pos_04 < pos_05
    
    def test_all_locks_visible(self, enforcer, buffer):
        """All 5 locks are visible in output."""
        enforcer.bootstrap("GID-01", "EXECUTION", "GOVERNANCE")
        
        output = buffer.getvalue()
        
        assert "BOOT-01" in output
        assert "BOOT-02" in output
        assert "BOOT-03" in output
        assert "BOOT-04" in output
        assert "BOOT-05" in output
        
        assert "Identity Lock" in output
        assert "Mode Lock" in output
        assert "Lane Lock" in output
        assert "Tool Strip" in output
        assert "Echo Handshake" in output
