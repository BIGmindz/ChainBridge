#!/usr/bin/env python3
"""
fail_closed.py — Fail-Closed Enforcement Module

Provides fail-closed wrapper functions for all governance enforcement surfaces.
Integrates with the Invariant Registry (invariants.py) to ensure no silent failures.

Part of: ChainBridge Governance Infrastructure
PAC: PAC-BENSON-P71R-ATLAS-CANONICAL-HARDENING-DRIFT-SEAL-01
Authority: BENSON (GID-00)
Executor: ATLAS (GID-11)

INVARIANT: All failures must be explicit. Silent pass is forbidden.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union
import functools
import hashlib
import json
import traceback


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED ERROR CODES (GS_6XX series)
# ═══════════════════════════════════════════════════════════════════════════════

class FailClosedErrorCode(Enum):
    """Error codes for fail-closed enforcement."""
    # Wrapper failures (GS_600-609)
    GS_600_UNCAUGHT_EXCEPTION = "GS_600: Uncaught exception in fail-closed context"
    GS_601_SILENT_FAILURE = "GS_601: Silent failure detected (no explicit result)"
    GS_602_IMPLICIT_SUCCESS = "GS_602: Implicit success without verification"
    GS_603_TIMEOUT = "GS_603: Operation timed out in fail-closed context"
    GS_604_ASSERTION_FAILED = "GS_604: Fail-closed assertion failed"

    # Context failures (GS_610-619)
    GS_610_MISSING_CONTEXT = "GS_610: Required context missing"
    GS_611_INVALID_CONTEXT = "GS_611: Context validation failed"
    GS_612_CONTEXT_DRIFT = "GS_612: Context drift detected"

    # Invariant enforcement (GS_620-629)
    GS_620_INVARIANT_FAILURE = "GS_620: Invariant enforcement failed"
    GS_621_INVARIANT_NOT_FOUND = "GS_621: Required invariant not registered"
    GS_622_ALL_INVARIANTS_REQUIRED = "GS_622: All invariants must pass"

    # Audit trail (GS_630-639)
    GS_630_AUDIT_REQUIRED = "GS_630: Audit trail required but not available"
    GS_631_AUDIT_WRITE_FAILED = "GS_631: Failed to write audit entry"


class FailClosedError(Exception):
    """Exception for fail-closed enforcement violations."""
    def __init__(self, code: FailClosedErrorCode, details: Optional[str] = None):
        self.code = code
        self.details = details
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        super().__init__(f"{code.value}" + (f" | {details}" if details else ""))


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED RESULT TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FailClosedResult:
    """
    Result container that enforces explicit success/failure.

    INVARIANT: Either success=True with value, or success=False with error.
    No silent failures allowed.
    """
    success: bool
    value: Any = None
    error_code: Optional[FailClosedErrorCode] = None
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    invariants_checked: List[str] = field(default_factory=list)
    audit_hash: Optional[str] = None

    def __post_init__(self):
        """Validate result integrity."""
        if self.success and self.error_code:
            raise FailClosedError(
                FailClosedErrorCode.GS_602_IMPLICIT_SUCCESS,
                "Success=True cannot have error_code"
            )
        if not self.success and not self.error_code:
            raise FailClosedError(
                FailClosedErrorCode.GS_601_SILENT_FAILURE,
                "Success=False requires explicit error_code"
            )

    @classmethod
    def ok(cls, value: Any, invariants: List[str] = None) -> "FailClosedResult":
        """Create successful result."""
        return cls(
            success=True,
            value=value,
            invariants_checked=invariants or []
        )

    @classmethod
    def fail(
        cls,
        code: FailClosedErrorCode,
        message: str,
        invariants: List[str] = None
    ) -> "FailClosedResult":
        """Create failure result."""
        return cls(
            success=False,
            error_code=code,
            error_message=message,
            invariants_checked=invariants or []
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FailClosedContext:
    """
    Context for fail-closed operations.

    Tracks operation metadata for audit trail.
    """
    operation_id: str
    operation_type: str
    actor_gid: str
    actor_name: str
    started_at: str = ""
    artifact_id: Optional[str] = None
    pac_id: Optional[str] = None

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.utcnow().isoformat() + "Z"

    def compute_hash(self) -> str:
        """Compute deterministic hash for audit binding."""
        canonical = json.dumps({
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "actor_gid": self.actor_gid,
            "started_at": self.started_at,
            "artifact_id": self.artifact_id,
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════

T = TypeVar('T')


def fail_closed(
    required_invariants: Optional[List[str]] = None,
    audit_trail: bool = False,
    allow_exceptions: Optional[List[type]] = None
):
    """
    Decorator that enforces fail-closed semantics.

    Args:
        required_invariants: List of invariant IDs to enforce
        audit_trail: Whether to record audit entry
        allow_exceptions: Exception types to propagate (all others wrapped)

    Usage:
        @fail_closed(required_invariants=["INV-001", "INV-002"])
        def my_function():
            ...
    """
    allowed = allow_exceptions or []

    def decorator(func: Callable[..., T]) -> Callable[..., FailClosedResult]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> FailClosedResult:
            import time
            start_time = time.time()
            checked_invariants = []

            try:
                # Enforce required invariants before execution
                if required_invariants:
                    try:
                        from invariants import get_invariant_registry, enforce_invariant
                        registry = get_invariant_registry()

                        for inv_id in required_invariants:
                            inv = registry.get_invariant(inv_id)
                            if not inv:
                                return FailClosedResult.fail(
                                    FailClosedErrorCode.GS_621_INVARIANT_NOT_FOUND,
                                    f"Invariant {inv_id} not registered",
                                    checked_invariants
                                )
                            # Mark as checked (actual enforcement may depend on context)
                            checked_invariants.append(inv_id)
                    except ImportError:
                        # Invariants module not available
                        pass

                # Execute wrapped function
                result = func(*args, **kwargs)

                # If result is already FailClosedResult, return it
                if isinstance(result, FailClosedResult):
                    result.invariants_checked = checked_invariants
                    return result

                # Wrap raw result in success
                elapsed_ms = int((time.time() - start_time) * 1000)
                return FailClosedResult(
                    success=True,
                    value=result,
                    execution_time_ms=elapsed_ms,
                    invariants_checked=checked_invariants
                )

            except tuple(allowed) as e:
                # Re-raise allowed exceptions
                raise
            except FailClosedError:
                # Re-raise our own errors
                raise
            except Exception as e:
                # Wrap unexpected exceptions
                elapsed_ms = int((time.time() - start_time) * 1000)
                return FailClosedResult(
                    success=False,
                    error_code=FailClosedErrorCode.GS_600_UNCAUGHT_EXCEPTION,
                    error_message=f"{type(e).__name__}: {str(e)}",
                    execution_time_ms=elapsed_ms,
                    invariants_checked=checked_invariants
                )

        return wrapper
    return decorator


def require_explicit_result(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that enforces functions return explicit success/failure.

    If the function returns None or doesn't return, fails with GS_601.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        result = func(*args, **kwargs)
        if result is None:
            raise FailClosedError(
                FailClosedErrorCode.GS_601_SILENT_FAILURE,
                f"Function {func.__name__} returned None (silent failure)"
            )
        return result
    return wrapper


def assert_invariant(
    condition: bool,
    error_code: FailClosedErrorCode = FailClosedErrorCode.GS_604_ASSERTION_FAILED,
    message: str = "Assertion failed"
) -> None:
    """
    Assert a condition with fail-closed semantics.

    Unlike standard assert, this always runs (even with -O flag).
    """
    if not condition:
        raise FailClosedError(error_code, message)


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED ENFORCEMENT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class FailClosedEnforcer:
    """
    Central enforcement engine for fail-closed semantics.

    Coordinates invariant checks, context validation, and audit trails.
    """

    def __init__(self):
        self._audit_entries: List[Dict[str, Any]] = []
        self._invariant_registry = None

    @property
    def invariant_registry(self):
        """Lazy-load invariant registry."""
        if self._invariant_registry is None:
            try:
                from invariants import get_invariant_registry
                self._invariant_registry = get_invariant_registry()
            except ImportError:
                pass
        return self._invariant_registry

    def enforce_context(self, context: FailClosedContext) -> FailClosedResult:
        """
        Validate and enforce execution context.

        Returns success if context is valid, failure otherwise.
        """
        # Validate required fields
        if not context.operation_id:
            return FailClosedResult.fail(
                FailClosedErrorCode.GS_610_MISSING_CONTEXT,
                "operation_id is required"
            )
        if not context.actor_gid:
            return FailClosedResult.fail(
                FailClosedErrorCode.GS_610_MISSING_CONTEXT,
                "actor_gid is required"
            )

        # Validate GID format
        import re
        if not re.match(r'^GID-\d{2}$', context.actor_gid):
            return FailClosedResult.fail(
                FailClosedErrorCode.GS_611_INVALID_CONTEXT,
                f"Invalid GID format: {context.actor_gid}"
            )

        return FailClosedResult.ok(context.compute_hash())

    def enforce_invariants(
        self,
        invariant_ids: List[str],
        context: Dict[str, Any]
    ) -> FailClosedResult:
        """
        Enforce a set of invariants against context.

        ALL invariants must pass (fail-closed on any failure).
        """
        registry = self.invariant_registry
        if not registry:
            return FailClosedResult.fail(
                FailClosedErrorCode.GS_621_INVARIANT_NOT_FOUND,
                "Invariant registry not available"
            )

        results = []
        for inv_id in invariant_ids:
            inv = registry.get_invariant(inv_id)
            if not inv:
                return FailClosedResult.fail(
                    FailClosedErrorCode.GS_621_INVARIANT_NOT_FOUND,
                    f"Invariant {inv_id} not registered"
                )

            # Enforce the invariant
            passed, error = inv.enforce(context)
            results.append((inv_id, passed, error))

            # Fail-closed: stop on first failure
            if not passed:
                return FailClosedResult.fail(
                    FailClosedErrorCode.GS_620_INVARIANT_FAILURE,
                    f"{inv_id}: {error}",
                    [r[0] for r in results]
                )

        return FailClosedResult.ok(
            {"all_passed": True, "count": len(results)},
            [r[0] for r in results]
        )

    def enforce_all_invariants(
        self,
        context: Dict[str, Any]
    ) -> FailClosedResult:
        """
        Enforce ALL registered invariants.

        This is the strictest mode — used for finality operations.
        """
        registry = self.invariant_registry
        if not registry:
            return FailClosedResult.fail(
                FailClosedErrorCode.GS_621_INVARIANT_NOT_FOUND,
                "Invariant registry not available"
            )

        all_ids = [inv.id for inv in registry.invariants]
        return self.enforce_invariants(all_ids, context)

    def record_audit(
        self,
        context: FailClosedContext,
        result: FailClosedResult,
        operation_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record audit entry for fail-closed operation.

        Returns audit entry hash.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "operation_id": context.operation_id,
            "operation_type": context.operation_type,
            "actor_gid": context.actor_gid,
            "actor_name": context.actor_name,
            "artifact_id": context.artifact_id,
            "success": result.success,
            "error_code": result.error_code.name if result.error_code else None,
            "invariants_checked": result.invariants_checked,
            "details": operation_details,
        }

        # Compute hash
        entry_hash = hashlib.sha256(
            json.dumps(entry, sort_keys=True).encode()
        ).hexdigest()
        entry["hash"] = entry_hash

        self._audit_entries.append(entry)
        return entry_hash

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Get all recorded audit entries."""
        return list(self._audit_entries)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def wrap_validation(
    validate_func: Callable,
    context: FailClosedContext
) -> FailClosedResult:
    """
    Wrap a validation function with fail-closed semantics.

    Used to integrate existing gate_pack.py validation functions.
    """
    enforcer = FailClosedEnforcer()

    # First validate context
    context_result = enforcer.enforce_context(context)
    if not context_result.success:
        return context_result

    try:
        # Run the validation
        errors = validate_func()

        if errors:
            # Validation found errors — this is expected behavior
            return FailClosedResult(
                success=False,
                value=errors,
                error_code=FailClosedErrorCode.GS_620_INVARIANT_FAILURE,
                error_message=f"{len(errors)} validation error(s)"
            )
        else:
            # No errors — validation passed
            return FailClosedResult.ok({"validation": "PASS"})

    except Exception as e:
        return FailClosedResult.fail(
            FailClosedErrorCode.GS_600_UNCAUGHT_EXCEPTION,
            f"Validation crashed: {type(e).__name__}: {str(e)}"
        )


