"""
Decision Pydantic Models (v2 syntax)

Decisions represent governance-tracked choices made by agents/systems.
Each decision is immutably linked to:
- The artifact(s) it affects
- A ProofPack for verifiable audit
- Input state at decision time (for deterministic replay)

Author: CINDY (GID-04) - Backend
"""

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DecisionType(str, Enum):
    """Classification of decision types."""

    SETTLEMENT = "Settlement"  # Payment release decisions
    RISK_OVERRIDE = "RiskOverride"  # Manual risk adjustments
    ESCALATION = "Escalation"  # Escalated to human review
    APPROVAL = "Approval"  # General approvals
    REJECTION = "Rejection"  # General rejections
    POLICY_CHANGE = "PolicyChange"  # Policy/rule modifications
    SYSTEM = "System"  # Automated system decisions


class DecisionOutcome(str, Enum):
    """Outcome/result of a decision."""

    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class DecisionInputSnapshot(BaseModel):
    """
    Immutable snapshot of all inputs at decision time.

    This enables deterministic replay: given the same inputs,
    the decision logic should produce the same output.
    """

    model_config = ConfigDict(use_enum_values=True)

    # Core identifiers
    shipment_id: Optional[str] = Field(None, description="Shipment this decision concerns")
    payment_intent_id: Optional[str] = Field(None, description="Payment intent if applicable")
    artifact_id: Optional[UUID] = Field(None, description="Related artifact ID")

    # Risk inputs
    risk_score: Optional[float] = Field(None, ge=0, le=100, description="Risk score at decision time")
    risk_band: Optional[str] = Field(None, description="Risk band (LOW/MODERATE/HIGH/CRITICAL)")
    risk_factors: List[Dict[str, Any]] = Field(default_factory=list, description="Risk factor breakdown")

    # Policy inputs
    policy_version: Optional[str] = Field(None, description="Policy version used")
    policy_rules_applied: List[str] = Field(default_factory=list, description="Rules evaluated")

    # Entity context
    counterparty_id: Optional[str] = Field(None, description="Counterparty identifier")
    corridor: Optional[str] = Field(None, description="Trade corridor (e.g., US-MX)")

    # Additional context (flexible)
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional decision context")

    # Timestamp
    captured_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When snapshot was captured",
    )

    def compute_hash(self) -> str:
        """Compute deterministic hash of input snapshot."""
        canonical = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


class DecisionCreate(BaseModel):
    """Schema for creating a new decision."""

    model_config = ConfigDict(use_enum_values=True)

    # Decision metadata
    decision_type: DecisionType = Field(..., description="Type of decision")
    outcome: DecisionOutcome = Field(..., description="Decision outcome")
    rationale: str = Field(..., min_length=1, max_length=2000, description="Human-readable explanation")

    # Actor
    actor: str = Field(..., description="Who/what made the decision (agent GID or system)")
    actor_type: str = Field(default="system", description="Type: 'agent', 'human', 'system'")

    # Input state (required for replay)
    input_snapshot: DecisionInputSnapshot = Field(..., description="Immutable input state snapshot")

    # Linkages
    artifact_ids: List[UUID] = Field(default_factory=list, description="Related artifact IDs")
    parent_decision_id: Optional[UUID] = Field(None, description="Parent decision if this is derived")

    # Confidence
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Decision confidence (0-1)")

    # Tags
    tags: List[str] = Field(default_factory=list, description="Categorization tags")


class Decision(BaseModel):
    """
    Full decision model with server-generated fields.

    Decisions are immutable once created. State changes are
    tracked via linked audit events and new decisions.
    """

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)

    # Identity
    id: UUID = Field(default_factory=uuid4, description="Unique decision identifier")
    sequence_number: int = Field(default=0, description="Monotonic sequence for ordering")

    # Decision metadata
    decision_type: DecisionType = Field(..., description="Type of decision")
    outcome: DecisionOutcome = Field(..., description="Decision outcome")
    rationale: str = Field(..., description="Human-readable explanation")

    # Actor
    actor: str = Field(..., description="Who/what made the decision")
    actor_type: str = Field(default="system", description="Type: 'agent', 'human', 'system'")

    # Input state (immutable snapshot)
    input_snapshot: DecisionInputSnapshot = Field(..., description="Input state at decision time")
    input_hash: str = Field(..., description="Hash of input snapshot (for replay verification)")

    # Linkages
    artifact_ids: List[UUID] = Field(default_factory=list, description="Related artifact IDs")
    proofpack_id: Optional[UUID] = Field(None, description="Linked ProofPack ID")
    parent_decision_id: Optional[UUID] = Field(None, description="Parent decision ID")

    # Confidence & validation
    confidence: Optional[float] = Field(None, description="Decision confidence (0-1)")
    is_replayed: bool = Field(default=False, description="Whether this was generated via replay")
    replay_source_id: Optional[UUID] = Field(None, description="Original decision ID if replayed")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When decision was created",
    )

    # Tags
    tags: List[str] = Field(default_factory=list, description="Categorization tags")


class DecisionReplayRequest(BaseModel):
    """Request to replay a decision with its original inputs."""

    decision_id: UUID = Field(..., description="ID of decision to replay")
    dry_run: bool = Field(default=True, description="If true, don't persist the replayed decision")
    compare_output: bool = Field(default=True, description="Compare replay output with original")


class DecisionReplayResult(BaseModel):
    """Result of a decision replay operation."""

    original_decision_id: UUID
    replayed_decision: Decision
    is_deterministic: bool = Field(..., description="True if replay produced identical outcome")
    differences: List[str] = Field(default_factory=list, description="List of differences if any")
    input_hash_match: bool = Field(..., description="True if input hashes match")
    replay_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class DecisionTimeTravelQuery(BaseModel):
    """Query for time-travel audit: view decisions at a point in time."""

    # Target identifiers (at least one required)
    artifact_id: Optional[UUID] = Field(None, description="Artifact to query decisions for")
    shipment_id: Optional[str] = Field(None, description="Shipment to query decisions for")

    # Time window
    as_of: datetime = Field(..., description="Point-in-time to query (UTC)")
    window_start: Optional[datetime] = Field(None, description="Start of time window (optional)")

    # Filters
    decision_types: Optional[List[DecisionType]] = Field(None, description="Filter by decision types")
    actors: Optional[List[str]] = Field(None, description="Filter by actors")

    # Options
    include_input_snapshots: bool = Field(default=True, description="Include full input snapshots")
    include_linked_events: bool = Field(default=False, description="Include linked audit events")


class DecisionTimeTravelResult(BaseModel):
    """Result of a time-travel query."""

    query: DecisionTimeTravelQuery
    decisions: List[Decision] = Field(..., description="Decisions matching the query")
    count: int = Field(..., description="Number of decisions returned")
    state_hash: str = Field(..., description="Hash of decision state at query time")
    queried_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class DecisionListResponse(BaseModel):
    """Response for listing decisions."""

    items: List[Decision]
    count: int
    total: int
    limit: Optional[int]
    offset: int
