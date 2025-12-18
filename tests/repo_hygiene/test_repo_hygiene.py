"""
Repository Hygiene Regression Tests

PAC Reference: PAC-ATLAS-REPO-HYGIENE-03

These tests are regression sentinels that fail if:
1. Makefile targets reintroduce forbidden patterns
2. Archive files become importable
3. Root-level files violate REPO_CONTRACT.md

Run with: pytest tests/repo_hygiene/ -v
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

ROOT_DIR = Path(__file__).parent.parent.parent
MAKEFILE = ROOT_DIR / "Makefile"
ARCHIVE_DIR = ROOT_DIR / "archive"

# Forbidden patterns in Makefile targets (not comments)
MAKEFILE_FORBIDDEN_TARGETS = [
    re.compile(r"^(run-rsi|rsi-bot|trading-bot|crypto-bot)\s*:", re.MULTILINE),
    re.compile(r"^(benson_rsi|benson_system|dynamic_crypto)\s*:", re.MULTILINE),
    re.compile(r"^(start_trading|run_trading|live_trade)\s*:", re.MULTILINE),
]

# Forbidden patterns in Makefile help text (not comments)
MAKEFILE_FORBIDDEN_HELP = [
    re.compile(r'@echo.*".*RSI bot.*"', re.IGNORECASE),
    re.compile(r'@echo.*".*trading bot.*"', re.IGNORECASE),
    re.compile(r'@echo.*".*crypto execution.*"', re.IGNORECASE),
    re.compile(r'@echo.*".*signal bot.*"', re.IGNORECASE),
]


# ═══════════════════════════════════════════════════════════════════════════════
# MAKEFILE REGRESSION GUARDS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMakefileRegression:
    """Regression tests for Makefile integrity."""

    def test_makefile_exists(self):
        """Makefile must exist at repository root."""
        assert MAKEFILE.exists(), "Makefile not found at repository root"

    def test_no_forbidden_targets(self):
        """Makefile must not contain forbidden target names."""
        content = MAKEFILE.read_text(encoding="utf-8")
        for pattern in MAKEFILE_FORBIDDEN_TARGETS:
            match = pattern.search(content)
            assert match is None, f"Forbidden target found: {match.group(0) if match else 'unknown'}"

    def test_no_forbidden_help_text(self):
        """Makefile help text must not reference forbidden systems."""
        content = MAKEFILE.read_text(encoding="utf-8")
        for pattern in MAKEFILE_FORBIDDEN_HELP:
            match = pattern.search(content)
            assert match is None, f"Forbidden help text found: {match.group(0) if match else 'unknown'}"

    def test_makefile_has_scope_header(self):
        """Makefile must have scope header comment."""
        content = MAKEFILE.read_text(encoding="utf-8")
        assert "ChainBridge" in content, "Makefile missing ChainBridge header"
        assert "SCOPE LOCK" in content or "scope" in content.lower(), "Makefile missing scope reference"

    def test_makefile_references_scope_guard(self):
        """Makefile must include scope-guard target."""
        content = MAKEFILE.read_text(encoding="utf-8")
        assert "scope-guard" in content, "Makefile missing scope-guard target"


# ═══════════════════════════════════════════════════════════════════════════════
# ARCHIVE IMPORT GUARDS
# ═══════════════════════════════════════════════════════════════════════════════


class TestArchiveImportGuard:
    """Ensure archive directory is not a proper Python package."""

    def test_archive_not_in_sys_path(self):
        """Archive directory must not be in sys.path."""
        archive_path = str(ARCHIVE_DIR.resolve())
        assert archive_path not in sys.path, f"Archive directory found in sys.path: {archive_path}"

    def test_archive_has_no_init(self):
        """Archive directory must not have __init__.py (would make it a proper package)."""
        init_file = ARCHIVE_DIR / "__init__.py"
        assert not init_file.exists(), "Archive has __init__.py — this makes it a proper Python package!"

    def test_archive_subdir_has_no_init(self):
        """Archive subdirectories must not have __init__.py."""
        legacy_init = ARCHIVE_DIR / "legacy-rsi-bot" / "__init__.py"
        assert not legacy_init.exists(), "Archive subdir has __init__.py — remove it!"

    def test_archive_has_gitignore(self):
        """Archive must have .gitignore to prevent tooling discovery."""
        gitignore = ARCHIVE_DIR / ".gitignore"
        assert gitignore.exists(), "Archive missing .gitignore to prevent tooling discovery"


# ═══════════════════════════════════════════════════════════════════════════════
# REPO CONTRACT GUARDS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRepoContractGuard:
    """Verify repository structure matches REPO_CONTRACT.md."""

    def test_repo_contract_exists(self):
        """REPO_CONTRACT.md must exist at repository root."""
        contract = ROOT_DIR / "REPO_CONTRACT.md"
        assert contract.exists(), "REPO_CONTRACT.md not found at repository root"

    def test_archive_contract_exists(self):
        """ARCHIVE_CONTRACT.md must exist in archive directory."""
        contract = ARCHIVE_DIR / "ARCHIVE_CONTRACT.md"
        assert contract.exists(), "ARCHIVE_CONTRACT.md not found in archive/"

    def test_archive_readme_exists(self):
        """Archive must have README.md explaining its purpose."""
        readme = ARCHIVE_DIR / "legacy-rsi-bot" / "README.md"
        assert readme.exists(), "Archive missing README.md"

    def test_no_root_level_bot_scripts(self):
        """Root level must not have bot/trading scripts."""
        forbidden_patterns = ["*bot*.py", "*trading*.py", "*rsi*.py", "*signal*.py"]
        for pattern in forbidden_patterns:
            matches = list(ROOT_DIR.glob(pattern))
            # Filter out test files
            matches = [m for m in matches if "test" not in m.name.lower()]
            assert len(matches) == 0, f"Forbidden root-level file: {matches}"


# ═══════════════════════════════════════════════════════════════════════════════
# ARCHIVE INERTNESS GUARDS
# ═══════════════════════════════════════════════════════════════════════════════


class TestArchiveInertness:
    """Verify archive directory is documented as inert."""

    def test_archive_has_inert_documentation(self):
        """Archive README must state it is inert/non-executable."""
        readme = ARCHIVE_DIR / "legacy-rsi-bot" / "README.md"
        if readme.exists():
            content = readme.read_text(encoding="utf-8")
            assert any(
                term in content.upper() for term in ["INERT", "NON-EXECUTABLE", "NOT EXECUTED", "DO NOT"]
            ), "Archive README must explicitly state code is inert"

    def test_archive_contract_forbids_imports(self):
        """ARCHIVE_CONTRACT.md must forbid imports."""
        contract = ARCHIVE_DIR / "ARCHIVE_CONTRACT.md"
        if contract.exists():
            content = contract.read_text(encoding="utf-8")
            assert "FORBIDDEN" in content.upper() or "forbidden" in content, "ARCHIVE_CONTRACT.md must mention forbidden imports"

    def test_archive_contract_states_non_executable(self):
        """ARCHIVE_CONTRACT.md must state archive is non-executable."""
        contract = ARCHIVE_DIR / "ARCHIVE_CONTRACT.md"
        if contract.exists():
            content = contract.read_text(encoding="utf-8")
            assert any(
                term in content.upper() for term in ["NON-EXECUTABLE", "INERT", "NOT EXECUTED"]
            ), "ARCHIVE_CONTRACT.md must state archive is non-executable"


# ═══════════════════════════════════════════════════════════════════════════════
# REGRESSION SENTINEL: MAKEFILE ACTIVE TARGETS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMakefileActiveTargets:
    """Verify Makefile only contains ChainBridge-appropriate targets."""

    def test_all_targets_are_chainbridge_aligned(self):
        """All Makefile targets must be ChainBridge-aligned."""
        content = MAKEFILE.read_text(encoding="utf-8")

        # Extract target names (lines that end with : and don't start with .)
        target_pattern = re.compile(r"^([a-zA-Z][a-zA-Z0-9_-]*)\s*:", re.MULTILINE)
        targets = target_pattern.findall(content)

        # Forbidden terms in targets
        forbidden_terms = ["rsi", "trading", "bot", "crypto", "signal", "alpha"]

        for target in targets:
            target_lower = target.lower()
            # Check for forbidden terms
            for forbidden in forbidden_terms:
                assert forbidden not in target_lower, f"Makefile target '{target}' contains forbidden term '{forbidden}'"
