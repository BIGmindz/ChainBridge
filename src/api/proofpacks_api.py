from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Union
import uuid, hashlib, json, os, datetime

from src.security.signing import (
    now_utc_iso,
    canonical_json_bytes,
    sign_response_headers,
)

router = APIRouter(prefix="/proofpacks", tags=["ProofPacks"])

RUNTIME_DIR = "proofpacks/runtime"

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
        norm.append({
            "event_type": e.event_type,
            "timestamp": str(ts),
            "details": e.details or {}
        })
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

        os.makedirs(RUNTIME_DIR, exist_ok=True)
        with open(os.path.join(RUNTIME_DIR, f"{pack_id}.json"), "w") as f:
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
    path = os.path.join(RUNTIME_DIR, f"{pack_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="ProofPack not found")

    with open(path, "r") as f:
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
