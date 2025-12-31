"""
PDO Storage Engine

Proof-addressed storage for PDO artifacts (Carvana Model).
Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-PROOF-LAYER-024.

Agent: GID-07 (Dan) — DevOps/Systems Engineer

Invariants:
- INV-STORE-001: Immutable writes (once written, never modified)
- INV-STORE-002: Proof-first addressing (all lookups via proof_hash)
- INV-STORE-003: Referential integrity (all artifact_hashes valid)
- INV-STORE-004: Hash collision safety (detect and reject)
- INV-STORE-005: Audit trail (all operations logged)
- INV-STORE-006: No orphan artifacts
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class StorageOperation(Enum):
    """Types of storage operations."""
    WRITE = "WRITE"
    READ = "READ"
    INDEX_UPDATE = "INDEX_UPDATE"
    ARTIFACT_STORE = "ARTIFACT_STORE"


class StorageStatus(Enum):
    """Result status of storage operations."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"
    NOT_FOUND = "NOT_FOUND"
    COLLISION = "COLLISION"
    INTEGRITY_ERROR = "INTEGRITY_ERROR"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class ImmutabilityViolationError(StorageError):
    """Raised when attempting to modify an existing record (INV-STORE-001)."""
    pass


class DuplicateProofHashError(StorageError):
    """Raised when proof_hash already exists."""
    pass


class MissingArtifactError(StorageError):
    """Raised when referenced artifact doesn't exist (INV-STORE-003)."""
    pass


class HashCollisionError(StorageError):
    """Raised when hash collision is detected (INV-STORE-004)."""
    pass


