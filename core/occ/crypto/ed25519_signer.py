"""
Ed25519 Signing Module for ProofPacks

Implements asymmetric cryptographic signing using Ed25519 (EdDSA).
Ed25519 is preferred for:
- Fast signing and verification
- Small signatures (64 bytes)
- Resistant to side-channel attacks
- Deterministic (no random nonce needed)

Security Properties:
- Non-repudiation: Only private key holder can create valid signatures
- Tamper detection: Any modification invalidates the signature
- Key rotation: Supports multiple key IDs for rotation

Environment Variables:
- PROOFPACK_SIGNING_KEY: Base64-encoded 32-byte private seed (required in production)
- PROOFPACK_KEY_ID: Key identifier for rotation (default: "pp-v1")

Usage:
    from core.occ.crypto import get_proofpack_signer, verify_signature

    # Sign
    signer = get_proofpack_signer()
    signature_bundle = signer.sign(manifest_hash_bytes)

    # Verify
    is_valid = verify_signature(
        message=manifest_hash_bytes,
        signature=signature_bundle.signature,
        public_key=signature_bundle.public_key,
    )
"""

import base64
import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

# Use PyNaCl for ed25519 (audited, well-maintained)
try:
    from nacl.encoding import RawEncoder
    from nacl.signing import SigningKey, VerifyKey

    # BadSignature location varies by version
    try:
        from nacl.exceptions import BadSignature
    except ImportError:
        from nacl.exceptions import CryptoError as BadSignature
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass(frozen=True)
class SignatureBundle:
    """
    Complete signature bundle for ProofPack integrity.

    Includes all data needed for independent verification:
    - signature: The ed25519 signature (64 bytes, base64-encoded)
    - public_key: The public key for verification (32 bytes, base64-encoded)
    - key_id: Human-readable key identifier for rotation
    - algorithm: Always "Ed25519" for this implementation
    - signed_at: ISO timestamp when signature was created
    """

    signature: str  # Base64-encoded 64-byte signature
    public_key: str  # Base64-encoded 32-byte public key
    key_id: str
    algorithm: str = "Ed25519"
    signed_at: str = ""

    def __post_init__(self):
        if not self.signed_at:
            object.__setattr__(self, "signed_at", datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "signature": self.signature,
            "public_key": self.public_key,
            "key_id": self.key_id,
            "algorithm": self.algorithm,
            "signed_at": self.signed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SignatureBundle":
        """Create from dictionary."""
        return cls(
            signature=data["signature"],
            public_key=data["public_key"],
            key_id=data["key_id"],
            algorithm=data.get("algorithm", "Ed25519"),
            signed_at=data.get("signed_at", ""),
        )


# =============================================================================
# ED25519 SIGNER
# =============================================================================


class Ed25519Signer:
    """
    Ed25519 signing key manager.

    Thread-safe, singleton-friendly implementation.
    In production, the private key should come from a secure source
    (HSM, Vault, AWS KMS, etc.).
    """

    def __init__(self, private_seed: bytes, key_id: str = "pp-v1"):
        """
        Initialize with a 32-byte private seed.

        Args:
            private_seed: 32-byte seed for key derivation
            key_id: Human-readable identifier for this key

        Raises:
            ImportError: If PyNaCl is not installed
            ValueError: If seed is not 32 bytes
        """
        if not NACL_AVAILABLE:
            raise ImportError("PyNaCl is required for ed25519 signing. " "Install with: pip install pynacl")

        if len(private_seed) != 32:
            raise ValueError(f"Private seed must be 32 bytes, got {len(private_seed)}")

        self._signing_key = SigningKey(private_seed)
        self._verify_key = self._signing_key.verify_key
        self._key_id = key_id

        # Cache the public key (safe to expose)
        self._public_key_b64 = base64.b64encode(self._verify_key.encode()).decode("ascii")

        logger.info(
            "Ed25519 signer initialized",
            extra={
                "key_id": key_id,
                "public_key_prefix": self._public_key_b64[:16] + "...",
            },
        )

    @property
    def key_id(self) -> str:
        """Return the key identifier."""
        return self._key_id

    @property
    def public_key_b64(self) -> str:
        """Return the base64-encoded public key (safe to share)."""
        return self._public_key_b64

    @property
    def public_key_bytes(self) -> bytes:
        """Return the raw 32-byte public key."""
        return self._verify_key.encode()

    def sign(self, message: bytes) -> SignatureBundle:
        """
        Sign a message and return a complete signature bundle.

        Args:
            message: The bytes to sign (typically the manifest hash)

        Returns:
            SignatureBundle with signature, public key, and metadata
        """
        # Sign the message
        signed = self._signing_key.sign(message, encoder=RawEncoder)
        signature_bytes = signed.signature  # 64 bytes

        # Encode for transport
        signature_b64 = base64.b64encode(signature_bytes).decode("ascii")

        return SignatureBundle(
            signature=signature_b64,
            public_key=self._public_key_b64,
            key_id=self._key_id,
            algorithm="Ed25519",
            signed_at=datetime.now(timezone.utc).isoformat(),
        )

    def sign_manifest_hash(self, manifest_hash_hex: str) -> SignatureBundle:
        """
        Convenience method to sign a hex-encoded hash.

        Args:
            manifest_hash_hex: SHA-256 hash as hex string

        Returns:
            SignatureBundle
        """
        # Convert hex hash to bytes for signing
        hash_bytes = bytes.fromhex(manifest_hash_hex)
        return self.sign(hash_bytes)

    def verify(self, message: bytes, signature_b64: str) -> bool:
        """
        Verify a signature against this signer's public key.

        Args:
            message: The original message bytes
            signature_b64: Base64-encoded signature

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            signature_bytes = base64.b64decode(signature_b64)
            self._verify_key.verify(message, signature_bytes)
            return True
        except (BadSignature, ValueError, Exception) as e:
            logger.warning(f"Signature verification failed: {e}")
            return False


# =============================================================================
# VERIFICATION FUNCTIONS
# =============================================================================


def verify_signature(
    message: bytes,
    signature_b64: str,
    public_key_b64: str,
) -> bool:
    """
    Verify an ed25519 signature with a public key.

    This function is stateless - it only needs the signature and public key,
    not the private key. Safe for external verification.

    Args:
        message: The original message bytes
        signature_b64: Base64-encoded 64-byte signature
        public_key_b64: Base64-encoded 32-byte public key

    Returns:
        True if signature is valid, False otherwise
    """
    if not NACL_AVAILABLE:
        logger.error("PyNaCl not available for verification")
        return False

    try:
        signature_bytes = base64.b64decode(signature_b64)
        public_key_bytes = base64.b64decode(public_key_b64)

        verify_key = VerifyKey(public_key_bytes)
        verify_key.verify(message, signature_bytes)
        return True

    except BadSignature:
        logger.warning("Signature verification failed: invalid signature")
        return False
    except ValueError as e:
        logger.warning(f"Signature verification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def verify_proofpack_signature(
    manifest_hash_hex: str,
    signature_bundle: SignatureBundle,
) -> Tuple[bool, str]:
    """
    Verify a ProofPack signature.

    Args:
        manifest_hash_hex: The SHA-256 manifest hash (hex string)
        signature_bundle: The complete signature bundle

    Returns:
        Tuple of (is_valid, message)
    """
    if signature_bundle.algorithm != "Ed25519":
        return False, f"Unsupported algorithm: {signature_bundle.algorithm}"

    hash_bytes = bytes.fromhex(manifest_hash_hex)

    is_valid = verify_signature(
        message=hash_bytes,
        signature_b64=signature_bundle.signature,
        public_key_b64=signature_bundle.public_key,
    )

    if is_valid:
        return True, "Signature verified successfully"
    else:
        return False, "Signature verification failed - ProofPack may have been tampered with"


# =============================================================================
# SINGLETON / FACTORY
# =============================================================================


_signer_instance: Optional[Ed25519Signer] = None


def get_proofpack_signer() -> Ed25519Signer:
    """
    Get the singleton ProofPack signer.

    Key is loaded from environment:
    - PROOFPACK_SIGNING_KEY: Base64-encoded 32-byte seed
    - PROOFPACK_KEY_ID: Key identifier (default: "pp-v1")

    In development, a deterministic dev key is used if env var is not set.

    Returns:
        Ed25519Signer instance

    Raises:
        ImportError: If PyNaCl is not installed
    """
    global _signer_instance

    if _signer_instance is not None:
        return _signer_instance

    key_id = os.environ.get("PROOFPACK_KEY_ID", "pp-v1")
    key_b64 = os.environ.get("PROOFPACK_SIGNING_KEY")

    if key_b64:
        # Production: use provided key
        try:
            private_seed = base64.b64decode(key_b64)
        except Exception as e:
            raise ValueError(f"Invalid PROOFPACK_SIGNING_KEY: {e}")

        logger.info("Using production ProofPack signing key")
    else:
        # Development: derive deterministic key from a seed phrase
        # WARNING: This is for development only!
        dev_seed_phrase = "chainbridge-proofpack-dev-key-do-not-use-in-production"
        private_seed = hashlib.sha256(dev_seed_phrase.encode()).digest()

        logger.warning("Using development ProofPack signing key - " "set PROOFPACK_SIGNING_KEY in production!")
        key_id = "pp-dev"

    _signer_instance = Ed25519Signer(private_seed, key_id)
    return _signer_instance


def reset_signer() -> None:
    """Reset the singleton signer (for testing)."""
    global _signer_instance
    _signer_instance = None


def generate_new_keypair() -> Tuple[str, str]:
    """
    Generate a new ed25519 keypair.

    Returns:
        Tuple of (private_seed_b64, public_key_b64)

    Use this to generate keys for production deployment:
        python -c "from core.occ.crypto.ed25519_signer import generate_new_keypair; print(generate_new_keypair())"
    """
    if not NACL_AVAILABLE:
        raise ImportError("PyNaCl is required")

    private_seed = secrets.token_bytes(32)
    signing_key = SigningKey(private_seed)
    public_key = signing_key.verify_key.encode()

    return (
        base64.b64encode(private_seed).decode("ascii"),
        base64.b64encode(public_key).decode("ascii"),
    )


# =============================================================================
# MODULE INFO
# =============================================================================


__all__ = [
    "Ed25519Signer",
    "SignatureBundle",
    "get_proofpack_signer",
    "verify_signature",
    "verify_proofpack_signature",
    "generate_new_keypair",
    "reset_signer",
    "NACL_AVAILABLE",
]
