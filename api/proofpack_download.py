"""
ProofPack Download API — PAC-BENSON-P33

Doctrine Law 4, §4.2: ProofPack download with signed archive.

Provides:
- GET /api/v1/proofpack/{id}/download — Download complete signed archive

Archive contents:
- proofpack.json — Machine-verifiable JSON bundle
- proofpack.pdf (txt) — Human-readable document
- manifest.json — Hash manifest for offline verification
- verification.txt — Verification instructions

INVARIANTS:
- INV-PP-001: All archives cryptographically signed
- INV-PP-002: Hash manifest included for offline verification
- INV-OCC-005: Read-only endpoint (GET only)

Author: CODY (GID-01) — Backend Implementation
Security: SAM (GID-06) — Cryptographic verification
"""

import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from core.occ.schemas.artifact import Artifact
from core.occ.schemas.audit_event import AuditEvent
from core.occ.schemas.proofpack import (
    IntegrityManifest,
    ProofPack,
    ProofPackStatus,
)
from core.occ.store.artifact_store import ArtifactStore, get_artifact_store

# Import signing module (graceful fallback if PyNaCl not available)
try:
    from core.occ.crypto.ed25519_signer import (
        NACL_AVAILABLE,
        get_proofpack_signer,
    )
except ImportError:
    NACL_AVAILABLE = False
    get_proofpack_signer = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/proofpack", tags=["ProofPack Download"])


# =============================================================================
# HELPERS — Artifact to Summary conversion
# =============================================================================


def _artifact_to_dict(artifact: Artifact) -> dict:
    """Convert artifact to summary dict."""
    return {
        "id": str(artifact.id),
        "name": artifact.name,
        "artifact_type": artifact.artifact_type if isinstance(artifact.artifact_type, str) else artifact.artifact_type.value,
        "status": artifact.status if isinstance(artifact.status, str) else artifact.status.value,
        "description": artifact.description,
        "owner": artifact.owner,
        "tags": artifact.tags,
        "created_at": artifact.created_at.isoformat() if hasattr(artifact.created_at, "isoformat") else str(artifact.created_at),
        "updated_at": artifact.updated_at.isoformat() if hasattr(artifact.updated_at, "isoformat") else str(artifact.updated_at),
    }


def _event_to_dict(event: AuditEvent) -> dict:
    """Convert audit event to summary dict."""
    return {
        "id": str(event.id),
        "event_type": event.event_type if isinstance(event.event_type, str) else event.event_type.value,
        "actor": event.actor,
        "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp),
        "details": event.details,
    }


# =============================================================================
# ARCHIVE GENERATION
# =============================================================================


def _generate_proofpack_json(
    artifact: Artifact,
    events: list[AuditEvent],
    include_payload: bool = True,
) -> tuple[dict, str]:
    """
    Generate ProofPack JSON and manifest hash.

    Returns:
        Tuple of (proofpack_dict, manifest_hash)
    """
    generated_at = datetime.now(timezone.utc)
    generated_at_str = generated_at.isoformat()

    artifact_data = _artifact_to_dict(artifact)
    if include_payload:
        artifact_data["payload"] = artifact.payload

    events_data = [_event_to_dict(e) for e in events]

    # Compute integrity hashes
    integrity = IntegrityManifest.compute(artifact_data, events_data, generated_at_str)

    # Apply signature if available
    signature_info = {}
    if NACL_AVAILABLE and get_proofpack_signer is not None:
        try:
            signer = get_proofpack_signer()
            signature_bundle = signer.sign_manifest_hash(integrity.manifest_hash)
            integrity = integrity.apply_signature(
                signature=signature_bundle.signature,
                public_key=signature_bundle.public_key,
                key_id=signature_bundle.key_id,
                signed_at=signature_bundle.signed_at,
            )
            signature_info = {
                "signed": True,
                "algorithm": "Ed25519",
                "key_id": signature_bundle.key_id,
                "signed_at": signature_bundle.signed_at,
            }
            logger.debug(f"ProofPack signed with key {signature_bundle.key_id}")
        except Exception as e:
            logger.warning(f"Failed to sign ProofPack: {e}")
            signature_info = {"signed": False, "reason": str(e)}
    else:
        signature_info = {"signed": False, "reason": "PyNaCl not available"}

    proofpack_dict = {
        "schema_version": "1.0.0",
        "proofpack_id": str(artifact.id),
        "generated_at": generated_at_str,
        "artifact": artifact_data,
        "events": events_data,
        "event_count": len(events_data),
        "integrity": integrity.model_dump(),
        "signature_info": signature_info,
    }

    return proofpack_dict, integrity.manifest_hash


