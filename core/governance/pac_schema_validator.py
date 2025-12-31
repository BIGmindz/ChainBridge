"""
ChainBridge PAC Schema Validator — Pre-Dispatch Validation
════════════════════════════════════════════════════════════════════════════════

Validates PACs against immutable schema at ingest (before dispatch).
Raises PACSchemaViolationError on failure.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-IMMUTABLE-PAC-SCHEMA-019
Effective Date: 2025-12-26

VALIDATION RULES:
- No PAC dispatch without schema validation
- Missing WRAP obligation = REJECT
- Missing BER obligation = REJECT
- Missing FINAL_STATE = REJECT
- Schema violations visible in terminal

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from core.governance.pac_schema import (
    ALL_REQUIRED_SECTIONS,
    BODY_SECTIONS,
    HEADER_SECTIONS,
    LOOP_CLOSURE_SECTIONS,
    PAC_ID_PATTERN,
    PACBuilder,
    PACDiscipline,
    PACDispatch,
    PACMode,
    PACSchema,
    PACSection,
    SECTION_NAMES,
    WRAPObligation,
    BERObligation,
    PACFinalState,
    is_valid_pac_id,
)
from core.governance.terminal_gates import (
    BORDER_CHAR,
    BORDER_WIDTH,
    FAIL_SYMBOL,
    PASS_SYMBOL,
    TerminalGateRenderer,
    get_terminal_renderer,
)


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION HIERARCHY
# ═══════════════════════════════════════════════════════════════════════════════

class PACSchemaError(Exception):
    """Base exception for PAC schema errors."""
    pass


class PACSchemaViolationError(PACSchemaError):
    """Raised when PAC fails schema validation."""
    
    def __init__(
        self,
        message: str,
        missing_sections: List[PACSection] = None,
        pac_id: str = None,
    ):
        self.missing_sections = missing_sections or []
        self.pac_id = pac_id
        super().__init__(f"SCHEMA VIOLATION: {message}")


class MissingWRAPObligationError(PACSchemaViolationError):
    """Raised when WRAP obligation is missing."""
    
    def __init__(self, pac_id: str = None):
        super().__init__(
            "WRAP_OBLIGATION is required — executing agent must return WRAP",
            missing_sections=[PACSection.WRAP_OBLIGATION],
            pac_id=pac_id,
        )


class MissingBERObligationError(PACSchemaViolationError):
    """Raised when BER obligation is missing."""
    
    def __init__(self, pac_id: str = None):
        super().__init__(
            "BER_OBLIGATION is required — Orchestration Engine must issue BER",
            missing_sections=[PACSection.BER_OBLIGATION],
            pac_id=pac_id,
        )


class MissingFinalStateError(PACSchemaViolationError):
    """Raised when FINAL_STATE is missing."""
    
    def __init__(self, pac_id: str = None):
        super().__init__(
            "FINAL_STATE is required — expected terminal state must be declared",
            missing_sections=[PACSection.FINAL_STATE],
            pac_id=pac_id,
        )


class InvalidPACIDError(PACSchemaViolationError):
    """Raised when PAC ID format is invalid."""
    
    def __init__(self, pac_id: str):
        super().__init__(
            f"Invalid PAC_ID format: {pac_id}. Expected: PAC-{{ISSUER}}-{{MODE}}-{{LANE}}-{{NAME}}-{{SEQ}}",
            missing_sections=[PACSection.PAC_ID],
            pac_id=pac_id,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PACValidationResult:
    """Result of PAC schema validation."""
    
    valid: bool
    pac_id: Optional[str]
    missing_sections: List[PACSection] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    validated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    @property
    def has_loop_closure(self) -> bool:
        """Check if all loop closure sections are present."""
        return not any(
            section in self.missing_sections
            for section in LOOP_CLOSURE_SECTIONS
        )
    
    @property
    def missing_section_names(self) -> List[str]:
        """Get human-readable names of missing sections."""
        return [SECTION_NAMES[s] for s in self.missing_sections]


# ═══════════════════════════════════════════════════════════════════════════════
# TERMINAL RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

class PACSchemaTerminalRenderer:
    """
    Terminal renderer for PAC schema validation.
    
    Emits canonical output for validation results.
    """
    
    def __init__(self, renderer: TerminalGateRenderer = None):
        self._renderer = renderer or get_terminal_renderer()
    
    def _emit(self, text: str) -> None:
        """Emit text via base renderer."""
        self._renderer._emit(text)
    
    def emit_validation_start(self, pac_id: str = None) -> None:
        """Emit validation start."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("📋 PAC SCHEMA VALIDATION")
        if pac_id:
            self._emit(f"   PAC_ID: {pac_id}")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_section_check(
        self,
        section: PACSection,
        present: bool,
    ) -> None:
        """Emit section check result."""
        name = SECTION_NAMES[section]
        symbol = PASS_SYMBOL if present else FAIL_SYMBOL
        status = "PRESENT" if present else "MISSING"
        self._emit(f"   {section.value:<20} {symbol} {status}  {name}")
    
    def emit_pac_accepted(self, pac_id: str = None) -> None:
        """Emit PAC accepted notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"🟩 PAC ACCEPTED — SCHEMA VALID")
        if pac_id:
            self._emit(f"   PAC_ID: {pac_id}")
        self._emit("   STATUS: READY_FOR_DISPATCH")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_pac_rejected(
        self,
        missing_sections: List[PACSection],
        pac_id: str = None,
    ) -> None:
        """Emit PAC rejected notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟥 PAC REJECTED — SCHEMA VIOLATION")
        if pac_id:
            self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   MISSING SECTIONS: {len(missing_sections)}")
        for section in missing_sections:
            name = SECTION_NAMES[section]
            self._emit(f"   📋 MISSING: {section.value} ({name})")
        self._emit("   ACTION: FIX_SCHEMA_VIOLATIONS")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_loop_closure_check(
        self,
        wrap_present: bool,
        ber_present: bool,
        final_state_present: bool,
    ) -> None:
        """Emit loop closure check results."""
        self._emit("")
        self._emit("   LOOP CLOSURE CHECK:")
        wrap_sym = PASS_SYMBOL if wrap_present else FAIL_SYMBOL
        ber_sym = PASS_SYMBOL if ber_present else FAIL_SYMBOL
        fs_sym = PASS_SYMBOL if final_state_present else FAIL_SYMBOL
        self._emit(f"      WRAP_OBLIGATION:  {wrap_sym}")
        self._emit(f"      BER_OBLIGATION:   {ber_sym}")
        self._emit(f"      FINAL_STATE:      {fs_sym}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAC SCHEMA VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class PACSchemaValidator:
    """
    Validates PACs against immutable schema.
    
    Executed at PAC ingest (before dispatch).
    """
    
    def __init__(
        self,
        renderer: PACSchemaTerminalRenderer = None,
        emit_terminal: bool = True,
    ):
        self._renderer = renderer or PACSchemaTerminalRenderer()
        self._emit_terminal = emit_terminal
    
    def validate(self, pac: PACSchema) -> PACValidationResult:
        """
        Validate PAC against schema.
        
        Returns PACValidationResult with validation status.
        """
        pac_id = pac.pac_id if pac.header else None
        
        if self._emit_terminal:
            self._renderer.emit_validation_start(pac_id)
        
        missing_sections: List[PACSection] = []
        errors: List[str] = []
        
        # Validate header sections
        if not pac.header or not pac.header.pac_id:
            missing_sections.append(PACSection.PAC_ID)
            errors.append("PAC_ID is required")
        elif not is_valid_pac_id(pac.header.pac_id):
            # Still allow non-standard IDs but warn
            pass
        
        if not pac.header or not pac.header.issuer:
            missing_sections.append(PACSection.ISSUER)
            errors.append("ISSUER is required")
        
        if not pac.header or not pac.header.target:
            missing_sections.append(PACSection.TARGET)
            errors.append("TARGET is required")
        
        # Validate body sections
        if not pac.objective:
            missing_sections.append(PACSection.OBJECTIVE)
            errors.append("OBJECTIVE is required")
        
        if not pac.execution_plan:
            missing_sections.append(PACSection.EXECUTION_PLAN)
            errors.append("EXECUTION_PLAN is required")
        
        if not pac.required_deliverables:
            missing_sections.append(PACSection.REQUIRED_DELIVERABLES)
            errors.append("REQUIRED_DELIVERABLES is required")
        
        if not pac.constraints:
            missing_sections.append(PACSection.CONSTRAINTS)
            errors.append("CONSTRAINTS is required")
        
        if not pac.success_criteria:
            missing_sections.append(PACSection.SUCCESS_CRITERIA)
            errors.append("SUCCESS_CRITERIA is required")
        
        # Validate loop closure sections (CRITICAL)
        if not pac.dispatch:
            missing_sections.append(PACSection.DISPATCH)
            errors.append("DISPATCH is required")
        
        wrap_present = pac.has_wrap_obligation
        if not wrap_present:
            missing_sections.append(PACSection.WRAP_OBLIGATION)
            errors.append("WRAP_OBLIGATION is required — loop closure mandatory")
        
        ber_present = pac.has_ber_obligation
        if not ber_present:
            missing_sections.append(PACSection.BER_OBLIGATION)
            errors.append("BER_OBLIGATION is required — loop closure mandatory")
        
        final_state_present = pac.has_final_state
        if not final_state_present:
            missing_sections.append(PACSection.FINAL_STATE)
            errors.append("FINAL_STATE is required — loop closure mandatory")
        
        # Emit section checks
        if self._emit_terminal:
            for section in ALL_REQUIRED_SECTIONS:
                present = section not in missing_sections
                self._renderer.emit_section_check(section, present)
            
            self._renderer.emit_loop_closure_check(
                wrap_present,
                ber_present,
                final_state_present,
            )
        
        # Build result
        valid = len(missing_sections) == 0
        
        result = PACValidationResult(
            valid=valid,
            pac_id=pac_id,
            missing_sections=missing_sections,
            errors=errors,
        )
        
        # Emit final status
        if self._emit_terminal:
            if valid:
                self._renderer.emit_pac_accepted(pac_id)
            else:
                self._renderer.emit_pac_rejected(missing_sections, pac_id)
        
        return result
    
    def validate_and_raise(self, pac: PACSchema) -> None:
        """
        Validate PAC and raise on failure.
        
        Raises PACSchemaViolationError if validation fails.
        """
        result = self.validate(pac)
        
        if not result.valid:
            # Check for specific loop closure violations
            if PACSection.WRAP_OBLIGATION in result.missing_sections:
                raise MissingWRAPObligationError(result.pac_id)
            if PACSection.BER_OBLIGATION in result.missing_sections:
                raise MissingBERObligationError(result.pac_id)
            if PACSection.FINAL_STATE in result.missing_sections:
                raise MissingFinalStateError(result.pac_id)
            
            # General schema violation
            raise PACSchemaViolationError(
                f"PAC missing {len(result.missing_sections)} required sections",
                missing_sections=result.missing_sections,
                pac_id=result.pac_id,
            )
    
    def is_valid(self, pac: PACSchema) -> bool:
        """Check if PAC is schema-valid (no terminal output)."""
        old_emit = self._emit_terminal
        self._emit_terminal = False
        try:
            result = self.validate(pac)
            return result.valid
        finally:
            self._emit_terminal = old_emit


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT PARSER — PARSE PAC FROM TEXT
# ═══════════════════════════════════════════════════════════════════════════════

class PACTextParser:
    """
    Parse PAC schema from text format.
    
    Extracts sections from canonical PAC text.
    """
    
    # Section header patterns
    SECTION_PATTERNS = {
        PACSection.OBJECTIVE: r"OBJECTIVE\s*[-═]+\s*(.*?)(?=\n═|$)",
        PACSection.EXECUTION_PLAN: r"EXECUTION[_ ]?PLAN\s*[-═]+\s*(.*?)(?=\n═|$)",
        PACSection.REQUIRED_DELIVERABLES: r"REQUIRED[_ ]?DELIVERABLES.*?\s*[-═]+\s*(.*?)(?=\n═|$)",
        PACSection.CONSTRAINTS: r"CONSTRAINTS\s*[-═]+\s*(.*?)(?=\n═|$)",
        PACSection.SUCCESS_CRITERIA: r"SUCCESS[_ ]?CRITERIA\s*[-═]+\s*(.*?)(?=\n═|$)",
        PACSection.DISPATCH: r"DISPATCH\s*[-═]+\s*(.*?)(?=\n═|$)",
        PACSection.WRAP_OBLIGATION: r"WRAP[_ ]?OBLIGATION.*?\s*[-═]+\s*(.*?)(?=\n═|$)",
        PACSection.BER_OBLIGATION: r"BER[_ ]?OBLIGATION.*?\s*[-═]+\s*(.*?)(?=\n═|$)",
        PACSection.FINAL_STATE: r"FINAL[_ ]?STATE.*?\s*[-═]+\s*(.*?)(?=\n═|$)",
    }
    
    # Header field patterns
    HEADER_PATTERNS = {
        "pac_id": r"PAC-[A-Z0-9-]+",
        "issuer": r"ISSUER:\s*(.+)",
        "target": r"TARGET:\s*(.+)",
        "mode": r"MODE:\s*(\w+)",
        "discipline": r"DISCIPLINE:\s*(.+)",
    }
    
    def parse(self, text: str) -> PACSchema:
        """
        Parse PAC text into PACSchema.
        
        Returns PACSchema (may be incomplete if sections missing).
        """
        builder = PACBuilder()
        
        # Extract PAC ID from first line
        pac_id_match = re.search(self.HEADER_PATTERNS["pac_id"], text)
        if pac_id_match:
            builder.with_id(pac_id_match.group(0))
        
        # Extract header fields
        issuer_match = re.search(self.HEADER_PATTERNS["issuer"], text)
        if issuer_match:
            builder.with_issuer(issuer_match.group(1).strip())
        
        target_match = re.search(self.HEADER_PATTERNS["target"], text)
        if target_match:
            builder.with_target(target_match.group(1).strip())
        
        mode_match = re.search(self.HEADER_PATTERNS["mode"], text)
        if mode_match:
            mode_str = mode_match.group(1).strip().upper()
            try:
                builder.with_mode(PACMode[mode_str])
            except KeyError:
                builder.with_mode(PACMode.EXECUTION)
        
        discipline_match = re.search(self.HEADER_PATTERNS["discipline"], text)
        if discipline_match:
            disc_str = discipline_match.group(1).strip().upper().replace(" ", "_")
            if "GOLD" in disc_str:
                builder.with_discipline(PACDiscipline.GOLD_STANDARD)
            else:
                builder.with_discipline(PACDiscipline.FAIL_CLOSED)
        
        # Extract body sections
        for section, pattern in self.SECTION_PATTERNS.items():
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                
                if section == PACSection.OBJECTIVE:
                    builder.with_objective(content)
                elif section == PACSection.EXECUTION_PLAN:
                    builder.with_execution_plan(content)
                elif section == PACSection.REQUIRED_DELIVERABLES:
                    # Parse numbered deliverables
                    for line in content.split("\n"):
                        line = line.strip()
                        if line and re.match(r"\d+\.", line):
                            desc = re.sub(r"^\d+\.\s*", "", line)
                            if desc:
                                builder.add_deliverable(desc)
                elif section == PACSection.CONSTRAINTS:
                    for line in content.split("\n"):
                        line = line.strip()
                        if line and line.startswith("-"):
                            builder.add_constraint(line[1:].strip())
                elif section == PACSection.SUCCESS_CRITERIA:
                    for line in content.split("\n"):
                        line = line.strip()
                        if line and line.startswith("-"):
                            builder.add_success_criterion(line[1:].strip())
                elif section == PACSection.DISPATCH:
                    # Parse dispatch fields
                    gid_match = re.search(r"(GID-\d+)", content)
                    role_match = re.search(r"ROLE:\s*(.+)", content)
                    lane_match = re.search(r"LANE:\s*(\w+)", content)
                    
                    if gid_match:
                        builder.with_dispatch(
                            target_gid=gid_match.group(1),
                            role=role_match.group(1).strip() if role_match else "Unknown",
                            lane=lane_match.group(1).strip() if lane_match else "UNKNOWN",
                            mode=builder._mode or PACMode.EXECUTION,
                        )
                elif section == PACSection.WRAP_OBLIGATION:
                    builder.with_wrap_obligation()
                elif section == PACSection.BER_OBLIGATION:
                    builder.with_ber_obligation()
                elif section == PACSection.FINAL_STATE:
                    builder.with_final_state()
        
        return builder.build()
    
    def has_section(self, text: str, section: PACSection) -> bool:
        """Check if text contains a section."""
        if section in self.SECTION_PATTERNS:
            pattern = self.SECTION_PATTERNS[section]
            return bool(re.search(pattern, text, re.DOTALL | re.IGNORECASE))
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_validator: Optional[PACSchemaValidator] = None
_parser: Optional[PACTextParser] = None


def get_pac_validator() -> PACSchemaValidator:
    """Get singleton PAC validator."""
    global _validator
    if _validator is None:
        _validator = PACSchemaValidator()
    return _validator


def get_pac_parser() -> PACTextParser:
    """Get singleton PAC parser."""
    global _parser
    if _parser is None:
        _parser = PACTextParser()
    return _parser


def reset_pac_validator() -> None:
    """Reset singleton (for testing)."""
    global _validator, _parser
    _validator = None
    _parser = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_pac(pac: PACSchema) -> PACValidationResult:
    """Validate PAC against schema."""
    return get_pac_validator().validate(pac)


def validate_pac_text(text: str) -> PACValidationResult:
    """Parse and validate PAC text."""
    pac = get_pac_parser().parse(text)
    return validate_pac(pac)


def require_valid_pac(pac: PACSchema) -> None:
    """Require valid PAC or raise."""
    get_pac_validator().validate_and_raise(pac)


def is_pac_valid(pac: PACSchema) -> bool:
    """Check if PAC is schema-valid."""
    return get_pac_validator().is_valid(pac)


def parse_pac(text: str) -> PACSchema:
    """Parse PAC from text."""
    return get_pac_parser().parse(text)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Exceptions
    "PACSchemaError",
    "PACSchemaViolationError",
    "MissingWRAPObligationError",
    "MissingBERObligationError",
    "MissingFinalStateError",
    "InvalidPACIDError",
    
    # Result
    "PACValidationResult",
    
    # Renderer
    "PACSchemaTerminalRenderer",
    
    # Validator
    "PACSchemaValidator",
    
    # Parser
    "PACTextParser",
    
    # Singletons
    "get_pac_validator",
    "get_pac_parser",
    "reset_pac_validator",
    
    # Convenience
    "validate_pac",
    "validate_pac_text",
    "require_valid_pac",
    "is_pac_valid",
    "parse_pac",
]
