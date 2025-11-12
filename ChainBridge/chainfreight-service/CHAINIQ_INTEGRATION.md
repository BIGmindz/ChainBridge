# ChainFreight + ChainIQ Integration Guide

## Overview

The ChainFreight service now automatically integrates with the ChainIQ ML scoring engine when shipments are tokenized. This enables risk-based pricing and automated decision-making at token creation time.

## Architecture

```text
┌─────────────────────────────┐
│   ChainFreight Service      │
│  (Port 8002)                │
│                             │
│  POST /shipments/{id}/tokenize
│         │                   │
│         ├─► ChainIQ Client  │
│         │   (chainiq_client)│
│         │                   │
└─────────┼───────────────────┘
          │
          │ HTTP POST
          ├─────────────────────────────┐
          │                             │
          ▼                             │
┌─────────────────────────────┐        │
│   ChainIQ Service           │◀───────┘
│  (Port 8001)                │
│  /score/shipment            │
│                             │
│  Returns:                   │
│  - risk_score (0.0-1.0)    │
│  - risk_category           │
│  - reasoning               │
└─────────────────────────────┘
```

## Data Flow

### Tokenization with Risk Scoring

```python
# 1. Client creates shipment
POST /shipments {
    "shipper_name": "Global Logistics",
    "origin": "Los Angeles, CA",
    "destination": "Chicago, IL",
    "cargo_value": 100000.00
}
# Returns shipment_id = 1

# 2. Client tokenizes shipment
POST /shipments/1/tokenize {
    "face_value": 100000.00,
    "currency": "USD"
}

# Behind the scenes:
# - ChainFreight looks up shipment details (origin, destination, dates)
# - ChainFreight calls ChainIQ: POST /score/shipment
# - ChainIQ returns risk_score, risk_category, reasoning
# - ChainFreight generates recommended_action based on risk
# - ChainFreight creates token with all risk fields populated

# 3. Token returned with risk scoring
{
    "id": 1,
    "shipment_id": 1,
    "face_value": 100000.00,
    "currency": "USD",
    "status": "created",
    "risk_score": 0.35,           # ◄─ From ChainIQ
    "risk_category": "low",        # ◄─ From ChainIQ
    "recommended_action": "APPROVE - Low risk, suitable for standard financing",
    "created_at": "2025-11-07T10:30:00",
    "updated_at": "2025-11-07T10:30:00"
}
```

## Database Schema Changes

### FreightToken Model - New Fields

```python
class FreightToken(Base):
    __tablename__ = "freight_tokens"
    
    # ... existing fields ...
    
    # NEW: Risk scoring from ChainIQ
    risk_score = Column(Float, nullable=True)       # 0.0-1.0
    risk_category = Column(String, nullable=True)   # "low", "medium", "high"
    recommended_action = Column(String, nullable=True)
```

### Migration

If you have existing freight_tokens table, add the new columns:

```sql
ALTER TABLE freight_tokens ADD COLUMN risk_score FLOAT;
ALTER TABLE freight_tokens ADD COLUMN risk_category VARCHAR(50);
ALTER TABLE freight_tokens ADD COLUMN recommended_action VARCHAR(255);
```

## ChainIQ Client Module

**File:** `chainfreight-service/app/chainiq_client.py`

### Key Functions

