# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Lint v2 — Platform-Wide Invariant Compiler & Runtime Enforcement
# PAC-JEFFREY-C16R: BER Formalization · P16 Agent Modularity (LAW)
# Supersedes: PAC-JEFFREY-P16 (EXECUTION OUTPUT ONLY)
# GOLD STANDARD · FAIL_CLOSED · BER FORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

"""
Lint v2 Platform-Wide Invariant Compiler — Runtime-Enforced Governance.

INVARIANT CLASSES (PAC-JEFFREY-P05R Block 5, C07R LOCKED):
- S-INV: Structural — Schema validation, required fields
- M-INV: Semantic — Meaning/intent validation
- X-INV: Cross-Artifact — Inter-document consistency
- T-INV: Temporal — Ordering, timestamps, sequences
- A-INV: Authority — GID/lane authorization
- F-INV: Finality — BER/settlement eligibility
- C-INV: Training — Signal emission compliance

PLATFORM INVARIANTS (PAC-JEFFREY-P10R Block 6):
- INV-LINT-PLAT-001: Runtime ACK REQUIRED
- INV-LINT-PLAT-002: Agent execution without ACK = ILLEGAL
- INV-LINT-PLAT-003: UI renders only lint-validated state
- INV-LINT-PLAT-004: API admission requires lint PASS
- INV-LINT-PLAT-005: Orchestration order deterministic

C16R EXECUTION MODEL (PAC-JEFFREY-C16R Block 2):
- Execution: NONE (CORRECTIVE · LAW)
- Automation Target: TRUE
- Binding Authority: JEFFREY (CTO)
- Fail Mode: HARD_FAIL
- Drift Tolerance: ZERO

C16R CHECKPOINT SEQUENCE (Block 5) — BER FORMALIZATION · 3 CHECKPOINTS:
1. BER_ADMISSION  → S-INV, A-INV
2. BER_REVIEW     → X-INV, C-INV
3. BER_FINALITY   → F-INV

C16R ACTIVATED AGENTS (Block 4) — 2 AGENTS · NON_EXECUTING:
- BENSON (GID-00) — orchestration · NON_EXECUTING
- ALEX (GID-08) — governance · NON_EXECUTING

C16R BER GOVERNANCE INVARIANTS (Block 6):
- INV-BER-016-01: execution_binding REQUIRED (explicit)
- INV-BER-016-02: ber_classification ∈ {PROVISIONAL, BINDING}
- INV-BER-016-03: ledger_commit_hash REQUIRED for BINDING
- INV-BER-016-04: settlement_effect ∈ {NONE, BINDING}
- INV-BER-016-05: reviewer_authority explicit
- INV-BER-016-06: training_signal REQUIRED
- INV-BER-016-07: positive_closure REQUIRED

C16R BER FINALITY (Block 9):
- ber_id: BER-PAC-JEFFREY-P16
- ber_classification: PROVISIONAL
- execution_binding: false
- ledger_commit_hash: null
- settlement_effect: NONE
- settlement: FORBIDDEN

C16R TRAINING SIGNAL (Block 10):
- TS-C16R-001: BER binding semantics must be explicit and lint-enforced

P16 EXECUTION MODEL (PAC-JEFFREY-P16 Block 2):
- Execution Model: PARALLEL
- Execution Barrier: AGENT_ACK_BARRIER
- Barrier Release: ALL_AGENT_ACKED
- Mixed Mode Execution: FORBIDDEN
- Fail Mode: HARD_FAIL
- Checkpoint Skip: FORBIDDEN
- Drift Tolerance: ZERO

P16 CHECKPOINT SEQUENCE (Block 5) — STRICT ORDER · NON-SKIPPABLE · 8 CHECKPOINTS:
1. PAC_ADMISSION        → S-INV, A-INV, T-INV
2. RUNTIME_ACTIVATION   → S-INV
3. RUNTIME_ACK          → A-INV
4. AGENT_ACTIVATION     → A-INV
5. AGENT_ACK_COLLECTION → A-INV
6. AGENT_EXECUTION      → M-INV
7. REVIEW_GATES         → X-INV, C-INV
8. BER_ELIGIBILITY      → F-INV

P16 OBJECTIVE (Block 1):
- Establish agent-type modularity under canonical governance "uniform"
- Prove non-software agents can be hot-swapped without governance degradation
- Outcome: Any compliant agent operates at identical determinism, auditability, finality

P16 ACTIVATED AGENTS (Block 4) — 8 AGENTS WITH SCOPES:
- BENSON (GID-00) — orchestration · execution control
- CODY (GID-01) — backend · system primitives
- SONNY (GID-02) — frontend · OC surfaces
- DAN (GID-07) — ci_cd · pipeline gates
- SAM (GID-06) — security · threat & controls
- ATLAS (GID-11) — repo_integrity · hygiene
- ALEX (GID-08) — governance · law & invariants
- PAX (GID-05) — product · constraint modeling

P16 BER (Block 8):
- Classification: PROVISIONAL
- execution_binding: false
- ledger_commit: FORBIDDEN
- settlement_effect: NONE

P16 TRAINING SIGNALS (Block 9):
- TS-P16-001: Agent-uniform decoupling validated
- TS-P16-002: Governance-first execution portability confirmed

SCHEMA REFERENCES (PINNED):
- pac_schema: CHAINBRIDGE_CANONICAL_PAC_SCHEMA@v1.0.0
- wrap_schema: CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v1.0.0
- ber_schema: CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0
- ack_schema: AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0
- rg_schema: RG01_SCHEMA@v1.0.0
- lint_schema: CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0

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
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

# CANONICAL IMPORT — gid_registry.py is the single source of truth
from core.governance.gid_registry import (
    get_registry as get_canonical_registry,
    UnknownGIDError,
)

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
# P11R EXECUTION MODEL — OPTION A (PAC-JEFFREY-P11R Block 2-5)
# ═══════════════════════════════════════════════════════════════════════════════
# Execution Model: PARALLEL
# Execution Barrier: AGENT_ACK_BARRIER
# Barrier Release: ALL_AGENT_ACKED
# Fail Mode: HARD_FAIL
# Checkpoint Skip: FORBIDDEN
# Drift Tolerance: ZERO

class P11RExecutionModel(str, Enum):
    """P11R Execution Models per Block 2."""
    PARALLEL = "PARALLEL"
    SEQUENTIAL = "SEQUENTIAL"


class P11RBarrierType(str, Enum):
    """P11R Barrier Types per Block 2."""
    AGENT_ACK_BARRIER = "AGENT_ACK_BARRIER"
    RUNTIME_ACK_BARRIER = "RUNTIME_ACK_BARRIER"
    WRAP_BARRIER = "WRAP_BARRIER"


class P11RBarrierRelease(str, Enum):
    """P11R Barrier Release Conditions per Block 2."""
    ALL_AGENT_ACKED = "ALL_AGENT_ACKED"
    RUNTIME_ACKED = "RUNTIME_ACKED"
    ALL_WRAPS_PRESENT = "ALL_WRAPS_PRESENT"


@dataclass
class RuntimeActivationACK:
    """
    Runtime Activation ACK per PAC-JEFFREY-P11R Block 3.
    
    REQUIRED before any agent execution.
    Missing ACK → HARD_FAIL
    """
    ack_id: str = field(default_factory=lambda: f"RUNTIME-ACK-{uuid4().hex[:8].upper()}")
    pac_id: str = ""
    schema_validation_enabled: bool = False
    invariant_registry_loaded: bool = False
    lint_engine_ready: bool = False
    runtime_ack_enforced: bool = False
    deterministic_execution_order: bool = False
    fail_closed_enabled: bool = False
    acked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def is_valid(self) -> bool:
        """ALL activation checks REQUIRED per P11R Block 3."""
        return all([
            self.schema_validation_enabled,
            self.invariant_registry_loaded,
            self.lint_engine_ready,
            self.runtime_ack_enforced,
            self.deterministic_execution_order,
            self.fail_closed_enabled,
        ])
    
    def get_missing_checks(self) -> List[str]:
        """Get list of missing activation checks."""
        missing = []
        if not self.schema_validation_enabled:
            missing.append("schema_validation_enabled")
        if not self.invariant_registry_loaded:
            missing.append("invariant_registry_loaded")
        if not self.lint_engine_ready:
            missing.append("lint_engine_ready")
        if not self.runtime_ack_enforced:
            missing.append("runtime_ack_enforced")
        if not self.deterministic_execution_order:
            missing.append("deterministic_execution_order")
        if not self.fail_closed_enabled:
            missing.append("fail_closed_enabled")
        return missing
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ack_id": self.ack_id,
            "pac_id": self.pac_id,
            "schema_validation_enabled": self.schema_validation_enabled,
            "invariant_registry_loaded": self.invariant_registry_loaded,
            "lint_engine_ready": self.lint_engine_ready,
            "runtime_ack_enforced": self.runtime_ack_enforced,
            "deterministic_execution_order": self.deterministic_execution_order,
            "fail_closed_enabled": self.fail_closed_enabled,
            "is_valid": self.is_valid(),
            "missing_checks": self.get_missing_checks(),
            "acked_at": self.acked_at,
        }


@dataclass
class AgentActivationACK:
    """
    Agent Activation ACK per PAC-JEFFREY-P12 Block 5.
    
    Explicit ACK REQUIRED per agent before execution.
    No execution before ACK.
    No undeclared agents permitted.
    
    P12 Enhanced Evidence Fields:
    - latency_ms: ACK response latency
    - authorization_scope: Agent's authorized scope
    - evidence_hash: SHA-256 hash of ACK evidence
    
    Schema: AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0
    """
    ack_id: str = field(default_factory=lambda: f"AGENT-ACK-{uuid4().hex[:8].upper()}")
    pac_id: str = ""
    gid: str = ""
    agent_name: str = ""
    lane: str = ""
    activated: bool = False
    acked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # P12 Enhanced Evidence Fields (Block 5)
    latency_ms: int = 0
    authorization_scope: str = ""  # e.g., "full", "code", "ui", "gates", "review", "hygiene", "law", "constraints"
    evidence_hash: str = field(default_factory=lambda: "")
    
    def compute_evidence_hash(self) -> str:
        """Compute SHA-256 hash of ACK evidence."""
        evidence_data = f"{self.ack_id}:{self.pac_id}:{self.gid}:{self.agent_name}:{self.lane}:{self.acked_at}"
        return hashlib.sha256(evidence_data.encode()).hexdigest()[:16]
    
    def __post_init__(self) -> None:
        """Auto-compute evidence hash if not provided."""
        if not self.evidence_hash:
            self.evidence_hash = self.compute_evidence_hash()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ack_id": self.ack_id,
            "pac_id": self.pac_id,
            "gid": self.gid,
            "agent_name": self.agent_name,
            "lane": self.lane,
            "activated": self.activated,
            "acked_at": self.acked_at,
            "latency_ms": self.latency_ms,
            "authorization_scope": self.authorization_scope,
            "evidence_hash": self.evidence_hash,
        }


@dataclass
class P11RAgentACKBarrier:
    """
    Agent ACK Barrier per PAC-JEFFREY-P11R Block 4.
    
    Barrier Release: ALL_AGENT_ACKED
    Missing ACK → HARD_FAIL
    """
    barrier_id: str = field(default_factory=lambda: f"BARRIER-{uuid4().hex[:8].upper()}")
    pac_id: str = ""
    required_agents: List[str] = field(default_factory=list)  # List of GIDs
    received_acks: Dict[str, AgentActivationACK] = field(default_factory=dict)
    barrier_type: P11RBarrierType = P11RBarrierType.AGENT_ACK_BARRIER
    release_condition: P11RBarrierRelease = P11RBarrierRelease.ALL_AGENT_ACKED
    released: bool = False
    released_at: Optional[str] = None
    
    def add_ack(self, ack: AgentActivationACK) -> None:
        """Add agent ACK to barrier."""
        if ack.gid in self.required_agents:
            self.received_acks[ack.gid] = ack
            self._check_release()
    
    def _check_release(self) -> None:
        """Check if barrier release condition is met."""
        if self.release_condition == P11RBarrierRelease.ALL_AGENT_ACKED:
            if all(gid in self.received_acks for gid in self.required_agents):
                self.released = True
                self.released_at = datetime.now(timezone.utc).isoformat()
    
    def get_missing_acks(self) -> List[str]:
        """Get list of agents that haven't ACKed."""
        return [gid for gid in self.required_agents if gid not in self.received_acks]
    
    def is_released(self) -> bool:
        """Check if barrier is released."""
        return self.released
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "barrier_id": self.barrier_id,
            "pac_id": self.pac_id,
            "required_agents": self.required_agents,
            "received_acks": {gid: ack.to_dict() for gid, ack in self.received_acks.items()},
            "barrier_type": self.barrier_type.value,
            "release_condition": self.release_condition.value,
            "released": self.released,
            "released_at": self.released_at,
            "missing_acks": self.get_missing_acks(),
        }


