"""
ChainBridge Agent Configuration Validator

Validates that all agent roles in the AGENTS directory are properly configured
with complete and non-empty prompt files.

This validator is designed to run in CI/CD pipelines and during local development
to ensure agent configurations remain consistent and complete.

Usage:
    python -m tools.agent_validate

Exit codes:
    0 — All agents valid
    1 — At least one agent is invalid
"""

import logging
from typing import Dict

from tools.agent_loader import list_agents, load_agent, validate_agent_structure

logger = logging.getLogger(__name__)

# Required files for each agent
REQUIRED_FILES = [
    "system_prompt.md",
    "onboarding_prompt.md",
    "knowledge_scope.md",
    "checklist.md",
]


def validate_agent_completeness(role_name: str) -> bool:
    """Validate that an agent has all required files with content.

    Args:
        role_name: The agent role name (e.g., "FRONTEND_SONNY").

    Returns:
        True if the agent is complete and valid, False otherwise.
    """
    agent = load_agent(role_name)

    if agent is None:
        logger.error("Failed to load agent: %s", role_name)
        return False

    # Check that all prompts are non-empty
    prompts = {
        "system_prompt": agent.system_prompt,
        "onboarding_prompt": agent.onboarding_prompt,
        "knowledge_scope": agent.knowledge_scope,
        "checklist": agent.checklist,
    }

    all_complete = True
    for prompt_name, prompt_content in prompts.items():
        if not prompt_content or not prompt_content.strip():
            logger.error(
                "Agent '%s' has empty %s",
                role_name,
                prompt_name,
            )
            all_complete = False

    return all_complete


def get_validation_results() -> tuple[int, int, list[str]]:
    """Get validation results for all agents.

    Returns:
        Tuple of (valid_count, total_count, list of invalid role names).
    """
    agents = list_agents()

    if not agents:
        logger.error("No agents found in AGENTS directory")
        return 0, 0, []

    # Validate structure for all agents
    structure_validation = {role: validate_agent_structure(role) for role in agents}

    # Validate content completeness
    content_validation = {role: validate_agent_completeness(role) for role in agents}

    # Collect results
    results: Dict[str, Dict[str, bool]] = {}
    for role in agents:
        results[role] = {
            "structure": structure_validation.get(role, {}).get("exists", False),
            "content": content_validation.get(role, False),
        }

    # Count valid and invalid
    valid_count = 0
    invalid_roles = []

    for role, validation_result in results.items():
        if validation_result["structure"] and validation_result["content"]:
            valid_count += 1
            logger.debug("✓ %s", role)
        else:
            invalid_roles.append(role)
            if not validation_result["structure"]:
                logger.error("✗ %s — structure invalid", role)
            if not validation_result["content"]:
                logger.error("✗ %s — content incomplete", role)

    return valid_count, len(agents), invalid_roles


def main() -> int:
    """Validate all agents in the AGENTS directory.

    Returns:
        0 if all agents are valid, 1 otherwise.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    logger.info("Validating agents...")

    valid_count, total_count, invalid_roles = get_validation_results()

    # Summary
    logger.info("")
    logger.info("Validation Results: %d/%d agents valid", valid_count, total_count)

    if invalid_roles:
        logger.error("Invalid agents: %s", ", ".join(invalid_roles))
        return 1

    logger.info("All agents are valid ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
