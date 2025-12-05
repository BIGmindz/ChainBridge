import base64
import hmac
import hashlib
import os
import datetime
import json
from fastapi import Header, HTTPException, Response

# Secret + clock skew policy
_raw_secret = os.getenv("SIGNING_SECRET")
if not _raw_secret or _raw_secret == "dev-secret":
    raise ValueError("SIGNING_SECRET environment variable must be set to a secure value")
SIGNING_SECRET = _raw_secret.encode("utf-8")
ALLOWED_SKEW = datetime.timedelta(minutes=5)


def now_utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def canonical_json_bytes(obj) -> bytes:
    # Deterministic JSON (no spaces, sorted keys)
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")


def compute_sig(ts_iso: str, body: bytes) -> str:
    msg = ts_iso.encode("utf-8") + b"\n" + body
    digest = hmac.new(SIGNING_SECRET, msg, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def sign_response_headers(response: Response, body_bytes: bytes, key_id: str = "proofpacks-v1") -> None:
    ts = now_utc_iso()
    sig = compute_sig(ts, body_bytes)
    response.headers["X-Signature"] = sig
    response.headers["X-Signature-Alg"] = "HMAC-SHA256"
    response.headers["X-Signature-KeyId"] = key_id
    response.headers["X-Signature-Timestamp"] = ts


def verify_headers(x_signature: str = Header(None), x_signature_timestamp: str = Header(None)):
    if not x_signature or not x_signature_timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")
    try:
        ts = datetime.datetime.fromisoformat(x_signature_timestamp.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Bad signature timestamp")
    now = datetime.datetime.now(datetime.timezone.utc)
    if abs(now - ts) > ALLOWED_SKEW:
        raise HTTPException(status_code=401, detail="Signature timestamp outside allowed window")
    return x_signature, x_signature_timestamp


__all__ = [
    "now_utc_iso",
    "canonical_json_bytes",
    "compute_sig",
    "sign_response_headers",
    "verify_headers",
]
