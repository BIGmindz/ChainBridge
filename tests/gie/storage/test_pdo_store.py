"""
PDO Store Tests

Test suite for proof-addressed PDO storage engine.
Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-PROOF-LAYER-024.

Agent: GID-07 (Dan) — DevOps/Systems Engineer

Tests:
- Immutability (INV-STORE-001)
- Referential integrity (INV-STORE-003)
- Hash collision safety (INV-STORE-004)
- Audit trail (INV-STORE-005)
"""

import hashlib
import json
import pytest
from datetime import datetime

from core.gie.storage.pdo_store import (
    PDOStore,
    PDORecord,
    StorageResult,
    StorageStatus,
    StorageOperation,
    StorageAuditEntry,
    ImmutabilityViolationError,
    DuplicateProofHashError,
    MissingArtifactError,
    HashCollisionError,
    get_pdo_store,
    reset_pdo_store,
)
from core.gie.storage.pdo_index import (
    PDOIndex,
    IndexType,
    get_pdo_index,
    reset_pdo_index,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def store():
    """Fresh PDO store for each test."""
    reset_pdo_store()
    return PDOStore()


@pytest.fixture
def index(store):
    """PDO index linked to store."""
    reset_pdo_index()
    return PDOIndex(store=store)


@pytest.fixture
def sample_artifact():
    """Sample artifact content."""
    return b'{"decision": "APPROVED", "timestamp": "2025-12-26T12:00:00Z"}'


@pytest.fixture
def sample_record(store, sample_artifact):
    """Sample PDO record with valid artifacts."""
    # Store artifact first
    artifact_hash, _ = store.store_artifact(sample_artifact)
    
    return PDORecord(
        pdo_id="PDO-2025-12-26-001",
        proof_hash="sha256:proof123abc",
        pdo_hash="sha256:content456def",
        artifact_hashes=(artifact_hash,),
        agent_gid="GID-01",
        pac_id="PAC-024",
        created_at="2025-12-26T12:00:00Z",
        proof_class="P2",
        proof_provider="SPACE_AND_TIME_P2",
    )


@pytest.fixture(autouse=True)
def cleanup():
    """Reset globals after each test."""
    yield
    reset_pdo_store()
    reset_pdo_index()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: IMMUTABILITY (INV-STORE-001)
# ═══════════════════════════════════════════════════════════════════════════════

class TestImmutability:
    """Tests for INV-STORE-001: Once written, never modified."""

    def test_cannot_store_duplicate_proof_hash(self, store, sample_record):
        """Storing same proof_hash twice fails."""
        result1 = store.store_pdo(sample_record)
        assert result1.success is True
        
        result2 = store.store_pdo(sample_record)
        assert result2.success is False
        assert result2.status == StorageStatus.DUPLICATE

    def test_duplicate_error_message_references_invariant(self, store, sample_record):
        """Duplicate error references INV-STORE-001."""
        store.store_pdo(sample_record)
        result = store.store_pdo(sample_record)
        
        assert "INV-STORE-001" in result.error

    def test_record_is_frozen(self, sample_record):
        """PDORecord is immutable (frozen dataclass)."""
        with pytest.raises((AttributeError, TypeError)):
            sample_record.pdo_id = "MODIFIED"

    def test_artifact_hashes_are_immutable(self, sample_record):
        """artifact_hashes tuple cannot be modified."""
        # Tuple is immutable by nature
        assert isinstance(sample_record.artifact_hashes, tuple)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: REFERENTIAL INTEGRITY (INV-STORE-003)
# ═══════════════════════════════════════════════════════════════════════════════

class TestReferentialIntegrity:
    """Tests for INV-STORE-003: All artifact_hashes must be valid."""

    def test_cannot_store_with_missing_artifact(self, store):
        """Storing record with missing artifact fails."""
        record = PDORecord(
            pdo_id="PDO-MISSING-ARTIFACT",
            proof_hash="sha256:proof999",
            pdo_hash="sha256:content999",
            artifact_hashes=("sha256:nonexistent",),  # Not stored
            agent_gid="GID-01",
            pac_id="PAC-024",
            created_at="2025-12-26T12:00:00Z",
            proof_class="P2",
            proof_provider="SPACE_AND_TIME_P2",
        )
        
        result = store.store_pdo(record)
        
        assert result.success is False
        assert result.status == StorageStatus.INTEGRITY_ERROR
        assert "INV-STORE-003" in result.error

    def test_artifact_exists_check(self, store, sample_artifact):
        """artifact_exists correctly checks storage."""
        artifact_hash, _ = store.store_artifact(sample_artifact)
        
        assert store.artifact_exists(artifact_hash) is True
        assert store.artifact_exists("sha256:nonexistent") is False

    def test_store_artifact_returns_hash(self, store, sample_artifact):
        """store_artifact returns correct SHA-256 hash."""
        expected_hash = f"sha256:{hashlib.sha256(sample_artifact).hexdigest()}"
        artifact_hash, result = store.store_artifact(sample_artifact)
        
        assert artifact_hash == expected_hash
        assert result.success is True

    def test_artifact_retrieval(self, store, sample_artifact):
        """Stored artifact can be retrieved."""
        artifact_hash, _ = store.store_artifact(sample_artifact)
        retrieved = store.get_artifact(artifact_hash)
        
        assert retrieved == sample_artifact


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: HASH COLLISION SAFETY (INV-STORE-004)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashCollisionSafety:
    """Tests for INV-STORE-004: Detect and reject collisions."""

    def test_content_hash_computed_deterministically(self, sample_record):
        """compute_content_hash is deterministic."""
        hash1 = sample_record.compute_content_hash()
        hash2 = sample_record.compute_content_hash()
        
        assert hash1 == hash2
        assert hash1.startswith("sha256:")

    def test_different_records_have_different_content_hash(self, store, sample_artifact):
        """Different records produce different content hashes."""
        artifact_hash, _ = store.store_artifact(sample_artifact)
        
        record1 = PDORecord(
            pdo_id="PDO-001",
            proof_hash="sha256:proof1",
            pdo_hash="sha256:hash1",
            artifact_hashes=(artifact_hash,),
            agent_gid="GID-01",
            pac_id="PAC-024",
            created_at="2025-12-26T12:00:00Z",
            proof_class="P2",
            proof_provider="SPACE_AND_TIME_P2",
        )
        
        record2 = PDORecord(
            pdo_id="PDO-002",  # Different ID
            proof_hash="sha256:proof2",
            pdo_hash="sha256:hash2",
            artifact_hashes=(artifact_hash,),
            agent_gid="GID-02",  # Different agent
            pac_id="PAC-024",
            created_at="2025-12-26T12:00:00Z",
            proof_class="P2",
            proof_provider="SPACE_AND_TIME_P2",
        )
        
        assert record1.compute_content_hash() != record2.compute_content_hash()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PROOF-FIRST ADDRESSING (INV-STORE-002)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProofFirstAddressing:
    """Tests for INV-STORE-002: All lookups via proof_hash."""

    def test_get_by_proof_hash(self, store, sample_record):
        """Primary lookup by proof_hash works."""
        store.store_pdo(sample_record)
        
        retrieved = store.get_by_proof_hash(sample_record.proof_hash)
        
        assert retrieved is not None
        assert retrieved.pdo_id == sample_record.pdo_id

    def test_get_by_unknown_proof_hash(self, store):
        """Unknown proof_hash returns None."""
        retrieved = store.get_by_proof_hash("sha256:unknown")
        assert retrieved is None

    def test_exists_check(self, store, sample_record):
        """exists() checks by proof_hash."""
        assert store.exists(sample_record.proof_hash) is False
        
        store.store_pdo(sample_record)
        
        assert store.exists(sample_record.proof_hash) is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: AUDIT TRAIL (INV-STORE-005)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditTrail:
    """Tests for INV-STORE-005: All operations logged."""

    def test_write_logged(self, store, sample_record):
        """Write operations are logged."""
        store.store_pdo(sample_record)
        
        log = store.get_audit_log()
        write_entries = [e for e in log if e.operation == StorageOperation.WRITE]
        
        assert len(write_entries) >= 1
        assert write_entries[-1].proof_hash == sample_record.proof_hash

    def test_read_logged(self, store, sample_record):
        """Read operations are logged."""
        store.store_pdo(sample_record)
        store.get_by_proof_hash(sample_record.proof_hash)
        
        log = store.get_audit_log()
        read_entries = [e for e in log if e.operation == StorageOperation.READ]
        
        assert len(read_entries) >= 1

    def test_artifact_store_logged(self, store, sample_artifact):
        """Artifact storage is logged."""
        store.store_artifact(sample_artifact, requestor_gid="GID-TEST")
        
        log = store.get_audit_log()
        artifact_entries = [
            e for e in log if e.operation == StorageOperation.ARTIFACT_STORE
        ]
        
        assert len(artifact_entries) >= 1
        assert artifact_entries[0].requestor_gid == "GID-TEST"

    def test_audit_entry_has_timestamp(self, store, sample_record):
        """Audit entries include timestamps."""
        store.store_pdo(sample_record)
        
        log = store.get_audit_log()
        assert log[-1].timestamp is not None
        assert "2025" in log[-1].timestamp or "20" in log[-1].timestamp


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: STORAGE STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStorageStatistics:
    """Tests for storage statistics and counts."""

    def test_count_empty_store(self, store):
        """Empty store has zero count."""
        assert store.count() == 0

    def test_count_after_store(self, store, sample_record):
        """Count increments after storage."""
        store.store_pdo(sample_record)
        assert store.count() == 1

    def test_list_all_proof_hashes(self, store, sample_artifact):
        """List all stored proof hashes."""
        artifact_hash, _ = store.store_artifact(sample_artifact)
        
        record1 = PDORecord(
            pdo_id="PDO-001",
            proof_hash="sha256:proof1",
            pdo_hash="sha256:hash1",
            artifact_hashes=(artifact_hash,),
            agent_gid="GID-01",
            pac_id="PAC-024",
            created_at="2025-12-26T12:00:00Z",
            proof_class="P2",
            proof_provider="TEST",
        )
        
        record2 = PDORecord(
            pdo_id="PDO-002",
            proof_hash="sha256:proof2",
            pdo_hash="sha256:hash2",
            artifact_hashes=(artifact_hash,),
            agent_gid="GID-02",
            pac_id="PAC-024",
            created_at="2025-12-26T12:00:00Z",
            proof_class="P2",
            proof_provider="TEST",
        )
        
        store.store_pdo(record1)
        store.store_pdo(record2)
        
        hashes = store.list_all_proof_hashes()
        
        assert len(hashes) == 2
        assert "sha256:proof1" in hashes
        assert "sha256:proof2" in hashes

    def test_export_statistics(self, store, sample_record):
        """Export statistics returns correct data."""
        store.store_pdo(sample_record)
        
        stats = store.export_statistics()
        
        assert stats["total_records"] == 1
        assert stats["total_artifacts"] >= 1
        assert stats["audit_entries"] >= 1
        assert "exported_at" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDO INDEX
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOIndex:
    """Tests for PDO index functionality."""

    def test_index_record(self, store, index, sample_record):
        """Record can be indexed."""
        store.store_pdo(sample_record)
        index.index_record(sample_record)
        
        # Lookup by proof hash
        result = index.lookup_by_proof_hash(sample_record.proof_hash)
        assert result is not None
        assert result.pdo_id == sample_record.pdo_id

    def test_lookup_by_pdo_hash(self, store, index, sample_record):
        """Lookup by PDO content hash works."""
        store.store_pdo(sample_record)
        index.index_record(sample_record)
        
        results = index.lookup_by_pdo_hash(sample_record.pdo_hash)
        
        assert len(results) == 1
        assert results[0].pdo_id == sample_record.pdo_id

    def test_lookup_by_pdo_id(self, store, index, sample_record):
        """Lookup by human-readable ID works."""
        store.store_pdo(sample_record)
        index.index_record(sample_record)
        
        result = index.lookup_by_pdo_id(sample_record.pdo_id)
        
        assert result is not None
        assert result.proof_hash == sample_record.proof_hash

    def test_lookup_by_agent(self, store, index, sample_artifact):
        """Lookup by agent GID works."""
        artifact_hash, _ = store.store_artifact(sample_artifact)
        
        record1 = PDORecord(
            pdo_id="PDO-A1",
            proof_hash="sha256:proofA1",
            pdo_hash="sha256:hashA1",
            artifact_hashes=(artifact_hash,),
            agent_gid="GID-01",  # Agent 1
            pac_id="PAC-024",
            created_at="2025-12-26T12:00:00Z",
            proof_class="P2",
            proof_provider="TEST",
        )
        
        record2 = PDORecord(
            pdo_id="PDO-A2",
            proof_hash="sha256:proofA2",
            pdo_hash="sha256:hashA2",
            artifact_hashes=(artifact_hash,),
            agent_gid="GID-01",  # Same agent
            pac_id="PAC-024",
            created_at="2025-12-26T12:00:00Z",
            proof_class="P2",
            proof_provider="TEST",
        )
        
        store.store_pdo(record1)
        store.store_pdo(record2)
        index.index_record(record1)
        index.index_record(record2)
        
        results = index.lookup_by_agent("GID-01")
        
        assert len(results) == 2

    def test_lookup_by_pac(self, store, index, sample_record):
        """Lookup by PAC ID works."""
        store.store_pdo(sample_record)
        index.index_record(sample_record)
        
        results = index.lookup_by_pac(sample_record.pac_id)
        
        assert len(results) == 1
        assert results[0].pdo_id == sample_record.pdo_id

    def test_lookup_by_artifact(self, store, index, sample_artifact, sample_record):
        """Lookup by artifact hash works."""
        store.store_pdo(sample_record)
        index.index_record(sample_record)
        
        artifact_hash = sample_record.artifact_hashes[0]
        results = index.lookup_by_artifact(artifact_hash)
        
        assert len(results) == 1
        assert results[0].proof_hash == sample_record.proof_hash

    def test_reindex_all(self, store, index, sample_record):
        """Reindex rebuilds all indices."""
        store.store_pdo(sample_record)
        
        # Index should be empty initially
        assert index.lookup_by_pdo_id(sample_record.pdo_id) is None
        
        # Reindex
        count = index.reindex_all()
        
        assert count == 1
        assert index.lookup_by_pdo_id(sample_record.pdo_id) is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INDEX STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIndexStatistics:
    """Tests for index statistics."""

    def test_get_statistics(self, store, index, sample_record):
        """Statistics reflect index state."""
        store.store_pdo(sample_record)
        index.index_record(sample_record)
        
        stats = index.get_statistics()
        
        assert stats.total_entries == 1
        assert stats.index_counts["PROOF_HASH"] >= 1

    def test_count_by_agent(self, store, index, sample_artifact):
        """Count by agent works."""
        artifact_hash, _ = store.store_artifact(sample_artifact)
        
        for i in range(3):
            record = PDORecord(
                pdo_id=f"PDO-{i}",
                proof_hash=f"sha256:proof{i}",
                pdo_hash=f"sha256:hash{i}",
                artifact_hashes=(artifact_hash,),
                agent_gid="GID-01" if i < 2 else "GID-02",
                pac_id="PAC-024",
                created_at="2025-12-26T12:00:00Z",
                proof_class="P2",
                proof_provider="TEST",
            )
            store.store_pdo(record)
            index.index_record(record)
        
        counts = index.count_by_agent()
        
        assert counts.get("GID-01") == 2
        assert counts.get("GID-02") == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingletonManagement:
    """Tests for singleton store access."""

    def test_get_global_store(self):
        """Global store access works."""
        reset_pdo_store()
        
        store1 = get_pdo_store()
        store2 = get_pdo_store()
        
        assert store1 is store2

    def test_reset_global_store(self):
        """Global store can be reset."""
        store1 = get_pdo_store()
        reset_pdo_store()
        store2 = get_pdo_store()
        
        assert store1 is not store2

    def test_get_global_index(self):
        """Global index access works."""
        reset_pdo_index()
        
        index1 = get_pdo_index()
        index2 = get_pdo_index()
        
        assert index1 is index2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RECORD SERIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecordSerialization:
    """Tests for PDORecord serialization."""

    def test_to_dict(self, sample_record):
        """to_dict produces valid dictionary."""
        d = sample_record.to_dict()
        
        assert d["pdo_id"] == sample_record.pdo_id
        assert d["proof_hash"] == sample_record.proof_hash
        assert isinstance(d["artifact_hashes"], list)

    def test_to_dict_is_json_serializable(self, sample_record):
        """to_dict result can be JSON serialized."""
        d = sample_record.to_dict()
        json_str = json.dumps(d)
        
        assert isinstance(json_str, str)
        assert sample_record.pdo_id in json_str


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: STORAGE RESULT
# ═══════════════════════════════════════════════════════════════════════════════

class TestStorageResult:
    """Tests for StorageResult."""

    def test_success_result(self, store, sample_record):
        """Success result has correct fields."""
        result = store.store_pdo(sample_record)
        
        assert result.success is True
        assert result.status == StorageStatus.SUCCESS
        assert result.pdo_id == sample_record.pdo_id
        assert result.proof_hash == sample_record.proof_hash
        assert result.error is None

    def test_failure_result(self, store):
        """Failure result has error message."""
        record = PDORecord(
            pdo_id="PDO-FAIL",
            proof_hash="sha256:fail",
            pdo_hash="sha256:fail",
            artifact_hashes=("sha256:missing",),
            agent_gid="GID-01",
            pac_id="PAC-024",
            created_at="2025-12-26T12:00:00Z",
            proof_class="P2",
            proof_provider="TEST",
        )
        
        result = store.store_pdo(record)
        
        assert result.success is False
        assert result.error is not None

    def test_result_to_dict(self, store, sample_record):
        """StorageResult can be serialized."""
        result = store.store_pdo(sample_record)
        d = result.to_dict()
        
        assert d["success"] is True
        assert d["status"] == "SUCCESS"
