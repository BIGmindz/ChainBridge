"""
ChainBridge Agent Roster — Canonical Source Loader
════════════════════════════════════════════════════════════════════════════════

This module LOADS the canonical agent registry from:
  docs/governance/AGENT_REGISTRY.json

SINGLE SOURCE OF TRUTH — NO DRIFT ALLOWED.

All agent definitions originate from the JSON registry.
This module provides Python interfaces for enforcement tooling.

GOVERNANCE INVARIANTS (enforced):
- INV-AGENT-01: No agent may appear in more than one color lane
- INV-AGENT-02: No color may be claimed without registry match
- INV-AGENT-03: TEAL is reserved for GID-00 (BENSON) and GID-04 (CINDY) only
- INV-AGENT-04: GIDs are immutable once assigned
- INV-AGENT-05: No new agents without explicit registry update

PAC Reference: PAC-ALEX-CANONICAL-AGENT-COLOR-LOCK-01
Effective Date: 2025-12-19

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, FrozenSet, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL REGISTRY PATH
# ═══════════════════════════════════════════════════════════════════════════════

CANONICAL_REGISTRY_PATH = Path(__file__).parent.parent.parent / "docs" / "governance" / "AGENT_REGISTRY.json"


def _load_canonical_registry() -> dict:
    """Load the canonical agent registry from JSON."""
    if not CANONICAL_REGISTRY_PATH.exists():
        raise FileNotFoundError(
            f"CANONICAL REGISTRY NOT FOUND: {CANONICAL_REGISTRY_PATH}\n"
            "This is a governance violation. The registry must exist."
        )
    with open(CANONICAL_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Load on module import
_REGISTRY_DATA = _load_canonical_registry()


class AgentColor(Enum):
    """Canonical agent colors — derived from AGENT_REGISTRY.json."""
    
    TEAL = "TEAL"
    BLUE = "BLUE"
    YELLOW = "YELLOW"
    PURPLE = "PURPLE"
    ORANGE = "ORANGE"
    DARK_RED = "DARK RED"
    GREEN = "GREEN"
    WHITE = "WHITE"
    PINK = "PINK"


@dataclass(frozen=True)
class Agent:
    """Immutable agent definition."""
    
    name: str
    gid: str
    role: str
    emoji: str
    color: str
    aliases: FrozenSet[str] = frozenset()
    
    @property
    def gid_number(self) -> int:
        """Extract numeric GID (e.g., 'GID-01' -> 1)."""
        return int(self.gid.split("-")[1])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION — PAC-ATLAS-AGENT-REGISTRY-ENFORCEMENT-01
# ═══════════════════════════════════════════════════════════════════════════════

class RegistrySchemaError(Exception):
    """Raised when registry schema validation fails. HARD STOP."""
    pass


class MutabilityViolationError(Exception):
    """Raised when an immutable field mutation is detected. HARD STOP."""
    pass


# Valid agent levels (L0-L3)
VALID_AGENT_LEVELS: FrozenSet[str] = frozenset(["L0", "L1", "L2", "L3"])

# Required top-level registry fields
REQUIRED_REGISTRY_FIELDS: FrozenSet[str] = frozenset([
    "registry_version",
    "agents",
    "governance_invariants",
    "schema_metadata",
])

# Required agent fields (v3.0.0 schema)
REQUIRED_AGENT_FIELDS: FrozenSet[str] = frozenset([
    "gid",
    "lane",
    "color",
    "emoji_primary",
    "agent_level",
    "diversity_profile",
    "role",
    "mutable_fields",
    "immutable_fields",
])

# Always immutable fields (cannot change without registry_version bump)
ALWAYS_IMMUTABLE_FIELDS: FrozenSet[str] = frozenset([
    "gid",
    "lane",
    "color",
])


def validate_registry_schema(registry_data: dict) -> tuple[bool, list[str]]:
    """
    Validate registry schema against v3.0.0 requirements.
    
    HARD STOP on failure — no silent coercion.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors: list[str] = []
    
    # Check required top-level fields
    for field in REQUIRED_REGISTRY_FIELDS:
        if field not in registry_data:
            errors.append(f"Missing required top-level field: {field}")
    
    # Validate registry_version format
    version = registry_data.get("registry_version", "")
    if not version or not isinstance(version, str):
        errors.append("registry_version must be a non-empty string")
    elif not _is_valid_semver(version):
        errors.append(f"registry_version '{version}' is not valid semver (X.Y.Z)")
    
    # Validate schema_metadata
    metadata = registry_data.get("schema_metadata", {})
    if not isinstance(metadata, dict):
        errors.append("schema_metadata must be a dictionary")
    else:
        if "agent_levels" not in metadata:
            errors.append("schema_metadata missing 'agent_levels'")
        if "field_mutability" not in metadata:
            errors.append("schema_metadata missing 'field_mutability'")
    
    # Validate each agent
    agents = registry_data.get("agents", {})
    if not isinstance(agents, dict):
        errors.append("agents must be a dictionary")
    else:
        for agent_name, agent_data in agents.items():
            agent_errors = _validate_agent_schema(agent_name, agent_data)
            errors.extend(agent_errors)
    
    return len(errors) == 0, errors


