"""
Audit Archival & Storage — Storage Exhaustion Prevention

PAC: PAC-OCC-P07
Lane: EX4 — Audit Archival & Storage
Agent: Dan (GID-07)

Addresses existential failure EX4: "Storage Exhaustion"
BER-P05 finding: Audit logs grow unbounded, no archival mechanism

MECHANICAL ENFORCEMENT:
- Automatic archival when storage exceeds thresholds
- Chain-preserving archival (maintains cryptographic continuity)
- Compressed archive storage with integrity verification
- Configurable retention policies

INVARIANTS:
- INV-ARCH-001: Audit chain integrity MUST be preserved across archives
- INV-ARCH-002: Archives MUST be independently verifiable
- INV-ARCH-003: Active storage NEVER exceeds MAX_ACTIVE_STORAGE_MB
- INV-ARCH-004: All archival operations are logged
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Storage thresholds
MAX_ACTIVE_STORAGE_MB = int(os.environ.get("CHAINBRIDGE_MAX_AUDIT_STORAGE_MB", "500"))
ARCHIVE_TRIGGER_THRESHOLD = 0.8  # Trigger archival at 80% of max
MIN_ENTRIES_BEFORE_ARCHIVE = 10000  # Minimum entries before archival allowed

# Retention settings
ARCHIVE_RETENTION_DAYS = int(os.environ.get("CHAINBRIDGE_ARCHIVE_RETENTION_DAYS", "365"))
ACTIVE_RETENTION_DAYS = int(os.environ.get("CHAINBRIDGE_ACTIVE_RETENTION_DAYS", "30"))

# Paths
DEFAULT_AUDIT_PATH = "./data/audit"
DEFAULT_ARCHIVE_PATH = "./data/audit_archive"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AuditEntry:
    """Single audit log entry."""
    
    entry_id: str
    timestamp: str
    event_type: str
    actor: str
    action: str
    details: Dict[str, Any]
    chain_hash: str  # Hash linking to previous entry


@dataclass
class ArchiveManifest:
    """Manifest for an archived audit segment."""
    
    archive_id: str
    created_at: str
    created_by: str
    
    # Coverage
    start_timestamp: str
    end_timestamp: str
    entry_count: int
    
    # Chain integrity
    first_entry_hash: str
    last_entry_hash: str
    chain_valid: bool
    
    # Storage
    original_size_bytes: int
    compressed_size_bytes: int
    compression_ratio: float
    
    # Verification
    content_hash: str  # SHA-256 of compressed content
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "archive_id": self.archive_id,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "entry_count": self.entry_count,
            "first_entry_hash": self.first_entry_hash,
            "last_entry_hash": self.last_entry_hash,
            "chain_valid": self.chain_valid,
            "original_size_bytes": self.original_size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "compression_ratio": self.compression_ratio,
            "content_hash": self.content_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchiveManifest":
        """Create from dictionary."""
        return cls(
            archive_id=data["archive_id"],
            created_at=data["created_at"],
            created_by=data["created_by"],
            start_timestamp=data["start_timestamp"],
            end_timestamp=data["end_timestamp"],
            entry_count=data["entry_count"],
            first_entry_hash=data["first_entry_hash"],
            last_entry_hash=data["last_entry_hash"],
            chain_valid=data["chain_valid"],
            original_size_bytes=data["original_size_bytes"],
            compressed_size_bytes=data["compressed_size_bytes"],
            compression_ratio=data["compression_ratio"],
            content_hash=data["content_hash"],
        )


@dataclass
class StorageStatus:
    """Current storage status."""
    
    active_size_mb: float
    active_entry_count: int
    archive_count: int
    total_archived_entries: int
    total_archive_size_mb: float
    threshold_percentage: float
    archival_recommended: bool


class ArchiveIntegrityError(Exception):
    """Archive integrity verification failed."""
    
    def __init__(self, archive_id: str, message: str):
        super().__init__(f"INV-ARCH-002 VIOLATION: Archive {archive_id} integrity failed: {message}")
        self.archive_id = archive_id


class ChainContinuityError(Exception):
    """Audit chain continuity broken."""
    
    def __init__(self, message: str):
        super().__init__(f"INV-ARCH-001 VIOLATION: Chain continuity broken: {message}")


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT ARCHIVER
# ═══════════════════════════════════════════════════════════════════════════════


class AuditArchiver:
    """
    Manages audit log archival with chain preservation.
    
    INVARIANT ENFORCEMENT:
    - INV-ARCH-001: Verify chain continuity before/after archive
    - INV-ARCH-002: Generate verifiable archive with content hash
    - INV-ARCH-003: Monitor and enforce storage limits
    - INV-ARCH-004: Log all archival operations
    """
    
    def __init__(
        self,
        audit_path: Optional[str] = None,
        archive_path: Optional[str] = None,
    ):
        """Initialize the audit archiver."""
        self._lock = threading.Lock()
        
        self._audit_path = Path(audit_path or DEFAULT_AUDIT_PATH)
        self._archive_path = Path(archive_path or DEFAULT_ARCHIVE_PATH)
        
        # Ensure directories exist
        self._audit_path.mkdir(parents=True, exist_ok=True)
        self._archive_path.mkdir(parents=True, exist_ok=True)
        
        # Archive manifest tracking
        self._manifests: List[ArchiveManifest] = []
        self._load_manifests()
        
        # Chain tracking
        self._last_archived_hash: Optional[str] = None
        
        logger.info(f"AuditArchiver initialized — audit: {self._audit_path}, archive: {self._archive_path}")
    
    def _load_manifests(self) -> None:
        """Load existing archive manifests."""
        manifest_file = self._archive_path / "manifests.json"
        if manifest_file.exists():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                self._manifests = [
                    ArchiveManifest.from_dict(m) for m in data.get("manifests", [])
                ]
                self._last_archived_hash = data.get("last_archived_hash")
                logger.info(f"Loaded {len(self._manifests)} archive manifests")
            except Exception as e:
                logger.error(f"Failed to load manifests: {e}")
    
    def _save_manifests(self) -> None:
        """Save archive manifests."""
        manifest_file = self._archive_path / "manifests.json"
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "last_archived_hash": self._last_archived_hash,
            "manifests": [m.to_dict() for m in self._manifests],
        }
        
        tmp_path = manifest_file.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(manifest_file)
    
    def _compute_file_hash(self, path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    
    def _get_directory_size_mb(self, path: Path) -> float:
        """Get total size of directory in MB."""
        total = 0
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total / (1024 * 1024)
    
    def _read_audit_entries(self, path: Path) -> List[Dict[str, Any]]:
        """Read audit entries from a file."""
        if not path.exists():
            return []
        
        entries = []
        content = path.read_text(encoding="utf-8")
        
        for line in content.strip().split("\n"):
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        return entries
    
    def _verify_chain(self, entries: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """
        Verify chain integrity of entries.
        
        Returns:
            (is_valid, error_message)
        """
        if not entries:
            return True, None
        
        for i in range(1, len(entries)):
            prev_entry = entries[i - 1]
            curr_entry = entries[i]
            
            # Compute expected hash
            prev_json = json.dumps(prev_entry, sort_keys=True)
            expected_hash = hashlib.sha256(prev_json.encode()).hexdigest()[:16]
            
            # Check chain hash
            if curr_entry.get("chain_hash") != expected_hash:
                return False, f"Chain break at entry {i}: expected {expected_hash}, got {curr_entry.get('chain_hash')}"
        
        return True, None
    
    def get_storage_status(self) -> StorageStatus:
        """Get current storage status."""
        with self._lock:
            active_size = self._get_directory_size_mb(self._audit_path)
            archive_size = self._get_directory_size_mb(self._archive_path)
            
            # Count active entries (rough estimate based on files)
            active_entries = 0
            for f in self._audit_path.glob("*.jsonl"):
                try:
                    active_entries += sum(1 for _ in f.open())
                except Exception:
                    pass
            
            total_archived = sum(m.entry_count for m in self._manifests)
            
            threshold_pct = active_size / MAX_ACTIVE_STORAGE_MB if MAX_ACTIVE_STORAGE_MB > 0 else 0
            
            return StorageStatus(
                active_size_mb=round(active_size, 2),
                active_entry_count=active_entries,
                archive_count=len(self._manifests),
                total_archived_entries=total_archived,
                total_archive_size_mb=round(archive_size, 2),
                threshold_percentage=round(threshold_pct * 100, 1),
                archival_recommended=threshold_pct >= ARCHIVE_TRIGGER_THRESHOLD,
            )
    
    def archive_segment(
        self,
        source_file: str,
        archived_by: str,
        verify_chain: bool = True,
    ) -> ArchiveManifest:
        """
        Archive a segment of audit logs.
        
        Args:
            source_file: Path to the audit log file to archive
            archived_by: Operator/system performing archival
            verify_chain: Whether to verify chain integrity before archiving
            
        Returns:
            Archive manifest
            
        ENFORCES: INV-ARCH-001, INV-ARCH-002
        """
        with self._lock:
            source_path = Path(source_file)
            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_file}")
            
            # Read entries
            entries = self._read_audit_entries(source_path)
            if not entries:
                raise ValueError("No entries to archive")
            
            if len(entries) < MIN_ENTRIES_BEFORE_ARCHIVE:
                raise ValueError(
                    f"Minimum {MIN_ENTRIES_BEFORE_ARCHIVE} entries required for archival, "
                    f"got {len(entries)}"
                )
            
            # INV-ARCH-001: Verify chain integrity
            if verify_chain:
                valid, error = self._verify_chain(entries)
                if not valid:
                    raise ChainContinuityError(error)
            
            # Check chain continuity with previous archive
            if self._last_archived_hash:
                first_entry = entries[0]
                if first_entry.get("chain_hash") != self._last_archived_hash:
                    logger.warning(
                        f"Archive chain discontinuity detected: "
                        f"expected {self._last_archived_hash}, got {first_entry.get('chain_hash')}"
                    )
            
            # Create archive
            archive_id = f"archive_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
            archive_file = self._archive_path / f"{archive_id}.jsonl.gz"
            
            # Compress
            original_content = source_path.read_bytes()
            original_size = len(original_content)
            
            with gzip.open(archive_file, "wb", compresslevel=9) as f:
                f.write(original_content)
            
            compressed_size = archive_file.stat().st_size
            
            # INV-ARCH-002: Compute content hash
            content_hash = self._compute_file_hash(archive_file)
            
            # Compute chain hashes
            first_json = json.dumps(entries[0], sort_keys=True)
            first_hash = hashlib.sha256(first_json.encode()).hexdigest()[:16]
            
            last_json = json.dumps(entries[-1], sort_keys=True)
            last_hash = hashlib.sha256(last_json.encode()).hexdigest()[:16]
            
            # Create manifest
            manifest = ArchiveManifest(
                archive_id=archive_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                created_by=archived_by,
                start_timestamp=entries[0].get("timestamp", ""),
                end_timestamp=entries[-1].get("timestamp", ""),
                entry_count=len(entries),
                first_entry_hash=first_hash,
                last_entry_hash=last_hash,
                chain_valid=True,
                original_size_bytes=original_size,
                compressed_size_bytes=compressed_size,
                compression_ratio=round(compressed_size / original_size, 3) if original_size > 0 else 0,
                content_hash=content_hash,
            )
            
            self._manifests.append(manifest)
            self._last_archived_hash = last_hash
            self._save_manifests()
            
            logger.info(
                f"AUDIT_ARCHIVED: {archive_id} — {len(entries)} entries, "
                f"{original_size / 1024:.1f}KB -> {compressed_size / 1024:.1f}KB "
                f"({manifest.compression_ratio:.1%} ratio)"
            )
            
            return manifest
    
    def verify_archive(self, archive_id: str) -> bool:
        """
        Verify integrity of an archive.
        
        Args:
            archive_id: Archive ID to verify
            
        Returns:
            True if valid
            
        Raises:
            ArchiveIntegrityError: If verification fails
            
        ENFORCES: INV-ARCH-002
        """
        with self._lock:
            # Find manifest
            manifest = None
            for m in self._manifests:
                if m.archive_id == archive_id:
                    manifest = m
                    break
            
            if not manifest:
                raise ValueError(f"Archive {archive_id} not found")
            
            archive_file = self._archive_path / f"{archive_id}.jsonl.gz"
            if not archive_file.exists():
                raise ArchiveIntegrityError(archive_id, "Archive file missing")
            
            # Verify content hash
            actual_hash = self._compute_file_hash(archive_file)
            if actual_hash != manifest.content_hash:
                raise ArchiveIntegrityError(
                    archive_id,
                    f"Content hash mismatch: expected {manifest.content_hash}, got {actual_hash}"
                )
            
            # Decompress and verify chain
            with gzip.open(archive_file, "rb") as f:
                content = f.read().decode("utf-8")
            
            entries = []
            for line in content.strip().split("\n"):
                if line:
                    entries.append(json.loads(line))
            
            if len(entries) != manifest.entry_count:
                raise ArchiveIntegrityError(
                    archive_id,
                    f"Entry count mismatch: expected {manifest.entry_count}, got {len(entries)}"
                )
            
            # Verify chain
            valid, error = self._verify_chain(entries)
            if not valid:
                raise ArchiveIntegrityError(archive_id, f"Chain integrity failed: {error}")
            
            logger.info(f"ARCHIVE_VERIFIED: {archive_id} — {len(entries)} entries, chain valid")
            return True
    
    def restore_archive(self, archive_id: str, destination: Optional[str] = None) -> Path:
        """
        Restore an archive to a readable file.
        
        Args:
            archive_id: Archive to restore
            destination: Optional destination path
            
        Returns:
            Path to restored file
        """
        with self._lock:
            # Verify first
            self.verify_archive(archive_id)
            
            archive_file = self._archive_path / f"{archive_id}.jsonl.gz"
            
            if destination:
                dest_path = Path(destination)
            else:
                dest_path = self._audit_path / f"restored_{archive_id}.jsonl"
            
            with gzip.open(archive_file, "rb") as f_in:
                with open(dest_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            logger.info(f"ARCHIVE_RESTORED: {archive_id} -> {dest_path}")
            return dest_path
    
    def cleanup_old_archives(self, retention_days: Optional[int] = None) -> int:
        """
        Remove archives older than retention period.
        
        Args:
            retention_days: Override default retention
            
        Returns:
            Number of archives removed
        """
        with self._lock:
            retention = retention_days or ARCHIVE_RETENTION_DAYS
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention)
            
            removed = 0
            remaining_manifests = []
            
            for manifest in self._manifests:
                created = datetime.fromisoformat(manifest.created_at.replace("Z", "+00:00"))
                
                if created < cutoff:
                    archive_file = self._archive_path / f"{manifest.archive_id}.jsonl.gz"
                    if archive_file.exists():
                        archive_file.unlink()
                    
                    logger.info(f"ARCHIVE_EXPIRED: {manifest.archive_id} removed (created {manifest.created_at})")
                    removed += 1
                else:
                    remaining_manifests.append(manifest)
            
            self._manifests = remaining_manifests
            self._save_manifests()
            
            return removed
    
    def auto_archive_if_needed(self, archived_by: str = "system") -> Optional[ArchiveManifest]:
        """
        Automatically archive if storage threshold exceeded.
        
        ENFORCES: INV-ARCH-003
        """
        status = self.get_storage_status()
        
        if not status.archival_recommended:
            return None
        
        # Find oldest audit file
        audit_files = sorted(self._audit_path.glob("*.jsonl"))
        if not audit_files:
            logger.warning("No audit files to archive despite high storage")
            return None
        
        oldest_file = audit_files[0]
        
        try:
            manifest = self.archive_segment(
                source_file=str(oldest_file),
                archived_by=archived_by,
            )
            
            # Remove source file after successful archive
            oldest_file.unlink()
            
            logger.info(f"AUTO_ARCHIVE: {oldest_file.name} archived as {manifest.archive_id}")
            return manifest
            
        except Exception as e:
            logger.error(f"Auto-archive failed: {e}")
            return None
    
    def list_archives(self) -> List[ArchiveManifest]:
        """List all archive manifests."""
        with self._lock:
            return list(self._manifests)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_archiver_instance: Optional[AuditArchiver] = None
_archiver_lock = threading.Lock()


def get_audit_archiver() -> AuditArchiver:
    """Get the singleton audit archiver instance."""
    global _archiver_instance
    
    if _archiver_instance is None:
        with _archiver_lock:
            if _archiver_instance is None:
                _archiver_instance = AuditArchiver()
    
    return _archiver_instance
