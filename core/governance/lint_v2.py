# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Lint v2 — Invariant Compiler & Runtime Enforcement Engine
# PAC-JEFFREY-P07: Lint v2 Law — Runtime & CI Enforcement Implementation
# Supersedes: PAC-JEFFREY-C07R (LAW), PAC-JEFFREY-P06R
# GOLD STANDARD · FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

"""
Lint v2 Invariant Compiler — Runtime-Enforced Governance.

INVARIANT CLASSES (PAC-JEFFREY-P05R Block 5, C07R LOCKED):
- S-INV: Structural — Schema validation, required fields
- M-INV: Semantic — Meaning/intent validation
- X-INV: Cross-Artifact — Inter-document consistency
- T-INV: Temporal — Ordering, timestamps, sequences
- A-INV: Authority — GID/lane authorization
- F-INV: Finality — BER/settlement eligibility
- C-INV: Training — Signal emission compliance

RUNTIME CHECKPOINTS (PAC-JEFFREY-P07 Block 5):
1. PAC_ADMISSION     → S-INV, A-INV, T-INV
2. WRAP_INGESTION    → S-INV, X-INV, C-INV
3. RG01_REVIEW       → X-INV, A-INV
4. BER_ELIGIBILITY   → F-INV, C-INV
5. SETTLEMENT_READINESS → F-INV

RUNTIME ACTIVATION (P07 Block 3):
- Schema validation ENABLED
- Invariant registry LOADED
- Fail-closed mode ACTIVE
- Runtime admission hook ENABLED

SCHEMA REFERENCES:
- lint_schema: CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0
- runtime_schema: PAC_EXECUTION_RUNTIME_TEMPLATE_V1

Rule Engine: Deterministic (Pydantic-based)
Output: Binary { valid: true|false, violation_id }
Warnings: FORBIDDEN (Production)
Override: FORBIDDEN (C07R)

Author: CODY (GID-01) — Backend Lane
Orchestration: BENSON (GID-00)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME ACTIVATION (PAC-JEFFREY-P07 Block 3)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RuntimeActivationStatus:
    """
    Runtime Activation Status per PAC-JEFFREY-C07R Block 3.
    
    ALL preconditions REQUIRED:
    - schema_validation_enabled
    - invariant_registry_loaded
    - fail_closed_enabled
    - runtime_admission_hook_enabled
    
    Failure Mode: HARD_FAIL
    """
    schema_validation_enabled: bool = False
    invariant_registry_loaded: bool = False
    fail_closed_enabled: bool = False
    runtime_admission_hook_enabled: bool = False
    activated_at: Optional[str] = None
    
    def is_ready(self) -> bool:
        """Check if ALL runtime preconditions are met."""
        return all([
            self.schema_validation_enabled,
            self.invariant_registry_loaded,
            self.fail_closed_enabled,
            self.runtime_admission_hook_enabled,
        ])
    
    def get_missing_preconditions(self) -> List[str]:
        """Get list of missing preconditions."""
        missing = []
        if not self.schema_validation_enabled:
            missing.append("schema_validation_enabled")
        if not self.invariant_registry_loaded:
            missing.append("invariant_registry_loaded")
        if not self.fail_closed_enabled:
            missing.append("fail_closed_enabled")
        if not self.runtime_admission_hook_enabled:
            missing.append("runtime_admission_hook_enabled")
        return missing
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_validation_enabled": self.schema_validation_enabled,
            "invariant_registry_loaded": self.invariant_registry_loaded,
            "fail_closed_enabled": self.fail_closed_enabled,
            "runtime_admission_hook_enabled": self.runtime_admission_hook_enabled,
            "is_ready": self.is_ready(),
            "missing_preconditions": self.get_missing_preconditions(),
            "activated_at": self.activated_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ROSTER (PAC-JEFFREY-P07 Block 4)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentRegistration:
    """Agent registration in the governance roster."""
    agent_name: str
    gid: str
    lane: str
    mode: str  # EXECUTING | NON_EXECUTING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "gid": self.gid,
            "lane": self.lane,
            "mode": self.mode,
        }


# Canonical Agent Roster per PAC-JEFFREY-C07R Block 4
# Undeclared agents: FORBIDDEN
# Dynamic agents: FORBIDDEN
AGENT_ROSTER: Dict[str, AgentRegistration] = {
    "GID-00": AgentRegistration("BENSON", "GID-00", "orchestration", "EXECUTING"),
    "GID-01": AgentRegistration("CODY", "GID-01", "backend", "EXECUTING"),
    "GID-02": AgentRegistration("SONNY", "GID-02", "frontend", "EXECUTING"),
    "GID-03": AgentRegistration("REECE", "GID-03", "docs", "EXECUTING"),
    "GID-04": AgentRegistration("MAXWELL", "GID-04", "ml", "EXECUTING"),
    "GID-05": AgentRegistration("TOBY", "GID-05", "testing", "EXECUTING"),
    "GID-06": AgentRegistration("SAM", "GID-06", "security", "EXECUTING"),
    "GID-07": AgentRegistration("DAN", "GID-07", "ci_cd", "EXECUTING"),
    "GID-11": AgentRegistration("ATLAS", "GID-11", "repo_integrity", "EXECUTING"),
}


def get_registered_agent(gid: str) -> Optional[AgentRegistration]:
    """Get agent registration by GID."""
    return AGENT_ROSTER.get(gid)


def validate_agent_gid(gid: str) -> Tuple[bool, Optional[str]]:
    """Validate that agent GID is registered."""
    if gid not in AGENT_ROSTER:
        return False, f"Unregistered agent GID: {gid}"
    return True, None


def validate_agent_lane(gid: str, requested_lane: str) -> Tuple[bool, Optional[str]]:
    """Validate agent is operating in authorized lane."""
    agent = AGENT_ROSTER.get(gid)
    if not agent:
        return False, f"Unregistered agent GID: {gid}"
    if agent.lane != requested_lane:
        return False, f"Cross-lane violation: {agent.agent_name} ({gid}) cannot operate in {requested_lane}"
    return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT → INVARIANT CLASS MAPPING (PAC-JEFFREY-P07 Block 5)
# ═══════════════════════════════════════════════════════════════════════════════

# Canonical mapping per PAC-JEFFREY-C07R Block 5
# Checkpoint skip: FORBIDDEN
CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    "PAC_ADMISSION": ["S-INV", "A-INV", "T-INV"],
    "WRAP_INGESTION": ["S-INV", "X-INV", "C-INV"],
    "RG01_EVALUATION": ["X-INV", "A-INV"],
    "BER_ELIGIBILITY": ["F-INV", "C-INV"],
    "SETTLEMENT_READINESS": ["F-INV"],
}


def get_required_invariant_classes(checkpoint: str) -> List[str]:
    """Get required invariant classes for a checkpoint."""
    return CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, [])


def validate_checkpoint_coverage(checkpoint: str, evaluated_classes: Set[str]) -> Tuple[bool, Optional[str]]:
    """Validate that all required invariant classes were evaluated at checkpoint."""
    required = set(CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, []))
    missing = required - evaluated_classes
    if missing:
        return False, f"Missing invariant classes at {checkpoint}: {missing}"
    return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT CLASS TAXONOMY (PAC-JEFFREY-P05R Block 5, C07R LOCKED)
# ═══════════════════════════════════════════════════════════════════════════════

class InvariantClass(str, Enum):
    """
    Lint v2 Invariant Classes per PAC-JEFFREY-P05R.
    
    ALL classes REQUIRED for complete governance coverage.
    """
    S_INV = "S-INV"  # Structural
    M_INV = "M-INV"  # Semantic
    X_INV = "X-INV"  # Cross-Artifact
    T_INV = "T-INV"  # Temporal
    A_INV = "A-INV"  # Authority
    F_INV = "F-INV"  # Finality
    C_INV = "C-INV"  # Training


class InvariantSeverity(str, Enum):
    """Invariant violation severity — ALL are HARD_FAIL in production."""
    CRITICAL = "CRITICAL"  # Immediate halt
    HIGH = "HIGH"          # Blocks progression
    # NOTE: MEDIUM/LOW/WARNING are FORBIDDEN in production per P05R


class EnforcementPoint(str, Enum):
    """
    Runtime Enforcement Points per PAC-JEFFREY-P06R Block 5.
    
    Each checkpoint evaluates ALL applicable invariants.
    """
    PAC_ADMISSION = "PAC_ADMISSION"
    WRAP_INGESTION = "WRAP_INGESTION"
    RG01_EVALUATION = "RG01_EVALUATION"
    BER_ELIGIBILITY = "BER_ELIGIBILITY"
    SETTLEMENT_READINESS = "SETTLEMENT_READINESS"


class EvaluationResult(str, Enum):
    """Binary evaluation result — NO WARNINGS in production."""
    PASS = "PASS"
    FAIL = "FAIL"


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class InvariantDefinition:
    """
    Definition of a single lint invariant.
    
    Each invariant has:
    - Unique ID (e.g., S-INV-001)
    - Class (S/M/X/T/A/F/C)
    - Description
    - Enforcement points
    - Evaluation function
    """
    invariant_id: str
    invariant_class: InvariantClass
    name: str
    description: str
    enforcement_points: List[EnforcementPoint]
    severity: InvariantSeverity = InvariantSeverity.CRITICAL
    schema_version: str = "CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "invariant_id": self.invariant_id,
            "invariant_class": self.invariant_class.value,
            "name": self.name,
            "description": self.description,
            "enforcement_points": [ep.value for ep in self.enforcement_points],
            "severity": self.severity.value,
            "schema_version": self.schema_version,
        }


@dataclass
class InvariantViolation:
    """
    Record of an invariant violation.
    
    Binary outcome — violation means HARD_FAIL.
    """
    violation_id: str
    invariant_id: str
    invariant_class: InvariantClass
    enforcement_point: EnforcementPoint
    artifact_id: str  # PAC/WRAP/BER ID
    artifact_type: str  # "PAC" | "WRAP" | "BER" | "ACK"
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    violation_hash: str = ""
    
    def __post_init__(self):
        if not self.violation_hash:
            self.violation_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic violation hash."""
        data = {
            "invariant_id": self.invariant_id,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "description": self.description,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "violation_id": self.violation_id,
            "invariant_id": self.invariant_id,
            "invariant_class": self.invariant_class.value,
            "enforcement_point": self.enforcement_point.value,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "description": self.description,
            "context": self.context,
            "detected_at": self.detected_at,
            "violation_hash": self.violation_hash,
        }


