# BensonBot - Multi-Signal ML-Driven Trading Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/BIGmindz/ChainBridge/workflows/Tests/badge.svg)](https://github.com/BIGmindz/ChainBridge/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/BIGmindz/ChainBridge/branch/main/graph/badge.svg)](https://codecov.io/gh/BIGmindz/ChainBridge)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

BensonBot is a sophisticated multi-signal cryptocurrency trading bot that uses uncorrelated signal aggregation and machine learning-powered market regime detection to make intelligent trading decisions across bull, bear, and sideways markets.

## 🎯 What is BensonBot?

BensonBot combines multiple independent trading signals to generate high-confidence BUY/SELL/HOLD decisions. Unlike single-indicator bots, BensonBot aggregates signals with low correlation to create a robust, diversified trading strategy.

### Core Philosophy

1. **Signal Independence**: Use uncorrelated signals for true diversification (target correlation < 0.30)
2. **Adaptive Weighting**: Dynamically adjust signal importance based on market conditions
3. **Regime Detection**: Optimize strategy for current market regime (bull/bear/sideways)
4. **Risk Management**: Professional position sizing with Kelly Criterion and stop-loss/take-profit
5. **Paper Trading First**: Always test strategies before risking capital

## 🔬 Trading Signals

BensonBot aggregates the following uncorrelated signals:

### 1. RSI (Relative Strength Index)
**Type**: Momentum oscillator  
**Purpose**: Identify overbought/oversold conditions  
**Thresholds**:
- BUY: RSI < 35 (oversold)
- SELL: RSI > 64 (overbought)
- HOLD: Between 35-64

**Correlation with other signals**: Low (< 0.25)

### 2. MACD (Moving Average Convergence Divergence)
**Type**: Trend-following momentum indicator  
**Purpose**: Detect trend changes and momentum shifts  
**Signal**: Bullish/bearish crossovers and histogram analysis

**Correlation with RSI**: ~0.15 (uncorrelated)

### 3. Volume Analysis
**Type**: Volume-based indicator  
**Purpose**: Confirm price movements with volume validation  
**Signal**: Volume spikes, unusual activity, volume-price divergence

**Correlation with technical indicators**: ~0.10 (uncorrelated)

### 4. Bollinger Bands
**Type**: Volatility indicator  
**Purpose**: Identify volatility expansion/contraction  
**Signal**: Price touching bands, band squeeze, bandwidth

**Correlation with momentum**: ~0.20 (low correlation)

### 5. Sentiment Analysis
**Type**: Alternative data  
**Purpose**: Gauge market sentiment from news, social media  
**Signal**: Sentiment scores, fear/greed index

**Correlation with technical**: ~0.05 (highly uncorrelated)

### 6. Logistics Signals (Proprietary)
**Type**: Supply chain data  
**Purpose**: Forward-looking (30-45 day) predictions  
**Metrics**:
- Port congestion (inflation hedge prediction)
- Diesel prices (mining cost economics)
- Container rates (supply chain stress)

**Correlation**: Ultra-low (< 0.05) - **Competitive advantage**

### 7. ML Regime Detection
**Type**: Machine learning  
**Purpose**: Identify bull/bear/sideways market regimes  
**Output**: Current regime + confidence score

Adapts strategy parameters based on detected market regime.

## 🏗️ Architecture

### Entry Points

#### `src/main.py` (Main Entry Point)
```bash
# Paper trading (safe testing)
python -m src.main --mode paper

# Live trading (requires confirmation)
python -m src.main --mode live --confirm-live

# Backtesting
python -m src.main --mode backtest

# Alternatively, use direct path
python src/main.py --mode paper
```

#### `src/tests.py` (Built-in Tests)
```bash
# Run built-in unit tests
python -m src.tests

# Or use pytest if available
pytest src/tests.py -v
```

#### `start_trading.sh` (Automated System)
```bash
# Complete trading system
./start_trading.sh

# Test mode
./start_trading.sh --test

# Performance analysis
./start_trading.sh --analyze
```

### Core Components

