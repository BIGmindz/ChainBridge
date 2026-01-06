"""
OCC v1.x Constitutional File Integrity

PAC: PAC-OCC-P06
Lane: 5 — Governance Reinforcement
Agent: ALEX (GID-08) — Governance Enforcement

Implements CI/CD checks for constitutional file integrity.
Addresses P04A finding: "Amendment protection is convention-based".

Invariant: INV-OCC-CONST-001 — Constitutional files require elevated review
Invariant: INV-OCC-CONST-002 — Unauthorized changes trigger CI failure
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTITUTIONAL FILE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Files that constitute the governance framework
CONSTITUTIONAL_FILES = {
    # Core governance documents
    "docs/OCC_v1_CONSTITUTION.md": "OCC Constitution",
    "docs/GOVERNANCE.md": "Governance Framework",
    "docs/REPO_CONTRACT.md": "Repository Contract",
    # Governance directives
    "core/benson_execution/directives/ber_requirement.yaml": "BER Requirement Directive",
    "core/benson_execution/directives/benson_jeffrey_contract.yaml": "Benson-Jeffrey Contract",
    # Schemas
    "schemas/CHAINBRIDGE_PAC_UPLOAD_SCHEMA_v1.0.0.json": "PAC Upload Schema",
    "schemas/PAC_REJECTION_CODES.yaml": "PAC Rejection Codes",
    # ALEX rules
    ".github/ALEX_RULES.json": "ALEX Governance Rules",
}

# Files that are protected but can be modified with justification
PROTECTED_FILES = {
    "core/occ/auth/operator_auth.py": "Operator Authentication",
    "core/occ/store/kill_switch.py": "Kill Switch Implementation",
    "core/benson_execution/preflight_gates.py": "Preflight Gates",
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class FileIntegrity:
    """Integrity record for a file."""

    path: str
    sha256: str
    recorded_at: str
    classification: str  # CONSTITUTIONAL | PROTECTED | STANDARD
    description: str = ""


@dataclass
class IntegrityViolation:
    """Record of an integrity violation."""

    path: str
    violation_type: str  # MODIFIED | DELETED | ADDED
    expected_hash: Optional[str]
    actual_hash: Optional[str]
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class IntegrityReport:
    """Report of integrity check results."""

    passed: bool
    violations: List[IntegrityViolation]
    files_checked: int
    constitutional_files_ok: int
    protected_files_ok: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRITY CHECKER
# ═══════════════════════════════════════════════════════════════════════════════


class ConstitutionalIntegrityChecker:
    """
    Checks integrity of constitutional and protected files.

    For use in:
    - CI/CD pipelines
    - Pre-commit hooks
    - Runtime verification
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        """
        Initialize the integrity checker.

        Args:
            repo_root: Root directory of the repository.
                       If None, uses current working directory.
        """
        self._repo_root = repo_root or Path.cwd()
        self._baseline: Dict[str, FileIntegrity] = {}

    def compute_hash(self, filepath: Path) -> Optional[str]:
        """Compute SHA-256 hash of a file."""
        try:
            with open(filepath, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error hashing {filepath}: {e}")
            return None

    def create_baseline(self) -> Dict[str, FileIntegrity]:
        """
        Create integrity baseline for all constitutional and protected files.

        Returns:
            Dict mapping file paths to their integrity records
        """
        baseline = {}
        now = datetime.now(timezone.utc).isoformat()

        # Constitutional files
        for rel_path, description in CONSTITUTIONAL_FILES.items():
            filepath = self._repo_root / rel_path
            sha256 = self.compute_hash(filepath)
            if sha256:
                baseline[rel_path] = FileIntegrity(
                    path=rel_path,
                    sha256=sha256,
                    recorded_at=now,
                    classification="CONSTITUTIONAL",
                    description=description,
                )

        # Protected files
        for rel_path, description in PROTECTED_FILES.items():
            filepath = self._repo_root / rel_path
            sha256 = self.compute_hash(filepath)
            if sha256:
                baseline[rel_path] = FileIntegrity(
                    path=rel_path,
                    sha256=sha256,
                    recorded_at=now,
                    classification="PROTECTED",
                    description=description,
                )

        self._baseline = baseline
        return baseline

    def load_baseline(self, filepath: Path) -> bool:
        """
        Load baseline from a JSON file.

        Args:
            filepath: Path to baseline JSON file

        Returns:
            True if loaded successfully
        """
        try:
            with open(filepath) as f:
                data = json.load(f)

            self._baseline = {
                path: FileIntegrity(**record)
                for path, record in data.items()
            }
            return True
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            return False

    def save_baseline(self, filepath: Path) -> bool:
        """
        Save baseline to a JSON file.

        Args:
            filepath: Path to save baseline

        Returns:
            True if saved successfully
        """
        try:
            data = {
                path: {
                    "path": record.path,
                    "sha256": record.sha256,
                    "recorded_at": record.recorded_at,
                    "classification": record.classification,
                    "description": record.description,
                }
                for path, record in self._baseline.items()
            }

            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
            return False

    def check_integrity(self) -> IntegrityReport:
        """
        Check current file integrity against baseline.

        Returns:
            IntegrityReport with violations
        """
        if not self._baseline:
            # Create baseline if not loaded
            self.create_baseline()

        violations = []
        constitutional_ok = 0
        protected_ok = 0

        for rel_path, baseline_record in self._baseline.items():
            filepath = self._repo_root / rel_path
            current_hash = self.compute_hash(filepath)

            if current_hash is None:
                # File deleted
                violations.append(
                    IntegrityViolation(
                        path=rel_path,
                        violation_type="DELETED",
                        expected_hash=baseline_record.sha256,
                        actual_hash=None,
                    )
                )
            elif current_hash != baseline_record.sha256:
                # File modified
                violations.append(
                    IntegrityViolation(
                        path=rel_path,
                        violation_type="MODIFIED",
                        expected_hash=baseline_record.sha256,
                        actual_hash=current_hash,
                    )
                )
            else:
                # File OK
                if baseline_record.classification == "CONSTITUTIONAL":
                    constitutional_ok += 1
                else:
                    protected_ok += 1

        return IntegrityReport(
            passed=len(violations) == 0,
            violations=violations,
            files_checked=len(self._baseline),
            constitutional_files_ok=constitutional_ok,
            protected_files_ok=protected_ok,
        )

    def check_file(self, rel_path: str) -> Optional[IntegrityViolation]:
        """
        Check integrity of a single file.

        Args:
            rel_path: Relative path from repo root

        Returns:
            IntegrityViolation if file is violated, None otherwise
        """
        baseline_record = self._baseline.get(rel_path)
        if not baseline_record:
            # File not in baseline - check if it should be
            if rel_path in CONSTITUTIONAL_FILES or rel_path in PROTECTED_FILES:
                return IntegrityViolation(
                    path=rel_path,
                    violation_type="ADDED",
                    expected_hash=None,
                    actual_hash=self.compute_hash(self._repo_root / rel_path),
                )
            return None

        filepath = self._repo_root / rel_path
        current_hash = self.compute_hash(filepath)

        if current_hash is None:
            return IntegrityViolation(
                path=rel_path,
                violation_type="DELETED",
                expected_hash=baseline_record.sha256,
                actual_hash=None,
            )

        if current_hash != baseline_record.sha256:
            return IntegrityViolation(
                path=rel_path,
                violation_type="MODIFIED",
                expected_hash=baseline_record.sha256,
                actual_hash=current_hash,
            )

        return None

    def is_constitutional_file(self, rel_path: str) -> bool:
        """Check if a file is classified as constitutional."""
        return rel_path in CONSTITUTIONAL_FILES

    def is_protected_file(self, rel_path: str) -> bool:
        """Check if a file is classified as protected."""
        return rel_path in PROTECTED_FILES


# ═══════════════════════════════════════════════════════════════════════════════
# CI/CD INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════


def run_ci_check(
    repo_root: Optional[Path] = None,
    baseline_path: Optional[Path] = None,
    fail_on_violation: bool = True,
) -> int:
    """
    Run integrity check for CI/CD pipeline.

    Args:
        repo_root: Repository root directory
        baseline_path: Path to baseline file
        fail_on_violation: Exit with error code on violation

    Returns:
        Exit code (0 = pass, 1 = fail)
    """
    checker = ConstitutionalIntegrityChecker(repo_root)

    # Load or create baseline
    if baseline_path and baseline_path.exists():
        checker.load_baseline(baseline_path)
    else:
        checker.create_baseline()

    # Run check
    report = checker.check_integrity()

    # Output results
    print("=" * 60)
    print("CONSTITUTIONAL INTEGRITY CHECK")
    print("=" * 60)
    print(f"Files checked: {report.files_checked}")
    print(f"Constitutional files OK: {report.constitutional_files_ok}")
    print(f"Protected files OK: {report.protected_files_ok}")
    print(f"Violations: {len(report.violations)}")

    if report.violations:
        print("\nVIOLATIONS DETECTED:")
        for v in report.violations:
            classification = "CONSTITUTIONAL" if checker.is_constitutional_file(v.path) else "PROTECTED"
            print(f"  [{classification}] {v.path}")
            print(f"    Type: {v.violation_type}")
            if v.expected_hash:
                print(f"    Expected: {v.expected_hash[:16]}...")
            if v.actual_hash:
                print(f"    Actual: {v.actual_hash[:16]}...")

    print("=" * 60)
    print(f"RESULT: {'PASS' if report.passed else 'FAIL'}")
    print("=" * 60)

    if fail_on_violation and not report.passed:
        return 1
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-COMMIT HOOK
# ═══════════════════════════════════════════════════════════════════════════════


def check_changed_files(changed_files: List[str]) -> List[IntegrityViolation]:
    """
    Check if any changed files require elevated review.

    For use in pre-commit hooks or PR checks.

    Args:
        changed_files: List of changed file paths

    Returns:
        List of violations requiring review
    """
    violations = []

    for filepath in changed_files:
        # Normalize path
        rel_path = filepath.lstrip("./")

        if rel_path in CONSTITUTIONAL_FILES:
            violations.append(
                IntegrityViolation(
                    path=rel_path,
                    violation_type="CONSTITUTIONAL_CHANGE",
                    expected_hash=None,
                    actual_hash=None,
                )
            )

        elif rel_path in PROTECTED_FILES:
            violations.append(
                IntegrityViolation(
                    path=rel_path,
                    violation_type="PROTECTED_CHANGE",
                    expected_hash=None,
                    actual_hash=None,
                )
            )

    return violations


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "CONSTITUTIONAL_FILES",
    "PROTECTED_FILES",
    "FileIntegrity",
    "IntegrityViolation",
    "IntegrityReport",
    "ConstitutionalIntegrityChecker",
    "run_ci_check",
    "check_changed_files",
]


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    exit_code = run_ci_check()
    sys.exit(exit_code)
