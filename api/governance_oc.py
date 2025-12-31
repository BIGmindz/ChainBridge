# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Governance OC API — Visibility Endpoints
# PAC-012: Governance Hardening — ORDER 3 (Sonny GID-05)
# ═══════════════════════════════════════════════════════════════════════════════

"""
FastAPI router for governance visibility in Operations Console.

Provides GET-only endpoints for:
- Agent acknowledgments
- Execution dependencies
- Failure semantics & boundaries
- Non-capabilities display

All endpoints are READ-ONLY. Mutations return 405.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.governance.governance_schema import (
    CANONICAL_NON_CAPABILITIES,
    AcknowledgmentStatus,
    AcknowledgmentType,
    CapabilityCategory,
    FailureMode,
    GovernanceViolation,
    HumanBoundaryStatus,
    HumanInterventionType,
    RollbackStrategy,
    get_acknowledgment_registry,
)
from core.governance.dependency_graph import (
    DependencyStatus,
    DependencyType,
    FailurePropagationMode,
    get_dependency_registry,
    get_causality_registry,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class AcknowledgmentDTO(BaseModel):
    """Acknowledgment response model."""
    ack_id: str
    pac_id: str
    order_id: str
    agent_gid: str
    agent_name: str
    ack_type: str
    status: str
    requested_at: str
    acknowledged_at: Optional[str] = None
    timeout_at: Optional[str] = None
    response_message: Optional[str] = None
    rejection_reason: Optional[str] = None
    ack_hash: str


class AcknowledgmentListDTO(BaseModel):
    """List of acknowledgments response."""
    pac_id: str
    acknowledgments: List[AcknowledgmentDTO]
    total: int
    pending_count: int
    acknowledged_count: int
    rejected_count: int


class DependencyDTO(BaseModel):
    """Dependency response model."""
    dependency_id: str
    pac_id: str
    dependent_order_id: str
    dependent_agent_gid: str
    source_order_id: str
    source_agent_gid: str
    dependency_type: str
    description: str
    status: str
    declared_at: str
    resolved_at: Optional[str] = None
    on_failure_action: str
    is_blocking: bool


class DependencyGraphDTO(BaseModel):
    """Dependency graph response model."""
    pac_id: str
    dependencies: List[DependencyDTO]
    execution_order: List[str]
    total_dependencies: int
    satisfied_count: int
    pending_count: int
    failed_count: int


class CausalityLinkDTO(BaseModel):
    """Causality link response model."""
    link_id: str
    pac_id: str
    order_id: str
    agent_gid: str
    artifact_id: str
    artifact_type: str
    artifact_location: str
    caused_by_order_ids: List[str]
    created_at: str
    link_hash: str


class NonCapabilityDTO(BaseModel):
    """Non-capability response model."""
    capability_id: str
    category: str
    description: str
    reason: str
    applies_to_agents: List[str]
    applies_to_pacs: List[str]
    enforced: bool
    violation_action: str


class NonCapabilitiesListDTO(BaseModel):
    """List of non-capabilities response."""
    non_capabilities: List[NonCapabilityDTO]
    total: int
    categories: List[str]


class FailureSemanticsDTO(BaseModel):
    """Failure semantics summary response."""
    failure_modes: List[str]
    rollback_strategies: List[str]
    propagation_modes: List[str]
    human_intervention_types: List[str]
    human_boundary_statuses: List[str]


class GovernanceSummaryDTO(BaseModel):
    """Overall governance summary response."""
    total_acknowledgments: int
    total_dependencies: int
    total_causality_links: int
    total_non_capabilities: int
    pending_acknowledgments: int
    pending_dependencies: int
    governance_invariants: List[str]


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

governance_oc_router = APIRouter(prefix="/oc/governance", tags=["governance-oc"])


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION REJECTION
# ═══════════════════════════════════════════════════════════════════════════════

@governance_oc_router.api_route(
    "/{path:path}",
    methods=["POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
async def reject_mutations(path: str, request: Request):
    """
    Reject all mutation attempts.
    
    OC endpoints are GET-only. Any mutation attempt returns 405.
    """
    logger.warning(
        f"GOVERNANCE OC: Mutation rejected method={request.method} path={path}"
    )
    raise HTTPException(
        status_code=405,
        detail="Governance OC endpoints are read-only. Mutations not permitted.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ACKNOWLEDGMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@governance_oc_router.get("/acknowledgments/{pac_id}", response_model=AcknowledgmentListDTO)
async def get_acknowledgments(pac_id: str) -> AcknowledgmentListDTO:
    """
    Get all acknowledgments for a PAC.
    
    Returns acknowledgment status for all orders in the PAC.
    """
    registry = get_acknowledgment_registry()
    acks = registry.get_by_pac_id(pac_id)
    
    ack_dtos = [
        AcknowledgmentDTO(
            ack_id=a.ack_id,
            pac_id=a.pac_id,
            order_id=a.order_id,
            agent_gid=a.agent_gid,
            agent_name=a.agent_name,
            ack_type=a.ack_type.value,
            status=a.status.value,
            requested_at=a.requested_at,
            acknowledged_at=a.acknowledged_at,
            timeout_at=a.timeout_at,
            response_message=a.response_message,
            rejection_reason=a.rejection_reason,
            ack_hash=a.ack_hash,
        )
        for a in acks
    ]
    
    pending = sum(1 for a in acks if a.status == AcknowledgmentStatus.PENDING)
    acknowledged = sum(1 for a in acks if a.status == AcknowledgmentStatus.ACKNOWLEDGED)
    rejected = sum(1 for a in acks if a.status == AcknowledgmentStatus.REJECTED)
    
    return AcknowledgmentListDTO(
        pac_id=pac_id,
        acknowledgments=ack_dtos,
        total=len(ack_dtos),
        pending_count=pending,
        acknowledged_count=acknowledged,
        rejected_count=rejected,
    )


@governance_oc_router.get("/acknowledgments/{pac_id}/order/{order_id}")
async def get_acknowledgment_by_order(pac_id: str, order_id: str) -> List[AcknowledgmentDTO]:
    """Get acknowledgments for a specific order."""
    registry = get_acknowledgment_registry()
    acks = registry.get_by_order_id(order_id)
    
    # Filter by PAC ID
    acks = [a for a in acks if a.pac_id == pac_id]
    
    return [
        AcknowledgmentDTO(
            ack_id=a.ack_id,
            pac_id=a.pac_id,
            order_id=a.order_id,
            agent_gid=a.agent_gid,
            agent_name=a.agent_name,
            ack_type=a.ack_type.value,
            status=a.status.value,
            requested_at=a.requested_at,
            acknowledged_at=a.acknowledged_at,
            timeout_at=a.timeout_at,
            response_message=a.response_message,
            rejection_reason=a.rejection_reason,
            ack_hash=a.ack_hash,
        )
        for a in acks
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@governance_oc_router.get("/dependencies/{pac_id}", response_model=DependencyGraphDTO)
async def get_dependency_graph(pac_id: str) -> DependencyGraphDTO:
    """
    Get the dependency graph for a PAC.
    
    Returns all dependencies and execution order.
    """
    registry = get_dependency_registry()
    graph = registry.get(pac_id)
    
    if not graph:
        return DependencyGraphDTO(
            pac_id=pac_id,
            dependencies=[],
            execution_order=[],
            total_dependencies=0,
            satisfied_count=0,
            pending_count=0,
            failed_count=0,
        )
    
    graph_dict = graph.to_dict()
    
    dep_dtos = []
    satisfied = 0
    pending = 0
    failed = 0
    
    for dep in graph_dict["dependencies"]:
        dep_dto = DependencyDTO(
            dependency_id=dep["dependency_id"],
            pac_id=dep["pac_id"],
            dependent_order_id=dep["dependent_order_id"],
            dependent_agent_gid=dep["dependent_agent_gid"],
            source_order_id=dep["source_order_id"],
            source_agent_gid=dep["source_agent_gid"],
            dependency_type=dep["dependency_type"],
            description=dep["description"],
            status=dep["status"],
            declared_at=dep["declared_at"],
            resolved_at=dep.get("resolved_at"),
            on_failure_action=dep["on_failure_action"],
            is_blocking=dep["dependency_type"] == "HARD",
        )
        dep_dtos.append(dep_dto)
        
        if dep["status"] == "SATISFIED":
            satisfied += 1
        elif dep["status"] == "PENDING":
            pending += 1
        elif dep["status"] == "FAILED":
            failed += 1
    
    return DependencyGraphDTO(
        pac_id=pac_id,
        dependencies=dep_dtos,
        execution_order=graph_dict["execution_order"],
        total_dependencies=len(dep_dtos),
        satisfied_count=satisfied,
        pending_count=pending,
        failed_count=failed,
    )


@governance_oc_router.get("/dependencies/{pac_id}/order/{order_id}")
async def get_dependencies_for_order(pac_id: str, order_id: str) -> List[DependencyDTO]:
    """Get dependencies for a specific order."""
    registry = get_dependency_registry()
    graph = registry.get(pac_id)
    
    if not graph:
        return []
    
    deps = graph.get_dependencies_for(order_id)
    
    return [
        DependencyDTO(
            dependency_id=d.dependency_id,
            pac_id=d.pac_id,
            dependent_order_id=d.dependent_order_id,
            dependent_agent_gid=d.dependent_agent_gid,
            source_order_id=d.source_order_id,
            source_agent_gid=d.source_agent_gid,
            dependency_type=d.dependency_type.value,
            description=d.description,
            status=d.status.value,
            declared_at=d.declared_at,
            resolved_at=d.resolved_at,
            on_failure_action=d.on_failure_action,
            is_blocking=d.is_blocking,
        )
        for d in deps
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# CAUSALITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@governance_oc_router.get("/causality/{pac_id}/order/{order_id}")
async def get_causality_for_order(pac_id: str, order_id: str) -> List[CausalityLinkDTO]:
    """Get causality links for artifacts produced by an order."""
    registry = get_causality_registry()
    links = registry.get_artifacts_by_order(order_id)
    
    return [
        CausalityLinkDTO(
            link_id=l.link_id,
            pac_id=l.pac_id,
            order_id=l.order_id,
            agent_gid=l.agent_gid,
            artifact_id=l.artifact.artifact_id,
            artifact_type=l.artifact.artifact_type.value,
            artifact_location=l.artifact.location,
            caused_by_order_ids=l.caused_by_order_ids,
            created_at=l.created_at,
            link_hash=l.link_hash,
        )
        for l in links
    ]


@governance_oc_router.get("/causality/trace/{artifact_id}")
async def trace_artifact_causality(artifact_id: str) -> Dict[str, Any]:
    """Trace causality chain for an artifact."""
    registry = get_causality_registry()
    chain = registry.trace_causality(artifact_id)
    
    return {
        "artifact_id": artifact_id,
        "causality_chain": chain,
        "chain_length": len(chain),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NON-CAPABILITIES ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@governance_oc_router.get("/non-capabilities", response_model=NonCapabilitiesListDTO)
async def get_non_capabilities() -> NonCapabilitiesListDTO:
    """
    Get all declared non-capabilities.
    
    Returns the canonical list of things the system explicitly cannot do.
    """
    non_cap_dtos = [
        NonCapabilityDTO(
            capability_id=nc.capability_id,
            category=nc.category.value,
            description=nc.description,
            reason=nc.reason,
            applies_to_agents=nc.applies_to_agents,
            applies_to_pacs=nc.applies_to_pacs,
            enforced=nc.enforced,
            violation_action=nc.violation_action,
        )
        for nc in CANONICAL_NON_CAPABILITIES
    ]
    
    categories = list(set(nc.category.value for nc in CANONICAL_NON_CAPABILITIES))
    
    return NonCapabilitiesListDTO(
        non_capabilities=non_cap_dtos,
        total=len(non_cap_dtos),
        categories=sorted(categories),
    )


@governance_oc_router.get("/non-capabilities/category/{category}")
async def get_non_capabilities_by_category(category: str) -> List[NonCapabilityDTO]:
    """Get non-capabilities filtered by category."""
    try:
        cat_enum = CapabilityCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {category}. Valid: {[c.value for c in CapabilityCategory]}",
        )
    
    return [
        NonCapabilityDTO(
            capability_id=nc.capability_id,
            category=nc.category.value,
            description=nc.description,
            reason=nc.reason,
            applies_to_agents=nc.applies_to_agents,
            applies_to_pacs=nc.applies_to_pacs,
            enforced=nc.enforced,
            violation_action=nc.violation_action,
        )
        for nc in CANONICAL_NON_CAPABILITIES
        if nc.category == cat_enum
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# FAILURE SEMANTICS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@governance_oc_router.get("/failure-semantics", response_model=FailureSemanticsDTO)
async def get_failure_semantics() -> FailureSemanticsDTO:
    """
    Get failure semantics reference.
    
    Returns all failure modes, rollback strategies, and related enumerations.
    """
    return FailureSemanticsDTO(
        failure_modes=[m.value for m in FailureMode],
        rollback_strategies=[r.value for r in RollbackStrategy],
        propagation_modes=[p.value for p in FailurePropagationMode],
        human_intervention_types=[h.value for h in HumanInterventionType],
        human_boundary_statuses=[s.value for s in HumanBoundaryStatus],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE SUMMARY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@governance_oc_router.get("/summary", response_model=GovernanceSummaryDTO)
async def get_governance_summary() -> GovernanceSummaryDTO:
    """
    Get overall governance summary.
    
    Returns counts and status across all governance mechanisms.
    """
    ack_registry = get_acknowledgment_registry()
    dep_registry = get_dependency_registry()
    causality_registry = get_causality_registry()
    
    # Count acknowledgments
    total_acks = len(ack_registry)
    pending_acks = 0  # Would need iteration to count
    
    # Count dependencies across all PACs
    total_deps = 0
    pending_deps = 0
    for pac_id in dep_registry.list_pac_ids():
        graph = dep_registry.get(pac_id)
        if graph:
            graph_dict = graph.to_dict()
            total_deps += len(graph_dict["dependencies"])
            pending_deps += sum(
                1 for d in graph_dict["dependencies"]
                if d["status"] == "PENDING"
            )
    
    # Governance invariants
    invariants = [
        "INV-GOV-001: Explicit agent acknowledgment required",
        "INV-GOV-002: No execution without declared dependencies",
        "INV-GOV-003: No silent partial success",
        "INV-GOV-004: No undeclared capabilities",
        "INV-GOV-005: No human override without PDO",
        "INV-GOV-006: Retention & time bounds explicit",
        "INV-GOV-007: Training signals classified",
        "INV-GOV-008: Fail-closed on any violation",
    ]
    
    return GovernanceSummaryDTO(
        total_acknowledgments=total_acks,
        total_dependencies=total_deps,
        total_causality_links=len(causality_registry),
        total_non_capabilities=len(CANONICAL_NON_CAPABILITIES),
        pending_acknowledgments=pending_acks,
        pending_dependencies=pending_deps,
        governance_invariants=invariants,
    )


@governance_oc_router.get("/invariants")
async def get_governance_invariants() -> Dict[str, Any]:
    """Get governance invariants reference."""
    return {
        "invariants": {
            "INV-GOV-001": {
                "name": "Explicit agent acknowledgment required",
                "description": "Every execution requires explicit agent acknowledgment before proceeding",
                "enforcement": "AcknowledgmentRegistry validates before execution",
            },
            "INV-GOV-002": {
                "name": "No execution without declared dependencies",
                "description": "All execution dependencies must be declared and validated",
                "enforcement": "DependencyGraph validates before execution",
            },
            "INV-GOV-003": {
                "name": "No silent partial success",
                "description": "Partial successes must be explicitly declared, never silent",
                "enforcement": "ExecutionOutcome.PARTIAL_SUCCESS must be explicit",
            },
            "INV-GOV-004": {
                "name": "No undeclared capabilities",
                "description": "System can only do what is explicitly declared",
                "enforcement": "CANONICAL_NON_CAPABILITIES defines explicit boundaries",
            },
            "INV-GOV-005": {
                "name": "No human override without PDO",
                "description": "Human overrides require explicit PDO reference",
                "enforcement": "HumanIntervention.validate_override() checks PDO",
            },
            "INV-GOV-006": {
                "name": "Retention & time bounds explicit",
                "description": "All data retention periods must be declared",
                "enforcement": "RetentionPolicy declarations required",
            },
            "INV-GOV-007": {
                "name": "Training signals classified",
                "description": "All data used for training must be classified",
                "enforcement": "TrainingSignalClassification required",
            },
            "INV-GOV-008": {
                "name": "Fail-closed on any violation",
                "description": "Any governance violation results in failure, not degradation",
                "enforcement": "GovernanceViolation exception halts execution",
            },
        },
        "total": 8,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "governance_oc_router",
    # DTOs
    "AcknowledgmentDTO",
    "AcknowledgmentListDTO",
    "DependencyDTO",
    "DependencyGraphDTO",
    "CausalityLinkDTO",
    "NonCapabilityDTO",
    "NonCapabilitiesListDTO",
    "FailureSemanticsDTO",
    "GovernanceSummaryDTO",
]
