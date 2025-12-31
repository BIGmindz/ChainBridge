"""
ChainBridge Mode Declaration Schema — HARD LAW Enforcement
════════════════════════════════════════════════════════════════════════════════

Mode declaration is MANDATORY for all agent executions.
Missing or malformed fields → HARD FAIL (no warnings).

PAC Reference: PAC-BENSON-CTO-EXEC-CODY-IDENTITY-MODE-LAW-011
Effective Date: 2025-12-26

MANDATORY FIELDS:
- GID: Agent identifier (validated against registry)
- ROLE: Agent role (must match registry)
- MODE: Execution mode (must be in permitted_modes)
- EXECUTION_LANE: Execution lane (must be in execution_lanes)

OPTIONAL FIELDS:
- PAC_ID: Reference PAC if executing under one
- WRAP_ID: Reference WRAP if continuing work

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .gid_registry import (
    GIDEnforcementError,
    GIDRegistry,
    validate_agent_gid,
    validate_full_identity,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA EXCEPTIONS — HARD FAIL
# ═══════════════════════════════════════════════════════════════════════════════

class ModeSchemaError(Exception):
    """Base exception for mode schema failures. HARD STOP."""
    pass


class MissingFieldError(ModeSchemaError):
    """Raised when a mandatory field is missing. HARD FAIL."""
    
    def __init__(self, field_name: str):
        self.field_name = field_name
        super().__init__(
            f"HARD FAIL: Mandatory field '{field_name}' is missing. "
            f"Mode declaration rejected. No conversational forgiveness."
        )


class MalformedFieldError(ModeSchemaError):
    """Raised when a field is malformed. HARD FAIL."""
    
    def __init__(self, field_name: str, expected: str, got: Any):
        self.field_name = field_name
        self.expected = expected
        self.got = got
        super().__init__(
            f"HARD FAIL: Field '{field_name}' is malformed. "
            f"Expected: {expected}. Got: {type(got).__name__} = {got}. "
            f"Mode declaration rejected."
        )


class RoleMismatchError(ModeSchemaError):
    """Raised when declared role doesn't match registry. HARD FAIL."""
    
    def __init__(self, gid: str, declared: str, registered: str):
        self.gid = gid
        self.declared = declared
        self.registered = registered
        super().__init__(
            f"HARD FAIL: Role mismatch for {gid}. "
            f"Declared: '{declared}'. Registered: '{registered}'. "
            f"Mode declaration rejected."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MANDATORY FIELD DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

MANDATORY_FIELDS = frozenset(["GID", "ROLE", "MODE", "EXECUTION_LANE"])

OPTIONAL_FIELDS = frozenset([
    "PAC_ID",
    "WRAP_ID",
    "BER_ID",
    "TIMESTAMP",
    "DISCIPLINE",
    "GOVERNANCE_MODE",
])

FIELD_TYPES = {
    "GID": str,
    "ROLE": str,
    "MODE": str,
    "EXECUTION_LANE": str,
    "PAC_ID": str,
    "WRAP_ID": str,
    "BER_ID": str,
    "TIMESTAMP": str,
    "DISCIPLINE": str,
    "GOVERNANCE_MODE": str,
}


# ═══════════════════════════════════════════════════════════════════════════════
# MODE DECLARATION — VALIDATED DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ModeDeclaration:
    """
    Validated mode declaration.
    
    All fields are validated at construction time.
    Invalid declarations cannot be created.
    """
    
    gid: str
    role: str
    mode: str
    execution_lane: str
    pac_id: Optional[str] = None
    wrap_id: Optional[str] = None
    ber_id: Optional[str] = None
    discipline: str = "FAIL-CLOSED"
    governance_mode: str = "GOLD_STANDARD"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def __post_init__(self) -> None:
        """Validate all fields at construction. HARD FAIL on any error."""
        # Validate GID exists in registry
        agent = validate_agent_gid(self.gid)
        
        # Validate role matches registry (case-insensitive contains check)
        # Allow partial match since role descriptions may vary
        registered_role = agent.role.upper()
        declared_role = self.role.upper()
        
        # Check for meaningful overlap
        role_words = set(registered_role.split())
        declared_words = set(declared_role.split())
        
        if not role_words & declared_words:
            raise RoleMismatchError(self.gid, self.role, agent.role)
        
        # Validate mode is permitted for this agent
        agent.validate_mode(self.mode)
        
        # Validate lane is permitted for this agent
        agent.validate_lane(self.execution_lane)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "GID": self.gid,
            "ROLE": self.role,
            "MODE": self.mode,
            "EXECUTION_LANE": self.execution_lane,
            "PAC_ID": self.pac_id,
            "WRAP_ID": self.wrap_id,
            "BER_ID": self.ber_id,
            "DISCIPLINE": self.discipline,
            "GOVERNANCE_MODE": self.governance_mode,
            "TIMESTAMP": self.timestamp,
        }
    
    def format_echo_line(self) -> str:
        """Format as echo-back handshake line."""
        return f"{self.gid} | MODE: {self.mode} | LANE: {self.execution_lane}"
    
    def format_header(self) -> str:
        """Format as full header block."""
        lines = [
            f"GID: {self.gid}",
            f"ROLE: {self.role}",
            f"MODE: {self.mode}",
            f"EXECUTION_LANE: {self.execution_lane}",
        ]
        if self.pac_id:
            lines.append(f"PAC_ID: {self.pac_id}")
        if self.wrap_id:
            lines.append(f"WRAP_ID: {self.wrap_id}")
        lines.append(f"DISCIPLINE: {self.discipline}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATOR — PROGRAMMATIC ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class ModeSchemaValidator:
    """
    Mode schema validator — programmatic enforcement.
    
    No conversational forgiveness.
    Invalid input → HARD FAIL.
    """
    
    def __init__(self):
        self.registry = GIDRegistry()
    
    def validate_raw_input(self, data: Dict[str, Any]) -> ModeDeclaration:
        """
        Validate raw input dictionary.
        
        HARD FAIL on any error.
        Returns validated ModeDeclaration on success.
        """
        # Check all mandatory fields present
        for field_name in MANDATORY_FIELDS:
            if field_name not in data or data[field_name] is None:
                raise MissingFieldError(field_name)
        
        # Check field types
        for field_name, expected_type in FIELD_TYPES.items():
            if field_name in data and data[field_name] is not None:
                if not isinstance(data[field_name], expected_type):
                    raise MalformedFieldError(
                        field_name,
                        expected_type.__name__,
                        data[field_name]
                    )
        
        # Create validated declaration (validation happens in __post_init__)
        return ModeDeclaration(
            gid=data["GID"],
            role=data["ROLE"],
            mode=data["MODE"],
            execution_lane=data["EXECUTION_LANE"],
            pac_id=data.get("PAC_ID"),
            wrap_id=data.get("WRAP_ID"),
            ber_id=data.get("BER_ID"),
            discipline=data.get("DISCIPLINE", "FAIL-CLOSED"),
            governance_mode=data.get("GOVERNANCE_MODE", "GOLD_STANDARD"),
        )
    
    def validate_pac_header(self, pac_text: str) -> ModeDeclaration:
        """
        Extract and validate mode declaration from PAC text.
        
        Parses structured text to find GID, ROLE, MODE, EXECUTION_LANE.
        """
        data = {}
        
        # Pattern matchers for common formats
        import re
        
        patterns = {
            "GID": [
                r"GID[:\s]+([A-Z]+-\d+)",
                r"ASSIGNED_AGENT[:\s]+\w+\s*\(([A-Z]+-\d+)\)",
                r"\(([A-Z]+-\d+)\)",
            ],
            "ROLE": [
                r"ROLE[:\s]+(.+?)(?:\n|$)",
            ],
            "MODE": [
                r"MODE[:\s]+(\w+)",
                r"EXECUTION_MODE[:\s]+(\w+)",
            ],
            "EXECUTION_LANE": [
                r"EXECUTION_LANE[:\s]+(.+?)(?:\n|$)",
                r"LANE[:\s]+(.+?)(?:\n|$)",
            ],
        }
        
        for field_name, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, pac_text, re.IGNORECASE)
                if match:
                    data[field_name] = match.group(1).strip()
                    break
        
        return self.validate_raw_input(data)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_validator = None


def get_validator() -> ModeSchemaValidator:
    """Get the singleton validator."""
    global _validator
    if _validator is None:
        _validator = ModeSchemaValidator()
    return _validator


def validate_mode_declaration(data: Dict[str, Any]) -> ModeDeclaration:
    """
    Validate mode declaration from dictionary.
    
    HARD FAIL on error.
    """
    return get_validator().validate_raw_input(data)


def create_mode_declaration(
    gid: str,
    role: str,
    mode: str,
    execution_lane: str,
    pac_id: Optional[str] = None,
    wrap_id: Optional[str] = None,
) -> ModeDeclaration:
    """
    Create a validated mode declaration.
    
    HARD FAIL if validation fails.
    """
    return ModeDeclaration(
        gid=gid,
        role=role,
        mode=mode,
        execution_lane=execution_lane,
        pac_id=pac_id,
        wrap_id=wrap_id,
    )


def extract_mode_from_pac(pac_text: str) -> ModeDeclaration:
    """
    Extract and validate mode declaration from PAC text.
    
    HARD FAIL if required fields not found or invalid.
    """
    return get_validator().validate_pac_header(pac_text)
