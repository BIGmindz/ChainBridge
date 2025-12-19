"""
ChainBridge Constitution Engine
═══════════════════════════════════════════════════════════════════════════════

Machine enforcement layer for constitutional locks.

This module is the runtime enforcement component of the Constitution system:
- Loads lock registry
- Validates enforcement coverage
- Exposes assert_lock() for runtime checks
- Validates PAC admission

PAC Reference: PAC-BENSON-CONSTITUTION-ENGINE-01
Effective Date: 2025-12-18

INVARIANTS:
- Every lock must have enforcement
- Enforcement must be mechanically verifiable
- Locks cannot be bypassed at runtime
- PACs must acknowledge affected locks

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

LOCK_REGISTRY_PATH = Path("docs/constitution/LOCK_REGISTRY.yaml")


class LockSeverity(Enum):
    """Lock severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class LockType(Enum):
    """Lock type classification."""

    INVARIANT = "invariant"
    CONSTRAINT = "constraint"
    BOUNDARY = "boundary"
    GATE = "gate"


class ViolationAction(Enum):
    """Action to take on lock violation."""

    HARD_FAIL = "HARD_FAIL"
    SOFT_FAIL = "SOFT_FAIL"


class EnforcementType(Enum):
    """Types of enforcement mechanisms."""

    TEST_REQUIRED = "test_required"
    RUNTIME_ASSERT = "runtime_assert"
    CI_WORKFLOW = "ci_workflow"
    LINT_RULE = "lint_rule"
    PAC_GATE = "pac_gate"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class ConstitutionError(Exception):
    """Base exception for Constitution Engine errors."""

    pass


class LockRegistryError(ConstitutionError):
    """Error loading or parsing lock registry."""

    pass


class LockViolationError(ConstitutionError):
    """A lock invariant was violated."""

    def __init__(
        self,
        lock_id: str,
        message: str,
        severity: LockSeverity = LockSeverity.CRITICAL,
        context: dict[str, Any] | None = None,
    ):
        self.lock_id = lock_id
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(f"[{lock_id}] {message}")


class LockEnforcementMissingError(ConstitutionError):
    """A lock has no enforcement mechanism."""

    def __init__(self, lock_id: str):
        self.lock_id = lock_id
        super().__init__(f"Lock {lock_id} has no enforcement mechanism")


class PACAdmissionError(ConstitutionError):
    """PAC failed admission gate."""

    def __init__(self, reason: str, missing_locks: list[str] | None = None):
        self.reason = reason
        self.missing_locks = missing_locks or []
        super().__init__(f"PAC admission failed: {reason}")


class ForbiddenZoneError(ConstitutionError):
    """Attempt to modify a forbidden zone."""

    def __init__(self, lock_id: str, zone: str):
        self.lock_id = lock_id
        self.zone = zone
        super().__init__(f"Forbidden zone violation: {zone} (protected by {lock_id})")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ViolationPolicy:
    """Policy for handling lock violations."""

    action: ViolationAction
    telemetry: str  # "REQUIRED" or "OPTIONAL"


@dataclass(frozen=True)
class Lock:
    """Immutable representation of a constitutional lock."""

    lock_id: str
    description: str
    scope: tuple[str, ...]
    lock_type: LockType
    enforcement: tuple[dict[str, Any], ...]
    severity: LockSeverity
    violation_policy: ViolationPolicy
    source_invariants: tuple[str, ...] = field(default_factory=tuple)
    forbidden_zones: tuple[str, ...] = field(default_factory=tuple)
    status: str = "ACTIVE"
    superseded_by: str | None = None

    def has_enforcement(self) -> bool:
        """Check if lock has at least one enforcement mechanism."""
        return len(self.enforcement) > 0

    def requires_test(self) -> bool:
        """Check if lock requires a test file."""
        return any(EnforcementType.TEST_REQUIRED.value in e for e in self.enforcement)

    def requires_ci_workflow(self) -> bool:
        """Check if lock requires a CI workflow."""
        return any(EnforcementType.CI_WORKFLOW.value in e for e in self.enforcement)

    def get_test_paths(self) -> list[str]:
        """Get all required test paths for this lock."""
        paths = []
        for e in self.enforcement:
            if EnforcementType.TEST_REQUIRED.value in e:
                paths.append(e[EnforcementType.TEST_REQUIRED.value])
        return paths

    def get_ci_workflows(self) -> list[str]:
        """Get all required CI workflows for this lock."""
        workflows = []
        for e in self.enforcement:
            if EnforcementType.CI_WORKFLOW.value in e:
                workflows.append(e[EnforcementType.CI_WORKFLOW.value])
        return workflows


