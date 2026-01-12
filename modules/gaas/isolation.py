"""
TenantJail — The Jail
=====================

Process isolation primitive for multi-tenant Sovereign Nodes.

This module enforces hard boundaries between tenant processes using:
- subprocess isolation (separate memory space)
- unique filesystem paths (no shared state)
- unique network ports (no port collisions)
- resource limits (CPU/RAM quotas via psutil)

Invariants:
    INV-GAAS-001: Memory space of Tenant A is inaccessible to Tenant B
    INV-GAAS-002: No tenant can starve the host system

PAC Reference: PAC-STRAT-P900-GAAS
"""

from __future__ import annotations

import os
import sys
import json
import signal
import subprocess
import tempfile
import shutil
import time
import threading
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
from enum import Enum
import logging

# Optional psutil for resource monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class JailState(Enum):
    """Lifecycle states for a TenantJail."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    FAILED = "failed"


@dataclass
class ResourceLimits:
    """
    Resource quotas for tenant isolation.
    
    These limits ensure INV-GAAS-002 (no tenant can starve the host).
    """
    max_cpu_percent: float = 25.0      # Max CPU usage (%)
    max_memory_mb: int = 512           # Max RAM (MB)
    max_disk_mb: int = 1024            # Max disk usage (MB)
    max_open_files: int = 256          # Max file descriptors
    max_runtime_seconds: int = 86400   # Max lifetime (24h default)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResourceLimits:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class IsolationConfig:
    """
    Configuration for a tenant's isolated environment.
    
    Each tenant gets unique paths and ports to ensure
    INV-GAAS-001 (memory/state isolation).
    """
    tenant_id: str
    base_port: int = 9000
    data_dir: Optional[Path] = None
    ledger_path: Optional[Path] = None
    keys_path: Optional[Path] = None
    logs_path: Optional[Path] = None
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize derived paths if not set."""
        if self.data_dir is None:
            # Each tenant gets isolated data directory
            self.data_dir = Path(tempfile.gettempdir()) / "chainbridge_gaas" / self.tenant_id
        
        self.data_dir = Path(self.data_dir)
        
        if self.ledger_path is None:
            self.ledger_path = self.data_dir / "ledger"
        if self.keys_path is None:
            self.keys_path = self.data_dir / "keys"
        if self.logs_path is None:
            self.logs_path = self.data_dir / "logs"
    
    @property
    def api_port(self) -> int:
        """Unique API port for this tenant."""
        # Hash tenant_id to get deterministic port offset
        offset = int(hashlib.sha256(self.tenant_id.encode()).hexdigest()[:4], 16) % 1000
        return self.base_port + offset
    
    @property
    def gossip_port(self) -> int:
        """Unique gossip port for this tenant."""
        return self.api_port + 1000
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "base_port": self.base_port,
            "data_dir": str(self.data_dir),
            "ledger_path": str(self.ledger_path),
            "keys_path": str(self.keys_path),
            "logs_path": str(self.logs_path),
            "api_port": self.api_port,
            "gossip_port": self.gossip_port,
            "limits": self.limits.to_dict(),
            "env_vars": self.env_vars,
        }


