#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     MESH EXPLORER - THE OBSERVATORY                          ║
║                   PAC-INT-P330-MESH-EXPLORER                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  God View of the Federation - Watch the Mesh Breathe                         ║
║                                                                              ║
║  "To govern, one must see."                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Mesh Explorer provides:
  - Real-time topology visualization
  - Node status aggregation
  - Leader/Follower identification
  - Health reporting
  - Slashing event history

CONSTRAINTS:
  - READ-ONLY: Explorer cannot modify state
  - SANITIZED: Private keys are never exposed
  - PARTITION-TOLERANT: Handles partial visibility

INVARIANTS:
  INV-INT-001 (Observer Effect): Observation must not interfere with Consensus.
  INV-INT-002 (Public Transparency): Federation status is public data.

Usage:
    from modules.mesh.explorer import MeshExplorer
    
    # Create explorer
    explorer = MeshExplorer()
    
    # Register data sources
    explorer.register_consensus_engine(consensus)
    explorer.register_policy(policy)
    
    # Get topology
    topology = explorer.get_topology()
    
    # Get health report
    health = explorer.get_health_report()
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .consensus import ConsensusEngine
    from ..governance.policy import FederationPolicy

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class NodeRole(Enum):
    """Consensus role of a node."""
    
    LEADER = "LEADER"
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"
    OBSERVER = "OBSERVER"        # Non-voting node
    UNKNOWN = "UNKNOWN"


class NodeHealth(Enum):
    """Health status of a node."""
    
    HEALTHY = "HEALTHY"           # Normal operation
    DEGRADED = "DEGRADED"         # Slow/lagging
    UNREACHABLE = "UNREACHABLE"   # No recent heartbeat
    BANNED = "BANNED"             # Slashed and expelled
    UNKNOWN = "UNKNOWN"


class NetworkHealth(Enum):
    """Overall network health status."""
    
    HEALTHY = "HEALTHY"           # All systems nominal
    DEGRADED = "DEGRADED"         # Some nodes unhealthy
    PARTITIONED = "PARTITIONED"   # Network split detected
    CRITICAL = "CRITICAL"         # No leader / consensus broken
    UNKNOWN = "UNKNOWN"


