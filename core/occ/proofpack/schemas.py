"""
ProofPack Schemas — PROOFPACK_SPEC_v1.md Implementation

PAC-CODY-PROOFPACK-IMPL-01: ProofPack Generation & Offline Verification

These schemas define the canonical structure for ProofPacks per spec v1:
- Deterministic JSON serialization
- SHA-256 hash binding
- Manifest structure
- Artifact wrappers

NO interpretation, NO derived data, NO compliance claims.

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# CONSTANTS
# =============================================================================

PROOFPACK_VERSION = "1.0"
HASH_ALGORITHM = "sha256"
EXPORTER_SYSTEM = "chainbridge"
EXPORTER_COMPONENT = "proofpack-exporter"
EXPORTER_VERSION = "1.0.0"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def canonical_json(data: Any) -> str:
    """
    Serialize data to canonical JSON (deterministic).

    Per spec:
    - Lexicographic key ordering (sorted)
    - Compact separators (",", ":")
    - UTF-8 encoding
    - No BOM

    Note: Must match PDORecord.compute_hash() algorithm exactly.
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash and return lowercase hex string."""
    return hashlib.sha256(data).hexdigest()


def compute_json_hash(data: Any) -> str:
    """Compute SHA-256 hash of canonical JSON."""
    canonical = canonical_json(data)
    return compute_sha256(canonical.encode("utf-8"))


def ref_to_filename(ref: str) -> str:
    """
    Convert a ref to a canonical filename.

    Per spec: {sha256_first_16_chars}.json
    """
    full_hash = compute_sha256(ref.encode("utf-8"))
    return f"{full_hash[:16]}.json"


# =============================================================================
# VERIFICATION OUTCOMES
# =============================================================================


class VerificationOutcome(str, Enum):
    """ProofPack verification outcomes per spec Section 6.2."""

    VALID = "VALID"
    INVALID_PDO_HASH = "INVALID_PDO_HASH"
    INVALID_ARTIFACT_HASH = "INVALID_ARTIFACT_HASH"
    INVALID_MANIFEST_HASH = "INVALID_MANIFEST_HASH"
    INVALID_LINEAGE = "INVALID_LINEAGE"
    INVALID_REFERENCES = "INVALID_REFERENCES"
    INCOMPLETE = "INCOMPLETE"


# =============================================================================
# ARTIFACT SCHEMAS (Section 5)
# =============================================================================


class ArtifactResolutionStatus(str, Enum):
    """Resolution status for input artifacts."""

    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    ACCESS_DENIED = "access_denied"
    EXPIRED = "expired"


class InputArtifact(BaseModel):
    """
    Input artifact wrapper per spec Section 5.2.

    Wraps resolved or unresolved input artifacts.
    """

    model_config = ConfigDict(extra="forbid")

    ref: str = Field(..., description="Original ref from input_refs")
    artifact_type: str = Field(..., description="Type identifier")
    content: Optional[Dict[str, Any]] = Field(None, description="Artifact content (null if unresolved)")
    content_hash: Optional[str] = Field(None, description="SHA-256 of content")
    acquired_at: Optional[str] = Field(None, description="ISO8601 UTC when acquired")

    # For unresolved artifacts
    resolution_status: Optional[ArtifactResolutionStatus] = Field(None, description="Resolution status if unresolved")
    resolution_attempted_at: Optional[str] = Field(None, description="ISO8601 UTC when resolution was attempted")


class DecisionArtifact(BaseModel):
    """
    Decision artifact wrapper per spec Section 5.3.
    """

    model_config = ConfigDict(extra="forbid")

    ref: str = Field(..., description="Decision ref")
    artifact_type: str = Field(default="decision", description="Always 'decision'")
    content: Dict[str, Any] = Field(..., description="Decision content")
    content_hash: str = Field(..., description="SHA-256 of content")
    decision_timestamp: str = Field(..., description="ISO8601 UTC of decision")


class OutcomeArtifact(BaseModel):
    """
    Outcome artifact wrapper per spec Section 5.4.
    """

    model_config = ConfigDict(extra="forbid")

    ref: str = Field(..., description="Outcome ref")
    artifact_type: str = Field(default="outcome", description="Always 'outcome'")
    content: Dict[str, Any] = Field(..., description="Outcome content")
    content_hash: str = Field(..., description="SHA-256 of content")
    outcome_timestamp: str = Field(..., description="ISO8601 UTC of outcome")


# =============================================================================
# MANIFEST SCHEMAS (Section 4)
# =============================================================================


class ManifestContentEntry(BaseModel):
    """Entry in manifest contents array."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Relative path within ProofPack")
    hash: str = Field(..., description="SHA-256 of file content")
    hash_algorithm: str = Field(default="sha256", description="Hash algorithm")


