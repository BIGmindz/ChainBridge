# ChainPay Service - Settlement with Risk-Based Conditional Logic

## Overview

ChainPay is a payment settlement service that consumes **FreightTokens** from ChainFreight and implements **risk-based conditional settlement logic**. It bridges tokenized freight assets with intelligent payment workflows.

**Key Features:**
- Risk-aware payment intents tied to freight tokens
- Conditional settlement delays based on risk tier
- Automatic decision logic: LOW=immediate, MEDIUM=24h, HIGH=manual review
- Complete audit logging of all settlement decisions
- Integration with ChainFreight risk scoring (ChainIQ)

---

## Architecture

### Service Integration

```text
┌─────────────────────────────────┐
│   ChainPay Service (8003)       │
│                                 │
│  POST /payment_intents          │
│  POST /payment_intents/{}/settle│
│  GET  /payment_intents/{}       │
└──────────────┬──────────────────┘
               │
               │ Fetches token details
               ├─ status
               ├─ risk_score
               ├─ risk_category
               │
               ▼
┌─────────────────────────────────┐
│   ChainFreight Service (8002)   │
│                                 │
│  GET  /tokens/{id}              │
│  (Includes ChainIQ risk scores) │
└─────────────────────────────────┘
```

### Risk-Based Settlement Flow

``` text
CREATE PAYMENT INTENT
  ↓
Fetch freight token from ChainFreight
  ↓
Extract risk_score and risk_category
  ↓
Map to Settlement Tier:
  LOW (0.0-0.33)    → Immediate approval
  MEDIUM (0.33-0.67)  → 24-hour delay + auto-approval
  HIGH (0.67-1.0)    → Requires manual force_approval
  ↓
SETTLE PAYMENT
  ↓
Apply conditional logic based on tier
  ↓
Return settlement decision + timing
```

---

## Database Schema

### PaymentIntent Table

```sql
CREATE TABLE payment_intents (
    id INTEGER PRIMARY KEY,
    freight_token_id INTEGER NOT NULL,
    amount FLOAT NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    description VARCHAR(255),

    -- Risk information (cached)
    risk_score FLOAT,
    risk_category VARCHAR(20),
    risk_tier ENUM (low, medium, high),

    -- Settlement status
    status ENUM (pending, approved, settled, delayed, rejected, cancelled),

    -- Settlement timing
    settlement_approved_at DATETIME,
    settlement_delayed_until DATETIME,
    settlement_completed_at DATETIME,

    -- Notes
    settlement_reason TEXT,
    settlement_notes TEXT,

    -- Audit
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE settlement_logs (
    id INTEGER PRIMARY KEY,
    payment_intent_id INTEGER NOT NULL,
    action VARCHAR(50),
    reason VARCHAR(255),
    triggered_by VARCHAR(50),
    approved_by VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Risk Tiers & Settlement Logic

### Risk Tier Mapping

| Risk Category | Score | Tier | Settlement | Delay |
|---------------|-------|------|-----------|-------|
| LOW | 0.0-0.33 | LOW | Immediate | None |
| MEDIUM | 0.33-0.67 | MEDIUM | Delayed | 24 hours |
| HIGH | 0.67-1.0 | HIGH | Manual | ∞ (requires override) |

### Settlement Logic by Tier

#### LOW Risk (Immediate)

```python
# Condition: risk_score < 0.33
# Action: APPROVE immediately
# Settlement: Can proceed to SETTLED status immediately

{
  "status": "approved",
  "action_taken": "approved",
  "settlement_reason": "Low risk token - immediate approval",
  "settlement_approved_at": "2025-11-07T10:30:00Z"
}
```

#### MEDIUM Risk (Delayed)

```python
# Condition: 0.33 <= risk_score < 0.67
# Action 1: Set DELAYED status with 24-hour window
# Action 2: After 24 hours: Auto-transition to APPROVED

# Initial response:
{
  "status": "delayed",
  "action_taken": "delayed",
  "settlement_reason": "Medium risk - settlement delayed until 2025-11-08T10:30:00Z",
  "settlement_delayed_until": "2025-11-08T10:30:00Z"
}

# After 24 hours (retry settle):
{
  "status": "approved",
  "action_taken": "approved",
  "settlement_reason": "Medium risk - 24h delay period completed",
  "settlement_approved_at": "2025-11-08T10:30:00Z"
}
```

#### HIGH Risk (Manual Review)

```python
# Condition: risk_score >= 0.67
# Action: REJECT unless force_approval=True
# Settlement: Requires explicit manual override

# Without override:
{
  "status": "rejected",
  "action_taken": "rejected",
  "settlement_reason": "High risk token - requires manual review and force_approval flag"
}

