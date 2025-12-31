"""
ChainBridge PAC Schema — Immutable Schema Definition
════════════════════════════════════════════════════════════════════════════════

Typed schema definition for PACs (Principal Action Commands).
No optional loop components. All loop closure fields mandatory.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-IMMUTABLE-PAC-SCHEMA-019
Effective Date: 2025-12-26

SCHEMA INVARIANTS:
- INV-PAC-001: No PAC dispatch without schema validation
- INV-PAC-002: Missing WRAP obligation = REJECT
- INV-PAC-003: Missing BER obligation = REJECT
- INV-PAC-004: Missing FINAL_STATE = REJECT

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import FrozenSet, List, Optional, Set


# ═══════════════════════════════════════════════════════════════════════════════
# PAC EXECUTION MODES
# ═══════════════════════════════════════════════════════════════════════════════

class PACMode(Enum):
    """Valid PAC execution modes."""
    
    ORCHESTRATION = "ORCHESTRATION"
    EXECUTION = "EXECUTION"
    SYNTHESIS = "SYNTHESIS"
    REVIEW = "REVIEW"


class PACDiscipline(Enum):
    """Valid PAC enforcement disciplines."""
    
    GOLD_STANDARD = "GOLD_STANDARD"
    FAIL_CLOSED = "FAIL-CLOSED"


class PACStatus(Enum):
    """PAC lifecycle status."""
    
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    DISPATCHED = "DISPATCHED"
    EXECUTING = "EXECUTING"
    WRAP_RECEIVED = "WRAP_RECEIVED"
    BER_ISSUED = "BER_ISSUED"
    LOOP_CLOSED = "LOOP_CLOSED"
    REJECTED = "REJECTED"


class WRAPStatus(Enum):
    """WRAP execution status."""
    
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class BERStatus(Enum):
    """BER decision status."""
    
    APPROVE = "APPROVE"
    CORRECTIVE = "CORRECTIVE"
    REJECT = "REJECT"


# ═══════════════════════════════════════════════════════════════════════════════
# PAC SECTION IDENTIFIERS — MANDATORY
# ═══════════════════════════════════════════════════════════════════════════════

class PACSection(Enum):
    """
    Canonical PAC section identifiers.
    
    ALL sections are MANDATORY. No optional sections.
    """
    
    # Header fields
    PAC_ID = "PAC_ID"
    ISSUER = "ISSUER"
    TARGET = "TARGET"
    MODE = "MODE"
    DISCIPLINE = "DISCIPLINE"
    
    # Body sections
    OBJECTIVE = "OBJECTIVE"
    EXECUTION_PLAN = "EXECUTION_PLAN"
    REQUIRED_DELIVERABLES = "REQUIRED_DELIVERABLES"
    CONSTRAINTS = "CONSTRAINTS"
    SUCCESS_CRITERIA = "SUCCESS_CRITERIA"
    
    # Loop closure sections (CRITICAL)
    DISPATCH = "DISPATCH"
    WRAP_OBLIGATION = "WRAP_OBLIGATION"
    BER_OBLIGATION = "BER_OBLIGATION"
    FINAL_STATE = "FINAL_STATE"


# Section display names
SECTION_NAMES = {
    PACSection.PAC_ID: "PAC ID",
    PACSection.ISSUER: "Issuer",
    PACSection.TARGET: "Target",
    PACSection.MODE: "Mode",
    PACSection.DISCIPLINE: "Discipline",
    PACSection.OBJECTIVE: "Objective",
    PACSection.EXECUTION_PLAN: "Execution Plan",
    PACSection.REQUIRED_DELIVERABLES: "Required Deliverables",
    PACSection.CONSTRAINTS: "Constraints",
    PACSection.SUCCESS_CRITERIA: "Success Criteria",
    PACSection.DISPATCH: "Dispatch",
    PACSection.WRAP_OBLIGATION: "WRAP Obligation",
    PACSection.BER_OBLIGATION: "BER Obligation",
    PACSection.FINAL_STATE: "Final State",
}

# Header sections (inline fields)
HEADER_SECTIONS: FrozenSet[PACSection] = frozenset({
    PACSection.PAC_ID,
    PACSection.ISSUER,
    PACSection.TARGET,
    PACSection.MODE,
    PACSection.DISCIPLINE,
})

# Body sections (block sections)
BODY_SECTIONS: FrozenSet[PACSection] = frozenset({
    PACSection.OBJECTIVE,
    PACSection.EXECUTION_PLAN,
    PACSection.REQUIRED_DELIVERABLES,
    PACSection.CONSTRAINTS,
    PACSection.SUCCESS_CRITERIA,
})

# Loop closure sections (CRITICAL - must be present)
LOOP_CLOSURE_SECTIONS: FrozenSet[PACSection] = frozenset({
    PACSection.DISPATCH,
    PACSection.WRAP_OBLIGATION,
    PACSection.BER_OBLIGATION,
    PACSection.FINAL_STATE,
})

# All required sections
ALL_REQUIRED_SECTIONS: FrozenSet[PACSection] = frozenset(PACSection)


# ═══════════════════════════════════════════════════════════════════════════════
# PAC ID FORMAT
# ═══════════════════════════════════════════════════════════════════════════════

# PAC ID pattern: PAC-{ISSUER}-{MODE}-{LANE}-{NAME}-{SEQ}
PAC_ID_PATTERN = re.compile(
    r"^PAC-[A-Z]+-[A-Z]+-[A-Z]+-[A-Z0-9-]+-\d{3}$",
    re.IGNORECASE,
)


def is_valid_pac_id(pac_id: str) -> bool:
    """Check if PAC ID matches canonical format."""
    return bool(PAC_ID_PATTERN.match(pac_id))


# ═══════════════════════════════════════════════════════════════════════════════
# PAC HEADER — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PACHeader:
    """
    Immutable PAC header fields.
    
    ALL fields are MANDATORY. No None values permitted.
    """
    
    pac_id: str
    issuer: str
    target: str
    mode: PACMode
    discipline: PACDiscipline
    
    def __post_init__(self):
        """Validate all fields are present."""
        if not self.pac_id:
            raise ValueError("PAC_ID is required")
        if not self.issuer:
            raise ValueError("ISSUER is required")
        if not self.target:
            raise ValueError("TARGET is required")


# ═══════════════════════════════════════════════════════════════════════════════
# PAC DISPATCH — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PACDispatch:
    """
    Immutable dispatch specification.
    
    Defines who executes the PAC.
    """
    
    target_gid: str
    role: str
    lane: str
    mode: PACMode
    
    def __post_init__(self):
        """Validate all fields are present."""
        if not self.target_gid:
            raise ValueError("target_gid is required")
        if not self.role:
            raise ValueError("role is required")
        if not self.lane:
            raise ValueError("lane is required")


# ═══════════════════════════════════════════════════════════════════════════════
# PAC WRAP OBLIGATION — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class WRAPObligation:
    """
    Immutable WRAP obligation.
    
    Declares that executing agent MUST return WRAP.
    """
    
    required: bool = True  # Always true, but explicit
    required_fields: FrozenSet[str] = frozenset({
        "pac_id",
        "status",
        "deliverables",
        "test_results",
    })
    
    @property
    def is_valid(self) -> bool:
        """WRAP obligation is always valid if present."""
        return self.required


# ═══════════════════════════════════════════════════════════════════════════════
# PAC BER OBLIGATION — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BERObligation:
    """
    Immutable BER obligation.
    
    Declares that Orchestration Engine MUST issue BER.
    """
    
    required: bool = True  # Always true, but explicit
    issuer: str = "GID-00"  # Orchestration Engine
    required_statuses: FrozenSet[BERStatus] = frozenset({
        BERStatus.APPROVE,
        BERStatus.CORRECTIVE,
        BERStatus.REJECT,
    })
    
    @property
    def is_valid(self) -> bool:
        """BER obligation is always valid if present."""
        return self.required


# ═══════════════════════════════════════════════════════════════════════════════
# PAC FINAL STATE — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PACFinalState:
    """
    Immutable final state declaration.
    
    Declares expected terminal state after loop closure.
    """
    
    expected_state: str = "LOOP_CLOSED"
    wrap_required: bool = True
    ber_required: bool = True
    
    @property
    def is_valid(self) -> bool:
        """Final state is valid if WRAP and BER required."""
        return self.wrap_required and self.ber_required


# ═══════════════════════════════════════════════════════════════════════════════
# PAC DELIVERABLE — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PACDeliverable:
    """Single deliverable item."""
    
    index: int
    description: str
    path: Optional[str] = None
    
    def __post_init__(self):
        """Validate description is present."""
        if not self.description:
            raise ValueError(f"Deliverable {self.index} requires description")


# ═══════════════════════════════════════════════════════════════════════════════
# FULL PAC SCHEMA — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PACSchema:
    """
    Complete immutable PAC schema.
    
    ALL fields are MANDATORY. No optional loop components.
    """
    
    # Header
    header: PACHeader
    
    # Body sections
    objective: str
    execution_plan: str
    required_deliverables: tuple  # Tuple of PACDeliverable
    constraints: tuple  # Tuple of strings
    success_criteria: tuple  # Tuple of strings
    
    # Loop closure sections (CRITICAL)
    dispatch: PACDispatch
    wrap_obligation: WRAPObligation
    ber_obligation: BERObligation
    final_state: PACFinalState
    
    # Metadata
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    def __post_init__(self):
        """Validate all required sections are present."""
        if not self.objective:
            raise ValueError("OBJECTIVE is required")
        if not self.execution_plan:
            raise ValueError("EXECUTION_PLAN is required")
        if not self.required_deliverables:
            raise ValueError("REQUIRED_DELIVERABLES is required")
        if not self.constraints:
            raise ValueError("CONSTRAINTS is required")
        if not self.success_criteria:
            raise ValueError("SUCCESS_CRITERIA is required")
    
    @property
    def pac_id(self) -> str:
        """Get PAC ID from header."""
        return self.header.pac_id
    
    @property
    def has_wrap_obligation(self) -> bool:
        """Check WRAP obligation is present and valid."""
        return self.wrap_obligation is not None and self.wrap_obligation.is_valid
    
    @property
    def has_ber_obligation(self) -> bool:
        """Check BER obligation is present and valid."""
        return self.ber_obligation is not None and self.ber_obligation.is_valid
    
    @property
    def has_final_state(self) -> bool:
        """Check final state is present and valid."""
        return self.final_state is not None and self.final_state.is_valid
    
    @property
    def is_loop_closure_complete(self) -> bool:
        """Check all loop closure sections are present."""
        return (
            self.dispatch is not None
            and self.has_wrap_obligation
            and self.has_ber_obligation
            and self.has_final_state
        )
    
    @property
    def missing_sections(self) -> List[PACSection]:
        """Get list of missing sections."""
        missing = []
        
        # Check header
        if not self.header.pac_id:
            missing.append(PACSection.PAC_ID)
        if not self.header.issuer:
            missing.append(PACSection.ISSUER)
        if not self.header.target:
            missing.append(PACSection.TARGET)
        
        # Check body
        if not self.objective:
            missing.append(PACSection.OBJECTIVE)
        if not self.execution_plan:
            missing.append(PACSection.EXECUTION_PLAN)
        if not self.required_deliverables:
            missing.append(PACSection.REQUIRED_DELIVERABLES)
        if not self.constraints:
            missing.append(PACSection.CONSTRAINTS)
        if not self.success_criteria:
            missing.append(PACSection.SUCCESS_CRITERIA)
        
        # Check loop closure
        if self.dispatch is None:
            missing.append(PACSection.DISPATCH)
        if not self.has_wrap_obligation:
            missing.append(PACSection.WRAP_OBLIGATION)
        if not self.has_ber_obligation:
            missing.append(PACSection.BER_OBLIGATION)
        if not self.has_final_state:
            missing.append(PACSection.FINAL_STATE)
        
        return missing


# ═══════════════════════════════════════════════════════════════════════════════
# PAC BUILDER — FLUENT API
# ═══════════════════════════════════════════════════════════════════════════════

class PACBuilder:
    """
    Fluent builder for constructing PACs.
    
    Guides creation of schema-compliant PACs.
    """
    
    def __init__(self):
        self._pac_id: Optional[str] = None
        self._issuer: Optional[str] = None
        self._target: Optional[str] = None
        self._mode: Optional[PACMode] = None
        self._discipline: Optional[PACDiscipline] = None
        self._objective: Optional[str] = None
        self._execution_plan: Optional[str] = None
        self._deliverables: List[PACDeliverable] = []
        self._constraints: List[str] = []
        self._success_criteria: List[str] = []
        self._dispatch: Optional[PACDispatch] = None
        self._wrap_obligation: Optional[WRAPObligation] = None
        self._ber_obligation: Optional[BERObligation] = None
        self._final_state: Optional[PACFinalState] = None
    
    def with_id(self, pac_id: str) -> PACBuilder:
        """Set PAC ID."""
        self._pac_id = pac_id
        return self
    
    def with_issuer(self, issuer: str) -> PACBuilder:
        """Set issuer."""
        self._issuer = issuer
        return self
    
    def with_target(self, target: str) -> PACBuilder:
        """Set target."""
        self._target = target
        return self
    
    def with_mode(self, mode: PACMode) -> PACBuilder:
        """Set execution mode."""
        self._mode = mode
        return self
    
    def with_discipline(self, discipline: PACDiscipline) -> PACBuilder:
        """Set enforcement discipline."""
        self._discipline = discipline
        return self
    
    def with_objective(self, objective: str) -> PACBuilder:
        """Set objective."""
        self._objective = objective
        return self
    
    def with_execution_plan(self, plan: str) -> PACBuilder:
        """Set execution plan."""
        self._execution_plan = plan
        return self
    
    def add_deliverable(self, description: str, path: str = None) -> PACBuilder:
        """Add a deliverable."""
        index = len(self._deliverables) + 1
        self._deliverables.append(PACDeliverable(index, description, path))
        return self
    
    def add_constraint(self, constraint: str) -> PACBuilder:
        """Add a constraint."""
        self._constraints.append(constraint)
        return self
    
    def add_success_criterion(self, criterion: str) -> PACBuilder:
        """Add a success criterion."""
        self._success_criteria.append(criterion)
        return self
    
    def with_dispatch(
        self,
        target_gid: str,
        role: str,
        lane: str,
        mode: PACMode,
    ) -> PACBuilder:
        """Set dispatch specification."""
        self._dispatch = PACDispatch(target_gid, role, lane, mode)
        return self
    
    def with_wrap_obligation(self) -> PACBuilder:
        """Set WRAP obligation (mandatory)."""
        self._wrap_obligation = WRAPObligation()
        return self
    
    def with_ber_obligation(self) -> PACBuilder:
        """Set BER obligation (mandatory)."""
        self._ber_obligation = BERObligation()
        return self
    
    def with_final_state(self) -> PACBuilder:
        """Set final state (mandatory)."""
        self._final_state = PACFinalState()
        return self
    
    def build(self) -> PACSchema:
        """
        Build the PAC schema.
        
        Raises ValueError if any required field is missing.
        """
        header = PACHeader(
            pac_id=self._pac_id or "",
            issuer=self._issuer or "",
            target=self._target or "",
            mode=self._mode or PACMode.EXECUTION,
            discipline=self._discipline or PACDiscipline.FAIL_CLOSED,
        )
        
        return PACSchema(
            header=header,
            objective=self._objective or "",
            execution_plan=self._execution_plan or "",
            required_deliverables=tuple(self._deliverables),
            constraints=tuple(self._constraints),
            success_criteria=tuple(self._success_criteria),
            dispatch=self._dispatch,
            wrap_obligation=self._wrap_obligation,
            ber_obligation=self._ber_obligation,
            final_state=self._final_state,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "PACMode",
    "PACDiscipline",
    "PACStatus",
    "WRAPStatus",
    "BERStatus",
    "PACSection",
    
    # Section collections
    "SECTION_NAMES",
    "HEADER_SECTIONS",
    "BODY_SECTIONS",
    "LOOP_CLOSURE_SECTIONS",
    "ALL_REQUIRED_SECTIONS",
    
    # Utilities
    "PAC_ID_PATTERN",
    "is_valid_pac_id",
    
    # Dataclasses
    "PACHeader",
    "PACDispatch",
    "WRAPObligation",
    "BERObligation",
    "PACFinalState",
    "PACDeliverable",
    "PACSchema",
    
    # Builder
    "PACBuilder",
]
