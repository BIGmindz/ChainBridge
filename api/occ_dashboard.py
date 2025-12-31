# ═══════════════════════════════════════════════════════════════════════════════
# OCC Dashboard API — Read-Only Endpoints for OCC UI
# PAC-BENSON-P21-C: OCC Intensive Multi-Agent Execution
#
# Provides GET-only endpoints for OCC Dashboard consumption:
# - /occ/dashboard/agents       - Agent lane tiles with health states
# - /occ/dashboard/decisions    - Decision stream (PDO + BER cards)
# - /occ/dashboard/governance   - Governance rail (invariants)
# - /occ/dashboard/kill-switch  - Kill switch status
# - /occ/dashboard/state        - Full dashboard state (aggregate)
#
# INVARIANTS:
# - INV-OCC-001: No mutation routes - read-only state display
# - INV-OCC-002: Always reflects backend state (no optimistic rendering)
# - INV-OCC-003: UI reflects invariant failures with rule IDs
# - INV-SAM-001: No hidden execution paths
#
# Authors:
# - CODY (GID-01) — Backend Lead
# - CINDY (GID-04) — Backend Support
# Security: SAM (GID-06)
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/dashboard", tags=["OCC Dashboard"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS — Agent Lane Tiles
# ═══════════════════════════════════════════════════════════════════════════════

AgentLane = Literal[
    "orchestration",
    "frontend",
    "backend",
    "security",
    "governance",
    "ci",
    "integrity",
    "ml",
    "documentation",
    "testing",
]

AgentHealthState = Literal["healthy", "degraded", "critical", "unknown"]

AgentExecutionState = Literal[
    "idle",
    "executing",
    "blocked",
    "completed",
    "failed",
]


class AgentLaneTile(BaseModel):
    """Agent lane tile for OCC grid display."""

    agent_id: str = Field(..., description="Agent GID (e.g., 'GID-00')")
    agent_name: str = Field(..., description="Agent name (e.g., 'BENSON')")
    lane: AgentLane = Field(..., description="Agent's execution lane")
    health: AgentHealthState = Field("healthy", description="Health state")
    execution_state: AgentExecutionState = Field("idle", description="Current execution state")
    current_pac_id: Optional[str] = Field(None, description="Currently bound PAC ID")
    tasks_completed: int = Field(0, ge=0, description="Completed tasks in current PAC")
    tasks_pending: int = Field(0, ge=0, description="Pending tasks in current PAC")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")
    blocked_reason: Optional[str] = Field(None, description="Reason if blocked")


class AgentLaneTileListResponse(BaseModel):
    """Response for agent tiles list."""

    agents: List[AgentLaneTile]
    total: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS — Decision Stream
# ═══════════════════════════════════════════════════════════════════════════════

DecisionType = Literal[
    "FILE_CREATE",
    "FILE_MODIFY",
    "FILE_DELETE",
    "API_CALL",
    "COMMAND_EXEC",
    "PAC_TRANSITION",
    "GOVERNANCE_CHECK",
    "SETTLEMENT",
    "OTHER",
]

DecisionOutcome = Literal["APPROVED", "REJECTED", "ESCALATED", "PENDING"]

BERStatus = Literal["DRAFT", "PENDING_REVIEW", "FINAL", "SUPERSEDED"]


class PDOCard(BaseModel):
    """Pre-Decision Object card for decision stream."""

    pdo_id: str = Field(..., description="PDO identifier")
    pac_id: str = Field(..., description="Associated PAC ID")
    agent_id: str = Field(..., description="Agent that generated the PDO")
    agent_name: str = Field(..., description="Agent name")
    decision_type: DecisionType = Field(..., description="Type of decision")
    description: str = Field(..., description="Human-readable description")
    outcome: DecisionOutcome = Field(..., description="Decision outcome")
    invariants_checked: List[str] = Field(default_factory=list, description="Invariant IDs checked")
    timestamp: datetime = Field(..., description="Decision timestamp")
    rationale: Optional[str] = Field(None, description="Decision rationale")


class WRAPProgress(BaseModel):
    """WRAP (Work Record Acceptance Protocol) progress."""

    wrap_id: str
    agents_required: int
    agents_approved: int
    approved_agents: List[str]
    pending_agents: List[str]


