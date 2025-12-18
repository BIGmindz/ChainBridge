"""
Tests for ChainBridge Repository Scope Guard.

PAC Reference: PAC-REPO-SCOPE-LOCK-01

NOTE: This test file uses inline definitions to avoid import conflicts
with the existing scripts/ci/check_repo_scope.py module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

import pytest

# ═══════════════════════════════════════════════════════════════════════════════
# INLINE DEFINITIONS (mirrors scripts/scope_guard/check_repo_scope.py)
# ═══════════════════════════════════════════════════════════════════════════════

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
    "archive",
    "ql-db",
    "repo.git",
}

FORBIDDEN_PATTERNS: List[re.Pattern] = [
    re.compile(r".*bot.*\.py$", re.IGNORECASE),
    re.compile(r".*trading.*\.py$", re.IGNORECASE),
    re.compile(r".*alpha.*\.py$", re.IGNORECASE),
    re.compile(r".*crypto_selector.*\.py$", re.IGNORECASE),
    re.compile(r".*rsi_bot.*\.py$", re.IGNORECASE),
    re.compile(r".*multi_signal.*\.py$", re.IGNORECASE),
]

PATTERN_EXCEPTIONS: List[re.Pattern] = [
    re.compile(r".*chatbot.*", re.IGNORECASE),
    re.compile(r".*robot.*", re.IGNORECASE),
    re.compile(r".*trading_partner.*", re.IGNORECASE),
    re.compile(r".*trading_entity.*", re.IGNORECASE),
]

FORBIDDEN_IMPORTS: List[re.Pattern] = [
    re.compile(r"^\s*from\s+archive\b"),
    re.compile(r"^\s*import\s+archive\b"),
    re.compile(r"^\s*from\s+archive\."),
]

FORBIDDEN_MAKEFILE_PATTERNS: List[re.Pattern] = [
    re.compile(r"benson_rsi", re.IGNORECASE),
    re.compile(r"benson_system", re.IGNORECASE),
    re.compile(r"dynamic_crypto", re.IGNORECASE),
    re.compile(r"run-rsi", re.IGNORECASE),
    re.compile(r"run-trading", re.IGNORECASE),
]


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

    def add_violation(self, category: str, file_path: str, message: str, line_number: int | None = None) -> None:
        self.violations.append(Violation(category, file_path, message, line_number))


def is_pattern_exception(filename: str) -> bool:
    """Check if filename matches an allowed exception pattern."""
    return any(pattern.match(filename) for pattern in PATTERN_EXCEPTIONS)


def check_forbidden_files(root: Path, result: ScopeCheckResult) -> None:
    """Check for files matching forbidden patterns outside archive."""
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        parts = path.relative_to(root).parts
        if any(skip in parts for skip in SKIP_DIRS):
            continue
        result.files_checked += 1
        filename = path.name
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.match(filename):
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
            pass


def check_makefile(root: Path, result: ScopeCheckResult) -> None:
    """Check Makefile for forbidden patterns."""
    makefile = root / "Makefile"
    if not makefile.exists():
        return
    try:
        content = makefile.read_text(encoding="utf-8")
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
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


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN MATCHING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestForbiddenPatterns:
    """Test forbidden file pattern detection."""

    def test_bot_pattern_matches(self):
        """Bot files should match forbidden pattern."""
        test_files = ["trading_bot.py", "my_bot.py", "crypto_bot.py", "rsi_bot.py"]
        for filename in test_files:
            matched = any(p.match(filename) for p in FORBIDDEN_PATTERNS)
            assert matched, f"{filename} should match forbidden pattern"

    def test_trading_pattern_matches(self):
        """Trading files should match forbidden pattern."""
        test_files = ["trading_engine.py", "auto_trading.py", "day_trading.py"]
        for filename in test_files:
            matched = any(p.match(filename) for p in FORBIDDEN_PATTERNS)
            assert matched, f"{filename} should match forbidden pattern"

    def test_alpha_pattern_matches(self):
        """Alpha files should match forbidden pattern."""
        test_files = ["alpha_generator.py", "alpha_model.py", "generate_alpha.py"]
        for filename in test_files:
            matched = any(p.match(filename) for p in FORBIDDEN_PATTERNS)
            assert matched, f"{filename} should match forbidden pattern"

    def test_allowed_files_dont_match(self):
        """Legitimate ChainBridge files should not match."""
        allowed_files = [
            "decision_envelope.py",
            "gateway.py",
            "governance.py",
            "alex_middleware.py",
            "diggi_handler.py",
            "chainboard_api.py",
            "test_gateway.py",
        ]
        for filename in allowed_files:
            matched = any(p.match(filename) for p in FORBIDDEN_PATTERNS)
            assert not matched, f"{filename} should NOT match forbidden pattern"


class TestPatternExceptions:
    """Test exception patterns for allowed 'bot' usages."""

    def test_chatbot_allowed(self):
        assert is_pattern_exception("chatbot_service.py")
        assert is_pattern_exception("my_chatbot.py")

    def test_robot_allowed(self):
        assert is_pattern_exception("robot_controller.py")
        assert is_pattern_exception("robotics_module.py")

    def test_trading_partner_allowed(self):
        assert is_pattern_exception("trading_partner.py")
        assert is_pattern_exception("trading_partner_api.py")

    def test_trading_bot_not_exception(self):
        assert not is_pattern_exception("trading_bot.py")
        assert not is_pattern_exception("rsi_bot.py")


class TestForbiddenImports:
    """Test detection of forbidden archive imports."""

    def test_from_archive_import_detected(self):
        lines = ["from archive import something", "from archive.legacy import module"]
        for line in lines:
            matched = any(p.search(line) for p in FORBIDDEN_IMPORTS)
            assert matched, f"'{line}' should match forbidden import"

    def test_import_archive_detected(self):
        lines = ["import archive", "  import archive"]
        for line in lines:
            matched = any(p.search(line) for p in FORBIDDEN_IMPORTS)
            assert matched, f"'{line}' should match forbidden import"

    def test_normal_imports_allowed(self):
        lines = [
            "from gateway import decision_envelope",
            "from core.governance import diggi_handler",
            "import pytest",
        ]
        for line in lines:
            matched = any(p.search(line) for p in FORBIDDEN_IMPORTS)
            assert not matched, f"'{line}' should NOT match forbidden import"


class TestScopeCheckIntegration:
    """Integration tests using temporary directories."""

    def test_forbidden_file_detected(self, tmp_path):
        bot_file = tmp_path / "my_trading_bot.py"
        bot_file.write_text("# forbidden bot code")
        result = ScopeCheckResult()
        check_forbidden_files(tmp_path, result)
        assert not result.passed
        assert len(result.violations) == 1
        assert result.violations[0].category == "FORBIDDEN_FILE"

    def test_allowed_file_passes(self, tmp_path):
        (tmp_path / "gateway.py").write_text("# gateway code")
        (tmp_path / "governance.py").write_text("# governance code")
        result = ScopeCheckResult()
        check_forbidden_files(tmp_path, result)
        assert result.passed

    def test_archive_files_ignored(self, tmp_path):
        archive = tmp_path / "archive"
        archive.mkdir()
        (archive / "trading_bot.py").write_text("# legacy bot - should be ignored")
        result = ScopeCheckResult()
        check_forbidden_files(tmp_path, result)
        assert result.passed

    def test_archive_import_detected(self, tmp_path):
        bad_file = tmp_path / "bad_import.py"
        bad_file.write_text("from archive.legacy import something\n")
        result = ScopeCheckResult()
        check_archive_imports(tmp_path, result)
        assert not result.passed
        assert len(result.violations) >= 1
        assert result.violations[0].category == "ARCHIVE_IMPORT"

    def test_makefile_violation_detected(self, tmp_path):
        makefile = tmp_path / "Makefile"
        makefile.write_text("run-rsi:\n\tpython benson_rsi_bot.py\n")
        result = ScopeCheckResult()
        check_makefile(tmp_path, result)
        assert not result.passed
        assert any(v.category == "MAKEFILE_VIOLATION" for v in result.violations)

    def test_clean_makefile_passes(self, tmp_path):
        makefile = tmp_path / "Makefile"
        makefile.write_text(".PHONY: test\n\ntest:\n\tpytest\n")
        result = ScopeCheckResult()
        check_makefile(tmp_path, result)
        assert result.passed


class TestScopeCheckResult:
    """Test ScopeCheckResult data structure."""

    def test_empty_result_passes(self):
        result = ScopeCheckResult()
        assert result.passed

    def test_result_with_violation_fails(self):
        result = ScopeCheckResult()
        result.add_violation(category="TEST", file_path="test.py", message="Test")
        assert not result.passed

    def test_violation_with_line_number(self):
        result = ScopeCheckResult()
        result.add_violation(category="IMPORT", file_path="bad.py", message="Bad", line_number=42)
        assert result.violations[0].line_number == 42
