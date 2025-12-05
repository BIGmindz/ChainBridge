
"""
ChainPay Service (ChainBridge)

Goal:
- Provide a payment settlement API for tokenized freight.
- Consume FreightTokens from ChainFreight service.
- Use risk_score to implement conditional settlement logic.
- Support immediate, delayed, and manual-review payment flows.
- Track all settlement decisions with audit logs.

Milestone-Based Payments:
- Extend PaymentIntent with risk-based, milestone payment schedules.
- When ChainFreight sends shipment events, use the schedule to create partial payments
    (MilestoneSettlements) based on percentages like 20/70/10 that depend on risk_score.
- Each milestone is tracked separately and prevents double-payment via unique constraints.

Integration:
- Fetches freight token details (status, risk_score, risk_category) from ChainFreight
- Uses risk metrics to determine settlement tier and delay
- Implements business rules: LOW=immediate, MEDIUM=24h delay, HIGH=manual review
"""

from __future__ import annotations
from core.import_safety import ensure_import_safety
ensure_import_safety()

import logging
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session


# Identity module not yet part of ChainBridge — removed legacy import
# TODO: integrate identity service once ChainBridge identity module is ready

from .chainfreight_client import (
    fetch_freight_token,
    map_risk_to_tier,
)
from .database import get_db, init_db
from .models import MilestoneSettlement as MilestoneSettlementModel
from .models import PaymentIntent as PaymentIntentModel
from .models import PaymentSchedule as PaymentScheduleModel
from .models import PaymentScheduleItem as PaymentScheduleItemModel
from .models import (
    PaymentStatus,
    RiskTier,
    ScheduleType,
    SettlementLog,
)
from .schemas import (
    PaymentIntentCreate,
    PaymentIntentListResponse,
    PaymentIntentResponse,
    RiskAssessmentResponse,
    SettlementRequest,
    SettlementResponse,
    ShipmentEventWebhookRequest,
    ShipmentEventWebhookResponse,
)
from .schedule_builder import RiskTierSchedule, build_default_schedule, calculate_milestone_amount
from .payment_rails import (
    ReleaseStrategy,
    canonical_milestone_id,
    canonical_shipment_reference,
)
from .services.payment_rails_engine import PaymentRailsEngine
from .schemas_context_ledger_feed import ContextLedgerRiskFeed
from .schemas_settlement import (
    SettleOnchainRequest,
    SettleOnchainResponse,
    SettlementAckRequest,
    SettlementAckResponse,
    SettlementDetailResponse,
)
from app.schemas import SettlementHistoryResponse
# Setup logging


logger = logging.getLogger(__name__)

app = FastAPI()

from app.api_settlement import router as settlement_router
from app import api_analytics

from .services.context_ledger_feed import serialize_feed
from .services.context_ledger_service import ContextLedgerService
from .services.event_publisher import EventPublisher
from .services.settlement_orchestrator import SettlementOrchestrator
from .services.event_consumer import EventConsumer
from .services.settlement_api import (
    SettlementAPIService,
    SettlementConflictError,
    SettlementNotFoundError,
)
from .services.xrpl_stub_adapter import XRPLSettlementAdapter
event_publisher = EventPublisher()
settlement_orchestrator = SettlementOrchestrator(event_publisher)
event_consumer = EventConsumer(settlement_orchestrator)
xrpl_adapter = XRPLSettlementAdapter()

app.include_router(settlement_router)
app.include_router(api_analytics.router)

@app.on_event("startup")
async def start_event_consumer():
    await event_consumer.start()
    logger.info("ChainPay event consumer started on startup")


# --- HELPER FUNCTIONS ---


