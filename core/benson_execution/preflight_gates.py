# ═══════════════════════════════════════════════════════════════════════════════
# BensonExecution — Preflight Enforcement Gates
# PAC-BENSON-EXEC-C01: BENSON EXECUTION GENESIS & IDENTITY INSTANTIATION
# Agent: Benson Execution (GID-00-EXEC) — Deterministic Execution Engine
# ═══════════════════════════════════════════════════════════════════════════════

"""
Preflight Enforcement Gates — Canonical Preflight Invariant Enforcement

PURPOSE:
    Enforce CB-INV-PREFLIGHT-LAW-001:
        - Preflight gates MUST execute for every PAC
        - Gates execute in FIXED order
        - Any failure HALTS execution
        - No bypass or self-attestation allowed

GATE EXECUTION ORDER (IMMUTABLE):
    1. SCHEMA_VALIDATION_GATE   - Schema must be valid
    2. LINT_ENFORCEMENT_GATE    - Lint rules must pass
    3. ADMISSION_GATE           - PAC must be admissible
    4. GOVERNANCE_GATE          - Governance mode must be valid
    5. IDENTITY_GATE            - Agent identity must be locked
    6. INVARIANT_GATE           - All invariants must be satisfied

ENFORCEMENT:
    - Gate failure → HARD STOP
    - No partial execution
    - No gate bypass
    - No self-attestation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# GATE IDENTIFIERS
# ═══════════════════════════════════════════════════════════════════════════════

class PreflightGateID(Enum):
    """Canonical preflight gate identifiers (execution order)."""
    
    SCHEMA_VALIDATION_GATE = "GATE-001"
    LINT_ENFORCEMENT_GATE = "GATE-002"
    ADMISSION_GATE = "GATE-003"
    GOVERNANCE_GATE = "GATE-004"
    IDENTITY_GATE = "GATE-005"
    INVARIANT_GATE = "GATE-006"
    BER_REQUIREMENT_GATE = "GATE-BER-REQUIRED"  # PAC-JEFFREY-C07


# Fixed execution order
GATE_EXECUTION_ORDER: Tuple[PreflightGateID, ...] = (
    PreflightGateID.SCHEMA_VALIDATION_GATE,
    PreflightGateID.LINT_ENFORCEMENT_GATE,
    PreflightGateID.ADMISSION_GATE,
    PreflightGateID.GOVERNANCE_GATE,
    PreflightGateID.IDENTITY_GATE,
    PreflightGateID.INVARIANT_GATE,
)

# Loop closure gates (post-execution)
LOOP_CLOSURE_GATES: Tuple[PreflightGateID, ...] = (
    PreflightGateID.BER_REQUIREMENT_GATE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GATE STATUS
# ═══════════════════════════════════════════════════════════════════════════════

class GateStatus(Enum):
    """Gate execution status."""
    
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"  # Only if previous gate failed
    NOT_EXECUTED = "NOT_EXECUTED"


# ═══════════════════════════════════════════════════════════════════════════════
# PREFLIGHT FAILURE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PreflightFailure:
    """
    Immutable record of a preflight gate failure.
    
    Attributes:
        gate_id: Which gate failed
        message: Human-readable failure message
        details: Additional failure details
        halts_execution: Whether this failure halts all execution (always True)
    """
    
    gate_id: PreflightGateID
    message: str
    details: Optional[str] = None
    halts_execution: bool = True  # Always true — no soft failures
    
    def __str__(self) -> str:
        parts = [f"[{self.gate_id.value}] {self.message}"]
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# GATE RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PreflightGateResult:
    """
    Immutable result of a single preflight gate execution.
    
    Attributes:
        gate_id: The gate that was executed
        status: Pass/fail/skipped status
        failure: Failure details if failed
        execution_time_ms: How long the gate took to execute
        gate_timestamp: When the gate was executed
    """
    
    gate_id: PreflightGateID
    status: GateStatus
    failure: Optional[PreflightFailure] = None
    execution_time_ms: float = 0.0
    gate_timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    
    @property
    def passed(self) -> bool:
        return self.status == GateStatus.PASSED
    
    @property
    def failed(self) -> bool:
        return self.status == GateStatus.FAILED


# ═══════════════════════════════════════════════════════════════════════════════
# PREFLIGHT RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PreflightResult:
    """
    Immutable result of complete preflight enforcement.
    
    Attributes:
        passed: True if ALL gates passed
        pac_id: The PAC that was checked
        gate_results: Results for each gate in execution order
        halted_at: Which gate caused halt (if any)
        total_execution_time_ms: Total preflight time
        preflight_timestamp: When preflight completed
    """
    
    passed: bool
    pac_id: str
    gate_results: Tuple[PreflightGateResult, ...] = field(default_factory=tuple)
    halted_at: Optional[PreflightGateID] = None
    total_execution_time_ms: float = 0.0
    preflight_timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    
    @property
    def gates_executed(self) -> int:
        return sum(1 for r in self.gate_results if r.status != GateStatus.SKIPPED)
    
    @property
    def gates_passed(self) -> int:
        return sum(1 for r in self.gate_results if r.passed)
    
    @property
    def first_failure(self) -> Optional[PreflightFailure]:
        for result in self.gate_results:
            if result.failure:
                return result.failure
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PREFLIGHT GATE (ABSTRACT)
# ═══════════════════════════════════════════════════════════════════════════════

class PreflightGate:
    """
    Abstract base for preflight gates.
    
    Each gate is a deterministic check with no interpretation.
    """
    
    gate_id: PreflightGateID
    
    def execute(self, pac: Dict[str, Any]) -> PreflightGateResult:
        """Execute the gate check. Must be implemented by subclass."""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════════════
# CONCRETE GATES
# ═══════════════════════════════════════════════════════════════════════════════

class SchemaValidationGate(PreflightGate):
    """GATE-001: Schema validation gate."""
    
    gate_id = PreflightGateID.SCHEMA_VALIDATION_GATE
    
    def __init__(self) -> None:
        from core.benson_execution.schema_registry import get_benson_schema_registry
        self._registry = get_benson_schema_registry()
    
    def execute(self, pac: Dict[str, Any]) -> PreflightGateResult:
        import time
        start = time.perf_counter()
        
        result = self._registry.validate(pac)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        if result.is_valid:
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.PASSED,
                execution_time_ms=elapsed_ms,
            )
        else:
            error_summary = "; ".join(str(e) for e in result.errors[:3])
            if len(result.errors) > 3:
                error_summary += f" (+{len(result.errors) - 3} more)"
            
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAILED,
                failure=PreflightFailure(
                    gate_id=self.gate_id,
                    message="Schema validation failed",
                    details=error_summary,
                ),
                execution_time_ms=elapsed_ms,
            )


class LintEnforcementGate(PreflightGate):
    """GATE-002: Lint enforcement gate."""
    
    gate_id = PreflightGateID.LINT_ENFORCEMENT_GATE
    
    def __init__(self) -> None:
        from core.benson_execution.pac_lint_law import get_pac_lint_law
        self._lint_law = get_pac_lint_law()
    
    def execute(self, pac: Dict[str, Any]) -> PreflightGateResult:
        import time
        start = time.perf_counter()
        
        result = self._lint_law.enforce(pac)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        if result.passed:
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.PASSED,
                execution_time_ms=elapsed_ms,
            )
        else:
            error_summary = "; ".join(str(v) for v in result.violations[:3])
            if len(result.violations) > 3:
                error_summary += f" (+{len(result.violations) - 3} more)"
            
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAILED,
                failure=PreflightFailure(
                    gate_id=self.gate_id,
                    message="Lint enforcement failed",
                    details=error_summary,
                ),
                execution_time_ms=elapsed_ms,
            )


class AdmissionGate(PreflightGate):
    """GATE-003: PAC admission gate."""
    
    gate_id = PreflightGateID.ADMISSION_GATE
    
    def execute(self, pac: Dict[str, Any]) -> PreflightGateResult:
        import time
        start = time.perf_counter()
        
        # Check PAC_ADMISSION_CHECK block
        blocks = pac.get("blocks", {})
        admission = blocks.get("1") or blocks.get(1)
        
        if admission is None:
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAILED,
                failure=PreflightFailure(
                    gate_id=self.gate_id,
                    message="PAC_ADMISSION_CHECK block missing",
                ),
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
        
        # Check admission decision
        if isinstance(admission, dict):
            decision = admission.get("admission_decision", "").upper()
            if decision == "REJECTED":
                return PreflightGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAILED,
                    failure=PreflightFailure(
                        gate_id=self.gate_id,
                        message="PAC admission was rejected",
                        details=admission.get("rejection_reason", "No reason provided"),
                    ),
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                )
        
        return PreflightGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASSED,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )


class GovernanceGate(PreflightGate):
    """GATE-004: Governance mode gate."""
    
    gate_id = PreflightGateID.GOVERNANCE_GATE
    
    VALID_GOVERNANCE_MODES = frozenset(["LAW", "POLICY", "GUIDELINE"])
    
    def execute(self, pac: Dict[str, Any]) -> PreflightGateResult:
        import time
        start = time.perf_counter()
        
        # Check GOVERNANCE_MODE_DECLARATION block
        blocks = pac.get("blocks", {})
        governance = blocks.get("3") or blocks.get(3)
        
        if governance is None:
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAILED,
                failure=PreflightFailure(
                    gate_id=self.gate_id,
                    message="GOVERNANCE_MODE_DECLARATION block missing",
                ),
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
        
        # Check governance mode
        if isinstance(governance, dict):
            mode = governance.get("governance_mode", "").upper()
            if mode and mode not in self.VALID_GOVERNANCE_MODES:
                return PreflightGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAILED,
                    failure=PreflightFailure(
                        gate_id=self.gate_id,
                        message=f"Invalid governance mode: {mode}",
                        details=f"Valid modes: {self.VALID_GOVERNANCE_MODES}",
                    ),
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                )
            
            # Check downgrade_allowed for LAW tier
            if mode == "LAW":
                downgrade = governance.get("downgrade_allowed")
                if downgrade is True:
                    return PreflightGateResult(
                        gate_id=self.gate_id,
                        status=GateStatus.FAILED,
                        failure=PreflightFailure(
                            gate_id=self.gate_id,
                            message="LAW tier cannot allow downgrade",
                        ),
                        execution_time_ms=(time.perf_counter() - start) * 1000,
                    )
        
        return PreflightGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASSED,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )


class IdentityGate(PreflightGate):
    """GATE-005: Agent identity gate."""
    
    gate_id = PreflightGateID.IDENTITY_GATE
    
    def execute(self, pac: Dict[str, Any]) -> PreflightGateResult:
        import time
        start = time.perf_counter()
        
        # Check AGENT_ACTIVATION_ACK block
        blocks = pac.get("blocks", {})
        identity = blocks.get("4") or blocks.get(4)
        
        if identity is None:
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAILED,
                failure=PreflightFailure(
                    gate_id=self.gate_id,
                    message="AGENT_ACTIVATION_ACK block missing",
                ),
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
        
        # Check agent acknowledgement
        if isinstance(identity, dict):
            ack = identity.get("acknowledgement", {})
            if isinstance(ack, dict):
                agent_ack = ack.get("agent_ack", "").upper()
                if agent_ack not in ("EXPLICIT", "IMPLICIT"):
                    return PreflightGateResult(
                        gate_id=self.gate_id,
                        status=GateStatus.FAILED,
                        failure=PreflightFailure(
                            gate_id=self.gate_id,
                            message="Agent acknowledgement not valid",
                            details=f"Got: {agent_ack}, expected: EXPLICIT or IMPLICIT",
                        ),
                        execution_time_ms=(time.perf_counter() - start) * 1000,
                    )
        
        return PreflightGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASSED,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )


class InvariantGate(PreflightGate):
    """GATE-006: Invariant enforcement gate."""
    
    gate_id = PreflightGateID.INVARIANT_GATE
    
    def execute(self, pac: Dict[str, Any]) -> PreflightGateResult:
        import time
        start = time.perf_counter()
        
        # Check INVARIANTS_ENFORCED block
        blocks = pac.get("blocks", {})
        invariants = blocks.get("9") or blocks.get(9)
        
        if invariants is None:
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAILED,
                failure=PreflightFailure(
                    gate_id=self.gate_id,
                    message="INVARIANTS_ENFORCED block missing",
                ),
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
        
        # For LAW tier, check that invariant_registry is LOCKED
        metadata = pac.get("metadata", {})
        tier = metadata.get("governance_tier", "").upper()
        
        if tier == "LAW" and isinstance(invariants, dict):
            registry_status = str(invariants.get("invariant_registry", "")).upper()
            if registry_status != "LOCKED":
                return PreflightGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAILED,
                    failure=PreflightFailure(
                        gate_id=self.gate_id,
                        message="LAW tier requires invariant_registry to be LOCKED",
                        details=f"Got: {registry_status}",
                    ),
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                )
        
        return PreflightGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASSED,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# BER REQUIREMENT GATE — PAC-JEFFREY-C07
# Constitutional enforcement: Every PAC produces exactly one BER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LoopClosureContext:
    """
    Context for loop closure validation.
    
    Attributes:
        pac_id: The PAC being closed
        wrap_id: The WRAP issued for this PAC
        ber_id: The BER issued for this PAC (required)
        has_wrap: Whether WRAP exists
        has_ber: Whether BER exists
    """
    
    pac_id: str
    wrap_id: Optional[str] = None
    ber_id: Optional[str] = None
    has_wrap: bool = False
    has_ber: bool = False


class BERRequirementGate(PreflightGate):
    """
    GATE-BER-REQUIRED: BER Requirement Gate
    PAC-JEFFREY-C07: Constitutional enforcement
    
    INVARIANTS:
        - INV-GOV-010: Every PAC produces exactly one BER
        - INV-GOV-011: WRAP ≠ Decision (Proof only)
        - INV-GOV-012: LAW review without BER is FORBIDDEN
        - INV-GOV-013: Benson MUST emit BER before any closure
    
    This gate is executed BEFORE loop closure, not during preflight.
    It ensures that no PAC can be closed without a BER.
    """
    
    gate_id = PreflightGateID.BER_REQUIREMENT_GATE
    
    # Invariants enforced by this gate
    INVARIANTS = (
        "INV-GOV-010",  # Every PAC produces exactly one BER
        "INV-GOV-011",  # WRAP ≠ Decision (Proof only)
        "INV-GOV-012",  # LAW review without BER is FORBIDDEN
        "INV-GOV-013",  # Benson MUST emit BER before any closure
    )
    
    def execute(self, pac: Dict[str, Any]) -> PreflightGateResult:
        """
        This gate is not used during preflight.
        Use check_closure_requirements() for loop closure validation.
        """
        import time
        return PreflightGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASSED,
            execution_time_ms=0.0,
        )
    
    def check_closure_requirements(
        self,
        context: LoopClosureContext,
    ) -> PreflightGateResult:
        """
        Check that BER exists before allowing loop closure.
        
        Args:
            context: Loop closure context with PAC/WRAP/BER references
            
        Returns:
            PreflightGateResult indicating pass/fail
        """
        import time
        start = time.perf_counter()
        
        # INV-GOV-010: Every PAC produces exactly one BER
        if not context.has_ber:
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAILED,
                failure=PreflightFailure(
                    gate_id=self.gate_id,
                    message="BER required for loop closure (INV-GOV-010)",
                    details=f"PAC {context.pac_id} has no BER. "
                            f"WRAP is proof only — BER is mandatory.",
                ),
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
        
        # INV-GOV-011: WRAP ≠ Decision — verify BER exists even if WRAP exists
        if context.has_wrap and not context.has_ber:
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAILED,
                failure=PreflightFailure(
                    gate_id=self.gate_id,
                    message="WRAP is not a decision artifact (INV-GOV-011)",
                    details=f"PAC {context.pac_id} has WRAP {context.wrap_id} but no BER. "
                            f"WRAP documents execution — BER authorizes closure.",
                ),
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
        
        # All checks passed
        return PreflightGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASSED,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )
    
    def check_law_review_requirements(
        self,
        context: LoopClosureContext,
    ) -> PreflightGateResult:
        """
        Check that BER exists before LAW review.
        
        INV-GOV-012: LAW review without BER is FORBIDDEN
        
        Args:
            context: Loop closure context
            
        Returns:
            PreflightGateResult indicating pass/fail
        """
        import time
        start = time.perf_counter()
        
        if not context.has_ber:
            return PreflightGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAILED,
                failure=PreflightFailure(
                    gate_id=self.gate_id,
                    message="LAW review requires BER (INV-GOV-012)",
                    details=f"PAC {context.pac_id} cannot be LAW-reviewed without BER. "
                            f"Issue BER-{context.pac_id.replace('PAC-', '')} first.",
                ),
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
        
        return PreflightGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASSED,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LOOP CLOSURE ENFORCER — PAC-JEFFREY-C07
# ═══════════════════════════════════════════════════════════════════════════════

class LoopClosureEnforcer:
    """
    Enforces governance requirements for loop closure.
    PAC-JEFFREY-C07: Constitutional enforcement
    
    Ensures:
        - BER exists before closure (INV-GOV-010)
        - WRAP alone cannot close loop (INV-GOV-011)
        - LAW review has BER (INV-GOV-012)
        - Benson emits BER before closure (INV-GOV-013)
    """
    
    VERSION = "1.0.0"
    DIRECTIVE_ID = "DIR-BER-001"
    
    def __init__(self) -> None:
        self._ber_gate = BERRequirementGate()
    
    def can_close_loop(self, context: LoopClosureContext) -> PreflightGateResult:
        """
        Check if loop can be closed.
        
        Args:
            context: Loop closure context
            
        Returns:
            PreflightGateResult — PASSED if closure allowed, FAILED otherwise
        """
        return self._ber_gate.check_closure_requirements(context)
    
    def can_request_law_review(self, context: LoopClosureContext) -> PreflightGateResult:
        """
        Check if LAW review can be requested.
        
        Args:
            context: Loop closure context
            
        Returns:
            PreflightGateResult — PASSED if LAW review allowed, FAILED otherwise
        """
        return self._ber_gate.check_law_review_requirements(context)
    
    def enforce_ber_requirement(
        self,
        pac_id: str,
        wrap_id: Optional[str],
        ber_id: Optional[str],
    ) -> PreflightGateResult:
        """
        Convenience method to enforce BER requirement.
        
        Args:
            pac_id: The PAC ID
            wrap_id: The WRAP ID (if exists)
            ber_id: The BER ID (if exists)
            
        Returns:
            PreflightGateResult
        """
        context = LoopClosureContext(
            pac_id=pac_id,
            wrap_id=wrap_id,
            ber_id=ber_id,
            has_wrap=wrap_id is not None,
            has_ber=ber_id is not None,
        )
        return self.can_close_loop(context)


# Singleton instance
_LOOP_CLOSURE_ENFORCER: Optional[LoopClosureEnforcer] = None


def get_loop_closure_enforcer() -> LoopClosureEnforcer:
    """Get singleton LoopClosureEnforcer instance."""
    global _LOOP_CLOSURE_ENFORCER
    if _LOOP_CLOSURE_ENFORCER is None:
        _LOOP_CLOSURE_ENFORCER = LoopClosureEnforcer()
    return _LOOP_CLOSURE_ENFORCER


# ═══════════════════════════════════════════════════════════════════════════════
# PREFLIGHT ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════

class PreflightEnforcer:
    """
    Canonical Preflight Enforcer — CB-INV-PREFLIGHT-LAW-001
    
    Executes all preflight gates in FIXED order.
    Any failure HALTS execution immediately.
    No bypass. No self-attestation. No interpretation.
    
    Usage:
        enforcer = PreflightEnforcer()
        result = enforcer.enforce(pac_document)
        if not result.passed:
            # HARD STOP — execution is blocked
            print(f"Halted at: {result.halted_at}")
            print(f"Failure: {result.first_failure}")
    """
    
    VERSION = "1.0.0"
    INVARIANT_ID = "CB-INV-PREFLIGHT-LAW-001"
    
    def __init__(self) -> None:
        """Initialize with all gates in fixed order."""
        self._gates: Tuple[PreflightGate, ...] = (
            SchemaValidationGate(),
            LintEnforcementGate(),
            AdmissionGate(),
            GovernanceGate(),
            IdentityGate(),
            InvariantGate(),
        )
        
        # Verify gate order matches canonical order
        for i, gate in enumerate(self._gates):
            assert gate.gate_id == GATE_EXECUTION_ORDER[i], \
                f"Gate order mismatch at {i}: {gate.gate_id} != {GATE_EXECUTION_ORDER[i]}"
    
    def enforce(self, pac: Dict[str, Any]) -> PreflightResult:
        """
        Execute all preflight gates in fixed order.
        
        Args:
            pac: The PAC document to validate
            
        Returns:
            PreflightResult with pass/fail and gate details
        """
        import time
        start_total = time.perf_counter()
        
        pac_id = pac.get("metadata", {}).get("pac_id", "UNKNOWN")
        gate_results: List[PreflightGateResult] = []
        halted_at: Optional[PreflightGateID] = None
        all_passed = True
        
        for gate in self._gates:
            if halted_at is not None:
                # Previous gate failed — skip remaining gates
                gate_results.append(PreflightGateResult(
                    gate_id=gate.gate_id,
                    status=GateStatus.SKIPPED,
                ))
                continue
            
            # Execute gate
            result = gate.execute(pac)
            gate_results.append(result)
            
            if result.failed:
                all_passed = False
                halted_at = gate.gate_id
                # HARD STOP — no more gates execute
        
        total_time_ms = (time.perf_counter() - start_total) * 1000
        
        return PreflightResult(
            passed=all_passed,
            pac_id=pac_id,
            gate_results=tuple(gate_results),
            halted_at=halted_at,
            total_execution_time_ms=total_time_ms,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_PREFLIGHT_ENFORCER_INSTANCE: Optional[PreflightEnforcer] = None


def get_preflight_enforcer() -> PreflightEnforcer:
    """Get the singleton PreflightEnforcer instance."""
    global _PREFLIGHT_ENFORCER_INSTANCE
    if _PREFLIGHT_ENFORCER_INSTANCE is None:
        _PREFLIGHT_ENFORCER_INSTANCE = PreflightEnforcer()
    return _PREFLIGHT_ENFORCER_INSTANCE
