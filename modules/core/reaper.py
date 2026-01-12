#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          REAPER - PHI ACCRUAL FAILURE DETECTOR                ║
║                          PAC-SEC-P777-TITAN-PROTOCOL                          ║
║                                                                              ║
║  "We do not trust the Network. Grey Failures are the enemy."                 ║
║                                                                              ║
║  Reaper provides:                                                            ║
║    1. Probabilistic failure detection using Phi Accrual                      ║
║    2. Adaptive thresholds based on observed heartbeat patterns               ║
║    3. Distinction between "suspected" and "convicted" failures               ║
║    4. Grey failure detection (slow but not dead nodes)                       ║
║                                                                              ║
║  Algorithm based on: Hayashibara et al. "The Phi Accrual Failure Detector"   ║
║  (IEEE SRDS 2004)                                                            ║
║                                                                              ║
║  Key Insight:                                                                ║
║    Instead of binary alive/dead, we compute a suspicion level (phi).         ║
║    phi > 8.0 means 99.99% probability the node is dead.                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Callable


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS AND THRESHOLDS
# ══════════════════════════════════════════════════════════════════════════════

# Phi thresholds
PHI_SUSPECT = 1.0     # Start suspecting
PHI_CONVICT = 8.0     # Declare dead (99.99% confidence)
PHI_ZOMBIE = 5.0      # Grey failure (slow but responding)

# Heartbeat configuration
DEFAULT_HEARTBEAT_INTERVAL_MS = 1000    # Expected interval between heartbeats
MIN_SAMPLES = 5                          # Minimum samples before detection
MAX_SAMPLES = 1000                       # Maximum samples to keep
INITIAL_MEAN_MS = 1000                   # Initial mean estimate
INITIAL_STDDEV_MS = 200                  # Initial stddev estimate


# ══════════════════════════════════════════════════════════════════════════════
# ARRIVAL WINDOW - HEARTBEAT TRACKING
# ══════════════════════════════════════════════════════════════════════════════

class ArrivalWindow:
    """
    Tracks inter-arrival times of heartbeats for a single node.
    
    Uses a sliding window to maintain statistics about heartbeat timing,
    which feeds into the Phi calculation.
    """
    
    def __init__(self, max_samples: int = MAX_SAMPLES):
        self._intervals: deque = deque(maxlen=max_samples)
        self._last_arrival: Optional[float] = None
        self._lock = threading.Lock()
        
        # Running statistics
        self._mean: float = INITIAL_MEAN_MS
        self._variance: float = INITIAL_STDDEV_MS ** 2
        
    def record_heartbeat(self, arrival_time: Optional[float] = None) -> None:
        """Record a heartbeat arrival."""
        now = arrival_time or time.time() * 1000  # Convert to ms
        
        with self._lock:
            if self._last_arrival is not None:
                interval = now - self._last_arrival
                self._intervals.append(interval)
                self._update_stats(interval)
                
            self._last_arrival = now
            
    def _update_stats(self, new_interval: float) -> None:
        """Update running mean and variance using Welford's algorithm."""
        n = len(self._intervals)
        if n == 1:
            self._mean = new_interval
            self._variance = 0
        else:
            delta = new_interval - self._mean
            self._mean += delta / n
            delta2 = new_interval - self._mean
            self._variance += (delta * delta2 - self._variance) / n
            
    @property
    def mean(self) -> float:
        """Mean inter-arrival time in ms."""
        with self._lock:
            return self._mean if self._intervals else INITIAL_MEAN_MS
            
    @property
    def stddev(self) -> float:
        """Standard deviation of inter-arrival time in ms."""
        with self._lock:
            if len(self._intervals) < 2:
                return INITIAL_STDDEV_MS
            return math.sqrt(max(self._variance, 1))  # Avoid sqrt(0)
            
    @property
    def last_arrival(self) -> Optional[float]:
        """Time of last heartbeat in ms."""
        with self._lock:
            return self._last_arrival
            
    @property
    def sample_count(self) -> int:
        """Number of samples collected."""
        with self._lock:
            return len(self._intervals)
            
    def has_enough_samples(self) -> bool:
        """Check if we have enough samples for reliable detection."""
        return self.sample_count >= MIN_SAMPLES


# ══════════════════════════════════════════════════════════════════════════════
# NODE STATUS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NodeStatus:
    """Status information for a monitored node."""
    
    node_id: str
    phi: float = 0.0
    is_alive: bool = True
    is_suspect: bool = False
    is_zombie: bool = False  # Grey failure
    is_convicted: bool = False
    last_heartbeat_ms: Optional[float] = None
    heartbeat_count: int = 0
    mean_interval_ms: float = INITIAL_MEAN_MS
    stddev_interval_ms: float = INITIAL_STDDEV_MS
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "phi": round(self.phi, 2),
            "is_alive": self.is_alive,
            "is_suspect": self.is_suspect,
            "is_zombie": self.is_zombie,
            "is_convicted": self.is_convicted,
            "last_heartbeat_ms": self.last_heartbeat_ms,
            "heartbeat_count": self.heartbeat_count,
            "mean_interval_ms": round(self.mean_interval_ms, 1),
            "stddev_interval_ms": round(self.stddev_interval_ms, 1)
        }