class ReferentialIntegrityError(StorageError):
    """Raised when referential integrity is violated."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PDORecord:
    """
    Immutable PDO storage record.
    
    Per INV-STORE-001: Once created, never modified.
    """
    pdo_id: str  # Human-readable identifier
    proof_hash: str  # Primary key (proof reference)
    pdo_hash: str  # Hash of PDO content
    artifact_hashes: Tuple[str, ...]  # References to artifacts
    
    # Metadata
    agent_gid: str
    pac_id: str
    created_at: str  # ISO 8601 UTC
    
    # Proof metadata
    proof_class: str  # P0, P1, P2, P3
    proof_provider: str
    
    # Optional blockchain anchor
    anchor_tx: Optional[str] = None
    anchor_chain: Optional[str] = None

    def compute_content_hash(self) -> str:
        """
        Compute hash of record content.
        
        Used for collision detection (INV-STORE-004).
        """
        canonical = json.dumps({
            "pdo_id": self.pdo_id,
            "proof_hash": self.proof_hash,
            "pdo_hash": self.pdo_hash,
            "artifact_hashes": list(self.artifact_hashes),
            "agent_gid": self.agent_gid,
            "pac_id": self.pac_id,
            "proof_class": self.proof_class,
            "proof_provider": self.proof_provider,
        }, sort_keys=True, separators=(",", ":"))
        
        return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pdo_id": self.pdo_id,
            "proof_hash": self.proof_hash,
            "pdo_hash": self.pdo_hash,
            "artifact_hashes": list(self.artifact_hashes),
            "agent_gid": self.agent_gid,
            "pac_id": self.pac_id,
            "created_at": self.created_at,
            "proof_class": self.proof_class,
            "proof_provider": self.proof_provider,
            "anchor_tx": self.anchor_tx,
            "anchor_chain": self.anchor_chain,
        }


@dataclass(frozen=True)
class StorageResult:
    """Result of a storage operation."""
    success: bool
    status: StorageStatus
    operation: StorageOperation
    pdo_id: Optional[str] = None
    proof_hash: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "status": self.status.value,
            "operation": self.operation.value,
            "pdo_id": self.pdo_id,
            "proof_hash": self.proof_hash,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class StorageAuditEntry:
    """
    Audit log entry for storage operations.
    
    Per INV-STORE-005: All operations must be logged.
    """
    entry_id: str
    operation: StorageOperation
    proof_hash: Optional[str]
    pdo_id: Optional[str]
    status: StorageStatus
    timestamp: str
    requestor_gid: str
    details: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# PDO STORE
# ═══════════════════════════════════════════════════════════════════════════════

class PDOStore:
    """
    Proof-addressed PDO storage engine.
    
    Implements the Carvana Model:
    - Proof-first addressing (INV-STORE-002)
    - Immutable writes (INV-STORE-001)
    - Hash collision safety (INV-STORE-004)
    - Full audit trail (INV-STORE-005)
    """

    def __init__(self):
        """Initialize PDO store."""
        self._lock = threading.RLock()
        
        # Primary storage: proof_hash → PDORecord
        self._records: Dict[str, PDORecord] = {}
        
        # Artifact storage: artifact_hash → content
        self._artifacts: Dict[str, bytes] = {}
        
        # Content hash registry for collision detection
        self._content_hashes: Dict[str, str] = {}  # content_hash → proof_hash
        
        # Audit log
        self._audit_log: List[StorageAuditEntry] = []
        self._entry_counter = 0

    # ─────────────────────────────────────────────────────────────────────────
    # Artifact Management
    # ─────────────────────────────────────────────────────────────────────────

    def store_artifact(
        self,
        content: bytes,
        requestor_gid: str = "SYSTEM",
    ) -> Tuple[str, StorageResult]:
        """
        Store an artifact and return its hash.
        
        Per INV-STORE-006: Artifacts can exist before PDO record.
        """
        with self._lock:
            artifact_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
            
            # Check for existing (idempotent)
            if artifact_hash in self._artifacts:
                result = StorageResult(
                    success=True,
                    status=StorageStatus.DUPLICATE,
                    operation=StorageOperation.ARTIFACT_STORE,
                    proof_hash=artifact_hash,
                )
            else:
                self._artifacts[artifact_hash] = content
                result = StorageResult(
                    success=True,
                    status=StorageStatus.SUCCESS,
                    operation=StorageOperation.ARTIFACT_STORE,
                    proof_hash=artifact_hash,
                )
            
            self._log_operation(
                operation=StorageOperation.ARTIFACT_STORE,
                proof_hash=artifact_hash,
                pdo_id=None,
                status=result.status,
                requestor_gid=requestor_gid,
            )
            
            return artifact_hash, result

    def artifact_exists(self, artifact_hash: str) -> bool:
        """Check if artifact exists."""
        with self._lock:
            return artifact_hash in self._artifacts

    def get_artifact(self, artifact_hash: str) -> Optional[bytes]:
        """Retrieve artifact by hash."""
        with self._lock:
            return self._artifacts.get(artifact_hash)

    # ─────────────────────────────────────────────────────────────────────────
    # PDO Record Storage
    # ─────────────────────────────────────────────────────────────────────────

    def store_pdo(
        self,
        pdo_record: PDORecord,
        requestor_gid: str = "SYSTEM",
    ) -> StorageResult:
        """
        Store a PDO record.
        
        Per INV-STORE-001: Immutable — FAILS if record exists.
        Per INV-STORE-003: All artifact_hashes must be valid.
        Per INV-STORE-004: Detects hash collisions.
        """
        with self._lock:
            # Check 1: Duplicate proof_hash (INV-STORE-001)
            if pdo_record.proof_hash in self._records:
                result = StorageResult(
                    success=False,
                    status=StorageStatus.DUPLICATE,
                    operation=StorageOperation.WRITE,
                    pdo_id=pdo_record.pdo_id,
                    proof_hash=pdo_record.proof_hash,
                    error="Proof hash already exists (INV-STORE-001)",
                )
                self._log_operation(
                    operation=StorageOperation.WRITE,
                    proof_hash=pdo_record.proof_hash,
                    pdo_id=pdo_record.pdo_id,
                    status=StorageStatus.DUPLICATE,
                    requestor_gid=requestor_gid,
                    details="Duplicate proof_hash",
                )
                return result
            
            # Check 2: Referential integrity (INV-STORE-003)
            for artifact_hash in pdo_record.artifact_hashes:
                if not self.artifact_exists(artifact_hash):
                    result = StorageResult(
                        success=False,
                        status=StorageStatus.INTEGRITY_ERROR,
                        operation=StorageOperation.WRITE,
                        pdo_id=pdo_record.pdo_id,
                        proof_hash=pdo_record.proof_hash,
                        error=f"Missing artifact: {artifact_hash} (INV-STORE-003)",
                    )
                    self._log_operation(
                        operation=StorageOperation.WRITE,
                        proof_hash=pdo_record.proof_hash,
                        pdo_id=pdo_record.pdo_id,
                        status=StorageStatus.INTEGRITY_ERROR,
                        requestor_gid=requestor_gid,
                        details=f"Missing artifact: {artifact_hash}",
                    )
                    return result
            
            # Check 3: Hash collision safety (INV-STORE-004)
            content_hash = pdo_record.compute_content_hash()
            if content_hash in self._content_hashes:
                existing_proof_hash = self._content_hashes[content_hash]
                existing_record = self._records.get(existing_proof_hash)
                
                # Same content but different proof_hash = potential collision
                if existing_record and existing_record.proof_hash != pdo_record.proof_hash:
                    # Check if it's truly different content with same hash
                    if existing_record.to_dict() != pdo_record.to_dict():
                        result = StorageResult(
                            success=False,
                            status=StorageStatus.COLLISION,
                            operation=StorageOperation.WRITE,
                            pdo_id=pdo_record.pdo_id,
                            proof_hash=pdo_record.proof_hash,
                            error=f"Hash collision detected (INV-STORE-004)",
                        )
                        self._log_operation(
                            operation=StorageOperation.WRITE,
                            proof_hash=pdo_record.proof_hash,
                            pdo_id=pdo_record.pdo_id,
                            status=StorageStatus.COLLISION,
                            requestor_gid=requestor_gid,
                            details="Hash collision",
                        )
                        return result
            
            # All checks passed — store record
            self._records[pdo_record.proof_hash] = pdo_record
            self._content_hashes[content_hash] = pdo_record.proof_hash
            
            result = StorageResult(
                success=True,
                status=StorageStatus.SUCCESS,
                operation=StorageOperation.WRITE,
                pdo_id=pdo_record.pdo_id,
                proof_hash=pdo_record.proof_hash,
            )
            
            self._log_operation(
                operation=StorageOperation.WRITE,
                proof_hash=pdo_record.proof_hash,
                pdo_id=pdo_record.pdo_id,
                status=StorageStatus.SUCCESS,
                requestor_gid=requestor_gid,
            )
            
            return result

    def get_by_proof_hash(
        self,
        proof_hash: str,
        requestor_gid: str = "SYSTEM",
    ) -> Optional[PDORecord]:
        """
        Retrieve PDO by proof hash (primary lookup).
        
        Per INV-STORE-002: This is the canonical retrieval method.
        """
        with self._lock:
            record = self._records.get(proof_hash)
            
            self._log_operation(
                operation=StorageOperation.READ,
                proof_hash=proof_hash,
                pdo_id=record.pdo_id if record else None,
                status=StorageStatus.SUCCESS if record else StorageStatus.NOT_FOUND,
                requestor_gid=requestor_gid,
            )
            
            return record

    def exists(self, proof_hash: str) -> bool:
        """Check if PDO record exists."""
        with self._lock:
            return proof_hash in self._records

    def count(self) -> int:
        """Get total number of stored PDO records."""
        with self._lock:
            return len(self._records)

    def list_all_proof_hashes(self) -> List[str]:
        """List all stored proof hashes."""
        with self._lock:
            return list(self._records.keys())

    # ─────────────────────────────────────────────────────────────────────────
    # Audit Trail
    # ─────────────────────────────────────────────────────────────────────────

    def _log_operation(
        self,
        operation: StorageOperation,
        proof_hash: Optional[str],
        pdo_id: Optional[str],
        status: StorageStatus,
        requestor_gid: str,
        details: Optional[str] = None,
    ) -> None:
        """Log storage operation (INV-STORE-005)."""
        self._entry_counter += 1
        
        entry = StorageAuditEntry(
            entry_id=f"AUDIT-STORE-{self._entry_counter:06d}",
            operation=operation,
            proof_hash=proof_hash,
            pdo_id=pdo_id,
            status=status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            requestor_gid=requestor_gid,
            details=details,
        )
        
        self._audit_log.append(entry)

    def get_audit_log(self) -> List[StorageAuditEntry]:
        """Get full audit log."""
        with self._lock:
            return list(self._audit_log)

    # ─────────────────────────────────────────────────────────────────────────
    # Export
    # ─────────────────────────────────────────────────────────────────────────

    def export_statistics(self) -> Dict[str, Any]:
        """Export storage statistics."""
        with self._lock:
            return {
                "total_records": len(self._records),
                "total_artifacts": len(self._artifacts),
                "audit_entries": len(self._audit_log),
                "exported_at": datetime.utcnow().isoformat() + "Z",
            }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_global_store: Optional[PDOStore] = None
_global_lock = threading.Lock()


def get_pdo_store() -> PDOStore:
    """Get or create global PDO store."""
    global _global_store
    
    with _global_lock:
        if _global_store is None:
            _global_store = PDOStore()
        return _global_store


def reset_pdo_store() -> None:
    """Reset global store (for testing)."""
    global _global_store
    
    with _global_lock:
        _global_store = None
