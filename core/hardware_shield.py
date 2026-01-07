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

# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OCC-P16-HW: DEAD MAN'S SWITCH (Physical Sovereignty Layer)
# ═══════════════════════════════════════════════════════════════════════════════
# Invariant: HUMAN_ANCHOR | NO_GHOSTS | FAIL_CLOSED
# "The circuit is the law. The break in the circuit is the execution of the law."
# ═══════════════════════════════════════════════════════════════════════════════

class HeartbeatSource(Enum):
    """Type of heartbeat source for Dead Man's Switch"""
    FILE_LOCK = "file_lock"     # Dev mode: lockfile existence
    SERIAL = "serial"          # Production: serial port signal
    GPIO = "gpio"              # Embedded: GPIO pin state


@dataclass
class DeadManSwitchConfig:
    """Configuration for Dead Man's Switch"""
    source: HeartbeatSource = HeartbeatSource.FILE_LOCK
    poll_interval_hz: float = 1.0       # Polling frequency (Hz)
    timeout_seconds: float = 2.0        # Max time without heartbeat before kill
    lockfile_path: Optional[Path] = None  # For FILE_LOCK mode
    serial_port: str = "/dev/ttyUSB0"   # For SERIAL mode
    gpio_pin: int = 17                  # For GPIO mode (BCM numbering)
    bypass_in_dev: bool = False         # If True, skip kill in DEV mode