def build_default_schedule_for_risk(
    db: Session,
    payment_intent: PaymentIntentModel,
) -> PaymentScheduleModel:
    """
    Build and attach a default payment schedule based on payment intent's risk score.

    Creates a PaymentSchedule with milestone items according to risk level:
    - LOW risk (< 0.3):    20% at PICKUP_CONFIRMED, 70% at POD_CONFIRMED, 10% at CLAIM_WINDOW_CLOSED
    - MEDIUM risk (< 0.6): 10% at PICKUP_CONFIRMED, 70% at POD_CONFIRMED, 20% at CLAIM_WINDOW_CLOSED
    - HIGH risk (>= 0.6):  0% at PICKUP_CONFIRMED, 80% at POD_CONFIRMED, 20% at CLAIM_WINDOW_CLOSED

    Args:
        db: Database session
        payment_intent: The payment intent to attach the schedule to

    Returns:
        Created PaymentSchedule with all items
    """
    risk_score = payment_intent.risk_score or 0.5  # Default to MEDIUM if not set

    # Determine schedule based on risk score
    if risk_score < 0.3:
        risk_tier = RiskTier.LOW
        schedule_items = [
            {"event_type": "PICKUP_CONFIRMED", "percentage": 0.20, "sequence": 1},
            {"event_type": "POD_CONFIRMED", "percentage": 0.70, "sequence": 2},
            {"event_type": "CLAIM_WINDOW_CLOSED", "percentage": 0.10, "sequence": 3},
        ]
        description = "Low-risk: Release upon milestone events with majority at POD"
    elif risk_score < 0.6:
        risk_tier = RiskTier.MEDIUM
        schedule_items = [
            {"event_type": "PICKUP_CONFIRMED", "percentage": 0.10, "sequence": 1},
            {"event_type": "POD_CONFIRMED", "percentage": 0.70, "sequence": 2},
            {"event_type": "CLAIM_WINDOW_CLOSED", "percentage": 0.20, "sequence": 3},
        ]
        description = "Medium-risk: Hold more until POD with final release at claims closure"
    else:
        risk_tier = RiskTier.HIGH
        schedule_items = [
            {"event_type": "PICKUP_CONFIRMED", "percentage": 0.0, "sequence": 1},
            {"event_type": "POD_CONFIRMED", "percentage": 0.80, "sequence": 2},
            {"event_type": "CLAIM_WINDOW_CLOSED", "percentage": 0.20, "sequence": 3},
        ]
        description = "High-risk: Hold until POD, then staged release"

    # Create PaymentSchedule
    schedule = PaymentScheduleModel(
        payment_intent_id=payment_intent.id,
        schedule_type=ScheduleType.MILESTONE,
        description=description,
        risk_tier=risk_tier,
    )
    db.add(schedule)
    db.flush()  # Flush to get the schedule ID

    # Create PaymentScheduleItems
    for item_data in schedule_items:
        item = PaymentScheduleItemModel(
            schedule_id=schedule.id,
            event_type=item_data["event_type"],
            percentage=item_data["percentage"],
            sequence=item_data["sequence"],
        )
        db.add(item)

    db.commit()
    db.refresh(schedule)

    logger.info(
        f"Built payment schedule {schedule.id} for payment intent {payment_intent.id}: "
        f"risk_tier={risk_tier}, items={len(schedule_items)}"
    )

    return schedule