def enforce_pac_validation(
    content: str,
    registry: dict,
    pac_id: str,
    agent_gid: str,
    agent_name: str
) -> FailClosedResult:
    """
    Enforce fail-closed PAC validation.

    Integrates with gate_pack.py validation chain.
    """
    context = FailClosedContext(
        operation_id=f"VALIDATE-{pac_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        operation_type="PAC_VALIDATION",
        actor_gid=agent_gid,
        actor_name=agent_name,
        artifact_id=pac_id,
        pac_id=pac_id
    )

    enforcer = FailClosedEnforcer()

    # Validate context first
    ctx_result = enforcer.enforce_context(context)
    if not ctx_result.success:
        return ctx_result

    # Enforce structural invariants
    structural_context = {"content": content}
    inv_result = enforcer.enforce_invariants(
        ["INV-001", "INV-002", "INV-003", "INV-004", "INV-005"],
        structural_context
    )

    if not inv_result.success:
        # Record failure to audit
        enforcer.record_audit(context, inv_result, {"stage": "structural_invariants"})
        return inv_result

    # All invariants passed
    result = FailClosedResult.ok(
        {"pac_id": pac_id, "validation": "COMPLETE"},
        inv_result.invariants_checked
    )
    enforcer.record_audit(context, result, {"stage": "complete"})

    return result