# With force_approval override:
{
  "status": "approved",
  "action_taken": "approved",
  "settlement_reason": "High risk - manual override approved",
  "settlement_approved_at": "2025-11-07T10:30:00Z"
}
```

---

## API Endpoints

### Create Payment Intent

**Endpoint:** `POST /payment_intents`

**Request:**
```json
{
  "freight_token_id": 1,
  "amount": 100000.00,
  "currency": "USD",
  "description": "Payment for shipment LA→CHI"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "freight_token_id": 1,
  "amount": 100000.00,
  "currency": "USD",
  "description": "Payment for shipment LA→CHI",
  "risk_score": 0.35,
  "risk_category": "low",
  "risk_tier": "low",
  "status": "pending",
  "settlement_approved_at": null,
  "settlement_delayed_until": null,
  "settlement_completed_at": null,
  "settlement_reason": null,
  "settlement_notes": null,
  "created_at": "2025-11-07T10:25:00Z",
  "updated_at": "2025-11-07T10:25:00Z"
}
```

**Error Cases:**
- `404` - Freight token not found or ChainFreight unavailable
- `400` - Token status not eligible (must be "active" or "locked")

---

### Assess Risk

**Endpoint:** `POST /payment_intents/{id}/assess_risk`

**Purpose:** View risk assessment without settling

**Response (200 OK):**
```json
{
  "payment_intent_id": 1,
  "freight_token_id": 1,
  "risk_score": 0.35,
  "risk_category": "low",
  "risk_tier": "low",
  "settlement_delay": "immediate",
  "recommended_action": "APPROVE_IMMEDIATELY - Low risk token",
  "created_at": "2025-11-07T10:25:00Z"
}
```

---

### Settle Payment

**Endpoint:** `POST /payment_intents/{id}/settle`

**Request:**
```json
{
  "settlement_notes": "Approved by finance team",
  "force_approval": false
}
```

**Response (200 OK):**
```json
{
  "payment_intent_id": 1,
  "status": "approved",
  "action_taken": "approved",
  "settlement_approved_at": "2025-11-07T10:30:00Z",
  "settlement_delayed_until": null,
  "settlement_reason": "Low risk token - immediate approval",
  "risk_factors": null
}
```

**Key Logic:**
- LOW risk → `"status": "approved"`
- MEDIUM risk → `"status": "delayed"` with 24-hour window
- HIGH risk → `"status": "rejected"` (unless `force_approval: true`)

---

### Complete Settlement

**Endpoint:** `POST /payment_intents/{id}/complete`

**Purpose:** Mark payment as settled after funds transferred

**Response (200 OK):**
```json
{
  "id": 1,
  "freight_token_id": 1,
  "amount": 100000.00,
  "status": "settled",
  "settlement_completed_at": "2025-11-07T10:35:00Z",
  ...
}
```

**Requirements:**
- Payment must be in `"approved"` status
- Transitions to `"settled"` status

---

### List Payment Intents

**Endpoint:** `GET /payment_intents?skip=0&limit=10&status=pending&risk_tier=medium`

**Query Parameters:**
- `skip` - Pagination offset (default: 0)
- `limit` - Maximum records (default: 10, max: 100)
- `status` - Filter by status (pending, approved, settled, delayed, rejected)
- `risk_tier` - Filter by risk tier (low, medium, high)

**Response (200 OK):**
```json
{
  "total": 42,
  "payment_intents": [
    {
      "id": 1,
      "freight_token_id": 1,
      ...
    },
    ...
  ]
}
```

---

### Get Single Payment Intent

**Endpoint:** `GET /payment_intents/{id}`

**Response (200 OK):**
```json
{
  "id": 1,
  "freight_token_id": 1,
  "amount": 100000.00,
  ...
}
```

---

### Get Settlement History

**Endpoint:** `GET /payment_intents/{id}/history`

**Purpose:** View audit log of all settlement decisions

**Response (200 OK):**
```json
{
  "payment_intent_id": 1,
  "total_actions": 2,
  "logs": [
    {
      "id": 1,
      "payment_intent_id": 1,
      "action": "delayed",
      "reason": "Medium risk - settlement delayed until 2025-11-08T10:30:00Z",
      "triggered_by": "system",
      "approved_by": null,
      "created_at": "2025-11-07T10:30:00Z"
    },
    {
      "id": 2,
      "payment_intent_id": 1,
      "action": "approved",
      "reason": "Medium risk - 24h delay period completed",
      "triggered_by": "system",
      "approved_by": null,
      "created_at": "2025-11-08T10:30:00Z"
    }
  ]
}
```

---

## Testing Workflow

### Setup

```bash
# Terminal 1: ChainIQ (port 8001)
cd chainiq-service
python -m uvicorn app.main:app --port 8001 --reload

