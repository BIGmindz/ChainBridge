"""
🧪 Gameday Test: G6 — Scope Violation
PAC-GOV-GAMEDAY-01: Governance Failure Simulation

Simulate:
- Forbidden file patterns (bot, trading, etc.)
- Archive imports
- Forbidden extensions
- Unauthorized directories

Invariants:
- Operation denied (violation detected)
- No state mutation
- Event emitted (SCOPE_VIOLATION)
- audit_ref present
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.governance.event_sink import GovernanceEventEmitter, InMemorySink
from core.governance.events import GovernanceEvent, GovernanceEventType, scope_violation_event
from scripts.scope_guard.check_repo_scope import (
    ALLOWED_ROOT_DIRS,
    FORBIDDEN_EXTENSIONS,
    FORBIDDEN_IMPORTS,
    FORBIDDEN_PATTERNS,
    PATTERN_EXCEPTIONS,
    SKIP_DIRS,
    ScopeCheckResult,
    Violation,
    check_archive_imports,
    check_forbidden_extensions,
    check_forbidden_files,
    check_makefile,
    is_pattern_exception,
)

# =============================================================================
# G6.1 — Forbidden File Patterns
# =============================================================================


class TestForbiddenFilePatterns:
    """
    G6.1: Simulate detection of forbidden file patterns.

    Attack scenario: Attacker tries to add bot/trading/crypto
    files outside the archive directory.
    """

    @pytest.fixture
    def repo_root(self, tmp_path: Path) -> Path:
        """Create a minimal repo structure."""
        (tmp_path / "core").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / ".git").mkdir()  # Git marker
        return tmp_path

    def test_bot_file_detected(self, repo_root: Path) -> None:
        """Files matching *bot*.py should be detected."""
        # Create forbidden file
        (repo_root / "core" / "trading_bot.py").write_text("# Bot code")

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        # Invariant 1: Violation detected
        assert not result.passed
        assert any("FORBIDDEN_FILE" in v.category for v in result.violations)
        assert any("bot" in v.file_path.lower() for v in result.violations)

    def test_trading_file_detected(self, repo_root: Path) -> None:
        """Files matching *trading*.py should be detected."""
        (repo_root / "core" / "auto_trading.py").write_text("# Trading code")

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        assert not result.passed
        assert any("trading" in v.file_path.lower() for v in result.violations)

    def test_crypto_file_detected(self, repo_root: Path) -> None:
        """Files matching *crypto*.py should be detected."""
        (repo_root / "core" / "crypto_selector.py").write_text("# Crypto code")

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        assert not result.passed
        assert any("crypto" in v.file_path.lower() for v in result.violations)

    def test_rsi_file_detected(self, repo_root: Path) -> None:
        """Files matching *rsi*.py should be detected."""
        (repo_root / "core" / "rsi_analysis.py").write_text("# RSI code")

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        assert not result.passed
        assert any("rsi" in v.file_path.lower() for v in result.violations)

    def test_signal_file_detected(self, repo_root: Path) -> None:
        """Files matching *signal*.py should be detected (except exceptions)."""
        (repo_root / "core" / "buy_signal.py").write_text("# Signal code")

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        assert not result.passed


# =============================================================================
# G6.2 — Pattern Exceptions
# =============================================================================


class TestPatternExceptions:
    """
    G6.2: Verify allowed exceptions are not flagged.

    Some patterns like chatbot, robot, trading_partner are allowed.
    """

    def test_chatbot_allowed(self) -> None:
        """Chatbot files should be allowed (exception)."""
        assert is_pattern_exception("chatbot.py")
        assert is_pattern_exception("ai_chatbot_service.py")

    def test_robot_allowed(self) -> None:
        """Robot/robotics files should be allowed (exception)."""
        assert is_pattern_exception("robot_controller.py")
        assert is_pattern_exception("robotics.py")

    def test_trading_partner_allowed(self) -> None:
        """Trading partner files should be allowed (business context)."""
        assert is_pattern_exception("trading_partner.py")

    def test_market_metrics_allowed(self) -> None:
        """Market metrics files should be allowed (ChainBridge context)."""
        assert is_pattern_exception("market_metrics.py")

    def test_signal_envelope_allowed(self) -> None:
        """Signal envelope files should be allowed (governance context)."""
        assert is_pattern_exception("signal_envelope.py")

    def test_crypto_signer_allowed(self) -> None:
        """Cryptographic signer files should be allowed."""
        assert is_pattern_exception("crypto_signer.py")

    @pytest.fixture
    def repo_root(self, tmp_path: Path) -> Path:
        """Create a minimal repo structure."""
        (tmp_path / "core").mkdir()
        (tmp_path / ".git").mkdir()
        return tmp_path

    def test_allowed_file_not_flagged(self, repo_root: Path) -> None:
        """Files matching exceptions should not be flagged."""
        # Create an allowed file
        (repo_root / "core" / "chatbot_service.py").write_text("# Chatbot")

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        # Should pass (exception applies)
        assert result.passed


# =============================================================================
# G6.3 — Archive Import Violations
# =============================================================================


class TestArchiveImportViolations:
    """
    G6.3: Simulate detection of imports from archive directory.

    Attack scenario: Attacker tries to import forbidden code
    from the archive directory.
    """

    @pytest.fixture
    def repo_root(self, tmp_path: Path) -> Path:
        """Create a repo with Python files."""
        (tmp_path / "core").mkdir()
        (tmp_path / ".git").mkdir()
        return tmp_path

    def test_direct_archive_import_detected(self, repo_root: Path) -> None:
        """Direct imports from archive should be detected."""
        # Create file with forbidden import
        (repo_root / "core" / "module.py").write_text("from archive import old_module\n")

        result = ScopeCheckResult()
        check_archive_imports(repo_root, result)

        # Invariant 1: Violation detected
        assert not result.passed
        assert any("ARCHIVE_IMPORT" in v.category for v in result.violations)

    def test_nested_archive_import_detected(self, repo_root: Path) -> None:
        """Nested imports from archive should be detected."""
        (repo_root / "core" / "module.py").write_text("from archive.old_bot import TradingBot\n")

        result = ScopeCheckResult()
        check_archive_imports(repo_root, result)

        assert not result.passed
        assert any("archive" in v.message.lower() for v in result.violations)

    def test_import_archive_statement_detected(self, repo_root: Path) -> None:
        """'import archive' statement should be detected."""
        (repo_root / "core" / "module.py").write_text("import archive\n")

        result = ScopeCheckResult()
        check_archive_imports(repo_root, result)

        assert not result.passed

    def test_line_number_captured(self, repo_root: Path) -> None:
        """Violation should include line number."""
        (repo_root / "core" / "module.py").write_text("# Header comment\n" "import os\n" "from archive import forbidden\n" "import json\n")

        result = ScopeCheckResult()
        check_archive_imports(repo_root, result)

        assert not result.passed
        assert result.violations[0].line_number == 3


# =============================================================================
# G6.4 — Forbidden Extensions
# =============================================================================


class TestForbiddenExtensions:
    """
    G6.4: Simulate detection of forbidden file extensions.

    Attack scenario: Attacker tries to add Jupyter notebooks
    or other forbidden file types.
    """

    @pytest.fixture
    def repo_root(self, tmp_path: Path) -> Path:
        """Create a minimal repo structure."""
        (tmp_path / "notebooks").mkdir()
        (tmp_path / ".git").mkdir()
        return tmp_path

    def test_ipynb_extension_detected(self, repo_root: Path) -> None:
        """Jupyter notebook files (.ipynb) should be detected."""
        (repo_root / "notebooks" / "analysis.ipynb").write_text("{}")

        result = ScopeCheckResult()
        check_forbidden_extensions(repo_root, result)

        # Invariant 1: Violation detected
        assert not result.passed
        assert any("FORBIDDEN_EXTENSION" in v.category for v in result.violations)
        assert any(".ipynb" in v.message for v in result.violations)

    def test_streamlit_extension_detected(self, repo_root: Path) -> None:
        """Streamlit config files should be detected."""
        # Create .streamlit file
        (repo_root / "app.streamlit").write_text("config")

        result = ScopeCheckResult()
        check_forbidden_extensions(repo_root, result)

        assert not result.passed


# =============================================================================
# G6.5 — Skip Directory Logic
# =============================================================================


class TestSkipDirectoryLogic:
    """
    G6.5: Verify files in skip directories are not flagged.

    Files in .git, .venv, archive, etc. should be skipped.
    """

    @pytest.fixture
    def repo_root(self, tmp_path: Path) -> Path:
        """Create repo with skip directories."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "archive").mkdir()
        (tmp_path / ".venv").mkdir()
        (tmp_path / "core").mkdir()
        return tmp_path

    def test_archive_directory_skipped(self, repo_root: Path) -> None:
        """Files in archive/ should be skipped."""
        # Create forbidden file IN archive (should be OK)
        (repo_root / "archive" / "old_trading_bot.py").write_text("# Old bot")

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        # Should pass (archive is skipped)
        assert result.passed

    def test_venv_directory_skipped(self, repo_root: Path) -> None:
        """Files in .venv/ should be skipped."""
        venv_site = repo_root / ".venv" / "lib" / "site-packages"
        venv_site.mkdir(parents=True)
        (venv_site / "trading_lib.py").write_text("# Library")

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        assert result.passed

    def test_git_directory_skipped(self, repo_root: Path) -> None:
        """Files in .git/ should be skipped."""
        (repo_root / ".git" / "config").write_text("bot=yes")

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        assert result.passed