class BERCard(BaseModel):
    """BENSON Execution Report card for decision stream."""

    ber_id: str = Field(..., description="BER identifier")
    pac_id: str = Field(..., description="Associated PAC ID")
    status: BERStatus = Field(..., description="BER status")
    execution_mode: str = Field(..., description="Execution mode (e.g., 'PARALLEL')")
    total_tasks: int = Field(0, ge=0, description="Total tasks in execution")
    completed_tasks: int = Field(0, ge=0, description="Completed tasks")
    wrap_progress: Optional[WRAPProgress] = Field(None, description="WRAP progress if in review")
    ber_finality: Literal["FINAL", "PROVISIONAL"] = Field(..., description="Finality state")
    timestamp: datetime = Field(..., description="BER timestamp")
    summary: Optional[str] = Field(None, description="Execution summary")


class DecisionStreamItem(BaseModel):
    """Single item in the decision stream (either PDO or BER)."""

    id: str = Field(..., description="Unique item ID")
    item_type: Literal["pdo", "ber"] = Field(..., description="Item type")
    timestamp: datetime = Field(..., description="Item timestamp")
    pdo_card: Optional[PDOCard] = Field(None, description="PDO card if item_type is 'pdo'")
    ber_card: Optional[BERCard] = Field(None, description="BER card if item_type is 'ber'")


class DecisionStreamResponse(BaseModel):
    """Response for decision stream."""

    items: List[DecisionStreamItem]
    total: int
    has_more: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS — Governance Rail
# ═══════════════════════════════════════════════════════════════════════════════

InvariantClass = Literal[
    "S-INV",   # Security invariants (SAM)
    "M-INV",   # Mutation invariants
    "X-INV",   # Execution invariants
    "T-INV",   # Trust invariants
    "A-INV",   # Audit invariants (ALEX)
    "F-INV",   # Financial invariants
    "C-INV",   # Compliance invariants
]

InvariantStatus = Literal["passing", "warning", "failing", "unknown"]


class InvariantDisplay(BaseModel):
    """Single invariant for governance rail."""

    invariant_id: str = Field(..., description="Invariant identifier (e.g., 'INV-OCC-001')")
    rule_id: str = Field(..., description="Associated rule ID")
    description: str = Field(..., description="Invariant description")
    invariant_class: InvariantClass = Field(..., alias="class", description="Invariant class")
    status: InvariantStatus = Field(..., description="Current status")
    last_checked: datetime = Field(..., description="Last check timestamp")
    source: str = Field(..., description="Source agent (e.g., 'SAM', 'ALEX')")
    violation_message: Optional[str] = Field(None, description="Violation message if failing")
    affected_entities: List[str] = Field(default_factory=list, description="Affected entity IDs")

    class Config:
        populate_by_name = True


class GovernanceRailState(BaseModel):
    """Governance rail state for OCC display."""

    invariants: List[InvariantDisplay]
    lint_v2_passing: bool = Field(True, description="Lint v2 validation status")
    schema_registry_valid: bool = Field(True, description="Schema registry validation status")
    fail_closed_active: bool = Field(True, description="Fail-closed governance active")
    last_refresh: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS — Kill Switch
# ═══════════════════════════════════════════════════════════════════════════════

KillSwitchState = Literal["DISARMED", "ARMED", "ENGAGED", "COOLDOWN"]
KillSwitchAuthLevel = Literal["UNAUTHORIZED", "ARM_ONLY", "FULL_ACCESS"]


class KillSwitchStatus(BaseModel):
    """Kill switch status for OCC display."""

    state: KillSwitchState = Field(..., description="Current kill switch state")
    auth_level: KillSwitchAuthLevel = Field(..., description="Operator's authorization level")
    engaged_by: Optional[str] = Field(None, description="Who engaged (if engaged)")
    engaged_at: Optional[datetime] = Field(None, description="When engaged (if engaged)")
    engagement_reason: Optional[str] = Field(None, description="Engagement reason")
    affected_pacs: List[str] = Field(default_factory=list, description="PACs affected")
    cooldown_remaining_ms: Optional[int] = Field(None, description="Cooldown remaining in ms")


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS — Aggregate Dashboard State
# ═══════════════════════════════════════════════════════════════════════════════


