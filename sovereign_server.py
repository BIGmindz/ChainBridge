#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CHAINBRIDGE SOVEREIGN SERVER v2.0                                  ║
║                   PAC-INT-P211-API-UPGRADE                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TYPE: INFRASTRUCTURE_BINDING                                                ║
║  GOVERNANCE_TIER: CONSTITUTIONAL_LAW                                         ║
║  MODE: INTERFACE_SOVEREIGNTY + FINANCIAL_TRANSPARENCY                        ║
║  LANE: INFRASTRUCTURE_LANE                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

THE SOVEREIGN API v2.0:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                      SOVEREIGN SERVER v2.0                              │
  │           FastAPI Exoskeleton (Port 8000) + Financial Trace             │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                         │
  │   [External World]                                                      │
  │         │                                                               │
  │         ▼                                                               │
  │   ┌─────────────────────────────────────────────────────────────┐      │
  │   │  POST /v1/transaction                                       │      │
  │   │  ─────────────────────────────────────────────────────────  │      │
  │   │  Input: { user_data, payment_data (+ fee_strategy), ... }   │      │
  │   │  Validation: Pydantic Schema Enforcement                    │      │
  │   │  Output: TransactionReceipt + financial_trace               │      │
  │   │          (200 OK / 402 Payment Required / 422 Error)        │      │
  │   └─────────────────────────────────────────────────────────────┘      │
  │         │                                                               │
  │         ▼                                                               │
  │   ┌─────────────────────────────────────────────────────────────┐      │
  │   │          CHAINBRIDGE CONTROLLER v2.0 (P80 + P210)           │      │
  │   │    [BIOMETRIC] → [AML] → [CUSTOMS] → [INVISIBLE BANK]       │      │
  │   │         Trinity Gates      +      Financial Execution       │      │
  │   └─────────────────────────────────────────────────────────────┘      │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

INVARIANTS:
  INV-API-001 (Schema Strictness): Input must match the Trinity contract.
  INV-API-002 (Fail Safe): API crash must not corrupt the Ledger.
  INV-API-003 (Rich Receipts): Client receives proof of financial execution.

TRAINING SIGNAL:
  "The Voice now speaks the language of Money."
