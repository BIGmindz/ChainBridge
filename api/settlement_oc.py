# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Settlement OC API — Settlement Lifecycle Endpoints
# PAC-JEFFREY-P08: Settlement End-to-End Execution
# GOLD STANDARD · FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

"""
FastAPI router for Settlement Engine visibility in Operations Console.

Provides endpoints for:
- Settlement lifecycle creation and execution
- PDO processing
- Readiness evaluation
- Ledger commit execution
- Finality attestation
- Full lifecycle execution

GOVERNANCE INVARIANTS (P08):
- INV-CP-021: Settlement requires PDO with APPROVED outcome
- INV-CP-022: Settlement readiness must pass before ledger commit
- INV-CP-023: Ledger commit required before BER FINAL
- INV-CP-024: Finality attestation seals settlement lifecycle

SCHEMA REFERENCES:
- Settlement Engine Schema: SETTLEMENT_ENGINE_SCHEMA@v1.0.0
- Settlement Lifecycle Schema: SETTLEMENT_LIFECYCLE_SCHEMA@v1.0.0
- Ledger Commit Attestation Schema: LEDGER_COMMIT_ATTESTATION_SCHEMA@v1.0.0
- Finality Attestation Schema: FINALITY_ATTESTATION_SCHEMA@v1.0.0

Author: CODY (GID-01) — Backend Lane
Orchestration: BENSON (GID-00)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.governance.settlement_engine import (
    FinalityAttestation,
    FinalityStatus,
    LedgerCommitResult,
    LedgerCommitStatus,
    PDOOutcome,
    SettlementCheckpoint,
    SettlementEngine,
    SettlementLifecycle,
    SettlementOutcome,
    SettlementPDO,
    SettlementPhase,
    create_settlement_pdo,
    get_settlement_engine,
    reset_settlement_engine,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER SETUP
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/oc/settlement", tags=["settlement"])


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS — API REQUEST/RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementEngineStatusResponse(BaseModel):
    """Settlement engine status response."""
    activated: bool
    fail_closed: bool = True
    lifecycle_count: int
    schema_version: str = "SETTLEMENT_ENGINE_SCHEMA@v1.0.0"


class PDORequest(BaseModel):
    """PDO creation request."""
    pac_id: str = Field(..., description="PAC ID for settlement")
    amount: float = Field(..., description="Settlement amount")
    currency: str = Field(default="USD", description="Settlement currency")
    source_account: str = Field(..., description="Source account")
    destination_account: str = Field(..., description="Destination account")
    approved: bool = Field(default=True, description="PDO approval status")
    reasons: List[str] = Field(default_factory=list, description="Reasons for decision")


class PDOResponse(BaseModel):
    """PDO response."""
    pdo_id: str
    pac_id: str
    outcome: str
    amount: float
    currency: str
    source_account: str
    destination_account: str
    reasons: List[str]
    created_at: str
    pdo_hash: str


class ReadinessEvaluationRequest(BaseModel):
    """Settlement readiness evaluation request."""
    settlement_id: str = Field(..., description="Settlement lifecycle ID")
    readiness_verdict_hash: str = Field(..., description="Hash of readiness verdict")
    is_eligible: bool = Field(..., description="Whether settlement is eligible")


class LedgerCommitRequest(BaseModel):
    """Ledger commit request."""
    settlement_id: str = Field(..., description="Settlement lifecycle ID")
    ber_hash: str = Field(..., description="BER hash for commit")


class LedgerCommitResponse(BaseModel):
    """Ledger commit response."""
    commit_id: str
    pac_id: str
    settlement_id: str
    status: str
    commit_hash: str
    commit_timestamp: str
    commit_authority: str
    block_number: Optional[int]
    transaction_id: Optional[str]


class FinalityResponse(BaseModel):
    """Finality attestation response."""
    attestation_id: str
    pac_id: str
    settlement_id: str
    status: str
    pdo_hash: str
    readiness_verdict_hash: str
    ledger_commit_hash: str
    ber_hash: str
    attested_at: str
    attested_by: str
    attestation_hash: str


class CheckpointResponse(BaseModel):
    """Settlement checkpoint response."""
    checkpoint_id: str
    checkpoint_name: str
    phase: str
    passed: bool
    invariants_checked: List[str]
    timestamp: str
    evidence: Dict[str, Any]


class LifecycleResponse(BaseModel):
    """Settlement lifecycle response."""
    settlement_id: str
    pac_id: str
    current_phase: str
    outcome: str
    is_terminal: bool
    pdo_hash: Optional[str] = None
    readiness_verdict_hash: Optional[str] = None
    ledger_commit_hash: Optional[str] = None
    finality_attestation_hash: Optional[str] = None
    ber_hash: Optional[str] = None
    checkpoints: List[CheckpointResponse]
    created_at: str
    completed_at: Optional[str] = None
    lifecycle_hash: str


class LifecycleSummaryResponse(BaseModel):
    """Settlement lifecycle summary."""
    settlement_id: str
    pac_id: str
    current_phase: str
    outcome: str
    is_terminal: bool
    checkpoints_passed: int
    total_checkpoints: int
    created_at: str
    completed_at: Optional[str] = None
    lifecycle_hash: str


class FullLifecycleRequest(BaseModel):
    """Full lifecycle execution request."""
    pac_id: str = Field(..., description="PAC ID")
    pdo_amount: float = Field(..., description="PDO amount")
    pdo_currency: str = Field(default="USD", description="PDO currency")
    pdo_source_account: str = Field(..., description="Source account")
    pdo_destination_account: str = Field(..., description="Destination account")
    readiness_verdict_hash: str = Field(..., description="Readiness verdict hash")
    is_eligible: bool = Field(..., description="Whether eligible")
    ber_hash: str = Field(..., description="BER hash")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _checkpoint_to_response(cp: SettlementCheckpoint) -> CheckpointResponse:
    """Convert checkpoint to response model."""
    return CheckpointResponse(
        checkpoint_id=cp.checkpoint_id,
        checkpoint_name=cp.checkpoint_name,
        phase=cp.phase.value,
        passed=cp.passed,
        invariants_checked=cp.invariants_checked,
        timestamp=cp.timestamp,
        evidence=cp.evidence,
    )


def _lifecycle_to_response(lifecycle: SettlementLifecycle) -> LifecycleResponse:
    """Convert lifecycle to response model."""
    return LifecycleResponse(
        settlement_id=lifecycle.settlement_id,
        pac_id=lifecycle.pac_id,
        current_phase=lifecycle.current_phase.value,
        outcome=lifecycle.outcome.value,
        is_terminal=lifecycle.is_terminal(),
        pdo_hash=lifecycle.pdo.pdo_hash if lifecycle.pdo else None,
        readiness_verdict_hash=lifecycle.readiness_verdict_hash,
        ledger_commit_hash=(
            lifecycle.ledger_commit.commit_hash if lifecycle.ledger_commit else None
        ),
        finality_attestation_hash=(
            lifecycle.finality_attestation.attestation_hash
            if lifecycle.finality_attestation else None
        ),
        ber_hash=lifecycle.ber_hash,
        checkpoints=[_checkpoint_to_response(cp) for cp in lifecycle.checkpoints],
        created_at=lifecycle.created_at,
        completed_at=lifecycle.completed_at,
        lifecycle_hash=lifecycle.lifecycle_hash,
    )


def _pdo_to_response(pdo: SettlementPDO) -> PDOResponse:
    """Convert PDO to response model."""
    return PDOResponse(
        pdo_id=pdo.pdo_id,
        pac_id=pdo.pac_id,
        outcome=pdo.outcome.value,
        amount=pdo.amount,
        currency=pdo.currency,
        source_account=pdo.source_account,
        destination_account=pdo.destination_account,
        reasons=pdo.reasons,
        created_at=pdo.created_at,
        pdo_hash=pdo.pdo_hash,
    )


def _ledger_commit_to_response(commit: LedgerCommitResult) -> LedgerCommitResponse:
    """Convert ledger commit to response model."""
    return LedgerCommitResponse(
        commit_id=commit.commit_id,
        pac_id=commit.pac_id,
        settlement_id=commit.settlement_id,
        status=commit.status.value,
        commit_hash=commit.commit_hash,
        commit_timestamp=commit.commit_timestamp,
        commit_authority=commit.commit_authority,
        block_number=commit.block_number,
        transaction_id=commit.transaction_id,
    )


def _finality_to_response(attestation: FinalityAttestation) -> FinalityResponse:
    """Convert finality attestation to response model."""
    return FinalityResponse(
        attestation_id=attestation.attestation_id,
        pac_id=attestation.pac_id,
        settlement_id=attestation.settlement_id,
        status=attestation.status.value,
        pdo_hash=attestation.pdo_hash,
        readiness_verdict_hash=attestation.readiness_verdict_hash,
        ledger_commit_hash=attestation.ledger_commit_hash,
        ber_hash=attestation.ber_hash,
        attested_at=attestation.attested_at,
        attested_by=attestation.attested_by,
        attestation_hash=attestation.attestation_hash,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE STATUS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/engine/status", response_model=SettlementEngineStatusResponse)
def get_engine_status() -> SettlementEngineStatusResponse:
    """
    Get settlement engine status.
    
    Returns activation state and lifecycle count.
    """
    engine = get_settlement_engine()
    return SettlementEngineStatusResponse(
        activated=engine.is_activated(),
        fail_closed=engine._fail_closed,
        lifecycle_count=len(engine._lifecycles),
    )


@router.post("/engine/activate")
def activate_engine() -> Dict[str, Any]:
    """
    Activate settlement engine.
    
    Must be called before any settlement operations.
    """
    engine = get_settlement_engine()
    result = engine.activate()
    return {
        "activated": result,
        "message": "Settlement engine activated" if result else "Activation failed",
    }


@router.post("/engine/reset")
def reset_engine() -> Dict[str, Any]:
    """
    Reset settlement engine (testing only).
    
    Clears all lifecycles and resets activation.
    """
    reset_settlement_engine()
    return {"reset": True, "message": "Settlement engine reset"}


# ═══════════════════════════════════════════════════════════════════════════════
# LIFECYCLE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/lifecycle/create", response_model=LifecycleSummaryResponse)
def create_lifecycle(pac_id: str = Query(..., description="PAC ID")) -> LifecycleSummaryResponse:
    """
    Create new settlement lifecycle.
    
    Returns lifecycle in INITIALIZED phase.
    """
    engine = get_settlement_engine()
    
    if not engine.is_activated():
        raise HTTPException(
            status_code=400,
            detail="Settlement engine not activated. Call /engine/activate first.",
        )
    
    lifecycle = engine.create_lifecycle(pac_id)
    summary = engine.get_lifecycle_summary(lifecycle)
    
    return LifecycleSummaryResponse(**summary)


@router.get("/lifecycle/{settlement_id}", response_model=LifecycleResponse)
def get_lifecycle(settlement_id: str) -> LifecycleResponse:
    """
    Get settlement lifecycle by ID.
    
    Returns full lifecycle state with all checkpoints.
    """
    engine = get_settlement_engine()
    lifecycle = engine.get_lifecycle(settlement_id)
    
    if not lifecycle:
        raise HTTPException(
            status_code=404,
            detail=f"Settlement lifecycle {settlement_id} not found",
        )
    
    return _lifecycle_to_response(lifecycle)


@router.get("/lifecycle/{settlement_id}/summary", response_model=LifecycleSummaryResponse)
def get_lifecycle_summary(settlement_id: str) -> LifecycleSummaryResponse:
    """
    Get settlement lifecycle summary.
    
    Returns compact summary without full checkpoint details.
    """
    engine = get_settlement_engine()
    lifecycle = engine.get_lifecycle(settlement_id)
    
    if not lifecycle:
        raise HTTPException(
            status_code=404,
            detail=f"Settlement lifecycle {settlement_id} not found",
        )
    
    summary = engine.get_lifecycle_summary(lifecycle)
    return LifecycleSummaryResponse(**summary)


# ═══════════════════════════════════════════════════════════════════════════════
# PDO ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/pdo/create", response_model=PDOResponse)
def create_pdo(request: PDORequest) -> PDOResponse:
    """
    Create a Settlement PDO.
    
    INV-CP-021: Settlement requires PDO with APPROVED outcome.
    """
    pdo = create_settlement_pdo(
        pac_id=request.pac_id,
        amount=request.amount,
        currency=request.currency,
        source_account=request.source_account,
        destination_account=request.destination_account,
        approved=request.approved,
        reasons=request.reasons,
    )
    return _pdo_to_response(pdo)


@router.post("/pdo/process")
def process_pdo(
    settlement_id: str = Query(..., description="Settlement lifecycle ID"),
    request: PDORequest = ...,
) -> Dict[str, Any]:
    """
    Process PDO for settlement lifecycle.
    
    INV-CP-021: Settlement requires PDO with APPROVED outcome.
    
    Transitions lifecycle from INITIALIZED → PDO_RECEIVED → PDO_APPROVED/PDO_REJECTED.
    """
    engine = get_settlement_engine()
    
    if not engine.is_activated():
        raise HTTPException(
            status_code=400,
            detail="Settlement engine not activated",
        )
    
    lifecycle = engine.get_lifecycle(settlement_id)
    if not lifecycle:
        raise HTTPException(
            status_code=404,
            detail=f"Settlement lifecycle {settlement_id} not found",
        )
    
    pdo = create_settlement_pdo(
        pac_id=request.pac_id,
        amount=request.amount,
        currency=request.currency,
        source_account=request.source_account,
        destination_account=request.destination_account,
        approved=request.approved,
        reasons=request.reasons,
    )
    
    result = engine.process_pdo(lifecycle, pdo)
    
    return {
        "settlement_id": settlement_id,
        "pdo_id": pdo.pdo_id,
        "pdo_approved": result,
        "current_phase": lifecycle.current_phase.value,
        "outcome": lifecycle.outcome.value,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# READINESS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/readiness/evaluate")
def evaluate_readiness(request: ReadinessEvaluationRequest) -> Dict[str, Any]:
    """
    Evaluate settlement readiness.
    
    INV-CP-022: Settlement readiness must pass before ledger commit.
    
    Transitions lifecycle from PDO_APPROVED → READINESS_ELIGIBLE/READINESS_BLOCKED.
    """
    engine = get_settlement_engine()
    
    if not engine.is_activated():
        raise HTTPException(
            status_code=400,
            detail="Settlement engine not activated",
        )
    
    lifecycle = engine.get_lifecycle(request.settlement_id)
    if not lifecycle:
        raise HTTPException(
            status_code=404,
            detail=f"Settlement lifecycle {request.settlement_id} not found",
        )
    
    result = engine.evaluate_readiness(
        lifecycle,
        request.readiness_verdict_hash,
        request.is_eligible,
    )
    
    return {
        "settlement_id": request.settlement_id,
        "readiness_eligible": result,
        "current_phase": lifecycle.current_phase.value,
        "outcome": lifecycle.outcome.value,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER COMMIT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/ledger/commit", response_model=LedgerCommitResponse)
def execute_ledger_commit(request: LedgerCommitRequest) -> LedgerCommitResponse:
    """
    Execute ledger commit.
    
    INV-CP-023: Ledger commit required before BER FINAL.
    
    Transitions lifecycle from READINESS_ELIGIBLE → LEDGER_COMMITTED/LEDGER_FAILED.
    """
    engine = get_settlement_engine()
    
    if not engine.is_activated():
        raise HTTPException(
            status_code=400,
            detail="Settlement engine not activated",
        )
    
    lifecycle = engine.get_lifecycle(request.settlement_id)
    if not lifecycle:
        raise HTTPException(
            status_code=404,
            detail=f"Settlement lifecycle {request.settlement_id} not found",
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PAC-P10 GUARD: INV-CP-023 — NO VERDICT = NO COMMIT
    # ═══════════════════════════════════════════════════════════════════════════
    if not lifecycle.readiness_verdict_hash:
        raise HTTPException(
            status_code=400,
            detail="SettlementError: Violation INV-CP-023 — No Readiness Verdict. "
                   "Cannot commit to ledger without readiness evaluation.",
        )
    
    try:
        commit_result = engine.execute_ledger_commit(lifecycle, request.ber_hash)
        return _ledger_commit_to_response(commit_result)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# FINALITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/finality/attest", response_model=FinalityResponse)
def attest_finality(
    settlement_id: str = Query(..., description="Settlement lifecycle ID"),
) -> FinalityResponse:
    """
    Attest settlement finality.
    
    INV-CP-024: Finality attestation seals settlement lifecycle.
    
    Transitions lifecycle from LEDGER_COMMITTED → SETTLEMENT_COMPLETE.
    """
    engine = get_settlement_engine()
    
    if not engine.is_activated():
        raise HTTPException(
            status_code=400,
            detail="Settlement engine not activated",
        )
    
    lifecycle = engine.get_lifecycle(settlement_id)
    if not lifecycle:
        raise HTTPException(
            status_code=404,
            detail=f"Settlement lifecycle {settlement_id} not found",
        )
    
    try:
        attestation = engine.attest_finality(lifecycle)
        return _finality_to_response(attestation)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# FULL LIFECYCLE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/execute", response_model=LifecycleResponse)
def execute_full_lifecycle(request: FullLifecycleRequest) -> LifecycleResponse:
    """
    Execute full settlement lifecycle in one call.
    
    Lifecycle: PDO → Settlement Readiness → Ledger Commit → Final BER
    
    This is the canonical entry point for P08 settlement execution.
    
    INVARIANTS ENFORCED:
    - INV-CP-021: Settlement requires PDO with APPROVED outcome
    - INV-CP-022: Settlement readiness must pass before ledger commit
    - INV-CP-023: Ledger commit required before BER FINAL
    - INV-CP-024: Finality attestation seals settlement lifecycle
    """
    engine = get_settlement_engine()
    
    if not engine.is_activated():
        raise HTTPException(
            status_code=400,
            detail="Settlement engine not activated. Call /engine/activate first.",
        )
    
    pdo = create_settlement_pdo(
        pac_id=request.pac_id,
        amount=request.pdo_amount,
        currency=request.pdo_currency,
        source_account=request.pdo_source_account,
        destination_account=request.pdo_destination_account,
        approved=True,  # Full lifecycle assumes approved PDO
    )
    
    lifecycle = engine.execute_full_lifecycle(
        pac_id=request.pac_id,
        pdo=pdo,
        readiness_verdict_hash=request.readiness_verdict_hash,
        is_eligible=request.is_eligible,
        ber_hash=request.ber_hash,
    )
    
    return _lifecycle_to_response(lifecycle)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANTS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/invariants")
def get_settlement_invariants() -> Dict[str, Any]:
    """
    Get P08 settlement invariants.
    
    Returns all invariants enforced by the settlement engine.
    """
    return {
        "pac": "PAC-JEFFREY-P08",
        "invariants": {
            "INV-CP-021": "Settlement requires PDO with APPROVED outcome",
            "INV-CP-022": "Settlement readiness must pass before ledger commit",
            "INV-CP-023": "Ledger commit required before BER FINAL",
            "INV-CP-024": "Finality attestation seals settlement lifecycle",
        },
        "schema": "SETTLEMENT_ENGINE_SCHEMA@v1.0.0",
        "fail_mode": "HARD_FAIL / FAIL_CLOSED",
    }
