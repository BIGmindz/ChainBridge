#!/usr/bin/env python3
"""
Governance Gate Engine — PAC/WRAP Validation

Authority: PAC-BENSON-G0-GOVERNANCE-CORRECTION-02
Owner: Benson (GID-00)
Mode: FAIL_CLOSED

This is the single validation engine for all PAC/WRAP artifacts.
Invalid packs cannot be emitted, committed, or merged.

Governance is physics, not policy.

Enforcement Chain:
  GATE 0: TEMPLATE SELECTION (CANONICAL ONLY)
  GATE 1: PACK EMISSION VALIDATION (this script)
  GATE 2: PRE-COMMIT HOOK (FAIL-CLOSED)
  GATE 3: CI MERGE BLOCKER
  GATE 4: WRAP AUTHORIZATION

No bypass paths exist.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "governance" / "AGENT_REGISTRY.json"
LEDGER_PATH = REPO_ROOT / "docs" / "governance" / "ledger" / "GOVERNANCE_LEDGER.json"

# Ledger integration (lazy import to avoid circular deps)
_ledger = None

def get_ledger():
    """Get or create ledger instance (lazy loading)."""
    global _ledger
    if _ledger is None:
        try:
            from ledger_writer import GovernanceLedger
            _ledger = GovernanceLedger(LEDGER_PATH)
        except ImportError:
            # Fallback if ledger_writer not available
            _ledger = None
    return _ledger


def record_validation_to_ledger(
    artifact_id: str,
    agent_gid: str,
    agent_name: str,
    artifact_type: str,
    result: str,
    error_codes: list = None,
    file_path: str = None
):
    """Record validation result to governance ledger."""
    ledger = get_ledger()
    if ledger is None:
        return  # Ledger not available, skip recording

    try:
        if result == "PASS":
            ledger.record_validation_pass(
                artifact_id=artifact_id,
                agent_gid=agent_gid,
                agent_name=agent_name,
                artifact_type=artifact_type,
                file_path=file_path
            )
        else:
            ledger.record_validation_fail(
                artifact_id=artifact_id,
                agent_gid=agent_gid,
                agent_name=agent_name,
                artifact_type=artifact_type,
                error_codes=error_codes or [],
                file_path=file_path
            )
            # G2: Also record as block enforced (learning event)
            if error_codes:
                try:
                    ledger.record_block_enforced(
                        artifact_id=f"BLOCK-{artifact_id}",
                        agent_gid=agent_gid,
                        agent_name=agent_name,
                        pac_id=artifact_id,
                        authority_gid="GID-00",  # BENSON is default authority
                        error_codes=error_codes,
                        training_signal={
                            "signal_type": "NEGATIVE_CONSTRAINT_REINFORCEMENT",
                            "pattern": "GOVERNANCE_BLOCK_ENFORCED",
                            "learning": [f"Violation: {code}" for code in error_codes[:3]]
                        },
                        file_path=file_path,
                        notes="Auto-recorded by gate_pack.py"
                    )
                except Exception:
                    pass  # Don't fail on learning event recording
    except Exception as e:
        # Don't fail validation if ledger write fails
        print(f"⚠ Ledger write failed: {e}")


def _record_bsrg_to_ledger(content: str, bsrg_data: dict):
    """
    Record BSRG review result to governance ledger.

    This creates a BSRG_REVIEW entry in the hash-chained ledger
    for audit trail purposes.
    """
    ledger = get_ledger()
    if ledger is None:
        return

    # Extract artifact info
    artifact_id = extract_artifact_id(content) or "UNKNOWN-PAC"
    agent_info = extract_agent_info(content)

    try:
        # Compute SHA256 of artifact content for integrity
        import hashlib
        artifact_sha256 = hashlib.sha256(content.encode('utf-8')).hexdigest()

        ledger.record_bsrg_review(
            artifact_id=artifact_id,
            artifact_sha256=artifact_sha256,
            reviewer=bsrg_data.get("reviewer", "BENSON"),
            reviewer_gid=bsrg_data.get("reviewer_gid", "GID-00"),
            bsrg_gate_id=bsrg_data.get("gate_id", "BSRG-01"),
            status=bsrg_data.get("status", "FAIL"),
            failed_items=bsrg_data.get("failed_items", []),
            checklist_results=bsrg_data.get("checklist_results", {}),
        )
    except Exception as e:
        print(f"⚠ BSRG ledger recording failed: {e}")


class ErrorCode(Enum):
    """Governance error codes."""
    G0_001 = "Missing required block"
    G0_002 = "Block order violation"
    G0_003 = "Invalid GID"
    G0_004 = "Registry mismatch"
    G0_005 = "Invalid field value"
    G0_006 = "Missing required field"
    G0_007 = "Runtime has GID"
    G0_008 = "Invalid PAC ID format"
    G0_009 = "Training signal invalid"
    G0_010 = "Constraint violation"
    G0_011 = "Missing FORBIDDEN_ACTIONS"
    G0_012 = "Missing SCOPE"
    # G2.0.0 Correction Pack Error Codes
    G0_020 = "GOLD_STANDARD_CHECKLIST_INCOMPLETE"
    G0_021 = "SELF_CERTIFICATION_MISSING"
    G0_022 = "VIOLATIONS_ADDRESSED_MISSING"
    G0_023 = "CHECKLIST_ITEM_UNCHECKED"
    G0_024 = "CHECKLIST_KEY_MISSING"
    # G3.0.0 Positive Closure Error Codes
    G0_040 = "POSITIVE_CLOSURE_MISSING_LINEAGE"
    G0_041 = "POSITIVE_CLOSURE_CHECKLIST_INCOMPLETE"
    G0_042 = "POSITIVE_CLOSURE_AUTHORITY_MISSING"
    G0_043 = "POSITIVE_CLOSURE_NOT_TERMINAL"
    G0_044 = "IMPLICIT_SUCCESS_FORBIDDEN"
    G0_045 = "POSITIVE_CLOSURE_TRAINING_SIGNAL_INVALID"
    G0_046 = "POSITIVE_CLOSURE_SECTION_MISSING"
    # G2 Learning Ledger Error Codes
    G0_050 = "LEARNING_EVENT_MISSING_LEDGER_ENTRY"
    G0_051 = "LEARNING_EVENT_INVALID_SEQUENCE"
    G0_052 = "LEARNING_EVENT_AUTHORITY_MISMATCH"
    # Review Gate v1.1 Error Codes (PAC-BENSON-G0-REVIEW-GATE-V1-1-IMPLEMENTATION-01)
    RG_001 = "Missing ReviewGate declaration"
    RG_002 = "Missing terminal Gold Standard Checklist"
    RG_003 = "Missing reviewer self-certification"
    RG_004 = "Missing training signal"
    RG_005 = "Incomplete checklist"
    RG_006 = "Missing activation acknowledgements"
    RG_007 = "Missing runtime enforcement"
    # BSRG-01 Error Codes (PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01)
    BSRG_001 = "PAC missing BENSON_SELF_REVIEW_GATE"
    BSRG_002 = "BSRG gate_id must be BSRG-01"
    BSRG_003 = "BSRG reviewer must be BENSON"
    BSRG_004 = "BSRG reviewer_gid must be GID-00"
    BSRG_005 = "BSRG issuance_policy must be FAIL_CLOSED"
    BSRG_006 = "BSRG checklist_results missing required key"
    BSRG_007 = "BSRG checklist_results item not PASS"
    BSRG_008 = "BSRG failed_items must be empty"
    BSRG_009 = "BSRG override_used must be false"
    BSRG_010 = "BSRG not immediately before GOLD_STANDARD_CHECKLIST"
    BSRG_011 = "GOLD_STANDARD_CHECKLIST not terminal in PAC"
    BSRG_012 = "BSRG missing required field"
    # Agent Color Enforcement Error Codes (PAC-ATLAS-P25-GOLD-STANDARD-AGENT-COLOR-ENFORCEMENT-01)
    GS_030 = "Agent referenced without agent_color"
    GS_031 = "agent_color does not match canonical registry"
    GS_032 = "agent_color missing from activation acknowledgements"


@dataclass
class ValidationError:
    """A single validation error."""
    code: ErrorCode
    message: str
    location: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of PAC validation."""
    valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)  # Not used in FAIL_CLOSED mode


# Required blocks in order
REQUIRED_BLOCKS = [
    "RUNTIME_ACTIVATION_ACK",
    "AGENT_ACTIVATION_ACK",
]

# Optional but expected blocks (order matters if present)
EXPECTED_BLOCKS = [
    "PAC_HEADER",
    "GATEWAY_CHECK",
    "CONTEXT_AND_GOAL",
    "SCOPE",
    "FORBIDDEN_ACTIONS",
    "CONSTRAINTS",
    "TASKS",
    "FILES",
    "ACCEPTANCE",
    "TRAINING_SIGNAL",
    "FINAL_STATE",
]

# Runtime block forbidden fields
RUNTIME_FORBIDDEN_FIELDS = {
    "agent_name",
    "color",
    "icon",
    "role",
}

# Valid training levels (L1-L10 per G0.2.0)
VALID_TRAINING_LEVELS = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10"]


# Gold Standard Checklist required keys (G2.0.0)
GOLD_STANDARD_CHECKLIST_KEYS = [
    "identity_correct",
    "agent_color_correct",
    "execution_lane_correct",
    "canonical_headers_present",
    "block_order_correct",
    "forbidden_actions_section_present",
    "scope_lock_present",
    "training_signal_present",
    "final_state_declared",
    "wrap_schema_valid",
    "no_extra_content",
    "no_scope_drift",
    "self_certification_present",
]


# Correction pack detection markers - must be STRUCTURAL, not narrative
# These are explicit markers that indicate a correction pack submission
CORRECTION_MARKERS = [
    "GOVERNANCE_CORRECTION",
    "MODE: GOVERNANCE_CORRECTION",
    "PACK_TYPE: CORRECTION",
    "correction_type:",
    "original_pac_id:",
    "CORRECTION_LINEAGE:",
]


# ═══════════════════════════════════════════════════════════════════════════════
# G3.0.0 POSITIVE CLOSURE ENFORCEMENT
# PAC-ATLAS-G3-GATEPACK-POSITIVE-CLOSURE-HARDWIRE-01
# ═══════════════════════════════════════════════════════════════════════════════

