"""
Attestation Provider Protocol — PAC-SAM-P01-ATTESTATION-PROVIDER-READINESS-01

Defines the abstract interface for attestation providers supporting:
- Off-chain (file-based, database)
- On-chain (blockchain anchoring)
- Hybrid (off-chain with periodic on-chain anchoring)

Authority: SAM (GID-06)
Dispatch: PAC-BENSON-EXEC-P62
Mode: SECURITY ANALYSIS

THREAT MODEL CONTROLS:
- ATT-001: All attestations MUST include content hash
- ATT-002: All attestations MUST include timestamp
- ATT-003: Provider MUST verify hash before anchoring
- ATT-004: Provider MUST fail-closed on verification failure
- ATT-005: Chain integrity MUST be verifiable

CRYPTOGRAPHIC REQUIREMENTS:
- Primary: SHA-256 (FIPS 180-4)
- Alternative: SHA-3-256 (FIPS 202)
- Quantum-safe: CRYSTALS-Dilithium (FIPS 204) - stub only
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import uuid4


class AttestationStatus(Enum):
    """Status of an attestation operation."""
    PENDING = "PENDING"
    ANCHORED = "ANCHORED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class AttestationError(Exception):
    """
    Raised when attestation operations fail.
    
    FAIL-CLOSED: Any attestation error MUST halt the operation.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


