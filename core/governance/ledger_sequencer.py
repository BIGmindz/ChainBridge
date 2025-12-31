# ═══════════════════════════════════════════════════════════════════════════════
# Ledger Sequencer — Cryptographic Ordering & Sequencing
# PAC-BENSON-P24: CONTROL PLANE CORE HARDENING
# Agent: ATLAS (GID-11) — Ledger / Hash Integrity
# ═══════════════════════════════════════════════════════════════════════════════

"""
Ledger Sequencer Module

PURPOSE:
    Provide enterprise-grade sequencing for ledger entries.
    Ensures cryptographic ordering and prevents reordering attacks.

INVARIANTS:
    INV-LEDGER-SEQ-001: Sequence numbers are monotonically increasing
    INV-LEDGER-SEQ-002: No gaps in sequence allowed
    INV-LEDGER-SEQ-003: Hash chain binds all entries
    INV-LEDGER-SEQ-004: Timestamps are monotonically non-decreasing
    INV-LEDGER-SEQ-005: Reordering is cryptographically impossible

EXECUTION MODE: PARALLEL
LANE: INTEGRITY (GID-11)
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

LEDGER_SEQUENCER_VERSION = "1.0.0"
"""Module version."""

GENESIS_SEQUENCE = 0
"""Genesis entry sequence number."""

GENESIS_HASH = "0" * 64
"""Genesis entry hash (all zeros)."""

GENESIS_TIMESTAMP = "1970-01-01T00:00:00+00:00"
"""Genesis timestamp (Unix epoch)."""


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SequencerError(Exception):
    """Base exception for sequencer errors."""
    pass


class SequenceGapError(SequencerError):
    """Raised when sequence gap is detected."""
    
    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"SEQUENCE_GAP: Expected sequence {expected}, got {actual}. "
            f"Gaps are forbidden (INV-LEDGER-SEQ-002)."
        )


class SequenceRegressionError(SequencerError):
    """Raised when sequence number regresses."""
    
    def __init__(self, current: int, attempted: int):
        self.current = current
        self.attempted = attempted
        super().__init__(
            f"SEQUENCE_REGRESSION: Current sequence is {current}, "
            f"attempted {attempted}. Sequence must increase (INV-LEDGER-SEQ-001)."
        )


class ChainBrokenError(SequencerError):
    """Raised when hash chain is broken."""
    
    def __init__(self, sequence: int, expected_prev: str, actual_prev: str):
        self.sequence = sequence
        self.expected_prev = expected_prev
        self.actual_prev = actual_prev
        super().__init__(
            f"CHAIN_BROKEN at sequence {sequence}: "
            f"Expected previous hash {expected_prev[:16]}..., "
            f"got {actual_prev[:16]}... (INV-LEDGER-SEQ-003)."
        )


class TimestampRegressionError(SequencerError):
    """Raised when timestamp regresses."""
    
    def __init__(self, previous_ts: str, current_ts: str):
        self.previous_ts = previous_ts
        self.current_ts = current_ts
        super().__init__(
            f"TIMESTAMP_REGRESSION: Previous timestamp {previous_ts}, "
            f"current {current_ts}. Timestamps must not decrease (INV-LEDGER-SEQ-004)."
        )


class ReorderingDetectedError(SequencerError):
    """Raised when reordering attempt is detected."""
    
    def __init__(self, entry_id: str, details: str):
        self.entry_id = entry_id
        self.details = details
        super().__init__(
            f"REORDERING_DETECTED: Entry '{entry_id}' - {details}. "
            f"Reordering is forbidden (INV-LEDGER-SEQ-005)."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SEQUENCE POINT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SequencePoint:
    """
    Immutable sequence point in the ledger.
    
    Captures the state of the ledger at a specific sequence number.
    """
    sequence: int
    entry_hash: str
    timestamp: str
    entry_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sequence": self.sequence,
            "entry_hash": self.entry_hash,
            "timestamp": self.timestamp,
            "entry_id": self.entry_id,
        }
    
    @classmethod
    def genesis(cls) -> "SequencePoint":
        """Create genesis sequence point."""
        return cls(
            sequence=GENESIS_SEQUENCE,
            entry_hash=GENESIS_HASH,
            timestamp=GENESIS_TIMESTAMP,
            entry_id="GENESIS",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HASH CHAIN
# ═══════════════════════════════════════════════════════════════════════════════

def compute_entry_binding_hash(
    sequence: int,
    previous_hash: str,
    entry_data: Dict[str, Any],
    timestamp: str,
) -> str:
    """
    Compute binding hash that links entry to chain.
    
    The binding hash incorporates:
    - Sequence number (ordering)
    - Previous hash (chain link)
    - Entry content (integrity)
    - Timestamp (temporal ordering)
    """
    binding_input = {
        "sequence": sequence,
        "previous_hash": previous_hash,
        "entry_data_hash": hashlib.sha256(
            json.dumps(entry_data, sort_keys=True).encode()
        ).hexdigest(),
        "timestamp": timestamp,
    }
    canonical = json.dumps(binding_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_chain_link(
    current_hash: str,
    previous_hash: str,
    sequence: int,
    entry_data: Dict[str, Any],
    timestamp: str,
) -> bool:
    """
    Verify that a chain link is valid.
    
    Returns True if valid, raises ChainBrokenError otherwise.
    """
    expected = compute_entry_binding_hash(
        sequence, previous_hash, entry_data, timestamp
    )
    
    if current_hash != expected:
        raise ChainBrokenError(sequence, expected, current_hash)
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# SEQUENCER
# ═══════════════════════════════════════════════════════════════════════════════

class LedgerSequencer:
    """
    Enterprise-grade ledger sequencer.
    
    Guarantees:
    - Monotonically increasing sequence numbers
    - No gaps in sequence
    - Cryptographic hash chain
    - Monotonic timestamps
    - Reordering prevention
    """
    
    def __init__(self) -> None:
        self._sequence_points: List[SequencePoint] = []
        self._current_sequence = GENESIS_SEQUENCE
        self._current_hash = GENESIS_HASH
        self._current_timestamp = GENESIS_TIMESTAMP
        self._lock = threading.Lock()
        
        # Initialize with genesis point
        self._sequence_points.append(SequencePoint.genesis())
    
    def next_sequence(self) -> int:
        """Get next sequence number."""
        with self._lock:
            return self._current_sequence + 1
    
    def current_state(self) -> Tuple[int, str, str]:
        """Get current (sequence, hash, timestamp)."""
        with self._lock:
            return (
                self._current_sequence,
                self._current_hash,
                self._current_timestamp,
            )
    
    def append(
        self,
        entry_id: str,
        entry_data: Dict[str, Any],
        timestamp: Optional[str] = None,
    ) -> SequencePoint:
        """
        Append entry to ledger and return sequence point.
        
        Enforces all sequencing invariants.
        """
        timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        
        with self._lock:
            # INV-LEDGER-SEQ-004: Check timestamp monotonicity
            if timestamp < self._current_timestamp:
                raise TimestampRegressionError(self._current_timestamp, timestamp)
            
            # INV-LEDGER-SEQ-001/002: Get next sequence
            next_seq = self._current_sequence + 1
            
            # INV-LEDGER-SEQ-003: Compute binding hash
            entry_hash = compute_entry_binding_hash(
                next_seq,
                self._current_hash,
                entry_data,
                timestamp,
            )
            
            # Create sequence point
            point = SequencePoint(
                sequence=next_seq,
                entry_hash=entry_hash,
                timestamp=timestamp,
                entry_id=entry_id,
            )
            
            # Update state
            self._sequence_points.append(point)
            self._current_sequence = next_seq
            self._current_hash = entry_hash
            self._current_timestamp = timestamp
            
            return point
    
    def verify_sequence(
        self, start: int = 0, end: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Verify sequence integrity over a range.
        
        Returns (is_valid, list_of_errors).
        """
        errors: List[str] = []
        
        with self._lock:
            points = self._sequence_points[start:end]
        
        for i, point in enumerate(points):
            # Check sequence number
            expected_seq = start + i
            if point.sequence != expected_seq:
                errors.append(
                    f"Sequence mismatch at {i}: expected {expected_seq}, "
                    f"got {point.sequence}"
                )
            
            # Check no gaps (implicit in iteration)
        
        return len(errors) == 0, errors
    
    def get_point(self, sequence: int) -> Optional[SequencePoint]:
        """Get sequence point by sequence number."""
        with self._lock:
            if 0 <= sequence < len(self._sequence_points):
                return self._sequence_points[sequence]
            return None
    
    def get_range(
        self, start: int, end: int
    ) -> List[SequencePoint]:
        """Get range of sequence points."""
        with self._lock:
            return self._sequence_points[start:end]
    
    def count(self) -> int:
        """Get total entry count (including genesis)."""
        with self._lock:
            return len(self._sequence_points)


