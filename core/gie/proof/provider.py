"""
GIE Proof Provider Interface

Abstract interface for proof generation backends.
Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-PROOF-LAYER-024.

Agent: GID-01 (Cody) — Senior Backend Engineer

Invariants:
- INV-PROOF-001: Deterministic output (same input → same hash)
- INV-PROOF-002: Hash-first returns (no full payloads)
- INV-PROOF-003: Provider isolation (failures don't propagate)
- INV-PROOF-004: Audit trail (all operations logged)
- INV-PROOF-005: No side effects beyond proof storage
"""

from __future__ import annotations

import hashlib
import json
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class ProofClass(Enum):
    """
    Classification of proof types.
    
    P0: Local hash — no external proof
    P1: Attestation — signed statement from trusted party
    P2: ZK Proof — zero-knowledge cryptographic proof
    P3: Blockchain Anchor — on-chain commitment
    """
    P0_LOCAL_HASH = "P0"
    P1_ATTESTATION = "P1"
    P2_ZK_PROOF = "P2"
    P3_BLOCKCHAIN = "P3"


class ProofStatus(Enum):
    """Status of a proof generation or verification."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"


class VerificationStatus(Enum):
    """Result of proof verification."""
    VALID = "VALID"
    INVALID = "INVALID"
    EXPIRED = "EXPIRED"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class ProofError(Exception):
    """Base exception for proof-related errors."""
    pass


class ProofGenerationError(ProofError):
    """Raised when proof generation fails."""
    pass


class ProofVerificationError(ProofError):
    """Raised when proof verification fails."""
    pass


class ProofTimeoutError(ProofError):
    """Raised when proof operation times out."""
    pass


class ProofDeterminismError(ProofError):
    """Raised when determinism invariant is violated (INV-PROOF-001)."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ProofInput:
    """
    Immutable input for proof generation.
    
    Per INV-PROOF-001: Identical inputs must produce identical outputs.
    """
    input_id: str
    data_hash: str  # SHA-256 of source data
    query_template: str  # Query or computation template
    parameters: Tuple[Tuple[str, str], ...]  # Immutable key-value pairs
    timestamp: str  # ISO 8601 UTC
    requestor_gid: str  # Agent GID requesting proof

    def compute_canonical_hash(self) -> str:
        """
        Compute deterministic hash of this input.
        
        Used to verify INV-PROOF-001 (determinism).
        """
        canonical = json.dumps({
            "input_id": self.input_id,
            "data_hash": self.data_hash,
            "query_template": self.query_template,
            "parameters": list(self.parameters),
            "timestamp": self.timestamp,
            "requestor_gid": self.requestor_gid,
        }, sort_keys=True, separators=(",", ":"))
        
        return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "input_id": self.input_id,
            "data_hash": self.data_hash,
            "query_template": self.query_template,
            "parameters": dict(self.parameters),
            "timestamp": self.timestamp,
            "requestor_gid": self.requestor_gid,
        }


@dataclass(frozen=True)
class ProofOutput:
    """
    Immutable output from proof generation.
    
    Per INV-PROOF-002: Contains hash references only, no full payloads.
    """
    proof_hash: str  # Primary identifier (hash of proof)
    input_hash: str  # Links to ProofInput
    provider_id: str  # Which provider generated this
    proof_class: ProofClass  # P0, P1, P2, or P3
    status: ProofStatus  # SUCCESS, FAILED, PENDING
    verification_handle: str  # Opaque handle for verification
    created_at: str  # ISO 8601 UTC
    expires_at: Optional[str] = None  # Optional expiration
    algorithm_version: str = "v1.0"  # For quantum migration
    error_message: Optional[str] = None  # If status is FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (hash-only per INV-PROOF-002)."""
        return {
            "proof_hash": self.proof_hash,
            "input_hash": self.input_hash,
            "provider_id": self.provider_id,
            "proof_class": self.proof_class.value,
            "status": self.status.value,
            "verification_handle": self.verification_handle,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "algorithm_version": self.algorithm_version,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class VerificationResult:
    """Result of proof verification."""
    proof_hash: str
    status: VerificationStatus
    is_valid: bool
    verified_at: str
    verifier_id: str
    failure_reason: Optional[str] = None
    verification_details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "proof_hash": self.proof_hash,
            "status": self.status.value,
            "is_valid": self.is_valid,
            "verified_at": self.verified_at,
            "verifier_id": self.verifier_id,
            "failure_reason": self.failure_reason,
            "verification_details": self.verification_details,
        }


