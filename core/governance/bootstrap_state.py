"""
ChainBridge Bootstrap State — Immutable Session Model
════════════════════════════════════════════════════════════════════════════════

Tracks bootstrap lock state for session enforcement.
All state is immutable — mutations return new instances.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-BOOTSTRAP-PROTOCOL-016
Effective Date: 2025-12-26

INVARIANTS:
- INV-BOOT-001: No PAC execution without bootstrap
- INV-BOOT-002: Bootstrap is idempotent within session
- INV-BOOT-003: Re-bootstrap mid-session is forbidden
- INV-BOOT-004: Partial bootstrap equals no bootstrap (FAIL-CLOSED)
- INV-BOOT-005: All locks must be acquired atomically

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import FrozenSet, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP LOCK IDENTIFIERS
# ═══════════════════════════════════════════════════════════════════════════════

class BootstrapLock(Enum):
    """Canonical bootstrap lock identifiers."""
    
    BOOT_01 = "BOOT-01"  # Identity Lock
    BOOT_02 = "BOOT-02"  # Mode Lock
    BOOT_03 = "BOOT-03"  # Lane Lock
    BOOT_04 = "BOOT-04"  # Tool Strip
    BOOT_05 = "BOOT-05"  # Echo Handshake


LOCK_NAMES = {
    BootstrapLock.BOOT_01: "Identity Lock",
    BootstrapLock.BOOT_02: "Mode Lock",
    BootstrapLock.BOOT_03: "Lane Lock",
    BootstrapLock.BOOT_04: "Tool Strip",
    BootstrapLock.BOOT_05: "Echo Handshake",
}


class BootstrapStatus(Enum):
    """Bootstrap session status."""
    
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SEALED = "SEALED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


# ═══════════════════════════════════════════════════════════════════════════════
# LOCK STATE — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LockState:
    """
    State of a single bootstrap lock.
    
    Immutable — acquiring a lock returns a new LockState.
    """
    
    lock_id: BootstrapLock
    acquired: bool = False
    value: Optional[str] = None
    acquired_at: Optional[str] = None
    
    @property
    def lock_name(self) -> str:
        """Get canonical name for this lock."""
        return LOCK_NAMES[self.lock_id]
    
    def acquire(self, value: str) -> LockState:
        """
        Acquire this lock with a value.
        
        Returns new LockState — original is unchanged.
        """
        if self.acquired:
            raise LockAlreadyAcquiredError(
                f"Lock {self.lock_id.value} already acquired"
            )
        
        return LockState(
            lock_id=self.lock_id,
            acquired=True,
            value=value,
            acquired_at=datetime.now(timezone.utc).isoformat(),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP STATE — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BootstrapState:
    """
    Immutable bootstrap session state.
    
    Tracks all lock acquisitions and session status.
    Mutations return new BootstrapState instances.
    """
    
    # Identity fields
    gid: Optional[str] = None
    role: Optional[str] = None
    mode: Optional[str] = None
    lane: Optional[str] = None
    
    # Lock states
    identity_lock: LockState = field(
        default_factory=lambda: LockState(BootstrapLock.BOOT_01)
    )
    mode_lock: LockState = field(
        default_factory=lambda: LockState(BootstrapLock.BOOT_02)
    )
    lane_lock: LockState = field(
        default_factory=lambda: LockState(BootstrapLock.BOOT_03)
    )
    tools_lock: LockState = field(
        default_factory=lambda: LockState(BootstrapLock.BOOT_04)
    )
    handshake_lock: LockState = field(
        default_factory=lambda: LockState(BootstrapLock.BOOT_05)
    )
    
    # Tool strip results
    permitted_tools: FrozenSet[str] = field(default_factory=frozenset)
    stripped_tools: FrozenSet[str] = field(default_factory=frozenset)
    
    # Session state
    status: BootstrapStatus = BootstrapStatus.NOT_STARTED
    bootstrap_token: Optional[str] = None
    started_at: Optional[str] = None
    sealed_at: Optional[str] = None
    failed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPUTED PROPERTIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def identity_locked(self) -> bool:
        """True if identity lock acquired."""
        return self.identity_lock.acquired
    
    @property
    def mode_locked(self) -> bool:
        """True if mode lock acquired."""
        return self.mode_lock.acquired
    
    @property
    def lane_locked(self) -> bool:
        """True if lane lock acquired."""
        return self.lane_lock.acquired
    
    @property
    def tools_locked(self) -> bool:
        """True if tools lock acquired."""
        return self.tools_lock.acquired
    
    @property
    def handshake_complete(self) -> bool:
        """True if echo handshake complete."""
        return self.handshake_lock.acquired
    
    @property
    def all_locks_acquired(self) -> bool:
        """True if all 5 locks acquired."""
        return all([
            self.identity_locked,
            self.mode_locked,
            self.lane_locked,
            self.tools_locked,
            self.handshake_complete,
        ])
    
    @property
    def is_sealed(self) -> bool:
        """True if session is sealed and ready for PAC execution."""
        return (
            self.status == BootstrapStatus.SEALED
            and self.all_locks_acquired
            and self.bootstrap_token is not None
        )
    
    @property
    def acquired_locks(self) -> List[LockState]:
        """List of acquired locks."""
        locks = [
            self.identity_lock,
            self.mode_lock,
            self.lane_lock,
            self.tools_lock,
            self.handshake_lock,
        ]
        return [l for l in locks if l.acquired]
    
    @property
    def missing_locks(self) -> List[BootstrapLock]:
        """List of locks not yet acquired."""
        missing = []
        if not self.identity_locked:
            missing.append(BootstrapLock.BOOT_01)
        if not self.mode_locked:
            missing.append(BootstrapLock.BOOT_02)
        if not self.lane_locked:
            missing.append(BootstrapLock.BOOT_03)
        if not self.tools_locked:
            missing.append(BootstrapLock.BOOT_04)
        if not self.handshake_complete:
            missing.append(BootstrapLock.BOOT_05)
        return missing
    
    @property
    def echo_handshake(self) -> Optional[str]:
        """Get echo handshake string if complete."""
        if self.handshake_complete:
            return self.handshake_lock.value
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATE TRANSITIONS — RETURN NEW INSTANCES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self) -> BootstrapState:
        """
        Start bootstrap sequence.
        
        Returns new state with status IN_PROGRESS.
        """
        if self.status != BootstrapStatus.NOT_STARTED:
            raise BootstrapAlreadyStartedError(
                f"Bootstrap already {self.status.value}"
            )
        
        return replace(
            self,
            status=BootstrapStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def acquire_identity(self, gid: str, role: str) -> BootstrapState:
        """
        Acquire identity lock.
        
        Returns new state with identity locked.
        """
        if self.status == BootstrapStatus.SEALED:
            raise RebootstrapForbiddenError(
                "Cannot re-acquire identity in sealed session"
            )
        
        new_lock = self.identity_lock.acquire(f"{gid}:{role}")
        
        return replace(
            self,
            gid=gid,
            role=role,
            identity_lock=new_lock,
            status=BootstrapStatus.IN_PROGRESS if self.status == BootstrapStatus.NOT_STARTED else self.status,
            started_at=self.started_at or datetime.now(timezone.utc).isoformat(),
        )
    
    def acquire_mode(self, mode: str) -> BootstrapState:
        """
        Acquire mode lock.
        
        Returns new state with mode locked.
        """
        if self.status == BootstrapStatus.SEALED:
            raise RebootstrapForbiddenError(
                "Cannot re-acquire mode in sealed session"
            )
        
        new_lock = self.mode_lock.acquire(mode)
        
        return replace(
            self,
            mode=mode,
            mode_lock=new_lock,
        )
    
    def acquire_lane(self, lane: str) -> BootstrapState:
        """
        Acquire lane lock.
        
        Returns new state with lane locked.
        """
        if self.status == BootstrapStatus.SEALED:
            raise RebootstrapForbiddenError(
                "Cannot re-acquire lane in sealed session"
            )
        
        new_lock = self.lane_lock.acquire(lane)
        
        return replace(
            self,
            lane=lane,
            lane_lock=new_lock,
        )
    
    def acquire_tools(
        self,
        permitted: FrozenSet[str],
        stripped: FrozenSet[str],
    ) -> BootstrapState:
        """
        Acquire tools lock after tool stripping.
        
        Returns new state with tools locked.
        """
        if self.status == BootstrapStatus.SEALED:
            raise RebootstrapForbiddenError(
                "Cannot re-acquire tools in sealed session"
            )
        
        tool_summary = f"permitted={len(permitted)},stripped={len(stripped)}"
        new_lock = self.tools_lock.acquire(tool_summary)
        
        return replace(
            self,
            tools_lock=new_lock,
            permitted_tools=permitted,
            stripped_tools=stripped,
        )
    
    def complete_handshake(self, handshake: str) -> BootstrapState:
        """
        Complete echo handshake.
        
        Returns new state with handshake complete.
        """
        if self.status == BootstrapStatus.SEALED:
            raise RebootstrapForbiddenError(
                "Cannot re-complete handshake in sealed session"
            )
        
        new_lock = self.handshake_lock.acquire(handshake)
        
        return replace(
            self,
            handshake_lock=new_lock,
        )
    
    def seal(self) -> BootstrapState:
        """
        Seal the bootstrap session.
        
        All locks must be acquired before sealing.
        Returns new state with status SEALED and token generated.
        """
        if self.status == BootstrapStatus.SEALED:
            raise RebootstrapForbiddenError(
                "Session already sealed"
            )
        
        if not self.all_locks_acquired:
            missing = self.missing_locks
            missing_names = [LOCK_NAMES[l] for l in missing]
            raise BootstrapIncompleteError(
                f"Cannot seal: missing locks: {missing_names}"
            )
        
        # Generate bootstrap token
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_suffix = secrets.token_hex(4)
        token = f"boot_{timestamp}_{self.gid}_{random_suffix}"
        
        return replace(
            self,
            status=BootstrapStatus.SEALED,
            bootstrap_token=token,
            sealed_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def fail(self, reason: str) -> BootstrapState:
        """
        Mark bootstrap as failed.
        
        Returns new state with status FAILED.
        """
        return replace(
            self,
            status=BootstrapStatus.FAILED,
            failed_at=datetime.now(timezone.utc).isoformat(),
            failure_reason=reason,
        )
    
    def terminate(self) -> BootstrapState:
        """
        Terminate the session (e.g., after re-bootstrap attempt).
        
        Returns new state with status TERMINATED.
        """
        return replace(
            self,
            status=BootstrapStatus.TERMINATED,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP BUILDER — FLUENT API
# ═══════════════════════════════════════════════════════════════════════════════

class BootstrapBuilder:
    """
    Fluent builder for bootstrap state.
    
    Provides a convenient API for building up bootstrap state
    while maintaining immutability of the underlying BootstrapState.
    """
    
    def __init__(self, state: BootstrapState = None):
        self._state = state or BootstrapState()
    
    @property
    def state(self) -> BootstrapState:
        """Get current state."""
        return self._state
    
    def start(self) -> BootstrapBuilder:
        """Start bootstrap sequence."""
        self._state = self._state.start()
        return self
    
    def with_identity(self, gid: str, role: str) -> BootstrapBuilder:
        """Set identity."""
        self._state = self._state.acquire_identity(gid, role)
        return self
    
    def with_mode(self, mode: str) -> BootstrapBuilder:
        """Set mode."""
        self._state = self._state.acquire_mode(mode)
        return self
    
    def with_lane(self, lane: str) -> BootstrapBuilder:
        """Set lane."""
        self._state = self._state.acquire_lane(lane)
        return self
    
    def with_tools(
        self,
        permitted: FrozenSet[str],
        stripped: FrozenSet[str] = frozenset(),
    ) -> BootstrapBuilder:
        """Set tools."""
        self._state = self._state.acquire_tools(permitted, stripped)
        return self
    
    def with_handshake(self, handshake: str = None) -> BootstrapBuilder:
        """Complete handshake."""
        if handshake is None:
            handshake = f"{self._state.gid} | {self._state.mode} | {self._state.lane}"
        self._state = self._state.complete_handshake(handshake)
        return self
    
    def seal(self) -> BootstrapState:
        """Seal and return final state."""
        self._state = self._state.seal()
        return self._state
    
    def build(self) -> BootstrapState:
        """Build current state without sealing."""
        return self._state


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class BootstrapError(Exception):
    """Base exception for bootstrap errors."""
    pass


class BootstrapRequiredError(BootstrapError):
    """Raised when PAC execution attempted without bootstrap."""
    pass


class BootstrapIncompleteError(BootstrapError):
    """Raised when attempting to seal incomplete bootstrap."""
    pass


class BootstrapAlreadyStartedError(BootstrapError):
    """Raised when attempting to start already-started bootstrap."""
    pass


class RebootstrapForbiddenError(BootstrapError):
    """Raised when attempting to re-bootstrap sealed session."""
    pass


class LockAlreadyAcquiredError(BootstrapError):
    """Raised when attempting to acquire already-acquired lock."""
    pass


class BootstrapValidationError(BootstrapError):
    """Raised when bootstrap validation fails."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_current_session: Optional[BootstrapState] = None


