import hashlib
import json
import logging
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, TypedDict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.security.signing import (
    canonical_json_bytes,
    now_utc_iso,
    sign_response_headers,
)

# Configure logging
logger = logging.getLogger(__name__)

# API versioning
router = APIRouter(prefix="/v1/proofpacks", tags=["ProofPacks v1"])

# Configuration
RUNTIME_DIR = os.getenv("PROOFPACK_RUNTIME_DIR", "proofpacks/runtime")
MAX_EVENTS_PER_PACK = int(os.getenv("MAX_EVENTS_PER_PACK", "100"))
MAX_EVENT_DETAIL_DEPTH = int(os.getenv("MAX_EVENT_DETAIL_DEPTH", "10"))

# Ensure runtime directory exists
os.makedirs(RUNTIME_DIR, exist_ok=True)


# ---------- TYPE DEFINITIONS ----------
class NormalizedEvent(TypedDict):
    """Type definition for normalized event structure."""
    event_type: str
    timestamp: str
    details: Dict


class ProofPackManifest(TypedDict):
    """Type definition for proof pack manifest."""
    shipment_id: str
    events: List[NormalizedEvent]
    risk_score: Optional[float]
    policy_version: str
    generated_at: str


# ---------- MODELS ----------
class ProofEvent(BaseModel):
    """Proof event with timestamp and optional details."""

    event_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[a-zA-Z0-9_\-\.]+$',
        description="Event type identifier (alphanumeric, underscore, hyphen, dot)"
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp"
    )
    details: Optional[Dict] = Field(
        default_factory=dict,
        description="Optional event metadata"
    )

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        """Validate timestamp is ISO 8601 format."""
        from src.security.signing import parse_timestamp
        try:
            parse_timestamp(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {e}")

    @field_validator('details')
    @classmethod
    def validate_details_depth(cls, v):
        """Validate details dict doesn't exceed max depth."""
        if v is None:
            return {}

        def get_depth(d, current_depth=0):
            if not isinstance(d, dict) or not d:
                return current_depth
            return max(get_depth(v, current_depth + 1) for v in d.values())

        depth = get_depth(v)
        if depth > MAX_EVENT_DETAIL_DEPTH:
            raise ValueError(f"Event details exceed max depth of {MAX_EVENT_DETAIL_DEPTH}")
        return v


class ProofPackRequest(BaseModel):
    """Request model for creating a proof pack."""

    shipment_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[a-zA-Z0-9\-_]+$',
        description="Shipment identifier (alphanumeric, hyphen, underscore)"
    )
    events: List[ProofEvent] = Field(
        ...,
        min_length=1,
        max_length=MAX_EVENTS_PER_PACK,
        description=f"List of proof events (max {MAX_EVENTS_PER_PACK})"
    )
    risk_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Risk score (0-100)"
    )
    policy_version: str = Field(
        "1.0",
        pattern=r'^\d+\.\d+$',
        description="Policy version (e.g., 1.0)"
    )


class ProofPackResponse(BaseModel):
    """Response model for proof pack operations."""
    pack_id: str
    shipment_id: str
    generated_at: str
    manifest_hash: str
    status: str
    message: str


# ---------- HELPERS ----------
def validate_pack_id(pack_id: str) -> str:
    """
    Validate pack_id is a valid UUID to prevent path traversal.

    Args:
        pack_id: UUID string to validate

    Returns:
        Validated pack_id

    Raises:
        HTTPException: If pack_id is invalid
    """
    # UUID v4 format: 8-4-4-4-12 hex characters
    if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', pack_id):
        logger.warning(f"Invalid pack_id format: {pack_id}")
        raise HTTPException(status_code=400, detail="Invalid pack_id format (must be UUID)")
    return pack_id


def normalize_events(events: List[ProofEvent]) -> List[NormalizedEvent]:
    """
    Normalize events to consistent format.

    Args:
        events: List of ProofEvent objects

    Returns:
        List of normalized event dictionaries
    """
    normalized = []
    for event in events:
        normalized.append({
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "details": event.details or {}
        })
    return normalized


def compute_manifest_hash(manifest_data: ProofPackManifest) -> str:
    """
    Compute SHA-256 hash of manifest.

    Args:
        manifest_data: Manifest dictionary

    Returns:
        Hex-encoded SHA-256 hash
    """
    manifest_bytes = canonical_json_bytes(manifest_data)
    return hashlib.sha256(manifest_bytes).hexdigest()


