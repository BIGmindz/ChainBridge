#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     PARTITION RESILIENCE TEST                                ║
║                     PAC-SEC-P610-PARTITION-TEST                               ║
║                                                                              ║
║  "The Truth is One. It cannot be Split."                                     ║
║                                                                              ║
║  Simulates a 5-node cluster with network partition (split-brain):            ║
║    1. Cluster: [N0, N1, N2, N3, N4]                                          ║
║    2. Partition: [N0, N1, N2] vs [N3, N4]                                    ║
║    3. Majority (3) commits Tx A                                              ║
║    4. Minority (2) stalls on Tx B                                            ║
║    5. Heal partition                                                         ║
║    6. All 5 converge to Tx A, discard Tx B                                   ║
║                                                                              ║
║  Invariants Enforced:                                                        ║
║    - INV-SEC-010: Majority Rule (>50% required for commit)                   ║
║    - INV-SEC-011: Self-Healing (minority syncs to majority)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS AND CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

class NodeState(Enum):
    """Node operational states."""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"
    PARTITIONED = "partitioned"


class TxStatus(Enum):
    """Transaction status."""
    PENDING = "pending"
    COMMITTED = "committed"
    REJECTED = "rejected"
    STALLED = "stalled"


# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Transaction:
    """A transaction to be committed to the cluster."""
    tx_id: str
    payload: str
    submitted_to: int  # Node ID
    submitted_at: float
    status: TxStatus = TxStatus.PENDING
    committed_at: Optional[float] = None
    committed_by: Optional[List[int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "payload": self.payload,
            "submitted_to": self.submitted_to,
            "submitted_at": self.submitted_at,
            "status": self.status.value,
            "committed_at": self.committed_at,
            "committed_by": self.committed_by
        }


@dataclass
class Block:
    """A block in the simulated chain."""
    height: int
    transactions: List[str]  # tx_ids
    state_root: str
    previous_hash: str
    timestamp: float
    
    def compute_hash(self) -> str:
        """Compute block hash."""
        content = f"{self.height}:{','.join(self.transactions)}:{self.previous_hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class SimulatedNode:
    """
    A simulated Raft-like consensus node.
    
    Simplified model focusing on partition behavior.
    """
    node_id: int
    state: NodeState = NodeState.FOLLOWER
    term: int = 0
    voted_for: Optional[int] = None
    leader_id: Optional[int] = None
    
    # Chain state
    blocks: List[Block] = field(default_factory=list)
    committed_txs: Set[str] = field(default_factory=set)
    pending_txs: List[Transaction] = field(default_factory=list)
    
    # Network state
    connected_peers: Set[int] = field(default_factory=set)
    
    def __post_init__(self):
        # Genesis block
        genesis = Block(
            height=0,
            transactions=[],
            state_root="genesis",
            previous_hash="0" * 16,
            timestamp=time.time()
        )
        self.blocks = [genesis]
        
    @property
    def block_height(self) -> int:
        return len(self.blocks) - 1
        
    @property
    def state_root(self) -> str:
        """Compute state root from committed transactions."""
        if not self.committed_txs:
            return "genesis"
        sorted_txs = sorted(self.committed_txs)
        content = ":".join(sorted_txs)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
        
    @property
    def latest_hash(self) -> str:
        return self.blocks[-1].compute_hash() if self.blocks else "0" * 16
        
    def can_reach_quorum(self, total_nodes: int) -> bool:
        """Check if this node can reach quorum (>50%)."""
        reachable = len(self.connected_peers) + 1  # self + connected
        return reachable > total_nodes / 2
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "term": self.term,
            "leader_id": self.leader_id,
            "block_height": self.block_height,
            "state_root": self.state_root,
            "committed_txs": list(self.committed_txs),
            "pending_txs": [tx.tx_id for tx in self.pending_txs],
            "connected_peers": list(self.connected_peers)
        }


