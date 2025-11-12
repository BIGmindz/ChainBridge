# ChainFreight + ChainIQ Integration - Complete Example

## End-to-End Workflow

This document walks through a complete example of tokenizing a shipment with automatic risk scoring.

## Setup

### Prerequisites

Both services must be running:

```bash
# Terminal 1: ChainIQ Service
cd /Users/johnbozza/Documents/Projects/ChainBridge/ChainBridge/chainiq-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: ChainFreight Service  
cd /Users/johnbozza/Documents/Projects/ChainBridge/ChainBridge/chainfreight-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 3: Make API calls
cd /Users/johnbozza/Documents/Projects/ChainBridge/ChainBridge
```

## Example Scenario

**Shipper:** Global Logistics  
**Route:** Los Angeles → Chicago  
**Cargo:** Electronics  
**Value:** $100,000  
**Timeline:** 7 days  

### Step 1: Create Shipment

The shipper creates a new shipment in ChainFreight.

```bash
curl -X POST "http://localhost:8002/shipments" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "shipper_name": "Global Logistics Inc",
    "origin": "Los Angeles, CA",
    "destination": "Chicago, IL",
    "cargo_value": 100000.00,
    "pickup_eta": "2025-11-08T08:00:00",
    "delivery_eta": "2025-11-14T18:00:00"
  }'
```

**Response:**

```json
{
  "id": 1,
  "shipper_name": "Global Logistics Inc",
  "origin": "Los Angeles, CA",
  "destination": "Chicago, IL",
  "cargo_value": 100000.00,
  "pickup_eta": "2025-11-08T08:00:00",
  "delivery_eta": "2025-11-14T18:00:00",
  "status": "pending",
  "created_at": "2025-11-07T10:25:00Z",
  "updated_at": "2025-11-07T10:25:00Z"
}
```

**What happened:**

- Shipment recorded in database
- Status set to "pending"
- Ready for pickup and tokenization

### Step 2: Tokenize Shipment (with Risk Scoring)

Now the shipper wants to finance this shipment by creating a tradeable token.

```bash
curl -X POST "http://localhost:8002/shipments/1/tokenize" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "face_value": 100000.00,
    "currency": "USD"
  }'
```

**Behind the scenes:**

1. ChainFreight validates shipment ID 1 exists ✓
2. ChainFreight calls ChainIQ service:

   ```bash
   POST http://localhost:8001/score/shipment
   {
     "shipment_id": "1",
     "origin": "Los Angeles, CA",
     "destination": "Chicago, IL",
     "planned_delivery_date": "2025-11-14T18:00:00"
   }
   ```

3. ChainIQ analyzes the shipment and returns:

   ```json
   {
     "shipment_id": "1",
     "risk_score": 0.35,
     "risk_category": "low",
     "confidence": 0.85,
     "reasoning": "Domestic LA-CHI route with good track record"
   }
   ```

4. ChainFreight generates recommended_action:
   - Risk category: "low"
   - Risk score: 0.35
   - Decision: "APPROVE - Low risk, suitable for standard financing"

5. Token is created and stored in database

**Response:**

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
  "created_at": "2025-11-07T10:30:00Z",
  "updated_at": "2025-11-07T10:30:00Z"
}
```

**Key fields populated:**

- `risk_score`: 0.35 (LOW risk)
- `risk_category`: "low"
- `recommended_action`: Actionable recommendation for financing decision

### Step 3: Query Token to Review Risk

The shipper can query the token to review risk details and trading parameters.

```bash
curl "http://localhost:8002/tokens/1" \
  -H "Accept: application/json"
```

**Response:**

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
  "created_at": "2025-11-07T10:30:00Z",
  "updated_at": "2025-11-07T10:30:00Z"
}
```

**Business Decision:**

- Risk is LOW
- Recommended action is APPROVE
- Suitable for working capital financing
- Can be offered to investors with standard terms

### Step 4: Shipment Pickup (Status Update)

Once shipment is picked up, the status is updated.

```bash
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "picked_up"
  }'
```

**Response:**

```json
{
  "id": 1,
  "shipper_name": "Global Logistics Inc",
  "origin": "Los Angeles, CA",
  "destination": "Chicago, IL",
  "cargo_value": 100000.00,
  "status": "picked_up",
  "created_at": "2025-11-07T10:25:00Z",
  "updated_at": "2025-11-07T11:00:00Z"
}
```

**Token is unaffected:**

- Token status remains "created"
- Risk score stays 0.35
- Independent from shipment status

### Step 5: Token Transitions Through Lifecycle

As the shipment progresses:

```bash
# Shipment in transit
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_transit"}'

# Shipment delivered
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "delivered"}'
```

**Timeline:**

