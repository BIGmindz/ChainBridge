# ChainBridge Service Architecture

This document provides an overview of the microservices architecture for the ChainBridge platform.

## Platform Overview

ChainBridge is an operating system for logistics built around three core services and one ML decision engine:

```text
┌─────────────────────────────────────────────────────────────────┐
│                    ChainBridge Platform                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐     ┌──────────────┐  │
│  │ ChainBoard   │      │ ChainFreight │     │  ChainPay    │  │
│  │   (Identity) │      │(Shipments)   │     │(Payments)    │  │
│  └──────────────┘      └──────────────┘     └──────────────┘  │
│         ▲                      ▲                    ▲            │
│         │                      │                    │            │
│         └──────────────────────┼────────────────────┘            │
│                                │                                │
│                         ┌──────▼───────┐                       │
│                         │   ChainIQ    │                       │
│                         │(ML Scoring)  │                       │
│                         └──────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Services

### ChainBoard (Port 8000)

**Purpose**: Driver identity and enterprise onboarding

**Key Endpoints**:

- `POST /drivers` - Register a driver
- `GET /drivers` - List drivers
- `GET /drivers/{id}` - Get driver details
- `PUT /drivers/{id}` - Update driver
- `DELETE /drivers/{id}` - Soft-delete driver
- `GET /drivers/search` - Search by email or DOT number

**Database**: SQLite (local) / PostgreSQL (production)

**Models**:

- `Driver`: Contains first_name, last_name, email, phone, dot_number, cdl_number

### ChainFreight (Port 8002)

**Purpose**: Shipment lifecycle and supply chain execution

**Key Endpoints**:

- `POST /shipments` - Create shipment
- `GET /shipments` - List shipments
- `GET /shipments/{id}` - Get shipment details
- `PUT /shipments/{id}` - Update shipment status

**Database**: SQLite (local) / PostgreSQL (production)

**Models**:

- `Shipment`: Contains shipper_name, origin, destination, pickup_date, planned_delivery_date, status

**Status Lifecycle**: `pending` → `picked_up` → `in_transit` → `delivered` | `cancelled`

### ChainPay (Port 8003)

**Purpose**: Payments, settlement, working capital (planned)

**Status**: To be implemented

### ChainIQ (Port 8001)

**Purpose**: ML decision engine for risk scoring and optimization

**Key Endpoints**:

- `POST /score/shipment` - Get risk score for shipment
- `GET /health` - Service health

**Input Features**:

- shipment_id
- driver_id (optional)
- origin, destination
- planned_delivery_date

**Output**: Risk score (0.0-1.0), category (low/medium/high), confidence

**Current Implementation**: Placeholder using deterministic hashing

**Roadmap**:

- Feature engineering from shipment/driver/lane data
- Adaptive weighting system (from legacy crypto engine)
- Real ML model integration
- Anomaly detection

## Service Communication Patterns

### Synchronous API Calls

Services call each other via HTTP for real-time data needs:

```python
# ChainFreight creates a shipment
# → ChainFreight calls ChainIQ to score it
# → ChainIQ returns risk score
# → ChainFreight stores risk in database
```

Example flow:

```python
# 1. Client creates shipment via ChainFreight
POST /shipments
{
  "shipper_name": "ACME",
  "origin": "LA",
  "destination": "Chicago",
  "pickup_date": "2025-11-08",
  "planned_delivery_date": "2025-11-15"
}

# 2. ChainFreight internally calls ChainIQ
chainiq_response = requests.post(
    "http://chainiq:8001/score/shipment",
    json={
      "shipment_id": "123",
      "origin": "LA",
      "destination": "Chicago",
      "planned_delivery_date": "2025-11-15"
    }
)

# 3. ChainFreight stores response
shipment.risk_score = chainiq_response["risk_score"]
shipment.risk_category = chainiq_response["risk_category"]
db.commit()

# 4. Return enriched shipment to client
return shipment  # includes risk_score
```

### Data Reference Patterns

When one service needs data from another:

```python
# ChainFreight needs driver info
driver_response = requests.get(
    f"http://chainboard:8000/drivers/{driver_id}"
)
driver_info = driver_response.json()

# Use driver info in ChainIQ scoring
score_response = requests.post(
    "http://chainiq:8001/score/shipment",
    json={
        "shipment_id": "123",
        "driver_id": driver_id,
        ...
    }
)
```

## Development Workflow

### 1. Local Setup

Each service can run independently:

```bash
# Terminal 1: ChainBoard
cd chainboard-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: ChainFreight
cd chainfreight-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002

# Terminal 3: ChainIQ
cd chainiq-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 2. API Testing

Use the Swagger UIs:

- ChainBoard: `http://localhost:8000/docs`
- ChainFreight: `http://localhost:8002/docs`
- ChainIQ: `http://localhost:8001/docs`

Or use `curl`:

```bash
# Create driver
curl -X POST "http://localhost:8000/drivers" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"John","last_name":"Doe","email":"john@example.com"}'

# Create shipment
curl -X POST "http://localhost:8002/shipments" \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name":"ACME",
    "origin":"LA",
    "destination":"Chicago",
    "pickup_date":"2025-11-08T08:00:00",
    "planned_delivery_date":"2025-11-15T12:00:00"
  }'

# Score shipment
curl -X POST "http://localhost:8001/score/shipment" \
  -H "Content-Type: application/json" \
  -d '{"shipment_id":"123"}'
```

