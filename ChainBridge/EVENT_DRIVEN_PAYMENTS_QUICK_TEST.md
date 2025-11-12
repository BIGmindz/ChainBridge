# Event-Driven Payments: Quick Test Guide

**Status**: ✅ All code complete (7 Python files, 0 errors)  
**Date**: November 7, 2025

---

## Quick Start: 7-Step Workflow

### Prerequisites
```bash
# Terminal 1: Start ChainFreight (port 8002)
cd chainfreight-service
python -m uvicorn app.main:app --port 8002 --reload

# Terminal 2: Start ChainPay (port 8003)
cd chainpay-service
python -m uvicorn app.main:app --port 8003 --reload
```

### 1️⃣ Create a Shipment
```bash
curl -X POST http://localhost:8002/shipments \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name": "FedEx",
    "origin": "San Francisco",
    "destination": "New York",
    "cargo_value": 50000.00,
    "pickup_eta": "2025-11-08T10:00:00Z"
  }'
```

**Expected**: Status 201, returns `Shipment(id=1, status=PENDING)`

---

### 2️⃣ Tokenize the Shipment
```bash
curl -X POST http://localhost:8002/shipments/1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "face_value": 50000.00,
    "currency": "USD"
  }'
```

**Expected**: Status 201, returns:
```json
{
  "id": 1,
  "shipment_id": 1,
  "face_value": 50000.00,
  "status": "active",
  "risk_score": 0.45,
  "risk_category": "medium",
  "currency": "USD"
}
```

📝 **Note**: Risk score is assigned by ChainIQ during tokenization.

---

### 3️⃣ Create Payment Intent in ChainPay
```bash
curl -X POST http://localhost:8003/payment_intents \
  -H "Content-Type: application/json" \
  -d '{
    "freight_token_id": 1,
    "amount": 50000.00,
    "currency": "USD",
    "description": "Payment for shipment 1 (FedEx SF→NY)"
  }'
```

**Expected**: Status 201, returns:
```json
{
  "id": 1,
  "freight_token_id": 1,
  "amount": 50000.00,
  "currency": "USD",
  "risk_tier": "medium",
  "status": "pending",
  "created_at": "2025-11-07T...",
  "updated_at": "2025-11-07T..."
}
```

---

### 4️⃣ Build Payment Schedule
```bash
curl -X POST http://localhost:8003/payment_intents/1/build_schedule
```

**Expected**: Status 200, returns:
```json
{
  "payment_id": 1,
  "schedule_id": 1,
  "risk_tier": "medium",
  "items_count": 3,
  "message": "Payment schedule created successfully"
}
```

✅ **What happened**: Created 3 milestone items:
- PICKUP_CONFIRMED: 10% ($5,000)
- POD_CONFIRMED: 70% ($35,000)
- CLAIM_WINDOW_CLOSED: 20% ($10,000)

---

### 5️⃣ Record First Shipment Event (Pickup)
```bash
curl -X POST http://localhost:8002/shipments/1/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "PICKUP_CONFIRMED",
    "occurred_at": "2025-11-08T10:30:00Z",
    "metadata": "driver_id: 12345, vehicle_id: V-8899"
  }'
```

**Expected**: Status 201, returns:
```json
{
  "id": 1,
  "shipment_id": 1,
  "event_type": "PICKUP_CONFIRMED",
  "occurred_at": "2025-11-08T10:30:00Z",
  "metadata": "driver_id: 12345, vehicle_id: V-8899",
  "recorded_at": "2025-11-07T...",
  "webhook_sent": 1,
  "webhook_sent_at": "2025-11-07T..."
}
```

🔄 **Behind the scenes**:
- ChainFreight recorded the event in DB
- ChainFreight called ChainPay webhook
- ChainPay created MilestoneSettlement:
  - `payment_intent_id=1`
  - `event_type="PICKUP_CONFIRMED"`
  - `settlement_amount=5000.00`
  - `status="pending"`

---

### 6️⃣ Record Second Event (Proof of Delivery)
```bash
curl -X POST http://localhost:8002/shipments/1/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "POD_CONFIRMED",
    "occurred_at": "2025-11-09T14:45:00Z",
    "metadata": "signature_hash: 0x7f9e8a..., recipient: John Smith"
  }'
```

**Expected**: Status 201, `webhook_sent=1`

🔄 **Behind the scenes**:
- ChainPay creates 2nd MilestoneSettlement:
  - `event_type="POD_CONFIRMED"`
  - `settlement_amount=35000.00`

---

### 7️⃣ Query Payment History
```bash
curl http://localhost:8003/payment_intents/1/history
```

**Expected**: Status 200, returns:
```json
{
  "payment_intent_id": 1,
  "logs": [
    {
      "id": 1,
      "payment_intent_id": 1,
      "action": "approved",
      "reason": "Low-risk settlement",
      "triggered_by": "system",
      "created_at": "2025-11-07T..."
    }
  ],
  "total_actions": 1
}
```

---

## ✅ Verification Checklist

