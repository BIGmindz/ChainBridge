"""
Color Gateway Validator - PAC-BENSON-COLOR-GATEWAY-ENFORCEMENT-IMPLEMENTATION-01

Runtime enforcement of Color Gateway doctrine. Validates that executing agents
are permitted to operate in their declared color lanes per the canonical spec.

This module provides:
1. JSON-spec-based validation (authoritative from docs/governance/)
2. Exception classes for stop-the-line enforcement
3. PAC header validation for ingress enforcement

Reference: docs/governance/color_gateway_spec.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

# Re-export existing agent_roster functions for backward compatibility
from core.governance.agent_roster import (
    AGENT_CANONICAL_COLORS as AGENT_CANONICAL_COLORS,
    COLOR_LANES as COLOR_LANES,
    EMOJI_TO_COLOR as EMOJI_TO_COLOR,
    TEAL_RESERVED_GIDS as TEAL_RESERVED_GIDS,
    is_teal_allowed as is_teal_allowed,
    validate_agent_color as validate_agent_color,
    validate_color_gateway as validate_color_gateway,
    validate_teal_usage as validate_teal_usage,
)


# Exception classes for explicit failure modes (stop-the-line)
class ColorGatewayViolation(Exception):
    """Base exception for Color Gateway violations. Triggers stop-the-line."""
    pass


class ColorMismatchError(ColorGatewayViolation):
    """Agent GID does not match declared color lane."""
    pass


class TealExecutionError(ColorGatewayViolation):
    """TEAL lane cannot be used as executing lane (orchestration only)."""
    pass


class MissingFieldError(ColorGatewayViolation):
    """Required PAC header field is missing."""
    pass


class UnknownAgentError(ColorGatewayViolation):
    """Agent GID not found in registry."""
    pass


class UnknownColorError(ColorGatewayViolation):
    """Color lane not found in spec."""
    pass


# Paths to canonical governance files (JSON-based source of truth)
SPEC_PATH = Path(__file__).parent.parent.parent / "docs" / "governance" / "color_gateway_spec.json"
REGISTRY_PATH = Path(__file__).parent.parent.parent / "docs" / "governance" / "AGENT_REGISTRY.json"


def _load_spec() -> dict:
    """Load color gateway spec from canonical JSON."""
    if not SPEC_PATH.exists():
        raise FileNotFoundError(f"Color Gateway spec not found: {SPEC_PATH}")
    with open(SPEC_PATH, "r") as f:
        return json.load(f)


def _load_registry() -> dict:
    """Load agent registry from canonical JSON."""
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Agent Registry not found: {REGISTRY_PATH}")
    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)


def _normalize_color(color: str) -> str:
    """Normalize color name for comparison (uppercase, strip emoji, strip whitespace)."""
    # Strip common emoji patterns
    stripped = color
    for emoji in ["🟦🟩", "🔵", "🟡", "🟣", "🟠", "🔴", "🟢", "⚪", "🩷", "💗", "🔷"]:
        stripped = stripped.replace(emoji, "")
    # Normalize whitespace and case
    return stripped.strip().upper().replace(" ", "_").replace("/", "_")


def validate_execution(
    executing_agent_gid: str,
    executing_color: str,
    pac_id: Optional[str] = None
) -> dict:
    """
    Validate that an agent is permitted to execute in the declared color lane.

    Args:
        executing_agent_gid: The GID of the executing agent (e.g., "GID-01")
        executing_color: The declared executing color (e.g., "BLUE" or "🔵 BLUE")
        pac_id: Optional PAC ID for error context

    Returns:
        dict with validation result:
            {
                "valid": True,
                "agent_name": "CODY",
                "gid": "GID-01",
                "color": "BLUE",
                "pac_id": "PAC-..."
            }

    Raises:
        MissingFieldError: If required fields are missing
        UnknownAgentError: If GID not in registry
        UnknownColorError: If color not in spec
        TealExecutionError: If TEAL used as executing lane
        ColorMismatchError: If agent not permitted in color lane
    """
    # Load canonical sources
    spec = _load_spec()
    registry = _load_registry()

    # Validate required fields
    if not executing_agent_gid:
        raise MissingFieldError("EXECUTING GID is required")
    if not executing_color:
        raise MissingFieldError("EXECUTING COLOR is required")

    # Normalize inputs
    gid = executing_agent_gid.strip().upper()
    color_normalized = _normalize_color(executing_color)

    # Map normalized color names to spec keys (matches color_gateway_spec.json)
    color_map = {
        "TEAL": "TEAL",
        "BLUE": "BLUE",
        "YELLOW": "YELLOW",
        "PURPLE": "PURPLE",
        "ORANGE": "ORANGE",
        "DARK_RED": "DARK RED",
        "DARKRED": "DARK RED",
        "DARK": "DARK RED",  # partial match fallback
        "RED": "DARK RED",
        "GREEN": "GREEN",
        "WHITE": "WHITE",
        "GREY": "WHITE",
        "WHITE_GREY": "WHITE",
        "PINK": "PINK",
    }

    spec_color_key = color_map.get(color_normalized)
    if not spec_color_key:
        raise UnknownColorError(f"Unknown color lane: {executing_color}")

    # Check if color exists in spec
    lanes = spec.get("lanes", {})
    if spec_color_key not in lanes:
        raise UnknownColorError(f"Color lane not in spec: {spec_color_key}")

    lane_spec = lanes[spec_color_key]

    # Rule: TEAL cannot be executing lane
    if spec_color_key == "TEAL":
        raise TealExecutionError(
            f"TEAL lane is orchestration-only and cannot be used as executing lane. "
            f"PAC: {pac_id or 'unknown'}"
        )

    # Validate GID exists in registry
    gid_index = registry.get("gid_index", {})
    if gid not in gid_index:
        raise UnknownAgentError(f"Unknown agent GID: {gid}")

    agent_name = gid_index[gid]

    # Validate GID is permitted in this color lane
    allowed_gids = lane_spec.get("allowed_gids", [])
    if gid not in allowed_gids:
        expected_agents = lane_spec.get("allowed_agents", [])
        raise ColorMismatchError(
            f"Agent {agent_name} ({gid}) is not permitted in {spec_color_key} lane. "
            f"Allowed: {expected_agents} ({allowed_gids}). "
            f"PAC: {pac_id or 'unknown'}"
        )

    # Success
    return {
        "valid": True,
        "agent_name": agent_name,
        "gid": gid,
        "color": spec_color_key,
        "pac_id": pac_id,
    }


def validate_pac_header(pac_header: dict) -> dict:
    """
    Validate a PAC header dictionary for Color Gateway compliance.

    Args:
        pac_header: Dict with keys like "EXECUTING AGENT", "EXECUTING GID", "EXECUTING COLOR"

    Returns:
        Validation result dict

    Raises:
        MissingFieldError: If required fields missing
        ColorGatewayViolation subclass: On validation failure
    """
    executing_agent = pac_header.get("EXECUTING AGENT")
    executing_gid = pac_header.get("EXECUTING GID")
    executing_color = pac_header.get("EXECUTING COLOR")
    pac_id = pac_header.get("PAC ID") or pac_header.get("pac_id")

    if not executing_agent:
        raise MissingFieldError("PAC header missing: EXECUTING AGENT")
    if not executing_gid:
        raise MissingFieldError("PAC header missing: EXECUTING GID")
    if not executing_color:
        raise MissingFieldError("PAC header missing: EXECUTING COLOR")

    return validate_execution(
        executing_agent_gid=executing_gid,
        executing_color=executing_color,
        pac_id=pac_id,
    )


def get_agent_color(gid: str) -> str:
    """
    Look up the canonical color for an agent GID.

    Args:
        gid: Agent GID (e.g., "GID-01")

    Returns:
        Color name (e.g., "BLUE")

    Raises:
        UnknownAgentError: If GID not found
    """
    registry = _load_registry()
    gid_index = registry.get("gid_index", {})
    gid = gid.strip().upper()

    if gid not in gid_index:
        raise UnknownAgentError(f"Unknown agent GID: {gid}")

    agent_name = gid_index[gid]
    agents = registry.get("agents", {})
    agent_info = agents.get(agent_name, {})

    return agent_info.get("color", "UNKNOWN")


def get_color_agents(color: str) -> list[str]:
    """
    Get list of agent GIDs permitted in a color lane.

    Args:
        color: Color name (e.g., "BLUE")

    Returns:
        List of GIDs (e.g., ["GID-01", "GID-11"])

    Raises:
        UnknownColorError: If color not found
    """
    spec = _load_spec()
    color_normalized = _normalize_color(color)

    color_map = {
        "TEAL": "TEAL",
        "BLUE": "BLUE",
        "YELLOW": "YELLOW",
        "PURPLE": "PURPLE",
        "ORANGE": "ORANGE",
        "DARK_RED": "DARK_RED",
        "GREEN": "GREEN",
        "WHITE": "WHITE",
        "GREY": "WHITE",
        "PINK": "PINK",
    }

    spec_key = color_map.get(color_normalized)
    if not spec_key:
        raise UnknownColorError(f"Unknown color: {color}")

    lanes = spec.get("lanes", {})
    if spec_key not in lanes:
        raise UnknownColorError(f"Color not in spec: {spec_key}")

    return lanes[spec_key].get("allowed_gids", [])
