"""
ChainBridge Agent Loader

Utility module for loading and managing agent configurations from the AGENTS directory.
Each agent has specialized prompts and knowledge scope for different roles in the development team.

Usage:
    from tools.agent_loader import load_agent, list_agents, get_agent_prompt

    # Load a specific agent
    agent = load_agent("FRONTEND_SONNY")

    # List all available agents
    agents = list_agents()

    # Get formatted prompt for an agent
    prompt = get_agent_prompt("BACKEND_CODY", include_knowledge=True)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

# Base directory for agent configurations
REPO_ROOT = Path(__file__).parent.parent
AGENTS_BASE_DIR = REPO_ROOT / "AGENTS"

# Required files for each agent
REQUIRED_FILES = [
    "system_prompt.md",
    "onboarding_prompt.md",
    "knowledge_scope.md",
    "checklist.md",
]


class AgentConfig:
    """Configuration for a single agent role."""

    def __init__(self, role_name: str, base_path: Path):
        self.role_name = role_name
        self.base_path = base_path
        self.system_prompt = ""
        self.onboarding_prompt = ""
        self.knowledge_scope = ""
        self.checklist = ""

        self._load_files()

    def _load_files(self) -> None:
        """Load all markdown files for this agent."""
        files = {
            "system_prompt": self.base_path / "system_prompt.md",
            "onboarding_prompt": self.base_path / "onboarding_prompt.md",
            "knowledge_scope": self.base_path / "knowledge_scope.md",
            "checklist": self.base_path / "checklist.md",
        }

        for attr, file_path in files.items():
            if file_path.exists():
                setattr(self, attr, file_path.read_text(encoding="utf-8"))
            else:
                print(f"Warning: Missing {file_path.name} for {self.role_name}")

    def get_full_prompt(self, include_knowledge: bool = True, include_checklist: bool = False) -> str:
        """Get formatted prompt combining system, onboarding, and optionally knowledge/checklist."""
        parts = [
            self.system_prompt,
            self.onboarding_prompt,
        ]

        if include_knowledge and self.knowledge_scope:
            parts.append(f"\n## Knowledge Scope\n\n{self.knowledge_scope}")

        if include_checklist and self.checklist:
            parts.append(f"\n## Task Checklist\n\n{self.checklist}")

        return "\n\n".join(filter(None, parts))

    def __repr__(self) -> str:
        return f"AgentConfig(role={self.role_name})"


def list_agents() -> List[str]:
    """List all available agent roles."""
    if not AGENTS_BASE_DIR.exists():
        return []

    agents = []
    for item in AGENTS_BASE_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            agents.append(item.name)

    return sorted(agents)


def load_agent(role_name: str) -> Optional[AgentConfig]:
    """Load configuration for a specific agent role."""
    agent_path = AGENTS_BASE_DIR / role_name

    if not agent_path.exists():
        print(f"Error: Agent directory not found: {agent_path}")
        return None

    if not agent_path.is_dir():
        print(f"Error: {agent_path} is not a directory")
        return None

    return AgentConfig(role_name, agent_path)


def get_agent_prompt(role_name: str, include_knowledge: bool = True, include_checklist: bool = False) -> str:
    """Get formatted prompt for an agent role."""
    agent = load_agent(role_name)
    if not agent:
        return f"Error: Agent '{role_name}' not found"

    return agent.get_full_prompt(include_knowledge, include_checklist)


def validate_agent_structure(role_name: str) -> Dict[str, bool]:
    """Validate that an agent has all required files."""
    agent_path = AGENTS_BASE_DIR / role_name

    if not agent_path.exists():
        return {"exists": False}

    results = {"exists": True}
    for required_file in REQUIRED_FILES:
        file_path = agent_path / required_file
        results[required_file] = file_path.exists()

    return results


def validate_all_agents() -> Dict[str, Dict[str, bool]]:
    """Validate structure for all agents."""
    agents = list_agents()
    return {agent: validate_agent_structure(agent) for agent in agents}


def dump_all_agents_to_json(output_path: Optional[str] = None) -> Optional[str]:
    """Export all agent configs and prompts to JSON.

    Args:
        output_path: Optional file path to write JSON to. If None, returns JSON string.

    Returns:
        JSON string if output_path is None, otherwise None (writes to file).
    """
    agents = list_agents()
    agents_data = {}

    for role_name in agents:
        agent_config = load_agent(role_name)
        if agent_config:
            agents_data[role_name] = {
                "system_prompt": agent_config.system_prompt,
                "onboarding_prompt": agent_config.onboarding_prompt,
                "knowledge_scope": agent_config.knowledge_scope,
                "checklist": agent_config.checklist,
            }

    # Convert to JSON
    json_str = json.dumps(agents_data, indent=2)

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json_str, encoding="utf-8")
        return None

    return json_str


if __name__ == "__main__":
    # CLI interface for testing
    import sys

    if len(sys.argv) < 2:
        print("Available agents:")
        for agent in list_agents():
            print(f"  - {agent}")
        print("\nUsage: python agent_loader.py <AGENT_NAME>")
        sys.exit(0)

    role = sys.argv[1]
    agent = load_agent(role)

    if agent:
        print(f"\n{'='*60}")
        print(f"Agent: {role}")
        print(f"{'='*60}\n")
        print(agent.get_full_prompt(include_knowledge=True, include_checklist=True))
    else:
        print(f"Failed to load agent: {role}")
        sys.exit(1)
