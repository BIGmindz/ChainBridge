"""
ChainBridge Bootstrap Enforcer — Programmatic Bootstrap Validator
════════════════════════════════════════════════════════════════════════════════

Blocks PAC execution unless bootstrap acknowledged.
Emits PAG-style terminal output for all bootstrap operations.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-BOOTSTRAP-PROTOCOL-016
Effective Date: 2025-12-26

ENFORCEMENT RULES:
- No PAC execution without sealed bootstrap
- Partial bootstrap equals no bootstrap (FAIL-CLOSED)
- Re-bootstrap mid-session terminates session
- All operations emit terminal output

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import functools
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, FrozenSet, List, Optional, Set, TypeVar

from core.governance.bootstrap_state import (
    LOCK_NAMES,
    BootstrapBuilder,
    BootstrapError,
    BootstrapIncompleteError,
    BootstrapLock,
    BootstrapRequiredError,
    BootstrapState,
    BootstrapStatus,
    BootstrapValidationError,
    LockAlreadyAcquiredError,
    RebootstrapForbiddenError,
    clear_current_session,
    get_current_session,
    require_sealed_session,
    set_current_session,
)
from core.governance.snapshot_state import (
    SnapshotRequiredError,
    get_current_snapshot,
)
from core.governance.gid_registry import (
    GIDRegistry,
    validate_agent_gid,
    validate_agent_lane,
    validate_agent_mode,
)
from core.governance.terminal_gates import (
    BORDER_CHAR,
    BORDER_WIDTH,
    FAIL_SYMBOL,
    PASS_SYMBOL,
    TerminalGateRenderer,
    get_terminal_renderer,
)
from core.governance.tool_matrix import ToolMatrix, evaluate_tools


# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP TERMINAL RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

class BootstrapTerminalRenderer:
    """
    Terminal renderer for bootstrap operations.
    
    Extends TerminalGateRenderer with bootstrap-specific output.
    """
    
    def __init__(self, renderer: TerminalGateRenderer = None):
        self._renderer = renderer or get_terminal_renderer()
    
    def _emit(self, text: str) -> None:
        """Emit text via base renderer."""
        self._renderer._emit(text)
    
    def emit_bootstrap_start(self) -> None:
        """Emit bootstrap sequence start."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🔐 BOOTSTRAP SEQUENCE INITIATED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_lock_acquired(
        self,
        lock: BootstrapLock,
        value: str,
    ) -> None:
        """Emit lock acquisition."""
        lock_name = LOCK_NAMES[lock]
        self._emit(f"{lock.value}  {lock_name:<20} {PASS_SYMBOL} LOCKED  {value}")
    
    def emit_lock_failed(
        self,
        lock: BootstrapLock,
        reason: str,
    ) -> None:
        """Emit lock failure."""
        lock_name = LOCK_NAMES[lock]
        self._emit(f"{lock.value}  {lock_name:<20} {FAIL_SYMBOL} FAILED  {reason}")
    
    def emit_bootstrap_complete(self, state: BootstrapState) -> None:
        """Emit bootstrap complete."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟩 BOOTSTRAP COMPLETE — SESSION SEALED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"TOKEN:       {state.bootstrap_token}")
        self._emit(f"IDENTITY:    {state.gid} ({state.role})")
        self._emit(f"MODE:        {state.mode}")
        self._emit(f"LANE:        {state.lane}")
        self._emit(f"TOOLS:       {len(state.permitted_tools)} permitted, {len(state.stripped_tools)} stripped")
        self._emit(f"STATUS:      READY_FOR_PAC")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_bootstrap_failed(
        self,
        reason: str,
        failed_locks: List[BootstrapLock] = None,
    ) -> None:
        """Emit bootstrap failure."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟥 BOOTSTRAP FAILED — SESSION NOT SEALED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"REASON:      {reason}")
        if failed_locks:
            self._emit("FAILED_LOCKS:")
            for lock in failed_locks:
                self._emit(f"   └─ {lock.value}: {LOCK_NAMES[lock]}")
        self._emit("ACTION:      BOOTSTRAP_REQUIRED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_rebootstrap_blocked(self) -> None:
        """Emit re-bootstrap attempt blocked."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟥 RE-BOOTSTRAP FORBIDDEN — SESSION TERMINATED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("REASON:      Cannot re-bootstrap sealed session")
        self._emit("ACTION:      NEW_SESSION_REQUIRED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_pac_blocked(self, reason: str) -> None:
        """Emit PAC execution blocked."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟥 PAC EXECUTION BLOCKED — BOOTSTRAP REQUIRED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"REASON:      {reason}")
        self._emit("ACTION:      COMPLETE_BOOTSTRAP_FIRST")
        self._emit(BORDER_CHAR * BORDER_WIDTH)

    def emit_snapshot_required(self) -> None:
        """Emit snapshot required before bootstrap."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟥 BOOTSTRAP BLOCKED — SNAPSHOT REQUIRED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("REASON:      No snapshot ingested")
        self._emit("ACTION:      INGEST_SNAPSHOT_FIRST")
        self._emit(BORDER_CHAR * BORDER_WIDTH)


# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BootstrapResult:
    """Result of bootstrap attempt."""
    
    success: bool
    state: BootstrapState
    message: str
    failed_locks: List[BootstrapLock] = None
    
    @property
    def token(self) -> Optional[str]:
        """Get bootstrap token if successful."""
        if self.success and self.state.is_sealed:
            return self.state.bootstrap_token
        return None


class BootstrapEnforcer:
    """
    Programmatic bootstrap validator.
    
    Blocks PAC execution unless bootstrap acknowledged.
    Validates identity, mode, lane, and tools against registry.
    """
    
    def __init__(
        self,
        registry: GIDRegistry = None,
        tool_matrix: ToolMatrix = None,
        renderer: BootstrapTerminalRenderer = None,
    ):
        self._registry = registry or GIDRegistry()
        self._tool_matrix = tool_matrix or ToolMatrix()
        self._renderer = renderer or BootstrapTerminalRenderer()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def validate_gid(self, gid: str) -> bool:
        """Validate GID against registry."""
        try:
            validate_agent_gid(gid)
            return True
        except Exception:
            return False
    
    def validate_mode(self, gid: str, mode: str) -> bool:
        """Validate mode is permitted for GID."""
        try:
            validate_agent_mode(gid, mode)
            return True
        except Exception:
            return False
    
    def validate_lane(self, gid: str, lane: str) -> bool:
        """Validate lane is permitted for GID."""
        try:
            validate_agent_lane(gid, lane)
            return True
        except Exception:
            return False
    
    def get_agent_role(self, gid: str) -> Optional[str]:
        """Get role for GID from registry."""
        try:
            agent = self._registry.get_agent(gid)
            return agent.role if agent else None
        except Exception:
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BOOTSTRAP EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def bootstrap(
        self,
        gid: str,
        mode: str,
        lane: str,
        available_tools: Set[str] = None,
        skip_snapshot_check: bool = False,
    ) -> BootstrapResult:
        """
        Execute full bootstrap sequence.
        
        Validates identity, mode, lane, strips tools, completes handshake,
        and seals session.
        
        PREREQUISITE: Snapshot must be ingested and locked before bootstrap.
        
        Returns BootstrapResult with success/failure status.
        """
        # PRE-BOOT: Check for locked snapshot (mandatory prerequisite)
        if not skip_snapshot_check:
            snapshot = get_current_snapshot()
            if snapshot is None or not snapshot.is_locked:
                self._renderer.emit_snapshot_required()
                raise SnapshotRequiredError(
                    "Cannot bootstrap without locked snapshot — ingest snapshot first"
                )
        
        # Check for re-bootstrap attempt
        current = get_current_session()
        if current and current.is_sealed:
            self._renderer.emit_rebootstrap_blocked()
            # Terminate the session
            terminated = current.terminate()
            set_current_session(terminated)
            raise RebootstrapForbiddenError(
                "Cannot re-bootstrap sealed session — session terminated"
            )
        
        self._renderer.emit_bootstrap_start()
        
        failed_locks: List[BootstrapLock] = []
        builder = BootstrapBuilder()
        
        # BOOT-01: Identity Lock
        if not self.validate_gid(gid):
            self._renderer.emit_lock_failed(
                BootstrapLock.BOOT_01,
                f"Invalid GID: {gid}",
            )
            failed_locks.append(BootstrapLock.BOOT_01)
        else:
            role = self.get_agent_role(gid) or "Unknown"
            try:
                builder.with_identity(gid, role)
                self._renderer.emit_lock_acquired(
                    BootstrapLock.BOOT_01,
                    gid,
                )
            except LockAlreadyAcquiredError as e:
                self._renderer.emit_lock_failed(BootstrapLock.BOOT_01, str(e))
                failed_locks.append(BootstrapLock.BOOT_01)
        
        # BOOT-02: Mode Lock
        if failed_locks:
            # Can't validate mode without valid GID
            self._renderer.emit_lock_failed(
                BootstrapLock.BOOT_02,
                "Blocked by prior failure",
            )
            failed_locks.append(BootstrapLock.BOOT_02)
        elif not self.validate_mode(gid, mode):
            self._renderer.emit_lock_failed(
                BootstrapLock.BOOT_02,
                f"Mode {mode} not permitted for {gid}",
            )
            failed_locks.append(BootstrapLock.BOOT_02)
        else:
            try:
                builder.with_mode(mode)
                self._renderer.emit_lock_acquired(
                    BootstrapLock.BOOT_02,
                    mode,
                )
            except LockAlreadyAcquiredError as e:
                self._renderer.emit_lock_failed(BootstrapLock.BOOT_02, str(e))
                failed_locks.append(BootstrapLock.BOOT_02)
        
        # BOOT-03: Lane Lock
        if BootstrapLock.BOOT_01 in failed_locks:
            # Can't validate lane without valid GID
            self._renderer.emit_lock_failed(
                BootstrapLock.BOOT_03,
                "Blocked by prior failure",
            )
            failed_locks.append(BootstrapLock.BOOT_03)
        elif not self.validate_lane(gid, lane):
            self._renderer.emit_lock_failed(
                BootstrapLock.BOOT_03,
                f"Lane {lane} not permitted for {gid}",
            )
            failed_locks.append(BootstrapLock.BOOT_03)
        else:
            try:
                builder.with_lane(lane)
                self._renderer.emit_lock_acquired(
                    BootstrapLock.BOOT_03,
                    lane,
                )
            except LockAlreadyAcquiredError as e:
                self._renderer.emit_lock_failed(BootstrapLock.BOOT_03, str(e))
                failed_locks.append(BootstrapLock.BOOT_03)
        
        # BOOT-04: Tool Strip
        if BootstrapLock.BOOT_02 in failed_locks or BootstrapLock.BOOT_03 in failed_locks:
            self._renderer.emit_lock_failed(
                BootstrapLock.BOOT_04,
                "Blocked by prior failure",
            )
            failed_locks.append(BootstrapLock.BOOT_04)
        else:
            # Get tool matrix result for mode+lane
            result = evaluate_tools(mode, lane)
            # Convert ToolCategory enums to strings
            permitted = frozenset(t.value for t in result.allowed_tools)
            stripped = frozenset(t.value for t in result.denied_tools)
            
            try:
                builder.with_tools(permitted, stripped)
                self._renderer.emit_lock_acquired(
                    BootstrapLock.BOOT_04,
                    f"{len(permitted)} tools permitted",
                )
            except LockAlreadyAcquiredError as e:
                self._renderer.emit_lock_failed(BootstrapLock.BOOT_04, str(e))
                failed_locks.append(BootstrapLock.BOOT_04)
        
        # BOOT-05: Echo Handshake
        if failed_locks:
            self._renderer.emit_lock_failed(
                BootstrapLock.BOOT_05,
                "Blocked by prior failure",
            )
            failed_locks.append(BootstrapLock.BOOT_05)
        else:
            state = builder.build()
            handshake = f"{state.gid} | {state.mode} | {state.lane}"
            try:
                builder.with_handshake(handshake)
                self._renderer.emit_lock_acquired(
                    BootstrapLock.BOOT_05,
                    handshake,
                )
            except LockAlreadyAcquiredError as e:
                self._renderer.emit_lock_failed(BootstrapLock.BOOT_05, str(e))
                failed_locks.append(BootstrapLock.BOOT_05)
        
        # Attempt seal
        if failed_locks:
            state = builder.build().fail(f"Failed locks: {[l.value for l in failed_locks]}")
            self._renderer.emit_bootstrap_failed(
                "One or more locks failed",
                failed_locks,
            )
            set_current_session(state)
            return BootstrapResult(
                success=False,
                state=state,
                message=f"Bootstrap failed: {len(failed_locks)} locks failed",
                failed_locks=failed_locks,
            )
        
        try:
            sealed = builder.seal()
            set_current_session(sealed)
            self._renderer.emit_bootstrap_complete(sealed)
            return BootstrapResult(
                success=True,
                state=sealed,
                message="Bootstrap complete — session sealed",
            )
        except BootstrapIncompleteError as e:
            state = builder.build().fail(str(e))
            self._renderer.emit_bootstrap_failed(str(e))
            set_current_session(state)
            return BootstrapResult(
                success=False,
                state=state,
                message=str(e),
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PAC GATE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def require_bootstrap(self) -> BootstrapState:
        """
        Require sealed bootstrap for PAC execution.
        
        Raises BootstrapRequiredError if not bootstrapped.
        Emits terminal output on failure.
        """
        try:
            return require_sealed_session()
        except BootstrapRequiredError as e:
            self._renderer.emit_pac_blocked(str(e))
            raise
    
    def is_bootstrapped(self) -> bool:
        """Check if current session is bootstrapped."""
        session = get_current_session()
        return session is not None and session.is_sealed


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATOR FOR PAC GATE
# ═══════════════════════════════════════════════════════════════════════════════

F = TypeVar("F", bound=Callable)


def requires_bootstrap(func: F) -> F:
    """
    Decorator that requires bootstrap before function execution.
    
    Raises BootstrapRequiredError if not bootstrapped.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        enforcer = get_bootstrap_enforcer()
        enforcer.require_bootstrap()
        return func(*args, **kwargs)
    return wrapper  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

@contextmanager
def bootstrap_session(
    gid: str,
    mode: str,
    lane: str,
    available_tools: Set[str] = None,
):
    """
    Context manager for bootstrap session.
    
    Bootstraps on enter, clears session on exit.
    Raises BootstrapError if bootstrap fails.
    
    Usage:
        with bootstrap_session("GID-01", "EXECUTION", "GOVERNANCE"):
            # Execute PAC here
            pass
    """
    enforcer = get_bootstrap_enforcer()
    
    result = enforcer.bootstrap(gid, mode, lane, available_tools)
    
    if not result.success:
        raise BootstrapError(result.message)
    
    try:
        yield result.state
    finally:
        clear_current_session()


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_enforcer: Optional[BootstrapEnforcer] = None


def get_bootstrap_enforcer() -> BootstrapEnforcer:
    """Get singleton bootstrap enforcer."""
    global _enforcer
    if _enforcer is None:
        _enforcer = BootstrapEnforcer()
    return _enforcer


def reset_bootstrap_enforcer() -> None:
    """Reset singleton (for testing)."""
    global _enforcer
    _enforcer = None
    clear_current_session()


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def bootstrap(
    gid: str,
    mode: str,
    lane: str,
    available_tools: Set[str] = None,
) -> BootstrapResult:
    """Execute bootstrap sequence."""
    return get_bootstrap_enforcer().bootstrap(gid, mode, lane, available_tools)


def require_bootstrap_before_pac() -> BootstrapState:
    """Require bootstrap for PAC execution."""
    return get_bootstrap_enforcer().require_bootstrap()


def is_session_bootstrapped() -> bool:
    """Check if current session is bootstrapped."""
    return get_bootstrap_enforcer().is_bootstrapped()


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Classes
    "BootstrapEnforcer",
    "BootstrapTerminalRenderer",
    "BootstrapResult",
    
    # Decorator
    "requires_bootstrap",
    
    # Context manager
    "bootstrap_session",
    
    # Singleton
    "get_bootstrap_enforcer",
    "reset_bootstrap_enforcer",
    
    # Convenience functions
    "bootstrap",
    "require_bootstrap_before_pac",
    "is_session_bootstrapped",
]
