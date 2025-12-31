"""
Tests for PDO Retention Policy Engine

Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-REAL-WORK-SIX-AGENT-029.
Agent: GID-07 (Dan) — Data / Storage

REAL WORK MODE tests — comprehensive coverage.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch

from core.gie.storage.pdo_retention import (
    # Enums
    RetentionTier,
    RetentionAction,
    PolicyPriority,
    # Exceptions
    RetentionPolicyError,
    PolicyConflictError,
    InvalidPolicyError,
    RetentionViolationError,
    LegalHoldError,
    # Data Classes
    RetentionPolicy,
    PDOMetadata,
    RetentionDecision,
    CompactedPDO,
    Tombstone,
    RetentionStats,
    # Classes
    PolicyMatcher,
    PDORetentionEngine,
    # Default Policies
    DEFAULT_PAC_POLICY,
    DEFAULT_WRAP_POLICY,
    DEFAULT_BER_POLICY,
    DEFAULT_PDO_POLICY,
    # Factory
    get_retention_engine,
    reset_retention_engine,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Fresh engine without default policies."""
    return PDORetentionEngine()


@pytest.fixture
def engine_with_defaults():
    """Engine with default policies registered."""
    eng = PDORetentionEngine()
    eng.register_policy(DEFAULT_PAC_POLICY)
    eng.register_policy(DEFAULT_WRAP_POLICY)
    eng.register_policy(DEFAULT_BER_POLICY)
    eng.register_policy(DEFAULT_PDO_POLICY)
    return eng


@pytest.fixture
def sample_policy():
    """Sample retention policy."""
    return RetentionPolicy(
        policy_id="test-policy",
        name="Test Policy",
        priority=PolicyPriority.NORMAL,
        min_retention_days=30,
        max_retention_days=365,
        hot_days=7,
        warm_days=30,
        cold_days=90,
        compact_after_days=60,
        subject_pattern="TEST*",
    )


@pytest.fixture
def sample_pdo():
    """Sample PDO metadata."""
    return PDOMetadata(
        pdo_id="pdo-001",
        pdo_hash="sha256:abc123",
        created_at=datetime.utcnow() - timedelta(days=45),
        modified_at=datetime.utcnow() - timedelta(days=45),
        subject_type="TEST-PDO",
        size_bytes=1024,
    )


@pytest.fixture
def old_pdo():
    """Old PDO that exceeds retention."""
    return PDOMetadata(
        pdo_id="pdo-old",
        pdo_hash="sha256:old123",
        created_at=datetime.utcnow() - timedelta(days=400),
        modified_at=datetime.utcnow() - timedelta(days=400),
        subject_type="TEST-PDO",
        size_bytes=2048,
    )


@pytest.fixture(autouse=True)
def reset_global():
    """Reset global engine before each test."""
    reset_retention_engine()
    yield
    reset_retention_engine()


# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION POLICY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetentionPolicy:
    """Tests for RetentionPolicy dataclass."""

    def test_create_valid_policy(self):
        """Create valid retention policy."""
        policy = RetentionPolicy(
            policy_id="test",
            name="Test",
            priority=PolicyPriority.NORMAL,
            min_retention_days=30,
            max_retention_days=365,
        )
        assert policy.policy_id == "test"
        assert policy.min_retention_days == 30

    def test_invalid_negative_retention(self):
        """Negative retention days raises error."""
        with pytest.raises(InvalidPolicyError):
            RetentionPolicy(
                policy_id="test",
                name="Test",
                priority=PolicyPriority.NORMAL,
                min_retention_days=-1,
                max_retention_days=365,
            )

    def test_invalid_max_less_than_min(self):
        """Max less than min raises error."""
        with pytest.raises(InvalidPolicyError):
            RetentionPolicy(
                policy_id="test",
                name="Test",
                priority=PolicyPriority.NORMAL,
                min_retention_days=100,
                max_retention_days=50,
            )

    def test_policy_immutability(self):
        """Policy is frozen."""
        policy = RetentionPolicy(
            policy_id="test",
            name="Test",
            priority=PolicyPriority.NORMAL,
            min_retention_days=30,
            max_retention_days=365,
        )
        with pytest.raises(Exception):
            policy.min_retention_days = 60

    def test_no_max_retention(self):
        """Policy with no max retention (forever)."""
        policy = RetentionPolicy(
            policy_id="test",
            name="Test",
            priority=PolicyPriority.NORMAL,
            min_retention_days=30,
            max_retention_days=None,
        )
        assert policy.max_retention_days is None