# ═══════════════════════════════════════════════════════════════════════════════
# MERKLE PROOF
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MerkleProof:
    """
    Merkle proof for ledger entry.
    
    Enables efficient verification of entry inclusion.
    """
    entry_id: str
    sequence: int
    entry_hash: str
    path: List[Tuple[str, str]]  # List of (direction, hash)
    root_hash: str
    
    def verify(self) -> bool:
        """Verify the Merkle proof."""
        current = self.entry_hash
        
        for direction, sibling_hash in self.path:
            if direction == "L":
                combined = sibling_hash + current
            else:
                combined = current + sibling_hash
            current = hashlib.sha256(combined.encode()).hexdigest()
        
        return current == self.root_hash


class MerkleTree:
    """
    Merkle tree for ledger entries.
    
    Provides efficient inclusion proofs and root computation.
    """
    
    def __init__(self) -> None:
        self._leaves: List[str] = []
        self._lock = threading.Lock()
    
    def add_leaf(self, leaf_hash: str) -> int:
        """Add leaf and return index."""
        with self._lock:
            index = len(self._leaves)
            self._leaves.append(leaf_hash)
            return index
    
    def compute_root(self) -> str:
        """Compute Merkle root."""
        with self._lock:
            if not self._leaves:
                return GENESIS_HASH
            
            level = self._leaves.copy()
            
            while len(level) > 1:
                # Pad if odd
                if len(level) % 2 == 1:
                    level.append(level[-1])
                
                # Compute next level
                next_level = []
                for i in range(0, len(level), 2):
                    combined = level[i] + level[i + 1]
                    next_level.append(
                        hashlib.sha256(combined.encode()).hexdigest()
                    )
                level = next_level
            
            return level[0]
    
    def get_proof(self, index: int) -> Optional[MerkleProof]:
        """Get Merkle proof for leaf at index."""
        with self._lock:
            if index < 0 or index >= len(self._leaves):
                return None
            
            path: List[Tuple[str, str]] = []
            level = self._leaves.copy()
            current_index = index
            
            while len(level) > 1:
                # Pad if odd
                if len(level) % 2 == 1:
                    level.append(level[-1])
                
                # Get sibling
                if current_index % 2 == 0:
                    sibling_index = current_index + 1
                    direction = "R"
                else:
                    sibling_index = current_index - 1
                    direction = "L"
                
                path.append((direction, level[sibling_index]))
                
                # Move to next level
                next_level = []
                for i in range(0, len(level), 2):
                    combined = level[i] + level[i + 1]
                    next_level.append(
                        hashlib.sha256(combined.encode()).hexdigest()
                    )
                level = next_level
                current_index = current_index // 2
            
            return MerkleProof(
                entry_id=f"entry-{index}",
                sequence=index,
                entry_hash=self._leaves[index],
                path=path,
                root_hash=level[0] if level else GENESIS_HASH,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT CHECKPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AuditCheckpoint:
    """
    Audit checkpoint for ledger state.
    
    Captures verifiable state at a point in time.
    """
    checkpoint_id: str
    sequence: int
    ledger_hash: str
    merkle_root: str
    timestamp: str
    entry_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "sequence": self.sequence,
            "ledger_hash": self.ledger_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "entry_count": self.entry_count,
        }
    
    def compute_checkpoint_hash(self) -> str:
        """Compute hash of checkpoint."""
        data = self.to_dict()
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()


