# Smart Settlements Implementation Guide

## Quick Start

### What Changed in ChainPay v2

The `process_milestone_for_intent()` function now includes **Smart Settlements** logic that determines whether to release payments immediately or hold them for later processing based on risk assessment.

### New Files

- `app/payment_rails.py`: Payment processing abstraction layer
  - Abstract `PaymentRail` base class
  - `InternalLedgerRail` implementation
  - `should_release_now()` decision logic
  - `ReleaseStrategy` and `SettlementResult` types

### Modified Files

- `app/main.py`: Enhanced `process_milestone_for_intent()`
  - Integrates Smart Settlements logic
  - Routes IMMEDIATE settlements through payment rails
  - Marks others as DELAYED/PENDING
  - Two new audit endpoints: `/audit/shipments/{id}` and `/audit/payment_intents/{id}/milestones`

## Decision Logic

### The should_release_now() Function

```python
def should_release_now(risk_score: float, event_type: str) -> ReleaseStrategy
```

Takes risk score (0.0-1.0) and event type, returns release strategy:

```python
ReleaseStrategy.IMMEDIATE        # Release now through payment rail
ReleaseStrategy.DELAYED          # Hold for 24 hours
ReleaseStrategy.MANUAL_REVIEW    # Requires compliance approval
ReleaseStrategy.PENDING          # Don't release yet (event not eligible)
```

### Decision Matrix

| Risk Level | PICKUP_CONFIRMED | POD_CONFIRMED | CLAIM_WINDOW_CLOSED |
|---|---|---|---|
| LOW (< 0.33) | IMMEDIATE | IMMEDIATE | IMMEDIATE |
| MEDIUM (0.33-0.67) | DELAYED | IMMEDIATE | DELAYED |
| HIGH (≥ 0.67) | PENDING | MANUAL_REVIEW | MANUAL_REVIEW |

## Payment Rail Architecture

### Adding a New Payment Provider

1. Create new rail class inheriting from `PaymentRail`:

```python
class StripePaymentRail(PaymentRail):
    def __init__(self, db: Session, stripe_key: str):
        self.db = db
        self.stripe_api_key = stripe_key

    def process_settlement(
        self,
        milestone_id: int,
        amount: float,
        currency: str,
        recipient_id: Optional[str] = None,
    ) -> SettlementResult:
        """Process through Stripe Connect"""
        try:
            # Call Stripe API
            payout = stripe.Payout.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency.lower(),
                destination=recipient_id,  # Connected account ID
            )

            reference_id = f"STRIPE:{payout.id}"

            milestone = self.db.query(MilestoneSettlementModel).get(milestone_id)
            milestone.status = PaymentStatus.APPROVED
            milestone.reference = reference_id
            self.db.commit()

            return SettlementResult(
                success=True,
                provider=SettlementProvider.STRIPE,
                reference_id=reference_id,
                message=f"Stripe payout created: {payout.id}",
                released_at=datetime.utcnow(),
            )
        except stripe.error.StripeError as e:
            return SettlementResult(
                success=False,
                provider=SettlementProvider.STRIPE,
                error=str(e),
                message="Stripe payout failed",
            )

    def get_provider(self) -> SettlementProvider:
        return SettlementProvider.STRIPE
```

1. Update `process_milestone_for_intent()` to use new rail:

```python
if release_strategy == ReleaseStrategy.IMMEDIATE:
    try:
        # Determine which rail based on payment method
        if payment_intent.payment_method == "stripe":
            rail = StripePaymentRail(db, stripe_key)
        else:
            rail = InternalLedgerRail(db)

        result = rail.process_settlement(...)
        # Handle result
    except Exception as e:
        # Handle error
```

## Workflow Example: Processing a Shipment Event

### Request

```bash
POST /webhooks/shipment_event
Content-Type: application/json

{
  "shipment_id": "SHIP-BOZZA-001",
  "event_type": "POD_CONFIRMED",
  "occurred_at": "2025-11-07T15:30:00Z"
}
```

### Processing Steps

1. **Webhook Handler** receives event
2. **Query** all payment intents with active schedules
3. **For each intent**, call `process_milestone_for_intent()`:
   - Look up payment schedule
   - Find schedule item for event_type
   - Check for duplicate (idempotency)
   - Calculate amount: `total * percentage`
   - Get risk_score from payment_intent
   - Call `should_release_now(risk_score, event_type)`
