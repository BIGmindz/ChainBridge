"""
ChainBridge Agent Orchestration Runtime

Provides a modular, LLM-agnostic runtime for orchestrating AI agents based on the AGENTS directory.
The runtime loads agent configurations, prepares prompts, and manages agent task execution context.

This module is designed to be integrated with LLM providers (Gemini, Claude, LangGraph, etc.)
and does NOT implement actual LLM calls—it prepares the data structures needed to call them.

Example:
    from tools.agent_runtime import AgentRuntime, AgentTask

    runtime = AgentRuntime()
    roles = runtime.list_roles()

    task = AgentTask(
        role_name="FRONTEND_SONNY",
        instruction="Build a responsive control panel for ChainBoard",
        context={"current_file": "chainboard-ui/src/index.tsx"}
    )

    prompt_data = runtime.prepare_prompt(task)
    # Now pass prompt_data to your LLM provider
"""

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from tools.agent_loader import (
    AGENTS_BASE_DIR,
    AgentConfig,
    list_agents,
    load_agent,
)

logger = logging.getLogger(__name__)


class AgentRuntimeError(Exception):
    """Base exception for agent runtime errors."""


class AgentNotFoundError(AgentRuntimeError):
    """Raised when an agent role cannot be found."""


class AgentPromptError(AgentRuntimeError):
    """Raised when agent prompts are missing or malformed."""