def get_current_session() -> Optional[BootstrapState]:
    """Get the current bootstrap session state."""
    global _current_session
    return _current_session


def set_current_session(state: BootstrapState) -> None:
    """Set the current bootstrap session state."""
    global _current_session
    _current_session = state


def clear_current_session() -> None:
    """Clear the current session (for testing)."""
    global _current_session
    _current_session = None


def require_sealed_session() -> BootstrapState:
    """
    Get the current session, raising if not sealed.
    
    This is the primary enforcement point for PAC execution.
    """
    session = get_current_session()
    
    if session is None:
        raise BootstrapRequiredError(
            "No bootstrap session — complete bootstrap before PAC execution"
        )
    
    if not session.is_sealed:
        raise BootstrapRequiredError(
            f"Bootstrap not complete — status: {session.status.value}, "
            f"missing locks: {[l.value for l in session.missing_locks]}"
        )
    
    return session


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "BootstrapLock",
    "BootstrapStatus",
    "LOCK_NAMES",
    
    # State classes
    "LockState",
    "BootstrapState",
    "BootstrapBuilder",
    
    # Exceptions
    "BootstrapError",
    "BootstrapRequiredError",
    "BootstrapIncompleteError",
    "BootstrapAlreadyStartedError",
    "RebootstrapForbiddenError",
    "LockAlreadyAcquiredError",
    "BootstrapValidationError",
    
    # Session management
    "get_current_session",
    "set_current_session",
    "clear_current_session",
    "require_sealed_session",
]
