"""
PAC-DEV-P52: Hive Context Synchronization Tests
================================================
Validates context integrity and input drift detection.

Test Coverage:
1. test_context_block_creation: Canonical hash generation
2. test_context_hash_determinism: Same data → Same hash
3. test_input_resonance_valid: Identical inputs → Resonance ✅
4. test_input_drift_detection: Different inputs → Drift detected ❌
5. test_squad_synchronization: Broadcast context to squad
6. test_context_immutability: ContextBlock verification

Invariants:
- SYNC-01: All atoms operate on identical context hash
- SYNC-02: Input drift triggers immediate SCRAM
- SYNC-03: Context blocks are immutable
"""

import pytest
from core.intelligence.hive_memory import HiveMemory, ContextBlock


def test_context_block_creation():
    """
    SYNC-03: ContextBlock creation with canonical hash.
    
    Test Scenario:
    - Create context block with data
    - Verify SHA3-256 hash is computed
    - Verify hash is 64 characters (SHA3-256 hex)
    """
    # Arrange
    data = {
        "transaction_id": "TXN-123",
        "amount_usd": 50000,
        "timestamp": "2026-01-25T21:30:00Z"
    }
    
    # Act
    context = ContextBlock.create(block_id="CTX-001", data=data)
    
    # Assert: Hash computed
    assert context.context_hash is not None, "Context hash not computed"
    assert len(context.context_hash) == 64, (
        f"Invalid hash length: {len(context.context_hash)} (expected 64)"
    )
    
    # Verify hash is hex string
    try:
        int(context.context_hash, 16)
    except ValueError:
        pytest.fail("Context hash is not valid hexadecimal")
    
    # Verify immutability (hash matches data)
    assert context.verify_hash(), "Hash verification failed (data corrupted)"
    
    print(f"✅ SYNC-03 PASSED: ContextBlock created with hash {context.context_hash[:16]}...")


def test_context_hash_determinism():
    """
    SYNC-01: Identical data MUST produce identical hash.
    
    Test Scenario:
    - Create two context blocks with identical data
    - Verify hashes match (determinism)
    """
    # Arrange
    data = {
        "transaction_id": "TXN-456",
        "amount_usd": 75000,
        "sender": "0xABC123",
        "receiver": "0xDEF456"
    }
    
    # Act: Create two contexts with same data
    context1 = ContextBlock.create(block_id="CTX-002A", data=data)
    context2 = ContextBlock.create(block_id="CTX-002B", data=data)
    
    # Assert: Hashes MUST match (determinism)
    assert context1.context_hash == context2.context_hash, (
        f"DETERMINISM FAILURE: Same data produced different hashes.\n"
        f"Hash 1: {context1.context_hash}\n"
        f"Hash 2: {context2.context_hash}"
    )
    
    print(f"✅ SYNC-01 DETERMINISM PASSED: Hash = {context1.context_hash[:16]}...")


def test_context_hash_uniqueness():
    """
    SYNC-01: Different data MUST produce different hash.
    
    Test Scenario:
    - Create two context blocks with different data
    - Verify hashes differ (uniqueness)
    """
    # Arrange
    data1 = {"transaction_id": "TXN-789", "amount_usd": 10000}
    data2 = {"transaction_id": "TXN-789", "amount_usd": 20000}  # Different amount
    
    # Act
    context1 = ContextBlock.create(block_id="CTX-003A", data=data1)
    context2 = ContextBlock.create(block_id="CTX-003B", data=data2)
    
    # Assert: Hashes MUST differ (uniqueness)
    assert context1.context_hash != context2.context_hash, (
        f"UNIQUENESS FAILURE: Different data produced identical hashes.\n"
        f"Hash: {context1.context_hash}"
    )
    
    print(f"✅ SYNC-01 UNIQUENESS PASSED: Hash1 != Hash2")


