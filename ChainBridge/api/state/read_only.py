"""
ChainBridge Read-Only State API

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

This module provides READ-ONLY API endpoints for state observation.
NO write endpoints exist in this module.

Used by:
- Operator Console
- Audit / Regulator views
- Monitoring systems
- Dispute resolution
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.state import (
    ArtifactType,
    StateValidator,
    StateReplayEngine,
    ValidationResult,
    ReplayResult,
    EventStateRecord,
)

# =============================================================================
# API ROUTER
# =============================================================================

router = APIRouter(
    prefix="/api/state/v1",
    tags=["state", "read-only"],
    responses={
        403: {"description": "Write operations forbidden"},
        404: {"description": "Artifact not found"},
    },
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class StateQueryResponse(BaseModel):
    """Response for state queries."""

    artifact_type: str
    artifact_id: str
    current_state: str
    last_updated: datetime
    is_finalized: bool
    proof_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    queried_at: datetime = Field(default_factory=datetime.utcnow)


class StateHistoryResponse(BaseModel):
    """Response for state history queries."""

    artifact_type: str
    artifact_id: str
    transitions: list[dict[str, Any]]
    total_transitions: int
    queried_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationResponse(BaseModel):
    """Response for validation requests."""

    artifact_type: str
    artifact_id: str
    is_valid: bool
    violation_count: int
    violations: list[dict[str, Any]]
    warnings: list[str]
    validated_at: datetime


class ReplayRequest(BaseModel):
    """Request for state replay (read-only verification)."""

    artifact_type: str
    artifact_id: str
    events: list[dict[str, Any]]
    expected_state: Optional[str] = None
    expected_hash: Optional[str] = None


class ReplayResponse(BaseModel):
    """Response for replay verification."""

    is_deterministic: bool
    computed_state: Optional[str]
    expected_state: Optional[str]
    state_hash: str
    hashes_match: bool
    events_processed: int
    transitions_applied: int
    validation_errors: list[str]
    replayed_at: datetime
    duration_ms: float


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    component: str
    read_only: bool = True
    write_endpoints: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# READ-ONLY ENDPOINTS
# =============================================================================


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check for state API.

    Confirms:
    - Service is running
    - Read-only mode active
    - No write endpoints exposed
    """
    return HealthResponse(
        status="healthy",
        component="state-api",
        read_only=True,
        write_endpoints=0,
    )


@router.get("/shipment/{shipment_id}", response_model=StateQueryResponse)
async def get_shipment_state(shipment_id: str) -> StateQueryResponse:
    """
    Get current state of a shipment.

    READ-ONLY: No state modification.
    """
    # In production, this would query the state store
    # For now, return a placeholder indicating read-only nature
    raise HTTPException(
        status_code=501,
        detail="State store integration pending. This is a read-only endpoint.",
    )


@router.get("/settlement/{settlement_id}", response_model=StateQueryResponse)
async def get_settlement_state(settlement_id: str) -> StateQueryResponse:
    """
    Get current state of a settlement.

    READ-ONLY: No state modification.
    """
    raise HTTPException(
        status_code=501,
        detail="State store integration pending. This is a read-only endpoint.",
    )


@router.get("/pdo/{pdo_id}", response_model=StateQueryResponse)
async def get_pdo_state(pdo_id: str) -> StateQueryResponse:
    """
    Get current state of a PDO.

    READ-ONLY: No state modification.
    """
    raise HTTPException(
        status_code=501,
        detail="State store integration pending. This is a read-only endpoint.",
    )


@router.get("/proof/{proof_id}", response_model=StateQueryResponse)
async def get_proof_state(proof_id: str) -> StateQueryResponse:
    """
    Get current state of a proof artifact.

    READ-ONLY: No state modification.
    """
    raise HTTPException(
        status_code=501,
        detail="State store integration pending. This is a read-only endpoint.",
    )


@router.get("/history/{artifact_type}/{artifact_id}", response_model=StateHistoryResponse)
async def get_state_history(
    artifact_type: str,
    artifact_id: str,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
) -> StateHistoryResponse:
    """
    Get transition history for an artifact.

    READ-ONLY: No state modification.
    Returns ordered list of state transitions.
    """
    raise HTTPException(
        status_code=501,
        detail="State store integration pending. This is a read-only endpoint.",
    )


