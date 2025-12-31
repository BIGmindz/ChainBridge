"""
Tests for PDO Ledger — Immutable, Append-Only Persistence Layer
════════════════════════════════════════════════════════════════════════════════

Tests that validate:
- INV-LEDGER-001: Entries are immutable after creation
- INV-LEDGER-002: No UPDATE operations permitted
- INV-LEDGER-003: No DELETE operations permitted
- INV-LEDGER-004: Hash chain links all entries
- INV-LEDGER-005: Ordering is cryptographically enforced

PAC Reference: PAC-JEFFREY-CHAINBRIDGE-PDO-CORE-EXEC-005
Effective Date: 2025-12-30
"""

import json
import pytest
import uuid
from datetime import datetime, timezone

from core.governance.pdo_ledger import (
    PDOLedger,
    LedgerEntry,
    LedgerError,
    LedgerMutationForbiddenError,
    LedgerChainBrokenError,
    LedgerOrderingError,
    get_pdo_ledger,
    reset_pdo_ledger,
    compute_entry_hash,
    verify_entry_hash,
    LEDGER_VERSION,
    GENESIS_HASH,
)
from core.governance.pdo_artifact import PDO_AUTHORITY


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset ledger singleton before each test."""
    reset_pdo_ledger()
    yield
    reset_pdo_ledger()


@pytest.fixture
def ledger():
    """Get fresh PDO ledger."""
    return PDOLedger()


@pytest.fixture
def sample_pdo_data():
    """Sample PDO data for testing."""
    pdo_id = f"pdo_{uuid.uuid4().hex[:12]}"
    return {
        "pdo_id": pdo_id,
        "pac_id": "PAC-TEST-001",
        "ber_id": f"ber_{uuid.uuid4().hex[:12]}",
        "wrap_id": f"wrap_{uuid.uuid4().hex[:12]}",
        "outcome_status": "ACCEPTED",
        "issuer": PDO_AUTHORITY,
        "pdo_hash": "a" * 64,
        "proof_hash": "b" * 64,
        "decision_hash": "c" * 64,
        "outcome_hash": "d" * 64,
        "pdo_created_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# APPEND TESTS (CREATE ONLY)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAppend:
    """Tests for append operations."""
    
    def test_append_creates_entry(self, ledger, sample_pdo_data):
        """Append should create a ledger entry."""
        entry = ledger.append(**sample_pdo_data)
        
        assert entry is not None
        assert entry.pdo_id == sample_pdo_data["pdo_id"]
        assert entry.pac_id == sample_pdo_data["pac_id"]
        assert entry.sequence_number == 0
    
    def test_append_generates_entry_id(self, ledger, sample_pdo_data):
        """Append should generate unique entry ID."""
        entry = ledger.append(**sample_pdo_data)
        
        assert entry.entry_id is not None
        assert entry.entry_id.startswith("ledger_")
    
    def test_append_computes_entry_hash(self, ledger, sample_pdo_data):
        """Append should compute entry hash."""
        entry = ledger.append(**sample_pdo_data)
        
        assert entry.entry_hash is not None
        assert len(entry.entry_hash) == 64  # SHA-256
    
    def test_first_entry_links_to_genesis(self, ledger, sample_pdo_data):
        """First entry should link to genesis hash."""
        entry = ledger.append(**sample_pdo_data)
        
        assert entry.previous_entry_hash == GENESIS_HASH
    
    def test_subsequent_entries_link_to_previous(self, ledger, sample_pdo_data):
        """Subsequent entries should link to previous entry hash."""
        entry1 = ledger.append(**sample_pdo_data)
        
        # Create second entry
        sample_pdo_data["pdo_id"] = f"pdo_{uuid.uuid4().hex[:12]}"
        sample_pdo_data["pac_id"] = "PAC-TEST-002"
        entry2 = ledger.append(**sample_pdo_data)
        
        assert entry2.previous_entry_hash == entry1.entry_hash
        assert entry2.sequence_number == 1
    
    def test_append_records_timestamp(self, ledger, sample_pdo_data):
        """Append should record timestamp."""
        entry = ledger.append(**sample_pdo_data)
        
        assert entry.ledger_recorded_at is not None
    
    def test_append_increments_sequence(self, ledger, sample_pdo_data):
        """Sequence numbers should increment."""
        entries = []
        for i in range(5):
            sample_pdo_data["pdo_id"] = f"pdo_{uuid.uuid4().hex[:12]}"
            sample_pdo_data["pac_id"] = f"PAC-TEST-{i:03d}"
            entries.append(ledger.append(**sample_pdo_data))
        
        for i, entry in enumerate(entries):
            assert entry.sequence_number == i


# ═══════════════════════════════════════════════════════════════════════════════
# FORBIDDEN MUTATION TESTS (INV-LEDGER-002, INV-LEDGER-003)
# ═══════════════════════════════════════════════════════════════════════════════

class TestForbiddenMutations:
    """Tests for forbidden UPDATE and DELETE operations."""
    
    def test_update_forbidden(self, ledger, sample_pdo_data):
        """UPDATE operation should be forbidden."""
        entry = ledger.append(**sample_pdo_data)
        
        with pytest.raises(LedgerMutationForbiddenError) as exc_info:
            ledger.update(entry.entry_id, outcome_status="REJECTED")
        
        assert exc_info.value.operation == "UPDATE"
        assert "forbidden" in str(exc_info.value).lower()
    
    def test_delete_forbidden(self, ledger, sample_pdo_data):
        """DELETE operation should be forbidden."""
        entry = ledger.append(**sample_pdo_data)
        
        with pytest.raises(LedgerMutationForbiddenError) as exc_info:
            ledger.delete(entry.entry_id)
        
        assert exc_info.value.operation == "DELETE"
        assert "forbidden" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# IMMUTABILITY TESTS (INV-LEDGER-001)
# ═══════════════════════════════════════════════════════════════════════════════

class TestImmutability:
    """Tests for entry immutability."""
    
    def test_entry_is_frozen(self, ledger, sample_pdo_data):
        """LedgerEntry should be frozen (immutable)."""
        entry = ledger.append(**sample_pdo_data)
        
        # Attempting to modify should raise
        with pytest.raises(Exception):  # FrozenInstanceError
            entry.outcome_status = "REJECTED"
    
    def test_entry_hash_matches_after_retrieval(self, ledger, sample_pdo_data):
        """Entry hash should match after retrieval."""
        entry = ledger.append(**sample_pdo_data)
        retrieved = ledger.get_by_pdo_id(sample_pdo_data["pdo_id"])
        
        assert retrieved.entry_hash == entry.entry_hash


# ═══════════════════════════════════════════════════════════════════════════════
# HASH CHAIN TESTS (INV-LEDGER-004)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashChain:
    """Tests for hash chain integrity."""
    
    def test_verify_chain_empty_ledger(self, ledger):
        """Empty ledger should pass verification."""
        is_valid, error = ledger.verify_chain()
        
        assert is_valid is True
        assert error is None
    
    def test_verify_chain_single_entry(self, ledger, sample_pdo_data):
        """Single entry ledger should pass verification."""
        ledger.append(**sample_pdo_data)
        
        is_valid, error = ledger.verify_chain()
        
        assert is_valid is True
        assert error is None
    
    def test_verify_chain_multiple_entries(self, ledger, sample_pdo_data):
        """Multiple entry ledger should pass verification."""
        for i in range(10):
            sample_pdo_data["pdo_id"] = f"pdo_{uuid.uuid4().hex[:12]}"
            sample_pdo_data["pac_id"] = f"PAC-TEST-{i:03d}"
            ledger.append(**sample_pdo_data)
        
        is_valid, error = ledger.verify_chain()
        
        assert is_valid is True
        assert error is None
    
    def test_verify_entry_hash(self, ledger, sample_pdo_data):
        """Individual entry hash should be verifiable."""
        entry = ledger.append(**sample_pdo_data)
        
        is_valid = verify_entry_hash(entry)
        
        assert is_valid is True
    
    def test_compute_entry_hash_deterministic(self):
        """Entry hash computation should be deterministic."""
        entry_id = "test_entry"
        sequence = 0
        pdo_id = "pdo_test"
        pac_id = "PAC-TEST"
        pdo_hash = "a" * 64
        previous_hash = GENESIS_HASH
        recorded_at = "2025-12-30T00:00:00+00:00"
        
        hash1 = compute_entry_hash(
            entry_id, sequence, pdo_id, pac_id, pdo_hash, previous_hash, recorded_at
        )
        hash2 = compute_entry_hash(
            entry_id, sequence, pdo_id, pac_id, pdo_hash, previous_hash, recorded_at
        )
        
        assert hash1 == hash2


# ═══════════════════════════════════════════════════════════════════════════════
# ORDERING TESTS (INV-LEDGER-005)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrdering:
    """Tests for cryptographic ordering."""
    
    def test_entries_ordered_by_sequence(self, ledger, sample_pdo_data):
        """Entries should be ordered by sequence."""
        for i in range(5):
            sample_pdo_data["pdo_id"] = f"pdo_{uuid.uuid4().hex[:12]}"
            sample_pdo_data["pac_id"] = f"PAC-TEST-{i:03d}"
            ledger.append(**sample_pdo_data)
        
        entries = ledger.get_all()
        
        for i, entry in enumerate(entries):
            assert entry.sequence_number == i
    
    def test_get_by_sequence(self, ledger, sample_pdo_data):
        """Should retrieve by sequence number."""
        entries = []
        for i in range(5):
            sample_pdo_data["pdo_id"] = f"pdo_{uuid.uuid4().hex[:12]}"
            sample_pdo_data["pac_id"] = f"PAC-TEST-{i:03d}"
            entries.append(ledger.append(**sample_pdo_data))
        
        for i, expected in enumerate(entries):
            retrieved = ledger.get_by_sequence(i)
            assert retrieved.entry_id == expected.entry_id
    
    def test_get_latest(self, ledger, sample_pdo_data):
        """Should retrieve latest entry."""
        last_entry = None
        for i in range(5):
            sample_pdo_data["pdo_id"] = f"pdo_{uuid.uuid4().hex[:12]}"
            sample_pdo_data["pac_id"] = f"PAC-TEST-{i:03d}"
            last_entry = ledger.append(**sample_pdo_data)
        
        latest = ledger.get_latest()
        
        assert latest.entry_id == last_entry.entry_id
        assert latest.sequence_number == 4


# ═══════════════════════════════════════════════════════════════════════════════
# RETRIEVAL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetrieval:
    """Tests for entry retrieval."""
    
    def test_get_by_pdo_id(self, ledger, sample_pdo_data):
        """Should retrieve by PDO ID."""
        entry = ledger.append(**sample_pdo_data)
        
        retrieved = ledger.get_by_pdo_id(sample_pdo_data["pdo_id"])
        
        assert retrieved is not None
        assert retrieved.entry_id == entry.entry_id
    
    def test_get_by_pac_id(self, ledger, sample_pdo_data):
        """Should retrieve by PAC ID."""
        entry = ledger.append(**sample_pdo_data)
        
        retrieved = ledger.get_by_pac_id(sample_pdo_data["pac_id"])
        
        assert retrieved is not None
        assert retrieved.entry_id == entry.entry_id
    
    def test_get_by_nonexistent_id_returns_none(self, ledger):
        """Nonexistent ID should return None."""
        assert ledger.get_by_pdo_id("nonexistent") is None
        assert ledger.get_by_pac_id("nonexistent") is None
        assert ledger.get_by_sequence(999) is None
    
    def test_len(self, ledger, sample_pdo_data):
        """len() should return entry count."""
        assert len(ledger) == 0
        
        for i in range(3):
            sample_pdo_data["pdo_id"] = f"pdo_{uuid.uuid4().hex[:12]}"
            sample_pdo_data["pac_id"] = f"PAC-TEST-{i:03d}"
            ledger.append(**sample_pdo_data)
        
        assert len(ledger) == 3
    
    def test_iteration(self, ledger, sample_pdo_data):
        """Should be iterable."""
        entry_ids = []
        for i in range(3):
            sample_pdo_data["pdo_id"] = f"pdo_{uuid.uuid4().hex[:12]}"
            sample_pdo_data["pac_id"] = f"PAC-TEST-{i:03d}"
            entry = ledger.append(**sample_pdo_data)
            entry_ids.append(entry.entry_id)
        
        iterated_ids = [e.entry_id for e in ledger]
        
        assert iterated_ids == entry_ids


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExport:
    """Tests for ledger export."""
    
    def test_export_json(self, ledger, sample_pdo_data):
        """Should export as JSON."""
        for i in range(3):
            sample_pdo_data["pdo_id"] = f"pdo_{uuid.uuid4().hex[:12]}"
            sample_pdo_data["pac_id"] = f"PAC-TEST-{i:03d}"
            ledger.append(**sample_pdo_data)
        
        json_str = ledger.export_json()
        data = json.loads(json_str)
        
        assert data["ledger_version"] == LEDGER_VERSION
        assert data["entry_count"] == 3
        assert len(data["entries"]) == 3
    
    def test_entry_to_dict(self, ledger, sample_pdo_data):
        """Entry should convert to dict."""
        entry = ledger.append(**sample_pdo_data)
        
        d = entry.to_dict()
        
        assert d["pdo_id"] == sample_pdo_data["pdo_id"]
        assert d["sequence_number"] == 0
        assert "entry_hash" in d
    
    def test_entry_to_json(self, ledger, sample_pdo_data):
        """Entry should convert to JSON."""
        entry = ledger.append(**sample_pdo_data)
        
        json_str = entry.to_json()
        data = json.loads(json_str)
        
        assert data["pdo_id"] == sample_pdo_data["pdo_id"]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    """Tests for singleton ledger access."""
    
    def test_get_pdo_ledger_returns_same_instance(self):
        """get_pdo_ledger should return singleton."""
        ledger1 = get_pdo_ledger()
        ledger2 = get_pdo_ledger()
        
        assert ledger1 is ledger2
    
    def test_reset_pdo_ledger_clears_instance(self):
        """reset_pdo_ledger should create new instance."""
        ledger1 = get_pdo_ledger()
        reset_pdo_ledger()
        ledger2 = get_pdo_ledger()
        
        assert ledger1 is not ledger2
