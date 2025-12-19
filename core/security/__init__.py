"""
core/security - Security Controls Module

PAC-SAM-PROOF-INTEGRITY-01

Security controls for execution spine:
- Replay attack detection
- Event deduplication
- Integrity validation
"""

from core.security.replay_guard import (
    ReplayAttackError,
    ReplayGuard,
    get_replay_guard,
)

__all__ = [
    "ReplayAttackError",
    "ReplayGuard",
    "get_replay_guard",
]