class ManifestInputEntry(ManifestContentEntry):
    """Entry for input artifacts in manifest."""

    ref: str = Field(..., description="Original ref from input_refs")


class ManifestDecisionEntry(ManifestContentEntry):
    """Entry for decision artifact in manifest."""

    ref: str = Field(..., description="Decision ref")


class ManifestOutcomeEntry(ManifestContentEntry):
    """Entry for outcome artifact in manifest."""

    ref: str = Field(..., description="Outcome ref")


class ManifestLineageEntry(ManifestContentEntry):
    """Entry for lineage PDO in manifest."""

    pdo_id: str = Field(..., description="Lineage PDO ID")


class ManifestContents(BaseModel):
    """Contents section of manifest."""

    model_config = ConfigDict(extra="forbid")

    pdo: ManifestContentEntry = Field(..., description="PDO record entry")
    inputs: List[ManifestInputEntry] = Field(default_factory=list, description="Input artifacts")
    decision: ManifestDecisionEntry = Field(..., description="Decision artifact")
    outcome: ManifestOutcomeEntry = Field(..., description="Outcome artifact")
    lineage: List[ManifestLineageEntry] = Field(default_factory=list, description="Lineage PDOs")


class ManifestExporter(BaseModel):
    """Exporter metadata in manifest."""

    model_config = ConfigDict(extra="forbid")

    system: str = Field(default=EXPORTER_SYSTEM, description="Exporting system")
    component: str = Field(default=EXPORTER_COMPONENT, description="Exporting component")
    version: str = Field(default=EXPORTER_VERSION, description="Exporter version")


class ManifestIntegrity(BaseModel):
    """Integrity section of manifest."""

    model_config = ConfigDict(extra="forbid")

    manifest_hash: str = Field(..., description="SHA-256 of manifest (excluding integrity block)")
    hash_algorithm: str = Field(default="sha256", description="Hash algorithm")
    hash_inputs: List[str] = Field(
        default=["proofpack_version", "pdo_id", "exported_at", "exporter", "contents"],
        description="Fields included in hash computation",
    )


class ProofPackManifest(BaseModel):
    """
    Root manifest per spec Section 4.1.

    This is the authoritative index of a ProofPack.
    """

    model_config = ConfigDict(extra="forbid")

    proofpack_version: str = Field(default=PROOFPACK_VERSION, description="Spec version")
    pdo_id: str = Field(..., description="PDO ID this ProofPack represents")
    exported_at: str = Field(..., description="ISO8601 UTC export timestamp")
    exporter: ManifestExporter = Field(default_factory=ManifestExporter, description="Exporter info")
    contents: ManifestContents = Field(..., description="Content index")
    integrity: ManifestIntegrity = Field(..., description="Integrity hashes")

    def compute_manifest_hash(self) -> str:
        """
        Compute manifest hash per spec Section 4.2.

        Hash covers everything EXCEPT the integrity block.
        """
        manifest_data = {
            "proofpack_version": self.proofpack_version,
            "pdo_id": self.pdo_id,
            "exported_at": self.exported_at,
            "exporter": self.exporter.model_dump(),
            "contents": self.contents.model_dump(),
        }
        return compute_json_hash(manifest_data)


# =============================================================================
# VERIFICATION RESULT
# =============================================================================


class VerificationStep(BaseModel):
    """Result of a single verification step."""

    model_config = ConfigDict(extra="forbid")

    step: str = Field(..., description="Step name")
    passed: bool = Field(..., description="Whether step passed")
    message: str = Field(..., description="Human-readable result")
    expected: Optional[str] = Field(None, description="Expected value")
    actual: Optional[str] = Field(None, description="Actual value")


class ProofPackVerificationResult(BaseModel):
    """
    Complete verification result for a ProofPack.
    """

    model_config = ConfigDict(extra="forbid")

    outcome: VerificationOutcome = Field(..., description="Overall verification outcome")
    pdo_id: str = Field(..., description="PDO ID being verified")
    verified_at: str = Field(..., description="ISO8601 UTC verification timestamp")
    steps: List[VerificationStep] = Field(default_factory=list, description="Individual step results")
    is_valid: bool = Field(..., description="True if outcome is VALID")
    error_message: Optional[str] = Field(None, description="Error description if invalid")