#### `score_shipment()`
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
    
    Returns:
        Tuple of (risk_score, risk_category, recommended_action) or None if fails
    """
```

**Features:**
- Async HTTP client (httpx) for non-blocking calls
- Timeout handling (10 second default)
- Graceful degradation if ChainIQ unavailable
- Automatic recommended_action generation based on risk

#### `generate_recommended_action()`
```python
def generate_recommended_action(risk_category: str, risk_score: float) -> str:
    """
    Generate business rules-based recommendations.
    
    Examples:
    - LOW:    "APPROVE - Low risk, suitable for standard financing"
    - MEDIUM: "REVIEW - Consider additional risk mitigation"
    - HIGH:   "REJECT - High risk, recommend against tokenization"
    """
```

## Integration Details

### Error Handling

**Scenario: ChainIQ Service Unavailable**

If the ChainIQ service cannot be reached:

```python
# Tokenization STILL SUCCEEDS with null risk fields
{
    "id": 1,
    "shipment_id": 1,
    "face_value": 100000.00,
    "currency": "USD",
    "status": "created",
    "risk_score": null,
    "risk_category": null,
    "recommended_action": null,
    "created_at": "2025-11-07T10:30:00",
    "updated_at": "2025-11-07T10:30:00"
}

# Warning logged:
# "ChainIQ service unavailable while scoring shipment 1. 
#  Proceeding with token creation without risk scoring."
```

**Why This Matters:**
- System is resilient to external service failures
- Users aren't blocked from creating tokens
- Risk fields can be populated later via batch scoring

### Timeouts

Default timeout is 10 seconds for ChainIQ calls:

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(SCORE_ENDPOINT, json=request_body.model_dump())
```

If ChainIQ takes longer than 10 seconds, tokenization proceeds without scoring.

### Configuration

**Update the ChainIQ endpoint URL:**

```python
# In chainiq_client.py
CHAINIQ_URL = "http://localhost:8001"  # Change this
SCORE_ENDPOINT = f"{CHAINIQ_URL}/score/shipment"
```

For production, use environment variables:

```python
import os
CHAINIQ_URL = os.getenv("CHAINIQ_URL", "http://localhost:8001")
```

## Testing Integration

### Test Locally

#### 1. Start ChainIQ Service

```bash
cd chainiq-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

#### 2. Start ChainFreight Service

```bash
cd chainfreight-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

#### 3. Create Shipment

```bash
curl -X POST "http://localhost:8002/shipments" \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name": "Global Logistics",
    "origin": "Los Angeles, CA",
    "destination": "Chicago, IL",
    "cargo_value": 100000.00,
    "pickup_eta": "2025-11-08T08:00:00",
    "delivery_eta": "2025-11-14T18:00:00"
  }'
```

Response:
```json
{
  "id": 1,
  "shipper_name": "Global Logistics",
  "origin": "Los Angeles, CA",
  "destination": "Chicago, IL",
  "cargo_value": 100000.00,
  "status": "pending",
  "created_at": "2025-11-07T10:25:00",
  "updated_at": "2025-11-07T10:25:00"
}
```

#### 4. Tokenize with Risk Scoring

```bash
curl -X POST "http://localhost:8002/shipments/1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{
    "face_value": 100000.00,
    "currency": "USD"
  }'
```

Response (with risk scoring):
```json
{
  "id": 1,
  "shipment_id": 1,
  "face_value": 100000.00,
  "currency": "USD",
  "status": "created",
  "risk_score": 0.35,
  "risk_category": "low",
  "recommended_action": "APPROVE - Low risk, suitable for standard financing",
  "token_address": null,
  "created_at": "2025-11-07T10:30:00",
  "updated_at": "2025-11-07T10:30:00"
}
```

#### 5. Verify Risk Fields Persisted

```bash
curl "http://localhost:8002/tokens/1"
```

Risk fields should be present and identical to creation response.

### Test Error Scenarios

#### ChainIQ Service Stopped

1. Stop the ChainIQ service
2. Try to tokenize a new shipment
3. Should succeed with null risk fields
4. Check logs for warning message

#### Network Timeout

Add artificial delay to ChainIQ endpoint and observe graceful fallback.

## Recommended Actions Reference

The `recommended_action` field is populated automatically based on risk scoring:

| Risk Category | Score Range | Recommendation |
|---------------|-------------|-----------------|
| LOW | 0.0-0.33 | APPROVE - Standard financing |
| MEDIUM | 0.33-0.5 | APPROVE_WITH_CONDITIONS - Monitor/collateral |
| MEDIUM | 0.5-0.67 | REVIEW - Risk mitigation needed |
| HIGH | 0.67-0.85 | REVIEW_URGENTLY - Detailed assessment |
| HIGH | 0.85-1.0 | REJECT - Advise against tokenization |

## Production Checklist

Before deploying to production:

- [ ] Configure ChainIQ service URL in environment
- [ ] Test ChainIQ service is reachable from ChainFreight
- [ ] Configure appropriate timeout (default 10s)
- [ ] Update database migration (add risk_score, risk_category, recommended_action columns)
- [ ] Test error handling with ChainIQ service down
- [ ] Monitor logs for scoring errors
- [ ] Set up alerting if ChainIQ scoring fails consistently
- [ ] Document risk categories and thresholds for your business
- [ ] Validate recommended_action rules match business requirements

## Future Enhancements

1. **Batch Scoring**: Score multiple shipments at once
2. **Async Job Queue**: Use Celery for long-running scoring
3. **Scoring Cache**: Cache risk scores for repeated shipment patterns
4. **Custom Risk Models**: Support different risk models per shipper
5. **Webhook Notifications**: Notify on high-risk tokens
6. **Risk Dashboard**: Visualization of token risk distribution
7. **Dynamic Pricing**: Use risk_score to automatically adjust token pricing
8. **On-Chain Integration**: Include risk_score in on-chain token metadata

## Troubleshooting

### ChainIQ Calls Always Fail

Check logs for error messages:
```python
# In chainiq_client.py - look for these log messages
logger.warning("ChainIQ service timeout...")
logger.warning("ChainIQ service unavailable...")
logger.error("Error calling ChainIQ service...")
```

**Solutions:**
- Verify ChainIQ service is running: `curl http://localhost:8001/health`
- Check firewall allows port 8001
- Verify network connectivity between services
- Check ChainIQ service logs for errors

### Risk Fields Are Always Null

1. Is ChainIQ service running?
2. Can ChainFreight reach it? Test with curl
3. Check logs for timeout or connection errors
4. Verify CHAINIQ_URL is correct in chainiq_client.py

### Tokenization is Slow

ChainIQ scoring adds latency. Current flow is synchronous (blocks tokenization).

**Future optimization:** Use job queue (Celery) for async scoring.

---

**Status**: ✅ Integration complete and tested
**Date**: November 7, 2025
**Last Updated**: November 7, 2025
