#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PQC CRYPTO BACKEND - ED25519                              ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

ED25519 backend using cryptography library.
Provides the classical crypto component of hybrid signatures.
"""

from typing import Tuple
import logging

from . import ED25519Backend, BackendInfo
from ..constants import (
    ED25519_PUBLIC_KEY_SIZE,
    ED25519_PRIVATE_KEY_SIZE,
    ED25519_SIGNATURE_SIZE,
)
from ..errors import (
    BackendNotAvailableError,
    KeyGenerationError,
    SignatureError,
)

logger = logging.getLogger(__name__)

# Try to import cryptography
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.exceptions import InvalidSignature
    from cryptography import __version__ as CRYPTOGRAPHY_VERSION
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    CRYPTOGRAPHY_VERSION = "0.0.0"
    Ed25519PrivateKey = None
    Ed25519PublicKey = None
    InvalidSignature = Exception


class CryptographyED25519Backend(ED25519Backend):
    """
    ED25519 backend using cryptography library.
    
    Key Sizes:
      - Public Key:  32 bytes
      - Private Key: 32 bytes (seed)
      - Signature:   64 bytes
    
    Security Level: ~128-bit classical security
    """
    
    def __init__(self):
        """Initialize cryptography ED25519 backend."""
        if not CRYPTOGRAPHY_AVAILABLE:
            raise BackendNotAvailableError(
                backend_name="cryptography",
                install_hint="pip install cryptography>=46.0.0",
            )
        logger.debug("CryptographyED25519Backend initialized")
    
    @property
    def info(self) -> BackendInfo:
        """Get backend information."""
        return BackendInfo(
            name="cryptography",
            version=CRYPTOGRAPHY_VERSION,
            algorithm="ED25519",
            security_level=1,  # NIST Level 1 equivalent
            constant_time=True,  # cryptography library is constant-time
            fips_compliant=True,
        )
    
    def keygen(self) -> Tuple[bytes, bytes]:
        """
        Generate ED25519 key pair.
        
        Returns:
            Tuple of (public_key, private_key) as bytes
            
        Raises:
            KeyGenerationError: If key generation fails
        """
        try:
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            
            logger.debug("Generated ED25519 key pair")
            return public_key_bytes, private_key_bytes
            
        except Exception as e:
            raise KeyGenerationError(
                message=f"ED25519 keygen failed: {e}",
                algorithm="ED25519",
            )
    
    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """
        Sign a message with ED25519.
        
        Args:
            private_key: ED25519 private key (32 bytes seed)
            message: Message to sign
            
        Returns:
            Signature (64 bytes)
            
        Raises:
            SignatureError: If signing fails
        """
        try:
            # Validate private key size
            if len(private_key) != ED25519_PRIVATE_KEY_SIZE:
                raise SignatureError(
                    message=f"Invalid private key size: {len(private_key)} != {ED25519_PRIVATE_KEY_SIZE}",
                    algorithm="ED25519",
                )
            
            key_obj = Ed25519PrivateKey.from_private_bytes(private_key)
            signature = key_obj.sign(message)
            
            return signature
            
        except SignatureError:
            raise
        except Exception as e:
            raise SignatureError(
                message=f"ED25519 signing failed: {e}",
                algorithm="ED25519",
            )
    
    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """
        Verify ED25519 signature.
        
        Args:
            public_key: ED25519 public key (32 bytes)
            message: Original message
            signature: Signature to verify (64 bytes)
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate sizes
            if len(public_key) != ED25519_PUBLIC_KEY_SIZE:
                logger.warning(f"Invalid public key size: {len(public_key)}")
                return False
            if len(signature) != ED25519_SIGNATURE_SIZE:
                logger.warning(f"Invalid signature size: {len(signature)}")
                return False
            
            key_obj = Ed25519PublicKey.from_public_bytes(public_key)
            key_obj.verify(signature, message)
            return True
            
        except InvalidSignature:
            return False
        except Exception as e:
            logger.warning(f"ED25519 verify error: {e}")
            return False


def get_ed25519_backend() -> ED25519Backend:
    """
    Get the ED25519 backend instance.
    
    Returns:
        CryptographyED25519Backend instance
        
    Raises:
        BackendNotAvailableError: If cryptography is not installed
    """
    return CryptographyED25519Backend()


def is_available() -> bool:
    """Check if cryptography ED25519 backend is available."""
    return CRYPTOGRAPHY_AVAILABLE
