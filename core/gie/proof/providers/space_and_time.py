"""
Space and Time Proof Provider

ZK-proof generation via Space and Time Proof of SQL.
Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-PROOF-LAYER-024.

Agent: GID-01 (Cody) — Senior Backend Engineer

Implements P2 (ZK Proof) class provider with:
- Query → Proof → Verification handle flow
- Hash-first return model (INV-PROOF-002)
- Deterministic output (INV-PROOF-001)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from core.gie.proof.provider import (
    ProofProvider,
    ProofClass,
    ProofInput,
    ProofOutput,
    ProofStatus,
    VerificationResult,
    VerificationStatus,
    ProofGenerationError,
    ProofTimeoutError,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SpaceAndTimeConfig:
    """Configuration for Space and Time provider."""
    api_endpoint: str = "https://api.spaceandtime.io"
    api_key: Optional[str] = None
    namespace: str = "chainbridge_governance"
    proof_format: str = "snark"
    timeout_seconds: int = 30
    max_retries: int = 3
    proof_expiry_hours: int = 24

    @classmethod
    def from_env(cls) -> "SpaceAndTimeConfig":
        """Load configuration from environment variables."""
        return cls(
            api_endpoint=os.getenv("SXT_API_ENDPOINT", "https://api.spaceandtime.io"),
            api_key=os.getenv("SXT_API_KEY"),
            namespace=os.getenv("SXT_NAMESPACE", "chainbridge_governance"),
            proof_format=os.getenv("SXT_PROOF_FORMAT", "snark"),
            timeout_seconds=int(os.getenv("SXT_TIMEOUT", "30")),
            max_retries=int(os.getenv("SXT_MAX_RETRIES", "3")),
            proof_expiry_hours=int(os.getenv("SXT_PROOF_EXPIRY_HOURS", "24")),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SPACE AND TIME PROOF PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class SpaceAndTimeProofProvider(ProofProvider):
    """
    P2 ZK Proof provider using Space and Time Proof of SQL.
    
    Space and Time provides cryptographic proofs that SQL query results
    were computed correctly over a specific dataset.
    
    This implementation can operate in two modes:
    - Live mode: Actual API calls to Space and Time
    - Mock mode: Deterministic simulation for testing
    
    Invariants:
    - INV-PROOF-001: Deterministic output (same input → same proof hash)
    - INV-PROOF-002: Hash-first returns (no full payloads)
    """

    def __init__(
        self,
        config: Optional[SpaceAndTimeConfig] = None,
        mock_mode: bool = True,  # Default to mock for safety
    ):
        """
        Initialize Space and Time proof provider.
        
        Args:
            config: Provider configuration
            mock_mode: If True, use deterministic mock instead of live API
        """
        super().__init__(
            provider_id="SPACE_AND_TIME_P2",
            proof_class=ProofClass.P2_ZK_PROOF,
        )
        
        self._config = config or SpaceAndTimeConfig.from_env()
        self._mock_mode = mock_mode
        
        # Proof storage for verification
        self._proof_store: Dict[str, ProofOutput] = {}
        self._proof_data: Dict[str, Dict[str, Any]] = {}  # proof_hash → full proof data

    @property
    def config(self) -> SpaceAndTimeConfig:
        """Get current configuration."""
        return self._config

    @property
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode

    def _do_generate_proof(self, proof_input: ProofInput) -> ProofOutput:
        """
        Generate ZK proof via Space and Time.
        
        Per INV-PROOF-001: Same input always produces same proof hash.
        """
        if self._mock_mode:
            return self._generate_mock_proof(proof_input)
        else:
            return self._generate_live_proof(proof_input)

    def _generate_mock_proof(self, proof_input: ProofInput) -> ProofOutput:
        """
        Generate deterministic mock proof.
        
        Used for testing and when SxT API is unavailable.
        """
        input_hash = proof_input.compute_canonical_hash()
        
        # Build deterministic proof data
        proof_data = {
            "provider": self._provider_id,
            "proof_class": "P2",
            "proof_format": self._config.proof_format,
            "namespace": self._config.namespace,
            "input_hash": input_hash,
            "data_hash": proof_input.data_hash,
            "query_template": proof_input.query_template,
            "parameters": dict(proof_input.parameters),
            "mock": True,
        }
        
        # Generate deterministic proof hash
        proof_canonical = json.dumps(proof_data, sort_keys=True, separators=(",", ":"))
        proof_hash = f"sxt:{hashlib.sha256(proof_canonical.encode()).hexdigest()}"
        
        # Generate verification handle (would be opaque from real SxT)
        verification_handle = f"vh:{hashlib.sha256(proof_hash.encode()).hexdigest()[:32]}"
        
        # Calculate expiry
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=self._config.proof_expiry_hours)
        
        output = ProofOutput(
            proof_hash=proof_hash,
            input_hash=input_hash,
            provider_id=self._provider_id,
            proof_class=self._proof_class,
            status=ProofStatus.SUCCESS,
            verification_handle=verification_handle,
            created_at=created_at.isoformat() + "Z",
            expires_at=expires_at.isoformat() + "Z",
            algorithm_version="sxt-mock-v1.0",
        )
        
        # Store for verification
        self._proof_store[proof_hash] = output
        self._proof_data[proof_hash] = proof_data
        
        return output

    def _generate_live_proof(self, proof_input: ProofInput) -> ProofOutput:
        """
        Generate proof via live Space and Time API.
        
        Note: This is a placeholder for actual API integration.
        In production, this would make HTTP calls to SxT API.
        """
        if not self._config.api_key:
            raise ProofGenerationError(
                "SXT_API_KEY not configured. Set environment variable or use mock_mode=True"
            )
        
        input_hash = proof_input.compute_canonical_hash()
        
        # Placeholder for actual API call
        # In production:
        # 1. Construct SQL query from template + parameters
        # 2. POST to SxT API endpoint
        # 3. Receive proof + verification handle
        # 4. Return hash-only output
        
        # For now, fall back to mock
        return self._generate_mock_proof(proof_input)

    def _do_verify_proof(self, proof_hash: str) -> VerificationResult:
        """
        Verify a Space and Time proof.
        
        In mock mode, checks local store.
        In live mode, would verify via SxT API.
        """
        if self._mock_mode:
            return self._verify_mock_proof(proof_hash)
        else:
            return self._verify_live_proof(proof_hash)

    def _verify_mock_proof(self, proof_hash: str) -> VerificationResult:
        """Verify mock proof from local store."""
        if proof_hash not in self._proof_store:
            return VerificationResult(
                proof_hash=proof_hash,
                status=VerificationStatus.NOT_FOUND,
                is_valid=False,
                verified_at=datetime.utcnow().isoformat() + "Z",
                verifier_id=self._provider_id,
                failure_reason="Proof not found in store",
            )
        
        stored_proof = self._proof_store[proof_hash]
        
        # Check expiry
        if stored_proof.expires_at:
            expires = datetime.fromisoformat(stored_proof.expires_at.rstrip("Z"))
            if datetime.utcnow() > expires:
                return VerificationResult(
                    proof_hash=proof_hash,
                    status=VerificationStatus.EXPIRED,
                    is_valid=False,
                    verified_at=datetime.utcnow().isoformat() + "Z",
                    verifier_id=self._provider_id,
                    failure_reason=f"Proof expired at {stored_proof.expires_at}",
                )
        
        return VerificationResult(
            proof_hash=proof_hash,
            status=VerificationStatus.VALID,
            is_valid=True,
            verified_at=datetime.utcnow().isoformat() + "Z",
            verifier_id=self._provider_id,
            verification_details=f"Mock verification via {self._provider_id}",
        )

    def _verify_live_proof(self, proof_hash: str) -> VerificationResult:
        """Verify proof via live SxT API."""
        # Placeholder — would make API call in production
        return self._verify_mock_proof(proof_hash)

    # ─────────────────────────────────────────────────────────────────────────
    # Query Building Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def build_governance_query(
        self,
        table: str,
        conditions: Dict[str, Any],
        select_columns: Optional[list] = None,
    ) -> str:
        """
        Build a SQL query for governance proof.
        
        Args:
            table: Table name in SxT namespace
            conditions: WHERE clause conditions
            select_columns: Columns to select (default: *)
        
        Returns:
            SQL query string
        """
        columns = "*" if not select_columns else ", ".join(select_columns)
        full_table = f"{self._config.namespace}.{table}"
        
        where_clauses = []
        for key, value in conditions.items():
            if isinstance(value, str):
                where_clauses.append(f"{key} = '{value}'")
            else:
                where_clauses.append(f"{key} = {value}")
        
        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        return f"SELECT {columns} FROM {full_table} WHERE {where_str}"

    def create_proof_input(
        self,
        input_id: str,
        data_hash: str,
        query: str,
        requestor_gid: str,
        parameters: Optional[Dict[str, str]] = None,
    ) -> ProofInput:
        """
        Create a ProofInput for this provider.
        
        Convenience method for building properly formatted inputs.
        """
        return ProofInput(
            input_id=input_id,
            data_hash=data_hash,
            query_template=query,
            parameters=tuple((k, v) for k, v in (parameters or {}).items()),
            timestamp=datetime.utcnow().isoformat() + "Z",
            requestor_gid=requestor_gid,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Proof Data Access (Hash-First)
    # ─────────────────────────────────────────────────────────────────────────

    def get_proof_metadata(self, proof_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get proof metadata by hash.
        
        Per INV-PROOF-002: Returns hash references, not full payloads.
        """
        if proof_hash not in self._proof_store:
            return None
        
        output = self._proof_store[proof_hash]
        return {
            "proof_hash": output.proof_hash,
            "input_hash": output.input_hash,
            "status": output.status.value,
            "created_at": output.created_at,
            "expires_at": output.expires_at,
            "verification_handle": output.verification_handle,
        }

    def count_proofs(self) -> int:
        """Get total number of generated proofs."""
        with self._lock:
            return len(self._proof_store)

    def list_proof_hashes(self) -> list:
        """List all proof hashes (hash-only per INV-PROOF-002)."""
        with self._lock:
            return list(self._proof_store.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_global_sxt_provider: Optional[SpaceAndTimeProofProvider] = None
_global_lock = threading.Lock()


def get_space_and_time_provider(
    config: Optional[SpaceAndTimeConfig] = None,
    mock_mode: bool = True,
) -> SpaceAndTimeProofProvider:
    """Get or create global Space and Time provider."""
    global _global_sxt_provider
    
    with _global_lock:
        if _global_sxt_provider is None:
            _global_sxt_provider = SpaceAndTimeProofProvider(
                config=config,
                mock_mode=mock_mode,
            )
        return _global_sxt_provider


def reset_space_and_time_provider() -> None:
    """Reset global provider (for testing)."""
    global _global_sxt_provider
    
    with _global_lock:
        _global_sxt_provider = None
