# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Trace OC API
# PAC-009: Full End-to-End Traceability — ORDER 4 (Sonny GID-02)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Operator Console API for end-to-end trace visibility.

Provides GET-only endpoints for:
- Full trace view by PDO
- Trace timeline events
- PAC trace summary
- Trace gap indicators

GOVERNANCE INVARIANTS:
- INV-TRACE-004: OC renders full chain without inference
- INV-TRACE-005: Missing links are explicit and non-silent
- READ-ONLY: No mutation endpoints permitted
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from core.execution.trace_registry import (
    TraceDomain,
    TraceLink,
    get_trace_registry,
    UNAVAILABLE_MARKER,
)
from core.execution.trace_aggregator import (
    OCTraceView,
    OCTraceTimeline,
    TraceGraphAggregator,
    get_trace_aggregator,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/oc/trace",
    tags=["Operator Console - Trace"],
    responses={
        405: {"description": "Method Not Allowed - OC is read-only"},
    },
)


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

FORBIDDEN_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@router.api_route(
    "/{path:path}",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def reject_mutations(path: str, request: Request) -> Response:
    """
    Reject all mutation attempts.
    
    OC is strictly read-only. No mutations permitted.
    """
    logger.warning(
        f"OC_TRACE_API: Rejected {request.method} to /oc/trace/{path}"
    )
    raise HTTPException(
        status_code=405,
        detail={
            "error": "METHOD_NOT_ALLOWED",
            "message": "Operator Console Trace API is read-only",
            "permitted_methods": ["GET"],
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE VIEW ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/pdo/{pdo_id}",
    response_model=None,
    summary="Get full trace view for PDO",
    description="Returns complete end-to-end trace from PDO → Agent → Settlement → Ledger",
)
async def get_pdo_trace_view(
    pdo_id: str,
    include_gaps: bool = Query(True, description="Include trace gap indicators"),
) -> Dict[str, Any]:
    """
    Get complete trace view for a PDO.
    
    INV-TRACE-004: OC renders full chain without inference.
    
    Args:
        pdo_id: PDO identifier
        include_gaps: Whether to include gap indicators
    
    Returns:
        Full trace view with all domains and links
    """
    try:
        aggregator = get_trace_aggregator()
        view = aggregator.aggregate_trace_view(pdo_id)
        
        result = view.to_dict()
        
        # Optionally exclude gaps
        if not include_gaps:
            result["gaps"] = []
        
        logger.debug(
            f"OC_TRACE_API: Returned trace view for PDO {pdo_id} "
            f"[nodes={view.total_nodes}, gaps={len(view.gaps)}]"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"OC_TRACE_API: Error getting trace view for PDO {pdo_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TRACE_VIEW_ERROR",
                "message": str(e),
                "pdo_id": pdo_id,
            },
        )


@router.get(
    "/pdo/{pdo_id}/timeline",
    response_model=None,
    summary="Get trace timeline for PDO",
    description="Returns chronological timeline of trace events",
)
async def get_pdo_trace_timeline(pdo_id: str) -> Dict[str, Any]:
    """
    Get chronological trace timeline for a PDO.
    
    Args:
        pdo_id: PDO identifier
    
    Returns:
        Timeline of trace events ordered by timestamp
    """
    try:
        aggregator = get_trace_aggregator()
        timeline = aggregator.aggregate_trace_timeline(pdo_id)
        
        logger.debug(
            f"OC_TRACE_API: Returned timeline for PDO {pdo_id} "
            f"[events={len(timeline.events)}]"
        )
        
        return timeline.to_dict()
        
    except Exception as e:
        logger.error(f"OC_TRACE_API: Error getting timeline for PDO {pdo_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TRACE_TIMELINE_ERROR",
                "message": str(e),
                "pdo_id": pdo_id,
            },
        )


@router.get(
    "/pdo/{pdo_id}/gaps",
    response_model=None,
    summary="Get trace gaps for PDO",
    description="Returns explicit list of missing trace links (INV-TRACE-005)",
)
async def get_pdo_trace_gaps(pdo_id: str) -> Dict[str, Any]:
    """
    Get trace gaps for a PDO.
    
    INV-TRACE-005: Missing links are explicit and non-silent.
    
    Args:
        pdo_id: PDO identifier
    
    Returns:
        List of identified trace gaps
    """
    try:
        aggregator = get_trace_aggregator()
        view = aggregator.aggregate_trace_view(pdo_id)
        
        result = {
            "pdo_id": pdo_id,
            "gaps": [g.to_dict() for g in view.gaps],
            "gap_count": len(view.gaps),
            "completeness_score": view.completeness_score,
            "status": view.status.value,
        }
        
        logger.debug(
            f"OC_TRACE_API: Returned gaps for PDO {pdo_id} "
            f"[gaps={len(view.gaps)}]"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"OC_TRACE_API: Error getting gaps for PDO {pdo_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TRACE_GAPS_ERROR",
                "message": str(e),
                "pdo_id": pdo_id,
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-LEVEL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/pac/{pac_id}",
    response_model=None,
    summary="Get trace summary for PAC",
    description="Returns aggregated trace summary for all PDOs in a PAC",
)
async def get_pac_trace_summary(pac_id: str) -> Dict[str, Any]:
    """
    Get trace summary for all PDOs in a PAC.
    
    Args:
        pac_id: PAC identifier
    
    Returns:
        PAC-level trace summary with PDO breakdowns
    """
    try:
        aggregator = get_trace_aggregator()
        summary = aggregator.aggregate_pac_trace_summary(pac_id)
        
        logger.debug(
            f"OC_TRACE_API: Returned PAC summary for {pac_id} "
            f"[pdos={summary['pdo_count']}, gaps={summary['total_gaps']}]"
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"OC_TRACE_API: Error getting PAC summary for {pac_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "PAC_TRACE_SUMMARY_ERROR",
                "message": str(e),
                "pac_id": pac_id,
            },
        )