@router.get("/validate/{artifact_type}/{artifact_id}", response_model=ValidationResponse)
async def validate_artifact_state(
    artifact_type: str,
    artifact_id: str,
) -> ValidationResponse:
    """
    Validate current state of an artifact.

    READ-ONLY: Performs validation checks without modification.
    Checks:
    - No duplicate states
    - Valid transitions
    - Proof lineage
    - Temporal ordering
    """
    raise HTTPException(
        status_code=501,
        detail="State store integration pending. This is a read-only endpoint.",
    )


@router.post("/replay", response_model=ReplayResponse)
async def replay_state(request: ReplayRequest) -> ReplayResponse:
    """
    Replay events and verify state determinism.

    READ-ONLY: This endpoint is idempotent and does not modify state.
    It computes what the state WOULD be given the events.

    Used for:
    - Audit verification
    - Dispute resolution
    - Consistency checks
    """
    try:
        artifact_type = ArtifactType(request.artifact_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid artifact_type: {request.artifact_type}",
        )

    # Convert events to EventStateRecord objects
    # In production, this would properly deserialize
    events: list[EventStateRecord] = []
    for i, event_dict in enumerate(request.events):
        try:
            event = EventStateRecord(
                event_id=event_dict.get("event_id", f"replay-{i}"),
                event_type=event_dict.get("event_type", "UNKNOWN"),
                artifact_type=artifact_type,
                artifact_id=request.artifact_id,
                timestamp=datetime.fromisoformat(event_dict.get("timestamp", datetime.utcnow().isoformat())),
                sequence_number=event_dict.get("sequence_number", i),
                payload_hash=event_dict.get("payload_hash", ""),
            )
            events.append(event)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event at index {i}: {str(e)}",
            )

    # Execute replay
    engine = StateReplayEngine()
    result = engine.replay_events(
        events=events,
        artifact_type=artifact_type,
        artifact_id=request.artifact_id,
        expected_final_state=request.expected_state,
        expected_hash=request.expected_hash,
    )

    return ReplayResponse(
        is_deterministic=result.is_deterministic,
        computed_state=result.computed_state,
        expected_state=result.expected_state,
        state_hash=result.state_hash,
        hashes_match=result.hashes_match,
        events_processed=result.events_processed,
        transitions_applied=result.transitions_applied,
        validation_errors=result.validation_errors,
        replayed_at=result.replayed_at,
        duration_ms=result.duration_ms,
    )


# =============================================================================
# WRITE ENDPOINTS — EXPLICITLY FORBIDDEN
# =============================================================================


@router.post("/shipment/{shipment_id}")
@router.put("/shipment/{shipment_id}")
@router.patch("/shipment/{shipment_id}")
@router.delete("/shipment/{shipment_id}")
async def write_shipment_forbidden(shipment_id: str) -> None:
    """Write operations are forbidden on state API."""
    raise HTTPException(
        status_code=403,
        detail="FORBIDDEN: State API is read-only. Atlas (GID-05) has no write authority.",
    )


@router.post("/settlement/{settlement_id}")
@router.put("/settlement/{settlement_id}")
@router.patch("/settlement/{settlement_id}")
@router.delete("/settlement/{settlement_id}")
async def write_settlement_forbidden(settlement_id: str) -> None:
    """Write operations are forbidden on state API."""
    raise HTTPException(
        status_code=403,
        detail="FORBIDDEN: State API is read-only. Atlas (GID-05) has no write authority.",
    )


@router.post("/pdo/{pdo_id}")
@router.put("/pdo/{pdo_id}")
@router.patch("/pdo/{pdo_id}")
@router.delete("/pdo/{pdo_id}")
async def write_pdo_forbidden(pdo_id: str) -> None:
    """Write operations are forbidden on state API."""
    raise HTTPException(
        status_code=403,
        detail="FORBIDDEN: State API is read-only. Atlas (GID-05) has no write authority.",
    )
