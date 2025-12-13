"""
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
ALEX — GID-08 — GOVERNANCE ENGINE
PAC-ALEX-NEXT-023: Multi-Service Compliance Alignment
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪

Forbidden Regions Check Tests
CRITICAL: Any file move before ATLAS delivers Move Matrix → BLOCK PR

This module enforces the "no file moves without Move Matrix" rule:
- Files cannot be moved/renamed without ATLAS approval
- Move Matrix must be delivered before any restructuring
- Blocks PRs that attempt unauthorized file movements
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pytest

# =============================================================================
# FORBIDDEN REGIONS CONFIGURATION
# =============================================================================

# Files/directories that require ATLAS Move Matrix before any restructuring
FORBIDDEN_REGIONS: Dict[str, Dict] = {
    "core": {
        "description": "Core trading logic and bot infrastructure",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
    "modules": {
        "description": "Pluggable trading modules",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
    "src": {
        "description": "Source code directory",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
    "chainpay-service": {
        "description": "ChainPay payment service",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
    "chainiq-service": {
        "description": "ChainIQ ML service",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
    "chainboard-ui": {
        "description": "ChainBoard UI application",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
    "ChainBridge": {
        "description": "Legacy ChainBridge directory",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
    "api": {
        "description": "API server code",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
    "strategies": {
        "description": "Trading strategies",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
    "tests": {
        "description": "Test suites",
        "requires_matrix": True,
        "owner": "ATLAS",
        "gid": "GID-05",
    },
}

# Critical files that can NEVER be moved without explicit approval
CRITICAL_FILES: Set[str] = {
    "main.py",
    "config.yaml",
    "requirements.txt",
    "pyproject.toml",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    ".github/ALEX_RULES.json",
    ".github/agents/colors.json",
}

# Move Matrix approval format
MOVE_MATRIX_PATTERN = re.compile(r"ATLAS-MOVE-MATRIX-\d{4}-\d{2}-\d{2}", re.IGNORECASE)


# =============================================================================
# MOVE MATRIX VALIDATION
# =============================================================================


class MoveMatrix:
    """
    Represents an ATLAS-approved Move Matrix document.
    """

    def __init__(self, matrix_id: str, approved_moves: List[Dict], expires: str):
        self.matrix_id = matrix_id
        self.approved_moves = approved_moves
        self.expires = datetime.fromisoformat(expires)

    def is_valid(self) -> bool:
        """Check if matrix is still valid (not expired)."""
        return datetime.now() < self.expires

    def is_move_approved(self, source: str, destination: str) -> bool:
        """Check if a specific file move is approved by this matrix."""
        for move in self.approved_moves:
            if move["source"] == source and move["destination"] == destination:
                return True
            # Also check wildcard patterns
            if "*" in move["source"]:
                pattern = move["source"].replace("*", ".*")
                if re.match(pattern, source):
                    return True
        return False


def load_move_matrix(filepath: str = "docs/governance/ATLAS_MOVE_MATRIX.json") -> Optional[MoveMatrix]:
    """
    Load the current Move Matrix from file.
    Returns None if no matrix exists.
    """
    path = Path(filepath)
    if not path.exists():
        return None

    try:
        with open(path) as f:
            data = json.load(f)
        return MoveMatrix(matrix_id=data["matrix_id"], approved_moves=data["approved_moves"], expires=data["expires"])
    except (json.JSONDecodeError, KeyError):
        return None


def detect_file_moves(changed_files: List[str], git_diff_output: str) -> List[Tuple[str, str]]:
    """
    Detect file moves/renames from git diff output.
    Returns list of (source, destination) tuples.
    """
    moves = []

    # Normalize line endings and whitespace
    normalized = re.sub(r"\r\n", "\n", git_diff_output)

    # Pattern for git rename detection (handles whitespace variations)
    rename_pattern = re.compile(r"rename from\s+(.+?)\s*\n\s*rename to\s+(.+?)(?:\n|$)")

    for match in rename_pattern.finditer(normalized):
        source = match.group(1).strip()
        destination = match.group(2).strip()
        moves.append((source, destination))

    # Also check for similarity-based detection
    similarity_pattern = re.compile(r"similarity index \d+%\s*\n\s*rename from\s+(.+?)\s*\n\s*rename to\s+(.+?)(?:\n|$)")

    for match in similarity_pattern.finditer(git_diff_output):
        source = match.group(1)
        destination = match.group(2)
        if (source, destination) not in moves:
            moves.append((source, destination))

    return moves


def is_forbidden_region(filepath: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a filepath is in a forbidden region.
    Returns (is_forbidden, region_name).
    """
    path_parts = filepath.replace("\\", "/").split("/")

    for region in FORBIDDEN_REGIONS.keys():
        if filepath.startswith(region) or region in path_parts:
            return True, region

    return False, None