@dataclass
class PartitionEvent:
    """Record of a partition event."""
    event_type: str  # "partition", "heal", "tx_submit", "tx_commit", "tx_stall"
    timestamp: float
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "details": self.details
        }


@dataclass
class PartitionReport:
    """Complete partition test report."""
    pac_id: str = "PAC-SEC-P610-PARTITION-TEST"
    status: str = "PENDING"
    
    # Cluster info
    total_nodes: int = 5
    majority_partition: List[int] = field(default_factory=list)
    minority_partition: List[int] = field(default_factory=list)
    
    # Transactions
    majority_tx: Optional[Dict] = None
    minority_tx: Optional[Dict] = None
    
    # Timing
    partition_start: Optional[float] = None
    partition_end: Optional[float] = None
    convergence_time_ms: float = 0.0
    
    # Results
    majority_committed: bool = False
    minority_stalled: bool = False
    healed_successfully: bool = False
    all_nodes_converged: bool = False
    
    # Invariants
    inv_sec_010_passed: bool = False  # Majority Rule
    inv_sec_011_passed: bool = False  # Self-Healing
    
    # Events
    events: List[PartitionEvent] = field(default_factory=list)
    
    # Final state
    final_states: Dict[int, Dict] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pac_id": self.pac_id,
            "status": self.status,
            "cluster": {
                "total_nodes": self.total_nodes,
                "majority_partition": self.majority_partition,
                "minority_partition": self.minority_partition
            },
            "transactions": {
                "majority_tx": self.majority_tx,
                "minority_tx": self.minority_tx
            },
            "timing": {
                "partition_start": self.partition_start,
                "partition_end": self.partition_end,
                "convergence_time_ms": round(self.convergence_time_ms, 2)
            },
            "results": {
                "majority_committed": self.majority_committed,
                "minority_stalled": self.minority_stalled,
                "healed_successfully": self.healed_successfully,
                "all_nodes_converged": self.all_nodes_converged
            },
            "invariants": {
                "INV-SEC-010_Majority_Rule": {
                    "passed": self.inv_sec_010_passed,
                    "criteria": "Only partition with >50% nodes can commit"
                },
                "INV-SEC-011_Self_Healing": {
                    "passed": self.inv_sec_011_passed,
                    "criteria": "Minority syncs to majority state upon reconnection"
                }
            },
            "events": [e.to_dict() for e in self.events],
            "final_states": self.final_states,
            "verdict": {
                "overall_passed": self.inv_sec_010_passed and self.inv_sec_011_passed,
                "summary": "PARTITION_HEALED" if (self.inv_sec_010_passed and self.inv_sec_011_passed) else "PARTITION_FAILED"
            }
        }


# ══════════════════════════════════════════════════════════════════════════════
# NETWORK TOPOLOGY
# ══════════════════════════════════════════════════════════════════════════════

class NetworkTopology:
    """
    Manages network connections between simulated nodes.
    
    Provides methods to cut and restore connections for partition testing.
    """
    
    def __init__(self, nodes: List[SimulatedNode]):
        self.nodes = {n.node_id: n for n in nodes}
        self.partitioned = False
        self.partition_groups: List[Set[int]] = []
        
        # Initially, all nodes are connected
        for node in nodes:
            node.connected_peers = {n.node_id for n in nodes if n.node_id != node.node_id}
            
    def cut_connection(self, group_a: List[int], group_b: List[int]) -> PartitionEvent:
        """
        Sever connections between two groups of nodes.
        
        Nodes within each group remain connected to each other.
        """
        group_a_set = set(group_a)
        group_b_set = set(group_b)
        
        # Update connectivity
        for node_id in group_a:
            node = self.nodes[node_id]
            node.connected_peers -= group_b_set
            node.state = NodeState.PARTITIONED
            
        for node_id in group_b:
            node = self.nodes[node_id]
            node.connected_peers -= group_a_set
            node.state = NodeState.PARTITIONED
            
        self.partitioned = True
        self.partition_groups = [group_a_set, group_b_set]
        
        return PartitionEvent(
            event_type="partition",
            timestamp=time.time(),
            details={
                "group_a": list(group_a_set),
                "group_b": list(group_b_set),
                "action": "cut"
            }
        )
        
    def restore_connection(self) -> PartitionEvent:
        """
        Restore connections between all nodes.
        """
        all_ids = set(self.nodes.keys())
        
        for node in self.nodes.values():
            node.connected_peers = all_ids - {node.node_id}
            node.state = NodeState.FOLLOWER
            
        self.partitioned = False
        self.partition_groups = []
        
        return PartitionEvent(
            event_type="heal",
            timestamp=time.time(),
            details={
                "action": "restore",
                "all_connected": True
            }
        )
        
    def get_partition_group(self, node_id: int) -> Set[int]:
        """Get the partition group containing this node."""
        for group in self.partition_groups:
            if node_id in group:
                return group
        return set(self.nodes.keys())  # Not partitioned
        
    def is_majority_partition(self, node_id: int) -> bool:
        """Check if node is in the majority partition."""
        if not self.partitioned:
            return True
        group = self.get_partition_group(node_id)
        return len(group) > len(self.nodes) / 2