def write_manifest_atomic(pack_id: str, manifest_data: ProofPackManifest) -> Path:
    """
    Write manifest to disk atomically to prevent race conditions.

    Args:
        pack_id: UUID of the proof pack
        manifest_data: Manifest data to write

    Returns:
        Path to written file

    Raises:
        IOError: If write fails
    """
    final_path = Path(RUNTIME_DIR) / f"{pack_id}.json"

    # Write to temporary file first
    temp_fd, temp_path = tempfile.mkstemp(
        dir=RUNTIME_DIR,
        suffix='.json',
        prefix='.tmp_'
    )

    try:
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(manifest_data, f, indent=2, sort_keys=True)

        # Atomic rename (POSIX systems)
        Path(temp_path).replace(final_path)
        logger.debug(f"Manifest written atomically: {final_path}")
        return final_path

    except Exception as e:
        # Clean up temp file on error
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
        logger.error(f"Failed to write manifest: {e}", exc_info=True)
        raise IOError(f"Failed to write manifest: {e}")


def read_manifest(pack_id: str) -> ProofPackManifest:
    """
    Read manifest from disk.

    Args:
        pack_id: UUID of the proof pack

    Returns:
        Manifest data

    Raises:
        HTTPException: If pack not found or read fails
    """
    pack_id = validate_pack_id(pack_id)
    file_path = Path(RUNTIME_DIR) / f"{pack_id}.json"

    # Ensure path is within runtime directory (extra safety)
    if not file_path.resolve().is_relative_to(Path(RUNTIME_DIR).resolve()):
        logger.error(f"Path traversal attempt detected: {pack_id}")
        raise HTTPException(status_code=400, detail="Invalid pack_id")

    if not file_path.exists():
        logger.info(f"ProofPack not found: {pack_id}")
        raise HTTPException(status_code=404, detail="ProofPack not found")

    try:
        with open(file_path, 'r') as f:
            manifest_data = json.load(f)
        return manifest_data
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read manifest {pack_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read ProofPack")


# ---------- ENDPOINTS ----------
@router.post("/run", response_model=ProofPackResponse)
async def run_proofpack(request: Request, payload: ProofPackRequest):
    """
    Create a new proof pack for a shipment.

    This endpoint:
    1. Validates the request
    2. Generates a unique pack ID
    3. Creates a manifest with events and metadata
    4. Computes a cryptographic hash of the manifest
    5. Stores the pack atomically
    6. Returns a signed response

    Rate limit: Configured per environment
    """
    start_time = time.time()

    try:
        pack_id = str(uuid.uuid4())
        generated_at = now_utc_iso()

        logger.info(
            f"Creating ProofPack for shipment {payload.shipment_id}, "
            f"pack_id={pack_id}, events={len(payload.events)}"
        )

        # Build manifest
        manifest_data: ProofPackManifest = {
            "shipment_id": payload.shipment_id,
            "events": normalize_events(payload.events),
            "risk_score": payload.risk_score,
            "policy_version": payload.policy_version,
            "generated_at": generated_at,
        }

        # Compute hash
        manifest_hash = compute_manifest_hash(manifest_data)

        # Write atomically
        write_manifest_atomic(pack_id, manifest_data)

        # Build response envelope
        envelope = {
            "pack_id": pack_id,
            "shipment_id": payload.shipment_id,
            "generated_at": generated_at,
            "manifest_hash": manifest_hash,
            "status": "SUCCESS",
            "message": f"ProofPack {pack_id} created successfully.",
        }

        # Sign response
        body_bytes = canonical_json_bytes(envelope)
        resp = JSONResponse(content=envelope, status_code=201)
        sign_response_headers(resp, body_bytes)

        duration = time.time() - start_time
        logger.info(
            f"ProofPack {pack_id} created successfully in {duration:.3f}s, "
            f"hash={manifest_hash[:16]}..."
        )

        return resp

    except HTTPException:
        raise
    except IOError as e:
        logger.error(f"Storage error creating ProofPack: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Storage error")
    except Exception as e:
        logger.error(f"Unexpected error creating ProofPack: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{pack_id}", response_model=ProofPackResponse)
async def get_proofpack(pack_id: str):
    """
    Retrieve an existing proof pack by ID.

    Returns the proof pack envelope with manifest hash.
    The full manifest is stored but not returned in the response for efficiency.

    Args:
        pack_id: UUID of the proof pack

    Returns:
        Signed proof pack envelope
    """
    start_time = time.time()

    try:
        logger.info(f"Retrieving ProofPack: {pack_id}")

        # Read and validate
        manifest_data = read_manifest(pack_id)

        # Recompute hash for verification
        manifest_hash = compute_manifest_hash(manifest_data)

        # Build response envelope
        envelope = {
            "pack_id": pack_id,
            "shipment_id": manifest_data["shipment_id"],
            "generated_at": manifest_data["generated_at"],
            "manifest_hash": manifest_hash,
            "status": "SUCCESS",
            "message": f"ProofPack {pack_id} retrieved successfully.",
        }

        # Sign response
        body_bytes = canonical_json_bytes(envelope)
        resp = JSONResponse(content=envelope)
        sign_response_headers(resp, body_bytes)

        duration = time.time() - start_time
        logger.info(
            f"ProofPack {pack_id} retrieved in {duration:.3f}s, "
            f"hash={manifest_hash[:16]}..."
        )

        return resp

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving ProofPack {pack_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