4. **Based on strategy**:
   - IMMEDIATE: Call payment rail, mark APPROVED
   - DELAYED: Mark DELAYED, set delay timestamp
   - MANUAL_REVIEW: Mark PENDING, alert team
   - PENDING: Mark PENDING, skip
5. **Return** webhook response with count

### Response

```json
{
  "shipment_id": "SHIP-BOZZA-001",
  "event_type": "POD_CONFIRMED",
  "processed_at": "2025-11-07T15:30:15Z",
  "milestone_settlements_created": 3,
  "message": "Processed shipment event: 3 milestone settlement(s) created/updated"
}
```

### Database State After Processing

**payment_intents** table (unchanged):

- id=10, freight_token_id=5, amount=10000, risk_score=0.28, risk_tier=LOW

**milestone_settlements** table (new records):

```sql
id  payment_intent_id  event_type       amount   status    provider
40  10                 PICKUP_CONFIRMED 2000.00  APPROVED  INTERNAL_LEDGER
41  10                 POD_CONFIRMED    7000.00  APPROVED  INTERNAL_LEDGER
42  10                 CLAIM_WINDOW...  1000.00  APPROVED  INTERNAL_LEDGER
```

## Audit Endpoints Usage

### Get Shipment Audit Trail

```bash
GET /audit/shipments/SHIP-BOZZA-001

{
  "shipment_id": "SHIP-BOZZA-001",
  "milestones": [
    {
      "id": 40,
      "payment_intent_id": 10,
      "event_type": "PICKUP_CONFIRMED",
      "amount": 2000.00,
      "status": "approved",
      "reference": "INTERNAL_LEDGER:2025-11-07T15:30:15:40",
      "created_at": "2025-11-07T15:30:15"
    },
    ...
  ],
  "summary": {
    "total_milestones": 3,
    "approved_count": 3,
    "pending_count": 0,
    "total_approved_amount": 10000.00
  }
}
```

### Get Payment Intent Milestones

```bash
GET /audit/payment_intents/10/milestones

{
  "payment_intent_id": 10,
  "amount": 10000.00,
  "risk_score": 0.28,
  "risk_tier": "low",
  "milestones": [
    {
      "id": 40,
      "event_type": "PICKUP_CONFIRMED",
      "amount": 2000.00,
      "status": "approved"
    },
    ...
  ],
  "summary": {
    "total_milestones": 3,
    "approved_amount": 10000.00,
    "pending_amount": 0.00
  }
}
```

## Testing Checklist

### Unit Tests to Add

```python
# tests/test_smart_settlements.py

def test_should_release_now_low_risk():
    """LOW risk always releases immediately"""
    assert should_release_now(0.15, "PICKUP_CONFIRMED") == ReleaseStrategy.IMMEDIATE
    assert should_release_now(0.15, "POD_CONFIRMED") == ReleaseStrategy.IMMEDIATE

def test_should_release_now_medium_risk():
    """MEDIUM risk: POD immediate, others delayed"""
    assert should_release_now(0.50, "POD_CONFIRMED") == ReleaseStrategy.IMMEDIATE
    assert should_release_now(0.50, "PICKUP_CONFIRMED") == ReleaseStrategy.DELAYED

def test_should_release_now_high_risk():
    """HIGH risk: manual review for POD/CLAIM"""
    assert should_release_now(0.85, "POD_CONFIRMED") == ReleaseStrategy.MANUAL_REVIEW
    assert should_release_now(0.85, "PICKUP_CONFIRMED") == ReleaseStrategy.PENDING

def test_internal_ledger_rail():
    """InternalLedgerRail marks settlements as APPROVED"""
    rail = InternalLedgerRail(db)
    result = rail.process_settlement(
        milestone_id=1,
        amount=1000.00,
        currency="USD"
    )
    assert result.success
    assert "INTERNAL_LEDGER:" in result.reference_id
```

### Integration Tests

```python
# tests/test_smart_settlements_integration.py

def test_webhook_immediate_settlement():
    """LOW risk settlement released immediately via rail"""
    # 1. Create payment intent with LOW risk
    # 2. Create payment schedule
    # 3. Trigger webhook with event
    # 4. Verify milestone status is APPROVED
    # 5. Verify reference ID generated

def test_webhook_delayed_settlement():
    """MEDIUM risk non-POD held for 24h"""
    # 1. Create MEDIUM risk intent
    # 2. Trigger PICKUP_CONFIRMED event
    # 3. Verify milestone status is DELAYED
    # 4. Verify settlement_delayed_until is 24h away

def test_webhook_manual_review_settlement():
    """HIGH risk requires manual approval"""
    # 1. Create HIGH risk intent
    # 2. Trigger POD_CONFIRMED event
    # 3. Verify milestone status is PENDING
```

