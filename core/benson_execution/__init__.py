# ═══════════════════════════════════════════════════════════════════════════════
# BensonExecution — Constitutional Execution Boundary
# PAC-BENSON-EXEC-C01: BENSON EXECUTION GENESIS & IDENTITY INSTANTIATION
# Agent: Benson Execution (GID-00-EXEC) — Deterministic Execution Engine
# ═══════════════════════════════════════════════════════════════════════════════

"""
Benson Execution — Constitutional Execution Boundary

PURPOSE:
    Benson Execution is the constitutional boundary ensuring law executes 
    before intelligence and structure precedes autonomy.

IDENTITY:
    Name: Benson Execution
    Canonical ID: GID-00-EXEC
    Type: Deterministic Execution Engine
    Learning: DISABLED
    Reasoning: FORBIDDEN

MISSION:
    Enforce ChainBridge law mechanically at the execution boundary.

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
    CB-INV-PREFLIGHT-LAW-001: Canonical Preflight Enforcement
        - Preflight gates MUST execute for every PAC
        - Gates execute in fixed order
        - Any failure HALTS execution
        - No bypass or self-attestation allowed

    CB-INV-BENSON-EXEC-001: Single Instance
        - Only one Benson Execution instance allowed
        - No PAC → no execution
        - Invalid PAC → hard stop

GOVERNANCE_MODE: LAW
ENFORCEMENT_ENGINES: ALEX, Lex
INVARIANT_REGISTRY: LOCKED
DOWNGRADE_ALLOWED: FALSE
"""

from core.benson_execution.execution_engine import (
    BensonExecution,
    ExecutionAdmitResult,
    ExecutionRejectResult,
    get_benson_execution,
)
from core.benson_execution.pac_ingress_validator import (
    PACIngressValidator,
    PACIngressResult,
    PACAdmitDecision,
    PACRejectDecision,
)
from core.benson_execution.preflight_gates import (
    PreflightGate,
    PreflightGateResult,
    PreflightEnforcer,
    PreflightFailure,
)
from core.benson_execution.pac_lint_law import (
    PACLintLaw,
    LintViolation,
    LintResult,
)
from core.benson_execution.audit_emitter import (
    BensonAuditEmitter,
    AuditEvent,
    AuditEventType,
)

__all__ = [
    # Core execution engine
    "BensonExecution",
    "ExecutionAdmitResult",
    "ExecutionRejectResult",
    "get_benson_execution",
    # PAC ingress
    "PACIngressValidator",
    "PACIngressResult",
    "PACAdmitDecision",
    "PACRejectDecision",
    # Preflight
    "PreflightGate",
    "PreflightGateResult",
    "PreflightEnforcer",
    "PreflightFailure",
    # Lint
    "PACLintLaw",
    "LintViolation",
    "LintResult",
    # Audit
    "BensonAuditEmitter",
    "AuditEvent",
    "AuditEventType",
]

__version__ = "1.0.0"
__pac_reference__ = "PAC-BENSON-EXEC-C01"
__gid__ = "GID-00-EXEC"