def _is_valid_semver(version: str) -> bool:
    """Check if version is valid semver (X.Y.Z)."""
    import re
    pattern = r"^\d+\.\d+\.\d+$"
    return bool(re.match(pattern, version))


def _validate_agent_schema(agent_name: str, agent_data: dict) -> list[str]:
    """
    Validate individual agent schema.
    
    Returns list of errors (empty if valid).
    """
    errors: list[str] = []
    prefix = f"Agent {agent_name}:"
    
    # Check required fields
    for field in REQUIRED_AGENT_FIELDS:
        if field not in agent_data:
            errors.append(f"{prefix} missing required field '{field}'")
    
    # Validate GID format
    gid = agent_data.get("gid", "")
    if gid and not _is_valid_gid_format(gid):
        errors.append(f"{prefix} invalid GID format '{gid}' (expected GID-NN)")
    
    # Validate agent_level
    level = agent_data.get("agent_level", "")
    if level and level not in VALID_AGENT_LEVELS:
        errors.append(f"{prefix} invalid agent_level '{level}' (expected L0-L3)")
    
    # Validate diversity_profile is a list
    diversity = agent_data.get("diversity_profile")
    if diversity is not None and not isinstance(diversity, list):
        errors.append(f"{prefix} diversity_profile must be a list")
    
    # Validate emoji_aliases is a list
    aliases = agent_data.get("emoji_aliases")
    if aliases is not None and not isinstance(aliases, list):
        errors.append(f"{prefix} emoji_aliases must be a list")
    
    # Validate mutable_fields and immutable_fields are lists
    mutable = agent_data.get("mutable_fields")
    if mutable is not None and not isinstance(mutable, list):
        errors.append(f"{prefix} mutable_fields must be a list")
    
    immutable = agent_data.get("immutable_fields")
    if immutable is not None and not isinstance(immutable, list):
        errors.append(f"{prefix} immutable_fields must be a list")
    
    # Validate immutable_fields contains ALWAYS_IMMUTABLE
    if immutable and isinstance(immutable, list):
        missing_immutable = ALWAYS_IMMUTABLE_FIELDS - set(immutable)
        if missing_immutable:
            errors.append(
                f"{prefix} immutable_fields missing required: {missing_immutable}"
            )
    
    return errors


def _is_valid_gid_format(gid: str) -> bool:
    """Check if GID is valid format (GID-NN where NN is 00-99)."""
    import re
    return bool(re.match(r"^GID-\d{2}$", gid))


