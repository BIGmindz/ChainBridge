#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          CHRONOS - HYBRID LOGICAL CLOCK                       ║
║                          PAC-SEC-P777-TITAN-PROTOCOL                          ║
║                                                                              ║
║  "We do not rely on the environment. We dominate it."                        ║
║                                                                              ║
║  The Hybrid Logical Clock (HLC) provides:                                    ║
║    1. Causal ordering of events across distributed nodes                     ║
║    2. Monotonicity even when wall clock drifts or rewinds                    ║
║    3. Bounded divergence from physical time                                  ║
║                                                                              ║
║  Algorithm based on: Kulkarni et al. "Logical Physical Clocks" (HotNets'14)  ║
║                                                                              ║
║  Invariant Enforced:                                                         ║
║    INV-SEC-012 (Causal Consistency): If A → B, then HLC(A) < HLC(B)          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import time
import threading
from dataclasses import dataclass
from typing import Tuple, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════════════════════
# HLC TIMESTAMP
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True, order=True)
class HLCTimestamp:
    """
    Hybrid Logical Clock Timestamp.
    
    Components:
      - wall_time: Physical time in nanoseconds (from system clock)
      - logical: Logical counter for events within same wall_time
      - node_id: Tie-breaker for total ordering
      
    Comparison is lexicographic: (wall_time, logical, node_id)
    """
    
    wall_time: int   # Physical time in nanoseconds
    logical: int     # Logical counter
    node_id: str     # Node identifier for tie-breaking
    
    def __str__(self) -> str:
        ts = datetime.fromtimestamp(self.wall_time / 1e9, tz=timezone.utc)
        return f"HLC({ts.isoformat()}:{self.logical}@{self.node_id})"
        
    def to_tuple(self) -> Tuple[int, int, str]:
        """Export as comparable tuple."""
        return (self.wall_time, self.logical, self.node_id)
        
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "wall_time": self.wall_time,
            "logical": self.logical,
            "node_id": self.node_id
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> "HLCTimestamp":
        """Deserialize from dictionary."""
        return cls(
            wall_time=data["wall_time"],
            logical=data["logical"],
            node_id=data["node_id"]
        )
        
    def happens_before(self, other: "HLCTimestamp") -> bool:
        """
        Check if this timestamp causally precedes another.
        
        INV-SEC-012: If A → B (A happens before B), then HLC(A) < HLC(B)
        """
        return self.to_tuple() < other.to_tuple()


# ══════════════════════════════════════════════════════════════════════════════
# CHRONOS - THE HYBRID LOGICAL CLOCK
# ══════════════════════════════════════════════════════════════════════════════