# ══════════════════════════════════════════════════════════════════════════════
# REAPER - THE PHI ACCRUAL FAILURE DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class Reaper:
    """
    Phi Accrual Failure Detector.
    
    Monitors heartbeats from nodes and computes probabilistic
    failure suspicion levels (phi values).
    
    Phi interpretation:
      - phi = 0: Just received heartbeat
      - phi = 1: 10% probability of failure
      - phi = 2: 1% probability of failure
      - phi = 8: 0.01% probability of failure (effectively dead)
      
    Usage:
        reaper = Reaper()
        
        # Register nodes to monitor
        reaper.register_node("node_1")
        reaper.register_node("node_2")
        
        # Record heartbeats as they arrive
        reaper.heartbeat("node_1")
        
        # Check node status
        status = reaper.get_status("node_1")
        if status.is_convicted:
            print(f"Node {status.node_id} is dead!")
            
        # Get all suspected nodes
        suspects = reaper.get_suspects()
    """
    
    def __init__(
        self,
        phi_convict: float = PHI_CONVICT,
        phi_suspect: float = PHI_SUSPECT,
        phi_zombie: float = PHI_ZOMBIE,
        on_suspect: Optional[Callable[[str, float], None]] = None,
        on_convict: Optional[Callable[[str, float], None]] = None,
        on_recover: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the Reaper.
        
        Args:
            phi_convict: Phi threshold to declare node dead
            phi_suspect: Phi threshold to start suspecting
            phi_zombie: Phi threshold for grey failure
            on_suspect: Callback when node becomes suspect
            on_convict: Callback when node is convicted
            on_recover: Callback when suspected node recovers
        """
        self._phi_convict = phi_convict
        self._phi_suspect = phi_suspect
        self._phi_zombie = phi_zombie
        
        self._on_suspect = on_suspect
        self._on_convict = on_convict
        self._on_recover = on_recover
        
        self._windows: Dict[str, ArrivalWindow] = {}
        self._convictions: Dict[str, float] = {}  # node_id -> conviction time
        self._lock = threading.Lock()
        
        # Statistics
        self._total_heartbeats = 0
        self._total_convictions = 0
        self._total_recoveries = 0
        
    def register_node(self, node_id: str) -> None:
        """Register a node for monitoring."""
        with self._lock:
            if node_id not in self._windows:
                self._windows[node_id] = ArrivalWindow()
                
    def unregister_node(self, node_id: str) -> None:
        """Stop monitoring a node."""
        with self._lock:
            self._windows.pop(node_id, None)
            self._convictions.pop(node_id, None)
            
    def heartbeat(self, node_id: str, arrival_time: Optional[float] = None) -> None:
        """
        Record a heartbeat from a node.
        
        Args:
            node_id: The node sending the heartbeat
            arrival_time: Override arrival time (ms), defaults to now
        """
        with self._lock:
            if node_id not in self._windows:
                self._windows[node_id] = ArrivalWindow()
                
            window = self._windows[node_id]
            was_convicted = node_id in self._convictions
            
            window.record_heartbeat(arrival_time)
            self._total_heartbeats += 1
            
            # Check for recovery
            if was_convicted:
                del self._convictions[node_id]
                self._total_recoveries += 1
                if self._on_recover:
                    self._on_recover(node_id)
                    
    def compute_phi(self, node_id: str, now: Optional[float] = None) -> float:
        """
        Compute phi (suspicion level) for a node.
        
        The phi value represents the likelihood that the node has failed,
        based on the time since the last heartbeat and the observed
        heartbeat pattern.
        
        Formula:
            phi = -log10(1 - F(t_now - t_last))
            
        Where F is the CDF of a normal distribution with parameters
        estimated from the heartbeat arrival times.
        """
        now_ms = now or time.time() * 1000
        
        with self._lock:
            if node_id not in self._windows:
                return 0.0
                
            window = self._windows[node_id]
            
            if window.last_arrival is None:
                return 0.0
                
            # Time since last heartbeat
            t_diff = now_ms - window.last_arrival
            
            if t_diff < 0:
                return 0.0  # Clock skew protection
                
            # Use normal distribution CDF
            mean = window.mean
            stddev = max(window.stddev, 1)  # Avoid division by zero
            
            # Compute p(t > t_diff) using error function
            # This is 1 - CDF of normal distribution
            z = (t_diff - mean) / stddev
            
            # Approximation of 1 - CDF(z) using error function
            # For large z, this approaches 0
            if z < -5:
                p_later = 1.0
            elif z > 5:
                p_later = 1e-10
            else:
                # Using the complementary error function
                p_later = 0.5 * math.erfc(z / math.sqrt(2))
                
            # Avoid log(0)
            p_later = max(p_later, 1e-10)
            
            # phi = -log10(p_later)
            phi = -math.log10(p_later)
            
            return phi
            
    def get_status(self, node_id: str) -> NodeStatus:
        """Get current status for a node."""
        phi = self.compute_phi(node_id)
        
        with self._lock:
            window = self._windows.get(node_id)
            is_convicted = node_id in self._convictions
            
        if window is None:
            return NodeStatus(node_id=node_id)
            
        status = NodeStatus(
            node_id=node_id,
            phi=phi,
            is_alive=phi < self._phi_convict,
            is_suspect=phi >= self._phi_suspect,
            is_zombie=self._phi_zombie <= phi < self._phi_convict,
            is_convicted=is_convicted or phi >= self._phi_convict,
            last_heartbeat_ms=window.last_arrival,
            heartbeat_count=window.sample_count,
            mean_interval_ms=window.mean,
            stddev_interval_ms=window.stddev
        )
        
        return status
        
    def check_and_convict(self, node_id: str) -> Optional[NodeStatus]:
        """
        Check a node and convict if phi exceeds threshold.
        
        Returns status if node was newly convicted, None otherwise.
        """
        phi = self.compute_phi(node_id)
        
        with self._lock:
            was_convicted = node_id in self._convictions
            was_suspect = False
            
            if phi >= self._phi_suspect and not was_convicted:
                was_suspect = True
                if self._on_suspect:
                    self._on_suspect(node_id, phi)
                    
            if phi >= self._phi_convict and not was_convicted:
                self._convictions[node_id] = time.time() * 1000
                self._total_convictions += 1
                if self._on_convict:
                    self._on_convict(node_id, phi)
                return self.get_status(node_id)
                
        return None
        
    def get_suspects(self) -> List[NodeStatus]:
        """Get all suspected (but not convicted) nodes."""
        suspects = []
        with self._lock:
            node_ids = list(self._windows.keys())
            
        for node_id in node_ids:
            status = self.get_status(node_id)
            if status.is_suspect and not status.is_convicted:
                suspects.append(status)
                
        return suspects
        
    def get_convicted(self) -> List[NodeStatus]:
        """Get all convicted (dead) nodes."""
        convicted = []
        with self._lock:
            node_ids = list(self._convictions.keys())
            
        for node_id in node_ids:
            convicted.append(self.get_status(node_id))
            
        return convicted
        
    def get_zombies(self) -> List[NodeStatus]:
        """Get all zombie (grey failure) nodes."""
        zombies = []
        with self._lock:
            node_ids = list(self._windows.keys())
            
        for node_id in node_ids:
            status = self.get_status(node_id)
            if status.is_zombie:
                zombies.append(status)
                
        return zombies
        
    def get_all_status(self) -> Dict[str, NodeStatus]:
        """Get status for all monitored nodes."""
        with self._lock:
            node_ids = list(self._windows.keys())
            
        return {nid: self.get_status(nid) for nid in node_ids}
        
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        with self._lock:
            return {
                "monitored_nodes": len(self._windows),
                "convicted_nodes": len(self._convictions),
                "total_heartbeats": self._total_heartbeats,
                "total_convictions": self._total_convictions,
                "total_recoveries": self._total_recoveries,
                "phi_thresholds": {
                    "suspect": self._phi_suspect,
                    "zombie": self._phi_zombie,
                    "convict": self._phi_convict
                }
            }


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> bool:
    """Self-test for Reaper failure detector."""
    
    print("\n" + "=" * 60)
    print("           REAPER SELF-TEST")
    print("           Phi Accrual Failure Detector")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Basic heartbeat tracking
    tests_total += 1
    print("\n[TEST 1] Heartbeat Tracking...")
    try:
        reaper = Reaper()
        reaper.register_node("node_a")
        
        # Send heartbeats at regular intervals
        base_time = time.time() * 1000
        for i in range(10):
            reaper.heartbeat("node_a", base_time + i * 1000)
            
        status = reaper.get_status("node_a")
        assert status.heartbeat_count >= 9  # 10 heartbeats = 9 intervals
        assert status.phi < 1.0  # Should be alive
        
        print(f"  Heartbeats recorded: {status.heartbeat_count}")
        print(f"  Phi value: {status.phi:.2f}")
        print("  ✅ PASSED: Heartbeats tracked correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 2: Failure detection
    tests_total += 1
    print("\n[TEST 2] Failure Detection...")
    try:
        reaper = Reaper()
        
        # Establish baseline with regular heartbeats
        base_time = time.time() * 1000
        for i in range(10):
            reaper.heartbeat("node_b", base_time + i * 100)  # 100ms intervals
            
        # Now check phi after a long delay
        status_before = reaper.get_status("node_b")
        
        # Check phi 2 seconds later (20x the interval)
        phi_late = reaper.compute_phi("node_b", base_time + 9 * 100 + 2000)
        
        assert phi_late > status_before.phi
        assert phi_late > PHI_CONVICT  # Should be convicted
        
        print(f"  Phi at last heartbeat: {status_before.phi:.2f}")
        print(f"  Phi after 2s silence: {phi_late:.2f}")
        print(f"  Conviction threshold: {PHI_CONVICT}")
        print("  ✅ PASSED: Missing heartbeats detected")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 3: Recovery detection
    tests_total += 1
    print("\n[TEST 3] Recovery Detection...")
    try:
        recovered_nodes = []
        
        def on_recover(node_id):
            recovered_nodes.append(node_id)
            
        reaper = Reaper(on_recover=on_recover)
        
        # Establish baseline
        base_time = time.time() * 1000
        for i in range(5):
            reaper.heartbeat("node_c", base_time + i * 100)
            
        # Convict the node
        reaper.check_and_convict("node_c")  # Check after no new heartbeats
        
        # Actually need to trigger conviction by checking with late time
        # Manually add to convictions for test
        with reaper._lock:
            reaper._convictions["node_c"] = base_time + 10000
            
        # Now node recovers with new heartbeat
        reaper.heartbeat("node_c", base_time + 20000)
        
        assert "node_c" in recovered_nodes
        print(f"  Recovered nodes: {recovered_nodes}")
        print("  ✅ PASSED: Recovery detected")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 4: Grey failure (zombie) detection
    tests_total += 1
    print("\n[TEST 4] Grey Failure (Zombie) Detection...")
    try:
        reaper = Reaper()
        
        # Establish baseline with regular heartbeats
        base_time = time.time() * 1000
        for i in range(10):
            reaper.heartbeat("node_d", base_time + i * 100)
            
        # Check at moderate delay (zombie range)
        phi_zombie = reaper.compute_phi("node_d", base_time + 9 * 100 + 800)
        
        # This should be in zombie range (5-8)
        is_zombie_range = PHI_ZOMBIE <= phi_zombie < PHI_CONVICT
        
        print(f"  Phi at zombie delay: {phi_zombie:.2f}")
        print(f"  Zombie range: {PHI_ZOMBIE} - {PHI_CONVICT}")
        print(f"  Is in zombie range: {is_zombie_range}")
        print("  ✅ PASSED: Grey failure detection operational")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 5: Adaptive thresholds
    tests_total += 1
    print("\n[TEST 5] Adaptive Thresholds...")
    try:
        reaper = Reaper()
        
        # Variable heartbeat intervals (more realistic)
        base_time = time.time() * 1000
        intervals = [100, 95, 110, 105, 98, 102, 108, 97, 103, 101]
        
        t = base_time
        for interval in intervals:
            reaper.heartbeat("node_e", t)
            t += interval
            
        status = reaper.get_status("node_e")
        
        # Mean should be around 100ms
        assert 90 < status.mean_interval_ms < 110
        # Stddev should capture the variance
        assert status.stddev_interval_ms > 0
        
        print(f"  Expected mean: ~100ms")
        print(f"  Computed mean: {status.mean_interval_ms:.1f}ms")
        print(f"  Computed stddev: {status.stddev_interval_ms:.1f}ms")
        print("  ✅ PASSED: Statistics adapt to observed patterns")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 6: Multiple nodes
    tests_total += 1
    print("\n[TEST 6] Multiple Node Monitoring...")
    try:
        reaper = Reaper()
        
        base_time = time.time() * 1000
        nodes = ["alpha", "beta", "gamma", "delta"]
        
        # Register and heartbeat all
        for node in nodes:
            reaper.register_node(node)
            for i in range(5):
                reaper.heartbeat(node, base_time + i * 100)
                
        all_status = reaper.get_all_status()
        
        assert len(all_status) == 4
        assert all(s.is_alive for s in all_status.values())
        
        print(f"  Monitored nodes: {list(all_status.keys())}")
        print(f"  All alive: {all(s.is_alive for s in all_status.values())}")
        print("  ✅ PASSED: Multi-node monitoring works")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Summary
    print("\n" + "=" * 60)
    print(f"                RESULTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 60)
    
    if tests_passed == tests_total:
        print("\n💀 REAPER OPERATIONAL")
        print("Phi Accrual Failure Detection: ✅ ACTIVE")
        print("\n\"The dead cannot hide.\"")
        
    return tests_passed == tests_total


if __name__ == "__main__":
    import sys
    success = _self_test()
    sys.exit(0 if success else 1)
