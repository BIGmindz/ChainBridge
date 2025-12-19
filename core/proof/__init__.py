"""
core/proof - Proof Integrity Module

PAC-SAM-PROOF-INTEGRITY-01

Security controls for proof artifact integrity:
- Deterministic hashing over canonical fields
- Hash chain validation
- Tamper detection
"""

from core.proof.validation import (
    ProofValidationError,
    ProofValidator,
    validate_proof_integrity,
    verify_proof_chain,
)

__all__ = [
    "ProofValidationError",
    "ProofValidator",
    "validate_proof_integrity",
    "verify_proof_chain",
]