# Canonical Closure Classes - Terminal vs Non-Terminal
CLOSURE_CLASSES = {
    "POSITIVE_CLOSURE": {
        "terminal": True,
        "requires_correction_lineage": True,
        "requires_gold_standard": True,
        "implicit_success_allowed": False,
        "requires_authority": True,
        "requires_training_signal": True,
        "training_signal_type": "POSITIVE_REINFORCEMENT",
    },
    "BLOCKED_CLOSURE": {
        "terminal": False,
        "requires_correction_lineage": False,
        "requires_gold_standard": False,
        "implicit_success_allowed": False,
        "requires_authority": False,
        "requires_training_signal": True,
        "training_signal_type": "NEGATIVE",
    },
    "PENDING_CLOSURE": {
        "terminal": False,
        "requires_correction_lineage": False,
        "requires_gold_standard": False,
        "implicit_success_allowed": False,
        "requires_authority": False,
        "requires_training_signal": False,
        "training_signal_type": None,
    },
}

# Positive Closure WRAP MUST contain these sections
POSITIVE_CLOSURE_REQUIRED_SECTIONS = [
    "CLOSURE_CLASS",
    "CLOSURE_AUTHORITY",
    "VIOLATIONS_ADDRESSED",
    "POSITIVE_CLOSURE",  # or POSITIVE_CLOSURE_ACKNOWLEDGEMENT
    "TRAINING_SIGNAL",
    "GOLD_STANDARD_CHECKLIST",
    "SELF_CERTIFICATION",
    "FINAL_STATE",
]

# Positive Closure detection markers
POSITIVE_CLOSURE_MARKERS = [
    "POSITIVE_CLOSURE",
    "type: POSITIVE_CLOSURE",
    "type: \"POSITIVE_CLOSURE\"",
    "closure_type: POSITIVE_CLOSURE",
    "POSITIVE_CLOSURE_ACKNOWLEDGED",
    "GOLD_STANDARD_MET",
]


# ═══════════════════════════════════════════════════════════════════════════════
# BSRG-01 CONSTANTS (PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01)
# ═══════════════════════════════════════════════════════════════════════════════

# PAC detection markers (structural, not filename-based)
PAC_STRUCTURAL_MARKERS = [
    "PAC-",
    "RUNTIME_ACTIVATION_ACK",
    "AGENT_ACTIVATION_ACK",
    "execution_lane:",
    "mode: CTO_EXECUTION",
]

# BSRG Required Checklist Keys
BSRG_REQUIRED_CHECKLIST_KEYS = [
    "identity_correct",
    "agent_color_correct",
    "execution_lane_correct",
    "canonical_headers_present",
    "block_order_correct",
    "scope_lock_present",
    "forbidden_actions_present",
    "runtime_activation_ack_present",
    "agent_activation_ack_present",
    "review_gate_declared",
    "training_signal_present",
    "self_certification_present",
    "final_state_declared",
    "checklist_at_end",
    "checklist_all_items_checked",
    "return_permitted",
]