### Manual Testing Commands

```bash
# 1. Start local API
python -m uvicorn app.main:app --reload --port 8003

# 2. Create payment intent with LOW risk
INTENT_ID=$(curl -s -X POST http://localhost:8003/payment_intents \
  -H "Content-Type: application/json" \
  -d '{
    "freight_token_id": 1,
    "amount": 10000,
    "currency": "USD"
  }' | jq -r '.id')

echo "Created payment intent: $INTENT_ID"

# 3. Verify schedule was created
curl http://localhost:8003/audit/payment_intents/$INTENT_ID/milestones

# 4. Simulate webhook event
curl -X POST http://localhost:8003/webhooks/shipment_event \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "SHIP-TEST-001",
    "event_type": "POD_CONFIRMED",
    "occurred_at": "2025-11-07T15:30:00Z"
  }'

# 5. Check audit trail
curl http://localhost:8003/audit/shipments/SHIP-TEST-001
```

## Logging & Debugging

### Key Log Messages

Watch for these when debugging:

```text
Created milestone settlement {id}: payment_intent={pid}, event_type={event}, status={status}
Smart Settlement: releasing immediately
Smart Settlement: delayed release (24h)
Smart Settlement: pending manual review (HIGH risk)
Internal ledger settlement approved: milestone_id={id}, amount={amount}, reference={ref}
Payment rail processing succeeded: milestone={id}, reference={ref}
Payment rail processing failed: milestone={id}, error={error}
```

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

## Backward Compatibility

All existing endpoints continue to work:

- POST /payment_intents
- GET /payment_intents
- GET /payment_intents/{id}
- POST /payment_intents/{id}/settle
- POST /payment_intents/{id}/complete
- GET /payment_intents/{id}/history

New endpoints added:

- GET /audit/shipments/{id}
- GET /audit/payment_intents/{id}/milestones

## Performance Considerations

### Query Optimization

The webhook processes **all** payment intents. For high volume:

1. Add index on `freight_token_id` in payment_intents table
2. Query only intents with active schedules: `db.query(PaymentIntentModel).join(PaymentScheduleModel).filter(PaymentIntentModel.status == PaymentStatus.PENDING).all()`
3. Consider batch processing for 100+ milestones
4. Add rate limiting on webhook endpoint

### Settlement Processing

- IMMEDIATE settlements: <100ms via internal ledger
- DELAYED settlements: async job runs every 5 minutes
- MANUAL_REVIEW: batched notification to compliance team

## Future Work

### Phase 2: Delayed Settlement Automation

```python
# Background job (Celery/APScheduler)
@app.on_event("startup")
async def start_settlement_processor():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(process_delayed_settlements, 'interval', minutes=5)
    scheduler.start()

async def process_delayed_settlements():
    """Auto-release DELAYED settlements after 24h"""
    now = datetime.utcnow()
    delayed = db.query(MilestoneSettlementModel).filter(
        MilestoneSettlementModel.status == PaymentStatus.DELAYED,
        MilestoneSettlementModel.settlement_delayed_until <= now
    ).all()

    for milestone in delayed:
        rail = InternalLedgerRail(db)
        result = rail.process_settlement(...)
        # Update status to APPROVED
```

### Phase 3: Compliance Approval Endpoint

```python
@app.post("/compliance/approve/{milestone_id}")
async def approve_settlement(milestone_id: int, db: Session = Depends(get_db)):
    """Manual approval endpoint for HIGH risk milestones"""
    milestone = db.query(MilestoneSettlementModel).get(milestone_id)
    milestone.status = PaymentStatus.APPROVED
    db.commit()
    return {"message": "Settlement approved"}
```

### Phase 4: Multi-Rail Selection

```python
# Support multiple payment providers per intent
@app.post("/payment_intents/{id}/set_payment_method")
async def set_payment_method(
    payment_id: int,
    method: str,  # "internal_ledger", "stripe", "ach"
    db: Session = Depends(get_db)
):
    intent = db.query(PaymentIntentModel).get(payment_id)
    intent.payment_method = method
    db.commit()
    return intent
```