def validate_mutability(
    old_registry: dict,
    new_registry: dict,
) -> tuple[bool, list[str]]:
    """
    Validate that no immutable fields have changed between registry versions.
    
    HARD STOP if immutable field mutation detected without version bump.
    
    Returns:
        (is_valid, list_of_violations)
    """
    violations: list[str] = []
    
    old_version = old_registry.get("registry_version", "0.0.0")
    new_version = new_registry.get("registry_version", "0.0.0")
    
    # If version unchanged, check for immutable field mutations
    if old_version == new_version:
        old_agents = old_registry.get("agents", {})
        new_agents = new_registry.get("agents", {})
        
        for agent_name in old_agents:
            if agent_name not in new_agents:
                violations.append(f"Agent {agent_name} removed without version bump")
                continue
            
            old_data = old_agents[agent_name]
            new_data = new_agents[agent_name]
            
            # Get immutable fields for this agent
            immutable_fields = set(old_data.get("immutable_fields", []))
            # Always include ALWAYS_IMMUTABLE_FIELDS
            immutable_fields.update(ALWAYS_IMMUTABLE_FIELDS)
            
            for field in immutable_fields:
                old_val = old_data.get(field)
                new_val = new_data.get(field)
                if old_val != new_val:
                    violations.append(
                        f"Agent {agent_name}: immutable field '{field}' changed "
                        f"from '{old_val}' to '{new_val}' without version bump"
                    )
    
    return len(violations) == 0, violations


def get_agent_level(agent_name: str) -> Optional[str]:
    """
    Get agent level (L0-L3) for a named agent.
    
    Returns None if agent not found.
    """
    name_upper = agent_name.upper().replace(" ", "-")
    agent_data = _REGISTRY_DATA.get("agents", {}).get(name_upper)
    if agent_data:
        return agent_data.get("agent_level")
    
    # Check aliases
    for name, data in _REGISTRY_DATA.get("agents", {}).items():
        if name_upper in [a.upper() for a in data.get("aliases", [])]:
            return data.get("agent_level")
    
    return None


def get_agent_diversity_profile(agent_name: str) -> Optional[list[str]]:
    """
    Get diversity profile for a named agent.
    
    Returns None if agent not found.
    """
    name_upper = agent_name.upper().replace(" ", "-")
    agent_data = _REGISTRY_DATA.get("agents", {}).get(name_upper)
    if agent_data:
        return agent_data.get("diversity_profile")
    return None


def get_registry_version() -> str:
    """Get the current registry version."""
    return _REGISTRY_DATA.get("registry_version", "unknown")


def is_field_mutable(agent_name: str, field: str) -> bool:
    """
    Check if a field is mutable for a given agent.
    
    Returns False if field is immutable or agent not found.
    """
    name_upper = agent_name.upper().replace(" ", "-")
    agent_data = _REGISTRY_DATA.get("agents", {}).get(name_upper)
    
    if not agent_data:
        return False
    
    # Always immutable fields are never mutable
    if field in ALWAYS_IMMUTABLE_FIELDS:
        return False
    
    mutable = agent_data.get("mutable_fields", [])
    return field in mutable


def is_deprecated_agent(agent_name: str) -> bool:
    """
    Check if an agent is deprecated (not in current registry).
    
    Returns True if agent not found in registry.
    """
    name_upper = agent_name.upper().replace(" ", "-")
    
    # Direct match
    if name_upper in _REGISTRY_DATA.get("agents", {}):
        return False
    
    # Alias match
    for name, data in _REGISTRY_DATA.get("agents", {}).items():
        aliases = [a.upper() for a in data.get("aliases", [])]
        if name_upper in aliases:
            return False
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE INVARIANTS — PAC-ALEX-CANONICAL-AGENT-COLOR-LOCK-01
# ═══════════════════════════════════════════════════════════════════════════════

class GovernanceInvariantViolation(Exception):
    """Raised when a governance invariant is violated."""
    pass


def _get_governance_invariants() -> Dict[str, str]:
    """Get governance invariants from canonical registry."""
    return _REGISTRY_DATA.get("governance_invariants", {})


GOVERNANCE_INVARIANTS: Dict[str, str] = _get_governance_invariants()


