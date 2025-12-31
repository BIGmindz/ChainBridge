"""
Attestation Schemas — PAC-SAM-P01-ATTESTATION-PROVIDER-READINESS-01

Pydantic schemas for attestation records and validation.

Authority: SAM (GID-06)
Dispatch: PAC-BENSON-EXEC-P62
Mode: SECURITY ANALYSIS
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================

class AttestationStatusSchema(str, Enum):
    """Attestation status values."""
    PENDING = "PENDING"
    ANCHORED = "ANCHORED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class ArtifactTypeSchema(str, Enum):
    """Governance artifact types."""
    PAC = "PAC"
    BER = "BER"
    PDO = "PDO"
    WRAP = "WRAP"


class HashAlgorithmSchema(str, Enum):
    """Supported hash algorithms."""
    SHA256 = "sha256"
    SHA3_256 = "sha3_256"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"


class ProviderTypeSchema(str, Enum):
    """Attestation provider types."""
    OFFCHAIN_FILE = "OFFCHAIN_FILE"
    ONCHAIN_ETHEREUM = "ONCHAIN_ETHEREUM"
    ONCHAIN_POLYGON = "ONCHAIN_POLYGON"
    HYBRID = "HYBRID"
    STUB = "STUB"


# =============================================================================
# ATTESTATION RECORD SCHEMA
# =============================================================================

class AttestationRecord(BaseModel):
    """
    Schema for a single attestation record.
    
    Represents the cryptographic binding between a governance
    artifact and its attestation proof.
    """
    
    attestation_id: str = Field(
        ...,
        description="Unique identifier for this attestation",
        pattern=r"^ATT-[A-Z0-9]{16}$",
    )
    
    artifact_id: str = Field(
        ...,
        description="ID of the attested artifact",
    )
    
    artifact_type: ArtifactTypeSchema = Field(
        ...,
        description="Type of governance artifact",
    )
    
    artifact_hash: str = Field(
        ...,
        description="SHA-256 hash of artifact content",
        min_length=64,
        max_length=128,
    )
    
    hash_algorithm: HashAlgorithmSchema = Field(
        default=HashAlgorithmSchema.SHA256,
        description="Hash algorithm used",
    )
    
    status: AttestationStatusSchema = Field(
        ...,
        description="Current attestation status",
    )
    
    provider_type: ProviderTypeSchema = Field(
        ...,
        description="Type of attestation provider",
    )
    
    timestamp: datetime = Field(
        ...,
        description="When attestation was created",
    )
    
    anchor_reference: Optional[str] = Field(
        None,
        description="External anchor reference (tx hash, file path)",
    )
    
    chain_hash: Optional[str] = Field(
        None,
        description="Hash linking to previous attestation",
    )
    
    previous_attestation_id: Optional[str] = Field(
        None,
        description="ID of previous attestation in chain",
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attestation metadata",
    )
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "attestation_id": "ATT-A1B2C3D4E5F6G7H8",
                "artifact_id": "PAC-SAM-P01",
                "artifact_type": "PAC",
                "artifact_hash": "abc123" + "0" * 58,
                "hash_algorithm": "sha256",
                "status": "ANCHORED",
                "provider_type": "OFFCHAIN_FILE",
                "timestamp": "2025-12-26T00:00:00Z",
                "anchor_reference": "data/attestations/PAC_attestations.json",
                "chain_hash": "def456" + "0" * 58,
                "metadata": {"agent_gid": "GID-06"},
            }
        }


class AttestationChain(BaseModel):
    """
    Schema for an attestation chain.
    
    Represents the full chain of attestations for an artifact,
    enabling verification of attestation history.
    """
    
    artifact_id: str = Field(
        ...,
        description="ID of the artifact this chain belongs to",
    )
    
    artifact_type: ArtifactTypeSchema = Field(
        ...,
        description="Type of governance artifact",
    )
    
    attestations: List[AttestationRecord] = Field(
        default_factory=list,
        description="Ordered list of attestations",
    )
    
    chain_length: int = Field(
        ...,
        description="Number of attestations in chain",
    )
    
    first_attestation: Optional[datetime] = Field(
        None,
        description="Timestamp of first attestation",
    )
    
    last_attestation: Optional[datetime] = Field(
        None,
        description="Timestamp of most recent attestation",
    )
    
    chain_integrity: bool = Field(
        ...,
        description="Whether chain hash integrity is valid",
    )
    
    @field_validator("chain_length", mode="before")
    @classmethod
    def compute_chain_length(cls, v, info):
        """Compute chain length from attestations if not provided."""
        if v is None and "attestations" in info.data:
            return len(info.data["attestations"])
        return v


class ArtifactAttestation(BaseModel):
    """
    Schema for artifact with its attestation.
    
    Combines artifact metadata with its attestation proof
    for verification and audit purposes.
    """
    
    artifact_id: str = Field(
        ...,
        description="Unique artifact identifier",
    )
    
    artifact_type: ArtifactTypeSchema = Field(
        ...,
        description="Type of governance artifact",
    )
    
    content_hash: str = Field(
        ...,
        description="Hash of artifact content",
    )
    
    attestation: Optional[AttestationRecord] = Field(
        None,
        description="Most recent attestation for this artifact",
    )
    
    is_attested: bool = Field(
        ...,
        description="Whether artifact has valid attestation",
    )
    
    attestation_chain: Optional[AttestationChain] = Field(
        None,
        description="Full attestation chain if requested",
    )


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class CreateAttestationRequest(BaseModel):
    """Request schema for creating attestation."""
    
    artifact_id: str = Field(
        ...,
        description="ID of artifact to attest",
    )
    
    artifact_type: ArtifactTypeSchema = Field(
        ...,
        description="Type of artifact",
    )
    
    content: str = Field(
        ...,
        description="Base64-encoded artifact content",
    )
    
    hash_algorithm: HashAlgorithmSchema = Field(
        default=HashAlgorithmSchema.SHA256,
        description="Hash algorithm to use",
    )
    
    provider_type: ProviderTypeSchema = Field(
        default=ProviderTypeSchema.OFFCHAIN_FILE,
        description="Attestation provider to use",
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class CreateAttestationResponse(BaseModel):
    """Response schema for attestation creation."""
    
    success: bool = Field(
        ...,
        description="Whether attestation was created",
    )
    
    attestation: Optional[AttestationRecord] = Field(
        None,
        description="Created attestation record",
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if failed",
    )
    
    timestamp: datetime = Field(
        ...,
        description="Response timestamp",
    )


class VerifyAttestationRequest(BaseModel):
    """Request schema for verifying attestation."""
    
    attestation_id: str = Field(
        ...,
        description="ID of attestation to verify",
    )
    
    expected_hash: Optional[str] = Field(
        None,
        description="Expected artifact hash",
    )


class VerifyAttestationResponse(BaseModel):
    """Response schema for attestation verification."""
    
    success: bool = Field(
        ...,
        description="Whether verification passed",
    )
    
    attestation: Optional[AttestationRecord] = Field(
        None,
        description="Verified attestation record",
    )
    
    verification_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Verification details",
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if failed",
    )
    
    timestamp: datetime = Field(
        ...,
        description="Response timestamp",
    )


class GetChainRequest(BaseModel):
    """Request schema for getting attestation chain."""
    
    artifact_id: str = Field(
        ...,
        description="ID of artifact",
    )
    
    artifact_type: Optional[ArtifactTypeSchema] = Field(
        None,
        description="Type filter",
    )
    
    verify_integrity: bool = Field(
        default=True,
        description="Whether to verify chain integrity",
    )


class GetChainResponse(BaseModel):
    """Response schema for attestation chain."""
    
    success: bool = Field(
        ...,
        description="Whether chain was retrieved",
    )
    
    chain: Optional[AttestationChain] = Field(
        None,
        description="Attestation chain",
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if failed",
    )
    
    timestamp: datetime = Field(
        ...,
        description="Response timestamp",
    )
