import datetime
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.security.signing import canonical_json_bytes, now_utc_iso, sign_response_headers

router = APIRouter(prefix="/proofpacks", tags=["ProofPacks"])

# Resolved base directory prevents path traversal
_RUNTIME_BASE = Path("proofpacks/runtime").resolve()

# UUID pattern for pack_id validation (defense in depth)
_UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def _safe_pack_path(pack_id: str) -> Path:
    """
    Securely resolve a pack_id to a file path within RUNTIME_BASE.

    Prevents path traversal by:
    1. Validating pack_id is a valid UUID format
    2. Resolving the final path and verifying it stays under base
    """
    if not _UUID_PATTERN.match(pack_id):
        raise ValueError(f"Invalid pack_id format: {pack_id}")

    # Construct candidate path
    candidate = (_RUNTIME_BASE / f"{pack_id}.json").resolve()

    # Verify candidate is under the base directory
    try:
        candidate.relative_to(_RUNTIME_BASE)
    except ValueError:
        raise ValueError(f"Path traversal detected for pack_id: {pack_id}")

    return candidate


# ---------- MODELS ----------
class ProofEvent(BaseModel):
    event_type: str
    timestamp: Union[datetime.datetime, str]
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
        norm.append({"event_type": e.event_type, "timestamp": str(ts), "details": e.details or {}})
    return norm


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


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

        # Use secure path resolution
        _RUNTIME_BASE.mkdir(parents=True, exist_ok=True)
        safe_path = _safe_pack_path(pack_id)
        with safe_path.open("w") as f:
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pack_id}")
async def get_proofpack(pack_id: str):
    # Secure path resolution with validation
    try:
        safe_path = _safe_pack_path(pack_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid pack_id format")

    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="ProofPack not found")

    with safe_path.open("r") as f:
        manifest_data = json.load(f)

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
