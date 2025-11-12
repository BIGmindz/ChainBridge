# ChainPay Architecture & Integration Design

## System Overview

ChainPay is the **fourth service** in the ChainBridge payment ecosystem, sitting between **ChainFreight** (tokenization) and **future payment processors** (ACH, Stripe, etc).

### Service Stack

``` text
┌──────────────────────────────────────────────────────────────┐
│                    ChainBridge Platform                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐   │
│  │  ChainBoard   │  │  ChainFreight │  │    ChainPay    │   │
│  │   (8000)      │  │     (8002)    │  │    (8003)      │   │
│  │               │  │               │  │                │   │
│  │ Drivers       │  │ Shipments     │  │ Payments       │   │
│  │ Onboarding    │  │ Tokenization  │  │ Settlement     │   │
│  └───────────────┘  └───────────────┘  └────────────────┘   │
│         ▲                   ▲                    ▲            │
│         │                   │                    │            │
│         └───────────────────┼────────────────────┘            │
│                     Federated Architecture                    │
│                                                              │
│  ┌───────────────┐                                           │
│  │   ChainIQ     │                                           │
│  │   (8001)      │                                           │
│  │               │                                           │
│  │ ML Scoring    │                                           │
│  │ Risk Engine   │                                           │
│  └───────────────┘                                           │
│         ▲                                                    │
│         │                                                    │
│         └──────────────────────────────────────────────────┐ │
│                                                            │ │
│              Called by ChainFreight & ChainPay            │ │
│                                                            │ │
└────────────────────────────────────────────────────────────┘─┘
```

### Information Flow

``` bash
1. Shipment Creation (ChainBoard → ChainFreight)
   └─ Shipment created with origin, destination, cargo_value

2. Tokenization (ChainFreight ↔ ChainIQ)
   ├─ POST /shipments/{id}/tokenize
   ├─ ChainFreight calls ChainIQ /score/shipment
   ├─ Returns: risk_score, risk_category, recommended_action
   └─ Token stored with risk metrics

3. Payment Creation (ChainFreight → ChainPay)
   ├─ Client creates payment intent via ChainPay
   ├─ ChainPay fetches token from ChainFreight
   ├─ Extracts risk_score and risk_category
   └─ Stores payment with risk_tier and settlement schedule

4. Settlement (ChainPay Decision Engine)
   ├─ POST /payment_intents/{id}/settle
   ├─ Apply conditional logic:
   │  ├─ LOW: Approve immediately
   │  ├─ MEDIUM: Delay 24 hours, auto-approve
   │  └─ HIGH: Reject unless force_approval
   ├─ Log all decisions to SettlementLog
   └─ Return decision + timing

5. Completion (External Processor)
   ├─ POST /payment_intents/{id}/complete
   ├─ ChainPay transitions to SETTLED status
   └─ Ready for blockchain or fiat transfer
```

---

## Risk-Based Settlement Engine

### Core Algorithm

```python
def settle_payment(payment_intent):
    # Step 1: Determine settlement tier from risk
    risk_tier = map_risk_to_tier(payment_intent.risk_category)
    
    # Step 2: Apply conditional logic
    if risk_tier == LOW:
        # Immediate approval
        status = APPROVED
        delay = 0
        
    elif risk_tier == MEDIUM:
        # Conditional delay
        if current_time >= delayed_until:
            status = APPROVED
        else:
            status = DELAYED
            delayed_until = now + 24 hours
            
    else:  # HIGH
        # Manual review required
        if force_approval:
            status = APPROVED
        else:
            status = REJECTED
    
    # Step 3: Log decision
    log_settlement_action(
        payment_id=payment_intent.id,
        action=status,
        reason=generate_reason(risk_tier, status),
        triggered_by="system"
    )
    
    return SettlementResponse(status, reason, timing)
```

### State Machine

``` text
Creation
    ↓
  pending
    ↓
  settle()
    ├─ LOW risk     → approved ─→ complete() ─→ settled ✓
    │
    ├─ MEDIUM risk  → delayed
    │                   ↓
    │              (wait 24h)
    │                   ↓
    │              settle() → approved ─→ complete() ─→ settled ✓
    │
    └─ HIGH risk    → rejected
                        ↓
                   settle(force_approval=true)
                        ↓
                      approved ─→ complete() ─→ settled ✓
```

---

## Database Design

### Schema Relationships