```
BensonBot Architecture
│
├── Trading Engine (src/core/unified_trading_engine.py)
│   ├── Signal aggregation
│   ├── Decision logic
│   └── Order execution
│
├── Signal Processors (modules/)
│   ├── RSI Module
│   ├── MACD Module
│   ├── Volume Module
│   ├── Sentiment Module
│   └── Logistics Module
│
├── Market Regime Detection (modules/market_regime_module/)
│   ├── Regime classifier
│   ├── Strategy selector
│   └── Parameter optimizer
│
├── Risk Management (modules/risk_management/)
│   ├── Position sizing (Kelly Criterion)
│   ├── Stop-loss management
│   └── Take-profit targets
│
├── Adaptive Weights (modules/adaptive_weight_module/)
│   ├── Signal performance tracking
│   ├── Dynamic weight adjustment
│   └── Regime-specific weighting
│
└── Strategies (strategies/)
    ├── Bull market config
    ├── Bear market config
    └── Sideways market config
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- pip package manager
- Exchange API credentials (Kraken, Binance, etc.)

### Installation

1. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

4. **Validate installation**
   ```bash
   # Run built-in tests
   python -m src.tests
   
   # Or if pytest is installed
   pytest src/tests.py -v
   ```

### Configuration

Edit `.env` file:
```bash
# Exchange Configuration
EXCHANGE=kraken                    # Exchange to use
API_KEY=your_api_key_here          # API key
API_SECRET=your_api_secret_here    # API secret

# Trading Mode
PAPER=true                         # Paper trading (false for live)

# Symbols (comma-separated)
SYMBOLS=BTC/USD,ETH/USD,SOL/USD

# RSI Thresholds (canonical values)
RSI_BUY_THRESHOLD=35
RSI_SELL_THRESHOLD=64

# Risk Management
STOP_LOSS_PCT=0.05                 # 5% stop-loss
TAKE_PROFIT_PCT=0.10               # 10% take-profit
MAX_POSITION_SIZE=0.20             # Max 20% of portfolio
```

## 🧪 Testing

### Built-in Unit Tests

```bash
# Run RSI calculation tests
python -m src.tests

# Or with pytest
pytest src/tests.py -v

# Expected output: All tests PASS
# - Flatline test
# - Uptrend test  
# - Downtrend test
# - Insufficient data handling
# - Edge case handling
```

### Paper Trading

**Always start with paper trading** to validate strategy:

```bash
# Paper trading mode (no real money)
python -m src.main --mode paper

# Monitor for 24-48 hours
# Review performance metrics
```

### Backtesting

```bash
# Run backtesting on historical data
python -m src.main --mode backtest

# Regime-specific backtesting
python strategies/bull_market/backtest.py
python strategies/bear_market/backtest.py
python strategies/sideways_market/backtest.py
```

### Integration Tests

```bash
# Run test suite (if exists)
pytest tests/ -v -k trading

# Test signal modules
pytest tests/test_signals.py -v

# Test risk management
pytest tests/test_risk_management.py -v
```

## 📊 Live Trading

### Safety Requirements

**Live trading requires explicit confirmation flag:**

```bash
# This will NOT work (safe by design)
python -m src.main --mode live

# This WILL work (explicit confirmation)
python -m src.main --mode live --confirm-live
```

### Pre-Flight Checklist

Before going live:

- [ ] Tested in paper trading mode for 48+ hours
- [ ] Reviewed and understood all configuration parameters
- [ ] Set appropriate risk limits (stop-loss, position size)
- [ ] Verified API credentials and exchange connection
- [ ] Tested emergency stop procedure
- [ ] Backed up configuration files
- [ ] Set up monitoring/alerts

### Monitoring

```bash
# Real-time monitoring dashboard
python apps/dashboard/monitor.py

# Alternative Streamlit dashboard
streamlit run apps/dashboard/streamlit_dashboard.py

