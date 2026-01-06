"""
OCC Cryptographic Module

Provides ed25519 signing and verification for ProofPacks and Audit Entries.

PAC: PAC-OCC-P06 (hardening)
Lane: 2 — Evidence & Non-Repudiation
"""

from core.occ.crypto.ed25519_signer import (
    Ed25519Signer,
    SignatureBundle,
    get_proofpack_signer,
    verify_signature,
)
from core.occ.crypto.audit_signing import (
    SignedAuditEntry,
    AuditEntrySigner,
    EvidenceChainVerifier,
    get_audit_signer,
    get_evidence_verifier,
)

__all__ = [
    # ProofPack signing
    "Ed25519Signer",
    "SignatureBundle",
    "get_proofpack_signer",
    "verify_signature",
    # Audit entry signing (P06 hardening)
    "SignedAuditEntry",
    "AuditEntrySigner",
    "EvidenceChainVerifier",
    "get_audit_signer",
    "get_evidence_verifier",
]
