#!/usr/bin/env python3
"""
🟢 DAN (GID-07) — Claim Binding Guardrail
PAC-DAN-CLAIMS-BINDING-02: Bind Claim IDs into Audit Bundles

CI guardrail that validates claim bindings are complete and consistent.

Validation rules:
1. Every claim in TRUST_CLAIMS.md MUST have a binding in CLAIM_BINDINGS.json
2. Every binding MUST reference at least one test file
3. Every referenced test file MUST exist
4. No orphaned bindings (bindings without corresponding claims)

Usage:
    python scripts/validate_claim_bindings.py
    python scripts/validate_claim_bindings.py --strict

Exit codes:
    0 - All validations passed
    1 - Validation failures detected
    2 - Configuration or file errors

NO NEW GOVERNANCE LOGIC. Validation only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

TRUST_CLAIMS_PATH = "docs/trust/TRUST_CLAIMS.md"
CLAIM_BINDINGS_PATH = "docs/trust/CLAIM_BINDINGS.json"

# Regex to extract claim IDs from TRUST_CLAIMS.md
# Matches patterns like "### TC-ID-01:" or "### TC-AUTH-02:"
CLAIM_ID_PATTERN = re.compile(r"^###\s+(TC-[A-Z]+-\d+):", re.MULTILINE)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def find_project_root() -> Path:
    """Find project root by looking for pyproject.toml."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return current


def extract_claims_from_markdown(path: Path) -> set[str]:
    """Extract claim IDs from TRUST_CLAIMS.md."""
    if not path.exists():
        return set()

    content = path.read_text(encoding="utf-8")
    matches = CLAIM_ID_PATTERN.findall(content)
    return set(matches)


def load_bindings(path: Path) -> dict[str, Any] | None:
    """Load CLAIM_BINDINGS.json."""
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def validate_test_exists(test_path: str, project_root: Path) -> bool:
    """Check if a test file or test pattern exists."""
    # Handle test::class::method patterns
    file_path = test_path.split("::")[0]
    full_path = project_root / file_path

    # Handle glob patterns in paths (like manifests/*.yaml)
    if "*" in file_path:
        return len(list(project_root.glob(file_path))) > 0

    return full_path.exists()


def validate_bindings(
    project_root: Path,
    strict: bool = False,
) -> tuple[bool, list[str]]:
    """
    Validate claim bindings.

    Returns (success, messages).
    """
    messages: list[str] = []
    errors: list[str] = []

    claims_path = project_root / TRUST_CLAIMS_PATH
    bindings_path = project_root / CLAIM_BINDINGS_PATH

    # Check files exist
    if not claims_path.exists():
        errors.append(f"TRUST_CLAIMS.md not found at {claims_path}")
        return False, errors

    if not bindings_path.exists():
        errors.append(f"CLAIM_BINDINGS.json not found at {bindings_path}")
        return False, errors

    # Extract claims from markdown
    markdown_claims = extract_claims_from_markdown(claims_path)
    if not markdown_claims:
        errors.append("No claims found in TRUST_CLAIMS.md")
        return False, errors

    messages.append(f"Found {len(markdown_claims)} claims in TRUST_CLAIMS.md")

    # Load bindings
    bindings = load_bindings(bindings_path)
    if bindings is None:
        errors.append("Failed to parse CLAIM_BINDINGS.json")
        return False, errors

    binding_claims = set(bindings.get("claims", {}).keys())
    messages.append(f"Found {len(binding_claims)} bindings in CLAIM_BINDINGS.json")

    # Validation 1: Every claim has a binding
    missing_bindings = markdown_claims - binding_claims
    if missing_bindings:
        for claim in sorted(missing_bindings):
            errors.append(f"Missing binding for claim: {claim}")

    # Validation 2: No orphaned bindings
    orphaned_bindings = binding_claims - markdown_claims
    if orphaned_bindings:
        for claim in sorted(orphaned_bindings):
            errors.append(f"Orphaned binding (no claim in markdown): {claim}")

    # Validation 3: Every binding has at least one test
    claims_data = bindings.get("claims", {})
    for claim_id, claim_info in claims_data.items():
        tests = claim_info.get("tests", [])
        if not tests:
            errors.append(f"Claim {claim_id} has no tests defined")

    # Validation 4: Referenced test files exist (strict mode)
    if strict:
        for claim_id, claim_info in claims_data.items():
            tests = claim_info.get("tests", [])
            for test_path in tests:
                if not validate_test_exists(test_path, project_root):
                    errors.append(f"Claim {claim_id} references non-existent test: {test_path}")

            modules = claim_info.get("modules", [])
            for module_path in modules:
                if not validate_test_exists(module_path, project_root):
                    errors.append(f"Claim {claim_id} references non-existent module: {module_path}")

    # Validation 5: Schema version present
    meta = bindings.get("meta", {})
    if not meta.get("version"):
        errors.append("CLAIM_BINDINGS.json missing meta.version")

    # Summary
    if errors:
        messages.extend(errors)
        messages.append(f"\n❌ VALIDATION FAILED: {len(errors)} error(s)")
        return False, messages
    else:
        messages.append("\n✓ All claim bindings validated")
        return True, messages


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate claim bindings for CI guardrail",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/validate_claim_bindings.py
    python scripts/validate_claim_bindings.py --strict

Exit Codes:
    0 - All validations passed
    1 - Validation failures detected
    2 - Configuration or file errors
""",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (validate test file existence)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (auto-detected if not specified)",
    )

    args = parser.parse_args()

    project_root = args.project_root or find_project_root()

    print("=" * 60)
    print("CLAIM BINDING VALIDATION")
    print("PAC-DAN-CLAIMS-BINDING-02")
    print("=" * 60)
    print(f"Project root: {project_root}")
    print(f"Strict mode: {args.strict}")
    print("-" * 60)

    try:
        success, messages = validate_bindings(project_root, strict=args.strict)

        for msg in messages:
            print(msg)

        return 0 if success else 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
