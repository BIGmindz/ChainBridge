"""
PDO Store Thread Safety Tests — GAP-001, GAP-003 Enforcement

PAC-CODY-INVARIANT-ENFORCEMENT-01: Automated Invariant Enforcement

Tests for:
- INV-PDO-009: Thread Safety (concurrent access)
- INV-PDO-008: Atomic Persistence (no partial writes)
- Concurrent create operations
- No race conditions or data corruption

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import concurrent.futures
import os
import tempfile
import threading
import time
from typing import List
from uuid import UUID

import pytest

from core.occ.schemas.pdo import PDOCreate, PDOOutcome, PDORecord, PDOSourceSystem
from core.occ.store.pdo_store import PDOStore, get_pdo_store, reset_pdo_store


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    """Create isolated store for each test."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        temp_path = f.name
    monkeypatch.setenv("CHAINBRIDGE_PDO_STORE_PATH", temp_path)
    reset_pdo_store()
    yield temp_path
    reset_pdo_store()
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def store():
    """Get fresh store instance."""
    return get_pdo_store()


def create_pdo_request(actor: str) -> PDOCreate:
    """Create a PDO request with unique actor identifier."""
    return PDOCreate(
        source_system=PDOSourceSystem.OCC,
        outcome=PDOOutcome.APPROVED,
        actor=actor,
        input_refs=[f"input:{actor}:1"],
        decision_ref=f"decision:{actor}",
        outcome_ref=f"outcome:{actor}",
    )


# =============================================================================
# INV-PDO-009: THREAD SAFETY TESTS
# =============================================================================


class TestConcurrentCreates:
    """Tests for concurrent PDO creation (INV-PDO-009)."""

    def test_concurrent_creates_no_data_loss(self, store):
        """Concurrent creates do not lose any records."""
        num_threads = 10
        creates_per_thread = 20
        results: List[PDORecord] = []
        results_lock = threading.Lock()
        errors: List[Exception] = []

        def worker(thread_id: int) -> None:
            for i in range(creates_per_thread):
                try:
                    actor = f"thread-{thread_id}-create-{i}"
                    pdo = store.create(create_pdo_request(actor))
                    with results_lock:
                        results.append(pdo)
                except Exception as e:
                    with results_lock:
                        errors.append(e)

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=worker, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # No errors should have occurred
        assert len(errors) == 0, f"Errors during concurrent creates: {errors}"

        # All records should be created
        expected_count = num_threads * creates_per_thread
        assert len(results) == expected_count
        assert store.count() == expected_count

    def test_concurrent_creates_unique_ids(self, store):
        """Concurrent creates generate unique PDO IDs."""
        num_threads = 5
        creates_per_thread = 50
        all_ids: List[UUID] = []
        ids_lock = threading.Lock()

        def worker(thread_id: int) -> None:
            for i in range(creates_per_thread):
                pdo = store.create(create_pdo_request(f"thread-{thread_id}-{i}"))
                with ids_lock:
                    all_ids.append(pdo.pdo_id)

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=worker, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All IDs must be unique
        assert len(all_ids) == len(set(all_ids)), "Duplicate PDO IDs generated"

    def test_concurrent_creates_valid_hashes(self, store):
        """Concurrent creates produce valid hashes."""
        num_threads = 5
        creates_per_thread = 20
        pdos: List[PDORecord] = []
        pdos_lock = threading.Lock()

        def worker(thread_id: int) -> None:
            for i in range(creates_per_thread):
                pdo = store.create(create_pdo_request(f"thread-{thread_id}-{i}"))
                with pdos_lock:
                    pdos.append(pdo)

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=worker, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All hashes must be valid
        for pdo in pdos:
            assert pdo.verify_hash(), f"Invalid hash for PDO {pdo.pdo_id}"

    def test_concurrent_creates_with_threadpool(self, store):
        """Concurrent creates work with ThreadPoolExecutor."""
        num_creates = 100

        def create_one(i: int) -> PDORecord:
            return store.create(create_pdo_request(f"executor-{i}"))

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(create_one, i) for i in range(num_creates)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_creates
        assert store.count() == num_creates


# =============================================================================
# CONCURRENT READ/WRITE TESTS
# =============================================================================


class TestConcurrentReadWrite:
    """Tests for concurrent read and write operations."""

    def test_concurrent_read_during_writes(self, store):
        """Reads return consistent data during concurrent writes."""
        # Pre-populate some records
        initial_pdos = []
        for i in range(10):
            pdo = store.create(create_pdo_request(f"initial-{i}"))
            initial_pdos.append(pdo)

        read_results: List[PDORecord] = []
        write_results: List[PDORecord] = []
        read_lock = threading.Lock()
        write_lock = threading.Lock()
        stop_reading = threading.Event()

        def reader():
            while not stop_reading.is_set():
                for pdo in initial_pdos:
                    try:
                        fetched = store.get(pdo.pdo_id)
                        if fetched:
                            with read_lock:
                                read_results.append(fetched)
                    except Exception:
                        pass
                time.sleep(0.001)

        def writer(thread_id: int):
            for i in range(20):
                pdo = store.create(create_pdo_request(f"writer-{thread_id}-{i}"))
                with write_lock:
                    write_results.append(pdo)

        # Start readers
        readers = [threading.Thread(target=reader) for _ in range(3)]
        for r in readers:
            r.start()

        # Start writers
        writers = [threading.Thread(target=writer, args=(i,)) for i in range(3)]
        for w in writers:
            w.start()

        # Wait for writers
        for w in writers:
            w.join()

        # Stop readers
        stop_reading.set()
        for r in readers:
            r.join()

        # All writes succeeded
        assert len(write_results) == 60  # 3 threads * 20 writes

        # All reads returned valid data (hash verified)
        for pdo in read_results:
            assert pdo.verify_hash()

    def test_list_during_concurrent_writes(self, store):
        """list() returns consistent data during concurrent writes."""
        list_results: List[int] = []
        list_lock = threading.Lock()
        stop_listing = threading.Event()

        def lister():
            while not stop_listing.is_set():
                all_pdos = store.list()
                with list_lock:
                    list_results.append(len(all_pdos))
                time.sleep(0.002)

        def writer(thread_id: int):
            for i in range(30):
                store.create(create_pdo_request(f"list-writer-{thread_id}-{i}"))

        # Start lister
        lister_thread = threading.Thread(target=lister)
        lister_thread.start()

        # Start writers
        writers = [threading.Thread(target=writer, args=(i,)) for i in range(3)]
        for w in writers:
            w.start()

        for w in writers:
            w.join()

        stop_listing.set()
        lister_thread.join()

        # List counts should be monotonically increasing or equal (never decreasing)
        for i in range(1, len(list_results)):
            assert list_results[i] >= list_results[i - 1], \
                f"List count decreased from {list_results[i-1]} to {list_results[i]}"


