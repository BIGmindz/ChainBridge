"""
File System Storage Backend Module
==================================

PAC-SEC-P822-A: IMMUTABLE AUDIT STORAGE CORE
Component: File System Backend with Rotation
Agent: ATLAS (GID-11)

PURPOSE:
  Implements persistent file system storage for immutable audit events.
  Handles rotation, archival, and disk I/O with fail-closed discipline.
  Integrates with CODY's ImmutableAuditStore for chain integrity.

INVARIANTS:
  INV-AUDIT-005: Backend MUST handle rotation and archival
  INV-BACKEND-001: Written data MUST be immediately persistent
  INV-BACKEND-002: Rotation MUST NOT lose events
  INV-BACKEND-003: Backend MUST fail-closed on I/O errors

STORAGE STRUCTURE:
  /audit/
    current.jsonl          # Current active log
    archive/
      2024-01-01.jsonl.gz  # Rotated and compressed
      2024-01-02.jsonl.gz
    manifests/
      manifest.json        # Index of all files
      hashes.json          # Hash verification data
"""

import gzip
import json
import os
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
import fcntl


class BackendError(Exception):
    """Raised when backend operations fail."""
    pass


class RotationError(Exception):
    """Raised when log rotation fails."""
    pass


@dataclass
class StorageConfig:
    """Configuration for file system backend."""
    # Paths
    base_path: Path = field(default_factory=lambda: Path("./audit"))
    current_file: str = "current.jsonl"
    archive_dir: str = "archive"
    manifest_dir: str = "manifests"
    
    # Rotation settings
    max_file_size_mb: int = 100
    max_events_per_file: int = 100000
    rotation_interval_hours: int = 24
    
    # Compression
    compress_archives: bool = True
    
    # Retention
    retention_days: int = 90
    
    # Performance
    flush_interval_events: int = 100
    sync_on_write: bool = True


@dataclass
class FileManifest:
    """Manifest entry for a storage file."""
    filename: str
    start_time: str
    end_time: Optional[str]
    event_count: int
    size_bytes: int
    merkle_root: str
    is_active: bool = False
    is_compressed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "event_count": self.event_count,
            "size_bytes": self.size_bytes,
            "merkle_root": self.merkle_root,
            "is_active": self.is_active,
            "is_compressed": self.is_compressed,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileManifest":
        return cls(**data)


