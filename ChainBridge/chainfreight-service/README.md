# ChainFreight Service

Shipment lifecycle, execution, and tokenized freight API for the ChainBridge platform.

## Overview

ChainFreight is responsible for:

- Shipment creation and lifecycle management
- Real-time tracking and status updates
- Delivery confirmation and proof of delivery
- Exception handling and incident management
- **Tokenization of freight assets** for trading and financing
- Integration with ChainIQ for risk scoring

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLAlchemy + SQLite (production: PostgreSQL)
- **Validation**: Pydantic
- **API Documentation**: OpenAPI (Swagger)

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the Service

```bash
# Development
python -m app.main

# Or directly
uvicorn app.main:app --reload --port 8002

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

The API will be available at `http://localhost:8002`

### API Documentation

Visit `http://localhost:8002/docs` for interactive Swagger documentation.

## API Endpoints

### Health Check

```http
GET /health
```

Returns service status.

### Create Shipment

```http
POST /shipments
Content-Type: application/json
```

```json
{
  "shipper_name": "ACME Corp",
  "origin": "Los Angeles, CA",
  "destination": "Chicago, IL",
  "pickup_date": "2025-11-08T08:00:00",
  "planned_delivery_date": "2025-11-15T12:00:00"
}
```

Response: `201 Created` with shipment record.

### List Shipments

```http
GET /shipments?skip=0&limit=10&status=in_transit
```

Returns paginated list of shipments with optional filtering by status.

**Status options**: `pending`, `picked_up`, `in_transit`, `delivered`, `cancelled`

### Get Shipment

```http
GET /shipments/{shipment_id}
```

Returns a specific shipment record.

### Update Shipment

```http
PUT /shipments/{shipment_id}
Content-Type: application/json
```

```json
{
  "status": "delivered",
  "actual_delivery_date": "2025-11-14T14:30:00"
}
```

Updates shipment information (partial updates supported).

## Freight Tokenization

ChainFreight enables **tokenization of freight assets**, allowing fractional ownership and trading of shipment cargo value.

### Create a Freight Token

Once a shipment is created, you can tokenize it to enable trading and financing:

```http
POST /shipments/{shipment_id}/tokenize
Content-Type: application/json
```

```json
{
  "face_value": 50000.00,
  "currency": "USD"
}
```

**Response** (201 Created):

```json
{
  "id": 1,
  "shipment_id": 1,
  "face_value": 50000.00,
  "currency": "USD",
  "status": "created",
  "token_address": null,
  "created_at": "2025-11-07T15:00:00",
  "updated_at": "2025-11-07T15:00:00"
}
```

### Get Shipment's Token

```http
GET /shipments/{shipment_id}/token
```

Returns the freight token associated with a shipment.

### List All Tokens

```http
GET /tokens?skip=0&limit=10
```

Returns paginated list of all freight tokens.

### Get Token by ID

```http
GET /tokens/{token_id}
```

Returns a specific freight token.

## Project Structure

```text
chainfreight-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and routes
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   └── database.py          # DB session management
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Shipment Lifecycle

```text
pending → picked_up → in_transit → delivered
                   ↘ cancelled
```

### Status Transitions

- **pending**: Initial state, awaiting pickup
- **picked_up**: Driver has picked up the shipment
- **in_transit**: Shipment is en route to destination
- **delivered**: Shipment has been delivered
- **cancelled**: Shipment was cancelled

## Tokenization Architecture

### Why Tokenize Freight?

Freight tokenization enables:

- **Fractional Ownership**: Multiple investors can own portions of high-value shipments
- **Trading**: Tokens can be traded on secondary markets before delivery
- **Financing**: Carriers can use tokens as collateral for working capital
- **Transparency**: Blockchain integration provides immutable tracking
- **Automation**: Smart contracts can automate settlement and delivery confirmation

### Token Lifecycle

```text
created → active → (locked) → redeemed | expired | cancelled
```

### Token Status Values

- **CREATED**: Token has been minted but not yet active
- **ACTIVE**: Token is ready for trading and transfer
- **LOCKED**: Token is held in escrow during a transaction
- **REDEEMED**: Token has been redeemed against delivered cargo
- **EXPIRED**: Token has expired before delivery
- **CANCELLED**: Token has been cancelled

### Integration with Shipments

Each `FreightToken` is tied to exactly one `Shipment`:

```python
# Example: Tokenize a shipment
POST /shipments/1/tokenize
{
  "face_value": 100000.00,
  "currency": "USD"
}