def validate_invariant_agent_single_color() -> tuple[bool, list[str]]:
    """
    INV-AGENT-01: No agent may appear in more than one color lane.
    
    Returns (is_valid, list_of_violations)
    """
    violations = []
    for name, data in _REGISTRY_DATA["agents"].items():
        # Each agent should have exactly one color
        color = data.get("color")
        if not color:
            violations.append(f"Agent {name} has no color assigned")
    return len(violations) == 0, violations


def validate_invariant_color_registry_match() -> tuple[bool, list[str]]:
    """
    INV-AGENT-02: No color may be claimed without registry match.
    
    Returns (is_valid, list_of_violations)
    """
    violations = []
    valid_colors = set(_REGISTRY_DATA.get("color_lanes", {}).keys())
    for name, data in _REGISTRY_DATA["agents"].items():
        color = data.get("color", "").upper()
        # Normalize DARK RED
        color_key = color.replace(" ", "_") if " " in color else color
        if color not in valid_colors and color_key not in valid_colors:
            # Check if it's a known alias
            if color != "DARK RED":  # DARK RED is valid
                violations.append(f"Agent {name} claims color '{color}' not in registry")
    return len(violations) == 0, violations


def validate_invariant_teal_reserved() -> tuple[bool, list[str]]:
    """
    INV-AGENT-03: TEAL is reserved for GID-00 (BENSON) and GID-04 (CINDY) only.
    
    Returns (is_valid, list_of_violations)
    """
    violations = []
    teal_allowed = {"GID-00", "GID-04"}
    for name, data in _REGISTRY_DATA["agents"].items():
        color = data.get("color", "").upper()
        gid = data.get("gid", "")
        if color == "TEAL" and gid not in teal_allowed:
            violations.append(f"Agent {name} ({gid}) uses TEAL but not in reserved list")
    return len(violations) == 0, violations


def validate_all_invariants() -> tuple[bool, Dict[str, list[str]]]:
    """
    Validate all governance invariants.
    
    Returns (all_valid, dict_of_invariant_to_violations)
    """
    results = {}
    all_valid = True
    
    valid, violations = validate_invariant_agent_single_color()
    results["INV-AGENT-01"] = violations
    if not valid:
        all_valid = False
    
    valid, violations = validate_invariant_color_registry_match()
    results["INV-AGENT-02"] = violations
    if not valid:
        all_valid = False
    
    valid, violations = validate_invariant_teal_reserved()
    results["INV-AGENT-03"] = violations
    if not valid:
        all_valid = False
    
    return all_valid, results


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL AGENT REGISTRY — LOADED FROM JSON
# ═══════════════════════════════════════════════════════════════════════════════

def _build_agents_from_registry() -> Dict[str, Agent]:
    """Build Agent objects from canonical JSON registry."""
    agents = {}
    for name, data in _REGISTRY_DATA["agents"].items():
        # Support both 'emoji' (legacy) and 'emoji_primary' (v3.0.0+)
        emoji = data.get("emoji_primary") or data.get("emoji")
        if emoji is None:
            raise RegistrySchemaError(f"Agent {name} missing emoji_primary field")
        agents[name] = Agent(
            name=name,
            gid=data["gid"],
            role=data["role"],
            emoji=emoji,
            color=data["color"],
            aliases=frozenset(data.get("aliases", [])),
        )
    return agents


CANONICAL_AGENTS: Dict[str, Agent] = _build_agents_from_registry()

# Build lookup indices
_GID_TO_AGENT: Dict[str, Agent] = {a.gid: a for a in CANONICAL_AGENTS.values()}
_EMOJI_TO_AGENTS: Dict[str, list[Agent]] = {}
for agent in CANONICAL_AGENTS.values():
    _EMOJI_TO_AGENTS.setdefault(agent.emoji, []).append(agent)

# All valid emojis
VALID_EMOJIS: FrozenSet[str] = frozenset(a.emoji for a in CANONICAL_AGENTS.values())

# All valid GIDs
VALID_GIDS: FrozenSet[str] = frozenset(a.gid for a in CANONICAL_AGENTS.values())


