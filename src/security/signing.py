import base64
import hmac
import hashlib
import os
import datetime
import json
import logging
from typing import Tuple
from fastapi import Header, HTTPException, Response

logger = logging.getLogger(__name__)

# Secret + clock skew policy
_secret_str = os.getenv("SIGNING_SECRET")
if not _secret_str:
    if os.getenv("APP_ENV", "").lower() == "dev":
        logger.warning("SIGNING_SECRET not set, using dev-secret. DO NOT USE IN PRODUCTION!")
        _secret_str = "dev-secret"
    else:
        raise RuntimeError(
            "SIGNING_SECRET environment variable must be set in production. "
            "Generate a secure secret with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
elif _secret_str in ["your_signing_secret_here_CHANGE_IN_PRODUCTION", "dev-secret"]:
    if os.getenv("APP_ENV", "").lower() != "dev":
        raise RuntimeError(
            "SIGNING_SECRET is set to a placeholder value. "
            "Generate a secure secret with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    logger.warning("Using placeholder SIGNING_SECRET. DO NOT USE IN PRODUCTION!")

SIGNING_SECRET = _secret_str.encode("utf-8")
ALLOWED_SKEW = datetime.timedelta(minutes=5)


def now_utc_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def canonical_json_bytes(obj) -> bytes:
    """
    Convert object to deterministic JSON bytes.

    Uses sorted keys and compact format for consistent hashing.
    """
    return json.dumps(
        obj,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False
    ).encode("utf-8")


def compute_sig(ts_iso: str, body: bytes) -> str:
    """
    Compute HMAC-SHA256 signature for timestamp + body.

    Args:
        ts_iso: ISO 8601 timestamp string
        body: Request/response body bytes

    Returns:
        Base64-encoded signature
    """
    msg = ts_iso.encode("utf-8") + b"\n" + body
    digest = hmac.new(SIGNING_SECRET, msg, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def sign_response_headers(
    response: Response,
    body_bytes: bytes,
    key_id: str = "proofpacks-v1"
) -> None:
    """
    Sign response by adding signature headers.

    Args:
        response: FastAPI Response object
        body_bytes: Canonical JSON body bytes
        key_id: Key identifier for signature verification
    """
    ts = now_utc_iso()
    sig = compute_sig(ts, body_bytes)
    response.headers["X-Signature"] = sig
    response.headers["X-Signature-Alg"] = "HMAC-SHA256"
    response.headers["X-Signature-KeyId"] = key_id
    response.headers["X-Signature-Timestamp"] = ts


def parse_timestamp(ts_str: str) -> datetime.datetime:
    """
    Parse ISO 8601 timestamp string to datetime.

    Handles various formats including 'Z' suffix.

    Args:
        ts_str: ISO 8601 timestamp string

    Returns:
        Timezone-aware datetime object

    Raises:
        ValueError: If timestamp format is invalid
    """
    # Handle 'Z' suffix (Zulu time = UTC)
    if ts_str.endswith('Z'):
        ts_str = ts_str[:-1] + '+00:00'

    try:
        ts = datetime.datetime.fromisoformat(ts_str)
    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {ts_str}") from e

    # Ensure timezone aware
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)

    return ts


def verify_headers(
    x_signature: str = Header(None, alias="X-Signature"),
    x_signature_timestamp: str = Header(None, alias="X-Signature-Timestamp")
) -> Tuple[str, str]:
    """
    Verify signature headers are present and timestamp is within allowed window.

    Note: This only validates headers exist and timestamp is recent.
    Call verify_request() to verify the signature against request body.

    Args:
        x_signature: HMAC signature from request header
        x_signature_timestamp: ISO timestamp from request header

    Returns:
        Tuple of (signature, timestamp)

    Raises:
        HTTPException: If headers missing or timestamp invalid/expired
    """
    if not x_signature or not x_signature_timestamp:
        logger.warning("Request missing signature headers")
        raise HTTPException(
            status_code=401,
            detail="Missing signature headers (X-Signature, X-Signature-Timestamp)"
        )

    try:
        ts = parse_timestamp(x_signature_timestamp)
    except ValueError as e:
        logger.warning(f"Invalid signature timestamp: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature timestamp format")

    now = datetime.datetime.now(datetime.timezone.utc)
    time_diff = abs(now - ts)

    if time_diff > ALLOWED_SKEW:
        logger.warning(
            f"Signature timestamp outside allowed window: {time_diff.total_seconds()}s "
            f"(max: {ALLOWED_SKEW.total_seconds()}s)"
        )
        raise HTTPException(
            status_code=401,
            detail=f"Signature timestamp outside allowed window ({ALLOWED_SKEW.total_seconds()}s)"
        )

    return x_signature, x_signature_timestamp


def verify_request(body: bytes, signature: str, timestamp: str) -> None:
    """
    Verify request body signature.

    Args:
        body: Raw request body bytes
        signature: Expected HMAC signature (base64)
        timestamp: ISO timestamp used in signature

    Raises:
        HTTPException: If signature verification fails
    """
    expected_sig = compute_sig(timestamp, body)

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_sig, signature):
        logger.warning("Signature verification failed")
        raise HTTPException(
            status_code=401,
            detail="Signature verification failed"
        )

    logger.debug("Signature verification successful")


__all__ = [
    "now_utc_iso",
    "canonical_json_bytes",
    "compute_sig",
    "sign_response_headers",
    "verify_headers",
    "verify_request",
    "parse_timestamp",
]
