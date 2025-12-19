"""
Decision Engine - PAC-BENSON-EXEC-SPINE-01

Pure function decision logic for the Minimum Execution Spine.

CONSTRAINTS:
- Pure function: same inputs → same outputs
- Rule-based or glass-box logic ONLY
- Inputs and outputs fully logged
- No side effects in decision computation

Decision Rule (V1 - LOCKED):
- Payment requests ≤ $10,000: APPROVED
- Payment requests > $10,000: REQUIRES_REVIEW
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from core.spine.event import SpineEvent, SpineEventType


class DecisionOutcome(str, Enum):
    """Deterministic decision outcomes."""
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"
    ERROR = "error"


class DecisionResult(BaseModel):
    """
    Immutable decision result with full traceability.
    
    Contains all inputs used in the decision for auditability.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique decision identifier")
    event_id: UUID = Field(..., description="ID of the triggering event")
    event_hash: str = Field(..., description="Hash of the triggering event")
    outcome: DecisionOutcome = Field(..., description="Decision outcome")
    rule_applied: str = Field(..., description="Name of the rule that produced this decision")
    rule_version: str = Field(..., description="Version of the rule")
    inputs_snapshot: Dict[str, Any] = Field(..., description="Snapshot of all inputs used")
    explanation: str = Field(..., description="Human-readable explanation of decision")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO8601 timestamp of decision"
    )
    
    model_config = {"frozen": True}  # Immutable
    
    def compute_hash(self) -> str:
        """Compute deterministic SHA-256 hash of this decision."""
        canonical = json.dumps(
            {
                "id": str(self.id),
                "event_id": str(self.event_id),
                "event_hash": self.event_hash,
                "outcome": self.outcome.value,
                "rule_applied": self.rule_applied,
                "rule_version": self.rule_version,
                "inputs_snapshot": self.inputs_snapshot,
                "explanation": self.explanation,
                "timestamp": self.timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class DecisionEngine:
    """
    Pure function decision engine.
    
    Rule-based, deterministic, fully traceable.
    No side effects during decision computation.
    """
    
    # V1 Decision Rule Configuration (LOCKED)
    PAYMENT_THRESHOLD = 10_000.00  # USD
    RULE_NAME = "payment_threshold_v1"
    RULE_VERSION = "1.0.0"
    
    @classmethod
    def decide(cls, event: SpineEvent) -> DecisionResult:
        """
        Execute deterministic decision logic.
        
        Args:
            event: The triggering event
            
        Returns:
            Immutable DecisionResult with full traceability
            
        Raises:
            ValueError: If event type is not supported
        """
        if event.event_type != SpineEventType.PAYMENT_REQUEST:
            return cls._create_error_result(
                event=event,
                explanation=f"Unsupported event type: {event.event_type}",
            )
        
        return cls._decide_payment_request(event)
    
    @classmethod
    def _decide_payment_request(cls, event: SpineEvent) -> DecisionResult:
        """
        V1 Decision Rule: Payment Threshold
        
        Rule (LOCKED):
        - amount ≤ 10,000: APPROVED
        - amount > 10,000: REQUIRES_REVIEW
        """
        payload = event.payload
        
        # Extract and validate required field
        amount = payload.get("amount")
        if amount is None:
            return cls._create_error_result(
                event=event,
                explanation="Missing required field: amount",
            )
        
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return cls._create_error_result(
                event=event,
                explanation=f"Invalid amount type: {type(amount).__name__}",
            )
        
        # Build inputs snapshot for auditability
        inputs_snapshot = {
            "amount": amount,
            "currency": payload.get("currency", "USD"),
            "vendor_id": payload.get("vendor_id"),
            "requestor_id": payload.get("requestor_id"),
            "threshold": cls.PAYMENT_THRESHOLD,
        }
        
        # Apply deterministic rule
        if amount <= cls.PAYMENT_THRESHOLD:
            return DecisionResult(
                event_id=event.id,
                event_hash=event.compute_hash(),
                outcome=DecisionOutcome.APPROVED,
                rule_applied=cls.RULE_NAME,
                rule_version=cls.RULE_VERSION,
                inputs_snapshot=inputs_snapshot,
                explanation=f"Payment of ${amount:.2f} is within threshold of ${cls.PAYMENT_THRESHOLD:.2f}",
            )
        else:
            return DecisionResult(
                event_id=event.id,
                event_hash=event.compute_hash(),
                outcome=DecisionOutcome.REQUIRES_REVIEW,
                rule_applied=cls.RULE_NAME,
                rule_version=cls.RULE_VERSION,
                inputs_snapshot=inputs_snapshot,
                explanation=f"Payment of ${amount:.2f} exceeds threshold of ${cls.PAYMENT_THRESHOLD:.2f}",
            )
    
    @classmethod
    def _create_error_result(cls, event: SpineEvent, explanation: str) -> DecisionResult:
        """Create an error decision result."""
        return DecisionResult(
            event_id=event.id,
            event_hash=event.compute_hash(),
            outcome=DecisionOutcome.ERROR,
            rule_applied=cls.RULE_NAME,
            rule_version=cls.RULE_VERSION,
            inputs_snapshot={"raw_payload": event.payload},
            explanation=explanation,
        )