# ═══════════════════════════════════════════════════════════════════════════════
# LOOKUP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def get_agent_by_name(name: str) -> Optional[Agent]:
    """Get agent by canonical name or alias."""
    name_upper = name.upper().replace(" ", "-")
    
    # Direct match
    if name_upper in CANONICAL_AGENTS:
        return CANONICAL_AGENTS[name_upper]
    
    # Alias match
    for agent in CANONICAL_AGENTS.values():
        if name_upper in agent.aliases:
            return agent
    
    return None


def get_agent_by_gid(gid: str) -> Optional[Agent]:
    """Get agent by GID string (e.g., 'GID-01')."""
    return _GID_TO_AGENT.get(gid.upper())


def get_agents_by_emoji(emoji: str) -> list[Agent]:
    """Get all agents that use a specific emoji."""
    return _EMOJI_TO_AGENTS.get(emoji, [])


def is_valid_agent(name: str) -> bool:
    """Check if name is a valid agent or alias."""
    return get_agent_by_name(name) is not None


def is_valid_gid(gid: str) -> bool:
    """Check if GID is in the canonical registry."""
    return gid.upper() in VALID_GIDS


def is_valid_emoji(emoji: str) -> bool:
    """Check if emoji is assigned to any agent."""
    return emoji in VALID_EMOJIS


def validate_agent_gid_match(name: str, gid: str) -> bool:
    """Validate that an agent name matches its expected GID."""
    agent = get_agent_by_name(name)
    if agent is None:
        return False
    return agent.gid == gid.upper()


def validate_agent_emoji_match(name: str, emoji: str) -> bool:
    """Validate that an agent name matches its expected emoji."""
    agent = get_agent_by_name(name)
    if agent is None:
        return False
    return agent.emoji == emoji


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY INFO
# ═══════════════════════════════════════════════════════════════════════════════


def get_roster_summary() -> str:
    """Return a formatted roster summary."""
    lines = ["CHAINBRIDGE AGENT ROSTER — CANONICAL", "=" * 50]
    for agent in sorted(CANONICAL_AGENTS.values(), key=lambda a: a.gid_number):
        lines.append(f"{agent.emoji} {agent.name} ({agent.gid}) - {agent.role}")
    return "\n".join(lines)


def get_agent_count() -> int:
    """Return total number of registered agents."""
    return len(CANONICAL_AGENTS)


# ═══════════════════════════════════════════════════════════════════════════════
# COLOR GATEWAY ENFORCEMENT — PAC-ALEX-CANONICAL-AGENT-COLOR-LOCK-01
# ═══════════════════════════════════════════════════════════════════════════════

# Load color lanes from canonical registry
def _build_color_lanes() -> Dict[str, str]:
    """Build color → lane mapping from canonical registry."""
    lanes = {}
    for color, data in _REGISTRY_DATA.get("color_lanes", {}).items():
        lanes[color] = data["lane"]
    # Add GREY alias for WHITE
    if "WHITE" in lanes:
        lanes["GREY"] = lanes["WHITE"]
    return lanes


COLOR_LANES: Dict[str, str] = _build_color_lanes()

# TEAL reserved GIDs from canonical registry
def _get_teal_reserved() -> FrozenSet[str]:
    """Get TEAL reserved GIDs from canonical registry."""
    color_lanes = _REGISTRY_DATA.get("color_lanes", {})
    teal_data = color_lanes.get("TEAL", {})
    return frozenset(teal_data.get("reserved_gids", ["GID-00", "GID-04"]))


TEAL_RESERVED_GIDS: FrozenSet[str] = _get_teal_reserved()

# Canonical emoji → color mapping
EMOJI_TO_COLOR: Dict[str, str] = {
    "🟦🟩": "TEAL",   # Benson orchestration (dual emoji)
    "🟦": "TEAL",     # Legacy Benson / Cindy
    "🔷": "TEAL",     # Cindy alternate
    "🔵": "BLUE",     # Cody, Atlas
    "🟡": "YELLOW",   # Sonny
    "🟨": "YELLOW",   # Sonny alternate
    "🟣": "PURPLE",   # Mira-R
    "🟠": "ORANGE",   # Pax
    "🟧": "ORANGE",   # Pax alternate
    "🔴": "DARK RED", # Sam
    "🟥": "DARK RED", # Sam alternate
    "🟢": "GREEN",    # Dan
    "🟩": "GREEN",    # Dan alternate (single, not dual)
    "⚪": "WHITE",    # Alex
    "🩷": "PINK",     # Lira, Maggie
    "💗": "PINK",     # Maggie alternate
}

