# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Agent Execution OC API
# PAC-008: Agent Execution Visibility — ORDER 3 (Sonny GID-02)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Operator Console API for agent execution visibility.

Provides READ-ONLY endpoints for viewing agent execution state.
No control actions are permitted (INV-AGENT-004).

GOVERNANCE INVARIANTS:
- INV-AGENT-001: Agent activation must be explicit and visible
- INV-AGENT-002: Each execution step maps to exactly one agent
- INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
- INV-AGENT-004: OC is read-only; no agent control actions
- INV-AGENT-005: Missing state must be explicit (no inference)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.execution.agent_events import AgentState, UNAVAILABLE_MARKER
from core.execution.agent_aggregator import (
    AgentExecutionAggregator,
    get_agent_aggregator,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER SETUP
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/oc/agents",
    tags=["operator-console-agents"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS — API CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

class AgentExecutionView(BaseModel):
    """Agent execution view for OC."""
    
    agent_gid: str
    agent_name: str
    agent_role: str
    agent_color: str
    current_state: str
    pac_id: str
    execution_mode: str
    execution_order: Optional[int] = None
    order_description: str = UNAVAILABLE_MARKER
    activated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    artifacts_created: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    ledger_entry_hash: str = UNAVAILABLE_MARKER
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_gid": "GID-01",
                "agent_name": "Cody",
                "agent_role": "Backend / Events",
                "agent_color": "BLUE",
                "current_state": "COMPLETE",
                "pac_id": "PAC-008",
                "execution_mode": "EXECUTION",
                "execution_order": 1,
                "order_description": "Emit agent_activation_event",
            }
        }


class AgentTimelineEvent(BaseModel):
    """Timeline event for agent execution."""
    
    event_id: str
    event_type: str
    timestamp: str
    agent_gid: str
    agent_name: str
    description: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    ledger_entry_hash: str = UNAVAILABLE_MARKER


class PACExecutionView(BaseModel):
    """PAC execution view with all agents."""
    
    pac_id: str
    agents: List[AgentExecutionView] = Field(default_factory=list)
    timeline: List[AgentTimelineEvent] = Field(default_factory=list)
    total_agents: int = 0
    agents_queued: int = 0
    agents_active: int = 0
    agents_complete: int = 0
    agents_failed: int = 0
    execution_started_at: Optional[str] = None
    execution_completed_at: Optional[str] = None
    execution_status: str = "PENDING"


class AgentListResponse(BaseModel):
    """Response for agent list endpoints."""
    
    items: List[AgentExecutionView]
    count: int
    total: int
    limit: int
    offset: int


