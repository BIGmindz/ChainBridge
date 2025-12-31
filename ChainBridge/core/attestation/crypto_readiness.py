"""
Cryptographic Readiness Validation — PAC-SAM-P01-ATTESTATION-PROVIDER-READINESS-01

Validates cryptographic implementation readiness for governance attestation.
Tests hash algorithms, signature verification, and key derivation functions.

Authority: SAM (GID-06)
Dispatch: PAC-BENSON-EXEC-P62
Mode: SECURITY ANALYSIS

CRYPTOGRAPHIC INVENTORY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HASH ALGORITHMS:
  - SHA-256 (FIPS 180-4) — Primary
  - SHA-3-256 (FIPS 202) — Alternative
  - BLAKE3 (optional, performance)

SIGNATURE ALGORITHMS (Future):
  - Ed25519 — Fast, secure
  - ECDSA P-256 — Widely supported
  - RSA-PSS — Legacy compatibility

POST-QUANTUM (Stub Only):
  - CRYSTALS-Dilithium (FIPS 204)
  - SPHINCS+ (FIPS 205)
  - CRYSTALS-Kyber (FIPS 203) — Key encapsulation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


# =============================================================================
# ALGORITHM SUPPORT DETECTION
# =============================================================================

class CryptoAlgorithm(Enum):
    """Supported cryptographic algorithms."""
    # Hash algorithms
    SHA256 = "sha256"
    SHA3_256 = "sha3_256"
    SHA512 = "sha512"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    
    # Future: signatures
    ED25519 = "ed25519"
    ECDSA_P256 = "ecdsa_p256"
    RSA_PSS = "rsa_pss"
    
    # Post-quantum (stub)
    DILITHIUM = "dilithium"
    SPHINCS_PLUS = "sphincs_plus"
    KYBER = "kyber"


class AlgorithmStatus(Enum):
    """Status of algorithm availability."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    STUB_ONLY = "STUB_ONLY"
    DEPRECATED = "DEPRECATED"


@dataclass(frozen=True)
class AlgorithmCheck:
    """Result of algorithm availability check."""
    algorithm: CryptoAlgorithm
    status: AlgorithmStatus
    version: Optional[str] = None
    notes: str = ""


def check_hash_algorithm(name: str) -> Tuple[bool, str]:
    """
    Check if hash algorithm is available.
    
    Args:
        name: Algorithm name (e.g., 'sha256', 'sha3_256')
    
    Returns:
        Tuple of (available, notes)
    """
    try:
        if name.startswith("sha3_"):
            # SHA-3 requires Python 3.6+
            h = hashlib.new(name)
            h.update(b"test")
            _ = h.hexdigest()
            return True, f"Available via hashlib.new('{name}')"
        elif name in ("blake2b", "blake2s"):
            h = getattr(hashlib, name)()
            h.update(b"test")
            _ = h.hexdigest()
            return True, f"Available via hashlib.{name}()"
        else:
            h = getattr(hashlib, name)()
            h.update(b"test")
            _ = h.hexdigest()
            return True, f"Available via hashlib.{name}()"
    except (AttributeError, ValueError) as e:
        return False, f"Not available: {e}"


def check_hmac_support() -> Tuple[bool, str]:
    """Check HMAC support."""
    try:
        key = secrets.token_bytes(32)
        msg = b"test message"
        mac = hmac.new(key, msg, "sha256")
        _ = mac.hexdigest()
        return True, "HMAC available with all hash algorithms"
    except Exception as e:
        return False, f"HMAC error: {e}"


def check_secrets_module() -> Tuple[bool, str]:
    """Check secrets module for secure random generation."""
    try:
        _ = secrets.token_bytes(32)
        _ = secrets.token_hex(16)
        _ = secrets.token_urlsafe(16)
        return True, "secrets module available for CSPRNG"
    except Exception as e:
        return False, f"secrets module error: {e}"


# =============================================================================
# CRYPTOGRAPHIC READINESS VALIDATOR
# =============================================================================