def process_milestone_for_intent(
    db: Session,
    payment_intent: PaymentIntentModel,
    event_payload: ShipmentEventWebhookRequest,
) -> tuple[MilestoneSettlementModel | None, str]:
    """
    Process a shipment event to create a milestone settlement for a payment intent.

    This is the core Smart Settlements (v2) function that:
    1. Finds the PaymentSchedule for the intent
    2. Looks up the PaymentScheduleItem for the event_type
    3. Checks if a MilestoneSettlement already exists (idempotency)
    4. Creates a MilestoneSettlement with calculated amount
    5. Determines if payment should be released immediately or delayed
    6. If release conditions met, routes through PaymentRail for settlement
    7. Otherwise, marks as PENDING and logs for later processing

    Args:
        db: Database session
        payment_intent: The payment intent to process
        event_payload: The shipment event webhook payload

    Returns:
        Tuple of (MilestoneSettlement if created or None, status message)
    """
    from app.payment_rails import should_release_now as _should_release_now  # local import guards circulars in tests

    rails_engine = PaymentRailsEngine(db)

    # Find PaymentSchedule
    schedule = db.query(PaymentScheduleModel).filter(PaymentScheduleModel.payment_intent_id == payment_intent.id).first()

    if not schedule:
        logger.warning(
            "No payment schedule for payment intent %s",
            payment_intent.id,
        )
        return None, f"No payment schedule for payment intent {payment_intent.id}"

    # Find PaymentScheduleItem for this event_type
    schedule_item = (
        db.query(PaymentScheduleItemModel)
        .filter(
            PaymentScheduleItemModel.schedule_id == schedule.id,
            PaymentScheduleItemModel.event_type == event_payload.event_type,
        )
        .first()
    )

    if not schedule_item:
        logger.warning(
            "No schedule item for event_type=%s in schedule %s",
            event_payload.event_type,
            schedule.id,
        )
        return None, f"Event type {event_payload.event_type} not in payment schedule"

    # Check if milestone already settled (idempotency via unique constraint)
    existing_milestone = (
        db.query(MilestoneSettlementModel)
        .filter(
            MilestoneSettlementModel.payment_intent_id == payment_intent.id,
            MilestoneSettlementModel.event_type == event_payload.event_type,
        )
        .first()
    )

    if existing_milestone:
        logger.info(
            "Milestone already exists for payment_intent=%s, event_type=%s (idempotent)",
            payment_intent.id,
            event_payload.event_type,
        )
        return existing_milestone, "Milestone already created (idempotent)"

    # Calculate settlement amount
    milestone_amount = calculate_milestone_amount(
        total_amount=payment_intent.amount,
        milestone_percentage=schedule_item.percentage,
    )

    # Determine release strategy using Smart Settlements logic
    risk_score = payment_intent.risk_score or 0.5
    release_strategy = _should_release_now(risk_score, event_payload.event_type)

    # Create MilestoneSettlement with status based on release strategy
    if release_strategy == ReleaseStrategy.IMMEDIATE:
        initial_status = PaymentStatus.APPROVED
        log_note = "Smart Settlement: releasing immediately"
    elif release_strategy == ReleaseStrategy.DELAYED:
        initial_status = PaymentStatus.DELAYED
        log_note = "Smart Settlement: delayed release (24h)"
    elif release_strategy == ReleaseStrategy.MANUAL_REVIEW:
        initial_status = PaymentStatus.PENDING
        log_note = "Smart Settlement: pending manual review (HIGH risk)"
    else:  # PENDING
        initial_status = PaymentStatus.PENDING
        log_note = "Smart Settlement: pending (event not yet eligible for release)"

    shipment_reference = canonical_shipment_reference(
        shipment_reference=getattr(payment_intent, "shipment_reference", None),
        freight_token_id=payment_intent.freight_token_id,
    )
    milestone_index = schedule_item.sequence or 1
    canonical_identifier = canonical_milestone_id(shipment_reference, milestone_index)

    provider_code = rails_engine.default_provider().value

    milestone = MilestoneSettlementModel(
        payment_intent_id=payment_intent.id,
        schedule_item_id=schedule_item.id,
        event_type=event_payload.event_type,
        amount=milestone_amount,
        currency=payment_intent.currency,
        status=initial_status,
        occurred_at=event_payload.occurred_at,
        provider=provider_code,
        milestone_identifier=canonical_identifier,
        shipment_reference=shipment_reference,
        freight_token_id=payment_intent.freight_token_id,
    )

    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    logger.info(
        "Created milestone settlement %s: payment_intent=%s, event_type=%s, amount=%s %s, status=%s, strategy=%s",
        milestone.id,
        payment_intent.id,
        event_payload.event_type,
        milestone_amount,
        payment_intent.currency,
        initial_status,
        release_strategy,
    )

    # If immediate release, route through payment rail
    if release_strategy == ReleaseStrategy.IMMEDIATE:
        try:
            rail = rails_engine.get_immediate_rail()
            result = rail.process_settlement(
                milestone_id=milestone.id,
                amount=milestone_amount,
                currency=payment_intent.currency,
                recipient_id=None,  # TODO: Get from freight token or payment intent
            )

            if result.success:
                logger.info(
                    "Payment rail processing succeeded: milestone=%s, reference=%s",
                    milestone.id,
                    result.reference_id,
                )
                return milestone, f"Milestone created and released: {result.message}"
            else:
                logger.error(
                    "Payment rail processing failed: milestone=%s, error=%s",
                    milestone.id,
                    result.error,
                )
                return (
                    milestone,
                    f"Milestone created but rail processing failed: {result.error}",
                )

        except Exception as e:
            logger.error(
                "Error routing to payment rail: milestone=%s, error=%s",
                milestone.id,
                str(e),
            )
            return milestone, f"Milestone created but rail processing errored: {str(e)}"

    else:
        # Log as pending settlement for later processing
        return milestone, f"Milestone created: {log_note}"


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    logger.info("ChainPay database initialized")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "chainpay", "version": "1.0.0"}