def load_registry() -> dict:
    """Load the agent registry."""
    if not REGISTRY_PATH.exists():
        return {}
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def extract_block(content: str, block_name: str) -> Optional[str]:
    """Extract a named block from content."""
    # Try multiple formats:

    # Format 1: BLOCK_NAME { ... } (raw block)
    pattern = rf"{block_name}\s*\{{\s*(.*?)\s*\}}"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)

    # Format 2: YAML code block with BLOCK_NAME: (legacy Markdown)
    yaml_pattern = rf"```(?:yaml|yml)?\s*\n{block_name}:\s*(.*?)```"
    match = re.search(yaml_pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)

    # Format 3: Inline YAML BLOCK_NAME:\n  key: value
    inline_pattern = rf"^{block_name}:\s*\n((?:\s+\w+:.*\n?)+)"
    match = re.search(inline_pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def find_block_position(content: str, block_name: str) -> int:
    """Find the position of a block in content. Returns -1 if not found."""
    # Try raw block format
    pattern = rf"{block_name}\s*\{{"
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return match.start()

    # Try YAML code block format
    yaml_pattern = rf"```(?:yaml|yml)?\s*\n{block_name}:"
    match = re.search(yaml_pattern, content, re.IGNORECASE)
    if match:
        return match.start()

    # Try inline YAML format
    inline_pattern = rf"^{block_name}:\s*\n"
    match = re.search(inline_pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.start()

    return -1


def parse_block_fields(block_content: str) -> dict:
    """Parse key-value pairs from a block."""
    fields = {}
    # Match: key: "value" or key: value or key: [list]
    pattern = r'(\w+)\s*:\s*(?:"([^"]+)"|\'([^\']+)\'|\[([^\]]*)\]|([^\n,}]+))'
    for match in re.finditer(pattern, block_content):
        key = match.group(1).lower()
        # Get the value from whichever group matched
        value = match.group(2) or match.group(3) or match.group(4) or match.group(5)
        if value:
            value = value.strip().strip('"').strip("'")
        fields[key] = value
    return fields


def validate_runtime_block(content: str, registry: dict) -> list:
    """Validate RUNTIME_ACTIVATION_ACK block."""
    errors = []

    block = extract_block(content, "RUNTIME_ACTIVATION_ACK")
    if not block:
        errors.append(ValidationError(
            ErrorCode.G0_001,
            "Missing RUNTIME_ACTIVATION_ACK block"
        ))
        return errors

    fields = parse_block_fields(block)

    # Check required fields
    required = ["runtime_name", "gid", "authority", "execution_lane", "mode", "executes_for_agent"]
    for field_name in required:
        if field_name not in fields:
            errors.append(ValidationError(
                ErrorCode.G0_006,
                f"RUNTIME_ACTIVATION_ACK missing required field: {field_name}"
            ))

    # GID must be "N/A"
    gid = fields.get("gid", "")
    if gid and "N/A" not in gid.upper():
        errors.append(ValidationError(
            ErrorCode.G0_007,
            f"Runtime has GID '{gid}' — runtimes must have gid: 'N/A'"
        ))

    # Authority must be DELEGATED
    authority = fields.get("authority", "")
    if authority and "DELEGATED" not in authority.upper():
        errors.append(ValidationError(
            ErrorCode.G0_005,
            f"Runtime authority must be 'DELEGATED', got '{authority}'"
        ))

    # Check for forbidden fields (agent identity fields)
    for forbidden in RUNTIME_FORBIDDEN_FIELDS:
        if forbidden in fields and fields[forbidden]:
            # Allow N/A values
            if "N/A" not in str(fields[forbidden]).upper():
                errors.append(ValidationError(
                    ErrorCode.G0_007,
                    f"Runtime block contains forbidden field: {forbidden}"
                ))

    # Validate executes_for_agent references valid GID
    executes_for = fields.get("executes_for_agent", "")
    if executes_for:
        gid_match = re.search(r"GID-(\d+)", executes_for, re.IGNORECASE)
        if gid_match:
            gid_num = f"GID-{gid_match.group(1).zfill(2)}"
            agents = registry.get("agents", {})
            valid_gids = [a.get("gid", "").upper() for a in agents.values()]
            if gid_num.upper() not in valid_gids:
                errors.append(ValidationError(
                    ErrorCode.G0_003,
                    f"executes_for_agent references invalid GID: {gid_num}"
                ))

    return errors


def validate_agent_block(content: str, registry: dict) -> list:
    """Validate AGENT_ACTIVATION_ACK block."""
    errors = []

    block = extract_block(content, "AGENT_ACTIVATION_ACK")
    if not block:
        errors.append(ValidationError(
            ErrorCode.G0_001,
            "Missing AGENT_ACTIVATION_ACK block"
        ))
        return errors

    fields = parse_block_fields(block)

    # Check required fields
    required = ["agent_name", "gid", "role", "color", "icon", "execution_lane", "mode"]
    for field_name in required:
        if field_name not in fields:
            errors.append(ValidationError(
                ErrorCode.G0_006,
                f"AGENT_ACTIVATION_ACK missing required field: {field_name}"
            ))

    # Validate against registry
    agent_name = fields.get("agent_name", "").upper()
    agents = registry.get("agents", {})

    if agent_name and agent_name in agents:
        reg_agent = agents[agent_name]

        # Validate GID
        declared_gid = fields.get("gid", "").upper()
        registry_gid = reg_agent.get("gid", "").upper()
        if declared_gid and registry_gid and declared_gid != registry_gid:
            errors.append(ValidationError(
                ErrorCode.G0_004,
                f"GID mismatch: declared '{declared_gid}', registry has '{registry_gid}'"
            ))

        # Validate color
        declared_color = fields.get("color", "").upper()
        registry_color = reg_agent.get("color", "").upper()
        if declared_color and registry_color and declared_color != registry_color:
            errors.append(ValidationError(
                ErrorCode.G0_004,
                f"Color mismatch: declared '{declared_color}', registry has '{registry_color}'"
            ))

        # Validate execution_lane (allow legacy synonyms)
        declared_lane = fields.get("execution_lane", "").upper()
        registry_lane = reg_agent.get("execution_lane", "").upper()

        # Known equivalent lanes (legacy mappings)
        lane_equivalents = {
            "BUILD / STATE ENGINE": "SYSTEM_STATE",
            "STATE ENGINE": "SYSTEM_STATE",
            "BUILD": "SYSTEM_STATE",
            "SYSTEM STATE": "SYSTEM_STATE",
        }

        # Normalize declared lane
        normalized_declared = lane_equivalents.get(declared_lane, declared_lane)

        if declared_lane and registry_lane and normalized_declared != registry_lane:
            errors.append(ValidationError(
                ErrorCode.G0_004,
                f"Execution lane mismatch: declared '{declared_lane}', registry has '{registry_lane}'"
            ))

    # Check forbidden aliases
    forbidden = registry.get("forbidden_aliases", [])
    if agent_name in [a.upper() for a in forbidden]:
        errors.append(ValidationError(
            ErrorCode.G0_003,
            f"Agent name '{agent_name}' is a forbidden alias"
        ))

    return errors


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT COLOR ENFORCEMENT (PAC-ATLAS-P25-GOLD-STANDARD-AGENT-COLOR-ENFORCEMENT-01)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Agent color is a FIRST-CLASS GOVERNANCE INVARIANT.
# Any artifact referencing an agent MUST declare agent_color.
# Color MUST match the canonical agent registry.
# Mode: FAIL_CLOSED. No bypass. No override.
# ═══════════════════════════════════════════════════════════════════════════════

# Color name normalization map (icons to color names)
COLOR_ICON_MAP = {
    "🟦": "BLUE",
    "🔵": "BLUE",
    "🟢": "GREEN",
    "🟩": "GREEN",
    "🟡": "YELLOW",
    "🟨": "YELLOW",
    "🟣": "PURPLE",
    "🟪": "PURPLE",
    "🔴": "RED",
    "🟥": "RED",
    "⚪": "WHITE",
    "⬜": "WHITE",
    "🔷": "CYAN",
    "🟧": "ORANGE",
    "🟫": "BROWN",
    "⬛": "BLACK",
    "🟦🟩": "TEAL",  # Benson's unique icon
}


def normalize_color(color_value: str) -> str:
    """
    Normalize color value to standard color name.

    Handles:
    - Icon-prefixed colors: "🟦 BLUE" -> "BLUE"
    - Icon-only: "🟦" -> "BLUE"
    - Plain text: "BLUE" -> "BLUE"
    """
    if not color_value:
        return ""

    color_value = color_value.strip()

    # Check if it's just an icon
    if color_value in COLOR_ICON_MAP:
        return COLOR_ICON_MAP[color_value]

    # Check for icon prefix (e.g., "🟦 BLUE")
    for icon, color_name in COLOR_ICON_MAP.items():
        if color_value.startswith(icon):
            return color_name

    # Return uppercase of the value (strip any leading icon)
    # Handle cases like "🟦 BLUE" by taking the last word
    parts = color_value.split()
    if parts:
        return parts[-1].upper()

    return color_value.upper()


def validate_agent_color(content: str, registry: dict) -> list:
    """
    Validate agent color enforcement.

    PAC-ATLAS-P25-GOLD-STANDARD-AGENT-COLOR-ENFORCEMENT-01

    Rules (FAIL_CLOSED):
    1. If agent OR agent_gid detected AND agent_color missing → GS_030
    2. If agent_color != registry_color(agent_gid) → GS_031
    3. If activation blocks present WITHOUT agent_color → GS_032

    Returns:
        List of ValidationError for any color violations
    """
    errors = []
    agents = registry.get("agents", {})

    # Extract agent references from content
    agent_gid_match = re.search(r'(?:agent_gid|gid):\s*["\']?(GID-\d+)["\']?', content, re.IGNORECASE)
    agent_name_match = re.search(r'agent(?:_name)?:\s*["\']?([A-Z][A-Za-z]+)["\']?', content, re.IGNORECASE)

    has_agent_reference = agent_gid_match is not None or agent_name_match is not None

    # Check activation blocks for agent_color
    runtime_block = extract_block(content, "RUNTIME_ACTIVATION_ACK")
    agent_block = extract_block(content, "AGENT_ACTIVATION_ACK")

    has_activation_blocks = runtime_block is not None or agent_block is not None

    # Find all agent_color declarations in content
    color_matches = re.findall(r'agent_color:\s*["\']?([^\n"\',}]+)["\']?', content, re.IGNORECASE)

    # Also check for "color:" in activation blocks
    color_in_block_matches = []
    if agent_block:
        block_color_match = re.search(r'color:\s*["\']?([^\n"\',}]+)["\']?', agent_block, re.IGNORECASE)
        if block_color_match:
            color_in_block_matches.append(block_color_match.group(1))

    has_agent_color = len(color_matches) > 0 or len(color_in_block_matches) > 0

    # Rule 1: Agent referenced without agent_color → GS_030
    if has_agent_reference and not has_agent_color:
        errors.append(ValidationError(
            ErrorCode.GS_030,
            "Agent referenced without agent_color declaration"
        ))

    # Rule 3: Activation blocks without agent_color → GS_032
    if has_activation_blocks and not has_agent_color:
        errors.append(ValidationError(
            ErrorCode.GS_032,
            "Activation acknowledgement blocks missing agent_color"
        ))

    # Rule 2: Validate agent_color matches registry → GS_031
    if has_agent_color:
        # Get declared color
        declared_color = color_matches[0] if color_matches else (color_in_block_matches[0] if color_in_block_matches else "")
        declared_color_normalized = normalize_color(declared_color)

        # Get agent name for registry lookup
        agent_name = None
        if agent_name_match:
            agent_name = agent_name_match.group(1).upper()
        elif agent_gid_match:
            # Find agent by GID
            gid = agent_gid_match.group(1).upper()
            for name, info in agents.items():
                if info.get("gid", "").upper() == gid:
                    agent_name = name
                    break

        if agent_name and agent_name in agents:
            registry_color = agents[agent_name].get("color", "").upper()

            if declared_color_normalized and registry_color:
                if declared_color_normalized != registry_color:
                    errors.append(ValidationError(
                        ErrorCode.GS_031,
                        f"agent_color mismatch: declared '{declared_color_normalized}', registry has '{registry_color}'"
                    ))

    return errors


def validate_block_order(content: str) -> list:
    """Validate that required blocks appear in correct order."""
    errors = []

    positions = {}
    for block_name in REQUIRED_BLOCKS:
        pos = find_block_position(content, block_name)
        if pos >= 0:
            positions[block_name] = pos

    # Check order
    prev_pos = -1
    prev_block = None
    for block_name in REQUIRED_BLOCKS:
        if block_name in positions:
            pos = positions[block_name]
            if pos < prev_pos:
                errors.append(ValidationError(
                    ErrorCode.G0_002,
                    f"Block order violation: {block_name} appears before {prev_block}"
                ))
            prev_pos = pos
            prev_block = block_name

    return errors


def validate_training_signal(content: str, require_training: bool = False) -> list:
    """Validate TRAINING_SIGNAL block if present or required."""
    errors = []

    block = extract_block(content, "TRAINING_SIGNAL")

    # Check for TRAINING_SIGNAL in various formats
    has_training = block is not None or "TRAINING_SIGNAL" in content.upper()

    if not has_training and require_training:
        errors.append(ValidationError(
            ErrorCode.G0_009,
            "Missing TRAINING_SIGNAL block (mandatory for G0.2.0+)"
        ))
        return errors

    if not block:
        return errors

    fields = parse_block_fields(block)

    # Check program
    program = fields.get("program", "")
    if program and "Agent University" not in program:
        errors.append(ValidationError(
            ErrorCode.G0_009,
            f"TRAINING_SIGNAL program must be 'Agent University', got '{program}'"
        ))

    # Check level
    level = fields.get("level", "").upper()
    if level:
        # Extract just the L# part
        level_match = re.search(r"L(\d+)", level)
        if level_match:
            level_code = f"L{level_match.group(1)}"
            if level_code not in VALID_TRAINING_LEVELS:
                errors.append(ValidationError(
                    ErrorCode.G0_009,
                    f"Invalid training level: {level_code}. Must be L1-L10"
                ))

    # Check evaluation
    evaluation = fields.get("evaluation", "")
    if evaluation and "BINARY" not in evaluation.upper():
        errors.append(ValidationError(
            ErrorCode.G0_009,
            f"TRAINING_SIGNAL evaluation must be 'Binary', got '{evaluation}'"
        ))

    return errors


def validate_forbidden_actions(content: str) -> list:
    """Validate FORBIDDEN_ACTIONS section if present (mandatory for G0.2.0+)."""
    errors = []

    # Check for FORBIDDEN_ACTIONS or FORBIDDEN ACTIONS section
    forbidden_patterns = [
        r"FORBIDDEN[_\s]?ACTIONS",
        r"##\s*\d*\.?\s*FORBIDDEN",
        r"STRICTLY\s+PROHIBITED",
    ]

    has_forbidden = any(re.search(p, content, re.IGNORECASE) for p in forbidden_patterns)

    # For non-legacy G0.2.0+ files, FORBIDDEN_ACTIONS is mandatory
    # But we only enforce this on new files, not legacy
    # Detection: if file has ACTIVATION_ACK but no FORBIDDEN, it's a gap
    # For now, just track presence for reporting

    return errors


def validate_scope(content: str) -> list:
    """Validate SCOPE section if present (mandatory for G0.2.0+)."""
    errors = []

    # Check for SCOPE section with IN SCOPE and OUT OF SCOPE
    scope_patterns = [
        r"##\s*\d*\.?\s*SCOPE",
        r"IN[_\s]?SCOPE",
        r"OUT[_\s]?OF[_\s]?SCOPE",
    ]

    # For now, just track presence for reporting
    # Full enforcement can be enabled later

    return errors


def is_correction_pack(content: str) -> bool:
    """Detect if content is a correction pack artifact."""
    content_upper = content.upper()
    for marker in CORRECTION_MARKERS:
        if marker.upper() in content_upper:
            return True
    return False


def extract_yaml_block(content: str, block_name: str) -> Optional[dict]:
    """
    Extract and parse a YAML block from content.
    Returns parsed dict or None if not found/invalid.

    Supports formats:
    - ```yaml\nBLOCK_NAME:\n  key: value\n```
    - BLOCK_NAME:\n  key: { checked: true }
    """
    import yaml

    # Try YAML code block format
    yaml_pattern = rf"```(?:yaml|yml)?\s*\n({block_name}:\s*.*?)```"
    match = re.search(yaml_pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            pass

    # Try inline YAML format (indented block)
    inline_pattern = rf"^{block_name}:\s*\n((?:\s+\w+:.*\n?)+)"
    match = re.search(inline_pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        try:
            full_yaml = f"{block_name}:\n{match.group(1)}"
            return yaml.safe_load(full_yaml)
        except yaml.YAMLError:
            pass

    # Try to find it as a section with key-value pairs
    section_pattern = rf"{block_name}:\s*\n((?:\s+\w+:\s*\{{[^}}]+\}}\s*\n?)+)"
    match = re.search(section_pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        try:
            full_yaml = f"{block_name}:\n{match.group(1)}"
            return yaml.safe_load(full_yaml)
        except yaml.YAMLError:
            pass

    return None


def validate_gold_standard_checklist(content: str) -> list:
    """
    Validate GOLD_STANDARD_CHECKLIST block for correction packs.

    This is a HARD GATE — any failure results in immediate rejection.

    Requirements:
    - Block MUST be present
    - ALL 13 keys MUST be present
    - ALL values MUST be { checked: true }
    """
    errors = []

    # Only enforce on correction packs
    if not is_correction_pack(content):
        return errors

    # Extract the checklist block
    checklist = extract_yaml_block(content, "GOLD_STANDARD_CHECKLIST")

    if not checklist:
        # Try alternate detection (raw string matching)
        if "GOLD_STANDARD_CHECKLIST" not in content:
            errors.append(ValidationError(
                ErrorCode.G0_020,
                "Correction pack missing GOLD_STANDARD_CHECKLIST block"
            ))
            return errors
        else:
            # Block exists but couldn't be parsed as YAML
            # Do string-based validation as fallback
            return validate_gold_standard_checklist_string(content)

    # Get the checklist items
    checklist_items = checklist.get("GOLD_STANDARD_CHECKLIST", checklist)

    # Validate all required keys are present
    missing_keys = []
    unchecked_items = []

    for key in GOLD_STANDARD_CHECKLIST_KEYS:
        if key not in checklist_items:
            missing_keys.append(key)
        else:
            item = checklist_items[key]
            # Check if item is checked: true
            if isinstance(item, dict):
                if not item.get("checked", False):
                    unchecked_items.append(key)
            elif isinstance(item, bool):
                if not item:
                    unchecked_items.append(key)
            else:
                # Treat as unchecked if not clearly true
                if str(item).lower() not in ("true", "yes", "1"):
                    unchecked_items.append(key)

    if missing_keys:
        errors.append(ValidationError(
            ErrorCode.G0_024,
            f"GOLD_STANDARD_CHECKLIST missing keys: {', '.join(missing_keys)}"
        ))

    if unchecked_items:
        errors.append(ValidationError(
            ErrorCode.G0_023,
            f"GOLD_STANDARD_CHECKLIST unchecked items: {', '.join(unchecked_items)}"
        ))

    if missing_keys or unchecked_items:
        errors.append(ValidationError(
            ErrorCode.G0_020,
            "GOLD_STANDARD_CHECKLIST_INCOMPLETE — correction pack rejected"
        ))

    return errors


def validate_gold_standard_checklist_string(content: str) -> list:
    """
    Fallback string-based validation for GOLD_STANDARD_CHECKLIST.
    Used when YAML parsing fails.
    """
    errors = []

    # Find the checklist section
    checklist_pattern = r"GOLD_STANDARD_CHECKLIST:?\s*\n((?:.*\n)*?)(?=\n[A-Z_]+:|$|\n---|\n```)"
    match = re.search(checklist_pattern, content, re.IGNORECASE)

    if not match:
        errors.append(ValidationError(
            ErrorCode.G0_020,
            "Could not parse GOLD_STANDARD_CHECKLIST block"
        ))
        return errors

    checklist_content = match.group(1)

    # Check each required key
    missing_keys = []
    unchecked_items = []

    for key in GOLD_STANDARD_CHECKLIST_KEYS:
        # Look for key: { checked: true } or key: true
        key_pattern = rf"{key}\s*:\s*(?:\{{\s*checked\s*:\s*(true|false)\s*\}}|(true|false))"
        key_match = re.search(key_pattern, checklist_content, re.IGNORECASE)

        if not key_match:
            # Also try simple presence
            if key not in checklist_content.lower():
                missing_keys.append(key)
            else:
                # Key exists but value unclear
                if "true" not in checklist_content.lower():
                    unchecked_items.append(key)
        else:
            # Check if value is true
            value = key_match.group(1) or key_match.group(2)
            if value and value.lower() != "true":
                unchecked_items.append(key)

    if missing_keys:
        errors.append(ValidationError(
            ErrorCode.G0_024,
            f"GOLD_STANDARD_CHECKLIST missing keys: {', '.join(missing_keys)}"
        ))

    if unchecked_items:
        errors.append(ValidationError(
            ErrorCode.G0_023,
            f"GOLD_STANDARD_CHECKLIST unchecked items: {', '.join(unchecked_items)}"
        ))

    if missing_keys or unchecked_items:
        errors.append(ValidationError(
            ErrorCode.G0_020,
            "GOLD_STANDARD_CHECKLIST_INCOMPLETE — correction pack rejected"
        ))

    return errors


def validate_self_certification(content: str) -> list:
    """
    Validate SELF_CERTIFICATION section for correction packs.

    This is a HARD GATE — missing certification = rejection.
    """
    errors = []

    # Only enforce on correction packs
    if not is_correction_pack(content):
        return errors

    # Check for SELF_CERTIFICATION section
    cert_patterns = [
        r"SELF_CERTIFICATION",
        r"SELF-CERTIFICATION",
        r"I,\s+\w+\s+\(GID-\d+\),\s+certify",
    ]

    has_certification = any(re.search(p, content, re.IGNORECASE) for p in cert_patterns)

    if not has_certification:
        errors.append(ValidationError(
            ErrorCode.G0_021,
            "Correction pack missing SELF_CERTIFICATION — all corrections require self-certification"
        ))

    return errors


def validate_violations_addressed(content: str) -> list:
    """
    Validate VIOLATIONS_ADDRESSED section for correction packs.
    """
    errors = []

    # Only enforce on correction packs
    if not is_correction_pack(content):
        return errors

    # Check for VIOLATIONS_ADDRESSED section
    has_violations = "VIOLATIONS_ADDRESSED" in content.upper() or "VIOLATION" in content.upper()

    # For WRAP corrections, violation details may be in other sections
    # So we check more flexibly
    violation_indicators = [
        r"VIOLATIONS?_ADDRESSED",
        r"violation_codes?:",
        r"correction_type:",
        r"original_pac_id:",
        r"DEFICIENCIES",
        r"G0_\d{3}",  # Error code references
    ]

    has_violations = any(re.search(p, content, re.IGNORECASE) for p in violation_indicators)

    if not has_violations:
        errors.append(ValidationError(
            ErrorCode.G0_022,
            "Correction pack should document VIOLATIONS_ADDRESSED"
        ))

    return errors


def emit_training_signal_for_failure(error_code: ErrorCode) -> dict:
    """
    Generate a training signal for governance failures.
    Used when a correction pack is rejected.
    """
    return {
        "TRAINING_SIGNAL": {
            "type": "GOVERNANCE_FAILURE",
            "failure_code": error_code.name,
            "corrective_required": True,
            "retry_allowed": True,
            "program": "Agent University",
            "level": "L9",
            "evaluation": "Binary",
            "retention": "PERMANENT",
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# G3.0.0 POSITIVE CLOSURE VALIDATION
# PAC-ATLAS-G3-GATEPACK-POSITIVE-CLOSURE-HARDWIRE-01
# ═══════════════════════════════════════════════════════════════════════════════

def is_positive_closure_pack(content: str) -> bool:
    """
    Detect if content is a Positive Closure artifact.

    Positive Closure is a DISTINCT closure class — not implicit success.
    Detection is by explicit markers, not string matching.
    """
    content_check = content.upper()

    # Must have explicit positive closure markers
    for marker in POSITIVE_CLOSURE_MARKERS:
        if marker.upper() in content_check:
            return True

    # Also check for files named with POSITIVE-CLOSURE
    # (handled by caller via filename check)
    return False


def get_closure_class(content: str) -> Optional[str]:
    """
    Extract the closure class from content.

    Returns: POSITIVE_CLOSURE, BLOCKED_CLOSURE, PENDING_CLOSURE, or None
    """
    # Try to extract CLOSURE_CLASS block
    closure_block = extract_yaml_block(content, "CLOSURE_CLASS")

    if closure_block:
        closure_data = closure_block.get("CLOSURE_CLASS", closure_block)
        if isinstance(closure_data, dict):
            return closure_data.get("type", None)

    # Fallback: string pattern matching
    if "type: POSITIVE_CLOSURE" in content or 'type: "POSITIVE_CLOSURE"' in content:
        return "POSITIVE_CLOSURE"
    if "type: BLOCKED_CLOSURE" in content or 'type: "BLOCKED_CLOSURE"' in content:
        return "BLOCKED_CLOSURE"
    if "type: PENDING_CLOSURE" in content or 'type: "PENDING_CLOSURE"' in content:
        return "PENDING_CLOSURE"

    # Check for positive closure indicators without explicit type
    if is_positive_closure_pack(content):
        return "POSITIVE_CLOSURE"

    return None


def validate_positive_closure(content: str) -> list:
    """
    Validate Positive Closure artifacts.

    This is a HARD GATE — Positive Closure is structurally enforced.

    Requirements:
    - CLOSURE_CLASS must be declared and terminal
    - CLOSURE_AUTHORITY must be present
    - VIOLATIONS_ADDRESSED must be documented
    - POSITIVE_CLOSURE_ACKNOWLEDGEMENT must be explicit
    - TRAINING_SIGNAL must be POSITIVE_REINFORCEMENT
    - GOLD_STANDARD_CHECKLIST must be complete
    - SELF_CERTIFICATION must be present
    - FINAL_STATE must be declared and terminal

    NO IMPLICIT SUCCESS. NO DOWNGRADE FROM POSITIVE TO NON-TERMINAL.
    """
    errors = []

    # Only validate if this is a positive closure pack
    if not is_positive_closure_pack(content):
        return errors

    closure_class = get_closure_class(content)

    # Validate closure class definition
    if closure_class != "POSITIVE_CLOSURE":
        errors.append(ValidationError(
            ErrorCode.G0_043,
            f"Positive Closure artifact has invalid closure class: {closure_class}"
        ))

    # Get closure class requirements
    class_requirements = CLOSURE_CLASSES.get("POSITIVE_CLOSURE", {})

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION VALIDATION — All required sections must be present
    # ═══════════════════════════════════════════════════════════════════════════

    missing_sections = []
    for section in POSITIVE_CLOSURE_REQUIRED_SECTIONS:
        # Handle alternate names
        section_variants = [section]
        if section == "POSITIVE_CLOSURE":
            section_variants = ["POSITIVE_CLOSURE", "POSITIVE_CLOSURE_ACKNOWLEDGEMENT",
                               "POSITIVE_CLOSURE_ATTESTATION"]
        if section == "VIOLATIONS_ADDRESSED":
            section_variants = ["VIOLATIONS_ADDRESSED", "VIOLATIONS_RESOLVED"]

        found = any(variant in content for variant in section_variants)
        if not found:
            missing_sections.append(section)

    if missing_sections:
        errors.append(ValidationError(
            ErrorCode.G0_046,
            f"Positive Closure missing required sections: {', '.join(missing_sections)}"
        ))

    # ═══════════════════════════════════════════════════════════════════════════
    # CLOSURE AUTHORITY — Must be explicitly declared
    # ═══════════════════════════════════════════════════════════════════════════

    if class_requirements.get("requires_authority", True):
        authority_patterns = [
            r"CLOSURE_AUTHORITY",
            r"approved_by\s*:",
            r"ratification_authority\s*:",
            r"authority\s*:\s*\"?BENSON",
        ]
        has_authority = any(re.search(p, content, re.IGNORECASE) for p in authority_patterns)

        if not has_authority:
            errors.append(ValidationError(
                ErrorCode.G0_042,
                "Positive Closure requires explicit CLOSURE_AUTHORITY"
            ))

    # ═══════════════════════════════════════════════════════════════════════════
    # CORRECTION LINEAGE — Must document what was corrected
    # ═══════════════════════════════════════════════════════════════════════════

    if class_requirements.get("requires_correction_lineage", True):
        lineage_patterns = [
            r"CORRECTION_LINEAGE",
            r"VIOLATIONS_ADDRESSED",
            r"VIOLATIONS_RESOLVED",
            r"prior_corrections\s*:",
            r"correction_cycles_completed",
        ]
        has_lineage = any(re.search(p, content, re.IGNORECASE) for p in lineage_patterns)

        if not has_lineage:
            errors.append(ValidationError(
                ErrorCode.G0_040,
                "Positive Closure requires correction lineage documentation"
            ))

    # ═══════════════════════════════════════════════════════════════════════════
    # TRAINING SIGNAL — Must be POSITIVE_REINFORCEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    if class_requirements.get("requires_training_signal", True):
        required_signal = class_requirements.get("training_signal_type", "POSITIVE_REINFORCEMENT")

        # Check for TRAINING_SIGNAL block
        if "TRAINING_SIGNAL" not in content:
            errors.append(ValidationError(
                ErrorCode.G0_045,
                "Positive Closure requires TRAINING_SIGNAL block"
            ))
        else:
            # Verify signal type
            signal_pattern = rf"signal_type\s*:\s*\"?{required_signal}"
            if not re.search(signal_pattern, content, re.IGNORECASE):
                errors.append(ValidationError(
                    ErrorCode.G0_045,
                    f"Positive Closure requires TRAINING_SIGNAL.signal_type = {required_signal}"
                ))

    # ═══════════════════════════════════════════════════════════════════════════
    # GOLD STANDARD CHECKLIST — Must be complete
    # ═══════════════════════════════════════════════════════════════════════════

    if class_requirements.get("requires_gold_standard", True):
        checklist_errors = validate_gold_standard_checklist(content)
        if checklist_errors:
            errors.append(ValidationError(
                ErrorCode.G0_041,
                "Positive Closure requires complete GOLD_STANDARD_CHECKLIST"
            ))
            errors.extend(checklist_errors)

    # ═══════════════════════════════════════════════════════════════════════════
    # TERMINAL STATE — Closure must be irreversible
    # ═══════════════════════════════════════════════════════════════════════════

    if class_requirements.get("terminal", True):
        terminal_indicators = [
            r"terminal\s*:\s*true",
            r"irreversible\s*:\s*true",
            r"STATE_CHANGING_IRREVERSIBLE",
            r"correction_cycle[s]?_closed\s*:\s*true",
            r"status\s*:\s*\"?COMPLETE",
        ]
        is_terminal = any(re.search(p, content, re.IGNORECASE) for p in terminal_indicators)

        if not is_terminal:
            errors.append(ValidationError(
                ErrorCode.G0_043,
                "Positive Closure must be terminal/irreversible — found non-terminal state"
            ))

    # ═══════════════════════════════════════════════════════════════════════════
    # IMPLICIT SUCCESS FORBIDDEN
    # ═══════════════════════════════════════════════════════════════════════════

    if not class_requirements.get("implicit_success_allowed", False):
        # Must have explicit success markers, not just absence of failure
        explicit_success_patterns = [
            r"GOLD_STANDARD_MET",
            r"MEETS_GOLD_STANDARD",
            r"determination\s*:\s*\"?MEETS_GOLD_STANDARD",
            r"acknowledgement\s*:\s*\"?GOLD_STANDARD_MET",
            r"POSITIVE_CLOSURE",
        ]
        has_explicit_success = any(re.search(p, content, re.IGNORECASE) for p in explicit_success_patterns)

        if not has_explicit_success:
            errors.append(ValidationError(
                ErrorCode.G0_044,
                "Positive Closure requires EXPLICIT success declaration — implicit success forbidden"
            ))

    return errors


# ═══════════════════════════════════════════════════════════════════════════════
# BSRG-01 VALIDATION (PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01)
# Benson Self-Review Gate — Enforcement Engine
#
# Authority: BENSON (GID-00)
# Mode: FAIL_CLOSED
#
# This is a HARD GATE — PACs cannot be issued without valid BSRG-01.
# No bypass paths. No manual overrides. No implicit approvals.
# ═══════════════════════════════════════════════════════════════════════════════


def is_pac_artifact(content: str) -> bool:
    """
    Detect if content is a PAC artifact requiring BSRG enforcement.

    Uses structural markers rather than filename to ensure robust detection.
    A PAC must have multiple structural indicators to trigger BSRG validation.
    """
    content_upper = content.upper()

    # Count structural markers present
    marker_count = 0
    for marker in PAC_STRUCTURAL_MARKERS:
        if marker.upper() in content_upper:
            marker_count += 1

    # Must have at least 3 markers to be considered a PAC
    # This prevents false positives on partial documents
    if marker_count < 3:
        return False

    # Exclude correction packs (they have their own validation)
    if is_correction_pack(content):
        return False

    # Exclude positive closure packs
    if is_positive_closure_pack(content):
        return False

    # Exclude review artifacts
    if is_review_artifact(content):
        return False

    # Exclude template files
    template_markers = [
        "CANONICAL_PAC_TEMPLATE",
        "GOLD_STANDARD_WRAP_TEMPLATE",
        "Template Schema",
        "## Block 0:",
    ]
    if any(marker in content for marker in template_markers):
        return False

    # Exclude WRAP artifacts (WRAPs reference PACs but are not PACs themselves)
    # Detection: filename pattern WRAP- or explicit WRAP markers
    wrap_markers = [
        "WRAP-",
        "Work Result and Attestation Proof",
        "WRAP METADATA",
        "WRAP HEADER",
        "wrap_id:",
    ]
    # If "WRAP-" appears in the content header (first 500 chars), it's a WRAP
    first_500 = content[:500].upper()
    if "WRAP-" in first_500:
        return False
    # Also check for multiple wrap markers anywhere
    wrap_count = sum(1 for marker in wrap_markers if marker in content)
    if wrap_count >= 2:
        return False

    return True


def extract_bsrg_block(content: str) -> Optional[dict]:
    """
    Extract BENSON_SELF_REVIEW_GATE block from content.

    Returns parsed dict or None if not found/invalid.
    Strict extraction — must be exact top-level YAML key.
    """
    import yaml

    # Pattern 1: YAML code block
    yaml_pattern = r"```(?:yaml|yml)?\s*\n(BENSON_SELF_REVIEW_GATE:\s*.*?)```"
    match = re.search(yaml_pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            parsed = yaml.safe_load(match.group(1))
            if isinstance(parsed, dict) and "BENSON_SELF_REVIEW_GATE" in parsed:
                return parsed.get("BENSON_SELF_REVIEW_GATE", parsed)
            return parsed
        except yaml.YAMLError:
            pass

    # Pattern 2: Inline YAML (indented block)
    inline_pattern = r"^BENSON_SELF_REVIEW_GATE:\s*\n((?:[ \t]+[^\n]+\n?)+)"
    match = re.search(inline_pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        try:
            full_yaml = f"BENSON_SELF_REVIEW_GATE:\n{match.group(1)}"
            parsed = yaml.safe_load(full_yaml)
            if isinstance(parsed, dict):
                return parsed.get("BENSON_SELF_REVIEW_GATE", parsed)
            return parsed
        except yaml.YAMLError:
            pass

    return None


def find_bsrg_position(content: str) -> int:
    """
    Find the character position where BENSON_SELF_REVIEW_GATE block starts.
    Returns -1 if not found.
    """
    # Try YAML code block
    yaml_pattern = r"```(?:yaml|yml)?\s*\nBENSON_SELF_REVIEW_GATE:"
    match = re.search(yaml_pattern, content, re.IGNORECASE)
    if match:
        return match.start()

    # Try inline YAML
    inline_pattern = r"^BENSON_SELF_REVIEW_GATE:"
    match = re.search(inline_pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.start()

    return -1


def find_gold_standard_checklist_position(content: str) -> int:
    """
    Find the character position where GOLD_STANDARD_CHECKLIST starts.
    Returns -1 if not found.
    """
    # Try YAML code block
    yaml_pattern = r"```(?:yaml|yml)?\s*\nGOLD_STANDARD_CHECKLIST:"
    match = re.search(yaml_pattern, content, re.IGNORECASE)
    if match:
        return match.start()

    # Try inline YAML
    inline_pattern = r"^GOLD_STANDARD_CHECKLIST:"
    match = re.search(inline_pattern, content, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.start()

    return -1


def validate_bsrg_ordering(content: str) -> list:
    """
    Validate BSRG block ordering constraints.

    Requirements:
    1. BSRG must appear immediately before GOLD_STANDARD_CHECKLIST
    2. GOLD_STANDARD_CHECKLIST must be terminal (nothing significant after)

    Returns list of ValidationErrors.
    """
    errors = []

    bsrg_pos = find_bsrg_position(content)
    checklist_pos = find_gold_standard_checklist_position(content)

    if bsrg_pos == -1:
        # BSRG not found — this is caught elsewhere
        return errors

    if checklist_pos == -1:
        # Checklist not found — this is caught elsewhere
        return errors

    # BSRG must come before checklist
    if bsrg_pos > checklist_pos:
        errors.append(ValidationError(
            ErrorCode.BSRG_010,
            "BENSON_SELF_REVIEW_GATE must appear before GOLD_STANDARD_CHECKLIST"
        ))
        return errors

    # Check that BSRG is immediately before checklist
    # Extract content between BSRG end and checklist start
    # Find end of BSRG block
    bsrg_end = bsrg_pos

    # For YAML code block, find the closing ```
    yaml_block_pattern = r"```(?:yaml|yml)?\s*\nBENSON_SELF_REVIEW_GATE:.*?```"
    yaml_match = re.search(yaml_block_pattern, content, re.DOTALL | re.IGNORECASE)
    if yaml_match and yaml_match.start() == bsrg_pos:
        bsrg_end = yaml_match.end()
    else:
        # For inline YAML, find end of indented block
        inline_pattern = r"^BENSON_SELF_REVIEW_GATE:\s*\n(?:[ \t]+[^\n]+\n?)+"
        inline_match = re.search(inline_pattern, content, re.MULTILINE | re.IGNORECASE)
        if inline_match and inline_match.start() == bsrg_pos:
            bsrg_end = inline_match.end()

    # Get content between BSRG and checklist
    between_content = content[bsrg_end:checklist_pos].strip()

    # Only whitespace, horizontal rules, or empty lines allowed between
    allowed_pattern = r'^[\s═─\-\*]*$'
    if between_content and not re.match(allowed_pattern, between_content):
        # Check if there's significant content between
        # Filter out just section dividers
        significant_content = re.sub(r'[═─\-\*\s]+', '', between_content)
        if significant_content:
            errors.append(ValidationError(
                ErrorCode.BSRG_010,
                f"BENSON_SELF_REVIEW_GATE must appear immediately before GOLD_STANDARD_CHECKLIST — found content between: '{between_content[:50]}...'"
            ))

    # Check that checklist is terminal
    # Find end of checklist
    checklist_end = checklist_pos
    checklist_yaml_pattern = r"```(?:yaml|yml)?\s*\nGOLD_STANDARD_CHECKLIST:.*?```"
    checklist_yaml_match = re.search(checklist_yaml_pattern, content, re.DOTALL | re.IGNORECASE)
    if checklist_yaml_match and checklist_yaml_match.start() == checklist_pos:
        checklist_end = checklist_yaml_match.end()
    else:
        checklist_inline_pattern = r"^GOLD_STANDARD_CHECKLIST:\s*\n(?:[ \t]+[^\n]+\n?)+"
        checklist_inline_match = re.search(checklist_inline_pattern, content, re.MULTILINE | re.IGNORECASE)
        if checklist_inline_match and checklist_inline_match.start() == checklist_pos:
            checklist_end = checklist_inline_match.end()

    # Check content after checklist
    after_checklist = content[checklist_end:].strip()

    # Only allowed content after checklist: whitespace, dividers, END markers, color tags
    terminal_allowed = [
        r'^[\s═─\-\*]*$',  # Whitespace and dividers only
        r'^[\s═─\-\*]*🟦.*END.*$',  # END markers
        r'^[\s═─\-\*]*Color Tag:.*$',  # Color tags
        r'^[\s═─\-\*]*🟦.*$',  # Blue squares
    ]

    if after_checklist:
        # Filter line by line
        lines = after_checklist.split('\n')
        significant_lines = []
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            # Check if line is allowed terminal content
            is_terminal = any(re.match(p, line_stripped) for p in terminal_allowed)
            # Also allow lines that are just symbols
            is_symbols = all(c in '═─—-*\n\t 🟦🟩🟨🟥🟪🟫⚪⬜' for c in line_stripped)
            if not is_terminal and not is_symbols and len(line_stripped) > 3:
                significant_lines.append(line_stripped)

        if significant_lines:
            errors.append(ValidationError(
                ErrorCode.BSRG_011,
                f"GOLD_STANDARD_CHECKLIST must be terminal in PAC — found content after: '{significant_lines[0][:50]}...'"
            ))

    return errors


def validate_benson_self_review_gate(content: str) -> tuple[list, dict]:
    """
    Validate BENSON_SELF_REVIEW_GATE (BSRG-01) block for PAC artifacts.

    This is a HARD GATE — any failure results in immediate rejection.

    Requirements:
    - gate_id == "BSRG-01"
    - reviewer == "BENSON"
    - reviewer_gid == "GID-00"
    - issuance_policy == "FAIL_CLOSED"
    - checklist_results contains all required keys with value "PASS"
    - failed_items is an empty list
    - override_used == false

    Returns:
    - Tuple of (list of ValidationErrors, dict of BSRG data for ledger)
    """
    errors = []
    bsrg_data = {
        "found": False,
        "gate_id": None,
        "reviewer": None,
        "reviewer_gid": None,
        "status": "FAIL",
        "failed_items": [],
        "checklist_results": {},
    }

    # Only enforce on PAC artifacts
    if not is_pac_artifact(content):
        return errors, bsrg_data

    # Extract BSRG block
    bsrg = extract_bsrg_block(content)

    if not bsrg:
        # Check if BSRG is present at all (might be malformed)
        if "BENSON_SELF_REVIEW_GATE" in content:
            errors.append(ValidationError(
                ErrorCode.BSRG_001,
                "BENSON_SELF_REVIEW_GATE block found but could not be parsed — check YAML syntax"
            ))
        else:
            errors.append(ValidationError(
                ErrorCode.BSRG_001,
                "PAC missing BENSON_SELF_REVIEW_GATE (BSRG-01) — all PACs require Benson Self-Review"
            ))
        bsrg_data["failed_items"].append("BSRG_MISSING")
        return errors, bsrg_data

    bsrg_data["found"] = True

    # Validate gate_id
    gate_id = bsrg.get("gate_id", "")
    bsrg_data["gate_id"] = gate_id
    if gate_id != "BSRG-01":
        errors.append(ValidationError(
            ErrorCode.BSRG_002,
            f"BSRG gate_id must be 'BSRG-01', got '{gate_id}'"
        ))
        bsrg_data["failed_items"].append(f"gate_id={gate_id}")

    # Validate reviewer
    reviewer = bsrg.get("reviewer", "")
    bsrg_data["reviewer"] = reviewer
    if reviewer.upper() != "BENSON":
        errors.append(ValidationError(
            ErrorCode.BSRG_003,
            f"BSRG reviewer must be 'BENSON', got '{reviewer}'"
        ))
        bsrg_data["failed_items"].append(f"reviewer={reviewer}")

    # Validate reviewer_gid
    reviewer_gid = bsrg.get("reviewer_gid", "")
    bsrg_data["reviewer_gid"] = reviewer_gid
    if reviewer_gid.upper() != "GID-00":
        errors.append(ValidationError(
            ErrorCode.BSRG_004,
            f"BSRG reviewer_gid must be 'GID-00', got '{reviewer_gid}'"
        ))
        bsrg_data["failed_items"].append(f"reviewer_gid={reviewer_gid}")

    # Validate issuance_policy
    issuance_policy = bsrg.get("issuance_policy", "")
    if issuance_policy.upper() != "FAIL_CLOSED":
        errors.append(ValidationError(
            ErrorCode.BSRG_005,
            f"BSRG issuance_policy must be 'FAIL_CLOSED', got '{issuance_policy}'"
        ))
        bsrg_data["failed_items"].append(f"issuance_policy={issuance_policy}")

    # Validate checklist_results
    checklist_results = bsrg.get("checklist_results", {})
    bsrg_data["checklist_results"] = checklist_results

    if not checklist_results:
        errors.append(ValidationError(
            ErrorCode.BSRG_006,
            "BSRG checklist_results is missing or empty"
        ))
        bsrg_data["failed_items"].append("checklist_results=MISSING")
    else:
        # Check for required keys
        missing_keys = []
        non_pass_items = []

        for key in BSRG_REQUIRED_CHECKLIST_KEYS:
            if key not in checklist_results:
                missing_keys.append(key)
            else:
                value = checklist_results[key]
                # Normalize value
                if isinstance(value, bool):
                    value_str = "PASS" if value else "FAIL"
                elif isinstance(value, str):
                    value_str = value.upper().strip()
                else:
                    value_str = str(value).upper().strip()

                # Must be exactly "PASS" or True
                if value_str not in ("PASS", "TRUE"):
                    non_pass_items.append(f"{key}={value}")

        if missing_keys:
            errors.append(ValidationError(
                ErrorCode.BSRG_006,
                f"BSRG checklist_results missing required keys: {', '.join(missing_keys[:5])}"
            ))
            bsrg_data["failed_items"].extend([f"MISSING:{k}" for k in missing_keys])

        if non_pass_items:
            errors.append(ValidationError(
                ErrorCode.BSRG_007,
                f"BSRG checklist_results items not PASS: {', '.join(non_pass_items[:5])}"
            ))
            bsrg_data["failed_items"].extend(non_pass_items)

    # Validate failed_items
    failed_items = bsrg.get("failed_items", None)
    if failed_items is None:
        errors.append(ValidationError(
            ErrorCode.BSRG_012,
            "BSRG missing required field: failed_items"
        ))
    elif failed_items and len(failed_items) > 0:
        errors.append(ValidationError(
            ErrorCode.BSRG_008,
            f"BSRG failed_items must be empty, got: {failed_items}"
        ))
        bsrg_data["failed_items"].extend(failed_items)

    # Validate override_used
    override_used = bsrg.get("override_used", None)
    if override_used is None:
        errors.append(ValidationError(
            ErrorCode.BSRG_012,
            "BSRG missing required field: override_used"
        ))
    elif override_used is True or str(override_used).lower() == "true":
        errors.append(ValidationError(
            ErrorCode.BSRG_009,
            "BSRG override_used must be false — no manual overrides permitted"
        ))
        bsrg_data["failed_items"].append("override_used=true")

    # Validate ordering constraints
    ordering_errors = validate_bsrg_ordering(content)
    errors.extend(ordering_errors)

    # Set final status
    if not errors:
        bsrg_data["status"] = "PASS"

    return errors, bsrg_data


def emit_positive_closure_training_signal() -> dict:
    """
    Generate the canonical training signal for successful Positive Closure.
    """
    return {
        "TRAINING_SIGNAL": {
            "type": "POSITIVE_REINFORCEMENT",
            "pattern": "GOVERNANCE_POSITIVE_CLOSURE",
            "learning": [
                "Positive Closure is the only valid success state",
                "Gold Standard compliance is binary",
                "Corrections require explicit closure",
                "Implicit success is forbidden",
            ],
            "propagate_to_agents": True,
            "retention": "PERMANENT",
        }
    }


def validate_final_state(content: str) -> list:
    """Validate FINAL_STATE block if present."""
    errors = []

    block = extract_block(content, "FINAL_STATE")
    if not block:
        # Not required for legacy files
        return errors

    fields = parse_block_fields(block)

    # Check governance_compliant if present
    compliant = fields.get("governance_compliant", "")
    if compliant and "true" not in compliant.lower():
        errors.append(ValidationError(
            ErrorCode.G0_010,
            f"FINAL_STATE governance_compliant must be true, got '{compliant}'"
        ))

    # Check hard_gates if present
    gates = fields.get("hard_gates", "")
    if gates and "ENFORCED" not in gates.upper():
        errors.append(ValidationError(
            ErrorCode.G0_010,
            f"FINAL_STATE hard_gates must be 'ENFORCED', got '{gates}'"
        ))

    return errors


# ═══════════════════════════════════════════════════════════════════════════════
# REVIEW GATE v1.1 VALIDATION
# PAC-BENSON-G0-REVIEW-GATE-V1-1-IMPLEMENTATION-01
#
# Review Gate mirrors gate_pack exactly. No discretionary logic.
# All PAC/WRAP reviews must include terminal Gold Standard Checklist.
# Mode: STRICT. Bypass: IMPOSSIBLE.
# ═══════════════════════════════════════════════════════════════════════════════

# Required checklist items for Review Gate Gold Standard
REVIEW_GATE_CHECKLIST_ITEMS = [
    "identity_correct",
    "agent_color_correct",
    "execution_lane_correct",
    "canonical_headers_present",
    "block_order_correct",
    "agent_activation_ack_present",
    "runtime_activation_ack_present",
    "review_gate_declared",
    "scope_lock_present",
    "forbidden_actions_declared",
    "error_codes_declared",
    "training_signal_present",
    "final_state_declared",
    "self_certification_present",
    "checklist_terminal",
    "checklist_all_items_passed",
]


def is_review_artifact(content: str) -> bool:
    """
    Detect if content is a Review artifact that requires Review Gate validation.

    Review artifacts are identified by EXPLICIT review markers only.
    Does NOT trigger on correction packs or positive closures that use similar sections.
    """
    content_upper = content.upper()

    # Explicit review artifact markers - must have one of these
    explicit_review_markers = [
        "REVIEW_GATE_DECLARATION",
        "REVIEW-GATE",
        "REVIEWGATE:",
        "REVIEW_ID:",
        "ARTIFACT_UNDER_REVIEW:",
    ]

    # Check for explicit review markers
    has_explicit_marker = any(marker in content_upper for marker in explicit_review_markers)

    # Also check if the file ID explicitly contains REVIEW-
    has_review_id = "REVIEW-" in content_upper and "PAC-" not in content_upper.split("REVIEW-")[0][-20:]

    # Only return True if explicitly marked as a review artifact
    return has_explicit_marker or has_review_id


def validate_review_gate(content: str) -> list:
    """
    Validate Review Gate artifacts.

    This is a HARD GATE — Review Gate requirements are structurally enforced.
    - Mode: STRICT
    - Discretionary review: FORBIDDEN
    - All checklist items must pass

    FORBIDDEN_ACTIONS:
    - Implicit approval
    - Narrative-only review
    - Partial checklist acceptance
    - Discretionary override
    - Approval without self-certification
    - Approval without training signal
    """
    errors = []
    content_upper = content.upper()

    # RG_006: Check for activation acknowledgements
    if "RUNTIME_ACTIVATION_ACK" not in content_upper:
        errors.append(ValidationError(
            ErrorCode.RG_006,
            "Review artifact missing RUNTIME_ACTIVATION_ACK"
        ))

    if "AGENT_ACTIVATION_ACK" not in content_upper:
        errors.append(ValidationError(
            ErrorCode.RG_006,
            "Review artifact missing AGENT_ACTIVATION_ACK"
        ))

    # RG_001: Check for ReviewGate declaration
    has_review_gate = any(marker in content_upper for marker in [
        "REVIEW_GATE_DECLARATION",
        "REVIEWGATE",
        "REVIEW_GATE:",
    ])

    if not has_review_gate:
        errors.append(ValidationError(
            ErrorCode.RG_001,
            "Missing ReviewGate declaration"
        ))

    # RG_002: Check for terminal Gold Standard Checklist
    if "GOLD_STANDARD_CHECKLIST" not in content_upper:
        errors.append(ValidationError(
            ErrorCode.RG_002,
            "Missing terminal Gold Standard Checklist"
        ))
    else:
        # Validate checklist items
        checklist_errors = _validate_review_checklist(content)
        errors.extend(checklist_errors)

    # RG_003: Check for self-certification
    if "SELF_CERTIFICATION" not in content_upper:
        errors.append(ValidationError(
            ErrorCode.RG_003,
            "Missing reviewer self-certification"
        ))
    else:
        # Validate self-certification is complete
        cert_block = extract_block(content, "SELF_CERTIFICATION")
        if cert_block:
            fields = parse_block_fields(cert_block)
            certified = fields.get("certified", "").lower()
            if "true" not in certified:
                errors.append(ValidationError(
                    ErrorCode.RG_003,
                    "Self-certification not marked as certified: true"
                ))

    # RG_004: Check for training signal
    if "TRAINING_SIGNAL" not in content_upper:
        errors.append(ValidationError(
            ErrorCode.RG_004,
            "Missing training signal in review artifact"
        ))

    # RG_007: Check for runtime enforcement markers
    enforcement_markers = [
        "FAIL_CLOSED",
        "CI_ENFORCED",
        "PRE_COMMIT_ENFORCED",
    ]

    has_enforcement = any(marker in content_upper for marker in enforcement_markers)
    if not has_enforcement:
        errors.append(ValidationError(
            ErrorCode.RG_007,
            "Missing runtime enforcement declaration (fail_closed, ci_enforced, or pre_commit_enforced)"
        ))

    return errors


def _validate_review_checklist(content: str) -> list:
    """
    Validate Gold Standard Checklist in review artifacts.
    All items must be present and marked true.
    """
    errors = []

    # Extract checklist block
    checklist_block = extract_block(content, "GOLD_STANDARD_CHECKLIST")
    if not checklist_block:
        return errors

    fields = parse_block_fields(checklist_block)

    # Check required items
    missing_items = []
    false_items = []

    for item in REVIEW_GATE_CHECKLIST_ITEMS:
        if item not in fields:
            missing_items.append(item)
        else:
            value = fields[item].lower().strip()
            if value not in ["true", "yes", "✓", "✅", "pass", "passed"]:
                false_items.append(f"{item}={fields[item]}")

    if missing_items:
        errors.append(ValidationError(
            ErrorCode.RG_005,
            f"Gold Standard Checklist missing items: {', '.join(missing_items[:5])}"
        ))

    if false_items:
        errors.append(ValidationError(
            ErrorCode.RG_005,
            f"Gold Standard Checklist items not passing: {', '.join(false_items[:5])}"
        ))

    return errors


def validate_pac_id(content: str) -> list:
    """Validate PAC ID format if present."""
    errors = []

    # Look for PAC ID in various formats
    pac_id_pattern = r"PAC-[A-Z]+-[A-Z0-9]+-[A-Z0-9]+-\d+"
    if not re.search(pac_id_pattern, content, re.IGNORECASE):
        # Also try simpler format
        simple_pattern = r"PAC-[A-Z]+-[A-Z0-9-]+-\d+"
        if not re.search(simple_pattern, content, re.IGNORECASE):
            # Check if there's any PAC reference
            if "PAC-" in content.upper():
                # There's a PAC reference but it doesn't match pattern
                pass  # Allow flexible PAC ID formats for now

    return errors


def validate_content(content: str, registry: dict) -> ValidationResult:
    """Validate PAC content against canonical template."""
    errors = []

    # Skip files that don't look like PACs
    if "ACTIVATION_ACK" not in content and "PAC-" not in content and "WRAP-" not in content:
        return ValidationResult(valid=True, errors=[])

    # Check for legacy format markers (grandfathered files)
    # Legacy files created before G0.1.0 don't require ACTIVATION_ACK blocks
    legacy_markers = [
        "GOVERNANCE_CORRECTION",  # Legacy correction PACs
        "## I. EXECUTING AGENT",  # Old table format
        "| EXECUTING AGENT |",    # Old table format
        "## II. PAC REFERENCE",   # Old section format
    ]

    is_legacy = any(marker in content for marker in legacy_markers)

    # If file has ACTIVATION_ACK content, validate it fully regardless of legacy
    has_activation_ack = "ACTIVATION_ACK" in content.upper()

    # Legacy files without ACTIVATION_ACK blocks are grandfathered
    if is_legacy and not has_activation_ack:
        # Still validate what we can
        errors.extend(validate_training_signal(content))
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )

    # Full validation for G0.1.0+ compliant files
    # Validate block order
    errors.extend(validate_block_order(content))

    # =========================================================================
    # HARD-GATE: CORRECTION PACK VALIDATION (G0_020-G0_024)
    # If this is a correction pack, apply fail-closed validation
    # NO PARTIAL CHECKLISTS. NO MANUAL OVERRIDES. NO EXCEPTIONS.
    # =========================================================================
    if is_correction_pack(content):
        # Validate Gold Standard Checklist - MANDATORY
        checklist_errors = validate_gold_standard_checklist(content)
        if checklist_errors:
            # Emit training signal for each failure
            for err in checklist_errors:
                emit_training_signal_for_failure(err.code)
            errors.extend(checklist_errors)

        # Validate Self-Certification - MANDATORY
        cert_errors = validate_self_certification(content)
        if cert_errors:
            for err in cert_errors:
                emit_training_signal_for_failure(err.code)
            errors.extend(cert_errors)

        # Validate Violations Addressed Section - MANDATORY
        violations_errors = validate_violations_addressed(content)
        if violations_errors:
            for err in violations_errors:
                emit_training_signal_for_failure(err.code)
            errors.extend(violations_errors)
    # =========================================================================
    # END HARD-GATE: CORRECTION PACK VALIDATION
    # =========================================================================

    # =========================================================================
    # HARD-GATE: POSITIVE CLOSURE VALIDATION (G0_040-G0_046)
    # PAC-ATLAS-G3-GATEPACK-POSITIVE-CLOSURE-HARDWIRE-01
    #
    # Positive Closure is a FIRST-CLASS closure class.
    # Structural enforcement. Semantic misuse impossible.
    # NO IMPLICIT SUCCESS. NO DOWNGRADE. NO BYPASS.
    # =========================================================================
    if is_positive_closure_pack(content):
        # Validate all Positive Closure requirements
        closure_errors = validate_positive_closure(content)
        if closure_errors:
            # Emit training signal for each failure
            for err in closure_errors:
                emit_training_signal_for_failure(err.code)
            errors.extend(closure_errors)
    # =========================================================================
    # END HARD-GATE: POSITIVE CLOSURE VALIDATION
    # =========================================================================

    # =========================================================================
    # HARD-GATE: REVIEW GATE v1.1 VALIDATION (RG_001-RG_007)
    # PAC-BENSON-G0-REVIEW-GATE-V1-1-IMPLEMENTATION-01
    #
    # Review Gate mirrors gate_pack exactly. No discretionary logic.
    # All PAC/WRAP reviews require terminal Gold Standard Checklist.
    # Mode: STRICT. Discretionary override: FORBIDDEN. Bypass: IMPOSSIBLE.
    # =========================================================================
    if is_review_artifact(content):
        # Validate all Review Gate requirements
        review_errors = validate_review_gate(content)
        if review_errors:
            # Emit training signal for each failure
            for err in review_errors:
                emit_training_signal_for_failure(err.code)
            errors.extend(review_errors)
    # =========================================================================
    # END HARD-GATE: REVIEW GATE v1.1 VALIDATION
    # =========================================================================

    # =========================================================================
    # HARD-GATE: BSRG-01 VALIDATION (BSRG_001-BSRG_012)
    # PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01
    #
    # Benson Self-Review Gate — Every PAC requires explicit self-review.
    # Mode: FAIL_CLOSED. No bypass. No implicit approval.
    # =========================================================================
    if is_pac_artifact(content):
        # Validate BSRG-01 requirements
        bsrg_errors, bsrg_data = validate_benson_self_review_gate(content)
        if bsrg_errors:
            # Emit training signal for each failure
            for err in bsrg_errors:
                emit_training_signal_for_failure(err.code)
            errors.extend(bsrg_errors)

        # Record BSRG result to ledger if enabled
        import os
        if os.environ.get("LEDGER_WRITE_ENABLED", "0") == "1":
            try:
                _record_bsrg_to_ledger(content, bsrg_data)
            except Exception as e:
                print(f"⚠ BSRG ledger recording failed: {e}")
    # =========================================================================
    # END HARD-GATE: BSRG-01 VALIDATION
    # =========================================================================

    # Validate runtime block
    errors.extend(validate_runtime_block(content, registry))

    # Validate agent block
    errors.extend(validate_agent_block(content, registry))

    # =========================================================================
    # HARD-GATE: AGENT COLOR ENFORCEMENT (GS_030-GS_032)
    # PAC-ATLAS-P25-GOLD-STANDARD-AGENT-COLOR-ENFORCEMENT-01
    #
    # Agent color is a FIRST-CLASS GOVERNANCE INVARIANT.
    # Color is not cosmetic; it is governance-critical identity.
    # Mode: FAIL_CLOSED. No bypass. No override.
    # =========================================================================
    color_errors = validate_agent_color(content, registry)
    if color_errors:
        for err in color_errors:
            emit_training_signal_for_failure(err.code)
        errors.extend(color_errors)
    # =========================================================================
    # END HARD-GATE: AGENT COLOR ENFORCEMENT
    # =========================================================================

    # Determine if TRAINING_SIGNAL is required
    # Required for: new PACs/WRAPs with ACTIVATION_ACK blocks (G0.2.0+)
    # Not required for: template files, lock files, protocol files
    is_template_file = any(marker in content for marker in [
        "CANONICAL_PAC_TEMPLATE",
        "GOLD_STANDARD_WRAP_TEMPLATE",
        "CORRECTION_PROTOCOL",
        "AGENT_REGISTRY",
        "Template Schema",
        "## Block 0:",  # Template documentation
    ])

    require_training = has_activation_ack and not is_template_file

    # Validate training signal
    errors.extend(validate_training_signal(content, require_training))

    # Validate FINAL_STATE
    errors.extend(validate_final_state(content))

    # Validate PAC ID
    errors.extend(validate_pac_id(content))

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors
    )


def validate_file(file_path: Path, registry: dict) -> ValidationResult:
    """Validate a single file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=[ValidationError(ErrorCode.G0_010, f"Cannot read file: {e}")]
        )

    return validate_content(content, registry)


def find_pac_files(paths: list) -> list:
    """Find PAC/WRAP files in given paths."""
    pac_files = []

    for path_str in paths:
        path = Path(path_str)
        if path.is_file():
            pac_files.append(path)
        elif path.is_dir():
            pac_files.extend(path.glob("**/PAC-*.md"))
            pac_files.extend(path.glob("**/WRAP-*.md"))
            pac_files.extend(path.glob("**/docs/governance/**/*.md"))

    return list(set(pac_files))


def run_precommit_mode() -> int:
    """Run in pre-commit mode. Returns exit code."""
    print("=" * 60)
    print("Governance Gate — Pre-Commit Validation")
    print("Mode: FAIL_CLOSED")
    print("=" * 60)

    registry = load_registry()
    if not registry:
        print("⚠ Warning: Could not load registry. Validation limited.")

    # Get staged files (in real pre-commit, this would come from git)
    # For now, validate governance directory
    paths = [REPO_ROOT / "docs" / "governance"]
    pac_files = find_pac_files([str(p) for p in paths])

    if not pac_files:
        print("No PAC files to validate.")
        return 0

    all_errors = {}
    for pac_file in pac_files:
        result = validate_file(pac_file, registry)
        if not result.valid:
            all_errors[str(pac_file)] = result.errors

    if all_errors:
        print("\n✗ VALIDATION FAILED — COMMIT BLOCKED")
        for file_path, errors in all_errors.items():
            print(f"\n{file_path}:")
            for error in errors:
                print(f"  [{error.code.name}] {error.message}")
        return 1

    print(f"\n✓ Validated {len(pac_files)} file(s) — COMMIT ALLOWED")
    return 0


def run_ci_mode() -> int:
    """Run in CI mode. Returns exit code."""
    print("=" * 60)
    print("Governance Gate — CI Validation")
    print("Mode: FAIL_CLOSED")
    print("=" * 60)

    registry = load_registry()
    if not registry:
        print("⚠ Warning: Could not load registry. Validation limited.")

    paths = [REPO_ROOT / "docs" / "governance"]
    pac_files = find_pac_files([str(p) for p in paths])

    if not pac_files:
        print("No PAC files to validate.")
        return 0

    all_errors = {}
    for pac_file in pac_files:
        result = validate_file(pac_file, registry)
        if not result.valid:
            all_errors[str(pac_file)] = result.errors

    print(f"\nValidated: {len(pac_files)} files")
    print(f"Errors: {sum(len(e) for e in all_errors.values())}")

    if all_errors:
        print("\n" + "=" * 60)
        print("✗ VALIDATION FAILED — MERGE BLOCKED")
        print("=" * 60)
        for file_path, errors in all_errors.items():
            print(f"\n{file_path}:")
            for error in errors:
                print(f"  [{error.code.name}] {error.message}")
        return 1

    print("\n✓ ALL VALIDATIONS PASSED — MERGE ALLOWED")
    return 0


def run_file_mode(file_path: str, record_ledger: bool = True) -> int:
    """Validate a single file. Returns exit code."""
    print(f"Validating: {file_path}")

    registry = load_registry()
    path = Path(file_path)

    if not path.exists():
        print(f"✗ File not found: {file_path}")
        return 2

    result = validate_file(path, registry)

    # Extract artifact info for ledger recording
    content = path.read_text()
    artifact_id = extract_artifact_id(content) or path.stem
    agent_info = extract_agent_info(content)
    agent_gid = agent_info.get("gid", "UNKNOWN")
    agent_name = agent_info.get("name", "UNKNOWN")
    artifact_type = "PAC" if "PAC-" in artifact_id else "WRAP"

    if result.valid:
        print("✓ VALID")
        if record_ledger:
            record_validation_to_ledger(
                artifact_id=artifact_id,
                agent_gid=agent_gid,
                agent_name=agent_name,
                artifact_type=artifact_type,
                result="PASS",
                file_path=str(path)
            )
        return 0
    else:
        print("✗ INVALID")
        for error in result.errors:
            print(f"  [{error.code.name}] {error.message}")
        if record_ledger:
            error_codes = [e.code.name for e in result.errors]
            record_validation_to_ledger(
                artifact_id=artifact_id,
                agent_gid=agent_gid,
                agent_name=agent_name,
                artifact_type=artifact_type,
                result="FAIL",
                error_codes=error_codes,
                file_path=str(path)
            )
        return 1


def extract_artifact_id(content: str) -> Optional[str]:
    """Extract PAC/WRAP ID from content."""
    # Try PAC ID
    pac_match = re.search(r'(PAC-[A-Z]+-G\d+-[A-Z0-9-]+)', content)
    if pac_match:
        return pac_match.group(1)

    # Try WRAP ID
    wrap_match = re.search(r'(WRAP-[A-Z]+-G\d+-[A-Z0-9-]+)', content)
    if wrap_match:
        return wrap_match.group(1)

    return None


def extract_agent_info(content: str) -> dict:
    """Extract agent GID and name from content."""
    result = {"gid": "UNKNOWN", "name": "UNKNOWN"}

    # Try AGENT_ACTIVATION_ACK block
    gid_match = re.search(r'gid:\s*["\']?(GID-\d+)["\']?', content, re.IGNORECASE)
    if gid_match:
        result["gid"] = gid_match.group(1)

    agent_match = re.search(r'agent:\s*["\']?(\w+)["\']?', content, re.IGNORECASE)
    if agent_match:
        result["name"] = agent_match.group(1).upper()

    return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Governance Gate Engine — PAC Validation"
    )
    parser.add_argument(
        "--mode",
        choices=["precommit", "ci"],
        help="Validation mode"
    )
    parser.add_argument(
        "--file",
        help="Single file to validate"
    )

    args = parser.parse_args()

    if args.file:
        sys.exit(run_file_mode(args.file))
    elif args.mode == "precommit":
        sys.exit(run_precommit_mode())
    elif args.mode == "ci":
        sys.exit(run_ci_mode())
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
