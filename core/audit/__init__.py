"""
ChainBridge Sovereign Audit Package
PAC-GENESIS-CERTIFIER-29 | JOB C
PAC-AUDIT-P70 | Immutable Chronicle

This package provides compliance certification and audit functionality:
- Genesis Certifier: Sovereign Settlement Proof generation
- Certificate verification and validation
- JSON-LD Verifiable Credential export
- QR code verification generation
- Merkle Chronicler: Tamper-evident log anchoring (PAC-P70)

Exports:
- GenesisCertifier: Main certification engine
- SovereignCertificate: Certificate data structure
- DealMetadata: Deal information container
- ComplianceMetrics: Compliance statistics
- CryptographicBinding: Cryptographic anchors
- CertificationLevel: Certificate authority levels
- CertificateStatus: Certificate lifecycle states
- MerkleChronicler: Immutable log anchoring via Merkle trees
"""

try:
    from core.audit.genesis_certifier import (
        GenesisCertifier,
        SovereignCertificate,
        DealMetadata,
        ComplianceMetrics,
        CryptographicBinding,
        CertificationLevel,
        CertificateStatus,
        QRCodeGenerator,
        GENESIS_BLOCK_HASH,
        GENESIS_ANCHOR,
        CHAINBRIDGE_LEGAL_ENTITY,
        CERTIFICATION_VERSION,
        certify_megacorp_alpha_pilot,
    )
except ImportError as e:
    # Graceful degradation if qrcode or other dependencies missing
    import warnings
    warnings.warn(f"Genesis Certifier unavailable: {e}", ImportWarning)
    GenesisCertifier = None
    GENESIS_BLOCK_HASH = None
    GENESIS_ANCHOR = None
    CHAINBRIDGE_LEGAL_ENTITY = None
    CERTIFICATION_VERSION = None

from core.audit.merkle_chronicler import MerkleChronicler, get_global_chronicler

__all__ = [
    "GenesisCertifier",
    "SovereignCertificate",
    "DealMetadata",
    "ComplianceMetrics",
    "CryptographicBinding",
    "CertificationLevel",
    "CertificateStatus",
    "QRCodeGenerator",
    "GENESIS_BLOCK_HASH",
    "GENESIS_ANCHOR",
    "CHAINBRIDGE_LEGAL_ENTITY",
    "CERTIFICATION_VERSION",
    "certify_megacorp_alpha_pilot",
    "MerkleChronicler",
    "get_global_chronicler",
]

__version__ = "1.0.0"
__pac__ = "PAC-GENESIS-CERTIFIER-29"
