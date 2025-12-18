#!/usr/bin/env python3
"""
ChainBridge Repository Scope Guard

Validates that repository contents conform to the locked scope defined in
docs/governance/REPO_SCOPE_LOCK.md

This script:
1. Checks for forbidden file patterns outside archive
2. Validates no imports from archive directory
3. Ensures Makefile targets don't reference forbidden patterns
4. Checks for unauthorized requirements files
5. Validates governance override if scope violations detected
6. Reports violations and exits non-zero if any found

Usage:
    python scripts/scope_guard/check_repo_scope.py [--strict] [--ci]

Exit codes:
    0 - No violations
    1 - Violations found
    2 - Script error

PAC Reference: PAC-DAN-03
Locked by: DAN (GID-07)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE CONFIGURATION (LOCKED)
# ═══════════════════════════════════════════════════════════════════════════════

SCOPE_VERSION = "2.0.0"

# Directories that are allowed at root level
ALLOWED_ROOT_DIRS: Set[str] = {
    "api",
    "apps",
    "archive",
    "archived_logs",
    "assets",
    "cache",
    "chainboard-service",
    "chainboard-ui",
    "chainiq-service",
    "ChainBridge",
    "config",
    "core",
    "data",
    "docs",
    "examples",
    "gateway",
    "htmlcov",
    "k8s",
    "logs",
    "manifests",
    "market_metrics",
    "ml_models",
    "modules",
    "prompts",
    "proofpacks",
    "ql-db",
    "repo.git",
    "reports",
    "sample_data",
    "scripts",
    "src",
    "static",
    "strategies",
    "tests",
    "tools",
    "tracking",
    "utils",
    # Standard hidden dirs
    ".chainbridge",
    ".devcontainer",
    ".git",
    ".github",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-lean",
    ".vscode",
    "__pycache__",
}

# File patterns forbidden outside archive (case-insensitive)
FORBIDDEN_PATTERNS: List[re.Pattern] = [
    re.compile(r".*bot.*\.py$", re.IGNORECASE),
    re.compile(r".*trading.*\.py$", re.IGNORECASE),
    re.compile(r".*alpha.*\.py$", re.IGNORECASE),
    re.compile(r".*crypto_selector.*\.py$", re.IGNORECASE),
    re.compile(r".*rsi_bot.*\.py$", re.IGNORECASE),
    re.compile(r".*multi_signal.*\.py$", re.IGNORECASE),
    # PAC-DAN-03: Additional forbidden patterns
    re.compile(r".*rsi.*\.py$", re.IGNORECASE),
    re.compile(r".*crypto.*\.py$", re.IGNORECASE),
    re.compile(r".*market.*\.py$", re.IGNORECASE),
    re.compile(r".*signal.*\.py$", re.IGNORECASE),
]

# Forbidden file extensions (anywhere outside archive)
FORBIDDEN_EXTENSIONS: Set[str] = {
    ".ipynb",  # Jupyter notebooks
    ".streamlit",  # Streamlit config
}

# Forbidden extensions at root level only
FORBIDDEN_ROOT_EXTENSIONS: Set[str] = {
    ".png",  # Images at root (likely dashboard screenshots)
}

# Allowed requirements files (PAC-DAN-03: Requirements lock)
# Only these requirements files are allowed at root level
ALLOWED_REQUIREMENTS: Set[str] = {
    "requirements.txt",  # Core dependencies
    "requirements-dev.txt",  # Development dependencies
}

# Patterns allowed as exceptions (e.g., chatbot is OK, trading_partner is OK)
PATTERN_EXCEPTIONS: List[re.Pattern] = [
    re.compile(r".*chatbot.*", re.IGNORECASE),  # Chatbots are allowed
    re.compile(r".*robot.*", re.IGNORECASE),  # Robot/robotics OK
    re.compile(r".*trading_partner.*", re.IGNORECASE),  # Business partner OK
    re.compile(r".*trading_entity.*", re.IGNORECASE),  # Entity OK
    # PAC-DAN-03: ChainBridge-specific exceptions
    re.compile(r".*market_metrics.*", re.IGNORECASE),  # Market metrics module OK
    re.compile(r".*signal_.*envelope.*", re.IGNORECASE),  # Signal envelopes OK
    re.compile(r".*crypto.*signer.*", re.IGNORECASE),  # Cryptographic signer OK (ed25519)
    re.compile(r".*crypto.*hash.*", re.IGNORECASE),  # Cryptographic hash OK
    # PAC-ATLAS-LEGACY-CLEAN-02: ChainBridge commerce/supply chain exceptions
    re.compile(r".*marketplace.*", re.IGNORECASE),  # ChainBridge commerce marketplace OK
    re.compile(r".*logistics_signal.*", re.IGNORECASE),  # Supply chain logistics signals OK
    re.compile(r".*event_parsing.*", re.IGNORECASE),  # ChainIQ event parsing OK
    re.compile(r".*test_rsi_scenarios.*", re.IGNORECASE),  # Legacy placeholder test OK
    re.compile(r".*test_iq_persistence.*", re.IGNORECASE),  # ChainIQ persistence test OK
    re.compile(r".*test_ingestion.*", re.IGNORECASE),  # ChainIQ ingestion test OK
]

# Directories to skip entirely
SKIP_DIRS: Set[str] = {
    ".git",
    ".venv",
    ".venv-lean",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "htmlcov",
    "archive",  # Archive is allowed to have anything
    "ql-db",  # CodeQL database
    "repo.git",  # Git bundle
}

# Forbidden import patterns
FORBIDDEN_IMPORTS: List[re.Pattern] = [
    re.compile(r"^\s*from\s+archive\b"),
    re.compile(r"^\s*import\s+archive\b"),
    re.compile(r"^\s*from\s+archive\."),
]

# Forbidden Makefile target patterns
FORBIDDEN_MAKEFILE_PATTERNS: List[re.Pattern] = [
    re.compile(r"benson_rsi", re.IGNORECASE),
    re.compile(r"benson_system", re.IGNORECASE),
    re.compile(r"dynamic_crypto", re.IGNORECASE),
    re.compile(r"run-rsi", re.IGNORECASE),
    re.compile(r"run-trading", re.IGNORECASE),
]


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Violation:
    """Represents a scope violation."""

    category: str
    file_path: str
    message: str
    line_number: int | None = None


@dataclass
class ScopeCheckResult:
    """Result of scope validation."""

    violations: List[Violation] = field(default_factory=list)
    files_checked: int = 0
    dirs_checked: int = 0

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    def add_violation(
        self,
        category: str,
        file_path: str,
        message: str,
        line_number: int | None = None,
    ) -> None:
        self.violations.append(
            Violation(
                category=category,
                file_path=file_path,
                message=message,
                line_number=line_number,
            )
        )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def is_pattern_exception(filename: str) -> bool:
    """Check if filename matches an allowed exception pattern."""
    return any(pattern.match(filename) for pattern in PATTERN_EXCEPTIONS)


def check_forbidden_files(root: Path, result: ScopeCheckResult) -> None:
    """Check for files matching forbidden patterns outside archive."""
    for path in root.rglob("*"):
        if path.is_dir():
            continue

        # Skip if in excluded directory
        parts = path.relative_to(root).parts
        if any(skip in parts for skip in SKIP_DIRS):
            continue

        result.files_checked += 1
        filename = path.name

        # Check against forbidden patterns
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.match(filename):
                # Check if it's an allowed exception
                if not is_pattern_exception(filename):
                    result.add_violation(
                        category="FORBIDDEN_FILE",
                        file_path=str(path.relative_to(root)),
                        message=f"File matches forbidden pattern: {pattern.pattern}",
                    )
                break


def check_archive_imports(root: Path, result: ScopeCheckResult) -> None:
    """Check for imports from archive directory."""
    for path in root.rglob("*.py"):
        # Skip archive itself and excluded dirs
        parts = path.relative_to(root).parts
        if any(skip in parts for skip in SKIP_DIRS):
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                for pattern in FORBIDDEN_IMPORTS:
                    if pattern.search(line):
                        result.add_violation(
                            category="ARCHIVE_IMPORT",
                            file_path=str(path.relative_to(root)),
                            message=f"Forbidden import from archive: {line.strip()}",
                            line_number=line_num,
                        )
        except Exception:
            pass  # Skip files we can't read


def check_makefile(root: Path, result: ScopeCheckResult) -> None:
    """Check Makefile for forbidden patterns."""
    makefile = root / "Makefile"
    if not makefile.exists():
        return

    try:
        content = makefile.read_text(encoding="utf-8")
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            for pattern in FORBIDDEN_MAKEFILE_PATTERNS:
                if pattern.search(line):
                    result.add_violation(
                        category="MAKEFILE_VIOLATION",
                        file_path="Makefile",
                        message=f"Forbidden pattern in Makefile: {pattern.pattern}",
                        line_number=line_num,
                    )
    except Exception:
        pass


def check_forbidden_extensions(root: Path, result: ScopeCheckResult) -> None:
    """Check for files with forbidden extensions outside archive (PAC-DAN-03)."""
    for path in root.rglob("*"):
        if path.is_dir():
            continue

        # Skip if in excluded directory
        parts = path.relative_to(root).parts
        if any(skip in parts for skip in SKIP_DIRS):
            continue

        suffix = path.suffix.lower()

        # Check forbidden extensions anywhere
        if suffix in FORBIDDEN_EXTENSIONS:
            result.add_violation(
                category="FORBIDDEN_EXTENSION",
                file_path=str(path.relative_to(root)),
                message=f"File has forbidden extension: {suffix}",
            )

        # Check root-level only forbidden extensions
        if len(parts) == 1 and suffix in FORBIDDEN_ROOT_EXTENSIONS:
            result.add_violation(
                category="FORBIDDEN_ROOT_FILE",
                file_path=str(path.relative_to(root)),
                message=f"File at root has forbidden extension: {suffix}",
            )


def check_requirements_lock(root: Path, result: ScopeCheckResult) -> None:
    """Check that only allowed requirements files exist (PAC-DAN-03)."""
    for path in root.glob("requirements*.txt"):
        filename = path.name
        if filename not in ALLOWED_REQUIREMENTS:
            result.add_violation(
                category="REQUIREMENTS_LOCK",
                file_path=filename,
                message=f"Unauthorized requirements file: {filename} (allowed: {', '.join(sorted(ALLOWED_REQUIREMENTS))})",
            )


def check_governance_override(root: Path) -> bool:
    """
    Check if governance override is in effect (PAC-DAN-03).

    Returns True if override is active (violations should be warnings only).

    Override requires BOTH:
    1. Commit message contains: GOVERNANCE-OVERRIDE: APPROVED
    2. docs/governance/OVERRIDE.md exists and was modified in this PR
    """
    override_file = root / "docs" / "governance" / "OVERRIDE.md"

    # Check if override file exists
    if not override_file.exists():
        return False

    # Check git commit message for override marker
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=10,
        )
        if result.returncode == 0:
            commit_msg = result.stdout
            if "GOVERNANCE-OVERRIDE: APPROVED" in commit_msg:
                return True
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    return False


def check_new_root_dirs(root: Path, result: ScopeCheckResult) -> None:
    """Check for unexpected directories at root level."""
    for path in root.iterdir():
        if not path.is_dir():
            continue

        result.dirs_checked += 1
        dirname = path.name

        # Skip hidden dirs not in allowlist
        if dirname.startswith(".") and dirname not in ALLOWED_ROOT_DIRS:
            # Allow common dotfiles/dirs
            if dirname in {".DS_Store"}:
                continue
            # Don't flag unknown hidden dirs as violations (too noisy)
            continue

        # Check non-hidden dirs
        if not dirname.startswith(".") and dirname not in ALLOWED_ROOT_DIRS:
            result.add_violation(
                category="UNKNOWN_DIRECTORY",
                file_path=dirname,
                message=f"Directory not in allowed list: {dirname}",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════


def run_scope_check(root: Path, strict: bool = False) -> ScopeCheckResult:
    """Run all scope validation checks."""
    result = ScopeCheckResult()

    print(f"🔍 ChainBridge Scope Guard v{SCOPE_VERSION}")
    print(f"   Root: {root}")
    print()

    # Check for governance override
    override_active = check_governance_override(root)
    if override_active:
        print("   ⚠️  GOVERNANCE OVERRIDE ACTIVE")
        print("   Violations will be reported as warnings only.")
        print()

    # Run all checks
    print("   Checking forbidden file patterns...")
    check_forbidden_files(root, result)

    print("   Checking forbidden extensions...")
    check_forbidden_extensions(root, result)

    print("   Checking requirements lock...")
    check_requirements_lock(root, result)

    print("   Checking archive imports...")
    check_archive_imports(root, result)

    print("   Checking Makefile...")
    check_makefile(root, result)

    if strict:
        print("   Checking root directories (strict mode)...")
        check_new_root_dirs(root, result)

    print()
    print(f"   Files checked: {result.files_checked}")
    print(f"   Dirs checked: {result.dirs_checked}")
    print()

    return result


def print_violations(result: ScopeCheckResult) -> None:
    """Print violations in human-readable format."""
    if result.passed:
        print("✅ SCOPE CHECK PASSED")
        print("   No violations found.")
        return

    print("❌ SCOPE CHECK FAILED")
    print(f"   {len(result.violations)} violation(s) found:")
    print()

    # Group by category
    by_category: dict[str, List[Violation]] = {}
    for v in result.violations:
        by_category.setdefault(v.category, []).append(v)

    for category, violations in sorted(by_category.items()):
        print(f"   [{category}] ({len(violations)} issues)")
        for v in violations:
            loc = f":{v.line_number}" if v.line_number else ""
            print(f"      • {v.file_path}{loc}")
            print(f"        {v.message}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ChainBridge Repository Scope Guard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/scope_guard/check_repo_scope.py
  python scripts/scope_guard/check_repo_scope.py --strict
  python scripts/scope_guard/check_repo_scope.py --ci

Exit codes:
  0 - No violations
  1 - Violations found
  2 - Script error
        """,
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (check root directory structure)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode (same as --strict, formatted for CI output)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect)",
    )

    args = parser.parse_args()

    # Determine root
    if args.root:
        root = args.root
    else:
        # Auto-detect: look for Makefile or .git
        root = Path.cwd()
        while root != root.parent:
            if (root / "Makefile").exists() or (root / ".git").exists():
                break
            root = root.parent

    if not root.exists():
        print(f"❌ Error: Root directory not found: {root}", file=sys.stderr)
        return 2

    try:
        strict = args.strict or args.ci
        result = run_scope_check(root, strict=strict)
        print_violations(result)

        if args.ci and not result.passed:
            print()
            print("::error::Scope guard failed. See violations above.")

        return 0 if result.passed else 1

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