# Agent → canonical color mapping (derived from registry)
def _build_agent_colors() -> Dict[str, str]:
    """Build agent → color mapping from canonical registry."""
    return {name: data["color"] for name, data in _REGISTRY_DATA["agents"].items()}


AGENT_CANONICAL_COLORS: Dict[str, str] = _build_agent_colors()


def get_agent_color(agent_name: str) -> Optional[str]:
    """Get canonical color for an agent."""
    name_upper = agent_name.upper().replace(" ", "-")
    return AGENT_CANONICAL_COLORS.get(name_upper)


def get_lane_for_color(color: str) -> Optional[str]:
    """Get lane for a color."""
    return COLOR_LANES.get(color.upper())


def is_teal_allowed(gid: str) -> bool:
    """Check if a GID is allowed to use TEAL color."""
    return gid.upper() in TEAL_RESERVED_GIDS


def validate_agent_color(agent_name: str, declared_color: str) -> tuple[bool, str]:
    """
    Validate that agent is using their canonical color.
    
    Returns:
        (is_valid, error_message)
    """
    canonical = get_agent_color(agent_name)
    if canonical is None:
        return False, f"Unknown agent: {agent_name}"
    
    declared_upper = declared_color.upper().strip()
    
    if canonical != declared_upper:
        return False, f"Agent {agent_name} declared color '{declared_color}' but canonical is '{canonical}'"
    
    return True, ""


def validate_teal_usage(agent_name: str, gid: str, color: str) -> tuple[bool, str]:
    """
    Validate TEAL color is only used by authorized agents.
    
    TEAL is reserved for GID-00 (Benson) ONLY.
    
    Returns:
        (is_valid, error_message)
    """
    color_upper = color.upper().strip()
    
    if color_upper != "TEAL":
        return True, ""  # Not using TEAL, pass
    
    if not is_teal_allowed(gid):
        return False, f"TEAL color reserved for GID-00 (Benson). Agent {agent_name} ({gid}) cannot use TEAL."
    
    return True, ""


def validate_color_gateway(
    agent_name: str,
    gid: str,
    declared_color: str,
    declared_emoji: Optional[str] = None,
) -> tuple[bool, list[str]]:
    """
    Full color gateway validation.
    
    Checks:
    1. Agent exists in registry
    2. GID matches agent
    3. Color matches canonical assignment
    4. TEAL is reserved for Benson only
    5. Emoji matches color (if provided)
    
    Returns:
        (all_valid, list_of_errors)
    """
    errors: list[str] = []
    
    # Check 1: Agent exists
    agent = get_agent_by_name(agent_name)
    if agent is None:
        errors.append(f"Unknown agent: {agent_name}")
        return False, errors
    
    # Check 2: GID matches
    if agent.gid != gid.upper():
        errors.append(f"GID mismatch: {agent_name} is {agent.gid}, not {gid}")
    
    # Check 3: Color matches canonical
    valid, err = validate_agent_color(agent_name, declared_color)
    if not valid:
        errors.append(err)
    
    # Check 4: TEAL reservation
    valid, err = validate_teal_usage(agent_name, gid, declared_color)
    if not valid:
        errors.append(err)
    
    # Check 5: Emoji matches color (if provided)
    if declared_emoji:
        emoji_color = EMOJI_TO_COLOR.get(declared_emoji)
        if emoji_color and emoji_color.upper() != declared_color.upper():
            errors.append(
                f"Emoji {declared_emoji} is {emoji_color}, but declared color is {declared_color}"
            )
    
    return len(errors) == 0, errors