# Command-line monitoring
./monitor.sh
```

## 🎛️ Configuration Deep Dive

### Market Regime Strategies

Located in `strategies/`:

#### Bull Market (`strategies/bull_market/`)
- Aggressive position sizing
- Higher RSI thresholds
- Trend-following emphasis
- Longer holding periods

#### Bear Market (`strategies/bear_market/`)
- Conservative position sizing
- Lower RSI thresholds
- Mean-reversion emphasis
- Tighter stop-losses

#### Sideways Market (`strategies/sideways_market/`)
- Moderate position sizing
- Range-bound trading
- Quick profit-taking
- Reduced exposure

### Signal Weights

Adaptive weights adjust based on:
- Historical signal performance
- Current market regime
- Signal correlation changes
- Recent accuracy metrics

Default weights:
```python
{
    "rsi": 0.20,
    "macd": 0.15,
    "volume": 0.15,
    "bollinger": 0.15,
    "sentiment": 0.10,
    "logistics": 0.25  # Higher weight for uncorrelated signal
}
```

## 📈 Performance Tracking

### Metrics

BensonBot tracks:
- Win rate
- Sharpe ratio
- Maximum drawdown
- Average return per trade
- Signal accuracy by type
- Regime detection accuracy

### Reports

```bash
# Generate performance report
python analyze_trading_performance.py

# View trading history
cat reports/trading_performance_report.json

# Dashboard visualization
python apps/dashboard/monitor.py
```

## 🔒 Security & Safety

### API Key Management

**Never commit API keys to version control:**
- ✅ Store in `.env` file
- ✅ Use environment variables
- ✅ Rotate keys regularly
- ❌ Never hardcode in source
- ❌ Never share in logs/screenshots

### Paper Trading Mode

**Default mode is paper trading** for safety:
- Simulated trades with real market data
- No real money at risk
- Test strategies safely
- Validate configuration

### Stop-Loss Protection

All positions have automatic stop-loss:
- Configurable percentage (default: 5%)
- Executed automatically
- No manual intervention required

## 🗺️ Roadmap

### Phase 1: Core Functionality (Complete)
- [x] Multi-signal aggregation
- [x] RSI, MACD, Volume, Bollinger signals
- [x] Paper trading mode
- [x] Basic risk management

### Phase 2: ML Enhancement (Complete)
- [x] Market regime detection
- [x] Adaptive signal weighting
- [x] Regime-specific strategies
- [x] Sentiment analysis integration

### Phase 3: Advanced Features (Complete)
- [x] Logistics signal module
- [x] Kelly Criterion position sizing
- [x] Real-time monitoring dashboards
- [x] Comprehensive backtesting

### Phase 4: Scaling (In Progress)
- [ ] Multi-exchange support expansion
- [ ] Portfolio rebalancing
- [ ] Advanced ML models (LSTM, Transformer)
- [ ] Social trading features
- [ ] Mobile app

## 📚 Additional Documentation

- [Market Regime Detection](../MARKET_REGIME_DETECTION.md) - ML regime classifier
- [Regime-Specific Backtesting](../REGIME_SPECIFIC_BACKTESTING.md) - Strategy evaluation
- [Regime-Based Strategies](../REGIME_BASED_STRATEGIES.md) - Market-specific configs
- [Kraken Paper Trading](../KRAKEN_PAPER_TRADING.md) - Exchange-specific guide

## 🤝 Contributing

See root [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

**BensonBot-specific:**
- Use `feat/bensonbot-*` branch naming
- All signals must be tested
- Maintain signal independence (correlation < 0.30)
- Paper trading validation required

## 🔬 Research & Development

Interested in signal development?

1. **New Signal Criteria:**
   - Low correlation with existing signals (< 0.30)
   - Forward-looking preferred
   - Validated on historical data
   - Clear BUY/SELL/HOLD logic

2. **Testing Requirements:**
   - Backtesting on 1+ year data
   - Correlation analysis with existing signals
   - Performance metrics (Sharpe, win rate)
   - Regime-specific performance

3. **Integration Process:**
   - Create signal module in `modules/`
   - Add unit tests
   - Update aggregation logic
   - Document in this README

## 📜 License

MIT License - Part of the BIGmindz trading system.

---

**⚠️ Risk Disclaimer**: Cryptocurrency trading involves substantial risk. BensonBot is provided as-is with no guarantees. Always start with paper trading. Never invest more than you can afford to lose. Past performance does not indicate future results.

**Questions?** Open an issue or check the [Repository Map](../REPO_MAP.md).

**Parent Repo:** [BIGmindz/ChainBridge](https://github.com/BIGmindz/ChainBridge)