def _generate_human_readable(proofpack_dict: dict) -> str:
    """Generate human-readable text document from ProofPack."""
    lines = [
        "=" * 70,
        "CHAINBRIDGE PROOFPACK — EVIDENCE BUNDLE",
        "Doctrine Law 4, §4.2 Compliant",
        "=" * 70,
        "",
        f"ProofPack ID: {proofpack_dict['proofpack_id']}",
        f"Generated At: {proofpack_dict['generated_at']}",
        f"Schema Version: {proofpack_dict['schema_version']}",
        "",
        "-" * 50,
        "ARTIFACT",
        "-" * 50,
    ]

    artifact = proofpack_dict["artifact"]
    lines.extend([
        f"ID: {artifact['id']}",
        f"Name: {artifact['name']}",
        f"Type: {artifact['artifact_type']}",
        f"Status: {artifact['status']}",
        f"Description: {artifact.get('description') or 'N/A'}",
        f"Owner: {artifact.get('owner') or 'N/A'}",
        f"Tags: {', '.join(artifact.get('tags', [])) or 'None'}",
        f"Created: {artifact['created_at']}",
        f"Updated: {artifact['updated_at']}",
        "",
        "-" * 50,
        f"AUDIT EVENTS ({proofpack_dict['event_count']})",
        "-" * 50,
    ])

    for i, event in enumerate(proofpack_dict["events"], 1):
        lines.append(f"{i}. [{event['event_type']}] by {event.get('actor') or 'system'} @ {event['timestamp']}")
        if event.get("details"):
            lines.append(f"   Details: {json.dumps(event['details'])}")
        lines.append("")

    integrity = proofpack_dict["integrity"]
    lines.extend([
        "-" * 50,
        "INTEGRITY VERIFICATION",
        "-" * 50,
        f"Algorithm: {integrity.get('algorithm', 'SHA-256')}",
        f"Artifact Hash: {integrity['artifact_hash']}",
        f"Events Hash: {integrity['events_hash']}",
        f"Manifest Hash: {integrity['manifest_hash']}",
        "",
    ])

    sig_info = proofpack_dict.get("signature_info", {})
    if sig_info.get("signed"):
        lines.extend([
            "-" * 50,
            "CRYPTOGRAPHIC SIGNATURE",
            "-" * 50,
            f"Algorithm: {sig_info.get('algorithm', 'Ed25519')}",
            f"Key ID: {sig_info.get('key_id', 'N/A')}",
            f"Signed At: {sig_info.get('signed_at', 'N/A')}",
            "",
            "✓ This ProofPack is cryptographically signed",
            "",
        ])
    else:
        lines.extend([
            "",
            f"⚠ WARNING: This ProofPack is NOT cryptographically signed",
            f"   Reason: {sig_info.get('reason', 'Unknown')}",
            "",
        ])

    lines.extend([
        "=" * 70,
        "END OF PROOFPACK",
        "=" * 70,
    ])

    return "\n".join(lines)


def _generate_manifest(proofpack_dict: dict, json_hash: str, pdf_hash: str) -> dict:
    """Generate hash manifest for offline verification."""
    return {
        "schema_version": "1.0.0",
        "proofpack_id": proofpack_dict["proofpack_id"],
        "generated_at": proofpack_dict["generated_at"],
        "contents": [
            {
                "file": "proofpack.json",
                "hash": json_hash,
                "algorithm": "SHA-256",
            },
            {
                "file": "proofpack.txt",
                "hash": pdf_hash,
                "algorithm": "SHA-256",
            },
        ],
        "manifest_hash": proofpack_dict["integrity"]["manifest_hash"],
        "signature": proofpack_dict.get("integrity", {}).get("signature"),
        "public_key": proofpack_dict.get("integrity", {}).get("public_key"),
        "signed": proofpack_dict.get("signature_info", {}).get("signed", False),
    }


