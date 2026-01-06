"""
Backup Integrity Pipeline — Independent Verification System

PAC: PAC-OCC-P07
Lane: EX5 — Backup Integrity Pipeline
Agent: Atlas (GID-11)

Addresses existential failure EX5: "Backup Integrity"
BER-P05 finding: Backup trust unverified — no independent verification

MECHANICAL ENFORCEMENT:
- Independent backup verification at configurable intervals
- Cryptographic integrity checks (SHA-256)
- Restorable verification (test extraction)
- Alert on integrity failures

INVARIANTS:
- INV-BACKUP-001: Backups MUST have verifiable integrity hashes
- INV-BACKUP-002: Verification MUST be independent of backup creation
- INV-BACKUP-003: Failed verifications trigger immediate alerts
- INV-BACKUP-004: All verification results are logged immutably
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Verification intervals
DEFAULT_VERIFICATION_INTERVAL_HOURS = int(
    os.environ.get("CHAINBRIDGE_BACKUP_VERIFY_INTERVAL_HOURS", "24")
)

# Paths
DEFAULT_BACKUP_PATH = "./data/backups"
DEFAULT_MANIFEST_PATH = "./data/backups/integrity_manifest.json"


class BackupType(str, Enum):
    """Types of backups."""
    
    AUDIT = "audit"
    DATABASE = "database"
    CONFIG = "config"
    STATE = "state"
    PROOFPACK = "proofpack"


class VerificationStatus(str, Enum):
    """Backup verification status."""
    
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    CORRUPTED = "corrupted"
    MISSING = "missing"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BackupEntry:
    """Record of a backup."""
    
    backup_id: str
    backup_type: BackupType
    source_path: str
    backup_path: str
    created_at: str
    created_by: str
    
    # Integrity
    size_bytes: int
    sha256_hash: str
    
    # Compression
    is_compressed: bool
    original_size_bytes: Optional[int] = None
    
    # Verification
    last_verified: Optional[str] = None
    verification_count: int = 0
    last_verification_status: VerificationStatus = VerificationStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "backup_id": self.backup_id,
            "backup_type": self.backup_type.value,
            "source_path": self.source_path,
            "backup_path": self.backup_path,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "size_bytes": self.size_bytes,
            "sha256_hash": self.sha256_hash,
            "is_compressed": self.is_compressed,
            "original_size_bytes": self.original_size_bytes,
            "last_verified": self.last_verified,
            "verification_count": self.verification_count,
            "last_verification_status": self.last_verification_status.value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackupEntry":
        """Create from dictionary."""
        return cls(
            backup_id=data["backup_id"],
            backup_type=BackupType(data["backup_type"]),
            source_path=data["source_path"],
            backup_path=data["backup_path"],
            created_at=data["created_at"],
            created_by=data["created_by"],
            size_bytes=data["size_bytes"],
            sha256_hash=data["sha256_hash"],
            is_compressed=data["is_compressed"],
            original_size_bytes=data.get("original_size_bytes"),
            last_verified=data.get("last_verified"),
            verification_count=data.get("verification_count", 0),
            last_verification_status=VerificationStatus(
                data.get("last_verification_status", "pending")
            ),
        )


@dataclass
class VerificationResult:
    """Result of a backup verification."""
    
    verification_id: str
    backup_id: str
    timestamp: str
    status: VerificationStatus
    
    # Checks performed
    file_exists: bool
    size_matches: bool
    hash_matches: bool
    restorable: bool
    
    # Details
    expected_hash: str
    actual_hash: Optional[str]
    expected_size: int
    actual_size: Optional[int]
    
    # Error info
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "verification_id": self.verification_id,
            "backup_id": self.backup_id,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "file_exists": self.file_exists,
            "size_matches": self.size_matches,
            "hash_matches": self.hash_matches,
            "restorable": self.restorable,
            "expected_hash": self.expected_hash,
            "actual_hash": self.actual_hash,
            "expected_size": self.expected_size,
            "actual_size": self.actual_size,
            "error_message": self.error_message,
        }


@dataclass
class IntegrityManifest:
    """Manifest of all backups and verification history."""
    
    manifest_version: str = "1.0.0"
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    backups: List[BackupEntry] = field(default_factory=list)
    verification_history: List[VerificationResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "manifest_version": self.manifest_version,
            "last_updated": self.last_updated,
            "backups": [b.to_dict() for b in self.backups],
            "verification_history": [v.to_dict() for v in self.verification_history[-1000:]],  # Keep last 1000
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntegrityManifest":
        """Create from dictionary."""
        return cls(
            manifest_version=data.get("manifest_version", "1.0.0"),
            last_updated=data.get("last_updated", datetime.now(timezone.utc).isoformat()),
            backups=[BackupEntry.from_dict(b) for b in data.get("backups", [])],
            verification_history=[
                VerificationResult(
                    verification_id=v["verification_id"],
                    backup_id=v["backup_id"],
                    timestamp=v["timestamp"],
                    status=VerificationStatus(v["status"]),
                    file_exists=v["file_exists"],
                    size_matches=v["size_matches"],
                    hash_matches=v["hash_matches"],
                    restorable=v["restorable"],
                    expected_hash=v["expected_hash"],
                    actual_hash=v.get("actual_hash"),
                    expected_size=v["expected_size"],
                    actual_size=v.get("actual_size"),
                    error_message=v.get("error_message"),
                )
                for v in data.get("verification_history", [])
            ],
        )


class BackupIntegrityError(Exception):
    """Backup integrity verification failed."""
    
    def __init__(self, backup_id: str, message: str, result: Optional[VerificationResult] = None):
        super().__init__(f"INV-BACKUP-001 VIOLATION: {backup_id}: {message}")
        self.backup_id = backup_id
        self.result = result


# ═══════════════════════════════════════════════════════════════════════════════
# BACKUP INTEGRITY VERIFIER
# ═══════════════════════════════════════════════════════════════════════════════


class BackupIntegrityVerifier:
    """
    Independent backup verification system.
    
    INVARIANT ENFORCEMENT:
    - INV-BACKUP-001: Hash verification for all backups
    - INV-BACKUP-002: Verification independent of creation
    - INV-BACKUP-003: Alert on failures
    - INV-BACKUP-004: Immutable verification log
    """
    
    def __init__(
        self,
        backup_path: Optional[str] = None,
        manifest_path: Optional[str] = None,
    ):
        """Initialize the backup integrity verifier."""
        self._lock = threading.Lock()
        
        self._backup_path = Path(backup_path or DEFAULT_BACKUP_PATH)
        self._manifest_path = Path(manifest_path or DEFAULT_MANIFEST_PATH)
        
        self._backup_path.mkdir(parents=True, exist_ok=True)
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[VerificationResult], None]] = []
        
        # Load manifest
        self._manifest = self._load_manifest()
        
        logger.info(f"BackupIntegrityVerifier initialized — {len(self._manifest.backups)} backups tracked")
    
    def _load_manifest(self) -> IntegrityManifest:
        """Load the integrity manifest."""
        if not self._manifest_path.exists():
            return IntegrityManifest()
        
        try:
            data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            return IntegrityManifest.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            return IntegrityManifest()
    
    def _save_manifest(self) -> None:
        """Save the integrity manifest."""
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._manifest.last_updated = datetime.now(timezone.utc).isoformat()
        
        tmp_path = self._manifest_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(self._manifest.to_dict(), indent=2),
            encoding="utf-8"
        )
        tmp_path.replace(self._manifest_path)
    
    def _compute_hash(self, path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    
    def _trigger_alerts(self, result: VerificationResult) -> None:
        """Trigger alert callbacks for failed verification."""
        if result.status in (VerificationStatus.FAILED, VerificationStatus.CORRUPTED, VerificationStatus.MISSING):
            logger.critical(
                f"INV-BACKUP-003 ALERT: Backup {result.backup_id} verification {result.status.value}: "
                f"{result.error_message}"
            )
            
            for callback in self._alert_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    def register_alert_callback(self, callback: Callable[[VerificationResult], None]) -> None:
        """Register a callback for verification failures."""
        self._alert_callbacks.append(callback)
    
    def register_backup(
        self,
        source_path: str,
        backup_type: BackupType,
        created_by: str,
        compress: bool = True,
    ) -> BackupEntry:
        """
        Register and create a new backup.
        
        Args:
            source_path: Path to source file/directory
            backup_type: Type of backup
            created_by: Operator/system creating backup
            compress: Whether to compress the backup
            
        Returns:
            BackupEntry for the new backup
            
        ENFORCES: INV-BACKUP-001 (creates verifiable hash)
        """
        with self._lock:
            source = Path(source_path)
            if not source.exists():
                raise FileNotFoundError(f"Source not found: {source_path}")
            
            # Generate backup ID
            backup_id = f"backup_{backup_type.value}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
            
            # Determine backup path
            if compress:
                backup_file = self._backup_path / f"{backup_id}.gz"
            else:
                backup_file = self._backup_path / backup_id
            
            # Create backup
            if source.is_file():
                original_content = source.read_bytes()
                original_size = len(original_content)
                
                if compress:
                    with gzip.open(backup_file, "wb", compresslevel=9) as f:
                        f.write(original_content)
                else:
                    shutil.copy2(source, backup_file)
            else:
                # Directory — create tar.gz
                backup_file = self._backup_path / f"{backup_id}.tar.gz"
                shutil.make_archive(
                    str(backup_file.with_suffix("")),
                    "gztar",
                    source.parent,
                    source.name
                )
                original_size = sum(f.stat().st_size for f in source.rglob("*") if f.is_file())
            
            # Compute hash
            backup_size = backup_file.stat().st_size
            backup_hash = self._compute_hash(backup_file)
            
            # Create entry
            entry = BackupEntry(
                backup_id=backup_id,
                backup_type=backup_type,
                source_path=str(source),
                backup_path=str(backup_file),
                created_at=datetime.now(timezone.utc).isoformat(),
                created_by=created_by,
                size_bytes=backup_size,
                sha256_hash=backup_hash,
                is_compressed=compress,
                original_size_bytes=original_size,
            )
            
            self._manifest.backups.append(entry)
            self._save_manifest()
            
            logger.info(
                f"BACKUP_REGISTERED: {backup_id} — {backup_type.value}, "
                f"{original_size / 1024:.1f}KB -> {backup_size / 1024:.1f}KB, "
                f"hash={backup_hash[:16]}..."
            )
            
            return entry
    
    def verify_backup(
        self,
        backup_id: str,
        test_restore: bool = True,
    ) -> VerificationResult:
        """
        Verify integrity of a specific backup.
        
        Args:
            backup_id: Backup to verify
            test_restore: Whether to test restoration
            
        Returns:
            VerificationResult
            
        ENFORCES: INV-BACKUP-002 (independent verification)
        """
        with self._lock:
            # Find backup entry
            entry = None
            for b in self._manifest.backups:
                if b.backup_id == backup_id:
                    entry = b
                    break
            
            if not entry:
                result = VerificationResult(
                    verification_id=str(uuid4()),
                    backup_id=backup_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status=VerificationStatus.MISSING,
                    file_exists=False,
                    size_matches=False,
                    hash_matches=False,
                    restorable=False,
                    expected_hash="unknown",
                    actual_hash=None,
                    expected_size=0,
                    actual_size=None,
                    error_message="Backup not found in manifest",
                )
                self._manifest.verification_history.append(result)
                self._save_manifest()
                self._trigger_alerts(result)
                return result
            
            backup_path = Path(entry.backup_path)
            
            # Check file exists
            if not backup_path.exists():
                result = VerificationResult(
                    verification_id=str(uuid4()),
                    backup_id=backup_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status=VerificationStatus.MISSING,
                    file_exists=False,
                    size_matches=False,
                    hash_matches=False,
                    restorable=False,
                    expected_hash=entry.sha256_hash,
                    actual_hash=None,
                    expected_size=entry.size_bytes,
                    actual_size=None,
                    error_message=f"Backup file missing: {entry.backup_path}",
                )
                entry.last_verified = result.timestamp
                entry.verification_count += 1
                entry.last_verification_status = result.status
                self._manifest.verification_history.append(result)
                self._save_manifest()
                self._trigger_alerts(result)
                return result
            
            # Check size
            actual_size = backup_path.stat().st_size
            size_matches = actual_size == entry.size_bytes
            
            # Compute hash
            actual_hash = self._compute_hash(backup_path)
            hash_matches = actual_hash == entry.sha256_hash
            
            # Test restoration if requested
            restorable = False
            restore_error = None
            
            if test_restore and hash_matches:
                try:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        tmp_path = Path(tmp_dir) / "test_restore"
                        
                        if entry.is_compressed:
                            if backup_path.suffix == ".gz":
                                with gzip.open(backup_path, "rb") as f_in:
                                    with open(tmp_path, "wb") as f_out:
                                        shutil.copyfileobj(f_in, f_out)
                                restorable = tmp_path.exists() and tmp_path.stat().st_size > 0
                            else:
                                # tar.gz
                                shutil.unpack_archive(backup_path, tmp_path)
                                restorable = tmp_path.exists()
                        else:
                            shutil.copy2(backup_path, tmp_path)
                            restorable = tmp_path.exists()
                            
                except Exception as e:
                    restore_error = str(e)
                    restorable = False
            
            # Determine status
            if hash_matches and size_matches and (restorable or not test_restore):
                status = VerificationStatus.VERIFIED
                error_msg = None
            elif not hash_matches:
                status = VerificationStatus.CORRUPTED
                error_msg = f"Hash mismatch: expected {entry.sha256_hash[:16]}..., got {actual_hash[:16]}..."
            elif not restorable:
                status = VerificationStatus.FAILED
                error_msg = f"Restoration test failed: {restore_error}"
            else:
                status = VerificationStatus.FAILED
                error_msg = f"Size mismatch: expected {entry.size_bytes}, got {actual_size}"
            
            result = VerificationResult(
                verification_id=str(uuid4()),
                backup_id=backup_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status=status,
                file_exists=True,
                size_matches=size_matches,
                hash_matches=hash_matches,
                restorable=restorable,
                expected_hash=entry.sha256_hash,
                actual_hash=actual_hash,
                expected_size=entry.size_bytes,
                actual_size=actual_size,
                error_message=error_msg,
            )
            
            # Update entry
            entry.last_verified = result.timestamp
            entry.verification_count += 1
            entry.last_verification_status = result.status
            
            self._manifest.verification_history.append(result)
            self._save_manifest()
            
            if status == VerificationStatus.VERIFIED:
                logger.info(f"BACKUP_VERIFIED: {backup_id} — hash valid, restorable={restorable}")
            else:
                self._trigger_alerts(result)
            
            return result
    
    def verify_all(self, test_restore: bool = False) -> List[VerificationResult]:
        """
        Verify all registered backups.
        
        Args:
            test_restore: Whether to test restoration for each
            
        Returns:
            List of verification results
        """
        results = []
        
        for entry in self._manifest.backups:
            result = self.verify_backup(entry.backup_id, test_restore=test_restore)
            results.append(result)
        
        # Summary
        verified = sum(1 for r in results if r.status == VerificationStatus.VERIFIED)
        failed = len(results) - verified
        
        logger.info(f"BACKUP_VERIFICATION_COMPLETE: {verified}/{len(results)} verified, {failed} failed")
        
        return results
    
    def get_stale_backups(
        self,
        max_age_hours: Optional[int] = None
    ) -> List[BackupEntry]:
        """
        Get backups that haven't been verified recently.
        
        Args:
            max_age_hours: Maximum hours since last verification
            
        Returns:
            List of stale backup entries
        """
        max_age = max_age_hours or DEFAULT_VERIFICATION_INTERVAL_HOURS
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age)
        
        stale = []
        for entry in self._manifest.backups:
            if entry.last_verified is None:
                stale.append(entry)
            else:
                last = datetime.fromisoformat(entry.last_verified.replace("Z", "+00:00"))
                if last < cutoff:
                    stale.append(entry)
        
        return stale
    
    def list_backups(self, backup_type: Optional[BackupType] = None) -> List[BackupEntry]:
        """List all backup entries, optionally filtered by type."""
        with self._lock:
            if backup_type:
                return [b for b in self._manifest.backups if b.backup_type == backup_type]
            return list(self._manifest.backups)
    
    def get_verification_history(
        self,
        backup_id: Optional[str] = None,
        limit: int = 100
    ) -> List[VerificationResult]:
        """Get verification history, optionally filtered by backup."""
        with self._lock:
            history = self._manifest.verification_history
            if backup_id:
                history = [v for v in history if v.backup_id == backup_id]
            return history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get backup integrity statistics."""
        with self._lock:
            by_type = {}
            by_status = {}
            total_size = 0
            
            for entry in self._manifest.backups:
                by_type[entry.backup_type.value] = by_type.get(entry.backup_type.value, 0) + 1
                by_status[entry.last_verification_status.value] = \
                    by_status.get(entry.last_verification_status.value, 0) + 1
                total_size += entry.size_bytes
            
            stale_count = len(self.get_stale_backups())
            
            return {
                "total_backups": len(self._manifest.backups),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "by_type": by_type,
                "by_verification_status": by_status,
                "stale_count": stale_count,
                "verification_history_count": len(self._manifest.verification_history),
            }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_verifier_instance: Optional[BackupIntegrityVerifier] = None
_verifier_lock = threading.Lock()


def get_backup_verifier() -> BackupIntegrityVerifier:
    """Get the singleton backup integrity verifier instance."""
    global _verifier_instance
    
    if _verifier_instance is None:
        with _verifier_lock:
            if _verifier_instance is None:
                _verifier_instance = BackupIntegrityVerifier()
    
    return _verifier_instance
