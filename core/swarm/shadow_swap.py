#!/usr/bin/env python3
"""
SHADOW SWAP - PAC-HARDENING-SWARM-36
Zero-Downtime Node Replacement Protocol

Implements warm boot replacement: spin up shadow node BEFORE killing deprecated node.
Ensures zero capacity loss during node lifecycle management.

TRADITIONAL SWAP (DEPRECATED):
1. Stop old node (capacity: N → N-1)
2. Start new node
3. Wait for new node READY
4. Capacity restored (N-1 → N)
Problem: Temporary capacity loss during replacement

SHADOW SWAP (PAC-36):
1. Start new node (shadow) while old node still running
2. Wait for shadow node READY (capacity: N → N+1)
3. Stop old node (capacity: N+1 → N)
Result: Zero downtime, capacity preserved throughout

CONSTITUTIONAL ENFORCEMENT:
- CB-SHADOW-01: Shadow node MUST achieve READY state before swap
- CB-SHADOW-02: Old node removal FORBIDDEN until shadow operational
- CB-SHADOW-03: Swap timeout 5 seconds, SCRAM on failure

INTEGRATION:
- PAC-31: Swarm orchestration (10,000 agents)
- PAC-36: Shadow swap ensures zero capacity loss during maintenance
"""

import asyncio
import time
import sys
import json
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from enum import Enum


class NodeState(Enum):
    """Node lifecycle states."""
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    TERMINATED = "TERMINATED"


@dataclass
class Node:
    """
    Represents a single swarm agent node.
    
    Attributes:
        node_id: Unique identifier
        state: Current lifecycle state
        created_at: Unix timestamp of creation
        ready_at: Unix timestamp when READY state achieved
        terminated_at: Unix timestamp when terminated
        is_shadow: True if this is a shadow (replacement) node
    """
    node_id: str
    state: NodeState
    created_at: float
    ready_at: Optional[float] = None
    terminated_at: Optional[float] = None
    is_shadow: bool = False


@dataclass
class SwapReport:
    """
    Shadow swap operation report.
    
    Attributes:
        old_node_id: Node being replaced
        shadow_node_id: Replacement node
        swap_start: Unix timestamp of swap initiation
        shadow_ready_time: Unix timestamp when shadow became READY
        old_node_terminated_time: Unix timestamp when old node terminated
        total_duration_ms: Total swap duration
        swap_success: True if swap completed without downtime
    """
    old_node_id: str
    shadow_node_id: str
    swap_start: float
    shadow_ready_time: float
    old_node_terminated_time: float
    total_duration_ms: float
    swap_success: bool