@dataclass
class LockViolationEvent:
    """Telemetry event for lock violation."""

    lock_id: str
    severity: LockSeverity
    enforcement_type: str
    context: dict[str, Any]
    action_taken: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for telemetry emission."""
        return {
            "event": "LOCK_VIOLATION",
            "lock_id": self.lock_id,
            "severity": self.severity.value,
            "enforcement_type": self.enforcement_type,
            "context": self.context,
            "action_taken": self.action_taken,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTITUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class ConstitutionEngine:
    """
    Machine enforcement layer for constitutional locks.

    Responsibilities:
    - Load lock registry from YAML
    - Validate enforcement coverage
    - Expose assert_lock() for runtime checks
    - Validate PAC admission
    """

    def __init__(self, registry_path: Path | None = None):
        """Initialize Constitution Engine."""
        self._registry_path = registry_path or LOCK_REGISTRY_PATH
        self._locks: dict[str, Lock] = {}
        self._loaded = False
        self._registry_hash: str | None = None

    def load_registry(self) -> None:
        """Load lock registry from YAML file."""
        if not self._registry_path.exists():
            raise LockRegistryError(f"Lock registry not found: {self._registry_path}")

        try:
            with open(self._registry_path) as f:
                content = f.read()
                self._registry_hash = hashlib.sha256(content.encode()).hexdigest()
                data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise LockRegistryError(f"Invalid YAML in lock registry: {e}") from e

        if "locks" not in data:
            raise LockRegistryError("Lock registry missing 'locks' section")

        self._locks = {}
        for lock_data in data["locks"]:
            lock = self._parse_lock(lock_data)
            self._locks[lock.lock_id] = lock

        self._loaded = True

    def _parse_lock(self, data: dict[str, Any]) -> Lock:
        """Parse a lock from YAML data."""
        try:
            violation_policy_data = data.get("violation_policy", {})
            violation_policy = ViolationPolicy(
                action=ViolationAction(
                    violation_policy_data.get("action", "HARD_FAIL")
                ),
                telemetry=violation_policy_data.get("telemetry", "REQUIRED"),
            )

            return Lock(
                lock_id=data["lock_id"],
                description=data["description"],
                scope=tuple(data.get("scope", [])),
                lock_type=LockType(data.get("type", "invariant")),
                enforcement=tuple(data.get("enforcement", [])),
                severity=LockSeverity(data.get("severity", "CRITICAL")),
                violation_policy=violation_policy,
                source_invariants=tuple(data.get("source_invariants", [])),
                forbidden_zones=tuple(data.get("forbidden_zones", [])),
                status=data.get("status", "ACTIVE"),
                superseded_by=data.get("superseded_by"),
            )
        except (KeyError, ValueError) as e:
            raise LockRegistryError(
                f"Invalid lock definition: {data.get('lock_id', 'unknown')}: {e}"
            ) from e

    def ensure_loaded(self) -> None:
        """Ensure registry is loaded."""
        if not self._loaded:
            self.load_registry()

    def get_lock(self, lock_id: str) -> Lock | None:
        """Get a lock by ID."""
        self.ensure_loaded()
        return self._locks.get(lock_id)

    def get_all_locks(self) -> list[Lock]:
        """Get all locks."""
        self.ensure_loaded()
        return list(self._locks.values())

    def get_active_locks(self) -> list[Lock]:
        """Get all active (non-superseded) locks."""
        self.ensure_loaded()
        return [lock for lock in self._locks.values() if lock.status == "ACTIVE"]

    def get_locks_by_scope(self, scope: str) -> list[Lock]:
        """Get all locks that affect a given scope."""
        self.ensure_loaded()
        return [lock for lock in self._locks.values() if scope in lock.scope]

    def get_locks_by_severity(self, severity: LockSeverity) -> list[Lock]:
        """Get all locks of a given severity."""
        self.ensure_loaded()
        return [lock for lock in self._locks.values() if lock.severity == severity]

    def validate_enforcement_coverage(self) -> list[str]:
        """
        Validate that all locks have enforcement.

        Returns list of lock IDs without enforcement.
        """
        self.ensure_loaded()
        missing = []
        for lock in self._locks.values():
            if not lock.has_enforcement():
                missing.append(lock.lock_id)
        return missing

    def assert_lock(
        self,
        lock_id: str,
        context: dict[str, Any] | None = None,
        condition: bool = True,
    ) -> None:
        """
        Assert a lock condition at runtime.

        Args:
            lock_id: The lock to assert
            context: Optional context for violation event
            condition: The condition that must be True

        Raises:
            LockViolationError if condition is False
        """
        self.ensure_loaded()

        lock = self._locks.get(lock_id)
        if lock is None:
            raise LockRegistryError(f"Unknown lock: {lock_id}")

        if not condition:
            # Emit telemetry
            event = LockViolationEvent(
                lock_id=lock_id,
                severity=lock.severity,
                enforcement_type="runtime_assert",
                context=context or {},
                action_taken="BLOCKED",
            )
            self._emit_violation_telemetry(event)

            # Raise violation error
            raise LockViolationError(
                lock_id=lock_id,
                message=f"Lock assertion failed: {lock.description}",
                severity=lock.severity,
                context=context,
            )

    def _emit_violation_telemetry(self, event: LockViolationEvent) -> None:
        """Emit telemetry for lock violation."""
        # In production, this would emit to telemetry service
        # For now, we log to governance audit
        lock = self._locks.get(event.lock_id)
        if lock and lock.violation_policy.telemetry == "REQUIRED":
            # TODO: Integrate with GovernanceAuditLogger
            pass

    def validate_pac_admission(
        self,
        acknowledged_locks: list[str],
        affected_scopes: list[str],
        touched_files: list[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate PAC admission against lock acknowledgment.

        Args:
            acknowledged_locks: Locks acknowledged in PAC
            affected_scopes: Scopes affected by PAC
            touched_files: Files modified by PAC (for forbidden zone check)

        Returns:
            Tuple of (admitted: bool, missing_locks: list[str])
        """
        self.ensure_loaded()

        # Get all locks for affected scopes
        required_locks = set()
        for scope in affected_scopes:
            for lock in self.get_locks_by_scope(scope):
                if lock.status == "ACTIVE":
                    # Only require pac_gate locks
                    if any("pac_gate" in e for e in lock.enforcement):
                        required_locks.add(lock.lock_id)

        # Check acknowledgment
        acknowledged_set = set(acknowledged_locks)
        missing = list(required_locks - acknowledged_set)

        # Check forbidden zones
        if touched_files:
            for lock in self.get_active_locks():
                if lock.forbidden_zones:
                    for zone in lock.forbidden_zones:
                        # Simple substring match for now
                        zone_path = zone.split(" ")[0]  # Extract path from "path (note)"
                        for touched in touched_files:
                            if zone_path in touched:
                                # Forbidden zone touched without supersession
                                missing.append(f"FORBIDDEN_ZONE:{lock.lock_id}:{zone}")

        return len(missing) == 0, missing

    def check_forbidden_zone(self, file_path: str) -> Lock | None:
        """
        Check if a file path is in a forbidden zone.

        Returns the protecting lock if path is forbidden, None otherwise.
        """
        self.ensure_loaded()

        for lock in self.get_active_locks():
            if lock.forbidden_zones:
                for zone in lock.forbidden_zones:
                    zone_path = zone.split(" ")[0]
                    if zone_path in file_path:
                        return lock
        return None

    def get_registry_hash(self) -> str | None:
        """Get SHA-256 hash of loaded registry."""
        return self._registry_hash

    def get_statistics(self) -> dict[str, Any]:
        """Get registry statistics."""
        self.ensure_loaded()

        locks = self.get_all_locks()
        active = [lk for lk in locks if lk.status == "ACTIVE"]

        by_severity = {}
        for sev in LockSeverity:
            by_severity[sev.value] = len(
                [lk for lk in active if lk.severity == sev]
            )

        by_type = {}
        for lt in LockType:
            by_type[lt.value] = len([lk for lk in active if lk.lock_type == lt])

        scopes: dict[str, int] = {}
        for lock in active:
            for scope in lock.scope:
                scopes[scope] = scopes.get(scope, 0) + 1

        return {
            "total_locks": len(active),
            "superseded_locks": len(locks) - len(active),
            "by_severity": by_severity,
            "by_type": by_type,
            "by_scope": scopes,
            "registry_hash": self._registry_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

# Global singleton for runtime use
_engine: ConstitutionEngine | None = None


def get_constitution_engine() -> ConstitutionEngine:
    """Get or create the singleton Constitution Engine."""
    global _engine
    if _engine is None:
        _engine = ConstitutionEngine()
    return _engine


def assert_lock(
    lock_id: str,
    context: dict[str, Any] | None = None,
    condition: bool = True,
) -> None:
    """
    Convenience function to assert a lock condition.

    Usage:
        from core.governance.constitution_engine import assert_lock

        assert_lock("LOCK-GW-IMMUTABILITY-001", {"envelope_id": "..."}, envelope.frozen)
    """
    engine = get_constitution_engine()
    engine.assert_lock(lock_id, context, condition)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI FOR CI INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    """CLI entry point for CI integration."""
    import sys

    engine = ConstitutionEngine()

    try:
        engine.load_registry()
    except LockRegistryError as e:
        print(f"❌ Failed to load lock registry: {e}", file=sys.stderr)
        return 1

    # Validate enforcement coverage
    missing = engine.validate_enforcement_coverage()
    if missing:
        print("❌ Locks without enforcement:", file=sys.stderr)
        for lock_id in missing:
            print(f"   - {lock_id}", file=sys.stderr)
        return 1

    # Get and print statistics
    stats = engine.get_statistics()
    print("✅ Constitution Engine validation passed")
    print(f"   Total active locks: {stats['total_locks']}")
    print(f"   By severity: {stats['by_severity']}")
    print(f"   Registry hash: {stats['registry_hash'][:16]}...")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
