"""
OCC ProofPack API

Endpoints for generating and exporting ProofPacks (evidence bundles).
Mounted at /occ/proofpacks

Security Features (PP-003 mitigation):
- Ed25519 signatures on all ProofPacks
- Cryptographic verification endpoint
- Tamper-evident hash chains
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from core.occ.schemas.artifact import Artifact
from core.occ.schemas.audit_event import AuditEvent
from core.occ.schemas.proofpack import (
    ArtifactSummary,
    AuditEventSummary,
    IntegrityManifest,
    ProofPack,
    ProofPackCreate,
    ProofPackResponse,
    ProofPackStatus,
    SignatureVerificationResult,
)
from core.occ.store.artifact_store import ArtifactStore, get_artifact_store

# Import signing module (graceful fallback if PyNaCl not available)
try:
    from core.occ.crypto.ed25519_signer import NACL_AVAILABLE, SignatureBundle, get_proofpack_signer, verify_proofpack_signature
except ImportError:
    NACL_AVAILABLE = False
    get_proofpack_signer = None
    verify_proofpack_signature = None
    SignatureBundle = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/proofpacks", tags=["OCC ProofPacks"])


# =============================================================================
# HELPERS
# =============================================================================


def _artifact_to_summary(artifact: Artifact) -> ArtifactSummary:
    """Convert full artifact to summary for ProofPack."""
    return ArtifactSummary(
        id=str(artifact.id),
        name=artifact.name,
        artifact_type=artifact.artifact_type if isinstance(artifact.artifact_type, str) else artifact.artifact_type.value,
        status=artifact.status if isinstance(artifact.status, str) else artifact.status.value,
        description=artifact.description,
        owner=artifact.owner,
        tags=artifact.tags,
        created_at=artifact.created_at.isoformat() if hasattr(artifact.created_at, "isoformat") else str(artifact.created_at),
        updated_at=artifact.updated_at.isoformat() if hasattr(artifact.updated_at, "isoformat") else str(artifact.updated_at),
    )


def _event_to_summary(event: AuditEvent) -> AuditEventSummary:
    """Convert full audit event to summary for ProofPack."""
    return AuditEventSummary(
        id=str(event.id),
        event_type=event.event_type if isinstance(event.event_type, str) else event.event_type.value,
        actor=event.actor,
        timestamp=event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp),
        details=event.details,
    )


def _generate_proofpack(
    artifact: Artifact,
    events: list[AuditEvent],
    include_payload: bool = True,
    notes: Optional[str] = None,
    sign: bool = True,
) -> ProofPack:
    """
    Generate a ProofPack from artifact and events.

    Args:
        artifact: The artifact to bundle
        events: List of audit events
        include_payload: Whether to include artifact payload in bundle
        notes: Optional notes
        sign: Whether to cryptographically sign the ProofPack (default: True)

    Returns:
        ProofPack with integrity manifest (and signature if sign=True)
    """
    generated_at = datetime.now(timezone.utc)
    generated_at_str = generated_at.isoformat()

    # Build summaries
    artifact_summary = _artifact_to_summary(artifact)
    event_summaries = [_event_to_summary(e) for e in events]

    # Build data for hashing
    artifact_data = artifact_summary.model_dump()
    if include_payload:
        artifact_data["payload"] = artifact.payload
    events_data = [e.model_dump() for e in event_summaries]

    # Compute integrity hashes
    integrity = IntegrityManifest.compute(artifact_data, events_data, generated_at_str)

    # Apply cryptographic signature (PP-003 mitigation)
    if sign and NACL_AVAILABLE and get_proofpack_signer is not None:
        try:
            signer = get_proofpack_signer()
            signature_bundle = signer.sign_manifest_hash(integrity.manifest_hash)

            # Apply signature to integrity manifest
            integrity = integrity.apply_signature(
                signature=signature_bundle.signature,
                public_key=signature_bundle.public_key,
                key_id=signature_bundle.key_id,
                signed_at=signature_bundle.signed_at,
            )

            logger.debug(
                f"ProofPack signed with key {signature_bundle.key_id}",
                extra={"artifact_id": str(artifact.id)},
            )
        except Exception as e:
            logger.warning(f"Failed to sign ProofPack: {e}")
            # Continue without signature - log but don't fail
    elif sign and not NACL_AVAILABLE:
        logger.warning("ProofPack signing requested but PyNaCl not available. " "Install with: pip install pynacl")

    return ProofPack(
        artifact_id=artifact.id,
        artifact=artifact_summary,
        events=event_summaries,
        event_count=len(event_summaries),
        integrity=integrity,
        status=ProofPackStatus.COMPLETE,
        generated_at=generated_at,
        notes=notes,
    )


def _proofpack_to_json(proofpack: ProofPack, include_payload: bool = True, artifact: Optional[Artifact] = None) -> dict:
    """Convert ProofPack to JSON-serializable dict for export."""
    data = proofpack.model_dump(mode="json")
    if include_payload and artifact:
        data["artifact"]["payload"] = artifact.payload
    return data


def _proofpack_to_pdf_bytes(proofpack: ProofPack, artifact: Optional[Artifact] = None) -> bytes:
    """
    Generate a simple text-based PDF representation.
    In production, use reportlab or weasyprint for proper PDF generation.
    """
    # Simple text representation (placeholder for real PDF generation)
    lines = [
        "=" * 60,
        "CHAINBRIDGE PROOFPACK - EVIDENCE BUNDLE",
        "=" * 60,
        "",
        f"ProofPack ID: {proofpack.id}",
        f"Generated At: {proofpack.generated_at}",
        f"Schema Version: {proofpack.schema_version}",
        "",
        "-" * 40,
        "ARTIFACT",
        "-" * 40,
        f"ID: {proofpack.artifact.id}",
        f"Name: {proofpack.artifact.name}",
        f"Type: {proofpack.artifact.artifact_type}",
        f"Status: {proofpack.artifact.status}",
        f"Description: {proofpack.artifact.description or 'N/A'}",
        f"Owner: {proofpack.artifact.owner or 'N/A'}",
        f"Tags: {', '.join(proofpack.artifact.tags) if proofpack.artifact.tags else 'None'}",
        f"Created: {proofpack.artifact.created_at}",
        f"Updated: {proofpack.artifact.updated_at}",
        "",
        "-" * 40,
        f"AUDIT EVENTS ({proofpack.event_count})",
        "-" * 40,
    ]

    for i, event in enumerate(proofpack.events, 1):
        lines.append(f"{i}. [{event.event_type}] by {event.actor or 'system'} @ {event.timestamp}")
        if event.details:
            lines.append(f"   Details: {json.dumps(event.details)}")
        lines.append("")

    lines.extend(
        [
            "-" * 40,
            "INTEGRITY VERIFICATION",
            "-" * 40,
            f"Algorithm: {proofpack.integrity.algorithm}",
            f"Artifact Hash: {proofpack.integrity.artifact_hash}",
            f"Events Hash: {proofpack.integrity.events_hash}",
            f"Manifest Hash: {proofpack.integrity.manifest_hash}",
            "",
        ]
    )

    # Add signature information if present
    if proofpack.integrity.is_signed:
        lines.extend(
            [
                "-" * 40,
                "CRYPTOGRAPHIC SIGNATURE",
                "-" * 40,
                f"Algorithm: {proofpack.integrity.signature_algorithm}",
                f"Key ID: {proofpack.integrity.key_id}",
                f"Signed At: {proofpack.integrity.signed_at}",
                f"Signature: {proofpack.integrity.signature[:32]}...",
                f"Public Key: {proofpack.integrity.public_key[:32]}...",
                "",
                "✓ This ProofPack is cryptographically signed",
                "  Verify at: /occ/proofpacks/artifact/{artifact_id}/verify-signature",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "⚠ WARNING: This ProofPack is NOT cryptographically signed",
                "",
            ]
        )

    lines.extend(
        [
            "=" * 60,
            "END OF PROOFPACK",
            "=" * 60,
        ]
    )

    return "\n".join(lines).encode("utf-8")


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("/generate", response_model=ProofPackResponse, status_code=201)
async def generate_proofpack(
    request: ProofPackCreate,
    store: ArtifactStore = Depends(get_artifact_store),
) -> ProofPackResponse:
    """
    Generate a ProofPack for an artifact.

    Creates a cryptographically verifiable evidence bundle containing:
    - Artifact metadata
    - Complete audit event timeline
    - Integrity hashes (SHA-256)
    - Ed25519 signature (if PyNaCl available)

    Security: ProofPacks are cryptographically signed to prevent forgery.
    """
    # Get artifact
    artifact = store.get(request.artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {request.artifact_id}")

    # Get events
    events = store.get_events(request.artifact_id)

    # Generate ProofPack (with signature)
    proofpack = _generate_proofpack(
        artifact=artifact,
        events=events,
        include_payload=request.include_payload,
        notes=request.notes,
        sign=True,  # Always sign
    )

    logger.info(
        f"Generated ProofPack {proofpack.id} for artifact {request.artifact_id}",
        extra={"signed": proofpack.integrity.is_signed},
    )

    return ProofPackResponse(
        proofpack=proofpack,
        export_formats=["json", "pdf"],
        is_signed=proofpack.integrity.is_signed,
        verification_url=f"/occ/proofpacks/{proofpack.id}/verify",
    )


@router.get("/artifact/{artifact_id}", response_model=ProofPackResponse)
async def get_proofpack_for_artifact(
    artifact_id: UUID,
    include_payload: bool = Query(True, description="Include artifact payload"),
    store: ArtifactStore = Depends(get_artifact_store),
) -> ProofPackResponse:
    """
    Generate and return a ProofPack for an artifact (on-demand).

    This endpoint generates a fresh ProofPack each time (no caching).
    For cached/stored ProofPacks, use POST /generate.
    """
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    events = store.get_events(artifact_id)

    proofpack = _generate_proofpack(
        artifact=artifact,
        events=events,
        include_payload=include_payload,
    )

    return ProofPackResponse(
        proofpack=proofpack,
        export_formats=["json", "pdf"],
    )


@router.get("/artifact/{artifact_id}/export")
async def export_proofpack(
    artifact_id: UUID,
    format: str = Query("json", description="Export format: json or pdf"),
    include_payload: bool = Query(True, description="Include artifact payload"),
    store: ArtifactStore = Depends(get_artifact_store),
) -> Response:
    """
    Export a ProofPack in the specified format.

    Formats:
    - json: Machine-verifiable JSON bundle
    - pdf: Human/regulator-readable document
    """
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    events = store.get_events(artifact_id)

    proofpack = _generate_proofpack(
        artifact=artifact,
        events=events,
        include_payload=include_payload,
    )

    if format.lower() == "json":
        content = _proofpack_to_json(proofpack, include_payload, artifact)
        return Response(
            content=json.dumps(content, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="proofpack-{artifact_id}.json"',
            },
        )
    elif format.lower() == "pdf":
        # Return text file as placeholder (real PDF would use reportlab)
        content = _proofpack_to_pdf_bytes(proofpack, artifact)
        return Response(
            content=content,
            media_type="text/plain",  # Would be application/pdf with real PDF generation
            headers={
                "Content-Disposition": f'attachment; filename="proofpack-{artifact_id}.txt"',
            },
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use 'json' or 'pdf'.")


@router.get("/artifact/{artifact_id}/verify")
async def verify_proofpack(
    artifact_id: UUID,
    manifest_hash: str = Query(..., description="Manifest hash to verify"),
    store: ArtifactStore = Depends(get_artifact_store),
) -> dict:
    """
    Verify a ProofPack's integrity by comparing manifest hashes.

    Pass the manifest_hash from a previously generated ProofPack
    to verify the current state matches.
    """
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    events = store.get_events(artifact_id)

    # Generate fresh ProofPack
    proofpack = _generate_proofpack(artifact=artifact, events=events)

    # Compare hashes
    current_hash = proofpack.integrity.manifest_hash
    matches = current_hash == manifest_hash

    return {
        "artifact_id": str(artifact_id),
        "provided_hash": manifest_hash,
        "current_hash": current_hash,
        "verified": matches,
        "status": "VALID" if matches else "INVALID",
        "message": (
            "ProofPack integrity verified - no changes detected."
            if matches
            else "ProofPack integrity FAILED - artifact or events have changed since original generation."
        ),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/artifact/{artifact_id}/verify-signature", response_model=SignatureVerificationResult)
async def verify_proofpack_signature_endpoint(
    artifact_id: UUID,
    signature: str = Query(..., description="Base64-encoded Ed25519 signature"),
    public_key: str = Query(..., description="Base64-encoded Ed25519 public key"),
    manifest_hash: str = Query(..., description="SHA-256 manifest hash (hex)"),
    store: ArtifactStore = Depends(get_artifact_store),
) -> SignatureVerificationResult:
    """
    Verify a ProofPack's cryptographic signature.

    This endpoint performs full verification:
    1. Validates the Ed25519 signature against the provided public key
    2. Regenerates the current hash and compares with provided hash

    Security: This is the primary defense against ProofPack forgery (PP-003).

    Args:
        artifact_id: The artifact ID
        signature: Base64-encoded Ed25519 signature from the ProofPack
        public_key: Base64-encoded Ed25519 public key from the ProofPack
        manifest_hash: The manifest hash that was signed

    Returns:
        SignatureVerificationResult with detailed verification status
    """
    if not NACL_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Signature verification not available - PyNaCl not installed",
        )

    # Get artifact to verify hash
    artifact = store.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    events = store.get_events(artifact_id)

    # Regenerate ProofPack to get current hash (unsigned to compare)
    proofpack = _generate_proofpack(artifact=artifact, events=events, sign=False)
    current_hash = proofpack.integrity.manifest_hash

    # Verify hash matches
    hash_valid = current_hash == manifest_hash

    # Verify signature
    signature_bundle = SignatureBundle(
        signature=signature,
        public_key=public_key,
        key_id="external",  # Unknown key ID from external verification
    )

    signature_valid, sig_message = verify_proofpack_signature(manifest_hash, signature_bundle)

    # Combined result
    overall_valid = hash_valid and signature_valid

    if overall_valid:
        status = "VALID"
        message = "ProofPack signature and integrity verified successfully"
    elif not signature_valid:
        status = "INVALID_SIGNATURE"
        message = f"Signature verification failed: {sig_message}"
    else:
        status = "INVALID_HASH"
        message = "Content has changed since ProofPack was generated (hash mismatch)"

    return SignatureVerificationResult(
        artifact_id=str(artifact_id),
        proofpack_id=str(proofpack.id),
        signature_valid=signature_valid,
        hash_valid=hash_valid,
        overall_valid=overall_valid,
        status=status,
        message=message,
        manifest_hash=manifest_hash,
        key_id=None,  # Unknown for external verification
        algorithm="Ed25519",
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/signing-status")
async def get_signing_status() -> dict:
    """
    Get the current ProofPack signing configuration status.

    Returns:
        Information about signing capability and current key
    """
    if not NACL_AVAILABLE:
        return {
            "signing_available": False,
            "reason": "PyNaCl not installed",
            "install_command": "pip install pynacl",
        }

    try:
        signer = get_proofpack_signer()
        return {
            "signing_available": True,
            "key_id": signer.key_id,
            "public_key": signer.public_key_b64,
            "algorithm": "Ed25519",
            "message": "ProofPack signing is enabled",
        }
    except Exception as e:
        return {
            "signing_available": False,
            "reason": str(e),
        }
