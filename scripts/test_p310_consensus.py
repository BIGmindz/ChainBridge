#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              PAC-CON-P310-CONSENSUS-ENGINE TEST SUITE                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Validates: Raft leader election, log replication, crash recovery            ║
║                                                                              ║
║  INV-CON-001 (Safety): Never commit two different values at same index       ║
║  INV-CON-002 (Liveness): Eventually elect a leader if quorum is up           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import asyncio
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.mesh.consensus import (
    ConsensusEngine, RaftState, LogEntry, ClusterSimulator
)


async def test_1_cluster_creation():
    """Test 1: Create a 3-node Raft cluster"""
    print("\n[1/6] Testing cluster creation...")
    
    cluster = ClusterSimulator(["NODE-A", "NODE-B", "NODE-C"])
    
    assert len(cluster.nodes) == 3, "Should have 3 nodes"
    
    for node_id, node in cluster.nodes.items():
        assert node.state == RaftState.FOLLOWER, f"{node_id} should start as FOLLOWER"
        assert node.current_term == 0, f"{node_id} should start at term 0"
        assert node.cluster_size == 3, f"{node_id} cluster size should be 3"
        assert node.quorum_size == 2, f"{node_id} quorum size should be 2"
    
    print(f"      ✓ Created 3 nodes")
    print(f"      ✓ All nodes start as FOLLOWER")
    print(f"      ✓ Quorum size: 2 (majority of 3)")
    return cluster


async def test_2_leader_election():
    """Test 2: Leader election in 3-node cluster"""
    print("\n[2/6] Testing leader election...")
    
    cluster = ClusterSimulator(["NODE-A", "NODE-B", "NODE-C"])
    
    # Run ticks until leader elected
    leader = None
    for i in range(100):
        await cluster.tick_all(1)
        leader = cluster.get_leader()
        if leader:
            break
    
    assert leader, "Should elect a leader"
    leader_node = cluster.nodes[leader]
    
    assert leader_node.state == RaftState.LEADER
    assert leader_node.current_term >= 1, "Term should advance"
    
    # Check other nodes are followers
    followers = [n for n in cluster.nodes.values() if n.state == RaftState.FOLLOWER]
    assert len(followers) == 2, "Should have 2 followers"
    
    print(f"      ✓ Leader elected: {leader}")
    print(f"      ✓ Term: {leader_node.current_term}")
    print(f"      ✓ Followers: {[f.node_id for f in followers]}")
    return cluster, leader


async def test_3_log_replication():
    """Test 3: Log replication across cluster"""
    print("\n[3/6] Testing log replication...")
    
    cluster = ClusterSimulator(["NODE-A", "NODE-B", "NODE-C"])
    
    # Elect leader
    leader = None
    for i in range(100):
        await cluster.tick_all(1)
        leader = cluster.get_leader()
        if leader:
            break
    
    assert leader, "Need a leader"
    leader_node = cluster.nodes[leader]
    
    # Propose commands
    commands = [
        {"action": "SET", "key": "x", "value": 100},
        {"action": "SET", "key": "y", "value": 200},
        {"action": "SET", "key": "z", "value": 300},
    ]
    
    for cmd in commands:
        success, msg = await leader_node.propose_command(cmd)
        assert success, f"Propose should succeed: {msg}"
    
    print(f"      ✓ Proposed {len(commands)} commands")
    
    # Run ticks for replication
    for _ in range(100):
        await cluster.tick_all(1)
    
    # Verify all nodes have the log
    for node_id, node in cluster.nodes.items():
        assert len(node.log) >= len(commands), f"{node_id} should have {len(commands)} entries, has {len(node.log)}"
        
        # Verify entry contents
        for i, cmd in enumerate(commands):
            assert node.log[i].command == cmd, f"{node_id} entry {i} mismatch"
    
    print(f"      ✓ All {len(commands)} entries replicated to all nodes")
    print(f"      ✓ INV-CON-001 ENFORCED: Same values at same indices")
    return cluster


async def test_4_leader_failure():
    """Test 4: Leader failure and re-election"""
    print("\n[4/6] Testing leader failure and re-election...")
    
    cluster = ClusterSimulator(["NODE-A", "NODE-B", "NODE-C"])
    
    # Elect initial leader
    old_leader = None
    for i in range(100):
        await cluster.tick_all(1)
        old_leader = cluster.get_leader()
        if old_leader:
            break
    
    assert old_leader, "Need initial leader"
    old_term = cluster.nodes[old_leader].current_term
    print(f"      ✓ Initial leader: {old_leader} (term {old_term})")
    
    # Partition the leader (simulate crash)
    cluster.partition(old_leader)
    print(f"      ✓ Partitioned leader: {old_leader}")
    
    # Run ticks until new leader elected
    new_leader = None
    for i in range(100):
        await cluster.tick_all(1)
        for node_id, node in cluster.nodes.items():
            if node_id != old_leader and node.is_leader:
                new_leader = node_id
                break
        if new_leader:
            break
    
    assert new_leader, "Should elect new leader"
    assert new_leader != old_leader, "New leader should be different"
    
    new_term = cluster.nodes[new_leader].current_term
    assert new_term > old_term, "New term should be higher"
    
    print(f"      ✓ New leader elected: {new_leader}")
    print(f"      ✓ New term: {new_term} (was {old_term})")
    print(f"      ✓ INV-CON-002 ENFORCED: Liveness maintained after failure")
    return cluster, old_leader, new_leader


