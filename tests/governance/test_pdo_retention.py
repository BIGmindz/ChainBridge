"""
Test Suite for PDO Retention Policies.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-07 (Dan) — DATA
Deliverable: ≥40 tests for Tiered PDO Retention + Archival Policies
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from core.governance.pdo_retention import (
    # Constants
    MODULE_VERSION,
    DEFAULT_HOT_RETENTION_DAYS,
    DEFAULT_WARM_RETENTION_DAYS,
    # Enums
    StorageTier,
    RetentionStatus,
    ComplianceFramework,
    PDOType,
    # Exceptions
    RetentionError,
    PolicyNotFoundError,
    InvalidTransitionError,
    HoldViolationError,
    IntegrityError,
    # Data Classes
    RetentionPolicy,
    LegalHold,
    PDORecord,
    TransitionRecord,
    RetentionReport,
    # Core Classes
    TierTransitionValidator,
    RetentionPolicyManager,
    # Factory Functions
    create_retention_manager,
    create_default_policies,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def manager() -> RetentionPolicyManager:
    """Create a fresh retention manager."""
    return create_retention_manager()


@pytest.fixture
def manager_with_policies(manager: RetentionPolicyManager) -> RetentionPolicyManager:
    """Create manager with default policies."""
    create_default_policies(manager)
    return manager


@pytest.fixture
def sample_policy(manager: RetentionPolicyManager) -> RetentionPolicy:
    """Create a sample policy."""
    return manager.create_policy(
        name="Test Policy",
        pdo_types={PDOType.DECISION},
        hot_days=30,
        warm_days=60,
        cold_days=90,
        archive_days=365,
    )


# =============================================================================
# TEST: ENUMS
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_storage_tier_values(self):
        """Test storage tier enum values."""
        assert StorageTier.HOT.value == "HOT"
        assert StorageTier.WARM.value == "WARM"
        assert StorageTier.COLD.value == "COLD"
        assert StorageTier.ARCHIVE.value == "ARCHIVE"
        assert StorageTier.DELETED.value == "DELETED"
    
    def test_retention_status_values(self):
        """Test retention status enum values."""
        assert RetentionStatus.ACTIVE.value == "ACTIVE"
        assert RetentionStatus.TRANSITIONING.value == "TRANSITIONING"
        assert RetentionStatus.HOLD.value == "HOLD"
    
    def test_compliance_framework_values(self):
        """Test compliance framework enum values."""
        assert ComplianceFramework.SOC2.value == "SOC2"
        assert ComplianceFramework.GDPR.value == "GDPR"
        assert ComplianceFramework.HIPAA.value == "HIPAA"
    
    def test_pdo_type_values(self):
        """Test PDO type enum values."""
        assert PDOType.DECISION.value == "DECISION"
        assert PDOType.PROOF.value == "PROOF"
        assert PDOType.OUTCOME.value == "OUTCOME"


# =============================================================================
# TEST: EXCEPTIONS
# =============================================================================

class TestExceptions:
    """Test exception hierarchy."""
    
    def test_retention_error_base(self):
        """Test base exception."""
        err = RetentionError("test")
        assert str(err) == "test"
    
    def test_policy_not_found_error(self):
        """Test policy not found exception."""
        err = PolicyNotFoundError("POL-001")
        assert err.policy_id == "POL-001"
        assert "POL-001" in str(err)
    
    def test_invalid_transition_error(self):
        """Test invalid transition exception."""
        err = InvalidTransitionError(StorageTier.HOT, StorageTier.ARCHIVE)
        assert err.from_tier == StorageTier.HOT
        assert err.to_tier == StorageTier.ARCHIVE
    
    def test_hold_violation_error(self):
        """Test hold violation exception."""
        err = HoldViolationError("PDO-001", "HOLD-001")
        assert err.record_id == "PDO-001"
        assert err.hold_id == "HOLD-001"
    
    def test_integrity_error(self):
        """Test integrity error."""
        err = IntegrityError("PDO-001", "hash mismatch")
        assert err.record_id == "PDO-001"


# =============================================================================
# TEST: RETENTION POLICY
# =============================================================================

class TestRetentionPolicy:
    """Test RetentionPolicy data class."""
    
    def test_policy_creation(self, sample_policy):
        """Test policy creation."""
        assert sample_policy.policy_id.startswith("POL-")
        assert sample_policy.name == "Test Policy"
        assert PDOType.DECISION in sample_policy.pdo_types
    
    def test_total_retention_days(self, sample_policy):
        """Test total retention calculation."""
        expected = 30 + 60 + 90 + 365
        assert sample_policy.total_retention_days == expected
    
    def test_get_tier_for_age_hot(self, sample_policy):
        """Test tier determination for hot age."""
        assert sample_policy.get_tier_for_age(15) == StorageTier.HOT
    
    def test_get_tier_for_age_warm(self, sample_policy):
        """Test tier determination for warm age."""
        assert sample_policy.get_tier_for_age(45) == StorageTier.WARM
    
    def test_get_tier_for_age_cold(self, sample_policy):
        """Test tier determination for cold age."""
        assert sample_policy.get_tier_for_age(120) == StorageTier.COLD
    
    def test_get_tier_for_age_archive(self, sample_policy):
        """Test tier determination for archive age."""
        assert sample_policy.get_tier_for_age(300) == StorageTier.ARCHIVE
    
    def test_get_tier_for_age_deleted(self, sample_policy):
        """Test tier determination for expired age."""
        assert sample_policy.get_tier_for_age(600) == StorageTier.DELETED
    
    def test_policy_to_dict(self, sample_policy):
        """Test policy serialization."""
        data = sample_policy.to_dict()
        assert data["policy_id"] == sample_policy.policy_id
        assert data["hot_days"] == 30


# =============================================================================
# TEST: LEGAL HOLD
# =============================================================================

class TestLegalHold:
    """Test LegalHold data class."""
    
    def test_hold_creation(self):
        """Test hold creation."""
        hold = LegalHold(
            hold_id="HOLD-001",
            name="Test Hold",
            reason="Investigation",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert hold.hold_id == "HOLD-001"
        assert hold.active is True
    
    def test_hold_not_expired(self):
        """Test hold not expired without expiry."""
        hold = LegalHold(
            hold_id="HOLD-001",
            name="Test",
            reason="Test",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert hold.is_expired is False
    
    def test_hold_expired(self):
        """Test hold expiration."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        hold = LegalHold(
            hold_id="HOLD-001",
            name="Test",
            reason="Test",
            created_at=(past - timedelta(days=1)).isoformat(),
            expires_at=past.isoformat(),
        )
        assert hold.is_expired is True