"""

import logging
import json
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from modules.core.chainbridge_controller import ChainBridgeController, TransactionStatus

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [SOVEREIGN_API] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SovereignServer")


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS - TRINITY SCHEMA ENFORCEMENT
# ══════════════════════════════════════════════════════════════════════════════

class UserData(BaseModel):
    """
    P85 Biometric Gate Input Schema
    Validates identity verification data.
    """
    user_id: str = Field(..., min_length=1, description="Unique user identifier")
    liveness_score: float = Field(default=0.95, ge=0.0, le=1.0, description="Liveness detection score")
    face_similarity: float = Field(default=0.95, ge=0.0, le=1.0, description="Face match similarity")
    has_enrolled_template: bool = Field(default=True, description="Whether user has enrolled biometric")
    document_type: str = Field(default="PASSPORT", description="Type of ID document")
    is_expired: bool = Field(default=False, description="Whether document is expired")
    is_tampered: bool = Field(default=False, description="Whether document shows tampering")
    mrz_valid: bool = Field(default=True, description="Whether MRZ/barcode is valid")
    is_static_image: bool = Field(default=False, description="Static image attack indicator")
    is_replay: bool = Field(default=False, description="Video replay attack indicator")
    is_deepfake: bool = Field(default=False, description="Deepfake attack indicator")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "USR-ALICE-001",
                "liveness_score": 0.98,
                "face_similarity": 0.96,
                "has_enrolled_template": True,
                "document_type": "PASSPORT",
                "is_expired": False,
                "is_tampered": False,
                "mrz_valid": True
            }
        }


class PaymentData(BaseModel):
    """
    P65 AML Gate Input Schema + P202 Fee Strategy
    Validates financial transaction data with fee configuration.
    """
    transaction_id: Optional[str] = Field(None, description="Optional transaction ID")
    payer_id: str = Field(..., min_length=1, description="Entity ID of payer")
    payee_id: str = Field(..., min_length=1, description="Entity ID of payee")
    payer_country: str = Field(default="US", min_length=2, max_length=2, description="ISO country code")
    payee_country: str = Field(default="US", min_length=2, max_length=2, description="ISO country code")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD", description="ISO 4217 currency code (USD, EUR, GBP, etc.)")
    fee_strategy: str = Field(default="default", description="Fee calculation strategy (default, premium, zero)")
    daily_total: float = Field(default=0.0, ge=0, description="Running daily total for payer")
    is_new_customer: bool = Field(default=False, description="Whether payer is new customer")
    off_hours: bool = Field(default=False, description="Whether transaction is outside business hours")

    class Config:
        json_schema_extra = {
            "example": {
                "payer_id": "ACME-CORP",
                "payee_id": "GLOBEX-INC",
                "payer_country": "US",
                "payee_country": "DE",
                "amount": 250000.00,
                "currency": "USD",
                "fee_strategy": "default",
                "daily_total": 0
            }
        }


class ManifestData(BaseModel):
    """Shipment manifest for customs validation."""
    shipment_id: str = Field(..., min_length=1, description="Unique shipment identifier")
    seal_intact: bool = Field(default=True, description="Whether container seal is intact")
    declared_weight_kg: float = Field(..., gt=0, description="Declared weight in kg")
    actual_weight_kg: float = Field(..., gt=0, description="Actual weight in kg")
    bill_of_lading: bool = Field(default=True, description="Bill of lading present")
    commercial_invoice: bool = Field(default=True, description="Commercial invoice present")
    packing_list: bool = Field(default=True, description="Packing list present")


class TelemetryData(BaseModel):
    """Route telemetry for behavioral analysis."""
    route_deviation_km: float = Field(default=0.0, ge=0, description="Route deviation in km")
    unscheduled_stops: int = Field(default=0, ge=0, description="Number of unscheduled stops")
    stop_locations: List[str] = Field(default_factory=list, description="Stop location descriptions")
    arrival_delay_min: int = Field(default=0, ge=0, description="Arrival delay in minutes")
    gps_gaps: int = Field(default=0, ge=0, description="Number of GPS signal gaps")
    gps_gap_duration_min: int = Field(default=0, ge=0, description="Total GPS gap duration")


class ShipmentData(BaseModel):
    """
    P75 Smart Customs Gate Input Schema
    Validates cargo/logistics data.
    """
    manifest: ManifestData
    telemetry: TelemetryData = Field(default_factory=TelemetryData)

    class Config:
        json_schema_extra = {
            "example": {
                "manifest": {
                    "shipment_id": "SHP-001-LEGIT",
                    "seal_intact": True,
                    "declared_weight_kg": 5000,
                    "actual_weight_kg": 5050,
                    "bill_of_lading": True,
                    "commercial_invoice": True,
                    "packing_list": True
                },
                "telemetry": {
                    "route_deviation_km": 1.2,
                    "unscheduled_stops": 0,
                    "arrival_delay_min": 15,
                    "gps_gaps": 0
                }
            }
        }


class SovereignTransactionRequest(BaseModel):
    """
    Complete Sovereign Transaction Request
    The Trinity Contract - requires all three data types.
    """
    user_data: UserData
    payment_data: PaymentData
    shipment_data: ShipmentData

    class Config:
        json_schema_extra = {
            "example": {
                "user_data": {
                    "user_id": "USR-ALICE-001",
                    "liveness_score": 0.98,
                    "face_similarity": 0.96,
                    "document_type": "PASSPORT"
                },
                "payment_data": {
                    "payer_id": "ACME-CORP",
                    "payee_id": "GLOBEX-INC",
                    "amount": 250000.00
                },
                "shipment_data": {
                    "manifest": {
                        "shipment_id": "SHP-001",
                        "seal_intact": True,
                        "declared_weight_kg": 5000,
                        "actual_weight_kg": 5050
                    },
                    "telemetry": {
                        "route_deviation_km": 1.0,
                        "unscheduled_stops": 0
                    }
                }
            }
        }


class FinancialTrace(BaseModel):
    """
    P210 Financial Execution Trace
    Provides transparency into the movement of funds.
    INV-API-003: Rich Receipts
    """
    settlement_intent_id: Optional[str] = Field(None, description="Unique settlement intent ID")
    settlement_status: Optional[str] = Field(None, description="Settlement status (captured, voided, etc.)")
    gross_amount: str = Field(..., description="Original transaction amount")
    currency: str = Field(..., description="Currency code")
    fees: Optional[Dict[str, Any]] = Field(None, description="Fee breakdown (total, strategy, components)")
    net_amount: Optional[str] = Field(None, description="Amount after fees")
    payer_account: Optional[str] = Field(None, description="Payer account (public alias)")
    payee_account: Optional[str] = Field(None, description="Payee account (public alias)")
    ledger_committed: bool = Field(default=False, description="Whether ledger entry was committed")

    class Config:
        json_schema_extra = {
            "example": {
                "settlement_intent_id": "PI-abc123",
                "settlement_status": "captured",
                "gross_amount": "250000.00",
                "currency": "USD",
                "fees": {
                    "total": "7250.30",
                    "strategy": "default",
                    "breakdown": [{"name": "percentage_fee", "amount": "7250.00"}, {"name": "flat_fee", "amount": "0.30"}]
                },
                "net_amount": "242749.70",
                "payer_account": "ACME-CORP",
                "payee_account": "GLOBEX-INC",
                "ledger_committed": True
            }
        }


class TransactionReceipt(BaseModel):
    """
    Response model for transaction results.
    v2.0: Now includes financial_trace for full transparency.
    """
    transaction_id: str
    timestamp: str
    status: str
    finalized: bool
    transaction_hash: Optional[str] = None
    blame: Optional[Dict[str, str]] = None
    gates: Dict[str, Any]
    financial_trace: Optional[FinancialTrace] = Field(None, description="Financial execution trace (P210)")
    participants: Optional[Dict[str, Any]] = None
    value: Optional[Dict[str, str]] = None
    controller: str
    version: str
    attestation: Optional[str] = None
    invariants_enforced: Optional[List[str]] = Field(None, description="List of invariants enforced")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    controller: str
    uptime_seconds: float
    transactions_processed: int


class ErrorResponse(BaseModel):
    """Structured error response."""
    error: str
    detail: str
    timestamp: str


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL STATE
# ══════════════════════════════════════════════════════════════════════════════

# Singleton Controller (initialized on startup)
controller: Optional[ChainBridgeController] = None
start_time: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION LIFECYCLE
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    global controller, start_time
    
    # Startup
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║        SOVEREIGN SERVER v2.0 INITIALIZING...                  ║")
    logger.info("║        PAC-INT-P211-API-UPGRADE                                ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")
    
    controller = ChainBridgeController()
    start_time = datetime.now(timezone.utc)
    
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║        🚀 SOVEREIGN SERVER v2.0 ONLINE - PORT 8000            ║")
    logger.info("║        TRINITY GATES + INVISIBLE BANK ARMED                  ║")
    logger.info("║        ENDPOINT: POST /v1/transaction                        ║")
    logger.info("║        \"The Voice now speaks the language of Money.\"        ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")
    
    yield
    
    # Shutdown
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║        SOVEREIGN SERVER SHUTTING DOWN...                     ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ChainBridge Sovereign Server",
    description="The Voice of the Trinity - Sovereign Transaction Processing API v2.0 (Financial Transparency)",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPTION HANDLERS (INV-API-002: No Stack Trace Exposure)
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions without exposing internals."""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "detail": "An unexpected error occurred. The Ledger remains intact.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - Server identification."""
    return {
        "name": "ChainBridge Sovereign Server",
        "version": "2.0.0",
        "status": "ONLINE",
        "mode": "TRINITY_GATES + INVISIBLE_BANK",
        "endpoint": "/v1/transaction",
        "docs": "/docs",
        "benson_says": "The Voice now speaks the language of Money."
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    global controller, start_time
    
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds() if start_time else 0
    
    return HealthResponse(
        status="HEALTHY",
        version="2.0.0",
        controller="ChainBridgeController v2.0.0",
        uptime_seconds=uptime,
        transactions_processed=controller.transactions_processed if controller else 0
    )


@app.post(
    "/v1/transaction",
    response_model=TransactionReceipt,
    responses={
        200: {"description": "Transaction processed successfully (FINALIZED or ABORTED)"},
        402: {"description": "Payment Required - Settlement failed (insufficient funds)", "model": ErrorResponse},
        422: {"description": "Validation error - schema mismatch", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    tags=["Transactions"]
)
async def process_transaction(request: SovereignTransactionRequest):
    """
    Process a Sovereign Transaction through the Trinity Gates + Invisible Bank.
    
    This endpoint accepts a complete transaction payload containing:
    - **user_data**: Identity verification data (P85 Biometric Gate)
    - **payment_data**: Financial transaction data (P65 AML Gate) with fee_strategy
    - **shipment_data**: Cargo/logistics data (P75 Customs Gate)
    
    v2.0 FINANCIAL INTEGRATION (P210/P211):
    - All gates must pass before financial execution begins
    - Fees calculated using specified strategy (default: 2.9% + $0.30)
    - Settlement via two-phase commit (authorize → capture)
    - Full financial_trace in response for transparency
    
    **Response Codes:**
    - 200: Transaction processed (check 'finalized' field for outcome)
    - 402: Payment Required (settlement failed - insufficient funds)
    - 422: Validation error (schema mismatch)
    
    **Invariants Enforced:**
    - INV-API-001: Input must match the Trinity contract schema
    - INV-API-003: Rich Receipts - client receives proof of financial execution
    - INV-CORE-001: No partial sovereign transactions (Atomic Finality)
    - INV-INT-001: Gate Supremacy - money doesn't move if gates fail
    """
    global controller
    
    if controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Controller not initialized"
        )
    
    logger.info("=" * 70)
    logger.info("INCOMING SOVEREIGN TRANSACTION REQUEST (v2.0)")
    logger.info(f"User: {request.user_data.user_id}")
    logger.info(f"Payer: {request.payment_data.payer_id} → Payee: {request.payment_data.payee_id}")
    logger.info(f"Amount: ${request.payment_data.amount:,.2f} {request.payment_data.currency}")
    logger.info(f"Fee Strategy: {request.payment_data.fee_strategy}")
    logger.info(f"Shipment: {request.shipment_data.manifest.shipment_id}")
    logger.info("=" * 70)
    
    # Convert Pydantic models to dicts for Controller
    user_dict = request.user_data.model_dump()
    payment_dict = request.payment_data.model_dump()
    shipment_dict = {
        "manifest": request.shipment_data.manifest.model_dump(),
        "telemetry": request.shipment_data.telemetry.model_dump()
    }
    
    # Process through Trinity Controller v2.0
    result = controller.process_transaction(
        user_data=user_dict,
        payment_data=payment_dict,
        shipment_data=shipment_dict
    )
    
    # Check for settlement failure (402 Payment Required)
    blame = result.get("blame", {})
    if blame.get("gate") == "SETTLEMENT" or blame.get("component") == "SETTLEMENT":
        logger.warning(f"❌ SETTLEMENT FAILED: {result['transaction_id']} | Reason: {blame.get('reason')}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "SETTLEMENT_FAILED",
                "reason": blame.get("reason", "Insufficient funds or settlement error"),
                "transaction_id": result["transaction_id"],
                "gates_passed": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    # Map financial_execution to financial_trace for API response (INV-API-003)
    if "financial_execution" in result:
        fe = result["financial_execution"]
        result["financial_trace"] = {
            "settlement_intent_id": fe.get("settlement_intent_id"),
            "settlement_status": fe.get("settlement_status"),
            "gross_amount": fe.get("gross_amount"),
            "currency": fe.get("currency"),
            "fees": fe.get("fees"),
            "net_amount": fe.get("net_amount"),
            # Hide internal account IDs, use public aliases
            "payer_account": request.payment_data.payer_id,
            "payee_account": request.payment_data.payee_id,
            "ledger_committed": fe.get("settlement_status") == "captured"
        }
        # Remove internal financial_execution from response
        del result["financial_execution"]
    
    # Log outcome
    if result["status"] == TransactionStatus.FINALIZED.value:
        logger.info(f"✅ TRANSACTION FINALIZED: {result['transaction_id']}")
        if "financial_trace" in result:
            ft = result["financial_trace"]
            logger.info(f"   Financial: {ft.get('gross_amount')} {ft.get('currency')} (Net: {ft.get('net_amount')})")
    else:
        logger.warning(f"❌ TRANSACTION ABORTED: {result['transaction_id']} | Blame: {result.get('blame', {}).get('gate')}")
    
    return result


@app.get("/v1/stats", tags=["Statistics"])
async def get_statistics():
    """Get controller statistics."""
    global controller
    
    if controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Controller not initialized"
        )
    
    return {
        "transactions_processed": controller.transactions_processed,
        "transactions_finalized": controller.transactions_finalized,
        "transactions_aborted": controller.transactions_aborted,
        "finalization_rate": (
            controller.transactions_finalized / controller.transactions_processed * 100
            if controller.transactions_processed > 0 else 0
        ),
        "controller_version": controller.version
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║        CHAINBRIDGE SOVEREIGN SERVER v2.0                           ║")
    print("║        PAC-INT-P211-API-UPGRADE                                    ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  MODE: TRINITY_GATES + INVISIBLE_BANK                             ║")
    print("║  \"The Voice now speaks the language of Money.\"                   ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    
    uvicorn.run(
        "sovereign_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
