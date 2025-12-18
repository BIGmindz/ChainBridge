"""
PDO API Routes — Hardened Append-Only Endpoints

PAC-CODY-PDO-HARDEN-01: PDO Write-Path Integrity & Immutability

API Hardening:
- POST /pdo → Create (append) only
- GET /pdo/{id} → Read with integrity check
- GET /pdo → List with optional verification
- PUT/PATCH/DELETE → EXPLICITLY REJECTED with 405 Method Not Allowed

NO update or delete endpoints exist. Any attempt to call them
returns an explicit error with clear messaging.

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from core.occ.schemas.pdo import PDOCreate, PDOListResponse, PDOOutcome, PDORecord, PDOSourceSystem, PDOTamperDetectedError
from core.occ.store.pdo_store import PDOStore, get_pdo_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdo", tags=["PDO - Proof Decision Objects"])


def _get_store() -> PDOStore:
    """Get the PDO store instance."""
    return get_pdo_store()


# =============================================================================
# CREATE (APPEND-ONLY) — THE ONLY WRITE OPERATION PERMITTED
# =============================================================================


@router.post(
    "",
    response_model=PDORecord,
    status_code=201,
    summary="Create PDO (Append-Only)",
    description="""
Create a new immutable PDO record.

This is the ONLY way to write to the PDO store. The system will:
1. Generate a unique pdo_id
2. Set recorded_at to current UTC time
3. Compute and seal a SHA-256 hash
4. Return the immutable PDORecord

**IMMUTABILITY GUARANTEE**: Once created, this PDO cannot be modified or deleted.
    """,
)
async def create_pdo(pdo_create: PDOCreate) -> PDORecord:
    """Create a new immutable PDO record."""
    try:
        store = _get_store()
        record = store.create(pdo_create)
        logger.info(f"PDO created: {record.pdo_id}")
        return record
    except Exception as e:
        logger.error(f"Failed to create PDO: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create PDO: {str(e)}")


# =============================================================================
# READ OPERATIONS (ALLOWED)
# =============================================================================


@router.get(
    "/{pdo_id}",
    response_model=PDORecord,
    summary="Get PDO by ID",
    description="""
Retrieve a PDO by its unique identifier.