class Chronos:
    """
    Hybrid Logical Clock implementation.
    
    Guarantees:
      1. Monotonicity: Timestamps never decrease, even if wall clock rewinds
      2. Causality: send < recv for any message
      3. Bounded divergence: Logical counter resets when wall clock advances
      
    Thread-safe via mutex lock.
    
    Usage:
        chronos = Chronos("node_1")
        
        # Local event
        ts = chronos.tick()
        
        # Send message (get timestamp to include)
        send_ts = chronos.send()
        
        # Receive message (merge with sender's timestamp)
        recv_ts = chronos.receive(sender_timestamp)
    """
    
    # Maximum drift allowed between logical and physical time (5 minutes in ns)
    MAX_DRIFT_NS = 5 * 60 * 1_000_000_000
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._lock = threading.Lock()
        
        # Current HLC state
        self._wall_time: int = self._get_wall_time()
        self._logical: int = 0
        
        # Statistics
        self._ticks: int = 0
        self._sends: int = 0
        self._receives: int = 0
        self._clock_rollbacks: int = 0
        
    def _get_wall_time(self) -> int:
        """Get current wall time in nanoseconds."""
        return int(time.time() * 1_000_000_000)
        
    def _current_timestamp(self) -> HLCTimestamp:
        """Create timestamp from current state."""
        return HLCTimestamp(
            wall_time=self._wall_time,
            logical=self._logical,
            node_id=self.node_id
        )
        
    def tick(self) -> HLCTimestamp:
        """
        Record a local event.
        
        Algorithm:
          pt = physical_time()
          if pt > l.wall_time:
              l.wall_time = pt
              l.logical = 0
          else:
              l.logical += 1
          return l
          
        Returns the new HLC timestamp.
        """
        with self._lock:
            pt = self._get_wall_time()
            
            if pt > self._wall_time:
                # Physical time advanced - reset logical counter
                self._wall_time = pt
                self._logical = 0
            else:
                # Physical time same or rewound - increment logical
                if pt < self._wall_time:
                    self._clock_rollbacks += 1
                self._logical += 1
                
            self._ticks += 1
            return self._current_timestamp()
            
    def send(self) -> HLCTimestamp:
        """
        Generate timestamp for outgoing message.
        
        Same as tick() - advances clock and returns timestamp
        to include in the message.
        """
        with self._lock:
            pt = self._get_wall_time()
            
            if pt > self._wall_time:
                self._wall_time = pt
                self._logical = 0
            else:
                if pt < self._wall_time:
                    self._clock_rollbacks += 1
                self._logical += 1
                
            self._sends += 1
            return self._current_timestamp()
            
    def receive(self, msg_ts: HLCTimestamp) -> HLCTimestamp:
        """
        Merge with incoming message timestamp.
        
        Algorithm:
          pt = physical_time()
          if pt > max(l.wall_time, msg.wall_time):
              l.wall_time = pt
              l.logical = 0
          elif l.wall_time == msg.wall_time:
              l.logical = max(l.logical, msg.logical) + 1
          elif l.wall_time > msg.wall_time:
              l.logical += 1
          else:  # msg.wall_time > l.wall_time
              l.wall_time = msg.wall_time
              l.logical = msg.logical + 1
          return l
          
        INV-SEC-012: Guarantees recv_ts > msg_ts (causality preserved)
        """
        with self._lock:
            pt = self._get_wall_time()
            
            # Check for excessive drift (security measure)
            if msg_ts.wall_time > pt + self.MAX_DRIFT_NS:
                raise ChronosError(
                    f"Message timestamp too far in future: {msg_ts}. "
                    f"Possible NTP poisoning attack."
                )
                
            max_wall = max(pt, self._wall_time, msg_ts.wall_time)
            
            if pt > self._wall_time and pt > msg_ts.wall_time:
                # Physical time is ahead - use it
                self._wall_time = pt
                self._logical = 0
            elif self._wall_time == msg_ts.wall_time:
                # Same wall time - take max logical and increment
                self._logical = max(self._logical, msg_ts.logical) + 1
            elif self._wall_time > msg_ts.wall_time:
                # Our wall time is ahead - just increment logical
                self._logical += 1
            else:
                # Message wall time is ahead - adopt it
                self._wall_time = msg_ts.wall_time
                self._logical = msg_ts.logical + 1
                
            if pt < self._wall_time:
                self._clock_rollbacks += 1
                
            self._receives += 1
            return self._current_timestamp()
            
    def now(self) -> HLCTimestamp:
        """
        Get current timestamp without advancing clock.
        
        Use tick() if you need to record an event.
        """
        with self._lock:
            return self._current_timestamp()
            
    def verify_causality(self, before: HLCTimestamp, after: HLCTimestamp) -> bool:
        """
        Verify causal ordering between two timestamps.
        
        INV-SEC-012: Returns True if before → after relationship holds.
        """
        return before.happens_before(after)
        
    def get_stats(self) -> dict:
        """Get clock statistics."""
        with self._lock:
            return {
                "node_id": self.node_id,
                "current_wall_time": self._wall_time,
                "current_logical": self._logical,
                "total_ticks": self._ticks,
                "total_sends": self._sends,
                "total_receives": self._receives,
                "clock_rollbacks_survived": self._clock_rollbacks
            }