### Database Records Created
- [ ] `shipments` table has 1 record (FedEx SF→NY)
- [ ] `freight_tokens` table has 1 record (MEDIUM risk)
- [ ] `payment_intents` table has 1 record
- [ ] `payment_schedules` table has 1 record
- [ ] `payment_schedule_items` table has 3 records (10%, 70%, 20%)
- [ ] `shipment_events` table has 2 records (PICKUP_CONFIRMED, POD_CONFIRMED)
- [ ] `milestone_settlements` table has 2 records ($5k, $35k)

### API Responses
- [ ] All endpoints return expected status codes
- [ ] Risk tier correctly determined from risk_score
- [ ] Milestone amounts calculated correctly (total * percentage)
- [ ] Unique constraint prevents duplicate milestones

---

## 🧪 Additional Test Cases

### Test: Idempotency (No Double-Payment)
```bash
# Call the same event twice
curl -X POST http://localhost:8002/shipments/1/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "POD_CONFIRMED",
    "occurred_at": "2025-11-09T14:45:00Z",
    "metadata": "signature_hash: 0x7f9e8a..., recipient: John Smith"
  }'

# (Call again with same data)
curl -X POST http://localhost:8002/shipments/1/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "POD_CONFIRMED",
    "occurred_at": "2025-11-09T14:45:00Z",
    "metadata": "signature_hash: 0x7f9e8a..., recipient: John Smith"
  }'
```

✅ **Expected**: 
- First call: Status 201, MilestoneSettlement created
- Second call: Status 201, No new MilestoneSettlement (unique constraint prevents duplicate)

---

### Test: List Events
```bash
curl http://localhost:8002/shipments/1/events
```

✅ **Expected**:
```json
{
  "total": 2,
  "events": [
    { "event_type": "POD_CONFIRMED", "occurred_at": "...", ... },
    { "event_type": "PICKUP_CONFIRMED", "occurred_at": "...", ... }
  ]
}
```

---

### Test: Different Risk Tiers
**Repeat workflow with different shipments**:

#### LOW-risk shipment (low fraud risk)
```bash
# Shipment 2: risk_score = 0.15 → LOW
# Schedule: 20% / 70% / 10%
```

#### HIGH-risk shipment (high fraud risk)
```bash
# Shipment 3: risk_score = 0.85 → HIGH
# Schedule: 0% / 80% / 20%
```

---

## 📊 Expected Data Flow

``` text
Shipment 1 (FedEx SF→NY)
  └─ FreightToken 1 (risk=0.45, MEDIUM)
     └─ PaymentIntent 1 ($50k)
        └─ PaymentSchedule 1 (3 milestones)
           ├─ Item: PICKUP_CONFIRMED 10%
           ├─ Item: POD_CONFIRMED 70%
           └─ Item: CLAIM_WINDOW_CLOSED 20%

ShipmentEvent: PICKUP_CONFIRMED
  └─ Triggers webhook to ChainPay
     └─ Creates MilestoneSettlement 1 ($5k, PENDING)

ShipmentEvent: POD_CONFIRMED
  └─ Triggers webhook to ChainPay
     └─ Creates MilestoneSettlement 2 ($35k, PENDING)

ShipmentEvent: CLAIM_WINDOW_CLOSED
  └─ Triggers webhook to ChainPay
     └─ Creates MilestoneSettlement 3 ($10k, PENDING)
```

---

## 🐛 Troubleshooting

### Issue: Webhook not called
- **Check**: ChainFreight can reach ChainPay on `http://localhost:8003`
- **Check**: `CHAINPAY_URL` environment variable set correctly
- **Logs**: Look for "Calling ChainPay webhook" in ChainFreight logs

### Issue: MilestoneSettlement not created
- **Check**: PaymentSchedule exists for payment intent
- **Check**: PaymentScheduleItem exists for event_type
- **Logs**: Look for "No payment schedule" or "No schedule item" messages

### Issue: Amounts don't add up
- **Check**: Schedule percentages sum to 1.0 (tolerance: 1%)
- **Check**: Amount calculation: `payment_intent.amount * schedule_item.percentage`
- **Verify**: Amounts rounded to 2 decimal places

### Issue: Port conflicts
```bash
# Check what's using port 8002/8003
lsof -i :8002
lsof -i :8003

# Kill and restart
pkill -f "uvicorn.*8002"
pkill -f "uvicorn.*8003"
```

---

## 📝 Next Steps

After verifying the workflow:

1. **Test with Blockchain**: Mint FreightTokens on-chain
2. **Automated Settlement**: Automatically approve LOW-risk milestones
3. **Notifications**: Send email/SMS on milestone payment
4. **Analytics**: Track settlement times and patterns
5. **Integration**: Connect to payment processor (Stripe/ACH)

---

## 📚 Related Documentation

- `EVENT_DRIVEN_PAYMENTS_IMPLEMENTATION.md` - Full technical spec
- `chainfreight-service/README.md` - ChainFreight API docs
- `chainpay-service/README.md` - ChainPay API docs
- `chainpay-service/ARCHITECTURE.md` - System design
