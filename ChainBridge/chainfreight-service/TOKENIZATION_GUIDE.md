# ChainFreight Tokenization Example

This document walks through a complete freight tokenization workflow.

## Scenario

A shipper has a high-value cargo shipment from Los Angeles to Chicago worth $100,000. They want to:

1. Create the shipment
2. Tokenize it into tradeable assets worth $100,000
3. Sell tokens to investors to finance the shipment
4. Deliver the cargo
5. Settle the tokens on delivery

## Step 1: Create the Shipment

```bash
curl -X POST "http://localhost:8002/shipments" \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name": "Global Logistics Inc",
    "origin": "Los Angeles, CA",
    "destination": "Chicago, IL",
    "cargo_value": 100000.00,
    "pickup_date": "2025-11-08T08:00:00",
    "planned_delivery_date": "2025-11-15T12:00:00",
    "pickup_eta": "2025-11-08T08:30:00",
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
  "pickup_date": "2025-11-08T08:00:00",
  "planned_delivery_date": "2025-11-15T12:00:00",
  "pickup_eta": "2025-11-08T08:30:00",
  "delivery_eta": "2025-11-14T18:00:00",
  "status": "pending",
  "actual_delivery_date": null,
  "created_at": "2025-11-07T15:00:00",
  "updated_at": "2025-11-07T15:00:00"
}
```

**Save the shipment ID: `1`**

## Step 2: Tokenize the Shipment

Now create a freight token representing the $100,000 cargo value:

```bash
curl -X POST "http://localhost:8002/shipments/1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{
    "face_value": 100000.00,
    "currency": "USD"
  }'
```

**Response:**

```json
{
  "id": 1,
  "shipment_id": 1,
  "face_value": 100000.00,
  "currency": "USD",
  "status": "created",
  "token_address": null,
  "created_at": "2025-11-07T15:05:00",
  "updated_at": "2025-11-07T15:05:00"
}
```

**What happened:**

- Token created with `status: "created"`
- Face value matches cargo value
- `token_address` is null (not yet on blockchain)
- Ready for trading and financing

## Step 3: Query Token Details

### Get Token for Specific Shipment

```bash
curl "http://localhost:8002/shipments/1/token"
```

### Get Specific Token by ID

```bash
curl "http://localhost:8002/tokens/1"
```

### List All Tokens

```bash
curl "http://localhost:8002/tokens?skip=0&limit=10"
```

## Step 4: Update Shipment Status (Simulate Delivery)

As the shipment progresses, update its status:

```bash
# Picked up
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "picked_up"}'

# In transit
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_transit"}'

# Delivered
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "delivered",
    "actual_delivery_date": "2025-11-14T15:30:00"
  }'
```

## Step 5: Settlement (Future Blockchain Integration)

When blockchain integration is enabled:

```bash
# Mint token on blockchain
POST /tokens/1/mint-onchain
{
  "blockchain": "ethereum",
  "network": "mainnet"
}

# Response includes on-chain contract address
{
  "id": 1,
  "token_address": "0x1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
  "status": "active",
  "blockchain": "ethereum",
  "tx_hash": "0xabc123..."
}

# Transfer token between wallets
POST /tokens/1/transfer
{
  "to_address": "0xrecipient_wallet",
  "amount": 100000.00
}

# Redeem token on delivery
POST /tokens/1/redeem
{
  "shipment_delivered": true,
  "proof_hash": "0x..."
}

# Status becomes REDEEMED, cargo funds released to shipper
```

## Data Model

### Shipment Fields

```text
id                      ← Unique identifier
shipper_name           ← Company name
origin                 ← Pickup location
destination            ← Delivery location
cargo_value            ← Total cargo value
pickup_date            ← Scheduled pickup
planned_delivery_date  ← Scheduled delivery
actual_delivery_date   ← Actual delivery (nullable)
pickup_eta             ← Estimated pickup time
delivery_eta           ← Estimated delivery time
status                 ← Current status
created_at             ← Created timestamp
updated_at             ← Last update timestamp
```

### FreightToken Fields

```text
id                      ← Unique identifier
shipment_id            ← Associated shipment
face_value             ← Token value in currency
currency               ← Currency code (USD, EUR, etc.)
status                 ← Token status
token_address          ← Blockchain contract address (null until minted)
created_at             ← Created timestamp
updated_at             ← Last update timestamp
```

## Use Cases

### 1. Working Capital Financing

A carrier has pending shipments worth $1M. They tokenize them and:

- Sell 50% of tokens to investors immediately
- Get $500K upfront cash
- Use cash to fund operations
- On delivery, reimburse token holders

```bash
# Day 1: Shipment created
POST /shipments → ID: 101

# Day 1: Tokenize for $1M
POST /shipments/101/tokenize
{
  "face_value": 1000000.00
}

# Day 1: Mint on blockchain
POST /tokens/1/mint-onchain
→ token_address: "0x..."

# Day 2: Investors buy tokens
# (via DEX or direct transfer)

# Day 15: Shipment delivered
PUT /shipments/101
{ "status": "delivered" }

# Day 15: Redeem tokens
POST /tokens/1/redeem
{ "shipment_delivered": true }

# Funds distributed to token holders
```

### 2. Risk-Adjusted Fractional Ownership

Investors can own portions of shipments and receive returns based on delivery:

```bash
# High-value, low-risk shipment
POST /shipments/102/tokenize
{
  "face_value": 500000.00,
  "currency": "USD"
}

# Token sells at 100% of face value (low risk)
# On delivery, investors get full return

# Lower-quality route, higher risk
POST /shipments/103/tokenize
{
  "face_value": 500000.00,
  "currency": "USD"
}

# Token sells at 90% of face value (5% discount for risk)
# On delivery, investors get 105% return (premium for risk taken)
```

### 3. Insurance as Tokens

Tokens could represent insurance claims:

```bash
POST /shipments/104/tokenize
{
  "face_value": 100000.00,
  "currency": "USD",
  "insurance_coverage": 110000.00
}

# Token value: $100k cargo + $10k insurance
# If delivered on time: Token worth $100k
# If delayed >2 days: Token worth $110k (insurance payout)
```

## Integration with ChainIQ

ChainFreight can call ChainIQ to assess token risk:

```bash
# When tokenizing a shipment, get risk score
POST /shipments/1/tokenize
{
  "face_value": 100000.00
}

# ChainFreight internally calls ChainIQ
GET http://chainiq:8001/score/shipment
{
  "shipment_id": 1,
  "origin": "Los Angeles",
  "destination": "Chicago"
}

# ChainIQ returns risk score: 0.35 (low risk)
# ChainFreight could adjust token price based on risk
```

## Future Enhancements

- [ ] Multi-currency support
- [ ] Fractional token amounts
- [ ] Token insurance pools
- [ ] Yield farming for token holders
- [ ] On-chain settlement contracts
- [ ] Token marketplace
- [ ] Secondary market trading
- [ ] Automated settlement on delivery proof
- [ ] Integration with payment platforms (Stripe, Wise)
- [ ] Integration with blockchain (Ethereum, Polygon)

## Testing

See `QUICK_START.md` for how to test the tokenization workflow locally.

---

**Created:** November 7, 2025
**For:** ChainFreight Service Enhancement
**Status:** Ready for development