# =============================================================================
# TEST: PDO RECORD
# =============================================================================

class TestPDORecord:
    """Test PDORecord data class."""
    
    def test_record_creation(self):
        """Test record creation."""
        record = PDORecord(
            record_id="PDO-001",
            pdo_type=PDOType.DECISION,
            created_at=datetime.now(timezone.utc).isoformat(),
            policy_id="POL-001",
        )
        assert record.record_id == "PDO-001"
        assert record.current_tier == StorageTier.HOT
    
    def test_record_age_days(self):
        """Test record age calculation."""
        past = datetime.now(timezone.utc) - timedelta(days=10)
        record = PDORecord(
            record_id="PDO-001",
            pdo_type=PDOType.DECISION,
            created_at=past.isoformat(),
            policy_id="POL-001",
        )
        assert record.age_days >= 10
    
    def test_record_not_under_hold(self):
        """Test record not under hold."""
        record = PDORecord(
            record_id="PDO-001",
            pdo_type=PDOType.DECISION,
            created_at=datetime.now(timezone.utc).isoformat(),
            policy_id="POL-001",
        )
        assert record.is_under_hold is False
    
    def test_record_under_hold(self):
        """Test record under hold."""
        record = PDORecord(
            record_id="PDO-001",
            pdo_type=PDOType.DECISION,
            created_at=datetime.now(timezone.utc).isoformat(),
            policy_id="POL-001",
            hold_ids={"HOLD-001"},
        )
        assert record.is_under_hold is True
    
    def test_record_compute_hash(self):
        """Test hash computation."""
        record = PDORecord(
            record_id="PDO-001",
            pdo_type=PDOType.DECISION,
            created_at=datetime.now(timezone.utc).isoformat(),
            policy_id="POL-001",
        )
        hash_val = record.compute_hash("test content")
        assert len(hash_val) == 64
        assert record.content_hash == hash_val
    
    def test_record_verify_hash_success(self):
        """Test successful hash verification."""
        record = PDORecord(
            record_id="PDO-001",
            pdo_type=PDOType.DECISION,
            created_at=datetime.now(timezone.utc).isoformat(),
            policy_id="POL-001",
        )
        record.compute_hash("test content")
        assert record.verify_hash("test content") is True
    
    def test_record_verify_hash_failure(self):
        """Test failed hash verification."""
        record = PDORecord(
            record_id="PDO-001",
            pdo_type=PDOType.DECISION,
            created_at=datetime.now(timezone.utc).isoformat(),
            policy_id="POL-001",
        )
        record.compute_hash("test content")
        assert record.verify_hash("different content") is False


# =============================================================================
# TEST: TIER TRANSITION VALIDATOR
# =============================================================================