def is_critical_file(filepath: str) -> bool:
    """Check if filepath is a critical file."""
    filename = Path(filepath).name
    return filename in CRITICAL_FILES or filepath in CRITICAL_FILES


def validate_file_moves(moves: List[Tuple[str, str]], move_matrix: Optional[MoveMatrix] = None) -> List[str]:
    """
    Validate all file moves against forbidden regions and Move Matrix.
    Returns list of violations.
    """
    violations = []

    for source, destination in moves:
        # Check critical files
        if is_critical_file(source):
            if move_matrix and move_matrix.is_valid() and move_matrix.is_move_approved(source, destination):
                continue
            violations.append(f"❌ BLOCKED: Critical file '{source}' cannot be moved without ATLAS approval")
            continue

        # Check forbidden regions
        source_forbidden, source_region = is_forbidden_region(source)
        dest_forbidden, dest_region = is_forbidden_region(destination)

        if source_forbidden or dest_forbidden:
            if move_matrix and move_matrix.is_valid():
                if move_matrix.is_move_approved(source, destination):
                    continue

            region = source_region or dest_region
            violations.append(
                f"❌ BLOCKED: File move '{source}' → '{destination}' in forbidden region '{region}'. "
                f"Requires ATLAS Move Matrix approval."
            )

    return violations


# =============================================================================
# PR VALIDATION
# =============================================================================


