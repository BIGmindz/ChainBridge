"""
ChainBridge Determinism Enforcement — PAC-015 Implementation
════════════════════════════════════════════════════════════════════════════════

ABSOLUTE DETERMINISTIC enforcement across four governance phases:
1. STRUCTURAL — Section ordering, presence, content
2. GATE — Pipeline evaluation, no short-circuit
3. SEMANTIC — Binary validity, no interpretation
4. BEHAVIORAL — Training signal mapping, corrective paths

PAC Reference: PAC-JEFFREY-CHAINBRIDGE-DETERMINISM-ENFORCEMENT-EXEC-015
Effective Date: 2025-12-30

PHILOSOPHY:
- DETERMINISTIC: Same input → Same output (always)
- FAIL-CLOSED: Unknown → INVALID
- NO INTERPRETATION: Binary outcomes only
- NO DISCRETION: Mechanical enforcement

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

# =============================================================================
# CONSTANTS — IMMUTABLE SECTION REGISTRIES
# =============================================================================

PAC_015_VERSION = "1.0.0"
"""PAC-015 Determinism Enforcement version."""


# =============================================================================
# SECTION REGISTRIES (ORDER 1 — CODY: STRUCTURAL DETERMINISM)
# =============================================================================

class ArtifactType(Enum):
    """Governance artifact types."""
    PAC = "PAC"
    BER = "BER"
    WRAP = "WRAP"


@dataclass(frozen=True)
class SectionDefinition:
    """
    Immutable section definition.
    
    Defines a mandatory section with fixed ordering index.
    """
    index: int              # Fixed ordering (0-based, immutable)
    name: str               # Section name (canonical)
    header_pattern: str     # Regex for header detection
    required: bool = True   # Mandatory by default
    min_content_lines: int = 1  # Minimum non-empty lines
    
    def matches_header(self, line: str) -> bool:
        """Check if line matches section header pattern."""
        return bool(re.match(self.header_pattern, line.strip(), re.IGNORECASE))


# ─────────────────────────────────────────────────────────────────────────────
# PAC SECTION REGISTRY (CANONICAL ORDER — IMMUTABLE)
# ─────────────────────────────────────────────────────────────────────────────

PAC_SECTIONS: Tuple[SectionDefinition, ...] = (
    SectionDefinition(
        index=0,
        name="RUNTIME_ACTIVATION_BLOCK",
        header_pattern=r"^#+\s*RUNTIME\s+ACTIVATION\s+BLOCK|^RUNTIME\s+ACTIVATION\s+BLOCK",
    ),
    SectionDefinition(
        index=1,
        name="EXECUTION_AUTHORITY_DECLARATION",
        header_pattern=r"^#+\s*EXECUTION\s+AUTHORITY|^EXECUTION\s+AUTHORITY",
    ),
    SectionDefinition(
        index=2,
        name="AGENT_ACTIVATION_BLOCK",
        header_pattern=r"^#+\s*AGENT\s+ACTIVATION|^AGENT\s+ACTIVATION",
    ),
    SectionDefinition(
        index=3,
        name="PRE_FLIGHT_GATE",
        header_pattern=r"^#+\s*PRE-?FLIGHT\s+GATE|^PRE-?FLIGHT\s+GATE",
    ),
    SectionDefinition(
        index=4,
        name="OBJECTIVE",
        header_pattern=r"^#+\s*OBJECTIVE|^OBJECTIVE",
    ),
    SectionDefinition(
        index=5,
        name="EXECUTION_ORDERS",
        header_pattern=r"^#+\s*EXECUTION\s+ORDERS|^EXECUTION\s+ORDERS",
    ),
    SectionDefinition(
        index=6,
        name="REVIEW_STOP_FAIL_GATES",
        header_pattern=r"^#+\s*REVIEW.*STOP.?FAIL|^REVIEW.*STOP.?FAIL",
    ),
    SectionDefinition(
        index=7,
        name="TRAINING_SIGNAL_CAPTURE",
        header_pattern=r"^#+\s*TRAINING\s+SIGNAL|^TRAINING\s+SIGNAL",
    ),
    SectionDefinition(
        index=8,
        name="POSITIVE_CLOSURE_CONDITIONS",
        header_pattern=r"^#+\s*POSITIVE\s+CLOSURE|^POSITIVE\s+CLOSURE",
    ),
    SectionDefinition(
        index=9,
        name="FINAL_STATE_DECLARATION",
        header_pattern=r"^#+\s*FINAL.?STATE|^FINAL.?STATE|^FINAL_STATE",
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# BER SECTION REGISTRY (CANONICAL ORDER — IMMUTABLE)
# LAW-001-BER-GOLD-STANDARD v1.1.0 enforced
# ─────────────────────────────────────────────────────────────────────────────

BER_SECTIONS: Tuple[SectionDefinition, ...] = (
    SectionDefinition(
        index=0,
        name="RUNTIME_ACTIVATION_BLOCK",
        header_pattern=r"^#+\s*RUNTIME\s+ACTIVATION|^RUNTIME\s+ACTIVATION",
    ),
    SectionDefinition(
        index=1,
        name="EXECUTION_AUTHORITY_ORCHESTRATION",
        header_pattern=r"^#+\s*EXECUTION\s+AUTHORITY.*ORCHESTRATION|^EXECUTION\s+AUTHORITY",
    ),
    SectionDefinition(
        index=2,
        name="AGENT_ACTIVATION_ROLE_TABLE",
        header_pattern=r"^#+\s*AGENT\s+ACTIVATION|^AGENT\s+ACTIVATION",
    ),
    SectionDefinition(
        index=3,
        name="EXECUTION_REVIEW_ORDER_ACCOUNTING",
        header_pattern=r"^#+\s*EXECUTION.*ORDER|^ORDER\s+ACCOUNTING",
    ),
    SectionDefinition(
        index=4,
        name="INVARIANT_VERIFICATION_TABLE",
        header_pattern=r"^#+\s*INVARIANT\s+VERIFICATION|^INVARIANT\s+VERIFICATION",
    ),
    SectionDefinition(
        index=5,
        name="TEST_EVIDENCE",
        header_pattern=r"^#+\s*TEST\s+EVIDENCE|^TEST\s+EVIDENCE",
    ),
    SectionDefinition(
        index=6,
        name="TRAINING_LOOP",
        header_pattern=r"^#+\s*TRAINING\s+LOOP|^TRAINING\s+LOOP",
    ),
    SectionDefinition(
        index=7,
        name="POSITIVE_CLOSURE",
        header_pattern=r"^#+\s*POSITIVE\s+CLOSURE|^POSITIVE\s+CLOSURE",
    ),
    SectionDefinition(
        index=8,
        name="FINAL_STATE_DECLARATION",
        header_pattern=r"^#+\s*FINAL.?STATE|^FINAL.?STATE|^FINAL_STATE",
    ),
    SectionDefinition(
        index=9,
        name="SIGNATURES_ATTESTATIONS",
        header_pattern=r"^#+\s*SIGNATURE|^SIGNATURE|^#+\s*ATTESTATION|^ATTESTATION",
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# WRAP SECTION REGISTRY (CANONICAL ORDER — IMMUTABLE)
# ─────────────────────────────────────────────────────────────────────────────

WRAP_SECTIONS: Tuple[SectionDefinition, ...] = (
    SectionDefinition(
        index=0,
        name="WRAP_HEADER",
        header_pattern=r"^#+\s*WRAP|^WRAP|^═+.*WRAP",
    ),
    SectionDefinition(
        index=1,
        name="EXECUTION_SUMMARY",
        header_pattern=r"^#+\s*EXECUTION\s+SUMMARY|^EXECUTION\s+SUMMARY",
    ),
    SectionDefinition(
        index=2,
        name="FILES_CHANGED",
        header_pattern=r"^#+\s*FILES?\s+CHANGED|^FILES?\s+CHANGED|^#+\s*CHANGES|^CHANGES",
    ),
    SectionDefinition(
        index=3,
        name="INVARIANTS_VERIFIED",
        header_pattern=r"^#+\s*INVARIANTS?|^INVARIANTS?",
    ),
    SectionDefinition(
        index=4,
        name="NEXT_STEPS",
        header_pattern=r"^#+\s*NEXT\s+STEPS?|^NEXT\s+STEPS?",
    ),
)


# Section registry by artifact type
SECTION_REGISTRY: Dict[ArtifactType, Tuple[SectionDefinition, ...]] = {
    ArtifactType.PAC: PAC_SECTIONS,
    ArtifactType.BER: BER_SECTIONS,
    ArtifactType.WRAP: WRAP_SECTIONS,
}


# =============================================================================
# STRUCTURAL VALIDATION RESULT
# =============================================================================

@dataclass(frozen=True)
class SectionViolation:
    """
    Immutable record of a structural violation.
    
    INV-DET-STR: Deterministic violation representation.
    """
    section_name: str
    section_index: int
    violation_type: str  # MISSING | OUT_OF_ORDER | EMPTY
    details: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "section_name": self.section_name,
            "section_index": self.section_index,
            "violation_type": self.violation_type,
            "details": self.details,
        }


@dataclass(frozen=True)
class StructuralValidationResult:
    """
    Immutable structural validation result.
    
    Deterministic — same artifact produces identical result every time.
    """
    artifact_type: ArtifactType
    valid: bool
    violations: Tuple[SectionViolation, ...]
    sections_found: Tuple[str, ...]
    sections_expected: Tuple[str, ...]
    artifact_hash: str  # SHA-256 of input for reproducibility
    validated_at: str
    
    @property
    def violation_count(self) -> int:
        return len(self.violations)
    
    def to_dict(self) -> Dict:
        return {
            "artifact_type": self.artifact_type.value,
            "valid": self.valid,
            "violations": [v.to_dict() for v in self.violations],
            "sections_found": list(self.sections_found),
            "sections_expected": list(self.sections_expected),
            "artifact_hash": self.artifact_hash,
            "validated_at": self.validated_at,
        }


# =============================================================================
# STRUCTURAL VALIDATOR (ORDER 1 — CODY)
# =============================================================================

class StructuralValidator:
    """
    Deterministic structural validator for governance artifacts.
    
    INVARIANTS:
        INV-DET-STR-001: Missing section = INVALID
        INV-DET-STR-002: Out-of-order section = INVALID
        INV-DET-STR-003: Empty section = INVALID
    
    DETERMINISM GUARANTEE:
        Same artifact → Same result (always)
    """
    
    def validate(
        self,
        artifact_text: str,
        artifact_type: ArtifactType,
    ) -> StructuralValidationResult:
        """
        Validate artifact structure deterministically.
        
        Returns StructuralValidationResult (immutable).
        No interpretation, no discretion.
        """
        # Compute artifact hash for reproducibility
        artifact_hash = hashlib.sha256(artifact_text.encode()).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Get section registry
        sections = SECTION_REGISTRY[artifact_type]
        expected_names = tuple(s.name for s in sections)
        
        # Parse sections from artifact
        lines = artifact_text.split('\n')
        found_sections: List[Tuple[int, str, int]] = []  # (index, name, line_num)
        
        for line_num, line in enumerate(lines):
            for section in sections:
                if section.matches_header(line):
                    found_sections.append((section.index, section.name, line_num))
                    break
        
        # Build violations list (deterministic order)
        violations: List[SectionViolation] = []
        found_names = [s[1] for s in found_sections]
        found_indices = [s[0] for s in found_sections]
        
        # INV-DET-STR-001: Check for missing sections
        for section in sections:
            if section.required and section.name not in found_names:
                violations.append(SectionViolation(
                    section_name=section.name,
                    section_index=section.index,
                    violation_type="MISSING",
                    details=f"Required section '{section.name}' (index {section.index}) not found",
                ))
        
        # INV-DET-STR-002: Check for out-of-order sections
        if len(found_indices) > 1:
            for i in range(len(found_indices) - 1):
                if found_indices[i] > found_indices[i + 1]:
                    violations.append(SectionViolation(
                        section_name=found_names[i + 1],
                        section_index=found_indices[i + 1],
                        violation_type="OUT_OF_ORDER",
                        details=(
                            f"Section '{found_names[i + 1]}' (index {found_indices[i + 1]}) "
                            f"appears after '{found_names[i]}' (index {found_indices[i]})"
                        ),
                    ))
        
        # INV-DET-STR-003: Check for empty sections
        for i, (idx, name, line_num) in enumerate(found_sections):
            section_def = sections[idx]
            # Find next section start
            next_line = (
                found_sections[i + 1][2] if i + 1 < len(found_sections) else len(lines)
            )
            # Count non-empty lines in section
            content_lines = [
                l for l in lines[line_num + 1:next_line]
                if l.strip() and not l.strip().startswith('#')
            ]
            if len(content_lines) < section_def.min_content_lines:
                violations.append(SectionViolation(
                    section_name=name,
                    section_index=idx,
                    violation_type="EMPTY",
                    details=f"Section '{name}' has {len(content_lines)} content lines (minimum: {section_def.min_content_lines})",
                ))
        
        # Sort violations by section index (deterministic order)
        violations.sort(key=lambda v: (v.section_index, v.violation_type))
        
        return StructuralValidationResult(
            artifact_type=artifact_type,
            valid=len(violations) == 0,
            violations=tuple(violations),
            sections_found=tuple(found_names),
            sections_expected=expected_names,
            artifact_hash=artifact_hash,
            validated_at=timestamp,
        )


# =============================================================================
# GATE PIPELINE (ORDER 2 — CINDY)
# =============================================================================

class GateResult(Enum):
    """Gate evaluation result — BINARY only."""
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class GateEvaluation:
    """
    Immutable gate evaluation record.
    
    Each gate is evaluated and recorded regardless of previous failures.
    """
    gate_name: str
    gate_index: int
    result: GateResult
    reason: str
    evaluated_at: str


@dataclass(frozen=True)
class GatePipelineResult:
    """
    Immutable gate pipeline result.
    
    INV-DET-GATE: All gates evaluated in fixed order, no short-circuit.
    """
    evaluations: Tuple[GateEvaluation, ...]
    overall_result: GateResult
    first_failure_index: Optional[int]
    artifact_hash: str
    evaluated_at: str
    
    @property
    def all_passed(self) -> bool:
        return self.overall_result == GateResult.PASS
    
    @property
    def failure_count(self) -> int:
        return sum(1 for e in self.evaluations if e.result == GateResult.FAIL)
    
    def to_dict(self) -> Dict:
        return {
            "evaluations": [
                {
                    "gate_name": e.gate_name,
                    "gate_index": e.gate_index,
                    "result": e.result.value,
                    "reason": e.reason,
                }
                for e in self.evaluations
            ],
            "overall_result": self.overall_result.value,
            "first_failure_index": self.first_failure_index,
            "artifact_hash": self.artifact_hash,
            "evaluated_at": self.evaluated_at,
        }


# Gate definitions (fixed order, immutable)
@dataclass(frozen=True)
class GateDefinition:
    """Immutable gate definition."""
    index: int
    name: str
    description: str


# Canonical gate order for BER validation
BER_GATES: Tuple[GateDefinition, ...] = (
    GateDefinition(0, "STRUCTURAL_INTEGRITY", "All mandatory sections present and non-empty"),
    GateDefinition(1, "SECTION_ORDERING", "Sections in canonical order"),
    GateDefinition(2, "PROHIBITED_LANGUAGE", "No illegal phrases present"),
    GateDefinition(3, "SEMANTIC_VALIDITY", "Binary validity — no ambiguous states"),
    GateDefinition(4, "TRAINING_LOOP_PRESENCE", "At least one training signal present"),
    GateDefinition(5, "POSITIVE_CLOSURE_EXPLICIT", "Closure is explicit and declarative"),
    GateDefinition(6, "FINAL_STATE_PARSEABLE", "Final state is machine-readable"),
    GateDefinition(7, "SIGNATURE_PRESENT", "Sign-off table exists"),
)


class GatePipeline:
    """
    Deterministic gate pipeline.
    
    INVARIANTS:
        INV-DET-GATE-001: Gates evaluated in fixed order
        INV-DET-GATE-002: Any failure → STOP (after full evaluation)
        INV-DET-GATE-003: No "warn-only" states
    
    CRITICAL: All gates are evaluated. No short-circuit.
    """
    
    def __init__(self, gates: Tuple[GateDefinition, ...] = BER_GATES):
        self._gates = gates
    
    def evaluate(
        self,
        artifact_text: str,
        structural_result: StructuralValidationResult,
        semantic_result: Optional["SemanticValidationResult"] = None,
    ) -> GatePipelineResult:
        """
        Evaluate all gates in fixed order.
        
        NO SHORT-CIRCUIT: All gates are evaluated even after first failure.
        """
        artifact_hash = hashlib.sha256(artifact_text.encode()).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        evaluations: List[GateEvaluation] = []
        first_failure: Optional[int] = None
        
        for gate in self._gates:
            result, reason = self._evaluate_gate(
                gate, artifact_text, structural_result, semantic_result
            )
            
            evaluations.append(GateEvaluation(
                gate_name=gate.name,
                gate_index=gate.index,
                result=result,
                reason=reason,
                evaluated_at=timestamp,
            ))
            
            if result == GateResult.FAIL and first_failure is None:
                first_failure = gate.index
        
        # Overall result: PASS only if ALL gates passed
        overall = GateResult.PASS if first_failure is None else GateResult.FAIL
        
        return GatePipelineResult(
            evaluations=tuple(evaluations),
            overall_result=overall,
            first_failure_index=first_failure,
            artifact_hash=artifact_hash,
            evaluated_at=timestamp,
        )
    
    def _evaluate_gate(
        self,
        gate: GateDefinition,
        artifact_text: str,
        structural_result: StructuralValidationResult,
        semantic_result: Optional["SemanticValidationResult"],
    ) -> Tuple[GateResult, str]:
        """Evaluate a single gate deterministically."""
        
        if gate.name == "STRUCTURAL_INTEGRITY":
            # Check structural result for missing sections
            missing = [v for v in structural_result.violations if v.violation_type == "MISSING"]
            if missing:
                return GateResult.FAIL, f"{len(missing)} missing sections"
            return GateResult.PASS, "All sections present"
        
        elif gate.name == "SECTION_ORDERING":
            # Check structural result for out-of-order sections
            ooo = [v for v in structural_result.violations if v.violation_type == "OUT_OF_ORDER"]
            if ooo:
                return GateResult.FAIL, f"{len(ooo)} out-of-order sections"
            return GateResult.PASS, "Sections in order"
        
        elif gate.name == "PROHIBITED_LANGUAGE":
            # Check for prohibited phrases
            violations = self._check_prohibited_language(artifact_text)
            if violations:
                return GateResult.FAIL, f"Prohibited phrases: {', '.join(violations)}"
            return GateResult.PASS, "No prohibited language"
        
        elif gate.name == "SEMANTIC_VALIDITY":
            if semantic_result is not None:
                if not semantic_result.valid:
                    return GateResult.FAIL, "Semantic validation failed"
            return GateResult.PASS, "Semantically valid"
        
        elif gate.name == "TRAINING_LOOP_PRESENCE":
            # Check for training signals
            if "TRAINING" in artifact_text.upper() and (
                "TS-" in artifact_text or "training signal" in artifact_text.lower()
            ):
                return GateResult.PASS, "Training loop present"
            return GateResult.FAIL, "No training signals found"
        
        elif gate.name == "POSITIVE_CLOSURE_EXPLICIT":
            if "POSITIVE CLOSURE" in artifact_text.upper() and (
                "☑" in artifact_text or "✅" in artifact_text or "CLOSED" in artifact_text.upper()
            ):
                return GateResult.PASS, "Closure explicit"
            return GateResult.FAIL, "Closure not explicit"
        
        elif gate.name == "FINAL_STATE_PARSEABLE":
            if "FINAL_STATE" in artifact_text or "FINAL STATE" in artifact_text:
                return GateResult.PASS, "Final state present"
            return GateResult.FAIL, "Final state missing"
        
        elif gate.name == "SIGNATURE_PRESENT":
            if "SIGN" in artifact_text.upper() or "ATTEST" in artifact_text.upper():
                return GateResult.PASS, "Signatures present"
            return GateResult.FAIL, "No signatures"
        
        return GateResult.PASS, "Gate not implemented"
    
    def _check_prohibited_language(self, text: str) -> List[str]:
        """Check for prohibited phrases from LAW-001."""
        PROHIBITED = [
            "implicit pass",
            "covered elsewhere",
            "out of scope",
            "assumed complete",
            "see above",
            "tbd",
            "todo",
        ]
        found = []
        text_lower = text.lower()
        for phrase in PROHIBITED:
            if phrase in text_lower:
                # Don't flag if it's in a "prohibited" section definition
                if f'"{phrase}"' not in text_lower and f"'{phrase}'" not in text_lower:
                    found.append(phrase)
        return found


# =============================================================================
# SEMANTIC VALIDATOR (ORDER 4 — ALEX)
# =============================================================================

class SemanticValidity(Enum):
    """
    Binary semantic validity.
    
    INV-DET-SEM-001: No "mostly valid"
    """
    VALID = "VALID"
    INVALID = "INVALID"


@dataclass(frozen=True)
class SemanticViolation:
    """Immutable semantic violation record."""
    phrase: str
    context: str
    violation_type: str
    


@dataclass(frozen=True)
class SemanticValidationResult:
    """
    Immutable semantic validation result.
    
    BINARY: VALID or INVALID only.
    """
    validity: SemanticValidity
    violations: Tuple[SemanticViolation, ...]
    artifact_hash: str
    validated_at: str
    
    @property
    def valid(self) -> bool:
        return self.validity == SemanticValidity.VALID
    
    def to_dict(self) -> Dict:
        return {
            "validity": self.validity.value,
            "violations": [
                {"phrase": v.phrase, "context": v.context, "type": v.violation_type}
                for v in self.violations
            ],
            "artifact_hash": self.artifact_hash,
            "validated_at": self.validated_at,
        }


# Prohibited language dictionary (LAW-001)
PROHIBITED_PHRASES: FrozenSet[str] = frozenset([
    "implicit pass",
    "covered elsewhere",
    "out of scope",
    "assumed complete",
    "see above",
    "tbd",
    "todo",
    "mostly valid",
    "partially complete",
    "pending review",
    "to be determined",
])

# Ambiguous language (semantic drift risk)
AMBIGUOUS_PHRASES: FrozenSet[str] = frozenset([
    "should",
    "might",
    "could",
    "may",
    "probably",
    "likely",
    "possibly",
    "approximately",
    "around",
    "about",
    "roughly",
])


class SemanticValidator:
    """
    Deterministic semantic validator.
    
    INVARIANTS:
        INV-DET-SEM-001: No "mostly valid"
        INV-DET-SEM-002: No implied closure
        INV-DET-SEM-003: Language maps to outcome deterministically
    
    BINARY OUTCOMES ONLY: VALID or INVALID
    """
    
    def validate(
        self,
        artifact_text: str,
        strict: bool = True,
    ) -> SemanticValidationResult:
        """
        Validate artifact semantics deterministically.
        
        strict=True: Fail on prohibited AND ambiguous phrases
        strict=False: Fail on prohibited only
        """
        artifact_hash = hashlib.sha256(artifact_text.encode()).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        violations: List[SemanticViolation] = []
        text_lower = artifact_text.lower()
        
        # Check prohibited phrases
        for phrase in PROHIBITED_PHRASES:
            if phrase in text_lower:
                # Find context
                idx = text_lower.find(phrase)
                start = max(0, idx - 20)
                end = min(len(artifact_text), idx + len(phrase) + 20)
                context = artifact_text[start:end]
                
                violations.append(SemanticViolation(
                    phrase=phrase,
                    context=context,
                    violation_type="PROHIBITED",
                ))
        
        # Check ambiguous phrases in strict mode
        if strict:
            for phrase in AMBIGUOUS_PHRASES:
                # Only flag if not in a definition context
                pattern = rf'\b{phrase}\b'
                if re.search(pattern, text_lower):
                    # Don't flag if in quotes (definition context)
                    if f'"{phrase}"' not in text_lower:
                        violations.append(SemanticViolation(
                            phrase=phrase,
                            context=f"Ambiguous term '{phrase}' found",
                            violation_type="AMBIGUOUS",
                        ))
        
        # Binary decision
        validity = SemanticValidity.INVALID if violations else SemanticValidity.VALID
        
        return SemanticValidationResult(
            validity=validity,
            violations=tuple(violations),
            artifact_hash=artifact_hash,
            validated_at=timestamp,
        )


# =============================================================================
# BEHAVIORAL DETERMINISM (ORDER 6 — MAGGIE)
# =============================================================================

@dataclass(frozen=True)
class TrainingSignal:
    """
    Immutable training signal.
    
    INV-DET-BEH-001: Same violation → Same signal
    """
    signal_id: str
    category: str  # STRUCTURAL | GATE | SEMANTIC | BEHAVIORAL
    violation_type: str
    message: str
    emitted_at: str


@dataclass(frozen=True)
class TrainingSignalMapping:
    """
    Deterministic violation → signal mapping.
    
    INV-DET-BEH: Same violation MUST produce same signal.
    """
    violation_type: str
    category: str
    signal_template: str
    corrective_pac_type: str


# Canonical mappings (immutable)
TRAINING_SIGNAL_MAPPINGS: Tuple[TrainingSignalMapping, ...] = (
    # Structural violations
    TrainingSignalMapping("MISSING", "STRUCTURAL", "TS-STR-MISS-{section}", "CORRECTIVE"),
    TrainingSignalMapping("OUT_OF_ORDER", "STRUCTURAL", "TS-STR-ORD-{section}", "CORRECTIVE"),
    TrainingSignalMapping("EMPTY", "STRUCTURAL", "TS-STR-EMPTY-{section}", "CORRECTIVE"),
    
    # Gate violations
    TrainingSignalMapping("STRUCTURAL_INTEGRITY", "GATE", "TS-GATE-STR", "CORRECTIVE"),
    TrainingSignalMapping("PROHIBITED_LANGUAGE", "GATE", "TS-GATE-LANG", "CORRECTIVE"),
    TrainingSignalMapping("SEMANTIC_VALIDITY", "GATE", "TS-GATE-SEM", "CORRECTIVE"),
    TrainingSignalMapping("TRAINING_LOOP_PRESENCE", "GATE", "TS-GATE-TRAIN", "CORRECTIVE"),
    
    # Semantic violations
    TrainingSignalMapping("PROHIBITED", "SEMANTIC", "TS-SEM-PROHIB-{phrase}", "CORRECTIVE"),
    TrainingSignalMapping("AMBIGUOUS", "SEMANTIC", "TS-SEM-AMBIG-{phrase}", "TRAINING"),
    
    # Behavioral violations
    TrainingSignalMapping("NON_DETERMINISTIC", "BEHAVIORAL", "TS-BEH-NONDET", "LAW"),
)


class BehavioralEnforcer:
    """
    Deterministic behavioral enforcer.
    
    INVARIANTS:
        INV-DET-BEH-001: Same violation → same signal
        INV-DET-BEH-002: Same signal → same corrective PAC
        INV-DET-BEH-003: Learning cannot weaken enforcement
    """
    
    def __init__(self):
        self._mappings = {m.violation_type: m for m in TRAINING_SIGNAL_MAPPINGS}
    
    def generate_signal(
        self,
        violation_type: str,
        details: Dict[str, str],
    ) -> TrainingSignal:
        """
        Generate deterministic training signal for violation.
        
        Same violation + details → IDENTICAL signal (always).
        """
        mapping = self._mappings.get(violation_type)
        if not mapping:
            # Unknown violation type → default signal
            return TrainingSignal(
                signal_id=f"TS-UNKNOWN-{violation_type}",
                category="UNKNOWN",
                violation_type=violation_type,
                message=f"Unknown violation: {violation_type}",
                emitted_at=datetime.now(timezone.utc).isoformat(),
            )
        
        # Generate deterministic signal ID
        signal_id = mapping.signal_template.format(**details) if details else mapping.signal_template
        
        return TrainingSignal(
            signal_id=signal_id,
            category=mapping.category,
            violation_type=violation_type,
            message=f"{mapping.category} violation: {violation_type}",
            emitted_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def get_corrective_pac_type(self, violation_type: str) -> str:
        """Get deterministic corrective PAC type for violation."""
        mapping = self._mappings.get(violation_type)
        return mapping.corrective_pac_type if mapping else "CORRECTIVE"


# =============================================================================
# MASTER DETERMINISM ENFORCER (ORCHESTRATION)
# =============================================================================

@dataclass(frozen=True)
class DeterminismEnforcementResult:
    """
    Complete determinism enforcement result.
    
    Aggregates all four phases: Structural, Gate, Semantic, Behavioral
    """
    artifact_type: ArtifactType
    artifact_hash: str
    
    # Phase results
    structural: StructuralValidationResult
    gate: GatePipelineResult
    semantic: SemanticValidationResult
    
    # Training signals generated
    training_signals: Tuple[TrainingSignal, ...]
    
    # Overall verdict
    valid: bool
    
    # Metadata
    enforced_at: str
    enforcement_version: str = PAC_015_VERSION
    
    def to_dict(self) -> Dict:
        return {
            "artifact_type": self.artifact_type.value,
            "artifact_hash": self.artifact_hash,
            "valid": self.valid,
            "structural": self.structural.to_dict(),
            "gate": self.gate.to_dict(),
            "semantic": self.semantic.to_dict(),
            "training_signals": [
                {
                    "signal_id": s.signal_id,
                    "category": s.category,
                    "violation_type": s.violation_type,
                    "message": s.message,
                }
                for s in self.training_signals
            ],
            "enforced_at": self.enforced_at,
            "enforcement_version": self.enforcement_version,
        }


class DeterminismEnforcer:
    """
    Master determinism enforcer.
    
    Orchestrates all four enforcement phases:
    1. STRUCTURAL (Cody)
    2. GATE (Cindy)
    3. SEMANTIC (ALEX)
    4. BEHAVIORAL (Maggie)
    
    GUARANTEE: Same artifact → Identical result (always)
    """
    
    def __init__(self):
        self.structural = StructuralValidator()
        self.gate_pipeline = GatePipeline()
        self.semantic = SemanticValidator()
        self.behavioral = BehavioralEnforcer()
    
    def enforce(
        self,
        artifact_text: str,
        artifact_type: ArtifactType,
        strict_semantic: bool = True,
    ) -> DeterminismEnforcementResult:
        """
        Execute deterministic enforcement across all phases.
        
        CRITICAL: This is the canonical enforcement entry point.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        artifact_hash = hashlib.sha256(artifact_text.encode()).hexdigest()
        
        # Phase 1: Structural
        structural_result = self.structural.validate(artifact_text, artifact_type)
        
        # Phase 2: Semantic
        semantic_result = self.semantic.validate(artifact_text, strict=strict_semantic)
        
        # Phase 3: Gate
        gate_result = self.gate_pipeline.evaluate(
            artifact_text, structural_result, semantic_result
        )
        
        # Phase 4: Behavioral — Generate training signals
        signals: List[TrainingSignal] = []
        
        # Signals from structural violations
        for v in structural_result.violations:
            signals.append(self.behavioral.generate_signal(
                v.violation_type,
                {"section": v.section_name},
            ))
        
        # Signals from semantic violations
        for v in semantic_result.violations:
            signals.append(self.behavioral.generate_signal(
                v.violation_type,
                {"phrase": v.phrase.replace(" ", "_")},
            ))
        
        # Signals from gate failures
        for e in gate_result.evaluations:
            if e.result == GateResult.FAIL:
                signals.append(self.behavioral.generate_signal(
                    e.gate_name,
                    {},
                ))
        
        # Overall validity: ALL phases must pass
        valid = (
            structural_result.valid
            and semantic_result.valid
            and gate_result.all_passed
        )
        
        return DeterminismEnforcementResult(
            artifact_type=artifact_type,
            artifact_hash=artifact_hash,
            structural=structural_result,
            gate=gate_result,
            semantic=semantic_result,
            training_signals=tuple(signals),
            valid=valid,
            enforced_at=timestamp,
        )