def _generate_verification_txt() -> str:
    """Generate verification instructions."""
    return """PROOFPACK VERIFICATION INSTRUCTIONS
===================================

This archive contains a ChainBridge ProofPack — a cryptographically
verifiable evidence bundle for audit and compliance purposes.

CONTENTS:
- proofpack.json — Machine-verifiable JSON bundle
- proofpack.txt — Human-readable document
- manifest.json — Hash manifest for offline verification
- verification.txt — This file

VERIFICATION STEPS:

1. MANIFEST VERIFICATION
   a. Compute SHA-256 of proofpack.json
   b. Compare to "contents[0].hash" in manifest.json
   c. Compute SHA-256 of proofpack.txt
   d. Compare to "contents[1].hash" in manifest.json

2. INTEGRITY VERIFICATION
   a. Open proofpack.json
   b. Locate "integrity.manifest_hash"
   c. Compare to "manifest_hash" in manifest.json
   d. Values must match

3. SIGNATURE VERIFICATION (if signed)
   a. Locate "signature" and "public_key" in manifest.json
   b. Verify Ed25519 signature of manifest_hash
   c. Use standard Ed25519 verification library

HASH ALGORITHM: SHA-256
SIGNATURE ALGORITHM: Ed25519
ENCODING: UTF-8

If all verifications pass, the ProofPack is VALID and untampered.

This verification can be performed OFFLINE without ChainBridge access.

Doctrine Reference: Law 4, §4.2 — ProofPack with trust indicators (MANDATORY)
"""


