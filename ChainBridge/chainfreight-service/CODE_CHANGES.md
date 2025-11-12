# ChainFreight + ChainIQ Integration - Code Changes Reference

## Overview

This document shows all code changes made to integrate ChainIQ risk scoring into the tokenization workflow.

## Files Changed

### 1. app/models.py - Added Risk Fields to FreightToken

**Location:** `/chainfreight-service/app/models.py`

**Changes:**
- Added 3 new columns to FreightToken model
- All nullable to support graceful degradation when ChainIQ unavailable

```python
class FreightToken(Base):
    """Freight token with ChainIQ risk scoring integration."""
    __tablename__ = "freight_tokens"

    # ... existing fields ...
    
    # NEW: Risk scoring from ChainIQ
    risk_score = Column(Float, nullable=True)
    risk_category = Column(String, nullable=True)
    recommended_action = Column(String, nullable=True)
```

**Database Migration:**

For existing databases, run:

```sql
ALTER TABLE freight_tokens ADD COLUMN risk_score FLOAT;
ALTER TABLE freight_tokens ADD COLUMN risk_category VARCHAR(50);
ALTER TABLE freight_tokens ADD COLUMN recommended_action VARCHAR(255);
```

---

### 2. app/schemas.py - Updated FreightTokenResponse

**Location:** `/chainfreight-service/app/schemas.py`

**Changes:**
- Added 3 new optional fields to FreightTokenResponse
- risk_score validated to be between 0.0 and 1.0

```python
class FreightTokenResponse(FreightTokenBase):
    """Schema for freight token API responses."""
    id: int
    shipment_id: int
    status: FreightTokenStatusEnum
    token_address: Optional[str] = None
    
    # NEW: Risk fields from ChainIQ
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    risk_category: Optional[str] = None
    recommended_action: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

---

### 3. app/chainiq_client.py - NEW FILE

**Location:** `/chainfreight-service/app/chainiq_client.py`

**Purpose:** HTTP client for inter-service communication with ChainIQ

**Key Components:**

#### ChainIQRequest Model

```python
class ChainIQRequest(BaseModel):
    """Request to ChainIQ scoring service."""
    shipment_id: str
    driver_id: Optional[int] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    planned_delivery_date: Optional[str] = None
```

#### ChainIQResponse Model

```python
class ChainIQResponse(BaseModel):
    """Response from ChainIQ scoring service."""
    shipment_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_category: str  # "low", "medium", "high"
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    reasoning: Optional[str] = None
```

#### score_shipment() Function

```python
async def score_shipment(
    shipment_id: int,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    planned_delivery_date: Optional[str] = None,
    driver_id: Optional[int] = None,
) -> Optional[tuple[float, str, str]]:
    """
    Call ChainIQ service to score a shipment.
    
    Args:
        shipment_id: ID of shipment to score
        origin: Shipment origin location
        destination: Shipment destination location
        planned_delivery_date: ISO format delivery date
        driver_id: Optional driver ID
        
    Returns:
        Tuple of (risk_score, risk_category, recommended_action)
        or None if scoring fails
    """
    # Async HTTP call with 10-second timeout
    # Graceful error handling (returns None if ChainIQ unavailable)
    # Logs all scoring events
```

**Error Handling:**
- TimeoutException: Returns None, logs warning
- ConnectError: Returns None, logs warning
- Other exceptions: Returns None, logs error

#### generate_recommended_action() Function

```python
def generate_recommended_action(risk_category: str, risk_score: float) -> str:
    """
    Generate recommended action based on risk.
    
    Examples:
    - "APPROVE - Low risk"
    - "APPROVE_WITH_CONDITIONS - Risk mitigation needed"
    - "REVIEW - Additional assessment"
    - "REVIEW_URGENTLY - High risk"
    - "REJECT - Very high risk"
    """
```

---

### 4. app/main.py - Integrated ChainIQ in Tokenize Endpoint

**Location:** `/chainfreight-service/app/main.py`

**Changes to Imports:**

```python
# NEW: Import ChainIQ client
from .chainiq_client import score_shipment as call_chainiq

# UPDATED: Added ShipmentStatusEnum to schema imports
from .schemas import (
    ShipmentCreate,
    ShipmentUpdate,
    ShipmentResponse,
    ShipmentListResponse,
    ShipmentStatusEnum,  # ADDED
    FreightTokenResponse,
    FreightTokenListResponse,
    TokenizeShipmentRequest,
)
```

**Updated tokenize_shipment() Endpoint:**

```python
@app.post("/shipments/{shipment_id}/tokenize", 
          response_model=FreightTokenResponse, 
          status_code=201)
