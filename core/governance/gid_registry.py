"""
ChainBridge GID Registry — HARD LAW Enforcement
════════════════════════════════════════════════════════════════════════════════

CANONICAL SOURCE: core/governance/gid_registry.json

This module provides Python enum and typed interfaces for GID enforcement.
ALL PACs are validated against this registry.
UNKNOWN GID → HARD FAIL (no exceptions, no warnings).

PAC Reference: PAC-BENSON-CTO-EXEC-CODY-IDENTITY-MODE-LAW-011
Effective Date: 2025-12-26

INVARIANTS:
- INV-GID-001: Unknown GID = immediate rejection
- INV-GID-002: GID format must be GID-XX (00-99)
- INV-GID-003: No agent may operate without registered GID
- INV-GID-004: GIDs are immutable once assigned
- INV-GID-005: Mode must be in agent's permitted_modes

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Set


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS — HARD FAIL CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class GIDEnforcementError(Exception):
    """Base exception for all GID enforcement failures. HARD STOP."""
    pass


class UnknownGIDError(GIDEnforcementError):
    """Raised when a GID is not found in the registry. HARD FAIL."""
    
    def __init__(self, gid: str):
        self.gid = gid
        super().__init__(
            f"HARD FAIL: Unknown GID '{gid}'. "
            f"GID must exist in gid_registry.json. "
            f"No conversational forgiveness. Execution halted."
        )


class InvalidGIDFormatError(GIDEnforcementError):
    """Raised when GID format is invalid. HARD FAIL."""
    
    def __init__(self, gid: str):
        self.gid = gid
        super().__init__(
            f"HARD FAIL: Invalid GID format '{gid}'. "
            f"Expected format: GID-XX where XX is 00-99. "
            f"Execution halted."
        )


class ModeNotPermittedError(GIDEnforcementError):
    """Raised when agent attempts to use unpermitted mode. HARD FAIL."""
    
    def __init__(self, gid: str, mode: str, permitted: List[str]):
        self.gid = gid
        self.mode = mode
        self.permitted = permitted
        super().__init__(
            f"HARD FAIL: Mode '{mode}' not permitted for {gid}. "
            f"Permitted modes: {permitted}. "
            f"Execution halted."
        )


class LaneNotPermittedError(GIDEnforcementError):
    """Raised when agent attempts to execute in unpermitted lane. HARD FAIL."""
    
    def __init__(self, gid: str, lane: str, permitted: List[str]):
        self.gid = gid
        self.lane = lane
        self.permitted = permitted
        super().__init__(
            f"HARD FAIL: Lane '{lane}' not permitted for {gid}. "
            f"Permitted lanes: {permitted}. "
            f"Execution halted."
        )


class PACAuthorityError(GIDEnforcementError):
    """Raised when agent attempts unauthorized PAC issuance. HARD FAIL."""
    
    def __init__(self, gid: str, action: str):
        self.gid = gid
        self.action = action
        super().__init__(
            f"HARD FAIL: {gid} is not authorized to {action}. "
            f"Only GID-00 (BENSON) has this authority. "
            f"Execution halted."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GID REGEX — IMMUTABLE PATTERN
# ═══════════════════════════════════════════════════════════════════════════════

GID_PATTERN = re.compile(r"^GID-(\d{2})$")


def validate_gid_format(gid: str) -> bool:
    """Validate GID format. Returns True if valid, raises otherwise."""
    if not GID_PATTERN.match(gid):
        raise InvalidGIDFormatError(gid)
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL REGISTRY PATH
# ═══════════════════════════════════════════════════════════════════════════════

REGISTRY_PATH = Path(__file__).parent / "gid_registry.json"


def _load_registry() -> dict:
    """Load the GID registry from JSON. FAIL if not found."""
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(
            f"HARD FAIL: GID Registry not found at {REGISTRY_PATH}. "
            f"This is a fatal governance violation."
        )
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Load once at module import
_REGISTRY = _load_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# GID ENUM — TYPED ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class GID(Enum):
    """
    GID Enum — All valid agent identifiers.
    
    HARD LAW: Only these GIDs are valid.
    Any other GID → HARD FAIL.
    """
    
    GID_00 = "GID-00"  # BENSON
    GID_01 = "GID-01"  # CODY
    GID_02 = "GID-02"  # SONNY
    GID_03 = "GID-03"  # MIRA-R
    GID_04 = "GID-04"  # CINDY
    GID_05 = "GID-05"  # PAX
    GID_06 = "GID-06"  # SAM
    GID_07 = "GID-07"  # DAN
    GID_08 = "GID-08"  # ALEX
    GID_09 = "GID-09"  # LIRA
    GID_10 = "GID-10"  # MAGGIE
    GID_11 = "GID-11"  # ATLAS
    GID_12 = "GID-12"  # DIGGI
    
    @classmethod
    def from_string(cls, gid_str: str) -> "GID":
        """
        Convert string to GID enum.
        
        HARD FAIL if GID not found.
        """
        validate_gid_format(gid_str)
        
        # Normalize to enum key format
        enum_key = gid_str.replace("-", "_")
        
        try:
            return cls[enum_key]
        except KeyError:
            raise UnknownGIDError(gid_str)
    
    @classmethod
    def is_valid(cls, gid_str: str) -> bool:
        """Check if GID string is valid. No exceptions."""
        try:
            cls.from_string(gid_str)
            return True
        except GIDEnforcementError:
            return False


class Mode(Enum):
    """Valid execution modes."""
    
    ORCHESTRATION = "ORCHESTRATION"
    EXECUTION = "EXECUTION"
    RESEARCH = "RESEARCH"
    ANALYSIS = "ANALYSIS"
    REVIEW = "REVIEW"
    AUDIT = "AUDIT"
    DESIGN = "DESIGN"
    STRATEGY = "STRATEGY"
    DEPLOY = "DEPLOY"
    GOVERNANCE = "GOVERNANCE"
    DOCUMENTATION = "DOCUMENTATION"
    SYNTHESIS = "SYNTHESIS"
    REFACTOR = "REFACTOR"
    TESTING = "TESTING"
    DEPLOYMENT = "DEPLOYMENT"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    PLANNING = "PLANNING"
    MAINTENANCE = "MAINTENANCE"
    ADVISORY = "ADVISORY"
    
    @classmethod
    def from_string(cls, mode_str: str) -> "Mode":
        """Convert string to Mode enum."""
        try:
            return cls[mode_str.upper()]
        except KeyError:
            raise ValueError(f"Invalid mode: {mode_str}")


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT DEFINITION — IMMUTABLE DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AgentIdentity:
    """
    Immutable agent identity from registry.
    
    All fields are frozen — no runtime mutation.
    """
    
    gid: str
    name: str
    role: str
    lane: str
    level: str
    permitted_modes: FrozenSet[str]
    execution_lanes: FrozenSet[str]
    can_issue_pac: bool
    can_issue_ber: bool
    can_override: bool
    
    def can_execute_mode(self, mode: str) -> bool:
        """Check if agent can execute in given mode."""
        return mode.upper() in self.permitted_modes
    
    def can_execute_lane(self, lane: str) -> bool:
        """Check if agent can execute in given lane."""
        if "ALL" in self.execution_lanes:
            return True
        return lane.upper() in self.execution_lanes
    
    def validate_mode(self, mode: str) -> None:
        """Validate mode. HARD FAIL if not permitted."""
        if not self.can_execute_mode(mode):
            raise ModeNotPermittedError(
                self.gid, mode, list(self.permitted_modes)
            )
    
    def validate_lane(self, lane: str) -> None:
        """Validate lane. HARD FAIL if not permitted."""
        if not self.can_execute_lane(lane):
            raise LaneNotPermittedError(
                self.gid, lane, list(self.execution_lanes)
            )
    
    def validate_pac_authority(self) -> None:
        """Validate PAC issuance authority. HARD FAIL if not authorized."""
        if not self.can_issue_pac:
            raise PACAuthorityError(self.gid, "issue PAC")
    
    def validate_ber_authority(self) -> None:
        """Validate BER issuance authority. HARD FAIL if not authorized."""
        if not self.can_issue_ber:
            raise PACAuthorityError(self.gid, "issue BER")


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY INTERFACE — CANONICAL ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

class GIDRegistry:
    """
    GID Registry — Canonical access to agent identities.
    
    SINGLETON PATTERN — One registry per runtime.
    """
    
    _instance: Optional["GIDRegistry"] = None
    
    def __new__(cls) -> "GIDRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Initialize registry from JSON."""
        self._agents: Dict[str, AgentIdentity] = {}
        self._valid_modes: Set[str] = set(_REGISTRY.get("valid_modes", []))
        self._valid_lanes: Set[str] = set(_REGISTRY.get("valid_lanes", []))
        
        for gid, data in _REGISTRY.get("agents", {}).items():
            self._agents[gid] = AgentIdentity(
                gid=gid,
                name=data["name"],
                role=data["role"],
                lane=data["lane"],
                level=data["level"],
                permitted_modes=frozenset(data.get("permitted_modes", [])),
                execution_lanes=frozenset(data.get("execution_lanes", [])),
                can_issue_pac=data.get("can_issue_pac", False),
                can_issue_ber=data.get("can_issue_ber", False),
                can_override=data.get("can_override", False),
            )
    
    def get_agent(self, gid: str) -> AgentIdentity:
        """
        Get agent by GID.
        
        HARD FAIL if GID not found.
        """
        validate_gid_format(gid)
        
        if gid not in self._agents:
            raise UnknownGIDError(gid)
        
        return self._agents[gid]
    
    def validate_gid(self, gid: str) -> AgentIdentity:
        """
        Validate GID exists and return agent.
        
        Alias for get_agent — explicit validation intent.
        """
        return self.get_agent(gid)
    
    def list_all_gids(self) -> List[str]:
        """List all valid GIDs."""
        return sorted(self._agents.keys())
    
    def list_agents_by_lane(self, lane: str) -> List[AgentIdentity]:
        """List agents in a specific lane."""
        return [
            agent for agent in self._agents.values()
            if agent.lane.upper() == lane.upper()
        ]
    
    def list_agents_by_mode(self, mode: str) -> List[AgentIdentity]:
        """List agents permitted for a specific mode."""
        return [
            agent for agent in self._agents.values()
            if mode.upper() in agent.permitted_modes
        ]
    
    def is_valid_mode(self, mode: str) -> bool:
        """Check if mode is valid."""
        return mode.upper() in self._valid_modes
    
    def is_valid_lane(self, lane: str) -> bool:
        """Check if lane is valid."""
        return lane.upper() in self._valid_lanes
    
    @property
    def registry_version(self) -> str:
        """Get registry version."""
        return _REGISTRY.get("registry_version", "unknown")


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS — MODULE-LEVEL ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

