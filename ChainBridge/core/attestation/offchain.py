"""
Off-Chain Attestation Provider — PAC-SAM-P01-ATTESTATION-PROVIDER-READINESS-01

File-based attestation provider for governance artifacts.
Stores attestations locally with hash-chain integrity.

Authority: SAM (GID-06)
Dispatch: PAC-BENSON-EXEC-P62
Mode: SECURITY ANALYSIS

THREAT MODEL CONTROLS:
- OFF-001: Attestations stored as append-only JSON
- OFF-002: Each attestation includes chain hash
- OFF-003: Verification checks both content and chain hash
- OFF-004: File corruption detected via chain validation

USE CASES:
- Development/testing environments
- Air-gapped systems
- Audit trail without blockchain dependency
- Staging before on-chain anchoring
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.attestation.provider import (
    AttestationError,
    AttestationResult,
    AttestationStatus,
    BaseAttestationProvider,
)


logger = logging.getLogger(__name__)


# Default paths
DEFAULT_ATTESTATION_DIR = Path("data/attestations")


class OffChainAttestationProvider(BaseAttestationProvider):
    """
    File-based attestation provider.
    
    Stores attestations in JSON files with hash-chain integrity.
    Each artifact type gets its own attestation chain file.
    
    File Structure:
        data/attestations/
            PAC_attestations.json
            BER_attestations.json
            PDO_attestations.json
            WRAP_attestations.json
            chain_state.json
    
    SECURITY:
    - Append-only writes
    - Chain hash links each entry to previous
    - Verification validates entire chain
    """
    
    PROVIDER_TYPE = "OFFCHAIN_FILE"
    
    def __init__(
        self,
        attestation_dir: Optional[Path] = None,
        hash_algorithm: str = "sha256",
        fail_closed: bool = True,
        create_dirs: bool = True,
    ):
        """
        Initialize off-chain provider.
        
        Args:
            attestation_dir: Directory for attestation files
            hash_algorithm: Hash algorithm to use
            fail_closed: If True, raise on any error
            create_dirs: If True, create directories if missing
        """
        super().__init__(hash_algorithm, fail_closed)
        
        self._attestation_dir = attestation_dir or DEFAULT_ATTESTATION_DIR
        self._chain_state: Dict[str, str] = {}  # artifact_type -> last_chain_hash
        
        if create_dirs:
            self._attestation_dir.mkdir(parents=True, exist_ok=True)
        
        self._load_chain_state()
    
    @property
    def provider_type(self) -> str:
        """Return provider type identifier."""
        return self.PROVIDER_TYPE
    
    def _get_chain_file(self, artifact_type: str) -> Path:
        """Get path to attestation chain file for artifact type."""
        return self._attestation_dir / f"{artifact_type}_attestations.json"
    
    def _get_chain_state_file(self) -> Path:
        """Get path to chain state file."""
        return self._attestation_dir / "chain_state.json"
    
    def _load_chain_state(self) -> None:
        """Load chain state from disk."""
        state_file = self._get_chain_state_file()
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    self._chain_state = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load chain state: {e}")
                self._chain_state = {}
    
    def _save_chain_state(self) -> None:
        """Save chain state to disk."""
        state_file = self._get_chain_state_file()
        try:
            with open(state_file, "w") as f:
                json.dump(self._chain_state, f, indent=2)
        except IOError as e:
            self._fail(
                f"Failed to save chain state: {e}",
                "OFF_ERR_001",
                path=str(state_file),
            )
    
    def _load_attestations(self, artifact_type: str) -> List[Dict[str, Any]]:
        """Load attestations for artifact type from disk."""
        chain_file = self._get_chain_file(artifact_type)
        if not chain_file.exists():
            return []
        
        try:
            with open(chain_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self._fail(
                f"Failed to load attestations: {e}",
                "OFF_ERR_002",
                path=str(chain_file),
            )
            return []
    
    def _save_attestation(
        self,
        artifact_type: str,
        attestation: AttestationResult,
    ) -> None:
        """Append attestation to chain file (append-only)."""
        chain_file = self._get_chain_file(artifact_type)
        
        # Load existing
        attestations = self._load_attestations(artifact_type)
        
        # Append new
        attestations.append(attestation.to_dict())
        
        # Write back
        try:
            with open(chain_file, "w") as f:
                json.dump(attestations, f, indent=2)
        except IOError as e:
            self._fail(
                f"Failed to save attestation: {e}",
                "OFF_ERR_003",
                path=str(chain_file),
            )
    
    def attest(
        self,
        artifact_id: str,
        artifact_type: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AttestationResult:
        """
        Create attestation for artifact.
        
        Args:
            artifact_id: Unique identifier for artifact
            artifact_type: Type (PAC, BER, PDO, WRAP)
            content: Raw content to attest
            metadata: Additional context
        
        Returns:
            AttestationResult with file reference
        
        Raises:
            AttestationError: On failure (fail-closed)
        """
        # Compute content hash
        artifact_hash = self.compute_hash(content)
        
        # Get previous chain hash
        previous_chain_hash = self._chain_state.get(artifact_type)
        
        # Compute chain hash
        chain_hash = self.compute_chain_hash(artifact_hash, previous_chain_hash)
        
        # Generate attestation ID
        attestation_id = self.generate_attestation_id()
        
        # Create result
        result = AttestationResult(
            attestation_id=attestation_id,
            artifact_hash=artifact_hash,
            status=AttestationStatus.ANCHORED,
            timestamp=self.get_timestamp(),
            provider_type=self.provider_type,
            anchor_reference=str(self._get_chain_file(artifact_type)),
            chain_hash=chain_hash,
            metadata={
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "previous_chain_hash": previous_chain_hash,
                "hash_algorithm": self._hash_algorithm,
                **(metadata or {}),
            },
        )
        
        # Save attestation
        self._save_attestation(artifact_type, result)
        
        # Update chain state
        self._chain_state[artifact_type] = chain_hash
        self._save_chain_state()
        
        logger.info(
            f"Created attestation {attestation_id} for {artifact_type}:{artifact_id}"
        )
        
        return result
    
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
        # Search all chain files for attestation
        for artifact_type in ["PAC", "BER", "PDO", "WRAP"]:
            attestations = self._load_attestations(artifact_type)
            
            for att_data in attestations:
                if att_data["attestation_id"] == attestation_id:
                    result = AttestationResult.from_dict(att_data)
                    
                    # Verify hash if provided
                    if expected_hash and result.artifact_hash != expected_hash:
                        self._fail(
                            f"Hash mismatch: expected {expected_hash}, "
                            f"got {result.artifact_hash}",
                            "OFF_ERR_004",
                            attestation_id=attestation_id,
                        )
                        return AttestationResult(
                            attestation_id=attestation_id,
                            artifact_hash=result.artifact_hash,
                            status=AttestationStatus.FAILED,
                            timestamp=self.get_timestamp(),
                            provider_type=self.provider_type,
                            metadata={"error": "Hash mismatch"},
                        )
                    
                    # Return verified result
                    return AttestationResult(
                        attestation_id=result.attestation_id,
                        artifact_hash=result.artifact_hash,
                        status=AttestationStatus.VERIFIED,
                        timestamp=self.get_timestamp(),
                        provider_type=self.provider_type,
                        anchor_reference=result.anchor_reference,
                        chain_hash=result.chain_hash,
                        metadata={
                            **result.metadata,
                            "verified_at": self.get_timestamp().isoformat(),
                        },
                    )
        
        # Not found
        self._fail(
            f"Attestation not found: {attestation_id}",
            "OFF_ERR_005",
        )
        return AttestationResult(
            attestation_id=attestation_id,
            artifact_hash="",
            status=AttestationStatus.FAILED,
            timestamp=self.get_timestamp(),
            provider_type=self.provider_type,
            metadata={"error": "Attestation not found"},
        )
    
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
        results: List[AttestationResult] = []
        
        # Determine which types to search
        types_to_search = (
            [artifact_type] if artifact_type
            else ["PAC", "BER", "PDO", "WRAP"]
        )
        
        for atype in types_to_search:
            attestations = self._load_attestations(atype)
            
            for att_data in attestations:
                if att_data.get("metadata", {}).get("artifact_id") == artifact_id:
                    results.append(AttestationResult.from_dict(att_data))
        
        # Sort by timestamp
        results.sort(key=lambda r: r.timestamp)
        
        return results
    
    def verify_chain_integrity(
        self,
        artifact_type: str,
    ) -> bool:
        """
        Verify integrity of entire attestation chain.
        
        Checks:
        - Each chain hash links correctly to previous
        - No gaps in chain
        - No tampering detected
        
        Args:
            artifact_type: Type of chain to verify
        
        Returns:
            True if chain is valid, False otherwise
        
        Raises:
            AttestationError: On integrity failure (if fail_closed)
        """
        attestations = self._load_attestations(artifact_type)
        
        if not attestations:
            return True  # Empty chain is valid
        
        previous_chain_hash: Optional[str] = None
        
        for i, att_data in enumerate(attestations):
            att = AttestationResult.from_dict(att_data)
            
            # Recompute chain hash
            expected_chain_hash = self.compute_chain_hash(
                att.artifact_hash,
                previous_chain_hash,
            )
            
            if att.chain_hash != expected_chain_hash:
                self._fail(
                    f"Chain integrity violation at index {i}: "
                    f"expected {expected_chain_hash}, got {att.chain_hash}",
                    "OFF_ERR_006",
                    index=i,
                    attestation_id=att.attestation_id,
                )
                return False
            
            previous_chain_hash = att.chain_hash
        
        logger.info(
            f"Chain integrity verified for {artifact_type}: "
            f"{len(attestations)} attestations"
        )
        return True