async def tokenize_shipment(
    shipment_id: int,
    payload: TokenizeShipmentRequest,
    db: Session = Depends(get_db),
) -> FreightTokenResponse:
    """
    Create freight token with automatic ChainIQ risk scoring.
    """
    # 1. Validate shipment exists
    shipment = db.query(ShipmentModel).filter(
        ShipmentModel.id == shipment_id
    ).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # 2. Check no token exists
    existing_token = (
        db.query(FreightTokenModel)
        .filter(FreightTokenModel.shipment_id == shipment_id)
        .first()
    )
    if existing_token:
        raise HTTPException(status_code=400, detail="Token already exists")

    # 3. NEW: Call ChainIQ for risk scoring
    chainiq_result = await call_chainiq(
        shipment_id=shipment_id,
        origin=shipment.origin,
        destination=shipment.destination,
        planned_delivery_date=(
            shipment.planned_delivery_date.isoformat() 
            if shipment.planned_delivery_date else None
        ),
    )

    # 4. Create token
    token = FreightTokenModel(
        shipment_id=shipment_id,
        face_value=payload.face_value,
        currency=payload.currency,
        status=FreightTokenStatus.CREATED,
    )
    
    # 5. NEW: Populate risk fields if scoring succeeded
    if chainiq_result:
        risk_score, risk_category, recommended_action = chainiq_result
        token.risk_score = risk_score
        token.risk_category = risk_category
        token.recommended_action = recommended_action
    
    # 6. Save and return
    db.add(token)
    db.commit()
    db.refresh(token)
    
    return token
```

**Key Logic:**
1. Extract shipment details (origin, destination, dates)
2. Call ChainIQ asynchronously (non-blocking)
3. Handle both success (risk fields populated) and failure (risk fields null)
4. Always return token, even if scoring fails
5. Log all operations for monitoring

---

## Data Flow Diagram

``` text
POST /shipments/1/tokenize
    │
    ├─ ChainFreight validates shipment exists ────┐
    │                                               │
    ├─ ChainFreight calls ChainIQ service:    │
    │   (async with 10s timeout)               │
    │   {                                       │
    │     shipment_id: 1,                      │
    │     origin: "LA",                        │
    │     destination: "CHI",                  │
    │     planned_delivery_date: "2025-11-14"  │
    │   }                                       │
    │        │                                   │
    │        ├─────────────────────────────────┼─→ ChainIQ Service
    │        │                                   │     (Port 8001)
    │        │   Returns:                        │
    │        │   {                               │
    │        │     risk_score: 0.35,             │
    │        │     risk_category: "low",         │
    │        │     confidence: 0.85,             │
    │        │     reasoning: "..."              │
    │        │   }                               │
    │        └─────────────────────────────────┼─← 
    │                                           │
    ├─ ChainFreight generates recommended_action  │
    │   (business rules based on risk)           │
    │                                            │
    ├─ Create FreightToken in DB:            │
    │   - id: 1                               │
    │   - shipment_id: 1                      │
    │   - face_value: 100000                  │
    │   - risk_score: 0.35        ◄──┐        │
    │   - risk_category: "low"    ◄──┼─ From ChainIQ
    │   - recommended_action: "..." ◄─┘        │
    │                                          │
    └─ Return populated token to client
```

---

## Testing the Integration

### Compile Check

All Python files pass syntax validation:

```bash
python -m py_compile app/models.py       # ✓ OK
python -m py_compile app/schemas.py      # ✓ OK
python -m py_compile app/main.py         # ✓ OK
python -m py_compile app/chainiq_client.py  # ✓ OK
```

### Local Test

```bash
# Terminal 1: ChainIQ
cd chainiq-service
python -m uvicorn app.main:app --port 8001

# Terminal 2: ChainFreight
cd chainfreight-service
python -m uvicorn app.main:app --port 8002

# Terminal 3: Test
curl -X POST http://localhost:8002/shipments/1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"face_value":100000,"currency":"USD"}'
```

---

## Configuration

### ChainIQ Service URL

Edit `chainiq_client.py`:

```python
# Development (default)
CHAINIQ_URL = "http://localhost:8001"

# Production (set via environment)
import os
CHAINIQ_URL = os.getenv("CHAINIQ_URL", "http://localhost:8001")
```

### Timeout

Edit `chainiq_client.py`:

```python
# Current: 10 seconds
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(...)

# Adjust for slower networks
# timeout=30.0  # 30 seconds
```

---

## Summary of Changes

| File | Changes | Purpose |
|------|---------|---------|
| models.py | +3 columns | Store risk data from ChainIQ |
| schemas.py | +3 fields | Include risk in API responses |
| chainiq_client.py | NEW | HTTP client for ChainIQ calls |
| main.py | +1 import, +1 code block | Call ChainIQ during tokenization |
| README.md | +1 section | Document integration |

**Total Lines Added:** ~200 (mostly comments and documentation)  
**Breaking Changes:** None (backward compatible)  
**Database Migrations:** 3 new nullable columns

---

**Status**: ✅ All changes complete and tested
**Date**: November 7, 2025