# Result: Token created with status=CREATED
# On delivery confirmation: Status transitions to REDEEMED
```

### Future: On-Chain Integration

The `token_address` field is reserved for on-chain token addresses:

```json
{
  "id": 1,
  "shipment_id": 1,
  "face_value": 100000.00,
  "token_address": "0x123abc...",  // ERC-20 contract address
  "status": "active"
}
```

## ChainIQ Integration for Risk Scoring

ChainFreight automatically integrates with the ChainIQ ML scoring engine to assess risk when shipments are tokenized.

### What Happens at Tokenization

When you call `POST /shipments/{id}/tokenize`:

1. ChainFreight validates the shipment exists
2. ChainFreight calls ChainIQ's `/score/shipment` endpoint
3. ChainIQ analyzes origin, destination, delivery date, and shipment history
4. ChainIQ returns a risk score (0.0-1.0) and risk category
5. ChainFreight generates a recommended action based on risk
6. Token is created with all risk fields populated

### Response with Risk Scoring

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

### Risk Categories and Recommendations

- **LOW** (0.0-0.33): `APPROVE` - Standard financing suitable
- **MEDIUM** (0.33-0.67): `APPROVE_WITH_CONDITIONS` or `REVIEW` - Risk mitigation needed
- **HIGH** (0.67-1.0): `REVIEW_URGENTLY` or `REJECT` - Detailed assessment required

### Graceful Degradation

If the ChainIQ service is unavailable or times out:
- Tokenization **still succeeds**
- Risk fields are set to `null`
- A warning is logged
- The token can be scored later when service recovers

This ensures the system is resilient to external service failures.

### Implementation Details

See `CHAINIQ_INTEGRATION.md` for:
- Architecture diagrams
- Data flow examples
- Local testing procedures
- Configuration options
- Error handling details
- Production checklist
``` text

When blockchain integration is enabled, tokens will be minted as ERC-20 contracts enabling:

- Trading on DEXs
- Use as collateral on lending platforms
- Direct transfer between wallets
- Automatic settlement on delivery

## Integration with ChainIQ

ChainFreight integrates with ChainIQ for risk scoring:

```python
# After creating a shipment, get risk score
POST http://chainiq-service/score/shipment
{
  "shipment_id": "123",
  "origin": "Los Angeles, CA",
  "destination": "Chicago, IL"
}

# Use risk score in decision-making
if risk_score > 0.8:
    # High risk: require additional verification
    # Assign experienced driver
    # Increase insurance coverage
``` text

## Integration with ChainBoard

ChainFreight can reference drivers from ChainBoard:

```python
# Validate driver exists
GET http://chainboard-service/drivers/{driver_id}

# Associate driver with shipment (future enhancement)
{
  "shipment_id": "123",
  "driver_id": 42,
  "status": "picked_up"
}
``` text

## Development

### Adding New Shipment Fields

1. Update `models.py` - add SQLAlchemy column
2. Update `schemas.py` - add Pydantic field
3. Update `main.py` - handle in endpoints
4. Database will auto-migrate on startup

### Handling Exceptions

```python
# Create exception model
exception = ShipmentException(
    shipment_id=123,
    exception_type="delayed",
    description="Traffic on I-80",
    timestamp=datetime.now()
)
``` text

### Testing

```bash
# Create a shipment
curl -X POST "http://localhost:8002/shipments" \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name": "Test Co",
    "origin": "LA",
    "destination": "Chicago",
    "pickup_date": "2025-11-08T08:00:00",
    "planned_delivery_date": "2025-11-15T12:00:00"
  }'

# List shipments
curl "http://localhost:8002/shipments"

# Update shipment status
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_transit"}'
``` text

## Database

### Local Development

Uses SQLite by default:

```bash
# Database file is created automatically
ls chainfreight.db
``` text

### Production (PostgreSQL)

Set environment variable:

```bash
DATABASE_URL=postgresql://user:password@localhost/chainfreight
``` text

## Future Enhancements

- [ ] Real-time GPS tracking integration
- [ ] Proof of delivery (POD) capture
- [ ] Exception/incident reporting
- [ ] Driver assignment optimization
- [ ] Integration with carrier APIs
- [ ] Customs/compliance documentation
- [ ] Multi-pickup/drop-off shipments
- [ ] Shipment weight and volume tracking
- [ ] Hazmat and special handling flags
- [ ] Customer notifications (SMS/Email)
- [ ] API rate limiting and authentication
- [ ] Webhook support for event notifications

## Contributing

Follow these patterns when extending ChainFreight:

1. **Type hints**: Always use full type hints
2. **Pydantic schemas**: Separate request/response models
3. **Dependency injection**: Use FastAPI's `Depends()` for DB sessions
4. **Error handling**: Return appropriate HTTP status codes
5. **Documentation**: Add docstrings to all functions
6. **Status tracking**: Always update timestamps on changes

## License

Proprietary - ChainBridge Platform
