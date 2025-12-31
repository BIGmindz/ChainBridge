"""
Tests for Governance Boot Checks — PAC-GOV-GUARD-01

These tests verify fail-closed behavior for governance root files.
Each test proves that the system HALTS on governance violations.

Test Categories:
1. Happy path — valid files pass
2. Missing files — GovernanceBootError raised
3. Invalid JSON — GovernanceBootError raised
4. Empty content — GovernanceBootError raised
5. Missing required fields — GovernanceBootError raised

Author: ATLAS (GID-11)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Generator, Optional

import pytest

from core.governance.boot_checks import (
    BootCheckResult,
    GovernanceBootError,
    check_governance_boot,
    enforce_governance_boot,
    get_governance_files,
    get_governance_status,
    validate_governance_file,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_repo() -> Generator[Path, None, None]:
    """Create a temporary repository structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Create directory structure
        (repo_root / "config").mkdir(parents=True)
        (repo_root / ".github").mkdir(parents=True)

        # Create marker file so _find_repo_root works
        (repo_root / "pytest.ini").write_text("[pytest]\n")

        yield repo_root


@pytest.fixture
def valid_agents_json() -> dict:
    """Valid agents.json content."""
    return {
        "calp_version": "1.0.0",
        "agents": [
            {"gid": "GID-00", "name": "BENSON"},
        ],
    }


@pytest.fixture
def valid_alex_rules_json() -> dict:
    """Valid ALEX_RULES.json content."""
    return {
        "governance_id": "GID-08",
        "agent_name": "ALEX",
        "version": "1.0.0",
        "hard_constraints": [],
    }


def write_governance_files(
    repo_root: Path,
    agents_content: dict | Optional[str] = None,
    alex_content: dict | Optional[str] = None,
) -> None:
    """Helper to write governance files with various content."""
    if agents_content is not None:
        agents_path = repo_root / "config" / "agents.json"
        if isinstance(agents_content, dict):
            agents_path.write_text(json.dumps(agents_content, indent=2))
        else:
            agents_path.write_text(agents_content)

    if alex_content is not None:
        alex_path = repo_root / ".github" / "ALEX_RULES.json"
        if isinstance(alex_content, dict):
            alex_path.write_text(json.dumps(alex_content, indent=2))
        else:
            alex_path.write_text(alex_content)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: HAPPY PATH
# ═══════════════════════════════════════════════════════════════════════════════


class TestHappyPath:
    """Tests for valid governance files."""

    def test_valid_files_pass_check(
        self,
        temp_repo: Path,
        valid_agents_json: dict,
        valid_alex_rules_json: dict,
    ) -> None:
        """Valid governance files should pass all checks."""
        write_governance_files(temp_repo, valid_agents_json, valid_alex_rules_json)

        assert check_governance_boot(temp_repo) is True

    def test_valid_files_no_exception(
        self,
        temp_repo: Path,
        valid_agents_json: dict,
        valid_alex_rules_json: dict,
    ) -> None:
        """Valid governance files should not raise GovernanceBootError."""
        write_governance_files(temp_repo, valid_agents_json, valid_alex_rules_json)

        # Should not raise
        enforce_governance_boot(temp_repo)

    def test_valid_files_status_report(
        self,
        temp_repo: Path,
        valid_agents_json: dict,
        valid_alex_rules_json: dict,
    ) -> None:
        """Status report should show all files valid."""
        write_governance_files(temp_repo, valid_agents_json, valid_alex_rules_json)

        status = get_governance_status(temp_repo)

        assert status["overall_valid"] is True
        assert status["error_count"] == 0
        assert len(status["files"]) == 2
        assert all(f["valid"] for f in status["files"])

    def test_validate_single_file(
        self,
        temp_repo: Path,
        valid_agents_json: dict,
    ) -> None:
        """Single file validation should return BootCheckResult."""
        write_governance_files(temp_repo, agents_content=valid_agents_json)

        result = validate_governance_file("config/agents.json", temp_repo)

        assert isinstance(result, BootCheckResult)
        assert result.valid is True
        assert result.error is None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: MISSING FILES
# ═══════════════════════════════════════════════════════════════════════════════


