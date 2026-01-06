"""
PDO Replay Engine - Deterministic replay for Payment Decision Objects.

PAC Reference: PAC-OCC-P02
Constitutional Authority: OCC_CONSTITUTION_v1.0, Article V
Invariants Enforced: INV-OCC-008 (State Determinism), INV-OVR-009 (Override Replay Determinism)

This module implements deterministic replay capability that:
1. Reconstructs PDO state from transition history
2. Validates state consistency across replay
3. Supports point-in-time state recovery
4. Enables audit and forensic analysis
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ReplayMode(str, Enum):
    """Modes of replay operation."""
    FULL = "FULL"                    # Replay all transitions
    POINT_IN_TIME = "POINT_IN_TIME"  # Replay to specific timestamp
    VALIDATE = "VALIDATE"            # Replay and validate against current state
    FORENSIC = "FORENSIC"            # Detailed replay with all intermediate states


@dataclass
class TransitionRecord:
    """
    Transition record for replay.
    
    Mirrors PDOTransition from state machine.
    """
    id: str
    pdo_id: str
    from_state: str
    to_state: str
    transition_type: str
    actor_id: str
    timestamp: datetime
    reason: str
    is_override: bool
    override_id: str | None
    hash_previous: str | None
    hash_current: str


@dataclass
class ReplayState:
    """
    Reconstructed state at a point in replay.
    """
    pdo_id: str
    state: str
    timestamp: datetime
    transition_index: int
    is_overridden: bool
    override_count: int
    hash_at_state: str


@dataclass
class ReplayResult:
    """
    Result of a replay operation.
    
    Invariant: INV-OCC-008 - Replay must be deterministic
    """
    pdo_id: str
    mode: ReplayMode
    success: bool
    final_state: str
    transition_count: int
    override_count: int
    
    # Validation results
    hash_chain_valid: bool
    state_consistent: bool
    errors: list[str] = field(default_factory=list)
    
    # Intermediate states (for FORENSIC mode)
    intermediate_states: list[ReplayState] = field(default_factory=list)
    
    # Point-in-time (for POINT_IN_TIME mode)
    target_timestamp: datetime | None = None
    state_at_timestamp: str | None = None
    
    # Timing
    replay_started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    replay_completed_at: datetime | None = None
    
    def compute_hash(self) -> str:
        """Compute hash of replay result for verification."""
        content = (
            f"{self.pdo_id}|{self.mode.value}|{self.final_state}|"
            f"{self.transition_count}|{self.hash_chain_valid}"
        )
        return hashlib.sha256(content.encode()).hexdigest()


class ReplayError(Exception):
    """Raised when replay encounters an error."""


class ReplayValidationError(Exception):
    """Raised when replay validation fails."""


class PDOReplayEngine:
    """
    Deterministic replay engine for PDO state reconstruction.
    
    Constitutional Invariants Enforced:
    - INV-OCC-008: State Determinism - Same inputs produce same outputs
    - INV-OVR-009: Override Replay Determinism - Override states are reproducible
    
    Guarantees:
    - Given identical transition history, replay produces identical final state
    - Hash chain integrity is verified during replay
    - Point-in-time state can be deterministically reconstructed
    """
    
    # Singleton enforcement
    _INSTANCE: PDOReplayEngine | None = None
    _LOCK = threading.Lock()
    
    def __init__(self) -> None:
        """Initialize replay engine."""
        self._lock = threading.Lock()
        
        # Metrics
        self._replay_count = 0
        self._validation_failures = 0
        self._hash_failures = 0
        
    @classmethod
    def get_instance(cls) -> PDOReplayEngine:
        """Get singleton instance."""
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    cls._INSTANCE = cls()
        return cls._INSTANCE
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton for testing."""
        with cls._LOCK:
            cls._INSTANCE = None
    
    def replay(
        self,
        pdo_id: str,
        transitions: list[TransitionRecord],
        mode: ReplayMode = ReplayMode.FULL,
        target_timestamp: datetime | None = None,
        expected_final_state: str | None = None,
    ) -> ReplayResult:
        """
        Replay PDO state from transition history.
        
        Args:
            pdo_id: ID of PDO to replay
            transitions: Ordered list of transitions to replay
            mode: Replay mode
            target_timestamp: For POINT_IN_TIME mode, target timestamp
            expected_final_state: For VALIDATE mode, expected state to compare
            
        Returns:
            ReplayResult with reconstructed state and validation
            
        Raises:
            ReplayError: If replay encounters unrecoverable error
        """
        self._replay_count += 1
        
        # Initialize result
        result = ReplayResult(
            pdo_id=pdo_id,
            mode=mode,
            success=False,
            final_state="PENDING",  # Initial state
            transition_count=0,
            override_count=0,
            hash_chain_valid=True,
            state_consistent=True,
            target_timestamp=target_timestamp,
        )
        
        try:
            with self._lock:
                # Verify transitions are sorted by timestamp
                if not self._verify_ordering(transitions):
                    result.errors.append("Transitions not in chronological order")
                    result.success = False
                    return result
                
                # Replay transitions
                current_state = "PENDING"
                override_count = 0
                previous_hash: str | None = None
                
                for i, tr in enumerate(transitions):
                    # Verify hash chain
                    if not self._verify_hash_link(tr, previous_hash):
                        result.hash_chain_valid = False
                        result.errors.append(f"Hash chain broken at transition {tr.id}")
                        self._hash_failures += 1
                    
                    # Point-in-time check
                    if mode == ReplayMode.POINT_IN_TIME and target_timestamp:
                        if tr.timestamp > target_timestamp:
                            result.state_at_timestamp = current_state
                            break
                    
                    # Apply transition
                    current_state = tr.to_state
                    result.transition_count += 1
                    
                    if tr.is_override:
                        override_count += 1
                    
                    # Record intermediate state for forensic mode
                    if mode == ReplayMode.FORENSIC:
                        result.intermediate_states.append(
                            ReplayState(
                                pdo_id=pdo_id,
                                state=current_state,
                                timestamp=tr.timestamp,
                                transition_index=i,
                                is_overridden=tr.is_override,
                                override_count=override_count,
                                hash_at_state=tr.hash_current,
                            )
                        )
                    
                    previous_hash = tr.hash_current
                
                # Update result
                result.final_state = current_state
                result.override_count = override_count
                
                # Handle point-in-time mode final state
                if mode == ReplayMode.POINT_IN_TIME:
                    if result.state_at_timestamp is None:
                        # Target is after all transitions
                        result.state_at_timestamp = current_state
                
                # Validate mode - compare with expected
                if mode == ReplayMode.VALIDATE and expected_final_state:
                    if current_state != expected_final_state:
                        result.state_consistent = False
                        result.errors.append(
                            f"State mismatch: replayed '{current_state}', "
                            f"expected '{expected_final_state}'"
                        )
                        self._validation_failures += 1
                
                # Mark success if no errors
                result.success = len(result.errors) == 0
                result.replay_completed_at = datetime.now(timezone.utc)
                
                return result
                
        except Exception as e:
            result.errors.append(f"Replay failed: {type(e).__name__}: {str(e)}")
            result.success = False
            return result
    
    def _verify_ordering(self, transitions: list[TransitionRecord]) -> bool:
        """Verify transitions are in chronological order."""
        for i in range(1, len(transitions)):
            if transitions[i].timestamp < transitions[i - 1].timestamp:
                return False
        return True
    
    def _verify_hash_link(
        self, transition: TransitionRecord, expected_previous: str | None
    ) -> bool:
        """Verify hash chain link is correct."""
        return transition.hash_previous == expected_previous
    
    def validate_replay_determinism(
        self,
        pdo_id: str,
        transitions: list[TransitionRecord],
        runs: int = 3,
    ) -> tuple[bool, str | None]:
        """
        Validate that replay is deterministic by running multiple times.
        
        Constitutional basis: INV-OCC-008 requires deterministic state.
        
        Args:
            pdo_id: PDO to validate
            transitions: Transition history
            runs: Number of replay runs
            
        Returns:
            (is_deterministic, error_message)
        """
        results: list[ReplayResult] = []
        
        for _ in range(runs):
            result = self.replay(pdo_id, transitions, mode=ReplayMode.FULL)
            results.append(result)
        
        # Compare all results
        reference = results[0]
        for i, result in enumerate(results[1:], start=2):
            if result.final_state != reference.final_state:
                return False, f"Non-deterministic: run 1 produced '{reference.final_state}', run {i} produced '{result.final_state}'"
            if result.transition_count != reference.transition_count:
                return False, f"Non-deterministic transition count"
            if result.hash_chain_valid != reference.hash_chain_valid:
                return False, f"Non-deterministic hash validation"
        
        return True, None
    
    def reconstruct_state_at_time(
        self,
        pdo_id: str,
        transitions: list[TransitionRecord],
        timestamp: datetime,
    ) -> tuple[str, ReplayResult]:
        """
        Reconstruct PDO state at a specific point in time.
        
        Args:
            pdo_id: PDO ID
            transitions: Full transition history
            timestamp: Target timestamp
            
        Returns:
            (state_at_timestamp, full_replay_result)
        """
        result = self.replay(
            pdo_id=pdo_id,
            transitions=transitions,
            mode=ReplayMode.POINT_IN_TIME,
            target_timestamp=timestamp,
        )
        
        return result.state_at_timestamp or "PENDING", result
    
    def forensic_analysis(
        self,
        pdo_id: str,
        transitions: list[TransitionRecord],
    ) -> ReplayResult:
        """
        Perform forensic analysis with full intermediate state capture.
        
        Returns complete state history for audit/investigation.
        """
        return self.replay(
            pdo_id=pdo_id,
            transitions=transitions,
            mode=ReplayMode.FORENSIC,
        )
    
    def compare_replay_results(
        self,
        result1: ReplayResult,
        result2: ReplayResult,
    ) -> dict[str, Any]:
        """
        Compare two replay results for consistency analysis.
        
        Useful for comparing replays from different sources or times.
        """
        return {
            "pdo_id_match": result1.pdo_id == result2.pdo_id,
            "final_state_match": result1.final_state == result2.final_state,
            "transition_count_match": result1.transition_count == result2.transition_count,
            "override_count_match": result1.override_count == result2.override_count,
            "hash_valid_match": result1.hash_chain_valid == result2.hash_chain_valid,
            "both_successful": result1.success and result2.success,
            "differences": self._find_differences(result1, result2),
        }
    
    def _find_differences(
        self, result1: ReplayResult, result2: ReplayResult
    ) -> list[str]:
        """Find specific differences between replay results."""
        diffs = []
        
        if result1.final_state != result2.final_state:
            diffs.append(
                f"Final state: '{result1.final_state}' vs '{result2.final_state}'"
            )
        if result1.transition_count != result2.transition_count:
            diffs.append(
                f"Transition count: {result1.transition_count} vs {result2.transition_count}"
            )
        if result1.override_count != result2.override_count:
            diffs.append(
                f"Override count: {result1.override_count} vs {result2.override_count}"
            )
        if result1.hash_chain_valid != result2.hash_chain_valid:
            diffs.append(
                f"Hash chain valid: {result1.hash_chain_valid} vs {result2.hash_chain_valid}"
            )
        
        return diffs
    
    def get_metrics(self) -> dict[str, int]:
        """Return replay engine metrics."""
        return {
            "replay_count": self._replay_count,
            "validation_failures": self._validation_failures,
            "hash_failures": self._hash_failures,
        }
