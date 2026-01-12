#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      PQC CRYPTO BACKEND - BASE                               ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Abstract base class for pluggable PQC crypto backends.
Allows swapping dilithium-py → liboqs without code changes.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class BackendInfo:
    """Information about a crypto backend."""
    name: str
    version: str
    algorithm: str
    security_level: int
    constant_time: bool
    fips_compliant: bool


class PQCBackend(ABC):
    """
    Abstract base class for PQC cryptographic backends.
    
    Implementations must provide:
      - keygen(): Generate key pair
      - sign(): Sign message
      - verify(): Verify signature
    """
    
    @property
    @abstractmethod
    def info(self) -> BackendInfo:
        """Get backend information."""
        pass
    
    @property
    @abstractmethod
    def public_key_size(self) -> int:
        """Size of public key in bytes."""
        pass
    
    @property
    @abstractmethod
    def private_key_size(self) -> int:
        """Size of private key in bytes."""
        pass
    
    @property
    @abstractmethod
    def signature_size(self) -> int:
        """Size of signature in bytes."""
        pass
    
    @abstractmethod
    def keygen(self) -> Tuple[bytes, bytes]:
        """
        Generate a new key pair.
        
        Returns:
            Tuple of (public_key, private_key) as bytes
            
        Raises:
            KeyGenerationError: If key generation fails
        """
        pass
    
    @abstractmethod
    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """
        Sign a message with the private key.
        
        Args:
            private_key: Private key bytes
            message: Message to sign
            
        Returns:
            Signature bytes
            
        Raises:
            SignatureError: If signing fails
        """
        pass
    
    @abstractmethod
    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """
        Verify a signature against a public key and message.
        
        Args:
            public_key: Public key bytes
            message: Original message
            signature: Signature to verify
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def derive_public_key(self, private_key: bytes) -> Optional[bytes]:
        """
        Derive public key from private key (if supported).
        
        Args:
            private_key: Private key bytes
            
        Returns:
            Public key bytes, or None if not supported
        """
        return None


class ED25519Backend(ABC):
    """
    Abstract base class for ED25519 backend.
    
    Uses cryptography library by default.
    """
    
    @property
    @abstractmethod
    def info(self) -> BackendInfo:
        """Get backend information."""
        pass
    
    @property
    def public_key_size(self) -> int:
        """Size of public key in bytes."""
        return 32
    
    @property
    def private_key_size(self) -> int:
        """Size of private key in bytes."""
        return 32
    
    @property
    def signature_size(self) -> int:
        """Size of signature in bytes."""
        return 64
    
    @abstractmethod
    def keygen(self) -> Tuple[bytes, bytes]:
        """Generate ED25519 key pair."""
        pass
    
    @abstractmethod
    def sign(self, private_key: bytes, message: bytes) -> bytes:
        """Sign with ED25519."""
        pass
    
    @abstractmethod
    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify ED25519 signature."""
        pass


# Backend registry and factory functions
_ed25519_backend: Optional[ED25519Backend] = None
_pqc_backend: Optional[PQCBackend] = None


def get_ed25519_backend() -> ED25519Backend:
    """Get the default ED25519 backend (cryptography library)."""
    global _ed25519_backend
    if _ed25519_backend is None:
        from .ed25519 import CryptographyED25519Backend
        _ed25519_backend = CryptographyED25519Backend()
    return _ed25519_backend


def get_pqc_backend() -> PQCBackend:
    """Get the default PQC backend (dilithium-py ML-DSA-65)."""
    global _pqc_backend
    if _pqc_backend is None:
        from .dilithium_py import DilithiumPyBackend
        _pqc_backend = DilithiumPyBackend()
    return _pqc_backend


def set_ed25519_backend(backend: ED25519Backend) -> None:
    """Set a custom ED25519 backend."""
    global _ed25519_backend
    _ed25519_backend = backend


def set_pqc_backend(backend: PQCBackend) -> None:
    """Set a custom PQC backend."""
    global _pqc_backend
    _pqc_backend = backend