``` text
Payment Intents (Primary)
├── id (PK)
├── freight_token_id (FK to ChainFreight.freight_tokens)
├── amount
├── currency
├── risk_score (cached)
├── risk_category (cached)
├── risk_tier (computed)
├── status (pending → approved/delayed → settled)
├── settlement_approved_at
├── settlement_delayed_until
├── settlement_completed_at
└── timestamps
    
Settlement Logs (Audit Trail)
├── id (PK)
├── payment_intent_id (FK)
├── action (delayed, approved, rejected, settled)
├── reason (business logic)
├── triggered_by (system/manual)
├── approved_by (for manual overrides)
└── created_at
```

### Indexing Strategy

```sql
-- Fast lookups
CREATE INDEX idx_payment_status ON payment_intents(status);
CREATE INDEX idx_payment_risk_tier ON payment_intents(risk_tier);
CREATE INDEX idx_payment_freight_token ON payment_intents(freight_token_id);

-- Audit trail
CREATE INDEX idx_settlement_payment ON settlement_logs(payment_intent_id);
CREATE INDEX idx_settlement_action ON settlement_logs(action);

-- Queries by timestamp
CREATE INDEX idx_payment_created ON payment_intents(created_at);
CREATE INDEX idx_settlement_created ON settlement_logs(created_at);
```

---

## Integration Points

### 1. ChainFreight Service Integration

**What:** Fetch freight token details including risk metrics

**How:** HTTP GET to ChainFreight API

```python
# In chainfreight_client.py
async def fetch_freight_token(token_id: int):
    response = await client.get(f"{CHAINFREIGHT_URL}/tokens/{token_id}")
    # Returns: FreightTokenResponse with risk_score, risk_category
```

**Error Handling:**

- Service unavailable: Return 404 to user
- Network timeout: Return 404 to user
- Token not found: Return 404 to user

**Caching:** Risk metrics cached in PaymentIntent at creation time (no live fetch)

### 2. Future Payment Processor Integration

**What:** Execute actual payment transfer

**How:** Webhook or batch processor

```python
# Future enhancement
@app.post("/payment_intents/{id}/execute")
async def execute_payment(payment_id):
    payment = get_payment(payment_id)
    
    if payment.status != APPROVED:
        raise Error("Payment not approved for execution")
    
    # Call external processor (Stripe, ACH, etc)
    result = await payment_processor.transfer(
        amount=payment.amount,
        currency=payment.currency,
        recipient=get_recipient(payment.freight_token_id),
        reference=f"token-{payment.freight_token_id}"
    )
    
    if result.success:
        complete_settlement(payment_id)
    
    return result
```

---

## Deployment Architecture

### Development (Single Machine)

``` text
localhost:8001 ─ ChainIQ (ML scoring)
localhost:8002 ─ ChainFreight (Tokenization)
localhost:8003 ─ ChainPay (Settlement)

Each with SQLite database
```

### Production (Kubernetes)

``` text
Namespace: chainbridge

Services:
├── chainiq-service
│   ├── Port: 8001
│   ├── Replicas: 2 (stateless)
│   └── DB: PostgreSQL (shared)
│
├── chainfreight-service
│   ├── Port: 8002
│   ├── Replicas: 3 (stateless)
│   └── DB: PostgreSQL (chainfreight_db)
│
└── chainpay-service
    ├── Port: 8003
    ├── Replicas: 2 (stateless)
    └── DB: PostgreSQL (chainpay_db)

Persistence:
├── PostgreSQL Cluster (HA)
├── PVC for logs
└── Secrets for credentials

Monitoring:
├── Prometheus metrics
├── ELK logging
└── Grafana dashboards
```

---

## Security Considerations

### 1. Service-to-Service Authentication

```python
# Future: Add JWT tokens or mTLS
# Current: Assumes private network

# TODO: Implement
- API key authentication
- JWT bearer tokens
- mTLS certificates
- Rate limiting per service
```

### 2. Force Approval Audit

```python
# All manual overrides are logged
SettlementLog(
    action="approved",
    reason="High risk - manual override approved",
    triggered_by="manual",
    approved_by="john.doe@company.com",  # User identifier
    created_at=now
)

# Alert on: force_approval flag used
# Monitor: High-risk force approvals
```

### 3. Data Isolation

```python
# Separate databases per service
- ChainFreight: chainfreight.db
- ChainPay: chainpay.db
- ChainIQ: No data persistence (stateless)

# No cross-database foreign keys
# Looser coupling via HTTP APIs
```

