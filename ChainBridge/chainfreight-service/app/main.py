"""
ChainFreight Service (ChainBridge)

Goal:
- Provide an API for shipment lifecycle and supply chain execution.
- Enable tokenization of freight assets for trading and financing.
- Expose endpoints to create, track, and update shipments.
- Expose endpoints to create and manage freight tokens.
- Emit shipment events and call ChainPay webhook for milestone-based payments.
- Use SQLAlchemy and SQLite (for now) for persistence.
- Integrate with ChainIQ for risk scoring and optimization.
- Integrate with blockchain for token minting and trading.

Tasks for Copilot:
- Keep endpoints simple and RESTful.
- Use Pydantic models for request/response schemas.
- Use dependency-injected DB sessions.
- Make the code clean and ready to integrate with ChainIQ scoring.
- Structure tokenization logic for future blockchain integration.
"""

import os
import logging
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import httpx

from .database import get_db, init_db
from .models import (
    Shipment as ShipmentModel,
    FreightToken as FreightTokenModel,
    FreightTokenStatus,
    ShipmentEvent as ShipmentEventModel,
)
from .schemas import (
    ShipmentCreate,
    ShipmentUpdate,
    ShipmentResponse,
    ShipmentListResponse,
    ShipmentStatusEnum,
    FreightTokenResponse,
    FreightTokenListResponse,
    TokenizeShipmentRequest,
    ShipmentEventCreate,
    ShipmentEventResponse,
    ShipmentEventListResponse,
    ShipmentEventTypeEnum,
)
from .chainiq_client import score_shipment as call_chainiq

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CHAINPAY_URL = os.getenv("CHAINPAY_URL", "http://localhost:8003")

app = FastAPI(
    title="ChainFreight Service",
    description="Shipment lifecycle, execution, and tokenized freight API for ChainBridge",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "chainfreight"}


# --- Dependency ---


def get_db_session():
    """Dependency for FastAPI to get a DB session."""
    db = get_db()
    return db


# --- SHIPMENT ENDPOINTS ---


@app.post("/shipments", response_model=ShipmentResponse, status_code=201)
async def create_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    """
    Create a new shipment record.

    Args:
        shipment: Shipment information to create
        db: Database session

    Returns:
        Created shipment record
    """
    db_shipment = ShipmentModel(**shipment.model_dump())
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)

    return db_shipment


@app.get("/shipments", response_model=ShipmentListResponse)
async def list_shipments(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: ShipmentStatusEnum | None = Query(None),
    db: Session = Depends(get_db),
) -> ShipmentListResponse:
    """
    List shipments with optional filtering.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        status: Filter by shipment status (optional)
        db: Database session

    Returns:
        List of shipments with total count
    """
    query = db.query(ShipmentModel)

    # Apply status filter if provided
    if status is not None:
        query = query.filter(ShipmentModel.status == status)

    total = query.count()
    shipments = query.offset(skip).limit(limit).all()

    return ShipmentListResponse(total=total, shipments=shipments)


@app.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    """
    Retrieve a specific shipment by ID.

    Args:
        shipment_id: ID of the shipment to retrieve
        db: Database session

    Returns:
        Shipment record

    Raises:
        HTTPException: If shipment not found
    """
    shipment = db.query(ShipmentModel).filter(ShipmentModel.id == shipment_id).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return shipment


