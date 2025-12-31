# ═══════════════════════════════════════════════════════════════════════════════
# Neural Memory Interface — Titans-Ready Architecture (SHADOW MODE)
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE
# Agents: CODY (GID-01), MAGGIE (GID-10)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Neural Memory Interface — Non-Inferencing Architecture Layer

PURPOSE:
    Define abstract interfaces for Titans-compatible neural memory without
    actual model deployment. This is SHADOW MODE — architecture only.

EXECUTION CONSTRAINTS:
    - NO model weights
    - NO test-time training
    - NO runtime memory mutation
    - NO gradient computation
    - Interface definitions ONLY

TITANS COMPATIBILITY:
    Based on Google Research "Titans: Learning to Memorize at Test Time"
    - Persistent memory across context windows
    - Surprise-based memory updates
    - Fast (attention) / Slow (memory) dual-brain architecture

INVARIANTS:
    INV-MEM-001: Memory state is immutable once snapshotted
    INV-MEM-002: All memory updates require audit trail
    INV-MEM-003: Memory snapshots include integrity hash
    INV-MEM-004: Frozen memory cannot be modified
    INV-MEM-005: Memory rollback preserves chain integrity
    INV-MEM-006: No runtime learning in production mode

LANE: ARCHITECTURE_ONLY (NON-INFERENCING)
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY STATE ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class MemoryMode(Enum):
    """Operating mode for neural memory."""

    SHADOW = "SHADOW"  # Architecture only, no inference
    INFERENCE = "INFERENCE"  # Read-only inference
    LEARNING = "LEARNING"  # Test-time training (FORBIDDEN in production)
    FROZEN = "FROZEN"  # Immutable, no updates allowed


class MemoryTier(Enum):
    """Memory tier in dual-brain architecture."""

    FAST = "FAST"  # Short-term attention-based (within context)
    SLOW = "SLOW"  # Long-term persistent memory (across contexts)
    HYBRID = "HYBRID"  # Combined fast+slow routing


class SnapshotStatus(Enum):
    """Status of memory snapshot."""

    PENDING = "PENDING"  # Snapshot in progress
    COMPLETE = "COMPLETE"  # Snapshot finalized
    VERIFIED = "VERIFIED"  # Hash verified
    ANCHORED = "ANCHORED"  # Committed to ledger
    ROLLED_BACK = "ROLLED_BACK"  # Superseded by rollback


class SurpriseLevel(Enum):
    """Surprise metric categories for memory updates."""

    NEGLIGIBLE = "NEGLIGIBLE"  # No memory update needed
    LOW = "LOW"  # Minor memory adjustment
    MODERATE = "MODERATE"  # Significant memory update
    HIGH = "HIGH"  # Major memory restructuring
    CRITICAL = "CRITICAL"  # Emergency memory attention


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY STATE HASH
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MemoryStateHash:
    """
    Cryptographic hash of memory state.

    INV-MEM-003: Memory snapshots include integrity hash
    """

    hash_value: str
    algorithm: str = "sha256"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    memory_tier: MemoryTier = MemoryTier.SLOW
    entry_count: int = 0

    @classmethod
    def compute(cls, state_data: Dict[str, Any], tier: MemoryTier = MemoryTier.SLOW) -> "MemoryStateHash":
        """Compute hash from memory state data."""
        serialized = json.dumps(state_data, sort_keys=True, default=str)
        hash_value = hashlib.sha256(serialized.encode()).hexdigest()
        return cls(
            hash_value=hash_value,
            memory_tier=tier,
            entry_count=len(state_data),
        )

    def verify(self, state_data: Dict[str, Any]) -> bool:
        """Verify hash against state data."""
        recomputed = self.compute(state_data, self.memory_tier)
        return recomputed.hash_value == self.hash_value


