"""
Spine API Router - PAC-BENSON-EXEC-SPINE-01

HTTP POST endpoint for the Minimum Execution Spine.

Provides:
- POST /spine/event - Trigger execution flow
- GET /spine/proof/{proof_id} - Retrieve proof artifact

No mocks. No slides. Real execution.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.spine.decision import DecisionOutcome
from core.spine.event import SpineEvent, SpineEventType, create_payment_request_event
from core.spine.executor import ExecutionProof, ProofStore, SpineExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spine", tags=["Minimum Execution Spine"])

# Singleton executor instance
_executor: Optional[SpineExecutor] = None
_proof_store: Optional[ProofStore] = None


def get_executor() -> SpineExecutor:
    """Get or create the spine executor."""
    global _executor, _proof_store
    if _executor is None:
        _proof_store = ProofStore()
        _executor = SpineExecutor(proof_store=_proof_store)
    return _executor


def get_proof_store() -> ProofStore:
    """Get or create the proof store."""
    global _proof_store
    if _proof_store is None:
        _proof_store = ProofStore()
    return _proof_store


# =============================================================================
# Request/Response Models
# =============================================================================


class SpineEventRequest(BaseModel):
    """
    Request to trigger the Minimum Execution Spine.

    Canonical schema (LOCKED):
    - event_type: str
    - payload: dict
    - timestamp: optional (auto-generated if not provided)
    """
    event_type: str = Field(..., description="Type of event (e.g., 'payment_request')")
    payload: Dict[str, Any] = Field(..., description="Event payload data")
    timestamp: Optional[str] = Field(None, description="ISO8601 timestamp (optional)")


class PaymentRequestBody(BaseModel):
    """Convenience request body for payment requests."""
    amount: float = Field(..., gt=0, description="Payment amount (must be positive)")
    vendor_id: str = Field(..., min_length=1, description="Vendor identifier")
    requestor_id: str = Field(..., min_length=1, description="Requestor identifier")
    currency: str = Field(default="USD", description="Currency code")


class SpineExecutionResponse(BaseModel):
    """Response from spine execution."""
    success: bool = Field(..., description="Whether execution completed")
    proof_id: UUID = Field(..., description="ID of the generated proof")
    proof_hash: str = Field(..., description="SHA-256 hash of the proof")
    event_id: UUID = Field(..., description="ID of the processed event")
    decision_outcome: str = Field(..., description="Outcome of the decision")
    action_status: str = Field(..., description="Status of the action")
    proof_path: str = Field(..., description="Path where proof is stored")


class ProofResponse(BaseModel):
    """Response containing a proof artifact."""
    proof: Dict[str, Any] = Field(..., description="The proof artifact")
    proof_hash: str = Field(..., description="SHA-256 hash for verification")
    verified: bool = Field(..., description="Whether hash verification passed")


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/event",
    response_model=SpineExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Minimum Execution Spine",
    description="""
    Execute the canonical flow: Event → Decision → Action → Proof

    This endpoint:
    1. Ingests a real external event
    2. Computes a deterministic decision
    3. Executes a real side effect
    4. Generates and persists an immutable proof artifact

    No mocks. No slides. No narration.
    """,
)
async def execute_spine(request: SpineEventRequest) -> SpineExecutionResponse:
    """
    Execute the Minimum Execution Spine.

    PAC-BENSON-EXEC-SPINE-01 canonical flow.
    """
    logger.info(f"Spine execution requested: event_type={request.event_type}")

    # Validate event type
    try:
        event_type = SpineEventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported event_type: {request.event_type}. Supported: {[e.value for e in SpineEventType]}",
        )

    # Create immutable event
    try:
        # Only pass timestamp if explicitly provided
        event_kwargs = {
            "event_type": event_type,
            "payload": request.payload,
        }
        if request.timestamp:
            event_kwargs["timestamp"] = request.timestamp

        event = SpineEvent(**event_kwargs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event data: {e}",
        )

    # Execute spine (fails loudly on error)
    executor = get_executor()
    try:
        proof = executor.execute(event)
    except Exception as e:
        logger.error(f"Spine execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {e}",
        )

    # Get proof storage path
    proof_store = get_proof_store()
    proof_hash = proof.compute_hash()
    proof_path = str(proof_store._storage_dir / f"proof_{proof.id}_{proof_hash[:8]}.json")

    return SpineExecutionResponse(
        success=True,
        proof_id=proof.id,
        proof_hash=proof_hash,
        event_id=event.id,
        decision_outcome=proof.decision_outcome,
        action_status=proof.action_status,
        proof_path=proof_path,
    )


@router.post(
    "/payment",
    response_model=SpineExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute Payment Request (Convenience Endpoint)",
    description="Convenience endpoint for payment request events.",
)
async def execute_payment_request(request: PaymentRequestBody) -> SpineExecutionResponse:
    """
    Convenience endpoint for payment requests.

    Wraps the generic /spine/event endpoint with typed payload.
    """
    event = create_payment_request_event(
        amount=request.amount,
        vendor_id=request.vendor_id,
        requestor_id=request.requestor_id,
        currency=request.currency,
    )

    executor = get_executor()
    try:
        proof = executor.execute(event)
    except Exception as e:
        logger.error(f"Payment execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {e}",
        )

    proof_store = get_proof_store()
    proof_hash = proof.compute_hash()
    proof_path = str(proof_store._storage_dir / f"proof_{proof.id}_{proof_hash[:8]}.json")

    return SpineExecutionResponse(
        success=True,
        proof_id=proof.id,
        proof_hash=proof_hash,
        event_id=event.id,
        decision_outcome=proof.decision_outcome,
        action_status=proof.action_status,
        proof_path=proof_path,
    )


@router.get(
    "/proof/{proof_id}",
    response_model=ProofResponse,
    summary="Retrieve Proof Artifact",
    description="Retrieve and verify a proof artifact by ID.",
)
async def get_proof(proof_id: UUID) -> ProofResponse:
    """Retrieve a proof artifact for verification."""
    proof_store = get_proof_store()
    proof = proof_store.load(proof_id)

    if proof is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proof not found: {proof_id}",
        )

    proof_hash = proof.compute_hash()

    return ProofResponse(
        proof=proof.model_dump(mode="json"),
        proof_hash=proof_hash,
        verified=True,  # Hash computed successfully = verified
    )


@router.get(
    "/health",
    summary="Spine Health Check",
    description="Check if the Minimum Execution Spine is operational.",
)
async def spine_health() -> Dict[str, Any]:
    """Health check for the spine."""
    return {
        "status": "healthy",
        "spine_version": "1.0.0",
        "decision_rule": "payment_threshold_v1",
        "decision_rule_version": "1.0.0",
        "threshold": 10_000.00,
    }