class TestTierTransitionValidator:
    """Test TierTransitionValidator class."""
    
    def test_valid_hot_to_warm(self):
        """Test valid HOT to WARM transition."""
        validator = TierTransitionValidator()
        assert validator.is_valid_transition(StorageTier.HOT, StorageTier.WARM)
    
    def test_valid_warm_to_cold(self):
        """Test valid WARM to COLD transition."""
        validator = TierTransitionValidator()
        assert validator.is_valid_transition(StorageTier.WARM, StorageTier.COLD)
    
    def test_valid_archive_to_deleted(self):
        """Test valid ARCHIVE to DELETED transition."""
        validator = TierTransitionValidator()
        assert validator.is_valid_transition(StorageTier.ARCHIVE, StorageTier.DELETED)
    
    def test_invalid_hot_to_archive(self):
        """Test invalid HOT to ARCHIVE transition."""
        validator = TierTransitionValidator()
        assert not validator.is_valid_transition(StorageTier.HOT, StorageTier.ARCHIVE)
    
    def test_invalid_same_tier(self):
        """Test same tier transition is invalid."""
        validator = TierTransitionValidator()
        assert not validator.is_valid_transition(StorageTier.HOT, StorageTier.HOT)
    
    def test_validate_transition_record(self, sample_policy, manager):
        """Test record validation."""
        record = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        validator = TierTransitionValidator()
        
        errors = validator.validate_transition(record, StorageTier.WARM)
        assert len(errors) == 0


# =============================================================================
# TEST: RETENTION POLICY MANAGER - POLICIES
# =============================================================================

class TestRetentionPolicyManagerPolicies:
    """Test policy management."""
    
    def test_create_policy(self, manager):
        """Test policy creation."""
        policy = manager.create_policy(
            name="Test",
            pdo_types={PDOType.DECISION},
        )
        assert policy.policy_id.startswith("POL-")
    
    def test_get_policy(self, manager, sample_policy):
        """Test getting policy."""
        retrieved = manager.get_policy(sample_policy.policy_id)
        assert retrieved == sample_policy
    
    def test_get_policy_not_found(self, manager):
        """Test getting nonexistent policy."""
        with pytest.raises(PolicyNotFoundError):
            manager.get_policy("NONEXISTENT")
    
    def test_get_policy_for_type(self, manager, sample_policy):
        """Test finding policy by type."""
        policy = manager.get_policy_for_type(PDOType.DECISION)
        assert policy == sample_policy
    
    def test_list_policies(self, manager_with_policies):
        """Test listing policies."""
        policies = manager_with_policies.list_policies()
        assert len(policies) == 3  # Default policies


# =============================================================================
# TEST: RETENTION POLICY MANAGER - RECORDS
# =============================================================================

class TestRetentionPolicyManagerRecords:
    """Test record management."""
    
    def test_register_record(self, manager, sample_policy):
        """Test record registration."""
        record = manager.register_record(
            PDOType.DECISION,
            policy_id=sample_policy.policy_id,
        )
        assert record.record_id.startswith("PDO-")
        assert record.policy_id == sample_policy.policy_id
    
    def test_register_record_with_content(self, manager, sample_policy):
        """Test record registration with content."""
        record = manager.register_record(
            PDOType.DECISION,
            content="test content",
            policy_id=sample_policy.policy_id,
        )
        assert record.content_hash is not None
    
    def test_register_record_no_policy(self, manager):
        """Test registration fails without policy."""
        with pytest.raises(RetentionError):
            manager.register_record(PDOType.DECISION)
    
    def test_get_record(self, manager, sample_policy):
        """Test getting record."""
        record = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        retrieved = manager.get_record(record.record_id)
        assert retrieved == record
    
    def test_access_record(self, manager, sample_policy):
        """Test accessing record updates timestamp."""
        record = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        assert record.last_accessed is None
        
        manager.access_record(record.record_id)
        assert record.last_accessed is not None


# =============================================================================
# TEST: RETENTION POLICY MANAGER - TRANSITIONS
# =============================================================================

class TestRetentionPolicyManagerTransitions:
    """Test tier transitions."""
    
    def test_transition_record(self, manager, sample_policy):
        """Test manual transition."""
        record = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        
        transition = manager.transition_record(
            record.record_id,
            StorageTier.WARM,
            reason="Manual transition",
        )
        
        assert transition.from_tier == StorageTier.HOT
        assert transition.to_tier == StorageTier.WARM
        assert record.current_tier == StorageTier.WARM
    
    def test_transition_invalid(self, manager, sample_policy):
        """Test invalid transition raises error."""
        record = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        
        with pytest.raises(InvalidTransitionError):
            manager.transition_record(
                record.record_id,
                StorageTier.ARCHIVE,  # Can't jump HOT -> ARCHIVE
                reason="Invalid",
            )
    
    def test_transition_under_hold(self, manager, sample_policy):
        """Test transition to DELETED blocked by hold."""
        record = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        
        # Move to ARCHIVE first
        manager.transition_record(record.record_id, StorageTier.WARM, "test")
        manager.transition_record(record.record_id, StorageTier.COLD, "test")
        manager.transition_record(record.record_id, StorageTier.ARCHIVE, "test")
        
        # Apply hold
        manager.create_hold("Test Hold", "Testing", {record.record_id})
        
        with pytest.raises(HoldViolationError):
            manager.transition_record(record.record_id, StorageTier.DELETED, "test")


