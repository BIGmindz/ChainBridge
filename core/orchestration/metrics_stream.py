"""
ChainBridge Metrics Stream
PAC-VIZ-P55: God View Dashboard - Data Pipeline

Provides real-time metrics for:
- Legion status (active hive minds, consensus rate)
- Polyatomic consensus events (3-of-5 voting)
- Atom voting states (AGREE, DISAGREE, PENDING)
- Context synchronization health (SYNC-01/02/03)

Invariant: VIZ-01 (Truth in UI) - All metrics must reflect actual system state
"""

import random
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class AtomVoteState(Enum):
    """Vote state for individual atom in polyatomic consensus."""
    PENDING = "PENDING"        # Atom has not voted yet
    AGREE = "AGREE"            # Atom voted for majority hash
    DISAGREE = "DISAGREE"      # Atom voted for minority hash
    TIMEOUT = "TIMEOUT"        # Atom failed to respond
    SYNCING = "SYNCING"        # Atom receiving context


class HiveHealthState(Enum):
    """Overall hive health status."""
    OPERATIONAL = "OPERATIONAL"      # All systems nominal
    DEGRADED = "DEGRADED"            # Some atoms struggling
    SCRAM = "SCRAM"                  # Critical failure (SYNC-02/POLY-02 triggered)
    RECOVERING = "RECOVERING"        # Post-SCRAM recovery


@dataclass
class AtomVote:
    """Individual atom's vote in consensus."""
    gid: str
    hash: str
    vote_state: AtomVoteState
    latency_ms: float
    timestamp: datetime


@dataclass
class ConsensusEvent:
    """Single consensus decision event."""
    consensus_id: str
    task_description: str
    squad_gids: List[str]
    atom_votes: List[AtomVote]
    winning_hash: Optional[str]
    vote_count: Dict[str, int]  # hash -> count
    threshold: int
    achieved: bool
    context_hash: str  # P52 - Context sync verification
    timestamp: datetime


@dataclass
class LegionMetrics:
    """High-level legion statistics."""
    total_hives: int
    active_hives: int
    consensus_checks_per_sec: float
    hallucinations_crushed: int  # Disagreements caught
    uptime_hours: float
    scram_count: int
    health_state: HiveHealthState


@dataclass
class ContextSyncMetrics:
    """P52 - Context synchronization health."""
    total_syncs: int
    successful_syncs: int
    drift_detections: int
    success_rate: float
    last_sync_timestamp: Optional[datetime]


# ============================================================================
# MOCK DATA GENERATORS (For Demo - Replace with Real Integrations)
# ============================================================================

def _generate_mock_atom_votes(squad_size: int = 5) -> List[AtomVote]:
    """Generate mock atom votes for consensus event."""
    squad_gids = [f"GID-06-{str(i+1).zfill(2)}" for i in range(squad_size)]
    
    # Simulate 3-of-5 consensus scenario
    # Most atoms agree, some may disagree or timeout
    hashes = [
        "3f8a9c2b1e4d7a6f",  # Majority hash
        "7b1c5d9e2a8f4c6b",  # Minority hash
    ]
    
    votes = []
    for i, gid in enumerate(squad_gids):
        # 80% agree, 10% disagree, 10% timeout
        rand = random.random()
        if rand < 0.8:
            vote_hash = hashes[0]
            state = AtomVoteState.AGREE
        elif rand < 0.9:
            vote_hash = hashes[1]
            state = AtomVoteState.DISAGREE
        else:
            vote_hash = hashes[1]
            state = AtomVoteState.TIMEOUT
        
        votes.append(AtomVote(
            gid=gid,
            hash=vote_hash,
            vote_state=state,
            latency_ms=random.uniform(5, 50),
            timestamp=datetime.now()
        ))
    
    return votes


def _calculate_vote_count(votes: List[AtomVote]) -> Dict[str, int]:
    """Count votes by hash."""
    counts = {}
    for vote in votes:
        if vote.vote_state == AtomVoteState.AGREE or vote.vote_state == AtomVoteState.DISAGREE:
            counts[vote.hash] = counts.get(vote.hash, 0) + 1
    return counts


def _determine_winning_hash(votes: List[AtomVote], threshold: int) -> Optional[str]:
    """Determine if consensus achieved (POLY-01)."""
    counts = _calculate_vote_count(votes)
    for hash_val, count in counts.items():
        if count >= threshold:
            return hash_val
    return None


# ============================================================================
# PUBLIC API
# ============================================================================

def get_legion_metrics() -> LegionMetrics:
    """
    Get current legion-wide statistics.
    
    VIZ-01: Returns actual system state (not mocked in production).
    
    Returns:
        LegionMetrics with real-time stats
    """
    # MOCK DATA - Replace with actual legion queries
    return LegionMetrics(
        total_hives=200,
        active_hives=198,  # 2 hives in maintenance
        consensus_checks_per_sec=361685.0,  # PAC-48 benchmark
        hallucinations_crushed=0,  # No dissonance today
        uptime_hours=72.5,
        scram_count=0,
        health_state=HiveHealthState.OPERATIONAL
    )


