#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         PQC CONSTANTS                                        ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

FIPS 204 ML-DSA-65 (Dilithium) Parameters and System Constants.
"""

from enum import Enum, auto
from typing import Final

# ══════════════════════════════════════════════════════════════════════════════
# VERSION
# ══════════════════════════════════════════════════════════════════════════════

VERSION: Final[str] = "4.0.0"
FORMAT_VERSION: Final[int] = 1

# ══════════════════════════════════════════════════════════════════════════════
# SIGNATURE MODES
# ══════════════════════════════════════════════════════════════════════════════

SIGNATURE_MODE_LEGACY: Final[str] = "LEGACY"       # ED25519 only (backward compat)
SIGNATURE_MODE_HYBRID: Final[str] = "HYBRID"       # Both ED25519 + ML-DSA-65
SIGNATURE_MODE_PQC_ONLY: Final[str] = "PQC_ONLY"   # ML-DSA-65 only (future)

DEFAULT_SIGNATURE_MODE: Final[str] = SIGNATURE_MODE_HYBRID

# ══════════════════════════════════════════════════════════════════════════════
# ED25519 PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════

ED25519_PUBLIC_KEY_SIZE: Final[int] = 32    # bytes
ED25519_PRIVATE_KEY_SIZE: Final[int] = 32   # bytes (seed form)
ED25519_SIGNATURE_SIZE: Final[int] = 64     # bytes

# ══════════════════════════════════════════════════════════════════════════════
# ML-DSA-65 PARAMETERS (FIPS 204)
# ══════════════════════════════════════════════════════════════════════════════

MLDSA65_PUBLIC_KEY_SIZE: Final[int] = 1952   # bytes
MLDSA65_PRIVATE_KEY_SIZE: Final[int] = 4032  # bytes
MLDSA65_SIGNATURE_SIZE: Final[int] = 3309    # bytes

# Security level
MLDSA65_SECURITY_LEVEL: Final[int] = 3       # NIST Level 3 (~AES-192)
MLDSA65_OID: Final[str] = "2.16.840.1.101.3.4.3.17"  # FIPS 204 OID

# ══════════════════════════════════════════════════════════════════════════════
# HYBRID PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════

HYBRID_PUBLIC_KEY_SIZE: Final[int] = ED25519_PUBLIC_KEY_SIZE + MLDSA65_PUBLIC_KEY_SIZE  # 1984
HYBRID_PRIVATE_KEY_SIZE: Final[int] = ED25519_PRIVATE_KEY_SIZE + MLDSA65_PRIVATE_KEY_SIZE  # 4064
HYBRID_SIGNATURE_SIZE: Final[int] = ED25519_SIGNATURE_SIZE + MLDSA65_SIGNATURE_SIZE  # 3373

# Binary format: [VERSION:1][ED25519:64][MLDSA65:3309]
HYBRID_SIGNATURE_HEADER_SIZE: Final[int] = 1
HYBRID_SIGNATURE_TOTAL_SIZE: Final[int] = HYBRID_SIGNATURE_HEADER_SIZE + HYBRID_SIGNATURE_SIZE  # 3374

# ══════════════════════════════════════════════════════════════════════════════
# NODE IDENTITY PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════

NODE_ID_LENGTH: Final[int] = 32              # hex characters (16 bytes)
NODE_ID_HASH_ALGORITHM: Final[str] = "sha256"

DEFAULT_FEDERATION_ID: Final[str] = "CHAINBRIDGE-FEDERATION"
DEFAULT_CAPABILITIES: Final[tuple] = ("ATTEST", "RELAY", "GOSSIP", "PQC")

# ══════════════════════════════════════════════════════════════════════════════
# FILE PERMISSIONS
# ══════════════════════════════════════════════════════════════════════════════

IDENTITY_FILE_MODE: Final[int] = 0o600       # Owner read/write only

# ══════════════════════════════════════════════════════════════════════════════
# CHALLENGE-RESPONSE
# ══════════════════════════════════════════════════════════════════════════════

CHALLENGE_NONCE_SIZE: Final[int] = 32        # bytes (64 hex chars)
CHALLENGE_TIMEOUT_SECONDS: Final[int] = 300  # 5 minutes

# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION LIMITS
# ══════════════════════════════════════════════════════════════════════════════

MAX_MESSAGE_SIZE: Final[int] = 100 * 1024 * 1024  # 100 MB
MAX_NODE_NAME_LENGTH: Final[int] = 256
MAX_FEDERATION_ID_LENGTH: Final[int] = 256

# ══════════════════════════════════════════════════════════════════════════════
# BACKEND IDENTIFIERS
# ══════════════════════════════════════════════════════════════════════════════

BACKEND_DILITHIUM_PY: Final[str] = "dilithium-py"
BACKEND_LIBOQS: Final[str] = "liboqs"
DEFAULT_PQC_BACKEND: Final[str] = BACKEND_DILITHIUM_PY


class SignatureMode(Enum):
    """Signature mode enumeration."""
    LEGACY = auto()     # ED25519 only
    HYBRID = auto()     # ED25519 + ML-DSA-65
    PQC_ONLY = auto()   # ML-DSA-65 only
    
    @classmethod
    def from_string(cls, mode: str) -> "SignatureMode":
        """Convert string to enum."""
        mapping = {
            SIGNATURE_MODE_LEGACY: cls.LEGACY,
            SIGNATURE_MODE_HYBRID: cls.HYBRID,
            SIGNATURE_MODE_PQC_ONLY: cls.PQC_ONLY,
        }
        if mode not in mapping:
            raise ValueError(f"Unknown signature mode: {mode}")
        return mapping[mode]
    
    def to_string(self) -> str:
        """Convert enum to string."""
        mapping = {
            self.LEGACY: SIGNATURE_MODE_LEGACY,
            self.HYBRID: SIGNATURE_MODE_HYBRID,
            self.PQC_ONLY: SIGNATURE_MODE_PQC_ONLY,
        }
        return mapping[self]