# P11R Checkpoint Sequence (Block 5) — STRICT ORDER · NON-SKIPPABLE
P11R_CHECKPOINT_SEQUENCE: List[str] = [
    "PAC_ADMISSION",
    "RUNTIME_ACTIVATION",
    "RUNTIME_ACK_COLLECTION",
    "AGENT_ACTIVATION",
    "AGENT_ACK_COLLECTION",
    "AGENT_EXECUTION",
    "REVIEW_GATES",
    "BER_ELIGIBILITY",
]


# ═══════════════════════════════════════════════════════════════════════════════
# P12 CHECKPOINT SEQUENCE & INVARIANT MAPPING (PAC-JEFFREY-P12 Block 6)
# ═══════════════════════════════════════════════════════════════════════════════

# P12 Checkpoint Sequence (Block 6) — STRICT ORDER · NON-SKIPPABLE
P12_CHECKPOINT_SEQUENCE: List[str] = [
    "PAC_ADMISSION",
    "RUNTIME_ACTIVATION",
    "RUNTIME_ACK",
    "AGENT_ACTIVATION",
    "AGENT_EXECUTION",
    "REVIEW_GATES",
    "BER_ELIGIBILITY",
    "FINALITY_SEAL",
]

# P12 Checkpoint → Invariant Class Mapping (Block 6)
P12_CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    "PAC_ADMISSION": ["S-INV", "A-INV", "T-INV"],
    "RUNTIME_ACTIVATION": ["S-INV"],
    "RUNTIME_ACK": ["A-INV"],
    "AGENT_ACTIVATION": ["A-INV"],
    "AGENT_EXECUTION": ["M-INV"],
    "REVIEW_GATES": ["X-INV", "C-INV"],
    "BER_ELIGIBILITY": ["F-INV"],
    "FINALITY_SEAL": ["F-INV"],
}


def get_p12_required_invariants(checkpoint: str) -> List[str]:
    """Get required invariant classes for a P12 checkpoint."""
    return P12_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, [])


def validate_p12_checkpoint_invariants(
    checkpoint: str, evaluated_classes: Set[str]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required invariant classes were evaluated at P12 checkpoint.
    
    Returns:
        (success, error_message)
    """
    required = set(P12_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, []))
    missing = required - evaluated_classes
    if missing:
        return False, f"P12 checkpoint {checkpoint} missing invariants: {missing}"
    return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# P13 CHECKPOINT SEQUENCE & INVARIANT MAPPING (PAC-JEFFREY-P13 Block 5)
# ═══════════════════════════════════════════════════════════════════════════════

# P13 Checkpoint Sequence (Block 5) — STRICT ORDER · NON-SKIPPABLE
P13_CHECKPOINT_SEQUENCE: List[str] = [
    "PAC_ADMISSION",
    "RUNTIME_ACTIVATION",
    "RUNTIME_ACK",
    "AGENT_ACTIVATION",
    "AGENT_ACK_COLLECTION",  # P13 addition: explicit ACK collection checkpoint
    "AGENT_EXECUTION",
    "REVIEW_GATES",
    "BER_ELIGIBILITY",
]

# P13 Checkpoint → Invariant Class Mapping (Block 5)
P13_CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    "PAC_ADMISSION": ["S-INV", "A-INV", "T-INV"],
    "RUNTIME_ACTIVATION": ["S-INV"],
    "RUNTIME_ACK": ["A-INV"],
    "AGENT_ACTIVATION": ["A-INV"],
    "AGENT_ACK_COLLECTION": ["A-INV"],  # P13: ACK collection authority validation
    "AGENT_EXECUTION": ["M-INV"],
    "REVIEW_GATES": ["X-INV", "C-INV"],
    "BER_ELIGIBILITY": ["F-INV"],
}


def get_p13_required_invariants(checkpoint: str) -> List[str]:
    """Get required invariant classes for a P13 checkpoint."""
    return P13_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, [])


def validate_p13_checkpoint_invariants(
    checkpoint: str, evaluated_classes: Set[str]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required invariant classes were evaluated at P13 checkpoint.
    
    Returns:
        (success, error_message)
    """
    required = set(P13_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, []))
    missing = required - evaluated_classes
    if missing:
        return False, f"P13 checkpoint {checkpoint} missing invariants: {missing}"
    return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# P14R CHECKPOINT SEQUENCE & INVARIANT MAPPING (PAC-JEFFREY-P14R Block 5)
# BINDING SETTLEMENT · 9 CHECKPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

# P14R Checkpoint Sequence (Block 5) — STRICT ORDER · NON-SKIPPABLE · 9 CHECKPOINTS
P14R_CHECKPOINT_SEQUENCE: List[str] = [
    "PAC_ADMISSION",
    "RUNTIME_ACTIVATION",
    "RUNTIME_ACK",
    "AGENT_ACTIVATION",
    "AGENT_ACK_COLLECTION",
    "AGENT_EXECUTION",
    "REVIEW_GATES",
    "LEDGER_COMMIT",    # P14R ADDITION: Binding settlement requires ledger commit
    "FINALITY_SEAL",
]

# P14R Checkpoint → Invariant Class Mapping (Block 5)
P14R_CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    "PAC_ADMISSION": ["S-INV", "A-INV", "T-INV"],
    "RUNTIME_ACTIVATION": ["S-INV"],
    "RUNTIME_ACK": ["A-INV"],
    "AGENT_ACTIVATION": ["A-INV"],
    "AGENT_ACK_COLLECTION": ["A-INV"],
    "AGENT_EXECUTION": ["M-INV"],
    "REVIEW_GATES": ["X-INV", "C-INV"],
    "LEDGER_COMMIT": ["F-INV"],     # P14R: Ledger commit requires finality validation
    "FINALITY_SEAL": ["F-INV"],
}