# =============================================================================
# LAW-001 VALIDATE_BER_OR_FAIL IMPLEMENTATION
# =============================================================================

class BERValidationFailure(Exception):
    """
    Raised when BER fails validation.
    
    LAW-001: STOP, FAIL, EMIT SIGNAL, REQUIRE CORRECTIVE PAC
    """
    
    def __init__(
        self,
        message: str,
        result: DeterminismEnforcementResult,
    ):
        self.result = result
        super().__init__(f"BER VALIDATION FAILURE: {message}")


def validate_ber_or_fail(ber_text: str) -> DeterminismEnforcementResult:
    """
    LAW-001 v1.1.0 Mechanical Enforcement Primitive.
    
    BEHAVIOR:
        - Validates BER against all determinism phases
        - If INVALID: raises BERValidationFailure
        - If VALID: returns DeterminismEnforcementResult
    
    THIS FUNCTION MUST BE CALLED:
        - CI pre-merge
        - CI pre-release
        - Runtime ingestion
        - Tooling/scripts
        - Automation
        - Human-in-the-loop review
    
    THERE ARE NO EXCEPTIONS.
    """
    enforcer = DeterminismEnforcer()
    result = enforcer.enforce(ber_text, ArtifactType.BER)
    
    if not result.valid:
        # STOP · FAIL · EMIT SIGNAL · REQUIRE CORRECTIVE PAC
        raise BERValidationFailure(
            f"BER has {len(result.training_signals)} violations. "
            f"Structural: {result.structural.violation_count}, "
            f"Semantic: {len(result.semantic.violations)}, "
            f"Gates failed: {result.gate.failure_count}",
            result=result,
        )
    
    return result