# =============================================================================
# TEST: RETENTION POLICY MANAGER - HOLDS
# =============================================================================

class TestRetentionPolicyManagerHolds:
    """Test legal holds."""
    
    def test_create_hold(self, manager, sample_policy):
        """Test creating hold."""
        record = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        
        hold = manager.create_hold(
            name="Test Hold",
            reason="Investigation",
            record_ids={record.record_id},
        )
        
        assert hold.hold_id.startswith("HOLD-")
        assert record.is_under_hold
        assert record.status == RetentionStatus.HOLD
    
    def test_release_hold(self, manager, sample_policy):
        """Test releasing hold."""
        record = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        hold = manager.create_hold("Test", "Test", {record.record_id})
        
        manager.release_hold(hold.hold_id)
        
        assert not record.is_under_hold
        assert record.status == RetentionStatus.ACTIVE
    
    def test_get_records_under_hold(self, manager, sample_policy):
        """Test getting records under hold."""
        record1 = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        record2 = manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        
        manager.create_hold("Test", "Test", {record1.record_id})
        
        held = manager.get_records_under_hold()
        assert len(held) == 1
        assert held[0].record_id == record1.record_id


# =============================================================================
# TEST: RETENTION POLICY MANAGER - INTEGRITY
# =============================================================================

class TestRetentionPolicyManagerIntegrity:
    """Test integrity verification."""
    
    def test_verify_record_integrity(self, manager, sample_policy):
        """Test integrity verification."""
        record = manager.register_record(
            PDOType.DECISION,
            content="test content",
            policy_id=sample_policy.policy_id,
        )
        
        assert manager.verify_record_integrity(record.record_id, "test content")
        assert not manager.verify_record_integrity(record.record_id, "wrong content")
    
    def test_audit_integrity(self, manager, sample_policy):
        """Test integrity audit."""
        record = manager.register_record(
            PDOType.DECISION,
            content="content",
            policy_id=sample_policy.policy_id,
        )
        
        def content_provider(record_id):
            return "content"
        
        results = manager.audit_integrity(content_provider)
        assert results[record.record_id] is True


# =============================================================================
# TEST: RETENTION POLICY MANAGER - REPORTING
# =============================================================================

class TestRetentionPolicyManagerReporting:
    """Test reporting functionality."""
    
    def test_generate_report(self, manager, sample_policy):
        """Test report generation."""
        manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        
        report = manager.generate_report()
        
        assert report.report_id.startswith("RPT-")
        assert report.total_records == 2
        assert report.records_by_tier[StorageTier.HOT] == 2
    
    def test_report_to_dict(self, manager, sample_policy):
        """Test report serialization."""
        manager.register_record(PDOType.DECISION, policy_id=sample_policy.policy_id)
        report = manager.generate_report()
        
        data = report.to_dict()
        assert "total_records" in data
        assert "records_by_tier" in data


# =============================================================================
# TEST: FACTORY FUNCTIONS
# =============================================================================

class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_retention_manager(self):
        """Test manager creation."""
        manager = create_retention_manager()
        assert isinstance(manager, RetentionPolicyManager)
    
    def test_create_default_policies(self, manager):
        """Test default policy creation."""
        policies = create_default_policies(manager)
        assert len(policies) == 3
        
        # Check governance policy
        gov_policy = next(p for p in policies if "Governance" in p.name)
        assert PDOType.GOVERNANCE in gov_policy.pdo_types


# =============================================================================
# SUMMARY
# =============================================================================

"""
Test Summary:
- TestEnums: 4 tests
- TestExceptions: 5 tests
- TestRetentionPolicy: 8 tests
- TestLegalHold: 3 tests
- TestPDORecord: 7 tests
- TestTierTransitionValidator: 6 tests
- TestRetentionPolicyManagerPolicies: 5 tests
- TestRetentionPolicyManagerRecords: 5 tests
- TestRetentionPolicyManagerTransitions: 3 tests
- TestRetentionPolicyManagerHolds: 3 tests
- TestRetentionPolicyManagerIntegrity: 2 tests
- TestRetentionPolicyManagerReporting: 2 tests
- TestFactoryFunctions: 2 tests

Total: 55 tests (≥40 requirement met)
"""