# P14R BER Governance Invariants (Block 6) — LOCKED
P14R_BER_GOVERNANCE_INVARIANTS: List[str] = [
    "INV-BER-001",  # execution_binding REQUIRED
    "INV-BER-002",  # ledger_commit_hash REQUIRED
    "INV-BER-003",  # settlement_effect REQUIRED
    "INV-BER-004",  # reviewer_authority REQUIRED
    "INV-BER-005",  # training_signals REQUIRED
    "INV-BER-006",  # positive_closure REQUIRED
]


def get_p14r_required_invariants(checkpoint: str) -> List[str]:
    """Get required invariant classes for a P14R checkpoint."""
    return P14R_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, [])


def validate_p14r_checkpoint_invariants(
    checkpoint: str, evaluated_classes: Set[str]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required invariant classes were evaluated at P14R checkpoint.
    
    Returns:
        (success, error_message)
    """
    required = set(P14R_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, []))
    missing = required - evaluated_classes
    if missing:
        return False, f"P14R checkpoint {checkpoint} missing invariants: {missing}"
    return True, None


class P14RBERClassification(str, Enum):
    """BER Classification per P14R Block 9 — BINDING."""
    FINAL = "FINAL"          # P14R: Full binding settlement
    PROVISIONAL = "PROVISIONAL"  # Fallback (should not be used in P14R)


@dataclass
class P14RBERStatus:
    """
    BER Status per PAC-JEFFREY-P14R Block 9 — BINDING SETTLEMENT.
    
    P14R BER is FINAL (BINDING).
    execution_binding = TRUE
    ledger_commit_hash = REQUIRED
    settlement_effect = BINDING
    """
    ber_id: str = field(default_factory=lambda: f"BER-P14R-{uuid4().hex[:8].upper()}")
    pac_id: str = "PAC-JEFFREY-P14R"
    classification: P14RBERClassification = P14RBERClassification.FINAL
    execution_binding: bool = True
    ledger_commit_hash: str = ""  # REQUIRED for P14R
    settlement_effect: str = "BINDING"
    reviewer_authority: str = ""  # INV-BER-004
    training_signals_present: bool = False  # INV-BER-005
    positive_closure: bool = False  # INV-BER-006
    finalized_at: str = ""
    
    def is_valid_for_finality(self) -> Tuple[bool, List[str]]:
        """Validate P14R BER meets all governance invariants."""
        issues = []
        
        if not self.execution_binding:
            issues.append("INV-BER-001: execution_binding must be TRUE")
        if not self.ledger_commit_hash:
            issues.append("INV-BER-002: ledger_commit_hash REQUIRED")
        if self.settlement_effect != "BINDING":
            issues.append("INV-BER-003: settlement_effect must be BINDING")
        if not self.reviewer_authority:
            issues.append("INV-BER-004: reviewer_authority REQUIRED")
        if not self.training_signals_present:
            issues.append("INV-BER-005: training_signals REQUIRED")
        if not self.positive_closure:
            issues.append("INV-BER-006: positive_closure REQUIRED")
        
        return len(issues) == 0, issues
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ber_id": self.ber_id,
            "pac_id": self.pac_id,
            "classification": self.classification.value,
            "execution_binding": self.execution_binding,
            "ledger_commit_hash": self.ledger_commit_hash,
            "settlement_effect": self.settlement_effect,
            "reviewer_authority": self.reviewer_authority,
            "training_signals_present": self.training_signals_present,
            "positive_closure": self.positive_closure,
            "finalized_at": self.finalized_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# P15R CHECKPOINT SEQUENCE & INVARIANT MAPPING (PAC-JEFFREY-P15R Block 5)
# GOVERNANCE SATURATION · 10 CHECKPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

# P15R Checkpoint Sequence (Block 5) — STRICT ORDER · NON-SKIPPABLE · 10 CHECKPOINTS
P15R_CHECKPOINT_SEQUENCE: List[str] = [
    "PAC_ADMISSION",
    "RUNTIME_ACTIVATION",
    "RUNTIME_ACK_COLLECTION",  # P15R: Explicit runtime ACK collection
    "AGENT_ACTIVATION",
    "AGENT_ACK_COLLECTION",
    "AGENT_EXECUTION",
    "REVIEW_GATES",
    "BER_ELIGIBILITY",          # P15R: BER eligibility before commit
    "LEDGER_COMMIT",
    "FINALITY_SEAL",
]

# P15R Checkpoint → Invariant Class Mapping (Block 5)
P15R_CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    "PAC_ADMISSION": ["S-INV", "A-INV", "T-INV"],
    "RUNTIME_ACTIVATION": ["S-INV"],
    "RUNTIME_ACK_COLLECTION": ["A-INV"],
    "AGENT_ACTIVATION": ["A-INV"],
    "AGENT_ACK_COLLECTION": ["A-INV"],
    "AGENT_EXECUTION": ["M-INV"],
    "REVIEW_GATES": ["X-INV", "C-INV"],
    "BER_ELIGIBILITY": ["F-INV"],
    "LEDGER_COMMIT": ["F-INV"],
    "FINALITY_SEAL": ["F-INV"],
}

# P15R Governance Saturation Scope (Block 1)
P15R_GOVERNANCE_SATURATION_SCOPE: List[str] = [
    "control_plane",
    "governance_engine",
    "lint_v2_compiler",
    "runtime_admission",
    "operator_console",
    "api_routers",
    "ber_settlement",
]

# P15R Runtime Activation Requirements (Block 3) — ALL REQUIRED TRUE
P15R_RUNTIME_ACTIVATION_REQUIREMENTS: List[str] = [
    "schema_validation_enabled",
    "invariant_registry_loaded",
    "lint_v2_compiler_active",
    "runtime_ack_enforced",
    "agent_ack_enforced",
    "deterministic_execution_order",
    "fail_closed_enabled",
]


def get_p15r_required_invariants(checkpoint: str) -> List[str]:
    """Get required invariant classes for a P15R checkpoint."""
    return P15R_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, [])


def validate_p15r_checkpoint_invariants(
    checkpoint: str, evaluated_classes: Set[str]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required invariant classes were evaluated at P15R checkpoint.
    
    Returns:
        (success, error_message)
    """
    required = set(P15R_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, []))
    missing = required - evaluated_classes
    if missing:
        return False, f"P15R checkpoint {checkpoint} missing invariants: {missing}"
    return True, None


def validate_p15r_governance_saturation(
    covered_scopes: Set[str]
) -> Tuple[bool, List[str]]:
    """
    Validate P15R governance saturation across all required scopes.
    
    Returns:
        (saturated, missing_scopes)
    """
    required = set(P15R_GOVERNANCE_SATURATION_SCOPE)
    missing = required - covered_scopes
    return len(missing) == 0, list(missing)


# ═══════════════════════════════════════════════════════════════════════════════
# P16 CHECKPOINT SEQUENCE & AGENT MODULARITY (PAC-JEFFREY-P16 Block 5)
# AGENT MODULARITY & UNIFORMIZATION · 8 CHECKPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

# P16 Checkpoint Sequence (Block 5) — STRICT ORDER · NON-SKIPPABLE · 8 CHECKPOINTS
P16_CHECKPOINT_SEQUENCE: List[str] = [
    "PAC_ADMISSION",
    "RUNTIME_ACTIVATION",
    "RUNTIME_ACK",
    "AGENT_ACTIVATION",
    "AGENT_ACK_COLLECTION",
    "AGENT_EXECUTION",
    "REVIEW_GATES",
    "BER_ELIGIBILITY",
]

# P16 Checkpoint → Invariant Class Mapping (Block 5)
P16_CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    "PAC_ADMISSION": ["S-INV", "A-INV", "T-INV"],
    "RUNTIME_ACTIVATION": ["S-INV"],
    "RUNTIME_ACK": ["A-INV"],
    "AGENT_ACTIVATION": ["A-INV"],
    "AGENT_ACK_COLLECTION": ["A-INV"],
    "AGENT_EXECUTION": ["M-INV"],
    "REVIEW_GATES": ["X-INV", "C-INV"],
    "BER_ELIGIBILITY": ["F-INV"],
}

# P16 Agent Scopes (Block 4) — Canonical Agent "Uniform"
P16_AGENT_SCOPES: Dict[str, str] = {
    "GID-00": "execution_control",      # BENSON · orchestration
    "GID-01": "system_primitives",      # CODY · backend
    "GID-02": "oc_surfaces",            # SONNY · frontend
    "GID-07": "pipeline_gates",         # DAN · ci_cd
    "GID-06": "threat_controls",        # SAM · security
    "GID-11": "hygiene",                # ATLAS · repo_integrity
    "GID-08": "law_invariants",         # ALEX · governance
    "GID-05": "constraint_modeling",    # PAX · product
}

# P16 Training Signals (Block 9)
P16_TRAINING_SIGNALS: List[str] = [
    "TS-P16-001",  # Agent-uniform decoupling validated
    "TS-P16-002",  # Governance-first execution portability confirmed
]

# P16 Agent Modularity Invariants (Block 1)
P16_MODULARITY_INVARIANTS: List[str] = [
    "INV-MOD-001",  # Agent-type modularity under canonical governance uniform
    "INV-MOD-002",  # Hot-swap without governance degradation
    "INV-MOD-003",  # Identical determinism across agent types
    "INV-MOD-004",  # Identical auditability across agent types
    "INV-MOD-005",  # Identical finality across agent types
]


def get_p16_required_invariants(checkpoint: str) -> List[str]:
    """Get required invariant classes for a P16 checkpoint."""
    return P16_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, [])


