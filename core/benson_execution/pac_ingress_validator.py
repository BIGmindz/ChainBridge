# ═══════════════════════════════════════════════════════════════════════════════
# BensonExecution — PAC Ingress Validator
# PAC-BENSON-EXEC-C01: BENSON EXECUTION GENESIS & IDENTITY INSTANTIATION
# Agent: Benson Execution (GID-00-EXEC) — Deterministic Execution Engine
# ═══════════════════════════════════════════════════════════════════════════════

"""
PAC Ingress Validator — Execution Boundary Gate

PURPOSE:
    All PAC ingress is validated here before admission to execution.
    This is the single point of entry for all PAC execution.

INVARIANTS:
    INV-INGRESS-001: No PAC enters execution without validation
    INV-INGRESS-002: Invalid PAC → immediate REJECT
    INV-INGRESS-003: All validation is deterministic
    INV-INGRESS-004: No bypass paths

VALIDATION SEQUENCE:
    1. Schema validation (via BensonSchemaRegistry)
    2. Lint enforcement (via PACLintLaw)
    3. Preflight gates (via PreflightEnforcer)

DECISIONS:
    ADMIT: PAC may proceed to execution
    REJECT: PAC is blocked from execution (HARD STOP)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from core.benson_execution.schema_registry import (
    SchemaValidationResult,
    get_benson_schema_registry,
)
from core.benson_execution.pac_lint_law import (
    LintResult,
    get_pac_lint_law,
)
from core.benson_execution.preflight_gates import (
    PreflightResult,
    get_preflight_enforcer,
)


# ═══════════════════════════════════════════════════════════════════════════════
# INGRESS DECISION
# ═══════════════════════════════════════════════════════════════════════════════

class IngressDecision(Enum):
    """PAC ingress decision."""
    
    ADMIT = "ADMIT"
    REJECT = "REJECT"


class RejectReason(Enum):
    """Reason for PAC rejection."""
    
    SCHEMA_INVALID = "SCHEMA_INVALID"
    LINT_FAILED = "LINT_FAILED"
    PREFLIGHT_FAILED = "PREFLIGHT_FAILED"
    DUPLICATE_PAC = "DUPLICATE_PAC"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# ═══════════════════════════════════════════════════════════════════════════════
# INGRESS RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PACAdmitDecision:
    """
    Immutable decision to ADMIT a PAC to execution.
    
    Attributes:
        pac_id: The PAC that was admitted
        schema_result: Schema validation result
        lint_result: Lint enforcement result
        preflight_result: Preflight gate results
        admission_timestamp: When admission was granted
    """
    
    pac_id: str
    schema_result: SchemaValidationResult
    lint_result: LintResult
    preflight_result: PreflightResult
    admission_timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    
    @property
    def decision(self) -> IngressDecision:
        return IngressDecision.ADMIT


@dataclass(frozen=True)
class PACRejectDecision:
    """
    Immutable decision to REJECT a PAC from execution.
    
    Attributes:
        pac_id: The PAC that was rejected
        reason: Why the PAC was rejected
        schema_result: Schema validation result (if attempted)
        lint_result: Lint result (if attempted)
        preflight_result: Preflight result (if attempted)
        error_summary: Human-readable error summary
        rejection_timestamp: When rejection occurred
    """
    
    pac_id: str
    reason: RejectReason
    error_summary: str
    schema_result: Optional[SchemaValidationResult] = None
    lint_result: Optional[LintResult] = None
    preflight_result: Optional[PreflightResult] = None
    rejection_timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    
    @property
    def decision(self) -> IngressDecision:
        return IngressDecision.REJECT


# Union type for ingress results
PACIngressResult = PACAdmitDecision | PACRejectDecision


# ═══════════════════════════════════════════════════════════════════════════════
# PAC INGRESS VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class PACIngressValidator:
    """
    PAC Ingress Validator — Single Entry Point for PAC Execution
    
    All PACs must pass through this validator before execution.
    No bypass. No exceptions. No interpretation.
    
    VALIDATION SEQUENCE (FIXED ORDER):
        1. Schema validation
        2. Lint enforcement
        3. Preflight gates
    
    Any failure at any stage → REJECT
    
    Usage:
        validator = PACIngressValidator()
        result = validator.validate(pac_document)
        
        if result.decision == IngressDecision.ADMIT:
            # PAC may proceed to execution
            execute(pac_document)
        else:
            # HARD STOP — PAC is blocked
            log_rejection(result)
    """
    
    VERSION = "1.0.0"
    GID = "GID-00-EXEC"
    
    def __init__(self) -> None:
        """Initialize validator with all enforcement components."""
        self._schema_registry = get_benson_schema_registry()
        self._lint_law = get_pac_lint_law()
        self._preflight_enforcer = get_preflight_enforcer()
        self._validated_pacs: set[str] = set()  # Track validated PACs (duplicate prevention)
    
    def validate(self, pac: Dict[str, Any]) -> PACIngressResult:
        """
        Validate a PAC for execution admission.
        
        Args:
            pac: The PAC document as a dictionary
            
        Returns:
            PACAdmitDecision if PAC passes all validation
            PACRejectDecision if PAC fails any validation
        """
        # Extract PAC ID
        pac_id = pac.get("metadata", {}).get("pac_id", "UNKNOWN")
        
        # Check for duplicate PAC (same PAC cannot be validated twice)
        if pac_id != "UNKNOWN" and pac_id in self._validated_pacs:
            return PACRejectDecision(
                pac_id=pac_id,
                reason=RejectReason.DUPLICATE_PAC,
                error_summary=f"PAC '{pac_id}' has already been validated",
            )
        
        # STAGE 1: Schema Validation
        try:
            schema_result = self._schema_registry.validate(pac)
        except Exception as e:
            return PACRejectDecision(
                pac_id=pac_id,
                reason=RejectReason.UNKNOWN_ERROR,
                error_summary=f"Schema validation error: {str(e)}",
            )
        
        if not schema_result.is_valid:
            error_msgs = [str(e) for e in schema_result.errors[:3]]
            if len(schema_result.errors) > 3:
                error_msgs.append(f"+{len(schema_result.errors) - 3} more errors")
            
            return PACRejectDecision(
                pac_id=pac_id,
                reason=RejectReason.SCHEMA_INVALID,
                error_summary=f"Schema validation failed: {'; '.join(error_msgs)}",
                schema_result=schema_result,
            )
        
        # STAGE 2: Lint Enforcement
        try:
            lint_result = self._lint_law.enforce(pac)
        except Exception as e:
            return PACRejectDecision(
                pac_id=pac_id,
                reason=RejectReason.UNKNOWN_ERROR,
                error_summary=f"Lint enforcement error: {str(e)}",
                schema_result=schema_result,
            )
        
        if not lint_result.passed:
            violation_msgs = [str(v) for v in lint_result.violations[:3]]
            if len(lint_result.violations) > 3:
                violation_msgs.append(f"+{len(lint_result.violations) - 3} more violations")
            
            return PACRejectDecision(
                pac_id=pac_id,
                reason=RejectReason.LINT_FAILED,
                error_summary=f"Lint enforcement failed: {'; '.join(violation_msgs)}",
                schema_result=schema_result,
                lint_result=lint_result,
            )
        
        # STAGE 3: Preflight Gates
        try:
            preflight_result = self._preflight_enforcer.enforce(pac)
        except Exception as e:
            return PACRejectDecision(
                pac_id=pac_id,
                reason=RejectReason.UNKNOWN_ERROR,
                error_summary=f"Preflight enforcement error: {str(e)}",
                schema_result=schema_result,
                lint_result=lint_result,
            )
        
        if not preflight_result.passed:
            failure = preflight_result.first_failure
            error_msg = str(failure) if failure else "Unknown preflight failure"
            
            return PACRejectDecision(
                pac_id=pac_id,
                reason=RejectReason.PREFLIGHT_FAILED,
                error_summary=f"Preflight failed at {preflight_result.halted_at}: {error_msg}",
                schema_result=schema_result,
                lint_result=lint_result,
                preflight_result=preflight_result,
            )
        
        # ALL CHECKS PASSED — ADMIT
        if pac_id != "UNKNOWN":
            self._validated_pacs.add(pac_id)
        
        return PACAdmitDecision(
            pac_id=pac_id,
            schema_result=schema_result,
            lint_result=lint_result,
            preflight_result=preflight_result,
        )
    
    def reset_validation_cache(self) -> None:
        """
        Reset the validated PACs cache.
        
        WARNING: This should only be used in testing or
        when reprocessing PACs is explicitly required.
        """
        self._validated_pacs.clear()
    
    @property
    def validated_pac_count(self) -> int:
        """Number of PACs that have been validated."""
        return len(self._validated_pacs)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_INGRESS_VALIDATOR_INSTANCE: Optional[PACIngressValidator] = None


def get_pac_ingress_validator() -> PACIngressValidator:
    """Get the singleton PACIngressValidator instance."""
    global _INGRESS_VALIDATOR_INSTANCE
    if _INGRESS_VALIDATOR_INSTANCE is None:
        _INGRESS_VALIDATOR_INSTANCE = PACIngressValidator()
    return _INGRESS_VALIDATOR_INSTANCE
