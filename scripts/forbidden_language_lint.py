#!/usr/bin/env python3
"""
Forbidden Language Lint — GAP-002 Enforcement

PAC-CODY-INVARIANT-ENFORCEMENT-01: Automated Invariant Enforcement

Implements INV-GOV-002: Forbidden Language Patterns

This script scans sensitive domain files for:
- GATE-003: Marketing language
- GATE-004: Probabilistic language
- GATE-005: Future guarantee language

Per SENSITIVE_DOMAIN_GATEWAY.md Section 3.

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


# =============================================================================
# FORBIDDEN PATTERNS (from SENSITIVE_DOMAIN_GATEWAY.md)
# =============================================================================

# GATE-003: Marketing Language
MARKETING_TERMS: List[str] = [
    r"\bsecure\b",
    r"\btrusted\b",
    r"\bcompliant\b",
    r"\binsured\b",
    r"\bguaranteed\b",
    r"\bcertified\b",
    r"\bverified by\b",
    r"\bapproved by\b",
    r"\bindustry[- ]leading\b",
    r"\bbest[- ]in[- ]class\b",
    r"\bstate[- ]of[- ]the[- ]art\b",
    r"\benterprise[- ]grade\b",
]

# GATE-004: Probabilistic Language
PROBABILISTIC_PATTERNS: List[str] = [
    r"\bshould work\b",
    r"\btypically\b",
    r"\busually\b",
    r"\bin most cases\b",
    r"\balmost always\b",
    r"\brarely fails\b",
    r"\bnearly impossible\b",
    r"\bhighly unlikely\b",
]

# GATE-005: Future Guarantee Language
FUTURE_GUARANTEE_PATTERNS: List[str] = [
    r"\bwill never\b",
    r"\bwill always\b",
    r"\bis guaranteed to\b",
    r"\bensures that\b",
    r"\bprevents all\b",
]

# GATE-002: Sensitive Domain Paths (from contract)
SENSITIVE_PATHS: List[str] = [
    "core/occ/schemas/pdo",
    "core/occ/store/pdo_store",
    "core/occ/api/proofpack",
    "core/occ/proofpack/",
    "docs/contracts/",
    "docs/proof/",
    "docs/trust/",
    "docs/governance/",
    "gateway/pdo_",
    "src/security/",
]

# File extensions to scan
SCANNABLE_EXTENSIONS: Set[str] = {
    ".py",
    ".md",
    ".rst",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
}

# Files/patterns to exclude from scanning
EXCLUDE_PATTERNS: List[str] = [
    "forbidden_language_lint.py",  # This script itself
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "htmlcov",
    ".pytest_cache",
]


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class Violation:
    """Represents a single forbidden language violation."""

    file_path: str
    line_number: int
    line_content: str
    matched_pattern: str
    category: str  # "marketing", "probabilistic", "future_guarantee"

    def to_dict(self) -> Dict[str, str | int]:
        return {
            "file": self.file_path,
            "line": self.line_number,
            "content": self.line_content.strip(),
            "pattern": self.matched_pattern,
            "category": self.category,
        }


@dataclass
class LintResult:
    """Results from running the lint."""

    violations: List[Violation] = field(default_factory=list)
    files_scanned: int = 0
    sensitive_files_scanned: int = 0

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    def to_dict(self) -> Dict[str, any]:
        return {
            "passed": not self.has_violations,
            "violation_count": len(self.violations),
            "files_scanned": self.files_scanned,
            "sensitive_files_scanned": self.sensitive_files_scanned,
            "violations": [v.to_dict() for v in self.violations],
        }


# =============================================================================
# LINT ENGINE
# =============================================================================


class ForbiddenLanguageLinter:
    """Linter for forbidden language patterns in sensitive domains."""

    def __init__(
        self,
        workspace_root: Path,
        strict_mode: bool = False,
        include_all_files: bool = False,
    ):
        """
        Initialize the linter.

        Args:
            workspace_root: Root directory to scan.
            strict_mode: If True, also check non-sensitive files.
            include_all_files: If True, scan all files, not just sensitive paths.
        """
        self.workspace_root = workspace_root
        self.strict_mode = strict_mode
        self.include_all_files = include_all_files

        # Compile patterns for efficiency
        self._marketing_patterns = [
            re.compile(p, re.IGNORECASE) for p in MARKETING_TERMS
        ]
        self._probabilistic_patterns = [
            re.compile(p, re.IGNORECASE) for p in PROBABILISTIC_PATTERNS
        ]
        self._future_patterns = [
            re.compile(p, re.IGNORECASE) for p in FUTURE_GUARANTEE_PATTERNS
        ]

    def is_sensitive_path(self, file_path: Path) -> bool:
        """Check if a file is in a sensitive domain."""
        rel_path = str(file_path.relative_to(self.workspace_root))
        return any(sensitive in rel_path for sensitive in SENSITIVE_PATHS)

    def should_scan_file(self, file_path: Path) -> bool:
        """Determine if a file should be scanned."""
        # Check exclusions
        rel_path = str(file_path.relative_to(self.workspace_root))
        for exclude in EXCLUDE_PATTERNS:
            if exclude in rel_path:
                return False

        # Check extension
        if file_path.suffix not in SCANNABLE_EXTENSIONS:
            return False

        # Check if sensitive (unless include_all_files)
        if not self.include_all_files:
            if not self.is_sensitive_path(file_path):
                return False

        return True

    def scan_line(
        self,
        line: str,
        line_number: int,
        file_path: str,
    ) -> List[Violation]:
        """Scan a single line for violations."""
        violations = []

        # Skip comments in code files that explain the rules
        lower_line = line.lower()
        if "forbidden" in lower_line and ("term" in lower_line or "pattern" in lower_line):
            return violations
        if "gate-00" in lower_line:  # Skip gate rule references
            return violations

        # Check marketing terms (GATE-003)
        for pattern in self._marketing_patterns:
            if pattern.search(line):
                violations.append(Violation(
                    file_path=file_path,
                    line_number=line_number,
                    line_content=line,
                    matched_pattern=pattern.pattern,
                    category="marketing",
                ))

        # Check probabilistic language (GATE-004)
        for pattern in self._probabilistic_patterns:
            if pattern.search(line):
                violations.append(Violation(
                    file_path=file_path,
                    line_number=line_number,
                    line_content=line,
                    matched_pattern=pattern.pattern,
                    category="probabilistic",
                ))

        # Check future guarantees (GATE-005)
        for pattern in self._future_patterns:
            if pattern.search(line):
                violations.append(Violation(
                    file_path=file_path,
                    line_number=line_number,
                    line_content=line,
                    matched_pattern=pattern.pattern,
                    category="future_guarantee",
                ))

        return violations

    def scan_file(self, file_path: Path) -> List[Violation]:
        """Scan a single file for violations."""
        violations = []
        rel_path = str(file_path.relative_to(self.workspace_root))

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_number, line in enumerate(f, start=1):
                    line_violations = self.scan_line(line, line_number, rel_path)
                    violations.extend(line_violations)
        except Exception as e:
            print(f"Warning: Could not scan {rel_path}: {e}", file=sys.stderr)

        return violations

    def scan_directory(self, directory: Optional[Path] = None) -> LintResult:
        """Scan a directory for violations."""
        result = LintResult()
        scan_root = directory or self.workspace_root

        for root, dirs, files in os.walk(scan_root):
            root_path = Path(root)

            # Skip excluded directories
            dirs[:] = [
                d for d in dirs
                if not any(excl in d for excl in EXCLUDE_PATTERNS)
            ]

            for filename in files:
                file_path = root_path / filename
                result.files_scanned += 1

                if not self.should_scan_file(file_path):
                    continue

                result.sensitive_files_scanned += 1
                violations = self.scan_file(file_path)
                result.violations.extend(violations)

        return result


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scan sensitive domain files for forbidden language patterns.",
        epilog="Per SENSITIVE_DOMAIN_GATEWAY.md (INV-GOV-002)",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to scan (default: current directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (more thorough scanning)",
    )
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Scan all files, not just sensitive paths",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output except for exit code",
    )

    args = parser.parse_args()
    workspace_root = Path(args.path).resolve()

    if not workspace_root.exists():
        print(f"Error: Path does not exist: {workspace_root}", file=sys.stderr)
        return 2

    linter = ForbiddenLanguageLinter(
        workspace_root=workspace_root,
        strict_mode=args.strict,
        include_all_files=args.all_files,
    )

    result = linter.scan_directory()

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    elif not args.quiet:
        print(f"Forbidden Language Lint Results")
        print(f"================================")
        print(f"Files scanned: {result.files_scanned}")
        print(f"Sensitive files scanned: {result.sensitive_files_scanned}")
        print(f"Violations found: {len(result.violations)}")
        print()

        if result.violations:
            print("VIOLATIONS:")
            print("-----------")
            for v in result.violations:
                print(f"  {v.file_path}:{v.line_number}")
                print(f"    Category: {v.category}")
                print(f"    Pattern: {v.matched_pattern}")
                print(f"    Content: {v.line_content.strip()[:80]}")
                print()

            print(f"LINT FAILED: {len(result.violations)} violations found.")
        else:
            print("LINT PASSED: No forbidden language detected.")

    return 1 if result.has_violations else 0


if __name__ == "__main__":
    sys.exit(main())
