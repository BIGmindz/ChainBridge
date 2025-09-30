# Benson Modular Architecture Documentation

## Overview

Benson is a multi-signal decision bot built with a modular architecture to support both Light and Enterprise versions. The system provides a flexible, extensible framework for data ingestion, analysis, and ML-powered decision making.

## Architecture Components

### 1. Core System (`core/`)

The foundation of the modular architecture:

- **ModuleManager** (`core/module_manager.py`): Manages plugin-and-play module loading and execution
- **DataProcessor** (`core/data_processor.py`): Handles data normalization and validation
- **Pipeline** (`core/pipeline.py`): Orchestrates multi-step processing workflows

### 2. Modules (`modules/`)

Pluggable modules for specific functionality:

- **CSVIngestionModule** (`modules/csv_ingestion.py`): CSV file ingestion and processing
- **RSIModule** (`modules/rsi_module.py`): RSI calculation and trading signals
- **SalesForecastingModule** (`modules/sales_forecasting.py`): ML-powered sales forecasting

### 3. API Layer (`api/`)

REST API for system interaction:

- **FastAPI Server** (`api/server.py`): RESTful API endpoints for module execution and management
- Swagger/OpenAPI documentation at `/docs`
- Health checks and monitoring endpoints

### 4. Business Impact Tracking (`tracking/`)

Metrics and ROI measurement:

- **MetricsCollector** (`tracking/metrics_collector.py`): Comprehensive usage and business impact tracking
- ROI calculation and adoption metrics
- Error tracking and reliability metrics

## Getting Started

### Installation

```bash
pip install -r requirements.txt
```

### Running the System

1. **API Server Mode (Recommended)**:
   ```bash
   python benson_system.py --mode api-server --port 8000
   ```

2. **RSI Compatibility Mode**:
   ```bash
   python benson_system.py --mode rsi-compat --once
   ```

3. **System Tests**:
   ```bash
   python benson_system.py --mode test
   ```

### Docker Deployment

```bash
# Start API server
docker-compose up benson-api

# Start legacy RSI bot
docker-compose --profile legacy up benson-legacy
```

## API Usage Examples

### Health Check
```bash
curl http://localhost:8000/health
```

### List Available Modules
```bash
curl http://localhost:8000/modules
```

### Execute RSI Analysis
```bash
curl -X POST http://localhost:8000/modules/RSIModule/execute \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "RSIModule",
    "input_data": {
      "price_data": [
        {"close": 45000, "timestamp": "2024-01-01T00:00:00Z"},
        {"close": 45100, "timestamp": "2024-01-01T00:05:00Z"}
      ]
    }
  }'
```

### Ingest CSV Data
```bash
curl -X POST http://localhost:8000/modules/CSVIngestionModule/execute \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "CSVIngestionModule",
    "input_data": {
      "file_path": "sample_data/btc_price_data.csv"
    }
  }'
```

### Sales Forecasting
```bash
curl -X POST http://localhost:8000/modules/SalesForecastingModule/execute \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "SalesForecastingModule",
    "input_data": {
      "historical_sales": [
        {"date": "2024-01-01", "amount": 15000},
        {"date": "2024-01-02", "amount": 16200}
      ],
      "forecast_periods": 5
    }
  }'
```

### View Metrics and ROI
```bash
curl http://localhost:8000/metrics
```

## Creating Custom Modules

To create a new module, inherit from the base `Module` class:

```python
from core.module_manager import Module
from typing import Dict, Any

class CustomModule(Module):
    VERSION = "1.0.0"

    def get_schema(self) -> Dict[str, Any]:
        return {
            'input': {'data': 'string'},
            'output': {'result': 'string'}
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Your custom processing logic here
        return {'result': 'processed'}
```

Register the module:
```bash
curl -X POST http://localhost:8000/modules/register \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "CustomModule",
    "module_path": "path.to.your.module"
  }'
```

## Creating Pipelines

Pipelines chain multiple modules together:

```bash
curl -X POST http://localhost:8000/pipelines \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_name": "data_analysis_pipeline",
    "steps": [
      {"name": "ingest", "module_name": "CSVIngestionModule"},
      {"name": "analyze", "module_name": "RSIModule"}
    ]
  }'
```

Execute pipeline:
```bash
curl -X POST http://localhost:8000/pipelines/data_analysis_pipeline/execute \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_name": "data_analysis_pipeline",
    "input_data": {"file_path": "data.csv"}
  }'
```

## Business Impact Features

The system automatically tracks:

- **Usage Metrics**: Module executions, pipeline runs, data volumes
- **Adoption Metrics**: Daily active modules, feature usage patterns
- **ROI Metrics**: Automation time savings, cost reduction estimates
- **Reliability Metrics**: Error rates, uptime, success rates

Access business impact reports:
```bash
curl http://localhost:8000/metrics/modules
curl http://localhost:8000/metrics/pipelines
```

## Configuration

### Environment Variables

- `PORT`: API server port (default: 8000)
- `HOST`: API server host (default: 0.0.0.0)
- `BENSON_CONFIG`: Path to configuration file

### Module Configuration

Modules can be configured when loaded:
```python
module_manager.load_module("modules.rsi_module", {
    "period": 14,
    "buy_threshold": 30,
    "sell_threshold": 70
})
```

## Cloud-Native Deployment

The system is designed for containerized deployment:

### Kubernetes Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: benson-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: benson-api
  template:
    metadata:
      labels:
        app: benson-api
    spec:
      containers:
      - name: benson-api
        image: benson:latest
        ports:
        - containerPort: 8000
        env:
        - name: PORT
          value: "8000"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Serverless Deployment

The API can be deployed on AWS Lambda, Google Cloud Functions, or Azure Functions using appropriate adapters.

## Monitoring and Observability

- Health checks at `/health`
- Metrics collection and export
- Error tracking and alerting
- Performance monitoring

## Security Considerations

- API authentication (implement as needed)
- Input validation and sanitization
- Rate limiting
- Secure module loading

## Extending the System

1. **Add New Data Sources**: Create ingestion modules for different data formats
2. **Add ML Models**: Integrate new forecasting or analysis algorithms
3. **Add Business Logic**: Create domain-specific processing modules
4. **Add Connectors**: Integrate with external APIs and services

## Support and Troubleshooting

- Run system tests: `python benson_system.py --mode test`
- Check logs for error messages
- Validate module schemas before execution
- Use the `/docs` endpoint for API documentation