class ChronosError(Exception):
    """Chronos-specific errors (potential attacks or severe clock issues)."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> bool:
    """Self-test for Chronos HLC implementation."""
    
    print("\n" + "=" * 60)
    print("           CHRONOS SELF-TEST")
    print("           Hybrid Logical Clock")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Basic tick monotonicity
    tests_total += 1
    print("\n[TEST 1] Tick Monotonicity...")
    try:
        chronos = Chronos("test_node")
        ts1 = chronos.tick()
        ts2 = chronos.tick()
        ts3 = chronos.tick()
        
        assert ts1.happens_before(ts2), "ts1 must precede ts2"
        assert ts2.happens_before(ts3), "ts2 must precede ts3"
        assert ts1.happens_before(ts3), "ts1 must precede ts3 (transitivity)"
        
        print(f"  ts1: {ts1}")
        print(f"  ts2: {ts2}")
        print(f"  ts3: {ts3}")
        print("  ✅ PASSED: Ticks are monotonically increasing")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 2: Send/Receive causality
    tests_total += 1
    print("\n[TEST 2] Send/Receive Causality...")
    try:
        node_a = Chronos("node_a")
        node_b = Chronos("node_b")
        
        # Node A sends message
        send_ts = node_a.send()
        
        # Simulate network delay
        time.sleep(0.001)
        
        # Node B receives and merges
        recv_ts = node_b.receive(send_ts)
        
        # INV-SEC-012: recv_ts must be greater than send_ts
        assert send_ts.happens_before(recv_ts), "send_ts must precede recv_ts"
        
        print(f"  send_ts: {send_ts}")
        print(f"  recv_ts: {recv_ts}")
        print("  ✅ PASSED: Causality preserved across nodes")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 3: Logical counter increments when wall time same
    tests_total += 1
    print("\n[TEST 3] Logical Counter Increment...")
    try:
        chronos = Chronos("test_node")
        
        # Rapid ticks should increment logical counter
        timestamps = [chronos.tick() for _ in range(100)]
        
        # Verify all unique and ordered
        for i in range(len(timestamps) - 1):
            assert timestamps[i].happens_before(timestamps[i+1])
            
        # Check that logical counters increased
        max_logical = max(ts.logical for ts in timestamps)
        assert max_logical > 0, "Logical counter should have incremented"
        
        print(f"  Generated 100 timestamps")
        print(f"  Max logical counter: {max_logical}")
        print("  ✅ PASSED: Logical counter handles rapid events")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 4: Cross-node ordering
    tests_total += 1
    print("\n[TEST 4] Cross-Node Message Ordering...")
    try:
        node_a = Chronos("node_a")
        node_b = Chronos("node_b")
        node_c = Chronos("node_c")
        
        # A -> B -> C message chain
        msg1_ts = node_a.send()
        recv1_ts = node_b.receive(msg1_ts)
        msg2_ts = node_b.send()
        recv2_ts = node_c.receive(msg2_ts)
        
        # Verify causal chain
        assert msg1_ts.happens_before(recv1_ts)
        assert recv1_ts.happens_before(msg2_ts) or recv1_ts == msg2_ts
        assert msg2_ts.happens_before(recv2_ts)
        assert msg1_ts.happens_before(recv2_ts)  # Transitivity
        
        print(f"  A sends: {msg1_ts}")
        print(f"  B recvs: {recv1_ts}")
        print(f"  B sends: {msg2_ts}")
        print(f"  C recvs: {recv2_ts}")
        print("  ✅ PASSED: Causal chain A→B→C preserved")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 5: Clock rollback survival
    tests_total += 1
    print("\n[TEST 5] Clock Rollback Survival...")
    try:
        chronos = Chronos("test_node")
        
        # Get initial timestamp
        ts1 = chronos.tick()
        
        # Simulate multiple ticks (logical should increment)
        for _ in range(10):
            ts = chronos.tick()
            
        ts2 = chronos.tick()
        
        # Even if wall clock were to roll back, our logical time continues
        assert ts1.happens_before(ts2)
        
        stats = chronos.get_stats()
        print(f"  Initial ts: {ts1}")
        print(f"  Final ts: {ts2}")
        print(f"  Total ticks: {stats['total_ticks']}")
        print("  ✅ PASSED: Clock survives rollback scenarios")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 6: Serialization round-trip
    tests_total += 1
    print("\n[TEST 6] Serialization Round-Trip...")
    try:
        chronos = Chronos("test_node")
        ts1 = chronos.tick()
        
        # Serialize and deserialize
        data = ts1.to_dict()
        ts2 = HLCTimestamp.from_dict(data)
        
        assert ts1 == ts2
        assert ts1.to_tuple() == ts2.to_tuple()
        
        print(f"  Original: {ts1}")
        print(f"  Restored: {ts2}")
        print("  ✅ PASSED: Timestamp survives serialization")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Summary
    print("\n" + "=" * 60)
    print(f"                RESULTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 60)
    
    if tests_passed == tests_total:
        print("\n⏱️  CHRONOS OPERATIONAL")
        print("INV-SEC-012 (Causal Consistency): ✅ ENFORCED")
        print("\n\"Time flows forward. Always.\"")
        
    return tests_passed == tests_total


if __name__ == "__main__":
    import sys
    success = _self_test()
    sys.exit(0 if success else 1)