# Terminal 2: ChainFreight (port 8002)
cd chainfreight-service
python -m uvicorn app.main:app --port 8002 --reload

# Terminal 3: ChainPay (port 8003)
cd chainpay-service
python -m uvicorn app.main:app --port 8003 --reload
```

### Test Scenario 1: LOW Risk (Immediate Approval)

```bash
# 1. Create shipment in ChainFreight
SHIP=$(curl -s -X POST http://localhost:8002/shipments \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name":"Low Risk Shipper",
    "origin":"LA",
    "destination":"CHI",
    "cargo_value":100000
  }' | jq -r '.id')

# 2. Tokenize (gets low risk score from ChainIQ)
TOKEN=$(curl -s -X POST http://localhost:8002/shipments/$SHIP/tokenize \
  -H "Content-Type: application/json" \
  -d '{"face_value":100000,"currency":"USD"}' | jq -r '.id')

# 3. Create payment intent
PAYMENT=$(curl -s -X POST http://localhost:8003/payment_intents \
  -H "Content-Type: application/json" \
  -d '{
    "freight_token_id":'$TOKEN',
    "amount":100000,
    "currency":"USD",
    "description":"Payment for low-risk shipment"
  }' | jq -r '.id')

# 4. Assess risk
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/assess_risk | jq .

# 5. Settle (should approve immediately)
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/settle \
  -H "Content-Type: application/json" \
  -d '{"settlement_notes":"Approved"}' | jq .

# 6. Complete settlement
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/complete | jq '.status'

# Expected: "settled"
```

### Test Scenario 2: MEDIUM Risk (24-Hour Delay)

```bash
# Same as above, but token gets medium risk score
# When settling:

# First call - should delay
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/settle \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.action_taken'
# Result: "delayed"

# Wait 24 hours (or manually advance time in tests)
# Then settle again:

curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/settle \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.action_taken'
# Result: "approved"

# Complete settlement
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/complete | jq '.status'
# Result: "settled"
```

### Test Scenario 3: HIGH Risk (Manual Review)

```bash
# Token gets high risk score
# When settling without override:

curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/settle \
  -H "Content-Type: application/json" \
  -d '{"force_approval":false}' | jq '.action_taken'
# Result: "rejected"

# With manual override:
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/settle \
  -H "Content-Type: application/json" \
  -d '{"force_approval":true}' | jq '.action_taken'
# Result: "approved"

# Complete settlement
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/complete | jq '.status'
# Result: "settled"
```

---

## Error Handling

### Freight Token Not Found

```json
{
  "detail": "Freight token 999 not found or unreachable"
}
```
**HTTP Status:** 404

### Token Not Eligible for Settlement

```json
{
  "detail": "Token status 'cancelled' not eligible for settlement"
}
```
**HTTP Status:** 400

### Payment Already Settled

```json
{
  "detail": "Payment already settled"
}
```
**HTTP Status:** 400

### Payment Not in Appropriate Status

```json
{
  "detail": "Payment must be in APPROVED status, currently pending"
}
```
**HTTP Status:** 400

---

## Configuration

### ChainFreight Service URL

Edit `app/chainfreight_client.py`:

```python
CHAINFREIGHT_URL = "http://localhost:8002"  # Change for your environment
```

Or use environment variable:

```python
import os
CHAINFREIGHT_URL = os.getenv("CHAINFREIGHT_URL", "http://localhost:8002")
```

### Database URL

Default: `sqlite:///./chainpay.db`

Override via environment:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/chainpay"
```

---

## Deployment Checklist

- [ ] ChainFreight service is running and accessible
- [ ] Verify ChainFreight has freight tokens with risk scores
- [ ] Configure CHAINFREIGHT_URL environment variable
- [ ] Run database migrations
- [ ] Test all 3 risk scenarios locally
- [ ] Monitor ChainFreight fetch failures in logs
- [ ] Set up alerting for high-risk forced approvals
- [ ] Configure PostgreSQL for production
- [ ] Enable HTTPS between services
- [ ] Set up payment settlement webhook (future)

---

## Future Enhancements

1. **Webhook Notifications** - Alert when settlement decisions made
2. **Custom Risk Rules** - Allow per-shipper risk thresholds
3. **Payment Processing** - Integrate with Stripe/ACH for actual transfers
4. **Settlement Batching** - Batch settle multiple payments
5. **Risk Override Audit** - Enhanced tracking of manual overrides
6. **Scheduled Auto-Approval** - Cron job to auto-approve delayed payments
7. **Dashboard** - Visualization of payment statuses by risk tier
8. **API Rate Limiting** - Prevent abuse of settlement endpoints

---

**Status:** ✅ Production Ready
**Date:** November 7, 2025