def get_context_sync_metrics() -> ContextSyncMetrics:
    """
    Get P52 context synchronization health.
    
    VIZ-01: Returns actual SYNC-01/02/03 metrics.
    
    Returns:
        ContextSyncMetrics with sync health
    """
    # MOCK DATA - Replace with HiveMemory.get_sync_stats()
    return ContextSyncMetrics(
        total_syncs=15234,
        successful_syncs=15234,
        drift_detections=0,  # SYNC-02 not triggered
        success_rate=1.0,
        last_sync_timestamp=datetime.now()
    )


def get_latest_consensus_events(count: int = 10) -> List[ConsensusEvent]:
    """
    Get most recent consensus events.
    
    VIZ-01: Returns actual polyatomic votes (not mocked in production).
    
    Args:
        count: Number of events to retrieve
    
    Returns:
        List of ConsensusEvent (newest first)
    """
    events = []
    
    for i in range(count):
        votes = _generate_mock_atom_votes(squad_size=5)
        threshold = 3  # POLY-01: 3-of-5 threshold
        winning_hash = _determine_winning_hash(votes, threshold)
        
        event = ConsensusEvent(
            consensus_id=f"CONSENSUS-{str(int(time.time()) + i).zfill(10)}",
            task_description=f"Validate Transaction TXN-{random.randint(1000, 9999)}",
            squad_gids=[v.gid for v in votes],
            atom_votes=votes,
            winning_hash=winning_hash,
            vote_count=_calculate_vote_count(votes),
            threshold=threshold,
            achieved=(winning_hash is not None),
            context_hash="3f8a9c2b1e4d7a6f5c3b2a1e0d9c8b7a",  # P52 context hash
            timestamp=datetime.now()
        )
        
        events.append(event)
    
    return events


def get_hive_health() -> HiveHealthState:
    """
    Get overall hive health state.
    
    VIZ-01: Red dashboard if SCRAM triggered.
    
    Returns:
        HiveHealthState enum
    """
    # MOCK - Replace with actual health check
    # Check for SYNC-02 (context drift), POLY-02 (dissonance), etc.
    return HiveHealthState.OPERATIONAL


def stream_consensus_events():
    """
    Generator yielding real-time consensus events.
    
    VIZ-01: Streams actual events as they occur.
    
    Yields:
        ConsensusEvent objects in real-time
    """
    while True:
        # MOCK - Replace with event queue/subscription
        events = get_latest_consensus_events(count=1)
        if events:
            yield events[0]
        time.sleep(1)  # Poll every second


def export_metrics_json() -> Dict[str, Any]:
    """
    Export all metrics as JSON for dashboard consumption.
    
    VIZ-01: Single source of truth for dashboard.
    
    Returns:
        Dict with all metrics (serializable)
    """
    legion = get_legion_metrics()
    sync = get_context_sync_metrics()
    events = get_latest_consensus_events(count=10)
    health = get_hive_health()
    
    return {
        "legion": asdict(legion),
        "context_sync": asdict(sync),
        "recent_events": [asdict(e) for e in events],
        "health": health.value,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# INTEGRATION STUBS (Replace in Production)
# ============================================================================

def integrate_with_polyatomic_hive():
    """
    TODO: Integrate with core/intelligence/polyatomic_hive.py
    
    Listen to PolyatomicHive.think_polyatomic() events
    Capture ConsensusResult → Convert to ConsensusEvent
    """
    pass


def integrate_with_hive_memory():
    """
    TODO: Integrate with core/intelligence/hive_memory.py
    
    Call HiveMemory.get_sync_stats() for context sync metrics
    Monitor SYNC-02 triggers (drift detection)
    """
    pass


def integrate_with_legion_commander():
    """
    TODO: Integrate with PAC-48 Legion Commander
    
    Query legion for active hive count
    Get consensus rate (checks/sec)
    """
    pass


if __name__ == "__main__":
    # Demo: Print metrics
    print("=== ChainBridge Metrics Stream Demo ===\n")
    
    print("Legion Metrics:")
    legion = get_legion_metrics()
    print(f"  Active Hives: {legion.active_hives}/{legion.total_hives}")
    print(f"  Consensus Rate: {legion.consensus_checks_per_sec:,.0f} checks/sec")
    print(f"  Health: {legion.health_state.value}")
    print(f"  Hallucinations Crushed: {legion.hallucinations_crushed}\n")
    
    print("Context Sync Metrics (P52):")
    sync = get_context_sync_metrics()
    print(f"  Total Syncs: {sync.total_syncs:,}")
    print(f"  Success Rate: {sync.success_rate:.1%}")
    print(f"  Drift Detections: {sync.drift_detections}\n")
    
    print("Latest Consensus Events:")
    events = get_latest_consensus_events(count=3)
    for event in events:
        status = "✅ CONSENSUS" if event.achieved else "❌ DISSONANCE"
        print(f"  {event.consensus_id}: {status}")
        print(f"    Task: {event.task_description}")
        print(f"    Votes: {event.vote_count}")
        print(f"    Threshold: {event.threshold}")
        print(f"    Winner: {event.winning_hash[:16]}...")
        print()
