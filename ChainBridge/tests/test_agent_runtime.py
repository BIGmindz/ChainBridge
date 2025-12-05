"""
Unit tests for agent_runtime module.

Tests the AgentRuntime class and related data structures.
Fixtures automatically filter to valid agents to ensure stable, reliable tests.
"""

from typing import List

import pytest

from tools.agent_runtime import (
    AgentNotFoundError,
    AgentPromptError,
    AgentPrompts,
    AgentRuntime,
    AgentTask,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def runtime() -> AgentRuntime:
    """Create a fresh runtime instance for testing."""
    return AgentRuntime()


@pytest.fixture
def validation(runtime: AgentRuntime) -> dict[str, bool]:
    """Get validation map of all agents (role_name -> is_valid)."""
    return runtime.validate_all_agents()


@pytest.fixture
def valid_roles(runtime: AgentRuntime, validation: dict[str, bool]) -> List[str]:
    """Get list of all valid agent roles."""
    return [role for role in runtime.list_roles() if validation.get(role, False)]


@pytest.fixture
def one_valid_role(valid_roles: List[str]) -> str:
    """Get a single valid agent role for testing.

    Raises:
        pytest.skip: If no valid agents are available.
    """
    if not valid_roles:
        pytest.skip("No valid agent roles available for testing")
    return valid_roles[0]


# ============================================================================
# TESTS: AgentTask
# ============================================================================


class TestAgentTask:
    """Test AgentTask dataclass."""

    def test_valid_task_creation(self) -> None:
        """Test creating a valid task."""
        task = AgentTask(role_name="FRONTEND_SONNY", instruction="Build a responsive UI")
        assert task.role_name == "FRONTEND_SONNY"
        assert task.instruction == "Build a responsive UI"
        assert task.context is None
        assert task.metadata is None

    def test_task_with_context_and_metadata(self) -> None:
        """Test creating a task with context and metadata."""
        context = {"file": "index.tsx"}
        metadata = {"priority": "high"}
        task = AgentTask(
            role_name="BACKEND_CODY",
            instruction="Fix bug",
            context=context,
            metadata=metadata,
        )
        assert task.context == context
        assert task.metadata == metadata

    def test_task_validation_empty_role(self) -> None:
        """Test that empty role_name raises ValueError."""
        with pytest.raises(ValueError):
            AgentTask(role_name="", instruction="Do something")

    def test_task_validation_empty_instruction(self) -> None:
        """Test that empty instruction raises ValueError."""
        with pytest.raises(ValueError):
            AgentTask(role_name="SOME_ROLE", instruction="")


# ============================================================================
# TESTS: AgentPrompts
# ============================================================================


class TestAgentPrompts:
    """Test AgentPrompts dataclass."""

    def test_prompts_is_complete_with_all_fields(self) -> None:
        """Test is_complete returns True when all prompts present."""
        prompts = AgentPrompts(
            system_prompt="System",
            onboarding_prompt="Onboarding",
            knowledge_scope="Knowledge",
            checklist="Checklist",
        )
        assert prompts.is_complete() is True

    def test_prompts_is_complete_with_missing_field(self) -> None:
        """Test is_complete returns False when a prompt is empty."""
        prompts = AgentPrompts(
            system_prompt="System",
            onboarding_prompt="",
            knowledge_scope="Knowledge",
            checklist="Checklist",
        )
        assert prompts.is_complete() is False


# ============================================================================
# TESTS: AgentRuntime
# ============================================================================


class TestAgentRuntime:
    """Test AgentRuntime class."""

    def test_runtime_initialization(self) -> None:
        """Test runtime initializes without error."""
        runtime = AgentRuntime()
        assert runtime is not None

    def test_list_roles_non_empty(self, runtime: AgentRuntime) -> None:
        """Test that list_roles returns at least some roles."""
        roles = runtime.list_roles()
        assert isinstance(roles, list)
        assert len(roles) > 0

    def test_list_roles_cached(self, runtime: AgentRuntime) -> None:
        """Test that roles are cached on second call."""
        roles1 = runtime.list_roles()
        roles2 = runtime.list_roles()
        # Should be the same object due to caching
        assert roles1 is roles2

    def test_validate_all_agents_structure(self, runtime: AgentRuntime) -> None:
        """Test validate_all_agents returns correct structure."""
        validation = runtime.validate_all_agents()

        assert isinstance(validation, dict)
        roles = runtime.list_roles()
        assert len(validation) == len(roles)

        # Check that there are at least some valid agents
        valid_count = sum(1 for v in validation.values() if v)
        assert valid_count > 0

    def test_validate_all_agents_keys_match_roles(self, runtime: AgentRuntime, validation: dict[str, bool]) -> None:
        """Test that validation keys exactly match list_roles."""
        roles = runtime.list_roles()
        assert set(validation.keys()) == set(roles)

    def test_get_agent_known_role(self, runtime: AgentRuntime, one_valid_role: str) -> None:
        """Test getting a known agent role."""
        agent = runtime.get_agent(one_valid_role)

        assert agent is not None
        assert agent.role_name == one_valid_role

    def test_get_agent_unknown_role(self, runtime: AgentRuntime) -> None:
        """Test that getting unknown role raises AgentNotFoundError."""
        with pytest.raises(AgentNotFoundError):
            runtime.get_agent("NONEXISTENT_ROLE_XYZ")

    def test_get_agent_caching(self, runtime: AgentRuntime, one_valid_role: str) -> None:
        """Test that agents are cached on repeated calls."""
        agent1 = runtime.get_agent(one_valid_role)
        agent2 = runtime.get_agent(one_valid_role)

        # Should be the same object due to caching
        assert agent1 is agent2

    def test_get_prompts_known_role(self, runtime: AgentRuntime, one_valid_role: str) -> None:
        """Test retrieving prompts for a known valid role."""
        prompts = runtime.get_prompts(one_valid_role)

        assert isinstance(prompts, AgentPrompts)
        assert prompts.is_complete()

    def test_get_prompts_unknown_role(self, runtime: AgentRuntime) -> None:
        """Test that getting prompts for unknown role raises AgentNotFoundError."""
        with pytest.raises(AgentNotFoundError):
            runtime.get_prompts("NONEXISTENT_ROLE_XYZ")

    def test_prepare_prompt_valid_task(self, runtime: AgentRuntime, one_valid_role: str) -> None:
        """Test preparing a prompt for a valid task."""
        task = AgentTask(role_name=one_valid_role, instruction="Do something important")
        prompt_data = runtime.prepare_prompt(task)

        # Verify structure
        expected_keys = {
            "role_name",
            "system_prompt",
            "onboarding_prompt",
            "knowledge_scope",
            "checklist",
            "instruction",
            "context",
            "metadata",
        }
        assert set(prompt_data.keys()) == expected_keys

        # Verify values
        assert prompt_data["role_name"] == one_valid_role
        assert prompt_data["instruction"] == "Do something important"
        assert isinstance(prompt_data["context"], dict)
        assert isinstance(prompt_data["metadata"], dict)

    def test_prepare_prompt_with_context_and_metadata(self, runtime: AgentRuntime, one_valid_role: str) -> None:
        """Test preparing a prompt with context and metadata."""
        context = {"file": "test.py", "line": 42}
        metadata = {"priority": "high", "trace_id": "abc123"}

        task = AgentTask(
            role_name=one_valid_role,
            instruction="Fix this",
            context=context,
            metadata=metadata,
        )

        prompt_data = runtime.prepare_prompt(task)

        assert prompt_data["context"] == context
        assert prompt_data["metadata"] == metadata

    def test_prepare_prompt_invalid_role(self, runtime: AgentRuntime) -> None:
        """Test that preparing prompt with invalid role raises AgentPromptError."""
        task = AgentTask(role_name="NONEXISTENT_ROLE_XYZ", instruction="Do something")

        with pytest.raises(AgentNotFoundError):
            runtime.prepare_prompt(task)

    def test_prepare_prompt_fields_populated(self, runtime: AgentRuntime, one_valid_role: str) -> None:
        """Test that prepared prompt has all expected fields with non-empty content."""
        task = AgentTask(role_name=one_valid_role, instruction="Test instruction")
        prompt_data = runtime.prepare_prompt(task)

        # Verify core prompts are non-empty strings
        assert isinstance(prompt_data["system_prompt"], str)
        assert len(prompt_data["system_prompt"].strip()) > 0

        assert isinstance(prompt_data["onboarding_prompt"], str)
        assert len(prompt_data["onboarding_prompt"].strip()) > 0

        assert isinstance(prompt_data["knowledge_scope"], str)
        assert len(prompt_data["knowledge_scope"].strip()) > 0

        assert isinstance(prompt_data["checklist"], str)
        assert len(prompt_data["checklist"].strip()) > 0

    def test_clear_cache(self, runtime: AgentRuntime) -> None:
        """Test clearing the runtime cache."""
        roles = runtime.list_roles()
        if roles:
            # Load an agent to populate cache
            runtime.get_agent(roles[0])

        # Clear cache
        runtime.clear_cache()

        # After clearing, listing roles again should work
        roles_after = runtime.list_roles()
        assert roles == roles_after

    def test_all_roles_are_valid_strings(self, runtime: AgentRuntime) -> None:
        """Test that all listed roles are non-empty strings with valid naming."""
        roles = runtime.list_roles()

        for role in roles:
            assert isinstance(role, str)
            assert len(role) > 0
            assert not role.startswith(".")
            # Role names should be uppercase with underscores (common pattern)
            assert role == role.upper()
