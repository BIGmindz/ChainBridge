"""
Artifact Pydantic Models (v2 syntax)

Artifacts represent discrete units of work, decisions, or records
in the Operations Control Center (OCC).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ArtifactType(str, Enum):
    """Classification of artifact types in the OCC system."""

    PLAN = "Plan"
    REPORT = "Report"
    DECISION = "Decision"
    EXECUTION_RESULT = "ExecutionResult"
    COMPLIANCE_RECORD = "ComplianceRecord"


class ArtifactStatus(str, Enum):
    """Lifecycle status of an artifact."""

    DRAFT = "Draft"
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    LOCKED = "Locked"


class ArtifactBase(BaseModel):
    """Base fields shared across artifact operations."""

    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., min_length=1, max_length=255, description="Human-readable artifact name")
    artifact_type: ArtifactType = Field(..., description="Type classification of the artifact")
    description: Optional[str] = Field(None, max_length=2000, description="Optional description")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary JSON payload")
    tags: list[str] = Field(default_factory=list, description="Optional tags for categorization")
    owner: Optional[str] = Field(None, max_length=255, description="Owner identifier")


class ArtifactCreate(ArtifactBase):
    """Schema for creating a new artifact. ID and timestamps are server-generated."""

    status: ArtifactStatus = Field(default=ArtifactStatus.DRAFT, description="Initial status")


class ArtifactUpdate(BaseModel):
    """Schema for partial artifact updates (PATCH)."""

    model_config = ConfigDict(use_enum_values=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ArtifactStatus] = None
    payload: Optional[Dict[str, Any]] = None
    tags: Optional[list[str]] = None
    owner: Optional[str] = Field(None, max_length=255)


class Artifact(ArtifactBase):
    """Full artifact model with server-generated fields."""

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Unique artifact identifier")
    status: ArtifactStatus = Field(default=ArtifactStatus.DRAFT, description="Current lifecycle status")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of creation (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of last update (UTC)",
    )

    def apply_update(self, update: ArtifactUpdate) -> "Artifact":
        """Return a new Artifact with updated fields."""
        update_data = update.model_dump(exclude_unset=True)
        current_data = self.model_dump()
        current_data.update(update_data)
        current_data["updated_at"] = datetime.now(timezone.utc)
        return Artifact.model_validate(current_data)
