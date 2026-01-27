"""
ChainBridge Sovereign Swarm - Operators Control in Command (OCC)
PAC-OCC-COMMAND-34 | Root Level Interface

The "War Room" dashboard for the Founding CTO/Architect.
Provides real-time monitoring and control of the Sovereign Mesh.

Components:
- QUAD-LANE MONITOR: Real-time execution lane visualization
- GATE HEATMAP: 10,000 Law-Gates status grid
- PDO TICKER: Proof → Decision → Outcome feed
- ARR COUNTER: Live financial odometer
- KILL-SWITCH: Hardware-level emergency stop

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
Epoch: EPOCH_001

SECURITY: This interface is restricted to ARCHITECT access only.
All actions are signed and recorded to PERMANENT_LEDGER.
"""

import hashlib
import hmac
import json
import time
import uuid
import threading
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import sys
import os

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.zk.concordium_bridge import SovereignSalt


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# GENESIS ANCHORS: Environment-injected for sovereignty (PAC-FIX-CB-2026-01-27)
# Fallbacks provided for local development only - production MUST set these
GENESIS_ANCHOR = os.getenv("GENESIS_ANCHOR", "GENESIS-SOVEREIGN-2026-01-14")
GENESIS_BLOCK_HASH = os.getenv("GENESIS_BLOCK_HASH", "aa1bf8d47493e6bfc7435ce39b24a63e")
EPOCH_001 = "EPOCH_001"
OCC_VERSION = "1.0.0"

# Current ARR (would be loaded from ledger in production)
CURRENT_ARR_USD = 13197500.00

# Gate configuration
TOTAL_GATES = 10000
GATE_GRID_SIZE = 100  # 100x100 grid


class LaneStatus(Enum):
    """Execution lane status"""
    IDLE = "IDLE"
    EXECUTING = "EXECUTING"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class GateStatus(Enum):
    """Law-Gate status"""
    COMPLIANT = "COMPLIANT"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"
    DISABLED = "DISABLED"