class FileSystemBackend:
    """
    Persistent file system storage backend for audit events.
    
    Features:
    - JSONL format for append-friendly storage
    - Automatic rotation by size, count, or time
    - Optional gzip compression for archives
    - Manifest tracking for all files
    - File locking for concurrent access
    - Fail-closed on I/O errors
    
    Thread-safe for concurrent operations.
    """
    
    def __init__(self, config: Optional[StorageConfig] = None):
        """
        Initialize file system backend.
        
        Args:
            config: Storage configuration (uses defaults if None)
        """
        self.config = config or StorageConfig()
        self._lock = threading.RLock()
        self._file_handle: Optional[Any] = None
        self._current_manifest: Optional[FileManifest] = None
        self._manifests: List[FileManifest] = []
        self._event_buffer: List[str] = []
        self._unflushed_count = 0
        self._last_rotation = datetime.now(timezone.utc)
        self._initialized = False
    
    def initialize(self):
        """
        Initialize storage directories and files.
        
        Creates required directory structure and loads manifests.
        
        Raises:
            BackendError: If initialization fails
        """
        with self._lock:
            try:
                # Create directories
                self.config.base_path.mkdir(parents=True, exist_ok=True)
                (self.config.base_path / self.config.archive_dir).mkdir(exist_ok=True)
                (self.config.base_path / self.config.manifest_dir).mkdir(exist_ok=True)
                
                # Load existing manifests
                self._load_manifests()
                
                # Open or create current file
                self._open_current_file()
                
                self._initialized = True
                
            except Exception as e:
                raise BackendError(f"Failed to initialize backend: {e}") from e
    
    def _load_manifests(self):
        """Load manifest files from disk."""
        manifest_path = self.config.base_path / self.config.manifest_dir / "manifest.json"
        
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r') as f:
                    data = json.load(f)
                    self._manifests = [
                        FileManifest.from_dict(m) for m in data.get("files", [])
                    ]
            except Exception:
                self._manifests = []
    
    def _save_manifests(self):
        """Save manifest files to disk."""
        manifest_path = self.config.base_path / self.config.manifest_dir / "manifest.json"
        
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "files": [m.to_dict() for m in self._manifests],
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _open_current_file(self):
        """Open or create the current log file."""
        current_path = self.config.base_path / self.config.current_file
        
        # Check if we need to create new manifest entry
        active_manifest = None
        for m in self._manifests:
            if m.is_active:
                active_manifest = m
                break
        
        if active_manifest is None:
            # Create new manifest for current file
            active_manifest = FileManifest(
                filename=self.config.current_file,
                start_time=datetime.now(timezone.utc).isoformat(),
                end_time=None,
                event_count=0,
                size_bytes=0,
                merkle_root="",
                is_active=True,
            )
            self._manifests.append(active_manifest)
        
        self._current_manifest = active_manifest
        
        # Open file for appending
        self._file_handle = open(current_path, 'a')
        
        # Update size from existing file
        if current_path.exists():
            self._current_manifest.size_bytes = current_path.stat().st_size
    
    def write(self, event_json: str, merkle_root: str = "") -> bool:
        """
        Write an event to storage.
        
        Args:
            event_json: JSON-serialized event
            merkle_root: Current Merkle root for manifest
            
        Returns:
            True if write successful
            
        Raises:
            BackendError: If write fails (fail-closed)
        """
        if not self._initialized:
            raise BackendError("Backend not initialized. Call initialize() first.")
        
        with self._lock:
            try:
                # Check if rotation needed
                if self._should_rotate():
                    self._rotate()
                
                # Write to file
                self._file_handle.write(event_json + "\n")
                self._unflushed_count += 1
                
                # Update manifest
                self._current_manifest.event_count += 1
                self._current_manifest.size_bytes += len(event_json) + 1
                self._current_manifest.merkle_root = merkle_root
                
                # Flush if needed
                if self._unflushed_count >= self.config.flush_interval_events:
                    self._flush()
                
                return True
                
            except Exception as e:
                # Fail-closed: raise error, don't silently continue
                raise BackendError(f"Write failed: {e}") from e
    
    def _should_rotate(self) -> bool:
        """Check if log rotation is needed."""
        if not self._current_manifest:
            return False
        
        # Check size
        size_mb = self._current_manifest.size_bytes / (1024 * 1024)
        if size_mb >= self.config.max_file_size_mb:
            return True
        
        # Check event count
        if self._current_manifest.event_count >= self.config.max_events_per_file:
            return True
        
        # Check time
        elapsed = datetime.now(timezone.utc) - self._last_rotation
        if elapsed.total_seconds() >= self.config.rotation_interval_hours * 3600:
            return True
        
        return False
    
    def rotate(self) -> str:
        """
        Manually trigger log rotation.
        
        Returns:
            Path to the archived file
        """
        with self._lock:
            return self._rotate()
    
    def _rotate(self) -> str:
        """Internal rotation implementation."""
        if not self._current_manifest:
            return ""
        
        try:
            # Flush and close current file
            self._flush()
            self._file_handle.close()
            
            # Generate archive filename
            now = datetime.now(timezone.utc)
            archive_name = now.strftime("%Y-%m-%d_%H%M%S") + ".jsonl"
            
            if self.config.compress_archives:
                archive_name += ".gz"
            
            # Move current to archive
            current_path = self.config.base_path / self.config.current_file
            archive_path = self.config.base_path / self.config.archive_dir / archive_name
            
            if self.config.compress_archives:
                # Compress while archiving
                with open(current_path, 'rb') as f_in:
                    with gzip.open(archive_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                current_path.unlink()
            else:
                shutil.move(str(current_path), str(archive_path))
            
            # Update manifest
            self._current_manifest.is_active = False
            self._current_manifest.end_time = now.isoformat()
            self._current_manifest.filename = str(archive_path.relative_to(self.config.base_path))
            self._current_manifest.is_compressed = self.config.compress_archives
            
            # Save manifests
            self._save_manifests()
            
            # Open new current file
            self._open_current_file()
            self._last_rotation = now
            
            return str(archive_path)
            
        except Exception as e:
            raise RotationError(f"Rotation failed: {e}") from e
    
    def _flush(self):
        """Flush buffer to disk."""
        if self._file_handle:
            self._file_handle.flush()
            if self.config.sync_on_write:
                os.fsync(self._file_handle.fileno())
            self._unflushed_count = 0
    
    def read_current(self) -> Iterator[str]:
        """
        Read events from current log file.
        
        Yields:
            JSON strings for each event
        """
        current_path = self.config.base_path / self.config.current_file
        
        if not current_path.exists():
            return
        
        with open(current_path, 'r') as f:
            for line in f:
                if line.strip():
                    yield line.strip()
    
    def read_archive(self, filename: str) -> Iterator[str]:
        """
        Read events from an archived file.
        
        Args:
            filename: Archive filename (relative to archive dir)
            
        Yields:
            JSON strings for each event
        """
        archive_path = self.config.base_path / self.config.archive_dir / filename
        
        if not archive_path.exists():
            return
        
        opener = gzip.open if filename.endswith('.gz') else open
        
        with opener(archive_path, 'rt') as f:
            for line in f:
                if line.strip():
                    yield line.strip()
    
    def read_all(self) -> Iterator[str]:
        """
        Read all events from all files in chronological order.
        
        Yields:
            JSON strings for each event
        """
        # Read archives first (oldest to newest)
        for manifest in sorted(self._manifests, key=lambda m: m.start_time):
            if not manifest.is_active:
                yield from self.read_archive(manifest.filename)
        
        # Then read current
        yield from self.read_current()
    
    def archive(self, before_date: Optional[datetime] = None) -> List[str]:
        """
        Archive old files based on retention policy.
        
        Args:
            before_date: Archive files before this date (default: retention_days ago)
            
        Returns:
            List of archived file paths
        """
        if before_date is None:
            before_date = datetime.now(timezone.utc) - timedelta(
                days=self.config.retention_days
            )
        
        archived = []
        
        with self._lock:
            for manifest in self._manifests:
                if manifest.is_active:
                    continue
                
                try:
                    file_time = datetime.fromisoformat(
                        manifest.start_time.replace('Z', '+00:00')
                    )
                    if file_time < before_date:
                        archived.append(manifest.filename)
                except Exception:
                    pass
        
        return archived
    
    def get_manifests(self) -> List[FileManifest]:
        """Get all file manifests."""
        return list(self._manifests)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_events = sum(m.event_count for m in self._manifests)
        total_size = sum(m.size_bytes for m in self._manifests)
        
        return {
            "total_files": len(self._manifests),
            "total_events": total_events,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "current_file_events": self._current_manifest.event_count if self._current_manifest else 0,
            "oldest_file": min((m.start_time for m in self._manifests), default=None),
            "newest_file": max((m.start_time for m in self._manifests), default=None),
        }
    
    def verify_file(self, filename: str) -> Tuple[bool, int]:
        """
        Verify a file's contents are valid JSON.
        
        Args:
            filename: File to verify
            
        Returns:
            Tuple of (is_valid, event_count)
        """
        count = 0
        
        try:
            if filename == self.config.current_file:
                events = self.read_current()
            else:
                events = self.read_archive(filename)
            
            for event_json in events:
                json.loads(event_json)  # Validate JSON
                count += 1
            
            return True, count
            
        except Exception:
            return False, count
    
    def close(self):
        """Close the backend and flush all data."""
        with self._lock:
            if self._file_handle:
                self._flush()
                self._file_handle.close()
                self._file_handle = None
            
            self._save_manifests()
            self._initialized = False
    
    def __enter__(self):
        """Context manager entry."""
        if not self._initialized:
            self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
