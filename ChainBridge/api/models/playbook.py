"""SQLAlchemy models for Playbooks in ChainBridge.

Playbooks encode remediation flows - automated or semi-automated sequences
of steps to resolve exceptions and handle operational scenarios.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Index, Integer, String, Text

from api.database import Base


class Playbook(Base):
    """Represents an encoded remediation workflow.

    Playbooks define the steps to handle specific exception types or
    operational scenarios. They can be fully automated, require human
    approval at certain gates, or be purely advisory.
    """

    __tablename__ = "playbooks"
    __table_args__ = (
        Index("ix_playbooks_tenant_id", "tenant_id"),
        Index("ix_playbooks_active", "active"),
        Index("ix_playbooks_tenant_active", "tenant_id", "active"),
    )

    id = Column(String, primary_key=True, default=lambda: f"PB-{uuid4()}")
    tenant_id = Column(String, nullable=False)

    # Playbook identification
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)  # DELAY_HANDLING, CLAIMS, DOCUMENTATION, COMPLIANCE, etc.

    # Trigger conditions (when this playbook should be suggested/activated)
    trigger_condition = Column(JSON, nullable=True)
    # Example: {"exception_type": "DELAY", "severity": ["HIGH", "CRITICAL"], "corridor": "CN-US"}

    # Playbook steps
    steps = Column(JSON, nullable=False, default=list)
    # Example: [{"order": 1, "action": "notify_carrier", "params": {...}, "gate": "auto"},
    #           {"order": 2, "action": "request_eta_update", "gate": "human_approval"}]

    # Version control
    version = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True)
    supersedes_id = Column(String, nullable=True)  # Previous version's ID if upgraded

    # Metadata
    author_user_id = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)  # List of searchable tags
    estimated_duration_minutes = Column(Integer, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<Playbook(id={self.id}, name={self.name}, v{self.version})>"
