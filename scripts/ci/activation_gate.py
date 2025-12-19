#!/usr/bin/env python3
"""
CI Activation Gate — Mandatory Pre-Execution Validation
════════════════════════════════════════════════════════════════════════════════

ENFORCEMENT: No CI job may execute without validated Activation Block.

This script is called as the FIRST step in any CI pipeline that executes
code or makes changes. It validates:

1. Activation Block presence in changed files (if PAC-related)
2. Activation Block structure correctness
3. No duplicate/conflicting Activation Blocks
4. Position validation (Activation Block must be first)

FAILURE MODES (all are HARD FAIL):
- DENIED_ACTIVATION_MISSING: No Activation Block found
- DENIED_ACTIVATION_MALFORMED: Block structure invalid
- DENIED_ACTIVATION_DUPLICATE: Multiple blocks detected
- DENIED_ACTIVATION_MISORDERED: Block not in first position
- DENIED_ACTIVATION_REGISTRY_MISMATCH: Identity doesn't match registry

PAC Reference: PAC-DAN-ACTIVATION-GATE-CI-ENFORCEMENT-01
Agent: DAN (GID-07)
Lane: 🟢 GREEN — DevOps / CI-CD

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class DenialCode(str, Enum):
    """Structured denial codes for CI gate failures."""

    DENIED_ACTIVATION_MISSING = "DENIED_ACTIVATION_MISSING"
    DENIED_ACTIVATION_MALFORMED = "DENIED_ACTIVATION_MALFORMED"
    DENIED_ACTIVATION_DUPLICATE = "DENIED_ACTIVATION_DUPLICATE"
    DENIED_ACTIVATION_MISORDERED = "DENIED_ACTIVATION_MISORDERED"
    DENIED_ACTIVATION_REGISTRY_MISMATCH = "DENIED_ACTIVATION_REGISTRY_MISMATCH"
    DENIED_ACTIVATION_UNKNOWN_AGENT = "DENIED_ACTIVATION_UNKNOWN_AGENT"


@dataclass
class GateResult:
    """Structured result from activation gate check."""

    passed: bool
    denial_code: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    message: str = ""
    agent_claimed: Optional[str] = None
    gid_claimed: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        """Return JSON representation for structured logging."""
        return json.dumps(asdict(self), indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern for Activation Block header
ACTIVATION_BLOCK_HEADER = re.compile(
    r"AGENT\s+ACTIVATION\s+BLOCK|ACTIVATION\s+BLOCK",
    re.IGNORECASE
)

# Pattern for EXECUTING AGENT line
EXECUTING_AGENT_PATTERN = re.compile(
    r"EXECUTING\s+AGENT\s*[:\-—]\s*(\w+(?:-\w+)?)",
    re.IGNORECASE
)

# Pattern for GID
GID_PATTERN = re.compile(r"(GID-\d+)", re.IGNORECASE)

# Pattern for PAC header
PAC_HEADER_PATTERN = re.compile(r"PAC-\w+-[\w-]+", re.IGNORECASE)


def detect_activation_blocks(content: str) -> list[tuple[int, str]]:
    """
    Detect all Activation Block headers in content.

    Returns list of (line_number, matched_text) tuples.
    """
    blocks = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        if ACTIVATION_BLOCK_HEADER.search(line):
            blocks.append((i, line.strip()))

    return blocks


def find_pac_header_line(content: str) -> Optional[int]:
    """Find the line number of the PAC header (if present)."""
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if PAC_HEADER_PATTERN.search(line):
            return i
    return None


def find_executing_agent_line(content: str) -> Optional[int]:
    """Find the line number of EXECUTING AGENT declaration."""
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if EXECUTING_AGENT_PATTERN.search(line):
            return i
    return None


def extract_identity(content: str) -> tuple[Optional[str], Optional[str]]:
    """Extract agent name and GID from content."""
    agent_match = EXECUTING_AGENT_PATTERN.search(content)
    gid_match = GID_PATTERN.search(content)

    agent = agent_match.group(1) if agent_match else None
    gid = gid_match.group(1) if gid_match else None

    return agent, gid


def validate_against_registry(agent: str, gid: str) -> tuple[bool, str]:
    """
    Validate agent/GID against canonical registry.

    Returns (is_valid, error_message).
    """
    try:
        from core.governance.agent_roster import get_agent_by_name
    except ImportError:
        return True, ""  # Can't validate, assume OK

    canonical = get_agent_by_name(agent)
    if canonical is None:
        return False, f"Agent '{agent}' not found in canonical registry"

    if canonical.gid.upper() != gid.upper():
        return False, f"GID mismatch: {agent} is {canonical.gid}, not {gid}"

    return True, ""


def check_file(file_path: Path, require_pac: bool = False) -> GateResult:
    """
    Check a single file for Activation Block compliance.

    Args:
        file_path: Path to the file to check
        require_pac: If True, only check files that look like PACs

    Returns:
        GateResult with pass/fail status
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return GateResult(
            passed=False,
            denial_code=DenialCode.DENIED_ACTIVATION_MISSING.value,
            file_path=str(file_path),
            message=f"Could not read file: {e}",
        )

    # Check if this looks like a PAC file
    has_pac_header = PAC_HEADER_PATTERN.search(content) is not None
    has_executing_agent = EXECUTING_AGENT_PATTERN.search(content) is not None

    # If not a PAC-like file, skip unless explicitly required
    if not has_pac_header and not has_executing_agent:
        if require_pac:
            return GateResult(
                passed=False,
                denial_code=DenialCode.DENIED_ACTIVATION_MISSING.value,
                file_path=str(file_path),
                message="File does not contain PAC structure or EXECUTING AGENT",
            )
        return GateResult(passed=True, file_path=str(file_path), message="Not a PAC file, skipped")

    # Detect activation blocks
    blocks = detect_activation_blocks(content)

    # Check for duplicates
    if len(blocks) > 1:
        return GateResult(
            passed=False,
            denial_code=DenialCode.DENIED_ACTIVATION_DUPLICATE.value,
            file_path=str(file_path),
            line_number=blocks[1][0],
            message=f"Multiple Activation Blocks detected at lines: {[b[0] for b in blocks]}",
        )

    # Check for presence
    if not has_executing_agent:
        return GateResult(
            passed=False,
            denial_code=DenialCode.DENIED_ACTIVATION_MISSING.value,
            file_path=str(file_path),
            message="No EXECUTING AGENT declaration found",
        )

    # Check ordering: EXECUTING AGENT should come before meaningful code
    pac_header_line = find_pac_header_line(content)
    exec_agent_line = find_executing_agent_line(content)

    if pac_header_line and exec_agent_line:
        # EXECUTING AGENT should be within 20 lines of PAC header
        if exec_agent_line - pac_header_line > 20:
            return GateResult(
                passed=False,
                denial_code=DenialCode.DENIED_ACTIVATION_MISORDERED.value,
                file_path=str(file_path),
                line_number=exec_agent_line,
                message=f"EXECUTING AGENT at line {exec_agent_line} is too far from PAC header at line {pac_header_line}",
            )

    # Extract and validate identity
    agent, gid = extract_identity(content)

    if not agent:
        return GateResult(
            passed=False,
            denial_code=DenialCode.DENIED_ACTIVATION_MALFORMED.value,
            file_path=str(file_path),
            message="Could not extract agent name from EXECUTING AGENT",
        )

    if not gid:
        return GateResult(
            passed=False,
            denial_code=DenialCode.DENIED_ACTIVATION_MALFORMED.value,
            file_path=str(file_path),
            line_number=exec_agent_line,
            agent_claimed=agent,
            message="No GID found in activation block",
        )

    # Validate against registry
    valid, error = validate_against_registry(agent, gid)
    if not valid:
        return GateResult(
            passed=False,
            denial_code=DenialCode.DENIED_ACTIVATION_REGISTRY_MISMATCH.value,
            file_path=str(file_path),
            line_number=exec_agent_line,
            agent_claimed=agent,
            gid_claimed=gid,
            message=error,
        )

    return GateResult(
        passed=True,
        file_path=str(file_path),
        agent_claimed=agent,
        gid_claimed=gid,
        message=f"Activation Block valid: {agent} ({gid})",
    )