def get_registry() -> GIDRegistry:
    """Get the singleton GID registry."""
    return GIDRegistry()


def validate_agent_gid(gid: str) -> AgentIdentity:
    """
    Validate GID and return agent identity.
    
    HARD FAIL if invalid.
    """
    return get_registry().validate_gid(gid)


def validate_agent_mode(gid: str, mode: str) -> None:
    """
    Validate agent can execute in given mode.
    
    HARD FAIL if not permitted.
    """
    agent = validate_agent_gid(gid)
    agent.validate_mode(mode)


def validate_agent_lane(gid: str, lane: str) -> None:
    """
    Validate agent can execute in given lane.
    
    HARD FAIL if not permitted.
    """
    agent = validate_agent_gid(gid)
    agent.validate_lane(lane)


def validate_full_identity(gid: str, mode: str, lane: str) -> AgentIdentity:
    """
    Full identity validation — GID + MODE + LANE.
    
    HARD FAIL on any violation.
    """
    agent = validate_agent_gid(gid)
    agent.validate_mode(mode)
    agent.validate_lane(lane)
    return agent


# ═══════════════════════════════════════════════════════════════════════════════
# ECHO-BACK HANDSHAKE — MANDATORY FIRST OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def format_echo_handshake(gid: str, mode: str, lane: str) -> str:
    """
    Format the mandatory echo-back handshake.
    
    MUST be first line of agent output.
    Note: Does not validate - use validate_full_identity first.
    """
    return f"{gid} | MODE: {mode.upper()} | LANE: {lane.upper()}"


def validate_echo_handshake(output: str, expected_gid: str, expected_mode: str = None) -> tuple:
    """
    Validate echo-back handshake in output.
    
    Returns (True, None) if valid, (False, error_message) otherwise.
    """
    first_line = output.strip().split("\n")[0]
    
    if not first_line.startswith(expected_gid):
        return (False, f"Expected first line to start with '{expected_gid}'. Got: '{first_line[:50]}...'")
    
    # Optionally validate mode
    if expected_mode and f"MODE: {expected_mode.upper()}" not in first_line:
        return (False, f"Expected MODE: {expected_mode} in handshake. Got: '{first_line}'")
    
    return (True, None)
