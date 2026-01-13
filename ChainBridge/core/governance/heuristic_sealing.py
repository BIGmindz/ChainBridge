"""
Heuristic Sealing Boundary Primitive
PAC-P748-ARCH-GOVERNANCE-DEFENSIBILITY-LOCK-AND-EXECUTION
TASK-11: Implement HeuristicSealingBoundary primitive

Implements:
- Sealing boundary enforcement
- Trade secret protection wrapper
- Heuristic rotation manager
- Audit interface without internal exposure
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from pathlib import Path
from functools import wraps


class ProtectionLevel(Enum):
    """Protection level for sealed components."""
    TRADE_SECRET = "TRADE_SECRET"
    CONFIDENTIAL = "CONFIDENTIAL"
    INTERNAL = "INTERNAL"


class AuditAccessLevel(Enum):
    """Access levels for audit interface."""
    OPERATOR = "OPERATOR"
    ARCHITECT = "ARCHITECT"
    EMERGENCY = "EMERGENCY"


@dataclass
class SealRecord:
    """Record of a sealed heuristic state."""
    seal_id: str
    component_name: str
    algorithm_version: str
    parameter_hash: str  # Hash of parameters, not values
    sealed_at: datetime
    expires_at: datetime
    protection_level: ProtectionLevel
    rotation_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seal_id": self.seal_id,
            "component_name": self.component_name,
            "algorithm_version": self.algorithm_version,
            "parameter_hash": self.parameter_hash,
            "sealed_at": self.sealed_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "protection_level": self.protection_level.value,
            "rotation_count": self.rotation_count,
            "metadata": self.metadata
        }


@dataclass
class AuditMetrics:
    """Aggregated metrics exposed via audit interface."""
    component_name: str
    decision_count: int
    success_rate: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    error_count: int
    error_categories: dict[str, int]
    resource_utilization: float
    last_updated: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_name": self.component_name,
            "decision_count": self.decision_count,
            "success_rate": self.success_rate,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "error_count": self.error_count,
            "error_categories": self.error_categories,
            "resource_utilization": self.resource_utilization,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class RotationEvent:
    """Record of a heuristic rotation."""
    rotation_id: str
    component_name: str
    old_seal_id: str
    new_seal_id: str
    rotation_type: str  # "SCHEDULED" or "EMERGENCY"
    initiated_by: str
    initiated_at: datetime
    completed_at: Optional[datetime]
    transition_period_hours: int
    success: bool
    metrics_delta: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rotation_id": self.rotation_id,
            "component_name": self.component_name,
            "old_seal_id": self.old_seal_id,
            "new_seal_id": self.new_seal_id,
            "rotation_type": self.rotation_type,
            "initiated_by": self.initiated_by,
            "initiated_at": self.initiated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "transition_period_hours": self.transition_period_hours,
            "success": self.success,
            "metrics_delta": self.metrics_delta
        }


class SealedHeuristic:
    """
    Wrapper for a sealed heuristic that protects internals.
    
    Exposes audit interface without revealing:
    - Algorithm source code
    - Parameter values
    - Decision reasoning internals
    """

    def __init__(
        self,
        name: str,
        heuristic_fn: Callable[..., Any],
        parameters: dict[str, Any],
        protection_level: ProtectionLevel = ProtectionLevel.TRADE_SECRET,
        version: str = "1.0.0"
    ):
        self._name = name
        self._heuristic_fn = heuristic_fn
        self._parameters = parameters
        self._protection_level = protection_level
        self._version = version
        
        # Metrics tracking
        self._decision_count = 0
        self._success_count = 0
        self._latencies: list[float] = []
        self._errors: dict[str, int] = {}
        
        # Generate seal
        self._seal = self._generate_seal()

    def _generate_seal(self) -> SealRecord:
        """Generate a seal for the current state."""
        seal_id = f"SEAL-{secrets.token_hex(8).upper()}"
        param_hash = hashlib.sha3_256(
            json.dumps(self._parameters, sort_keys=True).encode()
        ).hexdigest()

        return SealRecord(
            seal_id=seal_id,
            component_name=self._name,
            algorithm_version=self._version,
            parameter_hash=f"sha3-256:{param_hash}",
            sealed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),  # Quarterly
            protection_level=self._protection_level,
            rotation_count=0
        )

    def execute(self, *args, **kwargs) -> Any:
        """Execute the heuristic and track metrics."""
        import time
        
        start = time.time()
        try:
            result = self._heuristic_fn(*args, **kwargs, **self._parameters)
            self._success_count += 1
            return result
        except Exception as e:
            error_type = type(e).__name__
            self._errors[error_type] = self._errors.get(error_type, 0) + 1
            raise
        finally:
            elapsed_ms = (time.time() - start) * 1000
            self._latencies.append(elapsed_ms)
            self._decision_count += 1
            
            # Keep latency buffer bounded
            if len(self._latencies) > 10000:
                self._latencies = self._latencies[-5000:]

    def verify_seal(self) -> tuple[bool, str]:
        """Verify seal integrity."""
        current_hash = hashlib.sha3_256(
            json.dumps(self._parameters, sort_keys=True).encode()
        ).hexdigest()
        
        expected_hash = self._seal.parameter_hash.replace("sha3-256:", "")
        
        if current_hash != expected_hash:
            return False, "Seal broken: parameters modified"
        
        if datetime.now(timezone.utc) > self._seal.expires_at:
            return False, "Seal expired: rotation required"
        
        return True, "Seal valid"

    def get_audit_metrics(self, access_level: AuditAccessLevel) -> AuditMetrics:
        """Get audit metrics (aggregated, no internals exposed)."""
        sorted_latencies = sorted(self._latencies) if self._latencies else [0]
        
        def percentile(data: list[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * p
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f])

        return AuditMetrics(
            component_name=self._name,
            decision_count=self._decision_count,
            success_rate=self._success_count / max(1, self._decision_count),
            latency_p50_ms=percentile(sorted_latencies, 0.50),
            latency_p95_ms=percentile(sorted_latencies, 0.95),
            latency_p99_ms=percentile(sorted_latencies, 0.99),
            error_count=sum(self._errors.values()),
            error_categories=dict(self._errors),  # Categories only, not details
            resource_utilization=0.0,  # Placeholder
            last_updated=datetime.now(timezone.utc)
        )

    def get_seal_record(self) -> SealRecord:
        """Get seal record (safe to expose)."""
        return self._seal

    @property
    def name(self) -> str:
        return self._name

    @property
    def protection_level(self) -> ProtectionLevel:
        return self._protection_level


class HeuristicSealingBoundary:
    """
    Manages sealed heuristics with rotation and audit capabilities.
    
    Enforces:
    - Boundary separation between auditable and sealed components
    - Trade secret protection
    - Mandatory rotation schedule
    - Audit interface availability
    """

    ROTATION_ADVANCE_NOTICE_DAYS = 14
    TRANSITION_PERIOD_DAYS = 7
    QUARTERLY_ROTATION_DAYS = 90

    def __init__(self, storage_path: Optional[Path] = None):
        self._sealed_heuristics: dict[str, SealedHeuristic] = {}
        self._rotation_history: list[RotationEvent] = []
        self._access_log: list[dict[str, Any]] = []
        self.storage_path = storage_path or Path("data/heuristic_seals.json")

    def register_heuristic(
        self,
        name: str,
        heuristic_fn: Callable[..., Any],
        parameters: dict[str, Any],
        protection_level: ProtectionLevel = ProtectionLevel.TRADE_SECRET
    ) -> SealRecord:
        """Register and seal a heuristic."""
        sealed = SealedHeuristic(
            name=name,
            heuristic_fn=heuristic_fn,
            parameters=parameters,
            protection_level=protection_level
        )
        
        self._sealed_heuristics[name] = sealed
        
        self._log_access(
            "REGISTER",
            name,
            "ARCHITECT",
            "Heuristic registered and sealed"
        )
        
        return sealed.get_seal_record()

    def execute_heuristic(self, name: str, *args, **kwargs) -> Any:
        """Execute a sealed heuristic."""
        if name not in self._sealed_heuristics:
            raise KeyError(f"Heuristic '{name}' not found")
        
        sealed = self._sealed_heuristics[name]
        
        # Verify seal before execution
        valid, message = sealed.verify_seal()
        if not valid:
            self._log_access("SEAL_VIOLATION", name, "SYSTEM", message)
            raise RuntimeError(f"Seal violation: {message}")
        
        return sealed.execute(*args, **kwargs)

    def get_audit_metrics(
        self,
        name: str,
        access_level: AuditAccessLevel
    ) -> dict[str, Any]:
        """Get audit metrics for a heuristic."""
        if name not in self._sealed_heuristics:
            raise KeyError(f"Heuristic '{name}' not found")
        
        sealed = self._sealed_heuristics[name]
        
        self._log_access("AUDIT_READ", name, access_level.value, "Metrics accessed")
        
        metrics = sealed.get_audit_metrics(access_level)
        
        result = metrics.to_dict()
        
        # Add seal verification status
        valid, message = sealed.verify_seal()
        result["seal_valid"] = valid
        result["seal_message"] = message
        
        return result

    def rotate_heuristic(
        self,
        name: str,
        new_parameters: dict[str, Any],
        initiated_by: str,
        rotation_type: str = "SCHEDULED"
    ) -> RotationEvent:
        """Rotate a heuristic to new parameters."""
        if name not in self._sealed_heuristics:
            raise KeyError(f"Heuristic '{name}' not found")
        
        old_sealed = self._sealed_heuristics[name]
        old_seal = old_sealed.get_seal_record()
        old_metrics = old_sealed.get_audit_metrics(AuditAccessLevel.ARCHITECT)
        
        # Create new sealed heuristic
        new_sealed = SealedHeuristic(
            name=name,
            heuristic_fn=old_sealed._heuristic_fn,  # Keep same function
            parameters=new_parameters,
            protection_level=old_sealed.protection_level,
            version=f"{float(old_sealed._version) + 0.1:.1f}"
        )
        new_seal = new_sealed.get_seal_record()
        new_seal.rotation_count = old_seal.rotation_count + 1
        
        # Record rotation
        rotation = RotationEvent(
            rotation_id=f"ROT-{secrets.token_hex(6).upper()}",
            component_name=name,
            old_seal_id=old_seal.seal_id,
            new_seal_id=new_seal.seal_id,
            rotation_type=rotation_type,
            initiated_by=initiated_by,
            initiated_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            transition_period_hours=self.TRANSITION_PERIOD_DAYS * 24,
            success=True,
            metrics_delta={
                "old_decision_count": old_metrics.decision_count,
                "old_success_rate": old_metrics.success_rate
            }
        )
        
        # Replace heuristic
        self._sealed_heuristics[name] = new_sealed
        self._rotation_history.append(rotation)
        
        self._log_access(
            "ROTATION",
            name,
            initiated_by,
            f"Rotated from {old_seal.seal_id} to {new_seal.seal_id}"
        )
        
        return rotation

    def check_rotation_due(self) -> list[dict[str, Any]]:
        """Check which heuristics need rotation."""
        due_list = []
        warning_date = datetime.now(timezone.utc) + timedelta(days=self.ROTATION_ADVANCE_NOTICE_DAYS)
        
        for name, sealed in self._sealed_heuristics.items():
            seal = sealed.get_seal_record()
            
            if seal.expires_at <= warning_date:
                due_list.append({
                    "name": name,
                    "seal_id": seal.seal_id,
                    "expires_at": seal.expires_at.isoformat(),
                    "days_remaining": (seal.expires_at - datetime.now(timezone.utc)).days,
                    "status": "OVERDUE" if seal.expires_at <= datetime.now(timezone.utc) else "DUE_SOON"
                })
        
        return due_list

    def _log_access(
        self,
        action: str,
        component: str,
        accessor: str,
        details: str
    ) -> None:
        """Log access to sealed components."""
        self._access_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "component": component,
            "accessor": accessor,
            "details": details
        })

    def get_boundary_summary(self) -> dict[str, Any]:
        """Get summary of sealed components."""
        return {
            "total_sealed": len(self._sealed_heuristics),
            "by_protection_level": {
                level.value: sum(
                    1 for s in self._sealed_heuristics.values()
                    if s.protection_level == level
                )
                for level in ProtectionLevel
            },
            "rotations_total": len(self._rotation_history),
            "rotation_due": self.check_rotation_due(),
            "access_log_entries": len(self._access_log)
        }

    def export(self) -> dict[str, Any]:
        """Export boundary state (seals only, no internals)."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "seals": [
                s.get_seal_record().to_dict()
                for s in self._sealed_heuristics.values()
            ],
            "rotation_history": [r.to_dict() for r in self._rotation_history],
            "summary": self.get_boundary_summary()
        }

    def save(self) -> None:
        """Save boundary state."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export(), f, indent=2)


# Singleton instance
_sealing_boundary: Optional[HeuristicSealingBoundary] = None


def get_sealing_boundary() -> HeuristicSealingBoundary:
    """Get global sealing boundary instance."""
    global _sealing_boundary
    if _sealing_boundary is None:
        _sealing_boundary = HeuristicSealingBoundary()
    return _sealing_boundary


def sealed_heuristic(
    name: str,
    protection_level: ProtectionLevel = ProtectionLevel.TRADE_SECRET
):
    """Decorator to seal a heuristic function."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        
        wrapper._sealed_name = name
        wrapper._protection_level = protection_level
        return wrapper
    
    return decorator