def validate_p16_checkpoint_invariants(
    checkpoint: str, evaluated_classes: Set[str]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required invariant classes were evaluated at P16 checkpoint.
    
    Returns:
        (success, error_message)
    """
    required = set(P16_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, []))
    missing = required - evaluated_classes
    if missing:
        return False, f"P16 checkpoint {checkpoint} missing invariants: {missing}"
    return True, None


def validate_p16_agent_modularity(
    agent_gid: str, scope: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate agent scope matches P16 canonical agent uniform.
    
    Returns:
        (valid, error_message)
    """
    expected_scope = P16_AGENT_SCOPES.get(agent_gid)
    if expected_scope is None:
        return False, f"Unknown agent GID: {agent_gid}"
    if scope != expected_scope:
        return False, f"Agent {agent_gid} scope mismatch: expected {expected_scope}, got {scope}"
    return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# C16R BER FORMALIZATION (PAC-JEFFREY-C16R Blocks 5-10)
# CORRECTIVE · LAW · NON_EXECUTING · BER-GRADE ARTIFACT
# ═══════════════════════════════════════════════════════════════════════════════

# C16R Checkpoint Sequence (Block 5) — BER FORMALIZATION · 3 CHECKPOINTS
C16R_CHECKPOINT_SEQUENCE: List[str] = [
    "BER_ADMISSION",
    "BER_REVIEW",
    "BER_FINALITY",
]

# C16R Checkpoint → Invariant Class Mapping (Block 5)
C16R_CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    "BER_ADMISSION": ["S-INV", "A-INV"],
    "BER_REVIEW": ["X-INV", "C-INV"],
    "BER_FINALITY": ["F-INV"],
}

# C16R BER Governance Invariants (Block 6)
C16R_BER_GOVERNANCE_INVARIANTS: List[str] = [
    "INV-BER-016-01",  # execution_binding REQUIRED (explicit)
    "INV-BER-016-02",  # ber_classification ∈ {PROVISIONAL, BINDING}
    "INV-BER-016-03",  # ledger_commit_hash REQUIRED for BINDING
    "INV-BER-016-04",  # settlement_effect ∈ {NONE, BINDING}
    "INV-BER-016-05",  # reviewer_authority explicit
    "INV-BER-016-06",  # training_signal REQUIRED
    "INV-BER-016-07",  # positive_closure REQUIRED
]

# C16R Required WRAPs (Block 7) — 2 AGENTS (NON_EXECUTING)
C16R_REQUIRED_WRAPS: List[str] = [
    "WRAP-BENSON-GID00-PAC-JEFFREY-C16R",
    "WRAP-ALEX-GID08-PAC-JEFFREY-C16R",
]

# C16R Activated Agents (Block 4) — 2 AGENTS (NON_EXECUTING)
C16R_ACTIVATED_AGENTS: List[str] = [
    "GID-00",  # BENSON · orchestration · NON_EXECUTING
    "GID-08",  # ALEX · governance · NON_EXECUTING
]

# C16R Review Gates (Block 8) — RG-01 REQUIREMENTS
C16R_REVIEW_GATES: List[str] = [
    "structural_conformance",
    "authority_validation",
    "cross_artifact_lineage",
    "invariant_pass",
    "training_signal_present",
]

# C16R Training Signal (Block 10)
C16R_TRAINING_SIGNALS: List[str] = [
    "TS-C16R-001",  # BER binding semantics must be explicit and lint-enforced
]

# C16R Positive Closure (Block 10)
C16R_POSITIVE_CLOSURE: Dict[str, bool] = {
    "pac_received": True,
    "all_blocks_present": True,
    "no_execution_performed": True,
    "ber_formalized": True,
    "zero_drift_confirmed": True,
}


@dataclass
class C16RBERFinality:
    """
    C16R BER Finality Declaration (Block 9).
    
    Formalizes PAC-JEFFREY-P16 into BER-grade artifact with explicit
    execution binding, finality, and settlement semantics.
    """
    ber_id: str = "BER-PAC-JEFFREY-P16"
    ber_classification: str = "PROVISIONAL"
    execution_binding: bool = False
    ledger_commit_hash: Optional[str] = None
    settlement_effect: str = "NONE"
    settlement: str = "FORBIDDEN"


def get_c16r_required_invariants(checkpoint: str) -> List[str]:
    """Get required invariant classes for a C16R checkpoint."""
    return C16R_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, [])