---

## Monitoring & Observability

### Key Metrics

```python
# Prometheus metrics to expose
payment_intents_created_total                 # Counter
payment_intents_settled_total                 # Counter
payment_settlement_duration_seconds          # Histogram
payment_settlement_delay_applied              # Counter (by tier)
payment_force_approvals_total                 # Counter (alerts on this)
chainfreight_client_fetch_errors_total        # Counter
chainfreight_client_latency_seconds           # Histogram
```

### Log Patterns

``` text
INFO  - Payment intent 1 created for token 1
DEBUG - Fetching freight token 1 from ChainFreight
INFO  - Successfully fetched freight token 1: risk_score=0.35
INFO  - Payment 1 settlement action: delayed (risk_tier=medium)
INFO  - Payment 1 settlement action: approved (risk_tier=low)
ERROR - Error calling ChainFreight service for token 1
WARN  - High-risk payment 1 force-approved
```

### Dashboards (Grafana)

- Settlement decisions by risk tier (pie chart)
- Payment status distribution (stacked bar)
- Approval latency by risk tier (histogram)
- Force approval rate (gauge)
- ChainFreight fetch success rate (gauge)

---

## Performance Characteristics

### Latency

``` text
Create payment intent:
├─ Fetch freight token:    50-200ms (network)
├─ DB insert:             10-50ms
└─ Total:                 60-250ms

Settle payment:
├─ DB query:              5-10ms
├─ Logic execution:       1-5ms
├─ Log insert:           10-20ms
└─ Total:                16-35ms

Complete settlement:
├─ DB update:            10-20ms
└─ Total:                10-20ms
```

### Throughput

``` text
Single instance (ChainPay):
- Create payment intents: ~1000/sec (CPU bound)
- Settle payments: ~5000/sec (DB I/O bound)
- Complete settlements: ~10000/sec

Scaling:
- Stateless services scale horizontally
- PostgreSQL becomes bottleneck at scale
- Consider connection pooling (PgBouncer)
```

### Database Size Estimate

``` text
For 10M shipments over 2 years:
- payment_intents:   10M rows × 200 bytes = 2GB
- settlement_logs:   30M rows × 150 bytes = 4.5GB (3 logs per payment average)
- Indexes:           ~2GB
- Total:             ~8.5GB

Retention: 2 years
Archive strategy: Move logs to S3 after 1 year
```

---

## Disaster Recovery

### Backup Strategy

```bash
# Daily backup of PostgreSQL
pg_dump chainpay_db | gzip > backups/chainpay_$(date +%Y%m%d).sql.gz

# Keep 30 days of backups
# Test restore weekly
```

### Recovery Procedures

``` text
Scenario 1: Single payment corrupted
├─ Query settlement_logs to understand history
├─ Manually set status based on logs
└─ Re-settle if needed

Scenario 2: Database lost
├─ Restore from latest backup
├─ Sync ChainFreight token list
├─ Re-create any lost payments from source
└─ Verify audit trail matches

Scenario 3: ChainFreight down
├─ ChainPay continues using cached risk metrics
├─ Cannot create NEW payments (token validation fails)
├─ Existing payments continue settling normally
└─ Must restore ChainFreight before new payments
```

---

## Future Roadmap

### Phase 2: Payment Execution

```python
@app.post("/payment_intents/{id}/execute")
async def execute_payment(payment_id):
    # Integrate with real payment processor
    # Stripe, ACH, blockchain, etc
```

### Phase 3: Webhooks

```python
# Notify external systems of settlement decisions
webhook_url = get_shipper_webhook(payment.freight_token_id)
await notify_webhook({
    "event": "payment.settled",
    "payment_id": payment.id,
    "token_id": payment.freight_token_id,
    "amount": payment.amount
})
```

### Phase 4: Custom Risk Rules

```python
# Per-shipper risk thresholds
@app.post("/risk_rules")
async def create_risk_rule(shipper_id, threshold_overrides):
    # Allow customization of settlement delays by shipper
    pass
```

### Phase 5: Settlement Batching

```python
# Batch settle multiple payments
@app.post("/settlement_batches")
async def create_settlement_batch(payment_ids):
    # Group payments for bulk processing
    pass
```

---

**Status:** ✅ Architecture Ready  
**Date:** November 7, 2025
