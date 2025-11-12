# Smart Settlements (ChainPay v2)

## Overview

Smart Settlements is a sophisticated payment orchestration layer that determines when and how milestone payments should be released based on real-time risk assessment and shipment event types.

**Core Principle**: Risk-informed, event-driven payment release with audit trails and payment rail abstraction for multi-provider support.

## Architecture

### Components

#### 1. Payment Rail Interface

Abstract layer for payment settlement providers.

```python
class PaymentRail(ABC):
    def process_settlement(
        self,
        milestone_id: int,
        amount: float,
        currency: str,
        recipient_id: Optional[str] = None,
    ) -> SettlementResult:
        """Process settlement through payment provider."""
```

**Supported Providers**:

- INTERNAL_LEDGER: ChainBridge internal accounting (v2 default)
- STRIPE: Future - Stripe Connect integration
- ACH: Future - Automated Clearing House
- WIRE: Future - International wire transfer

#### 2. InternalLedgerRail Implementation

Processes settlements through ChainBridge internal ledger.

**Flow**:

1. Validate milestone exists
2. Generate reference ID: INTERNAL_LEDGER:{timestamp}:{milestone_id}
3. Mark milestone as APPROVED in database
4. Return SettlementResult with reference ID

#### 3. Smart Settlement Logic

The should_release_now(risk_score, event_type) helper determines payment release timing.

**LOW Risk** (risk_score < 0.33): All events released immediately.

**MEDIUM Risk** (0.33 ≤ risk_score < 0.67): POD immediate, others delayed 24h.

**HIGH Risk** (risk_score ≥ 0.67): All events held for manual review.

## Core Integration

### process_milestone_for_intent() Workflow

1. Look up payment schedule and schedule item
2. Check idempotency (prevent double-payment)
3. Create MilestoneSettlement record
4. Determine release strategy via should_release_now()
5. If IMMEDIATE: route through PaymentRail
6. Otherwise: mark as DELAYED/PENDING and log for later processing

### Status Transitions

- PENDING → APPROVED (via IMMEDIATE strategy or manual approval)
- APPROVED → SETTLED (after payment rail processes)
- PENDING → DELAYED (for 24h hold)
- DELAYED → APPROVED (after delay period)

## Audit Endpoints

### GET /audit/shipments/{shipment_id}

Returns all milestone settlements for a shipment with status summary.

Example response:

```json
{
  "shipment_id": "SHIP-12345",
  "milestones": [
    {
      "id": 42,
      "event_type": "POD_CONFIRMED",
      "amount": 7000.00,
      "status": "approved",
      "provider": "internal_ledger"
    }
  ],
  "summary": {
    "total_milestones": 3,
    "approved_count": 2,
    "pending_count": 1,
    "total_approved_amount": 9000.00
  }
}
```

### GET /audit/payment_intents/{payment_id}/milestones

Returns audit trail for a specific payment intent with milestone details.

## Release Rules by Risk Tier

### LOW Risk Tier

All shipment events release immediately:

- PICKUP_CONFIRMED: 20% immediate
- POD_CONFIRMED: 70% immediate
- CLAIM_WINDOW_CLOSED: 10% immediate

### MEDIUM Risk Tier

Staged release with POD priority:

- PICKUP_CONFIRMED: 10% delayed 24h
- POD_CONFIRMED: 70% immediate
- CLAIM_WINDOW_CLOSED: 20% delayed 24h

### HIGH Risk Tier

Manual approval required:

- PICKUP_CONFIRMED: 0% pending
- POD_CONFIRMED: 80% manual review
- CLAIM_WINDOW_CLOSED: 20% manual review

## Code Quality

- Type hints on all functions
- PEP-8 compliant formatting
- Comprehensive docstrings
- No lint errors
- Idempotent operations
- Full audit trail logging
- Error handling and graceful degradation
- Backward compatible with existing code
