"""
ChainIQ FastAPI Router

Exposes risk scoring and intelligence endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException

from .risk_engine import calculate_risk_score
from .services.event_publisher import EventPublisher
from .services.risk_orchestrator import RiskOrchestrator
from .schemas import (
    AtRiskShipmentsResponse,
    AtRiskShipmentSummary,
    EntityHistoryRecord,
    EntityHistoryResponse,
    OptionsAdvisorResponse,
    PaymentQueueItem,
    PaymentQueueResponse,
    ProofPackResponse,
    RecentRiskResponse,
    ReplayResponse,
    RiskHistoryItem,
    RiskHistoryResponse,
    RiskSnapshot,
    ShipmentRiskRequest,
    ShipmentRiskResponse,
    SimulationRequest,
    SimulationResultResponse,
)

# Import options engine
try:
    from options import suggest_options_for_shipment

    OPTIONS_AVAILABLE = True
except ImportError as e:
    OPTIONS_AVAILABLE = False
    suggest_options_for_shipment = None
    logger = logging.getLogger(__name__)
    logger.warning("ChainIQ options engine not available: %s", str(e))

# Import storage with error handling
try:
    import sys
    from pathlib import Path

    # Add chainiq-service to path if not already there
    chainiq_path = Path(__file__).parent.parent
    if str(chainiq_path) not in sys.path:
        sys.path.insert(0, str(chainiq_path))

    from simulation import simulate_option_for_shipment
    from storage import (
        get_history,
        get_latest_risk_for_shipment,
        get_payment_queue_entry_for_shipment,
        get_score,
        init_db,
        insert_score,
        list_scores,
        replay_request,
    )

    STORAGE_AVAILABLE = True
    SIMULATION_AVAILABLE = True
except ImportError as e:
    STORAGE_AVAILABLE = False
    SIMULATION_AVAILABLE = False
    init_db = None
    insert_score = None
    get_score = None
    list_scores = None
    replay_request = None
    get_history = None
    get_latest_risk_for_shipment = None
    get_payment_queue_entry_for_shipment = None
    simulate_option_for_shipment = None
    logger = logging.getLogger(__name__)
    logger.warning("ChainIQ storage not available: %s", str(e))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iq", tags=["ChainIQ"])


@router.post("/score-shipment", response_model=ShipmentRiskResponse)
async def score_shipment(request: ShipmentRiskRequest) -> ShipmentRiskResponse:
    """
    Calculate risk score for a shipment.

    Business Purpose:
    Enables operators to make informed payment release decisions.

    Decision Context:
    "Should we release payment for this shipment, or is the risk too high?"

    Returns:
    - risk_score: 0-100 (higher = riskier)
    - severity: LOW, MEDIUM, HIGH, CRITICAL
    - reason_codes: Specific risk factors identified
    - recommended_action: What operator should do next

    Example:
        POST /iq/score-shipment
        {
            "shipment_id": "SHP-1001",
            "route": "CN-US",
            "carrier_id": "CARRIER-001",
            "shipment_value_usd": 25000,
            "days_in_transit": 5,
            "expected_days": 7,
            "documents_complete": true,
            "shipper_payment_score": 85
        }

        Response:
        {
            "shipment_id": "SHP-1001",
            "risk_score": 25,
            "severity": "LOW",
            "reason_codes": ["ELEVATED_VALUE"],
            "recommended_action": "RELEASE_PAYMENT"
        }
    """

    try:
        logger.info("Scoring shipment: %s", request.shipment_id)

        # Calculate risk score using deterministic engine (with optional IoT signals)
        risk_score, severity, reason_codes, recommended_action = calculate_risk_score(
            route=request.route,
            carrier_id=request.carrier_id,
            shipment_value_usd=request.shipment_value_usd,
            days_in_transit=request.days_in_transit,
            expected_days=request.expected_days,
            documents_complete=request.documents_complete,
            shipper_payment_score=request.shipper_payment_score,
            request=request,
        )

        response = ShipmentRiskResponse(
            shipment_id=request.shipment_id,
            risk_score=risk_score,
            severity=severity,
            reason_codes=reason_codes,
            recommended_action=recommended_action,
        )

        # Persist decision to database (if available)
        if STORAGE_AVAILABLE and insert_score is not None:
            try:
                insert_score(
                    shipment_id=request.shipment_id,
                    risk_score=risk_score,
                    severity=severity,
                    recommended_action=recommended_action,
                    reason_codes=reason_codes,
                    request_data=request.model_dump(),
                    response_data=response.model_dump(),
                )
            except Exception as storage_err:
                # Log but don't fail the request if storage fails
                logger.warning(
                    "Failed to persist risk decision: %s",
                    str(storage_err),
                )

        # --- Event Bus Integration ---
        try:
            publisher = EventPublisher()
            orchestrator = RiskOrchestrator(publisher)
            await orchestrator.handle_risk_result(
                shipment_id=request.shipment_id,
                risk_score=risk_score,
                severity=severity,
                reasons=reason_codes,
                source="chainiq-api"
            )
        except Exception as event_err:
            logger.warning(f"Failed to publish risk event: {event_err}")

        logger.info(
            "Risk score completed: shipment=%s, score=%d, severity=%s",
            request.shipment_id,
            risk_score,
            severity,
        )

        return response

    except Exception as e:
        logger.error("Risk scoring failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Risk scoring failed: {str(e)}") from e


@router.get("/risk-history/{shipment_id}", response_model=RiskHistoryResponse)
async def get_risk_history(shipment_id: str) -> RiskHistoryResponse:
    """
    Retrieve risk scoring history for a specific shipment.

    Business Purpose:
    Audit trail of all risk decisions for a shipment.
    Enables compliance reporting and trend analysis.

    Returns:
    - List of all risk scores for this shipment (most recent first)
    - Full request/response data for each score

    Example:
        GET /iq/risk-history/SHP-1001
    """
    if not STORAGE_AVAILABLE or get_score is None:
        raise HTTPException(status_code=503, detail="Storage layer not available")

    try:
        logger.info("Fetching risk history for shipment: %s", shipment_id)

        # Get most recent score to verify shipment exists
        recent_score = get_score(shipment_id)

        if not recent_score:
            raise HTTPException(
                status_code=404,
                detail=f"No risk scores found for shipment {shipment_id}",
            )

        # Build history items (currently only returning most recent)
        history_items = [
            RiskHistoryItem(
                id=recent_score["id"],
                shipment_id=recent_score["shipment_id"],
                scored_at=recent_score["scored_at"],
                risk_score=recent_score["risk_score"],
                severity=recent_score["severity"],
                recommended_action=recent_score["recommended_action"],
                reason_codes=recent_score["reason_codes"],
            )
        ]

        return RiskHistoryResponse(
            shipment_id=shipment_id,
            total_scores=1,
            history=history_items,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch risk history: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch risk history: {str(e)}") from e


@router.get("/risk-recent", response_model=RecentRiskResponse)
async def get_recent_risk(limit: int = 50) -> RecentRiskResponse:
    """
    Retrieve recent risk scores across all shipments.

    Business Purpose:
    Dashboard view of recent risk decisions.
    Enables operators to see patterns and trends.

    Query Parameters:
    - limit: Maximum number of records (default: 50, max: 100)

    Returns:
    - List of recent risk scores (most recent first)

    Example:
        GET /iq/risk-recent?limit=20
    """
    if not STORAGE_AVAILABLE or list_scores is None:
        raise HTTPException(status_code=503, detail="Storage layer not available")

    # Cap limit at 100
    limit = min(limit, 100)

    try:
        logger.info("Fetching %d recent risk scores", limit)

        scores = list_scores(limit=limit)

        score_items = [
            RiskHistoryItem(
                id=score["id"],
                shipment_id=score["shipment_id"],
                scored_at=score["scored_at"],
                risk_score=score["risk_score"],
                severity=score["severity"],
                recommended_action=score["recommended_action"],
                reason_codes=score["reason_codes"],
            )
            for score in scores
        ]

        return RecentRiskResponse(
            total=len(score_items),
            scores=score_items,
        )

    except Exception as e:
        logger.error("Failed to fetch recent risks: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent risks: {str(e)}") from e


@router.post("/risk-replay/{shipment_id}", response_model=ReplayResponse)
async def replay_risk_score(shipment_id: str) -> ReplayResponse:
    """
    Deterministically replay a risk score calculation.

    Business Purpose:
    Verify scoring algorithm changes don't alter past decisions.
    Enables auditing and algorithm validation.

    Process:
    1. Retrieve original request data from storage
    2. Re-run risk calculation with current algorithm
    3. Compare original vs replayed scores

    Returns:
    - Original score and severity
    - Replayed score and severity
    - Match status (true if scores are identical)

    Example:
        POST /iq/risk-replay/SHP-1001
    """
    if not STORAGE_AVAILABLE or replay_request is None or get_score is None:
        raise HTTPException(status_code=503, detail="Storage layer not available")

    try:
        logger.info("Replaying risk score for shipment: %s", shipment_id)

        # Get original score
        original_score = get_score(shipment_id)

        if not original_score:
            raise HTTPException(
                status_code=404,
                detail=f"No original score found for shipment {shipment_id}",
            )

        # Get original request data
        request_data = replay_request(shipment_id)

        if not request_data:
            raise HTTPException(
                status_code=404,
                detail=f"No request data found for shipment {shipment_id}",
            )

        # Re-run risk calculation
        replayed_score, replayed_severity, replayed_reasons, replayed_action = calculate_risk_score(
            route=request_data["route"],
            carrier_id=request_data["carrier_id"],
            shipment_value_usd=request_data["shipment_value_usd"],
            days_in_transit=request_data["days_in_transit"],
            expected_days=request_data["expected_days"],
            documents_complete=request_data["documents_complete"],
            shipper_payment_score=request_data["shipper_payment_score"],
        )

        # Check if scores match
        match = original_score["risk_score"] == replayed_score and original_score["severity"] == replayed_severity

        logger.info(
            "Replay completed: shipment=%s, original=%d, replayed=%d, match=%s",
            shipment_id,
            original_score["risk_score"],
            replayed_score,
            match,
        )

        return ReplayResponse(
            shipment_id=shipment_id,
            original_score=original_score["risk_score"],
            original_severity=original_score["severity"],
            original_scored_at=original_score["scored_at"],
            replayed_score=replayed_score,
            replayed_severity=replayed_severity,
            replayed_reason_codes=replayed_reasons,
            replayed_action=replayed_action,
            match=match,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to replay risk score: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to replay risk score: {str(e)}") from e


@router.get("/pay/queue", response_model=PaymentQueueResponse)
async def get_payment_queue(limit: int = 50) -> PaymentQueueResponse:
    """
    Get payment hold queue (shipments requiring manual review).

    Business Purpose:
    Payment automation decision surface. Shows operators which shipments
    should NOT be auto-released due to:
    - High/Critical risk severity
    - Explicit hold/review/escalate recommendations

    This is READ-ONLY. No payments are executed via this endpoint.

    Query Parameters:
    - limit: Maximum items to return (default: 50, max: 100)

    Returns:
    - List of shipments requiring payment review
    - Total count of pending items

    Decision Criteria:
    Includes shipments where:
    - recommended_action in ['MANUAL_REVIEW', 'HOLD_PAYMENT', 'ESCALATE_COMPLIANCE']
    OR
    - severity in ['HIGH', 'CRITICAL']

    Example:
        GET /pay/queue?limit=20
    """
    if not STORAGE_AVAILABLE or list_scores is None:
        raise HTTPException(
            status_code=503,
            detail="Payment queue unavailable (storage layer not initialized)",
        )

    # Cap limit at 100
    limit = min(limit, 100)

    try:
        logger.info("Fetching payment queue with limit=%d", limit)

        # Get recent scores
        all_scores = list_scores(limit=limit * 2)  # Fetch extra to account for filtering

        # Filter to hold-worthy items
        hold_actions = {"MANUAL_REVIEW", "HOLD_PAYMENT", "ESCALATE_COMPLIANCE"}
        high_severity = {"HIGH", "CRITICAL"}

        queue_items = []
        for score in all_scores:
            # Include if action requires hold OR severity is high
            if score["recommended_action"] in hold_actions or score["severity"] in high_severity:
                # Extract request data for shipment details
                request_data = score.get("request_data", {})

                queue_items.append(
                    PaymentQueueItem(
                        shipment_id=score["shipment_id"],
                        risk_score=score["risk_score"],
                        severity=score["severity"],
                        recommended_action=score["recommended_action"],
                        route=request_data.get("route", "UNKNOWN"),
                        carrier_id=request_data.get("carrier_id", "UNKNOWN"),
                        shipment_value_usd=request_data.get("shipment_value_usd", 0.0),
                        last_scored_at=score["scored_at"],
                    )
                )

        # Apply limit to filtered results
        queue_items = queue_items[:limit]

        logger.info(
            "Payment queue returned %d items (filtered from %d scores)",
            len(queue_items),
            len(all_scores),
        )

        return PaymentQueueResponse(
            items=queue_items,
            total_pending=len(queue_items),
        )

    except Exception as e:
        logger.error("Failed to fetch payment queue: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch payment queue: {str(e)}") from e


@router.get("/history/{entity_id}", response_model=EntityHistoryResponse)
async def get_entity_history(entity_id: str, limit: int = 100) -> EntityHistoryResponse:
    """
    Retrieve complete scoring history for an entity.

    Business Purpose:
    Full audit trail of all risk assessments for an entity (shipment).
    Enables compliance reporting, trend analysis, and decision review.

    Path Parameters:
    - entity_id: Entity identifier (shipment ID)

    Query Parameters:
    - limit: Maximum records to return (default: 100, max: 500)

    Returns:
    - Complete history of risk scores in reverse chronological order
    - Each record includes: timestamp, score, severity, action, payload

    Use Cases:
    - Compliance audit: "Show all risk assessments for SHP-1004"
    - Trend analysis: "How did risk evolve over time?"
    - Decision review: "What context led to HOLD_PAYMENT?"

    Example:
        GET /iq/history/SHP-1004?limit=50

    Status Codes:
    - 200: History retrieved successfully
    - 404: Entity not found (no scoring history)
    - 503: Storage layer unavailable
    """
    if not STORAGE_AVAILABLE or get_history is None:
        raise HTTPException(
            status_code=503,
            detail="History service unavailable (storage layer not initialized)",
        )

    # Cap limit at 500 for performance
    limit = min(limit, 500)

    try:
        logger.info("Fetching history for entity: %s (limit=%d)", entity_id, limit)

        # Get history from storage
        history_records = get_history(entity_id, limit=limit)

        # Check if entity exists
        if not history_records:
            logger.warning("No history found for entity: %s", entity_id)
            raise HTTPException(
                status_code=404,
                detail=f"No scoring history found for entity: {entity_id}",
            )

        # Convert to response models
        history_items = []
        for record in history_records:
            history_items.append(
                EntityHistoryRecord(
                    timestamp=record["timestamp"],
                    score=record["score"],
                    severity=record["severity"],
                    recommended_action=record["recommended_action"],
                    reason_codes=record["reason_codes"],
                    payload=record["payload"],
                )
            )

        logger.info(
            "History retrieved: entity=%s, records=%d",
            entity_id,
            len(history_items),
        )

        return EntityHistoryResponse(
            entity_id=entity_id,
            total_records=len(history_items),
            history=history_items,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch entity history: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch entity history: {str(e)}") from e


@router.get("/options/{shipment_id}", response_model=OptionsAdvisorResponse)
async def get_shipment_options(
    shipment_id: str,
    limit: int = 5,
    risk_appetite: str = "balanced",
):
    """
    Suggest safer route and payment rail options for a given shipment.

    This is read-only and advisory. It never mutates payment/settlement state.

    Sunny: add the Better Options Advisor endpoint using the new schemas and options engine.
    """

    # Check if options engine is available
    if not OPTIONS_AVAILABLE or suggest_options_for_shipment is None:
        logger.error("Options engine not available")
        raise HTTPException(status_code=503, detail="Options advisor service unavailable")

    # Clamp limit to a safe range
    if limit < 1:
        limit = 1
    if limit > 10:
        limit = 10

    # Normalize risk_appetite and default invalid values
    normalized = (risk_appetite or "balanced").lower()
    if normalized not in {"conservative", "balanced", "aggressive"}:
        normalized = "balanced"

    try:
        options_dict = suggest_options_for_shipment(
            shipment_id=shipment_id,
            limit=limit,
            risk_appetite=normalized,
        )
    except ValueError as exc:
        # No history/decision for this shipment
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Storage or engine issue
        logger.error("Options advisor failed for shipment %s: %s", shipment_id, str(exc))
        raise HTTPException(
            status_code=503,
            detail="Options advisor service unavailable",
        ) from exc

    return OptionsAdvisorResponse(
        shipment_id=options_dict["shipment_id"],
        current_risk_score=options_dict["current_risk_score"],
        current_route=options_dict.get("current_route"),
        current_carrier_id=options_dict.get("current_carrier_id"),
        current_payment_rail=options_dict.get("current_payment_rail"),
        risk_appetite=normalized,
        route_options=options_dict.get("route_options", []),
        payment_options=options_dict.get("payment_options", []),
    )


@router.post("/options/{shipment_id}/simulate", response_model=SimulationResultResponse)
async def simulate_option(
    shipment_id: str,
    request: SimulationRequest,
) -> SimulationResultResponse:
    """
    Run a sandbox risk simulation for a given option (route or payment rail).

    This is a non-persisting "what-if" analysis that shows the impact of
    selecting a specific option from the Better Options Advisor.

    Business Purpose:
    - Safe exploration of options before committing
    - Operator confidence in risk mitigation decisions
    - Validation of Better Options Advisor recommendations

    Args:
        shipment_id: Shipment identifier
        request: Simulation request with option_type and option_id

    Returns:
        SimulationResultResponse with baseline vs. simulated risk metrics

    Raises:
        404: Shipment not found or no scoring history
        503: Simulation engine unavailable

    Example Request:
        POST /iq/options/SHP-001/simulate
        {
            "option_type": "route",
            "option_id": "ROUTE-DE-UK-CARRIER-002"
        }

    Example Response:
        {
            "shipment_id": "SHP-001",
            "option_type": "route",
            "option_id": "ROUTE-DE-UK-CARRIER-002",
            "baseline_risk_score": 78,
            "simulated_risk_score": 52,
            "baseline_severity": "HIGH",
            "simulated_severity": "MEDIUM",
            "risk_delta": 26,
            "notes": ["Sandbox simulation only - no data persisted"]
        }

    Note:
        This endpoint does NOT modify any persistent state. It's a pure
        sandbox operation for testing options.
    """
    # Check if simulation engine is available
    if not SIMULATION_AVAILABLE or not simulate_option_for_shipment:
        logger.error("Simulation engine not available")
        raise HTTPException(
            status_code=503,
            detail="Simulation engine not available",
        )

    try:
        return simulate_option_for_shipment(
            shipment_id=shipment_id,
            option_type=request.option_type,
            option_id=request.option_id,
        )
    except ValueError as exc:
        # No data / unknown shipment / bad option
        logger.warning("Simulation failed for %s: %s", shipment_id, str(exc))
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Unexpected error
        logger.exception("Unexpected error during option simulation for %s", shipment_id)
        raise HTTPException(
            status_code=503,
            detail="Simulation service unavailable",
        ) from exc


@router.get("/proofpack/{shipment_id}", response_model=ProofPackResponse)
async def get_proofpack(
    shipment_id: str,
    history_limit: int = 100,
    options_limit: int = 5,
    options_risk_appetite: str = "balanced",
) -> ProofPackResponse:
    """
    Get comprehensive ProofPack for a shipment.

    Bundles all ChainIQ/ChainPay state into a single verifiable package for:
    - Space and Time verifiable analytics integration
    - On-chain settlement attestation
    - Comprehensive audit trail

    This endpoint aggregates:
    - Latest risk snapshot (from ChainIQ scoring)
    - Historical scoring records (for trend analysis)
    - Payment queue entry (if on hold)
    - Better Options Advisor recommendations (if available)

    Args:
        shipment_id: Unique shipment identifier
        history_limit: Max history records (1-500, default 100)
        options_limit: Max options per category (1-10, default 5)
        options_risk_appetite: Risk appetite for options (conservative/balanced/aggressive)

    Returns:
        ProofPack with all available data (fields are optional, graceful degradation)

    Design:
        - Always returns 200 (never 404) - empty ProofPack if shipment not found
        - Each component failure is isolated (e.g., if options fail, still return risk/history)
        - Timestamp in UTC ISO-8601 format for verifiability
        - All data is read-only snapshot at time of request

    Example Response:
        {
            "shipment_id": "SHP-001",
            "version": "proofpack-v1",
            "generated_at": "2025-01-17T10:30:00Z",
            "risk_snapshot": {
                "shipment_id": "SHP-001",
                "risk_score": 45,
                "severity": "MEDIUM",
                "recommended_action": "MANUAL_REVIEW",
                "reason_codes": ["ELEVATED_VALUE"],
                "last_scored_at": "2025-01-17T10:25:00Z"
            },
            "history": {...},
            "payment_queue_entry": {...},
            "options_advisor": {...}
        }
    """
    from datetime import datetime, timezone

    # Validate parameters
    if not (1 <= history_limit <= 500):
        raise HTTPException(status_code=400, detail="history_limit must be 1-500")
    if not (1 <= options_limit <= 10):
        raise HTTPException(status_code=400, detail="options_limit must be 1-10")

    # Check storage availability
    if not STORAGE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="ChainIQ storage not available",
        )

    # Generate timestamp
    generated_at = datetime.now(timezone.utc).isoformat()

    # Component 1: Latest Risk Snapshot
    risk_snapshot = None
    try:
        risk_data = get_latest_risk_for_shipment(shipment_id)
        if risk_data:
            risk_snapshot = RiskSnapshot(
                shipment_id=risk_data["shipment_id"],
                risk_score=risk_data["risk_score"],
                severity=risk_data["severity"],
                recommended_action=risk_data["recommended_action"],
                reason_codes=risk_data["reason_codes"],
                last_scored_at=risk_data["last_scored_at"],
            )
    except Exception as exc:
        logger.warning("ProofPack: Failed to fetch risk snapshot for %s: %s", shipment_id, str(exc))

    # Component 2: Historical Scoring Records
    history = None
    try:
        history_data = get_history(shipment_id, limit=history_limit)
        if history_data:
            history_records = [
                EntityHistoryRecord(
                    timestamp=record["timestamp"],
                    score=record["score"],
                    severity=record["severity"],
                    recommended_action=record["recommended_action"],
                    reason_codes=record.get("reason_codes", []),
                    payload=record["payload"],
                )
                for record in history_data
            ]
            history = EntityHistoryResponse(
                entity_id=shipment_id,
                total_records=len(history_records),
                history=history_records,
            )
    except Exception as exc:
        logger.warning("ProofPack: Failed to fetch history for %s: %s", shipment_id, str(exc))

    # Component 3: Payment Queue Entry
    payment_queue_entry = None
    try:
        queue_data = get_payment_queue_entry_for_shipment(shipment_id)
        if queue_data:
            payment_queue_entry = PaymentQueueItem(
                payment_id=queue_data["payment_id"],
                shipment_id=queue_data["shipment_id"],
                amount=queue_data["amount"],
                currency=queue_data["currency"],
                recipient=queue_data["recipient"],
                status=queue_data["status"],
                hold_reason=queue_data["hold_reason"],
                created_at=queue_data["created_at"],
            )
    except Exception as exc:
        logger.warning("ProofPack: Failed to fetch payment queue for %s: %s", shipment_id, str(exc))

    # Component 4: Better Options Advisor
    options_advisor = None
    if OPTIONS_AVAILABLE and suggest_options_for_shipment:
        try:
            options_dict = suggest_options_for_shipment(
                shipment_id=shipment_id,
                risk_appetite=options_risk_appetite,
                limit=options_limit,
            )
            if options_dict:
                options_advisor = OptionsAdvisorResponse(
                    shipment_id=options_dict["shipment_id"],
                    current_risk_score=options_dict["current_risk_score"],
                    current_route=options_dict.get("current_route"),
                    current_carrier_id=options_dict.get("current_carrier_id"),
                    current_payment_rail=options_dict.get("current_payment_rail"),
                    risk_appetite=options_risk_appetite,
                    route_options=options_dict.get("route_options", []),
                    payment_options=options_dict.get("payment_options", []),
                )
        except Exception as exc:
            logger.warning("ProofPack: Failed to fetch options for %s: %s", shipment_id, str(exc))

    # Return ProofPack (graceful degradation - all components optional)
    return ProofPackResponse(
        shipment_id=shipment_id,
        version="proofpack-v1",
        generated_at=generated_at,
        risk_snapshot=risk_snapshot,
        history=history,
        payment_queue_entry=payment_queue_entry,
        options_advisor=options_advisor,
    )


@router.get("/shipments/at_risk", response_model=AtRiskShipmentsResponse)
async def get_at_risk_shipments(min_risk_score: int = 70, max_results: int = 50) -> AtRiskShipmentsResponse:
    """
    Retrieve list of at-risk shipments for fleet monitoring.

    Business Purpose:
    Enables fleet-level risk visibility in the Control Tower.
    Operators can quickly identify shipments requiring immediate attention.

    Query Parameters:
    - min_risk_score: Minimum risk score threshold (default: 70)
    - max_results: Maximum number of results to return (default: 50)

    Business Context:
    "Show me all shipments with concerning risk levels so I can prioritize interventions."

    Example:
        GET /iq/shipments/at_risk?min_risk_score=75&max_results=25
    """

    logger.info(
        "Fetching at-risk shipments with min_risk_score=%d, max_results=%d",
        min_risk_score,
        max_results,
    )

    # For demo/development: Return synthetic at-risk shipments
    # TODO: Replace with actual database queries when storage layer is enhanced

    from datetime import datetime, timezone

    demo_shipments = [
        AtRiskShipmentSummary(
            shipment_id="SHIP-1001",
            route="CN-US-LAX",
            carrier_id="CARRIER-COSCO",
            corridor_code="TRANSPACIFIC",
            risk_score=85,
            risk_level="HIGH",
            days_in_transit=18,
            shipment_value_usd=125000.00,
            completeness_pct=65,
            blocking_gap_count=3,
            last_updated=datetime.now(timezone.utc).isoformat(),
        ),
        AtRiskShipmentSummary(
            shipment_id="SHIP-1002",
            route="DE-US-NYC",
            carrier_id="CARRIER-HAPAG",
            corridor_code="TRANSATLANTIC",
            risk_score=92,
            risk_level="CRITICAL",
            days_in_transit=22,
            shipment_value_usd=89000.00,
            completeness_pct=45,
            blocking_gap_count=5,
            last_updated=datetime.now(timezone.utc).isoformat(),
        ),
        AtRiskShipmentSummary(
            shipment_id="SHIP-1003",
            route="IN-US-CHI",
            carrier_id="CARRIER-MSC",
            corridor_code="TRANSPACIFIC",
            risk_score=78,
            risk_level="HIGH",
            days_in_transit=15,
            shipment_value_usd=67000.00,
            completeness_pct=72,
            blocking_gap_count=2,
            last_updated=datetime.now(timezone.utc).isoformat(),
        ),
        AtRiskShipmentSummary(
            shipment_id="SHIP-1004",
            route="BR-US-MIA",
            carrier_id="CARRIER-MAERSK",
            corridor_code="AMERICAS",
            risk_score=88,
            risk_level="HIGH",
            days_in_transit=20,
            shipment_value_usd=156000.00,
            completeness_pct=58,
            blocking_gap_count=4,
            last_updated=datetime.now(timezone.utc).isoformat(),
        ),
        AtRiskShipmentSummary(
            shipment_id="SHIP-123",  # Demo shipment used in UI
            route="CN-US-LAX",
            carrier_id="CARRIER-EVERGREEN",
            corridor_code="TRANSPACIFIC",
            risk_score=95,
            risk_level="CRITICAL",
            days_in_transit=25,
            shipment_value_usd=98000.00,
            completeness_pct=42,
            blocking_gap_count=6,
            last_updated=datetime.now(timezone.utc).isoformat(),
        ),
    ]

    # Filter by risk score threshold
    filtered_shipments = [shipment for shipment in demo_shipments if shipment.risk_score >= min_risk_score]

    # Sort by risk score descending (highest risk first)
    filtered_shipments.sort(key=lambda x: x.risk_score, reverse=True)

    # Apply result limit
    limited_shipments = filtered_shipments[:max_results]

    logger.info(
        "Returning %d at-risk shipments (filtered from %d total)",
        len(limited_shipments),
        len(filtered_shipments),
    )

    return AtRiskShipmentsResponse(
        shipments=limited_shipments,
        total_count=len(filtered_shipments),
        min_risk_score=min_risk_score,
        max_results=max_results,
    )