# =============================================================================
# G6.6 — Scope Violation Events
# =============================================================================


class TestScopeViolationEvents:
    """
    G6.6: Verify scope violations emit proper telemetry events.

    Invariant: SCOPE_VIOLATION event must be emitted.
    """

    def test_scope_violation_event_structure(self) -> None:
        """Test scope_violation_event factory produces valid event."""
        event = scope_violation_event(
            file_path="core/trading_bot.py",
            violation_type="FORBIDDEN_FILE",
            pattern=".*bot.*\.py$",
            metadata={"message": "File matches forbidden pattern"},
        )

        assert event.event_type == GovernanceEventType.SCOPE_VIOLATION.value
        assert event.target == "core/trading_bot.py"
        assert event.reason_code == "FORBIDDEN_FILE"
        assert "forbidden" in event.metadata["message"].lower()

    def test_scope_violation_event_has_audit_ref(self) -> None:
        """Scope violation event should support metadata for audit tracking."""
        event = scope_violation_event(
            file_path="test.py",
            violation_type="ARCHIVE_IMPORT",
            metadata={"audit_ref": "audit-2024-01-01-001"},
        )

        # Invariant 4: audit info present
        assert event.metadata["audit_ref"] == "audit-2024-01-01-001"

    def test_scope_violation_event_captured_by_sink(self) -> None:
        """Scope violation event should be captured by InMemorySink."""
        sink = InMemorySink()
        emitter = GovernanceEventEmitter()
        emitter.add_sink(sink)

        try:
            event = scope_violation_event(
                file_path="forbidden_bot.py",
                violation_type="FORBIDDEN_FILE",
                pattern=".*bot.*\.py$",
            )

            emitter.emit(event)

            # Invariant 3: Event emitted
            events = sink.get_events()
            assert len(events) == 1
            assert events[0].event_type == GovernanceEventType.SCOPE_VIOLATION.value
        finally:
            emitter.remove_sink(sink)


