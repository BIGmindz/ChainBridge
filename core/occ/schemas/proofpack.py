"""
ProofPack Pydantic Models (v2 syntax)

ProofPacks are cryptographically verifiable evidence bundles that package:
- Artifact metadata
- Complete audit event timeline
- Integrity hashes
- Cryptographic signatures (ed25519)
- Export metadata

They serve as the portable proof layer for external trust verification.

Security Properties (PP-003 mitigation):
- Hashes provide tamper detection
- Ed25519 signatures provide non-repudiation
- Public key embedded for independent verification
"""

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ProofPackStatus(str, Enum):
    """Status of a ProofPack."""

    GENERATING = "Generating"
    COMPLETE = "Complete"
    FAILED = "Failed"
    EXPIRED = "Expired"


class ProofPackFormat(str, Enum):
    """Export formats for ProofPacks."""

    JSON = "json"
    PDF = "pdf"


class AuditEventSummary(BaseModel):
    """Summarized audit event for inclusion in ProofPack."""

    id: str
    event_type: str
    actor: Optional[str]
    timestamp: str
    details: Dict[str, Any]


class ArtifactSummary(BaseModel):
    """Summarized artifact metadata for ProofPack."""

    id: str
    name: str
    artifact_type: str
    status: str
    description: Optional[str]
    owner: Optional[str]
    tags: List[str]
    created_at: str
    updated_at: str


class IntegrityManifest(BaseModel):
    """Cryptographic integrity information for the ProofPack."""

    algorithm: str = Field(default="SHA-256", description="Hash algorithm used")
    artifact_hash: str = Field(..., description="Hash of artifact data")
    events_hash: str = Field(..., description="Hash of events array")
    manifest_hash: str = Field(..., description="Hash of entire manifest")
    generated_at: str = Field(..., description="ISO timestamp of generation")

    # Signature fields (PP-003 mitigation)
    signature: Optional[str] = Field(
        None,
        description="Ed25519 signature of manifest_hash (base64-encoded)",
    )
    public_key: Optional[str] = Field(
        None,
        description="Ed25519 public key for verification (base64-encoded)",
    )
    key_id: Optional[str] = Field(
        None,
        description="Signing key identifier for rotation support",
    )
    signature_algorithm: Optional[str] = Field(
        None,
        description="Signature algorithm (Ed25519)",
    )
    signed_at: Optional[str] = Field(
        None,
        description="ISO timestamp when signature was created",
    )

    @classmethod
    def compute(cls, artifact_data: dict, events_data: list, generated_at: str) -> "IntegrityManifest":
        """Compute integrity hashes for the ProofPack (unsigned)."""

        def sha256_json(data: Any) -> str:
            canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(canonical.encode()).hexdigest()

        artifact_hash = sha256_json(artifact_data)
        events_hash = sha256_json(events_data)

        # Manifest hash covers everything
        manifest_data = {
            "artifact_hash": artifact_hash,
            "events_hash": events_hash,
            "generated_at": generated_at,
        }
        manifest_hash = sha256_json(manifest_data)

        return cls(
            artifact_hash=artifact_hash,
            events_hash=events_hash,
            manifest_hash=manifest_hash,
            generated_at=generated_at,
        )

    def apply_signature(
        self,
        signature: str,
        public_key: str,
        key_id: str,
        signed_at: str,
    ) -> "IntegrityManifest":
        """
        Create a new IntegrityManifest with signature applied.

        Returns a new instance (immutable pattern).
        """
        return IntegrityManifest(
            algorithm=self.algorithm,
            artifact_hash=self.artifact_hash,
            events_hash=self.events_hash,
            manifest_hash=self.manifest_hash,
            generated_at=self.generated_at,
            signature=signature,
            public_key=public_key,
            key_id=key_id,
            signature_algorithm="Ed25519",
            signed_at=signed_at,
        )

    @property
    def is_signed(self) -> bool:
        """Check if this manifest has a signature."""
        return self.signature is not None and self.public_key is not None


class ProofPackCreate(BaseModel):
    """Request to generate a ProofPack for an artifact."""

    artifact_id: UUID = Field(..., description="ID of the artifact to bundle")
    include_payload: bool = Field(default=True, description="Include artifact payload in bundle")
    redact_fields: List[str] = Field(default_factory=list, description="Fields to redact from payload")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes for the pack")


class ProofPack(BaseModel):
    """
    Complete ProofPack - a verifiable evidence bundle.

    Contains:
    - Artifact metadata and optionally payload
    - Complete audit event timeline
    - Cryptographic integrity manifest
    - Generation metadata
    """

    model_config = ConfigDict(use_enum_values=True)

    # Identity
    id: UUID = Field(default_factory=uuid4, description="Unique ProofPack identifier")
    artifact_id: UUID = Field(..., description="Source artifact ID")

    # Content
    artifact: ArtifactSummary = Field(..., description="Artifact metadata")
    events: List[AuditEventSummary] = Field(..., description="Audit event timeline")
    event_count: int = Field(..., description="Number of events included")

    # Integrity
    integrity: IntegrityManifest = Field(..., description="Cryptographic integrity data")

    # Metadata
    status: ProofPackStatus = Field(default=ProofPackStatus.COMPLETE)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the pack was generated",
    )
    generated_by: str = Field(default="system", description="Who/what generated the pack")
    notes: Optional[str] = Field(None, description="Optional notes")

    # Versioning
    schema_version: str = Field(default="1.1.0", description="ProofPack schema version")

    @property
    def is_signed(self) -> bool:
        """Check if this ProofPack has a valid signature."""
        return self.integrity.is_signed


class ProofPackResponse(BaseModel):
    """API response wrapper for ProofPack."""

    proofpack: ProofPack
    export_formats: List[str] = Field(
        default=["json", "pdf"],
        description="Available export formats",
    )
    verification_url: Optional[str] = Field(
        None,
        description="URL to verify this ProofPack externally",
    )
    is_signed: bool = Field(
        default=False,
        description="Whether the ProofPack has a cryptographic signature",
    )


class SignatureVerificationResult(BaseModel):
    """Result of ProofPack signature verification."""

    artifact_id: str = Field(..., description="Artifact ID that was verified")
    proofpack_id: Optional[str] = Field(None, description="ProofPack ID if known")

    # Verification results
    signature_valid: bool = Field(..., description="Whether the signature is valid")
    hash_valid: bool = Field(..., description="Whether the content hashes match")
    overall_valid: bool = Field(..., description="Combined validity (signature AND hash)")

    # Details
    status: str = Field(..., description="VALID, INVALID_SIGNATURE, INVALID_HASH, UNSIGNED")
    message: str = Field(..., description="Human-readable verification message")

    # Cryptographic details
    manifest_hash: str = Field(..., description="The manifest hash that was verified")
    key_id: Optional[str] = Field(None, description="Signing key ID used")
    algorithm: Optional[str] = Field(None, description="Signature algorithm")

    # Timestamp
    verified_at: str = Field(..., description="ISO timestamp of verification")

    class Config:
        json_schema_extra = {
            "example": {
                "artifact_id": "123e4567-e89b-12d3-a456-426614174000",
                "proofpack_id": "987fcdeb-51a2-3456-b789-012345678901",
                "signature_valid": True,
                "hash_valid": True,
                "overall_valid": True,
                "status": "VALID",
                "message": "ProofPack signature and integrity verified successfully",
                "manifest_hash": "a1b2c3d4e5f6...",
                "key_id": "pp-v1",
                "algorithm": "Ed25519",
                "verified_at": "2025-12-15T10:30:00Z",
            }
        }
