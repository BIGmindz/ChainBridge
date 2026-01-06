# ═══════════════════════════════════════════════════════════════════════════════
# BensonExecution — Execution Engine
# PAC-BENSON-EXEC-C01: BENSON EXECUTION GENESIS & IDENTITY INSTANTIATION
# Agent: Benson Execution (GID-00-EXEC) — Deterministic Execution Engine
# ═══════════════════════════════════════════════════════════════════════════════

"""
Benson Execution Engine — Constitutional Execution Boundary

PURPOSE:
    Enforce ChainBridge law mechanically at the execution boundary.
    Every execution is either proven lawful or deterministically blocked.

IDENTITY:
    Name: Benson Execution
    Canonical ID: GID-00-EXEC
    Type: Deterministic Execution Engine
    Learning: DISABLED
    Reasoning: FORBIDDEN

RESPONSIBILITIES:
    - PAC schema validation
    - PAC lint enforcement
    - Canonical preflight enforcement
    - Execution admit / reject
    - Fail-closed halting
    - Audit emission
    - Deterministic replay support

EXPLICIT NON-RESPONSIBILITIES:
    - No decision-making
    - No interpretation
    - No optimization
    - No overrides
    - No learning

INVARIANTS:
    CB-INV-BENSON-EXEC-001: Single instance only
    CB-INV-BENSON-EXEC-002: No PAC → no execution
    CB-INV-BENSON-EXEC-003: Invalid PAC → hard stop

CONSTRAINTS:
    - No UI authority
    - No agent trust
    - No human discretion
    - No soft validation
    - No silent failure

GOVERNANCE_MODE: LAW
FAIL_CLOSED: TRUE
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from core.benson_execution.pac_ingress_validator import (
    PACAdmitDecision,
    PACRejectDecision,
    get_pac_ingress_validator,
)
from core.benson_execution.audit_emitter import (
    AuditEvent,
    AuditEventType,
    get_benson_audit_emitter,
)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION STATUS
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionStatus(Enum):
    """Execution status codes."""
    
    ADMITTED = "ADMITTED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    HALTED = "HALTED"


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ExecutionAdmitResult:
    """
    Result when PAC is admitted to execution.
    
    Attributes:
        pac_id: The PAC that was admitted
        status: Always ADMITTED
        ingress_result: The full ingress validation result
        execution_token: Token for tracking execution
        admit_timestamp: When admission occurred
    """
    
    pac_id: str
    ingress_result: PACAdmitDecision
    execution_token: str
    admit_timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    
    @property
    def status(self) -> ExecutionStatus:
        return ExecutionStatus.ADMITTED
    
    @property
    def is_admitted(self) -> bool:
        return True


@dataclass(frozen=True)
class ExecutionRejectResult:
    """
    Result when PAC is rejected from execution.
    
    Attributes:
        pac_id: The PAC that was rejected
        status: Always REJECTED
        ingress_result: The full ingress validation result
        rejection_reason: Human-readable rejection reason
        reject_timestamp: When rejection occurred
    """
    
    pac_id: str
    ingress_result: PACRejectDecision
    rejection_reason: str
    reject_timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    
    @property
    def status(self) -> ExecutionStatus:
        return ExecutionStatus.REJECTED
    
    @property
    def is_admitted(self) -> bool:
        return False


# Union type
ExecutionResult = ExecutionAdmitResult | ExecutionRejectResult


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_BENSON_INSTANCE: Optional["BensonExecution"] = None
_BENSON_LOCK = threading.Lock()


class DuplicateInstanceError(Exception):
    """Raised when attempting to create duplicate Benson Execution instance."""


# ═══════════════════════════════════════════════════════════════════════════════
# BENSON EXECUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class BensonExecution:
    """
    Benson Execution — Constitutional Execution Boundary
    
    This is the single point of entry for all PAC execution.
    Enforces ChainBridge law mechanically with no interpretation.
    
    SINGLETON: Only one instance allowed (CB-INV-BENSON-EXEC-001)
    
    Usage:
        benson = get_benson_execution()
        result = benson.admit(pac_document)
        
        if result.is_admitted:
            # Execute the PAC
            benson.mark_execution_started(result.execution_token)
            # ... do work ...
            benson.mark_execution_completed(result.execution_token)
        else:
            # HARD STOP
            log_rejection(result.rejection_reason)
    """
    
    VERSION = "1.0.0"
    PAC_REFERENCE = "PAC-BENSON-EXEC-C01"
    GID = "GID-00-EXEC"
    NAME = "Benson Execution"
    TYPE = "Deterministic Execution Engine"
    
    # Explicit capabilities (for audit)
    LEARNING = False
    REASONING = False
    DECISION_MAKING = False
    INTERPRETATION = False
    OPTIMIZATION = False
    OVERRIDE_ALLOWED = False
    
    def __init__(self) -> None:
        """
        Initialize Benson Execution.
        
        This should only be called via get_benson_execution().
        Direct instantiation will raise DuplicateInstanceError if
        an instance already exists.
        """
        global _BENSON_INSTANCE
        
        with _BENSON_LOCK:
            if _BENSON_INSTANCE is not None:
                # Emit audit event for blocked duplicate
                audit = get_benson_audit_emitter()
                audit.emit(
                    AuditEventType.DUPLICATE_INSTANCE_BLOCKED,
                    details={"message": "Duplicate BensonExecution instance blocked"},
                )
                raise DuplicateInstanceError(
                    "CB-INV-BENSON-EXEC-001: Only one Benson Execution instance allowed"
                )
            
            self._ingress_validator = get_pac_ingress_validator()
            self._audit_emitter = get_benson_audit_emitter()
            self._execution_tokens: Dict[str, Dict[str, Any]] = {}
            self._token_counter = 0
            self._initialized_at = datetime.utcnow().isoformat() + "Z"
            
            # Emit initialization event
            self._audit_emitter.emit(
                AuditEventType.BENSON_INITIALIZED,
                details={
                    "version": self.VERSION,
                    "pac_reference": self.PAC_REFERENCE,
                    "gid": self.GID,
                    "initialized_at": self._initialized_at,
                },
            )
            
            _BENSON_INSTANCE = self
    
    def admit(self, pac: Dict[str, Any]) -> ExecutionResult:
        """
        Attempt to admit a PAC for execution.
        
        This is the ONLY entry point for PAC execution.
        All validation happens here. No bypass.
        
        Args:
            pac: The PAC document to validate and potentially execute
            
        Returns:
            ExecutionAdmitResult if PAC is valid and admitted
            ExecutionRejectResult if PAC fails any validation
        """
        pac_id = pac.get("metadata", {}).get("pac_id", "UNKNOWN")
        
        # Emit ingress received event
        self._audit_emitter.emit(
            AuditEventType.PAC_INGRESS_RECEIVED,
            pac_id=pac_id,
            details={"metadata": pac.get("metadata", {})},
        )
        
        # Validate through ingress validator
        ingress_result = self._ingress_validator.validate(pac)
        
        if isinstance(ingress_result, PACAdmitDecision):
            # Generate execution token
            token = self._generate_execution_token(pac_id)
            
            # Track execution
            self._execution_tokens[token] = {
                "pac_id": pac_id,
                "status": ExecutionStatus.ADMITTED,
                "admitted_at": datetime.utcnow().isoformat() + "Z",
                "started_at": None,
                "completed_at": None,
            }
            
            # Emit admit event
            self._audit_emitter.emit(
                AuditEventType.PAC_ADMITTED,
                pac_id=pac_id,
                details={
                    "execution_token": token,
                    "schema_valid": ingress_result.schema_result.is_valid,
                    "lint_passed": ingress_result.lint_result.passed,
                    "preflight_passed": ingress_result.preflight_result.passed,
                },
            )
            
            return ExecutionAdmitResult(
                pac_id=pac_id,
                ingress_result=ingress_result,
                execution_token=token,
            )
        else:
            # REJECTED
            # Emit reject event
            self._audit_emitter.emit(
                AuditEventType.PAC_REJECTED,
                pac_id=pac_id,
                details={
                    "reason": ingress_result.reason.value,
                    "error_summary": ingress_result.error_summary,
                },
            )
            
            return ExecutionRejectResult(
                pac_id=pac_id,
                ingress_result=ingress_result,
                rejection_reason=ingress_result.error_summary,
            )
    
    def mark_execution_started(self, token: str) -> bool:
        """
        Mark that execution has started for a token.
        
        Args:
            token: The execution token from admit()
            
        Returns:
            True if marked successfully, False if token invalid
        """
        if token not in self._execution_tokens:
            return False
        
        self._execution_tokens[token]["status"] = ExecutionStatus.EXECUTING
        self._execution_tokens[token]["started_at"] = datetime.utcnow().isoformat() + "Z"
        
        self._audit_emitter.emit(
            AuditEventType.EXECUTION_STARTED,
            pac_id=self._execution_tokens[token]["pac_id"],
            details={"execution_token": token},
        )
        
        return True
    
    def mark_execution_completed(self, token: str) -> bool:
        """
        Mark that execution has completed successfully.
        
        Args:
            token: The execution token from admit()
            
        Returns:
            True if marked successfully, False if token invalid
        """
        if token not in self._execution_tokens:
            return False
        
        self._execution_tokens[token]["status"] = ExecutionStatus.COMPLETED
        self._execution_tokens[token]["completed_at"] = datetime.utcnow().isoformat() + "Z"
        
        self._audit_emitter.emit(
            AuditEventType.EXECUTION_COMPLETED,
            pac_id=self._execution_tokens[token]["pac_id"],
            details={"execution_token": token},
        )
        
        return True
    
    def mark_execution_halted(self, token: str, reason: str) -> bool:
        """
        Mark that execution was halted (fail-closed).
        
        Args:
            token: The execution token from admit()
            reason: Why execution was halted
            
        Returns:
            True if marked successfully, False if token invalid
        """
        if token not in self._execution_tokens:
            return False
        
        self._execution_tokens[token]["status"] = ExecutionStatus.HALTED
        self._execution_tokens[token]["halted_at"] = datetime.utcnow().isoformat() + "Z"
        self._execution_tokens[token]["halt_reason"] = reason
        
        self._audit_emitter.emit(
            AuditEventType.EXECUTION_HALTED,
            pac_id=self._execution_tokens[token]["pac_id"],
            details={
                "execution_token": token,
                "halt_reason": reason,
            },
        )
        
        return True
    
    def get_execution_status(self, token: str) -> Optional[ExecutionStatus]:
        """Get the current status of an execution."""
        if token not in self._execution_tokens:
            return None
        return self._execution_tokens[token]["status"]
    
    def _generate_execution_token(self, pac_id: str) -> str:
        """Generate a unique execution token."""
        self._token_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"EXEC-{pac_id}-{timestamp}-{self._token_counter:04d}"
    
    @property
    def audit_trail(self) -> Tuple[AuditEvent, ...]:
        """Get the complete audit trail."""
        return self._audit_emitter.get_events()
    
    @property
    def identity(self) -> Dict[str, Any]:
        """Get the Benson Execution identity (for audit)."""
        return {
            "name": self.NAME,
            "gid": self.GID,
            "type": self.TYPE,
            "version": self.VERSION,
            "pac_reference": self.PAC_REFERENCE,
            "learning": self.LEARNING,
            "reasoning": self.REASONING,
            "decision_making": self.DECISION_MAKING,
            "interpretation": self.INTERPRETATION,
            "optimization": self.OPTIMIZATION,
            "override_allowed": self.OVERRIDE_ALLOWED,
            "initialized_at": self._initialized_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE ACCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

def get_benson_execution() -> BensonExecution:
    """
    Get the singleton BensonExecution instance.
    
    Creates the instance if it doesn't exist.
    
    Returns:
        The BensonExecution singleton
    """
    global _BENSON_INSTANCE
    
    if _BENSON_INSTANCE is None:
        with _BENSON_LOCK:
            if _BENSON_INSTANCE is None:
                BensonExecution()
    
    return _BENSON_INSTANCE


def reset_benson_execution_for_testing() -> None:
    """
    Reset the Benson Execution singleton.
    
    WARNING: This should ONLY be used in testing.
    In production, there is no reset capability.
    """
    global _BENSON_INSTANCE
    
    with _BENSON_LOCK:
        if _BENSON_INSTANCE is not None:
            _BENSON_INSTANCE._audit_emitter.emit(
                AuditEventType.BENSON_SHUTDOWN,
                details={"reason": "Testing reset"},
            )
        _BENSON_INSTANCE = None
