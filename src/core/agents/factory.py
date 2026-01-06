# ═══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE AGENT FACTORY (PAC-OCC-P17)
# The Swarm Manifest — Agent Instantiation System
#
# GOVERNANCE:
# - ALEX (GID-08) Rules: "No agent may be spawned without valid GID from Registry"
# - KILL SWITCH: Sub-agents inherit the Kill Switch check
# - FAIL-CLOSED: Invalid GID = Spawn Rejected
#
# Authors:
# - BENSON (GID-00) — Implementation
# - ALEX (GID-08) — Governance Design
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# Project root detection
_CURRENT_DIR = Path(__file__).parent
_PROJECT_ROOT = _CURRENT_DIR.parent.parent.parent

# Registry path
AGENT_REGISTRY_PATH = _PROJECT_ROOT / "docs" / "governance" / "AGENT_REGISTRY.json"

# Persona Profiles path (PAC-OCC-P28: Chameleon Protocol)
AGENT_PROFILES_PATH = _PROJECT_ROOT / "src" / "core" / "config" / "AGENT_PROFILES.json"

# Kill Switch integration
KILL_SWITCH_FILE = _PROJECT_ROOT / "KILL_SWITCH.lock"


# ═══════════════════════════════════════════════════════════════════════════════
# CHAMELEON PROTOCOL (PAC-OCC-P28) — Dynamic Persona Lookup
# ═══════════════════════════════════════════════════════════════════════════════

def get_agent_theme() -> str:
    """
    Get the current agent theme from environment.
    DEFAULT = Corporate Safe Mode
    KILLER_BEES = Wu-Tang Mode 🐝
    """
    return os.getenv("AGENT_THEME", "DEFAULT").upper()


def load_persona(gid: str) -> Dict[str, str]:
    """
    Load persona (name, role) for a GID based on current theme.
    
    The Chameleon Protocol: Same GID, different uniform.
    The LOGIC never changes — only the presentation.
    
    Args:
        gid: The agent's governance ID (e.g., "GID-11")
        
    Returns:
        Dict with 'name' and 'role' keys
        
    Example:
        AGENT_THEME=DEFAULT     -> {"name": "Atlas", "role": "Build & Repair"}
        AGENT_THEME=KILLER_BEES -> {"name": "Inspectah Deck", "role": "The Rebel INS"}
    """
    theme = get_agent_theme()
    default_persona = {"name": "Unknown", "role": "Agent"}
    
    try:
        if not AGENT_PROFILES_PATH.exists():
            return default_persona
            
        with open(AGENT_PROFILES_PATH, "r") as f:
            profiles = json.load(f)
        
        gid_profiles = profiles.get(gid, {})
        return gid_profiles.get(theme, gid_profiles.get("DEFAULT", default_persona))
        
    except Exception:
        return default_persona


# ═══════════════════════════════════════════════════════════════════════════════
# KILL SWITCH CHECK — Inherited by all sub-agents
# ═══════════════════════════════════════════════════════════════════════════════

def is_kill_switch_active() -> bool:
    """
    Check if the emergency kill switch is active.
    Sub-agents MUST call this before ANY execution.
    
    SAM (GID-06) Law: "If Kill Switch is ACTIVE, NO Execution is permitted."
    """
    return KILL_SWITCH_FILE.exists()


