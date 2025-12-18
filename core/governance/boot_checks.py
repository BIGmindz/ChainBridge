"""
Governance Boot Checks — Fail-Fast Enforcement

PAC-GOV-GUARD-01: Governance root file validation.

This module enforces presence and validity of critical governance files
BEFORE any governance evaluation, test execution, or CI pipeline proceeds.

Enforcement Principles:
- Fail Closed: Any violation raises GovernanceBootError
- No Warnings: Violations are hard stops, not logs
- No Defaults: Missing data is never inferred
- Deterministic: Same input → same error message

Validated Files:
- config/agents.json (CALP agent registry)
- .github/ALEX_RULES.json (ALEX hard constraints)

Author: ATLAS (GID-11)
Authority: Repository Integrity, Governance Artifacts
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from core.governance.event_sink import emit_event

# Telemetry import (PAC-GOV-OBS-01)
from core.governance.events import governance_boot_event

# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION
# ═══════════════════════════════════════════════════════════════════════════════


class GovernanceBootError(RuntimeError):
    """
    Raised when governance root files are missing, unreadable, or malformed.

    This exception halts startup, tests, and CI.
    It is NEVER caught silently — it indicates a fatal governance state.
    """

    def __init__(self, file_path: str, reason: str) -> None:
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"GOVERNANCE BOOT FAILURE: {file_path} — {reason}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Governance root files (relative to repository root)
GOVERNANCE_FILES: Final[dict[str, dict[str, Any]]] = {
    "config/agents.json": {
        "description": "CALP Agent Registry",
        "required_fields": ["calp_version"],
        "allow_list": False,  # Must be object with version
    },
    ".github/ALEX_RULES.json": {
        "description": "ALEX Governance Hard Constraints",
        "required_fields": ["governance_id", "version"],
        "allow_list": False,  # Must be object with version
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION RESULT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class BootCheckResult:
    """Result of a single file validation."""

    path: str
    valid: bool
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def _find_repo_root() -> Path:
    """
    Find the repository root by looking for known markers.

    Searches upward from current file location for:
    - .git directory
    - pytest.ini
    - pyproject.toml
    """
    current = Path(__file__).resolve()

    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
        if (parent / "pytest.ini").exists():
            return parent
        if (parent / "pyproject.toml").exists():
            return parent

    # Fallback: assume we're in core/governance/, go up 2 levels
    return current.parent.parent.parent


def validate_governance_file(
    file_path: str,
    repo_root: Path | None = None,
) -> BootCheckResult:
    """
    Validate a single governance file.

    Checks:
    1. File exists
    2. File is readable
    3. Content is valid JSON
    4. Content is non-empty object/list
    5. Required fields are present (for objects)

    Args:
        file_path: Relative path from repo root
        repo_root: Repository root directory (auto-detected if None)

    Returns:
        BootCheckResult with validation outcome
    """
    if repo_root is None:
        repo_root = _find_repo_root()

    full_path = repo_root / file_path
    config = GOVERNANCE_FILES.get(file_path, {})
    required_fields = config.get("required_fields", [])

    # Check 1: Existence
    if not full_path.exists():
        return BootCheckResult(
            path=file_path,
            valid=False,
            error=f"File does not exist: {full_path}",
        )

    # Check 2: Readable
    try:
        content = full_path.read_text(encoding="utf-8")
    except PermissionError:
        return BootCheckResult(
            path=file_path,
            valid=False,
            error=f"File not readable (permission denied): {full_path}",
        )
    except OSError as e:
        return BootCheckResult(
            path=file_path,
            valid=False,
            error=f"File read error: {e}",
        )

    # Check 3: Valid JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return BootCheckResult(
            path=file_path,
            valid=False,
            error=f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}",
        )

    # Check 4: Non-empty
    if data is None:
        return BootCheckResult(
            path=file_path,
            valid=False,
            error="File contains null/None",
        )

    if isinstance(data, dict) and len(data) == 0:
        return BootCheckResult(
            path=file_path,
            valid=False,
            error="File contains empty object {}",
        )

    if isinstance(data, list) and len(data) == 0:
        return BootCheckResult(
            path=file_path,
            valid=False,
            error="File contains empty array []",
        )

    # Check 5: Required fields (for objects)
    if isinstance(data, dict) and required_fields:
        missing = [f for f in required_fields if f not in data]
        if missing:
            return BootCheckResult(
                path=file_path,
                valid=False,
                error=f"Missing required fields: {', '.join(missing)}",
            )

    return BootCheckResult(path=file_path, valid=True)


def validate_all_governance_files(
    repo_root: Path | None = None,
) -> list[BootCheckResult]:
    """
    Validate all governance root files.

    Returns list of results for each file.
    Does NOT raise — caller decides whether to halt.
    """
    results = []
    for file_path in GOVERNANCE_FILES:
        result = validate_governance_file(file_path, repo_root)
        results.append(result)
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# ENFORCEMENT FUNCTION (FAIL-FAST)
# ═══════════════════════════════════════════════════════════════════════════════


def enforce_governance_boot(repo_root: Path | None = None) -> None:
    """
    Enforce governance boot checks — FAIL CLOSED.

    Validates all governance root files and raises GovernanceBootError
    on the FIRST violation encountered.

    This function should be called:
    - At application startup
    - Before governance evaluation
    - Before test execution (via conftest.py)
    - In CI governance check step

    Raises:
        GovernanceBootError: If any governance file is invalid
    """
    results = validate_all_governance_files(repo_root)

    for result in results:
        if not result.valid:
            # PAC-GOV-OBS-01: Emit telemetry before raising (fail-open on emit)
            try:
                emit_event(
                    governance_boot_event(
                        passed=False,
                        failures=[f"{result.path}: {result.error}"],
                    )
                )
            except Exception:
                pass  # Fail-open on telemetry
            raise GovernanceBootError(result.path, result.error or "Unknown error")


def check_governance_boot(repo_root: Path | None = None) -> bool:
    """
    Check governance boot status without raising.

    Returns True if all governance files are valid, False otherwise.
    Use enforce_governance_boot() for fail-fast behavior.
    """
    results = validate_all_governance_files(repo_root)
    return all(r.valid for r in results)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE: Get governance file info
# ═══════════════════════════════════════════════════════════════════════════════


def get_governance_files() -> dict[str, dict[str, Any]]:
    """Return the governance file configuration (read-only copy)."""
    return dict(GOVERNANCE_FILES)


def get_governance_status(repo_root: Path | None = None) -> dict[str, Any]:
    """
    Get detailed governance boot status.

    Returns a dictionary with:
    - overall_valid: bool
    - files: list of file statuses
    - error_count: int
    """
    results = validate_all_governance_files(repo_root)

    return {
        "overall_valid": all(r.valid for r in results),
        "files": [
            {
                "path": r.path,
                "valid": r.valid,
                "error": r.error,
                "description": GOVERNANCE_FILES.get(r.path, {}).get("description", "Unknown"),
            }
            for r in results
        ],
        "error_count": sum(1 for r in results if not r.valid),
    }