class OCCDashboardStateResponse(BaseModel):
    """Full OCC dashboard state (aggregate endpoint)."""

    agents: List[AgentLaneTile]
    decision_stream: List[DecisionStreamItem]
    governance_rail: GovernanceRailState
    kill_switch: KillSwitchStatus
    active_pac_id: Optional[str] = Field(None, description="Currently active PAC")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA PROVIDER (Replace with real store integration)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_mock_agents() -> List[AgentLaneTile]:
    """Get mock agent data. Replace with AgentStore integration."""
    now = datetime.now(timezone.utc)
    return [
        AgentLaneTile(agent_id="GID-00", agent_name="BENSON", lane="orchestration", health="healthy", execution_state="executing", current_pac_id="PAC-BENSON-P21-C", tasks_completed=4, tasks_pending=8, last_heartbeat=now),
        AgentLaneTile(agent_id="GID-01", agent_name="CODY", lane="backend", health="healthy", execution_state="executing", current_pac_id="PAC-BENSON-P21-C", tasks_completed=1, tasks_pending=2, last_heartbeat=now),
        AgentLaneTile(agent_id="GID-02", agent_name="SONNY", lane="frontend", health="healthy", execution_state="completed", current_pac_id="PAC-BENSON-P21-C", tasks_completed=7, tasks_pending=0, last_heartbeat=now),
        AgentLaneTile(agent_id="GID-04", agent_name="CINDY", lane="backend", health="healthy", execution_state="idle", current_pac_id=None, tasks_completed=0, tasks_pending=1, last_heartbeat=now),
        AgentLaneTile(agent_id="GID-06", agent_name="SAM", lane="security", health="healthy", execution_state="idle", current_pac_id=None, tasks_completed=0, tasks_pending=1, last_heartbeat=now),
        AgentLaneTile(agent_id="GID-07", agent_name="DAN", lane="ci", health="healthy", execution_state="idle", current_pac_id=None, tasks_completed=0, tasks_pending=1, last_heartbeat=now),
        AgentLaneTile(agent_id="GID-08", agent_name="ALEX", lane="governance", health="healthy", execution_state="idle", current_pac_id=None, tasks_completed=0, tasks_pending=1, last_heartbeat=now),
        AgentLaneTile(agent_id="GID-09", agent_name="LIRA", lane="frontend", health="healthy", execution_state="completed", current_pac_id="PAC-BENSON-P21-C", tasks_completed=3, tasks_pending=0, last_heartbeat=now),
        AgentLaneTile(agent_id="GID-10", agent_name="MAGGIE", lane="ml", health="healthy", execution_state="idle", current_pac_id=None, tasks_completed=0, tasks_pending=0, last_heartbeat=now),
        AgentLaneTile(agent_id="GID-11", agent_name="ATLAS", lane="integrity", health="healthy", execution_state="idle", current_pac_id="PAC-BENSON-P21-C", tasks_completed=1, tasks_pending=1, last_heartbeat=now),
    ]


def _get_mock_decisions() -> List[DecisionStreamItem]:
    """Get mock decision stream. Replace with DecisionStore integration."""
    now = datetime.now(timezone.utc)
    return [
        DecisionStreamItem(
            id="pdo-001",
            item_type="pdo",
            timestamp=now,
            pdo_card=PDOCard(
                pdo_id="PDO-P21C-001",
                pac_id="PAC-BENSON-P21-C",
                agent_id="GID-02",
                agent_name="SONNY",
                decision_type="FILE_CREATE",
                description="Create OCC Dashboard components (7 files)",
                outcome="APPROVED",
                invariants_checked=["INV-OCC-001", "INV-SAM-001", "INV-LIRA-001"],
                timestamp=now,
            ),
        ),
        DecisionStreamItem(
            id="pdo-002",
            item_type="pdo",
            timestamp=now,
            pdo_card=PDOCard(
                pdo_id="PDO-P21C-002",
                pac_id="PAC-BENSON-P21-C",
                agent_id="GID-01",
                agent_name="CODY",
                decision_type="FILE_CREATE",
                description="Create OCC Dashboard read-only API endpoints",
                outcome="APPROVED",
                invariants_checked=["INV-OCC-001", "INV-OCC-002"],
                timestamp=now,
            ),
        ),
    ]


