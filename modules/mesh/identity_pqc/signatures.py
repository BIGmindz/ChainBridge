#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      HYBRID SIGNATURE MODULE                                 ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Hybrid ED25519 + ML-DSA-65 signature creation and verification.

A hybrid signature contains BOTH an ED25519 and ML-DSA-65 signature.
Verification requires BOTH signatures to be valid (AND logic).

Binary Format:
    [VERSION:1][ED25519_SIG:64][MLDSA65_SIG:3309]
    Total: 3374 bytes

This provides:
  - Classical security from ED25519
  - Quantum resistance from ML-DSA-65
  - Backward compatibility (can extract ED25519 component)
"""

import struct
from dataclasses import dataclass
from typing import Optional, Tuple
import logging

from .constants import (
    SignatureMode,
    FORMAT_VERSION,
    ED25519_SIGNATURE_SIZE,
    MLDSA65_SIGNATURE_SIZE,
    HYBRID_SIGNATURE_HEADER_SIZE,
    HYBRID_SIGNATURE_TOTAL_SIZE,
    SIGNATURE_MODE_HYBRID,
    SIGNATURE_MODE_LEGACY,
    SIGNATURE_MODE_PQC_ONLY,
)
from .errors import (
    SignatureError,
    SignatureMalformedError,
    SignatureModeError,
    VerificationError,
    InvalidSignatureError,
)

logger = logging.getLogger(__name__)


@dataclass
class HybridSignature:
    """
    Hybrid signature containing both ED25519 and ML-DSA-65 components.
    
    Attributes:
        ed25519_sig: ED25519 signature (64 bytes), or None for PQC_ONLY
        mldsa65_sig: ML-DSA-65 signature (3309 bytes), or None for LEGACY
        mode: Signature mode (LEGACY, HYBRID, or PQC_ONLY)
        version: Format version
    """
    
    ed25519_sig: Optional[bytes]
    mldsa65_sig: Optional[bytes]
    mode: SignatureMode = SignatureMode.HYBRID
    version: int = FORMAT_VERSION
    
    def __post_init__(self):
        """Validate signature components."""
        if self.mode == SignatureMode.HYBRID:
            if not self.ed25519_sig or not self.mldsa65_sig:
                raise SignatureError("Hybrid mode requires both signature components")
            if len(self.ed25519_sig) != ED25519_SIGNATURE_SIZE:
                raise SignatureMalformedError(ED25519_SIGNATURE_SIZE, len(self.ed25519_sig))
            if len(self.mldsa65_sig) != MLDSA65_SIGNATURE_SIZE:
                raise SignatureMalformedError(MLDSA65_SIGNATURE_SIZE, len(self.mldsa65_sig))
        elif self.mode == SignatureMode.LEGACY:
            if not self.ed25519_sig:
                raise SignatureError("Legacy mode requires ED25519 signature")
            if len(self.ed25519_sig) != ED25519_SIGNATURE_SIZE:
                raise SignatureMalformedError(ED25519_SIGNATURE_SIZE, len(self.ed25519_sig))
        elif self.mode == SignatureMode.PQC_ONLY:
            if not self.mldsa65_sig:
                raise SignatureError("PQC_ONLY mode requires ML-DSA-65 signature")
            if len(self.mldsa65_sig) != MLDSA65_SIGNATURE_SIZE:
                raise SignatureMalformedError(MLDSA65_SIGNATURE_SIZE, len(self.mldsa65_sig))
    
    def to_bytes(self) -> bytes:
        """
        Serialize signature to binary format.
        
        Format:
            HYBRID:   [0x01][ED25519:64][MLDSA65:3309] = 3374 bytes
            LEGACY:   [0x00][ED25519:64] = 65 bytes
            PQC_ONLY: [0x02][MLDSA65:3309] = 3310 bytes
        
        Returns:
            Serialized signature bytes
        """
        if self.mode == SignatureMode.HYBRID:
            # Version byte 0x01 = HYBRID
            header = struct.pack("B", 0x01)
            return header + self.ed25519_sig + self.mldsa65_sig
        elif self.mode == SignatureMode.LEGACY:
            # Version byte 0x00 = LEGACY
            header = struct.pack("B", 0x00)
            return header + self.ed25519_sig
        elif self.mode == SignatureMode.PQC_ONLY:
            # Version byte 0x02 = PQC_ONLY
            header = struct.pack("B", 0x02)
            return header + self.mldsa65_sig
        else:
            raise SignatureError(f"Unknown signature mode: {self.mode}")
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "HybridSignature":
        """
        Deserialize signature from binary format.
        
        Args:
            data: Serialized signature bytes
            
        Returns:
            HybridSignature instance
            
        Raises:
            SignatureMalformedError: If data format is invalid
        """
        if len(data) < 1:
            raise SignatureMalformedError(1, 0)
        
        version_byte = data[0]
        
        if version_byte == 0x00:
            # LEGACY mode
            expected_size = 1 + ED25519_SIGNATURE_SIZE
            if len(data) != expected_size:
                raise SignatureMalformedError(expected_size, len(data))
            return cls(
                ed25519_sig=data[1:1 + ED25519_SIGNATURE_SIZE],
                mldsa65_sig=None,
                mode=SignatureMode.LEGACY,
            )
        elif version_byte == 0x01:
            # HYBRID mode
            expected_size = HYBRID_SIGNATURE_TOTAL_SIZE
            if len(data) != expected_size:
                raise SignatureMalformedError(expected_size, len(data))
            ed_start = 1
            ed_end = ed_start + ED25519_SIGNATURE_SIZE
            ml_end = ed_end + MLDSA65_SIGNATURE_SIZE
            return cls(
                ed25519_sig=data[ed_start:ed_end],
                mldsa65_sig=data[ed_end:ml_end],
                mode=SignatureMode.HYBRID,
            )
        elif version_byte == 0x02:
            # PQC_ONLY mode
            expected_size = 1 + MLDSA65_SIGNATURE_SIZE
            if len(data) != expected_size:
                raise SignatureMalformedError(expected_size, len(data))
            return cls(
                ed25519_sig=None,
                mldsa65_sig=data[1:1 + MLDSA65_SIGNATURE_SIZE],
                mode=SignatureMode.PQC_ONLY,
            )
        else:
            raise SignatureMalformedError(
                expected_size=0,
                actual_size=len(data),
            )
    
    @property
    def size(self) -> int:
        """Get signature size in bytes."""
        return len(self.to_bytes())
    
    def extract_legacy(self) -> bytes:
        """
        Extract ED25519 signature for legacy verification.
        
        Returns:
            ED25519 signature bytes (64 bytes)
            
        Raises:
            SignatureModeError: If no ED25519 component
        """
        if self.ed25519_sig is None:
            raise SignatureModeError(
                expected=SIGNATURE_MODE_HYBRID,
                actual=SIGNATURE_MODE_PQC_ONLY,
            )
        return self.ed25519_sig
    
    def extract_pqc(self) -> bytes:
        """
        Extract ML-DSA-65 signature.
        
        Returns:
            ML-DSA-65 signature bytes (3309 bytes)
            
        Raises:
            SignatureModeError: If no ML-DSA-65 component
        """
        if self.mldsa65_sig is None:
            raise SignatureModeError(
                expected=SIGNATURE_MODE_HYBRID,
                actual=SIGNATURE_MODE_LEGACY,
            )
        return self.mldsa65_sig
    
    def __repr__(self) -> str:
        return f"HybridSignature(mode={self.mode.name}, size={self.size})"


class HybridSigner:
    """
    Creates hybrid signatures using both ED25519 and ML-DSA-65.
    """
    
    def __init__(
        self,
        ed25519_backend,
        pqc_backend,
        default_mode: SignatureMode = SignatureMode.HYBRID,
    ):
        """
        Initialize hybrid signer.
        
        Args:
            ed25519_backend: ED25519 backend instance
            pqc_backend: PQC (ML-DSA-65) backend instance
            default_mode: Default signature mode
        """
        self._ed25519 = ed25519_backend
        self._pqc = pqc_backend
        self._default_mode = default_mode
    
    def sign(
        self,
        ed25519_private_key: Optional[bytes],
        pqc_private_key: Optional[bytes],
        message: bytes,
        mode: Optional[SignatureMode] = None,
    ) -> HybridSignature:
        """
        Create a hybrid signature.
        
        Args:
            ed25519_private_key: ED25519 private key (32 bytes)
            pqc_private_key: ML-DSA-65 private key (4032 bytes)
            message: Message to sign
            mode: Signature mode (default: HYBRID)
            
        Returns:
            HybridSignature instance
            
        Raises:
            SignatureError: If signing fails
        """
        mode = mode or self._default_mode
        
        ed_sig = None
        ml_sig = None
        
        if mode in (SignatureMode.HYBRID, SignatureMode.LEGACY):
            if ed25519_private_key is None:
                raise SignatureError("ED25519 private key required for this mode")
            ed_sig = self._ed25519.sign(ed25519_private_key, message)
        
        if mode in (SignatureMode.HYBRID, SignatureMode.PQC_ONLY):
            if pqc_private_key is None:
                raise SignatureError("ML-DSA-65 private key required for this mode")
            ml_sig = self._pqc.sign(pqc_private_key, message)
        
        return HybridSignature(
            ed25519_sig=ed_sig,
            mldsa65_sig=ml_sig,
            mode=mode,
        )


class HybridVerifier:
    """
    Verifies hybrid signatures.
    
    For HYBRID mode, BOTH signatures must be valid (AND logic).
    """
    
    def __init__(
        self,
        ed25519_backend,
        pqc_backend,
        minimum_mode: SignatureMode = SignatureMode.HYBRID,
    ):
        """
        Initialize hybrid verifier.
        
        Args:
            ed25519_backend: ED25519 backend instance
            pqc_backend: PQC (ML-DSA-65) backend instance
            minimum_mode: Minimum acceptable signature mode
        """
        self._ed25519 = ed25519_backend
        self._pqc = pqc_backend
        self._minimum_mode = minimum_mode
    
    def verify(
        self,
        ed25519_public_key: Optional[bytes],
        pqc_public_key: Optional[bytes],
        message: bytes,
        signature: HybridSignature,
        enforce_minimum_mode: bool = True,
    ) -> bool:
        """
        Verify a hybrid signature.
        
        Args:
            ed25519_public_key: ED25519 public key (32 bytes)
            pqc_public_key: ML-DSA-65 public key (1952 bytes)
            message: Original message
            signature: HybridSignature to verify
            enforce_minimum_mode: Enforce minimum signature mode
            
        Returns:
            True if valid, False otherwise
        """
        # Check minimum mode enforcement
        if enforce_minimum_mode:
            if not self._meets_minimum_mode(signature.mode):
                logger.warning(
                    f"Signature mode {signature.mode.name} below minimum {self._minimum_mode.name}"
                )
                return False
        
        # Verify based on mode
        if signature.mode == SignatureMode.HYBRID:
            return self._verify_hybrid(
                ed25519_public_key, pqc_public_key, message, signature
            )
        elif signature.mode == SignatureMode.LEGACY:
            return self._verify_legacy(ed25519_public_key, message, signature)
        elif signature.mode == SignatureMode.PQC_ONLY:
            return self._verify_pqc_only(pqc_public_key, message, signature)
        else:
            logger.warning(f"Unknown signature mode: {signature.mode}")
            return False
    
    def _meets_minimum_mode(self, mode: SignatureMode) -> bool:
        """Check if mode meets minimum requirement."""
        mode_levels = {
            SignatureMode.LEGACY: 0,
            SignatureMode.HYBRID: 1,
            SignatureMode.PQC_ONLY: 1,  # PQC_ONLY is equal to HYBRID
        }
        return mode_levels.get(mode, 0) >= mode_levels.get(self._minimum_mode, 0)
    
    def _verify_hybrid(
        self,
        ed25519_pk: Optional[bytes],
        pqc_pk: Optional[bytes],
        message: bytes,
        signature: HybridSignature,
    ) -> bool:
        """Verify hybrid signature (BOTH must be valid)."""
        if ed25519_pk is None or pqc_pk is None:
            logger.warning("Both public keys required for hybrid verification")
            return False
        
        # Verify ED25519
        ed_valid = self._ed25519.verify(
            ed25519_pk, message, signature.ed25519_sig
        )
        if not ed_valid:
            logger.debug("ED25519 verification failed")
            return False
        
        # Verify ML-DSA-65
        ml_valid = self._pqc.verify(
            pqc_pk, message, signature.mldsa65_sig
        )
        if not ml_valid:
            logger.debug("ML-DSA-65 verification failed")
            return False
        
        return True
    
    def _verify_legacy(
        self,
        ed25519_pk: Optional[bytes],
        message: bytes,
        signature: HybridSignature,
    ) -> bool:
        """Verify legacy ED25519-only signature."""
        if ed25519_pk is None:
            logger.warning("ED25519 public key required for legacy verification")
            return False
        
        return self._ed25519.verify(ed25519_pk, message, signature.ed25519_sig)
    
    def _verify_pqc_only(
        self,
        pqc_pk: Optional[bytes],
        message: bytes,
        signature: HybridSignature,
    ) -> bool:
        """Verify PQC-only ML-DSA-65 signature."""
        if pqc_pk is None:
            logger.warning("ML-DSA-65 public key required for PQC verification")
            return False
        
        return self._pqc.verify(pqc_pk, message, signature.mldsa65_sig)
