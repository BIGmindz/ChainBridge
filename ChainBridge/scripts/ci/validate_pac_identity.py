#!/usr/bin/env python3
"""
PAC Identity Validation Script — CI Gate Enforcement

Authority: PAC-BENSON-FUNNEL-ENFORCEMENT-CI-GATE-01
Owner: Benson (GID-00)
Mode: FAIL_CLOSED

This script enforces the identity funnel at CI time. Non-compliant PACs
cannot land. Drift is not a discussion — it's a blocked merge.

Exit Codes:
  0 = All validations passed
  1 = Validation failure (blocked)
  2 = Script error (blocked)
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "governance" / "AGENT_REGISTRY.json"

# CI Invariants
CI_INVARIANTS = {
    "required_blocks": [
        "RUNTIME_ACTIVATION_ACK",
        "AGENT_ACTIVATION_ACK",
    ],
    "block_order_enforced": True,
    "agent_identity_required": ["gid", "color", "icon", "execution_lane"],
    "runtime_identity_constraints": {
        "gid_forbidden": True,
        "agent_name_forbidden": True,
    },
    "wrap_identity_echo_required": True,
    "failure_mode": "FAIL_CLOSED",
}

# Allowed funnel stages
ALLOWED_FUNNEL_STAGES = [
    "CANONICAL",
    "IDENTITY",
    "TEMPLATE",
    "CI_ENFORCEMENT",
    "EXECUTION",
]


class ValidationError(Exception):
    """Raised when PAC/WRAP validation fails."""

    pass


def load_registry() -> dict:
    """Load the canonical agent registry."""
    if not REGISTRY_PATH.exists():
        raise ValidationError(f"Registry not found: {REGISTRY_PATH}")

    with open(REGISTRY_PATH) as f:
        return json.load(f)


def extract_block(content: str, block_name: str) -> Optional[str]:
    """Extract a named block from PAC/WRAP content."""
    # Match block pattern: BLOCK_NAME { ... }
    pattern = rf"{block_name}\s*\{{\s*(.*?)\s*\}}"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def parse_block_fields(block_content: str) -> dict:
    """Parse key-value pairs from a block."""
    fields = {}
    # Match: key: "value" or key: value
    pattern = r'(\w+)\s*:\s*["\']?([^"\'\n]+)["\']?'
    for match in re.finditer(pattern, block_content):
        key = match.group(1).lower()
        value = match.group(2).strip().strip('"').strip("'")
        fields[key] = value
    return fields


def find_block_positions(content: str) -> dict:
    """Find the positions of required blocks in content."""
    positions = {}
    for block_name in CI_INVARIANTS["required_blocks"]:
        pattern = rf"{block_name}\s*\{{"
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            positions[block_name] = match.start()
    return positions


def validate_block_order(content: str) -> None:
    """Ensure blocks appear in the required order."""
    if not CI_INVARIANTS["block_order_enforced"]:
        return

    positions = find_block_positions(content)
    required = CI_INVARIANTS["required_blocks"]

    prev_pos = -1
    prev_block = None
    for block_name in required:
        if block_name not in positions:
            continue  # Missing block handled elsewhere
        pos = positions[block_name]
        if pos < prev_pos:
            raise ValidationError(
                f"Block order violation: {block_name} appears before {prev_block}. "
                f"Required order: {' → '.join(required)}"
            )
        prev_pos = pos
        prev_block = block_name


def validate_runtime_block(content: str) -> None:
    """Validate RUNTIME_ACTIVATION_ACK block constraints."""
    block = extract_block(content, "RUNTIME_ACTIVATION_ACK")
    if not block:
        raise ValidationError(
            "Missing required block: RUNTIME_ACTIVATION_ACK. "
            "Every PAC/WRAP must declare the executing runtime."
        )

    fields = parse_block_fields(block)
    constraints = CI_INVARIANTS["runtime_identity_constraints"]

    # Runtime must NOT have a GID (or must explicitly state N/A)
    if constraints["gid_forbidden"]:
        gid = fields.get("gid", "")
        if gid and "N/A" not in gid.upper() and "RUNTIME" not in gid.upper():
            raise ValidationError(
                f"Runtime GID violation: Runtime declared gid='{gid}'. "
                "Runtimes are NOT agents. Use 'gid: N/A (RUNTIME)' or omit entirely."
            )

    # Runtime must have runtime_name, not agent_name
    if "runtime_name" not in fields and "runtime_type" not in fields:
        raise ValidationError(
            "Runtime block missing 'runtime_name' or 'runtime_type'. "
            "Runtimes must identify as runtimes, not agents."
        )


def validate_agent_block(content: str, registry: dict) -> None:
    """Validate AGENT_ACTIVATION_ACK block against registry."""
    block = extract_block(content, "AGENT_ACTIVATION_ACK")
    if not block:
        raise ValidationError(
            "Missing required block: AGENT_ACTIVATION_ACK. "
            "Every PAC/WRAP must declare the issuing agent."
        )

    fields = parse_block_fields(block)
    required_fields = CI_INVARIANTS["agent_identity_required"]

    # Check required fields
    for field in required_fields:
        if field not in fields:
            raise ValidationError(
                f"Agent block missing required field: '{field}'. "
                f"Required: {', '.join(required_fields)}"
            )

    # Validate against registry
    agent_name = fields.get("agent_name", "").upper()
    agents = registry.get("agents", {})

    if agent_name and agent_name in agents:
        reg_agent = agents[agent_name]

        # Validate GID
        declared_gid = fields.get("gid", "").upper()
        registry_gid = reg_agent.get("gid", "").upper()
        if declared_gid != registry_gid:
            raise ValidationError(
                f"GID mismatch: Agent {agent_name} declared gid='{declared_gid}' "
                f"but registry says '{registry_gid}'"
            )

        # Validate color
        declared_color = fields.get("color", "").upper()
        registry_color = reg_agent.get("color", "").upper()
        if declared_color != registry_color:
            raise ValidationError(
                f"Color mismatch: Agent {agent_name} declared color='{declared_color}' "
                f"but registry says '{registry_color}'"
            )

        # Validate icon (with some flexibility for emoji encoding)
        declared_icon = fields.get("icon", "")
        registry_icon = reg_agent.get("icon", "")
        if declared_icon and registry_icon:
            # Normalize for comparison (some emojis have variant selectors)
            if declared_icon.strip() != registry_icon.strip():
                # Allow if one contains the other (variant selector handling)
                if registry_icon not in declared_icon and declared_icon not in registry_icon:
                    raise ValidationError(
                        f"Icon mismatch: Agent {agent_name} declared icon='{declared_icon}' "
                        f"but registry says '{registry_icon}'"
                    )

        # Validate execution_lane
        declared_lane = fields.get("execution_lane", "").upper()
        registry_lane = reg_agent.get("execution_lane", "").upper()
        if declared_lane != registry_lane:
            raise ValidationError(
                f"Execution lane mismatch: Agent {agent_name} declared "
                f"execution_lane='{declared_lane}' but registry says '{registry_lane}'"
            )

    # Check for forbidden aliases
    forbidden = registry.get("forbidden_aliases", [])
    if agent_name in [a.upper() for a in forbidden]:
        raise ValidationError(
            f"Forbidden agent alias: '{agent_name}' is not a valid agent. "
            f"Forbidden aliases: {', '.join(forbidden)}"
        )


def validate_funnel_stage(content: str) -> None:
    """Validate that PAC declares a valid funnel stage."""
    # Look for "Funnel Stage:" declaration
    pattern = r"Funnel\s+Stage\s*:\s*(\w+)"
    match = re.search(pattern, content, re.IGNORECASE)

    if not match:
        raise ValidationError(
            "Missing Funnel Stage declaration. "
            f"Every PAC must include 'Funnel Stage: <STAGE>' where STAGE is one of: "
            f"{', '.join(ALLOWED_FUNNEL_STAGES)}"
        )

    stage = match.group(1).upper()
    if stage not in ALLOWED_FUNNEL_STAGES:
        raise ValidationError(
            f"Invalid Funnel Stage: '{stage}'. "
            f"Allowed values: {', '.join(ALLOWED_FUNNEL_STAGES)}"
        )


def validate_wrap_identity_echo(content: str) -> bool:
    """Check if this is a WRAP and validate identity echo if so."""
    if not CI_INVARIANTS["wrap_identity_echo_required"]:
        return True

    # Check if this looks like a WRAP (contains WRAP- in title or EXECUTION_SUMMARY)
    is_wrap = bool(re.search(r"WRAP-\w+", content)) or bool(
        extract_block(content, "EXECUTION_SUMMARY")
    )

    if not is_wrap:
        return True  # Not a WRAP, skip this check

    # WRAPs must have EXECUTION_SUMMARY that echoes agent identity
    summary = extract_block(content, "EXECUTION_SUMMARY")
    if not summary:
        raise ValidationError(
            "WRAP missing EXECUTION_SUMMARY block. "
            "WRAPs must echo agent identity in EXECUTION_SUMMARY."
        )

    fields = parse_block_fields(summary)
    required = ["agent", "gid"]
    for field in required:
        if field not in fields:
            raise ValidationError(
                f"WRAP EXECUTION_SUMMARY missing required field: '{field}'. "
                "WRAPs must echo agent identity."
            )

    return True


def validate_file(file_path: Path, registry: dict) -> list:
    """Validate a single PAC/WRAP file. Returns list of errors."""
    errors = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Cannot read file {file_path}: {e}"]

    # Skip files that don't look like PACs/WRAPs
    if not re.search(r"(PAC-|WRAP-|ACTIVATION_ACK)", content, re.IGNORECASE):
        return []  # Not a PAC/WRAP, skip

    try:
        validate_block_order(content)
    except ValidationError as e:
        errors.append(str(e))

    try:
        validate_runtime_block(content)
    except ValidationError as e:
        errors.append(str(e))

    try:
        validate_agent_block(content, registry)
    except ValidationError as e:
        errors.append(str(e))

    try:
        validate_funnel_stage(content)
    except ValidationError as e:
        errors.append(str(e))

    try:
        validate_wrap_identity_echo(content)
    except ValidationError as e:
        errors.append(str(e))

    return errors


def find_pac_files(paths: list) -> list:
    """Find all PAC/WRAP files from given paths."""
    pac_files = []

    for path_str in paths:
        path = Path(path_str)
        if path.is_file():
            pac_files.append(path)
        elif path.is_dir():
            # Search for PAC/WRAP files in directory
            pac_files.extend(path.glob("**/PAC-*.md"))
            pac_files.extend(path.glob("**/WRAP-*.md"))
            # Also check governance directory
            pac_files.extend(path.glob("**/docs/governance/**/*.md"))

    return list(set(pac_files))


def main() -> int:
    """Main entry point. Returns exit code."""
    print("=" * 60)
    print("PAC Identity Validation — CI Gate")
    print("Authority: Benson (GID-00)")
    print(f"Failure Mode: {CI_INVARIANTS['failure_mode']}")
    print("=" * 60)

    # Load registry
    try:
        registry = load_registry()
        print(f"✓ Registry loaded: v{registry.get('_metadata', {}).get('version', 'unknown')}")
    except ValidationError as e:
        print(f"✗ FATAL: {e}")
        return 2

    # Get files to validate
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
    else:
        # Default: validate governance docs
        paths = [str(REPO_ROOT / "docs" / "governance")]

    pac_files = find_pac_files(paths)
    print(f"Files to validate: {len(pac_files)}")

    if not pac_files:
        print("⚠ No PAC/WRAP files found. Nothing to validate.")
        return 0

    # Validate each file
    all_errors = {}
    for pac_file in pac_files:
        errors = validate_file(pac_file, registry)
        if errors:
            all_errors[str(pac_file)] = errors

    # Report results
    print("\n" + "=" * 60)
    if all_errors:
        print("✗ VALIDATION FAILED — MERGE BLOCKED")
        print("=" * 60)
        for file_path, errors in all_errors.items():
            print(f"\n{file_path}:")
            for error in errors:
                print(f"  ✗ {error}")
        print(f"\nTotal errors: {sum(len(e) for e in all_errors.values())}")
        print("\nDrift is not a discussion. Fix violations before merge.")
        return 1
    else:
        print("✓ ALL VALIDATIONS PASSED")
        print("=" * 60)
        print(f"Validated {len(pac_files)} file(s)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