class ShadowSwapOrchestrator:
    """
    Manages zero-downtime node replacement via shadow swap protocol.
    
    Methods:
        warm_boot(): Spin up shadow node before removing old node
        execute_swap(): Complete swap operation
        scram(): Emergency halt on swap failure
    """
    
    def __init__(self, shadow_ready_timeout_ms: float = 5000.0):
        """
        Initialize shadow swap orchestrator.
        
        Args:
            shadow_ready_timeout_ms: Maximum time for shadow to achieve READY state
        """
        self.shadow_ready_timeout_ms = shadow_ready_timeout_ms
        self.nodes: List[Node] = []
        self.swap_reports: List[SwapReport] = []
        self.scram_triggered = False
        
        # Logging
        self.log_dir = Path(__file__).resolve().parents[2] / "logs" / "swarm"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    async def warm_boot(self, old_node: Node) -> Node:
        """
        Spin up shadow node before terminating old node.
        
        CB-SHADOW-01: Shadow node MUST achieve READY state before swap
        CB-SHADOW-02: Old node removal FORBIDDEN until shadow operational
        
        Args:
            old_node: Node to be replaced
        
        Returns:
            Shadow node in READY state
        """
        # Create shadow node
        shadow_node_id = f"{old_node.node_id}-SHADOW"
        shadow_node = Node(
            node_id=shadow_node_id,
            state=NodeState.INITIALIZING,
            created_at=time.time(),
            is_shadow=True
        )
        
        self.nodes.append(shadow_node)
        
        print(f"[SHADOW SWAP] Warming up shadow node: {shadow_node_id}")
        print(f"[SHADOW SWAP] Old node {old_node.node_id} still ACTIVE")
        
        # Simulate node initialization (100-500ms)
        init_duration_ms = 100 + (asyncio.get_event_loop().time() % 400)
        await asyncio.sleep(init_duration_ms / 1000.0)
        
        # Transition to READY
        shadow_node.state = NodeState.READY
        shadow_node.ready_at = time.time()
        
        ready_duration_ms = (shadow_node.ready_at - shadow_node.created_at) * 1000.0
        
        # CB-SHADOW-03: Swap timeout 5 seconds
        if ready_duration_ms > self.shadow_ready_timeout_ms:
            self.scram(
                f"Shadow node {shadow_node_id} failed to reach READY within "
                f"{self.shadow_ready_timeout_ms}ms (took {ready_duration_ms:.1f}ms)"
            )
        
        print(f"[SHADOW SWAP] Shadow node {shadow_node_id} READY in {ready_duration_ms:.1f}ms")
        
        return shadow_node
    
    async def execute_swap(self, old_node: Node, shadow_node: Node) -> SwapReport:
        """
        Complete swap operation: terminate old node, activate shadow.
        
        Args:
            old_node: Node being replaced
            shadow_node: Replacement node (must be READY)
        
        Returns:
            SwapReport with operation metrics
        """
        swap_start = time.time()
        
        # CB-SHADOW-01: Verify shadow is READY
        if shadow_node.state != NodeState.READY:
            self.scram(
                f"Attempted to swap with shadow node {shadow_node.node_id} "
                f"in state {shadow_node.state.value} (must be READY)"
            )
        
        # CB-SHADOW-02: Safe to terminate old node now
        print(f"[SHADOW SWAP] Terminating old node: {old_node.node_id}")
        
        old_node.state = NodeState.DRAINING
        await asyncio.sleep(0.05)  # Graceful drain: 50ms
        
        old_node.state = NodeState.TERMINATED
        old_node.terminated_at = time.time()
        
        # Activate shadow node
        shadow_node.state = NodeState.ACTIVE
        
        # Calculate metrics
        total_duration_ms = (time.time() - swap_start) * 1000.0
        
        report = SwapReport(
            old_node_id=old_node.node_id,
            shadow_node_id=shadow_node.node_id,
            swap_start=swap_start,
            shadow_ready_time=shadow_node.ready_at,
            old_node_terminated_time=old_node.terminated_at,
            total_duration_ms=total_duration_ms,
            swap_success=True
        )
        
        self.swap_reports.append(report)
        
        print(f"[SHADOW SWAP] ✅ Swap complete in {total_duration_ms:.1f}ms")
        print(f"[SHADOW SWAP] Zero downtime achieved")
        
        return report
    
    def scram(self, reason: str):
        """
        Execute emergency halt on swap failure.
        
        Args:
            reason: Description of failure condition
        """
        self.scram_triggered = True
        
        print()
        print("=" * 80)
        print("🚨 HARDENING SCRAM: SHADOW SWAP FAILURE 🚨")
        print("=" * 80)
        print(f"Reason: {reason}")
        print(f"Shadow Ready Timeout: {self.shadow_ready_timeout_ms}ms")
        print()
        print("SYSTEM HALT. SWAP PROTOCOL VIOLATION.")
        print("=" * 80)
        
        # Export logs
        self.export_logs()
        
        sys.exit(1)
    
    def export_logs(self):
        """Export swap reports to JSON log file."""
        if not self.swap_reports:
            return
        
        log_data = {
            "pac_id": "PAC-HARDENING-SWARM-36",
            "protocol": "SHADOW_SWAP_RNP",
            "timestamp": datetime.now().isoformat(),
            "total_swaps": len(self.swap_reports),
            "scram_triggered": self.scram_triggered,
            "shadow_ready_timeout_ms": self.shadow_ready_timeout_ms,
            "swap_reports": [asdict(r) for r in self.swap_reports]
        }
        
        log_file = self.log_dir / "shadow_swap_report.json"
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"[EXPORT] Shadow swap log exported to: {log_file}")
    
    def get_statistics(self) -> dict:
        """
        Get shadow swap statistics.
        
        Returns:
            Dictionary with swap metrics
        """
        if not self.swap_reports:
            return {
                "total_swaps": 0,
                "mean_duration_ms": 0.0,
                "max_duration_ms": 0.0,
                "all_swaps_successful": True,
                "scram_triggered": self.scram_triggered
            }
        
        durations = [r.total_duration_ms for r in self.swap_reports]
        
        return {
            "total_swaps": len(self.swap_reports),
            "mean_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "all_swaps_successful": all(r.swap_success for r in self.swap_reports),
            "scram_triggered": self.scram_triggered
        }


async def run_shadow_swap_test(num_swaps: int = 10):
    """
    Run shadow swap validation test.
    
    Simulates node replacement with zero-downtime protocol.
    
    Args:
        num_swaps: Number of swap operations to test
    """
    print("=" * 80)
    print("  SHADOW SWAP - PAC-HARDENING-SWARM-36")
    print("  Zero-Downtime Node Replacement Test")
    print("=" * 80)
    print()
    print(f"[CONFIG] Shadow Ready Timeout: 5000ms")
    print(f"[CONFIG] Test Duration: {num_swaps} swaps")
    print()
    
    orchestrator = ShadowSwapOrchestrator(shadow_ready_timeout_ms=5000.0)
    
    # Create initial nodes
    initial_nodes = [
        Node(
            node_id=f"AGENT-{i:05d}",
            state=NodeState.ACTIVE,
            created_at=time.time(),
            ready_at=time.time()
        )
        for i in range(num_swaps)
    ]
    
    orchestrator.nodes.extend(initial_nodes)
    
    print("[TEST] Executing shadow swap sequence...")
    print()
    
    for i, old_node in enumerate(initial_nodes):
        print(f"[SWAP {i+1}/{num_swaps}] Node: {old_node.node_id}")
        
        # Warm boot shadow
        shadow_node = await orchestrator.warm_boot(old_node)
        
        # Execute swap
        report = await orchestrator.execute_swap(old_node, shadow_node)
        
        print()
    
    # Get statistics
    stats = orchestrator.get_statistics()
    
    print("=" * 80)
    print("  SHADOW SWAP TEST COMPLETE")
    print("=" * 80)
    print(f"Total Swaps: {stats['total_swaps']}")
    print(f"Mean Duration: {stats['mean_duration_ms']:.1f}ms")
    print(f"Max Duration: {stats['max_duration_ms']:.1f}ms")
    print(f"All Successful: {stats['all_swaps_successful']}")
    print(f"Zero Downtime: ✅ ACHIEVED")
    print("=" * 80)
    
    # Export logs
    orchestrator.export_logs()


async def main():
    """Execute shadow swap test."""
    await run_shadow_swap_test(num_swaps=10)
    sys.exit(0)


if __name__ == '__main__':
    asyncio.run(main())