# ═══════════════════════════════════════════════════════════════════════════════
# SURPRISE METRIC (TITANS COMPATIBILITY)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SurpriseMetric:
    """
    Surprise-based metric for memory update decisions.

    In Titans architecture, surprise measures how unexpected an input is
    relative to current memory state. High surprise triggers memory updates.

    NOTE: This is interface-only. No actual computation in SHADOW mode.
    """

    value: float  # Normalized [0.0, 1.0]
    level: SurpriseLevel
    context_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        """Validate surprise value bounds."""
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Surprise value must be in [0.0, 1.0], got {self.value}")

    @classmethod
    def from_value(cls, value: float, context_id: str) -> "SurpriseMetric":
        """Create SurpriseMetric from raw value."""
        if value < 0.1:
            level = SurpriseLevel.NEGLIGIBLE
        elif value < 0.3:
            level = SurpriseLevel.LOW
        elif value < 0.6:
            level = SurpriseLevel.MODERATE
        elif value < 0.85:
            level = SurpriseLevel.HIGH
        else:
            level = SurpriseLevel.CRITICAL
        return cls(value=value, level=level, context_id=context_id)

    def should_update_memory(self) -> bool:
        """Determine if surprise level warrants memory update."""
        return self.level in (SurpriseLevel.MODERATE, SurpriseLevel.HIGH, SurpriseLevel.CRITICAL)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MemorySnapshot:
    """
    Immutable snapshot of memory state.

    INV-MEM-001: Memory state is immutable once snapshotted
    """

    snapshot_id: str
    state_hash: MemoryStateHash
    status: SnapshotStatus
    created_at: str
    predecessor_id: Optional[str] = None
    ledger_anchor: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate snapshot ID format."""
        if not self.snapshot_id.startswith("MEM-SNAP-"):
            raise ValueError(f"Snapshot ID must start with 'MEM-SNAP-': {self.snapshot_id}")

    def is_anchored(self) -> bool:
        """Check if snapshot is anchored to ledger."""
        return self.status == SnapshotStatus.ANCHORED and self.ledger_anchor is not None

    def compute_chain_hash(self) -> str:
        """Compute hash including predecessor for chain integrity."""
        chain_data = {
            "snapshot_id": self.snapshot_id,
            "state_hash": self.state_hash.hash_value,
            "predecessor_id": self.predecessor_id or "GENESIS",
            "created_at": self.created_at,
        }
        return hashlib.sha256(json.dumps(chain_data, sort_keys=True).encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY UPDATE RECORD
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MemoryUpdateRecord:
    """
    Audit record for memory updates.

    INV-MEM-002: All memory updates require audit trail
    """

    update_id: str
    pre_state_hash: str
    post_state_hash: str
    surprise_metric: SurpriseMetric
    update_reason: str
    agent_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved: bool = False
    approval_id: Optional[str] = None

    def compute_audit_hash(self) -> str:
        """Compute hash for audit integrity."""
        audit_data = {
            "update_id": self.update_id,
            "pre_state_hash": self.pre_state_hash,
            "post_state_hash": self.post_state_hash,
            "surprise_value": self.surprise_metric.value,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
        }
        return hashlib.sha256(json.dumps(audit_data, sort_keys=True).encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# NEURAL MEMORY INTERFACE (ABSTRACT)
# ═══════════════════════════════════════════════════════════════════════════════


class NeuralMemoryInterface(ABC):
    """
    Abstract interface for neural memory operations.

    This is the core abstraction for Titans-compatible memory. Implementations
    MUST NOT perform actual inference or learning in SHADOW mode.

    INV-MEM-006: No runtime learning in production mode
    """

    @property
    @abstractmethod
    def mode(self) -> MemoryMode:
        """Current operating mode."""
        ...

    @property
    @abstractmethod
    def tier(self) -> MemoryTier:
        """Memory tier (FAST/SLOW/HYBRID)."""
        ...

    @abstractmethod
    def get_state_hash(self) -> MemoryStateHash:
        """Get current memory state hash."""
        ...

    @abstractmethod
    def create_snapshot(self) -> MemorySnapshot:
        """Create immutable snapshot of current state."""
        ...

    @abstractmethod
    def restore_snapshot(self, snapshot: MemorySnapshot) -> bool:
        """
        Restore memory to snapshot state.

        INV-MEM-005: Memory rollback preserves chain integrity
        """
        ...

    @abstractmethod
    def freeze(self) -> bool:
        """
        Freeze memory to prevent further updates.

        INV-MEM-004: Frozen memory cannot be modified
        """
        ...

    @abstractmethod
    def is_frozen(self) -> bool:
        """Check if memory is frozen."""
        ...

    @abstractmethod
    def compute_surprise(self, input_data: Dict[str, Any]) -> SurpriseMetric:
        """
        Compute surprise metric for input.

        NOTE: In SHADOW mode, returns placeholder metric.
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# DUAL-BRAIN ROUTER INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════


class DualBrainRouterInterface(ABC):
    """
    Abstract interface for dual-brain (Fast/Slow) routing decisions.

    The dual-brain architecture routes queries to either:
    - FAST: Standard attention mechanism (within context window)
    - SLOW: Persistent neural memory (across contexts)

    Routing is based on surprise metrics and query characteristics.
    """

    @abstractmethod
    def route_query(
        self,
        query: Dict[str, Any],
        fast_memory: NeuralMemoryInterface,
        slow_memory: NeuralMemoryInterface,
    ) -> Tuple[MemoryTier, Dict[str, Any]]:
        """
        Route query to appropriate memory tier.

        Returns (selected_tier, routing_metadata).
        """
        ...

    @abstractmethod
    def get_routing_stats(self) -> Dict[str, int]:
        """Get statistics on routing decisions."""
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY GATE PROTOCOL
# ═══════════════════════════════════════════════════════════════════════════════