@dataclass
class AgentTask:
    """Represents a concrete task for an agent to perform.

    Attributes:
        role_name: The agent role (e.g., "FRONTEND_SONNY").
        instruction: The specific task or instruction for the agent.
        context: Optional context dict with additional information (e.g., files, state).
        metadata: Optional metadata for tracking, logging, or filtering.
    """

    role_name: str
    instruction: str
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate task fields after initialization."""
        if not self.role_name or not self.role_name.strip():
            raise ValueError("role_name must be a non-empty string")
        if not self.instruction or not self.instruction.strip():
            raise ValueError("instruction must be a non-empty string")


@dataclass
class AgentPrompts:
    """Structured prompts for an agent.

    Attributes:
        system_prompt: The core system/role definition prompt.
        onboarding_prompt: Onboarding and workflow-oriented prompt.
        knowledge_scope: Knowledge boundaries and expertise areas.
        checklist: Quick reference checklist for the role.
    """

    system_prompt: str
    onboarding_prompt: str
    knowledge_scope: str
    checklist: str

    def is_complete(self) -> bool:
        """Check if all required prompts are non-empty."""
        return all(
            [
                self.system_prompt.strip(),
                self.onboarding_prompt.strip(),
                self.knowledge_scope.strip(),
                self.checklist.strip(),
            ]
        )


@dataclass
class AgentResult:
    """Represents the result from an agent execution.

    Attributes:
        role_name: The agent role that executed.
        success: Whether the task completed successfully.
        output: The main output or result from the agent.
        metadata: Optional metadata, timestamps, execution info, etc.
        errors: List of error messages if execution failed.
    """

    role_name: str
    success: bool
    output: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class AgentRuntime:
    """Orchestration runtime for ChainBridge AI agents.

    The runtime manages:
    - Loading and caching agent configurations
    - Preparing prompt data for LLM calls
    - Managing agent task context and metadata
    - Validating agent roles and prompts

    This is LLM-agnostic; actual LLM calls are delegated to higher-level orchestrators.
    """

    def __init__(self) -> None:
        """Initialize the agent runtime."""
        self._agents_cache: Dict[str, AgentConfig] = {}
        self._roles_cache: Optional[List[str]] = None
        logger.debug("AgentRuntime initialized. AGENTS_BASE_DIR: %s", AGENTS_BASE_DIR)

    def list_roles(self) -> List[str]:
        """List all available agent roles.

        Returns:
            A sorted list of agent role names.
        """
        if self._roles_cache is None:
            self._roles_cache = list_agents()
            logger.debug("Loaded %d agent roles", len(self._roles_cache))
        return self._roles_cache

    def get_agent(self, role_name: str) -> AgentConfig:
        """Retrieve a specific agent configuration.

        Args:
            role_name: The agent role name (e.g., "FRONTEND_SONNY").

        Returns:
            The AgentConfig for the given role.

        Raises:
            AgentNotFoundError: If the role does not exist.
        """
        if role_name in self._agents_cache:
            return self._agents_cache[role_name]

        agent = load_agent(role_name)
        if agent is None:
            available = ", ".join(self.list_roles())
            raise AgentNotFoundError(f"Agent role '{role_name}' not found. Available roles: {available}")

        self._agents_cache[role_name] = agent
        logger.debug("Loaded agent: %s", role_name)
        return agent

    def get_prompts(self, role_name: str) -> AgentPrompts:
        """Retrieve structured prompts for an agent.

        Args:
            role_name: The agent role name.

        Returns:
            An AgentPrompts dataclass with all four prompt components.

        Raises:
            AgentNotFoundError: If the role does not exist.
            AgentPromptError: If any required prompt is missing.
        """
        agent = self.get_agent(role_name)
        agent_prompts = AgentPrompts(
            system_prompt=agent.system_prompt,
            onboarding_prompt=agent.onboarding_prompt,
            knowledge_scope=agent.knowledge_scope,
            checklist=agent.checklist,
        )

        if not agent_prompts.is_complete():
            missing = [k for k, v in asdict(agent_prompts).items() if not v.strip()]
            raise AgentPromptError(f"Agent '{role_name}' has missing or empty prompts: {missing}")

        return agent_prompts

    def prepare_prompt(self, task: AgentTask) -> Dict[str, Any]:
        """Prepare a complete prompt data structure for an LLM call.

        This method assembles all necessary information for an LLM provider to execute
        the task. The resulting dict is JSON-serializable and includes:
        - All four agent prompts
        - The specific task instruction
        - Additional context and metadata

        Args:
            task: The AgentTask to prepare.

        Returns:
            A dict with keys:
            - system_prompt, onboarding_prompt, knowledge_scope, checklist (str)
            - instruction, context, metadata (as provided in task)
            - role_name, task_id (for tracking)

        Raises:
            AgentNotFoundError: If the role does not exist.
            AgentPromptError: If prompts are incomplete.
        """
        # Validate the task
        if not task.role_name or not task.instruction:
            raise ValueError("task.role_name and task.instruction are required")

        # Retrieve agent prompts
        try:
            agent_prompts = self.get_prompts(task.role_name)
        except (AgentNotFoundError, AgentPromptError) as e:
            logger.error("Failed to prepare prompt for %s: %s", task.role_name, e)
            raise

        # Build the prompt data structure
        prompt_data = {
            "role_name": task.role_name,
            "system_prompt": agent_prompts.system_prompt,
            "onboarding_prompt": agent_prompts.onboarding_prompt,
            "knowledge_scope": agent_prompts.knowledge_scope,
            "checklist": agent_prompts.checklist,
            "instruction": task.instruction,
            "context": task.context or {},
            "metadata": task.metadata or {},
        }

        logger.debug("Prepared prompt for %s: %d chars in instruction", task.role_name, len(task.instruction))
        return prompt_data

    def validate_all_agents(self) -> Dict[str, bool]:
        """Validate that all agent roles are properly configured.

        Returns:
            A dict mapping role names to validation status (True = valid, False = invalid).
        """
        results = {}
        for role_name in self.list_roles():
            try:
                self.get_prompts(role_name)
                results[role_name] = True
                logger.debug("Validation passed: %s", role_name)
            except (AgentNotFoundError, AgentPromptError) as e:
                results[role_name] = False
                logger.warning("Validation failed for %s: %s", role_name, e)

        return results

    def clear_cache(self) -> None:
        """Clear internal caches (useful for testing or reloading)."""
        self._agents_cache.clear()
        self._roles_cache = None
        logger.debug("Agent runtime caches cleared")


if __name__ == "__main__":
    # Local debugging: print agent loading info
    logging.basicConfig(level=logging.DEBUG)

    runtime = AgentRuntime()
    roles = runtime.list_roles()

    print(f"\n{'='*60}")
    print(f"Agent Runtime Loaded {len(roles)} Roles")
    print(f"{'='*60}\n")

    if roles:
        print("Available roles (first 5):")
        for role in roles[:5]:
            print(f"  • {role}")
        if len(roles) > 5:
            print(f"  ... and {len(roles) - 5} more")

        print(f"\nTotal: {len(roles)} roles")

        # Validate all agents
        print("Validating all agents...")
        validation = runtime.validate_all_agents()
        valid_count = sum(1 for v in validation.values() if v)
        print(f"✓ {valid_count}/{len(validation)} agents valid")

        # Show details for first agent as example
        first_role = roles[0]
        print(f"\n--- Example: {first_role} ---")
        try:
            prompts = runtime.get_prompts(first_role)
            print(f"System prompt length: {len(prompts.system_prompt)} chars")
            print(f"Onboarding prompt length: {len(prompts.onboarding_prompt)} chars")
            print(f"Knowledge scope length: {len(prompts.knowledge_scope)} chars")
            print(f"Checklist length: {len(prompts.checklist)} chars")
        except AgentPromptError as e:
            print(f"Error: {e}")
    else:
        print("No agents found. Check AGENTS directory.")
