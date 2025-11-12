# ChainPay Service - Quick Reference Guide

## What It Does

ChainPay is a **payment settlement service** that:

1. Consumes **FreightTokens** from ChainFreight (with risk scores from ChainIQ)
2. Creates **payment intents** tied to tokenized shipments
3. Implements **risk-based conditional settlement logic**:
   - **LOW risk** (0.0-0.33): Approve immediately
   - **MEDIUM risk** (0.33-0.67): Delay 24 hours, then auto-approve
   - **HIGH risk** (0.67-1.0): Require manual override (`force_approval: true`)

---

## Quick Start

### Start Services

```bash
# Terminal 1: ChainIQ (port 8001)
cd chainiq-service
python -m uvicorn app.main:app --port 8001

# Terminal 2: ChainFreight (port 8002)
cd chainfreight-service
python -m uvicorn app.main:app --port 8002

# Terminal 3: ChainPay (port 8003)
cd chainpay-service
python -m uvicorn app.main:app --port 8003
```

### Test Workflow (Low Risk)

```bash
# 1. Create shipment
SHIP=$(curl -s -X POST http://localhost:8002/shipments \
  -d '{"shipper_name":"Test","origin":"LA","destination":"CHI","cargo_value":100000}' | jq -r '.id')

# 2. Tokenize (gets risk score from ChainIQ)
TOKEN=$(curl -s -X POST http://localhost:8002/shipments/$SHIP/tokenize \
  -d '{"face_value":100000,"currency":"USD"}' | jq -r '.id')

# 3. Create payment intent
PAYMENT=$(curl -s -X POST http://localhost:8003/payment_intents \
  -d '{"freight_token_id":'$TOKEN',"amount":100000}' | jq -r '.id')

# 4. Settle (auto-approves for low risk)
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/settle | jq .

# 5. Complete
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/complete | jq '.status'
```

---

## API Reference

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/payment_intents` | Create payment intent |
| GET | `/payment_intents` | List all payment intents |
| GET | `/payment_intents/{id}` | Get single payment intent |
| POST | `/payment_intents/{id}/assess_risk` | View risk assessment |
| POST | `/payment_intents/{id}/settle` | Settle payment (with conditional logic) |
| POST | `/payment_intents/{id}/complete` | Mark as settled after transfer |
| GET | `/payment_intents/{id}/history` | View settlement audit log |

---

## Core Workflow

### 1. Create Payment Intent

```bash
curl -X POST http://localhost:8003/payment_intents \
  -H "Content-Type: application/json" \
  -d '{
    "freight_token_id": 1,
    "amount": 100000.00,
    "currency": "USD",
    "description": "Payment for shipment"
  }'
```

**Response:**

```json
{
  "id": 1,
  "freight_token_id": 1,
  "amount": 100000.00,
  "status": "pending",
  "risk_tier": "low",
  "risk_score": 0.35
}
```

### 2. Assess Risk (Optional)

```bash
curl -X POST http://localhost:8003/payment_intents/1/assess_risk
```

**Response:**

```json
{
  "payment_intent_id": 1,
  "risk_tier": "low",
  "settlement_delay": "immediate",
  "recommended_action": "APPROVE_IMMEDIATELY - Low risk token"
}
```

### 3. Settle Payment

```bash
curl -X POST http://localhost:8003/payment_intents/1/settle \
  -d '{"settlement_notes": "Approved"}'
```

**Response - LOW Risk (Approved):**

```json
{
  "status": "approved",
  "action_taken": "approved",
  "settlement_reason": "Low risk token - immediate approval"
}
```

**Response - MEDIUM Risk (Delayed):**

```json
{
  "status": "delayed",
  "action_taken": "delayed",
  "settlement_delayed_until": "2025-11-08T10:30:00Z",
  "settlement_reason": "Medium risk - settlement delayed until 2025-11-08T10:30:00Z"
}
```

**Response - HIGH Risk (Requires Override):**

```json
{
  "status": "rejected",
  "action_taken": "rejected",
  "settlement_reason": "High risk token - requires manual review and force_approval flag"
}
```

### 4. Force Approve (HIGH Risk Only)

```bash
curl -X POST http://localhost:8003/payment_intents/1/settle \
  -d '{"force_approval": true}'