@router.get(
    "/pac/{pac_id}/links",
    response_model=None,
    summary="Get all trace links for PAC",
    description="Returns all trace links registered for a PAC",
)
async def get_pac_trace_links(
    pac_id: str,
    domain: Optional[str] = Query(None, description="Filter by target domain"),
) -> Dict[str, Any]:
    """
    Get all trace links for a PAC.
    
    Args:
        pac_id: PAC identifier
        domain: Optional domain filter (DECISION, EXECUTION, SETTLEMENT, LEDGER)
    
    Returns:
        List of trace links
    """
    try:
        registry = get_trace_registry()
        links = registry.get_by_pac_id(pac_id)
        
        # Filter by domain if specified
        if domain:
            try:
                target_domain = TraceDomain(domain)
                links = [l for l in links if l.target_domain == target_domain]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "INVALID_DOMAIN",
                        "message": f"Invalid domain: {domain}",
                        "valid_domains": TraceDomain.values(),
                    },
                )
        
        result = {
            "pac_id": pac_id,
            "links": [l.to_dict() for l in links],
            "link_count": len(links),
            "domain_filter": domain,
        }
        
        logger.debug(
            f"OC_TRACE_API: Returned links for PAC {pac_id} "
            f"[links={len(links)}, domain={domain}]"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OC_TRACE_API: Error getting links for PAC {pac_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "PAC_TRACE_LINKS_ERROR",
                "message": str(e),
                "pac_id": pac_id,
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CLICK-THROUGH ENDPOINTS (Navigation)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/navigate/{domain}/{entity_id}",
    response_model=None,
    summary="Navigate to trace entity",
    description="Get trace context for a specific entity (click-through navigation)",
)
async def navigate_trace_entity(
    domain: str,
    entity_id: str,
) -> Dict[str, Any]:
    """
    Get trace context for click-through navigation.
    
    Supports navigation from any domain entity to its trace context.
    
    Args:
        domain: Entity domain (DECISION, EXECUTION, SETTLEMENT, LEDGER)
        entity_id: Entity identifier
    
    Returns:
        Trace context for the entity
    """
    try:
        # Validate domain
        try:
            trace_domain = TraceDomain(domain)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_DOMAIN",
                    "message": f"Invalid domain: {domain}",
                    "valid_domains": TraceDomain.values(),
                },
            )
        
        registry = get_trace_registry()
        
        # Get links where this entity is the source
        source_links = registry.get_by_source(trace_domain, entity_id)
        
        # Get links where this entity is the target
        target_links = registry.get_by_target(trace_domain, entity_id)
        
        # Find PDO ID if available
        pdo_id = UNAVAILABLE_MARKER
        for link in source_links + target_links:
            if link.pdo_id:
                pdo_id = link.pdo_id
                break
        
        result = {
            "domain": domain,
            "entity_id": entity_id,
            "pdo_id": pdo_id,
            "outbound_links": [l.to_dict() for l in source_links],
            "inbound_links": [l.to_dict() for l in target_links],
            "total_links": len(source_links) + len(target_links),
        }
        
        # If PDO found, include navigation hints
        if pdo_id != UNAVAILABLE_MARKER:
            result["navigation"] = {
                "full_trace_url": f"/oc/trace/pdo/{pdo_id}",
                "timeline_url": f"/oc/trace/pdo/{pdo_id}/timeline",
                "gaps_url": f"/oc/trace/pdo/{pdo_id}/gaps",
            }
        
        logger.debug(
            f"OC_TRACE_API: Navigation for {domain}:{entity_id} "
            f"[outbound={len(source_links)}, inbound={len(target_links)}]"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"OC_TRACE_API: Error navigating to {domain}:{entity_id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TRACE_NAVIGATION_ERROR",
                "message": str(e),
                "domain": domain,
                "entity_id": entity_id,
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CHAIN VERIFICATION ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/verify/chain",
    response_model=None,
    summary="Verify trace chain integrity",
    description="Verify the hash chain integrity of the trace registry",
)
async def verify_trace_chain() -> Dict[str, Any]:
    """
    Verify trace chain integrity.
    
    INV-TRACE-003: Ledger hash links all phases.
    
    Returns:
        Chain verification result
    """
    try:
        registry = get_trace_registry()
        is_valid, error_message = registry.verify_chain()
        
        result = {
            "chain_valid": is_valid,
            "error_message": error_message,
            "total_links": len(registry),
        }
        
        if is_valid:
            latest = registry.get_latest()
            if latest:
                result["latest_hash"] = latest.trace_hash
                result["latest_timestamp"] = latest.timestamp
        
        logger.debug(
            f"OC_TRACE_API: Chain verification [valid={is_valid}]"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"OC_TRACE_API: Error verifying chain: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "CHAIN_VERIFICATION_ERROR",
                "message": str(e),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = ["router"]