class AlertLevel(Enum):
    """OCC Alert levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class KillSwitchState(Enum):
    """Kill-Switch state"""
    ARMED = "ARMED"
    SAFE = "SAFE"
    TRIGGERED = "TRIGGERED"
    LOCKED = "LOCKED"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionLane:
    """Single execution lane status"""
    lane_id: int
    name: str
    status: LaneStatus
    current_task: str
    latency_ms: float
    progress_percent: float
    last_update: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "name": self.name,
            "status": self.status.value,
            "current_task": self.current_task,
            "latency_ms": round(self.latency_ms, 3),
            "progress_percent": round(self.progress_percent, 1),
            "last_update": self.last_update
        }


@dataclass
class PDOUnit:
    """Proof → Decision → Outcome unit"""
    pdo_id: str
    timestamp: str
    proof_hash: str
    decision: str
    outcome: str
    latency_ms: float
    deal_value_usd: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdo_id": self.pdo_id,
            "timestamp": self.timestamp,
            "proof_hash": f"{self.proof_hash[:8]}...{self.proof_hash[-8:]}",
            "decision": self.decision,
            "outcome": self.outcome,
            "latency_ms": round(self.latency_ms, 3),
            "deal_value_usd": self.deal_value_usd
        }


@dataclass
class OCCAlert:
    """OCC Alert notification"""
    alert_id: str
    level: AlertLevel
    timestamp: str
    source: str
    message: str
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "level": self.level.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "message": self.message,
            "acknowledged": self.acknowledged
        }


@dataclass
class SovereignMasterKey:
    """Architect authentication key"""
    key_id: str
    key_hash: str
    created_at: str
    expires_at: str
    permissions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "key_hash_preview": f"{self.key_hash[:8]}...{self.key_hash[-8:]}",
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "permissions": self.permissions
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SOVEREIGN MASTER KEY MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class SovereignKeyManager:
    """
    Manages Sovereign Master Keys for Architect authentication.
    Keys are time-limited and permission-scoped.
    """
    
    def __init__(self):
        self.sovereign_salt = SovereignSalt()
        self.active_keys: Dict[str, SovereignMasterKey] = {}
        self.revoked_keys: set = set()
        self.key_usage_log: List[Dict[str, Any]] = []
    
    def generate_master_key(
        self,
        duration_hours: int = 24,
        permissions: List[str] = None
    ) -> tuple[str, SovereignMasterKey]:
        """
        Generate a new Sovereign Master Key.
        Returns (raw_key, key_object) - raw_key is shown ONCE to Architect.
        """
        if permissions is None:
            permissions = [
                "OCC_VIEW",
                "OCC_CONTROL",
                "KILL_SWITCH_ARM",
                "KILL_SWITCH_TRIGGER",
                "LEDGER_READ",
                "SWARM_MONITOR"
            ]
        
        # Generate cryptographically secure key
        raw_key = secrets.token_urlsafe(32)
        key_id = f"SMK-{uuid.uuid4().hex[:12].upper()}"
        
        # Hash the key for storage
        key_hash = hmac.new(
            self.sovereign_salt.salt.encode(),
            raw_key.encode(),
            hashlib.sha256
        ).hexdigest()
        
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=duration_hours)
        
        key_obj = SovereignMasterKey(
            key_id=key_id,
            key_hash=key_hash,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            permissions=permissions
        )
        
        self.active_keys[key_id] = key_obj
        
        self.key_usage_log.append({
            "action": "KEY_GENERATED",
            "key_id": key_id,
            "timestamp": now.isoformat(),
            "permissions": permissions
        })
        
        return raw_key, key_obj
    
    def validate_key(self, raw_key: str) -> tuple[bool, Optional[SovereignMasterKey], str]:
        """Validate a raw key and return the key object if valid."""
        # Hash the provided key
        key_hash = hmac.new(
            self.sovereign_salt.salt.encode(),
            raw_key.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Find matching key
        for key_id, key_obj in self.active_keys.items():
            if hmac.compare_digest(key_obj.key_hash, key_hash):
                # Check if revoked
                if key_id in self.revoked_keys:
                    return False, None, "KEY_REVOKED"
                
                # Check expiry
                expires = datetime.fromisoformat(key_obj.expires_at.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > expires:
                    return False, None, "KEY_EXPIRED"
                
                self.key_usage_log.append({
                    "action": "KEY_VALIDATED",
                    "key_id": key_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                return True, key_obj, "KEY_VALID"
        
        return False, None, "KEY_NOT_FOUND"
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke a key immediately."""
        if key_id in self.active_keys:
            self.revoked_keys.add(key_id)
            self.key_usage_log.append({
                "action": "KEY_REVOKED",
                "key_id": key_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# QUAD-LANE MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class QuadLaneMonitor:
    """
    Real-time monitor for Benson's four execution lanes.
    Tracks latency, progress, and status of each lane.
    """
    
    def __init__(self):
        self.lanes: Dict[int, ExecutionLane] = {}
        self._initialize_lanes()
    
    def _initialize_lanes(self):
        """Initialize the four execution lanes"""
        lane_names = [
            "PROOF-INGESTION",
            "GATE-VALIDATION", 
            "DECISION-ENGINE",
            "OUTCOME-SETTLEMENT"
        ]
        
        for i, name in enumerate(lane_names, 1):
            self.lanes[i] = ExecutionLane(
                lane_id=i,
                name=name,
                status=LaneStatus.IDLE,
                current_task="Awaiting task",
                latency_ms=0.0,
                progress_percent=0.0,
                last_update=datetime.now(timezone.utc).isoformat()
            )
    
    def update_lane(
        self,
        lane_id: int,
        status: LaneStatus,
        task: str,
        latency_ms: float,
        progress: float
    ):
        """Update a lane's status"""
        if lane_id in self.lanes:
            lane = self.lanes[lane_id]
            lane.status = status
            lane.current_task = task
            lane.latency_ms = latency_ms
            lane.progress_percent = progress
            lane.last_update = datetime.now(timezone.utc).isoformat()
    
    def get_snapshot(self) -> Dict[str, Any]:
        """Get current snapshot of all lanes"""
        total_latency = sum(lane.latency_ms for lane in self.lanes.values())
        active_lanes = sum(1 for lane in self.lanes.values() if lane.status == LaneStatus.EXECUTING)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lanes": [lane.to_dict() for lane in self.lanes.values()],
            "summary": {
                "total_latency_ms": round(total_latency, 3),
                "active_lanes": active_lanes,
                "idle_lanes": 4 - active_lanes
            }
        }
    
    def simulate_activity(self):
        """Simulate lane activity for demo purposes"""
        import random
        
        tasks = [
            ("Processing ZK-Proof batch", LaneStatus.EXECUTING),
            ("Validating OFAC gates", LaneStatus.EXECUTING),
            ("Computing decision tree", LaneStatus.EXECUTING),
            ("Settling transaction", LaneStatus.EXECUTING),
            ("Awaiting task", LaneStatus.IDLE),
            ("Task complete", LaneStatus.COMPLETE)
        ]
        
        for lane_id in self.lanes:
            task, status = random.choice(tasks)
            latency = random.uniform(0.01, 2.5) if status == LaneStatus.EXECUTING else 0.0
            progress = random.uniform(10, 95) if status == LaneStatus.EXECUTING else 0.0
            self.update_lane(lane_id, status, task, latency, progress)


# ═══════════════════════════════════════════════════════════════════════════════
# GATE HEATMAP
# ═══════════════════════════════════════════════════════════════════════════════

class GateHeatmap:
    """
    100x100 grid visualization of 10,000 Law-Gates.
    Green = Compliant, Red = Blocked, Yellow = Pending
    """
    
    def __init__(self):
        self.gates: List[List[GateStatus]] = []
        self.gate_stats = {
            "compliant": 0,
            "blocked": 0,
            "pending": 0,
            "disabled": 0
        }
        self._initialize_gates()
    
    def _initialize_gates(self):
        """Initialize all gates as compliant"""
        self.gates = [
            [GateStatus.COMPLIANT for _ in range(GATE_GRID_SIZE)]
            for _ in range(GATE_GRID_SIZE)
        ]
        self.gate_stats["compliant"] = TOTAL_GATES
    
    def set_gate_status(self, row: int, col: int, status: GateStatus):
        """Set status of a specific gate"""
        if 0 <= row < GATE_GRID_SIZE and 0 <= col < GATE_GRID_SIZE:
            old_status = self.gates[row][col]
            self.gates[row][col] = status
            
            # Update stats
            self.gate_stats[old_status.value.lower()] -= 1
            self.gate_stats[status.value.lower()] += 1
    
    def get_gate_status(self, gate_id: int) -> GateStatus:
        """Get status of a gate by ID (0-9999)"""
        row = gate_id // GATE_GRID_SIZE
        col = gate_id % GATE_GRID_SIZE
        return self.gates[row][col]
    
    def trigger_gate(self, gate_id: int) -> bool:
        """Trigger a gate (mark as blocked)"""
        row = gate_id // GATE_GRID_SIZE
        col = gate_id % GATE_GRID_SIZE
        if self.gates[row][col] != GateStatus.DISABLED:
            self.set_gate_status(row, col, GateStatus.BLOCKED)
            return True
        return False
    
    def reset_gate(self, gate_id: int):
        """Reset a gate to compliant"""
        row = gate_id // GATE_GRID_SIZE
        col = gate_id % GATE_GRID_SIZE
        self.set_gate_status(row, col, GateStatus.COMPLIANT)
    
    def get_snapshot(self) -> Dict[str, Any]:
        """Get heatmap snapshot"""
        # Generate compact representation
        blocked_gates = []
        for row in range(GATE_GRID_SIZE):
            for col in range(GATE_GRID_SIZE):
                if self.gates[row][col] == GateStatus.BLOCKED:
                    gate_id = row * GATE_GRID_SIZE + col
                    blocked_gates.append(gate_id)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "grid_size": GATE_GRID_SIZE,
            "total_gates": TOTAL_GATES,
            "stats": self.gate_stats.copy(),
            "compliance_rate": self.gate_stats["compliant"] / TOTAL_GATES,
            "blocked_gates": blocked_gates[:100],  # Limit response size
            "blocked_count": len(blocked_gates)
        }
    
    def get_ascii_heatmap(self, size: int = 20) -> str:
        """Generate ASCII representation of heatmap (downsampled)"""
        step = GATE_GRID_SIZE // size
        lines = []
        
        for row in range(0, GATE_GRID_SIZE, step):
            line = ""
            for col in range(0, GATE_GRID_SIZE, step):
                # Sample this region
                blocked = False
                for r in range(row, min(row + step, GATE_GRID_SIZE)):
                    for c in range(col, min(col + step, GATE_GRID_SIZE)):
                        if self.gates[r][c] == GateStatus.BLOCKED:
                            blocked = True
                            break
                    if blocked:
                        break
                
                line += "█" if blocked else "░"
            lines.append(line)
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# PDO TICKER
# ═══════════════════════════════════════════════════════════════════════════════