@dataclass
class ProofAuditEntry:
    """
    Audit log entry for proof operations.
    
    Per INV-PROOF-004: All operations must be logged.
    """
    entry_id: str
    operation: str  # GENERATE, VERIFY
    input_hash: str
    output_hash: Optional[str]
    provider_id: str
    status: str
    timestamp: str
    duration_ms: float
    requestor_gid: str
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ABSTRACT PROVIDER INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class ProofProvider(ABC):
    """
    Abstract base class for proof providers.
    
    All providers MUST implement:
    - generate_proof(): Create cryptographic proof
    - verify_proof(): Verify existing proof
    - get_provider_id(): Return unique identifier
    
    Invariants enforced:
    - INV-PROOF-001: Deterministic output
    - INV-PROOF-003: Provider isolation (fail-closed)
    - INV-PROOF-004: Audit trail
    """

    def __init__(self, provider_id: str, proof_class: ProofClass):
        """Initialize base provider."""
        self._provider_id = provider_id
        self._proof_class = proof_class
        self._lock = threading.RLock()
        self._audit_log: List[ProofAuditEntry] = []
        self._entry_counter = 0

    @property
    def provider_id(self) -> str:
        """Get provider identifier."""
        return self._provider_id

    @property
    def proof_class(self) -> ProofClass:
        """Get proof classification."""
        return self._proof_class

    @abstractmethod
    def _do_generate_proof(self, proof_input: ProofInput) -> ProofOutput:
        """
        Internal proof generation — implement in subclass.
        
        MUST be deterministic (INV-PROOF-001).
        """
        pass

    @abstractmethod
    def _do_verify_proof(self, proof_hash: str) -> VerificationResult:
        """
        Internal proof verification — implement in subclass.
        """
        pass

    def generate_proof(self, proof_input: ProofInput) -> ProofOutput:
        """
        Generate proof with isolation and audit trail.
        
        Per INV-PROOF-003: Failures don't propagate.
        Per INV-PROOF-004: All operations logged.
        """
        start_time = datetime.utcnow()
        input_hash = proof_input.compute_canonical_hash()
        
        try:
            with self._lock:
                output = self._do_generate_proof(proof_input)
                
                # Log success
                self._log_operation(
                    operation="GENERATE",
                    input_hash=input_hash,
                    output_hash=output.proof_hash,
                    status=output.status.value,
                    start_time=start_time,
                    requestor_gid=proof_input.requestor_gid,
                )
                
                return output
                
        except Exception as e:
            # INV-PROOF-003: Fail-closed with error result
            error_output = ProofOutput(
                proof_hash=f"error:{input_hash}",
                input_hash=input_hash,
                provider_id=self._provider_id,
                proof_class=self._proof_class,
                status=ProofStatus.FAILED,
                verification_handle="",
                created_at=datetime.utcnow().isoformat() + "Z",
                error_message=str(e),
            )
            
            # Log failure
            self._log_operation(
                operation="GENERATE",
                input_hash=input_hash,
                output_hash=None,
                status="FAILED",
                start_time=start_time,
                requestor_gid=proof_input.requestor_gid,
                error=str(e),
            )
            
            return error_output

    def verify_proof(self, proof_hash: str) -> VerificationResult:
        """
        Verify proof with isolation and audit trail.
        
        Per INV-PROOF-003: Failures don't propagate.
        """
        start_time = datetime.utcnow()
        
        try:
            with self._lock:
                result = self._do_verify_proof(proof_hash)
                
                # Log verification
                self._log_operation(
                    operation="VERIFY",
                    input_hash=proof_hash,
                    output_hash=proof_hash,
                    status=result.status.value,
                    start_time=start_time,
                    requestor_gid="VERIFIER",
                )
                
                return result
                
        except Exception as e:
            # Fail-closed
            error_result = VerificationResult(
                proof_hash=proof_hash,
                status=VerificationStatus.ERROR,
                is_valid=False,
                verified_at=datetime.utcnow().isoformat() + "Z",
                verifier_id=self._provider_id,
                failure_reason=str(e),
            )
            
            self._log_operation(
                operation="VERIFY",
                input_hash=proof_hash,
                output_hash=None,
                status="ERROR",
                start_time=start_time,
                requestor_gid="VERIFIER",
                error=str(e),
            )
            
            return error_result

    def _log_operation(
        self,
        operation: str,
        input_hash: str,
        output_hash: Optional[str],
        status: str,
        start_time: datetime,
        requestor_gid: str,
        error: Optional[str] = None,
    ) -> None:
        """Log operation to audit trail (INV-PROOF-004)."""
        self._entry_counter += 1
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        entry = ProofAuditEntry(
            entry_id=f"AUDIT-{self._provider_id}-{self._entry_counter:06d}",
            operation=operation,
            input_hash=input_hash,
            output_hash=output_hash,
            provider_id=self._provider_id,
            status=status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            duration_ms=duration_ms,
            requestor_gid=requestor_gid,
            error=error,
        )
        
        self._audit_log.append(entry)

    def get_audit_log(self) -> List[ProofAuditEntry]:
        """Get audit log entries."""
        with self._lock:
            return list(self._audit_log)

    def get_provider_id(self) -> str:
        """Return provider identifier."""
        return self._provider_id


# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL HASH PROVIDER (P0 — FALLBACK)
# ═══════════════════════════════════════════════════════════════════════════════

class LocalHashProvider(ProofProvider):
    """
    P0 proof provider — local SHA-256 hashing.
    
    This is the fallback provider when external proofs are unavailable.
    Provides determinism guarantee but no external verification.
    """

    def __init__(self):
        """Initialize local hash provider."""
        super().__init__(
            provider_id="LOCAL_HASH_P0",
            proof_class=ProofClass.P0_LOCAL_HASH,
        )
        self._proof_store: Dict[str, ProofOutput] = {}

    def _do_generate_proof(self, proof_input: ProofInput) -> ProofOutput:
        """
        Generate P0 proof via SHA-256.
        
        DETERMINISTIC: Same input always produces same hash.
        """
        input_hash = proof_input.compute_canonical_hash()
        
        # Generate proof hash from input
        proof_data = json.dumps({
            "provider": self._provider_id,
            "input_hash": input_hash,
            "data_hash": proof_input.data_hash,
        }, sort_keys=True)
        
        proof_hash = f"sha256:{hashlib.sha256(proof_data.encode()).hexdigest()}"
        
        output = ProofOutput(
            proof_hash=proof_hash,
            input_hash=input_hash,
            provider_id=self._provider_id,
            proof_class=self._proof_class,
            status=ProofStatus.SUCCESS,
            verification_handle=proof_hash,  # Self-referential for P0
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        
        # Store for verification
        self._proof_store[proof_hash] = output
        
        return output

    def _do_verify_proof(self, proof_hash: str) -> VerificationResult:
        """Verify P0 proof by checking storage."""
        if proof_hash in self._proof_store:
            return VerificationResult(
                proof_hash=proof_hash,
                status=VerificationStatus.VALID,
                is_valid=True,
                verified_at=datetime.utcnow().isoformat() + "Z",
                verifier_id=self._provider_id,
            )
        else:
            return VerificationResult(
                proof_hash=proof_hash,
                status=VerificationStatus.NOT_FOUND,
                is_valid=False,
                verified_at=datetime.utcnow().isoformat() + "Z",
                verifier_id=self._provider_id,
                failure_reason="Proof not found in local store",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class ProofProviderRegistry:
    """
    Registry for managing proof providers.
    
    Supports fallback chain: Primary → Secondary → P0 Local
    """

    def __init__(self):
        """Initialize registry."""
        self._providers: Dict[str, ProofProvider] = {}
        self._primary_id: Optional[str] = None
        self._fallback_id: Optional[str] = None
        self._lock = threading.RLock()
        
        # Always register local hash as ultimate fallback
        local = LocalHashProvider()
        self.register(local)
        self._fallback_id = local.provider_id

    def register(self, provider: ProofProvider) -> None:
        """Register a provider."""
        with self._lock:
            self._providers[provider.provider_id] = provider

    def set_primary(self, provider_id: str) -> None:
        """Set the primary provider."""
        with self._lock:
            if provider_id not in self._providers:
                raise ValueError(f"Provider not registered: {provider_id}")
            self._primary_id = provider_id

    def get_primary(self) -> ProofProvider:
        """Get primary provider (or fallback)."""
        with self._lock:
            if self._primary_id and self._primary_id in self._providers:
                return self._providers[self._primary_id]
            if self._fallback_id:
                return self._providers[self._fallback_id]
            raise ProofError("No providers available")

    def get_provider(self, provider_id: str) -> Optional[ProofProvider]:
        """Get specific provider by ID."""
        with self._lock:
            return self._providers.get(provider_id)

    def list_providers(self) -> List[str]:
        """List all registered provider IDs."""
        with self._lock:
            return list(self._providers.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_global_registry: Optional[ProofProviderRegistry] = None
_global_lock = threading.Lock()


def get_proof_registry() -> ProofProviderRegistry:
    """Get or create global proof provider registry."""
    global _global_registry
    
    with _global_lock:
        if _global_registry is None:
            _global_registry = ProofProviderRegistry()
        return _global_registry


def reset_proof_registry() -> None:
    """Reset global registry (for testing)."""
    global _global_registry
    
    with _global_lock:
        _global_registry = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_proof(proof_input: ProofInput) -> ProofOutput:
    """Generate proof using primary provider."""
    registry = get_proof_registry()
    provider = registry.get_primary()
    return provider.generate_proof(proof_input)


def verify_proof(proof_hash: str, provider_id: Optional[str] = None) -> VerificationResult:
    """Verify proof using specified or primary provider."""
    registry = get_proof_registry()
    
    if provider_id:
        provider = registry.get_provider(provider_id)
        if not provider:
            raise ProofError(f"Provider not found: {provider_id}")
    else:
        provider = registry.get_primary()
    
    return provider.verify_proof(proof_hash)
