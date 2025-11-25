# api/schemas/agent_status.py
"""
Agent Framework Status Schema

Pydantic models for agent validation status API responses.
Provides programmatic access to agent framework health.

Author: ChainBridge Platform Team
Version: 1.0.0
"""

from typing import List

from pydantic import BaseModel, Field


class AgentStatusResponse(BaseModel):
    """Response schema for GET /api/agents/status endpoint.

    Provides a complete view of agent framework validation state,
    including counts and specific invalid agent identifiers.
    """

    total: int = Field(
        ...,
        description="Total number of agents in the framework",
        ge=0,
    )
    valid: int = Field(
        ...,
        description="Number of agents passing validation",
        ge=0,
    )
    invalid: int = Field(
        ...,
        description="Number of agents failing validation (total - valid)",
        ge=0,
    )
    invalid_roles: List[str] = Field(
        ...,
        description="List of role names for invalid/incomplete agents",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total": 20,
                "valid": 17,
                "invalid": 3,
                "invalid_roles": [
                    "AI_AGENT_TIM",
                    "AI_RESEARCH_BENSON",
                    "BIZDEV_PARTNERSHIPS_LEAD",
                ],
            }
        }
