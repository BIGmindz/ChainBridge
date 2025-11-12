# ChainPay Service Integration Summary

## Overview

The ChainPay Service has been successfully refactored to use a unified helper function (`process_milestone_for_intent`) for processing milestone settlements. This ensures consistent, idempotent, and maintainable milestone handling across all service endpoints.

## Architecture

### Helper Function: `process_milestone_for_intent()`

**Location**: `app/helpers.py`

**Purpose**: Central processing logic for milestone settlements

- Schedule lookup
- Schedule item matching
- Amount calculation
- Settlement creation (idempotent)
- Error handling

**Signature**:

```python
def process_milestone_for_intent(
    db: Session,
    payment_intent: PaymentIntentModel,
    event: ShipmentEventWebhookRequest,
) -> tuple[Optional[MilestoneSettlementModel], str]
```

**Returns**:

- `(milestone, status_msg)`: Tuple of created milestone or None
- Handles `IntegrityError` gracefully (idempotent on event_type + payment_intent_id)

---

## Integration Points

### Webhook Endpoint: `/webhooks/shipment_event`

**File**: `app/main.py` (lines 690-730)

**Flow**:

1. Receive ShipmentEventWebhookRequest with shipment_id, event_type, occurred_at
2. Query all payment intents (TODO: filter by shipment_id when ChainFreight integration complete)
3. For each payment intent, call `process_milestone_for_intent()`
   - Looks up PaymentSchedule
   - Finds schedule item for event_type
   - Calculates milestone_amount = total_amount * (percentage / 100)
   - Creates MilestoneSettlement (idempotent)
   - Returns (milestone, status_msg)
4. Return ShipmentEventWebhookResponse with count of created milestones

**Response Model**:

```python
class ShipmentEventWebhookResponse(BaseModel):
    shipment_id: str
    event_type: str
    processed_at: datetime
    milestone_settlements_created: int
    message: str
```

---

## Idempotency Guarantee

### Unique Constraint

The `MilestoneSettlement` table has a unique constraint on `(payment_intent_id, event_type)`

**Behavior**:

- If the same event_type is received twice for the same payment_intent
- First call: Creates MilestoneSettlement
- Subsequent calls: IntegrityError caught, returns (None, "already exists" message)
- Response counts both as success (milestone_count increments)

---

## Data Flow: From Event to Settlement

```text
ChainFreight Webhook Event
        ↓
POST /webhooks/shipment_event
        ↓
process_shipment_event()
        ↓
    For each payment_intent:
        ↓
    process_milestone_for_intent()
        ├─ Query: PaymentSchedule for payment_intent_id
        ├─ Query: PaymentScheduleItem for event_type
        ├─ Calculate: milestone_amount
        ├─ Create: MilestoneSettlement (idempotent)
        └─ Handle: IntegrityError (duplicate event_type)
        ↓
    Return: (milestone, status_msg)
        ↓
Return: ShipmentEventWebhookResponse
        └─ milestone_settlements_created
```

---

## Testing Strategy

### Unit Tests

- Test `process_milestone_for_intent()` with valid event
- Test idempotency (duplicate event_type)
- Test missing schedule handling
- Test missing schedule item handling
- Test amount calculation

### Integration Tests

- Test webhook endpoint with multiple payment intents
- Test webhook with no matching payment intents
- Test webhook response format
- Test idempotent webhook calls

---

## Configuration & Risk Tier Schedules

### Default Schedules by Risk Tier

**LOW Risk**:

```python
[
    {"event_type": "PICKED_UP", "percentage": 20, "order": 1},
    {"event_type": "IN_TRANSIT", "percentage": 70, "order": 2},
    {"event_type": "POD_CONFIRMED", "percentage": 10, "order": 3},
]
```

**MEDIUM Risk** (with delay):

```python
[
    {"event_type": "PICKED_UP", "percentage": 15, "order": 1},
    {"event_type": "IN_TRANSIT", "percentage": 70, "order": 2},
    {"event_type": "POD_CONFIRMED", "percentage": 15, "order": 3},
]
```

**HIGH Risk** (manual review):

```python
[
    {"event_type": "PICKED_UP", "percentage": 10, "order": 1},
    {"event_type": "IN_TRANSIT", "percentage": 60, "order": 2},
    {"event_type": "POD_CONFIRMED", "percentage": 30, "order": 3},
]
```

---

## Error Handling

### In `process_milestone_for_intent()`

1. **Missing PaymentSchedule**
   - Log: DEBUG
   - Return: `(None, "No payment schedule found")`
   - Webhook counts as 0 settlement

2. **Missing PaymentScheduleItem for event_type**
   - Log: DEBUG
   - Return: `(None, "No schedule item for event_type")`
   - Webhook counts as 0 settlement

3. **IntegrityError** (duplicate event_type)
   - Log: INFO (expected, idempotent)
   - Return: `(None, "Milestone already exists")`
   - Webhook counts as 0 new settlement

4. **Unexpected Exception**
   - Log: ERROR
   - Raise exception (caught in webhook, db.rollback())
   - Webhook continues to next payment_intent

---

## Future Enhancements

1. **ChainFreight Integration**
   - Query shipment_id from freight_token_id
   - Filter payment_intents by shipment_id (not all payment_intents)
   - Implement in webhook endpoint

2. **Settlement Approval Workflow**
   - Track approval status in MilestoneSettlement
   - HIGH risk settlements require manual approval
   - Add endpoint for reviewer to approve/reject

3. **Partial Settlement Triggering**
   - When all milestones for a payment_intent reach APPROVED status
   - Automatically trigger payment settlement

4. **Metrics & Monitoring**
   - Track milestone events processed per shipment
   - Monitor webhook latency
   - Alert on webhook failures

---

## Code Quality

- ✅ No lint errors
- ✅ Type hints on all functions
- ✅ Comprehensive docstrings
- ✅ Consistent error handling
- ✅ Clear logging statements
- ✅ Idempotent design
