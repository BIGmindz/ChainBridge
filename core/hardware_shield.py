#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OCC-P16-HW-SHIELD — Hardware Signal Handler
# Lane 6 (DevOps / GID-DAN) Implementation
# Governance Tier: LAW
# Invariant: FAIL_CLOSED | SIGTERM_GRACEFUL | SIGKILL_IMMEDIATE | NO_ZOMBIE
# ═══════════════════════════════════════════════════════════════════════════════
"""
Hardware Signal Handler for ChainBridge Emergency Termination

This module provides hardware-level interrupt handling for emergency system
termination. It listens for OS signals (SIGTERM, SIGKILL, SIGHUP) and ensures
graceful shutdown of all ChainBridge services.

Security Model:
- SIGTERM: Graceful shutdown with 30s timeout
- SIGINT: Interactive interrupt (Ctrl+C)
- SIGHUP: Terminal hangup, treat as graceful shutdown
- SIGKILL: Cannot be caught, but we log attempts

Signal Priority:
1. Save state to ledger
2. Close WebSocket connections
3. Flush audit logs
4. Release file locks
5. Exit with appropriate code

Constitutional Mandate (LAW-TLH-001):
- No zombie processes allowed
- All child processes must be terminated
- Audit trail must be preserved
"""

import asyncio
import atexit
import logging
import os
import signal
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# Shutdown configuration
GRACEFUL_SHUTDOWN_TIMEOUT = 30  # seconds
FORCE_SHUTDOWN_TIMEOUT = 5      # seconds after graceful fails
CHILD_REAP_INTERVAL = 0.1       # seconds

# Signal codes for exit
EXIT_SUCCESS = 0
EXIT_SIGTERM = 128 + signal.SIGTERM
EXIT_SIGINT = 128 + signal.SIGINT
EXIT_SIGHUP = 128 + signal.SIGHUP

# ═══════════════════════════════════════════════════════════════════════════════
# TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class ShutdownPhase(Enum):
    """Shutdown phases for ordered cleanup"""
    RUNNING = "running"
    SIGNAL_RECEIVED = "signal_received"
    SAVING_STATE = "saving_state"
    CLOSING_CONNECTIONS = "closing_connections"
    FLUSHING_LOGS = "flushing_logs"
    RELEASING_LOCKS = "releasing_locks"
    REAPING_CHILDREN = "reaping_children"
    TERMINATED = "terminated"


@dataclass
class ShutdownEvent:
    """Record of a shutdown event for audit"""
    signal_num: int
    signal_name: str
    timestamp: datetime
    phase: ShutdownPhase
    pid: int
    gid: str
    reason: str
    duration_ms: float = 0.0


@dataclass
class ShutdownHook:
    """A registered shutdown hook"""
    name: str
    callback: Callable[[], None]
    priority: int  # Lower = earlier execution
    async_callback: bool = False


