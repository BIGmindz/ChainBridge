# ═══════════════════════════════════════════════════════════════════════════════
# OCC Agent History API — Agent Drilldown Endpoints
# PAC-BENSON-P22-C: OCC + Control Plane Deepening
#
# Provides GET-only endpoints for agent drilldown:
# - /occ/agents/{agent_id}/history     - Agent execution history
# - /occ/agents/{agent_id}/drilldown   - Full drilldown (history, failures, evidence)
# - /occ/agents/{agent_id}/failures    - Failure records
# - /occ/agents/{agent_id}/evidence    - Evidence artifacts
# - /occ/agents/{agent_id}/metrics     - Performance metrics
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

router = APIRouter(prefix="/occ/agents", tags=["OCC Agents"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

ExecutionStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
FailureSeverity = Literal["low", "medium", "high", "critical"]
ArtifactType = Literal["log", "trace", "snapshot", "evidence", "proofpack", "screenshot", "metric"]


class AgentExecutionRecord(BaseModel):
    """Agent execution record."""
    execution_id: str
    pac_id: str
    agent_id: str
    task_name: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    output_summary: Optional[str] = None
    evidence_hash: Optional[str] = None


class AgentFailureRecord(BaseModel):
    """Agent failure record."""
    failure_id: str
    execution_id: str
    pac_id: str
    agent_id: str
    timestamp: datetime
    severity: FailureSeverity
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class AgentEvidenceArtifact(BaseModel):
    """Agent evidence artifact."""
    artifact_id: str
    execution_id: str
    pac_id: str
    agent_id: str
    artifact_type: ArtifactType
    name: str
    description: str
    created_at: datetime
    size_bytes: int
    content_hash: str
    verified: bool = False


class AgentPerformanceMetrics(BaseModel):
    """Agent performance metrics."""
    agent_id: str
    agent_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_duration_ms: float
    min_duration_ms: int
    max_duration_ms: int
    total_artifacts_generated: int
    period_start: datetime
    period_end: datetime


class AgentDrilldownResponse(BaseModel):
    """Complete agent drilldown response."""
    agent_id: str
    agent_name: str
    agent_role: str
    lane: str
    current_status: Literal["idle", "active", "paused", "error"]
    executions: List[AgentExecutionRecord]
    failures: List[AgentFailureRecord]
    evidence: List[AgentEvidenceArtifact]
    metrics: AgentPerformanceMetrics
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionHistoryResponse(BaseModel):
    """Paginated execution history response."""
    executions: List[AgentExecutionRecord]
    total: int
    has_more: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FailuresResponse(BaseModel):
    """Paginated failures response."""
    failures: List[AgentFailureRecord]
    total: int
    has_more: bool
    unresolved_count: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceResponse(BaseModel):
    """Paginated evidence response."""
    artifacts: List[AgentEvidenceArtifact]
    total: int
    has_more: bool
    total_size_bytes: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_REGISTRY = {
    "GID-00": {"name": "BENSON", "role": "Orchestrator", "lane": "orchestration"},
    "GID-01": {"name": "CODY", "role": "Backend Lead", "lane": "backend"},
    "GID-02": {"name": "SONNY", "role": "Frontend Lead", "lane": "frontend"},
    "GID-03": {"name": "LIRA", "role": "UX/Accessibility Lead", "lane": "frontend"},
    "GID-04": {"name": "CINDY", "role": "Backend Support", "lane": "backend"},
    "GID-05": {"name": "SAM", "role": "Security Hardener", "lane": "security"},
    "GID-06": {"name": "MAGGIE", "role": "Documentation Lead", "lane": "docs"},
    "GID-07": {"name": "DAN", "role": "DevOps/CI Lead", "lane": "infra"},
    "GID-11": {"name": "ATLAS", "role": "Repo Integrity Engineer", "lane": "governance"},
}


def _get_mock_executions(agent_id: str) -> List[AgentExecutionRecord]:
    """Get mock execution history."""
    now = datetime.now(timezone.utc)
    return [
        AgentExecutionRecord(
            execution_id="exec-001",
            pac_id="PAC-BENSON-P22-C",
            agent_id=agent_id,
            task_name="Timeline View implementation",
            status="completed",
            started_at=now,
            completed_at=now,
            duration_ms=45000,
            output_summary="5 files created",
            evidence_hash="abc123",
        ),
        AgentExecutionRecord(
            execution_id="exec-002",
            pac_id="PAC-BENSON-P22-C",
            agent_id=agent_id,
            task_name="Agent Drilldown implementation",
            status="completed",
            started_at=now,
            completed_at=now,
            duration_ms=38000,
            output_summary="3 files created",
            evidence_hash="def456",
        ),
    ]


def _get_mock_failures(agent_id: str) -> List[AgentFailureRecord]:
    """Get mock failures."""
    return []  # No failures in mock


def _get_mock_evidence(agent_id: str) -> List[AgentEvidenceArtifact]:
    """Get mock evidence."""
    now = datetime.now(timezone.utc)
    return [
        AgentEvidenceArtifact(
            artifact_id="art-001",
            execution_id="exec-001",
            pac_id="PAC-BENSON-P22-C",
            agent_id=agent_id,
            artifact_type="evidence",
            name="Timeline types",
            description="TypeScript type definitions",
            created_at=now,
            size_bytes=8500,
            content_hash="sha256:abc123",
            verified=True,
        ),
    ]


def _get_mock_metrics(agent_id: str) -> AgentPerformanceMetrics:
    """Get mock metrics."""
    now = datetime.now(timezone.utc)
    agent_info = AGENT_REGISTRY.get(agent_id, {"name": "Unknown"})
    return AgentPerformanceMetrics(
        agent_id=agent_id,
        agent_name=agent_info["name"],
        total_executions=10,
        successful_executions=10,
        failed_executions=0,
        success_rate=100.0,
        avg_duration_ms=42000,
        min_duration_ms=30000,
        max_duration_ms=55000,
        total_artifacts_generated=15,
        period_start=now,
        period_end=now,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/{agent_id}/drilldown", response_model=AgentDrilldownResponse)
async def get_agent_drilldown(agent_id: str) -> AgentDrilldownResponse:
    """
    Get full agent drilldown data.

    READ-ONLY: No mutations allowed.
    Invariant: INV-OCC-004 (Timeline completeness)
    Invariant: INV-OCC-005 (Evidence immutability)
    """
    agent_info = AGENT_REGISTRY.get(agent_id)
    if not agent_info:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return AgentDrilldownResponse(
        agent_id=agent_id,
        agent_name=agent_info["name"],
        agent_role=agent_info["role"],
        lane=agent_info["lane"],
        current_status="active",
        executions=_get_mock_executions(agent_id),
        failures=_get_mock_failures(agent_id),
        evidence=_get_mock_evidence(agent_id),
        metrics=_get_mock_metrics(agent_id),
    )


@router.get("/{agent_id}/history", response_model=ExecutionHistoryResponse)
async def get_agent_history(
    agent_id: str,
    pac_id: Optional[str] = Query(None),
    status: Optional[ExecutionStatus] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ExecutionHistoryResponse:
    """
    Get agent execution history.

    READ-ONLY: No mutations allowed.
    """
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    executions = _get_mock_executions(agent_id)

    # Apply filters
    if pac_id:
        executions = [e for e in executions if e.pac_id == pac_id]
    if status:
        executions = [e for e in executions if e.status == status]

    total = len(executions)
    executions = executions[offset:offset + limit]
    has_more = offset + len(executions) < total

    return ExecutionHistoryResponse(executions=executions, total=total, has_more=has_more)


@router.get("/{agent_id}/failures", response_model=FailuresResponse)
async def get_agent_failures(
    agent_id: str,
    severity: Optional[FailureSeverity] = Query(None),
    resolved: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> FailuresResponse:
    """
    Get agent failure records.

    READ-ONLY: No mutations allowed.
    """
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    failures = _get_mock_failures(agent_id)

    # Apply filters
    if severity:
        failures = [f for f in failures if f.severity == severity]
    if resolved is not None:
        failures = [f for f in failures if f.resolved == resolved]

    total = len(failures)
    unresolved_count = len([f for f in failures if not f.resolved])
    failures = failures[offset:offset + limit]
    has_more = offset + len(failures) < total

    return FailuresResponse(
        failures=failures,
        total=total,
        has_more=has_more,
        unresolved_count=unresolved_count,
    )


@router.get("/{agent_id}/evidence", response_model=EvidenceResponse)
async def get_agent_evidence(
    agent_id: str,
    artifact_type: Optional[ArtifactType] = Query(None),
    pac_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> EvidenceResponse:
    """
    Get agent evidence artifacts.

    READ-ONLY: No mutations allowed.
    Invariant: INV-OCC-005 (Evidence immutability)
    """
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    artifacts = _get_mock_evidence(agent_id)

    # Apply filters
    if artifact_type:
        artifacts = [a for a in artifacts if a.artifact_type == artifact_type]
    if pac_id:
        artifacts = [a for a in artifacts if a.pac_id == pac_id]

    total = len(artifacts)
    total_size = sum(a.size_bytes for a in artifacts)
    artifacts = artifacts[offset:offset + limit]
    has_more = offset + len(artifacts) < total

    return EvidenceResponse(
        artifacts=artifacts,
        total=total,
        has_more=has_more,
        total_size_bytes=total_size,
    )


@router.get("/{agent_id}/metrics", response_model=AgentPerformanceMetrics)
async def get_agent_metrics(agent_id: str) -> AgentPerformanceMetrics:
    """
    Get agent performance metrics.

    READ-ONLY: No mutations allowed.
    """
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return _get_mock_metrics(agent_id)


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION REJECTION
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/{agent_id}")
@router.put("/{agent_id}")
@router.patch("/{agent_id}")
@router.delete("/{agent_id}")
async def reject_agent_mutations(agent_id: str):
    """Reject mutations. READ-ONLY endpoint."""
    raise HTTPException(
        status_code=405,
        detail="Agent endpoints are READ-ONLY. INV-OCC-005: Evidence immutability.",
    )