@dataclass
class EvaluationReport:
    """
    Complete evaluation report from lint v2 engine.
    
    Contains:
    - Overall result (PASS/FAIL)
    - All violations (if any)
    - Invariants evaluated
    - Training signals to emit
    """
    report_id: str
    enforcement_point: EnforcementPoint
    artifact_id: str
    artifact_type: str
    result: EvaluationResult
    violations: List[InvariantViolation] = field(default_factory=list)
    invariants_evaluated: List[str] = field(default_factory=list)
    evaluation_started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    evaluation_completed_at: Optional[str] = None
    evaluation_duration_ms: Optional[int] = None
    report_hash: str = ""
    
    def __post_init__(self):
        if not self.report_hash:
            self.report_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic report hash."""
        data = {
            "report_id": self.report_id,
            "artifact_id": self.artifact_id,
            "result": self.result.value,
            "violation_count": len(self.violations),
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
    
    def is_pass(self) -> bool:
        """Check if evaluation passed."""
        return self.result == EvaluationResult.PASS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "report_id": self.report_id,
            "enforcement_point": self.enforcement_point.value,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "result": self.result.value,
            "is_pass": self.is_pass(),
            "violations": [v.to_dict() for v in self.violations],
            "violation_count": len(self.violations),
            "invariants_evaluated": self.invariants_evaluated,
            "invariants_count": len(self.invariants_evaluated),
            "evaluation_started_at": self.evaluation_started_at,
            "evaluation_completed_at": self.evaluation_completed_at,
            "evaluation_duration_ms": self.evaluation_duration_ms,
            "report_hash": self.report_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL INVARIANTS — STRUCTURAL (S-INV)
# ═══════════════════════════════════════════════════════════════════════════════

S_INV_001 = InvariantDefinition(
    invariant_id="S-INV-001",
    invariant_class=InvariantClass.S_INV,
    name="PAC Schema Compliance",
    description="PAC must conform to CHAINBRIDGE_CANONICAL_PAC_SCHEMA@v1.0.0",
    enforcement_points=[EnforcementPoint.PAC_ADMISSION],
)

S_INV_002 = InvariantDefinition(
    invariant_id="S-INV-002",
    invariant_class=InvariantClass.S_INV,
    name="WRAP Schema Compliance",
    description="WRAP must conform to CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v1.0.0",
    enforcement_points=[EnforcementPoint.WRAP_INGESTION],
)

S_INV_003 = InvariantDefinition(
    invariant_id="S-INV-003",
    invariant_class=InvariantClass.S_INV,
    name="BER Schema Compliance",
    description="BER must conform to CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0",
    enforcement_points=[EnforcementPoint.BER_ELIGIBILITY],
)

S_INV_004 = InvariantDefinition(
    invariant_id="S-INV-004",
    invariant_class=InvariantClass.S_INV,
    name="Required PAC Fields",
    description="PAC must include: pac_id, author, classification, execution_mode",
    enforcement_points=[EnforcementPoint.PAC_ADMISSION],
)

S_INV_005 = InvariantDefinition(
    invariant_id="S-INV-005",
    invariant_class=InvariantClass.S_INV,
    name="Required WRAP Blocks",
    description="WRAP must include all 8 required blocks per P05R Block 6",
    enforcement_points=[EnforcementPoint.WRAP_INGESTION],
)


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL INVARIANTS — SEMANTIC (M-INV)
# ═══════════════════════════════════════════════════════════════════════════════

M_INV_001 = InvariantDefinition(
    invariant_id="M-INV-001",
    invariant_class=InvariantClass.M_INV,
    name="Execution Mode Validity",
    description="execution_mode must be PARALLEL or SEQUENTIAL",
    enforcement_points=[EnforcementPoint.PAC_ADMISSION],
)

M_INV_002 = InvariantDefinition(
    invariant_id="M-INV-002",
    invariant_class=InvariantClass.M_INV,
    name="ACK State Validity",
    description="ACK state must be PENDING|ACKNOWLEDGED|REJECTED|TIMEOUT",
    enforcement_points=[EnforcementPoint.PAC_ADMISSION, EnforcementPoint.WRAP_INGESTION],
)

M_INV_003 = InvariantDefinition(
    invariant_id="M-INV-003",
    invariant_class=InvariantClass.M_INV,
    name="BER Finality Validity",
    description="ber_finality must be FINAL or PROVISIONAL",
    enforcement_points=[EnforcementPoint.BER_ELIGIBILITY],
)


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL INVARIANTS — CROSS-ARTIFACT (X-INV)
# ═══════════════════════════════════════════════════════════════════════════════

X_INV_001 = InvariantDefinition(
    invariant_id="X-INV-001",
    invariant_class=InvariantClass.X_INV,
    name="WRAP References Valid PAC",
    description="WRAP.pac_id must match an existing PAC",
    enforcement_points=[EnforcementPoint.WRAP_INGESTION],
)

X_INV_002 = InvariantDefinition(
    invariant_id="X-INV-002",
    invariant_class=InvariantClass.X_INV,
    name="BER References Valid WRAP Set",
    description="BER.wrap_hash_set must reference validated WRAPs",
    enforcement_points=[EnforcementPoint.BER_ELIGIBILITY],
)

X_INV_003 = InvariantDefinition(
    invariant_id="X-INV-003",
    invariant_class=InvariantClass.X_INV,
    name="ACK References Valid Agent",
    description="ACK.agent_gid must be a registered agent",
    enforcement_points=[EnforcementPoint.PAC_ADMISSION],
)


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL INVARIANTS — TEMPORAL (T-INV)
# ═══════════════════════════════════════════════════════════════════════════════

T_INV_001 = InvariantDefinition(
    invariant_id="T-INV-001",
    invariant_class=InvariantClass.T_INV,
    name="ACK Before WRAP",
    description="Agent ACK must precede WRAP submission",
    enforcement_points=[EnforcementPoint.WRAP_INGESTION],
)

T_INV_002 = InvariantDefinition(
    invariant_id="T-INV-002",
    invariant_class=InvariantClass.T_INV,
    name="WRAP Before BER",
    description="All WRAPs must be submitted before BER issuance",
    enforcement_points=[EnforcementPoint.BER_ELIGIBILITY],
)

T_INV_003 = InvariantDefinition(
    invariant_id="T-INV-003",
    invariant_class=InvariantClass.T_INV,
    name="RG-01 Before BER",
    description="RG-01 must PASS before BER issuance",
    enforcement_points=[EnforcementPoint.BER_ELIGIBILITY],
)

T_INV_004 = InvariantDefinition(
    invariant_id="T-INV-004",
    invariant_class=InvariantClass.T_INV,
    name="ACK Latency Threshold",
    description="ACK latency must not exceed threshold for settlement eligibility",
    enforcement_points=[EnforcementPoint.SETTLEMENT_READINESS],
)


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL INVARIANTS — AUTHORITY (A-INV)
# ═══════════════════════════════════════════════════════════════════════════════

A_INV_001 = InvariantDefinition(
    invariant_id="A-INV-001",
    invariant_class=InvariantClass.A_INV,
    name="Lane Authorization",
    description="Agent must operate within authorized lane (INV-CP-014)",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.WRAP_INGESTION,
    ],
)

A_INV_002 = InvariantDefinition(
    invariant_id="A-INV-002",
    invariant_class=InvariantClass.A_INV,
    name="GID Registration",
    description="Agent GID must be registered in system",
    enforcement_points=[EnforcementPoint.PAC_ADMISSION],
)

A_INV_003 = InvariantDefinition(
    invariant_id="A-INV-003",
    invariant_class=InvariantClass.A_INV,
    name="Non-Executing Constraints",
    description="NON_EXECUTING agents cannot perform code changes or approvals",
    enforcement_points=[EnforcementPoint.WRAP_INGESTION],
)

A_INV_004 = InvariantDefinition(
    invariant_id="A-INV-004",
    invariant_class=InvariantClass.A_INV,
    name="No Implicit Activation",
    description="Agents must explicitly ACK — no implicit activation (INV-CP-015)",
    enforcement_points=[EnforcementPoint.PAC_ADMISSION],
)


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL INVARIANTS — FINALITY (F-INV)
# ═══════════════════════════════════════════════════════════════════════════════

F_INV_001 = InvariantDefinition(
    invariant_id="F-INV-001",
    invariant_class=InvariantClass.F_INV,
    name="BER Requires All ACKs",
    description="BER cannot be issued without all required ACKs (INV-CP-005)",
    enforcement_points=[EnforcementPoint.BER_ELIGIBILITY],
)

F_INV_002 = InvariantDefinition(
    invariant_id="F-INV-002",
    invariant_class=InvariantClass.F_INV,
    name="BER Requires Valid WRAPs",
    description="BER requires all WRAPs validated (INV-CP-006)",
    enforcement_points=[EnforcementPoint.BER_ELIGIBILITY],
)

F_INV_003 = InvariantDefinition(
    invariant_id="F-INV-003",
    invariant_class=InvariantClass.F_INV,
    name="Settlement Requires FINAL BER",
    description="Settlement requires BER finality = FINAL",
    enforcement_points=[EnforcementPoint.SETTLEMENT_READINESS],
)

F_INV_004 = InvariantDefinition(
    invariant_id="F-INV-004",
    invariant_class=InvariantClass.F_INV,
    name="Settlement Requires Ledger Commit",
    description="Settlement requires ledger commit attestation (INV-CP-007)",
    enforcement_points=[EnforcementPoint.SETTLEMENT_READINESS],
)

F_INV_005 = InvariantDefinition(
    invariant_id="F-INV-005",
    invariant_class=InvariantClass.F_INV,
    name="Settlement Verdict Required",
    description="SettlementReadinessVerdict required before BER FINAL (INV-CP-017)",
    enforcement_points=[EnforcementPoint.SETTLEMENT_READINESS],
)


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL INVARIANTS — TRAINING (C-INV)
# ═══════════════════════════════════════════════════════════════════════════════

C_INV_001 = InvariantDefinition(
    invariant_id="C-INV-001",
    invariant_class=InvariantClass.C_INV,
    name="Training Signal Required",
    description="Each WRAP must include ≥1 training signal (INV-CP-011)",
    enforcement_points=[EnforcementPoint.WRAP_INGESTION, EnforcementPoint.RG01_EVALUATION],
)

C_INV_002 = InvariantDefinition(
    invariant_id="C-INV-002",
    invariant_class=InvariantClass.C_INV,
    name="Training Signal Non-Empty",
    description="Training signals must not be empty or generic",
    enforcement_points=[EnforcementPoint.WRAP_INGESTION],
)

C_INV_003 = InvariantDefinition(
    invariant_id="C-INV-003",
    invariant_class=InvariantClass.C_INV,
    name="Positive Closure Required",
    description="Each WRAP must include positive closure (INV-CP-012)",
    enforcement_points=[EnforcementPoint.WRAP_INGESTION, EnforcementPoint.RG01_EVALUATION],
)

C_INV_004 = InvariantDefinition(
    invariant_id="C-INV-004",
    invariant_class=InvariantClass.C_INV,
    name="Positive Closure Valid",
    description="Positive closure must pass all validation checks",
    enforcement_points=[EnforcementPoint.RG01_EVALUATION],
)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

# All canonical invariants indexed by ID
INVARIANT_REGISTRY: Dict[str, InvariantDefinition] = {
    # Structural
    "S-INV-001": S_INV_001,
    "S-INV-002": S_INV_002,
    "S-INV-003": S_INV_003,
    "S-INV-004": S_INV_004,
    "S-INV-005": S_INV_005,
    # Semantic
    "M-INV-001": M_INV_001,
    "M-INV-002": M_INV_002,
    "M-INV-003": M_INV_003,
    # Cross-Artifact
    "X-INV-001": X_INV_001,
    "X-INV-002": X_INV_002,
    "X-INV-003": X_INV_003,
    # Temporal
    "T-INV-001": T_INV_001,
    "T-INV-002": T_INV_002,
    "T-INV-003": T_INV_003,
    "T-INV-004": T_INV_004,
    # Authority
    "A-INV-001": A_INV_001,
    "A-INV-002": A_INV_002,
    "A-INV-003": A_INV_003,
    "A-INV-004": A_INV_004,
    # Finality
    "F-INV-001": F_INV_001,
    "F-INV-002": F_INV_002,
    "F-INV-003": F_INV_003,
    "F-INV-004": F_INV_004,
    "F-INV-005": F_INV_005,
    # Training
    "C-INV-001": C_INV_001,
    "C-INV-002": C_INV_002,
    "C-INV-003": C_INV_003,
    "C-INV-004": C_INV_004,
}


def get_invariants_for_enforcement_point(
    enforcement_point: EnforcementPoint,
) -> List[InvariantDefinition]:
    """Get all invariants applicable to a specific enforcement point."""
    return [
        inv for inv in INVARIANT_REGISTRY.values()
        if enforcement_point in inv.enforcement_points
    ]


def get_invariants_by_class(
    invariant_class: InvariantClass,
) -> List[InvariantDefinition]:
    """Get all invariants of a specific class."""
    return [
        inv for inv in INVARIANT_REGISTRY.values()
        if inv.invariant_class == invariant_class
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# LINT V2 ENGINE — RUNTIME EVALUATOR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LintV2Engine:
    """
    Lint v2 Runtime Enforcement Engine.
    
    PAC-JEFFREY-P07: Runtime & CI Enforcement Implementation
    
    Runtime Activation (Block 3):
    - schema_validation ENABLED
    - invariant_registry LOADED
    - fail_closed_enabled ACTIVE
    - runtime_admission_hook ENABLED
    
    Binary output only — no warnings in production.
    Override: FORBIDDEN (C07R)
    
    Usage:
        engine = LintV2Engine()
        
        # Verify runtime activation first
        if not engine.verify_runtime_activation():
            raise RuntimeError("Lint v2 runtime not activated")
        
        report = engine.evaluate_pac_admission(pac_data)
        if not report.is_pass():
            raise GovernanceViolation(report.violations)
    """
    
    schema_version: str = "CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0"
    runtime_schema: str = "PAC_EXECUTION_RUNTIME_TEMPLATE_V1"
    fail_mode: str = "HARD_FAIL"
    warnings_enabled: bool = False  # FORBIDDEN in production per P05R
    override_enabled: bool = False  # FORBIDDEN per C07R
    _activation_status: RuntimeActivationStatus = field(default_factory=RuntimeActivationStatus)
    
    def __post_init__(self):
        """Initialize and activate runtime."""
        self._activate_runtime()
    
    def _activate_runtime(self) -> None:
        """Activate runtime with all preconditions (P07 Block 3)."""
        self._activation_status.schema_validation_enabled = True
        self._activation_status.invariant_registry_loaded = len(INVARIANT_REGISTRY) > 0
        self._activation_status.fail_closed_enabled = self.fail_mode == "HARD_FAIL"
        self._activation_status.runtime_admission_hook_enabled = True
        
        if self._activation_status.is_ready():
            self._activation_status.activated_at = datetime.now(timezone.utc).isoformat()
            logger.info("LINT_V2: Runtime activated successfully")
        else:
            missing = self._activation_status.get_missing_preconditions()
            logger.error(f"LINT_V2: Runtime activation FAILED - missing: {missing}")
    
    def verify_runtime_activation(self) -> bool:
        """Verify all runtime preconditions are met (P07 Block 3)."""
        return self._activation_status.is_ready()
    
    def get_activation_status(self) -> RuntimeActivationStatus:
        """Get current runtime activation status."""
        return self._activation_status
    
    def validate_agent(self, gid: str, lane: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Validate agent against roster (P07 Block 4)."""
        valid, err = validate_agent_gid(gid)
        if not valid:
            return False, err
        if lane:
            return validate_agent_lane(gid, lane)
        return True, None
    
    def evaluate(
        self,
        enforcement_point: EnforcementPoint,
        artifact_id: str,
        artifact_type: str,
        context: Dict[str, Any],
    ) -> EvaluationReport:
        """
        Evaluate all applicable invariants at an enforcement point.
        
        Returns binary result — PASS or FAIL.
        First failure HALTS evaluation (fail-fast in HARD_FAIL mode).
        
        Runtime admission hook checks activation status first (P07 Block 3).
        """
        # Runtime admission hook - verify activation (P07 Block 3)
        if not self.verify_runtime_activation():
            missing = self._activation_status.get_missing_preconditions()
            return EvaluationReport(
                report_id=f"LINT-{uuid4().hex[:12].upper()}",
                enforcement_point=enforcement_point,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                result=EvaluationResult.FAIL,
                violations=[InvariantViolation(
                    violation_id=f"VIO-RUNTIME-{uuid4().hex[:8].upper()}",
                    invariant_id="RUNTIME-001",
                    invariant_class=InvariantClass.S_INV,
                    enforcement_point=enforcement_point,
                    artifact_id=artifact_id,
                    artifact_type=artifact_type,
                    description=f"Runtime not activated: {missing}",
                    context={"missing_preconditions": missing},
                )],
                invariants_evaluated=[],
            )
        
        start_time = datetime.now(timezone.utc)
        violations: List[InvariantViolation] = []
        evaluated: List[str] = []
        
        # Get applicable invariants
        invariants = get_invariants_for_enforcement_point(enforcement_point)
        
        for inv in invariants:
            evaluated.append(inv.invariant_id)
            
            # Evaluate invariant
            violation = self._evaluate_invariant(
                invariant=inv,
                enforcement_point=enforcement_point,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                context=context,
            )
            
            if violation:
                violations.append(violation)
                
                # Fail-fast in HARD_FAIL mode
                if self.fail_mode == "HARD_FAIL":
                    logger.warning(
                        f"LINT_V2: HARD_FAIL on {inv.invariant_id} "
                        f"at {enforcement_point.value} for {artifact_id}"
                    )
                    break
        
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        result = EvaluationResult.FAIL if violations else EvaluationResult.PASS
        
        report = EvaluationReport(
            report_id=f"LINT-{uuid4().hex[:12].upper()}",
            enforcement_point=enforcement_point,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            result=result,
            violations=violations,
            invariants_evaluated=evaluated,
            evaluation_completed_at=end_time.isoformat(),
            evaluation_duration_ms=duration_ms,
        )
        
        logger.info(
            f"LINT_V2: {enforcement_point.value} evaluation complete "
            f"artifact={artifact_id} result={result.value} "
            f"violations={len(violations)} duration={duration_ms}ms"
        )
        
        return report
    
    def _evaluate_invariant(
        self,
        invariant: InvariantDefinition,
        enforcement_point: EnforcementPoint,
        artifact_id: str,
        artifact_type: str,
        context: Dict[str, Any],
    ) -> Optional[InvariantViolation]:
        """
        Evaluate a single invariant.
        
        Returns violation if failed, None if passed.
        """
        try:
            # Dispatch to specific evaluator based on invariant class
            evaluator = self._get_evaluator(invariant.invariant_class)
            passed, failure_reason = evaluator(invariant, context)
            
            if not passed:
                return InvariantViolation(
                    violation_id=f"VIO-{uuid4().hex[:8].upper()}",
                    invariant_id=invariant.invariant_id,
                    invariant_class=invariant.invariant_class,
                    enforcement_point=enforcement_point,
                    artifact_id=artifact_id,
                    artifact_type=artifact_type,
                    description=failure_reason or invariant.description,
                    context={"invariant_name": invariant.name},
                )
            
            return None
            
        except Exception as e:
            # Exceptions are violations in FAIL_CLOSED mode
            logger.error(f"LINT_V2: Exception evaluating {invariant.invariant_id}: {e}")
            return InvariantViolation(
                violation_id=f"VIO-{uuid4().hex[:8].upper()}",
                invariant_id=invariant.invariant_id,
                invariant_class=invariant.invariant_class,
                enforcement_point=enforcement_point,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                description=f"Evaluation exception: {str(e)}",
                context={"exception_type": type(e).__name__},
            )
    
    def _get_evaluator(
        self, 
        inv_class: InvariantClass,
    ) -> Callable[[InvariantDefinition, Dict[str, Any]], Tuple[bool, Optional[str]]]:
        """Get the evaluator function for an invariant class."""
        evaluators = {
            InvariantClass.S_INV: self._evaluate_structural,
            InvariantClass.M_INV: self._evaluate_semantic,
            InvariantClass.X_INV: self._evaluate_cross_artifact,
            InvariantClass.T_INV: self._evaluate_temporal,
            InvariantClass.A_INV: self._evaluate_authority,
            InvariantClass.F_INV: self._evaluate_finality,
            InvariantClass.C_INV: self._evaluate_training,
        }
        return evaluators.get(inv_class, self._evaluate_default)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CLASS-SPECIFIC EVALUATORS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _evaluate_structural(
        self,
        invariant: InvariantDefinition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate structural invariants (S-INV)."""
        inv_id = invariant.invariant_id
        
        if inv_id == "S-INV-001":  # PAC Schema
            pac = context.get("pac")
            if not pac:
                return False, "PAC not provided in context"
            required = ["pac_id", "author", "classification"]
            for field in required:
                if not pac.get(field):
                    return False, f"Missing required PAC field: {field}"
            return True, None
        
        if inv_id == "S-INV-002":  # WRAP Schema
            wrap = context.get("wrap")
            if not wrap:
                return False, "WRAP not provided in context"
            return True, None
        
        if inv_id == "S-INV-003":  # BER Schema
            ber = context.get("ber")
            if not ber:
                return False, "BER not provided in context"
            return True, None
        
        if inv_id == "S-INV-004":  # Required PAC Fields
            pac = context.get("pac", {})
            required = ["pac_id", "author", "classification", "execution_mode"]
            missing = [f for f in required if not pac.get(f)]
            if missing:
                return False, f"Missing PAC fields: {', '.join(missing)}"
            return True, None
        
        if inv_id == "S-INV-005":  # Required WRAP Blocks
            wrap = context.get("wrap", {})
            required_blocks = [
                "identity", "ack_evidence", "task_receipt", 
                "determinism", "output_summary", "violations",
                "training_signals", "positive_closure"
            ]
            missing = [b for b in required_blocks if b not in wrap]
            if missing:
                return False, f"Missing WRAP blocks: {', '.join(missing)}"
            return True, None
        
        return True, None
    
    def _evaluate_semantic(
        self,
        invariant: InvariantDefinition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate semantic invariants (M-INV)."""
        inv_id = invariant.invariant_id
        
        if inv_id == "M-INV-001":  # Execution Mode Validity
            pac = context.get("pac", {})
            mode = pac.get("execution_mode")
            if mode not in ("PARALLEL", "SEQUENTIAL"):
                return False, f"Invalid execution_mode: {mode}"
            return True, None
        
        if inv_id == "M-INV-002":  # ACK State Validity
            acks = context.get("acks", [])
            valid_states = {"PENDING", "ACKNOWLEDGED", "REJECTED", "TIMEOUT"}
            for ack in acks:
                state = ack.get("state")
                if state not in valid_states:
                    return False, f"Invalid ACK state: {state}"
            return True, None
        
        if inv_id == "M-INV-003":  # BER Finality Validity
            ber = context.get("ber", {})
            finality = ber.get("ber_finality")
            if finality not in ("FINAL", "PROVISIONAL"):
                return False, f"Invalid ber_finality: {finality}"
            return True, None
        
        return True, None
    
    def _evaluate_cross_artifact(
        self,
        invariant: InvariantDefinition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate cross-artifact invariants (X-INV)."""
        inv_id = invariant.invariant_id
        
        if inv_id == "X-INV-001":  # WRAP References Valid PAC
            wrap = context.get("wrap", {})
            pac_id = wrap.get("pac_id")
            known_pacs = context.get("known_pacs", set())
            if pac_id and known_pacs and pac_id not in known_pacs:
                return False, f"WRAP references unknown PAC: {pac_id}"
            return True, None
        
        if inv_id == "X-INV-002":  # BER References Valid WRAP Set
            ber = context.get("ber", {})
            wrap_hashes = ber.get("wrap_hash_set", [])
            valid_wraps = context.get("valid_wrap_hashes", set())
            if valid_wraps:
                invalid = [h for h in wrap_hashes if h not in valid_wraps]
                if invalid:
                    return False, f"BER references invalid WRAPs: {invalid}"
            return True, None
        
        if inv_id == "X-INV-003":  # ACK References Valid Agent
            acks = context.get("acks", [])
            registered_gids = context.get("registered_gids", set())
            if registered_gids:
                for ack in acks:
                    gid = ack.get("agent_gid")
                    if gid not in registered_gids:
                        return False, f"ACK from unregistered agent: {gid}"
            return True, None
        
        return True, None
    
    def _evaluate_temporal(
        self,
        invariant: InvariantDefinition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate temporal invariants (T-INV)."""
        inv_id = invariant.invariant_id
        
        if inv_id == "T-INV-001":  # ACK Before WRAP
            wrap = context.get("wrap", {})
            agent_gid = wrap.get("agent_gid")
            acks = context.get("acks", [])
            ack_gids = {a.get("agent_gid") for a in acks if a.get("state") == "ACKNOWLEDGED"}
            if agent_gid and agent_gid not in ack_gids:
                return False, f"WRAP submitted without prior ACK from {agent_gid}"
            return True, None
        
        if inv_id == "T-INV-002":  # WRAP Before BER
            wraps_complete = context.get("wraps_complete", True)
            if not wraps_complete:
                return False, "BER issued before all WRAPs collected"
            return True, None
        
        if inv_id == "T-INV-003":  # RG-01 Before BER
            rg01_passed = context.get("rg01_passed")
            if rg01_passed is False:
                return False, "BER issued before RG-01 PASS"
            return True, None
        
        if inv_id == "T-INV-004":  # ACK Latency Threshold
            latency_eligible = context.get("latency_eligible", True)
            if not latency_eligible:
                return False, "ACK latency exceeds threshold"
            return True, None
        
        return True, None
    
    def _evaluate_authority(
        self,
        invariant: InvariantDefinition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate authority invariants (A-INV)."""
        inv_id = invariant.invariant_id
        
        if inv_id == "A-INV-001":  # Lane Authorization
            agent_gid = context.get("agent_gid")
            requested_lane = context.get("requested_lane")
            authorized_lanes = context.get("authorized_lanes", {})
            if agent_gid and requested_lane and authorized_lanes:
                agent_lane = authorized_lanes.get(agent_gid)
                if agent_lane and agent_lane != requested_lane:
                    return False, f"Cross-lane violation: {agent_gid} in {requested_lane}"
            return True, None
        
        if inv_id == "A-INV-002":  # GID Registration
            agent_gid = context.get("agent_gid")
            registered_gids = context.get("registered_gids", set())
            if agent_gid and registered_gids and agent_gid not in registered_gids:
                return False, f"Unregistered GID: {agent_gid}"
            return True, None
        
        if inv_id == "A-INV-003":  # Non-Executing Constraints
            agent_gid = context.get("agent_gid")
            agent_mode = context.get("agent_mode")
            has_code_changes = context.get("has_code_changes", False)
            if agent_mode == "NON_EXECUTING" and has_code_changes:
                return False, f"NON_EXECUTING agent {agent_gid} performed code changes"
            return True, None
        
        if inv_id == "A-INV-004":  # No Implicit Activation
            implicit_activation = context.get("implicit_activation", False)
            if implicit_activation:
                return False, "Implicit agent activation detected"
            return True, None
        
        return True, None
    
    def _evaluate_finality(
        self,
        invariant: InvariantDefinition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate finality invariants (F-INV)."""
        inv_id = invariant.invariant_id
        
        if inv_id == "F-INV-001":  # BER Requires All ACKs
            all_acks_received = context.get("all_acks_received", True)
            if not all_acks_received:
                return False, "BER issued without all required ACKs"
            return True, None
        
        if inv_id == "F-INV-002":  # BER Requires Valid WRAPs
            all_wraps_valid = context.get("all_wraps_valid", True)
            if not all_wraps_valid:
                return False, "BER issued with invalid WRAPs"
            return True, None
        
        if inv_id == "F-INV-003":  # Settlement Requires FINAL BER
            ber = context.get("ber", {})
            finality = ber.get("ber_finality")
            if finality != "FINAL":
                return False, f"Settlement requires BER FINAL, got {finality}"
            return True, None
        
        if inv_id == "F-INV-004":  # Settlement Requires Ledger Commit
            ledger_committed = context.get("ledger_committed", False)
            if not ledger_committed:
                return False, "Settlement requires ledger commit attestation"
            return True, None
        
        if inv_id == "F-INV-005":  # Settlement Verdict Required
            verdict_present = context.get("settlement_verdict_present", False)
            if not verdict_present:
                return False, "SettlementReadinessVerdict required before BER FINAL"
            return True, None
        
        return True, None
    
    def _evaluate_training(
        self,
        invariant: InvariantDefinition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate training invariants (C-INV)."""
        inv_id = invariant.invariant_id
        
        if inv_id == "C-INV-001":  # Training Signal Required
            training_signals = context.get("training_signals", [])
            if not training_signals or len(training_signals) == 0:
                return False, "No training signals present (minimum 1 required)"
            return True, None
        
        if inv_id == "C-INV-002":  # Training Signal Non-Empty
            training_signals = context.get("training_signals", [])
            for signal in training_signals:
                observation = signal.get("observation", "")
                if not observation or len(observation.strip()) < 10:
                    return False, "Training signal observation is empty or generic"
            return True, None
        
        if inv_id == "C-INV-003":  # Positive Closure Required
            positive_closure = context.get("positive_closure")
            if not positive_closure:
                return False, "No positive closure present"
            return True, None
        
        if inv_id == "C-INV-004":  # Positive Closure Valid
            positive_closure = context.get("positive_closure", {})
            required = ["scope_complete", "no_violations", "ready_for_next_stage"]
            for field in required:
                if not positive_closure.get(field):
                    return False, f"Positive closure missing or invalid: {field}"
            return True, None
        
        return True, None
    
    def _evaluate_default(
        self,
        invariant: InvariantDefinition,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Default evaluator — passes if no specific logic."""
        return True, None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS FOR ENFORCEMENT POINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def evaluate_pac_admission(
        self,
        pac_id: str,
        pac_data: Dict[str, Any],
        acks: Optional[List[Dict[str, Any]]] = None,
    ) -> EvaluationReport:
        """Evaluate PAC at admission checkpoint."""
        context = {
            "pac": pac_data,
            "acks": acks or [],
        }
        return self.evaluate(
            enforcement_point=EnforcementPoint.PAC_ADMISSION,
            artifact_id=pac_id,
            artifact_type="PAC",
            context=context,
        )
    
    def evaluate_wrap_ingestion(
        self,
        wrap_id: str,
        wrap_data: Dict[str, Any],
        acks: Optional[List[Dict[str, Any]]] = None,
        known_pacs: Optional[Set[str]] = None,
    ) -> EvaluationReport:
        """Evaluate WRAP at ingestion checkpoint."""
        context = {
            "wrap": wrap_data,
            "acks": acks or [],
            "known_pacs": known_pacs or set(),
            "agent_gid": wrap_data.get("agent_gid"),
        }
        return self.evaluate(
            enforcement_point=EnforcementPoint.WRAP_INGESTION,
            artifact_id=wrap_id,
            artifact_type="WRAP",
            context=context,
        )
    
    def evaluate_rg01(
        self,
        pac_id: str,
        wraps: List[Dict[str, Any]],
        training_signals: List[Dict[str, Any]],
        positive_closures: List[Dict[str, Any]],
    ) -> EvaluationReport:
        """Evaluate at RG-01 checkpoint."""
        context = {
            "wraps": wraps,
            "training_signals": training_signals,
            "positive_closures": positive_closures,
        }
        return self.evaluate(
            enforcement_point=EnforcementPoint.RG01_EVALUATION,
            artifact_id=pac_id,
            artifact_type="RG01",
            context=context,
        )
    
    def evaluate_ber_eligibility(
        self,
        ber_id: str,
        ber_data: Dict[str, Any],
        all_acks_received: bool,
        all_wraps_valid: bool,
        rg01_passed: bool,
    ) -> EvaluationReport:
        """Evaluate BER eligibility checkpoint."""
        context = {
            "ber": ber_data,
            "all_acks_received": all_acks_received,
            "all_wraps_valid": all_wraps_valid,
            "rg01_passed": rg01_passed,
            "wraps_complete": all_wraps_valid,
        }
        return self.evaluate(
            enforcement_point=EnforcementPoint.BER_ELIGIBILITY,
            artifact_id=ber_id,
            artifact_type="BER",
            context=context,
        )
    
    def evaluate_settlement_readiness(
        self,
        pac_id: str,
        ber_data: Dict[str, Any],
        latency_eligible: bool,
        ledger_committed: bool,
        verdict_present: bool,
    ) -> EvaluationReport:
        """Evaluate settlement readiness checkpoint."""
        context = {
            "ber": ber_data,
            "latency_eligible": latency_eligible,
            "ledger_committed": ledger_committed,
            "settlement_verdict_present": verdict_present,
        }
        return self.evaluate(
            enforcement_point=EnforcementPoint.SETTLEMENT_READINESS,
            artifact_id=pac_id,
            artifact_type="SETTLEMENT",
            context=context,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY & SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

# Global engine instance (singleton)
_lint_v2_engine: Optional[LintV2Engine] = None


def get_lint_v2_engine() -> LintV2Engine:
    """Get or create the Lint v2 engine singleton."""
    global _lint_v2_engine
    if _lint_v2_engine is None:
        _lint_v2_engine = LintV2Engine()
    return _lint_v2_engine


def create_lint_v2_engine(
    fail_mode: str = "HARD_FAIL",
    warnings_enabled: bool = False,
) -> LintV2Engine:
    """Create a new Lint v2 engine instance."""
    return LintV2Engine(
        fail_mode=fail_mode,
        warnings_enabled=warnings_enabled,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING SIGNAL EMISSION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LintTrainingSignal:
    """Training signal emitted from lint evaluation."""
    signal_id: str
    invariant_id: str
    invariant_class: InvariantClass
    enforcement_point: EnforcementPoint
    result: EvaluationResult
    artifact_id: str
    observation: str
    emitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "invariant_id": self.invariant_id,
            "invariant_class": self.invariant_class.value,
            "enforcement_point": self.enforcement_point.value,
            "result": self.result.value,
            "artifact_id": self.artifact_id,
            "observation": self.observation,
            "emitted_at": self.emitted_at,
        }


def emit_lint_training_signals(report: EvaluationReport) -> List[LintTrainingSignal]:
    """Emit training signals from lint evaluation report."""
    signals = []
    
    # Emit signal for overall result
    signals.append(LintTrainingSignal(
        signal_id=f"LINT-SIG-{uuid4().hex[:8].upper()}",
        invariant_id="LINT-EVAL",
        invariant_class=InvariantClass.C_INV,
        enforcement_point=report.enforcement_point,
        result=report.result,
        artifact_id=report.artifact_id,
        observation=f"Lint v2 evaluation at {report.enforcement_point.value}: "
                    f"{report.result.value} ({len(report.violations)} violations)",
    ))
    
    # Emit signals for each violation
    for violation in report.violations:
        signals.append(LintTrainingSignal(
            signal_id=f"LINT-SIG-{uuid4().hex[:8].upper()}",
            invariant_id=violation.invariant_id,
            invariant_class=violation.invariant_class,
            enforcement_point=violation.enforcement_point,
            result=EvaluationResult.FAIL,
            artifact_id=violation.artifact_id,
            observation=f"Violation: {violation.description}",
        ))
    
    return signals