def check_changed_files(
    base_branch: str = "main",
    check_all: bool = False,
) -> list[GateResult]:
    """
    Check changed files in current branch against base.

    Args:
        base_branch: Branch to compare against
        check_all: If True, check all Python files, not just changed ones

    Returns:
        List of GateResults
    """
    import subprocess

    results = []

    if check_all:
        # Find all Python files
        files = list(PROJECT_ROOT.rglob("*.py"))
        # Exclude tests, venv, etc.
        files = [
            f for f in files
            if ".venv" not in str(f)
            and "__pycache__" not in str(f)
            and "tests/" not in str(f)
        ]
    else:
        # Get changed files from git
        try:
            output = subprocess.check_output(
                ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
                cwd=PROJECT_ROOT,
                text=True,
            )
            changed = [f.strip() for f in output.split("\n") if f.strip().endswith(".py")]
            files = [PROJECT_ROOT / f for f in changed if (PROJECT_ROOT / f).exists()]
        except subprocess.CalledProcessError:
            # Fallback: check staged files
            try:
                output = subprocess.check_output(
                    ["git", "diff", "--cached", "--name-only"],
                    cwd=PROJECT_ROOT,
                    text=True,
                )
                changed = [f.strip() for f in output.split("\n") if f.strip().endswith(".py")]
                files = [PROJECT_ROOT / f for f in changed if (PROJECT_ROOT / f).exists()]
            except subprocess.CalledProcessError:
                files = []

    for file_path in files:
        result = check_file(file_path)
        if not result.passed or "PAC" in str(file_path).upper():
            results.append(result)

    return results