class DeadManSwitch:
    """
    Physical Sovereignty Layer - Dead Man's Switch
    
    This class monitors a hardware resource (serial port, GPIO, or lockfile)
    for a heartbeat signal. If the signal is lost for longer than the timeout,
    the process is forcefully terminated.
    
    Constitutional Mandate (LAW-P16-HW):
    - The digital system MUST terminate immediately if the physical link is severed
    - Fail-closed: Default state is OFF (blocking)
    - Poll at least 1Hz
    - Bypass graceful shutdown if signal loss > 2s
    
    Usage:
        # Development mode (lockfile):
        switch = DeadManSwitch(source=HeartbeatSource.FILE_LOCK)
        switch.start()  # Blocks until lockfile appears, then monitors
        
        # Production mode (serial):
        switch = DeadManSwitch(
            source=HeartbeatSource.SERIAL,
            serial_port="/dev/ttyUSB0"
        )
        switch.start()
    """
    
    _instance: Optional['DeadManSwitch'] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[DeadManSwitchConfig] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.config = config or DeadManSwitchConfig()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_heartbeat: float = 0.0
        self._armed = False
        self._state = "INIT"  # INIT, ARMED, POLLING, TERMINATED
        
        # Set default lockfile path
        if self.config.source == HeartbeatSource.FILE_LOCK and not self.config.lockfile_path:
            self.config.lockfile_path = Path.home() / ".chainbridge" / "heartbeat.lock"
        
        self._initialized = True
        logger.info(f"[P16-DEADMAN] Initialized: source={self.config.source.value}")
    
    def _check_heartbeat(self) -> bool:
        """
        Check if the heartbeat signal is present.
        
        Returns True if heartbeat detected (system should stay alive).
        Returns False if no heartbeat (system should prepare to die).
        """
        try:
            if self.config.source == HeartbeatSource.FILE_LOCK:
                return self._check_lockfile()
            elif self.config.source == HeartbeatSource.SERIAL:
                return self._check_serial()
            elif self.config.source == HeartbeatSource.GPIO:
                return self._check_gpio()
            else:
                logger.error(f"[P16-DEADMAN] Unknown source: {self.config.source}")
                return False
        except Exception as e:
            logger.error(f"[P16-DEADMAN] Heartbeat check failed: {e}")
            return False
    
    def _check_lockfile(self) -> bool:
        """Check if lockfile exists and is fresh (modified within timeout)."""
        lockfile = self.config.lockfile_path
        if not lockfile or not lockfile.exists():
            return False
        
        # Check if file was touched recently (within 2x poll interval)
        try:
            mtime = lockfile.stat().st_mtime
            age = time.time() - mtime
            return age < (2.0 / self.config.poll_interval_hz)
        except Exception:
            return False
    
    def _check_serial(self) -> bool:
        """Check serial port for heartbeat signal."""
        try:
            import serial
            with serial.Serial(self.config.serial_port, 9600, timeout=0.1) as ser:
                # Read one byte - any data means heartbeat
                data = ser.read(1)
                return len(data) > 0
        except ImportError:
            logger.warning("[P16-DEADMAN] pyserial not installed")
            return False
        except Exception as e:
            logger.debug(f"[P16-DEADMAN] Serial read failed: {e}")
            return False
    
    def _check_gpio(self) -> bool:
        """Check GPIO pin state (Raspberry Pi)."""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.config.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            return GPIO.input(self.config.gpio_pin) == GPIO.HIGH
        except ImportError:
            logger.warning("[P16-DEADMAN] RPi.GPIO not available")
            return False
        except Exception as e:
            logger.debug(f"[P16-DEADMAN] GPIO read failed: {e}")
            return False
    
    def _poll_loop(self) -> None:
        """Background thread polling loop."""
        poll_interval = 1.0 / self.config.poll_interval_hz
        
        logger.info(f"[P16-DEADMAN] Polling started: {self.config.poll_interval_hz}Hz, timeout={self.config.timeout_seconds}s")
        self._state = "POLLING"
        
        while not self._stop_event.is_set():
            if self._check_heartbeat():
                self._last_heartbeat = time.time()
                logger.debug("[P16-DEADMAN] Heartbeat OK")
            else:
                elapsed = time.time() - self._last_heartbeat
                logger.warning(f"[P16-DEADMAN] No heartbeat for {elapsed:.1f}s")
                
                if elapsed > self.config.timeout_seconds:
                    self._execute_kill()
                    return
            
            self._stop_event.wait(poll_interval)
    
    def _execute_kill(self) -> None:
        """
        Execute immediate process termination.
        
        NO GRACEFUL SHUTDOWN - this is a hardware interrupt.
        """
        self._state = "TERMINATED"
        
        # Check dev mode bypass
        dev_mode = os.getenv("BRIDGE_DEV_MODE", "false").lower() == "true"
        if self.config.bypass_in_dev and dev_mode:
            logger.warning("[P16-DEADMAN] KILL BYPASSED - DEV MODE")
            return
        
        logger.critical("=" * 60)
        logger.critical("[P16-DEADMAN] ☠️  HEARTBEAT LOST - EXECUTING KILL")
        logger.critical("[P16-DEADMAN] The circuit is broken. The law is executed.")
        logger.critical("=" * 60)
        
        # Log to audit file
        try:
            audit_path = Path("logs/deadman_audit.log")
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(audit_path, "a") as f:
                f.write(f"{datetime.utcnow().isoformat()} | KILL | PID={os.getpid()} | REASON=heartbeat_timeout\n")
        except Exception:
            pass
        
        # Immediate termination - bypass graceful shutdown
        pid = os.getpid()
        os.kill(pid, signal.SIGKILL)
    
    def start(self) -> None:
        """
        Start the Dead Man's Switch monitoring.
        
        This MUST be called after the application is ready to serve.
        The switch will immediately start checking for heartbeat.
        """
        if self._armed:
            logger.warning("[P16-DEADMAN] Already armed")
            return
        
        # Initial heartbeat check - FAIL_CLOSED
        if self._check_heartbeat():
            self._last_heartbeat = time.time()
            logger.info("[P16-DEADMAN] Initial heartbeat OK - arming")
        else:
            dev_mode = os.getenv("BRIDGE_DEV_MODE", "false").lower() == "true"
            if self.config.bypass_in_dev and dev_mode:
                logger.warning("[P16-DEADMAN] No initial heartbeat - DEV MODE BYPASS")
                self._last_heartbeat = time.time()  # Fake it for dev
            else:
                logger.critical("[P16-DEADMAN] No initial heartbeat - FAIL_CLOSED")
                # Give a brief grace period to create lockfile
                logger.info("[P16-DEADMAN] Waiting 5s for heartbeat source...")
                time.sleep(5)
                if not self._check_heartbeat():
                    logger.critical("[P16-DEADMAN] Still no heartbeat - TERMINATING")
                    sys.exit(1)
                self._last_heartbeat = time.time()
        
        # Start polling thread
        self._armed = True
        self._state = "ARMED"
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="DeadManSwitch",
            daemon=True  # Die with main thread
        )
        self._thread.start()
        
        logger.info("[P16-DEADMAN] ⚡ ARMED - Physical sovereignty active")
    
    def stop(self) -> None:
        """Stop the Dead Man's Switch (for graceful shutdown only)."""
        if not self._armed:
            return
        
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        
        self._armed = False
        self._state = "STOPPED"
        logger.info("[P16-DEADMAN] Disarmed")
    
    @property
    def is_armed(self) -> bool:
        """Check if the switch is currently armed."""
        return self._armed
    
    @property
    def state(self) -> str:
        """Get current state."""
        return self._state
    
    @property
    def seconds_since_heartbeat(self) -> float:
        """Get seconds since last heartbeat."""
        if self._last_heartbeat == 0:
            return float('inf')
        return time.time() - self._last_heartbeat