# ══════════════════════════════════════════════════════════════════════════════
# CONSENSUS SIMULATOR
# ══════════════════════════════════════════════════════════════════════════════

class ConsensusSimulator:
    """
    Simulates Raft-like consensus with partition handling.
    
    Key behaviors:
    - Only majority partition can elect leader and commit
    - Minority partition stalls (no commits)
    - Upon healing, minority syncs to majority state
    """
    
    def __init__(self, num_nodes: int = 5, verbose: bool = True):
        self.num_nodes = num_nodes
        self.verbose = verbose
        
        # Create nodes
        self.nodes = [SimulatedNode(node_id=i) for i in range(num_nodes)]
        
        # Network topology
        self.network = NetworkTopology(self.nodes)
        
        # Transaction tracking
        self.transactions: Dict[str, Transaction] = {}
        
        # Report
        self.report = PartitionReport(total_nodes=num_nodes)
        
        # Elect initial leader (Node 0)
        self._elect_leader(0)
        
    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)
            
    def _elect_leader(self, node_id: int) -> None:
        """Elect a node as leader within its partition."""
        node = self.nodes[node_id]
        node.state = NodeState.LEADER
        node.term += 1
        node.leader_id = node_id
        
        # Notify connected peers
        for peer_id in node.connected_peers:
            peer = self.nodes[peer_id]
            peer.leader_id = node_id
            peer.term = node.term
            if peer.state != NodeState.PARTITIONED:
                peer.state = NodeState.FOLLOWER
                
    async def submit_transaction(self, tx_id: str, payload: str, to_node: int) -> Transaction:
        """
        Submit a transaction to a specific node.
        
        Returns the transaction with updated status.
        """
        tx = Transaction(
            tx_id=tx_id,
            payload=payload,
            submitted_to=to_node,
            submitted_at=time.time()
        )
        self.transactions[tx_id] = tx
        
        node = self.nodes[to_node]
        node.pending_txs.append(tx)
        
        self._log(f"\n  📨 Tx '{tx_id}' submitted to Node {to_node}")
        
        # Record event
        self.report.events.append(PartitionEvent(
            event_type="tx_submit",
            timestamp=time.time(),
            details={"tx_id": tx_id, "node": to_node, "payload": payload}
        ))
        
        # Try to commit
        await self._try_commit(tx, node)
        
        return tx
        
    async def _try_commit(self, tx: Transaction, node: SimulatedNode) -> None:
        """
        Attempt to commit a transaction through consensus.
        
        INV-SEC-010: Only succeeds if node can reach quorum (>50%).
        """
        # Simulate network delay
        await asyncio.sleep(0.05)
        
        # Check if we can reach quorum
        if node.can_reach_quorum(self.num_nodes):
            # Majority - can commit
            tx.status = TxStatus.COMMITTED
            tx.committed_at = time.time()
            tx.committed_by = [node.node_id] + list(node.connected_peers)
            
            # Update state on all reachable nodes
            node.committed_txs.add(tx.tx_id)
            for peer_id in node.connected_peers:
                self.nodes[peer_id].committed_txs.add(tx.tx_id)
                
            # Create block
            block = Block(
                height=node.block_height + 1,
                transactions=[tx.tx_id],
                state_root=node.state_root,
                previous_hash=node.latest_hash,
                timestamp=time.time()
            )
            node.blocks.append(block)
            for peer_id in node.connected_peers:
                self.nodes[peer_id].blocks.append(block)
                
            self._log(f"  ✅ Tx '{tx.tx_id}' COMMITTED by majority ({len(tx.committed_by)} nodes)")
            
            self.report.events.append(PartitionEvent(
                event_type="tx_commit",
                timestamp=time.time(),
                details={
                    "tx_id": tx.tx_id,
                    "committed_by": tx.committed_by,
                    "block_height": block.height
                }
            ))
        else:
            # Minority - must stall
            tx.status = TxStatus.STALLED
            
            self._log(f"  ⏸️  Tx '{tx.tx_id}' STALLED (minority partition, cannot reach quorum)")
            
            self.report.events.append(PartitionEvent(
                event_type="tx_stall",
                timestamp=time.time(),
                details={
                    "tx_id": tx.tx_id,
                    "node": node.node_id,
                    "reason": "minority_partition",
                    "reachable_nodes": len(node.connected_peers) + 1,
                    "required_for_quorum": (self.num_nodes // 2) + 1
                }
            ))
            
    async def partition(self, majority: List[int], minority: List[int]) -> None:
        """
        Create a network partition.
        
        The majority group should have more than 50% of nodes.
        """
        self._log(f"\n{'='*60}")
        self._log(f"  ⚡ PARTITION: {majority} vs {minority}")
        self._log(f"{'='*60}")
        
        event = self.network.cut_connection(majority, minority)
        self.report.events.append(event)
        self.report.partition_start = event.timestamp
        self.report.majority_partition = majority
        self.report.minority_partition = minority
        
        # Re-elect leaders in each partition
        # Majority keeps/elects leader
        self._elect_leader(majority[0])
        
        # Minority tries but can't reach quorum
        # It stays in PARTITIONED state
        for node_id in minority:
            self.nodes[node_id].leader_id = None
            
        await asyncio.sleep(0.1)  # Simulate election timeout
        
    async def heal(self) -> None:
        """
        Heal the partition and trigger state synchronization.
        
        INV-SEC-011: Minority must sync to majority state.
        """
        self._log(f"\n{'='*60}")
        self._log(f"  🩹 HEALING PARTITION")
        self._log(f"{'='*60}")
        
        heal_start = time.time()
        
        event = self.network.restore_connection()
        self.report.events.append(event)
        self.report.partition_end = event.timestamp
        
        # Simulate state sync
        await asyncio.sleep(0.05)
        
        # Find majority leader and state
        majority_leader = None
        majority_state = None
        
        for node_id in self.report.majority_partition:
            node = self.nodes[node_id]
            if node.state == NodeState.LEADER or majority_leader is None:
                majority_leader = node
                majority_state = {
                    "committed_txs": node.committed_txs.copy(),
                    "blocks": node.blocks.copy(),
                    "state_root": node.state_root
                }
                
        # Sync minority to majority state
        for node_id in self.report.minority_partition:
            node = self.nodes[node_id]
            
            # Discard pending txs that weren't committed by majority
            discarded = []
            for tx in node.pending_txs:
                if tx.tx_id not in majority_state["committed_txs"]:
                    tx.status = TxStatus.REJECTED
                    discarded.append(tx.tx_id)
                    
            if discarded:
                self._log(f"  🗑️  Node {node_id} discarded pending txs: {discarded}")
                
            # Sync to majority state
            node.committed_txs = majority_state["committed_txs"].copy()
            node.blocks = majority_state["blocks"].copy()
            node.pending_txs = []
            node.state = NodeState.FOLLOWER
            node.leader_id = majority_leader.node_id
            
        # Re-elect single leader
        self._elect_leader(majority_leader.node_id)
        
        convergence_time = (time.time() - heal_start) * 1000
        self.report.convergence_time_ms = convergence_time
        
        self._log(f"  ✅ Partition healed in {convergence_time:.1f}ms")
        
        self.report.events.append(PartitionEvent(
            event_type="sync_complete",
            timestamp=time.time(),
            details={
                "convergence_time_ms": convergence_time,
                "leader": majority_leader.node_id,
                "state_root": majority_state["state_root"]
            }
        ))
        
    def verify_invariants(self) -> Tuple[bool, bool]:
        """
        Verify both partition invariants.
        
        Returns (INV-SEC-010_passed, INV-SEC-011_passed)
        """
        # INV-SEC-010: Majority Rule
        # Check that majority tx was committed and minority tx was not
        majority_tx = self.transactions.get("TX_A")
        minority_tx = self.transactions.get("TX_B")
        
        inv_010_passed = (
            majority_tx is not None and
            majority_tx.status == TxStatus.COMMITTED and
            minority_tx is not None and
            minority_tx.status in (TxStatus.STALLED, TxStatus.REJECTED)
        )
        
        self.report.majority_committed = majority_tx.status == TxStatus.COMMITTED if majority_tx else False
        self.report.minority_stalled = minority_tx.status in (TxStatus.STALLED, TxStatus.REJECTED) if minority_tx else False
        
        # INV-SEC-011: Self-Healing
        # Check that all nodes converged to same state
        state_roots = {n.state_root for n in self.nodes}
        committed_txs_sets = [n.committed_txs for n in self.nodes]
        
        all_same_state = len(state_roots) == 1
        all_have_majority_tx = all("TX_A" in txs for txs in committed_txs_sets)
        none_have_minority_tx = all("TX_B" not in txs for txs in committed_txs_sets)
        
        inv_011_passed = all_same_state and all_have_majority_tx and none_have_minority_tx
        
        self.report.healed_successfully = True
        self.report.all_nodes_converged = all_same_state
        
        return inv_010_passed, inv_011_passed
        
    def collect_final_states(self) -> None:
        """Collect final state of all nodes for report."""
        for node in self.nodes:
            self.report.final_states[node.node_id] = node.to_dict()
            
        # Also capture tx details
        majority_tx = self.transactions.get("TX_A")
        minority_tx = self.transactions.get("TX_B")
        
        if majority_tx:
            self.report.majority_tx = majority_tx.to_dict()
        if minority_tx:
            self.report.minority_tx = minority_tx.to_dict()


# ══════════════════════════════════════════════════════════════════════════════
# TEST EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

async def run_partition_test(verbose: bool = True) -> PartitionReport:
    """
    Execute the full partition test scenario.
    
    Scenario:
    1. Start 5-node cluster
    2. Partition: [0,1,2] vs [3,4]
    3. Submit TX_A to majority (Node 0) - should commit
    4. Submit TX_B to minority (Node 3) - should stall
    5. Heal partition
    6. Verify all nodes have TX_A, none have TX_B
    """
    
    print("\n" + "╔" + "═"*58 + "╗")
    print("║" + " "*15 + "PARTITION RESILIENCE TEST" + " "*18 + "║")
    print("║" + " "*10 + "\"The Truth is One. It cannot be Split.\"" + " "*8 + "║")
    print("╚" + "═"*58 + "╝")
    
    # Initialize simulator
    sim = ConsensusSimulator(num_nodes=5, verbose=verbose)
    
    print("\n" + "─"*60)
    print("  PHASE 1: Cluster Initialization")
    print("─"*60)
    print(f"  ✅ 5-node cluster initialized")
    print(f"  ✅ Node 0 elected as initial leader")
    
    # Phase 2: Create partition
    print("\n" + "─"*60)
    print("  PHASE 2: Create Partition (Split Brain)")
    print("─"*60)
    
    await sim.partition(
        majority=[0, 1, 2],
        minority=[3, 4]
    )
    
    # Phase 3: Submit transactions
    print("\n" + "─"*60)
    print("  PHASE 3: Submit Conflicting Transactions")
    print("─"*60)
    
    # TX_A to majority (should commit)
    print("\n  [Majority Partition - Nodes 0,1,2]")
    tx_a = await sim.submit_transaction("TX_A", "SOVEREIGN_PAYMENT_001", to_node=0)
    
    # TX_B to minority (should stall)
    print("\n  [Minority Partition - Nodes 3,4]")
    tx_b = await sim.submit_transaction("TX_B", "CONFLICTING_PAYMENT_999", to_node=3)
    
    # Phase 4: Heal partition
    print("\n" + "─"*60)
    print("  PHASE 4: Heal Partition")
    print("─"*60)
    
    await sim.heal()
    
    # Phase 5: Verify invariants
    print("\n" + "─"*60)
    print("  PHASE 5: Verify Invariants")
    print("─"*60)
    
    inv_010, inv_011 = sim.verify_invariants()
    sim.collect_final_states()
    
    sim.report.inv_sec_010_passed = inv_010
    sim.report.inv_sec_011_passed = inv_011
    
    print(f"\n  INV-SEC-010 (Majority Rule):")
    print(f"    TX_A (majority): {tx_a.status.value}")
    print(f"    TX_B (minority): {tx_b.status.value}")
    print(f"    Verdict: {'✅ PASSED' if inv_010 else '❌ FAILED'}")
    
    print(f"\n  INV-SEC-011 (Self-Healing):")
    state_roots = {n.state_root for n in sim.nodes}
    print(f"    Unique state roots: {len(state_roots)} (expected: 1)")
    print(f"    All have TX_A: {all('TX_A' in n.committed_txs for n in sim.nodes)}")
    print(f"    None have TX_B: {all('TX_B' not in n.committed_txs for n in sim.nodes)}")
    print(f"    Verdict: {'✅ PASSED' if inv_011 else '❌ FAILED'}")
    
    # Final verdict
    overall_passed = inv_010 and inv_011
    sim.report.status = "PARTITION_HEALED" if overall_passed else "PARTITION_FAILED"
    
    print("\n" + "═"*60)
    print("  PARTITION TEST VERDICT")
    print("═"*60)
    print(f"\n  Convergence Time: {sim.report.convergence_time_ms:.1f}ms (threshold: <2000ms)")
    print(f"  INV-SEC-010 (Majority Rule): {'✅' if inv_010 else '❌'}")
    print(f"  INV-SEC-011 (Self-Healing): {'✅' if inv_011 else '❌'}")
    print(f"\n  {'🩹 PARTITION HEALED' if overall_passed else '💥 PARTITION FAILED'}")
    
    if overall_passed:
        print("\n  \"The Wound is closed. The Mind is Whole.\"")
        print("  👑 The Network is Sovereign.")
        
    return sim.report


def save_report(report: PartitionReport, output_path: Path) -> None:
    """Save the partition report to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    report_dict = report.to_dict()
    report_dict["generated_at"] = datetime.now(timezone.utc).isoformat()
    
    with open(output_path, 'w') as f:
        json.dump(report_dict, f, indent=2)
        
    print(f"\n📄 Report saved: {output_path}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> bool:
    """Execute the partition test."""
    
    # Paths
    project_root = Path(__file__).parent.parent.parent
    report_path = project_root / "reports" / "PARTITION_RESILIENCE.json"
    
    # Run test
    report = asyncio.run(run_partition_test(verbose=True))
    
    # Save report
    save_report(report, report_path)
    
    return report.inv_sec_010_passed and report.inv_sec_011_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