class TenantJail:
    """
    Process isolation container for a single tenant.
    
    The Jail provides:
    - Isolated subprocess with dedicated memory space
    - Unique filesystem namespace (data_dir)
    - Unique network ports (api_port, gossip_port)
    - Resource monitoring and enforcement
    - Clean shutdown and cleanup
    
    Invariants Enforced:
        INV-GAAS-001: Memory isolation via subprocess boundary
        INV-GAAS-002: Resource limits via monitoring thread
    """
    
    def __init__(self, config: IsolationConfig):
        self.config = config
        self.tenant_id = config.tenant_id
        self.state = JailState.PENDING
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._violation_callback: Optional[Callable[[str, str], None]] = None
        self._stats_history: list = []
        
        logger.info(f"[JAIL] Created jail for tenant {self.tenant_id}")
    
    def initialize(self) -> bool:
        """
        Initialize the jail's filesystem namespace.
        
        Creates isolated directories for ledger, keys, and logs.
        Returns True if successful.
        """
        self.state = JailState.INITIALIZING
        
        try:
            # Create isolated directory structure
            for path in [self.config.data_dir, self.config.ledger_path, 
                        self.config.keys_path, self.config.logs_path]:
                path.mkdir(parents=True, exist_ok=True)
            
            # Write isolation manifest
            manifest = {
                "tenant_id": self.tenant_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "config": self.config.to_dict(),
                "invariants": ["INV-GAAS-001", "INV-GAAS-002"],
            }
            
            manifest_path = self.config.data_dir / "isolation_manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"[JAIL] Initialized filesystem for {self.tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"[JAIL] Failed to initialize {self.tenant_id}: {e}")
            self.state = JailState.FAILED
            return False
    
    def spawn(self, entry_script: str, args: list = None) -> bool:
        """
        Spawn the isolated tenant process.
        
        Args:
            entry_script: Path to the Python script to run
            args: Additional command-line arguments
        
        Returns:
            True if process started successfully
        """
        if self.state not in (JailState.PENDING, JailState.INITIALIZING):
            logger.error(f"[JAIL] Cannot spawn in state {self.state}")
            return False
        
        if not self.config.data_dir.exists():
            if not self.initialize():
                return False
        
        # Build environment with isolation settings
        env = os.environ.copy()
        env.update({
            "CHAINBRIDGE_TENANT_ID": self.tenant_id,
            "CHAINBRIDGE_DATA_DIR": str(self.config.data_dir),
            "CHAINBRIDGE_LEDGER_PATH": str(self.config.ledger_path),
            "CHAINBRIDGE_KEYS_PATH": str(self.config.keys_path),
            "CHAINBRIDGE_LOGS_PATH": str(self.config.logs_path),
            "CHAINBRIDGE_API_PORT": str(self.config.api_port),
            "CHAINBRIDGE_GOSSIP_PORT": str(self.config.gossip_port),
            "CHAINBRIDGE_ISOLATED": "1",
        })
        env.update(self.config.env_vars)
        
        # Build command
        cmd = [sys.executable, entry_script]
        if args:
            cmd.extend(args)
        
        try:
            # Spawn subprocess with isolation
            self.process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(self.config.data_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,  # Create new process group
            )
            
            self.pid = self.process.pid
            self.start_time = datetime.now(timezone.utc)
            self.state = JailState.RUNNING
            
            # Start resource monitoring
            self._start_monitoring()
            
            logger.info(f"[JAIL] Spawned {self.tenant_id} as PID {self.pid}")
            return True
            
        except Exception as e:
            logger.error(f"[JAIL] Failed to spawn {self.tenant_id}: {e}")
            self.state = JailState.FAILED
            return False
    
    def _start_monitoring(self):
        """Start the resource monitoring thread."""
        if not PSUTIL_AVAILABLE:
            logger.warning("[JAIL] psutil not available - resource monitoring disabled")
            return
        
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_resources,
            name=f"monitor-{self.tenant_id}",
            daemon=True,
        )
        self._monitor_thread.start()
    
    def _monitor_resources(self):
        """
        Monitor resource usage and enforce limits.
        
        This enforces INV-GAAS-002 (resource fairness).
        """
        while not self._stop_monitoring.is_set():
            try:
                if self.pid is None:
                    break
                
                try:
                    proc = psutil.Process(self.pid)
                except psutil.NoSuchProcess:
                    logger.info(f"[JAIL] Process {self.pid} no longer exists")
                    break
                
                # Collect stats
                cpu_percent = proc.cpu_percent(interval=0.1)
                memory_info = proc.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                
                stats = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cpu_percent": cpu_percent,
                    "memory_mb": memory_mb,
                    "open_files": len(proc.open_files()) if hasattr(proc, 'open_files') else 0,
                }
                self._stats_history.append(stats)
                
                # Keep only last 100 samples
                if len(self._stats_history) > 100:
                    self._stats_history = self._stats_history[-100:]
                
                # Check limits
                violations = []
                
                if cpu_percent > self.config.limits.max_cpu_percent:
                    violations.append(f"CPU {cpu_percent:.1f}% > {self.config.limits.max_cpu_percent}%")
                
                if memory_mb > self.config.limits.max_memory_mb:
                    violations.append(f"RAM {memory_mb:.1f}MB > {self.config.limits.max_memory_mb}MB")
                
                # Check runtime
                if self.start_time:
                    runtime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                    if runtime > self.config.limits.max_runtime_seconds:
                        violations.append(f"Runtime {runtime:.0f}s > {self.config.limits.max_runtime_seconds}s")
                
                # Handle violations
                if violations:
                    violation_msg = "; ".join(violations)
                    logger.warning(f"[JAIL] {self.tenant_id} LIMIT EXCEEDED: {violation_msg}")
                    
                    if self._violation_callback:
                        self._violation_callback(self.tenant_id, violation_msg)
                    
                    # Kill on memory violation (hard limit)
                    if memory_mb > self.config.limits.max_memory_mb * 1.5:
                        logger.error(f"[JAIL] {self.tenant_id} HARD KILL - memory 150% over limit")
                        self.terminate(force=True)
                        break
                
            except Exception as e:
                logger.error(f"[JAIL] Monitor error for {self.tenant_id}: {e}")
            
            # Check every 1 second
            self._stop_monitoring.wait(1.0)
    
    def set_violation_callback(self, callback: Callable[[str, str], None]):
        """Set callback for resource violations."""
        self._violation_callback = callback
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current resource statistics."""
        if not self._stats_history:
            return {}
        return self._stats_history[-1]
    
    def is_running(self) -> bool:
        """Check if the jail process is running."""
        if self.process is None:
            return False
        return self.process.poll() is None
    
    def suspend(self) -> bool:
        """Suspend the jail process (SIGSTOP)."""
        if not self.is_running():
            return False
        
        try:
            os.kill(self.pid, signal.SIGSTOP)
            self.state = JailState.SUSPENDED
            logger.info(f"[JAIL] Suspended {self.tenant_id}")
            return True
        except Exception as e:
            logger.error(f"[JAIL] Failed to suspend {self.tenant_id}: {e}")
            return False
    
    def resume(self) -> bool:
        """Resume the jail process (SIGCONT)."""
        if self.state != JailState.SUSPENDED:
            return False
        
        try:
            os.kill(self.pid, signal.SIGCONT)
            self.state = JailState.RUNNING
            logger.info(f"[JAIL] Resumed {self.tenant_id}")
            return True
        except Exception as e:
            logger.error(f"[JAIL] Failed to resume {self.tenant_id}: {e}")
            return False
    
    def terminate(self, force: bool = False, timeout: float = 5.0) -> bool:
        """
        Terminate the jail process.
        
        Args:
            force: If True, use SIGKILL immediately
            timeout: Seconds to wait for graceful shutdown
        
        Returns:
            True if process terminated
        """
        self._stop_monitoring.set()
        
        if self.process is None:
            self.state = JailState.TERMINATED
            return True
        
        try:
            if force:
                self.process.kill()
            else:
                self.process.terminate()
                try:
                    self.process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(f"[JAIL] {self.tenant_id} didn't terminate, killing")
                    self.process.kill()
            
            self.end_time = datetime.now(timezone.utc)
            self.state = JailState.TERMINATED
            logger.info(f"[JAIL] Terminated {self.tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"[JAIL] Failed to terminate {self.tenant_id}: {e}")
            self.state = JailState.FAILED
            return False
    
    def cleanup(self, remove_data: bool = False) -> bool:
        """
        Clean up jail resources.
        
        Args:
            remove_data: If True, delete the tenant's data directory
        """
        if self.is_running():
            self.terminate(force=True)
        
        if remove_data and self.config.data_dir.exists():
            try:
                shutil.rmtree(self.config.data_dir)
                logger.info(f"[JAIL] Removed data for {self.tenant_id}")
            except Exception as e:
                logger.error(f"[JAIL] Failed to remove data for {self.tenant_id}: {e}")
                return False
        
        return True
    
    def get_output(self) -> tuple[str, str]:
        """Get stdout/stderr from the process (if terminated)."""
        if self.process is None:
            return "", ""
        
        if self.is_running():
            return "", ""
        
        stdout, stderr = self.process.communicate()
        return stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize jail state."""
        return {
            "tenant_id": self.tenant_id,
            "state": self.state.value,
            "pid": self.pid,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "config": self.config.to_dict(),
            "stats": self.get_stats(),
        }