@app.put("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: int,
    shipment_update: ShipmentUpdate,
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    """
    Update a shipment's information.

    Args:
        shipment_id: ID of the shipment to update
        shipment_update: Fields to update
        db: Database session

    Returns:
        Updated shipment record

    Raises:
        HTTPException: If shipment not found
    """
    shipment = db.query(ShipmentModel).filter(ShipmentModel.id == shipment_id).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Update only provided fields
    update_data = shipment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(shipment, field, value)

    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    return shipment


# --- FREIGHT TOKEN ENDPOINTS ---


@app.post("/shipments/{shipment_id}/tokenize", response_model=FreightTokenResponse, status_code=201)
async def tokenize_shipment(
    shipment_id: int,
    payload: TokenizeShipmentRequest,
    db: Session = Depends(get_db),
) -> FreightTokenResponse:
    """
    Create a freight token for a shipment with automatic risk scoring via ChainIQ.

    Tokenization enables fractional ownership and trading of freight assets.
    Each token represents a claim on a portion of the shipment's cargo value.
    Risk scoring is performed automatically via ChainIQ service integration.

    Args:
        shipment_id: ID of the shipment to tokenize
        payload: Token creation parameters (face_value, currency)
        db: Database session

    Returns:
        Created freight token record with risk scoring fields populated

    Raises:
        HTTPException: If shipment not found or token already exists

    Note:
        If ChainIQ service is unavailable, tokenization proceeds with null risk fields.
    """
    # Verify shipment exists
    shipment = db.query(ShipmentModel).filter(ShipmentModel.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Check if token already exists for this shipment
    existing_token = db.query(FreightTokenModel).filter(FreightTokenModel.shipment_id == shipment_id).first()
    if existing_token:
        raise HTTPException(status_code=400, detail=f"Freight token already exists for shipment {shipment_id}")

    # Call ChainIQ service for risk scoring
    chainiq_result = await call_chainiq(
        shipment_id=shipment_id,
        origin=shipment.origin,
        destination=shipment.destination,
        planned_delivery_date=(shipment.planned_delivery_date.isoformat() if shipment.planned_delivery_date else None),
    )

    # Create new token with ChainIQ scoring
    token = FreightTokenModel(
        shipment_id=shipment_id,
        face_value=payload.face_value,
        currency=payload.currency,
        status=FreightTokenStatus.CREATED,
    )

    # Populate risk fields if scoring succeeded
    if chainiq_result:
        risk_score, risk_category, recommended_action = chainiq_result
        token.risk_score = risk_score
        token.risk_category = risk_category
        token.recommended_action = recommended_action

    db.add(token)
    db.commit()
    db.refresh(token)

    return token


@app.get("/shipments/{shipment_id}/token", response_model=FreightTokenResponse)
async def get_shipment_token(
    shipment_id: int,
    db: Session = Depends(get_db),
) -> FreightTokenResponse:
    """
    Get the freight token associated with a shipment.

    Args:
        shipment_id: ID of the shipment
        db: Database session

    Returns:
        Freight token record

    Raises:
        HTTPException: If shipment or token not found
    """
    # Verify shipment exists
    shipment = db.query(ShipmentModel).filter(ShipmentModel.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Get token
    token = db.query(FreightTokenModel).filter(FreightTokenModel.shipment_id == shipment_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="No freight token for this shipment")

    return token


@app.get("/tokens", response_model=FreightTokenListResponse)
async def list_tokens(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> FreightTokenListResponse:
    """
    List all freight tokens with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of tokens with total count
    """
    query = db.query(FreightTokenModel)
    total = query.count()
    tokens = query.offset(skip).limit(limit).all()

    return FreightTokenListResponse(total=total, tokens=tokens)


@app.get("/tokens/{token_id}", response_model=FreightTokenResponse)
async def get_token(
    token_id: int,
    db: Session = Depends(get_db),
) -> FreightTokenResponse:
    """
    Get a specific freight token by ID.

    Args:
        token_id: ID of the token to retrieve
        db: Database session

    Returns:
        Freight token record

    Raises:
        HTTPException: If token not found
    """
    token = db.query(FreightTokenModel).filter(FreightTokenModel.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Freight token not found")

    return token


# --- SHIPMENT EVENT ENDPOINTS ---


@app.post("/shipments/{shipment_id}/events", response_model=ShipmentEventResponse, status_code=201)
async def create_shipment_event(
    shipment_id: int,
    event_data: ShipmentEventCreate,
    db: Session = Depends(get_db),
) -> ShipmentEventResponse:
    """
    Record a new shipment event (e.g., pickup confirmed, POD confirmed).

    After saving the event to the database, this endpoint calls the ChainPay webhook
    to trigger milestone-based payment settlement for any related payment intents.

    Args:
        shipment_id: ID of the shipment
        event_data: Event details (type, occurred_at, metadata)
        db: Database session

    Returns:
        Created event record

    Raises:
        HTTPException: If shipment not found (404)
    """
    # Verify shipment exists
    shipment = db.query(ShipmentModel).filter(ShipmentModel.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Create event with default occurred_at if not provided
    occurred_at = event_data.occurred_at or datetime.utcnow()

    db_event = ShipmentEventModel(
        shipment_id=shipment_id,
        event_type=event_data.event_type,
        occurred_at=occurred_at,
        metadata=event_data.metadata,
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    logger.info(f"Event recorded: shipment_id={shipment_id}, event_type={event_data.event_type}, id={db_event.id}")

    # Call ChainPay webhook asynchronously (fire and forget)
    try:
        await call_chainpay_webhook(shipment_id, event_data.event_type, occurred_at, db_event.id)
    except Exception as e:
        # Log but don't fail the request - ChainPay can retry via other means
        logger.warning(f"Failed to call ChainPay webhook for event {db_event.id}: {e}")

    return db_event


@app.get("/shipments/{shipment_id}/events", response_model=ShipmentEventListResponse)
async def list_shipment_events(
    shipment_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> ShipmentEventListResponse:
    """
    List all events for a shipment.

    Args:
        shipment_id: ID of the shipment
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of events with total count

    Raises:
        HTTPException: If shipment not found (404)
    """
    # Verify shipment exists
    shipment = db.query(ShipmentModel).filter(ShipmentModel.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Query events ordered by occurred_at (descending)
    query = db.query(ShipmentEventModel).filter(ShipmentEventModel.shipment_id == shipment_id)
    total = query.count()
    events = query.order_by(ShipmentEventModel.occurred_at.desc()).offset(skip).limit(limit).all()

    return ShipmentEventListResponse(total=total, events=events)


# --- INTERNAL WEBHOOK HELPER ---


async def call_chainpay_webhook(
    shipment_id: int,
    event_type: ShipmentEventTypeEnum,
    occurred_at: datetime,
    event_id: int,
) -> None:
    """
    Call ChainPay webhook to process milestone-based payment settlement.

    This is called asynchronously after recording a shipment event.
    The webhook payload contains shipment_id, event_type, occurred_at for ChainPay
    to determine if any payment milestones should be triggered.

    Args:
        shipment_id: ID of the shipment
        event_type: Type of event that occurred
        occurred_at: When the event occurred
        event_id: ID of the event record (for logging)

    Raises:
        Various httpx exceptions if webhook call fails
    """
    webhook_url = f"{CHAINPAY_URL}/webhooks/shipment_event"
    payload = {
        "shipment_id": shipment_id,
        "event_type": event_type.value,
        "occurred_at": occurred_at.isoformat(),
        "event_id": event_id,
    }

    logger.info(f"Calling ChainPay webhook: {webhook_url} with payload={payload}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"ChainPay webhook succeeded for event {event_id}: {response.status_code}")
    except httpx.TimeoutException as e:
        logger.warning(f"ChainPay webhook timeout for event {event_id}: {e}")
        raise
    except httpx.ConnectError as e:
        logger.warning(f"ChainPay webhook connection error for event {event_id}: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.warning(f"ChainPay webhook HTTP error for event {event_id}: {e.response.status_code}")
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