### 3. Database

Each service has its own database:

- ChainBoard: `chainboard.db`
- ChainFreight: `chainfreight.db`
- ChainPay: `chainpay.db` (future)

For development:

```bash
# Delete and recreate
rm chainboard.db chainfreight.db
# Restart services - they auto-create on startup
```

For production, use PostgreSQL:

```bash
# Set environment variables
export DATABASE_URL=postgresql://user:password@postgres-host/chainboard
export DATABASE_URL=postgresql://user:password@postgres-host/chainfreight
```

## Integration Examples

### Example 1: Create Driver + Shipment + Score

```bash
# 1. Register a driver
DRIVER=$(curl -s -X POST "http://localhost:8000/drivers" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice@shipping.com",
    "phone": "555-1234",
    "dot_number": "DOT123456",
    "cdl_number": "CDL789012"
  }')
DRIVER_ID=$(echo $DRIVER | jq '.id')

# 2. Create a shipment
SHIPMENT=$(curl -s -X POST "http://localhost:8002/shipments" \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name": "ACME Corp",
    "origin": "Los Angeles, CA",
    "destination": "Chicago, IL",
    "pickup_date": "2025-11-08T08:00:00",
    "planned_delivery_date": "2025-11-15T12:00:00"
  }')
SHIPMENT_ID=$(echo $SHIPMENT | jq '.id')

# 3. Score the shipment
SCORE=$(curl -s -X POST "http://localhost:8001/score/shipment" \
  -H "Content-Type: application/json" \
  -d "{
    \"shipment_id\": \"$SHIPMENT_ID\",
    \"driver_id\": $DRIVER_ID,
    \"origin\": \"Los Angeles, CA\",
    \"destination\": \"Chicago, IL\",
    \"planned_delivery_date\": \"2025-11-15T12:00:00\"
  }")

# 4. Review risk score
echo "Risk Score: $(echo $SCORE | jq '.risk_score')"
echo "Risk Category: $(echo $SCORE | jq '.risk_category')"
```

### Example 2: Update Shipment Status

```bash
# Transition shipment through lifecycle
curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "picked_up"}'

curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_transit"}'

curl -X PUT "http://localhost:8002/shipments/1" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "delivered",
    "actual_delivery_date": "2025-11-14T14:30:00"
  }'
```

## Architecture Principles

1. **Separation of Concerns**: Each service owns its domain
   - ChainBoard: Identity
   - ChainFreight: Shipment execution
   - ChainPay: Financial transactions
   - ChainIQ: Decision intelligence

2. **Loose Coupling**: Services communicate via REST APIs
   - Can deploy independently
   - Can scale independently
   - Can evolve independently

3. **API-First Design**: All functionality exposed via REST
   - Stateless services
   - Scalable to multiple instances
   - Clear contracts via OpenAPI

4. **Testability**: Each service can be tested independently
   - Unit tests for business logic
   - Integration tests with mock dependencies
   - Contract tests via API

## Deployment

### Docker Compose (Local Development)

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  chainboard:
    build: ./chainboard-service
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: sqlite:///./chainboard.db

  chainfreight:
    build: ./chainfreight-service
    ports:
      - "8002:8002"
    environment:
      DATABASE_URL: sqlite:///./chainfreight.db

  chainiq:
    build: ./chainiq-service
    ports:
      - "8001:8001"

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: chainbridge
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: chainbridge
    ports:
      - "5432:5432"
```

Run:

```bash
docker-compose up -d
```

### Kubernetes (Production)

Each service becomes a Deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chainboard
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chainboard
  template:
    metadata:
      labels:
        app: chainboard
    spec:
      containers:
      - name: chainboard
        image: chainbridge/chainboard:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: chainbridge-secrets
              key: database-url
```

## Monitoring and Logging

### Health Checks

All services provide `/health` endpoint:

```bash
curl http://localhost:8000/health
curl http://localhost:8002/health
curl http://localhost:8001/health
```

### Logging

Each service logs to stdout (container-friendly):

```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"Created shipment {shipment_id}")
```

## Future Enhancements

1. **Event-Driven Architecture**: Add message queue (RabbitMQ/Kafka)
   - Shipment status changes trigger events
   - ChainIQ subscribes to shipment events
   - Asynchronous processing

2. **Service Mesh**: Deploy Istio/Linkerd
   - Automatic retries
   - Circuit breakers
   - Distributed tracing

3. **API Gateway**: Add Kong/Nginx
   - Single entry point
   - Rate limiting
   - Authentication/Authorization

4. **Real ChainPay**: Implement payment service
   - Stripe/PayPal integration
   - Settlement workflows
   - Invoice generation

5. **Real ChainIQ**: Implement ML models
   - Feature store
   - Model versioning
   - A/B testing framework

## References

- See `COPILOT_CONTEXT.md` for Copilot guidance
- See individual service `README.md` files for details
- OpenAPI documentation at each `/docs` endpoint