def validate_pr_for_moves(git_diff_output: str, pr_description: str, changed_files: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate a PR for unauthorized file moves.
    Returns (passed, violations).
    """
    violations = []

    # Detect file moves
    moves = detect_file_moves(changed_files, git_diff_output)

    if not moves:
        return True, []

    # Check for Move Matrix reference in PR
    has_matrix_reference = MOVE_MATRIX_PATTERN.search(pr_description) is not None

    # Load Move Matrix if referenced
    move_matrix = load_move_matrix() if has_matrix_reference else None

    # Validate moves
    move_violations = validate_file_moves(moves, move_matrix)
    violations.extend(move_violations)

    # Generate summary
    if violations:
        violations.insert(0, f"⚪ ALEX GOVERNANCE: {len(violations)} file move violation(s) detected")
        violations.append("")
        violations.append("To resolve:")
        violations.append("1. Request Move Matrix from ATLAS (GID-05)")
        violations.append("2. Include ATLAS-MOVE-MATRIX-YYYY-MM-DD reference in PR description")
        violations.append("3. Ensure all moves are listed in approved_moves")

    return len(violations) == 0, violations


# =============================================================================
# PYTEST TEST CASES
# =============================================================================


class TestForbiddenRegions:
    """Test forbidden region detection."""

    @pytest.mark.parametrize(
        "filepath,expected_forbidden",
        [
            ("core/trading_engine.py", True),
            ("modules/risk_manager.py", True),
            ("src/utils/helpers.py", True),
            ("chainpay-service/app/main.py", True),
            ("chainiq-service/app/ml/model.py", True),
            ("chainboard-ui/src/App.tsx", True),
            ("tests/test_main.py", True),
            ("docs/README.md", False),
            ("random_file.txt", False),
        ],
    )
    def test_forbidden_region_detection(self, filepath, expected_forbidden):
        is_forbidden, _ = is_forbidden_region(filepath)
        assert is_forbidden == expected_forbidden

    def test_forbidden_region_returns_region_name(self):
        is_forbidden, region = is_forbidden_region("modules/signal_aggregator.py")
        assert is_forbidden is True
        assert region == "modules"


class TestCriticalFiles:
    """Test critical file detection."""

    @pytest.mark.parametrize(
        "filepath,expected_critical",
        [
            ("main.py", True),
            ("config.yaml", True),
            ("requirements.txt", True),
            ("pyproject.toml", True),
            ("Makefile", True),
            ("Dockerfile", True),
            ("docker-compose.yml", True),
            (".github/ALEX_RULES.json", True),
            (".github/agents/colors.json", True),
            ("random_script.py", False),
            ("src/utils.py", False),
        ],
    )
    def test_critical_file_detection(self, filepath, expected_critical):
        assert is_critical_file(filepath) == expected_critical


class TestFileMoveDetection:
    """Test file move detection from git diff."""

    def test_detect_simple_rename(self):
        diff_output = """
        diff --git a/old_name.py b/new_name.py
        similarity index 95%
        rename from old_name.py
        rename to new_name.py
        """
        moves = detect_file_moves([], diff_output)
        assert len(moves) == 1
        assert moves[0] == ("old_name.py", "new_name.py")

    def test_detect_directory_move(self):
        diff_output = """
        rename from src/utils/helper.py
        rename to core/utils/helper.py
        """
        moves = detect_file_moves([], diff_output)
        assert len(moves) == 1
        assert moves[0] == ("src/utils/helper.py", "core/utils/helper.py")

    def test_detect_multiple_moves(self):
        diff_output = """
        rename from file1.py
        rename to new_file1.py
        rename from file2.py
        rename to new_file2.py
        """
        moves = detect_file_moves([], diff_output)
        assert len(moves) == 2


class TestMoveMatrixValidation:
    """Test Move Matrix approval validation."""

    @pytest.fixture
    def valid_matrix(self):
        return MoveMatrix(
            matrix_id="ATLAS-MOVE-MATRIX-2025-12-11",
            approved_moves=[
                {"source": "src/old.py", "destination": "core/new.py"},
                {"source": "modules/*", "destination": "src/modules/*"},
            ],
            expires="2025-12-31T23:59:59",
        )

    def test_matrix_approves_explicit_move(self, valid_matrix):
        assert valid_matrix.is_move_approved("src/old.py", "core/new.py") is True

    def test_matrix_approves_wildcard_move(self, valid_matrix):
        assert valid_matrix.is_move_approved("modules/risk.py", "src/modules/risk.py") is True

    def test_matrix_rejects_unapproved_move(self, valid_matrix):
        assert valid_matrix.is_move_approved("random.py", "other.py") is False

    def test_expired_matrix_invalid(self):
        expired = MoveMatrix(matrix_id="ATLAS-MOVE-MATRIX-2024-01-01", approved_moves=[], expires="2024-01-02T00:00:00")
        assert expired.is_valid() is False


class TestMoveViolations:
    """Test move validation returns violations."""

    def test_moves_in_forbidden_region_blocked(self):
        moves = [("modules/old.py", "modules/new.py")]
        violations = validate_file_moves(moves)
        assert len(violations) > 0
        assert "BLOCKED" in violations[0]

    def test_critical_file_move_blocked(self):
        moves = [("main.py", "src/main.py")]
        violations = validate_file_moves(moves)
        assert len(violations) > 0
        assert "BLOCKED" in violations[0]

    def test_approved_move_passes(self):
        matrix = MoveMatrix(
            matrix_id="ATLAS-MOVE-MATRIX-2025-12-11",
            approved_moves=[{"source": "modules/old.py", "destination": "src/old.py"}],
            expires="2099-12-31T23:59:59",
        )
        moves = [("modules/old.py", "src/old.py")]
        violations = validate_file_moves(moves, matrix)
        assert len(violations) == 0


class TestPRValidation:
    """Test full PR validation."""

    def test_pr_without_moves_passes(self):
        passed, violations = validate_pr_for_moves("", "", [])
        assert passed is True
        assert len(violations) == 0

    def test_pr_with_unapproved_moves_fails(self):
        diff_output = """
        rename from modules/risk.py
        rename to core/risk.py
        """
        passed, violations = validate_pr_for_moves(diff_output, "Simple PR", [])
        assert passed is False
        assert "BLOCKED" in str(violations)

    def test_pr_with_matrix_reference_format(self):
        # Test that the matrix reference pattern is detected
        pr_body = "This PR implements ATLAS-MOVE-MATRIX-2025-12-11 changes"
        assert MOVE_MATRIX_PATTERN.search(pr_body) is not None


class TestGovernanceCompliance:
    """Test governance compliance scenarios."""

    def test_alex_cannot_override_atlas_moves(self):
        """Even ALEX (Governance) cannot move files without ATLAS approval."""
        moves = [("core/engine.py", "src/engine.py")]
        # Simulate ALEX trying to move without matrix
        violations = validate_file_moves(moves, move_matrix=None)
        assert len(violations) > 0

    def test_forbidden_regions_comprehensive(self):
        """All forbidden regions must block unauthorized moves."""
        for region in FORBIDDEN_REGIONS.keys():
            moves = [(f"{region}/test.py", "new_location/test.py")]
            violations = validate_file_moves(moves)
            assert len(violations) > 0, f"Region {region} should block unauthorized moves"


# =============================================================================
# FOOTER
# ⚪ ALEX — GID-08 — GOVERNANCE ENGINE
# Ensuring absolute alignment.
# ⚪⚪⚪ END OF PAC ⚪⚪⚪
# =============================================================================
