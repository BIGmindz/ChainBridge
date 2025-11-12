# ChainIQ Service

Machine learning decision engine for logistics optimization and risk scoring on the ChainBridge platform.

## Overview

ChainIQ is responsible for:

- Shipment risk scoring
- Driver reliability assessment
- Lane optimization recommendations
- Anomaly detection and fraud prevention
- Predictive ETA and delivery reliability

## Tech Stack

- **Framework**: FastAPI
- **ML Framework**: TensorFlow / Scikit-Learn (to be integrated)
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
uvicorn app.main:app --reload --port 8001

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

The API will be available at `http://localhost:8001`

### API Documentation

Visit `http://localhost:8001/docs` for interactive Swagger documentation.

## API Endpoints

### Health Check

```http
GET /health
```

Returns service status.

### Score Shipment

```http
POST /score/shipment
Content-Type: application/json
```

```json
{
  "shipment_id": "SHIP-12345",
  "driver_id": 42,
  "origin": "Los Angeles, CA",
  "destination": "Chicago, IL",
  "planned_delivery_date": "2025-11-15T12:00:00"
}
```

Response:

```json
{
  "shipment_id": "SHIP-12345",
  "risk_score": 0.35,
  "risk_category": "low",
  "confidence": 0.92,
  "reasoning": "Historical performance on this lane is excellent. Driver has 99% on-time delivery."
}
```

**Risk Score**: 0.0 (low risk) to 1.0 (high risk)
**Risk Category**: `"low"` | `"medium"` | `"high"`

## Project Structure

```text
chainiq-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and routes
│   ├── engine.py            # Scoring and ML logic
│   ├── features.py          # Feature engineering (future)
│   ├── models.py            # ML model wrappers (future)
│   └── risk_engine.py       # Risk calculation (future)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Current Implementation

ChainIQ currently provides a **placeholder implementation** with deterministic scoring based on shipment ID hashing. This allows:

- API contract validation
- Integration testing with other services
- Foundation for ML engine replacement

### Placeholder Scoring Logic

```python
hash_value = hash(shipment_id)
risk_score = (abs(hash_value) % 100) / 100.0
```

## Real ML Engine (Roadmap)

The real ChainIQ engine will integrate:

### 1. **Feature Engineering** (`features.py`)

Extract signals from:

- Historical shipment data (transit time, exceptions)
- Driver performance metrics (on-time %, accident rate)
- Route characteristics (distance, terrain, weather)
- Market conditions (lane demand, pricing volatility)
- Global macro indicators (fuel prices, regulatory changes)

### 2. **Adaptive Weighting** (from legacy crypto engine)

Reuse the adaptive weight module to dynamically weight multiple signals:

- Shipment-specific risk factors
- Driver reliability indicators
- Lane historical performance
- Market conditions

### 3. **Regime Detection**

Adapt market regime detection for logistics:

- Peak season vs off-peak
- Regional demand patterns
- Seasonal carrier capacity
- Regulatory changes

### 4. **Risk Scoring**

Combine signals into a composite risk score using:

- Multi-signal aggregation
- Confidence weighting
- Anomaly detection
- Real-time recalibration

## Integration with Other Services

### ChainBoard Integration

```python
# Get driver info from ChainBoard
GET /drivers/{driver_id}  # ChainBoard

# Use in scoring
score = score_shipment(
    shipment_id="SHIP-123",
    driver_id=42,  # Validate driver exists
    origin="Los Angeles",
    destination="Chicago"
)
```

### ChainFreight Integration

```python
# Get shipment details from ChainFreight
GET /shipments/{shipment_id}  # ChainFreight

# Score and update shipment with risk level
PUT /shipments/{shipment_id}
{
  "risk_score": 0.35,
  "status": "in_transit"
}
```

## Development

### Adding New Scoring Signals

1. Extract features in `features.py`
2. Normalize/scale features
3. Add weighting to `risk_engine.py`
4. Update `engine.score_shipment()` to use new signals

### Testing Placeholder Implementation

```bash
curl -X POST "http://localhost:8001/score/shipment" \
  -H "Content-Type: application/json" \
  -d '{"shipment_id": "SHIP-999", "driver_id": 1}'
```

## ML Engine Refactoring Plan

The existing ChainBridge repo includes a sophisticated multi-signal crypto trading engine with:

- **Adaptive weights** (`modules/adaptive_weight_module/`)
- **Market regime detection** (`modules/market_regime_module/`)
- **Risk management** (`modules/risk_management/`)
- **Multi-source data ingestion** (alternative data, global macro, etc.)

**Refactoring Strategy**:

1. Extract generic feature engineering logic
2. Replace market-specific signals with logistics signals
3. Adapt regime detection for seasonal/regional patterns
4. Expose scoring via REST API

See `COPILOT_CONTEXT.md` for detailed refactoring prompts.

## Future Enhancements

- [ ] Train models on historical ChainBridge data
- [ ] Real-time feature store integration
- [ ] Model performance monitoring and retraining
- [ ] Explainability/interpretability (LIME, SHAP)
- [ ] A/B testing framework for model versions
- [ ] Integration with demand forecasting
- [ ] Carrier price negotiation optimization
- [ ] Route optimization engine

## Environment Variables

Create a `.env` file:

```bash
# API Configuration
API_PORT=8001

# ML Model Configuration
MODEL_PATH=./models
USE_GPU=false
```

## Contributing

Follow these patterns when extending ChainIQ:

1. **Type hints**: Always use full type hints
2. **Pydantic schemas**: Separate request/response models
3. **Separation of concerns**: API logic vs ML logic
4. **Testability**: Functions designed for unit testing
5. **Documentation**: Document scoring methodology
6. **Explainability**: Include reasoning in responses

## License

Proprietary - ChainBridge Platform
