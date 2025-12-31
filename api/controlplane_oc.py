# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Control Plane OC API — Read-Only Endpoints
# PAC-JEFFREY-P04: Settlement Readiness Wiring · Gold Standard
# Supersedes: PAC-JEFFREY-P03
# GOLD STANDARD · FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

"""
FastAPI router for Control Plane visibility in Operations Console.

Provides GET-only endpoints for:
- PAC lifecycle state
- Agent ACK status with full evidence
- Multi-agent WRAP aggregation
- RG-01 Review Gate status
- BSRG-01 Self-Review Gate status
- BER records with execution_mode and ber_finality
- Settlement eligibility
- Ledger commit attestations
- Training Signals (PAC-JEFFREY-P02R)
- Positive Closures (PAC-JEFFREY-P02R)
- Execution Barriers (PAC-JEFFREY-P03)
- PACK Immutability Attestations (PAC-JEFFREY-P03)
- Positive Closure Checklists (PAC-JEFFREY-P03)
- Settlement Readiness Verdict (PAC-JEFFREY-P04)

All endpoints are READ-ONLY. Mutations return 405.

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
- INV-CP-018: Settlement eligibility is BINARY (PAC-JEFFREY-P04)
- INV-CP-019: No human override on settlement verdict (PAC-JEFFREY-P04)
- INV-CP-020: Verdict must be machine-computed (PAC-JEFFREY-P04)

SCHEMA REFERENCES (EXPLICIT PINNING):
- PAC Schema: CHAINBRIDGE_CANONICAL_PAC_SCHEMA@v1.0.0
- WRAP Schema: CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v1.0.0
- Settlement Verdict Schema: SETTLEMENT_READINESS_VERDICT_SCHEMA@v1.0.0
- BER Schema: CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0
- RG-01 Schema: RG01_SCHEMA@v1.0.0
- BSRG-01 Schema: BSRG01_SCHEMA@v1.0.0
- ACK Schema: AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0

Author: Benson Execution Orchestrator (GID-00)
Backend Lane: CODY (GID-01)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.governance.control_plane import (
    ACK_LATENCY_THRESHOLD_MS,
    AgentACK,
    AgentACKEvidence,
    AgentACKState,
    AgentLane,
    BarrierReleaseCondition,
    BensonSelfReviewBSRG01,
    BERRecord,
    BERState,
    BlockingReasonEvidence,
    ControlPlaneState,
    ExecutionBarrier,
    ExecutionBarrierType,
    ExecutionMode,
    LedgerCommitAttestation,
    MultiAgentWRAPSet,
    PACLifecycleState,
    PackImmutabilityAttestation,
    PositiveClosure,
    PositiveClosureChecklist,
    ReviewGateRG01,
    SettlementBlockingReason,
    SettlementEligibility,
    SettlementReadinessStatus,
    SettlementReadinessVerdict,
    TrainingSignal,
    WRAPArtifact,
    WRAPValidationState,
    check_ack_latency_eligibility,
    compute_pack_hash,
    compute_positive_closure_digest,
    compute_training_signal_digest,
    create_ack_evidence,
    create_agent_ack,
    create_bsrg01,
    create_control_plane_state,
    create_execution_barrier,
    create_ledger_commit_attestation,
    create_multi_agent_wrap_set,
    create_pack_immutability_attestation,
    create_positive_closure,
    create_positive_closure_checklist,
    create_review_gate_rg01,
    create_settlement_readiness_verdict,
    create_training_signal,
    evaluate_settlement_readiness,
    get_agent_lane,
    validate_lane_authorization,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY STORE (Demo/Dev Mode)
# ═══════════════════════════════════════════════════════════════════════════════


_control_plane_store: Dict[str, ControlPlaneState] = {}


def _ensure_demo_state() -> str:
    """Ensure demo state exists for development."""
    demo_pac_id = "PAC-CP-UI-EXEC-001"
    
    if demo_pac_id not in _control_plane_store:
        state = create_control_plane_state(
            pac_id=demo_pac_id,
            runtime_id="PAC-CP-UI-EXEC-001",
        )
        
        # Add demo ACKs
        agents = [
            ("GID-00", "Benson", "ORDER-1"),
            ("GID-01", "Cody", "ORDER-2"),
            ("GID-02", "Sonny", "ORDER-3"),
            ("GID-05", "Dan", "ORDER-4"),
        ]
        
        for gid, name, order_id in agents:
            ack = create_agent_ack(
                pac_id=demo_pac_id,
                agent_gid=gid,
                agent_name=name,
                order_id=order_id,
            )
            # Mark some as acknowledged for demo
            if gid in ("GID-00", "GID-01"):
                ack.state = AgentACKState.ACKNOWLEDGED
                ack.acknowledged_at = datetime.now(timezone.utc).isoformat()
                ack.latency_ms = 150 if gid == "GID-00" else 320
            
            state.agent_acks[gid] = ack
        
        # Update lifecycle state
        state.lifecycle_state = PACLifecycleState.ACK_PENDING
        state.state_transitions.append({
            "from_state": PACLifecycleState.DRAFT.value,
            "to_state": PACLifecycleState.ACK_PENDING.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "PAC dispatched to agents",
            "actor": "GID-00",
        })
        
        _control_plane_store[demo_pac_id] = state
    
    return demo_pac_id


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class AgentACKDTO(BaseModel):
    """Agent ACK response model."""
    ack_id: str
    pac_id: str
    agent_gid: str
    agent_name: str
    order_id: str
    state: str
    requested_at: str
    deadline_at: str
    acknowledged_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    latency_ms: Optional[int] = None
    ack_hash: str


class AgentACKEvidenceDTO(BaseModel):
    """
    Full ACK Evidence response model per PAC-JEFFREY-P02R Section 1.
    
    Schema: AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0
    """
    agent_id: str
    gid: str
    lane: str
    mode: str
    timestamp: str
    ack_latency_ms: int
    authorization_scope: str
    evidence_hash: str


class WRAPArtifactDTO(BaseModel):
    """WRAP artifact response model."""
    wrap_id: str
    pac_id: str
    agent_gid: str
    submitted_at: str
    validation_state: str
    validated_at: Optional[str] = None
    artifact_refs: List[str]
    validation_errors: List[str]
    wrap_hash: str


class BERRecordDTO(BaseModel):
    """
    BER record response model per PAC-JEFFREY-P02R Section 9.
    
    Schema: CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0
    
    MANDATORY FIELDS:
    - execution_mode
    - execution_barrier
    - ber_finality: FINAL | PROVISIONAL
    - ledger_commit_status
    - ledger_commit_hash (if FINAL)
    """
    ber_id: str
    pac_id: str
    wrap_id: str
    state: str
    
    # PAC-JEFFREY-P02R: Execution mode (MANDATORY)
    execution_mode: str = "EXECUTING"
    execution_barrier: str = "ALL_WRAPS_BEFORE_RG01"
    
    # PAC-JEFFREY-P02R: BER finality (MANDATORY)
    ber_finality: str = "PROVISIONAL"
    ledger_commit_status: str = "PENDING"
    ledger_commit_hash: Optional[str] = None
    
    # PAC-JEFFREY-P02R: WRAP hash set (MANDATORY)
    wrap_hash_set: List[str] = Field(default_factory=list)
    
    # PAC-JEFFREY-P02R: Review gate results (MANDATORY)
    rg01_result: Optional[str] = None
    bsrg01_result: Optional[str] = None
    
    # PAC-JEFFREY-P02R: Training/Closure digests (MANDATORY)
    training_signal_digest: Optional[str] = None
    positive_closure_digest: Optional[str] = None
    
    issued_at: Optional[str] = None
    issuer_gid: str
    settlement_eligible: bool
    ber_hash: str


class TrainingSignalDTO(BaseModel):
    """
    Training Signal response model per PAC-JEFFREY-P02R Section 11.
    
    REQUIRED FROM ALL AGENTS.
    Append-only. Immutable.
    """
    signal_id: str
    pac_id: str
    agent_gid: str
    agent_name: str
    signal_type: str
    observation: str
    constraint_learned: str
    recommended_enforcement: str
    emitted_at: str
    signal_hash: str


class PositiveClosureDTO(BaseModel):
    """
    Positive Closure response model per PAC-JEFFREY-P02R Section 12.
    
    REQUIRED FROM ALL AGENTS.
    No Positive Closure → PAC INCOMPLETE.
    """
    closure_id: str
    pac_id: str
    agent_gid: str
    agent_name: str
    scope_complete: bool
    no_violations: bool
    ready_for_next_stage: bool
    emitted_at: str
    closure_hash: str


class ACKSummaryDTO(BaseModel):
    """ACK summary statistics."""
    total: int
    acknowledged: int
    pending: int
    rejected: int
    timeout: int
    latency: Dict[str, Optional[int]]


class StateTransitionDTO(BaseModel):
    """State transition record."""
    from_state: str
    to_state: str
    timestamp: str
    reason: str
    actor: str


class ControlPlaneStateDTO(BaseModel):
    """Complete Control Plane state response."""
    pac_id: str
    runtime_id: str
    lifecycle_state: str
    agent_acks: Dict[str, AgentACKDTO]
    wraps: Dict[str, WRAPArtifactDTO]
    ber: Optional[BERRecordDTO] = None
    settlement_eligibility: str
    settlement_block_reason: Optional[str] = None
    created_at: str
    updated_at: str
    ack_summary: ACKSummaryDTO
    state_transitions: List[StateTransitionDTO]


class ControlPlaneListDTO(BaseModel):
    """List of Control Plane states."""
    items: List[Dict[str, Any]]
    total: int


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-JEFFREY-P03 DTOs
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionBarrierDTO(BaseModel):
    """
    Execution Barrier response model per PAC-JEFFREY-P03 Section 2.
    
    INV-CP-013: AGENT_ACK_BARRIER release requires ALL agent ACKs
    """
    barrier_id: str
    pac_id: str
    execution_mode: str
    barrier_type: str
    release_condition: str
    required_agents: List[str]
    received_acks: Dict[str, Dict[str, Any]]
    missing_acks: List[str]
    released: bool
    released_at: Optional[str] = None
    created_at: str
    barrier_hash: str


class PackImmutabilityDTO(BaseModel):
    """
    PACK immutability attestation per PAC-JEFFREY-P03 Section 11.
    
    INV-CP-016: PACK_IMMUTABLE = true
    """
    attestation_id: str
    pac_id: str
    pack_hash: str
    ordering_verified: bool
    immutable: bool
    attested_at: str
    attester_gid: str
    component_hashes: Dict[str, str]
    attestation_hash: str


class PositiveClosureChecklistDTO(BaseModel):
    """
    Positive closure checklist per PAC-JEFFREY-P03 Section 10.
    
    All items must PASS for valid closure.
    """
    checklist_id: str
    pac_id: str
    items: Dict[str, str]
    overall_status: str
    evaluated_at: Optional[str] = None


class AgentLaneDTO(BaseModel):
    """Agent lane authorization per PAC-JEFFREY-P03 Section 3."""
    agent_id: str
    gid: str
    lane: str
    authorized: bool


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-JEFFREY-P04 DTOs
# ═══════════════════════════════════════════════════════════════════════════════

class BlockingReasonEvidenceDTO(BaseModel):
    """
    Evidence for a specific blocking reason per PAC-JEFFREY-P04.
    
    Links blocker to source artifact (WRAP/BER refs).
    """
    reason: str
    description: str
    source_type: str  # "WRAP" | "BER" | "RG01" | "BSRG01" | "ACK" | "LEDGER"
    source_ref: Optional[str] = None
    detected_at: str


class SettlementReadinessVerdictDTO(BaseModel):
    """
    Settlement Readiness Verdict per PAC-JEFFREY-P04 Section 4.
    
    Schema: SETTLEMENT_READINESS_VERDICT_SCHEMA@v1.0.0
    
    INVARIANTS:
    - INV-CP-017: Required before BER FINAL
    - INV-CP-018: Binary - ELIGIBLE or BLOCKED
    - INV-CP-019: No human override allowed
    - INV-CP-020: Must be machine-computed
    """
    verdict_id: str
    pac_id: str
    status: str  # "ELIGIBLE" | "BLOCKED"
    is_eligible: bool
    blocking_reasons: List[BlockingReasonEvidenceDTO] = Field(default_factory=list)
    blocking_count: int
    source_evidence: Dict[str, Any]
    computation: Dict[str, Any]
    verdict_hash: str


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

controlplane_oc_router = APIRouter(prefix="/oc/controlplane", tags=["controlplane-oc"])


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION REJECTION
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.api_route(
    "/{path:path}",
    methods=["POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
async def reject_mutations(path: str, request: Request):
    """
    Reject all mutation attempts.
    
    OC endpoints are GET-only. Any mutation attempt returns 405.
    FAIL_CLOSED: No unauthorized mutations permitted.
    """
    logger.warning(
        f"CONTROL_PLANE OC: Mutation rejected method={request.method} path={path}"
    )
    raise HTTPException(
        status_code=405,
        detail="Control Plane OC endpoints are read-only. Mutations not permitted. FAIL_CLOSED.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CONTROL PLANE STATE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/state/{pac_id}")
async def get_control_plane_state(pac_id: str) -> Dict[str, Any]:
    """
    Get complete Control Plane state for a PAC.
    
    Returns lifecycle state, ACKs, WRAPs, BER, and settlement eligibility.
    """
    # Ensure demo state exists
    _ensure_demo_state()
    
    state = _control_plane_store.get(pac_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Control Plane state not found for PAC: {pac_id}",
        )
    
    return state.to_dict()


@controlplane_oc_router.get("/list", response_model=ControlPlaneListDTO)
async def list_control_plane_states(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ControlPlaneListDTO:
    """
    List all Control Plane states.
    
    Returns summary of all tracked PACs.
    """
    # Ensure demo state exists
    _ensure_demo_state()
    
    all_states = list(_control_plane_store.values())
    total = len(all_states)
    
    # Paginate
    paginated = all_states[offset:offset + limit]
    
    items = [
        {
            "pac_id": s.pac_id,
            "runtime_id": s.runtime_id,
            "lifecycle_state": s.lifecycle_state.value,
            "settlement_eligibility": s.settlement_eligibility.value,
            "ack_count": f"{sum(1 for a in s.agent_acks.values() if a.state == AgentACKState.ACKNOWLEDGED)}/{len(s.agent_acks)}",
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in paginated
    ]
    
    return ControlPlaneListDTO(items=items, total=total)


# ═══════════════════════════════════════════════════════════════════════════════
# ACK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/state/{pac_id}/acks")
async def get_acks(pac_id: str) -> Dict[str, Any]:
    """
    Get all ACKs for a PAC.
    """
    _ensure_demo_state()
    
    state = _control_plane_store.get(pac_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"PAC not found: {pac_id}")
    
    return {
        "pac_id": pac_id,
        "acks": [
            {
                "ack_id": ack.ack_id,
                "agent_gid": ack.agent_gid,
                "agent_name": ack.agent_name,
                "order_id": ack.order_id,
                "state": ack.state.value,
                "requested_at": ack.requested_at,
                "deadline_at": ack.deadline_at,
                "acknowledged_at": ack.acknowledged_at,
                "latency_ms": ack.latency_ms,
                "ack_hash": ack.ack_hash,
            }
            for ack in state.agent_acks.values()
        ],
        "summary": state.to_dict()["ack_summary"],
    }


@controlplane_oc_router.get("/state/{pac_id}/acks/{agent_gid}")
async def get_ack_by_agent(pac_id: str, agent_gid: str) -> Dict[str, Any]:
    """
    Get ACK for a specific agent.
    """
    _ensure_demo_state()
    
    state = _control_plane_store.get(pac_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"PAC not found: {pac_id}")
    
    ack = state.agent_acks.get(agent_gid)
    if not ack:
        raise HTTPException(status_code=404, detail=f"ACK not found for agent: {agent_gid}")
    
    return {
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


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT ELIGIBILITY ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/state/{pac_id}/settlement")
async def get_settlement_eligibility(pac_id: str) -> Dict[str, Any]:
    """
    Get settlement eligibility status for a PAC.
    
    Returns eligibility status and blocking conditions.
    """
    _ensure_demo_state()
    
    state = _control_plane_store.get(pac_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"PAC not found: {pac_id}")
    
    # Compute blocking reasons
    blocking_reasons = []
    if state.has_pending_acks():
        blocking_reasons.append("Pending ACKs: Not all agents have acknowledged")
    if state.has_rejected_acks():
        blocking_reasons.append("Rejected ACKs: One or more agents rejected the PAC")
    if state.has_timed_out_acks():
        blocking_reasons.append("Timeout ACKs: One or more agents failed to respond")
    if not state.wraps:
        blocking_reasons.append("Missing WRAP: No WRAP artifact submitted")
    if not state.ber:
        blocking_reasons.append("Missing BER: BER has not been issued")
    
    return {
        "pac_id": pac_id,
        "eligibility": state.compute_settlement_eligibility().value,
        "is_eligible": state.compute_settlement_eligibility() == SettlementEligibility.ELIGIBLE,
        "blocking_reasons": blocking_reasons,
        "ack_summary": state.to_dict()["ack_summary"],
        "lifecycle_state": state.lifecycle_state.value,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT TRAIL ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/state/{pac_id}/audit")
async def get_audit_trail(pac_id: str) -> Dict[str, Any]:
    """
    Get complete audit trail for a PAC.
    
    Returns all state transitions with timestamps and actors.
    """
    _ensure_demo_state()
    
    state = _control_plane_store.get(pac_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"PAC not found: {pac_id}")
    
    return {
        "pac_id": pac_id,
        "transitions": state.state_transitions,
        "total_transitions": len(state.state_transitions),
        "current_state": state.lifecycle_state.value,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Control Plane health check.
    """
    return {
        "status": "healthy",
        "service": "control-plane-oc",
        "governance": "FAIL_CLOSED",
        "tracked_pacs": len(_control_plane_store),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-AGENT WRAP AGGREGATION (PAC-JEFFREY-P01 SECTION 7)
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory store for multi-agent WRAP sets (demo mode)
_wrap_sets: Dict[str, MultiAgentWRAPSet] = {}
_review_gates: Dict[str, ReviewGateRG01] = {}
_bsrg_gates: Dict[str, BensonSelfReviewBSRG01] = {}
_ledger_attestations: Dict[str, LedgerCommitAttestation] = {}


def _ensure_demo_wrap_set() -> str:
    """Ensure demo WRAP set exists."""
    demo_pac_id = "PAC-JEFFREY-P01"
    
    if demo_pac_id not in _wrap_sets:
        # Per PAC-JEFFREY-P01 Section 5: BENSON, CODY, SONNY, DAN are executing
        executing_agents = ["GID-00", "GID-01", "GID-02", "GID-07"]
        wrap_set = create_multi_agent_wrap_set(demo_pac_id, executing_agents)
        
        # Add demo WRAPs (BENSON and CODY submitted)
        from uuid import uuid4
        for gid, name in [("GID-00", "BENSON"), ("GID-01", "CODY")]:
            wrap = WRAPArtifact(
                wrap_id=f"WRAP-{uuid4().hex[:12].upper()}",
                pac_id=demo_pac_id,
                agent_gid=gid,
                submitted_at=datetime.now(timezone.utc).isoformat(),
                validation_state=WRAPValidationState.VALID,
                validated_at=datetime.now(timezone.utc).isoformat(),
                artifact_refs=[f"core/governance/control_plane.py", f"api/controlplane_oc.py"],
            )
            wrap_set.collected_wraps[gid] = wrap
        
        _wrap_sets[demo_pac_id] = wrap_set
        
        # Create review gate
        _review_gates[demo_pac_id] = create_review_gate_rg01(demo_pac_id)
        
        # Create BSRG-01 gate
        _bsrg_gates[demo_pac_id] = create_bsrg01(demo_pac_id)
    
    return demo_pac_id


@controlplane_oc_router.get("/state/{pac_id}/wraps")
async def get_multi_agent_wraps(pac_id: str) -> Dict[str, Any]:
    """
    Get multi-agent WRAP aggregation status.
    
    Per PAC-JEFFREY-P01 Section 7:
    - Each executing agent MUST return a WRAP
    - Schema: CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.0.0
    """
    _ensure_demo_wrap_set()
    
    wrap_set = _wrap_sets.get(pac_id)
    if not wrap_set:
        raise HTTPException(status_code=404, detail=f"WRAP set not found for PAC: {pac_id}")
    
    return {
        "pac_id": pac_id,
        "schema_version": "CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.0.0",
        "expected_agents": wrap_set.expected_agents,
        "is_complete": wrap_set.is_complete(),
        "missing_agents": wrap_set.get_missing_agents(),
        "all_valid": wrap_set.all_valid(),
        "aggregation_started_at": wrap_set.aggregation_started_at,
        "aggregation_completed_at": wrap_set.aggregation_completed_at,
        "set_hash": wrap_set.set_hash,
        "collected_wraps": [
            {
                "wrap_id": w.wrap_id,
                "agent_gid": w.agent_gid,
                "submitted_at": w.submitted_at,
                "validation_state": w.validation_state.value,
                "validated_at": w.validated_at,
                "artifact_refs": w.artifact_refs,
                "wrap_hash": w.wrap_hash,
            }
            for w in wrap_set.collected_wraps.values()
        ],
        "governance_invariant": "INV-CP-006: Multi-agent WRAPs required before BER",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REVIEW GATE RG-01 (PAC-JEFFREY-P01 SECTION 8)
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/state/{pac_id}/review-gate")
async def get_review_gate_rg01(pac_id: str) -> Dict[str, Any]:
    """
    Get RG-01 Review Gate status.
    
    Per PAC-JEFFREY-P01 Section 8:
    - Reviewer: BENSON
    - Pass conditions: WRAP schema valid, all mandatory blocks, no forbidden actions
    - Fail action: emit corrective PAC
    """
    _ensure_demo_wrap_set()
    
    rg01 = _review_gates.get(pac_id)
    if not rg01:
        raise HTTPException(status_code=404, detail=f"RG-01 gate not found for PAC: {pac_id}")
    
    wrap_set = _wrap_sets.get(pac_id)
    
    return {
        "pac_id": pac_id,
        "gate_id": rg01.gate_id,
        "gate_type": "RG-01",
        "reviewer": rg01.reviewer,
        "result": rg01.result,
        "evaluated_at": rg01.evaluated_at,
        "pass_conditions": rg01.pass_conditions or [
            {"condition": "wrap_schema_valid", "status": None},
            {"condition": "all_mandatory_blocks", "status": None},
            {"condition": "no_forbidden_actions", "status": None},
        ],
        "fail_reasons": rg01.fail_reasons,
        "fail_action": "emit corrective PAC",
        "wrap_set_complete": wrap_set.is_complete() if wrap_set else False,
        "wrap_set_valid": wrap_set.all_valid() if wrap_set else False,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BENSON SELF-REVIEW GATE BSRG-01 (PAC-JEFFREY-P01 SECTION 9)
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/state/{pac_id}/bsrg-gate")
async def get_bsrg01_status(pac_id: str) -> Dict[str, Any]:
    """
    Get BSRG-01 Benson Self-Review Gate status.
    
    Per PAC-JEFFREY-P01 Section 9:
    - self_attestation: REQUIRED
    - violations: ENUM[NONE | LIST]
    - training_signal_emission: REQUIRED
    """
    _ensure_demo_wrap_set()
    
    bsrg = _bsrg_gates.get(pac_id)
    if not bsrg:
        raise HTTPException(status_code=404, detail=f"BSRG-01 gate not found for PAC: {pac_id}")
    
    return {
        "pac_id": pac_id,
        "gate_id": bsrg.gate_id,
        "gate_type": "BSRG-01",
        "self_attestation": bsrg.self_attestation,
        "self_attestation_required": True,
        "violations": bsrg.violations if bsrg.violations else "NONE",
        "training_signals": bsrg.training_signals,
        "training_signal_emission_required": True,
        "attested_at": bsrg.attested_at,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ACK LATENCY SETTLEMENT BINDING (PAC-JEFFREY-P01 SECTION 6)
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/state/{pac_id}/ack-latency")
async def get_ack_latency_eligibility(pac_id: str) -> Dict[str, Any]:
    """
    Get ACK latency settlement eligibility.
    
    Per PAC-JEFFREY-P01 Section 6:
    - ACK latency measurement
    - ACK → settlement eligibility binding
    """
    _ensure_demo_state()
    
    state = _control_plane_store.get(pac_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"PAC not found: {pac_id}")
    
    latency_check = check_ack_latency_eligibility(state)
    latency_summary = state.get_ack_latency_summary()
    
    return {
        "pac_id": pac_id,
        "latency_eligible": latency_check["eligible"],
        "latency_reason": latency_check["reason"],
        "threshold_ms": latency_check["threshold_ms"],
        "max_latency_ms": latency_check["max_latency_ms"],
        "latency_summary": latency_summary,
        "agent_latencies": {
            gid: ack.latency_ms
            for gid, ack in state.agent_acks.items()
        },
        "governance_invariant": "INV-CP-008: ACK latency bound to settlement eligibility",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER COMMIT ATTESTATION (PAC-JEFFREY-P02R SECTION 10)
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/state/{pac_id}/ledger-attestation")
async def get_ledger_attestation(pac_id: str) -> Dict[str, Any]:
    """
    Get ledger commit attestation status.
    
    Per PAC-JEFFREY-P02R Section 10:
    Settlement FORBIDDEN unless:
    - ber_finality = FINAL
    - ledger_commit_hash present
    - ACK latency SLA met
    """
    attestation = _ledger_attestations.get(pac_id)
    
    if not attestation:
        return {
            "pac_id": pac_id,
            "attestation_status": "PENDING",
            "attestation_id": None,
            "committed": False,
            "ledger_block": None,
            "governance_invariant": "INV-CP-007: Ledger commit attestation required for finality",
        }
    
    return {
        "pac_id": pac_id,
        "attestation_status": "COMMITTED",
        "attestation_id": attestation.attestation_id,
        "committed": True,
        "committed_at": attestation.committed_at,
        "ledger_block": attestation.ledger_block,
        "wrap_hashes": attestation.wrap_hashes,
        "ber_hash": attestation.ber_hash,
        "attestation_hash": attestation.attestation_hash,
        "governance_invariant": "INV-CP-007: Ledger commit attestation required for finality",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING SIGNALS (PAC-JEFFREY-P02R SECTION 11)
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory store for training signals
_training_signals: Dict[str, List[TrainingSignal]] = {}


@controlplane_oc_router.get("/state/{pac_id}/training-signals")
async def get_training_signals(pac_id: str) -> Dict[str, Any]:
    """
    Get Training Signals for a PAC.
    
    Per PAC-JEFFREY-P02R Section 11:
    REQUIRED FROM ALL AGENTS.
    Append-only. Immutable.
    """
    signals = _training_signals.get(pac_id, [])
    
    return {
        "pac_id": pac_id,
        "schema_version": "TRAINING_SIGNAL_SCHEMA@v1.0.0",
        "total_signals": len(signals),
        "signals": [
            {
                "signal_id": s.signal_id,
                "agent_gid": s.agent_gid,
                "agent_name": s.agent_name,
                "signal_type": s.signal_type,
                "observation": s.observation,
                "constraint_learned": s.constraint_learned,
                "recommended_enforcement": s.recommended_enforcement,
                "emitted_at": s.emitted_at,
                "signal_hash": s.signal_hash,
            }
            for s in signals
        ],
        "digest": compute_training_signal_digest(signals) if signals else None,
        "governance_invariant": "INV-CP-011: Training Signals MANDATORY per agent",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# POSITIVE CLOSURES (PAC-JEFFREY-P02R SECTION 12)
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory store for positive closures
_positive_closures: Dict[str, List[PositiveClosure]] = {}


@controlplane_oc_router.get("/state/{pac_id}/positive-closures")
async def get_positive_closures(pac_id: str) -> Dict[str, Any]:
    """
    Get Positive Closures for a PAC.
    
    Per PAC-JEFFREY-P02R Section 12:
    REQUIRED FROM ALL AGENTS.
    No Positive Closure → PAC INCOMPLETE.
    """
    closures = _positive_closures.get(pac_id, [])
    
    all_valid = all(c.is_valid() for c in closures) if closures else False
    
    return {
        "pac_id": pac_id,
        "schema_version": "POSITIVE_CLOSURE_SCHEMA@v1.0.0",
        "total_closures": len(closures),
        "all_valid": all_valid,
        "closures": [
            {
                "closure_id": c.closure_id,
                "agent_gid": c.agent_gid,
                "agent_name": c.agent_name,
                "scope_complete": c.scope_complete,
                "no_violations": c.no_violations,
                "ready_for_next_stage": c.ready_for_next_stage,
                "emitted_at": c.emitted_at,
                "closure_hash": c.closure_hash,
                "is_valid": c.is_valid(),
            }
            for c in closures
        ],
        "digest": compute_positive_closure_digest(closures) if closures else None,
        "governance_invariant": "INV-CP-012: Positive Closure MANDATORY per agent",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ACK EVIDENCE (PAC-JEFFREY-P02R SECTION 1)
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory store for full ACK evidence
_ack_evidence: Dict[str, List[AgentACKEvidence]] = {}


@controlplane_oc_router.get("/state/{pac_id}/ack-evidence")
async def get_ack_evidence(pac_id: str) -> Dict[str, Any]:
    """
    Get full ACK evidence for a PAC.
    
    Per PAC-JEFFREY-P02R Section 1:
    ACK REQUIREMENTS (HARD):
    - agent_id, gid, lane
    - concrete ISO-8601 timestamp
    - ack_latency_ms
    - authorization_scope
    - evidence_hash
    """
    evidence = _ack_evidence.get(pac_id, [])
    
    return {
        "pac_id": pac_id,
        "schema_version": "AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0",
        "total_evidence": len(evidence),
        "evidence": [
            {
                "agent_id": e.agent_id,
                "gid": e.gid,
                "lane": e.lane,
                "mode": e.mode,
                "timestamp": e.timestamp,
                "ack_latency_ms": e.ack_latency_ms,
                "authorization_scope": e.authorization_scope,
                "evidence_hash": e.evidence_hash,
            }
            for e in evidence
        ],
        "governance_invariant": "PAG-01: Full ACK evidence with concrete timestamps",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE SUMMARY (PAC-JEFFREY-P02R)
# ═══════════════════════════════════════════════════════════════════════════════

@controlplane_oc_router.get("/state/{pac_id}/governance-summary")
async def get_governance_summary(pac_id: str) -> Dict[str, Any]:
    """
    Get complete governance summary for a PAC.
    
    Aggregates all governance gates and eligibility checks.
    Includes P02R mandatory fields: Training Signals, Positive Closures.
    """
    _ensure_demo_state()
    _ensure_demo_wrap_set()
    
    state = _control_plane_store.get(pac_id)
    wrap_set = _wrap_sets.get(pac_id)
    rg01 = _review_gates.get(pac_id)
    bsrg = _bsrg_gates.get(pac_id)
    attestation = _ledger_attestations.get(pac_id)
    signals = _training_signals.get(pac_id, [])
    closures = _positive_closures.get(pac_id, [])
    
    if not state:
        raise HTTPException(status_code=404, detail=f"PAC not found: {pac_id}")
    
    latency_check = check_ack_latency_eligibility(state)
    
    return {
        "pac_id": pac_id,
        "pac_title": "PAC-JEFFREY-P03: Control Plane Hardening",
        "governance_tier": "CANONICAL",
        "fail_mode": "HARD_FAIL / FAIL-CLOSED",
        "execution_mode": "PARALLEL",
        "execution_barrier": "AGENT_ACK_BARRIER",
        "barrier_release_condition": "ALL_REQUIRED_AGENT_ACKS_PRESENT",
        "lifecycle_state": state.lifecycle_state.value,
        "gates": {
            "ack_gate": {
                "name": "PAG-01 Agent Activation",
                "status": "PASS" if state.all_acks_received() else "PENDING",
                "total": len(state.agent_acks),
                "acknowledged": sum(1 for a in state.agent_acks.values() if a.state == AgentACKState.ACKNOWLEDGED),
            },
            "wrap_gate": {
                "name": "Multi-Agent WRAP Collection",
                "status": "PASS" if wrap_set and wrap_set.is_complete() else "PENDING",
                "expected": len(wrap_set.expected_agents) if wrap_set else 0,
                "collected": len(wrap_set.collected_wraps) if wrap_set else 0,
            },
            "rg01_gate": {
                "name": "RG-01 Review Gate",
                "status": rg01.result if rg01 and rg01.result else "PENDING",
                "reviewer": "BENSON",
                "training_signals_present": rg01.training_signals_present if rg01 else False,
                "positive_closures_present": rg01.positive_closures_present if rg01 else False,
            },
            "bsrg01_gate": {
                "name": "BSRG-01 Self-Review Gate",
                "status": "PASS" if bsrg and bsrg.self_attestation else "PENDING",
                "no_override": bsrg.no_override if bsrg else False,
                "no_drift": bsrg.no_drift if bsrg else False,
                "parallel_semantics": bsrg.parallel_semantics_respected if bsrg else False,
            },
            "latency_gate": {
                "name": "ACK Latency Eligibility",
                "status": "PASS" if latency_check["eligible"] else "BLOCKED",
                "threshold_ms": ACK_LATENCY_THRESHOLD_MS,
            },
            "ledger_gate": {
                "name": "Ledger Commit Attestation",
                "status": "COMMITTED" if attestation else "PENDING",
            },
            "training_gate": {
                "name": "Training Signals",
                "status": "PASS" if len(signals) > 0 else "PENDING",
                "count": len(signals),
            },
            "closure_gate": {
                "name": "Positive Closures",
                "status": "PASS" if closures and all(c.is_valid() for c in closures) else "PENDING",
                "count": len(closures),
            },
        },
        "settlement_eligibility": state.compute_settlement_eligibility().value,
        "positive_closure": {
            "all_wraps_pass_rg01": rg01.result == "PASS" if rg01 else False,
            "bsrg01_attested": bsrg.self_attestation if bsrg else False,
            "ber_issued": state.ber is not None and state.ber.state == BERState.ISSUED if state.ber else False,
            "ledger_committed": attestation is not None,
            "training_signals_complete": len(signals) > 0,
            "positive_closures_complete": closures and all(c.is_valid() for c in closures),
        },
        "schema_references": {
            "pac": "CHAINBRIDGE_CANONICAL_PAC_SCHEMA@v1.0.0",
            "wrap": "CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v1.0.0",
            "ber": "CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0",
            "rg01": "RG01_SCHEMA@v1.0.0",
            "bsrg01": "BSRG01_SCHEMA@v1.0.0",
            "ack": "AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0",
            "training_signal": "GOVERNANCE_TRAINING_SIGNAL_SCHEMA@v1.0.0",
            "positive_closure": "POSITIVE_CLOSURE_SCHEMA@v1.0.0",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-JEFFREY-P03 ENDPOINTS — CONTROL PLANE HARDENING
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory stores for P03 primitives
_execution_barriers: Dict[str, ExecutionBarrier] = {}
_pack_attestations: Dict[str, PackImmutabilityAttestation] = {}
_closure_checklists: Dict[str, PositiveClosureChecklist] = {}


def _ensure_demo_barrier() -> str:
    """Ensure demo execution barrier exists."""
    demo_pac_id = "PAC-CP-UI-EXEC-001"
    
    if demo_pac_id not in _execution_barriers:
        barrier = create_execution_barrier(
            pac_id=demo_pac_id,
            required_agents=["GID-00", "GID-01", "GID-02", "GID-07"],
            execution_mode=ExecutionMode.PARALLEL,
            barrier_type=ExecutionBarrierType.AGENT_ACK_BARRIER,
            release_condition=BarrierReleaseCondition.ALL_REQUIRED_AGENT_ACKS_PRESENT,
        )
        
        # Add some demo ACKs
        ack1 = create_ack_evidence(
            agent_id="BENSON",
            gid="GID-00",
            lane="orchestration",
            mode="EXECUTING",
            ack_latency_ms=125,
            authorization_scope="PAC-JEFFREY-P03",
        )
        ack2 = create_ack_evidence(
            agent_id="CODY",
            gid="GID-01",
            lane="backend",
            mode="EXECUTING",
            ack_latency_ms=340,
            authorization_scope="PAC-JEFFREY-P03",
        )
        barrier.record_ack(ack1)
        barrier.record_ack(ack2)
        
        _execution_barriers[demo_pac_id] = barrier
    
    return demo_pac_id


@controlplane_oc_router.get(
    "/execution-barrier/{pac_id}",
    summary="Get execution barrier status",
    description="PAC-JEFFREY-P03 Section 2: AGENT_ACK_BARRIER with ALL_REQUIRED_AGENT_ACKS_PRESENT",
)
async def get_execution_barrier(
    pac_id: str,
    request: Request,
) -> Dict[str, Any]:
    """
    Get execution barrier status for a PAC.
    
    INV-CP-013: AGENT_ACK_BARRIER release requires ALL agent ACKs
    """
    _ensure_demo_barrier()
    barrier = _execution_barriers.get(pac_id)
    
    if not barrier:
        raise HTTPException(status_code=404, detail=f"Execution barrier not found: {pac_id}")
    
    return barrier.to_dict()


@controlplane_oc_router.get(
    "/pack-immutability/{pac_id}",
    summary="Get PACK immutability attestation",
    description="PAC-JEFFREY-P03 Section 11: PACK_IMMUTABLE enforcement",
)
async def get_pack_immutability(
    pac_id: str,
    request: Request,
) -> Dict[str, Any]:
    """
    Get PACK immutability attestation for a PAC.
    
    INV-CP-016: PACK_IMMUTABLE = true
    """
    attestation = _pack_attestations.get(pac_id)
    
    if not attestation:
        # Return pending attestation status
        return {
            "pac_id": pac_id,
            "status": "PENDING",
            "message": "PACK not yet finalized - BER required before attestation",
            "pack_immutable": False,
        }
    
    return attestation.to_dict()


@controlplane_oc_router.get(
    "/closure-checklist/{pac_id}",
    summary="Get positive closure checklist",
    description="PAC-JEFFREY-P03 Section 10: Binary closure checklist",
)
async def get_closure_checklist(
    pac_id: str,
    request: Request,
) -> Dict[str, Any]:
    """
    Get positive closure checklist for a PAC.
    
    All items must PASS for valid positive closure.
    """
    demo_pac_id = _ensure_demo_state()
    
    # Create demo checklist if not exists
    if pac_id not in _closure_checklists:
        checklist = create_positive_closure_checklist(pac_id)
        
        # Set demo values based on current state
        state = _control_plane_store.get(pac_id)
        if state:
            checklist.pag01_acks_complete = state.all_acks_received()
            wrap_set = _wrap_sets.get(pac_id)
            checklist.all_required_wraps = wrap_set.is_complete() if wrap_set else False
            rg01 = _rg01_gates.get(pac_id)
            checklist.rg01_passed = rg01.result == "PASS" if rg01 else False
            bsrg = _bsrg_gates.get(pac_id)
            checklist.bsrg01_passed = bsrg.self_attestation if bsrg else False
            checklist.ber_issued = state.ber is not None and state.ber.state == BERState.ISSUED if state.ber else False
            attestation = _ledger_attestations.get(pac_id)
            checklist.ledger_commit = "PASS" if attestation else "PROVISIONAL"
        
        checklist.evaluate()
        _closure_checklists[pac_id] = checklist
    
    checklist = _closure_checklists.get(pac_id)
    if not checklist:
        raise HTTPException(status_code=404, detail=f"Closure checklist not found: {pac_id}")
    
    return checklist.to_dict()


@controlplane_oc_router.get(
    "/agent-lanes",
    summary="Get agent lane assignments",
    description="PAC-JEFFREY-P03 Section 3: Cross-lane execution FORBIDDEN",
)
async def get_agent_lanes(request: Request) -> Dict[str, Any]:
    """
    Get all agent lane assignments.
    
    INV-CP-014: Cross-lane execution FORBIDDEN
    INV-CP-015: Implicit agent activation FORBIDDEN
    """
    return {
        "agents": [
            {"agent": "BENSON", "gid": "GID-00", "lane": "orchestration", "mode": "EXECUTING"},
            {"agent": "CODY", "gid": "GID-01", "lane": "backend", "mode": "EXECUTING"},
            {"agent": "SONNY", "gid": "GID-02", "lane": "frontend", "mode": "EXECUTING"},
            {"agent": "DAN", "gid": "GID-07", "lane": "ci_cd", "mode": "EXECUTING"},
            {"agent": "SAM", "gid": "GID-06", "lane": "security", "mode": "NON_EXECUTING"},
        ],
        "forbidden": "Cross-lane execution",
        "enforcement": "HARD_FAIL",
        "invariants": ["INV-CP-014", "INV-CP-015"],
    }


@controlplane_oc_router.get(
    "/required-wraps/{pac_id}",
    summary="Get required WRAP obligations",
    description="PAC-JEFFREY-P03 Section 6: WRAP obligations (HARD REQUIREMENT)",
)
async def get_required_wraps(
    pac_id: str,
    request: Request,
) -> Dict[str, Any]:
    """
    Get required WRAP obligations for a PAC.
    
    Per PAC-JEFFREY-P03 Section 6:
    - WRAP-CODY-GID01-<pac_id>
    - WRAP-SONNY-GID02-<pac_id>
    - WRAP-DAN-GID07-<pac_id>
    - WRAP-BENSON-GID00-<pac_id>
    """
    demo_pac_id = _ensure_demo_state()
    wrap_set = _wrap_sets.get(pac_id)
    
    required_wraps = [
        {"wrap_id": f"WRAP-CODY-GID01-{pac_id}", "agent": "CODY", "gid": "GID-01", "status": "PENDING"},
        {"wrap_id": f"WRAP-SONNY-GID02-{pac_id}", "agent": "SONNY", "gid": "GID-02", "status": "PENDING"},
        {"wrap_id": f"WRAP-DAN-GID07-{pac_id}", "agent": "DAN", "gid": "GID-07", "status": "PENDING"},
        {"wrap_id": f"WRAP-BENSON-GID00-{pac_id}", "agent": "BENSON", "gid": "GID-00", "status": "PENDING"},
    ]
    
    # Update status based on collected WRAPs
    if wrap_set:
        for wrap in required_wraps:
            if wrap["gid"] in wrap_set.collected_wraps:
                collected = wrap_set.collected_wraps[wrap["gid"]]
                wrap["status"] = collected.validation_state.value
                wrap["wrap_hash"] = collected.wrap_hash
    
    return {
        "pac_id": pac_id,
        "wrap_schema": "CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v1.0.0",
        "wrap_required": True,
        "required_wraps": required_wraps,
        "total_expected": len(required_wraps),
        "total_collected": len(wrap_set.collected_wraps) if wrap_set else 0,
        "all_collected": wrap_set.is_complete() if wrap_set else False,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT READINESS VERDICT (PAC-JEFFREY-P04)
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory store for settlement verdicts
_settlement_verdicts: Dict[str, SettlementReadinessVerdict] = {}


@controlplane_oc_router.get(
    "/settlement-readiness/{pac_id}",
    response_model=SettlementReadinessVerdictDTO,
    summary="Get Settlement Readiness Verdict",
    description="PAC-JEFFREY-P04 Section 4: Binary settlement eligibility verdict",
)
async def get_settlement_readiness(
    pac_id: str,
    request: Request,
) -> Dict[str, Any]:
    """
    Get Settlement Readiness Verdict for a PAC.
    
    INV-CP-017: SettlementReadinessVerdict REQUIRED before BER FINAL
    INV-CP-018: Settlement eligibility is BINARY - ELIGIBLE or BLOCKED
    INV-CP-019: No human override on settlement verdict
    INV-CP-020: Verdict must be machine-computed
    
    This endpoint computes the settlement readiness verdict in real-time
    based on the current state of the PAC.
    """
    demo_pac_id = _ensure_demo_state()
    
    state = _control_plane_store.get(pac_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"PAC not found: {pac_id}")
    
    # Gather all evidence for verdict computation
    wrap_set = _wrap_sets.get(pac_id)
    rg01 = _rg01_gates.get(pac_id)
    bsrg = _bsrg_gates.get(pac_id)
    training_signals = list(_training_signals.get(pac_id, {}).values())
    positive_closures = list(_positive_closures.get(pac_id, {}).values())
    ledger_attestation = _ledger_attestations.get(pac_id)
    
    # Compute verdict (machine-computed, no inference)
    verdict = evaluate_settlement_readiness(
        pac_id=pac_id,
        state=state,
        wrap_set=wrap_set,
        rg01=rg01,
        bsrg01=bsrg,
        training_signals=training_signals,
        positive_closures=positive_closures,
        ledger_attestation=ledger_attestation,
    )
    
    # Cache verdict
    _settlement_verdicts[pac_id] = verdict
    
    return verdict.to_dict()


@controlplane_oc_router.get(
    "/settlement-readiness/{pac_id}/blocking-reasons",
    summary="Get Settlement Blocking Reasons",
    description="PAC-JEFFREY-P04: List all reasons blocking settlement",
)
async def get_settlement_blocking_reasons(
    pac_id: str,
    request: Request,
) -> Dict[str, Any]:
    """
    Get detailed blocking reasons for settlement.
    
    Returns empty list if settlement is ELIGIBLE.
    """
    demo_pac_id = _ensure_demo_state()
    
    # Get or compute verdict
    verdict = _settlement_verdicts.get(pac_id)
    if not verdict:
        # Force computation
        state = _control_plane_store.get(pac_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"PAC not found: {pac_id}")
        
        verdict = evaluate_settlement_readiness(
            pac_id=pac_id,
            state=state,
            wrap_set=_wrap_sets.get(pac_id),
            rg01=_rg01_gates.get(pac_id),
            bsrg01=_bsrg_gates.get(pac_id),
            training_signals=list(_training_signals.get(pac_id, {}).values()),
            positive_closures=list(_positive_closures.get(pac_id, {}).values()),
            ledger_attestation=_ledger_attestations.get(pac_id),
        )
    
    return {
        "pac_id": pac_id,
        "status": verdict.status.value,
        "is_blocked": verdict.status == SettlementReadinessStatus.BLOCKED,
        "blocking_count": len(verdict.blocking_reasons),
        "blocking_reasons": [
            {
                "reason": br.reason.value,
                "description": br.description,
                "source_type": br.source_type,
                "source_ref": br.source_ref,
                "detected_at": br.detected_at,
            }
            for br in verdict.blocking_reasons
        ],
        "governance_invariants": [
            "INV-CP-017: SettlementReadinessVerdict REQUIRED before BER FINAL",
            "INV-CP-018: Settlement eligibility is BINARY",
            "INV-CP-019: No human override on settlement verdict",
            "INV-CP-020: Verdict must be machine-computed",
        ],
    }
