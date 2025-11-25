# api/tests/test_agents_status.py
"""
Test Suite for Agent Framework Status API

Comprehensive tests for GET /api/agents/status endpoint.
Validates response structure, data consistency, and error handling.

Author: ChainBridge Platform Team
Version: 1.0.0
"""

import pytest
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


class TestAgentsStatusEndpoint:
    """Test suite for /api/agents/status endpoint."""

    def test_agents_status_returns_200(self):
        """Verify endpoint returns 200 OK."""
        response = client.get("/api/agents/status")
        assert response.status_code == 200

    def test_agents_status_response_schema(self):
        """Verify response matches AgentStatusResponse schema."""
        response = client.get("/api/agents/status")
        data = response.json()

        # Verify all required fields present
        assert "total" in data
        assert "valid" in data
        assert "invalid" in data
        assert "invalid_roles" in data

        # Verify field types
        assert isinstance(data["total"], int)
        assert isinstance(data["valid"], int)
        assert isinstance(data["invalid"], int)
        assert isinstance(data["invalid_roles"], list)

        # Verify all elements in invalid_roles are strings
        for role in data["invalid_roles"]:
            assert isinstance(role, str)

    def test_agents_status_mathematical_consistency(self):
        """Verify total = valid + invalid."""
        response = client.get("/api/agents/status")
        data = response.json()

        assert data["total"] == data["valid"] + data["invalid"]

    def test_agents_status_non_negative_counts(self):
        """Verify all counts are non-negative."""
        response = client.get("/api/agents/status")
        data = response.json()

        assert data["total"] >= 0
        assert data["valid"] >= 0
        assert data["invalid"] >= 0

    def test_agents_status_invalid_roles_count_matches_invalid(self):
        """Verify len(invalid_roles) matches invalid count."""
        response = client.get("/api/agents/status")
        data = response.json()

        assert len(data["invalid_roles"]) == data["invalid"]

    def test_agents_status_invalid_roles_format(self):
        """Verify invalid_roles contains uppercase role names."""
        response = client.get("/api/agents/status")
        data = response.json()

        # If there are invalid roles, verify naming convention
        for role in data["invalid_roles"]:
            # Role names should be uppercase with underscores
            assert role.isupper() or "_" in role
            assert role.strip() == role  # No leading/trailing whitespace
            assert len(role) > 0  # Not empty

    def test_agents_status_total_count_realistic(self):
        """Verify total agent count is within expected range."""
        response = client.get("/api/agents/status")
        data = response.json()

        # ChainBridge has 20 agents as of this implementation
        assert data["total"] >= 1  # At least one agent exists
        assert data["total"] <= 100  # Reasonable upper bound

    def test_agents_status_response_content_type(self):
        """Verify response content type is application/json."""
        response = client.get("/api/agents/status")
        assert response.headers["content-type"] == "application/json"

    def test_agents_status_idempotency(self):
        """Verify multiple calls return consistent results."""
        response1 = client.get("/api/agents/status")
        response2 = client.get("/api/agents/status")

        data1 = response1.json()
        data2 = response2.json()

        # Results should be identical (stateless endpoint)
        assert data1 == data2

    def test_agents_status_current_state(self):
        """Verify endpoint returns current agent framework state.

        This test validates against the known state of the ChainBridge
        agent framework as of this sprint (20 total, 17 valid, 3 invalid).

        Note: This test may need updating if agent configurations change.
        """
        response = client.get("/api/agents/status")
        data = response.json()

        # Known state as of sprint implementation
        assert data["total"] == 20
        assert data["valid"] == 17
        assert data["invalid"] == 3

        # Verify known invalid agents are present
        known_invalid = {
            "AI_AGENT_TIM",
            "AI_RESEARCH_BENSON",
            "BIZDEV_PARTNERSHIPS_LEAD",
        }
        assert set(data["invalid_roles"]) == known_invalid


class TestAgentsStatusIntegration:
    """Integration tests verifying endpoint behavior with agent framework."""

    def test_agents_status_uses_validation_logic(self):
        """Verify endpoint uses shared get_validation_results() function."""
        from tools.agent_validate import get_validation_results

        # Call shared function directly
        valid_count, total_count, invalid_roles = get_validation_results()

        # Call API endpoint
        response = client.get("/api/agents/status")
        data = response.json()

        # Results should match
        assert data["total"] == total_count
        assert data["valid"] == valid_count
        assert data["invalid"] == total_count - valid_count
        assert set(data["invalid_roles"]) == set(invalid_roles)

    def test_agents_status_no_regression_on_agent_validate(self):
        """Verify agent_validate module still works after API integration."""
        from tools.agent_validate import main as validate_main

        # agent_validate should still function independently
        exit_code = validate_main()

        # Should return 1 (agents invalid) based on current state
        assert exit_code in (0, 1)

    def test_agents_status_no_regression_on_agent_cli(self):
        """Verify agent_cli validate command still works."""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "tools.agent_cli", "validate"],
            capture_output=True,
            text=True,
        )

        # Command should execute (exit code 0 or 1, not crash)
        assert result.returncode in (0, 1)
        assert "valid" in result.stdout.lower()


@pytest.mark.parametrize(
    "field_name,expected_type",
    [
        ("total", int),
        ("valid", int),
        ("invalid", int),
        ("invalid_roles", list),
    ],
)
def test_agents_status_field_types(field_name, expected_type):
    """Parametrized test for response field types."""
    response = client.get("/api/agents/status")
    data = response.json()

    assert field_name in data
    assert isinstance(data[field_name], expected_type)
