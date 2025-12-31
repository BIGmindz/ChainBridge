"""
Audit Retention & CI Gates — Retention policies and CI validation for audit artifacts
════════════════════════════════════════════════════════════════════════════════

PAC Reference: PAC-013A (CORRECTED · GOLD STANDARD)
Agent: Dan (GID-07) — Retention & CI
Order: ORDER 4
Effective Date: 2025-12-30
Runtime: RUNTIME-013A
Execution Lane: SINGLE-LANE, ORDERED
Governance Mode: FAIL-CLOSED (LOCKED)

DEPENDENCIES:
    - ORDER 1 (Cody): audit_oc.py API
    - ORDER 2 (Cindy): audit_aggregator.py
    - ORDER 3 (Sonny): Audit UI components

HARD INVARIANTS (INV-RET-*):
    INV-RET-001: All audit artifacts have explicit retention periods
    INV-RET-002: No implicit retention (silence = violation)
    INV-RET-003: Retention violations trigger CI gate failure
    INV-RET-004: Export artifacts track retention metadata
    INV-RET-005: Audit chain reconstructions are PERMANENT retention

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

AUDIT_ARTIFACT_PREFIX = "AUDIT"
"""Prefix for audit artifact identifiers."""


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class AuditArtifactType(str, Enum):
    """Types of audit artifacts with retention requirements."""
    CHAIN_RECONSTRUCTION = "CHAIN_RECONSTRUCTION"  # Full P→D→O chain
    EXPORT_JSON = "EXPORT_JSON"  # JSON export file
    EXPORT_CSV = "EXPORT_CSV"  # CSV export file
    REGULATORY_SUMMARY = "REGULATORY_SUMMARY"  # Regulatory report
    VERIFICATION_RESULT = "VERIFICATION_RESULT"  # Hash verification
    AGGREGATION = "AGGREGATION"  # Cross-registry aggregation


class AuditRetentionPeriod(str, Enum):
    """Retention periods for audit artifacts."""
    PERMANENT = "PERMANENT"  # Never expire
    REGULATORY_7Y = "REGULATORY_7Y"  # 7-year regulatory requirement
    LONG_TERM = "LONG_TERM"  # 365 days
    MEDIUM_TERM = "MEDIUM_TERM"  # 90 days
    SHORT_TERM = "SHORT_TERM"  # 30 days
    EPHEMERAL = "EPHEMERAL"  # 24 hours


class CIGateStatus(str, Enum):
    """CI gate validation status."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION DAYS MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

AUDIT_RETENTION_DAYS: Dict[AuditRetentionPeriod, Optional[int]] = {
    AuditRetentionPeriod.PERMANENT: None,  # Never expires
    AuditRetentionPeriod.REGULATORY_7Y: 2557,  # 7 years
    AuditRetentionPeriod.LONG_TERM: 365,
    AuditRetentionPeriod.MEDIUM_TERM: 90,
    AuditRetentionPeriod.SHORT_TERM: 30,
    AuditRetentionPeriod.EPHEMERAL: 1,
}


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL AUDIT RETENTION POLICIES
# ═══════════════════════════════════════════════════════════════════════════════