class MemoryGateProtocol(Protocol):
    """
    Protocol for memory update gates.

    Gates control when memory updates are permitted based on:
    - Surprise threshold
    - Mode restrictions
    - Governance rules
    """

    def should_allow_update(
        self,
        surprise: SurpriseMetric,
        mode: MemoryMode,
        context: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Determine if memory update should be allowed.

        Returns (allowed, reason).
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW MODE IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowModeMemory(NeuralMemoryInterface):
    """
    Shadow mode implementation of neural memory.

    This implementation provides the interface without actual memory operations.
    Used for architecture validation before Titans deployment.

    INV-MEM-006: No runtime learning in production mode
    """

    def __init__(self, tier: MemoryTier = MemoryTier.SLOW) -> None:
        self._mode = MemoryMode.SHADOW
        self._tier = tier
        self._frozen = False
        self._state: Dict[str, Any] = {}
        self._snapshots: List[MemorySnapshot] = []
        self._snapshot_counter = 0

    @property
    def mode(self) -> MemoryMode:
        return self._mode

    @property
    def tier(self) -> MemoryTier:
        return self._tier

    def get_state_hash(self) -> MemoryStateHash:
        """Get current memory state hash."""
        return MemoryStateHash.compute(self._state, self._tier)

    def create_snapshot(self) -> MemorySnapshot:
        """Create immutable snapshot of current state."""
        self._snapshot_counter += 1
        snapshot_id = f"MEM-SNAP-{self._snapshot_counter:06d}"
        predecessor_id = self._snapshots[-1].snapshot_id if self._snapshots else None

        snapshot = MemorySnapshot(
            snapshot_id=snapshot_id,
            state_hash=self.get_state_hash(),
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
            predecessor_id=predecessor_id,
            metadata={"tier": self._tier.value, "mode": self._mode.value},
        )
        self._snapshots.append(snapshot)
        return snapshot

    def restore_snapshot(self, snapshot: MemorySnapshot) -> bool:
        """Restore memory to snapshot state (no-op in shadow mode)."""
        if self._frozen:
            return False
        # In shadow mode, we just track the intention
        return True

    def freeze(self) -> bool:
        """Freeze memory to prevent further updates."""
        self._frozen = True
        self._mode = MemoryMode.FROZEN
        return True

    def is_frozen(self) -> bool:
        """Check if memory is frozen."""
        return self._frozen

    def compute_surprise(self, input_data: Dict[str, Any]) -> SurpriseMetric:
        """
        Compute surprise metric (placeholder in shadow mode).

        In shadow mode, returns a fixed low-surprise metric.
        """
        return SurpriseMetric.from_value(0.1, context_id="SHADOW-CTX")


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class SnapshotRegistry:
    """
    Registry for managing memory snapshots.

    Provides snapshot storage, retrieval, and chain validation.
    """

    _instance: Optional["SnapshotRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "SnapshotRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if SnapshotRegistry._initialized:
            return
        SnapshotRegistry._initialized = True

        self._snapshots: Dict[str, MemorySnapshot] = {}
        self._chain: List[str] = []  # Ordered snapshot IDs

    def register(self, snapshot: MemorySnapshot) -> bool:
        """Register a snapshot in the registry."""
        if snapshot.snapshot_id in self._snapshots:
            return False

        # Validate chain linkage
        if self._chain and snapshot.predecessor_id != self._chain[-1]:
            return False

        self._snapshots[snapshot.snapshot_id] = snapshot
        self._chain.append(snapshot.snapshot_id)
        return True

    def get(self, snapshot_id: str) -> Optional[MemorySnapshot]:
        """Get snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def get_latest(self) -> Optional[MemorySnapshot]:
        """Get most recent snapshot."""
        if not self._chain:
            return None
        return self._snapshots.get(self._chain[-1])

    def verify_chain(self) -> Tuple[bool, Optional[str]]:
        """
        Verify integrity of snapshot chain.

        Returns (valid, error_message).
        """
        if not self._chain:
            return True, None

        for i, snapshot_id in enumerate(self._chain):
            snapshot = self._snapshots.get(snapshot_id)
            if snapshot is None:
                return False, f"Missing snapshot: {snapshot_id}"

            if i == 0:
                if snapshot.predecessor_id is not None:
                    return False, f"Genesis snapshot has predecessor: {snapshot.predecessor_id}"
            else:
                expected_pred = self._chain[i - 1]
                if snapshot.predecessor_id != expected_pred:
                    return False, f"Chain break at {snapshot_id}: expected {expected_pred}, got {snapshot.predecessor_id}"

        return True, None

    def count(self) -> int:
        """Return count of registered snapshots."""
        return len(self._snapshots)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "MemoryMode",
    "MemoryTier",
    "SnapshotStatus",
    "SurpriseLevel",
    # Data classes
    "MemoryStateHash",
    "SurpriseMetric",
    "MemorySnapshot",
    "MemoryUpdateRecord",
    # Interfaces
    "NeuralMemoryInterface",
    "DualBrainRouterInterface",
    "MemoryGateProtocol",
    # Implementations
    "ShadowModeMemory",
    "SnapshotRegistry",
]