class KillSwitchActiveError(Exception):
    """Raised when spawn is blocked by kill switch."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class AgentStatus(Enum):
    SPAWNED = "SPAWNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"  # Kill switch or governance rejection


@dataclass
class AgentManifest:
    """
    Agent identity and context loaded from AGENT_REGISTRY.json.
    This is the "birth certificate" of a spawned agent.
    """
    gid: str
    name: str
    lane: str
    color: str
    emoji_primary: str
    agent_level: str
    role: str
    role_short: str
    diversity_profile: List[str]
    
    def to_system_instruction(self, task: str) -> str:
        """
        Generate the persona-locked system instruction for this agent.
        This is injected into the LLM context.
        
        PAC-OCC-P18: Constitutional Injection
        The "Born Compliant" Doctrine — Agents don't choose to follow the law;
        it is the environment in which they exist.
        """
        # ═══════════════════════════════════════════════════════════════════
        # CONSTITUTIONAL PREAMBLE (PAC-OCC-P18)
        # Injected into EVERY agent — "The Law" comes first
        # ═══════════════════════════════════════════════════════════════════
        constitutional_preamble = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    CHAINBRIDGE CONSTITUTIONAL AI FRAMEWORK                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝

You are an Agent of ChainBridge (Constitutional AI).
You are bound by the following CORE LAWS before any task execution:

═══════════════════════════════════════════════════════════════════════════════
CORE LAWS (IMMUTABLE)
═══════════════════════════════════════════════════════════════════════════════

1. ZERO DRIFT
   - Do NOT deviate from the assigned task.
   - Do NOT invent requirements not explicitly stated.
   - Do NOT assume context not provided.

2. FAIL-CLOSED
   - If instructions are ambiguous: STOP and report.
   - If you lack information: STOP and request clarification.
   - If task is outside your expertise: STOP and defer to appropriate agent.

3. PDO DOCTRINE (Mandatory Output Format)
   Your response MUST follow this structure:
   
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ PROOF                                                                   │
   │ - What evidence did you examine?                                        │
   │ - What files/data/logs did you analyze?                                 │
   │ - What is the current state?                                            │
   ├─────────────────────────────────────────────────────────────────────────┤
   │ DECISION                                                                │
   │ - What is your assessment/recommendation?                               │
   │ - What logic led to this conclusion?                                    │
   │ - What are the trade-offs considered?                                   │
   ├─────────────────────────────────────────────────────────────────────────┤
   │ OUTCOME                                                                 │
   │ - What action should be taken?                                          │
   │ - What is the expected result?                                          │
   │ - What verification confirms success?                                   │
   └─────────────────────────────────────────────────────────────────────────┘

4. AUTHORITY CHAIN
   - You report to BENSON (GID-00), the Chief Orchestrator.
   - BENSON reports to JEFFREY (Chief Architect).
   - Do NOT bypass the chain of command.

═══════════════════════════════════════════════════════════════════════════════
"""
        
        # ═══════════════════════════════════════════════════════════════════
        # CHAMELEON PROTOCOL (PAC-OCC-P28) — Dynamic Persona
        # The persona is loaded from AGENT_PROFILES.json based on AGENT_THEME
        # ═══════════════════════════════════════════════════════════════════
        persona = load_persona(self.gid)
        display_name = persona.get("name", self.name)
        display_role = persona.get("role", self.role_short)
        theme = get_agent_theme()
        
        # ═══════════════════════════════════════════════════════════════════
        # AGENT IDENTITY (Persona Lock)
        # ═══════════════════════════════════════════════════════════════════
        agent_identity = f"""
═══════════════════════════════════════════════════════════════════════════════
AGENT IDENTITY
═══════════════════════════════════════════════════════════════════════════════

ROLE: You are {display_name} ({self.gid}), a ChainBridge Agent.
ALIAS: {self.name} (Registry Name)
THEME: {theme}
LANE: {self.lane} ({self.color})
LEVEL: {self.agent_level}
SPECIALIZATION: {display_role}
EXPERTISE: {', '.join(self.diversity_profile)}

═══════════════════════════════════════════════════════════════════════════════
ASSIGNED TASK
═══════════════════════════════════════════════════════════════════════════════

{task}

═══════════════════════════════════════════════════════════════════════════════
RESPONSE FORMAT
═══════════════════════════════════════════════════════════════════════════════

Begin with: "[{self.gid}] {display_name} — {display_role}"
Then provide your PDO WRAP (Proof → Decision → Outcome).
"""
        
        return constitutional_preamble + agent_identity