```

**Response:**

```json
{
  "status": "approved",
  "action_taken": "approved",
  "settlement_reason": "High risk - manual override approved"
}
```

### 5. Complete Settlement

```bash
curl -X POST http://localhost:8003/payment_intents/1/complete
```

**Response:**

```json
{
  "id": 1,
  "status": "settled",
  "settlement_completed_at": "2025-11-07T10:35:00Z"
}
```

---

## Risk Tier Decision Logic

### LOW Risk (0.0-0.33)

- **When:** `risk_score < 0.33`
- **Action:** Approve immediately
- **Settlement:** Instant
- **Use Case:** Established carriers, domestic routes, low-value shipments

### MEDIUM Risk (0.33-0.67)

- **When:** `0.33 <= risk_score < 0.67`
- **Action 1:** Delay 24 hours
- **Action 2:** Auto-approve after delay
- **Settlement:** 24-hour window then instant
- **Use Case:** International routes, new shippers, borderline-value shipments

### HIGH Risk (0.67-1.0)

- **When:** `risk_score >= 0.67`
- **Action:** Reject unless manually overridden
- **Settlement:** Requires `force_approval: true` flag
- **Use Case:** First-time shippers, high-value cargo, unusual routes

---

## Database Models

### PaymentIntent

```python
class PaymentIntent:
    id: int                          # Primary key
    freight_token_id: int            # Reference to ChainFreight token
    amount: float                    # Payment amount
    currency: str                    # Currency code (USD, EUR, etc)
    
    # Risk data (cached from token)
    risk_score: float                # 0.0-1.0 from ChainIQ
    risk_category: str               # low, medium, high
    risk_tier: RiskTier              # Mapped tier for settlement
    
    # Status tracking
    status: PaymentStatus            # pending, approved, delayed, settled, rejected
    settlement_approved_at: datetime  # When approved
    settlement_delayed_until: datetime # When 24h delay expires
    settlement_completed_at: datetime # When settled
    
    settlement_reason: str           # Why decision was made
    settlement_notes: str            # Additional notes
```

### SettlementLog

```python
class SettlementLog:
    id: int                    # Primary key
    payment_intent_id: int     # Which payment
    action: str                # delayed, approved, rejected, settled
    reason: str                # Why this action was taken
    triggered_by: str          # "system" or user name
    approved_by: str           # Who approved manual override
    created_at: datetime       # When action occurred
```

---

## Error Responses

| Error | Status | Meaning |
|-------|--------|---------|
| Freight token not found | 404 | Token doesn't exist in ChainFreight |
| Token status not eligible | 400 | Token must be "active" or "locked" |
| Payment already settled | 400 | Can't modify completed payment |
| Must be in APPROVED status | 400 | Only APPROVED can transition to SETTLED |

---

## Status Flow

``` text
      pending (initial)
        ↓
    [settle]
        ↓
    ├─→ approved (LOW risk or MEDIUM after delay)
    │       ↓
    │   [complete]
    │       ↓
    │   settled ✓
    │
    ├─→ delayed (MEDIUM risk initially)
    │       ↓
    │    [wait 24h + settle]
    │       ↓
    │   approved → settled ✓
    │
    └─→ rejected (HIGH risk without override)
            ↓
        [settle with force_approval]
            ↓
        approved → settled ✓
```

---

## Configuration

### Environment Variables

```bash
# ChainFreight service location
export CHAINFREIGHT_URL="http://localhost:8002"

# Database
export DATABASE_URL="sqlite:///./chainpay.db"
# or PostgreSQL:
export DATABASE_URL="postgresql://user:password@localhost/chainpay"
```

### Files

- `app/models.py` - Database schemas
- `app/schemas.py` - Request/response validation
- `app/chainfreight_client.py` - ChainFreight integration
- `app/main.py` - API endpoints

---

## Monitoring

### Log Messages

```python
# Successful creation
"Payment intent 1 created for token 1: amount=100000, risk_tier=low"

# Settlement decisions
"Payment 1 settlement action: approved (risk_tier=low, reason=...)"
"Payment 1 settlement action: delayed (risk_tier=medium, reason=...)"
"Payment 1 settlement action: rejected (risk_tier=high, reason=...)"

# Overrides
"High-risk payment 1 force-approved for token 1"
```

### Queries

```bash
# Get all pending payments
curl "http://localhost:8003/payment_intents?status=pending"

# Get all high-risk payments
curl "http://localhost:8003/payment_intents?risk_tier=high"

# Get payment with full history
curl "http://localhost:8003/payment_intents/1/history"
```

---

## Files & Structure

``` text
chainpay-service/
├── app/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy models
│   ├── schemas.py             # Pydantic schemas
│   ├── database.py            # Session management
│   ├── chainfreight_client.py # ChainFreight integration
│   └── main.py                # FastAPI app & endpoints
├── requirements.txt           # Dependencies
└── README.md                  # Full documentation
```

---

## Testing Checklist

- [ ] All 3 services running (ChainIQ, ChainFreight, ChainPay)
- [ ] Create payment intent for low-risk token
- [ ] Verify immediate approval
- [ ] Create payment intent for medium-risk token
- [ ] Verify 24-hour delay
- [ ] Wait 24 hours (or test with dates) and retry settle
- [ ] Verify auto-approval after delay
- [ ] Create payment intent for high-risk token
- [ ] Verify rejection without override
- [ ] Use force_approval flag
- [ ] Verify manual approval works
- [ ] Check settlement history/audit logs
- [ ] Verify complete() transitions to settled

---

## Next Steps

1. Run tests locally using workflow above
2. Verify database migrations in production environment
3. Configure ChainFreight service URL
4. Set up PostgreSQL for production
5. Deploy to staging environment
6. Test with real payment data
7. Set up webhook notifications (future)
8. Integrate with payment processor (future)

---

**Status:** ✅ Ready to Use  
**Date:** November 7, 2025  
**Port:** 8003
