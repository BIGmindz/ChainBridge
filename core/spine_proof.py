"""
core/spine_proof.py - Proof Artifact for Execution Spine
PAC-CODY-EXEC-SPINE-01 / PAC-CODY-EXEC-SPINE-INTEGRATION-02

Structured proof artifact:
- Links event → decision → action
- Deterministic hash from canonical fields
- Persisted append-only

PROOF SCHEMA:
- proof_id: UUID
- event_id: UUID
- event_hash: SHA-256 of event
- decision: decision outcome + explanation
- action_result: action status + details
- proof_hash: SHA-256 of entire proof (excluding proof_hash itself)
- timestamp: ISO8601
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from core.actions import ActionResult
from core.decisions import DecisionResult
from core.events import IngestEvent

logger = logging.getLogger(__name__)

# Proof storage directory (append-only)
PROOF_STORE_DIR = Path(os.getenv("PROOF_STORE_DIR", "proofpacks/spine"))


@dataclass
class ProofArtifact:
    """
    Immutable proof artifact linking event → decision → action.
    
    All fields except proof_hash are used to compute the proof_hash.
    proof_hash is computed after all other fields are set.
    """
    proof_id: UUID
    event_id: str
    event_hash: str
    event_type: str
    event_payload: Dict[str, Any]
    event_timestamp: str
    decision_outcome: str
    decision_reason: str
    decision_rule: str
    action_type: str
    action_status: str
    action_details: Dict[str, Any]
    action_error: Optional[str]
    timestamp: str
    proof_hash: str = field(default="")
    
    def __post_init__(self):
        """Compute proof_hash after initialization if not set."""
        if not self.proof_hash:
            self.proof_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """
        Compute deterministic SHA-256 hash of proof.
        
        Uses all fields except proof_hash itself.
        Canonical JSON encoding (sorted keys, no whitespace).
        """
        canonical_data = {
            "proof_id": str(self.proof_id),
            "event_id": self.event_id,
            "event_hash": self.event_hash,
            "event_type": self.event_type,
            "event_payload": self.event_payload,
            "event_timestamp": self.event_timestamp,
            "decision_outcome": self.decision_outcome,
            "decision_reason": self.decision_reason,
            "decision_rule": self.decision_rule,
            "action_type": self.action_type,
            "action_status": self.action_status,
            "action_details": self.action_details,
            "action_error": self.action_error,
            "timestamp": self.timestamp,
        }
        canonical = json.dumps(canonical_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "proof_id": str(self.proof_id),
            "event_id": self.event_id,
            "event_hash": self.event_hash,
            "event_type": self.event_type,
            "event_payload": self.event_payload,
            "event_timestamp": self.event_timestamp,
            "decision_outcome": self.decision_outcome,
            "decision_reason": self.decision_reason,
            "decision_rule": self.decision_rule,
            "action_type": self.action_type,
            "action_status": self.action_status,
            "action_details": self.action_details,
            "action_error": self.action_error,
            "timestamp": self.timestamp,
            "proof_hash": self.proof_hash,
        }
    
    def verify_hash(self) -> bool:
        """Verify that proof_hash matches computed hash."""
        return self.proof_hash == self._compute_hash()


def build_proof(
    event: IngestEvent,
    decision: DecisionResult,
    action_result: ActionResult,
) -> ProofArtifact:
    """
    Build proof artifact from event, decision, and action result.
    
    Args:
        event: The original IngestEvent
        decision: The DecisionResult from core/decisions
        action_result: The ActionResult from executing the decision
        
    Returns:
        ProofArtifact with computed proof_hash
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    proof = ProofArtifact(
        proof_id=uuid4(),
        event_id=str(event.event_id),
        event_hash=event.compute_hash(),
        event_type=event.event_type,
        event_payload=event.payload,
        event_timestamp=event.timestamp,
        decision_outcome=decision.outcome.value,
        decision_reason=decision.explanation,
        decision_rule=decision.rule_id,
        action_type=action_result.action_type,
        action_status=action_result.status.value,
        action_details=action_result.details,
        action_error=action_result.error,
        timestamp=timestamp,
    )
    
    logger.info(
        "build_proof: proof artifact created",
        extra={
            "proof_id": str(proof.proof_id),
            "event_id": proof.event_id,
            "proof_hash": proof.proof_hash,
        }
    )
    
    return proof


def persist_proof(proof: ProofArtifact) -> str:
    """
    Persist proof artifact to append-only storage.
    
    Creates storage directory if it doesn't exist.
    Each proof is stored as a separate JSON file named by proof_id.
    Also appends to proof_log.jsonl for append-only audit trail.
    
    Args:
        proof: The ProofArtifact to persist
        
    Returns:
        Path to the persisted proof file
    """
    PROOF_STORE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write individual proof file
    proof_file = PROOF_STORE_DIR / f"{proof.proof_id}.json"
    proof_dict = proof.to_dict()
    
    with open(proof_file, "w", encoding="utf-8") as f:
        json.dump(proof_dict, f, indent=2, sort_keys=True)
    
    # Append to proof log (append-only audit trail)
    log_file = PROOF_STORE_DIR / "proof_log.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(proof_dict, sort_keys=True, separators=(",", ":")) + "\n")
    
    logger.info(
        "persist_proof: proof persisted",
        extra={
            "proof_id": str(proof.proof_id),
            "proof_file": str(proof_file),
            "proof_hash": proof.proof_hash,
        }
    )
    
    return str(proof_file)


def load_proof(proof_id: str) -> Optional[ProofArtifact]:
    """
    Load proof artifact from storage by proof_id.
    
    Args:
        proof_id: The UUID of the proof to load
        
    Returns:
        ProofArtifact if found, None otherwise
    """
    proof_file = PROOF_STORE_DIR / f"{proof_id}.json"
    
    if not proof_file.exists():
        logger.warning(
            "load_proof: proof not found",
            extra={"proof_id": proof_id}
        )
        return None
    
    with open(proof_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    proof = ProofArtifact(
        proof_id=UUID(data["proof_id"]),
        event_id=data["event_id"],
        event_hash=data["event_hash"],
        event_type=data["event_type"],
        event_payload=data["event_payload"],
        event_timestamp=data["event_timestamp"],
        decision_outcome=data["decision_outcome"],
        decision_reason=data["decision_reason"],
        decision_rule=data["decision_rule"],
        action_type=data["action_type"],
        action_status=data["action_status"],
        action_details=data["action_details"],
        action_error=data.get("action_error"),
        timestamp=data["timestamp"],
        proof_hash=data["proof_hash"],
    )
    
    # Verify integrity
    if not proof.verify_hash():
        logger.error(
            "load_proof: proof hash mismatch - integrity violation",
            extra={"proof_id": proof_id}
        )
        raise ValueError(f"Proof {proof_id} failed integrity check - hash mismatch")
    
    return proof