def validate_c16r_checkpoint_invariants(
    checkpoint: str, evaluated_classes: Set[str]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required invariant classes were evaluated at C16R checkpoint.
    
    Returns:
        (success, error_message)
    """
    required = set(C16R_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, []))
    missing = required - evaluated_classes
    if missing:
        return False, f"C16R checkpoint {checkpoint} missing invariants: {missing}"
    return True, None


def validate_c16r_positive_closure() -> Tuple[bool, List[str]]:
    """
    Validate C16R positive closure requirements.
    
    Returns:
        (all_satisfied, missing_requirements)
    """
    missing = [k for k, v in C16R_POSITIVE_CLOSURE.items() if not v]
    return len(missing) == 0, missing


@dataclass
class P11RCheckpointTracker:
    """
    Checkpoint Tracker per PAC-JEFFREY-P11R Block 5.
    
    Enforces strict checkpoint order.
    Out-of-order execution → HARD_FAIL
    """
    tracker_id: str = field(default_factory=lambda: f"TRACK-{uuid4().hex[:8].upper()}")
    pac_id: str = ""
    completed_checkpoints: List[str] = field(default_factory=list)
    current_checkpoint_index: int = 0
    
    def get_next_checkpoint(self) -> Optional[str]:
        """Get next expected checkpoint."""
        if self.current_checkpoint_index < len(P11R_CHECKPOINT_SEQUENCE):
            return P11R_CHECKPOINT_SEQUENCE[self.current_checkpoint_index]
        return None
    
    def complete_checkpoint(self, checkpoint: str) -> Tuple[bool, Optional[str]]:
        """
        Complete a checkpoint.
        
        Returns:
            (success, error_message)
        """
        expected = self.get_next_checkpoint()
        if expected is None:
            return False, "All checkpoints already completed"
        if checkpoint != expected:
            return False, f"Out-of-order checkpoint: expected {expected}, got {checkpoint}"
        
        self.completed_checkpoints.append(checkpoint)
        self.current_checkpoint_index += 1
        return True, None
    
    def is_complete(self) -> bool:
        """Check if all checkpoints completed."""
        return len(self.completed_checkpoints) == len(P11R_CHECKPOINT_SEQUENCE)
    
    def get_remaining_checkpoints(self) -> List[str]:
        """Get list of remaining checkpoints."""
        return P11R_CHECKPOINT_SEQUENCE[self.current_checkpoint_index:]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tracker_id": self.tracker_id,
            "pac_id": self.pac_id,
            "completed_checkpoints": self.completed_checkpoints,
            "current_checkpoint_index": self.current_checkpoint_index,
            "next_checkpoint": self.get_next_checkpoint(),
            "is_complete": self.is_complete(),
            "remaining_checkpoints": self.get_remaining_checkpoints(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# P11R WRAP VALIDATION (PAC-JEFFREY-P11R Block 7)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class P11RWrapRequirement:
    """
    WRAP Requirement per PAC-JEFFREY-P11R Block 7.
    
    All WRAPs MANDATORY.
    Missing WRAP → HARD_FAIL
    """
    pac_id: str = ""
    required_wraps: List[str] = field(default_factory=list)
    received_wraps: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def add_wrap(self, wrap_id: str, wrap_data: Dict[str, Any]) -> None:
        """Add received WRAP."""
        self.received_wraps[wrap_id] = wrap_data
    
    def get_missing_wraps(self) -> List[str]:
        """Get list of missing WRAPs."""
        return [w for w in self.required_wraps if w not in self.received_wraps]
    
    def is_complete(self) -> bool:
        """Check if all required WRAPs received."""
        return all(w in self.received_wraps for w in self.required_wraps)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pac_id": self.pac_id,
            "required_wraps": self.required_wraps,
            "received_wraps": list(self.received_wraps.keys()),
            "missing_wraps": self.get_missing_wraps(),
            "is_complete": self.is_complete(),
        }


# P11R Required WRAPs per Block 7
P11R_REQUIRED_WRAPS: List[str] = [
    "WRAP-BENSON-GID00-PAC-JEFFREY-P11R",
    "WRAP-CODY-GID01-PAC-JEFFREY-P11R",
    "WRAP-SONNY-GID02-PAC-JEFFREY-P11R",
    "WRAP-DAN-GID07-PAC-JEFFREY-P11R",
    "WRAP-SAM-GID06-PAC-JEFFREY-P11R",
    "WRAP-ATLAS-GID11-PAC-JEFFREY-P11R",
    "WRAP-ALEX-GID08-PAC-JEFFREY-P11R",
]

# P12 Required WRAPs per Block 7 — 8 AGENTS (includes PAX)
P12_REQUIRED_WRAPS: List[str] = [
    "WRAP-BENSON-GID00-PAC-JEFFREY-P12",
    "WRAP-CODY-GID01-PAC-JEFFREY-P12",
    "WRAP-SONNY-GID02-PAC-JEFFREY-P12",
    "WRAP-DAN-GID07-PAC-JEFFREY-P12",
    "WRAP-SAM-GID06-PAC-JEFFREY-P12",
    "WRAP-ATLAS-GID11-PAC-JEFFREY-P12",
    "WRAP-ALEX-GID08-PAC-JEFFREY-P12",
    "WRAP-PAX-GID05-PAC-JEFFREY-P12",
]

# P13 Required WRAPs per Block 7 — 8 AGENTS
P13_REQUIRED_WRAPS: List[str] = [
    "WRAP-BENSON-GID00-PAC-JEFFREY-P13",
    "WRAP-CODY-GID01-PAC-JEFFREY-P13",
    "WRAP-SONNY-GID02-PAC-JEFFREY-P13",
    "WRAP-DAN-GID07-PAC-JEFFREY-P13",
    "WRAP-SAM-GID06-PAC-JEFFREY-P13",
    "WRAP-ATLAS-GID11-PAC-JEFFREY-P13",
    "WRAP-ALEX-GID08-PAC-JEFFREY-P13",
    "WRAP-PAX-GID05-PAC-JEFFREY-P13",
]

# P13 Activated Agents (Block 4) — 8 AGENTS
P13_ACTIVATED_AGENTS: List[str] = [
    "GID-00",  # BENSON · orchestration · EXECUTING
    "GID-01",  # CODY · backend · EXECUTING
    "GID-02",  # SONNY · frontend · EXECUTING
    "GID-07",  # DAN · ci_cd · EXECUTING
    "GID-06",  # SAM · security · EXECUTING
    "GID-11",  # ATLAS · repo_integrity · EXECUTING
    "GID-08",  # ALEX · governance · EXECUTING
    "GID-05",  # PAX · product · EXECUTING
]

# P14R Required WRAPs per Block 7 — 8 AGENTS (BINDING SETTLEMENT)
P14R_REQUIRED_WRAPS: List[str] = [
    "WRAP-BENSON-GID00-PAC-JEFFREY-P14R",
    "WRAP-CODY-GID01-PAC-JEFFREY-P14R",
    "WRAP-SONNY-GID02-PAC-JEFFREY-P14R",
    "WRAP-DAN-GID07-PAC-JEFFREY-P14R",
    "WRAP-SAM-GID06-PAC-JEFFREY-P14R",
    "WRAP-ATLAS-GID11-PAC-JEFFREY-P14R",
    "WRAP-ALEX-GID08-PAC-JEFFREY-P14R",
    "WRAP-PAX-GID05-PAC-JEFFREY-P14R",
]

# P14R Activated Agents (Block 4) — 8 AGENTS (BINDING SETTLEMENT)
P14R_ACTIVATED_AGENTS: List[str] = [
    "GID-00",  # BENSON · orchestration · EXECUTING
    "GID-01",  # CODY · backend · EXECUTING
    "GID-02",  # SONNY · frontend · EXECUTING
    "GID-07",  # DAN · ci_cd · EXECUTING
    "GID-06",  # SAM · security · EXECUTING
    "GID-11",  # ATLAS · repo_integrity · EXECUTING
    "GID-08",  # ALEX · governance · EXECUTING
    "GID-05",  # PAX · product · EXECUTING
]

# P15R Required WRAPs per Block 7 — 8 AGENTS (GOVERNANCE SATURATION)
P15R_REQUIRED_WRAPS: List[str] = [
    "WRAP-BENSON-GID00-PAC-JEFFREY-P15R",
    "WRAP-CODY-GID01-PAC-JEFFREY-P15R",
    "WRAP-SONNY-GID02-PAC-JEFFREY-P15R",
    "WRAP-DAN-GID07-PAC-JEFFREY-P15R",
    "WRAP-SAM-GID06-PAC-JEFFREY-P15R",
    "WRAP-ATLAS-GID11-PAC-JEFFREY-P15R",
    "WRAP-ALEX-GID08-PAC-JEFFREY-P15R",
    "WRAP-PAX-GID05-PAC-JEFFREY-P15R",
]

# P15R Activated Agents (Block 4) — 8 AGENTS (GOVERNANCE SATURATION)
P15R_ACTIVATED_AGENTS: List[str] = [
    "GID-00",  # BENSON · orchestration · EXECUTING
    "GID-01",  # CODY · backend · EXECUTING
    "GID-02",  # SONNY · frontend · EXECUTING
    "GID-07",  # DAN · ci_cd · EXECUTING
    "GID-06",  # SAM · security · EXECUTING
    "GID-11",  # ATLAS · repo_integrity · EXECUTING
    "GID-08",  # ALEX · governance · EXECUTING
    "GID-05",  # PAX · product · EXECUTING
]

# P16 Required WRAPs per Block 7 — 8 AGENTS (AGENT MODULARITY)
P16_REQUIRED_WRAPS: List[str] = [
    "WRAP-BENSON-GID00-PAC-JEFFREY-P16",
    "WRAP-CODY-GID01-PAC-JEFFREY-P16",
    "WRAP-SONNY-GID02-PAC-JEFFREY-P16",
    "WRAP-DAN-GID07-PAC-JEFFREY-P16",
    "WRAP-SAM-GID06-PAC-JEFFREY-P16",
    "WRAP-ATLAS-GID11-PAC-JEFFREY-P16",
    "WRAP-ALEX-GID08-PAC-JEFFREY-P16",
    "WRAP-PAX-GID05-PAC-JEFFREY-P16",
]

# P16 Activated Agents (Block 4) — 8 AGENTS (AGENT MODULARITY)
P16_ACTIVATED_AGENTS: List[str] = [
    "GID-00",  # BENSON · orchestration · execution_control
    "GID-01",  # CODY · backend · system_primitives
    "GID-02",  # SONNY · frontend · oc_surfaces
    "GID-07",  # DAN · ci_cd · pipeline_gates
    "GID-06",  # SAM · security · threat_controls
    "GID-11",  # ATLAS · repo_integrity · hygiene
    "GID-08",  # ALEX · governance · law_invariants
    "GID-05",  # PAX · product · constraint_modeling
]

# P12 Activated Agents (Block 4) — 8 AGENTS
P12_ACTIVATED_AGENTS: List[str] = [
    "GID-00",  # BENSON · orchestration · full
    "GID-01",  # CODY · backend · code
    "GID-02",  # SONNY · frontend · ui
    "GID-07",  # DAN · ci_cd · gates
    "GID-06",  # SAM · security · review
    "GID-11",  # ATLAS · repo_integrity · hygiene
    "GID-08",  # ALEX · governance · law
    "GID-05",  # PAX · product · constraints
]

# P12 Agent Authorization Scopes (Block 4)
P12_AGENT_SCOPES: Dict[str, str] = {
    "GID-00": "full",
    "GID-01": "code",
    "GID-02": "ui",
    "GID-07": "gates",
    "GID-06": "review",
    "GID-11": "hygiene",
    "GID-08": "law",
    "GID-05": "constraints",
}


# ═══════════════════════════════════════════════════════════════════════════════
# P17 SESSION ACTIVATION (PAC-JEFFREY-P17)
# SESSION ACTIVATION · CANONICAL GOVERNANCE · 8 AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

# P17 Checkpoint Sequence (Block 5) — STRICT ORDER · NON-SKIPPABLE · 8 CHECKPOINTS
P17_CHECKPOINT_SEQUENCE: List[str] = [
    "PAC_ADMISSION",
    "RUNTIME_ACTIVATION",
    "RUNTIME_ACK",
    "AGENT_ACTIVATION",
    "AGENT_ACK_COLLECTION",
    "AGENT_EXECUTION",
    "REVIEW_GATES",
    "BER_ELIGIBILITY",
]

# P17 Checkpoint → Invariant Class Mapping (Block 5)
P17_CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    "PAC_ADMISSION": ["S-INV", "A-INV", "T-INV"],
    "RUNTIME_ACTIVATION": ["S-INV"],
    "RUNTIME_ACK": ["A-INV"],
    "AGENT_ACTIVATION": ["A-INV"],
    "AGENT_ACK_COLLECTION": ["A-INV"],
    "AGENT_EXECUTION": ["M-INV"],
    "REVIEW_GATES": ["X-INV", "C-INV"],
    "BER_ELIGIBILITY": ["F-INV"],
}

# P17 Required WRAPs per Block 7 — 8 AGENTS (SESSION ACTIVATION)
P17_REQUIRED_WRAPS: List[str] = [
    "WRAP-BENSON-GID00-PAC-JEFFREY-P17",
    "WRAP-CODY-GID01-PAC-JEFFREY-P17",
    "WRAP-SONNY-GID02-PAC-JEFFREY-P17",
    "WRAP-DAN-GID07-PAC-JEFFREY-P17",
    "WRAP-SAM-GID06-PAC-JEFFREY-P17",
    "WRAP-ATLAS-GID11-PAC-JEFFREY-P17",
    "WRAP-ALEX-GID08-PAC-JEFFREY-P17",
    "WRAP-PAX-GID05-PAC-JEFFREY-P17",
]

# P17 Activated Agents (Block 4) — 8 AGENTS (SESSION ACTIVATION)
P17_ACTIVATED_AGENTS: List[str] = [
    "GID-00",  # BENSON · orchestration · EXECUTING
    "GID-01",  # CODY · backend · EXECUTING
    "GID-02",  # SONNY · frontend · EXECUTING
    "GID-07",  # DAN · ci_cd · EXECUTING
    "GID-06",  # SAM · security · EXECUTING
    "GID-11",  # ATLAS · repo_integrity · EXECUTING
    "GID-08",  # ALEX · governance · EXECUTING
    "GID-05",  # PAX · product · EXECUTING
]

# P17 Training Signals (Block 10)
P17_TRAINING_SIGNALS: List[str] = [
    "TS-P17-001",  # Session activation under canonical governance confirmed
]

# P17 BER Status (Block 9)
P17_BER_STATUS: Dict[str, Any] = {
    "classification": "PROVISIONAL",
    "execution_binding": False,
    "ledger_commit": "FORBIDDEN",
    "settlement_effect": "NONE",
}


# ═══════════════════════════════════════════════════════════════════════════════
# P18 AGENT UNIFORM DOCTRINE (PAC-JEFFREY-P18)
# AGENT UNIFORM ENFORCEMENT · RUNTIME LAW · 8 AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

# P18 Checkpoint Sequence (Block 5) — STRICT ORDER · NON-SKIPPABLE · 8 CHECKPOINTS
P18_CHECKPOINT_SEQUENCE: List[str] = [
    "PAC_ADMISSION",
    "RUNTIME_ACTIVATION",
    "RUNTIME_ACK_COLLECTION",
    "AGENT_ACTIVATION",
    "AGENT_ACK_COLLECTION",
    "AGENT_EXECUTION",
    "REVIEW_GATES",
    "BER_ELIGIBILITY",
]

# P18 Checkpoint → Invariant Class Mapping (Block 5)
P18_CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    "PAC_ADMISSION": ["S-INV", "A-INV", "T-INV"],
    "RUNTIME_ACTIVATION": ["S-INV"],
    "RUNTIME_ACK_COLLECTION": ["A-INV"],
    "AGENT_ACTIVATION": ["A-INV"],
    "AGENT_ACK_COLLECTION": ["A-INV"],
    "AGENT_EXECUTION": ["M-INV"],
    "REVIEW_GATES": ["X-INV", "C-INV"],
    "BER_ELIGIBILITY": ["F-INV"],
}

# P18 Governance Scope (Block 1)
P18_GOVERNANCE_SCOPE: List[str] = [
    "governance_engine",
    "lint_v2_compiler",
    "runtime_admission",
    "agent_registry",
    "ber_pipeline",
    "operator_console",
]

# P18 Required WRAPs per Block 7 — 8 AGENTS (AGENT UNIFORM)
P18_REQUIRED_WRAPS: List[str] = [
    "WRAP-BENSON-GID00-PAC-JEFFREY-P18",
    "WRAP-CODY-GID01-PAC-JEFFREY-P18",
    "WRAP-SONNY-GID02-PAC-JEFFREY-P18",
    "WRAP-DAN-GID07-PAC-JEFFREY-P18",
    "WRAP-SAM-GID06-PAC-JEFFREY-P18",
    "WRAP-ATLAS-GID11-PAC-JEFFREY-P18",
    "WRAP-ALEX-GID08-PAC-JEFFREY-P18",
    "WRAP-PAX-GID05-PAC-JEFFREY-P18",
]

# P18 Activated Agents (Block 4) — 8 AGENTS (AGENT UNIFORM)
P18_ACTIVATED_AGENTS: List[str] = [
    "GID-00",  # BENSON · orchestration
    "GID-01",  # CODY · backend
    "GID-02",  # SONNY · frontend
    "GID-07",  # DAN · ci_cd
    "GID-06",  # SAM · security
    "GID-11",  # ATLAS · repo_integrity
    "GID-08",  # ALEX · governance
    "GID-05",  # PAX · constraint_modeling
]

# P18 Agent Uniform Scopes (Block 4) — Canonical Agent "Uniform"
P18_AGENT_UNIFORM_SCOPES: Dict[str, str] = {
    "GID-00": "orchestration",
    "GID-01": "backend",
    "GID-02": "frontend",
    "GID-07": "ci_cd",
    "GID-06": "security",
    "GID-11": "repo_integrity",
    "GID-08": "governance",
    "GID-05": "constraint_modeling",
}

# P18 Agent Uniform Invariants (Block 6) — RUNTIME LAW
P18_UNIFORM_INVARIANTS: List[str] = [
    "INV-UNIFORM-001",  # No agent executes without uniform
    "INV-UNIFORM-002",  # Unknown agents forbidden
    "INV-UNIFORM-003",  # PAC required for all execution
    "INV-UNIFORM-004",  # BER required for finality
]

# P18 Training Signals (Block 9)
P18_TRAINING_SIGNALS: List[str] = [
    "TS-P18-001",  # Agent Uniform enforced as runtime law
    "TS-P18-002",  # Modular agent swap validated under governance
]

# P18 BER Status (Block 8)
P18_BER_STATUS: Dict[str, Any] = {
    "classification": "PROVISIONAL",
    "execution_binding": False,
    "ledger_commit": "FORBIDDEN",
    "settlement_effect": "NONE",
}

# P18 Positive Closure Conditions (Block 10)
P18_POSITIVE_CLOSURE: Dict[str, bool] = {
    "all_agents_acked": True,
    "all_wraps_present": True,
    "no_execution_outside_uniform": True,
    "zero_drift_confirmed": True,
    "system_ready_for_next_pac": True,
}


def get_p17_required_invariants(checkpoint: str) -> List[str]:
    """Get required invariant classes for a P17 checkpoint."""
    return P17_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, [])


def get_p18_required_invariants(checkpoint: str) -> List[str]:
    """Get required invariant classes for a P18 checkpoint."""
    return P18_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, [])


def validate_p18_checkpoint_invariants(
    checkpoint: str, evaluated_classes: Set[str]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required invariant classes were evaluated at P18 checkpoint.
    
    Returns:
        (success, error_message)
    """
    required = set(P18_CHECKPOINT_INVARIANT_MAPPING.get(checkpoint, []))
    missing = required - evaluated_classes
    if missing:
        return False, f"P18 checkpoint {checkpoint} missing invariants: {missing}"
    return True, None


def validate_p18_agent_uniform(
    agent_gid: str, scope: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate agent scope matches P18 Agent Uniform Doctrine.
    
    RUNTIME LAW: No agent executes without uniform (INV-UNIFORM-001).
    
    Returns:
        (valid, error_message)
    """
    expected_scope = P18_AGENT_UNIFORM_SCOPES.get(agent_gid)
    if expected_scope is None:
        return False, f"INV-UNIFORM-002: Unknown agent GID: {agent_gid}"
    if scope != expected_scope:
        return False, f"INV-UNIFORM-001: Agent {agent_gid} uniform mismatch: expected {expected_scope}, got {scope}"
    return True, None


def validate_p18_governance_scope(
    covered_scopes: Set[str]
) -> Tuple[bool, List[str]]:
    """
    Validate P18 governance coverage across all required scopes.
    
    Returns:
        (covered, missing_scopes)
    """
    required = set(P18_GOVERNANCE_SCOPE)
    missing = required - covered_scopes
    return len(missing) == 0, list(missing)


# ═══════════════════════════════════════════════════════════════════════════════
# P11R BER FINALITY (PAC-JEFFREY-P11R Block 9)
# ═══════════════════════════════════════════════════════════════════════════════

class P11RBERClassification(str, Enum):
    """BER Classification per P11R Block 9."""
    PROVISIONAL = "PROVISIONAL"  # P11R default — no execution binding
    BINDING = "BINDING"          # Full execution binding (not for P11R)


@dataclass
class P11RBERStatus:
    """
    BER Status per PAC-JEFFREY-P11R Block 9.
    
    P11R BER is PROVISIONAL only.
    execution_binding = false
    ledger_commit = FORBIDDEN
    settlement_effect = NONE
    """
    ber_id: str = field(default_factory=lambda: f"BER-P11R-{uuid4().hex[:8].upper()}")
    pac_id: str = ""
    classification: P11RBERClassification = P11RBERClassification.PROVISIONAL
    execution_binding: bool = False
    ledger_commit_allowed: bool = False
    settlement_effect: str = "NONE"
    eligible: bool = False
    eligibility_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ber_id": self.ber_id,
            "pac_id": self.pac_id,
            "classification": self.classification.value,
            "execution_binding": self.execution_binding,
            "ledger_commit_allowed": self.ledger_commit_allowed,
            "settlement_effect": self.settlement_effect,
            "eligible": self.eligible,
            "eligibility_reason": self.eligibility_reason,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# P11R EXECUTION STATE (COMBINED)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class P11RExecutionState:
    """
    Complete P11R Execution State per PAC-JEFFREY-P11R.
    
    Tracks:
    - Runtime activation ACK
    - Agent activation barrier
    - Checkpoint progression
    - WRAP collection
    - BER eligibility
    """
    state_id: str = field(default_factory=lambda: f"P11R-STATE-{uuid4().hex[:8].upper()}")
    pac_id: str = "PAC-JEFFREY-P11R"
    execution_model: P11RExecutionModel = P11RExecutionModel.PARALLEL
    
    # Components
    runtime_ack: Optional[RuntimeActivationACK] = None
    agent_barrier: Optional[P11RAgentACKBarrier] = None
    checkpoint_tracker: Optional[P11RCheckpointTracker] = None
    wrap_requirement: Optional[P11RWrapRequirement] = None
    ber_status: Optional[P11RBERStatus] = None
    
    # State tracking
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    
    def is_ready_for_execution(self) -> Tuple[bool, List[str]]:
        """Check if ready for agent execution."""
        issues = []
        
        # Check runtime ACK
        if not self.runtime_ack or not self.runtime_ack.is_valid():
            issues.append("Runtime ACK not valid")
        
        # Check agent barrier
        if not self.agent_barrier or not self.agent_barrier.is_released():
            issues.append("Agent ACK barrier not released")
        
        return len(issues) == 0, issues
    
    def is_complete(self) -> Tuple[bool, List[str]]:
        """Check if P11R execution is complete."""
        issues = []
        
        # Check checkpoint completion
        if not self.checkpoint_tracker or not self.checkpoint_tracker.is_complete():
            issues.append("Checkpoints not complete")
        
        # Check WRAP completion
        if not self.wrap_requirement or not self.wrap_requirement.is_complete():
            issues.append("WRAPs not complete")
        
        # Check BER eligibility
        if not self.ber_status or not self.ber_status.eligible:
            issues.append("BER not eligible")
        
        return len(issues) == 0, issues
    
    def to_dict(self) -> Dict[str, Any]:
        ready, ready_issues = self.is_ready_for_execution()
        complete, complete_issues = self.is_complete()
        
        return {
            "state_id": self.state_id,
            "pac_id": self.pac_id,
            "execution_model": self.execution_model.value,
            "runtime_ack": self.runtime_ack.to_dict() if self.runtime_ack else None,
            "agent_barrier": self.agent_barrier.to_dict() if self.agent_barrier else None,
            "checkpoint_tracker": self.checkpoint_tracker.to_dict() if self.checkpoint_tracker else None,
            "wrap_requirement": self.wrap_requirement.to_dict() if self.wrap_requirement else None,
            "ber_status": self.ber_status.to_dict() if self.ber_status else None,
            "is_ready_for_execution": ready,
            "ready_issues": ready_issues,
            "is_complete": complete,
            "complete_issues": complete_issues,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


def create_p11r_execution_state() -> P11RExecutionState:
    """
    Create P11R execution state with all components initialized.
    
    Per PAC-JEFFREY-P11R Blocks 2-9.
    """
    pac_id = "PAC-JEFFREY-P11R"
    
    # P11R activated agents (Block 4)
    p11r_agents = ["GID-00", "GID-01", "GID-02", "GID-07", "GID-06", "GID-11", "GID-08"]
    
    return P11RExecutionState(
        pac_id=pac_id,
        execution_model=P11RExecutionModel.PARALLEL,
        runtime_ack=RuntimeActivationACK(pac_id=pac_id),
        agent_barrier=P11RAgentACKBarrier(
            pac_id=pac_id,
            required_agents=p11r_agents,
        ),
        checkpoint_tracker=P11RCheckpointTracker(pac_id=pac_id),
        wrap_requirement=P11RWrapRequirement(
            pac_id=pac_id,
            required_wraps=P11R_REQUIRED_WRAPS,
        ),
        ber_status=P11RBERStatus(pac_id=pac_id),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ROSTER — DERIVED FROM CANONICAL REGISTRY (PAC-ATLAS-P02)
# ═══════════════════════════════════════════════════════════════════════════════
# INV-AGENT-001: Canonical Agent Registry is single source of truth
# INV-AGENT-002: AgentRegistration.agent_name MUST match registry for given GID
# INV-AGENT-003: Unknown agent names are forbidden
# INV-AGENT-004: Lane assignment MUST match registry
# INV-AGENT-005: Any violation → HARD_FAIL at lint, CI, and runtime

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


def _build_agent_roster_from_canonical() -> Dict[str, AgentRegistration]:
    """
    Build AGENT_ROSTER from canonical gid_registry.
    
    PAC-ATLAS-P02: Single source of truth enforcement.
    This function ensures lint_v2.py ALWAYS reflects canonical registry.
    """
    try:
        registry = get_canonical_registry()
        roster: Dict[str, AgentRegistration] = {}
        
        for gid in registry.list_all_gids():
            agent = registry.get_agent(gid)
            # Convert registry lane to lowercase for lint compatibility
            roster[gid] = AgentRegistration(
                agent_name=agent.name,
                gid=gid,
                lane=agent.lane.lower(),
                mode="EXECUTING",  # All registered agents are EXECUTING
            )
        
        return roster
    except Exception as e:
        # FAIL_CLOSED: If registry fails, use empty roster → all validations fail
        logger.error("LINT_V2: Failed to load canonical registry: %s", e)
        return {}


# CANONICAL AGENT ROSTER — Derived at module load from gid_registry.json
# Undeclared agents: FORBIDDEN
# Dynamic agents: FORBIDDEN
# Inline definitions: FORBIDDEN (PAC-ATLAS-P02)
AGENT_ROSTER: Dict[str, AgentRegistration] = _build_agent_roster_from_canonical()

# Compute registry hash for cross-artifact validation
def _compute_registry_hash() -> str:
    """Compute deterministic hash of agent roster for integrity checks."""
    roster_data = {gid: reg.to_dict() for gid, reg in sorted(AGENT_ROSTER.items())}
    return hashlib.sha256(json.dumps(roster_data, sort_keys=True).encode()).hexdigest()[:16]

AGENT_REGISTRY_HASH: str = _compute_registry_hash()


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
# CHECKPOINT → INVARIANT CLASS MAPPING (PAC-JEFFREY-P10R Block 5)
# ═══════════════════════════════════════════════════════════════════════════════

# Canonical mapping per PAC-JEFFREY-P10R Block 5
# 10 NON-SKIPPABLE checkpoints
# Checkpoint skip: FORBIDDEN
CHECKPOINT_INVARIANT_MAPPING: Dict[str, List[str]] = {
    # Original checkpoints
    "PAC_ADMISSION": ["S-INV", "A-INV", "T-INV"],
    "WRAP_INGESTION": ["S-INV", "X-INV", "C-INV"],
    "RG01_EVALUATION": ["X-INV", "A-INV"],
    "BER_ELIGIBILITY": ["F-INV", "C-INV"],
    "SETTLEMENT_READINESS": ["F-INV"],
    # P10R expanded checkpoints (Block 5)
    "RUNTIME_ACTIVATION": ["S-INV", "A-INV"],
    "AGENT_ACK_COLLECTION": ["A-INV", "T-INV"],
    "AGENT_EXECUTION": ["A-INV", "X-INV"],
    "API_ADMISSION": ["S-INV", "A-INV"],
    "UI_RENDER_VALIDATION": ["S-INV", "M-INV"],
    "REVIEW_GATES": ["X-INV", "C-INV"],
    "LEDGER_COMMIT": ["F-INV", "X-INV"],
    "FINALITY_SEAL": ["F-INV"],
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
    Runtime Enforcement Points per PAC-JEFFREY-P10R Block 5.
    
    10 NON-SKIPPABLE checkpoints.
    Each checkpoint evaluates ALL applicable invariants.
    """
    # Original checkpoints
    PAC_ADMISSION = "PAC_ADMISSION"
    WRAP_INGESTION = "WRAP_INGESTION"
    RG01_EVALUATION = "RG01_EVALUATION"
    BER_ELIGIBILITY = "BER_ELIGIBILITY"
    SETTLEMENT_READINESS = "SETTLEMENT_READINESS"
    # P10R expanded checkpoints (Block 5)
    RUNTIME_ACTIVATION = "RUNTIME_ACTIVATION"
    AGENT_ACK_COLLECTION = "AGENT_ACK_COLLECTION"
    AGENT_EXECUTION = "AGENT_EXECUTION"
    API_ADMISSION = "API_ADMISSION"
    UI_RENDER_VALIDATION = "UI_RENDER_VALIDATION"
    REVIEW_GATES = "REVIEW_GATES"
    LEDGER_COMMIT = "LEDGER_COMMIT"
    FINALITY_SEAL = "FINALITY_SEAL"


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
# CANONICAL INVARIANTS — AGENT REGISTRY ENFORCEMENT (PAC-ATLAS-P02)
# ═══════════════════════════════════════════════════════════════════════════════

A_INV_005 = InvariantDefinition(
    invariant_id="A-INV-005",
    invariant_class=InvariantClass.A_INV,
    name="Canonical Agent Registry",
    description="Canonical Agent Registry is single source of truth (INV-AGENT-001)",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.RUNTIME_ACTIVATION,
        EnforcementPoint.AGENT_EXECUTION,
    ],
)

A_INV_006 = InvariantDefinition(
    invariant_id="A-INV-006",
    invariant_class=InvariantClass.A_INV,
    name="Agent Name Registry Match",
    description="AgentRegistration.agent_name MUST match registry for given GID (INV-AGENT-002)",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.WRAP_INGESTION,
    ],
)