# ═══════════════════════════════════════════════════════════════════════════════
# PDO METADATA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOMetadata:
    """Tests for PDOMetadata dataclass."""

    def test_create_pdo_metadata(self, sample_pdo):
        """Create PDO metadata."""
        assert sample_pdo.pdo_id == "pdo-001"
        assert sample_pdo.tier == RetentionTier.HOT

    def test_age_days(self, sample_pdo):
        """Calculate age in days."""
        age = sample_pdo.age_days()
        assert age == 45

    def test_days_since_access_no_access(self, sample_pdo):
        """Days since access with no access record."""
        days = sample_pdo.days_since_access()
        assert days == sample_pdo.age_days()

    def test_days_since_access_with_access(self):
        """Days since access with recent access."""
        pdo = PDOMetadata(
            pdo_id="test",
            pdo_hash="sha256:test",
            created_at=datetime.utcnow() - timedelta(days=100),
            modified_at=datetime.utcnow() - timedelta(days=100),
            subject_type="TEST",
            size_bytes=100,
            last_accessed=datetime.utcnow() - timedelta(days=5),
        )
        assert pdo.days_since_access() == 5

    def test_to_dict(self, sample_pdo):
        """Convert to dictionary."""
        d = sample_pdo.to_dict()
        assert d["pdo_id"] == "pdo-001"
        assert d["tier"] == "HOT"
        assert "created_at" in d


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY MATCHER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyMatcher:
    """Tests for PolicyMatcher."""

    def test_wildcard_pattern(self):
        """Wildcard matches everything."""
        assert PolicyMatcher.matches_pattern("ANYTHING", "*") is True

    def test_prefix_pattern(self):
        """Prefix pattern matching."""
        assert PolicyMatcher.matches_pattern("PAC-001", "PAC*") is True
        assert PolicyMatcher.matches_pattern("WRAP-001", "PAC*") is False

    def test_suffix_pattern(self):
        """Suffix pattern matching."""
        assert PolicyMatcher.matches_pattern("test-PDO", "*PDO") is True
        assert PolicyMatcher.matches_pattern("test-WRAP", "*PDO") is False

    def test_exact_pattern(self):
        """Exact pattern matching."""
        assert PolicyMatcher.matches_pattern("PAC-001", "PAC-001") is True
        assert PolicyMatcher.matches_pattern("PAC-002", "PAC-001") is False

    def test_metadata_filter_empty(self):
        """Empty filter matches everything."""
        assert PolicyMatcher.matches_metadata({"key": "value"}, {}) is True

    def test_metadata_filter_exact(self):
        """Exact metadata match."""
        assert PolicyMatcher.matches_metadata(
            {"status": "active"},
            {"status": "active"}
        ) is True
        assert PolicyMatcher.matches_metadata(
            {"status": "inactive"},
            {"status": "active"}
        ) is False

    def test_metadata_filter_list(self):
        """List filter (any match)."""
        assert PolicyMatcher.matches_metadata(
            {"type": "A"},
            {"type": ["A", "B", "C"]}
        ) is True
        assert PolicyMatcher.matches_metadata(
            {"type": "D"},
            {"type": ["A", "B", "C"]}
        ) is False


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE INITIALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineInitialization:
    """Tests for engine initialization."""

    def test_empty_initialization(self, engine):
        """Engine starts empty."""
        assert len(engine.list_policies()) == 0

    def test_register_policy(self, engine, sample_policy):
        """Register a policy."""
        engine.register_policy(sample_policy)
        assert len(engine.list_policies()) == 1

    def test_duplicate_policy_error(self, engine, sample_policy):
        """Duplicate policy raises error."""
        engine.register_policy(sample_policy)
        with pytest.raises(PolicyConflictError):
            engine.register_policy(sample_policy)

    def test_unregister_policy(self, engine, sample_policy):
        """Unregister a policy."""
        engine.register_policy(sample_policy)
        result = engine.unregister_policy(sample_policy.policy_id)
        assert result is True
        assert len(engine.list_policies()) == 0

    def test_unregister_nonexistent(self, engine):
        """Unregister nonexistent policy returns False."""
        result = engine.unregister_policy("nonexistent")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# PDO MANAGEMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOManagement:
    """Tests for PDO management."""

    def test_register_pdo(self, engine, sample_pdo):
        """Register a PDO."""
        engine.register_pdo(sample_pdo)
        retrieved = engine.get_pdo(sample_pdo.pdo_id)
        assert retrieved is not None
        assert retrieved.pdo_id == sample_pdo.pdo_id

    def test_get_nonexistent_pdo(self, engine):
        """Get nonexistent PDO returns None."""
        assert engine.get_pdo("nonexistent") is None

    def test_update_access(self, engine, sample_pdo):
        """Update access time."""
        engine.register_pdo(sample_pdo)
        result = engine.update_access(sample_pdo.pdo_id)
        assert result is True
        
        updated = engine.get_pdo(sample_pdo.pdo_id)
        assert updated.last_accessed is not None

    def test_update_access_nonexistent(self, engine):
        """Update access for nonexistent PDO."""
        result = engine.update_access("nonexistent")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# LEGAL HOLD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegalHold:
    """Tests for legal hold functionality."""

    def test_apply_legal_hold(self, engine, sample_pdo):
        """Apply legal hold."""
        engine.register_pdo(sample_pdo)
        result = engine.apply_legal_hold(sample_pdo.pdo_id, "Investigation")
        
        assert result is True
        pdo = engine.get_pdo(sample_pdo.pdo_id)
        assert pdo.legal_hold is True
        assert pdo.legal_hold_reason == "Investigation"

    def test_release_legal_hold(self, engine, sample_pdo):
        """Release legal hold."""
        engine.register_pdo(sample_pdo)
        engine.apply_legal_hold(sample_pdo.pdo_id, "Investigation")
        result = engine.release_legal_hold(sample_pdo.pdo_id)
        
        assert result is True
        pdo = engine.get_pdo(sample_pdo.pdo_id)
        assert pdo.legal_hold is False

    def test_release_no_hold(self, engine, sample_pdo):
        """Release when no hold returns False."""
        engine.register_pdo(sample_pdo)
        result = engine.release_legal_hold(sample_pdo.pdo_id)
        assert result is False

    def test_legal_hold_blocks_delete(self, engine, sample_policy, sample_pdo):
        """Legal hold blocks deletion."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        engine.apply_legal_hold(sample_pdo.pdo_id, "Investigation")
        
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.DELETE,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.DELETED,
        )
        
        with pytest.raises(LegalHoldError):
            engine.execute_decision(decision)


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY EVALUATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyEvaluation:
    """Tests for policy evaluation."""

    def test_no_applicable_policy(self, engine, sample_pdo):
        """No policy results in RETAIN."""
        engine.register_pdo(sample_pdo)
        decision = engine.evaluate(sample_pdo)
        
        assert decision.action == RetentionAction.RETAIN
        assert decision.policy_id == "NONE"

    def test_find_applicable_policy(self, engine, sample_policy, sample_pdo):
        """Find applicable policy by pattern."""
        engine.register_policy(sample_policy)
        
        policy = engine.find_applicable_policy(sample_pdo)
        assert policy is not None
        assert policy.policy_id == sample_policy.policy_id

    def test_policy_priority(self, engine, sample_pdo):
        """Higher priority policy wins."""
        low_priority = RetentionPolicy(
            policy_id="low",
            name="Low",
            priority=PolicyPriority.LOW,
            min_retention_days=30,
            max_retention_days=365,
            subject_pattern="TEST*",
        )
        high_priority = RetentionPolicy(
            policy_id="high",
            name="High",
            priority=PolicyPriority.HIGH,
            min_retention_days=60,
            max_retention_days=730,
            subject_pattern="TEST*",
        )
        
        engine.register_policy(low_priority)
        engine.register_policy(high_priority)
        
        policy = engine.find_applicable_policy(sample_pdo)
        assert policy.policy_id == "high"

    def test_evaluate_legal_hold(self, engine, sample_policy, sample_pdo):
        """Evaluation respects legal hold."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        engine.apply_legal_hold(sample_pdo.pdo_id, "Investigation")
        
        # Get the updated PDO with legal hold applied
        pdo_with_hold = engine.get_pdo(sample_pdo.pdo_id)
        
        decision = engine.evaluate(pdo_with_hold)
        assert decision.action == RetentionAction.RETAIN
        assert "Legal hold" in decision.reason


