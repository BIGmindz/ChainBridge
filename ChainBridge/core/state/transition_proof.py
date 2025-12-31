"""
ChainBridge Transition Proof Emission

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

PAC: PAC-ATLAS-A12-STATE-TRANSITION-GOVERNANCE-LOCK-01

This module provides transition proof emission for governed state changes.
Proofs are READ-ONLY artifacts that record transitions without mutation.

Every valid governed transition emits a StateTransitionProof containing:
- Artifact identification
- State change details
- Authority chain
- Cryptographic hash
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from .transition_validator import (
    TransitionRequest,
    TransitionValidationResult,
    TransitionResult,
)


# =============================================================================
# STATE TRANSITION PROOF
# =============================================================================


@dataclass
class StateTransitionProof:
    """
    Immutable proof of a state transition.

    This proof is emitted when a governed transition is validated.
    It provides an auditable record of:
    - What changed (artifact, states)
    - Who authorized it (authority)
    - Why it was allowed (triggering proof)
    - When it happened (timestamp)
    - Cryptographic binding (hash)
    """

    proof_id: str = field(default_factory=lambda: f"STP-{uuid4().hex[:16]}")
    artifact_type: str = ""
    artifact_id: str = ""
    from_state: str = ""
    to_state: str = ""
    triggering_proof_id: Optional[str] = None
    authority_gid: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Compute hash after initialization."""
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """
        Compute deterministic SHA-256 hash of transition proof.

        Hash input: artifact_id + from_state + to_state + timestamp (ISO)
        """
        hash_input = (
            f"{self.artifact_id}|{self.from_state}|{self.to_state}|"
            f"{self.timestamp.isoformat()}"
        )
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def verify_hash(self) -> bool:
        """Verify the stored hash matches recomputed hash."""
        return self.hash == self._compute_hash()

    def to_dict(self) -> dict[str, Any]:
        """Serialize proof for storage/transmission."""
        return {
            "proof_id": self.proof_id,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "triggering_proof_id": self.triggering_proof_id,
            "authority_gid": self.authority_gid,
            "timestamp": self.timestamp.isoformat(),
            "hash": self.hash,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Serialize proof to JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StateTransitionProof":
        """Deserialize proof from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            proof_id=data.get("proof_id", f"STP-{uuid4().hex[:16]}"),
            artifact_type=data.get("artifact_type", ""),
            artifact_id=data.get("artifact_id", ""),
            from_state=data.get("from_state", ""),
            to_state=data.get("to_state", ""),
            triggering_proof_id=data.get("triggering_proof_id"),
            authority_gid=data.get("authority_gid"),
            timestamp=timestamp,
            hash=data.get("hash", ""),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# TRANSITION PROOF EMITTER
# =============================================================================


class TransitionProofEmitter:
    """
    Emits transition proofs for validated state changes.

    This emitter is READ-ONLY. It creates proof artifacts
    but does not persist them directly. Persistence is
    delegated to the caller.

    Usage:
        emitter = TransitionProofEmitter()
        proof = emitter.emit(request, validation_result)
        # Caller persists proof
    """

    def __init__(self) -> None:
        """Initialize the emitter."""
        self._emission_count = 0

    def emit(
        self,
        request: TransitionRequest,
        validation_result: TransitionValidationResult,
    ) -> Optional[StateTransitionProof]:
        """
        Emit a transition proof for a validated transition.

        Returns None if the transition was not allowed.
        This method has NO SIDE EFFECTS on system state.
        """
        # Only emit proofs for allowed transitions
        if not validation_result.is_allowed:
            return None

        self._emission_count += 1

        proof = StateTransitionProof(
            artifact_type=request.artifact_type,
            artifact_id=request.artifact_id,
            from_state=request.from_state,
            to_state=request.to_state,
            triggering_proof_id=request.proof_id,
            authority_gid=request.authority_gid,
            timestamp=request.timestamp,
            metadata={
                "validation_result": validation_result.result.value,
                "required_authority": validation_result.required_authority,
                "request_metadata": request.metadata,
            },
        )

        return proof

    def emit_batch(
        self,
        requests: list[TransitionRequest],
        results: list[TransitionValidationResult],
    ) -> list[StateTransitionProof]:
        """
        Emit proofs for a batch of validated transitions.

        Only emits proofs for allowed transitions.
        """
        proofs: list[StateTransitionProof] = []
        for request, result in zip(requests, results):
            proof = self.emit(request, result)
            if proof:
                proofs.append(proof)
        return proofs

    @property
    def emission_count(self) -> int:
        """Number of proofs emitted by this instance."""
        return self._emission_count


# =============================================================================
# PROOF VERIFICATION
# =============================================================================


def verify_transition_proof(proof: StateTransitionProof) -> bool:
    """Verify a transition proof's integrity."""
    return proof.verify_hash()


def verify_proof_chain(proofs: list[StateTransitionProof]) -> tuple[bool, list[str]]:
    """
    Verify a chain of transition proofs.

    Checks:
    1. Each proof's hash is valid
    2. Transitions are temporally ordered
    3. State continuity (to_state of N matches from_state of N+1)

    Returns (is_valid, list of errors).
    """
    errors: list[str] = []

    if not proofs:
        return True, []

    # Verify individual proof hashes
    for i, proof in enumerate(proofs):
        if not proof.verify_hash():
            errors.append(f"Proof {i} ({proof.proof_id}): hash verification failed")

    # Sort by timestamp for continuity checks
    sorted_proofs = sorted(proofs, key=lambda p: p.timestamp)

    # Check temporal ordering
    for i in range(1, len(sorted_proofs)):
        if sorted_proofs[i].timestamp < sorted_proofs[i - 1].timestamp:
            errors.append(
                f"Proof {i}: timestamp out of order "
                f"({sorted_proofs[i].timestamp} < {sorted_proofs[i - 1].timestamp})"
            )

    # Check state continuity (if same artifact)
    artifact_proofs: dict[tuple[str, str], list[StateTransitionProof]] = {}
    for proof in sorted_proofs:
        key = (proof.artifact_type, proof.artifact_id)
        if key not in artifact_proofs:
            artifact_proofs[key] = []
        artifact_proofs[key].append(proof)

    for (atype, aid), chain in artifact_proofs.items():
        for i in range(1, len(chain)):
            if chain[i].from_state != chain[i - 1].to_state:
                errors.append(
                    f"State discontinuity for {atype}/{aid}: "
                    f"proof {i-1} ended at {chain[i - 1].to_state}, "
                    f"proof {i} starts at {chain[i].from_state}"
                )

    return len(errors) == 0, errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def create_transition_proof(
    artifact_type: str,
    artifact_id: str,
    from_state: str,
    to_state: str,
    authority_gid: Optional[str] = None,
    triggering_proof_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> StateTransitionProof:
    """Convenience function to create a transition proof directly."""
    return StateTransitionProof(
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        from_state=from_state,
        to_state=to_state,
        triggering_proof_id=triggering_proof_id,
        authority_gid=authority_gid,
        metadata=metadata or {},
    )
