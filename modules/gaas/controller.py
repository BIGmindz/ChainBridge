"""
GaaSController — The Warden
===========================

Orchestrator for multi-tenant Governance as a Service.

The Warden manages the lifecycle of all TenantJails:
- Spawn new sovereign instances
- Monitor resource usage across all tenants
- Enforce fair scheduling
- Clean shutdown and tenant eviction

This enables "One Million Nodes on One Titan Cluster" by:
- Process isolation (no VM overhead)
- Resource quotas (fair sharing)
- Dynamic scaling (spawn/kill on demand)

Invariants:
    INV-GAAS-001: Tenant isolation via TenantJail
    INV-GAAS-002: Resource fairness via quotas and monitoring

PAC Reference: PAC-STRAT-P900-GAAS
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List, Any, Callable
from datetime import datetime, timezone
from enum import Enum
import logging
import hashlib

from .isolation import (
    TenantJail,
    IsolationConfig,
    ResourceLimits,
    JailState,
    verify_isolation,
    PSUTIL_AVAILABLE,
)

logger = logging.getLogger(__name__)


class TenantState(Enum):
    """Tenant lifecycle states from the controller's perspective."""
    PENDING = "pending"           # Configured but not spawned
    ACTIVE = "active"             # Running and healthy
    DEGRADED = "degraded"         # Running but over soft limits
    SUSPENDED = "suspended"       # Paused by controller
    TERMINATED = "terminated"     # Cleanly stopped
    EVICTED = "evicted"          # Force-killed due to violations