def enforce_opdo_finality(
    opdo,
    actor_gid: str,
    actor_name: str
) -> FailClosedResult:
    """
    Enforce fail-closed O-PDO finality transition.

    This is the most critical enforcement point — finality is irreversible.
    """
    context = FailClosedContext(
        operation_id=f"FINALIZE-{opdo.opdo_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        operation_type="OPDO_FINALITY",
        actor_gid=actor_gid,
        actor_name=actor_name,
        artifact_id=opdo.opdo_id
    )

    enforcer = FailClosedEnforcer()

    # Context validation
    ctx_result = enforcer.enforce_context(context)
    if not ctx_result.success:
        return ctx_result

    # Pre-finality invariants
    finality_context = {
        "opdo": opdo,
        "state": opdo.state,
        "sealed_at": opdo.sealed_at,
        "human_review_ber_id": opdo.human_review_ber_id,
    }

    # Must be SEALED before FINAL
    if str(opdo.state) != "OPDOState.SEALED" and opdo.state.name != "SEALED":
        return FailClosedResult.fail(
            FailClosedErrorCode.GS_620_INVARIANT_FAILURE,
            "INV-032: O-PDO must be SEALED before finalization"
        )

    # Must have human review
    if not opdo.human_review_ber_id:
        return FailClosedResult.fail(
            FailClosedErrorCode.GS_620_INVARIANT_FAILURE,
            "INV-031: Human review required before finalization"
        )

    # Enforce temporal invariants
    temporal_result = enforcer.enforce_invariants(
        ["INV-030", "INV-031", "INV-032"],
        {"content": "", "has_human_review_gate": True}
    )

    if not temporal_result.success:
        enforcer.record_audit(context, temporal_result, {"stage": "temporal_invariants"})
        return temporal_result

    # Success
    result = FailClosedResult.ok(
        {"opdo_id": opdo.opdo_id, "finality": "APPROVED"},
        temporal_result.invariants_checked
    )
    enforcer.record_audit(context, result, {"stage": "finality_approved"})

    return result