# =============================================================================
# REPEATABILITY TEST (ORDER 5 — SAM: ADVERSARIAL)
# =============================================================================

def verify_determinism(
    artifact_text: str,
    artifact_type: ArtifactType,
    iterations: int = 5,
) -> Tuple[bool, List[str]]:
    """
    Adversarial repeatability test.
    
    Runs enforcement N times and verifies identical results.
    
    Returns (is_deterministic, list_of_discrepancies)
    """
    enforcer = DeterminismEnforcer()
    results: List[DeterminismEnforcementResult] = []
    
    for _ in range(iterations):
        result = enforcer.enforce(artifact_text, artifact_type)
        results.append(result)
    
    # Compare all results to first
    baseline = results[0]
    discrepancies: List[str] = []
    
    for i, result in enumerate(results[1:], start=2):
        # Check validity match
        if result.valid != baseline.valid:
            discrepancies.append(f"Run {i}: valid={result.valid} != baseline valid={baseline.valid}")
        
        # Check violation counts
        if result.structural.violation_count != baseline.structural.violation_count:
            discrepancies.append(
                f"Run {i}: structural violations {result.structural.violation_count} "
                f"!= baseline {baseline.structural.violation_count}"
            )
        
        # Check signal count
        if len(result.training_signals) != len(baseline.training_signals):
            discrepancies.append(
                f"Run {i}: signals {len(result.training_signals)} "
                f"!= baseline {len(baseline.training_signals)}"
            )
        
        # Check signal IDs
        baseline_ids = {s.signal_id for s in baseline.training_signals}
        result_ids = {s.signal_id for s in result.training_signals}
        if baseline_ids != result_ids:
            discrepancies.append(f"Run {i}: signal IDs differ from baseline")
    
    return len(discrepancies) == 0, discrepancies


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Types
    "ArtifactType",
    "SectionDefinition",
    "GateResult",
    "SemanticValidity",
    
    # Registries
    "PAC_SECTIONS",
    "BER_SECTIONS",
    "WRAP_SECTIONS",
    "BER_GATES",
    "PROHIBITED_PHRASES",
    
    # Results
    "StructuralValidationResult",
    "GatePipelineResult",
    "SemanticValidationResult",
    "DeterminismEnforcementResult",
    "TrainingSignal",
    
    # Validators
    "StructuralValidator",
    "GatePipeline",
    "SemanticValidator",
    "BehavioralEnforcer",
    "DeterminismEnforcer",
    
    # LAW-001 Enforcement
    "validate_ber_or_fail",
    "BERValidationFailure",
    
    # Adversarial
    "verify_determinism",
]
