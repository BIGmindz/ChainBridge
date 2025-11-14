from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid, hashlib, json, os, datetime, logging
from pathlib import Path

from src.security.signing import (
    now_utc_iso,
    canonical_json_bytes,
    sign_response_headers,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proofpacks", tags=["ProofPacks"])

# Use pathlib for secure path handling
RUNTIME_DIR = Path("proofpacks/runtime").resolve()

# ---------- MODELS ----------
class ProofEvent(BaseModel):
    event_type: str
    timestamp: datetime.datetime | str
    details: Optional[dict] = None

class ProofPackRequest(BaseModel):
    shipment_id: str
    events: List[ProofEvent]
    risk_score: Optional[float] = None
    policy_version: Optional[str] = "1.0"

# ---------- HELPERS ----------
def _normalize_events(events: List[ProofEvent]) -> List[dict]:
    norm = []
    for e in events:
        ts = e.timestamp
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()
        norm.append({
            "event_type": e.event_type,
            "timestamp": str(ts),
            "details": e.details or {}
        })
    return norm

def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _validate_and_get_pack_path(pack_id: str) -> Path:
    """
    Validates pack_id and returns a secure resolved path.
    
    Security measures:
    1. Validates pack_id is a valid UUID format to prevent injection
    2. Uses pathlib.Path.resolve() to get absolute path
    3. Uses .relative_to() to ensure path stays within RUNTIME_DIR
    4. Prevents path traversal attacks (e.g., "../../../etc/passwd")
    
    Args:
        pack_id: UUID string for the proof pack
        
    Returns:
        Secure resolved Path object
        
    Raises:
        HTTPException: If pack_id is invalid or path is unsafe
    """
    # Validate UUID format - this prevents path traversal attempts
    try:
        uuid.UUID(pack_id)
    except ValueError:
        logger.error(f"Invalid pack_id format: {pack_id}")
        raise HTTPException(
            status_code=400,
            detail="Invalid pack_id: must be a valid UUID"
        )
    
    # Construct and resolve the full path
    pack_path = (RUNTIME_DIR / f"{pack_id}.json").resolve()
    
    # Ensure the resolved path is within RUNTIME_DIR (prevents path traversal)
    try:
        pack_path.relative_to(RUNTIME_DIR)
    except ValueError:
        logger.error(f"Path traversal attempt detected: {pack_id}")
        raise HTTPException(
            status_code=400,
            detail="Invalid pack_id: path traversal not allowed"
        )
    
    return pack_path

# ---------- ENDPOINTS ----------
@router.post("/run")
async def run_proofpack(payload: ProofPackRequest):
    try:
        pack_id = str(uuid.uuid4())
        generated_at = now_utc_iso()

        manifest_data = {
            "shipment_id": payload.shipment_id,
            "events": _normalize_events(payload.events),
            "risk_score": payload.risk_score,
            "policy_version": payload.policy_version,
            "generated_at": generated_at,
        }

        manifest_json = canonical_json_bytes(manifest_data)
        manifest_hash = _sha256_hex(manifest_json)

        # Ensure runtime directory exists
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        
        # Use secure path validation
        pack_path = _validate_and_get_pack_path(pack_id)
        
        # Write manifest to file
        with open(pack_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

        envelope = {
            "pack_id": pack_id,
            "shipment_id": payload.shipment_id,
            "generated_at": generated_at,
            "manifest_hash": manifest_hash,
            "status": "SUCCESS",
            "message": f"ProofPack {pack_id} created successfully.",
        }

        body_bytes = canonical_json_bytes(envelope)
        resp = JSONResponse(envelope)
        sign_response_headers(resp, body_bytes)
        return resp

    except HTTPException:
        # Re-raise HTTP exceptions from validation
        raise
    except Exception as e:
        logger.error(f"Error creating ProofPack: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{pack_id}")
async def get_proofpack(pack_id: str):
    # Validate pack_id and get secure path
    pack_path = _validate_and_get_pack_path(pack_id)
    
    if not pack_path.exists():
        logger.warning(f"ProofPack not found: {pack_id}")
        raise HTTPException(status_code=404, detail="ProofPack not found")

    try:
        with open(pack_path, "r") as f:
            manifest_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading ProofPack {pack_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading ProofPack")

    manifest_hash = _sha256_hex(canonical_json_bytes(manifest_data))

    envelope = {
        "pack_id": pack_id,
        "shipment_id": manifest_data["shipment_id"],
        "generated_at": manifest_data["generated_at"],
        "manifest_hash": manifest_hash,
        "status": "SUCCESS",
        "message": f"ProofPack {pack_id} loaded.",
    }

    body_bytes = canonical_json_bytes(envelope)
    resp = JSONResponse(envelope)
    sign_response_headers(resp, body_bytes)
    return resp
