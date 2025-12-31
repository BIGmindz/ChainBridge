"""
ChainBridge WRAP Schema Validator — Programmatic Enforcement
════════════════════════════════════════════════════════════════════════════════

WRAP (Work Record And Proof) validation is PROGRAMMATIC.
No conversational forgiveness.
Invalid WRAP → rejected BEFORE BER consideration.

PAC Reference: PAC-BENSON-CTO-EXEC-CODY-IDENTITY-MODE-LAW-011
Effective Date: 2025-12-26

WRAP STRUCTURE:
├── HEADER (identity declaration)
├── PROOF BLOCK (evidence of work)
├── DECISION BLOCK (actions taken)
├── OUTCOME BLOCK (results + metrics)
└── ATTESTATION (signature + timestamp)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .gid_registry import validate_agent_gid
from .mode_schema import ModeDeclaration, create_mode_declaration


# ═══════════════════════════════════════════════════════════════════════════════
# WRAP EXCEPTIONS — HARD FAIL
# ═══════════════════════════════════════════════════════════════════════════════

class WRAPValidationError(Exception):
    """Base exception for WRAP validation failures. HARD STOP."""
    pass


class WRAPMissingBlockError(WRAPValidationError):
    """Raised when a mandatory WRAP block is missing."""
    
    def __init__(self, block_name: str):
        self.block_name = block_name
        super().__init__(
            f"HARD FAIL: Mandatory WRAP block '{block_name}' is missing. "
            f"WRAP rejected before BER consideration."
        )


class WRAPMalformedBlockError(WRAPValidationError):
    """Raised when a WRAP block is malformed."""
    
    def __init__(self, block_name: str, reason: str):
        self.block_name = block_name
        self.reason = reason
        super().__init__(
            f"HARD FAIL: WRAP block '{block_name}' is malformed. "
            f"Reason: {reason}. WRAP rejected."
        )


class WRAPIdentityError(WRAPValidationError):
    """Raised when WRAP identity validation fails."""
    
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(
            f"HARD FAIL: WRAP identity validation failed. "
            f"Reason: {reason}. WRAP rejected."
        )


class WRAPProofError(WRAPValidationError):
    """Raised when WRAP proof block is insufficient."""
    
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(
            f"HARD FAIL: WRAP proof block insufficient. "
            f"Reason: {reason}. WRAP rejected."
        )


class WRAPSignatureError(WRAPValidationError):
    """Raised when WRAP attestation/signature is invalid."""
    
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(
            f"HARD FAIL: WRAP attestation invalid. "
            f"Reason: {reason}. WRAP rejected."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# WRAP BLOCK TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class WRAPBlockType(Enum):
    """Types of blocks in a WRAP."""
    
    HEADER = "HEADER"
    PROOF = "PROOF"
    DECISION = "DECISION"
    OUTCOME = "OUTCOME"
    ATTESTATION = "ATTESTATION"


# Mandatory blocks
MANDATORY_BLOCKS = frozenset([
    WRAPBlockType.HEADER,
    WRAPBlockType.PROOF,
    WRAPBlockType.DECISION,
    WRAPBlockType.OUTCOME,
    WRAPBlockType.ATTESTATION,
])


# ═══════════════════════════════════════════════════════════════════════════════
# WRAP DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class WRAPHeader:
    """WRAP header block — identity declaration."""
    
    wrap_id: str
    pac_id: str
    gid: str
    role: str
    mode: str
    execution_lane: str
    discipline: str = "FAIL-CLOSED"
    governance_mode: str = "GOLD_STANDARD"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class WRAPProof:
    """WRAP proof block — evidence of work."""
    
    artifacts_created: Tuple[str, ...]
    artifacts_modified: Tuple[str, ...]
    commands_executed: Tuple[str, ...]
    tests_run: Tuple[str, ...]
    verification_steps: Tuple[str, ...]
    
    @property
    def total_artifacts(self) -> int:
        return len(self.artifacts_created) + len(self.artifacts_modified)
    
    @property
    def has_verification(self) -> bool:
        return len(self.verification_steps) > 0


@dataclass(frozen=True)
class WRAPDecision:
    """WRAP decision block — actions taken."""
    
    action_summary: str
    rationale: str
    alternatives_considered: Tuple[str, ...]
    constraints_honored: Tuple[str, ...]
    deferred_items: Tuple[str, ...]


@dataclass(frozen=True)
class WRAPOutcome:
    """WRAP outcome block — results and metrics."""
    
    status: str  # COMPLETE, PARTIAL, BLOCKED
    deliverables: Tuple[str, ...]
    metrics: Dict[str, Any]
    blockers: Tuple[str, ...]
    next_steps: Tuple[str, ...]


@dataclass(frozen=True)
class WRAPAttestation:
    """WRAP attestation — signature and timestamp."""
    
    gid: str
    timestamp: str
    signature_hash: str
    pac_chain: Tuple[str, ...]
    ber_eligible: bool


@dataclass(frozen=True)
class ValidatedWRAP:
    """Fully validated WRAP structure."""
    
    header: WRAPHeader
    proof: WRAPProof
    decision: WRAPDecision
    outcome: WRAPOutcome
    attestation: WRAPAttestation
    raw_text: str
    validation_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    @property
    def wrap_id(self) -> str:
        return self.header.wrap_id
    
    @property
    def pac_id(self) -> str:
        return self.header.pac_id
    
    @property
    def is_complete(self) -> bool:
        return self.outcome.status == "COMPLETE"
    
    @property
    def is_ber_eligible(self) -> bool:
        return self.attestation.ber_eligible and self.is_complete


# ═══════════════════════════════════════════════════════════════════════════════
# WRAP PARSER
# ═══════════════════════════════════════════════════════════════════════════════

class WRAPParser:
    """
    WRAP document parser.
    
    Extracts structured blocks from WRAP markdown text.
    """
    
    # Block header patterns
    HEADER_PATTERN = re.compile(
        r"#+\s*(?:WRAP\s+)?HEADER|^WRAP[-_]ID:",
        re.IGNORECASE | re.MULTILINE
    )
    PROOF_PATTERN = re.compile(
        r"#+\s*PROOF(?:\s+BLOCK)?|^ARTIFACTS:",
        re.IGNORECASE | re.MULTILINE
    )
    DECISION_PATTERN = re.compile(
        r"#+\s*DECISION(?:\s+BLOCK)?|^ACTION:",
        re.IGNORECASE | re.MULTILINE
    )
    OUTCOME_PATTERN = re.compile(
        r"#+\s*OUTCOME(?:\s+BLOCK)?|^STATUS:",
        re.IGNORECASE | re.MULTILINE
    )
    ATTESTATION_PATTERN = re.compile(
        r"#+\s*ATTESTATION|^ATTESTED[-_]BY:",
        re.IGNORECASE | re.MULTILINE
    )
    
    def __init__(self, text: str):
        self.text = text
        self.blocks: Dict[WRAPBlockType, str] = {}
    
    def parse(self) -> Dict[WRAPBlockType, str]:
        """Parse WRAP text into blocks."""
        
        # Find all block positions
        positions: List[Tuple[int, WRAPBlockType]] = []
        
        patterns = [
            (self.HEADER_PATTERN, WRAPBlockType.HEADER),
            (self.PROOF_PATTERN, WRAPBlockType.PROOF),
            (self.DECISION_PATTERN, WRAPBlockType.DECISION),
            (self.OUTCOME_PATTERN, WRAPBlockType.OUTCOME),
            (self.ATTESTATION_PATTERN, WRAPBlockType.ATTESTATION),
        ]
        
        for pattern, block_type in patterns:
            match = pattern.search(self.text)
            if match:
                positions.append((match.start(), block_type))
        
        # Sort by position
        positions.sort(key=lambda x: x[0])
        
        # Extract block content
        for i, (pos, block_type) in enumerate(positions):
            # Get end position (start of next block or end of text)
            if i + 1 < len(positions):
                end_pos = positions[i + 1][0]
            else:
                end_pos = len(self.text)
            
            self.blocks[block_type] = self.text[pos:end_pos].strip()
        
        return self.blocks
    
    def extract_field(self, block: str, field_name: str) -> Optional[str]:
        """Extract a field value from a block."""
        # Try multiple patterns
        patterns = [
            rf"{field_name}[:\s]+([^\n]+)",
            rf"\*\*{field_name}\*\*[:\s]+([^\n]+)",
            rf"-\s+{field_name}[:\s]+([^\n]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_list(self, block: str, field_name: str) -> List[str]:
        """Extract a list of items from a block."""
        items = []
        
        # Find the field
        pattern = rf"{field_name}[:\s]*\n((?:[-*]\s+[^\n]+\n?)+)"
        match = re.search(pattern, block, re.IGNORECASE)
        
        if match:
            list_text = match.group(1)
            items = [
                line.strip().lstrip("-*").strip()
                for line in list_text.split("\n")
                if line.strip().startswith(("-", "*"))
            ]
        
        return items


# ═══════════════════════════════════════════════════════════════════════════════
# WRAP VALIDATOR — MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class WRAPValidator:
    """
    WRAP validator — programmatic enforcement.
    
    No conversational forgiveness.
    Invalid WRAP → rejected before BER consideration.
    """
    
    def __init__(self):
        self.parser: Optional[WRAPParser] = None
        self.blocks: Dict[WRAPBlockType, str] = {}
    
    def validate(self, wrap_text: str) -> ValidatedWRAP:
        """
        Validate a WRAP document.
        
        HARD FAIL on any error.
        Returns ValidatedWRAP on success.
        """
        self.parser = WRAPParser(wrap_text)
        self.blocks = self.parser.parse()
        
        # Check all mandatory blocks present
        self._check_mandatory_blocks()
        
        # Validate and extract each block
        header = self._validate_header()
        proof = self._validate_proof()
        decision = self._validate_decision()
        outcome = self._validate_outcome()
        attestation = self._validate_attestation(header)
        
        return ValidatedWRAP(
            header=header,
            proof=proof,
            decision=decision,
            outcome=outcome,
            attestation=attestation,
            raw_text=wrap_text,
        )
    
    def _check_mandatory_blocks(self) -> None:
        """Check all mandatory blocks are present."""
        for block_type in MANDATORY_BLOCKS:
            if block_type not in self.blocks:
                raise WRAPMissingBlockError(block_type.value)
    
    def _validate_header(self) -> WRAPHeader:
        """Validate and extract header block."""
        block = self.blocks[WRAPBlockType.HEADER]
        
        # Extract required fields
        wrap_id = self.parser.extract_field(block, "WRAP[-_]ID")
        pac_id = self.parser.extract_field(block, "PAC[-_]ID")
        gid = self.parser.extract_field(block, "GID")
        role = self.parser.extract_field(block, "ROLE")
        mode = self.parser.extract_field(block, "MODE")
        lane = self.parser.extract_field(block, "(?:EXECUTION[-_])?LANE")
        
        # Validate required fields
        if not wrap_id:
            raise WRAPMalformedBlockError("HEADER", "Missing WRAP_ID")
        if not pac_id:
            raise WRAPMalformedBlockError("HEADER", "Missing PAC_ID")
        if not gid:
            raise WRAPMalformedBlockError("HEADER", "Missing GID")
        
        # Validate GID exists in registry
        try:
            validate_agent_gid(gid)
        except Exception as e:
            raise WRAPIdentityError(str(e))
        
        return WRAPHeader(
            wrap_id=wrap_id,
            pac_id=pac_id,
            gid=gid,
            role=role or "UNKNOWN",
            mode=mode or "EXECUTION",
            execution_lane=lane or "ALL",
            discipline=self.parser.extract_field(block, "DISCIPLINE") or "FAIL-CLOSED",
            governance_mode=self.parser.extract_field(block, "GOVERNANCE[-_]MODE") or "GOLD_STANDARD",
        )
    
    def _validate_proof(self) -> WRAPProof:
        """Validate and extract proof block."""
        block = self.blocks[WRAPBlockType.PROOF]
        
        artifacts_created = self.parser.extract_list(block, "(?:ARTIFACTS[-_])?CREATED")
        artifacts_modified = self.parser.extract_list(block, "(?:ARTIFACTS[-_])?MODIFIED")
        commands = self.parser.extract_list(block, "COMMANDS(?:[-_]EXECUTED)?")
        tests = self.parser.extract_list(block, "TESTS(?:[-_]RUN)?")
        verification = self.parser.extract_list(block, "VERIFICATION(?:[-_]STEPS)?")
        
        # Proof must have at least some content
        if not (artifacts_created or artifacts_modified or commands):
            raise WRAPProofError("No artifacts or commands recorded")
        
        return WRAPProof(
            artifacts_created=tuple(artifacts_created),
            artifacts_modified=tuple(artifacts_modified),
            commands_executed=tuple(commands),
            tests_run=tuple(tests),
            verification_steps=tuple(verification),
        )
    
    def _validate_decision(self) -> WRAPDecision:
        """Validate and extract decision block."""
        block = self.blocks[WRAPBlockType.DECISION]
        
        summary = self.parser.extract_field(block, "(?:ACTION[-_])?SUMMARY")
        rationale = self.parser.extract_field(block, "RATIONALE")
        alternatives = self.parser.extract_list(block, "ALTERNATIVES(?:[-_]CONSIDERED)?")
        constraints = self.parser.extract_list(block, "CONSTRAINTS(?:[-_]HONORED)?")
        deferred = self.parser.extract_list(block, "DEFERRED(?:[-_]ITEMS)?")
        
        if not summary:
            raise WRAPMalformedBlockError("DECISION", "Missing action summary")
        
        return WRAPDecision(
            action_summary=summary,
            rationale=rationale or "See proof block",
            alternatives_considered=tuple(alternatives),
            constraints_honored=tuple(constraints),
            deferred_items=tuple(deferred),
        )
    
    def _validate_outcome(self) -> WRAPOutcome:
        """Validate and extract outcome block."""
        block = self.blocks[WRAPBlockType.OUTCOME]
        
        status = self.parser.extract_field(block, "STATUS")
        deliverables = self.parser.extract_list(block, "DELIVERABLES")
        blockers = self.parser.extract_list(block, "BLOCKERS")
        next_steps = self.parser.extract_list(block, "NEXT[-_]STEPS")
        
        if not status:
            raise WRAPMalformedBlockError("OUTCOME", "Missing status")
        
        # Parse metrics if present
        metrics: Dict[str, Any] = {}
        metrics_match = re.search(
            r"METRICS[:\s]*\n((?:[-*]\s+[^\n]+\n?)+)",
            block,
            re.IGNORECASE
        )
        if metrics_match:
            for line in metrics_match.group(1).split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metrics[key.strip().lstrip("-*").strip()] = value.strip()
        
        return WRAPOutcome(
            status=status.upper(),
            deliverables=tuple(deliverables),
            metrics=metrics,
            blockers=tuple(blockers),
            next_steps=tuple(next_steps),
        )
    
    def _validate_attestation(self, header: WRAPHeader) -> WRAPAttestation:
        """Validate and extract attestation block."""
        block = self.blocks[WRAPBlockType.ATTESTATION]
        
        attested_by = self.parser.extract_field(block, "ATTESTED[-_]BY")
        timestamp = self.parser.extract_field(block, "TIMESTAMP")
        
        if not attested_by:
            raise WRAPSignatureError("Missing attesting GID")
        
        # Generate signature hash
        signature_content = f"{header.wrap_id}:{header.pac_id}:{header.gid}:{timestamp}"
        signature_hash = hashlib.sha256(signature_content.encode()).hexdigest()[:16]
        
        # Extract PAC chain
        pac_chain = self.parser.extract_list(block, "PAC[-_]CHAIN")
        if not pac_chain:
            pac_chain = [header.pac_id]
        
        # BER eligibility
        ber_eligible = "BER[-_]ELIGIBLE" in block.upper() or "YES" in block.upper()
        
        return WRAPAttestation(
            gid=attested_by,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            signature_hash=signature_hash,
            pac_chain=tuple(pac_chain),
            ber_eligible=ber_eligible,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_validator: Optional[WRAPValidator] = None


def get_wrap_validator() -> WRAPValidator:
    """Get a WRAP validator instance."""
    global _validator
    if _validator is None:
        _validator = WRAPValidator()
    return _validator


def validate_wrap(wrap_text: str) -> ValidatedWRAP:
    """
    Validate a WRAP document.
    
    HARD FAIL on error.
    """
    return get_wrap_validator().validate(wrap_text)


def is_wrap_valid(wrap_text: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a WRAP is valid.
    
    Returns (True, None) on success.
    Returns (False, error_message) on failure.
    """
    try:
        validate_wrap(wrap_text)
        return True, None
    except WRAPValidationError as e:
        return False, str(e)


def check_ber_eligibility(wrap_text: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a WRAP is eligible for BER.
    
    WRAP must be valid AND marked complete AND BER-eligible.
    """
    try:
        validated = validate_wrap(wrap_text)
        if validated.is_ber_eligible:
            return True, None
        else:
            reasons = []
            if not validated.is_complete:
                reasons.append("WRAP status is not COMPLETE")
            if not validated.attestation.ber_eligible:
                reasons.append("WRAP not marked as BER-eligible")
            return False, "; ".join(reasons)
    except WRAPValidationError as e:
        return False, f"WRAP validation failed: {e}"
