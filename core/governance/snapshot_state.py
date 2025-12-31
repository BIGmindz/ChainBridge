"""
ChainBridge Snapshot State — Immutable Snapshot Lock Model
════════════════════════════════════════════════════════════════════════════════

Tracks repository snapshot ingestion state for session enforcement.
All state is immutable — mutations return new instances.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-REPO-SNAPSHOT-INGESTION-018
Effective Date: 2025-12-26

INVARIANTS:
- INV-SNAP-001: No PAC execution without snapshot ingestion
- INV-SNAP-002: Snapshot hash must match archive before lock
- INV-SNAP-003: Snapshot is immutable per session
- INV-SNAP-004: Re-ingestion mid-session is forbidden
- INV-SNAP-005: Hash mismatch invalidates session immediately
- INV-SNAP-006: Missing snapshot blocks bootstrap (FAIL-CLOSED)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT LOCK IDENTIFIERS
# ═══════════════════════════════════════════════════════════════════════════════

class SnapshotLockStep(Enum):
    """Canonical snapshot lock step identifiers."""
    
    SNAP_01 = "SNAP-01"  # Snapshot Received
    SNAP_02 = "SNAP-02"  # Hash Verification
    SNAP_03 = "SNAP-03"  # Manifest Validation
    SNAP_04 = "SNAP-04"  # Snapshot Locked


STEP_NAMES: Dict[SnapshotLockStep, str] = {
    SnapshotLockStep.SNAP_01: "Snapshot Received",
    SnapshotLockStep.SNAP_02: "Hash Verification",
    SnapshotLockStep.SNAP_03: "Manifest Validation",
    SnapshotLockStep.SNAP_04: "Snapshot Locked",
}


class SnapshotStatus(Enum):
    """Snapshot ingestion status."""
    
    NOT_INGESTED = "NOT_INGESTED"
    RECEIVING = "RECEIVING"
    VERIFYING = "VERIFYING"
    LOCKED = "LOCKED"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    FAILED = "FAILED"


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT METADATA — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SnapshotMetadata:
    """
    Metadata about a repository snapshot.
    
    Immutable — captured at ingestion time.
    """
    
    snapshot_id: str
    archive_hash: str
    timestamp: str
    source: str
    file_count: int = 0
    total_size: int = 0
    manifest_hash: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        source: str,
        archive_hash: str,
        file_count: int = 0,
        total_size: int = 0,
        manifest_hash: Optional[str] = None,
    ) -> SnapshotMetadata:
        """Create new snapshot metadata with generated ID and timestamp."""
        timestamp = datetime.now(timezone.utc)
        random_suffix = secrets.token_hex(4)
        snapshot_id = f"snap_{timestamp.strftime('%Y%m%d%H%M%S')}_{random_suffix}"
        
        return cls(
            snapshot_id=snapshot_id,
            archive_hash=archive_hash,
            timestamp=timestamp.isoformat(),
            source=source,
            file_count=file_count,
            total_size=total_size,
            manifest_hash=manifest_hash,
        )
    
    @property
    def hash_prefix(self) -> str:
        """Get first 12 characters of hash for display."""
        if self.archive_hash.startswith("sha256:"):
            return self.archive_hash[:19] + "..."
        return self.archive_hash[:12] + "..."


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT LOCK — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SnapshotLock:
    """
    Immutable snapshot lock binding.
    
    Once locked, the snapshot cannot be changed without terminating the session.
    """
    
    metadata: SnapshotMetadata
    locked_at: str
    session_token: Optional[str] = None
    
    @property
    def snapshot_id(self) -> str:
        """Get snapshot ID."""
        return self.metadata.snapshot_id
    
    @property
    def archive_hash(self) -> str:
        """Get archive hash."""
        return self.metadata.archive_hash
    
    @property
    def timestamp(self) -> str:
        """Get snapshot timestamp."""
        return self.metadata.timestamp
    
    @property
    def source(self) -> str:
        """Get snapshot source."""
        return self.metadata.source
    
    def bind_to_session(self, session_token: str) -> SnapshotLock:
        """
        Bind this lock to a session token.
        
        Returns new SnapshotLock with session_token set.
        """
        if self.session_token is not None:
            raise SnapshotAlreadyBoundError(
                f"Snapshot already bound to session: {self.session_token}"
            )
        
        return replace(self, session_token=session_token)


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT STATE — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SnapshotState:
    """
    Immutable snapshot ingestion state.
    
    Tracks all ingestion steps and lock status.
    Mutations return new SnapshotState instances.
    """
    
    # Metadata
    metadata: Optional[SnapshotMetadata] = None
    
    # Step completion tracking
    received: bool = False
    hash_verified: bool = False
    manifest_validated: bool = False
    locked: bool = False
    
    # Lock binding
    lock: Optional[SnapshotLock] = None
    
    # Status
    status: SnapshotStatus = SnapshotStatus.NOT_INGESTED
    
    # Timing
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    
    # Drift detection
    drift_detected: bool = False
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPUTED PROPERTIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def is_ingested(self) -> bool:
        """True if snapshot has been fully ingested and locked."""
        return (
            self.received
            and self.hash_verified
            and self.manifest_validated
            and self.locked
            and self.lock is not None
        )
    
    @property
    def is_locked(self) -> bool:
        """True if snapshot is locked."""
        return self.locked and self.lock is not None
    
    @property
    def snapshot_id(self) -> Optional[str]:
        """Get snapshot ID if metadata present."""
        return self.metadata.snapshot_id if self.metadata else None
    
    @property
    def archive_hash(self) -> Optional[str]:
        """Get archive hash if metadata present."""
        return self.metadata.archive_hash if self.metadata else None
    
    @property
    def completed_steps(self) -> List[SnapshotLockStep]:
        """List of completed steps."""
        steps = []
        if self.received:
            steps.append(SnapshotLockStep.SNAP_01)
        if self.hash_verified:
            steps.append(SnapshotLockStep.SNAP_02)
        if self.manifest_validated:
            steps.append(SnapshotLockStep.SNAP_03)
        if self.locked:
            steps.append(SnapshotLockStep.SNAP_04)
        return steps
    
    @property
    def missing_steps(self) -> List[SnapshotLockStep]:
        """List of incomplete steps."""
        missing = []
        if not self.received:
            missing.append(SnapshotLockStep.SNAP_01)
        if not self.hash_verified:
            missing.append(SnapshotLockStep.SNAP_02)
        if not self.manifest_validated:
            missing.append(SnapshotLockStep.SNAP_03)
        if not self.locked:
            missing.append(SnapshotLockStep.SNAP_04)
        return missing
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATE TRANSITIONS — RETURN NEW INSTANCES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def receive(self, metadata: SnapshotMetadata) -> SnapshotState:
        """
        Mark snapshot as received (SNAP-01).
        
        Returns new state with metadata and received=True.
        """
        if self.locked:
            raise ReingestionForbiddenError(
                "Cannot re-ingest snapshot in locked session"
            )
        
        return replace(
            self,
            metadata=metadata,
            received=True,
            status=SnapshotStatus.RECEIVING,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def verify_hash(self, actual_hash: str) -> SnapshotState:
        """
        Mark hash as verified (SNAP-02).
        
        Returns new state with hash_verified=True.
        Raises SnapshotDriftError if hash mismatch.
        """
        if not self.received:
            raise SnapshotNotReceivedError(
                "Cannot verify hash: snapshot not received"
            )
        
        if self.locked:
            raise ReingestionForbiddenError(
                "Cannot re-verify hash in locked session"
            )
        
        expected = self.metadata.archive_hash
        if actual_hash != expected:
            return replace(
                self,
                status=SnapshotStatus.DRIFT_DETECTED,
                drift_detected=True,
                expected_hash=expected,
                actual_hash=actual_hash,
                failed_at=datetime.now(timezone.utc).isoformat(),
                failure_reason=f"Hash mismatch: expected {expected}, got {actual_hash}",
            )
        
        return replace(
            self,
            hash_verified=True,
            status=SnapshotStatus.VERIFYING,
        )
    
    def validate_manifest(self) -> SnapshotState:
        """
        Mark manifest as validated (SNAP-03).
        
        Returns new state with manifest_validated=True.
        """
        if not self.hash_verified:
            raise SnapshotHashNotVerifiedError(
                "Cannot validate manifest: hash not verified"
            )
        
        if self.locked:
            raise ReingestionForbiddenError(
                "Cannot re-validate manifest in locked session"
            )
        
        return replace(
            self,
            manifest_validated=True,
        )
    
    def lock_snapshot(self) -> SnapshotState:
        """
        Lock the snapshot (SNAP-04).
        
        All prior steps must be completed before locking.
        Returns new state with locked=True and lock binding created.
        """
        if self.locked:
            raise ReingestionForbiddenError(
                "Snapshot already locked"
            )
        
        if not self.manifest_validated:
            raise SnapshotManifestNotValidatedError(
                "Cannot lock: manifest not validated"
            )
        
        lock = SnapshotLock(
            metadata=self.metadata,
            locked_at=datetime.now(timezone.utc).isoformat(),
        )
        
        return replace(
            self,
            locked=True,
            lock=lock,
            status=SnapshotStatus.LOCKED,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def bind_to_session(self, session_token: str) -> SnapshotState:
        """
        Bind locked snapshot to session token.
        
        Returns new state with session binding.
        """
        if not self.locked or self.lock is None:
            raise SnapshotNotLockedError(
                "Cannot bind: snapshot not locked"
            )
        
        bound_lock = self.lock.bind_to_session(session_token)
        return replace(self, lock=bound_lock)
    
    def detect_drift(self, expected: str, actual: str) -> SnapshotState:
        """
        Record drift detection.
        
        Returns new state with drift_detected=True.
        """
        return replace(
            self,
            status=SnapshotStatus.DRIFT_DETECTED,
            drift_detected=True,
            expected_hash=expected,
            actual_hash=actual,
            failed_at=datetime.now(timezone.utc).isoformat(),
            failure_reason=f"Drift detected: expected {expected}, got {actual}",
        )
    
    def fail(self, reason: str) -> SnapshotState:
        """
        Mark ingestion as failed.
        
        Returns new state with status FAILED.
        """
        return replace(
            self,
            status=SnapshotStatus.FAILED,
            failed_at=datetime.now(timezone.utc).isoformat(),
            failure_reason=reason,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT BUILDER — FLUENT API
# ═══════════════════════════════════════════════════════════════════════════════

class SnapshotBuilder:
    """
    Fluent builder for snapshot ingestion.
    
    Guides through SNAP-01 → SNAP-04 sequence.
    """
    
    def __init__(self):
        self._state = SnapshotState()
    
    @property
    def state(self) -> SnapshotState:
        """Get current state."""
        return self._state
    
    def receive(
        self,
        source: str,
        archive_hash: str,
        file_count: int = 0,
        total_size: int = 0,
    ) -> SnapshotBuilder:
        """SNAP-01: Receive snapshot metadata."""
        metadata = SnapshotMetadata.create(
            source=source,
            archive_hash=archive_hash,
            file_count=file_count,
            total_size=total_size,
        )
        self._state = self._state.receive(metadata)
        return self
    
    def verify_hash(self, actual_hash: str) -> SnapshotBuilder:
        """SNAP-02: Verify archive hash."""
        self._state = self._state.verify_hash(actual_hash)
        return self
    
    def validate_manifest(self) -> SnapshotBuilder:
        """SNAP-03: Validate manifest."""
        self._state = self._state.validate_manifest()
        return self
    
    def lock(self) -> SnapshotState:
        """SNAP-04: Lock snapshot and return final state."""
        self._state = self._state.lock_snapshot()
        return self._state


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SnapshotError(Exception):
    """Base exception for snapshot errors."""
    pass


class SnapshotRequiredError(SnapshotError):
    """Raised when snapshot is required but missing."""
    
    def __init__(self, message: str = "Snapshot ingestion required before bootstrap"):
        super().__init__(f"HARD FAIL: {message}")


class SnapshotNotReceivedError(SnapshotError):
    """Raised when snapshot not yet received."""
    
    def __init__(self, message: str = "Snapshot not received"):
        super().__init__(f"HARD FAIL: {message}")


class SnapshotHashNotVerifiedError(SnapshotError):
    """Raised when hash not yet verified."""
    
    def __init__(self, message: str = "Hash not verified"):
        super().__init__(f"HARD FAIL: {message}")


class SnapshotManifestNotValidatedError(SnapshotError):
    """Raised when manifest not yet validated."""
    
    def __init__(self, message: str = "Manifest not validated"):
        super().__init__(f"HARD FAIL: {message}")


class SnapshotNotLockedError(SnapshotError):
    """Raised when snapshot not locked."""
    
    def __init__(self, message: str = "Snapshot not locked"):
        super().__init__(f"HARD FAIL: {message}")


class SnapshotDriftError(SnapshotError):
    """Raised when snapshot drift is detected."""
    
    def __init__(self, expected: str, actual: str):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"HARD FAIL: Snapshot drift detected. "
            f"Expected hash: {expected}, actual: {actual}. "
            f"Session terminated."
        )


class ReingestionForbiddenError(SnapshotError):
    """Raised when re-ingestion is attempted on locked session."""
    
    def __init__(self, message: str = "Re-ingestion forbidden in locked session"):
        super().__init__(f"HARD FAIL: {message}")


class SnapshotAlreadyBoundError(SnapshotError):
    """Raised when snapshot is already bound to session."""
    
    def __init__(self, message: str = "Snapshot already bound"):
        super().__init__(f"HARD FAIL: {message}")


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_current_snapshot: Optional[SnapshotState] = None


def get_current_snapshot() -> Optional[SnapshotState]:
    """Get current snapshot state."""
    return _current_snapshot


def set_current_snapshot(state: SnapshotState) -> None:
    """Set current snapshot state."""
    global _current_snapshot
    _current_snapshot = state


def clear_current_snapshot() -> None:
    """Clear current snapshot state."""
    global _current_snapshot
    _current_snapshot = None


def require_locked_snapshot() -> SnapshotState:
    """
    Require a locked snapshot.
    
    HARD FAIL if snapshot not ingested or not locked.
    """
    snapshot = get_current_snapshot()
    if snapshot is None:
        raise SnapshotRequiredError("No snapshot ingested")
    if not snapshot.is_locked:
        raise SnapshotNotLockedError("Snapshot not locked")
    return snapshot


# ═══════════════════════════════════════════════════════════════════════════════
# HASH UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_hash(data: bytes) -> str:
    """Calculate SHA-256 hash of data."""
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def verify_hash(expected: str, actual: str) -> bool:
    """Verify hash matches."""
    return expected == actual


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT CHECKERS
# ═══════════════════════════════════════════════════════════════════════════════

INVARIANTS: FrozenSet[str] = frozenset([
    "INV-SNAP-001",  # No PAC execution without snapshot ingestion
    "INV-SNAP-002",  # Snapshot hash must match archive before lock
    "INV-SNAP-003",  # Snapshot is immutable per session
    "INV-SNAP-004",  # Re-ingestion mid-session is forbidden
    "INV-SNAP-005",  # Hash mismatch invalidates session immediately
    "INV-SNAP-006",  # Missing snapshot blocks bootstrap (FAIL-CLOSED)
])


def check_invariant_snap_001(snapshot: Optional[SnapshotState]) -> bool:
    """INV-SNAP-001: No PAC execution without snapshot ingestion."""
    return snapshot is not None and snapshot.is_locked


def check_invariant_snap_002(expected: str, actual: str) -> bool:
    """INV-SNAP-002: Snapshot hash must match archive before lock."""
    return expected == actual


def check_invariant_snap_003(snapshot: SnapshotState) -> bool:
    """INV-SNAP-003: Snapshot is immutable per session."""
    return snapshot.status != SnapshotStatus.DRIFT_DETECTED


def check_invariant_snap_004(snapshot: SnapshotState, is_reingestion: bool) -> bool:
    """INV-SNAP-004: Re-ingestion mid-session is forbidden."""
    if snapshot.is_locked and is_reingestion:
        return False
    return True


def check_invariant_snap_006(snapshot: Optional[SnapshotState]) -> bool:
    """INV-SNAP-006: Missing snapshot blocks bootstrap (FAIL-CLOSED)."""
    return snapshot is not None and snapshot.is_locked


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "SnapshotLockStep",
    "SnapshotStatus",
    "STEP_NAMES",
    
    # Classes
    "SnapshotMetadata",
    "SnapshotLock",
    "SnapshotState",
    "SnapshotBuilder",
    
    # Exceptions
    "SnapshotError",
    "SnapshotRequiredError",
    "SnapshotNotReceivedError",
    "SnapshotHashNotVerifiedError",
    "SnapshotManifestNotValidatedError",
    "SnapshotNotLockedError",
    "SnapshotDriftError",
    "ReingestionForbiddenError",
    "SnapshotAlreadyBoundError",
    
    # Session management
    "get_current_snapshot",
    "set_current_snapshot",
    "clear_current_snapshot",
    "require_locked_snapshot",
    
    # Hash utilities
    "calculate_hash",
    "calculate_file_hash",
    "verify_hash",
    
    # Invariants
    "INVARIANTS",
    "check_invariant_snap_001",
    "check_invariant_snap_002",
    "check_invariant_snap_003",
    "check_invariant_snap_004",
    "check_invariant_snap_006",
]
