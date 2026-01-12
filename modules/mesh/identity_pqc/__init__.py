#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               CHAINBRIDGE HYBRID PQC IDENTITY MODULE                         ║
║                       PAC-SEC-P819 IMPLEMENTATION                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Hybrid ED25519 + ML-DSA-65 Cryptographic Identity                           ║
║                                                                              ║
║  "Quantum-resistant trust for a post-quantum world."                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Public API:
    from modules.mesh.identity_pqc import (
        HybridIdentity,
        HybridSignature,
        IdentityManager,
        SignatureMode,
        migrate_legacy_identity,
    )

Version: 4.0.0
FIPS 204: ML-DSA-65 (Dilithium)
"""

from .core import HybridIdentity, HybridKeyPair, PQCKeyPair, ED25519KeyPair
from .signatures import HybridSignature, SignatureMode
from .errors import (
    PQCError,
    KeyGenerationError,
    SignatureError,
    VerificationError,
    SerializationError,
    MigrationError,
    ValidationError,
)
from .constants import (
    VERSION,
    SIGNATURE_MODE_HYBRID,
    SIGNATURE_MODE_LEGACY,
    SIGNATURE_MODE_PQC_ONLY,
    ED25519_PUBLIC_KEY_SIZE,
    ED25519_PRIVATE_KEY_SIZE,
    ED25519_SIGNATURE_SIZE,
    MLDSA65_PUBLIC_KEY_SIZE,
    MLDSA65_PRIVATE_KEY_SIZE,
    MLDSA65_SIGNATURE_SIZE,
)
from .migration import migrate_legacy_identity, can_migrate
from .validation import validate_public_key, validate_signature

__version__ = "4.0.0"
__all__ = [
    # Core classes
    "HybridIdentity",
    "HybridKeyPair",
    "PQCKeyPair",
    "ED25519KeyPair",
    # Signatures
    "HybridSignature",
    "SignatureMode",
    # Errors
    "PQCError",
    "KeyGenerationError",
    "SignatureError",
    "VerificationError",
    "SerializationError",
    "MigrationError",
    "ValidationError",
    # Constants
    "VERSION",
    "SIGNATURE_MODE_HYBRID",
    "SIGNATURE_MODE_LEGACY",
    "SIGNATURE_MODE_PQC_ONLY",
    # Utilities
    "migrate_legacy_identity",
    "can_migrate",
    "validate_public_key",
    "validate_signature",
]