By default, performs integrity verification (hash check).
Set `verify=false` to skip verification (not recommended).
    """,
)
async def get_pdo(
    pdo_id: UUID,
    verify: bool = Query(True, description="Verify hash integrity on read"),
) -> PDORecord:
    """Get a PDO by ID with optional integrity verification."""
    try:
        store = _get_store()
        record = store.get(pdo_id, verify_integrity=verify)

        if record is None:
            raise HTTPException(status_code=404, detail=f"PDO {pdo_id} not found")

        return record
    except PDOTamperDetectedError as e:
        logger.error(f"TAMPER DETECTED: {e}")
        raise HTTPException(
            status_code=409,
            detail={
                "error": "PDO_TAMPER_DETECTED",
                "message": str(e),
                "pdo_id": str(e.pdo_id),
                "expected_hash": e.expected_hash,
                "actual_hash": e.actual_hash,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDO {pdo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get PDO: {str(e)}")


@router.get(
    "",
    response_model=PDOListResponse,
    summary="List PDOs",
    description="List PDOs with optional filtering and pagination.",
)
async def list_pdos(
    source_system: Optional[PDOSourceSystem] = Query(None, description="Filter by source system"),
    outcome: Optional[PDOOutcome] = Query(None, description="Filter by outcome"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    actor: Optional[str] = Query(None, description="Filter by actor"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    verify: bool = Query(False, description="Verify hash integrity for each record"),
) -> PDOListResponse:
    """List PDOs with optional filtering."""
    try:
        store = _get_store()

        # Get total count before pagination
        all_records = store.list(
            source_system=source_system,
            outcome=outcome,
            correlation_id=correlation_id,
            actor=actor,
            verify_integrity=verify,
        )
        total = len(all_records)

        # Apply pagination
        records = store.list(
            source_system=source_system,
            outcome=outcome,
            correlation_id=correlation_id,
            actor=actor,
            limit=limit,
            offset=offset,
            verify_integrity=verify,
        )

        return PDOListResponse(
            items=records,
            count=len(records),
            total=total,
            limit=limit,
            offset=offset,
        )
    except PDOTamperDetectedError as e:
        logger.error(f"TAMPER DETECTED during list: {e}")
        raise HTTPException(
            status_code=409,
            detail={
                "error": "PDO_TAMPER_DETECTED",
                "message": str(e),
                "pdo_id": str(e.pdo_id),
            },
        )
    except Exception as e:
        logger.error(f"Failed to list PDOs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list PDOs: {str(e)}")


@router.get(
    "/{pdo_id}/chain",
    response_model=List[PDORecord],
    summary="Get PDO Chain",
    description="Get the full chain of PDOs linked by previous_pdo_id, from oldest to newest.",
)
async def get_pdo_chain(
    pdo_id: UUID,
    verify: bool = Query(True, description="Verify hash integrity for each record"),
) -> List[PDORecord]:
    """Get the full chain of PDOs linked by previous_pdo_id."""
    try:
        store = _get_store()
        chain = store.get_chain(pdo_id, verify_integrity=verify)

        if not chain:
            raise HTTPException(status_code=404, detail=f"PDO chain not found for {pdo_id}")

        return chain
    except PDOTamperDetectedError as e:
        logger.error(f"TAMPER DETECTED in chain: {e}")
        raise HTTPException(
            status_code=409,
            detail={
                "error": "PDO_TAMPER_DETECTED",
                "message": str(e),
                "pdo_id": str(e.pdo_id),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDO chain: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get PDO chain: {str(e)}")


@router.get(
    "/{pdo_id}/verify",
    summary="Verify PDO Integrity",
    description="Verify the hash integrity of a specific PDO.",
)
async def verify_pdo(pdo_id: UUID) -> dict:
    """Verify the hash integrity of a specific PDO."""
    try:
        store = _get_store()
        record = store.get(pdo_id, verify_integrity=False)

        if record is None:
            raise HTTPException(status_code=404, detail=f"PDO {pdo_id} not found")

        is_valid = record.verify_hash()
        computed_hash = record.compute_hash()

        return {
            "pdo_id": str(pdo_id),
            "is_valid": is_valid,
            "stored_hash": record.hash,
            "computed_hash": computed_hash,
            "hash_algorithm": record.hash_algorithm,
            "recorded_at": record.recorded_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify PDO {pdo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify PDO: {str(e)}")


# =============================================================================
# BLOCKED OPERATIONS — EXPLICIT 405 REJECTIONS
# =============================================================================


@router.put(
    "/{pdo_id}",
    status_code=405,
    summary="BLOCKED: Update Not Allowed",
    description="PDOs are immutable. Updates are not permitted.",
    responses={
        405: {
            "description": "Method Not Allowed - PDOs cannot be updated",
            "content": {
                "application/json": {
                    "example": {
                        "error": "PDO_IMMUTABILITY_VIOLATION",
                        "message": "PDOs cannot be updated. PDOs are append-only, immutable records.",
                        "pdo_id": "123e4567-e89b-12d3-a456-426614174000",
                    }
                }
            },
        }
    },
)
async def update_pdo_blocked(pdo_id: UUID, request: Request) -> JSONResponse:
    """BLOCKED: PDOs cannot be updated."""
    logger.warning(f"BLOCKED: Attempted PUT on PDO {pdo_id}")
    return JSONResponse(
        status_code=405,
        content={
            "error": "PDO_IMMUTABILITY_VIOLATION",
            "message": "PDOs cannot be updated. PDOs are append-only, immutable records.",
            "pdo_id": str(pdo_id),
        },
        headers={"Allow": "GET"},
    )


@router.patch(
    "/{pdo_id}",
    status_code=405,
    summary="BLOCKED: Partial Update Not Allowed",
    description="PDOs are immutable. Partial updates are not permitted.",
    responses={
        405: {
            "description": "Method Not Allowed - PDOs cannot be updated",
        }
    },
)
async def patch_pdo_blocked(pdo_id: UUID, request: Request) -> JSONResponse:
    """BLOCKED: PDOs cannot be partially updated."""
    logger.warning(f"BLOCKED: Attempted PATCH on PDO {pdo_id}")
    return JSONResponse(
        status_code=405,
        content={
            "error": "PDO_IMMUTABILITY_VIOLATION",
            "message": "PDOs cannot be updated. PDOs are append-only, immutable records.",
            "pdo_id": str(pdo_id),
        },
        headers={"Allow": "GET"},
    )


@router.delete(
    "/{pdo_id}",
    status_code=405,
    summary="BLOCKED: Delete Not Allowed",
    description="PDOs are immutable. Deletion is not permitted.",
    responses={
        405: {
            "description": "Method Not Allowed - PDOs cannot be deleted",
            "content": {
                "application/json": {
                    "example": {
                        "error": "PDO_IMMUTABILITY_VIOLATION",
                        "message": "PDOs cannot be deleted. PDOs are append-only, immutable records.",
                        "pdo_id": "123e4567-e89b-12d3-a456-426614174000",
                    }
                }
            },
        }
    },
)
async def delete_pdo_blocked(pdo_id: UUID) -> JSONResponse:
    """BLOCKED: PDOs cannot be deleted."""
    logger.warning(f"BLOCKED: Attempted DELETE on PDO {pdo_id}")
    return JSONResponse(
        status_code=405,
        content={
            "error": "PDO_IMMUTABILITY_VIOLATION",
            "message": "PDOs cannot be deleted. PDOs are append-only, immutable records.",
            "pdo_id": str(pdo_id),
        },
        headers={"Allow": "GET"},
    )


# =============================================================================
# ADDITIONAL BLOCKED OPERATIONS
# =============================================================================


@router.post(
    "/{pdo_id}/overwrite",
    status_code=405,
    summary="BLOCKED: Overwrite Not Allowed",
    description="PDOs cannot be overwritten.",
)
async def overwrite_pdo_blocked(pdo_id: UUID) -> JSONResponse:
    """BLOCKED: PDOs cannot be overwritten."""
    logger.warning(f"BLOCKED: Attempted overwrite on PDO {pdo_id}")
    return JSONResponse(
        status_code=405,
        content={
            "error": "PDO_IMMUTABILITY_VIOLATION",
            "message": "PDOs cannot be overwritten. Create a new PDO with previous_pdo_id linkage instead.",
            "pdo_id": str(pdo_id),
        },
    )


@router.post(
    "/{pdo_id}/rehash",
    status_code=405,
    summary="BLOCKED: Rehash Not Allowed",
    description="PDO hashes cannot be recomputed or modified.",
)
async def rehash_pdo_blocked(pdo_id: UUID) -> JSONResponse:
    """BLOCKED: PDO hashes cannot be modified."""
    logger.warning(f"BLOCKED: Attempted rehash on PDO {pdo_id}")
    return JSONResponse(
        status_code=405,
        content={
            "error": "PDO_IMMUTABILITY_VIOLATION",
            "message": "PDO hashes cannot be recomputed. Hash is sealed at write time.",
            "pdo_id": str(pdo_id),
        },
    )