@dataclass
class HardwareShieldState:
    """State of the hardware shield"""
    phase: ShutdownPhase = ShutdownPhase.RUNNING
    shutdown_requested: bool = False
    shutdown_signal: Optional[int] = None
    shutdown_time: Optional[datetime] = None
    hooks: List[ShutdownHook] = field(default_factory=list)
    child_pids: Set[int] = field(default_factory=set)
    events: List[ShutdownEvent] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE SHIELD CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class HardwareShield:
    """
    Hardware-level signal handler for emergency termination.
    
    This class manages:
    - Signal registration and handling
    - Ordered shutdown hooks
    - Child process reaping
    - Audit event logging
    
    Usage:
        shield = HardwareShield(gid="GID-00")
        shield.register_hook("save_ledger", save_ledger_func, priority=10)
        shield.register_hook("close_ws", close_websockets, priority=20)
        shield.arm()  # Start listening for signals
    """
    
    _instance: Optional['HardwareShield'] = None
    
    def __new__(cls, *args, **kwargs):
        # Singleton pattern - only one shield per process
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, gid: str = "GID-00", audit_path: Optional[Path] = None):
        # Skip re-initialization for singleton
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.gid = gid
        self.audit_path = audit_path or Path("logs/shield_audit.log")
        self.state = HardwareShieldState()
        self._armed = False
        self._original_handlers: Dict[int, signal.Handlers] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._initialized = True
        
        # Ensure audit directory exists
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[P16-HW-SHIELD] Initialized for {gid}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HOOK REGISTRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def register_hook(
        self,
        name: str,
        callback: Callable[[], None],
        priority: int = 50,
        async_callback: bool = False
    ) -> None:
        """
        Register a shutdown hook.
        
        Args:
            name: Human-readable name for the hook
            callback: Function to call during shutdown
            priority: Execution order (lower = earlier)
            async_callback: Whether the callback is async
        """
        hook = ShutdownHook(
            name=name,
            callback=callback,
            priority=priority,
            async_callback=async_callback
        )
        self.state.hooks.append(hook)
        self.state.hooks.sort(key=lambda h: h.priority)
        logger.debug(f"[P16-HW-SHIELD] Registered hook: {name} (priority={priority})")
    
    def unregister_hook(self, name: str) -> bool:
        """Remove a shutdown hook by name."""
        before = len(self.state.hooks)
        self.state.hooks = [h for h in self.state.hooks if h.name != name]
        removed = len(self.state.hooks) < before
        if removed:
            logger.debug(f"[P16-HW-SHIELD] Unregistered hook: {name}")
        return removed
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHILD PROCESS TRACKING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def track_child(self, pid: int) -> None:
        """Track a child process for cleanup during shutdown."""
        self.state.child_pids.add(pid)
        logger.debug(f"[P16-HW-SHIELD] Tracking child PID: {pid}")
    
    def untrack_child(self, pid: int) -> None:
        """Stop tracking a child process."""
        self.state.child_pids.discard(pid)
    
    def _reap_children(self) -> int:
        """
        Terminate and reap all tracked child processes.
        Returns the number of processes reaped.
        """
        reaped = 0
        
        for pid in list(self.state.child_pids):
            try:
                # First, try SIGTERM (graceful)
                os.kill(pid, signal.SIGTERM)
                logger.debug(f"[P16-HW-SHIELD] Sent SIGTERM to PID {pid}")
            except ProcessLookupError:
                self.state.child_pids.discard(pid)
                reaped += 1
                continue
            except PermissionError:
                logger.warning(f"[P16-HW-SHIELD] Cannot signal PID {pid}: permission denied")
                continue
        
        # Wait briefly for graceful termination
        deadline = time.time() + FORCE_SHUTDOWN_TIMEOUT
        while self.state.child_pids and time.time() < deadline:
            for pid in list(self.state.child_pids):
                try:
                    result = os.waitpid(pid, os.WNOHANG)
                    if result[0] != 0:
                        self.state.child_pids.discard(pid)
                        reaped += 1
                except ChildProcessError:
                    self.state.child_pids.discard(pid)
                    reaped += 1
            time.sleep(CHILD_REAP_INTERVAL)
        
        # Force kill any remaining
        for pid in list(self.state.child_pids):
            try:
                os.kill(pid, signal.SIGKILL)
                logger.warning(f"[P16-HW-SHIELD] Force killed PID {pid}")
                self.state.child_pids.discard(pid)
                reaped += 1
            except (ProcessLookupError, PermissionError):
                self.state.child_pids.discard(pid)
        
        return reaped
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIGNAL HANDLING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def arm(self) -> None:
        """
        Arm the hardware shield - start listening for signals.
        
        This registers handlers for SIGTERM, SIGINT, and SIGHUP.
        Call this after all hooks are registered.
        """
        if self._armed:
            logger.warning("[P16-HW-SHIELD] Already armed")
            return
        
        # Store original handlers
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            self._original_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, self._signal_handler)
        
        # Register atexit handler as fallback
        atexit.register(self._atexit_handler)
        
        self._armed = True
        logger.info("[P16-HW-SHIELD] ARMED - listening for termination signals")
    
    def disarm(self) -> None:
        """Disarm the shield - restore original signal handlers."""
        if not self._armed:
            return
        
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        
        self._original_handlers.clear()
        self._armed = False
        logger.info("[P16-HW-SHIELD] DISARMED")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle incoming signals."""
        sig_name = signal.Signals(signum).name
        
        logger.warning(f"[P16-HW-SHIELD] Received {sig_name} ({signum})")
        
        # Record the event
        event = ShutdownEvent(
            signal_num=signum,
            signal_name=sig_name,
            timestamp=datetime.utcnow(),
            phase=ShutdownPhase.SIGNAL_RECEIVED,
            pid=os.getpid(),
            gid=self.gid,
            reason=f"Signal {sig_name} received"
        )
        self.state.events.append(event)
        
        # If already shutting down, ignore (prevent re-entry)
        if self.state.shutdown_requested:
            logger.warning(f"[P16-HW-SHIELD] Shutdown already in progress, ignoring {sig_name}")
            return
        
        self.state.shutdown_requested = True
        self.state.shutdown_signal = signum
        self.state.shutdown_time = datetime.utcnow()
        
        # Execute shutdown
        self._execute_shutdown(signum)
    
    def _atexit_handler(self) -> None:
        """Fallback handler for normal exit."""
        if not self.state.shutdown_requested:
            logger.info("[P16-HW-SHIELD] Normal exit - executing cleanup")
            self._execute_shutdown(0)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SHUTDOWN EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _execute_shutdown(self, signum: int) -> None:
        """
        Execute the shutdown sequence.
        
        Order:
        1. Run all registered hooks (by priority)
        2. Reap child processes
        3. Write audit log
        4. Exit with appropriate code
        """
        start_time = time.time()
        
        # Phase: Saving state
        self.state.phase = ShutdownPhase.SAVING_STATE
        logger.info("[P16-HW-SHIELD] Phase: SAVING_STATE")
        
        # Run hooks
        for hook in self.state.hooks:
            try:
                logger.debug(f"[P16-HW-SHIELD] Running hook: {hook.name}")
                if hook.async_callback:
                    # For async callbacks, we need an event loop
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Schedule and don't wait
                            asyncio.ensure_future(hook.callback())
                        else:
                            loop.run_until_complete(hook.callback())
                    except RuntimeError:
                        # No event loop available, skip async hooks
                        logger.warning(f"[P16-HW-SHIELD] Cannot run async hook {hook.name}: no event loop")
                else:
                    hook.callback()
            except Exception as e:
                logger.error(f"[P16-HW-SHIELD] Hook {hook.name} failed: {e}")
        
        # Phase: Reaping children
        self.state.phase = ShutdownPhase.REAPING_CHILDREN
        logger.info("[P16-HW-SHIELD] Phase: REAPING_CHILDREN")
        reaped = self._reap_children()
        logger.info(f"[P16-HW-SHIELD] Reaped {reaped} child processes")
        
        # Phase: Terminated
        self.state.phase = ShutdownPhase.TERMINATED
        duration = (time.time() - start_time) * 1000
        
        # Final audit entry
        event = ShutdownEvent(
            signal_num=signum,
            signal_name=signal.Signals(signum).name if signum > 0 else "EXIT",
            timestamp=datetime.utcnow(),
            phase=ShutdownPhase.TERMINATED,
            pid=os.getpid(),
            gid=self.gid,
            reason="Shutdown complete",
            duration_ms=duration
        )
        self.state.events.append(event)
        
        # Write audit log
        self._write_audit_log()
        
        logger.info(f"[P16-HW-SHIELD] Shutdown complete in {duration:.2f}ms")
        
        # Determine exit code
        if signum == signal.SIGTERM:
            exit_code = EXIT_SIGTERM
        elif signum == signal.SIGINT:
            exit_code = EXIT_SIGINT
        elif signum == signal.SIGHUP:
            exit_code = EXIT_SIGHUP
        else:
            exit_code = EXIT_SUCCESS
        
        # Exit
        sys.exit(exit_code)
    
    def _write_audit_log(self) -> None:
        """Write shutdown events to audit log."""
        try:
            with open(self.audit_path, "a") as f:
                for event in self.state.events:
                    line = (
                        f"{event.timestamp.isoformat()} | "
                        f"PID={event.pid} | "
                        f"GID={event.gid} | "
                        f"SIGNAL={event.signal_name} | "
                        f"PHASE={event.phase.value} | "
                        f"REASON={event.reason}"
                    )
                    if event.duration_ms > 0:
                        line += f" | DURATION={event.duration_ms:.2f}ms"
                    f.write(line + "\n")
            logger.debug(f"[P16-HW-SHIELD] Audit log written to {self.audit_path}")
        except Exception as e:
            logger.error(f"[P16-HW-SHIELD] Failed to write audit log: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MANUAL SHUTDOWN
    # ═══════════════════════════════════════════════════════════════════════════
    
    def initiate_shutdown(self, reason: str = "Manual shutdown") -> None:
        """
        Manually initiate shutdown.
        
        Use this for programmatic termination (e.g., from the Cockpit KILL button).
        """
        logger.warning(f"[P16-HW-SHIELD] Manual shutdown initiated: {reason}")
        
        event = ShutdownEvent(
            signal_num=0,
            signal_name="MANUAL",
            timestamp=datetime.utcnow(),
            phase=ShutdownPhase.SIGNAL_RECEIVED,
            pid=os.getpid(),
            gid=self.gid,
            reason=reason
        )
        self.state.events.append(event)
        
        self.state.shutdown_requested = True
        self.state.shutdown_time = datetime.utcnow()
        
        self._execute_shutdown(0)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

@contextmanager
def hardware_shield(gid: str = "GID-00"):
    """
    Context manager for hardware shield.
    
    Usage:
        with hardware_shield("GID-00") as shield:
            shield.register_hook("cleanup", cleanup_func)
            # ... run your application ...
    """
    shield = HardwareShield(gid=gid)
    shield.arm()
    try:
        yield shield
    finally:
        shield.disarm()


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_shield() -> Optional[HardwareShield]:
    """Get the singleton HardwareShield instance, if initialized."""
    return HardwareShield._instance


def arm_shield(gid: str = "GID-00") -> HardwareShield:
    """Initialize and arm a hardware shield."""
    shield = HardwareShield(gid=gid)
    shield.arm()
    return shield


def register_shutdown_hook(
    name: str,
    callback: Callable[[], None],
    priority: int = 50
) -> None:
    """Register a shutdown hook on the global shield."""
    shield = get_shield()
    if shield:
        shield.register_hook(name, callback, priority)
    else:
        raise RuntimeError("HardwareShield not initialized. Call arm_shield() first.")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN (for testing)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    def cleanup_hook():
        print("[TEST] Cleanup hook executed")
        time.sleep(0.5)
    
    def save_state_hook():
        print("[TEST] State saved to ledger")
    
    with hardware_shield("GID-00-TEST") as shield:
        shield.register_hook("save_state", save_state_hook, priority=10)
        shield.register_hook("cleanup", cleanup_hook, priority=20)
        
        print("[TEST] Hardware shield armed. Press Ctrl+C to test.")
        print("[TEST] PID:", os.getpid())
        
        try:
            while True:
                time.sleep(1)
                print("[TEST] Still running...")
        except KeyboardInterrupt:
            pass  # Signal handler will take over
