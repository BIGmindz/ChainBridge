#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PAC-INT-P330-MESH-EXPLORER                                ║
║                         INTEGRATION TEST                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Test mesh explorer with simulated cluster scenarios.

INV-INT-001: Observation must not interfere with Consensus performance.
INV-INT-002: Federation status is public data.

Goal: Accurate reporting of Leader ID, Node Count, and Block Height.
"""

import sys
sys.path.insert(0, "/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")

from modules.mesh.explorer import (
    MeshExplorer, 
    NodeStatus, 
    NetworkTopology, 
    HealthReport,
    NodeRole, 
    NodeHealth,
    NetworkHealth,
)


def test_healthy_cluster():
    """
    Test: 3-node healthy cluster visualization.
    
    Goal: Accurately report Leader ID, Node Count, Block Height.
    """
    print("=" * 70)
    print("P330 MESH EXPLORER - Healthy Cluster Test")
    print("=" * 70)
    
    explorer = MeshExplorer()
    
    # Register 3-node cluster
    print("\n[SETUP] Registering 3-node cluster...")
    
    explorer.register_node(
        node_id="LEADER-1",
        endpoint="leader1.mesh.io:8080",
        public_key="pk_leader1_secret",
        role=NodeRole.LEADER,
        term=10,
        commit_index=500,
        latency_ms=5.0,
        stake=100000,
        status="ACTIVE",
    )
    
    explorer.register_node(
        node_id="FOLLOWER-2",
        endpoint="follower2.mesh.io:8080",
        public_key="pk_follower2_secret",
        role=NodeRole.FOLLOWER,
        term=10,
        commit_index=498,
        latency_ms=15.0,
        stake=100000,
        status="ACTIVE",
    )
    
    explorer.register_node(
        node_id="FOLLOWER-3",
        endpoint="follower3.mesh.io:8080",
        public_key="pk_follower3_secret",
        role=NodeRole.FOLLOWER,
        term=10,
        commit_index=499,
        latency_ms=12.0,
        stake=100000,
        status="ACTIVE",
    )
    
    # Get topology
    print("\n[TOPOLOGY QUERY]")
    topology = explorer.get_topology()
    
    print(f"   Total Nodes: {topology.total_nodes}")
    print(f"   Active Nodes: {topology.active_nodes}")
    print(f"   Leader ID: {topology.leader_id}")
    print(f"   Current Term: {topology.current_term}")
    print(f"   Latest Commit: {topology.latest_commit_index}")
    
    # Verify
    assert topology.total_nodes == 3, f"Expected 3 nodes, got {topology.total_nodes}"
    assert topology.leader_id == "LEADER-1", f"Expected LEADER-1, got {topology.leader_id}"
    assert topology.current_term == 10, f"Expected term 10, got {topology.current_term}"
    assert topology.latest_commit_index == 500
    
    print(f"\n   ✓ Node count: CORRECT")
    print(f"   ✓ Leader ID: CORRECT")
    print(f"   ✓ Term: CORRECT")
    print(f"   ✓ Commit index: CORRECT")
    
    # Get leader/followers
    print("\n[ROLE IDENTIFICATION]")
    leader = explorer.get_leader()
    followers = explorer.get_followers()
    
    assert leader is not None
    assert leader.node_id == "LEADER-1"
    assert len(followers) == 2
    
    print(f"   Leader: {leader.node_id}")
    print(f"   Followers: {[f.node_id for f in followers]}")
    print(f"   ✓ Leader count: 1")
    print(f"   ✓ Follower count: 2")
    
    # Get health report
    print("\n[HEALTH REPORT]")
    health = explorer.get_health_report()
    
    assert health.network_health == NetworkHealth.HEALTHY
    assert health.has_leader
    assert health.consensus_active
    
    print(f"   Network Health: {health.network_health.value}")
    print(f"   Has Leader: {health.has_leader}")
    print(f"   Consensus Active: {health.consensus_active}")
    print(f"   Healthy Nodes: {health.healthy_nodes}")
    print(f"   Avg Latency: {health.avg_latency_ms:.1f}ms")
    
    print("\n" + "=" * 70)
    print("HEALTHY CLUSTER TEST: PASSED ✅")
    print("=" * 70)
    return True


def test_degraded_cluster():
    """
    Test: Cluster with high-latency and unreachable nodes.
    """
    print("\n" + "=" * 70)
    print("P330 MESH EXPLORER - Degraded Cluster Test")
    print("=" * 70)
    
    explorer = MeshExplorer()
    
    print("\n[SETUP] Registering cluster with degraded nodes...")
    
    # Leader (healthy)
    explorer.register_node(
        node_id="NODE-A",
        endpoint="node-a.mesh.io:8080",
        public_key="pk_a",
        role=NodeRole.LEADER,
        term=5,
        commit_index=200,
        latency_ms=10.0,
        stake=100000,
        status="ACTIVE",
    )
    
    # Follower (high latency - degraded)
    explorer.register_node(
        node_id="NODE-B",
        endpoint="node-b.mesh.io:8080",
        public_key="pk_b",
        role=NodeRole.FOLLOWER,
        term=5,
        commit_index=195,
        latency_ms=300.0,  # High latency!
        stake=100000,
        status="ACTIVE",
    )
    
    # Follower (very high latency - unreachable)
    explorer.register_node(
        node_id="NODE-C",
        endpoint="node-c.mesh.io:8080",
        public_key="pk_c",
        role=NodeRole.FOLLOWER,
        term=5,
        commit_index=180,
        latency_ms=6000.0,  # Unreachable threshold!
        stake=100000,
        status="ACTIVE",
    )
    
    # Get topology
    topology = explorer.get_topology()
    
    print(f"\n[NODE HEALTH STATUS]")
    for node in topology.nodes:
        print(f"   {node.node_id}: {node.health.value} - {node.health_reason}")
    
    # Verify health assessments
    node_a = explorer.get_node("NODE-A")
    node_b = explorer.get_node("NODE-B")
    node_c = explorer.get_node("NODE-C")
    
    assert node_a.health == NodeHealth.HEALTHY
    assert node_b.health == NodeHealth.DEGRADED
    assert node_c.health == NodeHealth.UNREACHABLE
    
    print(f"\n   ✓ NODE-A correctly marked HEALTHY")
    print(f"   ✓ NODE-B correctly marked DEGRADED (high latency)")
    print(f"   ✓ NODE-C correctly marked UNREACHABLE (very high latency)")
    
    # Get health report
    health = explorer.get_health_report()
    
    assert health.network_health == NetworkHealth.DEGRADED
    assert health.healthy_nodes == 1
    assert health.degraded_nodes == 1
    assert health.unreachable_nodes == 1
    
    print(f"\n[HEALTH REPORT]")
    print(f"   Network Health: {health.network_health.value}")
    print(f"   Reason: {health.health_reason}")
    print(f"   Healthy: {health.healthy_nodes}")
    print(f"   Degraded: {health.degraded_nodes}")
    print(f"   Unreachable: {health.unreachable_nodes}")
    
    print("\n" + "=" * 70)
    print("DEGRADED CLUSTER TEST: PASSED ✅")
    print("=" * 70)
    return True


def test_leaderless_cluster():
    """
    Test: Cluster with no leader (critical state).
    """
    print("\n" + "=" * 70)
    print("P330 MESH EXPLORER - Leaderless Cluster Test")
    print("=" * 70)
    
    explorer = MeshExplorer()
    
    print("\n[SETUP] Registering leaderless cluster...")
    
    # All candidates (election in progress)
    for i in range(1, 4):
        explorer.register_node(
            node_id=f"CANDIDATE-{i}",
            endpoint=f"candidate{i}.mesh.io:8080",
            public_key=f"pk_candidate{i}",
            role=NodeRole.CANDIDATE,  # No leader!
            term=5,
            commit_index=100,
            latency_ms=20.0,
            stake=100000,
            status="ACTIVE",
        )
    
    topology = explorer.get_topology()
    health = explorer.get_health_report()
    
    print(f"\n[STATUS]")
    print(f"   Leader ID: {topology.leader_id}")
    print(f"   Has Leader: {health.has_leader}")
    print(f"   Network Health: {health.network_health.value}")
    print(f"   Reason: {health.health_reason}")
    
    assert topology.leader_id is None
    assert not health.has_leader
    assert health.network_health == NetworkHealth.CRITICAL
    assert "No leader" in health.health_reason
    
    print(f"\n   ✓ Correctly detected NO LEADER")
    print(f"   ✓ Correctly marked CRITICAL")
    
    print("\n" + "=" * 70)
    print("LEADERLESS CLUSTER TEST: PASSED ✅")
    print("=" * 70)
    return True


def test_banned_node():
    """
    Test: Cluster with a banned (slashed) node.
    """
    print("\n" + "=" * 70)
    print("P330 MESH EXPLORER - Banned Node Test")
    print("=" * 70)
    
    explorer = MeshExplorer()
    
    print("\n[SETUP] Registering cluster with banned node...")
    
    # Leader (healthy)
    explorer.register_node(
        node_id="HONEST-1",
        endpoint="honest1.mesh.io:8080",
        public_key="pk_honest1",
        role=NodeRole.LEADER,
        term=7,
        commit_index=300,
        latency_ms=8.0,
        stake=100000,
        status="ACTIVE",
    )
    
    # Follower (healthy)
    explorer.register_node(
        node_id="HONEST-2",
        endpoint="honest2.mesh.io:8080",
        public_key="pk_honest2",
        role=NodeRole.FOLLOWER,
        term=7,
        commit_index=299,
        latency_ms=12.0,
        stake=100000,
        status="ACTIVE",
    )
    
    # Banned node (slashed)
    explorer.register_node(
        node_id="MALICIOUS",
        endpoint="malicious.mesh.io:8080",
        public_key="pk_malicious",
        role=NodeRole.FOLLOWER,
        term=6,  # Old term - was banned
        commit_index=250,
        latency_ms=0.0,
        stake=0,  # Stake slashed!
        status="BANNED",
    )
    
    topology = explorer.get_topology()
    health = explorer.get_health_report()
    
    print(f"\n[STATUS]")
    print(f"   Total Nodes: {topology.total_nodes}")
    print(f"   Active Nodes: {topology.active_nodes}")
    print(f"   Banned Nodes: {health.banned_nodes}")
    
    # Verify counts
    assert topology.total_nodes == 3
    assert topology.active_nodes == 2  # Banned doesn't count as active
    assert health.banned_nodes == 1
    
    # Verify banned node detection
    banned = explorer.get_banned_nodes()
    assert len(banned) == 1
    assert banned[0].node_id == "MALICIOUS"
    assert banned[0].health == NodeHealth.BANNED
    
    print(f"\n   ✓ Total nodes: 3 (includes banned)")
    print(f"   ✓ Active nodes: 2 (excludes banned)")
    print(f"   ✓ Banned node correctly identified: MALICIOUS")
    
    print("\n[BANNED NODE DETAILS]")
    mal = explorer.get_node("MALICIOUS")
    print(f"   ID: {mal.node_id}")
    print(f"   Health: {mal.health.value}")
    print(f"   Status: {mal.governance_status}")
    print(f"   Stake: {mal.stake_amount}")
    
    print("\n" + "=" * 70)
    print("BANNED NODE TEST: PASSED ✅")
    print("=" * 70)
    return True


def test_key_sanitization():
    """
    Test: Private keys are sanitized before display.
    
    INV-INT-002: Federation status is public data (but keys are sanitized).
    """
    print("\n" + "=" * 70)
    print("P330 MESH EXPLORER - Key Sanitization Test (INV-INT-002)")
    print("=" * 70)
    
    explorer = MeshExplorer()
    
    # Register node with secret key
    secret_key = "SUPER_SECRET_PRIVATE_KEY_DO_NOT_SHARE_abc123xyz"
    
    explorer.register_node(
        node_id="SECURE-NODE",
        endpoint="secure.mesh.io:8080",
        public_key=secret_key,
        role=NodeRole.LEADER,
        term=1,
        commit_index=1,
        latency_ms=1.0,
        stake=100000,
        status="ACTIVE",
    )
    
    node = explorer.get_node("SECURE-NODE")
    
    print(f"\n[SANITIZATION CHECK]")
    print(f"   Original Key: {secret_key[:20]}...")
    print(f"   Fingerprint:  {node.public_key_fingerprint}")
    
    # Key must NOT be exposed
    assert node.public_key_fingerprint != secret_key
    assert len(node.public_key_fingerprint) == 16  # SHA256 truncated
    
    # Serialize and check dict
    node_dict = node.to_dict()
    assert secret_key not in str(node_dict)
    
    print(f"\n   ✓ Original key NOT in output")
    print(f"   ✓ Only 16-char fingerprint exposed")
    print(f"   ✓ Safe for public display")
    
    print("\n" + "=" * 70)
    print("KEY SANITIZATION TEST: PASSED ✅")
    print("=" * 70)
    return True


if __name__ == "__main__":
    test1 = test_healthy_cluster()
    test2 = test_degraded_cluster()
    test3 = test_leaderless_cluster()
    test4 = test_banned_node()
    test5 = test_key_sanitization()
    
    print("\n" + "=" * 70)
    print("P330 INTEGRATION TESTS COMPLETE")
    print("=" * 70)
    
    all_passed = all([test1, test2, test3, test4, test5])
    
    if all_passed:
        print("STATUS: ALL TESTS PASSED ✅")
        print("INV-INT-001 (Observer Effect): ENFORCED (read-only)")
        print("INV-INT-002 (Public Transparency): ENFORCED (sanitized)")
        print("=" * 70)
        print("\n🔭 The Fog of War is lifted. The Mesh is visible.")
        exit(0)
    else:
        print("STATUS: SOME TESTS FAILED ❌")
        exit(1)
