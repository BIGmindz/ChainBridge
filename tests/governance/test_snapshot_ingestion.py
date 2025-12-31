"""
Test Suite — Repository Snapshot Ingestion (PAC-018)
════════════════════════════════════════════════════════════════════════════════

Tests for REPO_SNAPSHOT_INGESTION_LAW_v1.md compliance.

REQUIRED SCENARIOS:
- Missing snapshot → FAIL
- Hash mismatch → FAIL (drift detected)
- Re-ingestion mid-session → FAIL
- Valid snapshot → PASS + LOCKED
- Bootstrap without snapshot → FAIL

════════════════════════════════════════════════════════════════════════════════
"""

import pytest
from datetime import datetime, timezone

from core.governance.snapshot_state import (
    SnapshotLockStep,
    SnapshotStatus,
    SnapshotMetadata,
    SnapshotLock,
    SnapshotState,
    SnapshotBuilder,
    SnapshotRequiredError,
    SnapshotNotLockedError,
    SnapshotNotReceivedError,
    SnapshotDriftError,
    ReingestionForbiddenError,
    SnapshotAlreadyBoundError,
    get_current_snapshot,
    set_current_snapshot,
    clear_current_snapshot,
    require_locked_snapshot,
    calculate_hash,
    verify_hash,
    STEP_NAMES,
)
from core.governance.snapshot_enforcer import (
    SnapshotTerminalRenderer,
    SnapshotIngestionResult,
    SnapshotEnforcer,
    get_snapshot_enforcer,
    reset_snapshot_enforcer,
    ingest_snapshot,
    require_snapshot_for_bootstrap,
    is_snapshot_ready,
    requires_snapshot,
    snapshot_session,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def clean_snapshot_state():
    """Clear snapshot state before and after each test."""
    reset_snapshot_enforcer()
    yield
    reset_snapshot_enforcer()


@pytest.fixture
def sample_hash():
    """Sample SHA256 hash for testing."""
    return "sha256:abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"


@pytest.fixture
def mismatched_hash():
    """Mismatched hash for drift testing."""
    return "sha256:ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000"


@pytest.fixture
def sample_metadata(sample_hash):
    """Sample snapshot metadata."""
    return SnapshotMetadata.create(
        source="vscode",
        archive_hash=sample_hash,
        file_count=100,
        total_size=1024000,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# STEP NAME TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStepNames:
    """Test step name mappings."""
    
    def test_all_steps_have_names(self):
        """All steps should have names."""
        for step in SnapshotLockStep:
            assert step in STEP_NAMES
            assert len(STEP_NAMES[step]) > 0
    
    def test_step_name_format(self):
        """Step names should be descriptive."""
        assert "Receive" in STEP_NAMES[SnapshotLockStep.SNAP_01]
        assert "Hash" in STEP_NAMES[SnapshotLockStep.SNAP_02]
        assert "Manifest" in STEP_NAMES[SnapshotLockStep.SNAP_03]
        assert "Lock" in STEP_NAMES[SnapshotLockStep.SNAP_04]


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT METADATA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotMetadata:
    """Test SnapshotMetadata frozen dataclass."""
    
    def test_metadata_creation(self, sample_hash):
        """Metadata should be created with all fields."""
        meta = SnapshotMetadata.create(
            source="vscode",
            archive_hash=sample_hash,
            file_count=50,
            total_size=512000,
        )
        
        assert meta.source == "vscode"
        assert meta.archive_hash == sample_hash
        assert meta.file_count == 50
        assert meta.total_size == 512000
    
    def test_metadata_is_frozen(self, sample_metadata):
        """Metadata should be immutable."""
        with pytest.raises(Exception):  # FrozenInstanceError
            sample_metadata.source = "other"
    
    def test_hash_prefix(self, sample_hash):
        """hash_prefix should return first 19 chars."""
        meta = SnapshotMetadata.create(
            source="test",
            archive_hash=sample_hash,
            file_count=1,
            total_size=100,
        )
        
        assert len(meta.hash_prefix) == 22  # "sha256:..." truncated + "..."
        assert meta.hash_prefix.startswith("sha256:")


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT LOCK TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotLock:
    """Test SnapshotLock frozen dataclass."""
    
    def test_lock_creation(self, sample_metadata):
        """Lock should be created from metadata."""
        from datetime import datetime, timezone
        lock = SnapshotLock(
            metadata=sample_metadata,
            locked_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert lock.snapshot_id is not None
        assert lock.metadata == sample_metadata
        assert lock.locked_at is not None
        assert lock.session_token is None
    
    def test_lock_is_frozen(self, sample_metadata):
        """Lock should be immutable."""
        from datetime import datetime, timezone
        lock = SnapshotLock(
            metadata=sample_metadata,
            locked_at=datetime.now(timezone.utc).isoformat(),
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            lock.metadata = None
    
    def test_lock_session_binding(self, sample_metadata):
        """Lock can be bound to session."""
        from datetime import datetime, timezone
        lock = SnapshotLock(
            metadata=sample_metadata,
            locked_at=datetime.now(timezone.utc).isoformat(),
        )
        bound = lock.bind_to_session("session-123")
        
        assert bound.session_token == "session-123"
        assert bound.snapshot_id == lock.snapshot_id


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT STATE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotState:
    """Test SnapshotState frozen dataclass."""
    
    def test_initial_state(self):
        """Initial state should be not ingested."""
        state = SnapshotState()
        
        assert state.status == SnapshotStatus.NOT_INGESTED
        assert state.metadata is None
        assert not state.is_locked
    
    def test_state_transitions(self, sample_hash):
        """State should transition through steps."""
        state = SnapshotState()
        
        # SNAP-01: Receive
        metadata = SnapshotMetadata.create(
            source="vscode",
            archive_hash=sample_hash,
            file_count=10,
            total_size=1000,
        )
        state = state.receive(metadata)
        assert state.received
        assert state.status == SnapshotStatus.RECEIVING
        
        # SNAP-02: Verify hash
        state = state.verify_hash(sample_hash)
        assert state.hash_verified
        assert not state.drift_detected
        
        # SNAP-03: Validate manifest
        state = state.validate_manifest()
        assert state.manifest_validated
        
        # SNAP-04: Lock
        state = state.lock_snapshot()
        assert state.locked
        assert state.is_locked
        assert state.status == SnapshotStatus.LOCKED
    
    def test_drift_detection(self, sample_hash, mismatched_hash):
        """Drift should be detected on hash mismatch."""
        state = SnapshotState()
        metadata = SnapshotMetadata.create(
            source="vscode",
            archive_hash=sample_hash,
            file_count=10,
            total_size=1000,
        )
        state = state.receive(metadata)
        
        # Verify with mismatched hash
        state = state.verify_hash(mismatched_hash)
        
        assert state.drift_detected
        assert state.expected_hash == sample_hash
        assert state.actual_hash == mismatched_hash


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT BUILDER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotBuilder:
    """Test SnapshotBuilder fluent API."""
    
    def test_full_sequence(self, sample_hash):
        """Builder should complete full sequence."""
        builder = SnapshotBuilder()
        
        state = (
            builder
            .receive("vscode", sample_hash, file_count=10)
            .verify_hash(sample_hash)
            .validate_manifest()
            .lock()
        )
        
        assert state.is_locked
        assert state.snapshot_id is not None
        assert state.archive_hash == sample_hash
    
    def test_must_receive_first(self, sample_hash):
        """Must receive before other steps."""
        builder = SnapshotBuilder()
        
        with pytest.raises(SnapshotNotReceivedError):
            builder.verify_hash(sample_hash)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION SINGLETON TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionSingleton:
    """Test session singleton management."""
    
    def test_get_returns_none_initially(self):
        """No snapshot initially."""
        assert get_current_snapshot() is None
    
    def test_set_and_get(self):
        """Can set and get snapshot."""
        state = SnapshotState()
        set_current_snapshot(state)
        
        assert get_current_snapshot() == state
    
    def test_clear(self):
        """Can clear snapshot."""
        state = SnapshotState()
        set_current_snapshot(state)
        clear_current_snapshot()
        
        assert get_current_snapshot() is None
    
    def test_require_locked_raises(self):
        """require_locked raises when not locked."""
        with pytest.raises(SnapshotRequiredError):
            require_locked_snapshot()
    
    def test_require_locked_succeeds(self, sample_hash):
        """require_locked succeeds when locked."""
        builder = SnapshotBuilder()
        state = (
            builder
            .receive("vscode", sample_hash, file_count=10)
            .verify_hash(sample_hash)
            .validate_manifest()
            .lock()
        )
        set_current_snapshot(state)
        
        result = require_locked_snapshot()
        assert result == state


# ═══════════════════════════════════════════════════════════════════════════════
# HASH UTILITIES TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashUtilities:
    """Test hash calculation and verification."""
    
    def test_calculate_hash(self):
        """calculate_hash should produce sha256: prefix."""
        data = b"test data for hashing"
        result = calculate_hash(data)
        
        assert result.startswith("sha256:")
        assert len(result) == 71  # "sha256:" + 64 hex chars
    
    def test_verify_hash_match(self, sample_hash):
        """verify_hash returns True on match."""
        assert verify_hash(sample_hash, sample_hash)
    
    def test_verify_hash_mismatch(self, sample_hash, mismatched_hash):
        """verify_hash returns False on mismatch."""
        assert not verify_hash(sample_hash, mismatched_hash)


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT ENFORCER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotEnforcer:
    """Test SnapshotEnforcer class."""
    
    def test_successful_ingestion(self, sample_hash):
        """Successful ingestion should lock snapshot."""
        enforcer = SnapshotEnforcer()
        result = enforcer.ingest(
            source="vscode",
            archive_hash=sample_hash,
            file_count=50,
        )
        
        assert result.success
        assert result.state.is_locked
        assert result.lock is not None
        assert result.message == "Snapshot ingested and locked successfully"
    
    def test_drift_detection_fails(self, sample_hash, mismatched_hash):
        """Drift detection should fail ingestion."""
        enforcer = SnapshotEnforcer()
        result = enforcer.ingest(
            source="vscode",
            archive_hash=sample_hash,
            actual_hash=mismatched_hash,
            file_count=50,
        )
        
        assert not result.success
        assert result.failed_steps is not None
        assert SnapshotLockStep.SNAP_02 in result.failed_steps
    
    def test_reingestion_blocked(self, sample_hash):
        """Re-ingestion should be blocked."""
        enforcer = SnapshotEnforcer()
        
        # First ingestion succeeds
        result1 = enforcer.ingest(
            source="vscode",
            archive_hash=sample_hash,
            file_count=50,
        )
        assert result1.success
        
        # Second ingestion blocked
        with pytest.raises(ReingestionForbiddenError):
            enforcer.ingest(
                source="vscode",
                archive_hash=sample_hash,
                file_count=50,
            )
    
    def test_require_snapshot_raises(self):
        """require_snapshot raises when not ingested."""
        enforcer = SnapshotEnforcer()
        
        with pytest.raises(SnapshotRequiredError):
            enforcer.require_snapshot()
    
    def test_require_snapshot_succeeds(self, sample_hash):
        """require_snapshot succeeds when locked."""
        enforcer = SnapshotEnforcer()
        result = enforcer.ingest(
            source="vscode",
            archive_hash=sample_hash,
            file_count=50,
        )
        
        snapshot = enforcer.require_snapshot()
        assert snapshot == result.state
    
    def test_is_snapshot_ready(self, sample_hash):
        """is_snapshot_ready reflects state."""
        enforcer = SnapshotEnforcer()
        
        assert not enforcer.is_snapshot_ready()
        
        enforcer.ingest(
            source="vscode",
            archive_hash=sample_hash,
            file_count=50,
        )
        
        assert enforcer.is_snapshot_ready()


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_ingest_snapshot(self, sample_hash):
        """ingest_snapshot convenience function."""
        result = ingest_snapshot(
            source="vscode",
            archive_hash=sample_hash,
            file_count=25,
        )
        
        assert result.success
        assert result.state.is_locked
    
    def test_require_snapshot_for_bootstrap(self, sample_hash):
        """require_snapshot_for_bootstrap convenience function."""
        # Fails without snapshot
        with pytest.raises(SnapshotRequiredError):
            require_snapshot_for_bootstrap()
        
        # Succeeds with snapshot
        ingest_snapshot(
            source="vscode",
            archive_hash=sample_hash,
            file_count=25,
        )
        
        snapshot = require_snapshot_for_bootstrap()
        assert snapshot.is_locked
    
    def test_is_snapshot_ready_function(self, sample_hash):
        """is_snapshot_ready convenience function."""
        assert not is_snapshot_ready()
        
        ingest_snapshot(
            source="vscode",
            archive_hash=sample_hash,
            file_count=25,
        )
        
        assert is_snapshot_ready()


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequiresSnapshotDecorator:
    """Test @requires_snapshot decorator."""
    
    def test_decorator_blocks_without_snapshot(self):
        """Decorator blocks execution without snapshot."""
        @requires_snapshot
        def protected_function():
            return "executed"
        
        with pytest.raises(SnapshotRequiredError):
            protected_function()
    
    def test_decorator_allows_with_snapshot(self, sample_hash):
        """Decorator allows execution with snapshot."""
        @requires_snapshot
        def protected_function():
            return "executed"
        
        ingest_snapshot(
            source="vscode",
            archive_hash=sample_hash,
            file_count=10,
        )
        
        result = protected_function()
        assert result == "executed"


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotSessionContextManager:
    """Test snapshot_session context manager."""
    
    def test_context_manager_ingests(self, sample_hash):
        """Context manager ingests and locks snapshot."""
        with snapshot_session("vscode", sample_hash, file_count=15) as snapshot:
            assert snapshot.is_locked
            assert is_snapshot_ready()
    
    def test_context_manager_clears(self, sample_hash):
        """Context manager clears snapshot on exit."""
        with snapshot_session("vscode", sample_hash, file_count=15):
            pass
        
        assert not is_snapshot_ready()
    
    def test_context_manager_clears_on_exception(self, sample_hash):
        """Context manager clears on exception."""
        try:
            with snapshot_session("vscode", sample_hash, file_count=15):
                raise ValueError("test error")
        except ValueError:
            pass
        
        assert not is_snapshot_ready()


# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBootstrapIntegration:
    """Test snapshot/bootstrap integration."""
    
    def test_bootstrap_requires_snapshot(self):
        """Bootstrap should require snapshot."""
        from core.governance.bootstrap_enforcer import BootstrapEnforcer
        from core.governance.bootstrap_state import clear_current_session
        
        clear_current_session()  # Ensure clean state
        
        enforcer = BootstrapEnforcer()
        
        with pytest.raises(SnapshotRequiredError):
            enforcer.bootstrap(
                gid="GID-01",
                mode="EXECUTION",
                lane="GOVERNANCE",
            )
    
    def test_bootstrap_succeeds_with_snapshot(self, sample_hash):
        """Bootstrap should succeed with snapshot."""
        from core.governance.bootstrap_enforcer import BootstrapEnforcer
        from core.governance.bootstrap_state import clear_current_session
        
        clear_current_session()  # Ensure clean state
        
        # Ingest snapshot first
        ingest_snapshot(
            source="vscode",
            archive_hash=sample_hash,
            file_count=50,
        )
        
        enforcer = BootstrapEnforcer()
        result = enforcer.bootstrap(
            gid="GID-01",
            mode="EXECUTION",
            lane="GOVERNANCE",
        )
        
        assert result.success
    
    def test_bootstrap_skip_snapshot_check(self):
        """Bootstrap can skip snapshot check for testing."""
        from core.governance.bootstrap_enforcer import BootstrapEnforcer
        from core.governance.bootstrap_state import clear_current_session
        
        clear_current_session()  # Ensure clean state
        
        enforcer = BootstrapEnforcer()
        result = enforcer.bootstrap(
            gid="GID-01",
            mode="EXECUTION",
            lane="GOVERNANCE",
            skip_snapshot_check=True,
        )
        
        assert result.success


# ═══════════════════════════════════════════════════════════════════════════════
# TERMINAL OUTPUT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotTerminalRenderer:
    """Test terminal renderer emissions."""
    
    def test_renderer_emits_received(self, sample_metadata):
        """Renderer emits snapshot received."""
        from io import StringIO
        from core.governance.terminal_gates import TerminalGateRenderer
        
        output = StringIO()
        base_renderer = TerminalGateRenderer(output=output)
        renderer = SnapshotTerminalRenderer(renderer=base_renderer)
        renderer.emit_snapshot_received(sample_metadata)
        
        result = output.getvalue()
        assert "SNAPSHOT RECEIVED" in result
        assert sample_metadata.source in result
    
    def test_renderer_emits_locked(self, sample_metadata):
        """Renderer emits snapshot locked."""
        from io import StringIO
        from datetime import datetime, timezone
        from core.governance.terminal_gates import TerminalGateRenderer
        
        lock = SnapshotLock(
            metadata=sample_metadata,
            locked_at=datetime.now(timezone.utc).isoformat(),
        )
        output = StringIO()
        base_renderer = TerminalGateRenderer(output=output)
        renderer = SnapshotTerminalRenderer(renderer=base_renderer)
        renderer.emit_snapshot_locked(lock)
        
        result = output.getvalue()
        assert "SNAPSHOT LOCKED" in result
    
    def test_renderer_emits_drift(self, sample_hash, mismatched_hash):
        """Renderer emits drift detected."""
        from io import StringIO
        from core.governance.terminal_gates import TerminalGateRenderer
        
        output = StringIO()
        base_renderer = TerminalGateRenderer(output=output)
        renderer = SnapshotTerminalRenderer(renderer=base_renderer)
        renderer.emit_snapshot_drift(sample_hash, mismatched_hash)
        
        result = output.getvalue()
        assert "SNAPSHOT DRIFT DETECTED" in result
        assert "SESSION TERMINATED" in result


# ═══════════════════════════════════════════════════════════════════════════════
# STATE IMMUTABILITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateImmutability:
    """Test state immutability guarantees."""
    
    def test_state_is_frozen(self):
        """SnapshotState should be immutable."""
        state = SnapshotState()
        
        with pytest.raises(Exception):  # FrozenInstanceError
            state.status = SnapshotStatus.LOCKED
    
    def test_transitions_return_new_state(self, sample_hash):
        """State transitions should return new instances."""
        state1 = SnapshotState()
        metadata = SnapshotMetadata.create(
            source="vscode",
            archive_hash=sample_hash,
            file_count=10,
            total_size=1000,
        )
        state2 = state1.receive(metadata)
        
        assert state1 is not state2
        assert state1.status == SnapshotStatus.NOT_INGESTED
        assert state2.status == SnapshotStatus.RECEIVING


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    """Test exception behaviors."""
    
    def test_snapshot_required_error(self):
        """SnapshotRequiredError should be raised correctly."""
        with pytest.raises(SnapshotRequiredError) as exc_info:
            raise SnapshotRequiredError("test message")
        
        assert "test message" in str(exc_info.value)
    
    def test_snapshot_drift_error(self, sample_hash, mismatched_hash):
        """SnapshotDriftError should contain hashes."""
        error = SnapshotDriftError(sample_hash, mismatched_hash)
        
        assert sample_hash[:20] in str(error)
        assert mismatched_hash[:20] in str(error)
    
    def test_reingestion_forbidden_error(self):
        """ReingestionForbiddenError should be raised correctly."""
        with pytest.raises(ReingestionForbiddenError) as exc_info:
            raise ReingestionForbiddenError("cannot re-ingest")
        
        assert "cannot re-ingest" in str(exc_info.value)