async def test_5_leader_rejoins():
    """Test 5: Old leader rejoins cluster"""
    print("\n[5/6] Testing old leader rejoin...")
    
    cluster = ClusterSimulator(["NODE-A", "NODE-B", "NODE-C"])
    
    # Elect initial leader
    old_leader = None
    for i in range(100):
        await cluster.tick_all(1)
        old_leader = cluster.get_leader()
        if old_leader:
            break
    
    # Propose command before partition
    await cluster.nodes[old_leader].propose_command({"pre_partition": True})
    for _ in range(50):
        await cluster.tick_all(1)
    
    # Partition leader
    cluster.partition(old_leader)
    
    # Wait for new leader
    new_leader = None
    for i in range(100):
        await cluster.tick_all(1)
        for node_id, node in cluster.nodes.items():
            if node_id != old_leader and node.is_leader:
                new_leader = node_id
                break
        if new_leader:
            break
    
    # Propose command with new leader
    await cluster.nodes[new_leader].propose_command({"post_partition": True})
    for _ in range(50):
        await cluster.tick_all(1)
    
    new_term = cluster.nodes[new_leader].current_term
    print(f"      ✓ New leader: {new_leader} (term {new_term})")
    
    # Heal partition - old leader rejoins
    cluster.heal(old_leader)
    print(f"      ✓ Old leader rejoined: {old_leader}")
    
    # Run more ticks for convergence (old leader needs to receive heartbeat)
    for _ in range(200):
        await cluster.tick_all(1)
    
    # Old leader should step down to follower
    old_leader_node = cluster.nodes[old_leader]
    
    # The old leader will either be follower or could become leader again
    # What matters is term convergence
    assert old_leader_node.current_term >= new_term, f"Should have term >= {new_term}, got {old_leader_node.current_term}"
    
    # Either stepped down or became leader at higher term - both are valid
    if old_leader_node.state == RaftState.FOLLOWER:
        print(f"      ✓ Old leader stepped down to FOLLOWER")
    else:
        print(f"      ✓ Old leader state: {old_leader_node.state.name} (valid - may have won new election)")
    
    print(f"      ✓ Old leader term: {old_leader_node.current_term}")
    return cluster


async def test_6_safety_invariant():
    """Test 6: Safety invariant - no conflicting commits"""
    print("\n[6/6] Testing safety invariant (INV-CON-001)...")
    
    cluster = ClusterSimulator(["NODE-A", "NODE-B", "NODE-C"])
    
    # Elect leader and replicate some entries
    leader = None
    for i in range(100):
        await cluster.tick_all(1)
        leader = cluster.get_leader()
        if leader:
            break
    
    # Propose multiple commands
    commands = [
        {"seq": 1, "value": "first"},
        {"seq": 2, "value": "second"},
        {"seq": 3, "value": "third"},
    ]
    
    for cmd in commands:
        await cluster.nodes[leader].propose_command(cmd)
    
    # Let replication happen
    for _ in range(100):
        await cluster.tick_all(1)
    
    # Verify all nodes have identical logs
    logs = {}
    for node_id, node in cluster.nodes.items():
        logs[node_id] = [(e.index, e.term, e.command) for e in node.log]
    
    # Check all logs match
    reference_log = logs[leader]
    for node_id, log in logs.items():
        for i, (idx, term, cmd) in enumerate(log):
            if i < len(reference_log):
                ref_idx, ref_term, ref_cmd = reference_log[i]
                assert idx == ref_idx, f"Index mismatch at position {i}"
                assert term == ref_term, f"Term mismatch at position {i}"
                assert cmd == ref_cmd, f"Command mismatch at position {i}"
    
    print(f"      ✓ All logs identical across cluster")
    print(f"      ✓ Log length: {len(reference_log)} entries")
    print(f"      ✓ INV-CON-001 ENFORCED: No conflicting commits")
    print(f"      ✓ SAFETY INVARIANT VERIFIED")


async def main():
    """Run all P310 tests."""
    print("=" * 70)
    print("PAC-CON-P310-CONSENSUS-ENGINE - Test Suite")
    print("=" * 70)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    tests = [
        ("Cluster Creation", test_1_cluster_creation),
        ("Leader Election", test_2_leader_election),
        ("Log Replication", test_3_log_replication),
        ("Leader Failure", test_4_leader_failure),
        ("Leader Rejoin", test_5_leader_rejoins),
        ("Safety Invariant", test_6_safety_invariant),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except AssertionError as e:
            print(f"\n      ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n      ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 70)
    
    if failed == 0:
        print("ALL TESTS PASSED ✅")
        print("")
        print("INVARIANTS VERIFIED:")
        print("  INV-CON-001 (Safety): ✓ ENFORCED - No conflicting commits")
        print("  INV-CON-002 (Liveness): ✓ ENFORCED - Leader elected when quorum up")
        print("")
        print("🏛️ THE PARLIAMENT IS SEATED")
        print("⚖️ THE GAVEL IS READY")
        print("🗳️ MANY VOICES, ONE TRUTH")
    else:
        print(f"FAILURES: {failed}")
        sys.exit(1)
    
    print("=" * 70)
    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