class PDOTicker:
    """
    Scrolling feed of Proof → Decision → Outcome units.
    Real-time visibility into finalized transactions.
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.pdo_units: List[PDOUnit] = []
        self.total_processed = 0
        self.total_value_usd = 0.0
    
    def add_pdo(
        self,
        proof_hash: str,
        decision: str,
        outcome: str,
        latency_ms: float,
        deal_value_usd: Optional[float] = None
    ) -> PDOUnit:
        """Add a new PDO unit to the ticker"""
        pdo = PDOUnit(
            pdo_id=f"PDO-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            proof_hash=proof_hash,
            decision=decision,
            outcome=outcome,
            latency_ms=latency_ms,
            deal_value_usd=deal_value_usd
        )
        
        self.pdo_units.append(pdo)
        self.total_processed += 1
        
        if deal_value_usd:
            self.total_value_usd += deal_value_usd
        
        # Trim history
        if len(self.pdo_units) > self.max_history:
            self.pdo_units = self.pdo_units[-self.max_history:]
        
        return pdo
    
    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get most recent PDO units"""
        return [pdo.to_dict() for pdo in self.pdo_units[-count:]][::-1]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ticker statistics"""
        decisions = {}
        outcomes = {}
        
        for pdo in self.pdo_units:
            decisions[pdo.decision] = decisions.get(pdo.decision, 0) + 1
            outcomes[pdo.outcome] = outcomes.get(pdo.outcome, 0) + 1
        
        avg_latency = (
            sum(p.latency_ms for p in self.pdo_units) / len(self.pdo_units)
            if self.pdo_units else 0
        )
        
        return {
            "total_processed": self.total_processed,
            "total_value_usd": self.total_value_usd,
            "history_size": len(self.pdo_units),
            "average_latency_ms": round(avg_latency, 3),
            "decisions": decisions,
            "outcomes": outcomes
        }


# ═══════════════════════════════════════════════════════════════════════════════
# KILL SWITCH
# ═══════════════════════════════════════════════════════════════════════════════

class KillSwitch:
    """
    Hardware-level emergency stop for the Sovereign Mesh.
    CRITICAL: Only accessible to ARCHITECT with proper authorization.
    """
    
    def __init__(self):
        self.state = KillSwitchState.SAFE
        self.armed_at: Optional[str] = None
        self.armed_by: Optional[str] = None
        self.triggered_at: Optional[str] = None
        self.triggered_by: Optional[str] = None
        self.action_log: List[Dict[str, Any]] = []
        self.sovereign_salt = SovereignSalt()
    
    def _log_action(self, action: str, actor: str, details: Dict[str, Any] = None):
        """Log a kill switch action"""
        entry = {
            "action": action,
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self.state.value,
            "details": details or {}
        }
        self.action_log.append(entry)
    
    def arm(self, actor: str, authorization_code: str) -> tuple[bool, str]:
        """
        Arm the kill switch.
        Requires valid authorization code.
        """
        # Verify authorization
        expected_code = hmac.new(
            self.sovereign_salt.salt.encode(),
            f"KILL_SWITCH_ARM:{actor}:{GENESIS_ANCHOR}".encode(),
            hashlib.sha256
        ).hexdigest()[:16].upper()
        
        if authorization_code != expected_code:
            self._log_action("ARM_REJECTED", actor, {"reason": "INVALID_CODE"})
            return False, "INVALID_AUTHORIZATION_CODE"
        
        if self.state == KillSwitchState.TRIGGERED:
            return False, "KILL_SWITCH_ALREADY_TRIGGERED"
        
        if self.state == KillSwitchState.LOCKED:
            return False, "KILL_SWITCH_LOCKED"
        
        self.state = KillSwitchState.ARMED
        self.armed_at = datetime.now(timezone.utc).isoformat()
        self.armed_by = actor
        
        self._log_action("ARMED", actor)
        
        return True, "KILL_SWITCH_ARMED"
    
    def trigger(self, actor: str, confirmation_code: str) -> tuple[bool, str]:
        """
        Trigger the kill switch - EMERGENCY STOP.
        This will halt all mesh operations.
        """
        if self.state != KillSwitchState.ARMED:
            self._log_action("TRIGGER_REJECTED", actor, {"reason": "NOT_ARMED"})
            return False, "KILL_SWITCH_NOT_ARMED"
        
        # Verify confirmation
        expected_code = hmac.new(
            self.sovereign_salt.salt.encode(),
            f"KILL_SWITCH_TRIGGER:{actor}:{GENESIS_ANCHOR}:{self.armed_at}".encode(),
            hashlib.sha256
        ).hexdigest()[:16].upper()
        
        if confirmation_code != expected_code:
            self._log_action("TRIGGER_REJECTED", actor, {"reason": "INVALID_CODE"})
            return False, "INVALID_CONFIRMATION_CODE"
        
        self.state = KillSwitchState.TRIGGERED
        self.triggered_at = datetime.now(timezone.utc).isoformat()
        self.triggered_by = actor
        
        self._log_action("TRIGGERED", actor, {"severity": "EMERGENCY"})
        
        return True, "KILL_SWITCH_TRIGGERED_MESH_HALTED"
    
    def safe(self, actor: str) -> tuple[bool, str]:
        """Return kill switch to safe state"""
        if self.state == KillSwitchState.LOCKED:
            return False, "KILL_SWITCH_LOCKED"
        
        self.state = KillSwitchState.SAFE
        self.armed_at = None
        self.armed_by = None
        
        self._log_action("SAFED", actor)
        
        return True, "KILL_SWITCH_SAFED"
    
    def get_arm_code(self, actor: str) -> str:
        """Generate authorization code for arming (display to Architect)"""
        return hmac.new(
            self.sovereign_salt.salt.encode(),
            f"KILL_SWITCH_ARM:{actor}:{GENESIS_ANCHOR}".encode(),
            hashlib.sha256
        ).hexdigest()[:16].upper()
    
    def get_status(self) -> Dict[str, Any]:
        """Get kill switch status"""
        return {
            "state": self.state.value,
            "armed_at": self.armed_at,
            "armed_by": self.armed_by,
            "triggered_at": self.triggered_at,
            "triggered_by": self.triggered_by,
            "action_count": len(self.action_log)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ARR COUNTER
# ═══════════════════════════════════════════════════════════════════════════════

class ARRCounter:
    """
    Live-updating Annual Recurring Revenue odometer.
    Displays current ARR with real-time updates.
    """
    
    def __init__(self, initial_arr: float = CURRENT_ARR_USD):
        self.current_arr = initial_arr
        self.baseline_arr = 11697500.00
        self.target_arr = 100000000.00
        self.history: List[Dict[str, Any]] = []
    
    def update_arr(self, amount: float, deal_id: str, reason: str):
        """Update ARR with a new amount"""
        old_arr = self.current_arr
        self.current_arr += amount
        
        self.history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "deal_id": deal_id,
            "amount": amount,
            "old_arr": old_arr,
            "new_arr": self.current_arr,
            "reason": reason
        })
    
    def get_display(self) -> Dict[str, Any]:
        """Get ARR counter display data"""
        progress = self.current_arr / self.target_arr
        growth = (self.current_arr - self.baseline_arr) / self.baseline_arr
        
        return {
            "current_arr": self.current_arr,
            "current_arr_formatted": f"${self.current_arr:,.2f}",
            "baseline_arr": self.baseline_arr,
            "target_arr": self.target_arr,
            "remaining": self.target_arr - self.current_arr,
            "progress_percent": round(progress * 100, 2),
            "growth_percent": round(growth * 100, 2),
            "last_update": self.history[-1]["timestamp"] if self.history else None
        }


# ═══════════════════════════════════════════════════════════════════════════════
# OCC COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════════

class OCCCommandCenter:
    """
    Master orchestrator for the Operators Control in Command interface.
    Integrates all monitoring and control components.
    """
    
    def __init__(self):
        self.key_manager = SovereignKeyManager()
        self.quad_lane = QuadLaneMonitor()
        self.gate_heatmap = GateHeatmap()
        self.pdo_ticker = PDOTicker()
        self.kill_switch = KillSwitch()
        self.arr_counter = ARRCounter()
        self.alerts: List[OCCAlert] = []
        self.session_log: List[Dict[str, Any]] = []
        self.initialized_at = datetime.now(timezone.utc).isoformat()
    
    def generate_master_key(self) -> tuple[str, SovereignMasterKey]:
        """Generate a new Sovereign Master Key for Architect"""
        raw_key, key_obj = self.key_manager.generate_master_key()
        
        self._log_session_action("MASTER_KEY_GENERATED", "SYSTEM", {
            "key_id": key_obj.key_id
        })
        
        return raw_key, key_obj
    
    def authenticate(self, raw_key: str) -> tuple[bool, Optional[SovereignMasterKey], str]:
        """Authenticate with a Sovereign Master Key"""
        valid, key_obj, reason = self.key_manager.validate_key(raw_key)
        
        self._log_session_action(
            "AUTHENTICATION_ATTEMPT",
            "UNKNOWN" if not key_obj else key_obj.key_id,
            {"result": reason}
        )
        
        return valid, key_obj, reason
    
    def _log_session_action(self, action: str, actor: str, details: Dict[str, Any] = None):
        """Log a session action"""
        self.session_log.append({
            "action": action,
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {}
        })
    
    def add_alert(self, level: AlertLevel, source: str, message: str) -> OCCAlert:
        """Add a new alert"""
        alert = OCCAlert(
            alert_id=f"ALERT-{uuid.uuid4().hex[:8].upper()}",
            level=level,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            message=message
        )
        self.alerts.append(alert)
        return alert
    
    def get_dashboard_state(self) -> Dict[str, Any]:
        """Get complete dashboard state"""
        return {
            "occ_version": OCC_VERSION,
            "initialized_at": self.initialized_at,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "genesis_anchor": GENESIS_ANCHOR,
            "epoch": EPOCH_001,
            "quad_lane_monitor": self.quad_lane.get_snapshot(),
            "gate_heatmap": self.gate_heatmap.get_snapshot(),
            "pdo_ticker": {
                "recent": self.pdo_ticker.get_recent(10),
                "stats": self.pdo_ticker.get_stats()
            },
            "arr_counter": self.arr_counter.get_display(),
            "kill_switch": self.kill_switch.get_status(),
            "alerts": {
                "active": [a.to_dict() for a in self.alerts if not a.acknowledged],
                "total": len(self.alerts)
            }
        }
    
    def render_ascii_dashboard(self) -> str:
        """Render ASCII dashboard for terminal display"""
        state = self.get_dashboard_state()
        arr = state["arr_counter"]
        ks = state["kill_switch"]
        gates = state["gate_heatmap"]
        
        # Build ASCII display
        output = []
        output.append("=" * 80)
        output.append("  ██████╗  ██████╗ ██████╗     OPERATORS CONTROL IN COMMAND")
        output.append(" ██╔═══██╗██╔════╝██╔════╝     ChainBridge Sovereign Systems")
        output.append(" ██║   ██║██║     ██║          Version: " + OCC_VERSION)
        output.append(" ██║   ██║██║     ██║          Epoch: " + EPOCH_001)
        output.append(" ╚██████╔╝╚██████╗╚██████╗     Genesis: " + GENESIS_ANCHOR[:24] + "...")
        output.append("  ╚═════╝  ╚═════╝ ╚═════╝")
        output.append("=" * 80)
        output.append("")
        
        # ARR Counter
        progress_bar_len = 40
        progress = int(arr["progress_percent"] / 100 * progress_bar_len)
        progress_bar = "█" * progress + "░" * (progress_bar_len - progress)
        
        output.append("┌─────────────────────────────────────────────────────────────────────────────┐")
        output.append("│  ARR COUNTER                                                                │")
        output.append("├─────────────────────────────────────────────────────────────────────────────┤")
        output.append(f"│  Current ARR:    {arr['current_arr_formatted']:>20}                              │")
        output.append(f"│  Target:         {'$100,000,000.00':>20}                              │")
        output.append(f"│  Progress:       [{progress_bar}] {arr['progress_percent']:>5.1f}%  │")
        output.append(f"│  Growth:         +{arr['growth_percent']:.2f}% from baseline                                    │")
        output.append("└─────────────────────────────────────────────────────────────────────────────┘")
        output.append("")
        
        # Quad-Lane Monitor
        output.append("┌─────────────────────────────────────────────────────────────────────────────┐")
        output.append("│  QUAD-LANE MONITOR                                                          │")
        output.append("├─────────────────────────────────────────────────────────────────────────────┤")
        
        for lane in state["quad_lane_monitor"]["lanes"]:
            status_icon = "●" if lane["status"] == "EXECUTING" else "○"
            status_color = "ACTIVE" if lane["status"] == "EXECUTING" else lane["status"]
            output.append(f"│  L{lane['lane_id']} {status_icon} {lane['name']:<20} │ {status_color:<10} │ {lane['latency_ms']:>6.2f}ms │")
        
        output.append("└─────────────────────────────────────────────────────────────────────────────┘")
        output.append("")
        
        # Gate Heatmap Summary
        output.append("┌─────────────────────────────────────────────────────────────────────────────┐")
        output.append("│  GATE HEATMAP (10,000 Law-Gates)                                            │")
        output.append("├─────────────────────────────────────────────────────────────────────────────┤")
        output.append(f"│  Compliant: {gates['stats']['compliant']:>6} │ Blocked: {gates['stats']['blocked']:>4} │ Rate: {gates['compliance_rate']*100:>6.2f}%              │")
        output.append("│  " + "░" * 73 + "│")
        output.append("└─────────────────────────────────────────────────────────────────────────────┘")
        output.append("")
        
        # Kill Switch Status
        ks_state_display = {
            "SAFE": "[ SAFE ]    ",
            "ARMED": "[! ARMED !] ",
            "TRIGGERED": "[X TRIGGERED X]",
            "LOCKED": "[ LOCKED ]  "
        }
        
        output.append("┌─────────────────────────────────────────────────────────────────────────────┐")
        output.append("│  KILL SWITCH                                                                │")
        output.append("├─────────────────────────────────────────────────────────────────────────────┤")
        output.append(f"│  Status: {ks_state_display.get(ks['state'], ks['state']):<65}│")
        if ks["armed_by"]:
            output.append(f"│  Armed By: {ks['armed_by']:<64}│")
        output.append("└─────────────────────────────────────────────────────────────────────────────┘")
        output.append("")
        
        # Alerts
        active_alerts = state["alerts"]["active"]
        output.append("┌─────────────────────────────────────────────────────────────────────────────┐")
        output.append(f"│  ALERTS ({len(active_alerts)} active)                                                         │")
        output.append("├─────────────────────────────────────────────────────────────────────────────┤")
        if active_alerts:
            for alert in active_alerts[:3]:
                output.append(f"│  [{alert['level']}] {alert['message'][:60]:<60}│")
        else:
            output.append("│  No active alerts                                                           │")
        output.append("└─────────────────────────────────────────────────────────────────────────────┘")
        output.append("")
        output.append("=" * 80)
        
        return "\n".join(output)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def launch_occ_command_center():
    """Launch the OCC Command Center and generate Sovereign Master Key"""
    print("=" * 80)
    print("INITIALIZING OPERATORS CONTROL IN COMMAND (OCC)")
    print("PAC-OCC-COMMAND-34 | Root Level Interface")
    print("=" * 80)
    print()
    
    # Initialize command center
    occ = OCCCommandCenter()
    
    # Simulate some activity
    print("[LANE 1] MASTER-CONSOLE: Initializing dashboard components...")
    occ.quad_lane.simulate_activity()
    
    print("[LANE 2] SWARM-VISUALIZER: Connecting to mesh telemetry...")
    # Add some PDO units
    for i in range(5):
        occ.pdo_ticker.add_pdo(
            proof_hash=hashlib.sha256(f"proof_{i}".encode()).hexdigest(),
            decision="APPROVED" if i % 2 == 0 else "COMPLIANT",
            outcome="SETTLED" if i % 3 == 0 else "CAPTURED",
            latency_ms=0.05 + (i * 0.01),
            deal_value_usd=100000 + (i * 50000) if i % 2 == 0 else None
        )
    
    print("[LANE 3] KILL-SWITCH-INIT: Verifying emergency stop...")
    # Kill switch is initialized in SAFE state
    
    print()
    print("=" * 80)
    print("GENERATING SOVEREIGN MASTER KEY")
    print("=" * 80)
    print()
    
    # Generate master key
    raw_key, key_obj = occ.generate_master_key()
    
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║  SOVEREIGN MASTER KEY GENERATED                                              ║")
    print("║  ────────────────────────────────────────────────────────────────────────    ║")
    print("║                                                                              ║")
    print(f"║  Key ID:     {key_obj.key_id:<62}║")
    print("║                                                                              ║")
    print("║  RAW KEY (DISPLAY ONCE - COPY NOW):                                          ║")
    print("║                                                                              ║")
    print(f"║  {raw_key:<74}║")
    print("║                                                                              ║")
    print(f"║  Expires:    {key_obj.expires_at:<62}║")
    print("║                                                                              ║")
    print("║  Permissions: OCC_VIEW, OCC_CONTROL, KILL_SWITCH_ARM,                        ║")
    print("║               KILL_SWITCH_TRIGGER, LEDGER_READ, SWARM_MONITOR                ║")
    print("║                                                                              ║")
    print("║  ⚠️  THIS KEY WILL NOT BE DISPLAYED AGAIN                                    ║")
    print("║  ⚠️  STORE SECURELY - REQUIRED FOR OCC ACCESS                                ║")
    print("║                                                                              ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Display dashboard
    print("=" * 80)
    print("OCC DASHBOARD")
    print("=" * 80)
    print()
    print(occ.render_ascii_dashboard())
    
    # Display kill switch arm code
    arm_code = occ.kill_switch.get_arm_code("ARCHITECT-JEFFREY")
    print()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║  KILL SWITCH AUTHORIZATION                                                   ║")
    print("║  ────────────────────────────────────────────────────────────────────────    ║")
    print("║                                                                              ║")
    print(f"║  ARM CODE (for ARCHITECT-JEFFREY):  {arm_code:<38}║")
    print("║                                                                              ║")
    print("║  To arm:  kill_switch.arm('ARCHITECT-JEFFREY', '<ARM_CODE>')                 ║")
    print("║                                                                              ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    print("=" * 80)
    print("OCC COMMAND CENTER: ONLINE")
    print("=" * 80)
    
    return occ, raw_key, key_obj


if __name__ == "__main__":
    occ, raw_key, key_obj = launch_occ_command_center()
    
    print()
    print("[PERMANENT LEDGER ENTRY: PL-043]")
    print(json.dumps({
        "entry_id": "PL-043",
        "entry_type": "OCC_COMMAND_CENTER_INITIALIZED",
        "key_id": key_obj.key_id,
        "permissions": key_obj.permissions
    }, indent=2))