A_INV_007 = InvariantDefinition(
    invariant_id="A-INV-007",
    invariant_class=InvariantClass.A_INV,
    name="Unknown Agent Forbidden",
    description="Unknown agent names are forbidden (INV-AGENT-003)",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.WRAP_INGESTION,
        EnforcementPoint.AGENT_EXECUTION,
    ],
)

A_INV_008 = InvariantDefinition(
    invariant_id="A-INV-008",
    invariant_class=InvariantClass.A_INV,
    name="Lane Registry Match",
    description="Lane assignment MUST match registry (INV-AGENT-004)",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.AGENT_EXECUTION,
    ],
)

A_INV_009 = InvariantDefinition(
    invariant_id="A-INV-009",
    invariant_class=InvariantClass.A_INV,
    name="Registry Violation Hard Fail",
    description="Any registry violation → HARD_FAIL at lint, CI, and runtime (INV-AGENT-005)",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.WRAP_INGESTION,
        EnforcementPoint.RUNTIME_ACTIVATION,
        EnforcementPoint.AGENT_EXECUTION,
        EnforcementPoint.API_ADMISSION,
    ],
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
# PLATFORM INVARIANTS (PAC-JEFFREY-P10R Block 6)
# ═══════════════════════════════════════════════════════════════════════════════

