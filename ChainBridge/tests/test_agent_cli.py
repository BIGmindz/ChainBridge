"""
Unit tests for agent_cli module.

Tests the CLI subcommands (list, show, validate, dump-json) for correctness,
exit codes, and output formatting.
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]


def run_agent_cli_command(command: list[str]) -> Tuple[int, str]:
    """Run an agent_cli command and capture output.

    Args:
        command: List of command parts (e.g., ["python", "-m", "tools.agent_cli", "list"])

    Returns:
        Tuple of (exit_code, stdout+stderr output)
    """
    env = os.environ.copy()
    # Ensure the monorepo root is on PYTHONPATH so `python -m tools.agent_cli` resolves
    env["PYTHONPATH"] = f"{ROOT_DIR}:{env.get('PYTHONPATH','')}" if env.get("PYTHONPATH") else str(ROOT_DIR)
    result = subprocess.run(
        command,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode, result.stdout + result.stderr


class TestAgentCLIList:
    """Test the 'list' subcommand."""

    def test_list_command_success(self) -> None:
        """Test that list command succeeds and returns 0."""
        exit_code, output = run_agent_cli_command(["python", "-m", "tools.agent_cli", "list"])

        assert exit_code == 0, f"Expected exit code 0, got {exit_code}\nOutput: {output}"
        assert "Available Agents" in output
        assert "20 total" in output

    def test_list_command_includes_all_agents(self) -> None:
        """Test that list includes expected agent names."""
        exit_code, output = run_agent_cli_command(["python", "-m", "tools.agent_cli", "list"])

        assert exit_code == 0
        # Check for at least some known agents
        assert "FRONTEND_SONNY" in output
        assert "BACKEND_CODY" in output
        assert "CTO_BENSON" in output


class TestAgentCLIValidate:
    """Test the 'validate' subcommand."""

    def test_validate_command_runs(self) -> None:
        """Test that validate command runs without crashing."""
        exit_code, output = run_agent_cli_command(["python", "-m", "tools.agent_cli", "validate"])

        # Exit code should be 0 or 1 depending on validation status
        assert exit_code in (0, 1), f"Unexpected exit code: {exit_code}"
        assert "Validation Results" in output

    def test_validate_output_format(self) -> None:
        """Test that validate output includes expected fields."""
        exit_code, output = run_agent_cli_command(["python", "-m", "tools.agent_cli", "validate"])

        # Should show valid/total count
        assert "valid" in output.lower()
        assert "/" in output  # Format: X/Y

    def test_validate_invalid_agents_listed(self) -> None:
        """Test that validate lists invalid agents when they exist."""
        exit_code, output = run_agent_cli_command(["python", "-m", "tools.agent_cli", "validate"])

        # We know there are 3 incomplete agents in the test environment
        if exit_code == 1:
            # If validation failed, check that invalid agents are listed
            assert "Invalid agents" in output

    def test_validate_exit_code_reflects_status(self) -> None:
        """Test that exit code reflects validation success/failure.

        Given the test environment has 3 incomplete agents:
        - Exit code should be 1 (validation failed)
        """
        exit_code, output = run_agent_cli_command(["python", "-m", "tools.agent_cli", "validate"])

        # In the test environment, we expect 3 invalid agents
        # So exit code should be 1
        assert exit_code == 1
        assert "17/20 agents valid" in output
        assert "AI_AGENT_TIM" in output


class TestAgentCLIShow:
    """Test the 'show' subcommand."""

    def test_show_valid_agent(self) -> None:
        """Test showing details for a valid agent."""
        exit_code, output = run_agent_cli_command(["python", "-m", "tools.agent_cli", "show", "FRONTEND_SONNY"])

        assert exit_code == 0
        assert "FRONTEND_SONNY" in output
        assert "STATISTICS" in output

    def test_show_invalid_agent_fails(self) -> None:
        """Test that showing an invalid agent returns error."""
        exit_code, output = run_agent_cli_command(["python", "-m", "tools.agent_cli", "show", "NONEXISTENT_AGENT"])

        assert exit_code == 1
        assert "not found" in output.lower()


class TestAgentCLIDumpJson:
    """Test the 'dump-json' subcommand."""

    def test_dump_json_to_stdout(self) -> None:
        """Test exporting agents to JSON via stdout."""
        exit_code, output = run_agent_cli_command(["python", "-m", "tools.agent_cli", "dump-json"])

        assert exit_code == 0
        # Should contain JSON structure
        assert "{" in output
        assert "}" in output
        assert "FRONTEND_SONNY" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
