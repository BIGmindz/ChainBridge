"""
ProofPack Module — PROOFPACK_SPEC_v1.md Implementation

PAC-CODY-PROOFPACK-IMPL-01: ProofPack Generation & Offline Verification

Exports:
- ProofPackGenerator: Generate ProofPacks from PDOs
- ProofPackVerifier: Verify ProofPacks offline
- Schema types for ProofPack structure

Author: CODY (GID-01) - Backend
"""

from core.occ.proofpack.generator import (
    ArtifactResolver,
    ProofPackGenerationError,
    ProofPackGenerator,
    StubArtifactResolver,
    generate_proofpack,
    get_proofpack_generator,
    reset_proofpack_generator,
)
from core.occ.proofpack.schemas import (
    HASH_ALGORITHM,
    PROOFPACK_VERSION,
    DecisionArtifact,
    InputArtifact,
    ManifestContents,
    ManifestExporter,
    ManifestIntegrity,
    OutcomeArtifact,
    ProofPackManifest,
    ProofPackVerificationResult,
    VerificationOutcome,
    VerificationStep,
    canonical_json,
    compute_json_hash,
    compute_sha256,
    ref_to_filename,
)
from core.occ.proofpack.verifier import ProofPackVerificationError, ProofPackVerifier, get_proofpack_verifier, verify_proofpack

__all__ = [
    # Generator
    "ArtifactResolver",
    "ProofPackGenerationError",
    "ProofPackGenerator",
    "StubArtifactResolver",
    "generate_proofpack",
    "get_proofpack_generator",
    "reset_proofpack_generator",
    # Verifier
    "ProofPackVerificationError",
    "ProofPackVerifier",
    "get_proofpack_verifier",
    "verify_proofpack",
    # Schemas
    "HASH_ALGORITHM",
    "PROOFPACK_VERSION",
    "DecisionArtifact",
    "InputArtifact",
    "ManifestContents",
    "ManifestExporter",
    "ManifestIntegrity",
    "OutcomeArtifact",
    "ProofPackManifest",
    "ProofPackVerificationResult",
    "VerificationOutcome",
    "VerificationStep",
    # Utilities
    "canonical_json",
    "compute_json_hash",
    "compute_sha256",
    "ref_to_filename",
]