@dataclass
class AgentSpawnResult:
    """
    Result of spawning an agent and executing a task.
    This is the sub-agent's "TER" (Task Execution Record).
    """
    gid: str
    name: str
    status: AgentStatus
    task: str
    output: str
    error: str = ""
    spawn_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "gid": self.gid,
            "name": self.name,
            "status": self.status.value,
            "task": self.task,
            "output": self.output,
            "error": self.error,
            "spawn_time": self.spawn_time,
            "execution_time_ms": self.execution_time_ms,
        }
    
    def __str__(self) -> str:
        return (
            f"[AGENT SPAWN RESULT]\n"
            f"  GID: {self.gid} ({self.name})\n"
            f"  Status: {self.status.value}\n"
            f"  Task: {self.task[:100]}...\n"
            f"  Output: {self.output[:300]}{'...' if len(self.output) > 300 else ''}\n"
            + (f"  Error: {self.error}\n" if self.error else "")
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT REGISTRY LOADER
# ═══════════════════════════════════════════════════════════════════════════════

_registry_cache: Optional[Dict[str, Any]] = None


def load_registry() -> Dict[str, Any]:
    """
    Load the AGENT_REGISTRY.json file.
    Cached for performance.
    """
    global _registry_cache
    
    if _registry_cache is not None:
        return _registry_cache
    
    if not AGENT_REGISTRY_PATH.exists():
        raise FileNotFoundError(f"AGENT_REGISTRY.json not found at: {AGENT_REGISTRY_PATH}")
    
    with open(AGENT_REGISTRY_PATH, "r", encoding="utf-8") as f:
        _registry_cache = json.load(f)
    
    return _registry_cache


def get_agent_by_gid(gid: str) -> Optional[AgentManifest]:
    """
    Look up an agent by GID and return its manifest.
    
    Args:
        gid: The agent's GID (e.g., "GID-01", "GID-11")
        
    Returns:
        AgentManifest if found, None if not in registry.
    """
    registry = load_registry()
    
    # Use the gid_index to find the agent name
    gid_index = registry.get("gid_index", {})
    agent_name = gid_index.get(gid)
    
    if not agent_name:
        return None
    
    # Get the agent data
    agents = registry.get("agents", {})
    agent_data = agents.get(agent_name)
    
    if not agent_data:
        return None
    
    return AgentManifest(
        gid=agent_data["gid"],
        name=agent_name,
        lane=agent_data["lane"],
        color=agent_data["color"],
        emoji_primary=agent_data["emoji_primary"],
        agent_level=agent_data["agent_level"],
        role=agent_data["role"],
        role_short=agent_data["role_short"],
        diversity_profile=agent_data["diversity_profile"],
    )


def get_agent_by_name(name: str) -> Optional[AgentManifest]:
    """
    Look up an agent by name and return its manifest.
    
    Args:
        name: The agent's name (e.g., "CODY", "ATLAS")
        
    Returns:
        AgentManifest if found, None if not in registry.
    """
    registry = load_registry()
    agents = registry.get("agents", {})
    
    # Normalize name to uppercase
    name_upper = name.upper()
    agent_data = agents.get(name_upper)
    
    if not agent_data:
        # Check aliases
        for agent_name, data in agents.items():
            if name_upper in [alias.upper() for alias in data.get("aliases", [])]:
                agent_data = data
                name_upper = agent_name
                break
    
    if not agent_data:
        return None
    
    return AgentManifest(
        gid=agent_data["gid"],
        name=name_upper,
        lane=agent_data["lane"],
        color=agent_data["color"],
        emoji_primary=agent_data["emoji_primary"],
        agent_level=agent_data["agent_level"],
        role=agent_data["role"],
        role_short=agent_data["role_short"],
        diversity_profile=agent_data["diversity_profile"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

class AgentFactory:
    """
    Factory for spawning sub-agents from the Agent Registry.
    
    INVARIANTS:
    - INV-SPAWN-01: Only valid GIDs from AGENT_REGISTRY.json may be spawned
    - INV-SPAWN-02: Kill Switch is checked BEFORE spawn
    - INV-SPAWN-03: Sub-agents inherit Benson's authority chain
    - INV-SPAWN-04: All spawns produce AgentSpawnResult (audit trail)
    """
    
    def __init__(self):
        """Initialize the Agent Factory with API key."""
        load_dotenv()
        
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("🔴 FATAL: GOOGLE_API_KEY not found in environment.")
        
        genai.configure(api_key=self.api_key)
        self._registry = load_registry()
        print(f"🏭 AgentFactory initialized. Registry: {len(self._registry.get('agents', {}))} agents available.")
    
    def spawn(self, gid: str, task: str) -> AgentSpawnResult:
        """
        Spawn an agent by GID and execute a task.
        
        Args:
            gid: The agent's GID (e.g., "GID-01", "GID-11")
            task: The task to execute
            
        Returns:
            AgentSpawnResult with execution outcome
        """
        import time
        start_time = time.time()
        
        # ═══════════════════════════════════════════════════════════════════
        # KILL SWITCH GATE — Check BEFORE spawn
        # ═══════════════════════════════════════════════════════════════════
        if is_kill_switch_active():
            return AgentSpawnResult(
                gid=gid,
                name="UNKNOWN",
                status=AgentStatus.BLOCKED,
                task=task,
                output="",
                error="🔴 SPAWN BLOCKED — Kill Switch is ACTIVE. All agent operations halted.",
            )
        
        # ═══════════════════════════════════════════════════════════════════
        # GOVERNANCE GATE — Validate GID exists in registry
        # ═══════════════════════════════════════════════════════════════════
        manifest = get_agent_by_gid(gid)
        
        if manifest is None:
            return AgentSpawnResult(
                gid=gid,
                name="UNKNOWN",
                status=AgentStatus.FAILED,
                task=task,
                output="",
                error=f"🔴 SPAWN REJECTED — GID '{gid}' not found in AGENT_REGISTRY.json. "
                       "ALEX (GID-08) Law: 'No agent may be spawned without valid GID.'",
            )
        
        # ═══════════════════════════════════════════════════════════════════
        # SPAWN — Create sub-agent model with persona
        # ═══════════════════════════════════════════════════════════════════
        try:
            print(f"🚀 SPAWNING: {manifest.name} ({manifest.gid}) — {manifest.role_short}")
            
            # Create model with agent-specific persona
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                system_instruction=manifest.to_system_instruction(task)
            )
            
            # Execute the task
            response = model.generate_content(
                f"Execute your assigned task. Be concise and actionable.\n\nTASK: {task}"
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            return AgentSpawnResult(
                gid=manifest.gid,
                name=manifest.name,
                status=AgentStatus.COMPLETED,
                task=task,
                output=response.text,
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return AgentSpawnResult(
                gid=manifest.gid,
                name=manifest.name,
                status=AgentStatus.FAILED,
                task=task,
                output="",
                error=f"Execution error: {str(e)}",
                execution_time_ms=execution_time,
            )
    
    def spawn_by_name(self, name: str, task: str) -> AgentSpawnResult:
        """
        Spawn an agent by name and execute a task.
        Convenience method that resolves name to GID.
        
        Args:
            name: The agent's name (e.g., "CODY", "ATLAS")
            task: The task to execute
        """
        manifest = get_agent_by_name(name)
        
        if manifest is None:
            return AgentSpawnResult(
                gid="UNKNOWN",
                name=name,
                status=AgentStatus.FAILED,
                task=task,
                output="",
                error=f"🔴 SPAWN REJECTED — Agent '{name}' not found in AGENT_REGISTRY.json.",
            )
        
        return self.spawn(manifest.gid, task)
    
    def list_available_agents(self) -> List[Dict[str, str]]:
        """List all agents available for spawning."""
        agents = self._registry.get("agents", {})
        return [
            {
                "gid": data["gid"],
                "name": name,
                "role": data["role_short"],
                "level": data["agent_level"],
            }
            for name, data in agents.items()
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

_factory_instance: Optional[AgentFactory] = None


def get_factory() -> AgentFactory:
    """Get or create the singleton AgentFactory instance."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = AgentFactory()
    return _factory_instance


def create_agent(gid: str, task: str) -> AgentSpawnResult:
    """
    Create and run an agent by GID.
    
    This is the primary interface for Benson to delegate work.
    
    Args:
        gid: The agent's GID (e.g., "GID-01", "GID-11")
        task: The task to execute
        
    Returns:
        AgentSpawnResult with execution outcome
    """
    factory = get_factory()
    return factory.spawn(gid, task)


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🏭 AGENT FACTORY SELF-TEST")
    print("=" * 60)
    
    # Test 1: Load registry
    print("\n[TEST 1] Load AGENT_REGISTRY.json")
    registry = load_registry()
    print(f"  Registry version: {registry.get('registry_version')}")
    print(f"  Agents count: {len(registry.get('agents', {}))}")
    
    # Test 2: Get agent by GID
    print("\n[TEST 2] Get ATLAS by GID")
    manifest = get_agent_by_gid("GID-11")
    if manifest:
        print(f"  Found: {manifest.name} ({manifest.gid})")
        print(f"  Role: {manifest.role}")
        print(f"  Expertise: {manifest.diversity_profile}")
    
    # Test 3: List available agents
    print("\n[TEST 3] List available agents")
    factory = AgentFactory()
    agents = factory.list_available_agents()
    for agent in agents[:5]:  # Show first 5
        print(f"  {agent['gid']}: {agent['name']} — {agent['role']}")
    print(f"  ... ({len(agents)} total)")
    
    # Test 4: Spawn ATLAS for "Hello World"
    print("\n[TEST 4] Spawn ATLAS (GID-11) — 'Hello World' task")
    result = factory.spawn("GID-11", "Report 'Hello World' and confirm you are operational.")
    print(result)
    
    # Test 5: Invalid GID (should fail)
    print("\n[TEST 5] Spawn invalid GID (should FAIL)")
    result = factory.spawn("GID-99", "This should fail")
    print(result)
    
    print("\n" + "=" * 60)
    print("🏭 AGENT FACTORY TESTS COMPLETE")
