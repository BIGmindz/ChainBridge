# ═══════════════════════════════════════════════════════════════════════════════
# OCC Timeline API — PAC Lifecycle Timeline Endpoints
# PAC-BENSON-P22-C: OCC + Control Plane Deepening
#
# Provides GET-only endpoints for timeline visualization:
# - /occ/timeline/{pac_id}          - Full PAC timeline
# - /occ/timeline/{pac_id}/events   - Timeline events (paginated)
# - /occ/timeline/{pac_id}/wraps    - WRAP milestones
# - /occ/timeline/{pac_id}/ber      - BER records
#
# INVARIANTS:
# - INV-OCC-004: Timeline completeness (all transitions visible)
# - INV-OCC-005: Evidence immutability (no retroactive edits)
# - INV-OCC-006: No hidden transitions
#
# Authors:
# - CODY (GID-01) — Backend Lead
# - CINDY (GID-04) — Backend Support
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/timeline", tags=["OCC Timeline"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

TimelineEventCategory = Literal[
    "pac_lifecycle",
    "agent_activation",
    "execution",
    "decision",
    "wrap",
    "review_gate",
    "ber",
    "governance",
    "error",
]

TimelineEventSeverity = Literal["info", "success", "warning", "error", "critical"]

PACLifecycleState = Literal[
    "ADMISSION",
    "RUNTIME_ACTIVATION",
    "AGENT_ACTIVATION",
    "EXECUTING",
    "WRAP_COLLECTION",
    "REVIEW_GATE",
    "BER_ISSUED",
    "SETTLED",
    "FAILED",
    "CANCELLED",
]


class TimelineEvent(BaseModel):
    """Single timeline event."""
    event_id: str
    pac_id: str
    category: TimelineEventCategory
    severity: TimelineEventSeverity
    title: str
    description: str
    timestamp: datetime
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    artifact_ids: List[str] = Field(default_factory=list)
    evidence_hash: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Optional[dict] = None


class AgentACKRecord(BaseModel):
    """Agent ACK record."""
    agent_id: str
    agent_name: str
    ack_timestamp: datetime
    ack_latency_ms: int
    lane: str


class WRAPMilestone(BaseModel):
    """WRAP milestone."""
    wrap_id: str
    pac_id: str
    status: Literal["collecting", "complete", "failed"]
    agents_required: int
    agents_approved: int
    approved_agents: List[AgentACKRecord]
    pending_agents: List[str]
    started_at: datetime
    completed_at: Optional[datetime] = None


class ReviewGateRecord(BaseModel):
    """Review gate record."""
    gate_id: str
    gate_type: Literal["RG-01", "BSRG-01"]
    status: Literal["pending", "passed", "failed"]
    checked_at: datetime
    checks: dict
    failure_reason: Optional[str] = None


class BERTimelineRecord(BaseModel):
    """BER record for timeline."""
    ber_id: str
    pac_id: str
    status: Literal["DRAFT", "PENDING_REVIEW", "FINAL", "SUPERSEDED"]
    issued_at: datetime
    issued_by: str
    execution_mode: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    finality: Literal["FINAL", "PROVISIONAL"]
    evidence_hash: str


class PACTimelineState(BaseModel):
    """Complete PAC timeline state."""
    pac_id: str
    lifecycle_state: PACLifecycleState
    title: str
    issuer: str
    events: List[TimelineEvent]
    agent_acks: List[AgentACKRecord]
    wrap_milestones: List[WRAPMilestone]
    review_gates: List[ReviewGateRecord]
    ber_records: List[BERTimelineRecord]
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class TimelineEventsResponse(BaseModel):
    """Paginated timeline events response."""
    events: List[TimelineEvent]
    total: int
    has_more: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

