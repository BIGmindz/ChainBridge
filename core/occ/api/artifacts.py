"""
OCC Artifact CRUD API

Endpoints for managing artifacts in the Operations Control Center.
Mounted at /occ/artifacts

Includes ProofPack generation endpoint: GET /occ/artifacts/{id}/proofpack
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.occ.schemas.artifact import Artifact, ArtifactCreate, ArtifactStatus, ArtifactType, ArtifactUpdate
from core.occ.schemas.audit_event import AuditEvent
from core.occ.store.artifact_store import ArtifactStore, get_artifact_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/artifacts", tags=["OCC Artifacts"])


class ArtifactListResponse(BaseModel):
    """Response model for artifact list endpoint."""

    items: List[Artifact]
    count: int
    limit: Optional[int]
    offset: int


@router.post("", response_model=Artifact, status_code=201)
async def create_artifact(
    artifact_in: ArtifactCreate,
    store: ArtifactStore = Depends(get_artifact_store),
) -> Artifact:
    """
    Create a new artifact.

    The artifact ID and timestamps are generated server-side.
    """
    try:
        artifact = store.create(artifact_in)
        return artifact
    except Exception as e:
        logger.error(f"Failed to create artifact: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create artifact: {str(e)}")


@router.get("", response_model=ArtifactListResponse)
async def list_artifacts(
    artifact_type: Optional[ArtifactType] = Query(None, description="Filter by artifact type"),
    status: Optional[ArtifactStatus] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    store: ArtifactStore = Depends(get_artifact_store),
) -> ArtifactListResponse:
    """
    List artifacts with optional filtering and pagination.
    """
    items = store.list(
        artifact_type=artifact_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ArtifactListResponse(
        items=items,
        count=len(items),
        limit=limit,
        offset=offset,
    )


@router.get("/{artifact_id}", response_model=Artifact)
async def get_artifact(
    artifact_id: UUID,
    store: ArtifactStore = Depends(get_artifact_store),
) -> Artifact:
    """
    Get a specific artifact by ID.
    """
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")
    return artifact


@router.patch("/{artifact_id}", response_model=Artifact)
async def update_artifact(
    artifact_id: UUID,
    artifact_update: ArtifactUpdate,
    store: ArtifactStore = Depends(get_artifact_store),
) -> Artifact:
    """
    Update an artifact with partial data.

    Only fields provided in the request body will be updated.
    """
    artifact = store.update(artifact_id, artifact_update)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")
    return artifact


@router.delete("/{artifact_id}", status_code=204)
async def delete_artifact(
    artifact_id: UUID,
    store: ArtifactStore = Depends(get_artifact_store),
) -> None:
    """
    Delete an artifact by ID.
    """
    deleted = store.delete(artifact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")


# =============================================================================
# PROOFPACK - VERIFIABLE EVIDENCE BUNDLE
# =============================================================================


class ProofPackBundle(BaseModel):
    """
    Immutable ProofPack bundle for an artifact.

    Contains a snapshot of the artifact and its complete audit trail,
    with a SHA-256 hash for integrity verification.
    """

    proofpack_id: UUID = Field(..., description="Unique ProofPack identifier")
    artifact_id: UUID = Field(..., description="Source artifact ID")
    artifact: Dict[str, Any] = Field(..., description="Artifact snapshot (canonical)")
    audit_events: List[Dict[str, Any]] = Field(..., description="Complete audit trail")
    event_count: int = Field(..., description="Number of audit events")
    generated_at: datetime = Field(..., description="Generation timestamp (UTC)")
    generated_by: str = Field(..., description="Actor/system that generated this pack")
    hash: str = Field(..., description="SHA-256 hash of canonical content")
    hash_algorithm: str = Field(default="SHA-256", description="Hash algorithm used")
    version: str = Field(default="1.0", description="ProofPack schema version")


class ProofPackResponse(BaseModel):
    """API response wrapper for ProofPack."""

    proofpack: ProofPackBundle
    verification: Dict[str, Any] = Field(
        default_factory=dict,
        description="Hash verification metadata",
    )


def _compute_canonical_hash(artifact_dict: Dict[str, Any], events_dicts: List[Dict[str, Any]]) -> str:
    """
    Compute SHA-256 hash over canonical JSON representation.

    Deterministic output: same input always produces same hash.
    Uses sorted keys and no extra whitespace.
    """
    canonical_content = {
        "artifact": artifact_dict,
        "audit_events": events_dicts,
    }
    canonical_json = json.dumps(
        canonical_content,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _build_proofpack(
    artifact: Artifact,
    events: List[AuditEvent],
    generated_by: str = "system",
) -> ProofPackBundle:
    """
    Build a ProofPack bundle from an artifact and its events.

    This is a pure function with no side effects.
    """
    # Serialize to canonical dicts
    artifact_dict = artifact.model_dump(mode="json")
    events_dicts = [e.model_dump(mode="json") for e in events]

    # Compute deterministic hash
    content_hash = _compute_canonical_hash(artifact_dict, events_dicts)

    return ProofPackBundle(
        proofpack_id=uuid4(),
        artifact_id=artifact.id,
        artifact=artifact_dict,
        audit_events=events_dicts,
        event_count=len(events_dicts),
        generated_at=datetime.now(timezone.utc),
        generated_by=generated_by,
        hash=content_hash,
    )


@router.get("/{artifact_id}/proofpack", response_model=ProofPackResponse)
async def get_proofpack(
    artifact_id: UUID,
    generated_by: str = Query("system", description="Actor generating the ProofPack"),
    store: ArtifactStore = Depends(get_artifact_store),
) -> ProofPackResponse:
    """
    Generate a verifiable ProofPack for an artifact.

    The ProofPack bundles:
    - Artifact snapshot (read-only, no mutation)
    - Complete audit event timeline
    - SHA-256 hash over canonical JSON

    Properties:
    - READ-ONLY: No mutation of underlying artifacts/events
    - DETERMINISTIC: Same input produces same hash
    - APPEND-ONLY COMPATIBLE: Works with immutable event logs

    The hash is computed over canonical JSON (sorted keys, no whitespace)
    to ensure repeated calls with unchanged data produce identical hashes.
    """
    # Read artifact (no mutation)
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    # Read audit events (no mutation)
    events = store.get_events(artifact_id)

    # Build ProofPack (pure function, no side effects)
    proofpack = _build_proofpack(artifact, events, generated_by)

    logger.info(
        f"Generated ProofPack {proofpack.proofpack_id} for artifact {artifact_id} | "
        f"events={proofpack.event_count} | hash={proofpack.hash[:16]}..."
    )

    return ProofPackResponse(
        proofpack=proofpack,
        verification={
            "algorithm": "SHA-256",
            "canonical_format": "JSON (sorted keys, minimal whitespace)",
            "hash": proofpack.hash,
            "note": "Hash is stable across repeated calls if artifact and events are unchanged.",
        },
    )