class PACListResponse(BaseModel):
    """Response for PAC list endpoint."""
    
    items: List[Dict[str, Any]]
    count: int
    total: int


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "ok"
    read_only: bool = True
    api_version: str = "1.0.0"
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# GET ENDPOINTS — READ-ONLY (INV-AGENT-004)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Agent OC Health Check",
    description="Health check for agent execution visibility API."
)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        read_only=True,
        api_version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/active",
    response_model=AgentListResponse,
    summary="Get Active Agents",
    description="Get all currently active agents across all PACs."
)
async def get_active_agents(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AgentListResponse:
    """
    Get all currently active agents.
    
    INV-AGENT-004: This is a read-only view. No control actions permitted.
    """
    try:
        aggregator = get_agent_aggregator()
        agents = aggregator.get_active_agents()
        
        total = len(agents)
        items = agents[offset:offset + limit]
        
        return AgentListResponse(
            items=[AgentExecutionView(**a.to_dict()) for a in items],
            count=len(items),
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Failed to get active agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/pac/{pac_id}",
    response_model=PACExecutionView,
    summary="Get PAC Execution View",
    description="Get comprehensive execution view for a PAC including all agents and timeline."
)
async def get_pac_execution(pac_id: str) -> PACExecutionView:
    """
    Get PAC execution view with all agent states.
    
    INV-AGENT-004: This is a read-only view. No control actions permitted.
    """
    try:
        aggregator = get_agent_aggregator()
        view = aggregator.get_pac_execution_view(pac_id)
        
        return PACExecutionView(
            pac_id=view.pac_id,
            agents=[AgentExecutionView(**a.to_dict()) for a in view.agents],
            timeline=[AgentTimelineEvent(**e.to_dict()) for e in view.timeline],
            total_agents=view.total_agents,
            agents_queued=view.agents_queued,
            agents_active=view.agents_active,
            agents_complete=view.agents_complete,
            agents_failed=view.agents_failed,
            execution_started_at=view.execution_started_at,
            execution_completed_at=view.execution_completed_at,
            execution_status=view.execution_status,
        )
    except Exception as e:
        logger.error(f"Failed to get PAC execution view for {pac_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/pac/{pac_id}/agents",
    response_model=AgentListResponse,
    summary="Get PAC Agents",
    description="Get all agents involved in a PAC execution."
)
async def get_pac_agents(
    pac_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AgentListResponse:
    """
    Get all agents for a PAC.
    
    INV-AGENT-004: This is a read-only view. No control actions permitted.
    """
    try:
        aggregator = get_agent_aggregator()
        agents = aggregator.get_all_agent_views(pac_id)
        
        total = len(agents)
        items = agents[offset:offset + limit]
        
        return AgentListResponse(
            items=[AgentExecutionView(**a.to_dict()) for a in items],
            count=len(items),
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Failed to get PAC agents for {pac_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/pac/{pac_id}/agent/{agent_gid}",
    response_model=AgentExecutionView,
    summary="Get Agent Execution View",
    description="Get execution view for a specific agent in a PAC."
)
async def get_agent_view(pac_id: str, agent_gid: str) -> AgentExecutionView:
    """
    Get specific agent execution view.
    
    INV-AGENT-004: This is a read-only view. No control actions permitted.
    """
    try:
        aggregator = get_agent_aggregator()
        view = aggregator.get_agent_view(pac_id, agent_gid)
        
        if view is None:
            raise HTTPException(
                status_code=404,
                detail=f"Agent {agent_gid} not found in PAC {pac_id}"
            )
        
        return AgentExecutionView(**view.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent view for {agent_gid} in {pac_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/pac/{pac_id}/timeline",
    response_model=List[AgentTimelineEvent],
    summary="Get PAC Timeline",
    description="Get execution timeline for a PAC."
)
async def get_pac_timeline(
    pac_id: str,
    agent_gid: Optional[str] = Query(None, description="Filter by agent GID"),
) -> List[AgentTimelineEvent]:
    """
    Get execution timeline for a PAC.
    
    INV-AGENT-004: This is a read-only view. No control actions permitted.
    """
    try:
        aggregator = get_agent_aggregator()
        events = aggregator.get_agent_timeline(pac_id, agent_gid)
        
        return [AgentTimelineEvent(**e.to_dict()) for e in events]
    except Exception as e:
        logger.error(f"Failed to get timeline for {pac_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/pacs",
    response_model=PACListResponse,
    summary="List PACs with Execution Status",
    description="Get list of all PACs with execution summary."
)
async def list_pacs() -> PACListResponse:
    """
    Get list of all PACs with execution status.
    
    INV-AGENT-004: This is a read-only view. No control actions permitted.
    """
    try:
        aggregator = get_agent_aggregator()
        pacs = aggregator.get_pac_list()
        
        return PACListResponse(
            items=pacs,
            count=len(pacs),
            total=len(pacs),
        )
    except Exception as e:
        logger.error(f"Failed to list PACs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCKED OPERATIONS — INV-AGENT-004
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{path:path}",
    include_in_schema=False,
)
async def block_post(path: str) -> None:
    """
    Block all POST requests.
    
    INV-AGENT-004: OC is read-only; no agent control actions.
    """
    logger.warning(f"INV-AGENT-004: POST blocked on /oc/agents/{path}")
    raise HTTPException(
        status_code=405,
        detail="INV-AGENT-004: Agent OC is read-only. POST not permitted."
    )


@router.put(
    "/{path:path}",
    include_in_schema=False,
)
async def block_put(path: str) -> None:
    """
    Block all PUT requests.
    
    INV-AGENT-004: OC is read-only; no agent control actions.
    """
    logger.warning(f"INV-AGENT-004: PUT blocked on /oc/agents/{path}")
    raise HTTPException(
        status_code=405,
        detail="INV-AGENT-004: Agent OC is read-only. PUT not permitted."
    )


@router.patch(
    "/{path:path}",
    include_in_schema=False,
)
async def block_patch(path: str) -> None:
    """
    Block all PATCH requests.
    
    INV-AGENT-004: OC is read-only; no agent control actions.
    """
    logger.warning(f"INV-AGENT-004: PATCH blocked on /oc/agents/{path}")
    raise HTTPException(
        status_code=405,
        detail="INV-AGENT-004: Agent OC is read-only. PATCH not permitted."
    )


@router.delete(
    "/{path:path}",
    include_in_schema=False,
)
async def block_delete(path: str) -> None:
    """
    Block all DELETE requests.
    
    INV-AGENT-004: OC is read-only; no agent control actions.
    """
    logger.warning(f"INV-AGENT-004: DELETE blocked on /oc/agents/{path}")
    raise HTTPException(
        status_code=405,
        detail="INV-AGENT-004: Agent OC is read-only. DELETE not permitted."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = ["router"]
