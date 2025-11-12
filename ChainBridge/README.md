# BensonBot – Multi-Signal Decision Bot with Modular Architecture

[![Tests](https://github.com/BIGmindz/ChainBridge/workflows/Tests/badge.svg)](https://github.com/BIGmindz/ChainBridge/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/BIGmindz/ChainBridge/branch/main/graph/badge.svg)](https://codecov.io/gh/BIGmindz/ChainBridge)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

BensonBot is a sophisticated multi-signal cryptocurrency decision bot built with a modular architecture to support both Light and Enterprise versions. The system provides flexible data ingestion, ML-powered analysis, and automated decision-making capabilities with market regime detection to optimize trading strategies for bull, bear, and sideways markets.

## 🚀 New Features - September 17, 2025 Update

### 📡 New Listings Radar

- Detects new coin listings on major exchanges in real-time

- Implements risk filters and confidence scoring for trading opportunities

- Generates trade signals with entry timing, stop-loss, and take-profit levels

- 20-40% average returns per successful listing

### 🌐 Region-Specific Crypto Mapping

- Maps macroeconomic signals to specific cryptocurrencies by region

- Targets the right assets for regional economic conditions

- Integrates with global macro module for comprehensive signal generation

### 📊 System Monitoring and Dashboard

- Real-time monitoring of all system components

- Trading performance dashboard with key metrics

- Automatic restart of critical components if they fail

- Resource usage tracking and optimization

## 🚀 Previous Features - Professional Budget Management & Volatile Crypto Selection

The latest version includes professional budget management with Kelly Criterion position sizing, automatic selection of the most volatile cryptocurrencies, and a comprehensive multi-signal approach combining RSI, MACD, Bollinger Bands, Volume Profile, and Sentiment Analysis.

### 💰 Professional Budget Management

- Kelly Criterion position sizing for mathematically optimal growth

- Risk management with stop-loss and take-profit

- Portfolio tracking with performance dashboard

- Dynamic risk adjustment based on drawdown

- Capital preservation with maximum position limits

### 📊 Volatile Cryptocurrency Selection

- Automatic identification of highest-volatility trading pairs

- Volatility calculation using price standard deviation

- Configuration updates with selected pairs

### 🚢 Logistics-Based Signal Module (NEW!)

- **Forward-looking signals** (30-45 days) based on supply chain metrics

- **Ultra-low correlation** (0.05) with traditional signals

- **Competitive advantage**: No other bot has these signals

- Port congestion analysis for inflation hedge predictions

- Diesel price monitoring for mining cost economics

- Container rate tracking for supply chain stress indicators

- Predictive power superior to lagging technical indicators

### One-Step Trading System

```bash

## Start the complete automated trading system

./start_trading.sh

## Run in test mode to verify functionality

./start_trading.sh --test

## Run performance analysis on your trading history

./start_trading.sh --analyze

## Set up enhanced trading with volatile cryptos and budget management

python3 run_enhanced_bot_setup.py

## Monitor performance in real-time

python3 monitor_performance.py

```text

### Individual Components

```bash

## Find the most volatile cryptocurrencies to trade

python3 dynamic_crypto_selector.py
python3 src/crypto_selector.py  # Alternative implementation

## Run the multi-signal trading bot with budget management

python3 multi_signal_bot.py

## Test the budget manager independently

python3 budget_manager.py

## Analyze trading performance with visualizations

python3 analyze_trading_performance.py

## Full automated system (selection + trading)

python3 automated_trader.py

## Monitor portfolio in real-time

python3 monitor_performance.py

```text

### Legacy API and Bot Compatibility

```bash

## Install dependencies

pip install -r requirements.txt

## Start the API server

python benson_system.py --mode api-server

## Run the original RSI bot functionality

python benson_system.py --mode rsi-compat --once

```text

## 🔐 Security Configuration

BensonBot prioritizes security by using environment variables for sensitive data. **Never commit API keys or secrets to version control.**

### Setting Up API Credentials

1. **Copy the environment template:**

   ```bash

   cp .env.example .env

   ```

1. **Edit `.env` with your credentials:**

   ```bash

   # Replace placeholder values with your actual API credentials

   API_KEY="your_actual_api_key_here"
   API_SECRET="your_actual_api_secret_here"
   EXCHANGE="kraken"  # or your preferred exchange

   ```

1. **Verify `.env` is in your `.gitignore`:**

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

```text

### Security Best Practices

- ✅ **DO**: Store API keys in environment variables or secure vaults

- ✅ **DO**: Use paper trading (`PAPER="true"`) for testing

- ✅ **DO**: Regularly rotate API keys

- ❌ **DON'T**: Commit `.env` files or API keys to version control

- ❌ **DON'T**: Share API keys in chat, logs, or screenshots

- ❌ **DON'T**: Use production API keys in development environments

## ✅ Preflight Checks & Market Validation

Before running the bot in live mode (`PAPER=false`), the system performs a preflight check to ensure your configured symbols have exchange-reported minima and valid price data. This prevents creating orders below exchange minimums or acting on symbols with invalid prices (for example, symbols returning a last price of 0.0).

Maintainers can validate a local markets dump (an export of `exchange.markets`) using the helper script:

```bash

.venv/bin/python3 scripts/validate_markets.py /path/to/markets.json

```text

This script reads `config.yaml` to find configured symbols and prints any symbols for which minima could not be detected. Use it during diagnostics or when you update exchange market metadata.

## 🏗️ Enhanced Architecture & Features

### New Trading Components

- **Dynamic Crypto Selector**: Automatically finds the most volatile cryptocurrencies with sufficient volume

- **Multi-Signal Integration**: Combines 5 different trading signals for better decision-making

- **Adaptive Risk Management**: Trading parameters optimized based on each crypto's volatility profile

- **Performance Analysis**: Detailed metrics and visualizations for strategy evaluation

- **Regime Detection**: Optimizes strategies for bull, bear, and sideways markets

### Core Architecture

Benson features a modular architecture with the following components:

- **Core System**: Module management, data processing, and pipeline orchestration

- **API Layer**: RESTful endpoints for system interaction and integration

- **Pluggable Modules**: CSV ingestion, RSI, MACD, Bollinger Bands, Volume Profile, and Sentiment Analysis

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

- **Market Regime Detection**: Automatic identification of bull, bear, and sideways markets

- **Adaptive Signal Optimization**: Regime-specific signal weighting and position sizing

- **Custom Modules**: Extensible framework for additional analysis

### Business Intelligence

- **Metrics Collection**: Automated tracking of usage and performance

- **ROI Calculation**: Business impact measurement and reporting

## 📘 Documentation

- [Regime-Specific Backtesting](./docs/REGIME_SPECIFIC_BACKTESTING.md): Learn how to evaluate trading strategy performance across different market regimes

- [Market Regime Detection](./docs/MARKET_REGIME_DETECTION.md): Understand how the system identifies bull, bear, and sideways markets

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

```text

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

```text

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

```text

### Available Signal Modules

```bash

curl http://localhost:8000/signals/available

```text

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

```text

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

```text

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