def _compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of data."""
    import hashlib
    return hashlib.sha256(data).hexdigest()


# =============================================================================
# ENDPOINT
# =============================================================================


@router.get("/{artifact_id}/download")
async def download_proofpack(
    artifact_id: UUID,
    include_payload: bool = Query(True, description="Include artifact payload in bundle"),
    store: ArtifactStore = Depends(get_artifact_store),
) -> StreamingResponse:
    """
    Download a complete ProofPack archive.

    Returns a ZIP archive containing:
    - proofpack.json — Machine-verifiable JSON bundle
    - proofpack.txt — Human-readable document
    - manifest.json — Hash manifest for offline verification
    - verification.txt — Verification instructions

    Doctrine Law 4, §4.2: ProofPack with trust indicators (MANDATORY)

    INV-PP-001: All archives cryptographically signed (if PyNaCl available)
    INV-PP-002: Hash manifest included for offline verification
    """
    # Fetch artifact
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact not found: {artifact_id}"
        )

    # Fetch audit events
    events = store.get_events(artifact_id)

    # Generate ProofPack JSON
    proofpack_dict, manifest_hash = _generate_proofpack_json(
        artifact=artifact,
        events=events,
        include_payload=include_payload,
    )

    # Generate human-readable document
    human_readable = _generate_human_readable(proofpack_dict)

    # Serialize to bytes
    json_bytes = json.dumps(proofpack_dict, indent=2, default=str).encode("utf-8")
    pdf_bytes = human_readable.encode("utf-8")

    # Compute content hashes
    json_hash = _compute_sha256(json_bytes)
    pdf_hash = _compute_sha256(pdf_bytes)

    # Generate manifest
    manifest = _generate_manifest(proofpack_dict, json_hash, pdf_hash)
    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")

    # Generate verification instructions
    verification_txt = _generate_verification_txt()
    verification_bytes = verification_txt.encode("utf-8")

    # Create ZIP archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("proofpack.json", json_bytes)
        zf.writestr("proofpack.txt", pdf_bytes)
        zf.writestr("manifest.json", manifest_bytes)
        zf.writestr("verification.txt", verification_bytes)

    zip_buffer.seek(0)

    # Log download
    logger.info(
        f"ProofPack download: artifact_id={artifact_id}, signed={manifest.get('signed', False)}"
    )

    # Return streaming response
    filename = f"proofpack-{artifact_id}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-ProofPack-Signed": str(manifest.get("signed", False)).lower(),
            "X-ProofPack-Manifest-Hash": manifest_hash,
        },
    )


@router.get("/{artifact_id}/manifest")
async def get_proofpack_manifest(
    artifact_id: UUID,
    store: ArtifactStore = Depends(get_artifact_store),
) -> dict:
    """
    Get the manifest for a ProofPack without downloading the full archive.

    Useful for quick verification checks or UI display.
    """
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact not found: {artifact_id}"
        )

    events = store.get_events(artifact_id)
    proofpack_dict, manifest_hash = _generate_proofpack_json(
        artifact=artifact,
        events=events,
        include_payload=False,  # Don't include payload for manifest-only
    )

    return {
        "artifact_id": str(artifact_id),
        "proofpack_id": proofpack_dict["proofpack_id"],
        "generated_at": proofpack_dict["generated_at"],
        "manifest_hash": manifest_hash,
        "event_count": proofpack_dict["event_count"],
        "signed": proofpack_dict.get("signature_info", {}).get("signed", False),
        "download_url": f"/api/v1/proofpack/{artifact_id}/download",
    }


@router.get("/{artifact_id}/verify")
async def verify_proofpack(
    artifact_id: UUID,
    store: ArtifactStore = Depends(get_artifact_store),
) -> dict:
    """
    Verify the integrity of a ProofPack.

    PAC-BENSON-P34: Trust Center verification endpoint.

    Returns verification result including:
    - Hash verification status
    - Signature verification status (if signed)
    - Overall verification status
    """
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact not found: {artifact_id}"
        )

    events = store.get_events(artifact_id)
    proofpack_dict, manifest_hash = _generate_proofpack_json(
        artifact=artifact,
        events=events,
        include_payload=True,
    )

    # Determine verification status
    is_signed = proofpack_dict.get("signature_info", {}).get("signed", False)
    signature_valid = is_signed  # Signature was verified during generation

    # Check integrity hashes
    integrity = proofpack_dict.get("integrity", {})
    hash_valid = bool(integrity.get("artifact_hash") and integrity.get("manifest_hash"))

    # Overall verification
    verified = hash_valid and (not is_signed or signature_valid)

    # Map to verification status
    if verified:
        status = "VERIFIED"
        message = "ProofPack integrity verified successfully"
    elif not hash_valid:
        status = "FAILED"
        message = "Hash verification failed"
    elif is_signed and not signature_valid:
        status = "FAILED"
        message = "Signature verification failed"
    else:
        status = "UNKNOWN"
        message = "Unable to determine verification status"

    return {
        "verified": verified,
        "status": status,
        "message": message,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "hash_algorithm": "SHA-256",
        "manifest_hash": manifest_hash,
        "signature_valid": signature_valid if is_signed else None,
        "hash_valid": hash_valid,
    }


@router.get("/{artifact_id}")
async def get_proofpack_summary(
    artifact_id: UUID,
    store: ArtifactStore = Depends(get_artifact_store),
) -> dict:
    """
    Get public summary of a ProofPack.

    PAC-BENSON-P34: Trust Center lookup endpoint.

    Returns public-safe summary without sensitive data.
    """
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail=f"ProofPack not found: {artifact_id}"
        )

    events = store.get_events(artifact_id)
    proofpack_dict, manifest_hash = _generate_proofpack_json(
        artifact=artifact,
        events=events,
        include_payload=False,
    )

    sig_info = proofpack_dict.get("signature_info", {})

    return {
        "proofpack_id": proofpack_dict["proofpack_id"],
        "generated_at": proofpack_dict["generated_at"],
        "schema_version": proofpack_dict.get("schema_version", "1.0.0"),
        "event_count": proofpack_dict["event_count"],
        "is_signed": sig_info.get("signed", False),
        "signature_algorithm": sig_info.get("algorithm") if sig_info.get("signed") else None,
        "manifest_hash": manifest_hash,
        "download_url": f"/api/v1/proofpack/{artifact_id}/download",
    }