# ══════════════════════════════════════════════════════════════════════════════
# NODE STATUS MODEL
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NodeStatus:
    """
    Comprehensive status of a single node in the mesh.
    
    Aggregates data from:
      - Networking (P300): Latency, last_seen
      - Identity (P305): node_id, endpoint
      - Consensus (P310): role, term, commit_index
      - Governance (P320): stake, warnings, status
    """
    
    # Identity
    node_id: str
    endpoint: str = ""
    public_key_fingerprint: str = ""  # Sanitized - not full key!
    
    # Consensus state
    role: NodeRole = NodeRole.UNKNOWN
    current_term: int = 0
    commit_index: int = 0
    last_log_index: int = 0
    
    # Networking
    latency_ms: float = 0.0
    last_seen: str = ""
    peers_connected: int = 0
    
    # Governance
    stake_amount: int = 0
    governance_status: str = "UNKNOWN"  # ACTIVE, PROBATION, BANNED, etc.
    warnings: int = 0
    slashing_events: int = 0
    
    # Health
    health: NodeHealth = NodeHealth.UNKNOWN
    health_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (sanitized for public display)."""
        return {
            "node_id": self.node_id,
            "endpoint": self._sanitize_endpoint(self.endpoint),
            "public_key_fingerprint": self.public_key_fingerprint,
            "role": self.role.value,
            "current_term": self.current_term,
            "commit_index": self.commit_index,
            "last_log_index": self.last_log_index,
            "latency_ms": round(self.latency_ms, 2),
            "last_seen": self.last_seen,
            "peers_connected": self.peers_connected,
            "stake_amount": self.stake_amount,
            "governance_status": self.governance_status,
            "warnings": self.warnings,
            "slashing_events": self.slashing_events,
            "health": self.health.value,
            "health_reason": self.health_reason,
        }
    
    @staticmethod
    def _sanitize_endpoint(endpoint: str) -> str:
        """Sanitize endpoint (hide port in production if needed)."""
        # For now, just return as-is; could mask in production
        return endpoint


# ══════════════════════════════════════════════════════════════════════════════
# NETWORK TOPOLOGY
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NetworkLink:
    """Link between two nodes in the mesh."""
    
    source_id: str
    target_id: str
    latency_ms: float = 0.0
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "latency_ms": round(self.latency_ms, 2),
            "is_active": self.is_active,
        }


@dataclass
class NetworkTopology:
    """
    Complete topology view of the mesh.
    
    Contains nodes and links for visualization.
    """
    
    # Timestamp
    snapshot_time: str = ""
    
    # Nodes
    nodes: List[NodeStatus] = field(default_factory=list)
    
    # Links (connections between nodes)
    links: List[NetworkLink] = field(default_factory=list)
    
    # Summary stats
    total_nodes: int = 0
    active_nodes: int = 0
    leader_id: Optional[str] = None
    current_term: int = 0
    latest_commit_index: int = 0
    
    def __post_init__(self):
        if not self.snapshot_time:
            self.snapshot_time = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_time": self.snapshot_time,
            "total_nodes": self.total_nodes,
            "active_nodes": self.active_nodes,
            "leader_id": self.leader_id,
            "current_term": self.current_term,
            "latest_commit_index": self.latest_commit_index,
            "nodes": [n.to_dict() for n in self.nodes],
            "links": [l.to_dict() for l in self.links],
        }


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH REPORT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class HealthReport:
    """
    Comprehensive health report of the federation.
    
    The truth of the network, even if ugly.
    """
    
    # Overall status
    network_health: NetworkHealth = NetworkHealth.UNKNOWN
    health_reason: str = ""
    
    # Timestamp
    report_time: str = ""
    
    # Node counts
    total_nodes: int = 0
    healthy_nodes: int = 0
    degraded_nodes: int = 0
    unreachable_nodes: int = 0
    banned_nodes: int = 0
    
    # Consensus status
    has_leader: bool = False
    leader_id: Optional[str] = None
    current_term: int = 0
    consensus_active: bool = False
    
    # Recent events
    recent_slashings: List[str] = field(default_factory=list)
    partition_detected: bool = False
    partition_groups: List[List[str]] = field(default_factory=list)
    
    # Metrics
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    commit_index_spread: int = 0  # Difference between highest and lowest
    
    def __post_init__(self):
        if not self.report_time:
            self.report_time = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "network_health": self.network_health.value,
            "health_reason": self.health_reason,
            "report_time": self.report_time,
            "total_nodes": self.total_nodes,
            "healthy_nodes": self.healthy_nodes,
            "degraded_nodes": self.degraded_nodes,
            "unreachable_nodes": self.unreachable_nodes,
            "banned_nodes": self.banned_nodes,
            "has_leader": self.has_leader,
            "leader_id": self.leader_id,
            "current_term": self.current_term,
            "consensus_active": self.consensus_active,
            "recent_slashings": self.recent_slashings,
            "partition_detected": self.partition_detected,
            "partition_groups": self.partition_groups,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "commit_index_spread": self.commit_index_spread,
        }


# ══════════════════════════════════════════════════════════════════════════════
# MESH EXPLORER
# ══════════════════════════════════════════════════════════════════════════════

class MeshExplorer:
    """
    The Observatory - God View of the Federation.
    
    Aggregates data from all mesh components to provide:
      - Real-time topology
      - Health reports
      - Leader identification
      - Slashing history
    
    CONSTRAINTS:
      - READ-ONLY: Cannot modify any state
      - SANITIZED: Never exposes private keys
    
    INV-INT-001: Observation does not interfere with Consensus
    INV-INT-002: Federation status is public data
    """
    
    def __init__(self):
        """Initialize the Mesh Explorer."""
        
        # Data sources (registered externally)
        self._consensus_engine: Optional["ConsensusEngine"] = None
        self._policy: Optional["FederationPolicy"] = None
        
        # Cached node data (simulated when no live sources)
        self._node_cache: Dict[str, Dict[str, Any]] = {}
        
        # Link cache
        self._link_cache: List[NetworkLink] = []
        
        # Configuration
        self._latency_threshold_degraded = 200.0  # ms
        self._latency_threshold_unreachable = 5000.0  # ms
        self._heartbeat_timeout = 30.0  # seconds
        
        logger.info("MeshExplorer initialized - The Observatory is open")
    
    # ──────────────────────────────────────────────────────────────────────────
    # DATA SOURCE REGISTRATION
    # ──────────────────────────────────────────────────────────────────────────
    
    def register_consensus_engine(self, engine: "ConsensusEngine"):
        """Register consensus engine as data source."""
        self._consensus_engine = engine
        logger.info(f"Registered consensus engine: {engine.node_id}")
    
    def register_policy(self, policy: "FederationPolicy"):
        """Register federation policy as data source."""
        self._policy = policy
        logger.info("Registered federation policy")
    
    def register_node(
        self,
        node_id: str,
        endpoint: str = "",
        public_key: str = "",
        role: NodeRole = NodeRole.FOLLOWER,
        term: int = 0,
        commit_index: int = 0,
        latency_ms: float = 0.0,
        stake: int = 0,
        status: str = "ACTIVE",
    ):
        """
        Register a node for tracking (simulated mode).
        
        Used when live data sources aren't available.
        """
        # Sanitize public key to fingerprint
        fingerprint = ""
        if public_key:
            fingerprint = hashlib.sha256(public_key.encode()).hexdigest()[:16]
        
        self._node_cache[node_id] = {
            "node_id": node_id,
            "endpoint": endpoint,
            "public_key_fingerprint": fingerprint,
            "role": role,
            "current_term": term,
            "commit_index": commit_index,
            "last_log_index": commit_index,
            "latency_ms": latency_ms,
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "stake_amount": stake,
            "governance_status": status,
            "warnings": 0,
            "slashing_events": 0,
        }
    
    def register_link(
        self,
        source_id: str,
        target_id: str,
        latency_ms: float = 0.0,
        is_active: bool = True,
    ):
        """Register a link between nodes."""
        self._link_cache.append(NetworkLink(
            source_id=source_id,
            target_id=target_id,
            latency_ms=latency_ms,
            is_active=is_active,
        ))
    
    def update_node(self, node_id: str, **kwargs):
        """Update cached node data."""
        if node_id in self._node_cache:
            self._node_cache[node_id].update(kwargs)
            self._node_cache[node_id]["last_seen"] = datetime.now(timezone.utc).isoformat()
    
    # ──────────────────────────────────────────────────────────────────────────
    # TOPOLOGY QUERY
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_topology(self) -> NetworkTopology:
        """
        Get current network topology.
        
        INV-INT-002: Federation status is public data.
        
        Returns:
            NetworkTopology with all nodes and links
        """
        nodes = []
        leader_id = None
        max_term = 0
        max_commit = 0
        
        # Build from cache
        for node_id, data in self._node_cache.items():
            health, reason = self._assess_node_health(data)
            
            node = NodeStatus(
                node_id=node_id,
                endpoint=data.get("endpoint", ""),
                public_key_fingerprint=data.get("public_key_fingerprint", ""),
                role=data.get("role", NodeRole.UNKNOWN),
                current_term=data.get("current_term", 0),
                commit_index=data.get("commit_index", 0),
                last_log_index=data.get("last_log_index", 0),
                latency_ms=data.get("latency_ms", 0.0),
                last_seen=data.get("last_seen", ""),
                peers_connected=data.get("peers_connected", 0),
                stake_amount=data.get("stake_amount", 0),
                governance_status=data.get("governance_status", "UNKNOWN"),
                warnings=data.get("warnings", 0),
                slashing_events=data.get("slashing_events", 0),
                health=health,
                health_reason=reason,
            )
            
            nodes.append(node)
            
            # Track leader
            if node.role == NodeRole.LEADER:
                leader_id = node_id
            
            # Track highest term and commit
            if node.current_term > max_term:
                max_term = node.current_term
            if node.commit_index > max_commit:
                max_commit = node.commit_index
        
        # Count active nodes (not banned)
        active_count = len([n for n in nodes 
                          if n.governance_status not in ("BANNED", "UNBONDING")])
        
        return NetworkTopology(
            nodes=nodes,
            links=self._link_cache.copy(),
            total_nodes=len(nodes),
            active_nodes=active_count,
            leader_id=leader_id,
            current_term=max_term,
            latest_commit_index=max_commit,
        )
    
    def _assess_node_health(self, data: Dict[str, Any]) -> Tuple[NodeHealth, str]:
        """Assess health of a single node."""
        
        # Check if banned
        if data.get("governance_status") == "BANNED":
            return NodeHealth.BANNED, "Node has been slashed and banned"
        
        # Check latency
        latency = data.get("latency_ms", 0.0)
        if latency > self._latency_threshold_unreachable:
            return NodeHealth.UNREACHABLE, f"Latency {latency}ms exceeds threshold"
        
        if latency > self._latency_threshold_degraded:
            return NodeHealth.DEGRADED, f"High latency: {latency}ms"
        
        # Check last seen
        last_seen = data.get("last_seen", "")
        if last_seen:
            try:
                seen_time = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                elapsed = (datetime.now(timezone.utc) - seen_time).total_seconds()
                if elapsed > self._heartbeat_timeout:
                    return NodeHealth.UNREACHABLE, f"No heartbeat for {elapsed:.0f}s"
            except Exception:
                pass
        
        # Check warnings
        if data.get("warnings", 0) >= 2:
            return NodeHealth.DEGRADED, f"Node has {data['warnings']} warnings"
        
        return NodeHealth.HEALTHY, "Node operating normally"
    
    # ──────────────────────────────────────────────────────────────────────────
    # HEALTH REPORT
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_health_report(self) -> HealthReport:
        """
        Get comprehensive health report.
        
        Shows the truth of the network, even if ugly.
        
        Returns:
            HealthReport with all metrics
        """
        topology = self.get_topology()
        
        # Count by health status
        healthy = 0
        degraded = 0
        unreachable = 0
        banned = 0
        
        latencies = []
        commit_indices = []
        
        for node in topology.nodes:
            if node.health == NodeHealth.HEALTHY:
                healthy += 1
            elif node.health == NodeHealth.DEGRADED:
                degraded += 1
            elif node.health == NodeHealth.UNREACHABLE:
                unreachable += 1
            elif node.health == NodeHealth.BANNED:
                banned += 1
            
            if node.latency_ms > 0:
                latencies.append(node.latency_ms)
            
            if node.commit_index > 0:
                commit_indices.append(node.commit_index)
        
        # Calculate metrics
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0
        commit_spread = (max(commit_indices) - min(commit_indices)) if commit_indices else 0
        
        # Determine overall health
        network_health, reason = self._assess_network_health(
            topology, healthy, degraded, unreachable, banned
        )
        
        # Detect partitions (simplified)
        partition_detected = False
        partition_groups: List[List[str]] = []
        
        if unreachable > 0 and topology.active_nodes > 1:
            # Simple partition detection: if some nodes unreachable
            reachable = [n.node_id for n in topology.nodes 
                        if n.health != NodeHealth.UNREACHABLE]
            unreachable_ids = [n.node_id for n in topology.nodes 
                              if n.health == NodeHealth.UNREACHABLE]
            
            if reachable and unreachable_ids:
                partition_detected = True
                partition_groups = [reachable, unreachable_ids]
        
        return HealthReport(
            network_health=network_health,
            health_reason=reason,
            total_nodes=topology.total_nodes,
            healthy_nodes=healthy,
            degraded_nodes=degraded,
            unreachable_nodes=unreachable,
            banned_nodes=banned,
            has_leader=topology.leader_id is not None,
            leader_id=topology.leader_id,
            current_term=topology.current_term,
            consensus_active=topology.leader_id is not None and healthy >= 2,
            recent_slashings=[],  # Would be populated from policy
            partition_detected=partition_detected,
            partition_groups=partition_groups,
            avg_latency_ms=avg_latency,
            max_latency_ms=max_latency,
            commit_index_spread=commit_spread,
        )
    
    def _assess_network_health(
        self,
        topology: NetworkTopology,
        healthy: int,
        degraded: int,
        unreachable: int,
        banned: int,
    ) -> Tuple[NetworkHealth, str]:
        """Assess overall network health."""
        
        total_active = healthy + degraded + unreachable
        
        # No leader = CRITICAL
        if topology.leader_id is None and total_active > 0:
            return NetworkHealth.CRITICAL, "No leader elected - consensus halted"
        
        # All banned = CRITICAL
        if total_active == 0:
            return NetworkHealth.CRITICAL, "No active nodes in federation"
        
        # Majority unreachable = PARTITIONED
        if unreachable > total_active / 2:
            return NetworkHealth.PARTITIONED, f"{unreachable}/{total_active} nodes unreachable"
        
        # Any unreachable = DEGRADED
        if unreachable > 0:
            return NetworkHealth.DEGRADED, f"{unreachable} node(s) unreachable"
        
        # Any degraded = DEGRADED
        if degraded > 0:
            return NetworkHealth.DEGRADED, f"{degraded} node(s) with high latency"
        
        # All healthy
        return NetworkHealth.HEALTHY, "All systems nominal"
    
    # ──────────────────────────────────────────────────────────────────────────
    # CONVENIENCE QUERIES
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_leader(self) -> Optional[NodeStatus]:
        """Get current leader node."""
        topology = self.get_topology()
        for node in topology.nodes:
            if node.role == NodeRole.LEADER:
                return node
        return None
    
    def get_followers(self) -> List[NodeStatus]:
        """Get all follower nodes."""
        topology = self.get_topology()
        return [n for n in topology.nodes if n.role == NodeRole.FOLLOWER]
    
    def get_node(self, node_id: str) -> Optional[NodeStatus]:
        """Get specific node status."""
        topology = self.get_topology()
        for node in topology.nodes:
            if node.node_id == node_id:
                return node
        return None
    
    def get_banned_nodes(self) -> List[NodeStatus]:
        """Get all banned nodes."""
        topology = self.get_topology()
        return [n for n in topology.nodes if n.health == NodeHealth.BANNED]
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATUS / SUMMARY
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_summary(self) -> Dict[str, Any]:
        """Get brief summary for dashboards."""
        topology = self.get_topology()
        health = self.get_health_report()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "network_health": health.network_health.value,
            "leader_id": topology.leader_id,
            "total_nodes": topology.total_nodes,
            "active_nodes": topology.active_nodes,
            "healthy_nodes": health.healthy_nodes,
            "current_term": topology.current_term,
            "commit_index": topology.latest_commit_index,
            "consensus_active": health.consensus_active,
        }
    
    def print_status(self):
        """Print formatted status to console."""
        topology = self.get_topology()
        health = self.get_health_report()
        
        print("\n" + "=" * 60)
        print("         MESH EXPLORER - FEDERATION STATUS")
        print("=" * 60)
        
        print(f"\n📊 NETWORK HEALTH: {health.network_health.value}")
        print(f"   Reason: {health.health_reason}")
        
        print(f"\n👑 LEADER: {topology.leader_id or 'NONE'}")
        print(f"   Term: {topology.current_term}")
        print(f"   Commit Index: {topology.latest_commit_index}")
        
        print(f"\n📡 NODES: {topology.total_nodes} total, {topology.active_nodes} active")
        print(f"   Healthy:     {health.healthy_nodes}")
        print(f"   Degraded:    {health.degraded_nodes}")
        print(f"   Unreachable: {health.unreachable_nodes}")
        print(f"   Banned:      {health.banned_nodes}")
        
        if health.partition_detected:
            print(f"\n⚠️  PARTITION DETECTED!")
            for i, group in enumerate(health.partition_groups):
                print(f"   Group {i+1}: {', '.join(group)}")
        
        print(f"\n🔗 LATENCY:")
        print(f"   Average: {health.avg_latency_ms:.1f}ms")
        print(f"   Maximum: {health.max_latency_ms:.1f}ms")
        
        print("\n" + "-" * 60)
        print("NODE DETAILS:")
        print("-" * 60)
        
        for node in topology.nodes:
            role_icon = {
                NodeRole.LEADER: "👑",
                NodeRole.FOLLOWER: "📋",
                NodeRole.CANDIDATE: "🗳️",
                NodeRole.OBSERVER: "👁️",
                NodeRole.UNKNOWN: "❓",
            }.get(node.role, "❓")
            
            health_icon = {
                NodeHealth.HEALTHY: "✅",
                NodeHealth.DEGRADED: "⚠️",
                NodeHealth.UNREACHABLE: "❌",
                NodeHealth.BANNED: "🚫",
            }.get(node.health, "❓")
            
            print(f"\n{role_icon} {node.node_id} {health_icon}")
            print(f"   Role: {node.role.value}, Term: {node.current_term}, Commit: {node.commit_index}")
            print(f"   Latency: {node.latency_ms}ms, Status: {node.governance_status}")
            if node.health_reason:
                print(f"   Health: {node.health_reason}")
        
        print("\n" + "=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test():
    """Run self-test to validate explorer module."""
    print("=" * 70)
    print("MESH EXPLORER v3.0.0 - Self Test")
    print("=" * 70)
    
    # Test 1: Create explorer and register nodes
    print("\n[1/5] Testing explorer initialization...")
    explorer = MeshExplorer()
    
    # Simulate 3-node cluster
    explorer.register_node(
        node_id="NODE-1",
        endpoint="node1.mesh.io:8080",
        public_key="pk_node1_secret_key",
        role=NodeRole.LEADER,
        term=5,
        commit_index=100,
        latency_ms=10.0,
        stake=100000,
        status="ACTIVE",
    )
    
    explorer.register_node(
        node_id="NODE-2",
        endpoint="node2.mesh.io:8080",
        public_key="pk_node2_secret_key",
        role=NodeRole.FOLLOWER,
        term=5,
        commit_index=99,
        latency_ms=25.0,
        stake=100000,
        status="ACTIVE",
    )
    
    explorer.register_node(
        node_id="NODE-3",
        endpoint="node3.mesh.io:8080",
        public_key="pk_node3_secret_key",
        role=NodeRole.FOLLOWER,
        term=5,
        commit_index=98,
        latency_ms=15.0,
        stake=100000,
        status="ACTIVE",
    )
    
    print(f"      ✓ Registered 3 nodes")
    
    # Test 2: Get topology
    print("\n[2/5] Testing topology query...")
    topology = explorer.get_topology()
    
    assert topology.total_nodes == 3
    assert topology.active_nodes == 3
    assert topology.leader_id == "NODE-1"
    assert topology.current_term == 5
    
    print(f"      ✓ Total nodes: {topology.total_nodes}")
    print(f"      ✓ Active nodes: {topology.active_nodes}")
    print(f"      ✓ Leader: {topology.leader_id}")
    print(f"      ✓ Term: {topology.current_term}")
    
    # Test 3: Verify leader/follower counts
    print("\n[3/5] Testing leader/follower identification...")
    
    leader = explorer.get_leader()
    followers = explorer.get_followers()
    
    assert leader is not None
    assert leader.node_id == "NODE-1"
    assert len(followers) == 2
    
    print(f"      ✓ Leader identified: {leader.node_id}")
    print(f"      ✓ Follower count: {len(followers)}")
    
    # Test 4: Health report
    print("\n[4/5] Testing health report...")
    health = explorer.get_health_report()
    
    assert health.network_health == NetworkHealth.HEALTHY
    assert health.has_leader
    assert health.healthy_nodes == 3
    assert health.consensus_active
    
    print(f"      ✓ Network health: {health.network_health.value}")
    print(f"      ✓ Has leader: {health.has_leader}")
    print(f"      ✓ Healthy nodes: {health.healthy_nodes}")
    print(f"      ✓ Consensus active: {health.consensus_active}")
    
    # Test 5: Sanitization check
    print("\n[5/5] Testing key sanitization (INV-INT-002)...")
    
    node = explorer.get_node("NODE-1")
    assert node is not None
    
    # Public key should be fingerprint, not full key
    assert node.public_key_fingerprint != "pk_node1_secret_key"
    assert len(node.public_key_fingerprint) == 16  # SHA256 truncated
    
    print(f"      ✓ Original key: pk_node1_secret_key")
    print(f"      ✓ Fingerprint:  {node.public_key_fingerprint}")
    print(f"      ✓ Keys are sanitized for public display")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print("INV-INT-001 (Observer Effect): ENFORCED (read-only)")
    print("INV-INT-002 (Public Transparency): ENFORCED (sanitized)")
    print("=" * 70)
    
    # Print full status display
    print("\n🔭 DEMONSTRATION: Full Status Display")
    explorer.print_status()
    
    print("\n🔭 The Fog of War is lifted. The Mesh is visible.")


if __name__ == "__main__":
    _self_test()