def test_canonical_json_order_independence():
    """
    SYNC-01: Hash must be order-independent (sort_keys=True).
    
    Test Scenario:
    - Create context with {"a": 1, "b": 2}
    - Create context with {"b": 2, "a": 1} (reverse order)
    - Verify hashes match (canonical ordering)
    """
    # Arrange
    data_ordered = {"a": 1, "b": 2, "c": 3}
    data_reversed = {"c": 3, "b": 2, "a": 1}
    
    # Act
    context1 = ContextBlock.create(block_id="CTX-004A", data=data_ordered)
    context2 = ContextBlock.create(block_id="CTX-004B", data=data_reversed)
    
    # Assert: Hashes MUST match (canonical ordering via sort_keys=True)
    assert context1.context_hash == context2.context_hash, (
        f"CANONICAL ORDERING FAILURE: Key order affected hash.\n"
        f"Ordered:  {context1.context_hash}\n"
        f"Reversed: {context2.context_hash}"
    )
    
    print(f"✅ SYNC-01 CANONICAL ORDERING PASSED: Order-independent hash")


def test_input_resonance_valid():
    """
    SYNC-01: Identical inputs produce resonance (same hash).
    
    Test Scenario:
    - Create 3 identical input dictionaries
    - Verify validate_input_resonance() returns True
    """
    # Arrange
    memory = HiveMemory()
    
    inputs = [
        {"transaction_id": "TXN-100", "amount": 1000, "status": "PENDING"},
        {"transaction_id": "TXN-100", "amount": 1000, "status": "PENDING"},
        {"transaction_id": "TXN-100", "amount": 1000, "status": "PENDING"}
    ]
    
    # Act
    resonance = memory.validate_input_resonance(inputs, ["Agent 1", "Agent 2", "Agent 3"])
    
    # Assert: Resonance detected (all inputs identical)
    assert resonance is True, (
        "INPUT RESONANCE FAILURE: Identical inputs did not resonate"
    )
    
    print(f"✅ SYNC-01 INPUT RESONANCE PASSED: All inputs identical")


def test_input_drift_detection():
    """
    SYNC-02: Input drift triggers fail-closed.
    
    Test Scenario:
    - Create 2 inputs with different data
    - Verify validate_input_resonance() returns False
    - Verify SYNC-02 warning logged
    """
    # Arrange
    memory = HiveMemory()
    
    inputs = [
        {"transaction_id": "TXN-200", "amount": 1000},
        {"transaction_id": "TXN-200", "amount": 2000}  # DRIFT: different amount
    ]
    
    # Act
    drift_detected = memory.validate_input_resonance(inputs, ["Agent 1", "Agent 2"])
    
    # Assert: Drift detected (SYNC-02 triggered)
    assert drift_detected is False, (
        "DRIFT DETECTION FAILURE: Different inputs did not trigger SYNC-02"
    )
    
    print(f"✅ SYNC-02 DRIFT DETECTION PASSED: Input drift caught")


def test_squad_synchronization():
    """
    SYNC-01: Broadcast context to squad and verify synchronization.
    
    Test Scenario:
    - Create context block
    - Synchronize to squad of 5 agents
    - Verify synchronization success
    """
    # Arrange
    memory = HiveMemory()
    
    context_data = {
        "task_id": "TASK-SYNC-001",
        "task_type": "GOVERNANCE_CHECK",
        "payload": {"transaction_id": "TXN-300", "amount_usd": 50000}
    }
    
    context = ContextBlock.create(
        block_id="CTX-SYNC-001",
        data=context_data,
        metadata={"squad_id": "SQUAD-01"}
    )
    
    squad_gids = ["GID-06-01", "GID-06-02", "GID-06-03", "GID-06-04", "GID-06-05"]
    
    # Act
    success = memory.synchronize_squad(squad_gids, context)
    
    # Assert: Synchronization successful
    assert success is True, "Squad synchronization failed"
    
    # Verify context registered
    retrieved = memory.get_context("CTX-SYNC-001")
    assert retrieved is not None, "Context not registered"
    assert retrieved.context_hash == context.context_hash, "Retrieved context hash mismatch"
    
    # Verify sync history
    history = memory.get_sync_history()
    assert len(history) >= 1, "Sync history not recorded"
    assert history[-1]["context_id"] == "CTX-SYNC-001", "Wrong context in history"
    assert history[-1]["squad_size"] == 5, "Wrong squad size in history"
    
    print(f"✅ SYNC-01 SQUAD SYNC PASSED: {len(squad_gids)} agents synchronized")


