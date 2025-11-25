        {"date": "2024-01-01", "amount": 15000}
      ],
      "forecast_periods": 5
    }
  }'

```text

## 🧪 Testing

```bash

## Run comprehensive system tests (includes all signal modules)

python benson_system.py --mode test

## Run multi-signal demonstration across market scenarios

python benson_system.py --mode multi-signal-demo

## Run comprehensive integration demo

python multi_signal_demo.py

## Test original RSI functionality

python benson_rsi_bot.py --test

```text

### Developer quick checks (lean path)

See README-QUICK-CHECKS.md for a fast, TensorFlow-free validation path and pre-commit setup.

## 📈 Business Impact Features

- **Automation Savings**: Tracks time saved through automated processes

- **Usage Analytics**: Module execution patterns and adoption metrics

- **ROI Reporting**: Cost-benefit analysis of system usage

- **Performance Monitoring**: Error rates, execution times, and reliability metrics

View metrics:

```bash

curl http://localhost:8000/metrics

```text

## 🔌 Extensibility

Create custom modules by extending the base `Module` class:

```python

from core.module_manager import Module

class CustomAnalyzer(Module):
    def process(self, data):

## Your custom logic here

        return {"result": "processed"}

```text

Register and use:

```bash

curl -X POST http://localhost:8000/modules/register \
  -d '{"module_name": "CustomAnalyzer", "module_path": "path.to.module"}'

```text

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

```text

## 🐳 Docker Support

Multiple deployment options:

```bash

## API server mode

docker-compose up benson-api

## Legacy RSI bot mode

docker-compose --profile legacy up benson-legacy

## One-time RSI analysis

docker-compose --profile rsi-only up benson-rsi

```text

## 📚 Additional Documentation

- [Modular Architecture Guide](MODULAR_ARCHITECTURE.md)

- [API Documentation](http://localhost:8000/docs) (when running)

- [Module Development Guide](MODULAR_ARCHITECTURE.md#creating-custom-modules)

## 🛠️ Development

### Project Structure

```plaintext

├── core/                   # Core system components
├── modules/               # Pluggable analysis modules
├── api/                   # REST API server
├── tracking/              # Business impact tracking
├── sample_data/           # Example data files
├── config/                # Configuration files
└── benson_system.py       # Main entry point

```text

### Running Tests

```bash

make test                  # Run all tests
python benson_system.py --mode test  # System tests

```text

## 🌟 Features

- ✅ **Multi-Signal Architecture**: 6 uncorrelated trading signal modules

- ✅ **Intelligent Signal Aggregation**: Consensus-based decision making

- ✅ **Risk-Aware Trading**: Automatic risk assessment and position sizing

- ✅ **Market Regime Detection**: Automatic optimization for bull, bear, and sideways markets ([learn more](docs/MARKET_REGIME_DETECTION.md))

- ✅ **Signal Independence**: Verified uncorrelated indicators (diversification score: 0.90)

- ✅ **Enhanced Machine Learning**: Faster adaptation to changing market conditions

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

1. Add new API endpoints for additional functionality

1. Extend business impact tracking for new metrics

1. Improve ML models and forecasting accuracy

## 📄 License

This project is part of the BIGmindz Multiple Signal Decision Bot system.

---

## Get started with the modular Benson system today and unlock scalable, automated decision-making capabilities
