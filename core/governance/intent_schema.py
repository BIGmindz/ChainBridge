"""
Agent Intent Schema — Canonical intent envelope for ACM enforcement.

This module defines the strict intent shape that all agent actions must conform to.
Any intent not matching this schema is rejected without evaluation.

ALEX (GID-08) is the sole authority for intent evaluation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntentVerb(str, Enum):
    """Canonical verbs for agent intents (aligned with ACM capabilities)."""

    READ = "READ"
    PROPOSE = "PROPOSE"
    EXECUTE = "EXECUTE"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"

    @classmethod
    def from_string(cls, value: str) -> "IntentVerb":
        """Parse a verb string (case-insensitive).

        Raises:
            ValueError: If verb is not recognized
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Unknown intent verb: {value}")


class AgentIntent(BaseModel):
    """Strict intent envelope for ACM enforcement.

    Every agent action must be wrapped in this envelope before
    reaching the gateway. Malformed intents are rejected.

    Attributes:
        agent_gid: The GID of the requesting agent (e.g., "GID-01")
        verb: The capability verb (READ, PROPOSE, EXECUTE, BLOCK, ESCALATE)
        target: The target resource/scope (e.g., "pytest", "backend.tests")
        scope: Optional narrower scope qualifier
        metadata: Optional key-value metadata (deterministic only)
        correlation_id: Optional idempotency/correlation key
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        frozen=True,  # Immutable after creation
        str_strip_whitespace=True,
    )

    agent_gid: str = Field(
        ...,
        description="Agent GID (e.g., GID-01)",
        pattern=r"^GID-\d{2}$",
    )
    verb: IntentVerb = Field(
        ...,
        description="Capability verb (READ, PROPOSE, EXECUTE, BLOCK, ESCALATE)",
    )
    target: str = Field(
        ...,
        description="Target resource or action",
        min_length=1,
        max_length=256,
    )
    scope: Optional[str] = Field(
        None,
        description="Optional scope qualifier",
        max_length=256,
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Deterministic key-value metadata",
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Idempotency/correlation key",
        max_length=128,
    )

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Ensure metadata contains only string key-value pairs."""
        if not isinstance(v, dict):
            raise ValueError("metadata must be a dict")
        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("metadata must contain only string key-value pairs")
        return v

    @property
    def full_target(self) -> str:
        """Return the full target path including scope if present."""
        if self.scope:
            return f"{self.target}.{self.scope}"
        return self.target

    def is_mutating(self) -> bool:
        """Check if this intent would mutate state.

        Only EXECUTE can mutate. READ/PROPOSE are read-only by definition.
        BLOCK prevents mutation but doesn't mutate itself.
        ESCALATE is a signal, not a mutation.
        """
        return self.verb == IntentVerb.EXECUTE


def parse_intent(data: Dict[str, Any]) -> AgentIntent:
    """Parse and validate an intent from raw data.

    Args:
        data: Raw intent dictionary

    Returns:
        Validated AgentIntent

    Raises:
        ValueError: If intent is malformed or missing required fields
    """
    try:
        # Normalize verb to enum if string
        if "verb" in data and isinstance(data["verb"], str):
            data = data.copy()
            data["verb"] = IntentVerb.from_string(data["verb"])
        return AgentIntent(**data)
    except Exception as e:
        raise ValueError(f"Invalid intent format: {e}") from e


def create_intent(
    agent_gid: str,
    verb: str | IntentVerb,
    target: str,
    scope: Optional[str] = None,
    metadata: Dict[str, str] | None = None,
    correlation_id: Optional[str] = None,
) -> AgentIntent:
    """Factory function to create a validated intent.

    Args:
        agent_gid: Agent GID (e.g., "GID-01")
        verb: Capability verb
        target: Target resource
        scope: Optional scope qualifier
        metadata: Optional metadata
        correlation_id: Optional correlation ID

    Returns:
        Validated AgentIntent
    """
    if isinstance(verb, str):
        verb = IntentVerb.from_string(verb)

    return AgentIntent(
        agent_gid=agent_gid,
        verb=verb,
        target=target,
        scope=scope,
        metadata=metadata or {},
        correlation_id=correlation_id,
    )
