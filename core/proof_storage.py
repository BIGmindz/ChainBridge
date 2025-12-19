"""
Proof Storage - Append-Only Persistence with Integrity Validation

PAC-DAN-PROOF-PERSISTENCE-01

DESIGN CHOICE: Option A - Append-Only JSONL Log

Rationale:
- Simplest implementation with proven reliability
- No external dependencies (no SQLite driver needed)
- Human-readable and inspectable
- Easy to backup and replicate
- fsync on write ensures durability

INVARIANTS:
- INV-001: Proofs are append-only (no UPDATE/DELETE)
- INV-002: Each proof has a content-addressable hash
- INV-003: Startup validation verifies all hashes
- INV-004: Corruption causes hard failure
- INV-005: Write operations use fsync for durability

Author: DAN (GID-07)
Date: 2025-12-19
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, TypedDict
from uuid import uuid4

logger = logging.getLogger(__name__)


class ProofIntegrityError(Exception):
    """Raised when proof integrity validation fails. Must crash startup."""
    pass


class ProofRecord(TypedDict):
    """Type definition for a proof record in the JSONL log."""
    proof_id: str
    content_hash: str
    timestamp: str
    proof_type: str
    payload: Dict[str, Any]
    sequence_number: int


# Default storage paths
DEFAULT_PROOF_LOG_PATH = "./data/proofs.jsonl"
DEFAULT_PROOF_MANIFEST_PATH = "./data/proofs_manifest.json"


def compute_content_hash(payload: Dict[str, Any]) -> str:
    """
    Compute deterministic SHA-256 hash of proof payload.
    
    Uses canonical JSON serialization for consistency.
    """
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,  # Handle UUIDs, datetimes, etc.
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_chain_hash(previous_hash: str, content_hash: str) -> str:
    """
    Compute chain hash linking to previous entry.
    
    This creates a hash chain making tampering detectable.
    """
    combined = f"{previous_hash}:{content_hash}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


class ProofStorageV1:
    """
    Append-only proof storage with integrity validation.
    
    Storage Format: JSONL (JSON Lines)
    - One proof per line
    - Each line is a complete JSON object
    - fsync on every write for durability
    - Lock-protected for concurrent access
    
    Manifest File: JSON
    - Total proof count
    - Last content hash
    - Last chain hash
    - Last validated timestamp
    
    Startup Behavior:
    - Loads all proofs
    - Recomputes all hashes
    - Verifies chain integrity
    - CRASHES if any mismatch (fail loud)
    
    Usage:
        store = ProofStorageV1()
        store.validate_on_startup()  # MUST be called before any operations
        store.append_proof(proof_type="execution", payload={...})
    """
    
    # Genesis hash for the first entry in the chain
    GENESIS_HASH = "0" * 64  # 64 zeros (SHA-256 length)
    
    def __init__(
        self,
        log_path: Optional[str] = None,
        manifest_path: Optional[str] = None,
    ):
        """
        Initialize proof storage.
        
        Args:
            log_path: Path to JSONL proof log. Defaults to
                      CHAINBRIDGE_PROOF_LOG_PATH env var or ./data/proofs.jsonl
            manifest_path: Path to manifest file. Defaults to
                           CHAINBRIDGE_PROOF_MANIFEST_PATH env var or ./data/proofs_manifest.json
        """
        self._log_path = Path(
            log_path or 
            os.environ.get("CHAINBRIDGE_PROOF_LOG_PATH", DEFAULT_PROOF_LOG_PATH)
        )
        self._manifest_path = Path(
            manifest_path or 
            os.environ.get("CHAINBRIDGE_PROOF_MANIFEST_PATH", DEFAULT_PROOF_MANIFEST_PATH)
        )
        
        # Runtime state
        self._proof_count: int = 0
        self._last_content_hash: str = self.GENESIS_HASH
        self._last_chain_hash: str = self.GENESIS_HASH
        self._validated: bool = False
        
        # Ensure directories exist
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ProofStorageV1 initialized: log={self._log_path}, manifest={self._manifest_path}")
    
    def validate_on_startup(self) -> Dict[str, Any]:
        """
        Validate proof integrity on startup.
        
        MUST be called before any write operations.
        
        Returns:
            Validation report with proof count and last hashes
            
        Raises:
            ProofIntegrityError: If validation fails (CRASHES startup)
        """
        logger.info("Starting proof integrity validation...")
        
        # If log file doesn't exist, this is a fresh start
        if not self._log_path.exists():
            logger.info("No existing proof log found. Starting fresh.")
            self._validated = True
            self._write_manifest()  # Write initial manifest
            return self._create_validation_report(validated_count=0, errors=[])
        
        errors: List[str] = []
        validated_count = 0
        previous_chain_hash = self.GENESIS_HASH
        
        try:
            with open(self._log_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue  # Skip empty lines
                    
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        errors.append(f"Line {line_num}: JSON parse error: {e}")
                        continue
                    
                    # Validate required fields
                    required_fields = ["proof_id", "content_hash", "payload", "sequence_number"]
                    missing = [f for f in required_fields if f not in record]
                    if missing:
                        errors.append(f"Line {line_num}: Missing fields: {missing}")
                        continue
                    
                    # Recompute content hash
                    computed_hash = compute_content_hash(record["payload"])
                    if computed_hash != record["content_hash"]:
                        errors.append(
                            f"Line {line_num}: Content hash mismatch! "
                            f"Stored={record['content_hash'][:16]}... "
                            f"Computed={computed_hash[:16]}..."
                        )
                        continue
                    
                    # Verify chain hash if present
                    if "chain_hash" in record:
                        expected_chain = compute_chain_hash(previous_chain_hash, computed_hash)
                        if expected_chain != record["chain_hash"]:
                            errors.append(
                                f"Line {line_num}: Chain hash mismatch! "
                                f"Stored={record['chain_hash'][:16]}... "
                                f"Computed={expected_chain[:16]}..."
                            )
                            continue
                        previous_chain_hash = record["chain_hash"]
                    else:
                        # Legacy record without chain hash - still validate content
                        previous_chain_hash = compute_chain_hash(previous_chain_hash, computed_hash)
                    
                    validated_count += 1
                    self._last_content_hash = record["content_hash"]
                    self._last_chain_hash = previous_chain_hash
        
        except Exception as e:
            raise ProofIntegrityError(f"Failed to read proof log: {e}") from e
        
        # FAIL LOUD on any errors
        if errors:
            error_summary = "\n".join(errors[:10])  # Show first 10 errors
            if len(errors) > 10:
                error_summary += f"\n... and {len(errors) - 10} more errors"
            
            logger.critical(f"PROOF INTEGRITY VALIDATION FAILED!\n{error_summary}")
            raise ProofIntegrityError(
                f"Proof log integrity check failed with {len(errors)} error(s). "
                f"First error: {errors[0]}"
            )
        
        self._proof_count = validated_count
        self._validated = True
        
        # Update manifest
        self._write_manifest()
        
        logger.info(
            f"Proof validation PASSED: count={validated_count}, "
            f"last_hash={self._last_content_hash[:16]}..."
        )
        
        return self._create_validation_report(validated_count=validated_count, errors=[])
    
    def append_proof(
        self,
        proof_type: str,
        payload: Dict[str, Any],
        proof_id: Optional[str] = None,
    ) -> ProofRecord:
        """
        Append a proof to the log (append-only).
        
        Args:
            proof_type: Type of proof (e.g., "execution", "artifact", "decision")
            payload: The proof payload (will be hashed)
            proof_id: Optional ID (auto-generated if not provided)
            
        Returns:
            The created ProofRecord
            
        Raises:
            RuntimeError: If validate_on_startup() wasn't called
            IOError: If write fails
        """
        if not self._validated:
            raise RuntimeError(
                "ProofStorageV1.validate_on_startup() must be called before any operations!"
            )
        
        # Generate proof record
        proof_id = proof_id or str(uuid4())
        content_hash = compute_content_hash(payload)
        chain_hash = compute_chain_hash(self._last_chain_hash, content_hash)
        sequence_number = self._proof_count + 1
        timestamp = datetime.now(timezone.utc).isoformat()
        
        record: ProofRecord = {
            "proof_id": proof_id,
            "content_hash": content_hash,
            "chain_hash": chain_hash,
            "timestamp": timestamp,
            "proof_type": proof_type,
            "payload": payload,
            "sequence_number": sequence_number,
        }
        
        # Append to log with fsync
        self._append_to_log(record)
        
        # Update state
        self._proof_count = sequence_number
        self._last_content_hash = content_hash
        self._last_chain_hash = chain_hash
        
        # Update manifest
        self._write_manifest()
        
        logger.info(
            f"Proof appended: id={proof_id}, type={proof_type}, "
            f"seq={sequence_number}, hash={content_hash[:16]}..."
        )
        
        return record
    
    def _append_to_log(self, record: ProofRecord) -> None:
        """
        Append record to JSONL log with fsync.
        
        Uses file locking for concurrent access safety.
        """
        line = json.dumps(record, separators=(",", ":"), default=str) + "\n"
        
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure durability
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Failed to append proof to log: {e}")
            raise IOError(f"Proof append failed: {e}") from e
    
    def _write_manifest(self) -> None:
        """
        Write manifest file with current state.
        
        Manifest is advisory - the JSONL log is the source of truth.
        """
        manifest = {
            "version": "1.0.0",
            "log_path": str(self._log_path),
            "proof_count": self._proof_count,
            "last_content_hash": self._last_content_hash,
            "last_chain_hash": self._last_chain_hash,
            "last_validated": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            with open(self._manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            # Manifest write failure is non-fatal (log is source of truth)
            logger.warning(f"Failed to write manifest: {e}")
    
    def _create_validation_report(
        self, validated_count: int, errors: List[str]
    ) -> Dict[str, Any]:
        """Create validation report for logging/handoff."""
        return {
            "status": "PASS" if not errors else "FAIL",
            "validated_count": validated_count,
            "last_content_hash": self._last_content_hash,
            "last_chain_hash": self._last_chain_hash,
            "error_count": len(errors),
            "errors": errors[:10],  # First 10 errors
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "log_path": str(self._log_path),
        }
    
    def iter_proofs(self) -> Iterator[ProofRecord]:
        """
        Iterate over all proofs in the log.
        
        Yields:
            ProofRecord for each valid entry
        """
        if not self._log_path.exists():
            return
        
        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
    
    def get_proof_count(self) -> int:
        """Get current proof count."""
        return self._proof_count
    
    def get_last_hash(self) -> str:
        """Get last content hash (for verification)."""
        return self._last_content_hash
    
    def get_chain_hash(self) -> str:
        """Get last chain hash (for verification)."""
        return self._last_chain_hash
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics for monitoring."""
        file_size = 0
        if self._log_path.exists():
            file_size = self._log_path.stat().st_size
        
        return {
            "log_path": str(self._log_path),
            "proof_count": self._proof_count,
            "file_size_bytes": file_size,
            "last_content_hash": self._last_content_hash[:16] + "..." if self._last_content_hash != self.GENESIS_HASH else "(empty)",
            "last_chain_hash": self._last_chain_hash[:16] + "..." if self._last_chain_hash != self.GENESIS_HASH else "(empty)",
            "validated": self._validated,
        }


# ============================================================================
# Singleton access pattern
# ============================================================================

_proof_storage_instance: Optional[ProofStorageV1] = None


def get_proof_storage() -> ProofStorageV1:
    """
    Get the singleton ProofStorageV1 instance.
    
    WARNING: validate_on_startup() must be called on the instance before use!
    """
    global _proof_storage_instance
    if _proof_storage_instance is None:
        _proof_storage_instance = ProofStorageV1()
    return _proof_storage_instance


def init_proof_storage() -> Dict[str, Any]:
    """
    Initialize and validate proof storage.
    
    Call this once during application startup.
    
    Returns:
        Validation report
        
    Raises:
        ProofIntegrityError: If validation fails
    """
    storage = get_proof_storage()
    return storage.validate_on_startup()