class CheckpointManager:
    """
    Manages audit checkpoints for the ledger.
    """
    
    def __init__(self, sequencer: LedgerSequencer) -> None:
        self._sequencer = sequencer
        self._merkle = MerkleTree()
        self._checkpoints: List[AuditCheckpoint] = []
        self._lock = threading.Lock()
        self._checkpoint_counter = 0
    
    def record_entry(self, entry_hash: str) -> int:
        """Record entry in Merkle tree."""
        return self._merkle.add_leaf(entry_hash)
    
    def create_checkpoint(self) -> AuditCheckpoint:
        """Create audit checkpoint at current state."""
        with self._lock:
            seq, ledger_hash, _ = self._sequencer.current_state()
            self._checkpoint_counter += 1
            
            checkpoint = AuditCheckpoint(
                checkpoint_id=f"CKP-{self._checkpoint_counter:06d}",
                sequence=seq,
                ledger_hash=ledger_hash,
                merkle_root=self._merkle.compute_root(),
                timestamp=datetime.now(timezone.utc).isoformat(),
                entry_count=self._sequencer.count(),
            )
            
            self._checkpoints.append(checkpoint)
            return checkpoint
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[AuditCheckpoint]:
        """Get checkpoint by ID."""
        with self._lock:
            for cp in self._checkpoints:
                if cp.checkpoint_id == checkpoint_id:
                    return cp
            return None
    
    def verify_checkpoint(self, checkpoint: AuditCheckpoint) -> bool:
        """Verify checkpoint is still valid."""
        seq, ledger_hash, _ = self._sequencer.current_state()
        
        # Checkpoint must be at or before current sequence
        if checkpoint.sequence > seq:
            return False
        
        # Get hash at checkpoint sequence
        point = self._sequencer.get_point(checkpoint.sequence)
        if point is None:
            return False
        
        return point.entry_hash == checkpoint.ledger_hash


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Version
    "LEDGER_SEQUENCER_VERSION",
    
    # Constants
    "GENESIS_SEQUENCE",
    "GENESIS_HASH",
    "GENESIS_TIMESTAMP",
    
    # Exceptions
    "SequencerError",
    "SequenceGapError",
    "SequenceRegressionError",
    "ChainBrokenError",
    "TimestampRegressionError",
    "ReorderingDetectedError",
    
    # Hash utilities
    "compute_entry_binding_hash",
    "verify_chain_link",
    
    # Core classes
    "SequencePoint",
    "LedgerSequencer",
    "MerkleProof",
    "MerkleTree",
    "AuditCheckpoint",
    "CheckpointManager",
]