# =============================================================================
# G6.7 — No State Mutation on Violation
# =============================================================================


class TestNoStateMutationOnViolation:
    """
    G6.7: Verify scope check does not mutate file system.

    Invariant: Scope checking is read-only.
    """

    @pytest.fixture
    def repo_root(self, tmp_path: Path) -> Path:
        """Create repo with files to check."""
        (tmp_path / "core").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / "core" / "module.py").write_text("# Valid module\n")
        (tmp_path / "core" / "forbidden_bot.py").write_text("# Bot\n")
        return tmp_path

    def test_scope_check_does_not_delete_files(self, repo_root: Path) -> None:
        """Scope check should not delete any files."""
        # List files before
        files_before = list(repo_root.rglob("*"))

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)

        # List files after
        files_after = list(repo_root.rglob("*"))

        # Invariant 2: No state mutation
        assert len(files_after) == len(files_before)

    def test_scope_check_does_not_modify_files(self, repo_root: Path) -> None:
        """Scope check should not modify any files."""
        # Read file content before
        module_path = repo_root / "core" / "module.py"
        content_before = module_path.read_text()

        result = ScopeCheckResult()
        check_forbidden_files(repo_root, result)
        check_archive_imports(repo_root, result)

        # Read file content after
        content_after = module_path.read_text()

        # Invariant 2: No state mutation
        assert content_after == content_before

    def test_multiple_checks_consistent(self, repo_root: Path) -> None:
        """Multiple scope checks should produce same results."""
        results = []
        for _ in range(3):
            result = ScopeCheckResult()
            check_forbidden_files(repo_root, result)
            results.append(len(result.violations))

        # All results should be consistent
        assert all(r == results[0] for r in results)


# =============================================================================
# G6.8 — FORBIDDEN_PATTERNS Completeness
# =============================================================================


class TestForbiddenPatternsCompleteness:
    """
    G6.8: Verify FORBIDDEN_PATTERNS covers all dangerous patterns.
    """

    def test_forbidden_patterns_not_empty(self) -> None:
        """FORBIDDEN_PATTERNS should not be empty."""
        assert len(FORBIDDEN_PATTERNS) > 0

    def test_all_patterns_are_regex(self) -> None:
        """All forbidden patterns should be compiled regex."""
        import re

        for pattern in FORBIDDEN_PATTERNS:
            assert isinstance(pattern, type(re.compile("")))

    @pytest.mark.parametrize(
        "dangerous_filename",
        [
            "trading_bot.py",
            "crypto_bot.py",
            "rsi_bot.py",
            "multi_signal_bot.py",
            "alpha_trading.py",
            "crypto_selector.py",
        ],
    )
    def test_dangerous_files_matched(self, dangerous_filename: str) -> None:
        """Dangerous filenames should match at least one pattern."""
        # Skip if it's an exception
        if is_pattern_exception(dangerous_filename):
            pytest.skip(f"{dangerous_filename} is an exception")

        matched = any(pattern.match(dangerous_filename) for pattern in FORBIDDEN_PATTERNS)
        assert matched, f"{dangerous_filename} should match a forbidden pattern"