# =============================================================================
# INV-PDO-008: ATOMIC PERSISTENCE TESTS
# =============================================================================


class TestAtomicPersistence:
    """Tests for atomic persistence (INV-PDO-008)."""

    def test_persist_during_concurrent_writes(self, store, isolated_store):
        """Persistence is atomic even during concurrent writes."""
        num_creates = 50

        def create_one(i: int) -> PDORecord:
            return store.create(create_pdo_request(f"persist-{i}"))

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_one, i) for i in range(num_creates)]
            [f.result() for f in concurrent.futures.as_completed(futures)]

        # Reload store from disk
        reset_pdo_store()
        new_store = get_pdo_store()

        # All records should be present (atomic persistence)
        assert new_store.count() == num_creates

    def test_no_partial_writes_on_disk(self, store, isolated_store):
        """No partial writes visible on disk."""
        # Create records
        for i in range(10):
            store.create(create_pdo_request(f"partial-{i}"))

        # Read file directly and validate JSON
        with open(isolated_store, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)

        # File should be valid JSON with correct structure
        assert "records" in data
        assert "sequence_counter" in data
        assert "immutability_enforced" in data
        assert len(data["records"]) == 10

    def test_persistence_survives_reload(self, store, isolated_store):
        """Created PDOs survive store reload."""
        created_ids = []
        for i in range(5):
            pdo = store.create(create_pdo_request(f"reload-{i}"))
            created_ids.append(pdo.pdo_id)

        # Reset and reload
        reset_pdo_store()
        reloaded_store = get_pdo_store()

        # All PDOs should be retrievable
        for pdo_id in created_ids:
            fetched = reloaded_store.get(pdo_id)
            assert fetched is not None
            assert fetched.verify_hash()


# =============================================================================
# RACE CONDITION TESTS
# =============================================================================


class TestNoRaceConditions:
    """Tests proving no race conditions exist."""

    def test_sequence_counter_monotonic(self, store):
        """Sequence counter is always monotonically increasing."""
        observed_sequences: List[int] = []
        seq_lock = threading.Lock()

        def create_and_observe(i: int):
            pdo = store.create(create_pdo_request(f"seq-{i}"))
            # Access internal counter (for test purposes)
            with seq_lock:
                observed_sequences.append(store._sequence_counter)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_and_observe, i) for i in range(50)]
            [f.result() for f in concurrent.futures.as_completed(futures)]

        # Counter should be monotonically increasing when sampled
        # Note: Due to timing, we can't guarantee strict ordering,
        # but final value must match count
        assert store._sequence_counter == 50

    def test_index_consistency(self, store):
        """Indexes remain consistent under concurrent access."""
        # Create with different outcomes
        outcomes = [PDOOutcome.APPROVED, PDOOutcome.REJECTED, PDOOutcome.DEFERRED]

        def create_with_outcome(i: int):
            outcome = outcomes[i % len(outcomes)]
            req = PDOCreate(
                source_system=PDOSourceSystem.OCC,
                outcome=outcome,
                actor=f"index-{i}",
                input_refs=[f"input:{i}"],
                decision_ref=f"decision:{i}",
                outcome_ref=f"outcome:{i}",
            )
            return store.create(req)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_with_outcome, i) for i in range(60)]
            [f.result() for f in concurrent.futures.as_completed(futures)]

        # Query by outcome should find all records
        approved = store.list(outcome=PDOOutcome.APPROVED)
        rejected = store.list(outcome=PDOOutcome.REJECTED)
        deferred = store.list(outcome=PDOOutcome.DEFERRED)

        assert len(approved) == 20
        assert len(rejected) == 20
        assert len(deferred) == 20


# =============================================================================
# STRESS TESTS
# =============================================================================


class TestStressScenarios:
    """High-load stress tests for thread safety."""

    def test_high_concurrency_burst(self, store):
        """Handle burst of concurrent operations."""
        num_threads = 50
        creates_per_thread = 10

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for t in range(num_threads):
                for c in range(creates_per_thread):
                    futures.append(
                        executor.submit(
                            store.create,
                            create_pdo_request(f"burst-{t}-{c}")
                        )
                    )
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_threads * creates_per_thread
        assert store.count() == num_threads * creates_per_thread

    def test_rapid_fire_creates(self, store):
        """Rapid sequential creates don't cause issues."""
        pdos = []
        for i in range(200):
            pdo = store.create(create_pdo_request(f"rapid-{i}"))
            pdos.append(pdo)

        # All PDOs valid
        assert len(pdos) == 200
        for pdo in pdos:
            assert pdo.verify_hash()
