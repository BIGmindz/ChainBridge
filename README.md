# BensonBot – Multi-Signal Decision Bot with Modular Architecture

BensonBot is a sophisticated multi-signal cryptocurrency decision bot built with a modular architecture to support both Light and Enterprise versions. The system provides flexible data ingestion, ML-powered analysis, and automated decision-making capabilities.

## 🚀 Quick Start

### API Server (Recommended)
```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
python benson_system.py --mode api-server

# Access the API documentation
open http://localhost:8000/docs
```

### Docker Deployment
```bash
# Start the complete system
docker-compose up benson-api

# Access the API
curl http://localhost:8000/health
```

### Legacy RSI Bot Compatibility
```bash
# Run the original RSI bot functionality
python benson_system.py --mode rsi-compat --once

# Or use the original bot directly
python benson_rsi_bot.py --once
```

## 🏗️ Architecture Overview

Benson features a modular architecture with the following components:

- **Core System**: Module management, data processing, and pipeline orchestration
- **API Layer**: RESTful endpoints for system interaction and integration
- **Pluggable Modules**: CSV ingestion, RSI analysis, sales forecasting, and more
- **Business Impact Tracking**: ROI metrics, usage analytics, and adoption tracking
- **Cloud-Native Design**: Containerized deployment with scalability support

## 📊 Available Modules

### Data Ingestion
- **CSV Ingestion**: Process CSV files with flexible column mapping
- **Alternative Data**: Geopolitical and sentiment data integration

### Analysis & ML
- **RSI Module**: Technical analysis with Wilder's RSI calculation
- **Sales Forecasting**: ML-powered sales predictions with trend analysis
- **Custom Modules**: Extensible framework for additional analysis

### Business Intelligence
- **Metrics Collection**: Automated tracking of usage and performance
- **ROI Calculation**: Business impact measurement and reporting

## 🔧 API Examples

### Execute RSI Analysis
```bash
curl -X POST http://localhost:8000/modules/RSIModule/execute \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "RSIModule",
    "input_data": {
      "price_data": [{"close": 45000}, {"close": 45100}]
    }
  }'
```

### Process CSV Data
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
        {"date": "2024-01-01", "amount": 15000}
      ],
      "forecast_periods": 5
    }
  }'
```

## 🧪 Testing

```bash
# Run comprehensive system tests
python benson_system.py --mode test

# Test original RSI functionality
python benson_rsi_bot.py --test
```

## 📈 Business Impact Features

- **Automation Savings**: Tracks time saved through automated processes
- **Usage Analytics**: Module execution patterns and adoption metrics  
- **ROI Reporting**: Cost-benefit analysis of system usage
- **Performance Monitoring**: Error rates, execution times, and reliability metrics

View metrics:
```bash
curl http://localhost:8000/metrics
```

## 🔌 Extensibility

Create custom modules by extending the base `Module` class:

```python
from core.module_manager import Module

class CustomAnalyzer(Module):
    def process(self, data):
        # Your custom logic here
        return {"result": "processed"}
```

Register and use:
```bash
curl -X POST http://localhost:8000/modules/register \
  -d '{"module_name": "CustomAnalyzer", "module_path": "path.to.module"}'
```

## 📋 Configuration

### Environment Variables
- `PORT`: API server port (default: 8000)
- `HOST`: API server host (default: 0.0.0.0) 
- `BENSON_CONFIG`: Configuration file path

### Module Configuration
Configure modules with custom parameters:
```python
{
  "rsi": {
    "period": 14,
    "buy_threshold": 30,
    "sell_threshold": 70
  }
}
```

## 🐳 Docker Support

Multiple deployment options:
```bash
# API server mode
docker-compose up benson-api

# Legacy RSI bot mode  
docker-compose --profile legacy up benson-legacy

# One-time RSI analysis
docker-compose --profile rsi-only up benson-rsi
```

## 📚 Documentation

- [Modular Architecture Guide](MODULAR_ARCHITECTURE.md)
- [API Documentation](http://localhost:8000/docs) (when running)
- [Module Development Guide](MODULAR_ARCHITECTURE.md#creating-custom-modules)

## 🛠️ Development

### Project Structure
```
├── core/                   # Core system components
├── modules/               # Pluggable analysis modules
├── api/                   # REST API server
├── tracking/              # Business impact tracking
├── sample_data/           # Example data files
├── config/                # Configuration files
└── benson_system.py       # Main entry point
```

### Running Tests
```bash
make test                  # Run all tests
python benson_system.py --mode test  # System tests
```

## 🌟 Features

- ✅ Modular, extensible architecture
- ✅ REST API with OpenAPI documentation  
- ✅ Multiple data ingestion formats
- ✅ Advanced RSI analysis with Wilder's smoothing
- ✅ ML-powered sales forecasting
- ✅ Business impact tracking and ROI metrics
- ✅ Docker containerization support
- ✅ Cloud-native deployment ready
- ✅ Backward compatibility with existing RSI bot

## 🤝 Contributing

1. Create custom modules following the `Module` interface
2. Add new API endpoints for additional functionality
3. Extend business impact tracking for new metrics
4. Improve ML models and forecasting accuracy

## 📄 License

This project is part of the BIGmindz Multiple Signal Decision Bot system.

---

**Get started with the modular Benson system today and unlock scalable, automated decision-making capabilities!**