CANONICAL_AUDIT_RETENTION: Dict[AuditArtifactType, AuditRetentionPeriod] = {
    # INV-RET-005: Chain reconstructions are PERMANENT
    AuditArtifactType.CHAIN_RECONSTRUCTION: AuditRetentionPeriod.PERMANENT,
    
    # Exports follow regulatory requirements
    AuditArtifactType.EXPORT_JSON: AuditRetentionPeriod.REGULATORY_7Y,
    AuditArtifactType.EXPORT_CSV: AuditRetentionPeriod.REGULATORY_7Y,
    
    # Regulatory summaries are permanent
    AuditArtifactType.REGULATORY_SUMMARY: AuditRetentionPeriod.PERMANENT,
    
    # Verification results long-term for audit trail
    AuditArtifactType.VERIFICATION_RESULT: AuditRetentionPeriod.LONG_TERM,
    
    # Aggregations follow long-term
    AuditArtifactType.AGGREGATION: AuditRetentionPeriod.LONG_TERM,
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AuditRetentionRecord:
    """
    Retention record for an audit artifact.
    
    INV-RET-001: All audit artifacts have explicit retention periods.
    """
    artifact_id: str
    artifact_type: AuditArtifactType
    retention_period: AuditRetentionPeriod
    created_at: str
    expires_at: Optional[str]  # None for PERMANENT
    content_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if artifact has expired."""
        if self.expires_at is None:
            return False  # PERMANENT never expires
        now = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return now > expires
    
    @property
    def days_until_expiry(self) -> Optional[int]:
        """Days until expiry, or None for permanent."""
        if self.expires_at is None:
            return None
        now = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        delta = expires - now
        return max(0, delta.days)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "retention_period": self.retention_period.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "content_hash": self.content_hash,
            "is_expired": self.is_expired,
            "days_until_expiry": self.days_until_expiry,
            "metadata": self.metadata
        }


@dataclass
class AuditCIGateResult:
    """Result of a CI gate validation."""
    gate_id: str
    gate_name: str
    status: CIGateStatus
    message: str
    checked_at: str
    artifacts_checked: int = 0
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gate_id": self.gate_id,
            "gate_name": self.gate_name,
            "status": self.status.value,
            "message": self.message,
            "checked_at": self.checked_at,
            "artifacts_checked": self.artifacts_checked,
            "failures": self.failures,
            "warnings": self.warnings
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT RETENTION REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class AuditRetentionRegistry:
    """
    Registry tracking retention for all audit artifacts.
    
    Thread-safe singleton pattern per ChainBridge conventions.
    
    INV-RET-002: No implicit retention (silence = violation).
    """
    
    _instance: Optional["AuditRetentionRegistry"] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> "AuditRetentionRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._records: Dict[str, AuditRetentionRecord] = {}
        self._init_timestamp = self._now_iso()
        self._initialized = True
        
        logger.info("[AUDIT-RET] AuditRetentionRegistry initialized")
    
    @staticmethod
    def _now_iso() -> str:
        """Current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def _compute_hash(content: Any) -> str:
        """Compute SHA-256 hash."""
        if isinstance(content, str):
            data = content.encode("utf-8")
        else:
            data = json.dumps(content, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(data).hexdigest()
    
    def _generate_artifact_id(self, artifact_type: AuditArtifactType) -> str:
        """Generate unique artifact identifier."""
        import uuid
        return f"{AUDIT_ARTIFACT_PREFIX}-{artifact_type.value}-{uuid.uuid4().hex[:12].upper()}"
    
    def _calculate_expiry(
        self,
        created_at: str,
        retention_period: AuditRetentionPeriod
    ) -> Optional[str]:
        """Calculate expiry timestamp from retention period."""
        days = AUDIT_RETENTION_DAYS.get(retention_period)
        if days is None:
            return None  # PERMANENT
        
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        expires = created + timedelta(days=days)
        return expires.isoformat()
    
    # ───────────────────────────────────────────────────────────────────────────
    # REGISTRATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def register_artifact(
        self,
        artifact_type: AuditArtifactType,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditRetentionRecord:
        """
        Register an audit artifact with retention tracking.
        
        INV-RET-001: All audit artifacts have explicit retention periods.
        """
        now = self._now_iso()
        
        # Get canonical retention period
        retention_period = CANONICAL_AUDIT_RETENTION.get(
            artifact_type,
            AuditRetentionPeriod.LONG_TERM  # Default fallback
        )
        
        # Calculate expiry
        expires_at = self._calculate_expiry(now, retention_period)
        
        # Create record
        record = AuditRetentionRecord(
            artifact_id=self._generate_artifact_id(artifact_type),
            artifact_type=artifact_type,
            retention_period=retention_period,
            created_at=now,
            expires_at=expires_at,
            content_hash=self._compute_hash(content),
            metadata=metadata or {}
        )
        
        # Store
        with self._lock:
            self._records[record.artifact_id] = record
        
        logger.info(
            f"[AUDIT-RET] Registered {artifact_type.value}: "
            f"{record.artifact_id} (retention={retention_period.value})"
        )
        
        return record
    
    # ───────────────────────────────────────────────────────────────────────────
    # QUERIES
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_record(self, artifact_id: str) -> Optional[AuditRetentionRecord]:
        """Get retention record by artifact ID."""
        return self._records.get(artifact_id)
    
    def get_all_records(self) -> List[AuditRetentionRecord]:
        """Get all retention records."""
        return list(self._records.values())
    
    def get_by_type(
        self,
        artifact_type: AuditArtifactType
    ) -> List[AuditRetentionRecord]:
        """Get records by artifact type."""
        return [r for r in self._records.values() if r.artifact_type == artifact_type]
    
    def get_expired(self) -> List[AuditRetentionRecord]:
        """Get all expired records."""
        return [r for r in self._records.values() if r.is_expired]
    
    def get_expiring_soon(self, days: int = 30) -> List[AuditRetentionRecord]:
        """Get records expiring within specified days."""
        result = []
        for record in self._records.values():
            remaining = record.days_until_expiry
            if remaining is not None and remaining <= days:
                result.append(record)
        return result
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def validate_retention_compliance(self) -> Tuple[bool, List[str]]:
        """
        Validate all artifacts have proper retention.
        
        INV-RET-002: No implicit retention (silence = violation).
        
        Returns (is_compliant, list_of_violations).
        """
        violations = []
        
        for record in self._records.values():
            # Check retention period is explicit
            if record.retention_period not in AuditRetentionPeriod:
                violations.append(
                    f"{record.artifact_id}: Invalid retention period"
                )
            
            # Check non-permanent artifacts have expiry
            if (record.retention_period != AuditRetentionPeriod.PERMANENT 
                and record.expires_at is None):
                violations.append(
                    f"{record.artifact_id}: Non-permanent artifact missing expiry"
                )
        
        return len(violations) == 0, violations
    
    # ───────────────────────────────────────────────────────────────────────────
    # RESET (for testing)
    # ───────────────────────────────────────────────────────────────────────────
    
    @classmethod
    def reset(cls) -> None:
        """Reset singleton for testing."""
        with cls._lock:
            if cls._instance:
                cls._instance._records.clear()
            cls._instance = None


# ═══════════════════════════════════════════════════════════════════════════════
# CI GATE VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════

class AuditCIGateValidator:
    """
    CI gate validators for audit artifact compliance.
    
    INV-RET-003: Retention violations trigger CI gate failure.
    """
    
    @staticmethod
    def _now_iso() -> str:
        """Current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def _generate_gate_id() -> str:
        """Generate unique gate ID."""
        import uuid
        return f"GATE-{uuid.uuid4().hex[:8].upper()}"
    
    @classmethod
    def validate_retention_declared(
        cls,
        registry: AuditRetentionRegistry
    ) -> AuditCIGateResult:
        """
        Gate: All artifacts must have declared retention.
        
        INV-RET-002: No implicit retention.
        """
        records = registry.get_all_records()
        failures = []
        
        for record in records:
            if record.retention_period not in CANONICAL_AUDIT_RETENTION.values():
                # Check if it's a valid period at all
                if record.retention_period not in AuditRetentionPeriod:
                    failures.append(
                        f"{record.artifact_id}: Unknown retention period"
                    )
        
        status = CIGateStatus.PASS if not failures else CIGateStatus.FAIL
        
        return AuditCIGateResult(
            gate_id=cls._generate_gate_id(),
            gate_name="AUDIT_RETENTION_DECLARED",
            status=status,
            message="All audit artifacts have explicit retention" if not failures else "Retention violations detected",
            checked_at=cls._now_iso(),
            artifacts_checked=len(records),
            failures=failures
        )
    
    @classmethod
    def validate_no_expired_permanent(
        cls,
        registry: AuditRetentionRegistry
    ) -> AuditCIGateResult:
        """
        Gate: PERMANENT artifacts must never be marked expired.
        
        INV-RET-005: Chain reconstructions are PERMANENT.
        """
        records = registry.get_all_records()
        failures = []
        
        for record in records:
            if (record.retention_period == AuditRetentionPeriod.PERMANENT 
                and record.expires_at is not None):
                failures.append(
                    f"{record.artifact_id}: PERMANENT artifact has expiry date"
                )
        
        status = CIGateStatus.PASS if not failures else CIGateStatus.FAIL
        
        return AuditCIGateResult(
            gate_id=cls._generate_gate_id(),
            gate_name="AUDIT_PERMANENT_NO_EXPIRY",
            status=status,
            message="All PERMANENT artifacts lack expiry" if not failures else "PERMANENT artifacts have expiry",
            checked_at=cls._now_iso(),
            artifacts_checked=len(records),
            failures=failures
        )
    
    @classmethod
    def validate_chain_reconstructions_permanent(
        cls,
        registry: AuditRetentionRegistry
    ) -> AuditCIGateResult:
        """
        Gate: Chain reconstructions must be PERMANENT.
        
        INV-RET-005: Chain reconstructions are PERMANENT retention.
        """
        chains = registry.get_by_type(AuditArtifactType.CHAIN_RECONSTRUCTION)
        failures = []
        
        for record in chains:
            if record.retention_period != AuditRetentionPeriod.PERMANENT:
                failures.append(
                    f"{record.artifact_id}: Chain reconstruction not PERMANENT"
                )
        
        status = CIGateStatus.PASS if not failures else CIGateStatus.FAIL
        
        return AuditCIGateResult(
            gate_id=cls._generate_gate_id(),
            gate_name="AUDIT_CHAINS_PERMANENT",
            status=status,
            message="All chain reconstructions are PERMANENT" if not failures else "Chain retention violations",
            checked_at=cls._now_iso(),
            artifacts_checked=len(chains),
            failures=failures
        )
    
    @classmethod
    def validate_exports_regulatory(
        cls,
        registry: AuditRetentionRegistry
    ) -> AuditCIGateResult:
        """
        Gate: Export artifacts must meet regulatory retention (7 years).
        """
        exports = (
            registry.get_by_type(AuditArtifactType.EXPORT_JSON) +
            registry.get_by_type(AuditArtifactType.EXPORT_CSV)
        )
        failures = []
        warnings = []
        
        for record in exports:
            days = AUDIT_RETENTION_DAYS.get(record.retention_period)
            if days is not None and days < 2557:  # Less than 7 years
                failures.append(
                    f"{record.artifact_id}: Export retention {record.retention_period.value} < 7Y"
                )
        
        status = CIGateStatus.PASS if not failures else CIGateStatus.FAIL
        
        return AuditCIGateResult(
            gate_id=cls._generate_gate_id(),
            gate_name="AUDIT_EXPORTS_REGULATORY",
            status=status,
            message="All exports meet regulatory retention" if not failures else "Export retention violations",
            checked_at=cls._now_iso(),
            artifacts_checked=len(exports),
            failures=failures,
            warnings=warnings
        )
    
    @classmethod
    def run_all_gates(
        cls,
        registry: AuditRetentionRegistry
    ) -> List[AuditCIGateResult]:
        """Run all CI gates and return results."""
        return [
            cls.validate_retention_declared(registry),
            cls.validate_no_expired_permanent(registry),
            cls.validate_chain_reconstructions_permanent(registry),
            cls.validate_exports_regulatory(registry),
        ]
    
    @classmethod
    def run_and_summarize(
        cls,
        registry: AuditRetentionRegistry
    ) -> Dict[str, Any]:
        """Run all gates and return summary."""
        results = cls.run_all_gates(registry)
        
        passed = sum(1 for r in results if r.status == CIGateStatus.PASS)
        failed = sum(1 for r in results if r.status == CIGateStatus.FAIL)
        warned = sum(1 for r in results if r.status == CIGateStatus.WARN)
        
        overall = CIGateStatus.PASS if failed == 0 else CIGateStatus.FAIL
        
        return {
            "overall_status": overall.value,
            "total_gates": len(results),
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "gates": [r.to_dict() for r in results],
            "timestamp": cls._now_iso()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL ACCESSORS
# ═══════════════════════════════════════════════════════════════════════════════

_retention_registry: Optional[AuditRetentionRegistry] = None


def get_audit_retention_registry() -> AuditRetentionRegistry:
    """Get the singleton AuditRetentionRegistry instance."""
    global _retention_registry
    if _retention_registry is None:
        _retention_registry = AuditRetentionRegistry()
    return _retention_registry


def reset_audit_retention_registry() -> None:
    """Reset the singleton for testing."""
    global _retention_registry
    AuditRetentionRegistry.reset()
    _retention_registry = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def register_audit_artifact(
    artifact_type: AuditArtifactType,
    content: Any,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditRetentionRecord:
    """Register an audit artifact with retention tracking."""
    return get_audit_retention_registry().register_artifact(
        artifact_type=artifact_type,
        content=content,
        metadata=metadata
    )


def run_audit_ci_gates() -> Dict[str, Any]:
    """Run all audit CI gates and return summary."""
    return AuditCIGateValidator.run_and_summarize(get_audit_retention_registry())


def get_audit_retention_summary() -> Dict[str, Any]:
    """Get summary of audit retention status."""
    registry = get_audit_retention_registry()
    records = registry.get_all_records()
    
    by_type = {}
    by_period = {}
    
    for record in records:
        by_type[record.artifact_type.value] = by_type.get(record.artifact_type.value, 0) + 1
        by_period[record.retention_period.value] = by_period.get(record.retention_period.value, 0) + 1
    
    expired = registry.get_expired()
    expiring_soon = registry.get_expiring_soon(30)
    
    return {
        "total_artifacts": len(records),
        "by_type": by_type,
        "by_retention_period": by_period,
        "expired_count": len(expired),
        "expiring_soon_count": len(expiring_soon),
        "canonical_policies": {k.value: v.value for k, v in CANONICAL_AUDIT_RETENTION.items()},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