PLAT_INV_001 = InvariantDefinition(
    invariant_id="INV-LINT-PLAT-001",
    invariant_class=InvariantClass.A_INV,
    name="Runtime ACK Required",
    description="Runtime ACK REQUIRED for all agent execution",
    enforcement_points=[
        EnforcementPoint.RUNTIME_ACTIVATION,
        EnforcementPoint.AGENT_ACK_COLLECTION,
    ],
)

PLAT_INV_002 = InvariantDefinition(
    invariant_id="INV-LINT-PLAT-002",
    invariant_class=InvariantClass.A_INV,
    name="Agent Execution ACK Gate",
    description="Agent execution without ACK = ILLEGAL",
    enforcement_points=[
        EnforcementPoint.AGENT_EXECUTION,
        EnforcementPoint.AGENT_ACK_COLLECTION,
    ],
)

PLAT_INV_003 = InvariantDefinition(
    invariant_id="INV-LINT-PLAT-003",
    invariant_class=InvariantClass.M_INV,
    name="UI Lint-Validated State Only",
    description="UI renders only lint-validated state",
    enforcement_points=[EnforcementPoint.UI_RENDER_VALIDATION],
)

PLAT_INV_004 = InvariantDefinition(
    invariant_id="INV-LINT-PLAT-004",
    invariant_class=InvariantClass.S_INV,
    name="API Admission Lint Gate",
    description="API admission requires lint PASS",
    enforcement_points=[EnforcementPoint.API_ADMISSION],
)

