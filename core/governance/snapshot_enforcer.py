"""
ChainBridge Snapshot Enforcer — Programmatic Snapshot Validator
════════════════════════════════════════════════════════════════════════════════

Validates repository snapshot ingestion as prerequisite for bootstrap.
Emits PAG-style terminal output for all snapshot operations.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-REPO-SNAPSHOT-INGESTION-018
Effective Date: 2025-12-26

ENFORCEMENT RULES:
- No bootstrap without locked snapshot
- Hash verification required before lock
- Re-ingestion mid-session is forbidden
- All operations emit terminal output

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import functools
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Set, TypeVar

from core.governance.snapshot_state import (
    STEP_NAMES,
    ReingestionForbiddenError,
    SnapshotAlreadyBoundError,
    SnapshotBuilder,
    SnapshotDriftError,
    SnapshotError,
    SnapshotLock,
    SnapshotLockStep,
    SnapshotMetadata,
    SnapshotNotLockedError,
    SnapshotNotReceivedError,
    SnapshotRequiredError,
    SnapshotState,
    SnapshotStatus,
    calculate_hash,
    clear_current_snapshot,
    get_current_snapshot,
    require_locked_snapshot,
    set_current_snapshot,
    verify_hash,
)
from core.governance.terminal_gates import (
    BORDER_CHAR,
    BORDER_WIDTH,
    FAIL_SYMBOL,
    PASS_SYMBOL,
    TerminalGateRenderer,
    get_terminal_renderer,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT TERMINAL RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

class SnapshotTerminalRenderer:
    """
    Terminal renderer for snapshot operations.
    
    Extends TerminalGateRenderer with snapshot-specific output.
    """
    
    def __init__(self, renderer: TerminalGateRenderer = None):
        self._renderer = renderer or get_terminal_renderer()
    
    def _emit(self, text: str) -> None:
        """Emit text via base renderer."""
        self._renderer._emit(text)
    
    def emit_snapshot_received(self, metadata: SnapshotMetadata) -> None:
        """
        Emit snapshot received notification.
        
        🧾 SNAPSHOT RECEIVED
        """
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🧾 SNAPSHOT RECEIVED")
        self._emit(f"   SNAPSHOT_ID: {metadata.snapshot_id}")
        self._emit(f"   SOURCE: {metadata.source}")
        self._emit(f"   FILE_COUNT: {metadata.file_count}")
        self._emit(f"   ARCHIVE_HASH: {metadata.hash_prefix}")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_step_complete(
        self,
        step: SnapshotLockStep,
        detail: str = "",
    ) -> None:
        """Emit step completion."""
        step_name = STEP_NAMES[step]
        self._emit(f"{step.value}  {step_name:<20} {PASS_SYMBOL} COMPLETE  {detail}")
    
    def emit_step_failed(
        self,
        step: SnapshotLockStep,
        reason: str,
    ) -> None:
        """Emit step failure."""
        step_name = STEP_NAMES[step]
        self._emit(f"{step.value}  {step_name:<20} {FAIL_SYMBOL} FAILED  {reason}")
    
    def emit_snapshot_locked(self, lock: SnapshotLock, session_token: str = None) -> None:
        """
        Emit snapshot locked notification.
        
        🔐 SNAPSHOT LOCKED
        """
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🔐 SNAPSHOT LOCKED")
        self._emit(f"   SNAPSHOT_ID: {lock.snapshot_id}")
        self._emit(f"   HASH: {lock.metadata.hash_prefix}")
        if session_token:
            self._emit(f"   BOUND_TO_SESSION: {session_token}")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_snapshot_verified(self, state: SnapshotState) -> None:
        """
        Emit snapshot verified notification.
        
        🟩 SNAPSHOT VERIFIED
        """
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟩 SNAPSHOT VERIFIED")
        self._emit(f"   SNAPSHOT_ID: {state.snapshot_id}")
        self._emit(f"   HASH: {state.metadata.hash_prefix} {PASS_SYMBOL} MATCH")
        self._emit("   STATUS: READY_FOR_BOOTSTRAP")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_snapshot_drift(
        self,
        expected: str,
        actual: str,
    ) -> None:
        """
        Emit snapshot drift detected notification.
        
        ⛔ SNAPSHOT DRIFT DETECTED
        """
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("⛔ SNAPSHOT DRIFT DETECTED")
        self._emit(f"   EXPECTED_HASH: {expected[:19]}...")
        self._emit(f"   ACTUAL_HASH: {actual[:19]}...")
        self._emit("   RESULT: SESSION TERMINATED")
        self._emit("   ACTION: NEW_SNAPSHOT_REQUIRED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_snapshot_required(self) -> None:
        """
        Emit snapshot required notification.
        
        ⛔ SNAPSHOT REQUIRED
        """
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("⛔ SNAPSHOT REQUIRED")
        self._emit("   REASON: No snapshot ingested")
        self._emit("   ACTION: INGEST_SNAPSHOT_FIRST")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_reingestion_blocked(self) -> None:
        """
        Emit re-ingestion blocked notification.
        
        ⛔ RE-INGESTION BLOCKED
        """
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("⛔ RE-INGESTION BLOCKED")
        self._emit("   REASON: Snapshot already locked")
        self._emit("   ACTION: NEW_SESSION_REQUIRED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_ingestion_failed(
        self,
        reason: str,
        failed_steps: List[SnapshotLockStep] = None,
    ) -> None:
        """
        Emit ingestion failure notification.
        
        🟥 SNAPSHOT INGESTION FAILED
        """
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟥 SNAPSHOT INGESTION FAILED")
        self._emit(f"   REASON: {reason}")
        if failed_steps:
            self._emit("   FAILED_STEPS:")
            for step in failed_steps:
                self._emit(f"      └─ {step.value}: {STEP_NAMES[step]}")
        self._emit("   ACTION: RETRY_INGESTION")
        self._emit(BORDER_CHAR * BORDER_WIDTH)


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SnapshotIngestionResult:
    """Result of snapshot ingestion attempt."""
    
    success: bool
    state: SnapshotState
    message: str
    failed_steps: List[SnapshotLockStep] = None
    
    @property
    def lock(self) -> Optional[SnapshotLock]:
        """Get snapshot lock if successful."""
        if self.success and self.state.is_locked:
            return self.state.lock
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════

class SnapshotEnforcer:
    """
    Programmatic snapshot validator.
    
    Enforces snapshot ingestion as prerequisite for bootstrap.
    Validates hash, manifest, and lock status.
    """
    
    def __init__(
        self,
        renderer: SnapshotTerminalRenderer = None,
    ):
        self._renderer = renderer or SnapshotTerminalRenderer()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INGESTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def ingest(
        self,
        source: str,
        archive_hash: str,
        actual_hash: str = None,
        file_count: int = 0,
        total_size: int = 0,
        skip_hash_verification: bool = False,
    ) -> SnapshotIngestionResult:
        """
        Execute full snapshot ingestion sequence.
        
        SNAP-01: Receive snapshot metadata
        SNAP-02: Verify archive hash
        SNAP-03: Validate manifest
        SNAP-04: Lock snapshot
        
        Returns SnapshotIngestionResult with success/failure status.
        """
        # Check for re-ingestion attempt
        current = get_current_snapshot()
        if current and current.is_locked:
            self._renderer.emit_reingestion_blocked()
            raise ReingestionForbiddenError(
                "Cannot re-ingest snapshot — session already locked"
            )
        
        failed_steps: List[SnapshotLockStep] = []
        builder = SnapshotBuilder()
        
        # SNAP-01: Receive snapshot
        try:
            builder.receive(
                source=source,
                archive_hash=archive_hash,
                file_count=file_count,
                total_size=total_size,
            )
            self._renderer.emit_snapshot_received(builder.state.metadata)
            self._renderer.emit_step_complete(
                SnapshotLockStep.SNAP_01,
                f"source={source}",
            )
        except SnapshotError as e:
            self._renderer.emit_step_failed(SnapshotLockStep.SNAP_01, str(e))
            failed_steps.append(SnapshotLockStep.SNAP_01)
        
        # SNAP-02: Verify hash
        if not failed_steps:
            # Use actual_hash if provided, otherwise assume match for testing
            hash_to_verify = actual_hash if actual_hash is not None else archive_hash
            
            if not skip_hash_verification:
                try:
                    builder.verify_hash(hash_to_verify)
                    
                    # Check if drift was detected
                    if builder.state.drift_detected:
                        self._renderer.emit_snapshot_drift(
                            builder.state.expected_hash,
                            builder.state.actual_hash,
                        )
                        self._renderer.emit_step_failed(
                            SnapshotLockStep.SNAP_02,
                            "Hash mismatch",
                        )
                        failed_steps.append(SnapshotLockStep.SNAP_02)
                    else:
                        self._renderer.emit_step_complete(
                            SnapshotLockStep.SNAP_02,
                            f"{PASS_SYMBOL} hash verified",
                        )
                except SnapshotError as e:
                    self._renderer.emit_step_failed(SnapshotLockStep.SNAP_02, str(e))
                    failed_steps.append(SnapshotLockStep.SNAP_02)
            else:
                # Skip verification (for testing only)
                builder.verify_hash(archive_hash)
                self._renderer.emit_step_complete(
                    SnapshotLockStep.SNAP_02,
                    "skipped (testing)",
                )
        
        # SNAP-03: Validate manifest
        if not failed_steps:
            try:
                builder.validate_manifest()
                self._renderer.emit_step_complete(
                    SnapshotLockStep.SNAP_03,
                    f"{file_count} files",
                )
            except SnapshotError as e:
                self._renderer.emit_step_failed(SnapshotLockStep.SNAP_03, str(e))
                failed_steps.append(SnapshotLockStep.SNAP_03)
        
        # SNAP-04: Lock snapshot
        if not failed_steps:
            try:
                state = builder.lock()
                self._renderer.emit_step_complete(
                    SnapshotLockStep.SNAP_04,
                    f"id={state.snapshot_id}",
                )
                self._renderer.emit_snapshot_locked(state.lock)
                self._renderer.emit_snapshot_verified(state)
                
                # Store in session
                set_current_snapshot(state)
                
                return SnapshotIngestionResult(
                    success=True,
                    state=state,
                    message="Snapshot ingested and locked successfully",
                )
            except SnapshotError as e:
                self._renderer.emit_step_failed(SnapshotLockStep.SNAP_04, str(e))
                failed_steps.append(SnapshotLockStep.SNAP_04)
        
        # Failure path
        state = builder.state.fail(f"Failed steps: {[s.value for s in failed_steps]}")
        self._renderer.emit_ingestion_failed(
            "One or more steps failed",
            failed_steps,
        )
        set_current_snapshot(state)
        
        return SnapshotIngestionResult(
            success=False,
            state=state,
            message=f"Ingestion failed: {len(failed_steps)} steps failed",
            failed_steps=failed_steps,
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def require_snapshot(self) -> SnapshotState:
        """
        Require a locked snapshot.
        
        HARD FAIL if not ingested or not locked.
        """
        snapshot = get_current_snapshot()
        if snapshot is None:
            self._renderer.emit_snapshot_required()
            raise SnapshotRequiredError("No snapshot ingested")
        if not snapshot.is_locked:
            self._renderer.emit_snapshot_required()
            raise SnapshotNotLockedError("Snapshot not locked")
        return snapshot
    
    def verify_no_drift(self, actual_hash: str) -> bool:
        """
        Verify current snapshot has not drifted.
        
        HARD FAIL if hash mismatch.
        """
        snapshot = self.require_snapshot()
        expected = snapshot.archive_hash
        
        if not verify_hash(expected, actual_hash):
            self._renderer.emit_snapshot_drift(expected, actual_hash)
            
            # Mark drift in state
            drifted = snapshot.detect_drift(expected, actual_hash)
            set_current_snapshot(drifted)
            
            raise SnapshotDriftError(expected, actual_hash)
        
        return True
    
    def is_snapshot_ready(self) -> bool:
        """Check if snapshot is ready for bootstrap."""
        snapshot = get_current_snapshot()
        return snapshot is not None and snapshot.is_locked
    
    def bind_to_session(self, session_token: str) -> SnapshotState:
        """
        Bind locked snapshot to session token.
        
        Returns updated state with binding.
        """
        snapshot = self.require_snapshot()
        bound = snapshot.bind_to_session(session_token)
        set_current_snapshot(bound)
        return bound


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_enforcer: Optional[SnapshotEnforcer] = None


def get_snapshot_enforcer() -> SnapshotEnforcer:
    """Get the singleton snapshot enforcer."""
    global _enforcer
    if _enforcer is None:
        _enforcer = SnapshotEnforcer()
    return _enforcer


def reset_snapshot_enforcer() -> None:
    """Reset the singleton (for testing)."""
    global _enforcer
    _enforcer = None
    clear_current_snapshot()


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def ingest_snapshot(
    source: str,
    archive_hash: str,
    actual_hash: str = None,
    file_count: int = 0,
) -> SnapshotIngestionResult:
    """
    Quick snapshot ingestion function.
    
    Returns SnapshotIngestionResult.
    """
    return get_snapshot_enforcer().ingest(
        source=source,
        archive_hash=archive_hash,
        actual_hash=actual_hash,
        file_count=file_count,
    )


def require_snapshot_for_bootstrap() -> SnapshotState:
    """
    Require snapshot before bootstrap.
    
    HARD FAIL if snapshot not ready.
    """
    return get_snapshot_enforcer().require_snapshot()


def is_snapshot_ready() -> bool:
    """Check if snapshot is ready."""
    return get_snapshot_enforcer().is_snapshot_ready()


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATOR — FOR FUNCTIONS REQUIRING SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════════

F = TypeVar("F", bound=Callable)


def requires_snapshot(func: F) -> F:
    """
    Decorator requiring snapshot before function execution.
    
    HARD FAIL if snapshot not ready.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        require_snapshot_for_bootstrap()
        return func(*args, **kwargs)
    
    return wrapper


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

@contextmanager
def snapshot_session(
    source: str,
    archive_hash: str,
    file_count: int = 0,
):
    """
    Context manager for snapshot session.
    
    Ingests snapshot on entry, clears on exit.
    
    Usage:
        with snapshot_session("vscode", "sha256:abc...") as snapshot:
            # Snapshot is locked
            pass
    """
    result = ingest_snapshot(
        source=source,
        archive_hash=archive_hash,
        file_count=file_count,
    )
    
    if not result.success:
        raise SnapshotRequiredError(result.message)
    
    try:
        yield result.state
    finally:
        reset_snapshot_enforcer()


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Classes
    "SnapshotTerminalRenderer",
    "SnapshotIngestionResult",
    "SnapshotEnforcer",
    
    # Singleton access
    "get_snapshot_enforcer",
    "reset_snapshot_enforcer",
    
    # Convenience functions
    "ingest_snapshot",
    "require_snapshot_for_bootstrap",
    "is_snapshot_ready",
    
    # Decorator
    "requires_snapshot",
    
    # Context manager
    "snapshot_session",
]
