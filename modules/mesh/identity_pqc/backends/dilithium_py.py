#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   PQC CRYPTO BACKEND - dilithium-py                          ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

ML-DSA-65 implementation using dilithium-py library.

Library: dilithium-py==1.4.0
License: MIT
Status: Pure Python (not constant-time)

WARNING: dilithium-py is intended for educational purposes and is NOT
constant-time. For production high-security deployments, consider liboqs.
"""

from typing import Tuple, Optional
import logging

from . import PQCBackend, BackendInfo
from ..constants import (
    MLDSA65_PUBLIC_KEY_SIZE,
    MLDSA65_PRIVATE_KEY_SIZE,
    MLDSA65_SIGNATURE_SIZE,
    MLDSA65_SECURITY_LEVEL,
)
from ..errors import (
    BackendNotAvailableError,
    BackendOperationError,
    KeyGenerationError,
    SignatureError,
)

logger = logging.getLogger(__name__)

# Try to import dilithium-py
try:
    from dilithium_py.ml_dsa import ML_DSA_65
    DILITHIUM_PY_AVAILABLE = True
except ImportError:
    DILITHIUM_PY_AVAILABLE = False
    ML_DSA_65 = None


class DilithiumPyBackend(PQCBackend):
    """
    ML-DSA-65 backend using dilithium-py library.
    
    Key Sizes (FIPS 204):
      - Public Key:  1952 bytes
      - Private Key: 4032 bytes
      - Signature:   3309 bytes
    
    Security Level: NIST Level 3 (~AES-192)
    """
    
    def __init__(self):
        """Initialize dilithium-py backend."""
        if not DILITHIUM_PY_AVAILABLE:
            raise BackendNotAvailableError(
                backend_name="dilithium-py",
                install_hint="pip install dilithium-py==1.4.0",
            )
        self._ml_dsa = ML_DSA_65
        logger.debug("DilithiumPyBackend initialized")
    
    @property
    def info(self) -> BackendInfo:
        """Get backend information."""
        return BackendInfo(
            name="dilithium-py",
            version="1.4.0",
            algorithm="ML-DSA-65",
            security_level=MLDSA65_SECURITY_LEVEL,
            constant_time=False,  # Pure Python, not constant-time
            fips_compliant=True,  # Implements FIPS 204
        )
    
    @property
    def public_key_size(self) -> int:
        """Size of public key in bytes."""
        return MLDSA65_PUBLIC_KEY_SIZE
    
    @property
    def private_key_size(self) -> int:
        """Size of private key in bytes."""
        return MLDSA65_PRIVATE_KEY_SIZE
    
    @property
    def signature_size(self) -> int:
        """Size of signature in bytes."""
        return MLDSA65_SIGNATURE_SIZE
    
    def keygen(self) -> Tuple[bytes, bytes]:
        """
        Generate ML-DSA-65 key pair.
        
        Returns:
            Tuple of (public_key, private_key) as bytes
            
        Raises:
            KeyGenerationError: If key generation fails
        """
        try:
            public_key, private_key = self._ml_dsa.keygen()
            
            # Validate key sizes
            if len(public_key) != MLDSA65_PUBLIC_KEY_SIZE:
                raise KeyGenerationError(
                    message=f"Public key size mismatch: {len(public_key)} != {MLDSA65_PUBLIC_KEY_SIZE}",
                    algorithm="ML-DSA-65",
                )
            if len(private_key) != MLDSA65_PRIVATE_KEY_SIZE:
                raise KeyGenerationError(
                    message=f"Private key size mismatch: {len(private_key)} != {MLDSA65_PRIVATE_KEY_SIZE}",
                    algorithm="ML-DSA-65",
                )
            
            logger.debug("Generated ML-DSA-65 key pair")
            return public_key, private_key
            
        except KeyGenerationError:
            raise
        except Exception as e:
            raise KeyGenerationError(
                message=f"ML-DSA-65 keygen failed: {e}",
                algorithm="ML-DSA-65",
            )
    
    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """
        Sign a message with ML-DSA-65.
        
        Args:
            private_key: ML-DSA-65 private key (4032 bytes)
            message: Message to sign
            
        Returns:
            Signature (3309 bytes)
            
        Raises:
            SignatureError: If signing fails
        """
        try:
            # Validate private key size
            if len(private_key) != MLDSA65_PRIVATE_KEY_SIZE:
                raise SignatureError(
                    message=f"Invalid private key size: {len(private_key)} != {MLDSA65_PRIVATE_KEY_SIZE}",
                    algorithm="ML-DSA-65",
                )
            
            signature = self._ml_dsa.sign(private_key, message)
            
            # Validate signature size
            if len(signature) != MLDSA65_SIGNATURE_SIZE:
                raise SignatureError(
                    message=f"Signature size mismatch: {len(signature)} != {MLDSA65_SIGNATURE_SIZE}",
                    algorithm="ML-DSA-65",
                )
            
            return signature
            
        except SignatureError:
            raise
        except Exception as e:
            raise SignatureError(
                message=f"ML-DSA-65 signing failed: {e}",
                algorithm="ML-DSA-65",
            )
    
    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """
        Verify ML-DSA-65 signature.
        
        Args:
            public_key: ML-DSA-65 public key (1952 bytes)
            message: Original message
            signature: Signature to verify (3309 bytes)
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate sizes
            if len(public_key) != MLDSA65_PUBLIC_KEY_SIZE:
                logger.warning(f"Invalid public key size: {len(public_key)}")
                return False
            if len(signature) != MLDSA65_SIGNATURE_SIZE:
                logger.warning(f"Invalid signature size: {len(signature)}")
                return False
            
            return self._ml_dsa.verify(public_key, message, signature)
            
        except Exception as e:
            logger.warning(f"ML-DSA-65 verify error: {e}")
            return False
    
    def derive_public_key(self, private_key: bytes) -> Optional[bytes]:
        """
        Derive public key from private key.
        
        Args:
            private_key: ML-DSA-65 private key
            
        Returns:
            Public key bytes, or None on error
        """
        try:
            if len(private_key) != MLDSA65_PRIVATE_KEY_SIZE:
                return None
            return self._ml_dsa.pk_from_sk(private_key)
        except Exception:
            return None


def get_mldsa65_backend() -> PQCBackend:
    """
    Get the ML-DSA-65 backend instance.
    
    Returns:
        DilithiumPyBackend instance
        
    Raises:
        BackendNotAvailableError: If dilithium-py is not installed
    """
    return DilithiumPyBackend()


def is_available() -> bool:
    """Check if dilithium-py backend is available."""
    return DILITHIUM_PY_AVAILABLE
