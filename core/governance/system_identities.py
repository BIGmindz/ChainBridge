"""
ChainBridge System Identities — Non-Persona System Components
════════════════════════════════════════════════════════════════════════════════

Defines canonical identities for system components that are NOT agents.
System components have no persona, no conversation, no GID collision.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-ORCHESTRATION-ENGINE-RENAMING-017
Effective Date: 2025-12-26

IDENTITY BOUNDARY:
- SYSTEM components ≠ AGENTS
- System components have no persona
- Only ORCHESTRATION_ENGINE may issue BER
- Drafting surfaces may never emit WRAP/BER
- Agents may never self-approve

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM IDENTITY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class SystemIdentityType(Enum):
    """
    Classification of system identity types.
    
    These are NOT agents. They have no persona.
    """
    
    SYSTEM_ORCHESTRATOR = "SYSTEM_ORCHESTRATOR"
    SYSTEM_EXECUTION = "SYSTEM_EXECUTION"
    DRAFTING_SURFACE = "DRAFTING_SURFACE"
    AGENT = "AGENT"
    
    @property
    def is_system(self) -> bool:
        """True if this is a system component (not agent, not drafting surface)."""
        return self in (
            SystemIdentityType.SYSTEM_ORCHESTRATOR,
            SystemIdentityType.SYSTEM_EXECUTION,
        )
    
    @property
    def has_persona(self) -> bool:
        """True if this identity type can have a persona."""
        return self == SystemIdentityType.AGENT
    
    @property
    def is_conversational(self) -> bool:
        """True if this identity type is conversational."""
        return self == SystemIdentityType.DRAFTING_SURFACE
    
    @property
    def can_issue_ber(self) -> bool:
        """True if this identity type can issue BER."""
        return self == SystemIdentityType.SYSTEM_ORCHESTRATOR
    
    @property
    def can_issue_wrap(self) -> bool:
        """True if this identity type can issue WRAP."""
        return self == SystemIdentityType.AGENT
    
    @property
    def can_emit_pac(self) -> bool:
        """True if this identity type can emit PAC."""
        return self == SystemIdentityType.DRAFTING_SURFACE
    
    @property
    def can_execute_work(self) -> bool:
        """True if this identity type can execute work."""
        return self == SystemIdentityType.AGENT


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM IDENTITY — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SystemIdentity:
    """
    Canonical identity for a system component.
    
    Immutable — no mutation after creation.
    """
    
    identity_id: str
    identity_type: SystemIdentityType
    description: str
    
    @property
    def is_system(self) -> bool:
        """True if this is a system component."""
        return self.identity_type.is_system
    
    @property
    def has_persona(self) -> bool:
        """True if this identity can have a persona."""
        return self.identity_type.has_persona
    
    @property
    def is_conversational(self) -> bool:
        """True if this identity is conversational."""
        return self.identity_type.is_conversational
    
    @property
    def can_issue_ber(self) -> bool:
        """True if this identity can issue BER."""
        return self.identity_type.can_issue_ber
    
    @property
    def can_issue_wrap(self) -> bool:
        """True if this identity can issue WRAP."""
        return self.identity_type.can_issue_wrap


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL SYSTEM IDENTITIES
# ═══════════════════════════════════════════════════════════════════════════════

# Orchestration Engine — the sole BER issuer
ORCHESTRATION_ENGINE = SystemIdentity(
    identity_id="ORCHESTRATION_ENGINE",
    identity_type=SystemIdentityType.SYSTEM_ORCHESTRATOR,
    description=(
        "Non-persona system orchestrator. Validates PACs, dispatches to agents, "
        "reviews WRAPs, and issues BERs. The sole authority for governance decisions. "
        "No persona, no conversation, no agent-like behavior."
    ),
)

# Execution Engine — dispatches work to agents
EXECUTION_ENGINE = SystemIdentity(
    identity_id="EXECUTION_ENGINE",
    identity_type=SystemIdentityType.SYSTEM_EXECUTION,
    description=(
        "Non-persona execution dispatcher. Routes work to appropriate agents. "
        "Cannot issue BER. No governance authority. "
        "No persona, no conversation."
    ),
)

# Drafting Surface — human interface
DRAFTING_SURFACE = SystemIdentity(
    identity_id="DRAFTING_SURFACE",
    identity_type=SystemIdentityType.DRAFTING_SURFACE,
    description=(
        "Human interface for PAC emission. Jeffrey and other humans interact here. "
        "Cannot issue WRAP or BER. No governance authority. "
        "The only conversational component."
    ),
)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM IDENTITY REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class SystemIdentityRegistry:
    """
    Registry of all system identities.
    
    Provides lookup and validation functions.
    """
    
    # Canonical system identities
    _identities: dict[str, SystemIdentity] = {
        ORCHESTRATION_ENGINE.identity_id: ORCHESTRATION_ENGINE,
        EXECUTION_ENGINE.identity_id: EXECUTION_ENGINE,
        DRAFTING_SURFACE.identity_id: DRAFTING_SURFACE,
    }
    
    @classmethod
    def get(cls, identity_id: str) -> Optional[SystemIdentity]:
        """Get a system identity by ID."""
        return cls._identities.get(identity_id)
    
    @classmethod
    def get_or_fail(cls, identity_id: str) -> SystemIdentity:
        """Get a system identity by ID, or raise if not found."""
        identity = cls.get(identity_id)
        if identity is None:
            raise UnknownSystemIdentityError(identity_id)
        return identity
    
    @classmethod
    def is_valid(cls, identity_id: str) -> bool:
        """Check if an identity ID is valid."""
        return identity_id in cls._identities
    
    @classmethod
    def all_identities(cls) -> list[SystemIdentity]:
        """Get all system identities."""
        return list(cls._identities.values())
    
    @classmethod
    def ber_issuers(cls) -> list[SystemIdentity]:
        """Get all identities that can issue BER."""
        return [i for i in cls._identities.values() if i.can_issue_ber]
    
    @classmethod
    def wrap_issuers(cls) -> list[SystemIdentity]:
        """Get all identities that can issue WRAP."""
        return [i for i in cls._identities.values() if i.can_issue_wrap]


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SystemIdentityError(Exception):
    """Base exception for system identity errors."""
    pass


class UnknownSystemIdentityError(SystemIdentityError):
    """Raised when an unknown system identity is referenced."""
    
    def __init__(self, identity_id: str):
        self.identity_id = identity_id
        super().__init__(
            f"HARD FAIL: Unknown system identity '{identity_id}'. "
            f"Valid identities: {list(SystemIdentityRegistry._identities.keys())}"
        )


class BERAuthorityError(SystemIdentityError):
    """Raised when an unauthorized entity attempts to issue BER."""
    
    def __init__(self, identity_id: str, identity_type: SystemIdentityType):
        self.identity_id = identity_id
        self.identity_type = identity_type
        super().__init__(
            f"HARD FAIL: '{identity_id}' ({identity_type.value}) cannot issue BER. "
            f"Only SYSTEM_ORCHESTRATOR may issue BER."
        )


class WRAPAuthorityError(SystemIdentityError):
    """Raised when an unauthorized entity attempts to issue WRAP."""
    
    def __init__(self, identity_id: str, identity_type: SystemIdentityType):
        self.identity_id = identity_id
        self.identity_type = identity_type
        super().__init__(
            f"HARD FAIL: '{identity_id}' ({identity_type.value}) cannot issue WRAP. "
            f"Only AGENT may issue WRAP."
        )


class PersonaAuthorityError(SystemIdentityError):
    """Raised when persona-based authority is claimed."""
    
    def __init__(self, claimed_persona: str):
        self.claimed_persona = claimed_persona
        super().__init__(
            f"HARD FAIL: Persona authority rejected. "
            f"Claimed persona: '{claimed_persona}'. "
            f"Persona strings have zero authority weight. "
            f"Authority is code-enforced, not persona-based."
        )


class SelfApprovalError(SystemIdentityError):
    """Raised when an agent attempts to self-approve."""
    
    def __init__(self, agent_gid: str):
        self.agent_gid = agent_gid
        super().__init__(
            f"HARD FAIL: Self-approval forbidden. "
            f"Agent '{agent_gid}' cannot approve their own work. "
            f"Only ORCHESTRATION_ENGINE may issue BER."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHORITY VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_ber_authority(issuer_id: str, issuer_type: SystemIdentityType) -> bool:
    """
    Validate that an issuer has authority to issue BER.
    
    HARD FAIL if unauthorized.
    
    Args:
        issuer_id: The identity ID of the issuer
        issuer_type: The type of identity
        
    Returns:
        True if authorized
        
    Raises:
        BERAuthorityError: If unauthorized
    """
    if issuer_type != SystemIdentityType.SYSTEM_ORCHESTRATOR:
        raise BERAuthorityError(issuer_id, issuer_type)
    return True


def validate_wrap_authority(issuer_id: str, issuer_type: SystemIdentityType) -> bool:
    """
    Validate that an issuer has authority to issue WRAP.
    
    HARD FAIL if unauthorized.
    
    Args:
        issuer_id: The identity ID of the issuer
        issuer_type: The type of identity
        
    Returns:
        True if authorized
        
    Raises:
        WRAPAuthorityError: If unauthorized
    """
    if issuer_type != SystemIdentityType.AGENT:
        raise WRAPAuthorityError(issuer_id, issuer_type)
    return True


def reject_persona_authority(claimed_persona: str) -> None:
    """
    Reject any persona-based authority claim.
    
    ALWAYS raises — persona authority has zero weight.
    
    Args:
        claimed_persona: The claimed persona string
        
    Raises:
        PersonaAuthorityError: Always
    """
    raise PersonaAuthorityError(claimed_persona)


def validate_not_self_approval(agent_gid: str, wrap_author_gid: str) -> bool:
    """
    Validate that an agent is not approving their own work.
    
    HARD FAIL if self-approval attempted.
    
    Args:
        agent_gid: The GID of the entity attempting to approve
        wrap_author_gid: The GID of the WRAP author
        
    Returns:
        True if not self-approval
        
    Raises:
        SelfApprovalError: If self-approval attempted
    """
    if agent_gid == wrap_author_gid:
        raise SelfApprovalError(agent_gid)
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_orchestration_engine() -> SystemIdentity:
    """Get the orchestration engine identity."""
    return ORCHESTRATION_ENGINE


def get_execution_engine() -> SystemIdentity:
    """Get the execution engine identity."""
    return EXECUTION_ENGINE


def get_drafting_surface() -> SystemIdentity:
    """Get the drafting surface identity."""
    return DRAFTING_SURFACE


def is_system_component(identity_id: str) -> bool:
    """Check if an identity is a system component."""
    identity = SystemIdentityRegistry.get(identity_id)
    return identity is not None and identity.is_system


def is_ber_authorized(identity_id: str) -> bool:
    """Check if an identity is authorized to issue BER."""
    identity = SystemIdentityRegistry.get(identity_id)
    return identity is not None and identity.can_issue_ber


def is_wrap_authorized(identity_id: str) -> bool:
    """Check if an identity is authorized to issue WRAP."""
    identity = SystemIdentityRegistry.get(identity_id)
    return identity is not None and identity.can_issue_wrap


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT CHECKERS
# ═══════════════════════════════════════════════════════════════════════════════

# Canonical invariants from ORCHESTRATION_ENGINE_LAW_v1.md
INVARIANTS: FrozenSet[str] = frozenset([
    "INV-ORC-001",  # Only SYSTEM_ORCHESTRATOR may issue BER
    "INV-ORC-002",  # DRAFTING_SURFACE may never emit WRAP or BER
    "INV-ORC-003",  # AGENT may never self-approve
    "INV-ORC-004",  # Persona strings have zero authority weight
    "INV-ORC-005",  # System components have no persona
    "INV-ORC-006",  # All authority is code-enforced, not prompt-enforced
    "INV-ORC-007",  # GID-00 registry entry marked system=True
])


def check_invariant_orc_001(issuer_type: SystemIdentityType) -> bool:
    """INV-ORC-001: Only SYSTEM_ORCHESTRATOR may issue BER."""
    return issuer_type == SystemIdentityType.SYSTEM_ORCHESTRATOR


def check_invariant_orc_002(issuer_type: SystemIdentityType) -> bool:
    """INV-ORC-002: DRAFTING_SURFACE may never emit WRAP or BER."""
    return issuer_type != SystemIdentityType.DRAFTING_SURFACE


def check_invariant_orc_003(agent_gid: str, wrap_author_gid: str) -> bool:
    """INV-ORC-003: AGENT may never self-approve."""
    return agent_gid != wrap_author_gid


def check_invariant_orc_005(identity_type: SystemIdentityType) -> bool:
    """INV-ORC-005: System components have no persona."""
    if identity_type.is_system:
        return not identity_type.has_persona
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "SystemIdentityType",
    
    # Classes
    "SystemIdentity",
    "SystemIdentityRegistry",
    
    # Canonical Identities
    "ORCHESTRATION_ENGINE",
    "EXECUTION_ENGINE",
    "DRAFTING_SURFACE",
    
    # Exceptions
    "SystemIdentityError",
    "UnknownSystemIdentityError",
    "BERAuthorityError",
    "WRAPAuthorityError",
    "PersonaAuthorityError",
    "SelfApprovalError",
    
    # Validators
    "validate_ber_authority",
    "validate_wrap_authority",
    "reject_persona_authority",
    "validate_not_self_approval",
    
    # Convenience Functions
    "get_orchestration_engine",
    "get_execution_engine",
    "get_drafting_surface",
    "is_system_component",
    "is_ber_authorized",
    "is_wrap_authorized",
    
    # Invariants
    "INVARIANTS",
    "check_invariant_orc_001",
    "check_invariant_orc_002",
    "check_invariant_orc_003",
    "check_invariant_orc_005",
]
