"""
Spine Executor - PAC-BENSON-EXEC-SPINE-01

Full execution flow: Event → Decision → Action → Proof

CONSTRAINTS:
- Real side effects (state transition, database write)
- Must fail loudly (no silent failures)
- Proof generation is mandatory
- Append-only persistence

This is the irreducible core of ChainBridge.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from core.spine.decision import DecisionEngine, DecisionOutcome, DecisionResult
from core.spine.event import SpineEvent

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions that can be executed."""
    STATE_TRANSITION = "state_transition"
    DATABASE_WRITE = "database_write"
    OUTBOUND_CALL = "outbound_call"


class ActionStatus(str, Enum):
    """Action execution status."""
    SUCCESS = "success"
    FAILED = "failed"


class ActionResult(BaseModel):
    """
    Result of an action execution.
    
    Actions must succeed or fail explicitly - no ambiguous states.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique action identifier")
    decision_id: UUID = Field(..., description="ID of the triggering decision")
    action_type: ActionType = Field(..., description="Type of action executed")
    status: ActionStatus = Field(..., description="Execution status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Action-specific details")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO8601 timestamp of action execution"
    )
    
    model_config = {"frozen": True}  # Immutable


class ExecutionProof(BaseModel):
    """
    Immutable proof artifact for a complete execution.
    
    Contains:
    - Event hash
    - Decision inputs
    - Decision output
    - Action result
    - Timestamp
    
    This is the canonical proof format per PAC-BENSON-EXEC-SPINE-01.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique proof identifier")
    version: str = Field(default="1.0.0", description="Proof schema version")
    
    # Event data
    event_id: UUID = Field(..., description="ID of the triggering event")
    event_hash: str = Field(..., description="SHA-256 hash of the event")
    event_type: str = Field(..., description="Type of the event")
    event_timestamp: str = Field(..., description="When the event was created")
    
    # Decision data
    decision_id: UUID = Field(..., description="ID of the decision")
    decision_hash: str = Field(..., description="SHA-256 hash of the decision")
    decision_outcome: str = Field(..., description="Outcome of the decision")
    decision_rule: str = Field(..., description="Rule that was applied")
    decision_rule_version: str = Field(..., description="Version of the rule")
    decision_inputs: Dict[str, Any] = Field(..., description="Inputs used in decision")
    decision_explanation: str = Field(..., description="Human-readable explanation")
    
    # Action data
    action_id: UUID = Field(..., description="ID of the action")
    action_type: str = Field(..., description="Type of action executed")
    action_status: str = Field(..., description="Execution status")
    action_details: Dict[str, Any] = Field(..., description="Action-specific details")
    action_error: Optional[str] = Field(None, description="Error if action failed")
    
    # Proof metadata
    proof_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the proof was generated"
    )
    
    model_config = {"frozen": True}  # Immutable
    
    def compute_hash(self) -> str:
        """Compute deterministic SHA-256 hash of the proof."""
        canonical = json.dumps(
            self.model_dump(exclude={"id"}),  # Exclude id for content-based hash
            sort_keys=True,
            separators=(",", ":"),
            default=str,  # Handle UUIDs
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    
    def to_canonical_json(self) -> str:
        """Export proof as canonical JSON for verification."""
        return json.dumps(
            self.model_dump(),
            sort_keys=True,
            indent=2,
            default=str,
        )


class ProofStore:
    """
    Append-only proof persistence.
    
    Stores proofs as individual JSON files in an append-only manner.
    Files are never modified after creation.
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize proof store.
        
        Args:
            storage_dir: Directory for proof storage. Defaults to
                         CHAINBRIDGE_PROOF_STORE_PATH env var or ./proofpacks/runtime/spine
        """
        self._storage_dir = Path(
            storage_dir or 
            os.environ.get("CHAINBRIDGE_PROOF_STORE_PATH", "./proofpacks/runtime/spine")
        )
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ProofStore initialized at: {self._storage_dir}")
    
    def persist(self, proof: ExecutionProof) -> Path:
        """
        Persist a proof artifact (append-only).
        
        Args:
            proof: The execution proof to persist
            
        Returns:
            Path to the persisted proof file
            
        Raises:
            IOError: If persistence fails
        """
        proof_hash = proof.compute_hash()
        filename = f"proof_{proof.id}_{proof_hash[:8]}.json"
        filepath = self._storage_dir / filename
        
        if filepath.exists():
            raise IOError(f"Proof file already exists (append-only violation): {filepath}")
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(proof.to_canonical_json())
            
            logger.info(f"Proof persisted: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to persist proof: {e}")
            raise IOError(f"Proof persistence failed: {e}") from e
    
    def load(self, proof_id: UUID) -> Optional[ExecutionProof]:
        """Load a proof by ID (for verification)."""
        for filepath in self._storage_dir.glob(f"proof_{proof_id}_*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return ExecutionProof.model_validate(data)
            except Exception as e:
                logger.error(f"Failed to load proof {filepath}: {e}")
        return None


class SpineExecutor:
    """
    The Minimum Execution Spine.
    
    Executes the canonical flow:
    Event → Decision → Action → Proof
    
    No mocks. No slides. No narration.
    Real execution with real proof.
    """
    
    def __init__(self, proof_store: Optional[ProofStore] = None):
        """Initialize executor with proof store."""
        self._proof_store = proof_store or ProofStore()
        self._state: Dict[str, Any] = {}  # Internal state for state transitions
    
    def execute(self, event: SpineEvent) -> ExecutionProof:
        """
        Execute the full spine flow.
        
        Args:
            event: The triggering event
            
        Returns:
            ExecutionProof containing complete audit trail
            
        Raises:
            Exception: On any failure (fails loudly)
        """
        logger.info(f"Spine execution started: event_id={event.id}")
        
        # Step 1: Decision (pure function)
        decision = DecisionEngine.decide(event)
        logger.info(f"Decision computed: outcome={decision.outcome}, rule={decision.rule_applied}")
        
        # Step 2: Action (real side effect)
        action = self._execute_action(decision)
        logger.info(f"Action executed: type={action.action_type}, status={action.status}")
        
        # Step 3: Generate proof
        proof = self._generate_proof(event, decision, action)
        logger.info(f"Proof generated: hash={proof.compute_hash()[:16]}...")
        
        # Step 4: Persist proof (append-only)
        proof_path = self._proof_store.persist(proof)
        logger.info(f"Proof persisted: {proof_path}")
        
        return proof
    
    def _execute_action(self, decision: DecisionResult) -> ActionResult:
        """
        Execute the action based on decision outcome.
        
        Actions are REAL side effects. This is not a mock.
        """
        try:
            if decision.outcome == DecisionOutcome.APPROVED:
                # Real action: State transition to APPROVED
                return self._action_approve_payment(decision)
            
            elif decision.outcome == DecisionOutcome.REQUIRES_REVIEW:
                # Real action: State transition to PENDING_REVIEW
                return self._action_queue_for_review(decision)
            
            elif decision.outcome == DecisionOutcome.REJECTED:
                # Real action: State transition to REJECTED
                return self._action_reject_payment(decision)
            
            else:
                # Error outcome
                return self._action_log_error(decision)
                
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return ActionResult(
                decision_id=decision.id,
                action_type=ActionType.STATE_TRANSITION,
                status=ActionStatus.FAILED,
                error_message=str(e),
            )
    
    def _action_approve_payment(self, decision: DecisionResult) -> ActionResult:
        """Execute payment approval action."""
        # Real state transition
        state_key = f"payment_{decision.event_id}"
        self._state[state_key] = {
            "status": "APPROVED",
            "decision_id": str(decision.id),
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "amount": decision.inputs_snapshot.get("amount"),
        }
        
        return ActionResult(
            decision_id=decision.id,
            action_type=ActionType.STATE_TRANSITION,
            status=ActionStatus.SUCCESS,
            details={
                "state_key": state_key,
                "new_status": "APPROVED",
                "amount": decision.inputs_snapshot.get("amount"),
            },
        )
    
    def _action_queue_for_review(self, decision: DecisionResult) -> ActionResult:
        """Queue payment for manual review."""
        state_key = f"payment_{decision.event_id}"
        self._state[state_key] = {
            "status": "PENDING_REVIEW",
            "decision_id": str(decision.id),
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "amount": decision.inputs_snapshot.get("amount"),
            "requires_approval_from": "senior_approver",
        }
        
        return ActionResult(
            decision_id=decision.id,
            action_type=ActionType.STATE_TRANSITION,
            status=ActionStatus.SUCCESS,
            details={
                "state_key": state_key,
                "new_status": "PENDING_REVIEW",
                "amount": decision.inputs_snapshot.get("amount"),
                "review_queue": "senior_approvals",
            },
        )
    
    def _action_reject_payment(self, decision: DecisionResult) -> ActionResult:
        """Execute payment rejection action."""
        state_key = f"payment_{decision.event_id}"
        self._state[state_key] = {
            "status": "REJECTED",
            "decision_id": str(decision.id),
            "rejected_at": datetime.now(timezone.utc).isoformat(),
        }
        
        return ActionResult(
            decision_id=decision.id,
            action_type=ActionType.STATE_TRANSITION,
            status=ActionStatus.SUCCESS,
            details={
                "state_key": state_key,
                "new_status": "REJECTED",
            },
        )
    
    def _action_log_error(self, decision: DecisionResult) -> ActionResult:
        """Log error for failed decisions."""
        return ActionResult(
            decision_id=decision.id,
            action_type=ActionType.STATE_TRANSITION,
            status=ActionStatus.FAILED,
            error_message=decision.explanation,
            details={"outcome": decision.outcome.value},
        )
    
    def _generate_proof(
        self, 
        event: SpineEvent, 
        decision: DecisionResult, 
        action: ActionResult
    ) -> ExecutionProof:
        """Generate immutable execution proof."""
        return ExecutionProof(
            # Event
            event_id=event.id,
            event_hash=event.compute_hash(),
            event_type=event.event_type.value,
            event_timestamp=event.timestamp,
            
            # Decision
            decision_id=decision.id,
            decision_hash=decision.compute_hash(),
            decision_outcome=decision.outcome.value,
            decision_rule=decision.rule_applied,
            decision_rule_version=decision.rule_version,
            decision_inputs=decision.inputs_snapshot,
            decision_explanation=decision.explanation,
            
            # Action
            action_id=action.id,
            action_type=action.action_type.value,
            action_status=action.status.value,
            action_details=action.details,
            action_error=action.error_message,
        )
    
    def get_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Get current state (for verification)."""
        return self._state.get(key)