@dataclass(frozen=True)
class AttestationResult:
    """
    Immutable result of an attestation operation.
    
    Contains:
    - attestation_id: Unique identifier
    - artifact_hash: SHA-256 hash of attested content
    - status: Current attestation status
    - timestamp: When attestation was created
    - provider_type: Which provider created this
    - anchor_reference: External reference (tx hash, file path, etc.)
    - metadata: Additional context
    """
    attestation_id: str
    artifact_hash: str
    status: AttestationStatus
    timestamp: datetime
    provider_type: str
    anchor_reference: Optional[str] = None
    chain_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "attestation_id": self.attestation_id,
            "artifact_hash": self.artifact_hash,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "provider_type": self.provider_type,
            "anchor_reference": self.anchor_reference,
            "chain_hash": self.chain_hash,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttestationResult":
        """Deserialize from dictionary."""
        return cls(
            attestation_id=data["attestation_id"],
            artifact_hash=data["artifact_hash"],
            status=AttestationStatus(data["status"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            provider_type=data["provider_type"],
            anchor_reference=data.get("anchor_reference"),
            chain_hash=data.get("chain_hash"),
            metadata=data.get("metadata", {}),
        )


@runtime_checkable
class AttestationProvider(Protocol):
    """
    Protocol for attestation providers.
    
    All providers MUST implement:
    - attest(): Create attestation for artifact
    - verify(): Verify existing attestation
    - get_chain(): Retrieve attestation chain
    
    SECURITY INVARIANTS:
    - Implementations MUST be fail-closed
    - Implementations MUST NOT silently swallow errors
    - Implementations MUST verify hashes before anchoring
    """
    
    @property
    def provider_type(self) -> str:
        """Return the provider type identifier."""
        ...
    
    def attest(
        self,
        artifact_id: str,
        artifact_type: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AttestationResult:
        """
        Create attestation for an artifact.
        
        Args:
            artifact_id: Unique identifier for the artifact
            artifact_type: Type (PAC, BER, PDO, WRAP)
            content: Raw content to attest
            metadata: Additional context
        
        Returns:
            AttestationResult with anchoring details
        
        Raises:
            AttestationError: On any failure (fail-closed)
        """
        ...
    
    def verify(
        self,
        attestation_id: str,
        expected_hash: Optional[str] = None,
    ) -> AttestationResult:
        """
        Verify an existing attestation.
        
        Args:
            attestation_id: ID of attestation to verify
            expected_hash: Optional hash to verify against
        
        Returns:
            AttestationResult with verification status
        
        Raises:
            AttestationError: On verification failure
        """
        ...
    
    def get_chain(
        self,
        artifact_id: str,
        artifact_type: Optional[str] = None,
    ) -> List[AttestationResult]:
        """
        Get attestation chain for an artifact.
        
        Args:
            artifact_id: Artifact to get chain for
            artifact_type: Optional type filter
        
        Returns:
            List of attestations in chronological order
        """
        ...


class BaseAttestationProvider(ABC):
    """
    Base class for attestation providers with common utilities.
    
    Provides:
    - Hash computation (SHA-256, SHA-3)
    - Chain hash computation
    - Timestamp generation
    - ID generation
    """
    
    # Hash algorithm constants
    HASH_SHA256 = "sha256"
    HASH_SHA3_256 = "sha3_256"
    
    def __init__(
        self,
        hash_algorithm: str = HASH_SHA256,
        fail_closed: bool = True,
    ):
        """
        Initialize base provider.
        
        Args:
            hash_algorithm: Hash algorithm to use
            fail_closed: If True, raise on any error
        """
        if hash_algorithm not in (self.HASH_SHA256, self.HASH_SHA3_256):
            raise ValueError(f"Unsupported hash algorithm: {hash_algorithm}")
        
        self._hash_algorithm = hash_algorithm
        self._fail_closed = fail_closed
    
    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Return the provider type identifier."""
        pass
    
    def compute_hash(self, content: bytes) -> str:
        """
        Compute hash of content using configured algorithm.
        
        Args:
            content: Raw bytes to hash
        
        Returns:
            Hex-encoded hash string
        """
        if self._hash_algorithm == self.HASH_SHA256:
            return hashlib.sha256(content).hexdigest()
        elif self._hash_algorithm == self.HASH_SHA3_256:
            return hashlib.sha3_256(content).hexdigest()
        else:
            raise AttestationError(
                f"Unsupported algorithm: {self._hash_algorithm}",
                "ATT_ERR_001",
            )
    
    def compute_chain_hash(
        self,
        artifact_hash: str,
        previous_chain_hash: Optional[str] = None,
    ) -> str:
        """
        Compute chain hash linking to previous attestation.
        
        Args:
            artifact_hash: Current artifact hash
            previous_chain_hash: Previous chain hash (None for first)
        
        Returns:
            Chain hash linking current to previous
        """
        chain_input = f"{artifact_hash}:{previous_chain_hash or 'GENESIS'}"
        return self.compute_hash(chain_input.encode("utf-8"))
    
    def generate_attestation_id(self) -> str:
        """Generate unique attestation ID."""
        return f"ATT-{uuid4().hex[:16].upper()}"
    
    def get_timestamp(self) -> datetime:
        """Get current UTC timestamp."""
        return datetime.now(timezone.utc)
    
    def _fail(self, message: str, code: str, **details: Any) -> None:
        """
        Handle failure based on fail_closed setting.
        
        Args:
            message: Error message
            code: Error code
            details: Additional error details
        
        Raises:
            AttestationError: If fail_closed is True
        """
        if self._fail_closed:
            raise AttestationError(message, code, details)
    
    @abstractmethod
    def attest(
        self,
        artifact_id: str,
        artifact_type: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AttestationResult:
        """Create attestation for artifact."""
        pass
    
    @abstractmethod
    def verify(
        self,
        attestation_id: str,
        expected_hash: Optional[str] = None,
    ) -> AttestationResult:
        """Verify existing attestation."""
        pass
    
    @abstractmethod
    def get_chain(
        self,
        artifact_id: str,
        artifact_type: Optional[str] = None,
    ) -> List[AttestationResult]:
        """Get attestation chain for artifact."""
        pass


# =============================================================================
# CRYPTOGRAPHIC UTILITY FUNCTIONS
# =============================================================================

def compute_artifact_hash(
    artifact_type: str,
    artifact_id: str,
    content: bytes,
    algorithm: str = "sha256",
) -> str:
    """
    Compute canonical hash for a governance artifact.
    
    Uses deterministic encoding to ensure reproducible hashes.
    
    Args:
        artifact_type: PAC, BER, PDO, WRAP
        artifact_id: Unique artifact identifier
        content: Raw artifact content
        algorithm: Hash algorithm (sha256 or sha3_256)
    
    Returns:
        Hex-encoded hash string
    """
    # Create canonical header
    header = f"{artifact_type}:{artifact_id}:"
    
    # Combine header + content
    full_content = header.encode("utf-8") + content
    
    # Compute hash
    if algorithm == "sha256":
        return hashlib.sha256(full_content).hexdigest()
    elif algorithm == "sha3_256":
        return hashlib.sha3_256(full_content).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def verify_artifact_hash(
    artifact_type: str,
    artifact_id: str,
    content: bytes,
    expected_hash: str,
    algorithm: str = "sha256",
) -> bool:
    """
    Verify artifact hash matches expected value.
    
    SECURITY: Uses constant-time comparison to prevent timing attacks.
    
    Args:
        artifact_type: PAC, BER, PDO, WRAP
        artifact_id: Unique artifact identifier
        content: Raw artifact content
        expected_hash: Expected hash value
        algorithm: Hash algorithm
    
    Returns:
        True if hash matches, False otherwise
    """
    import hmac
    
    computed = compute_artifact_hash(
        artifact_type, artifact_id, content, algorithm
    )
    
    # Constant-time comparison
    return hmac.compare_digest(computed, expected_hash)
