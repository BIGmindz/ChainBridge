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

## 🔐 Security Configuration

BensonBot prioritizes security by using environment variables for sensitive data. **Never commit API keys or secrets to version control.**

### Setting Up API Credentials

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**
   ```bash
   # Replace placeholder values with your actual API credentials
   API_KEY="your_actual_api_key_here"
   API_SECRET="your_actual_api_secret_here"
   EXCHANGE="kraken"  # or your preferred exchange
   ```

3. **Verify `.env` is in your `.gitignore`:**
   The `.env` file should never be committed to version control as it contains sensitive credentials.

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `API_KEY` | Exchange API key for live trading | `"ak_1234567890abcdef"` |
| `API_SECRET` | Exchange API secret for live trading | `"sk_abcdef1234567890"` |
| `EXCHANGE` | Exchange to use (kraken, coinbase, binance) | `"kraken"` |
| `PAPER` | Set to "true" for paper trading | `"true"` |

### Configuration Loading

The bot automatically loads environment variables using the `${VARIABLE_NAME}` syntax in `config/config.yaml`:

```yaml
api:
  key: ${API_KEY}
  secret: ${API_SECRET}
```

### Security Best Practices

- ✅ **DO**: Store API keys in environment variables or secure vaults
- ✅ **DO**: Use paper trading (`PAPER="true"`) for testing
- ✅ **DO**: Regularly rotate API keys
- ❌ **DON'T**: Commit `.env` files or API keys to version control
- ❌ **DON'T**: Share API keys in chat, logs, or screenshots
- ❌ **DON'T**: Use production API keys in development environments

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

### Trading Signal Analysis
- **RSI Module**: Technical analysis with Wilder's RSI calculation
- **MACD Module**: Moving Average Convergence Divergence momentum indicator
- **Bollinger Bands Module**: Volatility-based analysis with band squeeze detection
- **Volume Profile Module**: Volume-based support/resistance and POC analysis
- **Sentiment Analysis Module**: Alternative data sentiment scoring from multiple sources
- **Multi-Signal Aggregator**: Intelligent combination of uncorrelated signals

### Machine Learning & Forecasting
- **Sales Forecasting**: ML-powered sales predictions with trend analysis
- **Custom Modules**: Extensible framework for additional analysis

### Business Intelligence
- **Metrics Collection**: Automated tracking of usage and performance
- **ROI Calculation**: Business impact measurement and reporting

## 🔧 API Examples

### Multi-Signal Analysis
```bash
curl -X POST http://localhost:8000/analysis/multi-signal \
  -H "Content-Type: application/json" \
  -d '{
    "price_data": [
      {"close": 45000, "high": 45200, "low": 44800, "volume": 1000},
      {"close": 45100, "high": 45300, "low": 44900, "volume": 1200}
    ],
    "include_individual_signals": true
  }'
```

### Individual Signal Analysis

#### Execute RSI Analysis
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

#### Execute MACD Analysis  
```bash
curl -X POST http://localhost:8000/modules/MACDModule/execute \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "MACDModule", 
    "input_data": {
      "price_data": [{"close": 45000}, {"close": 45100}]
    }
  }'
```

### Available Signal Modules
```bash
curl http://localhost:8000/signals/available
```

### Multi-Signal Backtesting
```bash
curl -X POST http://localhost:8000/analysis/multi-signal/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "historical_data": [
      {"close": 45000, "high": 45200, "low": 44800, "volume": 1000},
      {"close": 45100, "high": 45300, "low": 44900, "volume": 1200}
    ],
    "initial_balance": 10000
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
# Run comprehensive system tests (includes all signal modules)
python benson_system.py --mode test

# Run multi-signal demonstration across market scenarios
python benson_system.py --mode multi-signal-demo

# Run comprehensive integration demo
python multi_signal_demo.py

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

- ✅ **Multi-Signal Architecture**: 6 uncorrelated trading signal modules
- ✅ **Intelligent Signal Aggregation**: Consensus-based decision making  
- ✅ **Risk-Aware Trading**: Automatic risk assessment and position sizing
- ✅ **Signal Independence**: Verified uncorrelated indicators (diversification score: 0.90)
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