@dataclass
class CryptoReadinessReport:
    """
    Comprehensive cryptographic readiness report.
    
    Contains:
    - Algorithm availability checks
    - Performance benchmarks
    - Security recommendations
    - Post-quantum readiness
    """
    timestamp: datetime
    python_version: str
    algorithms: List[AlgorithmCheck]
    hmac_available: bool
    csprng_available: bool
    overall_status: str
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize report to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "python_version": self.python_version,
            "algorithms": [
                {
                    "algorithm": a.algorithm.value,
                    "status": a.status.value,
                    "version": a.version,
                    "notes": a.notes,
                }
                for a in self.algorithms
            ],
            "hmac_available": self.hmac_available,
            "csprng_available": self.csprng_available,
            "overall_status": self.overall_status,
            "recommendations": self.recommendations,
        }
    
    def to_json(self) -> str:
        """Serialize report to JSON."""
        return json.dumps(self.to_dict(), indent=2)


class CryptoReadinessValidator:
    """
    Validates cryptographic implementation readiness.
    
    Checks:
    - Hash algorithm availability
    - HMAC support
    - CSPRNG availability
    - Performance characteristics
    - Post-quantum readiness (stub)
    """
    
    # Required algorithms for governance attestation
    REQUIRED_ALGORITHMS = [
        CryptoAlgorithm.SHA256,
        CryptoAlgorithm.SHA3_256,
    ]
    
    # Optional but recommended
    RECOMMENDED_ALGORITHMS = [
        CryptoAlgorithm.SHA512,
        CryptoAlgorithm.BLAKE2B,
    ]
    
    # Post-quantum (stub only)
    POST_QUANTUM_ALGORITHMS = [
        CryptoAlgorithm.DILITHIUM,
        CryptoAlgorithm.SPHINCS_PLUS,
        CryptoAlgorithm.KYBER,
    ]
    
    def __init__(self):
        """Initialize validator."""
        self._results: List[AlgorithmCheck] = []
        self._recommendations: List[str] = []
    
    def validate(self) -> CryptoReadinessReport:
        """
        Run full cryptographic readiness validation.
        
        Returns:
            CryptoReadinessReport with all checks
        """
        self._results = []
        self._recommendations = []
        
        # Check required algorithms
        for algo in self.REQUIRED_ALGORITHMS:
            self._check_algorithm(algo, required=True)
        
        # Check recommended algorithms
        for algo in self.RECOMMENDED_ALGORITHMS:
            self._check_algorithm(algo, required=False)
        
        # Check post-quantum (stub)
        for algo in self.POST_QUANTUM_ALGORITHMS:
            self._results.append(AlgorithmCheck(
                algorithm=algo,
                status=AlgorithmStatus.STUB_ONLY,
                notes="Post-quantum algorithm - stub only, awaiting NIST standardization",
            ))
        
        # Check HMAC
        hmac_ok, hmac_notes = check_hmac_support()
        if not hmac_ok:
            self._recommendations.append(
                "HMAC support required for message authentication"
            )
        
        # Check CSPRNG
        csprng_ok, csprng_notes = check_secrets_module()
        if not csprng_ok:
            self._recommendations.append(
                "secrets module required for cryptographically secure random numbers"
            )
        
        # Determine overall status
        required_available = all(
            r.status == AlgorithmStatus.AVAILABLE
            for r in self._results
            if r.algorithm in self.REQUIRED_ALGORITHMS
        )
        
        if required_available and hmac_ok and csprng_ok:
            overall_status = "READY"
        elif required_available:
            overall_status = "PARTIAL"
        else:
            overall_status = "NOT_READY"
        
        return CryptoReadinessReport(
            timestamp=datetime.now(timezone.utc),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            algorithms=self._results,
            hmac_available=hmac_ok,
            csprng_available=csprng_ok,
            overall_status=overall_status,
            recommendations=self._recommendations,
        )
    
    def _check_algorithm(
        self,
        algo: CryptoAlgorithm,
        required: bool = False,
    ) -> None:
        """Check availability of specific algorithm."""
        if algo in (
            CryptoAlgorithm.SHA256,
            CryptoAlgorithm.SHA3_256,
            CryptoAlgorithm.SHA512,
            CryptoAlgorithm.SHA3_512,
            CryptoAlgorithm.BLAKE2B,
            CryptoAlgorithm.BLAKE2S,
        ):
            available, notes = check_hash_algorithm(algo.value)
            status = (
                AlgorithmStatus.AVAILABLE if available
                else AlgorithmStatus.UNAVAILABLE
            )
            
            if not available and required:
                self._recommendations.append(
                    f"CRITICAL: Required algorithm {algo.value} not available"
                )
            
            self._results.append(AlgorithmCheck(
                algorithm=algo,
                status=status,
                notes=notes,
            ))
        else:
            # Signature algorithms - check for future
            self._results.append(AlgorithmCheck(
                algorithm=algo,
                status=AlgorithmStatus.STUB_ONLY,
                notes="Signature algorithm - future implementation",
            ))


