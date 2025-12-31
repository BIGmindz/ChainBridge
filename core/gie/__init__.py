"""
GIE (Governance Intelligence Engine) Package

Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-PROOF-LAYER-024.
"""

from core.gie.proof.provider import (
    ProofProvider,
    ProofInput,
    ProofOutput,
    ProofClass,
    ProofStatus,
    VerificationResult,
    VerificationStatus,
    get_proof_registry,
    generate_proof,
    verify_proof,
)
from core.gie.storage.pdo_store import (
    PDOStore,
    PDORecord,
    StorageResult,
    get_pdo_store,
)
from core.gie.storage.pdo_index import (
    PDOIndex,
    get_pdo_index,
)

__all__ = [
    # Proof Layer
    "ProofProvider",
    "ProofInput",
    "ProofOutput",
    "ProofClass",
    "ProofStatus",
    "VerificationResult",
    "VerificationStatus",
    "get_proof_registry",
    "generate_proof",
    "verify_proof",
    # Storage Layer
    "PDOStore",
    "PDORecord",
    "StorageResult",
    "get_pdo_store",
    "PDOIndex",
    "get_pdo_index",
]
