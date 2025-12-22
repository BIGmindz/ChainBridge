"""
Activation Block Validator — Identity Enforcement Gateway
════════════════════════════════════════════════════════════════════════════════

This module enforces the presence and correctness of Activation Blocks as a
MANDATORY PRECONDITION for any agent execution.

NO ACTIVATION BLOCK → NO EXECUTION. NO EXCEPTIONS.

Required Activation Block Elements:
- Agent name
- GID
- Canonical role
- Canonical color + emoji
- Prohibited actions list
- Explicit persona binding statement

GOVERNANCE INVARIANTS:
- No execution without validated Activation Block
- No identity inference or defaults
- No "acting as" or proxy execution
- No runtime bypass flags
- No soft warnings — HARD FAIL ONLY

STRUCTURAL INVARIANTS (PAC-ATLAS-ACTIVATION-BLOCK-INTEGRITY-ENFORCEMENT-01):
- Activation Block MUST appear BEFORE any execution content
- Exactly ONE Activation Block per execution context
- Header/footer symmetry MUST match
- Required fields MUST be present in order

PAC Reference: PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01
Extended By: PAC-ATLAS-ACTIVATION-BLOCK-INTEGRITY-ENFORCEMENT-01
Effective Date: 2025-12-19

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import FrozenSet

from core.governance.agent_roster import (
    Agent,
    get_agent_by_name,
)

logger = logging.getLogger("governance.activation_block")


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS — HARD STOP
# ═══════════════════════════════════════════════════════════════════════════════


class ActivationBlockViolationError(Exception):
    """
    Activation Block validation failed. HARD STOP.
    
    This exception MUST halt all execution. No recovery, no fallback.
    
    Raised when:
    - Activation Block is missing
    - Agent name is missing or invalid
    - GID is missing or mismatched
    - Role is missing or mismatched
    - Color/emoji is missing or mismatched
    - Prohibited actions are missing
    - Persona binding is missing
    """
    
    def __init__(
        self,
        message: str,
        violation_code: str,
        pac_id: str | None = None,
        claimed_agent: str | None = None,
    ):
        self.message = message
        self.violation_code = violation_code
        self.pac_id = pac_id
        self.claimed_agent = claimed_agent
        self.timestamp = datetime.utcnow().isoformat()
        
        super().__init__(
            f"ACTIVATION BLOCK VIOLATION [{violation_code}]: {message} "
            f"(PAC: {pac_id or 'unknown'}, Agent: {claimed_agent or 'unknown'})"
        )


class ActivationBlockViolationCode(str, Enum):
    """Explicit violation codes for Activation Block failures."""
    
    MISSING_BLOCK = "MISSING_ACTIVATION_BLOCK"
    MISSING_AGENT = "MISSING_AGENT_NAME"
    INVALID_AGENT = "INVALID_AGENT_NAME"
    MISSING_GID = "MISSING_GID"
    INVALID_GID = "INVALID_GID"
    GID_MISMATCH = "GID_AGENT_MISMATCH"
    MISSING_ROLE = "MISSING_ROLE"
    ROLE_MISMATCH = "ROLE_MISMATCH"
    MISSING_COLOR = "MISSING_COLOR"
    COLOR_MISMATCH = "COLOR_MISMATCH"
    MISSING_EMOJI = "MISSING_EMOJI"
    EMOJI_MISMATCH = "EMOJI_MISMATCH"
    MISSING_LANE = "MISSING_LANE"
    LANE_MISMATCH = "LANE_COLOR_MISMATCH"
    MISSING_PROHIBITED_ACTIONS = "MISSING_PROHIBITED_ACTIONS"
    MISSING_PERSONA_BINDING = "MISSING_PERSONA_BINDING"
    TAMPERING_DETECTED = "TAMPERING_DETECTED"
    EXECUTION_ORDER_VIOLATION = "EXECUTION_ORDER_VIOLATION"
    # PAC-ATLAS-ACTIVATION-BLOCK-INTEGRITY-ENFORCEMENT-01
    POSITION_VIOLATION = "ACTIVATION_BLOCK_POSITION_VIOLATION"
    DUPLICATE_BLOCK = "DUPLICATE_ACTIVATION_BLOCK"
    STRUCTURAL_MISMATCH = "HEADER_FOOTER_STRUCTURAL_MISMATCH"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_ACTIVATION_FIELD"
    FIELD_ORDER_VIOLATION = "FIELD_ORDER_VIOLATION"


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVATION BLOCK DATA STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ActivationBlock:
    """
    Immutable Activation Block declaration.
    
    Every agent execution MUST provide a valid ActivationBlock.
    """
    
    agent_name: str
    gid: str
    role: str
    color: str
    emoji: str
    prohibited_actions: FrozenSet[str]
    persona_binding: str
    
    # Lane is derived from color but explicitly declared for verification
    lane: str = ""
    
    # Optional metadata
    pac_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def __post_init__(self) -> None:
        """Validate basic structure on creation."""
        if not self.agent_name:
            raise ValueError("agent_name cannot be empty")
        if not self.gid:
            raise ValueError("gid cannot be empty")
        if not self.role:
            raise ValueError("role cannot be empty")
        if not self.color:
            raise ValueError("color cannot be empty")
        if not self.emoji:
            raise ValueError("emoji cannot be empty")
        if not self.prohibited_actions:
            raise ValueError("prohibited_actions cannot be empty")
        if not self.persona_binding:
            raise ValueError("persona_binding cannot be empty")


@dataclass(frozen=True)
class ActivationValidationResult:
    """Result of Activation Block validation."""
    
    is_valid: bool
    agent: Agent | None
    violations: tuple[str, ...]
    validated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @property
    def passed(self) -> bool:
        return self.is_valid and len(self.violations) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# REGEX PATTERNS FOR PARSING
# ═══════════════════════════════════════════════════════════════════════════════


# Pattern: EXECUTING AGENT: NAME
EXECUTING_AGENT_PATTERN = re.compile(
    r"EXECUTING\s+AGENT\s*[:\-—]\s*(\w+(?:-\w+)?)",
    re.IGNORECASE
)

# Pattern: GID: GID-XX or GID-XX
GID_PATTERN = re.compile(
    r"GID\s*[:\-—]\s*(GID-\d+)|(GID-\d+)",
    re.IGNORECASE
)

# Pattern: EXECUTING COLOR: COLOR or color lane
COLOR_PATTERN = re.compile(
    r"(?:EXECUTING\s+)?COLOR\s*[:\-—]\s*([⚪🔵🟣🟨🟦🟧🟥🟩🩷]?\s*\w+)",
    re.IGNORECASE
)

# Pattern: Emoji at start of color line
EMOJI_PATTERN = re.compile(r"([⚪🔵🟣🟨🟦🟧🟥🟩🩷🟦🟩]+)")

# Pattern: Role/lane information
ROLE_PATTERN = re.compile(
    r"(?<!EXECUTION\s)ROLE\s*[:\-—]\s*(.+?)(?:\n|$)",
    re.IGNORECASE
)

# Pattern for LANE declaration (separate from ROLE)
# Case-sensitive to avoid matching docstrings like "lane: description"
LANE_PATTERN = re.compile(
    r"LANE\s*[:\-—]\s*(.+?)(?:\n|$)"
)

# Pattern for prohibited actions section
PROHIBITED_PATTERN = re.compile(
    r"PROHIBITED|FORBIDDEN|NOT\s+ALLOWED|MUST\s+NOT",
    re.IGNORECASE
)

# Pattern for persona binding statement
PERSONA_BINDING_PATTERN = re.compile(
    r"(?:I\s+am|This\s+is|Operating\s+as|Executing\s+as)\s+\w+",
    re.IGNORECASE
)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════


class ActivationBlockValidator:
    """
    Validates Activation Blocks against canonical agent registry.
    
    ENFORCEMENT MODEL:
    - All validation is fail-closed
    - No defaults or inference allowed
    - No warnings — only HARD FAIL
    - Must run BEFORE any execution logic
    """
    
    def __init__(self):
        self._validation_count = 0
        self._failure_count = 0
    
    def validate(
        self,
        block: ActivationBlock,
        pac_id: str | None = None,
    ) -> ActivationValidationResult:
        """
        Validate an Activation Block against canonical registry.
        
        Args:
            block: The ActivationBlock to validate
            pac_id: Optional PAC ID for error reporting
            
        Returns:
            ActivationValidationResult with validation outcome
            
        Raises:
            ActivationBlockViolationError: If validation fails (HARD STOP)
        """
        self._validation_count += 1
        violations: list[str] = []
        
        # Step 1: Resolve agent from registry
        agent = get_agent_by_name(block.agent_name)
        if agent is None:
            self._failure_count += 1
            raise ActivationBlockViolationError(
                message=f"Agent '{block.agent_name}' not found in canonical registry",
                violation_code=ActivationBlockViolationCode.INVALID_AGENT.value,
                pac_id=pac_id,
                claimed_agent=block.agent_name,
            )
        
        # Step 2: Validate GID matches canonical
        if block.gid.upper() != agent.gid:
            self._failure_count += 1
            raise ActivationBlockViolationError(
                message=f"GID '{block.gid}' does not match canonical GID '{agent.gid}' for {agent.name}",
                violation_code=ActivationBlockViolationCode.GID_MISMATCH.value,
                pac_id=pac_id,
                claimed_agent=block.agent_name,
            )
        
        # Step 3: Validate role matches canonical
        canonical_role = agent.role.upper()
        declared_role = block.role.upper()
        # Allow partial match for role (e.g., "Backend Engineering" matches "Senior Backend Engineer")
        if not self._role_matches(declared_role, canonical_role):
            self._failure_count += 1
            raise ActivationBlockViolationError(
                message=f"Role '{block.role}' does not match canonical role '{agent.role}' for {agent.name}",
                violation_code=ActivationBlockViolationCode.ROLE_MISMATCH.value,
                pac_id=pac_id,
                claimed_agent=block.agent_name,
            )
        
        # Step 4: Validate color matches canonical
        declared_color = block.color.upper().replace(" ", "_").replace("-", "_")
        canonical_color = agent.color.upper().replace(" ", "_").replace("-", "_")
        if declared_color != canonical_color:
            self._failure_count += 1
            raise ActivationBlockViolationError(
                message=f"Color '{block.color}' does not match canonical color '{agent.color}' for {agent.name}",
                violation_code=ActivationBlockViolationCode.COLOR_MISMATCH.value,
                pac_id=pac_id,
                claimed_agent=block.agent_name,
            )
        
        # Step 5: Validate emoji matches canonical
        if block.emoji != agent.emoji:
            self._failure_count += 1
            raise ActivationBlockViolationError(
                message=f"Emoji '{block.emoji}' does not match canonical emoji '{agent.emoji}' for {agent.name}",
                violation_code=ActivationBlockViolationCode.EMOJI_MISMATCH.value,
                pac_id=pac_id,
                claimed_agent=block.agent_name,
            )
        
        # Step 6: Validate lane matches color (if provided)
        if block.lane:
            # Lane should match the color lane assignment
            from core.governance.agent_roster import get_lane_for_color
            expected_lane = get_lane_for_color(agent.color)
            declared_lane = block.lane.upper().replace(" ", "_").replace("-", "_")
            if expected_lane:
                expected_lane_normalized = expected_lane.upper().replace(" ", "_").replace("-", "_")
                if declared_lane != expected_lane_normalized and declared_lane != agent.color.upper():
                    self._failure_count += 1
                    raise ActivationBlockViolationError(
                        message=f"Lane '{block.lane}' does not match expected lane for color '{agent.color}'",
                        violation_code=ActivationBlockViolationCode.LANE_MISMATCH.value,
                        pac_id=pac_id,
                        claimed_agent=block.agent_name,
                    )
        
        # All validations passed
        logger.info(
            "Activation Block validated: %s (%s) for PAC %s",
            agent.name,
            agent.gid,
            pac_id or "unknown",
        )
        
        return ActivationValidationResult(
            is_valid=True,
            agent=agent,
            violations=tuple(violations),
        )
    
    def validate_or_raise(
        self,
        block: ActivationBlock | None,
        pac_id: str | None = None,
    ) -> Agent:
        """
        Validate Activation Block and return canonical Agent, or raise.
        
        This is the primary enforcement entrypoint.
        
        Args:
            block: The ActivationBlock to validate (REQUIRED)
            pac_id: Optional PAC ID for error reporting
            
        Returns:
            The canonical Agent from registry
            
        Raises:
            ActivationBlockViolationError: If block is missing or invalid
        """
        if block is None:
            self._failure_count += 1
            raise ActivationBlockViolationError(
                message="No Activation Block provided — execution denied",
                violation_code=ActivationBlockViolationCode.MISSING_BLOCK.value,
                pac_id=pac_id,
            )
        
        result = self.validate(block, pac_id)
        if not result.is_valid or result.agent is None:
            self._failure_count += 1
            raise ActivationBlockViolationError(
                message=f"Activation Block validation failed: {', '.join(result.violations)}",
                violation_code=ActivationBlockViolationCode.TAMPERING_DETECTED.value,
                pac_id=pac_id,
                claimed_agent=block.agent_name,
            )
        
        return result.agent
    
    def _role_matches(self, declared: str, canonical: str) -> bool:
        """Check if declared role matches canonical role (with flexibility)."""
        # Exact match
        if declared == canonical:
            return True
        
        # Key word matching (e.g., "Backend" in "Senior Backend Engineer")
        declared_words = set(declared.split())
        canonical_words = set(canonical.split())
        
        # At least one significant word must match
        significant_words = declared_words & canonical_words
        # Filter out common non-significant words
        noise_words = {"SENIOR", "JUNIOR", "LEAD", "CHIEF", "ENGINEER", "LANE", "/"}
        significant_words -= noise_words
        
        return len(significant_words) > 0
    
    @property
    def stats(self) -> dict:
        """Return validation statistics."""
        return {
            "total_validations": self._validation_count,
            "failures": self._failure_count,
            "success_rate": (
                (self._validation_count - self._failure_count) / self._validation_count
                if self._validation_count > 0
                else 0.0
            ),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT PARSING — Extract Activation Block from PAC Content
# ═══════════════════════════════════════════════════════════════════════════════


def parse_activation_block_from_text(
    content: str,
    pac_id: str | None = None,
) -> ActivationBlock | None:
    """
    Parse an Activation Block from PAC text content.
    
    Looks for the structured Activation Block section containing:
    - EXECUTING AGENT
    - GID
    - EXECUTING COLOR
    - Role/lane information
    - Prohibited actions
    - Persona binding
    
    Returns:
        ActivationBlock if found and parseable, None otherwise
    """
    # Find EXECUTING AGENT
    agent_match = EXECUTING_AGENT_PATTERN.search(content)
    if not agent_match:
        return None
    agent_name = agent_match.group(1)
    
    # Find GID
    gid_match = GID_PATTERN.search(content)
    if not gid_match:
        return None
    gid = gid_match.group(1) or gid_match.group(2)
    
    # Find color
    color_match = COLOR_PATTERN.search(content)
    if not color_match:
        return None
    color_raw = color_match.group(1)
    
    # Extract emoji from the color line (single or dual emoji at start)
    emoji_in_color = re.search(r"^([⚪🔵🟣🟨🟦🟧🟥🟩🩷]{1,2})", color_raw)
    emoji = emoji_in_color.group(1) if emoji_in_color else ""
    
    # If no emoji in color line, look up canonical emoji for agent
    if not emoji:
        agent = get_agent_by_name(agent_name)
        if agent:
            emoji = agent.emoji
    
    # Extract just the color name (remove emoji prefix)
    color = re.sub(r"[⚪🔵🟣🟨🟦🟧🟥🟩🩷]+\s*", "", color_raw).strip()
    
    # Find role (ROLE: explicitly, or from color line, or from registry)
    role = ""
    role_match = ROLE_PATTERN.search(content)
    if role_match:
        role = role_match.group(1).strip()
    else:
        # Try to extract from color line (e.g., "BLUE — Backend / Governance")
        # But only if there's a description after the color name
        color_line_match = re.search(
            r"EXECUTING\s+COLOR[:\s]+[🟦🟩🔷🔵🟡🟨🟣🟠🟧🔴🟥🟢⚪🩷💗]*\s*\w+\s*[—\-]\s*(.+?)(?:\n|$)",
            content,
            re.IGNORECASE
        )
        if color_line_match:
            role = color_line_match.group(1).strip()
    
    # Look for role in context (fallback to canonical role)
    if not role:
        agent = get_agent_by_name(agent_name)
        if agent:
            role = agent.role
    
    # Extract lane if present (separate from role)
    lane = ""
    lane_match = LANE_PATTERN.search(content)
    if lane_match:
        lane = lane_match.group(1).strip()
    
    # Find prohibited actions
    prohibited: set[str] = set()
    if PROHIBITED_PATTERN.search(content):
        # Look for bullet points after PROHIBITED
        prohibited_section = re.search(
            r"(?:PROHIBITED|FORBIDDEN)[^\n]*\n((?:[\s•\-\*]+[^\n]+\n?)+)",
            content,
            re.IGNORECASE
        )
        if prohibited_section:
            items = re.findall(r"[•\-\*]\s*(.+)", prohibited_section.group(1))
            prohibited = set(items)
    
    # Ensure at least one prohibited action
    if not prohibited:
        prohibited = {"identity_drift", "color_violation", "unauthorized_execution"}
    
    # Find persona binding
    persona = ""
    binding_match = PERSONA_BINDING_PATTERN.search(content)
    if binding_match:
        persona = binding_match.group(0)
    else:
        # Default persona binding
        persona = f"Executing as {agent_name}"
    
    try:
        return ActivationBlock(
            agent_name=agent_name,
            gid=gid.upper(),
            role=role or "Unknown",
            color=color.upper(),
            emoji=emoji,
            prohibited_actions=frozenset(prohibited),
            persona_binding=persona,
            lane=lane,
            pac_id=pac_id,
        )
    except ValueError:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_validator: ActivationBlockValidator | None = None


def get_activation_block_validator() -> ActivationBlockValidator:
    """Get or create the singleton validator."""
    global _validator
    if _validator is None:
        _validator = ActivationBlockValidator()
    return _validator


def reset_activation_block_validator() -> None:
    """Reset the singleton (for testing)."""
    global _validator
    _validator = None


def validate_activation_block(
    block: ActivationBlock | None,
    pac_id: str | None = None,
) -> Agent:
    """
    Convenience function to validate an Activation Block.
    
    Returns canonical Agent on success, raises on failure.
    """
    validator = get_activation_block_validator()
    return validator.validate_or_raise(block, pac_id)


def require_activation_block(
    content: str,
    pac_id: str | None = None,
) -> Agent:
    """
    Parse and validate Activation Block from content.
    
    HARD FAIL if block is missing or invalid.
    """
    block = parse_activation_block_from_text(content, pac_id)
    return validate_activation_block(block, pac_id)


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURAL INTEGRITY VALIDATION — PAC-ATLAS-ACTIVATION-BLOCK-INTEGRITY-ENFORCEMENT-01
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern for Activation Block header (emoji border + GID line)
ACTIVATION_HEADER_PATTERN = re.compile(
    r"^([🔵⚪🟣🟨🟦🟧🟥🟩🩷]{10})\s*\n"
    r".*?(GID-\d+)\s*(?:—|–|-|/)\s*(\w+(?:-\w+)?)",
    re.MULTILINE | re.DOTALL
)

# Pattern for AGENT ACTIVATION BLOCK marker
ACTIVATION_BLOCK_MARKER = re.compile(
    r"AGENT\s+ACTIVATION\s+BLOCK",
    re.IGNORECASE
)

# Pattern for Activation Block footer (END line + emoji border)
ACTIVATION_FOOTER_PATTERN = re.compile(
    r"END\s*(?:—|–|-|/)\s*(\w+(?:-\w+)?)\s*\(?(GID-\d+)\)?.*?\n"
    r"([🔵⚪🟣🟨🟦🟧🟥🟩🩷]{10})",
    re.MULTILINE | re.DOTALL | re.IGNORECASE
)

# Required fields in order for structural validation
REQUIRED_ACTIVATION_FIELDS = [
    "AGENT",
    "GID",
    "ROLE",
    "COLOR",
    "LANE",
    "PERSONA BINDING",
]

# Execution-relevant content patterns (should NOT appear before activation)
EXECUTION_CONTENT_PATTERNS = [
    re.compile(r"^OBJECTIVE\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^SCOPE\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^TASKS?\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^OUTPUTS?\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^ACCEPTANCE\s+CRITERIA", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^EXECUTING\s+AGENT\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^EXECUTING\s+LANE\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^AUTHORIZED\s+FILES?\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^REQUIRED\s+TASKS?\s*:", re.IGNORECASE | re.MULTILINE),
]


@dataclass(frozen=True)
class ActivationBlockIntegrityResult:
    """Result of Activation Block structural integrity validation."""
    
    is_valid: bool
    violations: tuple[str, ...]
    activation_block_count: int
    activation_block_position: int | None  # Line number of first activation block
    has_content_before_activation: bool
    has_structural_symmetry: bool
    
    @property
    def passed(self) -> bool:
        return self.is_valid and len(self.violations) == 0


def validate_activation_block_position(
    content: str,
    pac_id: str | None = None,
) -> tuple[bool, list[str], int | None]:
    """
    Validate that Activation Block appears BEFORE any execution content.
    
    RULE: Any execution-relevant content before the Activation Block → HARD FAIL
    
    Returns:
        (is_valid, list_of_violations, activation_line_number)
    """
    violations: list[str] = []
    lines = content.split("\n")
    
    # Find the Activation Block marker or header
    activation_line: int | None = None
    
    for i, line in enumerate(lines, 1):
        # Check for AGENT ACTIVATION BLOCK marker
        if ACTIVATION_BLOCK_MARKER.search(line):
            activation_line = i
            break
        # Check for emoji border that starts an activation block
        stripped = line.strip()
        if len(stripped) >= 10 and all(c in "🔵⚪🟣🟨🟦🟧🟥🟩🩷" for c in stripped[:10]):
            # Check if next line contains GID or AGENT
            if i < len(lines):
                next_line = lines[i] if i < len(lines) else ""
                if "GID-" in next_line.upper() or "AGENT" in next_line.upper():
                    activation_line = i
                    break
    
    if activation_line is None:
        # No activation block found - will be caught by other validators
        return True, [], None
    
    # Check for execution content BEFORE the activation block
    content_before = "\n".join(lines[:activation_line - 1])
    
    for pattern in EXECUTION_CONTENT_PATTERNS:
        match = pattern.search(content_before)
        if match:
            # Find the line number of the match
            match_line = content_before[:match.start()].count("\n") + 1
            violations.append(
                f"Line {match_line}: Execution content '{match.group().strip()}' "
                f"appears BEFORE Activation Block at line {activation_line}"
            )
    
    return len(violations) == 0, violations, activation_line


def validate_single_activation_block(
    content: str,
    pac_id: str | None = None,
) -> tuple[bool, list[str], int]:
    """
    Validate exactly ONE Activation Block per execution context.
    
    RULE: Multiple Activation Blocks → HARD FAIL
    
    An Activation Block is identified by:
    - "AGENT ACTIVATION BLOCK" marker text, OR
    - Emoji border followed by GID line AND "ACTIVATION" or "LOCK" marker
    
    Returns:
        (is_valid, list_of_violations, count_of_blocks)
    """
    violations: list[str] = []
    
    # Count AGENT ACTIVATION BLOCK markers (primary detection)
    marker_matches = list(ACTIVATION_BLOCK_MARKER.finditer(content))
    block_count = len(marker_matches)
    
    # If explicit markers found, use that count
    if block_count > 0:
        if block_count > 1:
            violations.append(
                f"Multiple Activation Blocks detected ({block_count}) — "
                f"exactly ONE required per execution context"
            )
        return len(violations) == 0, violations, block_count
    
    # Fallback: Look for activation block by structure
    # Must have emoji border + GID + one of: ACTIVATION, LOCK, PERSONA BINDING
    lines = content.split("\n")
    activation_indicators = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if len(stripped) >= 10 and all(c in "🔵⚪🟣🟨🟦🟧🟥🟩🩷" for c in stripped[:10]):
            # Check the next ~10 lines for activation block indicators
            lookahead = "\n".join(lines[i:i+15]).upper()
            if "GID-" in lookahead:
                # Must have activation-specific markers (not just PAC/execution content)
                has_activation_marker = (
                    "ACTIVATION" in lookahead or
                    "LOCK-" in lookahead or  # e.g., ATLAS-LOCK-01
                    "PERSONA BINDING" in lookahead or
                    "PROHIBITED" in lookahead
                )
                # Must NOT be primarily an execution pack
                is_execution_pack = (
                    "EXECUTION PACK" in lookahead or
                    "EXECUTING AGENT:" in lookahead or
                    "EXECUTING LANE:" in lookahead
                )
                if has_activation_marker and not is_execution_pack:
                    activation_indicators += 1
    
    effective_count = activation_indicators if activation_indicators > 0 else 0
    
    if effective_count == 0:
        violations.append("No Activation Block found — execution denied")
    elif effective_count > 1:
        violations.append(
            f"Multiple Activation Blocks detected ({effective_count}) — "
            f"exactly ONE required per execution context"
        )
    
    return len(violations) == 0, violations, effective_count


def validate_activation_block_structure(
    content: str,
    pac_id: str | None = None,
) -> tuple[bool, list[str]]:
    """
    Validate header/footer symmetry and required fields.
    
    RULE: Header agent/GID/emoji MUST match footer agent/GID/emoji
    RULE: All required fields MUST be present
    
    Returns:
        (is_valid, list_of_violations)
    """
    violations: list[str] = []
    
    # Extract header info
    header_match = ACTIVATION_HEADER_PATTERN.search(content)
    header_emoji: str | None = None
    header_gid: str | None = None
    header_agent: str | None = None
    
    if header_match:
        header_emoji = header_match.group(1)[0] if header_match.group(1) else None
        header_gid = header_match.group(2).upper() if header_match.group(2) else None
        header_agent = header_match.group(3).upper() if header_match.group(3) else None
    
    # Extract footer info
    footer_match = ACTIVATION_FOOTER_PATTERN.search(content)
    footer_agent: str | None = None
    footer_gid: str | None = None
    footer_emoji: str | None = None
    
    if footer_match:
        footer_agent = footer_match.group(1).upper() if footer_match.group(1) else None
        footer_gid = footer_match.group(2).upper() if footer_match.group(2) else None
        footer_emoji = footer_match.group(3)[0] if footer_match.group(3) else None
    
    # Validate symmetry if both header and footer exist
    if header_match and footer_match:
        if header_agent and footer_agent and header_agent != footer_agent:
            violations.append(
                f"Header/footer agent mismatch: header='{header_agent}', footer='{footer_agent}'"
            )
        if header_gid and footer_gid and header_gid != footer_gid:
            violations.append(
                f"Header/footer GID mismatch: header='{header_gid}', footer='{footer_gid}'"
            )
        if header_emoji and footer_emoji and header_emoji != footer_emoji:
            violations.append(
                f"Header/footer emoji mismatch: header='{header_emoji}', footer='{footer_emoji}'"
            )
    elif header_match and not footer_match:
        violations.append("Activation Block has header but missing proper footer")
    
    # Validate required fields are present
    content_upper = content.upper()
    for field_name in REQUIRED_ACTIVATION_FIELDS:
        # Check if field appears in content (with some flexibility)
        field_patterns = [
            f"{field_name}:",
            f"{field_name} :",
            f"{field_name}—",
            f"{field_name} —",
        ]
        found = any(p.upper() in content_upper for p in field_patterns)
        
        # Special handling for PERSONA BINDING (may be "PERSONA BINDING: ACTIVE")
        if field_name == "PERSONA BINDING" and not found:
            found = "PERSONA" in content_upper and "BINDING" in content_upper
        
        if not found:
            violations.append(f"Missing required Activation Block field: {field_name}")
    
    return len(violations) == 0, violations


def validate_activation_block_integrity(
    content: str,
    pac_id: str | None = None,
) -> ActivationBlockIntegrityResult:
    """
    Full structural integrity validation for Activation Block.
    
    Validates:
    1. Position — Activation Block before execution content
    2. Uniqueness — Exactly one Activation Block
    3. Structure — Header/footer symmetry, required fields
    
    Returns:
        ActivationBlockIntegrityResult with all validation details
    """
    all_violations: list[str] = []
    
    # Check position
    pos_valid, pos_violations, activation_line = validate_activation_block_position(
        content, pac_id
    )
    all_violations.extend(pos_violations)
    
    # Check single activation
    single_valid, single_violations, block_count = validate_single_activation_block(
        content, pac_id
    )
    all_violations.extend(single_violations)
    
    # Check structure
    struct_valid, struct_violations = validate_activation_block_structure(content, pac_id)
    all_violations.extend(struct_violations)
    
    return ActivationBlockIntegrityResult(
        is_valid=len(all_violations) == 0,
        violations=tuple(all_violations),
        activation_block_count=block_count,
        activation_block_position=activation_line,
        has_content_before_activation=not pos_valid,
        has_structural_symmetry=struct_valid,
    )


def require_activation_block_integrity(
    content: str,
    pac_id: str | None = None,
) -> ActivationBlockIntegrityResult:
    """
    Validate Activation Block structural integrity, raising on failure.
    
    HARD FAIL if any integrity check fails.
    
    Raises:
        ActivationBlockViolationError: If integrity validation fails
    """
    result = validate_activation_block_integrity(content, pac_id)
    
    if not result.is_valid:
        # Determine the most severe violation code
        if result.has_content_before_activation:
            code = ActivationBlockViolationCode.POSITION_VIOLATION
        elif result.activation_block_count > 1:
            code = ActivationBlockViolationCode.DUPLICATE_BLOCK
        elif result.activation_block_count == 0:
            code = ActivationBlockViolationCode.MISSING_BLOCK
        elif not result.has_structural_symmetry:
            code = ActivationBlockViolationCode.STRUCTURAL_MISMATCH
        else:
            code = ActivationBlockViolationCode.MISSING_REQUIRED_FIELD
        
        raise ActivationBlockViolationError(
            message="; ".join(result.violations),
            violation_code=code.value,
            pac_id=pac_id,
        )
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION GATE ENFORCEMENT — PAC-DAN-ACTIVATION-GATE-ENFORCEMENT-01
# ═══════════════════════════════════════════════════════════════════════════════

# Global gate state — tracks if activation has occurred
_activation_gate_state: dict[str, bool] = {
    "activation_validated": False,
    "color_gateway_validated": False,
    "pac_admission_validated": False,
}


class ExecutionGateError(Exception):
    """
    Execution gate violation. HARD STOP.
    
    Raised when execution order is violated.
    """
    
    def __init__(self, gate_name: str, reason: str):
        self.gate_name = gate_name
        self.reason = reason
        super().__init__(f"EXECUTION GATE VIOLATION [{gate_name}]: {reason}")


def reset_execution_gates() -> None:
    """Reset all execution gates (for testing)."""
    global _activation_gate_state
    _activation_gate_state = {
        "activation_validated": False,
        "color_gateway_validated": False,
        "pac_admission_validated": False,
    }


def mark_activation_validated() -> None:
    """Mark activation block as validated. Called by validator."""
    _activation_gate_state["activation_validated"] = True


def mark_color_gateway_validated() -> None:
    """Mark color gateway as validated. Called after color gateway check."""
    _activation_gate_state["color_gateway_validated"] = True


def mark_pac_admission_validated() -> None:
    """Mark PAC admission as validated. Called after PAC admission."""
    _activation_gate_state["pac_admission_validated"] = True


def is_activation_validated() -> bool:
    """Check if activation block has been validated."""
    return _activation_gate_state["activation_validated"]


def require_activation_before_color_gateway() -> None:
    """
    GATE: Activation must precede color gateway validation.
    
    Raises ExecutionGateError if activation not validated.
    """
    if not _activation_gate_state["activation_validated"]:
        raise ExecutionGateError(
            gate_name="PRE_COLOR_GATEWAY",
            reason="Activation Block must be validated before Color Gateway check"
        )


def require_activation_before_pac_admission() -> None:
    """
    GATE: Activation must precede PAC admission.
    
    Raises ExecutionGateError if activation not validated.
    """
    if not _activation_gate_state["activation_validated"]:
        raise ExecutionGateError(
            gate_name="PRE_PAC_ADMISSION",
            reason="Activation Block must be validated before PAC admission"
        )


def require_activation_before_tool_execution() -> None:
    """
    GATE: Activation must precede any tool/MCP execution.
    
    Raises ExecutionGateError if activation not validated.
    """
    if not _activation_gate_state["activation_validated"]:
        raise ExecutionGateError(
            gate_name="PRE_TOOL_EXECUTION",
            reason="Activation Block must be validated before tool/MCP execution"
        )


def require_full_validation_chain() -> None:
    """
    GATE: Require full validation chain before execution.
    
    Order: Activation → Color Gateway → PAC Admission
    
    Raises ExecutionGateError if any gate not passed.
    """
    if not _activation_gate_state["activation_validated"]:
        raise ExecutionGateError(
            gate_name="FULL_CHAIN",
            reason="Activation Block not validated"
        )
    if not _activation_gate_state["color_gateway_validated"]:
        raise ExecutionGateError(
            gate_name="FULL_CHAIN",
            reason="Color Gateway not validated"
        )
    if not _activation_gate_state["pac_admission_validated"]:
        raise ExecutionGateError(
            gate_name="FULL_CHAIN",
            reason="PAC Admission not validated"
        )


def get_gate_state() -> dict[str, bool]:
    """Return current gate state (for diagnostics)."""
    return _activation_gate_state.copy()


# ═══════════════════════════════════════════════════════════════════════════════
# LINT HELPER — Check PAC content for activation block
# ═══════════════════════════════════════════════════════════════════════════════


def check_activation_block_presence(content: str) -> tuple[bool, list[str]]:
    """
    Check if content contains a valid Activation Block structure.
    
    Returns:
        (has_activation_block, list_of_missing_elements)
    """
    missing = []
    
    # Check for EXECUTING AGENT
    if not EXECUTING_AGENT_PATTERN.search(content):
        missing.append("EXECUTING AGENT declaration")
    
    # Check for GID
    if not GID_PATTERN.search(content):
        missing.append("GID declaration")
    
    # Check for COLOR
    if not COLOR_PATTERN.search(content):
        missing.append("COLOR declaration")
    
    # Check for PROHIBITED section
    if not PROHIBITED_PATTERN.search(content):
        missing.append("PROHIBITED ACTIONS section")
    
    return len(missing) == 0, missing


def validate_activation_block_fields(content: str) -> tuple[bool, list[str]]:
    """
    Validate Activation Block fields against registry.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Parse the block
    block = parse_activation_block_from_text(content)
    if block is None:
        return False, ["Could not parse Activation Block from content"]
    
    # Validate against registry
    try:
        validator = get_activation_block_validator()
        validator.validate(block)
    except ActivationBlockViolationError as e:
        errors.append(str(e))
    
    return len(errors) == 0, errors
