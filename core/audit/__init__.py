"""
ChainBridge Sovereign Audit Package
PAC-GENESIS-CERTIFIER-29 | JOB C

This package provides compliance certification and audit functionality:
- Genesis Certifier: Sovereign Settlement Proof generation
- Certificate verification and validation
- JSON-LD Verifiable Credential export
- QR code verification generation

Exports:
- GenesisCertifier: Main certification engine
- SovereignCertificate: Certificate data structure
- DealMetadata: Deal information container
- ComplianceMetrics: Compliance statistics
- CryptographicBinding: Cryptographic anchors
- CertificationLevel: Certificate authority levels
- CertificateStatus: Certificate lifecycle states
"""

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
]

__version__ = "1.0.0"
__pac__ = "PAC-GENESIS-CERTIFIER-29"