@app.get(
    "/context-ledger/risk",
    response_model=ContextLedgerRiskFeed,
    tags=["context-ledger"],
)
def get_context_ledger_risk_feed(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ContextLedgerRiskFeed:
    """Return the most recent context-ledger events and their risk snapshots."""

    service = ContextLedgerService(db)
    entries = service.get_recent_context_ledger_events_with_risk(limit=limit)
    return serialize_feed(entries)


def _build_settlement_service(db: Session) -> SettlementAPIService:
    return SettlementAPIService(db, xrpl_adapter=xrpl_adapter)


@app.post(
    "/chainpay/settle-onchain",
    response_model=SettleOnchainResponse,
    tags=["chainpay"],
)
def submit_onchain_settlement(
    payload: SettleOnchainRequest,
    db: Session = Depends(get_db),
) -> SettleOnchainResponse:
    service = _build_settlement_service(db)
    try:
        return service.trigger_onchain_settlement(payload)
    except SettlementNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(exc)})
    except SettlementConflictError as exc:
        raise HTTPException(status_code=409, detail={"error": "VALIDATION_ERROR", "message": str(exc)})


@app.get(
    "/chainpay/settlements/{settlement_id}",
    response_model=SettlementDetailResponse,
    tags=["chainpay"],
)
def get_settlement_status(
    settlement_id: str,
    db: Session = Depends(get_db),
) -> SettlementDetailResponse:
    service = _build_settlement_service(db)
    try:
        return service.get_settlement_detail(settlement_id)
    except SettlementNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(exc)})


@app.post(
    "/chainpay/settlements/{settlement_id}/ack",
    response_model=SettlementAckResponse,
    tags=["chainpay"],
)
def acknowledge_settlement(
    settlement_id: str,
    payload: SettlementAckRequest,
    db: Session = Depends(get_db),
) -> SettlementAckResponse:
    service = _build_settlement_service(db)
    try:
        return service.record_acknowledgement(settlement_id, payload)
    except SettlementNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(exc)})


# --- PAYMENT INTENT ENDPOINTS ---


@app.post("/payment_intents", response_model=PaymentIntentResponse, status_code=201)
async def create_payment_intent(
    payload: PaymentIntentCreate,
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    """
    Create a new payment intent tied to a freight token.

    This endpoint:
    1. Validates the freight token exists in ChainFreight
    2. Fetches token details including risk metrics
    3. Determines settlement tier based on risk
    4. Creates payment intent with conditional settlement timing

    Args:
        payload: Payment intent creation parameters
        db: Database session

    Returns:
        Created payment intent with risk tier and settlement schedule

    Raises:
        HTTPException: If freight token not found or unavailable
    """
    # Fetch freight token from ChainFreight service
    token = await fetch_freight_token(payload.freight_token_id)
    if token is None:
        raise HTTPException(
            status_code=404,
            detail=f"Freight token {payload.freight_token_id} not found or unreachable",
        )

    # Validate token is in appropriate status for payment
    if token.status not in ["active", "locked"]:
        raise HTTPException(
            status_code=400,
            detail=f"Token status '{token.status}' not eligible for settlement",
        )

    # Determine risk tier
    risk_tier_str = map_risk_to_tier(token.risk_category)
    risk_tier = RiskTier(risk_tier_str)

    # Create payment intent
    payment_intent = PaymentIntentModel(
        freight_token_id=payload.freight_token_id,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        risk_score=token.risk_score,
        risk_category=token.risk_category,
        risk_tier=risk_tier,
        status=PaymentStatus.PENDING,
    )

    db.add(payment_intent)
    db.commit()
    db.refresh(payment_intent)

    # Build default payment schedule based on risk score
    try:
        build_default_schedule_for_risk(db, payment_intent)
    except Exception as e:
        logger.error(
            "Failed to build payment schedule for intent %s: %s",
            payment_intent.id,
            e,
        )
        # Continue without schedule - not a fatal error

    logger.info(
        "Payment intent %s created for token %s: amount=%s, risk_tier=%s",
        payment_intent.id,
        payload.freight_token_id,
        payload.amount,
        risk_tier,
    )

    return payment_intent


@app.get("/payment_intents", response_model=PaymentIntentListResponse)
async def list_payment_intents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: str = Query(None),
    risk_tier: str = Query(None),
    db: Session = Depends(get_db),
) -> PaymentIntentListResponse:
    """
    List payment intents with optional filtering.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        status: Filter by payment status (optional)
        risk_tier: Filter by risk tier (optional)
        db: Database session

    Returns:
        List of payment intents with total count
    """
    query = db.query(PaymentIntentModel)

    if status:
        query = query.filter(PaymentIntentModel.status == PaymentStatus(status))

    if risk_tier:
        query = query.filter(PaymentIntentModel.risk_tier == RiskTier(risk_tier))

    total = query.count()
    payment_intents = query.offset(skip).limit(limit).all()

    return PaymentIntentListResponse(total=total, payment_intents=payment_intents)