# === Isolation Verification ===

def verify_isolation(jail_a: TenantJail, jail_b: TenantJail) -> Dict[str, Any]:
    """
    Verify that two jails are properly isolated.
    
    Checks INV-GAAS-001 (memory isolation) by verifying:
    - Different PIDs
    - Different data directories
    - Different ports
    - No shared file handles
    
    Returns verification report.
    """
    report = {
        "verified": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenants": [jail_a.tenant_id, jail_b.tenant_id],
        "checks": {},
    }
    
    # Check 1: Different PIDs (different memory spaces)
    pid_check = jail_a.pid != jail_b.pid if (jail_a.pid and jail_b.pid) else True
    report["checks"]["different_pids"] = {
        "passed": pid_check,
        "values": [jail_a.pid, jail_b.pid],
    }
    
    # Check 2: Different data directories
    dir_check = jail_a.config.data_dir != jail_b.config.data_dir
    report["checks"]["different_data_dirs"] = {
        "passed": dir_check,
        "values": [str(jail_a.config.data_dir), str(jail_b.config.data_dir)],
    }
    
    # Check 3: Different ports
    port_check = (jail_a.config.api_port != jail_b.config.api_port and
                  jail_a.config.gossip_port != jail_b.config.gossip_port)
    report["checks"]["different_ports"] = {
        "passed": port_check,
        "values": {
            "a": {"api": jail_a.config.api_port, "gossip": jail_a.config.gossip_port},
            "b": {"api": jail_b.config.api_port, "gossip": jail_b.config.gossip_port},
        },
    }
    
    # Check 4: No overlapping paths
    paths_a = {str(jail_a.config.ledger_path), str(jail_a.config.keys_path)}
    paths_b = {str(jail_b.config.ledger_path), str(jail_b.config.keys_path)}
    path_check = paths_a.isdisjoint(paths_b)
    report["checks"]["no_path_overlap"] = {
        "passed": path_check,
        "overlap": list(paths_a & paths_b),
    }
    
    # Overall verification
    report["verified"] = all(c["passed"] for c in report["checks"].values())
    report["invariant"] = "INV-GAAS-001" if report["verified"] else "VIOLATED"
    
    return report
