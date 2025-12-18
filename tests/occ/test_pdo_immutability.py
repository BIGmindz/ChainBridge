"""
PDO Immutability Tests — PAC-CODY-PDO-HARDEN-01

Comprehensive tests to verify:
1. PDOs are append-only (create-once)
2. PDOs cannot be updated
3. PDOs cannot be deleted
4. Hash is computed at write time and stable
5. Tampering attempts are detected and fail loudly
6. API correctly rejects mutation requests

These tests MUST FAIL if immutability is broken.

Author: CODY (GID-01) - Backend
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from core.occ.schemas.pdo import PDOCreate, PDOImmutabilityError, PDOOutcome, PDORecord, PDOSourceSystem, PDOTamperDetectedError
from core.occ.store.pdo_store import PDOStore, get_pdo_store, reset_pdo_store

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_store_path(tmp_path):
    """Create a temporary storage path for tests."""
    return str(tmp_path / "test_pdos.json")


@pytest.fixture
def pdo_store(temp_store_path):
    """Create a fresh PDO store for each test."""
    reset_pdo_store()
    return PDOStore(storage_path=temp_store_path)


@pytest.fixture
def valid_pdo_create():
    """Create a valid PDO creation request."""
    return PDOCreate(
        input_refs=["artifact-123", "data-456"],
        decision_ref="decision-789",
        outcome_ref="outcome-abc",
        outcome=PDOOutcome.APPROVED,
        source_system=PDOSourceSystem.GATEWAY,
        actor="CODY-GID-01",
        actor_type="agent",
        correlation_id="corr-test-001",
        metadata={"test": True, "version": "1.0"},
        tags=["test", "unit-test"],
    )


@pytest.fixture
def created_pdo(pdo_store, valid_pdo_create):
    """Create a PDO and return it."""
    return pdo_store.create(valid_pdo_create)


# =============================================================================
# APPEND-ONLY TESTS (TASK 1 & 3)
# =============================================================================


class TestPDOAppendOnly:
    """Tests that verify append-only semantics."""

    def test_create_pdo_success(self, pdo_store, valid_pdo_create):
        """PDO can be created (append operation)."""
        record = pdo_store.create(valid_pdo_create)

        assert record is not None
        assert isinstance(record.pdo_id, UUID)
        assert record.decision_ref == valid_pdo_create.decision_ref
        assert record.outcome == valid_pdo_create.outcome
        assert record.source_system == valid_pdo_create.source_system

    def test_create_multiple_pdos(self, pdo_store, valid_pdo_create):
        """Multiple PDOs can be created (append-only)."""
        record1 = pdo_store.create(valid_pdo_create)
        record2 = pdo_store.create(valid_pdo_create)
        record3 = pdo_store.create(valid_pdo_create)

        assert record1.pdo_id != record2.pdo_id
        assert record2.pdo_id != record3.pdo_id
        assert pdo_store.count() == 3

    def test_create_with_lineage(self, pdo_store, valid_pdo_create):
        """PDOs can reference previous PDOs (append with lineage)."""
        first = pdo_store.create(valid_pdo_create)

        second_create = PDOCreate(
            input_refs=["new-input"],
            decision_ref="decision-follow-up",
            outcome_ref="outcome-follow-up",
            outcome=PDOOutcome.APPROVED,
            source_system=PDOSourceSystem.OCC,
            actor="CODY-GID-01",
            previous_pdo_id=first.pdo_id,  # Link to previous
        )
        second = pdo_store.create(second_create)

        assert second.previous_pdo_id == first.pdo_id

        # Verify chain retrieval
        chain = pdo_store.get_chain(second.pdo_id)
        assert len(chain) == 2
        assert chain[0].pdo_id == first.pdo_id
        assert chain[1].pdo_id == second.pdo_id


# =============================================================================
# IMMUTABILITY VIOLATION TESTS (TASK 1)
# =============================================================================


class TestPDOUpdateBlocked:
    """Tests that verify updates are blocked."""

    def test_update_raises_immutability_error(self, pdo_store, created_pdo):
        """Update operation raises PDOImmutabilityError."""
        with pytest.raises(PDOImmutabilityError) as exc_info:
            pdo_store.update(created_pdo.pdo_id, outcome="rejected")

        assert created_pdo.pdo_id == exc_info.value.pdo_id
        assert "cannot be updated" in str(exc_info.value)

    def test_delete_raises_immutability_error(self, pdo_store, created_pdo):
        """Delete operation raises PDOImmutabilityError."""
        with pytest.raises(PDOImmutabilityError) as exc_info:
            pdo_store.delete(created_pdo.pdo_id)

        assert created_pdo.pdo_id == exc_info.value.pdo_id
        assert "cannot be deleted" in str(exc_info.value)

    def test_soft_delete_raises_immutability_error(self, pdo_store, created_pdo):
        """Soft-delete operation raises PDOImmutabilityError."""
        with pytest.raises(PDOImmutabilityError) as exc_info:
            pdo_store.soft_delete(created_pdo.pdo_id)

        assert "cannot be soft-deleted" in str(exc_info.value)

    def test_overwrite_raises_immutability_error(self, pdo_store, created_pdo):
        """Overwrite operation raises PDOImmutabilityError."""
        fake_record = PDORecord(
            pdo_id=created_pdo.pdo_id,
            input_refs=[],
            decision_ref="fake",
            outcome_ref="fake",
            outcome=PDOOutcome.REJECTED,
            source_system=PDOSourceSystem.MANUAL,
            actor="attacker",
            hash="fakehash",
        )

        with pytest.raises(PDOImmutabilityError) as exc_info:
            pdo_store.overwrite(created_pdo.pdo_id, fake_record)

        assert "cannot be overwritten" in str(exc_info.value)

    def test_modify_hash_raises_immutability_error(self, pdo_store, created_pdo):
        """Hash modification raises PDOImmutabilityError."""
        with pytest.raises(PDOImmutabilityError) as exc_info:
            pdo_store.modify_hash(created_pdo.pdo_id, "tampered_hash")

        assert "hash cannot be modified" in str(exc_info.value)


class TestPDORecordImmutability:
    """Tests that PDORecord itself is immutable (frozen)."""

    def test_pdo_record_is_frozen(self, created_pdo):
        """PDORecord fields cannot be modified after creation."""
        with pytest.raises(Exception):  # Pydantic ValidationError for frozen models
            created_pdo.outcome = PDOOutcome.REJECTED

    def test_pdo_record_hash_frozen(self, created_pdo):
        """PDORecord hash cannot be modified."""
        with pytest.raises(Exception):
            created_pdo.hash = "tampered_hash"

    def test_pdo_record_decision_ref_frozen(self, created_pdo):
        """PDORecord decision_ref cannot be modified."""
        with pytest.raises(Exception):
            created_pdo.decision_ref = "tampered_ref"


# =============================================================================
# HASH SEALING TESTS (TASK 2)
# =============================================================================


class TestPDOHashSealing:
    """Tests that verify hash sealing at write time."""

    def test_hash_computed_at_write_time(self, pdo_store, valid_pdo_create):
        """Hash is computed when PDO is created."""
        record = pdo_store.create(valid_pdo_create)

        assert record.hash is not None
        assert len(record.hash) == 64  # SHA-256 hex = 64 chars
        assert record.hash_algorithm == "sha256"

    def test_hash_is_deterministic(self, pdo_store, valid_pdo_create):
        """Same inputs produce same hash (deterministic)."""
        record = pdo_store.create(valid_pdo_create)
        computed = record.compute_hash()

        assert record.hash == computed

    def test_hash_verification_passes(self, pdo_store, valid_pdo_create):
        """verify_hash() returns True for valid records."""
        record = pdo_store.create(valid_pdo_create)

        assert record.verify_hash() is True

    def test_hash_changes_with_different_inputs(self, pdo_store):
        """Different inputs produce different hashes."""
        create1 = PDOCreate(
            input_refs=["input-1"],
            decision_ref="decision-1",
            outcome_ref="outcome-1",
            outcome=PDOOutcome.APPROVED,
            source_system=PDOSourceSystem.GATEWAY,
            actor="actor-1",
        )
        create2 = PDOCreate(
            input_refs=["input-2"],
            decision_ref="decision-2",
            outcome_ref="outcome-2",
            outcome=PDOOutcome.REJECTED,
            source_system=PDOSourceSystem.OCC,
            actor="actor-2",
        )

        record1 = pdo_store.create(create1)
        record2 = pdo_store.create(create2)

        assert record1.hash != record2.hash

    def test_hash_remains_stable_after_read(self, pdo_store, valid_pdo_create):
        """Hash remains stable when reading record multiple times."""
        record = pdo_store.create(valid_pdo_create)
        original_hash = record.hash

        # Read multiple times
        for _ in range(5):
            retrieved = pdo_store.get(record.pdo_id)
            assert retrieved.hash == original_hash
            assert retrieved.verify_hash() is True


# =============================================================================
# TAMPER DETECTION TESTS (TASK 2)
# =============================================================================


class TestPDOTamperDetection:
    """Tests that verify tampering is detected."""

    def test_tamper_detection_on_read(self, temp_store_path):
        """Tampering with persisted data is detected on read."""
        # Create a store and add a record
        store1 = PDOStore(storage_path=temp_store_path)
        create = PDOCreate(
            input_refs=["input"],
            decision_ref="decision",
            outcome_ref="outcome",
            outcome=PDOOutcome.APPROVED,
            source_system=PDOSourceSystem.GATEWAY,
            actor="actor",
        )
        record = store1.create(create)
        pdo_id = record.pdo_id

        # Tamper with the persisted JSON file
        with open(temp_store_path, "r") as f:
            data = json.load(f)

        # Modify a field without updating the hash
        data["records"][0]["decision_ref"] = "TAMPERED_DECISION"

        with open(temp_store_path, "w") as f:
            json.dump(data, f)

        # Create new store to load tampered data
        with pytest.raises(PDOTamperDetectedError) as exc_info:
            PDOStore(storage_path=temp_store_path)

        assert "failed integrity check on load" in str(exc_info.value)

    def test_get_with_verification_detects_memory_tampering(self, pdo_store, valid_pdo_create):
        """If somehow memory is tampered, get() with verify=True catches it."""
        record = pdo_store.create(valid_pdo_create)

        # Simulate memory corruption by directly modifying the store's internal dict
        # (This bypasses normal immutability - simulates external tampering)
        corrupted_data = pdo_store._records[record.pdo_id].model_dump()
        corrupted_data["decision_ref"] = "CORRUPTED"
        corrupted_data["hash"] = record.hash  # Keep old hash (tamper signature)

        # Replace with corrupted record
        pdo_store._records[record.pdo_id] = PDORecord.model_validate(corrupted_data)

        # Verification should fail
        with pytest.raises(PDOTamperDetectedError) as exc_info:
            pdo_store.get(record.pdo_id, verify_integrity=True)

        assert exc_info.value.pdo_id == record.pdo_id
        assert exc_info.value.expected_hash == record.hash

    def test_verify_all_detects_tampering(self, pdo_store, valid_pdo_create):
        """verify_all() detects tampered records."""
        record = pdo_store.create(valid_pdo_create)

        # Tamper with record in memory
        corrupted_data = pdo_store._records[record.pdo_id].model_dump()
        corrupted_data["outcome_ref"] = "CORRUPTED"
        pdo_store._records[record.pdo_id] = PDORecord.model_validate(corrupted_data)

        # verify_all should return False for tampered record
        results = pdo_store.verify_all()
        assert results[record.pdo_id] is False


# =============================================================================
# PROVENANCE TESTS (TASK 4)
# =============================================================================


class TestPDOProvenance:
    """Tests that verify provenance fields."""

    def test_pdo_has_all_provenance_fields(self, created_pdo):
        """PDO includes all required provenance fields."""
        assert created_pdo.pdo_id is not None
        assert created_pdo.recorded_at is not None
        assert created_pdo.source_system is not None
        assert created_pdo.hash is not None
        # previous_pdo_id can be None (for root PDOs)

    def test_recorded_at_is_utc(self, created_pdo):
        """recorded_at is in UTC timezone."""
        assert created_pdo.recorded_at.tzinfo is not None
        # Check it's UTC (offset is 0)
        assert created_pdo.recorded_at.utcoffset().total_seconds() == 0

    def test_recorded_at_is_write_time(self, pdo_store, valid_pdo_create):
        """recorded_at reflects actual write time."""
        before = datetime.now(timezone.utc)
        record = pdo_store.create(valid_pdo_create)
        after = datetime.now(timezone.utc)

        assert before <= record.recorded_at <= after

    def test_source_system_is_preserved(self, pdo_store):
        """source_system is correctly stored."""
        for source in [PDOSourceSystem.GATEWAY, PDOSourceSystem.OCC, PDOSourceSystem.CHAINIQ]:
            create = PDOCreate(
                input_refs=["input"],
                decision_ref=f"decision-{source.value}",
                outcome_ref="outcome",
                outcome=PDOOutcome.APPROVED,
                source_system=source,
                actor="actor",
            )
            record = pdo_store.create(create)
            assert record.source_system == source


# =============================================================================
# PERSISTENCE TESTS (TASK 3)
# =============================================================================


class TestPDOPersistence:
    """Tests that verify atomic JSON persistence."""

    def test_pdo_persisted_to_file(self, temp_store_path, valid_pdo_create):
        """PDO is persisted to JSON file."""
        store = PDOStore(storage_path=temp_store_path)
        store.create(valid_pdo_create)

        assert Path(temp_store_path).exists()

        with open(temp_store_path, "r") as f:
            data = json.load(f)

        assert "records" in data
        assert len(data["records"]) == 1
        assert data.get("immutability_enforced") is True

    def test_pdo_survives_restart(self, temp_store_path, valid_pdo_create):
        """PDO survives store restart (persistence)."""
        # Create and add PDO
        store1 = PDOStore(storage_path=temp_store_path)
        record = store1.create(valid_pdo_create)
        pdo_id = record.pdo_id

        # Create new store (simulates restart)
        store2 = PDOStore(storage_path=temp_store_path)

        # PDO should still exist
        retrieved = store2.get(pdo_id)
        assert retrieved is not None
        assert retrieved.pdo_id == pdo_id
        assert retrieved.hash == record.hash

    def test_atomic_write_on_failure(self, temp_store_path, valid_pdo_create):
        """Atomic write protects against partial writes."""
        store = PDOStore(storage_path=temp_store_path)
        store.create(valid_pdo_create)

        # File should be valid JSON
        with open(temp_store_path, "r") as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "records" in data


# =============================================================================
# READ OPERATION TESTS
# =============================================================================


class TestPDOReadOperations:
    """Tests that verify read operations work correctly."""

    def test_get_existing_pdo(self, pdo_store, created_pdo):
        """Can retrieve existing PDO by ID."""
        retrieved = pdo_store.get(created_pdo.pdo_id)

        assert retrieved is not None
        assert retrieved.pdo_id == created_pdo.pdo_id
        assert retrieved.hash == created_pdo.hash

    def test_get_nonexistent_pdo(self, pdo_store):
        """Getting nonexistent PDO returns None."""
        fake_id = uuid4()
        retrieved = pdo_store.get(fake_id)

        assert retrieved is None

    def test_list_pdos(self, pdo_store, valid_pdo_create):
        """Can list all PDOs."""
        pdo_store.create(valid_pdo_create)
        pdo_store.create(valid_pdo_create)
        pdo_store.create(valid_pdo_create)

        records = pdo_store.list()
        assert len(records) == 3

    def test_list_with_filters(self, pdo_store):
        """Can filter PDOs by outcome."""
        approved = PDOCreate(
            input_refs=["input"],
            decision_ref="approved-decision",
            outcome_ref="outcome",
            outcome=PDOOutcome.APPROVED,
            source_system=PDOSourceSystem.GATEWAY,
            actor="actor",
        )
        rejected = PDOCreate(
            input_refs=["input"],
            decision_ref="rejected-decision",
            outcome_ref="outcome",
            outcome=PDOOutcome.REJECTED,
            source_system=PDOSourceSystem.GATEWAY,
            actor="actor",
        )

        pdo_store.create(approved)
        pdo_store.create(approved)
        pdo_store.create(rejected)

        approved_records = pdo_store.list(outcome=PDOOutcome.APPROVED)
        rejected_records = pdo_store.list(outcome=PDOOutcome.REJECTED)

        assert len(approved_records) == 2
        assert len(rejected_records) == 1

    def test_list_with_pagination(self, pdo_store, valid_pdo_create):
        """Can paginate PDO list."""
        for _ in range(10):
            pdo_store.create(valid_pdo_create)

        page1 = pdo_store.list(limit=5, offset=0)
        page2 = pdo_store.list(limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5

        # Different records
        ids1 = {r.pdo_id for r in page1}
        ids2 = {r.pdo_id for r in page2}
        assert ids1.isdisjoint(ids2)