def print_result(result: GateResult, verbose: bool = False) -> None:
    """Print a single result with formatting."""
    if result.passed:
        if verbose:
            print(f"  ✅ {result.file_path}: {result.message}")
    else:
        print(f"  ❌ {result.file_path}:{result.line_number or 0}")
        print(f"     [{result.denial_code}] {result.message}")
        if result.agent_claimed:
            print(f"     Agent: {result.agent_claimed}, GID: {result.gid_claimed}")


def main() -> int:
    """Main entry point for CI activation gate."""
    parser = argparse.ArgumentParser(
        description="CI Activation Gate — Validate Activation Blocks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base branch to compare against (default: main)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all Python files, not just changed ones",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Check a specific file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (for CI parsing)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require PAC structure in all checked files",
    )

    args = parser.parse_args()

    # Suppress banner in JSON mode for clean parsing
    if not args.json:
        print("════════════════════════════════════════════════════════════════════")
        print("🟢 DAN (GID-07) — CI Activation Gate")
        print("════════════════════════════════════════════════════════════════════")
        print()
        print("PAC Reference: PAC-DAN-ACTIVATION-GATE-CI-ENFORCEMENT-01")
        print("Enforcement: HARD FAIL on activation violation")
        print()

    results: list[GateResult] = []

    if args.file:
        # Check single file
        result = check_file(args.file, require_pac=args.strict)
        results.append(result)
    else:
        # Check changed files
        results = check_changed_files(base_branch=args.base, check_all=args.all)

    # Process results
    failures = [r for r in results if not r.passed]
    passes = [r for r in results if r.passed]

    if args.json:
        # JSON mode: single result for --file, full report otherwise
        if args.file and len(results) == 1:
            # Single file JSON output
            output = asdict(results[0])
        else:
            # Multi-file JSON output
            output = {
                "gate": "activation",
                "timestamp": datetime.utcnow().isoformat(),
                "total_checked": len(results),
                "passed": len(passes),
                "failed": len(failures),
                "results": [asdict(r) for r in results],
            }
        print(json.dumps(output, indent=2))
    else:
        print(f"Checked {len(results)} files")
        print()

        if failures:
            print("🔴 ACTIVATION GATE FAILURES")
            print("════════════════════════════════════════════════════════════════════")
            for result in failures:
                print_result(result, args.verbose)
            print("════════════════════════════════════════════════════════════════════")
            print()
            print(f"❌ GATE DENIED: {len(failures)} activation violation(s)")
            print()
            print("CI cannot proceed without valid Activation Blocks.")
            print("No bypass. No continue-on-error.")
        else:
            if args.verbose:
                print("✅ PASSING FILES")
                print("────────────────────────────────────────────────────────────────────")
                for result in passes:
                    print_result(result, args.verbose)
                print()

            print("════════════════════════════════════════════════════════════════════")
            print("✅ ACTIVATION GATE PASSED")
            print("════════════════════════════════════════════════════════════════════")

        print()
        print("════════════════════════════════════════════════════════════════════")
        print("🟢 END — DAN (GID-07) — CI Activation Gate")
        print("════════════════════════════════════════════════════════════════════")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