| Time | Shipment Status | Token Status | Notes |
|------|-----------------|--------------|-------|
| T+0 | pending | created | Token just minted, not yet active |
| T+8h | picked_up | created | Driver has shipment |
| T+6d | in_transit | created | En route to Chicago |
| T+7d | delivered | created | Arrived at destination |

**Future enhancement:** Token status could auto-transition to `REDEEMED` when shipment status becomes `DELIVERED`.

## Scenario: High-Risk Shipment

What if the route or timing was high-risk?

### Create High-Risk Shipment

```bash
curl -X POST "http://localhost:8002/shipments" \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name": "International Logistics",
    "origin": "Port of Shanghai",
    "destination": "Port of Newark",
    "cargo_value": 500000.00,
    "pickup_eta": "2025-11-08T08:00:00",
    "delivery_eta": "2025-12-15T18:00:00"
  }'
```

### Tokenize (High-Risk Result)

```bash
curl -X POST "http://localhost:8002/shipments/2/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"face_value": 500000.00, "currency": "USD"}'
```

**Response (high risk):**

```json
{
  "id": 2,
  "shipment_id": 2,
  "face_value": 500000.00,
  "currency": "USD",
  "status": "created",
  "risk_score": 0.82,
  "risk_category": "high",
  "recommended_action": "REVIEW_URGENTLY - Requires detailed assessment before approval",
  "created_at": "2025-11-07T10:35:00Z",
  "updated_at": "2025-11-07T10:35:00Z"
}
```

**Business Decision:**

- Risk is HIGH (0.82)
- Requires urgent review
- May need additional insurance
- Premium pricing justified
- Higher collateral requirements

## Scenario: ChainIQ Service Unavailable

What if ChainIQ service is down during tokenization?

### Stop ChainIQ Service

```bash
# Ctrl+C in Terminal 1 where ChainIQ is running
```

### Attempt to Tokenize

```bash
curl -X POST "http://localhost:8002/shipments/3/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"face_value": 75000.00, "currency": "USD"}'
```

**Response (degraded mode):**

```json
{
  "id": 3,
  "shipment_id": 3,
  "face_value": 75000.00,
  "currency": "USD",
  "status": "created",
  "risk_score": null,
  "risk_category": null,
  "recommended_action": null,
  "created_at": "2025-11-07T10:40:00Z",
  "updated_at": "2025-11-07T10:40:00Z"
}
```

**What happened:**

- Token created successfully ✓
- ChainIQ call timed out (10s timeout)
- Risk fields set to null
- Warning logged in ChainFreight service
- Tokenization didn't fail

**Business Impact:**

- Shipment can still be financed
- Risk assessment deferred
- Can be scored later when ChainIQ is available

**Log output (ChainFreight):**

``` text
WARNING - ChainIQ service timeout while scoring shipment 3. 
Proceeding with token creation without risk scoring.
```

## API Summary

### Shipment Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /shipments | Create shipment |
| GET | /shipments | List shipments |
| GET | /shipments/{id} | Get shipment |
| PUT | /shipments/{id} | Update shipment |

### Token Endpoints (with ChainIQ Integration)

| Method | Path | Purpose |
|--------|------|---------|
| POST | /shipments/{id}/tokenize | Create token (calls ChainIQ automatically) |
| GET | /shipments/{id}/token | Get token for shipment |
| GET | /tokens | List all tokens |
| GET | /tokens/{id} | Get token by ID |

All token responses include risk fields from ChainIQ scoring.

## Monitoring

### Check ChainFreight Logs

Look for scoring-related messages:

```bash
# Successful scoring
INFO - ChainIQ scoring successful for shipment 1: 
       risk_score=0.35, risk_category=low

# Service unavailable
WARNING - ChainIQ service unavailable while scoring shipment 2. 
          Proceeding with token creation without risk scoring.

# Timeout
WARNING - ChainIQ service timeout while scoring shipment 3. 
          Proceeding with token creation without risk scoring.

# Error
ERROR - Error calling ChainIQ service for shipment 4: 
        Connection refused
```

### Database Inspection

```bash
# Check tokens with scores
sqlite3 chainfreight.db "SELECT id, shipment_id, face_value, risk_score, risk_category, recommended_action FROM freight_tokens LIMIT 5;"

# Tokens without scores (ChainIQ was down)
sqlite3 chainfreight.db "SELECT id, shipment_id FROM freight_tokens WHERE risk_score IS NULL;"
```

## Next Steps

1. **Local Testing**: Follow the workflow above to verify integration
2. **Error Scenarios**: Test with ChainIQ service down
3. **Performance**: Monitor ChainIQ scoring latency
4. **Production Deployment**: Configure service URLs and timeouts
5. **Future**: Async scoring with job queue for non-blocking calls

---

**Status**: ✅ Complete example workflow
**Date**: November 7, 2025
