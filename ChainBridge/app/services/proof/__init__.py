"""Proof Services Module.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🔵 BLUE                                             ║
║ PAC: PAC-CODY-A6-BACKEND-GUARDRAILS-01                               ║
╚══════════════════════════════════════════════════════════════════════╝

Backend service layer for proof lineage validation.
"""

from app.services.proof.lineage import (
    ProofLineageService,
    LineageValidationResult,
    LineageViolationType,
    validate_proof_lineage,
    enforce_forward_only_linkage,
    detect_lineage_mutation,
)

__all__ = [
    # Classes
    "ProofLineageService",
    "LineageValidationResult",
    "LineageViolationType",
    # Functions
    "validate_proof_lineage",
    "enforce_forward_only_linkage",
    "detect_lineage_mutation",
]