def _get_mock_governance() -> GovernanceRailState:
    """Get mock governance state. Replace with GovernanceStore integration."""
    now = datetime.now(timezone.utc)
    return GovernanceRailState(
        invariants=[
            InvariantDisplay(invariant_id="INV-OCC-001", rule_id="RULE-OCC-001", description="No mutation routes - read-only state display", invariant_class="S-INV", status="passing", last_checked=now, source="SAM"),
            InvariantDisplay(invariant_id="INV-OCC-002", rule_id="RULE-OCC-002", description="Always reflects backend state (no optimistic rendering)", invariant_class="S-INV", status="passing", last_checked=now, source="SAM"),
            InvariantDisplay(invariant_id="INV-OCC-003", rule_id="RULE-OCC-003", description="UI reflects invariant failures with rule IDs", invariant_class="A-INV", status="passing", last_checked=now, source="ALEX"),
            InvariantDisplay(invariant_id="INV-KILL-001", rule_id="RULE-KILL-001", description="Kill switch DISABLED unless authorized", invariant_class="X-INV", status="passing", last_checked=now, source="SAM"),
            InvariantDisplay(invariant_id="INV-LIRA-001", rule_id="RULE-ACC-001", description="ARIA labels on all interactive elements", invariant_class="A-INV", status="passing", last_checked=now, source="LIRA"),
            InvariantDisplay(invariant_id="INV-CP-001", rule_id="RULE-CP-001", description="No execution without explicit ACK", invariant_class="X-INV", status="passing", last_checked=now, source="ALEX"),
        ],
        lint_v2_passing=True,
        schema_registry_valid=True,
        fail_closed_active=True,
        last_refresh=now,
    )