@app.get("/payment_intents/{payment_id}", response_model=PaymentIntentResponse)
async def get_payment_intent(
    payment_id: int,
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    """
    Retrieve a specific payment intent by ID.

    Args:
        payment_id: ID of the payment intent
        db: Database session

    Returns:
        Payment intent details

    Raises:
        HTTPException: If payment intent not found
    """
    payment_intent = db.query(PaymentIntentModel).filter(PaymentIntentModel.id == payment_id).first()

    if not payment_intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    return payment_intent


# --- SETTLEMENT ENDPOINTS ---


@app.post("/payment_intents/{payment_id}/assess_risk", response_model=RiskAssessmentResponse)
async def assess_risk(
    payment_id: int,
    db: Session = Depends(get_db),
) -> RiskAssessmentResponse:
    """
    Assess risk and settlement timing for a payment intent.

    This endpoint provides risk assessment and recommended settlement action
    without actually settling the payment.

    Args:
        payment_id: ID of the payment intent
        db: Database session

    Returns:
        Risk assessment with recommended action

    Raises:
        HTTPException: If payment intent not found
    """
    payment_intent = db.query(PaymentIntentModel).filter(PaymentIntentModel.id == payment_id).first()

    if not payment_intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    # Calculate settlement delay
    delay = payment_intent.get_settlement_delay()

    if delay.total_seconds() == 0:
        delay_str = "immediate"
    elif delay.days == 0:
        delay_str = f"{delay.seconds // 3600} hours"
    else:
        delay_str = f"{delay.days} days"

    # Generate recommendation
    if payment_intent.risk_tier == RiskTier.LOW:
        recommendation = "APPROVE_IMMEDIATELY - Low risk token"
    elif payment_intent.risk_tier == RiskTier.MEDIUM:
        recommendation = "APPROVE_WITH_DELAY - Monitor during 24h window"
    else:
        recommendation = "REQUIRES_MANUAL_REVIEW - High risk, needs approval"

    return RiskAssessmentResponse(
        payment_intent_id=payment_intent.id,
        freight_token_id=payment_intent.freight_token_id,
        risk_score=payment_intent.risk_score,
        risk_category=payment_intent.risk_category,
        risk_tier=payment_intent.risk_tier.value,
        settlement_delay=delay_str,
        recommended_action=recommendation,
        created_at=payment_intent.created_at,
    )


@app.post("/payment_intents/{payment_id}/settle", response_model=SettlementResponse)
async def settle_payment(
    payment_id: int,
    payload: SettlementRequest,
    db: Session = Depends(get_db),
) -> SettlementResponse:
    """
    Settle a payment intent with risk-based conditional logic.

    Settlement logic:
    - LOW risk (0.0-0.33): Approve immediately
    - MEDIUM risk (0.33-0.67): Delay 24 hours, then approve
    - HIGH risk (0.67-1.0): Reject until manual approval (force_approval=True)

    Args:
        payment_id: ID of the payment intent
        payload: Settlement request with optional notes and force approval flag
        db: Database session

    Returns:
        Settlement result with action taken and timing

    Raises:
        HTTPException: If payment intent not found or invalid state
    """
    payment_intent = db.query(PaymentIntentModel).filter(PaymentIntentModel.id == payment_id).first()

    if not payment_intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    # Check if already settled
    if payment_intent.status in [
        PaymentStatus.SETTLED,
        PaymentStatus.REJECTED,
        PaymentStatus.CANCELLED,
    ]:
        raise HTTPException(status_code=400, detail=f"Payment already {payment_intent.status.value}")

    # Implement risk-based settlement logic
    action_taken = ""
    settlement_reason = ""

    if payment_intent.risk_tier == RiskTier.LOW:
        # LOW RISK: Approve immediately
        payment_intent.status = PaymentStatus.APPROVED
        payment_intent.settlement_approved_at = datetime.utcnow()
        action_taken = "approved"
        settlement_reason = "Low risk token - immediate approval"

    elif payment_intent.risk_tier == RiskTier.MEDIUM:
        # MEDIUM RISK: Delay and approve
        delay = timedelta(hours=24)
        settlement_delayed_until = datetime.utcnow() + delay

        if payment_intent.is_ready_to_settle():
            # Delay has passed - approve now
            payment_intent.status = PaymentStatus.APPROVED
            payment_intent.settlement_approved_at = datetime.utcnow()
            action_taken = "approved"
            settlement_reason = "Medium risk - 24h delay period completed"
        else:
            # Still in delay window
            payment_intent.status = PaymentStatus.DELAYED
            payment_intent.settlement_delayed_until = settlement_delayed_until
            action_taken = "delayed"
            settlement_reason = f"Medium risk - settlement delayed until {settlement_delayed_until.isoformat()}"

    else:  # HIGH RISK
        # HIGH RISK: Require manual approval
        if payload.force_approval:
            payment_intent.status = PaymentStatus.APPROVED
            payment_intent.settlement_approved_at = datetime.utcnow()
            action_taken = "approved"
            settlement_reason = "High risk - manual override approved"
            logger.warning(
                "High-risk payment %s force-approved for token %s",
                payment_id,
                payment_intent.freight_token_id,
            )
        else:
            payment_intent.status = PaymentStatus.REJECTED
            action_taken = "rejected"
            settlement_reason = "High risk token - requires manual review and force_approval flag"

    # Add settlement notes
    if payload.settlement_notes:
        payment_intent.settlement_notes = payload.settlement_notes

    payment_intent.settlement_reason = settlement_reason

    # Log settlement action
    log_entry = SettlementLog(
        payment_intent_id=payment_intent.id,
        action=action_taken,
        reason=settlement_reason,
        triggered_by="system",
    )
    db.add(log_entry)
    db.commit()
    db.refresh(payment_intent)

    logger.info(
        "Payment %s settlement action: %s (risk_tier=%s, reason=%s)",
        payment_id,
        action_taken,
        payment_intent.risk_tier,
        settlement_reason,
    )

    return SettlementResponse(
        payment_intent_id=payment_intent.id,
        status=payment_intent.status.value,
        action_taken=action_taken,
        settlement_approved_at=payment_intent.settlement_approved_at,
        settlement_delayed_until=payment_intent.settlement_delayed_until,
        settlement_reason=settlement_reason,
    )


@app.post("/payment_intents/{payment_id}/complete", response_model=PaymentIntentResponse)
async def complete_settlement(
    payment_id: int,
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    """
    Mark a payment intent as fully settled/completed.

    This endpoint transitions payment from APPROVED to SETTLED status,
    typically after funds have been transferred.

    Args:
        payment_id: ID of the payment intent
        db: Database session

    Returns:
        Updated payment intent

    Raises:
        HTTPException: If payment not in appropriate status
    """
    payment_intent = db.query(PaymentIntentModel).filter(PaymentIntentModel.id == payment_id).first()

    if not payment_intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    if payment_intent.status != PaymentStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail=f"Payment must be in APPROVED status, currently {payment_intent.status.value}",
        )

    payment_intent.status = PaymentStatus.SETTLED
    payment_intent.settlement_completed_at = datetime.utcnow()

    # Log completion
    log_entry = SettlementLog(
        payment_intent_id=payment_intent.id,
        action="settled",
        reason="Payment settlement completed and funds transferred",
        triggered_by="system",
    )
    db.add(log_entry)
    db.commit()
    db.refresh(payment_intent)

    logger.info("Payment %s marked as settled", payment_id)

    return payment_intent


# --- SETTLEMENT HISTORY ENDPOINTS ---


@app.get("/payment_intents/{payment_id}/history", response_model=SettlementHistoryResponse)
async def get_settlement_history(
    payment_id: int,
    db: Session = Depends(get_db),
) -> SettlementHistoryResponse:
    """
    Retrieve settlement history/audit log for a payment intent.

    Args:
        payment_id: ID of the payment intent
        db: Database session

    Returns:
        Settlement history with all actions and approvals

    Raises:
        HTTPException: If payment intent not found
    """
    payment_intent = db.query(PaymentIntentModel).filter(PaymentIntentModel.id == payment_id).first()

    if not payment_intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    logs = db.query(SettlementLog).filter(SettlementLog.payment_intent_id == payment_id).order_by(SettlementLog.created_at).all()

    return SettlementHistoryResponse(
        payment_intent_id=payment_intent.id,
        logs=logs,
        total_actions=len(logs),
    )


# --- WEBHOOK ENDPOINTS ---


@app.post(
    "/webhooks/shipment_event",
    response_model=ShipmentEventWebhookResponse,
    status_code=200,
)
async def process_shipment_event(
    event: ShipmentEventWebhookRequest,
    db: Session = Depends(get_db),
) -> ShipmentEventWebhookResponse:
    """
    Webhook endpoint to receive shipment events from ChainFreight.

    When a shipment milestone occurs (e.g., POD_CONFIRMED), this endpoint:
    1. Finds all payment intents linked to the shipment via freight tokens
    2. For each payment intent, checks if it has a PaymentSchedule
    3. Looks up the scheduled % for this event_type
    4. Creates a MilestoneSettlement record (idempotent on event_type)
    5. Prevents double-payment via unique constraint

    Args:
        event: Shipment event details (shipment_id, event_type, occurred_at)
        db: Database session

    Returns:
        Webhook response with count of milestone settlements created
    """
    logger.info(
        "Received shipment event webhook: shipment_id=%s, event_type=%s, occurred_at=%s",
        event.shipment_id,
        event.event_type,
        event.occurred_at,
    )

    # Find all payment intents for this shipment
    # TODO: When ChainFreight integration is complete, query by shipment_id
    # For now, we process ALL payment intents that have a matching schedule item
    payment_intents = db.query(PaymentIntentModel).all()

    milestone_count = 0

    for payment_intent in payment_intents:
        try:
            milestone, status_msg = process_milestone_for_intent(db, payment_intent, event)
            if milestone:
                milestone_count += 1
        except Exception as e:
            logger.error(
                "Error processing milestone for payment_intent %s: %s",
                payment_intent.id,
                e,
            )
            db.rollback()
            continue

    return ShipmentEventWebhookResponse(
        shipment_id=event.shipment_id,
        event_type=event.event_type,
        processed_at=datetime.utcnow(),
        milestone_settlements_created=milestone_count,
        message=f"Processed shipment event: {milestone_count} milestone settlement(s) created/updated",
    )


@app.post(
    "/webhooks/shipment-events",
    response_model=ShipmentEventWebhookResponse,
    status_code=200,
)
async def process_shipment_event_compat(
    event: ShipmentEventWebhookRequest,
    db: Session = Depends(get_db),
) -> ShipmentEventWebhookResponse:
    """Compatibility alias for legacy test path `/webhooks/shipment-events`."""
    return await process_shipment_event(event, db)


@app.post("/payment_intents/{payment_id}/build_schedule")
async def build_and_attach_schedule(
    payment_id: int,
    db: Session = Depends(get_db),
):
    """
    Build and attach a default payment schedule to an existing payment intent.

    This is typically called right after creating a payment intent,
    or can be called separately if schedule creation was deferred.

    The schedule is built based on the payment intent's risk_tier.

    Args:
        payment_id: ID of the payment intent
        db: Database session

    Returns:
        Payment intent with attached schedule

    Raises:
        HTTPException: If payment intent not found or schedule already exists
    """
    payment_intent = db.query(PaymentIntentModel).filter(PaymentIntentModel.id == payment_id).first()

    if not payment_intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    # Check if schedule already exists
    existing_schedule = db.query(PaymentScheduleModel).filter(PaymentScheduleModel.payment_intent_id == payment_id).first()

    if existing_schedule:
        raise HTTPException(
            status_code=400,
            detail="Payment schedule already exists for this payment intent",
        )

    # Build default schedule based on risk tier
    schedule_risk_tier = RiskTierSchedule(payment_intent.risk_tier.value)
    schedule_items = build_default_schedule(risk_tier=schedule_risk_tier)

    # Create PaymentSchedule
    schedule = PaymentScheduleModel(
        payment_intent_id=payment_intent.id,
        risk_tier=payment_intent.risk_tier,
    )
    db.add(schedule)
    db.flush()  # Flush to get the schedule ID

    # Create PaymentScheduleItems
    for item_data in schedule_items:
        item = PaymentScheduleItemModel(
            schedule_id=schedule.id,
            event_type=item_data["event_type"],
            percentage=item_data["percentage"],
            order=item_data["order"],
        )
        db.add(item)

    db.commit()
    db.refresh(schedule)

    logger.info(
        "Built and attached payment schedule: id=%s, payment_intent=%s, risk_tier=%s",
        schedule.id,
        payment_id,
        payment_intent.risk_tier,
    )

    return {
        "payment_id": payment_intent.id,
        "schedule_id": schedule.id,
        "risk_tier": payment_intent.risk_tier.value,
        "items_count": len(schedule_items),
        "message": "Payment schedule created successfully",
    }


# --- AUDIT ENDPOINTS ---


@app.get("/audit/shipments/{shipment_id}")
async def get_shipment_audit(
    shipment_id: str,
    db: Session = Depends(get_db),
):
    """
    Get audit trail for a shipment showing all milestone settlements and their status.

    This endpoint provides comprehensive settlement information for a shipment including:
    - All payment intents linked to the shipment (via freight tokens)
    - Each milestone settlement with status, amount, and processing details
    - Release strategy applied to each milestone
    - Payment rail provider and reference IDs

    Args:
        shipment_id: Shipment identifier from ChainFreight
        db: Database session

    Returns:
        Audit response with settlement details

    Note:
        Current implementation: processes all payment intents with schedules.
        TODO: Filter by shipment_id when ChainFreight API fully integrated.
    """
    # Query all payment intents (TODO: filter by shipment_id when fully integrated)
    # For now, we return milestones for all intents that have associated events
    # Find payment intent for this shipment
    payment_intent = db.query(PaymentIntentModel).filter(PaymentIntentModel.freight_token_id == shipment_id).first()
    if not payment_intent:
        raise HTTPException(status_code=404, detail="Shipment not found")
    milestones = db.query(MilestoneSettlementModel).filter(MilestoneSettlementModel.payment_intent_id == payment_intent.id).order_by(MilestoneSettlementModel.created_at).all()

    # Build audit response with settlement details
    milestones_detail = [
        {
            "id": milestone.id,
            "event_type": milestone.event_type,
            "amount": milestone.amount,
            "currency": milestone.currency,
            "status": milestone.status.value,
            "provider": milestone.provider,
            "reference": milestone.reference,
            "occurred_at": (milestone.occurred_at.isoformat() if milestone.occurred_at else None),
            "settled_at": (milestone.settled_at.isoformat() if milestone.settled_at else None),
            "created_at": (milestone.created_at.isoformat() if milestone.created_at else None),
        }
        for milestone in milestones
    ]
    summary = {
        "total_milestones": len(milestones),
        # Maintain both deprecated and current keys for backward compatibility
        "total_approved": sum(m.amount for m in milestones if m.status == PaymentStatus.APPROVED),
        "total_settled": sum(m.amount for m in milestones if m.status == PaymentStatus.SETTLED),
        "total_approved_amount": sum(m.amount for m in milestones if m.status == PaymentStatus.APPROVED),
        "total_settled_amount": sum(m.amount for m in milestones if m.status == PaymentStatus.SETTLED),
    }
    return {
        "shipment_id": payment_intent.freight_token_id,
        "milestones": milestones_detail,
        "summary": summary,
    }


@app.get("/audit/payment_intents/{payment_id}/milestones")
async def get_payment_intent_milestones(
    payment_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all milestone settlements for a specific payment intent.

    Shows the status of each scheduled milestone and whether it has been released
    through the payment rail.

    Args:
        payment_id: Payment intent ID
        db: Database session

    Returns:
        Payment intent with milestone details

    Raises:
        HTTPException: If payment intent not found
    """
    payment_intent = db.query(PaymentIntentModel).filter(PaymentIntentModel.id == payment_id).first()

    if not payment_intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    # Get all milestones for this intent
    milestones = (
        db.query(MilestoneSettlementModel)
        .filter(MilestoneSettlementModel.payment_intent_id == payment_id)
        .order_by(MilestoneSettlementModel.created_at)
        .all()
    )

    milestones_detail = []
    total_approved = 0.0
    total_settled = 0.0

    for milestone in milestones:
        milestone_detail = {
            "id": milestone.id,
            "event_type": milestone.event_type,
            "amount": milestone.amount,
            "currency": milestone.currency,
            "status": milestone.status.value,
            "provider": milestone.provider,
            "reference": milestone.reference,
            "occurred_at": (milestone.occurred_at.isoformat() if milestone.occurred_at else None),
            "settled_at": (milestone.settled_at.isoformat() if milestone.settled_at else None),
            "created_at": milestone.created_at.isoformat(),
        }

        milestones_detail.append(milestone_detail)

        if milestone.status == PaymentStatus.APPROVED:
            total_approved += milestone.amount
        elif milestone.status == PaymentStatus.SETTLED:
            total_settled += milestone.amount

    return {
        "payment_intent": {
            "id": payment_intent.id,
            "freight_token_id": payment_intent.freight_token_id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "risk_score": payment_intent.risk_score,
            "risk_tier": payment_intent.risk_tier.value,
            "status": payment_intent.status.value,
        },
        "milestones": milestones_detail,
        "summary": {
            "total_milestones": len(milestones),
            # Maintain both deprecated and current keys for backward compatibility
            "total_approved": total_approved,
            "total_settled": total_settled,
            "total_approved_amount": total_approved,
            "total_settled_amount": total_settled,
        },
    }


if __name__ == "__main__":
    from core.import_safety import ensure_import_safety
    ensure_import_safety()

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
