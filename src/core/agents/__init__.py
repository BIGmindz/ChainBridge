# ═══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE AGENT SWARM MODULE
# PAC-OCC-P17: The Swarm Manifest
# ═══════════════════════════════════════════════════════════════════════════════

from .factory import AgentFactory, create_agent, AgentManifest, AgentSpawnResult

__all__ = [
    "AgentFactory",
    "create_agent",
    "AgentManifest",
    "AgentSpawnResult",
]
