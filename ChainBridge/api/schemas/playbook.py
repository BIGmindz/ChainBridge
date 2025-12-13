"""Pydantic schemas for Playbook entities."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlaybookStep(BaseModel):
    """Schema for a single playbook step."""

    order: int = Field(..., ge=1)
    action: str = Field(..., min_length=1)
    params: Optional[Dict[str, Any]] = None
    gate: str = Field(default="auto")  # auto, human_approval, conditional
    description: Optional[str] = None
    timeout_minutes: Optional[int] = None


class PlaybookBase(BaseModel):
    """Base schema for Playbook with common fields."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None  # DELAY_HANDLING, CLAIMS, DOCUMENTATION, etc.
    trigger_condition: Optional[Dict[str, Any]] = None
    steps: List[PlaybookStep] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    active: bool = Field(default=True)
    supersedes_id: Optional[str] = None
    author_user_id: Optional[str] = None
    tags: Optional[List[str]] = None
    estimated_duration_minutes: Optional[int] = None


class PlaybookCreate(BaseModel):
    """Schema for creating a new Playbook."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    trigger_condition: Optional[Dict[str, Any]] = None
    steps: List[PlaybookStep] = Field(default_factory=list)
    active: bool = Field(default=True)
    author_user_id: Optional[str] = None
    tags: Optional[List[str]] = None
    estimated_duration_minutes: Optional[int] = None


class PlaybookUpdate(BaseModel):
    """Schema for updating an existing Playbook."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    trigger_condition: Optional[Dict[str, Any]] = None
    steps: Optional[List[PlaybookStep]] = None
    active: Optional[bool] = None
    tags: Optional[List[str]] = None
    estimated_duration_minutes: Optional[int] = None


class PlaybookRead(PlaybookBase):
    """Schema for reading a Playbook (includes ID and timestamps)."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaybookListItem(BaseModel):
    """Lightweight schema for Playbook listings."""

    id: str
    name: str
    category: Optional[str] = None
    version: int
    active: bool
    estimated_duration_minutes: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