@dataclass
class TenantConfig:
    """
    Configuration for spawning a new tenant.
    
    This is the public API for tenant creation.
    """
    tenant_id: str
    name: str = ""
    entry_script: str = "sovereign_server.py"
    entry_args: List[str] = field(default_factory=list)
    base_port: int = 9000
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.name:
            self.name = self.tenant_id
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "entry_script": self.entry_script,
            "entry_args": self.entry_args,
            "base_port": self.base_port,
            "limits": self.limits.to_dict(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TenantConfig:
        limits = ResourceLimits.from_dict(data.get("limits", {}))
        return cls(
            tenant_id=data["tenant_id"],
            name=data.get("name", ""),
            entry_script=data.get("entry_script", "sovereign_server.py"),
            entry_args=data.get("entry_args", []),
            base_port=data.get("base_port", 9000),
            limits=limits,
            metadata=data.get("metadata", {}),
        )


@dataclass
class TenantRecord:
    """Internal record for a managed tenant."""
    config: TenantConfig
    jail: TenantJail
    state: TenantState = TenantState.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    violations: List[Dict[str, Any]] = field(default_factory=list)


class GaaSController:
    """
    The Warden — Multi-tenant orchestrator.
    
    Manages multiple TenantJails with:
    - Centralized lifecycle management
    - Resource fairness enforcement
    - Isolation verification
    - Event logging
    
    Usage:
        controller = GaaSController(data_dir="/var/chainbridge/gaas")
        
        config = TenantConfig(tenant_id="acme-corp", name="ACME Corporation")
        controller.spawn_tenant(config)
        
        # Later...
        controller.terminate_tenant("acme-corp")
    """
    
    def __init__(
        self,
        data_dir: str = "/tmp/chainbridge_gaas",
        max_tenants: int = 100,
        log_dir: str = None,
    ):
        self.data_dir = Path(data_dir)
        self.log_dir = Path(log_dir) if log_dir else self.data_dir / "logs"
        self.max_tenants = max_tenants
        
        # Tenant registry: tenant_id -> TenantRecord
        self._tenants: Dict[str, TenantRecord] = {}
        self._lock = threading.RLock()
        
        # Controller state
        self._started = False
        self._shutdown = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Event callbacks
        self._on_spawn: Optional[Callable[[str], None]] = None
        self._on_terminate: Optional[Callable[[str, str], None]] = None
        self._on_violation: Optional[Callable[[str, str], None]] = None
        
        # Initialize directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[WARDEN] Initialized GaaSController at {self.data_dir}")
    
    # === Lifecycle ===
    
    def start(self):
        """Start the controller's monitoring loop."""
        if self._started:
            return
        
        self._started = True
        self._shutdown.clear()
        
        # Start global monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._global_monitor,
            name="gaas-warden",
            daemon=True,
        )
        self._monitor_thread.start()
        
        logger.info("[WARDEN] Controller started")
    
    def stop(self, terminate_tenants: bool = True):
        """
        Stop the controller.
        
        Args:
            terminate_tenants: If True, terminate all running tenants
        """
        self._shutdown.set()
        
        if terminate_tenants:
            self.terminate_all()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        
        self._started = False
        logger.info("[WARDEN] Controller stopped")
    
    # === Tenant Management ===
    
    def spawn_tenant(self, config: TenantConfig) -> bool:
        """
        Spawn a new isolated tenant instance.
        
        Args:
            config: Tenant configuration
        
        Returns:
            True if tenant spawned successfully
        """
        with self._lock:
            # Check capacity
            active_count = sum(1 for t in self._tenants.values() 
                              if t.state == TenantState.ACTIVE)
            if active_count >= self.max_tenants:
                logger.error(f"[WARDEN] Max tenants ({self.max_tenants}) reached")
                return False
            
            # Check for duplicate
            if config.tenant_id in self._tenants:
                existing = self._tenants[config.tenant_id]
                if existing.state == TenantState.ACTIVE:
                    logger.error(f"[WARDEN] Tenant {config.tenant_id} already active")
                    return False
            
            # Create isolation config
            isolation_config = IsolationConfig(
                tenant_id=config.tenant_id,
                base_port=config.base_port,
                data_dir=self.data_dir / "tenants" / config.tenant_id,
                limits=config.limits,
            )
            
            # Create jail
            jail = TenantJail(isolation_config)
            jail.set_violation_callback(self._handle_violation)
            
            # Initialize jail filesystem
            if not jail.initialize():
                logger.error(f"[WARDEN] Failed to initialize jail for {config.tenant_id}")
                return False
            
            # Spawn process
            entry_script = self._resolve_entry_script(config.entry_script)
            if not jail.spawn(entry_script, config.entry_args):
                logger.error(f"[WARDEN] Failed to spawn {config.tenant_id}")
                return False
            
            # Record tenant
            record = TenantRecord(
                config=config,
                jail=jail,
                state=TenantState.ACTIVE,
            )
            self._tenants[config.tenant_id] = record
            
            # Log event
            self._log_event("SPAWN", config.tenant_id, {
                "pid": jail.pid,
                "api_port": isolation_config.api_port,
                "gossip_port": isolation_config.gossip_port,
            })
            
            if self._on_spawn:
                self._on_spawn(config.tenant_id)
            
            logger.info(f"[WARDEN] Spawned tenant {config.tenant_id} (PID {jail.pid})")
            return True
    
    def _resolve_entry_script(self, script: str) -> str:
        """Resolve entry script to absolute path."""
        # Check if already absolute
        if Path(script).is_absolute():
            return script
        
        # Check common locations
        candidates = [
            Path.cwd() / script,
            self.data_dir.parent / script,
            Path(__file__).parent.parent.parent / script,  # Project root
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        
        # Return as-is (let subprocess handle error)
        return script
    
    def terminate_tenant(self, tenant_id: str, force: bool = False, reason: str = "requested") -> bool:
        """
        Terminate a tenant.
        
        Args:
            tenant_id: Tenant to terminate
            force: Use SIGKILL if True
            reason: Reason for termination
        
        Returns:
            True if terminated
        """
        with self._lock:
            if tenant_id not in self._tenants:
                logger.warning(f"[WARDEN] Unknown tenant: {tenant_id}")
                return False
            
            record = self._tenants[tenant_id]
            
            if record.state in (TenantState.TERMINATED, TenantState.EVICTED):
                return True
            
            # Terminate jail
            record.jail.terminate(force=force)
            record.state = TenantState.EVICTED if force else TenantState.TERMINATED
            
            # Log event
            self._log_event("TERMINATE", tenant_id, {
                "reason": reason,
                "force": force,
            })
            
            if self._on_terminate:
                self._on_terminate(tenant_id, reason)
            
            logger.info(f"[WARDEN] Terminated {tenant_id}: {reason}")
            return True
    
    def terminate_all(self):
        """Terminate all active tenants."""
        with self._lock:
            for tenant_id in list(self._tenants.keys()):
                self.terminate_tenant(tenant_id, reason="controller_shutdown")
    
    def suspend_tenant(self, tenant_id: str) -> bool:
        """Suspend a tenant (SIGSTOP)."""
        with self._lock:
            if tenant_id not in self._tenants:
                return False
            
            record = self._tenants[tenant_id]
            if record.jail.suspend():
                record.state = TenantState.SUSPENDED
                self._log_event("SUSPEND", tenant_id, {})
                return True
            return False
    
    def resume_tenant(self, tenant_id: str) -> bool:
        """Resume a suspended tenant (SIGCONT)."""
        with self._lock:
            if tenant_id not in self._tenants:
                return False
            
            record = self._tenants[tenant_id]
            if record.jail.resume():
                record.state = TenantState.ACTIVE
                self._log_event("RESUME", tenant_id, {})
                return True
            return False
    
    # === Queries ===
    
    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant info."""
        with self._lock:
            if tenant_id not in self._tenants:
                return None
            
            record = self._tenants[tenant_id]
            return {
                "tenant_id": tenant_id,
                "name": record.config.name,
                "state": record.state.value,
                "created_at": record.created_at.isoformat(),
                "pid": record.jail.pid,
                "api_port": record.jail.config.api_port,
                "gossip_port": record.jail.config.gossip_port,
                "stats": record.jail.get_stats(),
                "violations": record.violations[-10:],  # Last 10
            }
    
    def list_tenants(self, state: TenantState = None) -> List[Dict[str, Any]]:
        """List all tenants, optionally filtered by state."""
        with self._lock:
            results = []
            for tenant_id, record in self._tenants.items():
                if state is None or record.state == state:
                    results.append({
                        "tenant_id": tenant_id,
                        "name": record.config.name,
                        "state": record.state.value,
                        "pid": record.jail.pid,
                        "api_port": record.jail.config.api_port,
                    })
            return results
    
    def count_tenants(self) -> Dict[str, int]:
        """Count tenants by state."""
        with self._lock:
            counts = {s.value: 0 for s in TenantState}
            for record in self._tenants.values():
                counts[record.state.value] += 1
            counts["total"] = len(self._tenants)
            return counts
    
    # === Isolation Verification ===
    
    def verify_all_isolation(self) -> Dict[str, Any]:
        """
        Verify isolation between all active tenant pairs.
        
        Returns comprehensive isolation report.
        """
        with self._lock:
            active_tenants = [
                (tid, record) for tid, record in self._tenants.items()
                if record.state == TenantState.ACTIVE
            ]
            
            report = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tenant_count": len(active_tenants),
                "pairs_checked": 0,
                "all_isolated": True,
                "violations": [],
                "details": [],
            }
            
            # Check all pairs
            for i, (tid_a, rec_a) in enumerate(active_tenants):
                for tid_b, rec_b in active_tenants[i+1:]:
                    verification = verify_isolation(rec_a.jail, rec_b.jail)
                    report["pairs_checked"] += 1
                    report["details"].append(verification)
                    
                    if not verification["verified"]:
                        report["all_isolated"] = False
                        report["violations"].append({
                            "tenants": [tid_a, tid_b],
                            "checks": verification["checks"],
                        })
            
            report["invariant"] = "INV-GAAS-001" if report["all_isolated"] else "VIOLATED"
            return report
    
    # === Monitoring ===
    
    def _global_monitor(self):
        """Global monitoring loop for all tenants."""
        while not self._shutdown.is_set():
            try:
                self._check_tenant_health()
            except Exception as e:
                logger.error(f"[WARDEN] Monitor error: {e}")
            
            self._shutdown.wait(5.0)  # Check every 5 seconds
    
    def _check_tenant_health(self):
        """Check health of all tenants."""
        with self._lock:
            for tenant_id, record in list(self._tenants.items()):
                if record.state not in (TenantState.ACTIVE, TenantState.DEGRADED):
                    continue
                
                # Check if process died
                if not record.jail.is_running():
                    stdout, stderr = record.jail.get_output()
                    record.state = TenantState.TERMINATED
                    self._log_event("DIED", tenant_id, {
                        "exit_code": record.jail.process.returncode if record.jail.process else None,
                        "stderr_tail": stderr[-500:] if stderr else "",
                    })
                    logger.warning(f"[WARDEN] Tenant {tenant_id} died unexpectedly")
    
    def _handle_violation(self, tenant_id: str, violation: str):
        """Handle resource violation from a jail."""
        with self._lock:
            if tenant_id not in self._tenants:
                return
            
            record = self._tenants[tenant_id]
            
            # Record violation
            violation_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "violation": violation,
            }
            record.violations.append(violation_record)
            
            # Update state
            if record.state == TenantState.ACTIVE:
                record.state = TenantState.DEGRADED
            
            # Log event
            self._log_event("VIOLATION", tenant_id, violation_record)
            
            if self._on_violation:
                self._on_violation(tenant_id, violation)
            
            # Check for repeated violations -> eviction
            recent_violations = [v for v in record.violations[-10:]]
            if len(recent_violations) >= 5:
                logger.error(f"[WARDEN] {tenant_id} has too many violations, evicting")
                self.terminate_tenant(tenant_id, force=True, reason="excessive_violations")
    
    # === Logging ===
    
    def _log_event(self, event_type: str, tenant_id: str, data: Dict[str, Any]):
        """Log a tenant event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "tenant_id": tenant_id,
            "data": data,
        }
        
        # Write to tenant init log
        log_file = self.log_dir / "TENANT_INIT.json"
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
    
    # === Callbacks ===
    
    def on_spawn(self, callback: Callable[[str], None]):
        """Set callback for tenant spawn events."""
        self._on_spawn = callback
    
    def on_terminate(self, callback: Callable[[str, str], None]):
        """Set callback for tenant termination events."""
        self._on_terminate = callback
    
    def on_violation(self, callback: Callable[[str, str], None]):
        """Set callback for resource violations."""
        self._on_violation = callback
    
    # === Serialization ===
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize controller state."""
        with self._lock:
            return {
                "data_dir": str(self.data_dir),
                "max_tenants": self.max_tenants,
                "started": self._started,
                "counts": self.count_tenants(),
                "tenants": {
                    tid: {
                        "state": rec.state.value,
                        "pid": rec.jail.pid,
                        "created_at": rec.created_at.isoformat(),
                    }
                    for tid, rec in self._tenants.items()
                },
            }


# === Demo / Test Function ===

def demo_gaas(count: int = 5):
    """
    Demonstrate GaaS with multiple concurrent tenants.
    
    This tests INV-GAAS-001 and INV-GAAS-002.
    """
    import tempfile
    
    print("=" * 60)
    print("GaaS DEMONSTRATION - Multi-Tenant Isolation")
    print("=" * 60)
    
    # Create a minimal sovereign server script for testing
    demo_script = '''
import os
import time
import json
from pathlib import Path

tenant_id = os.environ.get("CHAINBRIDGE_TENANT_ID", "unknown")
data_dir = os.environ.get("CHAINBRIDGE_DATA_DIR", "/tmp")
api_port = os.environ.get("CHAINBRIDGE_API_PORT", "9000")

print(f"[SOVEREIGN] Tenant {tenant_id} starting on port {api_port}")

# Create tenant-specific ledger entry
ledger_path = Path(data_dir) / "ledger" / "genesis.json"
ledger_path.parent.mkdir(parents=True, exist_ok=True)
with open(ledger_path, "w") as f:
    json.dump({
        "tenant_id": tenant_id,
        "genesis_time": time.time(),
        "api_port": api_port,
    }, f)

# Simulate work
for i in range(10):
    print(f"[SOVEREIGN] {tenant_id} heartbeat {i}")
    time.sleep(1)

print(f"[SOVEREIGN] Tenant {tenant_id} shutting down")
'''
    
    # Write demo script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(demo_script)
        demo_script_path = f.name
    
    try:
        # Create controller
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = GaaSController(data_dir=tmpdir, max_tenants=10)
            controller.start()
            
            # Spawn tenants
            print(f"\n[DEMO] Spawning {count} tenants...")
            for i in range(count):
                tenant_id = f"tenant-{i:03d}"
                config = TenantConfig(
                    tenant_id=tenant_id,
                    name=f"Test Tenant {i}",
                    entry_script=demo_script_path,
                    limits=ResourceLimits(max_memory_mb=256, max_cpu_percent=20),
                )
                
                if controller.spawn_tenant(config):
                    info = controller.get_tenant(tenant_id)
                    print(f"  ✓ {tenant_id}: PID {info['pid']}, Port {info['api_port']}")
                else:
                    print(f"  ✗ {tenant_id}: FAILED")
            
            # Show counts
            print(f"\n[DEMO] Tenant counts: {controller.count_tenants()}")
            
            # Verify isolation
            print("\n[DEMO] Verifying isolation...")
            isolation_report = controller.verify_all_isolation()
            print(f"  Pairs checked: {isolation_report['pairs_checked']}")
            print(f"  All isolated: {isolation_report['all_isolated']}")
            print(f"  Invariant: {isolation_report['invariant']}")
            
            if isolation_report['violations']:
                print(f"  VIOLATIONS: {isolation_report['violations']}")
            
            # Wait a bit for tenants to run
            print("\n[DEMO] Letting tenants run for 5 seconds...")
            time.sleep(5)
            
            # Check tenant states
            print("\n[DEMO] Tenant states:")
            for tenant in controller.list_tenants():
                print(f"  {tenant['tenant_id']}: {tenant['state']}")
            
            # Shutdown
            print("\n[DEMO] Shutting down...")
            controller.stop(terminate_tenants=True)
            
            print("\n" + "=" * 60)
            print("GaaS DEMONSTRATION COMPLETE")
            print("=" * 60)
            
            return isolation_report
            
    finally:
        # Cleanup demo script
        import os
        os.unlink(demo_script_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_gaas(5)
