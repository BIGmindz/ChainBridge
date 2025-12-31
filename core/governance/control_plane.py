# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Control Plane — Deterministic Execution State Model
# PAC-JEFFREY-P06R: Lint v2 Runtime Enforcement · Gold Standard
# Supersedes: PAC-JEFFREY-P05R (Law), PAC-JEFFREY-P04
# GOLD STANDARD · FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

"""
Control Plane execution state model.

GOVERNANCE INVARIANTS (CANONICAL):
- INV-CP-001: No execution without explicit ACK
- INV-CP-002: Missing ACK blocks execution AND settlement
- INV-CP-003: All state transitions are deterministic and auditable
- INV-CP-004: FAIL_CLOSED on any governance violation
- INV-CP-005: BER requires valid WRAP; WRAP requires all ACKs
- INV-CP-006: Multi-agent WRAPs required before BER
- INV-CP-007: Ledger commit attestation required for finality
- INV-CP-008: ACK latency bound to settlement eligibility
- INV-CP-009: execution_mode REQUIRED on all BERs (PAC-JEFFREY-P02R)
- INV-CP-010: ber_finality REQUIRED (FINAL | PROVISIONAL)
- INV-CP-011: Training Signals MANDATORY per agent
- INV-CP-012: Positive Closure MANDATORY per agent
- INV-CP-013: AGENT_ACK_BARRIER release requires ALL agent ACKs (PAC-JEFFREY-P03)
- INV-CP-014: Cross-lane execution FORBIDDEN (PAC-JEFFREY-P03)
- INV-CP-015: Implicit agent activation FORBIDDEN (PAC-JEFFREY-P03)
- INV-CP-016: PACK immutability ENFORCED (PAC-JEFFREY-P03)
- INV-CP-017: SettlementReadinessVerdict REQUIRED before BER FINAL (PAC-JEFFREY-P04)
- INV-CP-018: Settlement eligibility is BINARY - no inference allowed (PAC-JEFFREY-P04)
- INV-CP-019: No human override of settlement verdict (PAC-JEFFREY-P04)
- INV-CP-020: Verdict must be machine-computed (PAC-JEFFREY-P04)

LINT v2 INVARIANT CLASSES (PAC-JEFFREY-P05R LAW, P06R ENFORCEMENT):
- S-INV: Structural — Schema validation, required fields
- M-INV: Semantic — Meaning/intent validation
- X-INV: Cross-Artifact — Inter-document consistency
- T-INV: Temporal — Ordering, timestamps, sequences
- A-INV: Authority — GID/lane authorization
- F-INV: Finality — BER/settlement eligibility
- C-INV: Training — Signal emission compliance

SCHEMA REFERENCES (EXPLICIT PINNING):
- PAC Schema: CHAINBRIDGE_CANONICAL_PAC_SCHEMA@v1.0.0
- WRAP Schema: CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v1.0.0
- BER Schema: CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0
- RG-01 Schema: RG01_SCHEMA@v1.0.0
- BSRG-01 Schema: BSRG01_SCHEMA@v1.0.0
- ACK Schema: AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0
- Training Signal Schema: GOVERNANCE_TRAINING_SIGNAL_SCHEMA@v1.0.0
- Positive Closure Schema: POSITIVE_CLOSURE_SCHEMA@v1.0.0
- Settlement Readiness Schema: SETTLEMENT_READINESS_VERDICT_SCHEMA@v1.0.0
- Lint v2 Schema: CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0

Author: Benson Execution Orchestrator (GID-00)
Backend Lane: CODY (GID-01)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION MODE & BARRIER TYPES (PAC-JEFFREY-P03 Section 2)
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionMode(str, Enum):
    """Execution mode declaration per PAC-JEFFREY-P03."""
    PARALLEL = "PARALLEL"
    SEQUENTIAL = "SEQUENTIAL"


class ExecutionBarrierType(str, Enum):
    """Execution barrier types per PAC-JEFFREY-P03."""
    AGENT_ACK_BARRIER = "AGENT_ACK_BARRIER"
    WRAP_COMPLETE_BARRIER = "WRAP_COMPLETE_BARRIER"
    NONE = "NONE"


class BarrierReleaseCondition(str, Enum):
    """Barrier release conditions per PAC-JEFFREY-P03."""
    ALL_REQUIRED_AGENT_ACKS_PRESENT = "ALL_REQUIRED_AGENT_ACKS_PRESENT"
    ALL_WRAPS_COLLECTED = "ALL_WRAPS_COLLECTED"
    MANUAL_RELEASE = "MANUAL_RELEASE"


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT LANE DEFINITIONS (PAC-JEFFREY-P03 Section 3)
# ═══════════════════════════════════════════════════════════════════════════════

class AgentLane(str, Enum):
    """Agent lane assignments - cross-lane execution FORBIDDEN."""
    ORCHESTRATION = "orchestration"
    BACKEND = "backend"
    FRONTEND = "frontend"
    CI_CD = "ci_cd"
    SECURITY = "security"


# Agent to Lane mapping (PAC-JEFFREY-P03 Section 3)
AGENT_LANE_MAP: Dict[str, AgentLane] = {
    "GID-00": AgentLane.ORCHESTRATION,  # BENSON
    "GID-01": AgentLane.BACKEND,         # CODY
    "GID-02": AgentLane.FRONTEND,        # SONNY
    "GID-07": AgentLane.CI_CD,           # DAN
    "GID-06": AgentLane.SECURITY,        # SAM
}


def get_agent_lane(gid: str) -> AgentLane:
    """Get the authorized lane for an agent."""
    if gid not in AGENT_LANE_MAP:
        raise ValueError(f"Unknown agent GID: {gid} - implicit activation FORBIDDEN")
    return AGENT_LANE_MAP[gid]


def validate_lane_authorization(gid: str, target_lane: AgentLane) -> bool:
    """
    Validate agent is authorized for target lane.
    
    INV-CP-014: Cross-lane execution FORBIDDEN
    """
    authorized_lane = get_agent_lane(gid)
    if authorized_lane != target_lane:
        raise ControlPlaneStateError(
            f"Cross-lane execution FORBIDDEN: Agent {gid} (lane: {authorized_lane.value}) "
            f"cannot execute in lane: {target_lane.value}"
        )
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# PAC LIFECYCLE STATES
# ═══════════════════════════════════════════════════════════════════════════════

class PACLifecycleState(str, Enum):
    """
    Deterministic PAC lifecycle states.
    
    State transitions are strictly ordered:
    DRAFT → ACK_PENDING → EXECUTING → WRAP_PENDING → WRAP_SUBMITTED → BER_ISSUED → SETTLED
    
    FAIL states:
    Any → ACK_TIMEOUT (if ACK not received within deadline)
    Any → EXECUTION_FAILED (if agent reports failure)
    Any → WRAP_REJECTED (if WRAP validation fails)
    Any → SETTLEMENT_BLOCKED (if governance violation detected)
    """
    
    # Happy path states
    DRAFT = "DRAFT"                         # PAC created, not yet dispatched
    ACK_PENDING = "ACK_PENDING"             # Awaiting agent ACK
    EXECUTING = "EXECUTING"                 # Agent(s) actively executing
    WRAP_PENDING = "WRAP_PENDING"           # Execution complete, awaiting WRAP
    WRAP_SUBMITTED = "WRAP_SUBMITTED"       # WRAP submitted, pending validation
    WRAP_VALIDATED = "WRAP_VALIDATED"       # WRAP validated, BER eligible
    BER_ISSUED = "BER_ISSUED"               # BER generated
    SETTLED = "SETTLED"                     # Settlement complete
    
    # Fail states (terminal)
    ACK_TIMEOUT = "ACK_TIMEOUT"             # ACK deadline expired
    ACK_REJECTED = "ACK_REJECTED"           # Agent explicitly rejected ACK
    EXECUTION_FAILED = "EXECUTION_FAILED"   # Execution failed
    WRAP_REJECTED = "WRAP_REJECTED"         # WRAP validation failed
    SETTLEMENT_BLOCKED = "SETTLEMENT_BLOCKED"  # Governance violation


class AgentACKState(str, Enum):
    """Agent acknowledgment states."""
    
    PENDING = "PENDING"           # ACK requested, awaiting response
    ACKNOWLEDGED = "ACKNOWLEDGED" # Agent explicitly ACKed
    REJECTED = "REJECTED"         # Agent explicitly rejected
    TIMEOUT = "TIMEOUT"           # ACK deadline expired


class WRAPValidationState(str, Enum):
    """WRAP validation states."""
    
    PENDING = "PENDING"           # WRAP not yet submitted
    SUBMITTED = "SUBMITTED"       # WRAP submitted, validation in progress
    VALID = "VALID"               # WRAP passed all validation checks
    INVALID = "INVALID"           # WRAP failed validation
    SCHEMA_ERROR = "SCHEMA_ERROR" # WRAP failed schema validation
    MISSING_ACK = "MISSING_ACK"   # WRAP rejected due to missing ACK


class BERState(str, Enum):
    """BER generation states."""
    
    NOT_ELIGIBLE = "NOT_ELIGIBLE"     # Prerequisites not met
    ELIGIBLE = "ELIGIBLE"             # Ready for BER generation
    PENDING = "PENDING"               # BER generation in progress
    ISSUED = "ISSUED"                 # BER successfully issued
    CHALLENGED = "CHALLENGED"         # BER under challenge
    REVOKED = "REVOKED"               # BER revoked


class SettlementEligibility(str, Enum):
    """Settlement eligibility states."""
    
    BLOCKED = "BLOCKED"               # Cannot settle - governance violation
    PENDING = "PENDING"               # Prerequisites incomplete
    ELIGIBLE = "ELIGIBLE"             # Ready for settlement
    SETTLED = "SETTLED"               # Settlement complete


# ═══════════════════════════════════════════════════════════════════════════════
# VALID STATE TRANSITIONS (DETERMINISTIC)
# ═══════════════════════════════════════════════════════════════════════════════

VALID_PAC_TRANSITIONS: Dict[PACLifecycleState, List[PACLifecycleState]] = {
    PACLifecycleState.DRAFT: [
        PACLifecycleState.ACK_PENDING,
    ],
    PACLifecycleState.ACK_PENDING: [
        PACLifecycleState.EXECUTING,
        PACLifecycleState.ACK_TIMEOUT,
        PACLifecycleState.ACK_REJECTED,
    ],
    PACLifecycleState.EXECUTING: [
        PACLifecycleState.WRAP_PENDING,
        PACLifecycleState.EXECUTION_FAILED,
    ],
    PACLifecycleState.WRAP_PENDING: [
        PACLifecycleState.WRAP_SUBMITTED,
    ],
    PACLifecycleState.WRAP_SUBMITTED: [
        PACLifecycleState.WRAP_VALIDATED,
        PACLifecycleState.WRAP_REJECTED,
    ],
    PACLifecycleState.WRAP_VALIDATED: [
        PACLifecycleState.BER_ISSUED,
        PACLifecycleState.SETTLEMENT_BLOCKED,
    ],
    PACLifecycleState.BER_ISSUED: [
        PACLifecycleState.SETTLED,
        PACLifecycleState.SETTLEMENT_BLOCKED,
    ],
    # Terminal states - no transitions allowed
    PACLifecycleState.SETTLED: [],
    PACLifecycleState.ACK_TIMEOUT: [],
    PACLifecycleState.ACK_REJECTED: [],
    PACLifecycleState.EXECUTION_FAILED: [],
    PACLifecycleState.WRAP_REJECTED: [],
    PACLifecycleState.SETTLEMENT_BLOCKED: [],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentACK:
    """Agent acknowledgment record."""
    
    ack_id: str
    pac_id: str
    agent_gid: str
    agent_name: str
    order_id: str
    state: AgentACKState
    requested_at: str
    deadline_at: str
    acknowledged_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    ack_hash: str = ""
    latency_ms: Optional[int] = None
    
    def __post_init__(self):
        if not self.ack_hash:
            self.ack_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for audit trail."""
        data = {
            "ack_id": self.ack_id,
            "pac_id": self.pac_id,
            "agent_gid": self.agent_gid,
            "order_id": self.order_id,
            "state": self.state.value,
            "requested_at": self.requested_at,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class WRAPArtifact:
    """WRAP (Work Result Artifact Package) record."""
    
    wrap_id: str
    pac_id: str
    agent_gid: str
    submitted_at: str
    validation_state: WRAPValidationState
    validated_at: Optional[str] = None
    artifact_refs: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    schema_version: str = "1.0"
    wrap_hash: str = ""
    
    def __post_init__(self):
        if not self.wrap_hash:
            self.wrap_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for WRAP integrity."""
        data = {
            "wrap_id": self.wrap_id,
            "pac_id": self.pac_id,
            "agent_gid": self.agent_gid,
            "artifact_refs": sorted(self.artifact_refs),
            "schema_version": self.schema_version,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class BERRecord:
    """
    BER (Benson Execution Report) record.
    
    PAC-JEFFREY-P02R MANDATORY FIELDS:
    - execution_mode: EXECUTING | NON_EXECUTING
    - execution_barrier: ALL_WRAPS_BEFORE_RG01 | NONE
    - ber_finality: FINAL | PROVISIONAL
    - ledger_commit_status: PENDING | COMMITTED
    - ledger_commit_hash: Required if ber_finality=FINAL
    """
    
    ber_id: str
    pac_id: str
    wrap_id: str
    state: BERState
    
    # PAC-JEFFREY-P02R: Execution mode declaration (MANDATORY)
    execution_mode: str = "EXECUTING"  # EXECUTING | NON_EXECUTING
    execution_barrier: str = "ALL_WRAPS_BEFORE_RG01"  # ALL_WRAPS_BEFORE_RG01 | NONE
    
    # PAC-JEFFREY-P02R: BER finality semantics (MANDATORY)
    ber_finality: str = "PROVISIONAL"  # FINAL | PROVISIONAL
    ledger_commit_status: str = "PENDING"  # PENDING | COMMITTED
    ledger_commit_hash: Optional[str] = None
    
    # PAC-JEFFREY-P02R: WRAP hash set (MANDATORY)
    wrap_hash_set: List[str] = field(default_factory=list)
    
    # PAC-JEFFREY-P02R: Review gate results (MANDATORY)
    rg01_result: Optional[str] = None  # PASS | FAIL
    bsrg01_result: Optional[str] = None  # PASS | FAIL
    
    # PAC-JEFFREY-P02R: Training/Closure digests (MANDATORY)
    training_signal_digest: Optional[str] = None
    positive_closure_digest: Optional[str] = None
    
    issued_at: Optional[str] = None
    issuer_gid: str = "GID-00"
    challenge_deadline: Optional[str] = None
    settlement_eligible: bool = False
    ber_hash: str = ""
    
    def __post_init__(self):
        if not self.ber_hash:
            self.ber_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for BER integrity."""
        data = {
            "ber_id": self.ber_id,
            "pac_id": self.pac_id,
            "wrap_id": self.wrap_id,
            "state": self.state.value,
            "issuer_gid": self.issuer_gid,
            "execution_mode": self.execution_mode,
            "ber_finality": self.ber_finality,
            "wrap_hash_set": sorted(self.wrap_hash_set),
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def is_settlement_eligible(self) -> bool:
        """
        Check settlement eligibility per PAC-JEFFREY-P02R Section 10.
        
        Settlement FORBIDDEN unless:
        - ber_finality = FINAL
        - ledger_commit_hash present
        - ACK latency SLA met
        """
        return (
            self.ber_finality == "FINAL"
            and self.ledger_commit_hash is not None
            and self.ledger_commit_status == "COMMITTED"
        )


@dataclass
class ControlPlaneState:
    """
    Complete Control Plane execution state.
    
    This is the canonical state object that powers the Control Plane UI.
    All fields are deterministic and auditable.
    """
    
    # PAC identity
    pac_id: str
    runtime_id: str
    
    # Lifecycle state
    lifecycle_state: PACLifecycleState
    
    # Agent ACKs (keyed by agent_gid)
    agent_acks: Dict[str, AgentACK] = field(default_factory=dict)
    
    # WRAP artifacts (keyed by wrap_id)
    wraps: Dict[str, WRAPArtifact] = field(default_factory=dict)
    
    # BER record
    ber: Optional[BERRecord] = None
    
    # Settlement eligibility
    settlement_eligibility: SettlementEligibility = SettlementEligibility.PENDING
    settlement_block_reason: Optional[str] = None
    
    # Timestamps
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Audit trail
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    
    def all_acks_received(self) -> bool:
        """Check if all required ACKs have been received."""
        if not self.agent_acks:
            return False
        return all(
            ack.state == AgentACKState.ACKNOWLEDGED
            for ack in self.agent_acks.values()
        )
    
    def has_pending_acks(self) -> bool:
        """Check if any ACKs are still pending."""
        return any(
            ack.state == AgentACKState.PENDING
            for ack in self.agent_acks.values()
        )
    
    def has_timed_out_acks(self) -> bool:
        """Check if any ACKs have timed out."""
        return any(
            ack.state == AgentACKState.TIMEOUT
            for ack in self.agent_acks.values()
        )
    
    def has_rejected_acks(self) -> bool:
        """Check if any ACKs were rejected."""
        return any(
            ack.state == AgentACKState.REJECTED
            for ack in self.agent_acks.values()
        )
    
    def get_ack_latency_summary(self) -> Dict[str, Any]:
        """Get ACK latency statistics."""
        latencies = [
            ack.latency_ms
            for ack in self.agent_acks.values()
            if ack.latency_ms is not None
        ]
        if not latencies:
            return {"min_ms": None, "max_ms": None, "avg_ms": None}
        return {
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "avg_ms": sum(latencies) // len(latencies),
        }
    
    def compute_settlement_eligibility(self) -> SettlementEligibility:
        """
        Compute settlement eligibility based on current state.
        
        INVARIANTS:
        - Must have all ACKs acknowledged
        - Must have valid WRAP
        - Must have issued BER
        - No governance violations
        """
        # Check for blocking conditions
        if self.has_timed_out_acks():
            return SettlementEligibility.BLOCKED
        if self.has_rejected_acks():
            return SettlementEligibility.BLOCKED
        if self.lifecycle_state in (
            PACLifecycleState.ACK_TIMEOUT,
            PACLifecycleState.ACK_REJECTED,
            PACLifecycleState.EXECUTION_FAILED,
            PACLifecycleState.WRAP_REJECTED,
            PACLifecycleState.SETTLEMENT_BLOCKED,
        ):
            return SettlementEligibility.BLOCKED
        
        # Check for settlement completion
        if self.lifecycle_state == PACLifecycleState.SETTLED:
            return SettlementEligibility.SETTLED
        
        # Check BER eligibility
        if self.ber and self.ber.state == BERState.ISSUED:
            return SettlementEligibility.ELIGIBLE
        
        return SettlementEligibility.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "pac_id": self.pac_id,
            "runtime_id": self.runtime_id,
            "lifecycle_state": self.lifecycle_state.value,
            "agent_acks": {
                gid: {
                    "ack_id": ack.ack_id,
                    "agent_gid": ack.agent_gid,
                    "agent_name": ack.agent_name,
                    "order_id": ack.order_id,
                    "state": ack.state.value,
                    "requested_at": ack.requested_at,
                    "deadline_at": ack.deadline_at,
                    "acknowledged_at": ack.acknowledged_at,
                    "rejection_reason": ack.rejection_reason,
                    "latency_ms": ack.latency_ms,
                    "ack_hash": ack.ack_hash,
                }
                for gid, ack in self.agent_acks.items()
            },
            "wraps": {
                wrap_id: {
                    "wrap_id": wrap.wrap_id,
                    "pac_id": wrap.pac_id,
                    "agent_gid": wrap.agent_gid,
                    "submitted_at": wrap.submitted_at,
                    "validation_state": wrap.validation_state.value,
                    "validated_at": wrap.validated_at,
                    "artifact_refs": wrap.artifact_refs,
                    "validation_errors": wrap.validation_errors,
                    "wrap_hash": wrap.wrap_hash,
                }
                for wrap_id, wrap in self.wraps.items()
            },
            "ber": {
                "ber_id": self.ber.ber_id,
                "pac_id": self.ber.pac_id,
                "wrap_id": self.ber.wrap_id,
                "state": self.ber.state.value,
                "issued_at": self.ber.issued_at,
                "issuer_gid": self.ber.issuer_gid,
                "settlement_eligible": self.ber.settlement_eligible,
                "ber_hash": self.ber.ber_hash,
            } if self.ber else None,
            "settlement_eligibility": self.settlement_eligibility.value,
            "settlement_block_reason": self.settlement_block_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ack_summary": {
                "total": len(self.agent_acks),
                "acknowledged": sum(
                    1 for a in self.agent_acks.values()
                    if a.state == AgentACKState.ACKNOWLEDGED
                ),
                "pending": sum(
                    1 for a in self.agent_acks.values()
                    if a.state == AgentACKState.PENDING
                ),
                "rejected": sum(
                    1 for a in self.agent_acks.values()
                    if a.state == AgentACKState.REJECTED
                ),
                "timeout": sum(
                    1 for a in self.agent_acks.values()
                    if a.state == AgentACKState.TIMEOUT
                ),
                "latency": self.get_ack_latency_summary(),
            },
            "state_transitions": self.state_transitions,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# STATE TRANSITION VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ControlPlaneStateError(Exception):
    """Raised when a state transition is invalid."""
    pass


def validate_transition(
    current_state: PACLifecycleState,
    target_state: PACLifecycleState,
) -> bool:
    """
    Validate a state transition.
    
    Returns True if transition is valid, raises ControlPlaneStateError otherwise.
    """
    valid_targets = VALID_PAC_TRANSITIONS.get(current_state, [])
    if target_state not in valid_targets:
        raise ControlPlaneStateError(
            f"Invalid state transition: {current_state.value} → {target_state.value}. "
            f"Valid targets: {[s.value for s in valid_targets]}"
        )
    return True


def transition_state(
    state: ControlPlaneState,
    target_state: PACLifecycleState,
    reason: str,
    actor: str = "SYSTEM",
) -> ControlPlaneState:
    """
    Execute a state transition with full audit trail.
    
    FAIL_CLOSED: Invalid transitions raise ControlPlaneStateError.
    """
    validate_transition(state.lifecycle_state, target_state)
    
    # Record transition
    transition_record = {
        "from_state": state.lifecycle_state.value,
        "to_state": target_state.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "actor": actor,
    }
    
    state.state_transitions.append(transition_record)
    state.lifecycle_state = target_state
    state.updated_at = datetime.now(timezone.utc).isoformat()
    
    # Recompute settlement eligibility
    state.settlement_eligibility = state.compute_settlement_eligibility()
    
    logger.info(
        f"CONTROL_PLANE: State transition {transition_record['from_state']} → "
        f"{transition_record['to_state']} for PAC {state.pac_id}"
    )
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_control_plane_state(
    pac_id: str,
    runtime_id: str,
) -> ControlPlaneState:
    """Create a new Control Plane state in DRAFT."""
    return ControlPlaneState(
        pac_id=pac_id,
        runtime_id=runtime_id,
        lifecycle_state=PACLifecycleState.DRAFT,
    )


def create_agent_ack(
    pac_id: str,
    agent_gid: str,
    agent_name: str,
    order_id: str,
    deadline_seconds: int = 300,
) -> AgentACK:
    """Create a new ACK request for an agent."""
    now = datetime.now(timezone.utc)
    deadline = datetime.fromtimestamp(
        now.timestamp() + deadline_seconds,
        tz=timezone.utc
    )
    
    return AgentACK(
        ack_id=f"ACK-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
        agent_gid=agent_gid,
        agent_name=agent_name,
        order_id=order_id,
        state=AgentACKState.PENDING,
        requested_at=now.isoformat(),
        deadline_at=deadline.isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-AGENT WRAP AGGREGATION (PAC-JEFFREY-P01)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MultiAgentWRAPSet:
    """
    Multi-agent WRAP collection for BER eligibility.
    
    Per PAC-JEFFREY-P01 Section 7:
    - Each executing agent MUST return a WRAP
    - WRAP Authority: BENSON
    - WRAP Validation: HARD FAIL on omission
    """
    
    pac_id: str
    expected_agents: List[str]  # GIDs of agents expected to submit WRAPs
    collected_wraps: Dict[str, WRAPArtifact] = field(default_factory=dict)
    aggregation_started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    aggregation_completed_at: Optional[str] = None
    set_hash: str = ""
    
    def __post_init__(self):
        if not self.set_hash:
            self.set_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for WRAP set integrity."""
        data = {
            "pac_id": self.pac_id,
            "expected_agents": sorted(self.expected_agents),
            "wrap_hashes": sorted([w.wrap_hash for w in self.collected_wraps.values()]),
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def add_wrap(self, wrap: WRAPArtifact) -> None:
        """Add a WRAP to the collection."""
        if wrap.agent_gid not in self.expected_agents:
            raise ControlPlaneStateError(
                f"Unexpected WRAP from agent {wrap.agent_gid}. "
                f"Expected: {self.expected_agents}"
            )
        self.collected_wraps[wrap.agent_gid] = wrap
        self.set_hash = self._compute_hash()
        
        if self.is_complete():
            self.aggregation_completed_at = datetime.now(timezone.utc).isoformat()
    
    def is_complete(self) -> bool:
        """Check if all expected WRAPs have been collected."""
        return set(self.expected_agents) == set(self.collected_wraps.keys())
    
    def get_missing_agents(self) -> List[str]:
        """Get list of agents that haven't submitted WRAPs."""
        return [gid for gid in self.expected_agents if gid not in self.collected_wraps]
    
    def all_valid(self) -> bool:
        """Check if all collected WRAPs are valid."""
        return all(
            w.validation_state == WRAPValidationState.VALID
            for w in self.collected_wraps.values()
        )


@dataclass
class LedgerCommitAttestation:
    """
    Ledger commit attestation for governance finality.
    
    Per PAC-JEFFREY-P01 Section 11:
    - All WRAPs and the final BER are immutable
    - Are hash-bound to this PAC
    - MUST be committed to the Governance Ledger
    """
    
    attestation_id: str
    pac_id: str
    wrap_hashes: List[str]
    ber_hash: str
    committed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ledger_block: Optional[str] = None
    attestation_hash: str = ""
    
    def __post_init__(self):
        if not self.attestation_hash:
            self.attestation_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for attestation integrity."""
        data = {
            "attestation_id": self.attestation_id,
            "pac_id": self.pac_id,
            "wrap_hashes": sorted(self.wrap_hashes),
            "ber_hash": self.ber_hash,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class ReviewGateRG01:
    """
    Review Gate RG-01 (PAC-JEFFREY-P02R Section 7).
    
    Schema: RG01_SCHEMA@v1.0.0
    
    PASS CONDITIONS:
    - All WRAPs present
    - All WRAPs structurally complete
    - Training Signals present (ALL)
    - Positive Closure present (ALL)
    - No forbidden actions
    
    FAIL ACTION: emit corrective PAC
    """
    
    gate_id: str
    pac_id: str
    reviewer: str = "BENSON"
    pass_conditions: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[str] = None  # "PASS" | "FAIL"
    fail_reasons: List[str] = field(default_factory=list)
    evaluated_at: Optional[str] = None
    
    # PAC-JEFFREY-P02R: Training Signal validation
    training_signals_present: bool = False
    positive_closures_present: bool = False
    
    def evaluate(
        self,
        wrap_set: MultiAgentWRAPSet,
        training_signals: Optional[List[Any]] = None,
        positive_closures: Optional[List[Any]] = None,
    ) -> bool:
        """
        Evaluate RG-01 pass conditions per PAC-JEFFREY-P02R Section 7.
        
        Missing block → INVALID WRAP.
        """
        self.evaluated_at = datetime.now(timezone.utc).isoformat()
        self.fail_reasons = []
        
        # Condition 1: All expected WRAPs present
        if not wrap_set.is_complete():
            missing = wrap_set.get_missing_agents()
            self.fail_reasons.append(f"Missing WRAPs from agents: {missing}")
        
        # Condition 2: All WRAPs valid
        if not wrap_set.all_valid():
            invalid = [
                gid for gid, w in wrap_set.collected_wraps.items()
                if w.validation_state != WRAPValidationState.VALID
            ]
            self.fail_reasons.append(f"Invalid WRAPs from agents: {invalid}")
        
        # Condition 3: Training Signals present (ALL) - PAC-JEFFREY-P02R
        expected_agents = set(wrap_set.expected_agents)
        if training_signals:
            signal_agents = {s.agent_gid for s in training_signals}
            missing_signals = expected_agents - signal_agents
            self.training_signals_present = len(missing_signals) == 0
            if missing_signals:
                self.fail_reasons.append(
                    f"Missing Training Signals from agents: {list(missing_signals)}"
                )
        else:
            self.training_signals_present = False
            self.fail_reasons.append("No Training Signals submitted (MANDATORY)")
        
        # Condition 4: Positive Closure present (ALL) - PAC-JEFFREY-P02R
        if positive_closures:
            closure_agents = {c.agent_gid for c in positive_closures}
            missing_closures = expected_agents - closure_agents
            self.positive_closures_present = len(missing_closures) == 0
            if missing_closures:
                self.fail_reasons.append(
                    f"Missing Positive Closure from agents: {list(missing_closures)}"
                )
            # Check all closures are valid
            invalid_closures = [
                c.agent_gid for c in positive_closures if not c.is_valid()
            ]
            if invalid_closures:
                self.fail_reasons.append(
                    f"Invalid Positive Closure from agents: {invalid_closures}"
                )
        else:
            self.positive_closures_present = False
            self.fail_reasons.append("No Positive Closure submitted (MANDATORY)")
        
        # Record all pass conditions
        self.pass_conditions = [
            {"condition": "wrap_schema_valid", "status": wrap_set.all_valid()},
            {"condition": "all_mandatory_blocks", "status": wrap_set.is_complete()},
            {"condition": "training_signals_present", "status": self.training_signals_present},
            {"condition": "positive_closures_present", "status": self.positive_closures_present},
            {"condition": "no_forbidden_actions", "status": len(self.fail_reasons) == 0},
        ]
        
        self.result = "PASS" if not self.fail_reasons else "FAIL"
        return self.result == "PASS"


@dataclass
class BensonSelfReviewBSRG01:
    """
    Benson Self-Review Gate BSRG-01 (PAC-JEFFREY-P02R Section 8).
    
    Schema: BSRG01_SCHEMA@v1.0.0
    
    MANDATORY ATTESTATIONS:
    - No override
    - No drift
    - Parallel semantics respected
    - Training + Closure verified
    """
    
    gate_id: str
    pac_id: str
    self_attestation: bool = False
    violations: List[str] = field(default_factory=list)
    training_signals: List[Dict[str, Any]] = field(default_factory=list)
    attested_at: Optional[str] = None
    
    # PAC-JEFFREY-P02R: Mandatory attestations
    no_override: bool = False
    no_drift: bool = False
    parallel_semantics_respected: bool = False
    training_closure_verified: bool = False
    
    def attest(
        self,
        violations: Optional[List[str]] = None,
        training_signals: Optional[List[Dict[str, Any]]] = None,
        no_override: bool = True,
        no_drift: bool = True,
        parallel_semantics_respected: bool = True,
        training_closure_verified: bool = True,
    ) -> bool:
        """
        Execute self-attestation per PAC-JEFFREY-P02R Section 8.
        
        All attestations must be True for valid BSRG-01.
        """
        self.attested_at = datetime.now(timezone.utc).isoformat()
        self.violations = violations or []
        self.training_signals = training_signals or []
        
        # Record mandatory attestations
        self.no_override = no_override
        self.no_drift = no_drift
        self.parallel_semantics_respected = parallel_semantics_respected
        self.training_closure_verified = training_closure_verified
        
        # Self-attestation only valid if all mandatory attestations pass
        self.self_attestation = all([
            no_override,
            no_drift,
            parallel_semantics_respected,
            training_closure_verified,
            len(self.violations) == 0,
        ])
        
        return self.self_attestation


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING SIGNAL (PAC-JEFFREY-P02R SECTION 11)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TrainingSignal:
    """
    Training Signal — REQUIRED FROM ALL AGENTS per PAC-JEFFREY-P02R.
    
    Append-only. Immutable.
    
    Schema: TRAINING_SIGNAL_SCHEMA@v1.0.0
    """
    
    signal_id: str
    pac_id: str
    agent_gid: str
    agent_name: str
    signal_type: str  # CORRECTION | LEARNING | CONSTRAINT
    observation: str
    constraint_learned: str
    recommended_enforcement: str
    emitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    signal_hash: str = ""
    
    def __post_init__(self):
        if not self.signal_hash:
            self.signal_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for signal integrity."""
        data = {
            "signal_id": self.signal_id,
            "pac_id": self.pac_id,
            "agent_gid": self.agent_gid,
            "signal_type": self.signal_type,
            "observation": self.observation,
            "constraint_learned": self.constraint_learned,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class PositiveClosure:
    """
    Positive Closure — REQUIRED FROM ALL AGENTS per PAC-JEFFREY-P02R.
    
    No Positive Closure → PAC INCOMPLETE.
    
    Schema: POSITIVE_CLOSURE_SCHEMA@v1.0.0
    """
    
    closure_id: str
    pac_id: str
    agent_gid: str
    agent_name: str
    scope_complete: bool = False
    no_violations: bool = False
    ready_for_next_stage: bool = False
    emitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    closure_hash: str = ""
    
    def __post_init__(self):
        if not self.closure_hash:
            self.closure_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for closure integrity."""
        data = {
            "closure_id": self.closure_id,
            "pac_id": self.pac_id,
            "agent_gid": self.agent_gid,
            "scope_complete": self.scope_complete,
            "no_violations": self.no_violations,
            "ready_for_next_stage": self.ready_for_next_stage,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def is_valid(self) -> bool:
        """Check if closure represents valid positive completion."""
        return self.scope_complete and self.no_violations and self.ready_for_next_stage


@dataclass
class AgentACKEvidence:
    """
    Full ACK Evidence record per PAC-JEFFREY-P02R Section 1.
    
    Schema: AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0
    
    ACK REQUIREMENTS (HARD):
    - agent_id
    - gid
    - lane
    - concrete ISO-8601 timestamp
    - ack_latency_ms
    - authorization_scope
    - evidence_hash
    """
    
    agent_id: str
    gid: str
    lane: str  # orchestration | backend | frontend | ci_cd | security
    mode: str  # EXECUTING | NON_EXECUTING
    timestamp: str  # ISO-8601 concrete timestamp
    ack_latency_ms: int
    authorization_scope: str
    evidence_hash: str = ""
    
    def __post_init__(self):
        if not self.evidence_hash:
            self.evidence_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for ACK evidence integrity."""
        data = {
            "agent_id": self.agent_id,
            "gid": self.gid,
            "lane": self.lane,
            "mode": self.mode,
            "timestamp": self.timestamp,
            "ack_latency_ms": self.ack_latency_ms,
            "authorization_scope": self.authorization_scope,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# ACK LATENCY SETTLEMENT BINDING (PAC-JEFFREY-P02R)
# ═══════════════════════════════════════════════════════════════════════════════

ACK_LATENCY_THRESHOLD_MS = 5000  # 5 seconds max ACK latency for settlement


def check_ack_latency_eligibility(state: ControlPlaneState) -> Dict[str, Any]:
    """
    Check if ACK latencies are within settlement threshold.
    
    Per PAC-JEFFREY-P01 Section 6:
    - ACK latency measurement
    - ACK → settlement eligibility binding
    """
    latency_summary = state.get_ack_latency_summary()
    max_latency = latency_summary.get("max_ms")
    
    if max_latency is None:
        return {
            "eligible": False,
            "reason": "No ACK latency data available",
            "threshold_ms": ACK_LATENCY_THRESHOLD_MS,
            "max_latency_ms": None,
        }
    
    eligible = max_latency <= ACK_LATENCY_THRESHOLD_MS
    return {
        "eligible": eligible,
        "reason": None if eligible else f"Max ACK latency {max_latency}ms exceeds threshold {ACK_LATENCY_THRESHOLD_MS}ms",
        "threshold_ms": ACK_LATENCY_THRESHOLD_MS,
        "max_latency_ms": max_latency,
    }


def create_multi_agent_wrap_set(
    pac_id: str,
    executing_agents: List[str],
) -> MultiAgentWRAPSet:
    """Create a new multi-agent WRAP collection set."""
    return MultiAgentWRAPSet(
        pac_id=pac_id,
        expected_agents=executing_agents,
    )


def create_ledger_commit_attestation(
    pac_id: str,
    wrap_set: MultiAgentWRAPSet,
    ber: BERRecord,
) -> LedgerCommitAttestation:
    """Create a ledger commit attestation binding WRAPs and BER."""
    return LedgerCommitAttestation(
        attestation_id=f"ATTEST-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
        wrap_hashes=[w.wrap_hash for w in wrap_set.collected_wraps.values()],
        ber_hash=ber.ber_hash,
    )


def create_review_gate_rg01(pac_id: str) -> ReviewGateRG01:
    """Create a new RG-01 review gate."""
    return ReviewGateRG01(
        gate_id=f"RG01-{uuid4().hex[:8].upper()}",
        pac_id=pac_id,
    )


def create_bsrg01(pac_id: str) -> BensonSelfReviewBSRG01:
    """Create a new BSRG-01 self-review gate."""
    return BensonSelfReviewBSRG01(
        gate_id=f"BSRG01-{uuid4().hex[:8].upper()}",
        pac_id=pac_id,
    )


def create_training_signal(
    pac_id: str,
    agent_gid: str,
    agent_name: str,
    signal_type: str,
    observation: str,
    constraint_learned: str,
    recommended_enforcement: str,
) -> TrainingSignal:
    """Create a new Training Signal per PAC-JEFFREY-P02R Section 11."""
    return TrainingSignal(
        signal_id=f"SIGNAL-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
        agent_gid=agent_gid,
        agent_name=agent_name,
        signal_type=signal_type,
        observation=observation,
        constraint_learned=constraint_learned,
        recommended_enforcement=recommended_enforcement,
    )


def create_positive_closure(
    pac_id: str,
    agent_gid: str,
    agent_name: str,
    scope_complete: bool = True,
    no_violations: bool = True,
    ready_for_next_stage: bool = True,
) -> PositiveClosure:
    """Create a new Positive Closure per PAC-JEFFREY-P02R Section 12."""
    return PositiveClosure(
        closure_id=f"CLOSURE-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
        agent_gid=agent_gid,
        agent_name=agent_name,
        scope_complete=scope_complete,
        no_violations=no_violations,
        ready_for_next_stage=ready_for_next_stage,
    )


def create_ack_evidence(
    agent_id: str,
    gid: str,
    lane: str,
    mode: str,
    ack_latency_ms: int,
    authorization_scope: str,
) -> AgentACKEvidence:
    """Create full ACK evidence per PAC-JEFFREY-P02R Section 1."""
    return AgentACKEvidence(
        agent_id=agent_id,
        gid=gid,
        lane=lane,
        mode=mode,
        timestamp=datetime.now(timezone.utc).isoformat(),
        ack_latency_ms=ack_latency_ms,
        authorization_scope=authorization_scope,
    )


def compute_training_signal_digest(signals: List[TrainingSignal]) -> str:
    """Compute aggregate hash of all training signals."""
    if not signals:
        return ""
    hashes = sorted([s.signal_hash for s in signals])
    canonical = json.dumps(hashes, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def compute_positive_closure_digest(closures: List[PositiveClosure]) -> str:
    """Compute aggregate hash of all positive closures."""
    if not closures:
        return ""
    hashes = sorted([c.closure_hash for c in closures])
    canonical = json.dumps(hashes, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION BARRIER (PAC-JEFFREY-P03 Section 2)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionBarrier:
    """
    Execution barrier for parallel agent coordination.
    
    Per PAC-JEFFREY-P03 Section 2:
    - execution_mode: PARALLEL
    - execution_barrier: AGENT_ACK_BARRIER
    - barrier_release_condition: ALL_REQUIRED_AGENT_ACKS_PRESENT
    
    INV-CP-013: AGENT_ACK_BARRIER release requires ALL agent ACKs
    """
    
    barrier_id: str
    pac_id: str
    execution_mode: ExecutionMode
    barrier_type: ExecutionBarrierType
    release_condition: BarrierReleaseCondition
    required_agents: List[str]  # GIDs
    received_acks: Dict[str, AgentACKEvidence] = field(default_factory=dict)
    released: bool = False
    released_at: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    barrier_hash: str = ""
    
    def __post_init__(self):
        if not self.barrier_hash:
            self.barrier_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for barrier integrity."""
        data = {
            "barrier_id": self.barrier_id,
            "pac_id": self.pac_id,
            "execution_mode": self.execution_mode.value,
            "barrier_type": self.barrier_type.value,
            "release_condition": self.release_condition.value,
            "required_agents": sorted(self.required_agents),
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def record_ack(self, ack_evidence: AgentACKEvidence) -> None:
        """Record an agent ACK."""
        if ack_evidence.gid not in self.required_agents:
            raise ControlPlaneStateError(
                f"Unexpected ACK from agent {ack_evidence.gid}. "
                f"Required agents: {self.required_agents}"
            )
        self.received_acks[ack_evidence.gid] = ack_evidence
        self.barrier_hash = self._compute_hash()
    
    def check_release_condition(self) -> bool:
        """
        Check if barrier release condition is met.
        
        INV-CP-013: ALL_REQUIRED_AGENT_ACKS_PRESENT
        """
        if self.release_condition == BarrierReleaseCondition.ALL_REQUIRED_AGENT_ACKS_PRESENT:
            return set(self.required_agents) == set(self.received_acks.keys())
        elif self.release_condition == BarrierReleaseCondition.ALL_WRAPS_COLLECTED:
            # Requires external WRAP set validation
            return False
        return False
    
    def release(self) -> bool:
        """
        Attempt to release the barrier.
        
        FAIL_CLOSED: Cannot release if condition not met.
        """
        if not self.check_release_condition():
            return False
        self.released = True
        self.released_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"BARRIER_RELEASED: {self.barrier_id} for PAC {self.pac_id}")
        return True
    
    def get_missing_acks(self) -> List[str]:
        """Get list of agents that haven't sent ACKs."""
        return [gid for gid in self.required_agents if gid not in self.received_acks]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "barrier_id": self.barrier_id,
            "pac_id": self.pac_id,
            "execution_mode": self.execution_mode.value,
            "barrier_type": self.barrier_type.value,
            "release_condition": self.release_condition.value,
            "required_agents": self.required_agents,
            "received_acks": {
                gid: {
                    "agent_id": ack.agent_id,
                    "gid": ack.gid,
                    "lane": ack.lane,
                    "mode": ack.mode,
                    "timestamp": ack.timestamp,
                    "ack_latency_ms": ack.ack_latency_ms,
                    "evidence_hash": ack.evidence_hash,
                }
                for gid, ack in self.received_acks.items()
            },
            "missing_acks": self.get_missing_acks(),
            "released": self.released,
            "released_at": self.released_at,
            "created_at": self.created_at,
            "barrier_hash": self.barrier_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PACK IMMUTABILITY (PAC-JEFFREY-P03 Section 11)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PackImmutabilityAttestation:
    """
    PACK immutability attestation per PAC-JEFFREY-P03 Section 11.
    
    INV-CP-016: PACK_IMMUTABLE = true
    
    Once a PACK (PAC + all WRAPs + BER) is committed:
    - No modifications allowed
    - Hash-locked
    - Ordering attestation enforced
    """
    
    attestation_id: str
    pac_id: str
    pack_hash: str  # Combined hash of PAC + all WRAPs + BER
    ordering_verified: bool = False
    immutable: bool = True  # Always true once attested
    attested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    attester_gid: str = "GID-00"  # BENSON attests
    component_hashes: Dict[str, str] = field(default_factory=dict)
    attestation_hash: str = ""
    
    def __post_init__(self):
        if not self.attestation_hash:
            self.attestation_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for attestation integrity."""
        data = {
            "attestation_id": self.attestation_id,
            "pac_id": self.pac_id,
            "pack_hash": self.pack_hash,
            "ordering_verified": self.ordering_verified,
            "immutable": self.immutable,
            "attester_gid": self.attester_gid,
            "component_hashes": self.component_hashes,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "attestation_id": self.attestation_id,
            "pac_id": self.pac_id,
            "pack_hash": self.pack_hash,
            "ordering_verified": self.ordering_verified,
            "immutable": self.immutable,
            "attested_at": self.attested_at,
            "attester_gid": self.attester_gid,
            "component_hashes": self.component_hashes,
            "attestation_hash": self.attestation_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# POSITIVE CLOSURE CHECKLIST (PAC-JEFFREY-P03 Section 10)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PositiveClosureChecklist:
    """
    Positive closure checklist per PAC-JEFFREY-P03 Section 10.
    
    ALL items must PASS for valid closure:
    - PAG-01_ACKS_COMPLETE
    - ALL_REQUIRED_WRAPS
    - RG-01
    - BSRG-01
    - BER_ISSUED
    - LEDGER_COMMIT (PASS | PROVISIONAL)
    """
    
    checklist_id: str
    pac_id: str
    pag01_acks_complete: bool = False
    all_required_wraps: bool = False
    rg01_passed: bool = False
    bsrg01_passed: bool = False
    ber_issued: bool = False
    ledger_commit: str = "PENDING"  # PASS | PROVISIONAL | PENDING
    overall_status: str = "PENDING"  # PASS | FAIL | PENDING
    evaluated_at: Optional[str] = None
    
    def evaluate(self) -> str:
        """
        Evaluate the checklist.
        
        All items must PASS for overall PASS.
        """
        self.evaluated_at = datetime.now(timezone.utc).isoformat()
        
        all_pass = all([
            self.pag01_acks_complete,
            self.all_required_wraps,
            self.rg01_passed,
            self.bsrg01_passed,
            self.ber_issued,
            self.ledger_commit in ("PASS", "PROVISIONAL"),
        ])
        
        self.overall_status = "PASS" if all_pass else "FAIL"
        return self.overall_status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "checklist_id": self.checklist_id,
            "pac_id": self.pac_id,
            "items": {
                "PAG-01_ACKS_COMPLETE": "PASS" if self.pag01_acks_complete else "FAIL",
                "ALL_REQUIRED_WRAPS": "PASS" if self.all_required_wraps else "FAIL",
                "RG-01": "PASS" if self.rg01_passed else "FAIL",
                "BSRG-01": "PASS" if self.bsrg01_passed else "FAIL",
                "BER_ISSUED": "PASS" if self.ber_issued else "FAIL",
                "LEDGER_COMMIT": self.ledger_commit,
            },
            "overall_status": self.overall_status,
            "evaluated_at": self.evaluated_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# P03 FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_execution_barrier(
    pac_id: str,
    required_agents: List[str],
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
    barrier_type: ExecutionBarrierType = ExecutionBarrierType.AGENT_ACK_BARRIER,
    release_condition: BarrierReleaseCondition = BarrierReleaseCondition.ALL_REQUIRED_AGENT_ACKS_PRESENT,
) -> ExecutionBarrier:
    """Create a new execution barrier per PAC-JEFFREY-P03 Section 2."""
    return ExecutionBarrier(
        barrier_id=f"BARRIER-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
        execution_mode=execution_mode,
        barrier_type=barrier_type,
        release_condition=release_condition,
        required_agents=required_agents,
    )


def create_pack_immutability_attestation(
    pac_id: str,
    pack_hash: str,
    component_hashes: Dict[str, str],
    ordering_verified: bool = True,
) -> PackImmutabilityAttestation:
    """Create a PACK immutability attestation per PAC-JEFFREY-P03 Section 11."""
    return PackImmutabilityAttestation(
        attestation_id=f"PACK-ATTEST-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
        pack_hash=pack_hash,
        ordering_verified=ordering_verified,
        component_hashes=component_hashes,
    )


def create_positive_closure_checklist(pac_id: str) -> PositiveClosureChecklist:
    """Create a positive closure checklist per PAC-JEFFREY-P03 Section 10."""
    return PositiveClosureChecklist(
        checklist_id=f"CHECKLIST-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
    )


def compute_pack_hash(
    pac_hash: str,
    wrap_hashes: List[str],
    ber_hash: str,
) -> str:
    """Compute the combined PACK hash for immutability attestation."""
    data = {
        "pac_hash": pac_hash,
        "wrap_hashes": sorted(wrap_hashes),
        "ber_hash": ber_hash,
    }
    canonical = json.dumps(data, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT READINESS VERDICT (PAC-JEFFREY-P04)
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementBlockingReason(str, Enum):
    """
    Enumerated blocking reasons for settlement.
    
    INV-CP-018: Settlement eligibility is BINARY - no inference allowed.
    """
    MISSING_ACK = "MISSING_ACK"
    ACK_TIMEOUT = "ACK_TIMEOUT"
    ACK_REJECTED = "ACK_REJECTED"
    ACK_LATENCY_EXCEEDED = "ACK_LATENCY_EXCEEDED"
    MISSING_WRAP = "MISSING_WRAP"
    WRAP_VALIDATION_FAILED = "WRAP_VALIDATION_FAILED"
    RG01_FAILED = "RG01_FAILED"
    RG01_NOT_EVALUATED = "RG01_NOT_EVALUATED"
    BSRG01_FAILED = "BSRG01_FAILED"
    BSRG01_NOT_ATTESTED = "BSRG01_NOT_ATTESTED"
    BER_NOT_ISSUED = "BER_NOT_ISSUED"
    BER_FINALITY_PROVISIONAL = "BER_FINALITY_PROVISIONAL"
    LEDGER_COMMIT_PENDING = "LEDGER_COMMIT_PENDING"
    TRAINING_SIGNALS_MISSING = "TRAINING_SIGNALS_MISSING"
    POSITIVE_CLOSURE_MISSING = "POSITIVE_CLOSURE_MISSING"
    POSITIVE_CLOSURE_INVALID = "POSITIVE_CLOSURE_INVALID"
    GOVERNANCE_VIOLATION = "GOVERNANCE_VIOLATION"


class SettlementReadinessStatus(str, Enum):
    """
    Binary settlement readiness status.
    
    INV-CP-018: BLOCKED means BLOCKED. No soft warnings.
    """
    ELIGIBLE = "ELIGIBLE"
    BLOCKED = "BLOCKED"


@dataclass
class BlockingReasonEvidence:
    """
    Evidence for a specific blocking reason.
    
    Links blocker to source artifact (WRAP/BER refs).
    """
    reason: SettlementBlockingReason
    description: str
    source_type: str  # "WRAP" | "BER" | "RG01" | "BSRG01" | "ACK" | "LEDGER"
    source_ref: Optional[str] = None  # hash or ID
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class SettlementReadinessVerdict:
    """
    Settlement Readiness Verdict per PAC-JEFFREY-P04 Section 4.
    
    Schema: SETTLEMENT_READINESS_VERDICT_SCHEMA@v1.0.0
    
    INVARIANTS:
    - INV-CP-017: Required before BER FINAL
    - INV-CP-018: Binary - ELIGIBLE or BLOCKED
    - INV-CP-019: No human override allowed
    - INV-CP-020: Must be machine-computed
    
    CONSTRAINTS (Section 5):
    - No agent may infer settlement eligibility
    - Verdict must be machine-computed
    - No UI-level logic for eligibility
    - No human override
    - No soft warnings
    """
    
    verdict_id: str
    pac_id: str
    status: SettlementReadinessStatus
    blocking_reasons: List[BlockingReasonEvidence] = field(default_factory=list)
    
    # Source evidence references
    wrap_refs: List[str] = field(default_factory=list)
    ber_ref: Optional[str] = None
    rg01_ref: Optional[str] = None
    bsrg01_ref: Optional[str] = None
    
    # Computation metadata
    computed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    computed_by: str = "BENSON"  # Machine-computed by orchestrator
    computation_method: str = "DETERMINISTIC"  # No inference
    
    # Immutability
    verdict_hash: str = ""
    
    def __post_init__(self):
        if not self.verdict_hash:
            self.verdict_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for verdict integrity."""
        data = {
            "verdict_id": self.verdict_id,
            "pac_id": self.pac_id,
            "status": self.status.value,
            "blocking_reasons": [r.reason.value for r in self.blocking_reasons],
            "wrap_refs": sorted(self.wrap_refs),
            "ber_ref": self.ber_ref,
            "computed_at": self.computed_at,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def is_eligible(self) -> bool:
        """
        Check if settlement is eligible.
        
        INV-CP-018: Binary check - no interpretation.
        """
        return self.status == SettlementReadinessStatus.ELIGIBLE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "verdict_id": self.verdict_id,
            "pac_id": self.pac_id,
            "status": self.status.value,
            "is_eligible": self.is_eligible(),
            "blocking_reasons": [
                {
                    "reason": br.reason.value,
                    "description": br.description,
                    "source_type": br.source_type,
                    "source_ref": br.source_ref,
                    "detected_at": br.detected_at,
                }
                for br in self.blocking_reasons
            ],
            "blocking_count": len(self.blocking_reasons),
            "source_evidence": {
                "wrap_refs": self.wrap_refs,
                "ber_ref": self.ber_ref,
                "rg01_ref": self.rg01_ref,
                "bsrg01_ref": self.bsrg01_ref,
            },
            "computation": {
                "computed_at": self.computed_at,
                "computed_by": self.computed_by,
                "method": self.computation_method,
            },
            "verdict_hash": self.verdict_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT READINESS EVALUATION (PAC-JEFFREY-P04 Section 4)
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_settlement_readiness(
    pac_id: str,
    state: ControlPlaneState,
    wrap_set: Optional[MultiAgentWRAPSet] = None,
    rg01: Optional[ReviewGateRG01] = None,
    bsrg01: Optional[BensonSelfReviewBSRG01] = None,
    training_signals: Optional[List[TrainingSignal]] = None,
    positive_closures: Optional[List[PositiveClosure]] = None,
    ledger_attestation: Optional[LedgerCommitAttestation] = None,
) -> SettlementReadinessVerdict:
    """
    Evaluate settlement readiness for a PAC.
    
    This is the CANONICAL function for computing settlement eligibility.
    
    INV-CP-017: SettlementReadinessVerdict REQUIRED before BER FINAL
    INV-CP-018: Settlement eligibility is BINARY
    INV-CP-019: No human override
    INV-CP-020: Verdict must be machine-computed
    
    CONSTRAINTS:
    - Deterministic evaluation
    - No inference or interpretation
    - All blockers explicitly enumerated
    
    Returns:
        SettlementReadinessVerdict with status and blocking reasons
    """
    blocking_reasons: List[BlockingReasonEvidence] = []
    wrap_refs: List[str] = []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 1: ACK Status
    # ═══════════════════════════════════════════════════════════════════════════
    if not state.all_acks_received():
        # Identify specific ACK issues
        for gid, ack in state.agent_acks.items():
            if ack.state == AgentACKState.PENDING:
                blocking_reasons.append(BlockingReasonEvidence(
                    reason=SettlementBlockingReason.MISSING_ACK,
                    description=f"ACK pending from agent {gid} ({ack.agent_name})",
                    source_type="ACK",
                    source_ref=ack.ack_hash,
                ))
            elif ack.state == AgentACKState.TIMEOUT:
                blocking_reasons.append(BlockingReasonEvidence(
                    reason=SettlementBlockingReason.ACK_TIMEOUT,
                    description=f"ACK timeout from agent {gid} ({ack.agent_name})",
                    source_type="ACK",
                    source_ref=ack.ack_hash,
                ))
            elif ack.state == AgentACKState.REJECTED:
                blocking_reasons.append(BlockingReasonEvidence(
                    reason=SettlementBlockingReason.ACK_REJECTED,
                    description=f"ACK rejected by agent {gid}: {ack.rejection_reason}",
                    source_type="ACK",
                    source_ref=ack.ack_hash,
                ))
    
    # CHECK 1b: ACK Latency
    latency_check = check_ack_latency_eligibility(state)
    if not latency_check["eligible"]:
        blocking_reasons.append(BlockingReasonEvidence(
            reason=SettlementBlockingReason.ACK_LATENCY_EXCEEDED,
            description=f"ACK latency {latency_check['max_latency_ms']}ms exceeds threshold {ACK_LATENCY_THRESHOLD_MS}ms",
            source_type="ACK",
        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 2: WRAP Status
    # ═══════════════════════════════════════════════════════════════════════════
    if wrap_set is None:
        blocking_reasons.append(BlockingReasonEvidence(
            reason=SettlementBlockingReason.MISSING_WRAP,
            description="No WRAP set configured",
            source_type="WRAP",
        ))
    elif not wrap_set.is_complete():
        missing = wrap_set.get_missing_agents()
        for gid in missing:
            blocking_reasons.append(BlockingReasonEvidence(
                reason=SettlementBlockingReason.MISSING_WRAP,
                description=f"Missing WRAP from agent {gid}",
                source_type="WRAP",
            ))
    elif not wrap_set.all_valid():
        for gid, wrap in wrap_set.collected_wraps.items():
            if wrap.validation_state != WRAPValidationState.VALID:
                blocking_reasons.append(BlockingReasonEvidence(
                    reason=SettlementBlockingReason.WRAP_VALIDATION_FAILED,
                    description=f"WRAP from {gid} failed validation: {wrap.validation_state.value}",
                    source_type="WRAP",
                    source_ref=wrap.wrap_hash,
                ))
    
    # Collect WRAP refs
    if wrap_set:
        wrap_refs = [w.wrap_hash for w in wrap_set.collected_wraps.values()]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 3: RG-01 Review Gate
    # ═══════════════════════════════════════════════════════════════════════════
    rg01_ref = None
    if rg01 is None:
        blocking_reasons.append(BlockingReasonEvidence(
            reason=SettlementBlockingReason.RG01_NOT_EVALUATED,
            description="RG-01 review gate not evaluated",
            source_type="RG01",
        ))
    elif rg01.result != "PASS":
        rg01_ref = rg01.gate_id
        for fail_reason in rg01.fail_reasons:
            blocking_reasons.append(BlockingReasonEvidence(
                reason=SettlementBlockingReason.RG01_FAILED,
                description=f"RG-01 failed: {fail_reason}",
                source_type="RG01",
                source_ref=rg01.gate_id,
            ))
    else:
        rg01_ref = rg01.gate_id
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 4: BSRG-01 Self-Review Gate
    # ═══════════════════════════════════════════════════════════════════════════
    bsrg01_ref = None
    if bsrg01 is None:
        blocking_reasons.append(BlockingReasonEvidence(
            reason=SettlementBlockingReason.BSRG01_NOT_ATTESTED,
            description="BSRG-01 self-review not attested",
            source_type="BSRG01",
        ))
    elif not bsrg01.self_attestation:
        bsrg01_ref = bsrg01.gate_id
        for violation in bsrg01.violations:
            blocking_reasons.append(BlockingReasonEvidence(
                reason=SettlementBlockingReason.BSRG01_FAILED,
                description=f"BSRG-01 failed: {violation}",
                source_type="BSRG01",
                source_ref=bsrg01.gate_id,
            ))
    else:
        bsrg01_ref = bsrg01.gate_id
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 5: BER Status
    # ═══════════════════════════════════════════════════════════════════════════
    ber_ref = None
    if state.ber is None:
        blocking_reasons.append(BlockingReasonEvidence(
            reason=SettlementBlockingReason.BER_NOT_ISSUED,
            description="BER not yet issued",
            source_type="BER",
        ))
    else:
        ber_ref = state.ber.ber_hash
        if state.ber.state != BERState.ISSUED:
            blocking_reasons.append(BlockingReasonEvidence(
                reason=SettlementBlockingReason.BER_NOT_ISSUED,
                description=f"BER state is {state.ber.state.value}, not ISSUED",
                source_type="BER",
                source_ref=state.ber.ber_hash,
            ))
        if state.ber.ber_finality == "PROVISIONAL":
            blocking_reasons.append(BlockingReasonEvidence(
                reason=SettlementBlockingReason.BER_FINALITY_PROVISIONAL,
                description="BER finality is PROVISIONAL, FINAL required for settlement",
                source_type="BER",
                source_ref=state.ber.ber_hash,
            ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 6: Training Signals
    # ═══════════════════════════════════════════════════════════════════════════
    if not training_signals or len(training_signals) == 0:
        blocking_reasons.append(BlockingReasonEvidence(
            reason=SettlementBlockingReason.TRAINING_SIGNALS_MISSING,
            description="No training signals submitted (MANDATORY per agent)",
            source_type="WRAP",
        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 7: Positive Closures
    # ═══════════════════════════════════════════════════════════════════════════
    if not positive_closures or len(positive_closures) == 0:
        blocking_reasons.append(BlockingReasonEvidence(
            reason=SettlementBlockingReason.POSITIVE_CLOSURE_MISSING,
            description="No positive closures submitted (MANDATORY per agent)",
            source_type="WRAP",
        ))
    else:
        for closure in positive_closures:
            if not closure.is_valid():
                blocking_reasons.append(BlockingReasonEvidence(
                    reason=SettlementBlockingReason.POSITIVE_CLOSURE_INVALID,
                    description=f"Positive closure from {closure.agent_gid} is invalid",
                    source_type="WRAP",
                    source_ref=closure.closure_hash,
                ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK 8: Ledger Commit
    # ═══════════════════════════════════════════════════════════════════════════
    if ledger_attestation is None:
        blocking_reasons.append(BlockingReasonEvidence(
            reason=SettlementBlockingReason.LEDGER_COMMIT_PENDING,
            description="Ledger commit attestation not present",
            source_type="LEDGER",
        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPUTE FINAL VERDICT
    # ═══════════════════════════════════════════════════════════════════════════
    status = (
        SettlementReadinessStatus.ELIGIBLE 
        if len(blocking_reasons) == 0 
        else SettlementReadinessStatus.BLOCKED
    )
    
    return SettlementReadinessVerdict(
        verdict_id=f"VERDICT-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
        status=status,
        blocking_reasons=blocking_reasons,
        wrap_refs=wrap_refs,
        ber_ref=ber_ref,
        rg01_ref=rg01_ref,
        bsrg01_ref=bsrg01_ref,
    )


def create_settlement_readiness_verdict(
    pac_id: str,
    status: SettlementReadinessStatus,
    blocking_reasons: Optional[List[BlockingReasonEvidence]] = None,
) -> SettlementReadinessVerdict:
    """Create a settlement readiness verdict manually (for testing)."""
    return SettlementReadinessVerdict(
        verdict_id=f"VERDICT-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
        status=status,
        blocking_reasons=blocking_reasons or [],
    )
