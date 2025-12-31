"""
api/ingress.py - HTTP Ingress Endpoint for Execution Spine
PAC-CODY-EXEC-SPINE-01

HTTP POST endpoint: /events/ingest
- Accepts event payload
- Validates schema
- Executes Event → Decision → Action → Proof loop
- Returns proof_id + proof_hash

FLOW:
1. Validate incoming event schema
2. Create IngestEvent
3. Pass to decision function
4. Execute action handler
5. Build proof artifact
6. Hash proof deterministically
7. Persist proof
8. Return proof_id + hash in response
"""

from __future__ import annotations

from typing import Optional

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.actions import ActionStatus, execute_action
from core.decisions import decide
from core.events import IngestEvent, IngestEventRequest, create_event
from core.spine_proof import build_proof, persist_proof

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


class IngestResponse(BaseModel):
    """Response schema for POST /events/ingest."""
    proof_id: str = Field(..., description="UUID of the proof artifact")
    proof_hash: str = Field(..., description="SHA-256 hash of the proof")
    event_id: str = Field(..., description="UUID of the ingested event")
    decision_outcome: str = Field(..., description="Decision made on the event")
    action_status: str = Field(..., description="Status of the action execution")


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    event_id: Optional[str] = Field(None, description="Event ID if available")


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid event payload"},
        500: {"model": ErrorResponse, "description": "Internal processing error"},
    },
    summary="Ingest event and execute decision loop",
    description="Accepts an event, makes a decision, executes an action, and returns a proof artifact.",
)
async def ingest_event(request: IngestEventRequest) -> IngestResponse:
    """
    Ingest event and execute the canonical Event → Decision → Action → Proof loop.

    Steps:
    1. Validate minimal event schema (done by Pydantic)
    2. Create IngestEvent with generated event_id and timestamp
    3. Pass to decision function
    4. Execute action handler
    5. Build proof artifact
    6. Hash proof deterministically
    7. Persist proof
    8. Return proof_id + hash in response
    """
    event: IngestEvent | None = None

    try:
        # Step 2: Create event with generated ID and timestamp
        logger.info(
            "ingest: received event",
            extra={"event_type": request.event_type}
        )
        event = create_event(
            event_type=request.event_type,
            payload=request.payload,
        )
        event_id_str = str(event.event_id)

        logger.info(
            "ingest: event created",
            extra={"event_id": event_id_str, "event_type": event.event_type}
        )

        # Step 3: Pass to canonical decision function
        # Step 3: Pass to canonical decision function
        decision = decide(event.event_type, event.payload)
        logger.info(
            "ingest: decision made",
            extra={
                "event_id": event_id_str,
                "decision": decision.outcome.value,
                "rule": decision.rule_id,
            }
        )

        # Step 4: Execute action handler
        action_result = execute_action(decision, event.payload, event_id_str)
        logger.info(
            "ingest: action executed",
            extra={
                "event_id": event_id_str,
                "action_type": action_result.action_type,
                "action_status": action_result.status.value,
            }
        )

        # Check for action failure
        if action_result.status == ActionStatus.FAILURE:
            logger.error(
                "ingest: action failed",
                extra={
                    "event_id": event_id_str,
                    "error": action_result.error,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "action_failed",
                    "detail": action_result.error or "Action execution failed",
                    "event_id": event_id_str,
                },
            )

        # Step 5-6: Build proof artifact (hash computed in build_proof)
        proof = build_proof(event, decision, action_result)
        logger.info(
            "ingest: proof built",
            extra={
                "event_id": event_id_str,
                "proof_id": str(proof.proof_id),
                "proof_hash": proof.proof_hash,
            }
        )

        # Step 7: Persist proof
        proof_path = persist_proof(proof)
        logger.info(
            "ingest: proof persisted",
            extra={
                "event_id": event_id_str,
                "proof_id": str(proof.proof_id),
                "proof_path": proof_path,
            }
        )

        # Step 8: Return response
        return IngestResponse(
            proof_id=str(proof.proof_id),
            proof_hash=proof.proof_hash,
            event_id=event_id_str,
            decision_outcome=decision.outcome.value,
            action_status=action_result.status.value,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        # Validation errors
        event_id_str = str(event.event_id) if event else None
        logger.warning(
            "ingest: validation error",
            extra={"event_id": event_id_str, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "detail": str(e),
                "event_id": event_id_str,
            },
        ) from e
    except Exception as e:
        # Unexpected errors
        event_id_str = str(event.event_id) if event else None
        logger.exception(
            "ingest: unexpected error",
            extra={"event_id": event_id_str, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "detail": str(e),
                "event_id": event_id_str,
            },
        ) from e