def _get_mock_kill_switch() -> KillSwitchStatus:
    """Get mock kill switch status. Replace with KillSwitchStore integration."""
    return KillSwitchStatus(
        state="DISARMED",
        auth_level="ARM_ONLY",
        engaged_by=None,
        engaged_at=None,
        engagement_reason=None,
        affected_pacs=[],
        cooldown_remaining_ms=None,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/agents", response_model=AgentLaneTileListResponse)
async def get_agent_tiles(
    lane: Optional[AgentLane] = Query(None, description="Filter by lane"),
    health: Optional[AgentHealthState] = Query(None, description="Filter by health state"),
    execution_state: Optional[AgentExecutionState] = Query(None, description="Filter by execution state"),
) -> AgentLaneTileListResponse:
    """
    Get agent lane tiles for OCC grid display.

    READ-ONLY: No mutations allowed.
    Invariant: INV-OCC-001 (read-only state display)

    Returns agent tiles with health states and execution status.
    """
    agents = _get_mock_agents()

    # Apply filters
    if lane:
        agents = [a for a in agents if a.lane == lane]
    if health:
        agents = [a for a in agents if a.health == health]
    if execution_state:
        agents = [a for a in agents if a.execution_state == execution_state]

    return AgentLaneTileListResponse(agents=agents, total=len(agents))


@router.get("/decisions", response_model=DecisionStreamResponse)
async def get_decision_stream(
    limit: int = Query(50, ge=1, le=200, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    pac_id: Optional[str] = Query(None, description="Filter by PAC ID"),
    item_type: Optional[Literal["pdo", "ber"]] = Query(None, description="Filter by item type"),
) -> DecisionStreamResponse:
    """
    Get decision stream (PDO cards + BER actions).

    READ-ONLY: No mutations allowed.
    Invariant: INV-OCC-001 (read-only state display)
    Invariant: INV-OCC-002 (reflects backend state)

    Returns chronological decision stream items.
    """
    items = _get_mock_decisions()

    # Apply filters
    if pac_id:
        filtered = []
        for item in items:
            if item.pdo_card and item.pdo_card.pac_id == pac_id:
                filtered.append(item)
            elif item.ber_card and item.ber_card.pac_id == pac_id:
                filtered.append(item)
        items = filtered

    if item_type:
        items = [i for i in items if i.item_type == item_type]

    total = len(items)
    items = items[offset : offset + limit]
    has_more = offset + len(items) < total

    return DecisionStreamResponse(items=items, total=total, has_more=has_more)


@router.get("/governance", response_model=GovernanceRailState)
async def get_governance_rail(
    invariant_class: Optional[InvariantClass] = Query(None, description="Filter by invariant class"),
    status: Optional[InvariantStatus] = Query(None, description="Filter by status"),
) -> GovernanceRailState:
    """
    Get governance rail state (active invariants).

    READ-ONLY: No mutations allowed.
    Invariant: INV-OCC-003 (UI reflects invariant failures with rule IDs)

    Returns governance state with all active invariants and their statuses.
    """
    state = _get_mock_governance()

    # Apply filters to invariants
    invariants = state.invariants
    if invariant_class:
        invariants = [i for i in invariants if i.invariant_class == invariant_class]
    if status:
        invariants = [i for i in invariants if i.status == status]

    return GovernanceRailState(
        invariants=invariants,
        lint_v2_passing=state.lint_v2_passing,
        schema_registry_valid=state.schema_registry_valid,
        fail_closed_active=state.fail_closed_active,
        last_refresh=datetime.now(timezone.utc),
    )


@router.get("/kill-switch", response_model=KillSwitchStatus)
async def get_kill_switch_status() -> KillSwitchStatus:
    """
    Get kill switch status.

    READ-ONLY: No mutations allowed via this endpoint.
    Invariant: INV-KILL-001 (kill switch DISABLED unless authorized)

    Control actions require separate authenticated endpoints with PDO.
    """
    return _get_mock_kill_switch()


@router.get("/state", response_model=OCCDashboardStateResponse)
async def get_dashboard_state() -> OCCDashboardStateResponse:
    """
    Get full OCC dashboard state (aggregate endpoint).

    READ-ONLY: No mutations allowed.
    Combines: agents, decisions, governance, kill-switch

    Use this endpoint to hydrate the entire OCC dashboard in a single request.
    Individual endpoints can be used for targeted refreshes.
    """
    agents = _get_mock_agents()
    decisions = _get_mock_decisions()
    governance = _get_mock_governance()
    kill_switch = _get_mock_kill_switch()

    # Determine active PAC
    active_pac = None
    for agent in agents:
        if agent.execution_state == "executing" and agent.current_pac_id:
            active_pac = agent.current_pac_id
            break

    return OCCDashboardStateResponse(
        agents=agents,
        decision_stream=decisions,
        governance_rail=governance,
        kill_switch=kill_switch,
        active_pac_id=active_pac,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION REJECTION (Explicit 405 handlers)
# ═══════════════════════════════════════════════════════════════════════════════
# Per INV-OCC-001: All OCC Dashboard endpoints are READ-ONLY.
# Mutations must go through proper governance channels with PDO.


@router.post("/agents")
@router.put("/agents")
@router.patch("/agents")
@router.delete("/agents")
async def reject_agent_mutations():
    """Reject mutations on agent tiles. READ-ONLY endpoint."""
    raise HTTPException(
        status_code=405,
        detail="OCC Dashboard endpoints are READ-ONLY. Agent mutations require proper governance channels.",
    )


@router.post("/decisions")
@router.put("/decisions")
@router.patch("/decisions")
@router.delete("/decisions")
async def reject_decision_mutations():
    """Reject mutations on decisions. READ-ONLY endpoint."""
    raise HTTPException(
        status_code=405,
        detail="OCC Dashboard endpoints are READ-ONLY. Decision mutations require PDO submission.",
    )


@router.post("/governance")
@router.put("/governance")
@router.patch("/governance")
@router.delete("/governance")
async def reject_governance_mutations():
    """Reject mutations on governance. READ-ONLY endpoint."""
    raise HTTPException(
        status_code=405,
        detail="OCC Dashboard endpoints are READ-ONLY. Governance mutations require proper channels.",
    )


@router.post("/kill-switch")
@router.put("/kill-switch")
@router.patch("/kill-switch")
@router.delete("/kill-switch")
async def reject_kill_switch_mutations():
    """Reject mutations on kill switch. READ-ONLY endpoint."""
    raise HTTPException(
        status_code=405,
        detail="OCC Dashboard endpoints are READ-ONLY. Kill switch control requires authenticated endpoints.",
    )