# ═══════════════════════════════════════════════════════════════════════════════
# TIER TRANSITION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTierTransitions:
    """Tests for tier transitions."""

    def test_hot_tier_new_pdo(self, engine, sample_policy):
        """New PDO stays in HOT tier."""
        pdo = PDOMetadata(
            pdo_id="new",
            pdo_hash="sha256:new",
            created_at=datetime.utcnow() - timedelta(days=5),
            modified_at=datetime.utcnow(),
            subject_type="TEST-PDO",
            size_bytes=100,
        )
        engine.register_policy(sample_policy)
        
        tier = engine._determine_tier(5, sample_policy)
        assert tier == RetentionTier.HOT

    def test_warm_tier_transition(self, engine, sample_policy):
        """PDO transitions to WARM tier."""
        tier = engine._determine_tier(15, sample_policy)  # After hot_days (7)
        assert tier == RetentionTier.WARM

    def test_cold_tier_transition(self, engine, sample_policy):
        """PDO transitions to COLD tier."""
        tier = engine._determine_tier(50, sample_policy)  # After warm_days (30)
        assert tier == RetentionTier.COLD

    def test_frozen_tier_transition(self, engine, sample_policy):
        """PDO transitions to FROZEN tier."""
        tier = engine._determine_tier(150, sample_policy)  # After cold_days (90)
        assert tier == RetentionTier.FROZEN


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION EXECUTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestActionExecution:
    """Tests for action execution."""

    def test_execute_retain(self, engine, sample_policy, sample_pdo):
        """Execute RETAIN action."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.RETAIN,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.HOT,
        )
        
        result = engine.execute_decision(decision)
        assert result is True

    def test_execute_demote(self, engine, sample_policy, sample_pdo):
        """Execute DEMOTE action."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.DEMOTE,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.WARM,
        )
        
        result = engine.execute_decision(decision)
        assert result is True
        
        pdo = engine.get_pdo(sample_pdo.pdo_id)
        assert pdo.tier == RetentionTier.WARM

    def test_execute_compact(self, engine, sample_policy, sample_pdo):
        """Execute COMPACT action."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.COMPACT,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.HOT,
        )
        
        result = engine.execute_decision(decision)
        assert result is True
        
        pdo = engine.get_pdo(sample_pdo.pdo_id)
        assert pdo.compacted is True
        assert pdo.size_bytes == 0  # Payload removed

    def test_execute_delete_with_tombstone(self, engine, sample_policy, sample_pdo):
        """Execute DELETE with tombstone creation."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.DELETE,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.DELETED,
            preserves_hash=True,
        )
        
        result = engine.execute_decision(decision)
        assert result is True
        
        # PDO removed
        assert engine.get_pdo(sample_pdo.pdo_id) is None
        
        # Tombstone created
        tombstone = engine.get_tombstone(sample_pdo.pdo_id)
        assert tombstone is not None
        assert tombstone.pdo_hash == sample_pdo.pdo_hash

    def test_execute_purge(self, engine, sample_policy, sample_pdo):
        """Execute PURGE action (complete removal)."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.PURGE,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=None,
        )
        
        result = engine.execute_decision(decision)
        assert result is True
        
        # PDO removed
        assert engine.get_pdo(sample_pdo.pdo_id) is None
        # No tombstone
        assert engine.get_tombstone(sample_pdo.pdo_id) is None


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH OPERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchOperations:
    """Tests for batch operations."""

    def test_evaluate_all(self, engine, sample_policy):
        """Evaluate all PDOs."""
        engine.register_policy(sample_policy)
        
        for i in range(5):
            pdo = PDOMetadata(
                pdo_id=f"pdo-{i:03d}",
                pdo_hash=f"sha256:hash{i}",
                created_at=datetime.utcnow() - timedelta(days=i * 30),
                modified_at=datetime.utcnow(),
                subject_type="TEST-PDO",
                size_bytes=100,
            )
            engine.register_pdo(pdo)
        
        decisions = engine.evaluate_all()
        assert len(decisions) == 5

    def test_execute_all_dry_run(self, engine, sample_policy, sample_pdo):
        """Dry run doesn't modify data."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        # Force a decision that would modify
        old_pdo = PDOMetadata(
            pdo_id="old",
            pdo_hash="sha256:old",
            created_at=datetime.utcnow() - timedelta(days=400),
            modified_at=datetime.utcnow(),
            subject_type="TEST-PDO",
            size_bytes=100,
        )
        engine.register_pdo(old_pdo)
        
        counts = engine.execute_all_pending(dry_run=True)
        
        # PDO still exists
        assert engine.get_pdo("old") is not None


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatistics:
    """Tests for statistics collection."""

    def test_empty_statistics(self, engine):
        """Statistics for empty engine."""
        stats = engine.get_statistics()
        assert stats.total_pdos == 0

    def test_tier_counts(self, engine, sample_policy):
        """Count PDOs by tier."""
        engine.register_policy(sample_policy)
        
        hot_pdo = PDOMetadata(
            pdo_id="hot",
            pdo_hash="sha256:hot",
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
            subject_type="TEST",
            size_bytes=100,
            tier=RetentionTier.HOT,
        )
        warm_pdo = PDOMetadata(
            pdo_id="warm",
            pdo_hash="sha256:warm",
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
            subject_type="TEST",
            size_bytes=100,
            tier=RetentionTier.WARM,
        )
        
        engine.register_pdo(hot_pdo)
        engine.register_pdo(warm_pdo)
        
        stats = engine.get_statistics()
        assert stats.total_pdos == 2
        assert stats.hot_count == 1
        assert stats.warm_count == 1

    def test_legal_hold_count(self, engine, sample_pdo):
        """Count legal holds."""
        engine.register_pdo(sample_pdo)
        engine.apply_legal_hold(sample_pdo.pdo_id, "Test")
        
        stats = engine.get_statistics()
        assert stats.legal_hold_count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TOMBSTONE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTombstones:
    """Tests for tombstone operations."""

    def test_tombstone_creation(self, engine, sample_policy, sample_pdo):
        """Tombstone created on delete."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.DELETE,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.DELETED,
            preserves_hash=True,
        )
        engine.execute_decision(decision)
        
        tombstone = engine.get_tombstone(sample_pdo.pdo_id)
        assert tombstone.pdo_hash == sample_pdo.pdo_hash

    def test_verify_hash_existed_active(self, engine, sample_pdo):
        """Verify hash exists for active PDO."""
        engine.register_pdo(sample_pdo)
        assert engine.verify_hash_existed(sample_pdo.pdo_hash) is True

    def test_verify_hash_existed_tombstone(self, engine, sample_policy, sample_pdo):
        """Verify hash exists in tombstone."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.DELETE,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.DELETED,
            preserves_hash=True,
        )
        engine.execute_decision(decision)
        
        assert engine.verify_hash_existed(sample_pdo.pdo_hash) is True

    def test_verify_hash_not_existed(self, engine):
        """Verify nonexistent hash."""
        assert engine.verify_hash_existed("sha256:nonexistent") is False

    def test_list_tombstones(self, engine, sample_policy, sample_pdo):
        """List all tombstones."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.DELETE,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.DELETED,
            preserves_hash=True,
        )
        engine.execute_decision(decision)
        
        tombstones = engine.list_tombstones()
        assert len(tombstones) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditLog:
    """Tests for audit logging."""

    def test_audit_policy_registration(self, engine, sample_policy):
        """Audit log records policy registration."""
        engine.register_policy(sample_policy)
        
        log = engine.get_audit_log()
        assert len(log) == 1
        assert log[0]["action"] == "POLICY_REGISTERED"

    def test_audit_pdo_operations(self, engine, sample_policy, sample_pdo):
        """Audit log records PDO operations."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        log = engine.get_audit_log()
        pdo_entries = [e for e in log if e["action"] == "PDO_REGISTERED"]
        assert len(pdo_entries) == 1

    def test_audit_log_limit(self, engine, sample_policy):
        """Audit log respects limit."""
        # Generate many entries
        for i in range(200):
            pdo = PDOMetadata(
                pdo_id=f"pdo-{i}",
                pdo_hash=f"sha256:{i}",
                created_at=datetime.utcnow(),
                modified_at=datetime.utcnow(),
                subject_type="TEST",
                size_bytes=100,
            )
            engine.register_pdo(pdo)
        
        log = engine.get_audit_log(limit=50)
        assert len(log) == 50

    def test_clear_audit_log(self, engine, sample_pdo):
        """Clear audit log."""
        engine.register_pdo(sample_pdo)
        count = engine.clear_audit_log()
        assert count == 1
        assert len(engine.get_audit_log()) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT POLICY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDefaultPolicies:
    """Tests for default policies."""

    def test_default_pac_policy(self):
        """Default PAC policy configuration."""
        assert DEFAULT_PAC_POLICY.policy_id == "default-pac"
        assert DEFAULT_PAC_POLICY.min_retention_days == 365
        assert DEFAULT_PAC_POLICY.subject_pattern == "PAC*"

    def test_default_wrap_policy(self):
        """Default WRAP policy configuration."""
        assert DEFAULT_WRAP_POLICY.policy_id == "default-wrap"
        assert DEFAULT_WRAP_POLICY.subject_pattern == "WRAP*"

    def test_default_ber_policy(self):
        """Default BER policy configuration."""
        assert DEFAULT_BER_POLICY.policy_id == "default-ber"
        assert DEFAULT_BER_POLICY.max_retention_days is None  # Never delete
        assert DEFAULT_BER_POLICY.priority == PolicyPriority.HIGH

    def test_default_pdo_policy(self):
        """Default PDO policy configuration."""
        assert DEFAULT_PDO_POLICY.policy_id == "default-pdo"


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactory:
    """Tests for factory functions."""

    def test_get_engine_singleton(self):
        """Factory returns singleton."""
        e1 = get_retention_engine()
        e2 = get_retention_engine()
        assert e1 is e2

    def test_get_engine_with_defaults(self):
        """Factory includes default policies."""
        engine = get_retention_engine(with_defaults=True)
        assert len(engine.list_policies()) == 4

    def test_reset_engine(self):
        """Reset creates new engine."""
        e1 = get_retention_engine()
        reset_retention_engine()
        e2 = get_retention_engine()
        assert e1 is not e2


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSerialization:
    """Tests for data serialization."""

    def test_decision_to_dict(self):
        """RetentionDecision serializes to dict."""
        decision = RetentionDecision(
            pdo_id="test",
            action=RetentionAction.DEMOTE,
            reason="Test",
            policy_id="test-policy",
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.WARM,
        )
        d = decision.to_dict()
        assert d["action"] == "DEMOTE"
        assert d["source_tier"] == "HOT"

    def test_compacted_pdo_to_dict(self):
        """CompactedPDO serializes to dict."""
        compacted = CompactedPDO(
            pdo_id="test",
            pdo_hash="sha256:test",
            original_size=1024,
            created_at=datetime.utcnow(),
            compacted_at=datetime.utcnow(),
            subject_type="TEST",
            summary_metadata={},
        )
        d = compacted.to_dict()
        assert d["pdo_id"] == "test"
        assert d["original_size"] == 1024

    def test_tombstone_to_dict(self):
        """Tombstone serializes to dict."""
        tombstone = Tombstone(
            pdo_id="test",
            pdo_hash="sha256:test",
            deleted_at=datetime.utcnow(),
            reason="Test",
            deleted_by_policy="test-policy",
            original_created_at=datetime.utcnow(),
            original_subject_type="TEST",
        )
        d = tombstone.to_dict()
        assert d["pdo_hash"] == "sha256:test"

    def test_stats_to_dict(self):
        """RetentionStats serializes to dict."""
        stats = RetentionStats(
            total_pdos=100,
            hot_count=50,
            warm_count=30,
            cold_count=15,
            frozen_count=5,
        )
        d = stats.to_dict()
        assert d["total_pdos"] == 100


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""

    def test_execute_on_nonexistent_pdo(self, engine, sample_policy):
        """Execute decision for nonexistent PDO."""
        engine.register_policy(sample_policy)
        
        decision = RetentionDecision(
            pdo_id="nonexistent",
            action=RetentionAction.DELETE,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.DELETED,
        )
        
        result = engine.execute_decision(decision)
        assert result is False

    def test_compact_already_compacted(self, engine, sample_policy, sample_pdo):
        """Compacting already compacted PDO."""
        engine.register_policy(sample_policy)
        engine.register_pdo(sample_pdo)
        
        # First compaction
        decision = RetentionDecision(
            pdo_id=sample_pdo.pdo_id,
            action=RetentionAction.COMPACT,
            reason="Test",
            policy_id=sample_policy.policy_id,
            source_tier=RetentionTier.HOT,
            target_tier=RetentionTier.HOT,
        )
        engine.execute_decision(decision)
        
        # Second compaction should still work (idempotent)
        result = engine.execute_decision(decision)
        assert result is True

    def test_multiple_policies_same_pattern(self, engine):
        """Multiple policies matching same pattern."""
        policy1 = RetentionPolicy(
            policy_id="p1",
            name="P1",
            priority=PolicyPriority.NORMAL,
            min_retention_days=30,
            max_retention_days=365,
            subject_pattern="TEST*",
        )
        policy2 = RetentionPolicy(
            policy_id="p2",
            name="P2",
            priority=PolicyPriority.NORMAL,
            min_retention_days=60,
            max_retention_days=730,
            subject_pattern="TEST*",
        )
        
        engine.register_policy(policy1)
        engine.register_policy(policy2)
        
        pdo = PDOMetadata(
            pdo_id="test",
            pdo_hash="sha256:test",
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
            subject_type="TEST-X",
            size_bytes=100,
        )
        
        # Should pick one (first registered with same priority)
        policy = engine.find_applicable_policy(pdo)
        assert policy is not None