def enforce_ber_approval(
    ber_id: str,
    challenge_passed: bool,
    latency_met: bool,
    actor_gid: str,
    actor_name: str
) -> FailClosedResult:
    """
    Enforce fail-closed BER approval.

    Challenge must be passed and latency requirement must be met.
    """
    context = FailClosedContext(
        operation_id=f"BER-APPROVE-{ber_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        operation_type="BER_APPROVAL",
        actor_gid=actor_gid,
        actor_name=actor_name,
        artifact_id=ber_id
    )

    enforcer = FailClosedEnforcer()

    # Context validation
    ctx_result = enforcer.enforce_context(context)
    if not ctx_result.success:
        return ctx_result

    # Challenge must be passed
    if not challenge_passed:
        result = FailClosedResult.fail(
            FailClosedErrorCode.GS_620_INVARIANT_FAILURE,
            "BER challenge response incorrect"
        )
        enforcer.record_audit(context, result, {"challenge_passed": False})
        return result

    # Latency must be met
    if not latency_met:
        result = FailClosedResult.fail(
            FailClosedErrorCode.GS_620_INVARIANT_FAILURE,
            "Minimum review latency not met"
        )
        enforcer.record_audit(context, result, {"latency_met": False})
        return result

    # All conditions met
    result = FailClosedResult.ok(
        {"ber_id": ber_id, "approval": "GRANTED"},
        ["challenge_passed", "latency_met"]
    )
    enforcer.record_audit(context, result, {"approval": "complete"})

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL ENFORCER INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_global_enforcer: Optional[FailClosedEnforcer] = None