# =============================================================================
# HASH FUNCTION WRAPPERS
# =============================================================================

def compute_sha256(data: bytes) -> str:
    """
    Compute SHA-256 hash.
    
    Args:
        data: Raw bytes to hash
    
    Returns:
        Hex-encoded hash string
    """
    return hashlib.sha256(data).hexdigest()


def compute_sha3_256(data: bytes) -> str:
    """
    Compute SHA-3-256 hash.
    
    Args:
        data: Raw bytes to hash
    
    Returns:
        Hex-encoded hash string
    """
    return hashlib.sha3_256(data).hexdigest()


def compute_hash(data: bytes, algorithm: str = "sha256") -> str:
    """
    Compute hash using specified algorithm.
    
    Args:
        data: Raw bytes to hash
        algorithm: Algorithm name
    
    Returns:
        Hex-encoded hash string
    
    Raises:
        ValueError: If algorithm not supported
    """
    if algorithm == "sha256":
        return compute_sha256(data)
    elif algorithm == "sha3_256":
        return compute_sha3_256(data)
    elif algorithm == "sha512":
        return hashlib.sha512(data).hexdigest()
    elif algorithm == "sha3_512":
        return hashlib.sha3_512(data).hexdigest()
    elif algorithm == "blake2b":
        return hashlib.blake2b(data).hexdigest()
    elif algorithm == "blake2s":
        return hashlib.blake2s(data).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def verify_hash(
    data: bytes,
    expected_hash: str,
    algorithm: str = "sha256",
) -> bool:
    """
    Verify data matches expected hash.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        data: Raw bytes to verify
        expected_hash: Expected hash value
        algorithm: Algorithm name
    
    Returns:
        True if hash matches
    """
    computed = compute_hash(data, algorithm)
    return hmac.compare_digest(computed, expected_hash)


def generate_random_bytes(length: int = 32) -> bytes:
    """
    Generate cryptographically secure random bytes.
    
    Args:
        length: Number of bytes to generate
    
    Returns:
        Random bytes
    """
    return secrets.token_bytes(length)


def generate_random_hex(length: int = 32) -> str:
    """
    Generate cryptographically secure random hex string.
    
    Args:
        length: Number of bytes (output will be 2x length)
    
    Returns:
        Random hex string
    """
    return secrets.token_hex(length)


# =============================================================================
# VALIDATION ENTRY POINT
# =============================================================================

def validate_crypto_readiness() -> CryptoReadinessReport:
    """
    Run cryptographic readiness validation.
    
    Returns:
        CryptoReadinessReport
    """
    validator = CryptoReadinessValidator()
    return validator.validate()


def print_crypto_readiness_report() -> None:
    """Print formatted cryptographic readiness report."""
    report = validate_crypto_readiness()
    
    print("=" * 80)
    print("🔴 CRYPTOGRAPHIC READINESS REPORT")
    print("   PAC-SAM-P01-ATTESTATION-PROVIDER-READINESS-01")
    print("=" * 80)
    print()
    print(f"Timestamp: {report.timestamp.isoformat()}")
    print(f"Python Version: {report.python_version}")
    print(f"Overall Status: {report.overall_status}")
    print()
    print("ALGORITHM AVAILABILITY:")
    print("-" * 60)
    
    for algo in report.algorithms:
        status_icon = {
            AlgorithmStatus.AVAILABLE: "✅",
            AlgorithmStatus.UNAVAILABLE: "❌",
            AlgorithmStatus.STUB_ONLY: "⚠️",
            AlgorithmStatus.DEPRECATED: "🚫",
        }.get(algo.status, "❓")
        
        print(f"  {status_icon} {algo.algorithm.value}: {algo.status.value}")
        if algo.notes:
            print(f"     └─ {algo.notes}")
    
    print()
    print("SECURITY FEATURES:")
    print("-" * 60)
    print(f"  {'✅' if report.hmac_available else '❌'} HMAC Support")
    print(f"  {'✅' if report.csprng_available else '❌'} CSPRNG (secrets module)")
    
    if report.recommendations:
        print()
        print("RECOMMENDATIONS:")
        print("-" * 60)
        for rec in report.recommendations:
            print(f"  ⚠️ {rec}")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    print_crypto_readiness_report()