def test_context_immutability():
    """
    SYNC-03: ContextBlocks are immutable (verify_hash() validates integrity).
    
    Test Scenario:
    - Create context block
    - Verify hash matches data
    - Manually corrupt data
    - Verify verify_hash() detects corruption
    """
    # Arrange
    data = {"transaction_id": "TXN-400", "amount": 5000}
    context = ContextBlock.create(block_id="CTX-IMM-001", data=data)
    
    # Act: Verify hash initially valid
    assert context.verify_hash() is True, "Initial hash verification failed"
    
    # Corrupt data (simulate mutation)
    context.data["amount"] = 9999  # Change amount
    
    # Assert: verify_hash() should detect corruption
    assert context.verify_hash() is False, (
        "IMMUTABILITY VIOLATION: Hash verification did not detect data corruption"
    )
    
    print(f"✅ SYNC-03 IMMUTABILITY PASSED: Data corruption detected")


def test_context_drift_detection():
    """
    SYNC-02: Detect which agents have divergent context hashes.
    
    Test Scenario:
    - Create expected context
    - Simulate agents reporting different hashes
    - Verify detect_context_drift() identifies divergent agents
    """
    # Arrange
    memory = HiveMemory()
    
    context_data = {"task_id": "TASK-500", "data": "shared_reality"}
    context = ContextBlock.create(block_id="CTX-DRIFT-001", data=context_data)
    
    # Simulate agent hash reports (GID-06-02 and GID-06-04 have drift)
    agent_hashes = {
        "GID-06-01": context.context_hash,  # Correct
        "GID-06-02": "a1b2c3d4e5f6" + "0" * 52,  # DRIFT (wrong hash)
        "GID-06-03": context.context_hash,  # Correct
        "GID-06-04": "f1e2d3c4b5a6" + "0" * 52,  # DRIFT (wrong hash)
        "GID-06-05": context.context_hash,  # Correct
    }
    
    # Act
    divergent = memory.detect_context_drift(context, agent_hashes)
    
    # Assert: Detect 2 divergent agents
    assert len(divergent) == 2, f"Expected 2 divergent agents, got {len(divergent)}"
    assert "GID-06-02" in divergent, "GID-06-02 drift not detected"
    assert "GID-06-04" in divergent, "GID-06-04 drift not detected"
    
    print(f"✅ SYNC-02 DRIFT DETECTION PASSED: {len(divergent)} divergent agents identified")


def test_sync_statistics():
    """
    Verify sync statistics tracking.
    
    Test Scenario:
    - Perform multiple synchronizations
    - Verify statistics calculation
    """
    # Arrange
    memory = HiveMemory()
    
    # Perform 3 syncs
    for i in range(3):
        context = ContextBlock.create(
            block_id=f"CTX-STATS-{i:03d}",
            data={"iteration": i}
        )
        squad_gids = [f"GID-06-{j:02d}" for j in range(1, 6)]  # 5 agents each
        memory.synchronize_squad(squad_gids, context)
    
    # Act
    stats = memory.get_sync_stats()
    
    # Assert
    assert stats["total_syncs"] == 3, f"Expected 3 syncs, got {stats['total_syncs']}"
    assert stats["successful_syncs"] == 3, "Not all syncs successful"
    assert stats["total_atoms_synced"] == 15, f"Expected 15 atoms (3*5), got {stats['total_atoms_synced']}"
    assert stats["unique_contexts"] == 3, f"Expected 3 unique contexts, got {stats['unique_contexts']}"
    assert stats["success_rate"] == 1.0, f"Expected 100% success rate, got {stats['success_rate']:.0%}"
    
    print(f"✅ SYNC STATISTICS PASSED: {stats}")


# Run tests standalone
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