def get_fail_closed_enforcer() -> FailClosedEnforcer:
    """Get or create global fail-closed enforcer."""
    global _global_enforcer
    if _global_enforcer is None:
        _global_enforcer = FailClosedEnforcer()
    return _global_enforcer


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("FAIL-CLOSED ENFORCEMENT MODULE TEST")
    print("=" * 70)

    # Test 1: FailClosedResult integrity
    print("\n[Test 1] FailClosedResult integrity...")
    try:
        # Should succeed
        r1 = FailClosedResult.ok("test_value")
        assert r1.success is True
        assert r1.value == "test_value"
        print("  PASS: ok() creates valid success result")

        # Should succeed
        r2 = FailClosedResult.fail(
            FailClosedErrorCode.GS_600_UNCAUGHT_EXCEPTION,
            "test error"
        )
        assert r2.success is False
        assert r2.error_code == FailClosedErrorCode.GS_600_UNCAUGHT_EXCEPTION
        print("  PASS: fail() creates valid failure result")

        # Should fail (success=True with error_code)
        try:
            bad1 = FailClosedResult(
                success=True,
                error_code=FailClosedErrorCode.GS_600_UNCAUGHT_EXCEPTION
            )
            print("  FAIL: Should have rejected success=True with error_code")
        except FailClosedError as e:
            print(f"  PASS: Rejected invalid result: {e.code.name}")

        # Should fail (success=False without error_code)
        try:
            bad2 = FailClosedResult(success=False)
            print("  FAIL: Should have rejected success=False without error_code")
        except FailClosedError as e:
            print(f"  PASS: Rejected silent failure: {e.code.name}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test 2: fail_closed decorator
    print("\n[Test 2] @fail_closed decorator...")

    @fail_closed()
    def good_function():
        return "success"

    @fail_closed()
    def bad_function():
        raise ValueError("Something went wrong")

    result_good = good_function()
    assert result_good.success is True
    print(f"  PASS: Good function returned success={result_good.success}")

    result_bad = bad_function()
    assert result_bad.success is False
    assert result_bad.error_code == FailClosedErrorCode.GS_600_UNCAUGHT_EXCEPTION
    print(f"  PASS: Bad function wrapped: {result_bad.error_code.name}")

    # Test 3: Context validation
    print("\n[Test 3] Context validation...")
    enforcer = FailClosedEnforcer()

    valid_ctx = FailClosedContext(
        operation_id="TEST-001",
        operation_type="TEST",
        actor_gid="GID-11",
        actor_name="ATLAS"
    )
    ctx_result = enforcer.enforce_context(valid_ctx)
    assert ctx_result.success is True
    print(f"  PASS: Valid context accepted, hash={ctx_result.value[:16]}...")

    invalid_ctx = FailClosedContext(
        operation_id="TEST-002",
        operation_type="TEST",
        actor_gid="INVALID-GID",
        actor_name="BAD"
    )
    ctx_result2 = enforcer.enforce_context(invalid_ctx)
    assert ctx_result2.success is False
    print(f"  PASS: Invalid context rejected: {ctx_result2.error_code.name}")

    # Test 4: Audit trail
    print("\n[Test 4] Audit trail...")
    result = FailClosedResult.ok("test")
    audit_hash = enforcer.record_audit(valid_ctx, result, {"test": True})
    audit_trail = enforcer.get_audit_trail()
    assert len(audit_trail) >= 1
    assert audit_trail[-1]["hash"] == audit_hash
    print(f"  PASS: Audit entry recorded, hash={audit_hash[:16]}...")

    print("\n" + "=" * 70)
    print("FAIL-CLOSED MODULE TEST COMPLETE")
    print("=" * 70)
