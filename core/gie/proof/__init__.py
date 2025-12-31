"""
GIE Proof Package

Proof provider abstraction and implementations.
"""

from core.gie.proof.provider import (
    ProofProvider,
    ProofInput,
    ProofOutput,
    ProofClass,
    ProofStatus,
    VerificationResult,
    VerificationStatus,
    LocalHashProvider,
    ProofProviderRegistry,
    get_proof_registry,
    reset_proof_registry,
    generate_proof,
    verify_proof,
)

__all__ = [
    "ProofProvider",
    "ProofInput",
    "ProofOutput",
    "ProofClass",
    "ProofStatus",
    "VerificationResult",
    "VerificationStatus",
    "LocalHashProvider",
    "ProofProviderRegistry",
    "get_proof_registry",
    "reset_proof_registry",
    "generate_proof",
    "verify_proof",
]