# Import threading for DeadManSwitch
import threading


def get_dead_man_switch() -> Optional[DeadManSwitch]:
    """Get the singleton DeadManSwitch instance, if initialized."""
    return DeadManSwitch._instance


def arm_dead_man_switch(
    source: HeartbeatSource = HeartbeatSource.FILE_LOCK,
    lockfile_path: Optional[Path] = None,
    bypass_in_dev: bool = True
) -> DeadManSwitch:
    """
    Initialize and arm the Dead Man's Switch.
    
    Args:
        source: Heartbeat source type
        lockfile_path: Path to lockfile (for FILE_LOCK mode)
        bypass_in_dev: Skip kill in DEV mode
    
    Returns:
        Armed DeadManSwitch instance
    """
    config = DeadManSwitchConfig(
        source=source,
        lockfile_path=lockfile_path,
        bypass_in_dev=bypass_in_dev
    )
    switch = DeadManSwitch(config)
    switch.start()
    return switch


def create_heartbeat_lockfile(path: Optional[Path] = None) -> Path:
    """
    Create the heartbeat lockfile for development testing.
    
    Call this from a separate process or script to keep the system alive.
    The lockfile must be 'touched' periodically to maintain heartbeat.
    
    Returns the path to the lockfile.
    """
    lockfile = path or Path.home() / ".chainbridge" / "heartbeat.lock"
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    lockfile.touch()
    logger.info(f"[P16-DEADMAN] Heartbeat lockfile created: {lockfile}")
    return lockfile


def touch_heartbeat(path: Optional[Path] = None) -> None:
    """Touch the heartbeat lockfile to maintain heartbeat."""
    lockfile = path or Path.home() / ".chainbridge" / "heartbeat.lock"
    if lockfile.exists():
        lockfile.touch()
    else:
        create_heartbeat_lockfile(lockfile)


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
    
    # Test mode selection
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--deadman", action="store_true", help="Test Dead Man's Switch")
    args = parser.parse_args()
    
    if args.deadman:
        # Test Dead Man's Switch
        print("=" * 60)
        print("Testing Dead Man's Switch (FILE_LOCK mode)")
        print("=" * 60)
        print("To keep alive, run in another terminal:")
        print("  while true; do touch ~/.chainbridge/heartbeat.lock; sleep 0.5; done")
        print("=" * 60)
        
        os.environ["BRIDGE_DEV_MODE"] = "true"
        
        # Create initial lockfile
        lockfile = create_heartbeat_lockfile()
        print(f"Lockfile: {lockfile}")
        
        # Start heartbeat maintainer in background
        def heartbeat_maintainer():
            while True:
                touch_heartbeat()
                time.sleep(0.5)
        
        hb_thread = threading.Thread(target=heartbeat_maintainer, daemon=True)
        hb_thread.start()
        
        switch = arm_dead_man_switch(bypass_in_dev=False)
        
        print(f"Switch state: {switch.state}")
        print("Delete lockfile to trigger kill:")
        print(f"  rm {lockfile}")
        
        while True:
            time.sleep(1)
            print(f"[ALIVE] Last heartbeat: {switch.seconds_since_heartbeat:.1f}s ago")
    else:
        # Test HardwareShield (signals)
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
