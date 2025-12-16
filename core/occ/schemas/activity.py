"""
Agent Activity Pydantic Models (v2 syntax)

Glass-box design: Nothing happens without a trace.
All agent activities are logged immutably with full context.

Activity Types:
- RECOMMENDATION: Agent submitted a decision recommendation
- OVERRIDE: Human operator overrode an agent decision
- ARTIFACT_CREATE: Agent created an artifact
- ARTIFACT_UPDATE: Agent modified an artifact
- RUN_START: Agent run started
- RUN_COMPLETE: Agent run completed
- RUN_FAILED: Agent run failed
- HEARTBEAT: Agent health check
- CUSTOM: Application-specific activity
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ActivityType(str, Enum):
    """Types of agent activities that can be logged."""

    # Decision-related
    RECOMMENDATION = "RECOMMENDATION"
    OVERRIDE = "OVERRIDE"

    # Artifact-related
    ARTIFACT_CREATE = "ARTIFACT_CREATE"
    ARTIFACT_UPDATE = "ARTIFACT_UPDATE"
    ARTIFACT_DELETE = "ARTIFACT_DELETE"

    # Run lifecycle
    RUN_START = "RUN_START"
    RUN_COMPLETE = "RUN_COMPLETE"
    RUN_FAILED = "RUN_FAILED"

    # Health
    HEARTBEAT = "HEARTBEAT"

    # Extensibility
    CUSTOM = "CUSTOM"


class ActivityStatus(str, Enum):
    """Status of the activity (for async operations)."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# =============================================================================
# ACTIVITY MODELS
# =============================================================================


class AgentActivityCreate(BaseModel):
    """Schema for creating a new agent activity."""

    model_config = ConfigDict(use_enum_values=True)

    agent_gid: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Agent GID (e.g., GID-01, GID-02)",
        examples=["GID-01", "GID-02"],
    )
    activity_type: ActivityType = Field(
        ...,
        description="Type of activity being logged",
    )
    artifact_id: Optional[UUID] = Field(
        None,
        description="ID of related artifact (if any)",
    )
    status: ActivityStatus = Field(
        default=ActivityStatus.SUCCESS,
        description="Activity status",
    )
    summary: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Human-readable summary of the activity",
        examples=["Submitted APPROVE recommendation for artifact xyz"],
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Activity-specific details (glass-box: all context visible)",
    )
    correlation_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Correlation ID for tracing related activities",
    )


class AgentActivity(BaseModel):
    """
    Full agent activity model with server-generated fields.

    IMMUTABLE: Once created, activities cannot be modified or deleted.
    This ensures a complete audit trail of all agent operations.
    """

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique activity identifier",
    )
    agent_gid: str = Field(
        ...,
        description="Agent GID that performed this activity",
    )
    activity_type: ActivityType = Field(
        ...,
        description="Type of activity",
    )
    artifact_id: Optional[UUID] = Field(
        None,
        description="ID of related artifact (if any)",
    )
    status: ActivityStatus = Field(
        default=ActivityStatus.SUCCESS,
        description="Activity status",
    )
    summary: str = Field(
        ...,
        description="Human-readable summary",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Activity-specific details",
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for tracing",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the activity occurred (UTC) - server-generated",
    )
    sequence: int = Field(
        default=0,
        description="Monotonic sequence number for ordering",
    )

    def to_sse_event(self) -> str:
        """Format activity as Server-Sent Event."""
        import json

        data = self.model_dump(mode="json")
        return f"data: {json.dumps(data)}\n\n"


class AgentActivityList(BaseModel):
    """Response model for listing activities."""

    items: List[AgentActivity]
    count: int
    total: int
    has_more: bool = Field(
        default=False,
        description="Whether more activities exist beyond this page",
    )


class ActivityStats(BaseModel):
    """Statistics about agent activities."""

    total: int = Field(0, description="Total number of activities")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Count by activity type")
    by_agent: Dict[str, int] = Field(default_factory=dict, description="Count by agent GID")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Count by status")
    oldest_timestamp: Optional[datetime] = Field(None, description="Oldest activity timestamp")
    newest_timestamp: Optional[datetime] = Field(None, description="Newest activity timestamp")