def _get_mock_timeline(pac_id: str) -> PACTimelineState:
    """Get mock timeline data. Replace with TimelineStore integration."""
    now = datetime.now(timezone.utc)

    events = [
        TimelineEvent(
            event_id="evt-001",
            pac_id=pac_id,
            category="pac_lifecycle",
            severity="info",
            title="PAC Admission",
            description="PAC admitted to execution queue",
            timestamp=now,
            evidence_hash="abc123def456",
        ),
        TimelineEvent(
            event_id="evt-002",
            pac_id=pac_id,
            category="agent_activation",
            severity="success",
            title="BENSON Activated",
            description="BENSON (GID-00) acknowledged PAC",
            timestamp=now,
            agent_id="GID-00",
            agent_name="BENSON",
            evidence_hash="def456ghi789",
        ),
        TimelineEvent(
            event_id="evt-003",
            pac_id=pac_id,
            category="execution",
            severity="info",
            title="Task Execution Started",
            description="Frontend components creation started",
            timestamp=now,
            agent_id="GID-02",
            agent_name="SONNY",
        ),
    ]

    agent_acks = [
        AgentACKRecord(agent_id="GID-00", agent_name="BENSON", ack_timestamp=now, ack_latency_ms=50, lane="orchestration"),
        AgentACKRecord(agent_id="GID-02", agent_name="SONNY", ack_timestamp=now, ack_latency_ms=75, lane="frontend"),
        AgentACKRecord(agent_id="GID-01", agent_name="CODY", ack_timestamp=now, ack_latency_ms=60, lane="backend"),
    ]

    return PACTimelineState(
        pac_id=pac_id,
        lifecycle_state="EXECUTING",
        title="OCC + Control Plane Deepening",
        issuer="BENSON (GID-00)",
        events=events,
        agent_acks=agent_acks,
        wrap_milestones=[],
        review_gates=[],
        ber_records=[],
        started_at=now,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/{pac_id}", response_model=PACTimelineState)
async def get_pac_timeline(pac_id: str) -> PACTimelineState:
    """
    Get full PAC timeline.

    READ-ONLY: No mutations allowed.
    Invariant: INV-OCC-004 (Timeline completeness)
    Invariant: INV-OCC-005 (Evidence immutability)
    Invariant: INV-OCC-006 (No hidden transitions)
    """
    return _get_mock_timeline(pac_id)


@router.get("/{pac_id}/events", response_model=TimelineEventsResponse)
async def get_timeline_events(
    pac_id: str,
    category: Optional[TimelineEventCategory] = Query(None),
    severity: Optional[TimelineEventSeverity] = Query(None),
    agent_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> TimelineEventsResponse:
    """
    Get paginated timeline events.

    READ-ONLY: No mutations allowed.
    """
    timeline = _get_mock_timeline(pac_id)
    events = timeline.events

    # Apply filters
    if category:
        events = [e for e in events if e.category == category]
    if severity:
        events = [e for e in events if e.severity == severity]
    if agent_id:
        events = [e for e in events if e.agent_id == agent_id]

    total = len(events)
    events = events[offset:offset + limit]
    has_more = offset + len(events) < total

    return TimelineEventsResponse(events=events, total=total, has_more=has_more)


@router.get("/{pac_id}/wraps", response_model=List[WRAPMilestone])
async def get_wrap_milestones(pac_id: str) -> List[WRAPMilestone]:
    """
    Get WRAP milestones for PAC.

    READ-ONLY: No mutations allowed.
    """
    timeline = _get_mock_timeline(pac_id)
    return timeline.wrap_milestones


@router.get("/{pac_id}/ber", response_model=List[BERTimelineRecord])
async def get_ber_records(pac_id: str) -> List[BERTimelineRecord]:
    """
    Get BER records for PAC.

    READ-ONLY: No mutations allowed.
    """
    timeline = _get_mock_timeline(pac_id)
    return timeline.ber_records


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION REJECTION
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/{pac_id}")
@router.put("/{pac_id}")
@router.patch("/{pac_id}")
@router.delete("/{pac_id}")
async def reject_timeline_mutations(pac_id: str):
    """Reject mutations. READ-ONLY endpoint."""
    raise HTTPException(
        status_code=405,
        detail="Timeline endpoints are READ-ONLY. INV-OCC-005: Evidence immutability.",
    )