class TestMissingFiles:
    """Tests for missing governance files — must FAIL CLOSED."""

    def test_missing_agents_json_raises(
        self,
        temp_repo: Path,
        valid_alex_rules_json: dict,
    ) -> None:
        """Missing agents.json must raise GovernanceBootError."""
        # Only write ALEX_RULES, not agents.json
        write_governance_files(temp_repo, alex_content=valid_alex_rules_json)

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert "config/agents.json" in str(exc_info.value)
        assert "does not exist" in str(exc_info.value)

    def test_missing_alex_rules_raises(
        self,
        temp_repo: Path,
        valid_agents_json: dict,
    ) -> None:
        """Missing ALEX_RULES.json must raise GovernanceBootError."""
        # Only write agents.json, not ALEX_RULES
        write_governance_files(temp_repo, agents_content=valid_agents_json)

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert ".github/ALEX_RULES.json" in str(exc_info.value)
        assert "does not exist" in str(exc_info.value)

    def test_missing_both_files_raises(self, temp_repo: Path) -> None:
        """Missing both files must raise GovernanceBootError."""
        # Write neither file

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        # First failure should be reported
        assert "GOVERNANCE BOOT FAILURE" in str(exc_info.value)

    def test_missing_file_check_returns_false(
        self,
        temp_repo: Path,
        valid_alex_rules_json: dict,
    ) -> None:
        """check_governance_boot should return False for missing files."""
        write_governance_files(temp_repo, alex_content=valid_alex_rules_json)

        assert check_governance_boot(temp_repo) is False


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: INVALID JSON
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvalidJSON:
    """Tests for malformed JSON — must FAIL CLOSED."""

    def test_invalid_json_agents_raises(
        self,
        temp_repo: Path,
        valid_alex_rules_json: dict,
    ) -> None:
        """Invalid JSON in agents.json must raise GovernanceBootError."""
        write_governance_files(
            temp_repo,
            agents_content="{ invalid json ]",
            alex_content=valid_alex_rules_json,
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert "config/agents.json" in str(exc_info.value)
        assert "Invalid JSON" in str(exc_info.value)

    def test_invalid_json_alex_raises(
        self,
        temp_repo: Path,
        valid_agents_json: dict,
    ) -> None:
        """Invalid JSON in ALEX_RULES.json must raise GovernanceBootError."""
        write_governance_files(
            temp_repo,
            agents_content=valid_agents_json,
            alex_content="not { valid: json }",
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert ".github/ALEX_RULES.json" in str(exc_info.value)
        assert "Invalid JSON" in str(exc_info.value)

    def test_truncated_json_raises(
        self,
        temp_repo: Path,
        valid_alex_rules_json: dict,
    ) -> None:
        """Truncated JSON must raise GovernanceBootError."""
        write_governance_files(
            temp_repo,
            agents_content='{"calp_version": "1.0.0"',  # Missing closing brace
            alex_content=valid_alex_rules_json,
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert "Invalid JSON" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: EMPTY CONTENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmptyContent:
    """Tests for empty files — must FAIL CLOSED."""

    def test_empty_object_raises(
        self,
        temp_repo: Path,
        valid_alex_rules_json: dict,
    ) -> None:
        """Empty object {} must raise GovernanceBootError."""
        write_governance_files(
            temp_repo,
            agents_content={},
            alex_content=valid_alex_rules_json,
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert "empty object" in str(exc_info.value)

    def test_empty_array_raises(
        self,
        temp_repo: Path,
        valid_alex_rules_json: dict,
    ) -> None:
        """Empty array [] must raise GovernanceBootError."""
        write_governance_files(
            temp_repo,
            agents_content="[]",
            alex_content=valid_alex_rules_json,
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert "empty array" in str(exc_info.value)

    def test_null_content_raises(
        self,
        temp_repo: Path,
        valid_alex_rules_json: dict,
    ) -> None:
        """Null content must raise GovernanceBootError."""
        write_governance_files(
            temp_repo,
            agents_content="null",
            alex_content=valid_alex_rules_json,
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert "null" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: MISSING REQUIRED FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMissingFields:
    """Tests for missing required fields — must FAIL CLOSED."""

    def test_agents_missing_version_raises(
        self,
        temp_repo: Path,
        valid_alex_rules_json: dict,
    ) -> None:
        """agents.json without calp_version must raise GovernanceBootError."""
        agents_no_version = {
            "agents": [{"gid": "GID-00", "name": "BENSON"}],
            # Missing calp_version
        }
        write_governance_files(
            temp_repo,
            agents_content=agents_no_version,
            alex_content=valid_alex_rules_json,
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert "Missing required fields" in str(exc_info.value)
        assert "calp_version" in str(exc_info.value)

    def test_alex_missing_governance_id_raises(
        self,
        temp_repo: Path,
        valid_agents_json: dict,
    ) -> None:
        """ALEX_RULES.json without governance_id must raise GovernanceBootError."""
        alex_no_gid = {
            "agent_name": "ALEX",
            "version": "1.0.0",
            # Missing governance_id
        }
        write_governance_files(
            temp_repo,
            agents_content=valid_agents_json,
            alex_content=alex_no_gid,
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert "Missing required fields" in str(exc_info.value)
        assert "governance_id" in str(exc_info.value)

    def test_alex_missing_version_raises(
        self,
        temp_repo: Path,
        valid_agents_json: dict,
    ) -> None:
        """ALEX_RULES.json without version must raise GovernanceBootError."""
        alex_no_version = {
            "governance_id": "GID-08",
            "agent_name": "ALEX",
            # Missing version
        }
        write_governance_files(
            temp_repo,
            agents_content=valid_agents_json,
            alex_content=alex_no_version,
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert "Missing required fields" in str(exc_info.value)
        assert "version" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: ERROR MESSAGE QUALITY
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrorMessages:
    """Tests for deterministic, informative error messages."""

    def test_error_includes_file_path(self, temp_repo: Path) -> None:
        """Error must include the offending file path."""
        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        # Should mention the file path
        error_msg = str(exc_info.value)
        assert "config/agents.json" in error_msg or ".github/ALEX_RULES.json" in error_msg

    def test_error_includes_reason(
        self,
        temp_repo: Path,
        valid_alex_rules_json: dict,
    ) -> None:
        """Error must include the specific reason."""
        write_governance_files(
            temp_repo,
            agents_content="{ broken }",
            alex_content=valid_alex_rules_json,
        )

        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        # Should mention what went wrong
        assert "Invalid JSON" in str(exc_info.value)

    def test_error_is_deterministic(self, temp_repo: Path) -> None:
        """Same input must produce same error message."""
        error_messages = []

        for _ in range(3):
            try:
                enforce_governance_boot(temp_repo)
            except GovernanceBootError as e:
                error_messages.append(str(e))

        # All error messages should be identical
        assert len(set(error_messages)) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: EXCEPTION ATTRIBUTES
# ═══════════════════════════════════════════════════════════════════════════════


class TestExceptionAttributes:
    """Tests for GovernanceBootError attributes."""

    def test_exception_has_file_path_attribute(self, temp_repo: Path) -> None:
        """GovernanceBootError must have file_path attribute."""
        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert hasattr(exc_info.value, "file_path")
        assert exc_info.value.file_path in ("config/agents.json", ".github/ALEX_RULES.json")

    def test_exception_has_reason_attribute(self, temp_repo: Path) -> None:
        """GovernanceBootError must have reason attribute."""
        with pytest.raises(GovernanceBootError) as exc_info:
            enforce_governance_boot(temp_repo)

        assert hasattr(exc_info.value, "reason")
        assert len(exc_info.value.reason) > 0

    def test_exception_is_runtime_error(self, temp_repo: Path) -> None:
        """GovernanceBootError must be a RuntimeError subclass."""
        with pytest.raises(RuntimeError):
            enforce_governance_boot(temp_repo)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtilityFunctions:
    """Tests for utility/helper functions."""

    def test_get_governance_files_returns_dict(self) -> None:
        """get_governance_files should return a dictionary."""
        files = get_governance_files()

        assert isinstance(files, dict)
        assert "config/agents.json" in files
        assert ".github/ALEX_RULES.json" in files

    def test_get_governance_files_is_copy(self) -> None:
        """get_governance_files should return a copy, not the original."""
        files1 = get_governance_files()
        files2 = get_governance_files()

        # Should be equal but not same object
        assert files1 == files2
        assert files1 is not files2

    def test_status_report_includes_descriptions(
        self,
        temp_repo: Path,
        valid_agents_json: dict,
        valid_alex_rules_json: dict,
    ) -> None:
        """Status report should include file descriptions."""
        write_governance_files(temp_repo, valid_agents_json, valid_alex_rules_json)

        status = get_governance_status(temp_repo)

        descriptions = [f["description"] for f in status["files"]]
        assert any("CALP" in d for d in descriptions)
        assert any("ALEX" in d for d in descriptions)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: REAL REPOSITORY (Integration)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRealRepository:
    """Integration tests against real repository files."""

    def test_real_repo_passes_boot_check(self) -> None:
        """Real repository governance files should pass all checks."""
        # Uses auto-detected repo root
        assert check_governance_boot() is True

    def test_real_repo_enforce_does_not_raise(self) -> None:
        """Real repository should not raise GovernanceBootError."""
        # Uses auto-detected repo root
        enforce_governance_boot()  # Should not raise

    def test_real_repo_status_all_valid(self) -> None:
        """Real repository status should show all files valid."""
        status = get_governance_status()

        assert status["overall_valid"] is True
        assert status["error_count"] == 0
