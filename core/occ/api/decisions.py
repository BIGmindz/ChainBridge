"""
OCC Decision API

Endpoints for managing decisions with ProofPack linkage,
deterministic replay, and time-travel audit support.

Mounted at /occ/decisions

Author: CINDY (GID-04) - Backend

Endpoints:
- POST /occ/decisions           - Create a new decision
- GET  /occ/decisions           - List decisions with filters
- GET  /occ/decisions/{id}      - Get decision by ID
- POST /occ/decisions/{id}/link-proofpack - Link a ProofPack to a decision
- POST /occ/decisions/replay    - Replay a decision for verification
- POST /occ/decisions/time-travel - Query decisions at a point in time
- GET  /occ/decisions/artifact/{id} - Get decisions for an artifact
- GET  /occ/decisions/shipment/{id} - Get decisions for a shipment
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.occ.schemas.decision import (
    Decision,
    DecisionCreate,
    DecisionListResponse,
    DecisionOutcome,
    DecisionReplayRequest,
    DecisionReplayResult,
    DecisionTimeTravelQuery,
    DecisionTimeTravelResult,
    DecisionType,
)
from core.occ.store.artifact_store import ArtifactStore, get_artifact_store
from core.occ.store.decision_store import DecisionStore, get_decision_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/decisions", tags=["OCC Decisions"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class DecisionWithProofPackResponse(BaseModel):
    """Decision with linked ProofPack info."""

    decision: Decision
    proofpack_linked: bool = Field(..., description="Whether a ProofPack is linked")
    proofpack_id: Optional[UUID] = Field(None, description="Linked ProofPack ID")


class LinkProofPackRequest(BaseModel):
    """Request to link a ProofPack to a decision."""

    proofpack_id: UUID = Field(..., description="ProofPack ID to link")


class LinkProofPackResponse(BaseModel):
    """Response after linking a ProofPack."""

    decision: Decision
    proofpack_id: UUID
    message: str = "ProofPack linked successfully"


# =============================================================================
# CRUD ENDPOINTS
# =============================================================================


@router.post("", response_model=Decision, status_code=201)
async def create_decision(
    decision_in: DecisionCreate,
    store: DecisionStore = Depends(get_decision_store),
) -> Decision:
    """
    Create a new decision record.

    Decisions are immutable once created. The input_snapshot captures
    all inputs at decision time for deterministic replay verification.

    The decision can optionally be linked to artifacts and a ProofPack
    for complete audit traceability.
    """
    try:
        decision = store.create(decision_in)
        logger.info(f"Created decision {decision.id}: {decision.decision_type} -> {decision.outcome}")
        return decision
    except Exception as e:
        logger.error(f"Failed to create decision: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create decision: {str(e)}")


@router.get("", response_model=DecisionListResponse)
async def list_decisions(
    decision_type: Optional[DecisionType] = Query(None, description="Filter by decision type"),
    outcome: Optional[DecisionOutcome] = Query(None, description="Filter by outcome"),
    actor: Optional[str] = Query(None, description="Filter by actor"),
    artifact_id: Optional[UUID] = Query(None, description="Filter by linked artifact"),
    shipment_id: Optional[str] = Query(None, description="Filter by shipment ID"),
    limit: Optional[int] = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip results"),
    store: DecisionStore = Depends(get_decision_store),
) -> DecisionListResponse:
    """
    List decisions with optional filtering and pagination.

    Returns decisions sorted by created_at descending (newest first).
    """
    items = store.list(
        decision_type=decision_type,
        outcome=outcome,
        actor=actor,
        artifact_id=artifact_id,
        shipment_id=shipment_id,
        limit=limit,
        offset=offset,
    )

    # Get total count (without pagination)
    total_items = store.list(
        decision_type=decision_type,
        outcome=outcome,
        actor=actor,
        artifact_id=artifact_id,
        shipment_id=shipment_id,
    )

    return DecisionListResponse(
        items=items,
        count=len(items),
        total=len(total_items),
        limit=limit,
        offset=offset,
    )


@router.get("/{decision_id}", response_model=DecisionWithProofPackResponse)
async def get_decision(
    decision_id: UUID,
    store: DecisionStore = Depends(get_decision_store),
) -> DecisionWithProofPackResponse:
    """
    Get a specific decision by ID.

    Returns the decision with ProofPack linkage status.
    """
    decision = store.get(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")

    return DecisionWithProofPackResponse(
        decision=decision,
        proofpack_linked=decision.proofpack_id is not None,
        proofpack_id=decision.proofpack_id,
    )


# =============================================================================
# PROOFPACK LINKAGE
# =============================================================================


@router.post("/{decision_id}/link-proofpack", response_model=LinkProofPackResponse)
async def link_proofpack_to_decision(
    decision_id: UUID,
    request: LinkProofPackRequest,
    store: DecisionStore = Depends(get_decision_store),
) -> LinkProofPackResponse:
    """
    Link a ProofPack to a decision.

    This creates a verifiable audit trail linking the decision
    to its evidence bundle. Once linked, the association is immutable.

    Note: The ProofPack should be generated first via /occ/proofpacks.
    """
    decision = store.link_proofpack(decision_id, request.proofpack_id)
    if decision is None:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")

    logger.info(f"Linked ProofPack {request.proofpack_id} to decision {decision_id}")

    return LinkProofPackResponse(
        decision=decision,
        proofpack_id=request.proofpack_id,
    )


# =============================================================================
# DECISION REPLAY
# =============================================================================


@router.post("/replay", response_model=DecisionReplayResult)
async def replay_decision(
    request: DecisionReplayRequest,
    store: DecisionStore = Depends(get_decision_store),
) -> DecisionReplayResult:
    """
    Replay a decision using its original input snapshot.

    This enables **deterministic verification**: given the same inputs
    and decision logic, we should get the same output.

    Use cases:
    - Audit verification: prove a decision was correctly made
    - Regression testing: ensure decision logic hasn't changed
    - Debugging: trace why a specific decision was made

    Options:
    - dry_run (default: true): Don't persist the replayed decision
    - compare_output: Compare replay output with original

    Returns:
    - Original and replayed decisions
    - Whether outcome is deterministic (identical)
    - List of differences if any
    - Input hash verification
    """
    try:
        result = store.replay_decision(request)

        if result.is_deterministic:
            logger.info(f"Decision {request.decision_id} replay: DETERMINISTIC ✓")
        else:
            logger.warning(f"Decision {request.decision_id} replay: NON-DETERMINISTIC - " f"differences: {result.differences}")

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Decision replay failed: {e}")
        raise HTTPException(status_code=500, detail=f"Replay failed: {str(e)}")


# =============================================================================
# TIME-TRAVEL AUDIT
# =============================================================================


@router.post("/time-travel", response_model=DecisionTimeTravelResult)
async def time_travel_query(
    query: DecisionTimeTravelQuery,
    store: DecisionStore = Depends(get_decision_store),
) -> DecisionTimeTravelResult:
    """
    Query decisions as they existed at a point in time.

    This enables **time-travel audit**: see exactly what decisions
    were visible/active at any historical moment.

    Use cases:
    - Compliance audit: reconstruct decision state at audit date
    - Dispute resolution: prove what was decided when
    - Forensics: investigate decision timeline

    Query parameters:
    - as_of (required): Point-in-time to query (UTC)
    - window_start (optional): Start of time window
    - artifact_id / shipment_id: Filter by related entity
    - decision_types: Filter by decision types
    - actors: Filter by decision makers

    Returns:
    - Decisions matching query
    - State hash (fingerprint of decision state at query time)
    """
    try:
        result = store.time_travel_query(query)

        logger.info(f"Time-travel query as_of={query.as_of}: " f"found {result.count} decisions, state_hash={result.state_hash[:16]}...")

        return result
    except Exception as e:
        logger.error(f"Time-travel query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# =============================================================================
# CONVENIENCE ENDPOINTS
# =============================================================================


@router.get("/artifact/{artifact_id}", response_model=List[Decision])
async def get_decisions_for_artifact(
    artifact_id: UUID,
    store: DecisionStore = Depends(get_decision_store),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> List[Decision]:
    """
    Get all decisions linked to a specific artifact.

    Returns decisions sorted by created_at ascending (chronological order).
    """
    # Verify artifact exists
    artifact = artifact_store.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    decisions = store.get_decisions_for_artifact(artifact_id)
    decisions.sort(key=lambda d: d.created_at)

    return decisions


@router.get("/shipment/{shipment_id}", response_model=List[Decision])
async def get_decisions_for_shipment(
    shipment_id: str,
    store: DecisionStore = Depends(get_decision_store),
) -> List[Decision]:
    """
    Get all decisions for a specific shipment.

    Returns decisions sorted by created_at ascending (chronological order).
    """
    decisions = store.get_decisions_for_shipment(shipment_id)
    decisions.sort(key=lambda d: d.created_at)

    return decisions


# =============================================================================
# BATCH OPERATIONS
# =============================================================================


class BatchReplayRequest(BaseModel):
    """Request to replay multiple decisions."""

    decision_ids: List[UUID] = Field(..., description="Decision IDs to replay")
    dry_run: bool = Field(default=True, description="Don't persist replayed decisions")


class BatchReplayResult(BaseModel):
    """Result of batch replay operation."""

    total: int
    deterministic_count: int
    non_deterministic_count: int
    failed_count: int
    results: List[DecisionReplayResult]


@router.post("/replay/batch", response_model=BatchReplayResult)
async def batch_replay_decisions(
    request: BatchReplayRequest,
    store: DecisionStore = Depends(get_decision_store),
) -> BatchReplayResult:
    """
    Replay multiple decisions in batch.

    Useful for:
    - Bulk audit verification
    - Regression testing across decision set
    - Drift detection in decision logic

    Returns aggregate statistics plus individual results.
    """
    results = []
    deterministic_count = 0
    non_deterministic_count = 0
    failed_count = 0

    for decision_id in request.decision_ids:
        try:
            replay_request = DecisionReplayRequest(
                decision_id=decision_id,
                dry_run=request.dry_run,
            )
            result = store.replay_decision(replay_request)
            results.append(result)

            if result.is_deterministic:
                deterministic_count += 1
            else:
                non_deterministic_count += 1

        except Exception as e:
            logger.error(f"Batch replay failed for {decision_id}: {e}")
            failed_count += 1

    logger.info(
        f"Batch replay complete: {deterministic_count} deterministic, "
        f"{non_deterministic_count} non-deterministic, {failed_count} failed"
    )

    return BatchReplayResult(
        total=len(request.decision_ids),
        deterministic_count=deterministic_count,
        non_deterministic_count=non_deterministic_count,
        failed_count=failed_count,
        results=results,
    )