PLAT_INV_005 = InvariantDefinition(
    invariant_id="INV-LINT-PLAT-005",
    invariant_class=InvariantClass.T_INV,
    name="Orchestration Order Determinism",
    description="Orchestration order deterministic",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.AGENT_EXECUTION,
    ],
)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT UNIFORM INVARIANTS (PAC-JEFFREY-P18 Block 6)
# RUNTIME LAW · NO AGENT EXECUTES WITHOUT UNIFORM
# ═══════════════════════════════════════════════════════════════════════════════

UNIFORM_INV_001 = InvariantDefinition(
    invariant_id="INV-UNIFORM-001",
    invariant_class=InvariantClass.A_INV,
    name="Agent Uniform Required",
    description="No agent executes without uniform (PAC + ACK + WRAP + BER)",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.RUNTIME_ACTIVATION,
        EnforcementPoint.AGENT_EXECUTION,
        EnforcementPoint.AGENT_ACK_COLLECTION,
    ],
)

UNIFORM_INV_002 = InvariantDefinition(
    invariant_id="INV-UNIFORM-002",
    invariant_class=InvariantClass.A_INV,
    name="Unknown Agents Forbidden",
    description="Unknown agents forbidden under Agent Uniform Doctrine",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.WRAP_INGESTION,
        EnforcementPoint.AGENT_EXECUTION,
        EnforcementPoint.API_ADMISSION,
    ],
)

UNIFORM_INV_003 = InvariantDefinition(
    invariant_id="INV-UNIFORM-003",
    invariant_class=InvariantClass.A_INV,
    name="PAC Required For Execution",
    description="PAC required for all agent execution under Agent Uniform Doctrine",
    enforcement_points=[
        EnforcementPoint.PAC_ADMISSION,
        EnforcementPoint.AGENT_EXECUTION,
        EnforcementPoint.RUNTIME_ACTIVATION,
    ],
)

UNIFORM_INV_004 = InvariantDefinition(
    invariant_id="INV-UNIFORM-004",
    invariant_class=InvariantClass.F_INV,
    name="BER Required For Finality",
    description="BER required for finality under Agent Uniform Doctrine",
    enforcement_points=[
        EnforcementPoint.BER_ELIGIBILITY,
        EnforcementPoint.SETTLEMENT_READINESS,
    ],
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
    # Agent Registry Enforcement (PAC-ATLAS-P02)
    "A-INV-005": A_INV_005,
    "A-INV-006": A_INV_006,
    "A-INV-007": A_INV_007,
    "A-INV-008": A_INV_008,
    "A-INV-009": A_INV_009,
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
    # Platform (P10R)
    "INV-LINT-PLAT-001": PLAT_INV_001,
    "INV-LINT-PLAT-002": PLAT_INV_002,
    "INV-LINT-PLAT-003": PLAT_INV_003,
    "INV-LINT-PLAT-004": PLAT_INV_004,
    "INV-LINT-PLAT-005": PLAT_INV_005,
    # Agent Uniform (P18)
    "INV-UNIFORM-001": UNIFORM_INV_001,
    "INV-UNIFORM-002": UNIFORM_INV_002,
    "INV-UNIFORM-003": UNIFORM_INV_003,
    "INV-UNIFORM-004": UNIFORM_INV_004,
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
    Lint v2 Platform-Wide Runtime Enforcement Engine.
    
    PAC-JEFFREY-P10R: Platform-Wide Lint v2 Expansion
    
    Runtime Activation (Block 3):
    - lint_v2_engine_loaded
    - invariant_registry_loaded
    - execution_runtime_schema_loaded
    - agent_registry_loaded
    - fail_closed_enabled
    - RUNTIME_ACK_REQUIRED
    
    Platform Invariants (Block 6):
    - INV-LINT-PLAT-001: Runtime ACK REQUIRED
    - INV-LINT-PLAT-002: Agent execution without ACK = ILLEGAL
    - INV-LINT-PLAT-003: UI renders only lint-validated state
    - INV-LINT-PLAT-004: API admission requires lint PASS
    - INV-LINT-PLAT-005: Orchestration order deterministic
    
    10 Checkpoints (NON-SKIPPABLE):
    PAC_ADMISSION, RUNTIME_ACTIVATION, AGENT_ACK_COLLECTION,
    AGENT_EXECUTION, API_ADMISSION, UI_RENDER_VALIDATION,
    REVIEW_GATES, BER_ELIGIBILITY, LEDGER_COMMIT, FINALITY_SEAL
    
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
            logger.error("LINT_V2: Runtime activation FAILED - missing: %s", missing)
    
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
                        "LINT_V2: HARD_FAIL on %s at %s for %s",
                        inv.invariant_id,
                        enforcement_point.value,
                        artifact_id,
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
            "LINT_V2: %s evaluation complete artifact=%s result=%s violations=%s duration=%sms",
            enforcement_point.value,
            artifact_id,
            result.value,
            len(violations),
            duration_ms,
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
            logger.error("LINT_V2: Exception evaluating %s: %s", invariant.invariant_id, e)
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
            for field_name in required:
                if not pac.get(field_name):
                    return False, f"Missing required PAC field: {field_name}"
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # PAC-ATLAS-P02: Agent Registry Enforcement Invariants
        # ═══════════════════════════════════════════════════════════════════════
        
        if inv_id == "A-INV-005":  # Canonical Agent Registry
            # Verify we can access the canonical registry
            try:
                registry = get_canonical_registry()
                if not registry.list_all_gids():
                    return False, "Canonical registry empty or inaccessible"
                return True, None
            except Exception as e:
                return False, f"Canonical registry unavailable: {e}"
        
        if inv_id == "A-INV-006":  # Agent Name Registry Match
            agent_gid = context.get("agent_gid")
            agent_name = context.get("agent_name")
            if agent_gid and agent_name:
                try:
                    registry = get_canonical_registry()
                    canonical_agent = registry.get_agent(agent_gid)
                    if canonical_agent.name != agent_name:
                        return False, f"Agent name mismatch: {agent_name} != {canonical_agent.name} for {agent_gid}"
                except UnknownGIDError:
                    return False, f"Unknown GID in registry: {agent_gid}"
                except Exception as e:
                    return False, f"Registry validation failed: {e}"
            return True, None
        
        if inv_id == "A-INV-007":  # Unknown Agent Forbidden
            agent_name = context.get("agent_name")
            if agent_name:
                try:
                    registry = get_canonical_registry()
                    all_agents = {registry.get_agent(gid).name for gid in registry.list_all_gids()}
                    if agent_name not in all_agents:
                        return False, f"Unknown agent name: {agent_name}"
                except Exception as e:
                    return False, f"Agent validation failed: {e}"
            return True, None
        
        if inv_id == "A-INV-008":  # Lane Registry Match
            agent_gid = context.get("agent_gid")
            requested_lane = context.get("requested_lane")
            if agent_gid and requested_lane:
                try:
                    registry = get_canonical_registry()
                    canonical_agent = registry.get_agent(agent_gid)
                    # Normalize lane comparison (registry uses uppercase)
                    if canonical_agent.lane.upper() != requested_lane.upper():
                        return False, f"Lane mismatch: {requested_lane} != {canonical_agent.lane} for {agent_gid}"
                except UnknownGIDError:
                    return False, f"Unknown GID in registry: {agent_gid}"
                except Exception as e:
                    return False, f"Lane validation failed: {e}"
            return True, None
        
        if inv_id == "A-INV-009":  # Registry Violation Hard Fail
            # This invariant is a meta-check: any registry violation should trigger HARD_FAIL
            registry_violations = context.get("registry_violations", [])
            if registry_violations:
                return False, f"Registry violations detected: {registry_violations}"
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
            for field_name in required:
                if not positive_closure.get(field_name):
                    return False, f"Positive closure missing or invalid: {field_name}"
            return True, None
        
        return True, None
    
    def _evaluate_default(
        self,
        _invariant: InvariantDefinition,
        _context: Dict[str, Any],
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
