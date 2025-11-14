# CLAUDE.md - AI Assistant Guide for ChainBridge

**Last Updated**: 2025-11-14
**Repository**: ChainBridge
**Primary Language**: Python 3.11

---

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [Codebase Structure](#codebase-structure)
3. [Technology Stack](#technology-stack)
4. [Development Workflow](#development-workflow)
5. [Configuration Management](#configuration-management)
6. [Module Development Patterns](#module-development-patterns)
7. [Testing Strategy](#testing-strategy)
8. [Git Workflow](#git-workflow)
9. [Key Conventions](#key-conventions)
10. [Common Tasks](#common-tasks)
11. [Safety & Best Practices](#safety--best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Repository Overview

### Dual Nature of the Repository

This repository contains **two distinct systems**:

1. **Primary Implementation (90%+)**: A sophisticated multi-signal cryptocurrency trading bot system called "Benson"
   - 18,710+ lines of Python code
   - 15+ signal modules across 4 layers
   - ML-powered adaptive weight optimization
   - Professional capital management
   - Paper and live trading modes

2. **Aspirational Layer (5-10%)**: Enterprise supply chain/logistics system (ChainBridge)
   - Minimal implementation: API endpoints + documentation
   - ProofPacks for verifiable supply chain events
   - Located in `src/api/proofpacks_api.py` and `proofpacks/` directory

**Important**: The README.md describes the supply chain vision, but the actual codebase is primarily a trading bot. When working on trading features, you're working on the "Benson" system. When working on ProofPacks, you're working on the enterprise supply chain layer.

### Core Purpose

**Benson Trading Bot** provides:
- Multi-signal cryptocurrency trading across 20+ cryptocurrencies
- 4-layer signal architecture (Technical, Logistics, Global Macro, New Listings)
- TensorFlow-based adaptive weight optimization
- Market regime detection (Bull, Bear, Sideways, Volatile)
- Professional risk management (Kelly Criterion, max positions, drawdown limits)
- Paper trading with live data validation
- Kraken exchange integration (extensible to other exchanges via CCXT)

**ProofPacks System** provides:
- Enterprise-grade verifiable proof generation for logistics
- HMAC response signing for authenticity
- SHA-256 manifest hashing for integrity
- Customer-controlled governance model

---

## Codebase Structure

### Directory Layout

```
ChainBridge/
├── api/                          # FastAPI REST API server
│   ├── __init__.py
│   └── server.py                 # Main Benson API endpoints
│
├── apps/                         # Application components
│   ├── backtester/               # Backtesting framework
│   │   ├── backtester.py         # Main backtester logic
│   │   └── test_backtester.py    # Backtester tests
│   └── dashboard/                # Visualization dashboards
│       ├── comparison_dashboard.py
│       └── test_dashboard.py
│
├── core/                         # Core system components
│   ├── __init__.py
│   ├── module_manager.py         # Plugin-and-play module system
│   ├── pipeline.py               # Multi-step workflow orchestration
│   └── data_processor.py         # Data normalization & validation
│
├── modules/                      # Signal & analysis modules (15+)
│   ├── __init__.py
│   ├── rsi_module.py             # RSI technical indicator
│   ├── macd_module.py            # MACD momentum indicator
│   ├── bollinger_bands_module.py # Volatility bands
│   ├── volume_profile_module.py  # Volume distribution
│   ├── sentiment_analysis_module.py  # Market sentiment
│   ├── logistics_signal_module.py    # Supply chain signals (Layer 2)
│   ├── global_macro_module.py        # Macro indicators (Layer 3)
│   ├── adoption_tracker_module.py    # Crypto adoption tracking
│   ├── new_listings_radar.py         # Exchange listing monitor (Layer 4)
│   ├── multi_signal_aggregator_module.py  # Signal combination
│   └── adaptive_weight_module/       # TensorFlow weight optimization
│       ├── adaptive_weight_model.py  # Neural network model
│       ├── weight_trainer.py         # Training logic
│       ├── market_regime_integrator.py
│       └── retraining_scheduler.py   # Daily retraining scheduler
│
├── ml_pipeline/                  # Advanced ML components
│   ├── purged_kfold.py           # Time-series cross-validation
│   ├── triple_barrier_labeling.py    # Financial ML labeling
│   ├── ev_thresholding.py        # Expected value thresholding
│   └── bollinger_features.py     # Feature engineering
│
├── src/                          # Source code organization
│   ├── main.py                   # Main orchestrator
│   ├── data_provider.py          # Market data fetching
│   ├── exchange_adapter.py       # Exchange order management
│   ├── signal_engine.py          # Signal generation
│   ├── api/
│   │   └── proofpacks_api.py     # ProofPacks API implementation
│   ├── backtesting/              # Backtesting engine
│   └── security/                 # HMAC signing for ProofPacks
│
├── strategies/                   # Regime-specific strategies
│   ├── bull_market/              # Bull market config + reports
│   ├── bear_market/              # Bear market config + reports
│   └── sideways_market/          # Sideways market config + reports
│
├── config/                       # Configuration files
│   ├── regime_bull.yaml          # Bull market parameters
│   ├── regime_bear.yaml          # Bear market parameters
│   ├── regime_sideways.yaml      # Sideways market parameters
│   └── kraken_paper_trading.yaml # Paper trading config
│
├── tests/                        # Test suite
│   ├── test_module_manager.py
│   ├── test_budget_manager.py
│   ├── test_config_validation.py
│   ├── test_rsi_scenarios.py
│   └── ml_pipeline/              # ML pipeline tests
│
├── proofpacks/                   # ProofPacks system
│   ├── PROOFPACK_GOVERNANCE.md   # Governance documentation
│   └── runtime/                  # Generated proof pack storage
│
├── docs/                         # Documentation (30+ files)
│   ├── MARKET_REGIME_DETECTION.md
│   ├── REGIME_BASED_STRATEGIES.md
│   └── KRAKEN_PAPER_TRADING.md
│
├── scripts/                      # Utility scripts
│
# Root-level bot implementations and utilities
├── multi_signal_bot.py           # Main multi-signal trading bot
├── live_trading_bot.py           # Live trading implementation
├── benson_rsi_bot.py             # RSI-focused bot
├── benson_system.py              # System orchestrator
├── budget_manager.py             # Capital management
├── enhanced_regime_model.py      # Regime detection model
├── market_regime_trainer.py      # Regime model training
├── dashboard.py                  # Main dashboard
│
# Configuration
├── config.yaml                   # Main configuration
├── .env.example                  # Environment variables template
├── pyproject.toml                # Python project config
├── requirements.txt              # Core dependencies
├── requirements-enterprise.txt   # ML/TensorFlow dependencies
├── requirements-dev.txt          # Development dependencies
├── docker-compose.yml            # Docker services
└── Dockerfile                    # Container image
```

### Key Entry Points

| Purpose | File | Command |
|---------|------|---------|
| **API Server** | `api/server.py` or `benson_system.py` | `python benson_system.py --mode api-server` |
| **Multi-Signal Bot** | `multi_signal_bot.py` | `python multi_signal_bot.py` |
| **Live Trading** | `live_trading_bot.py` | `python live_trading_bot.py` |
| **Paper Trading Demo** | `test_kraken_paper_trading.py` | `python test_kraken_paper_trading.py` |
| **New Listings** | `diagnostic_new_listings.py` | `python diagnostic_new_listings.py` |
| **Adaptive Weights** | `modules/adaptive_weight_module/` | `python run_adaptive_weight_demo.py` |
| **ProofPacks API** | `src/api/proofpacks_api.py` | Included in `main.py` |

---

## Technology Stack

### Core Technologies

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Language** | Python | 3.11 | Primary language |
| **Web Framework** | FastAPI | 0.116.2 | REST API server |
| **Server** | Uvicorn | 0.36.0 | ASGI server |
| **Data Validation** | Pydantic | 2.11.9 | Schema validation |

### Machine Learning

| Technology | Version | Purpose |
|-----------|---------|---------|
| **TensorFlow** | 2.20.0 | Adaptive weight optimization |
| **Keras** | 3.10.0 | Neural network API |
| **LightGBM** | 4.5.0 | Regime detection classifier |
| **scikit-learn** | 1.6.1 | ML algorithms & metrics |
| **statsmodels** | 0.14.5 | Time series analysis |
| **hmmlearn** | 0.3.3 | Hidden Markov Models |

### Data Science

| Technology | Version | Purpose |
|-----------|---------|---------|
| **pandas** | 2.3.2 | Data manipulation |
| **numpy** | 2.0.2 | Numerical computing |
| **scipy** | 1.13.1 | Scientific computing |

### Trading & Finance

| Technology | Version | Purpose |
|-----------|---------|---------|
| **CCXT** | 4.5.5 | Cryptocurrency exchange integration |
| **TA-Lib** | 0.6.7 | Technical analysis indicators |

### Visualization

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Streamlit** | 1.49.1 | Interactive dashboards |
| **Dash** | 3.2.0 | Analytics applications |
| **Plotly** | 6.3.0 | Interactive plots |
| **Matplotlib** | 3.9.4 | Static plotting |
| **Seaborn** | 0.13.2 | Statistical visualization |

### External Integrations

- **Kraken API**: Primary exchange (paper + live trading)
- **Binance, Coinbase, OKX, KuCoin**: Exchange listing monitoring
- **Chainalysis API**: Crypto adoption tracking
- **News APIs**: Sentiment analysis data sources

---

## Development Workflow

### Setting Up Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/BIGmindz/ChainBridge.git
   cd ChainBridge
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:
   ```bash
   # Core dependencies
   pip install -r requirements.txt

   # With ML/TensorFlow (for adaptive weights)
   pip install -r requirements-enterprise.txt

   # Development tools
   pip install -r requirements-dev.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

5. **Validate setup**:
   ```bash
   python -c "import ccxt; print('CCXT OK')"
   python -c "import talib; print('TA-Lib OK')"
   python test_kraken_paper_trading.py  # Test exchange connectivity
   ```

### Running the System

#### Paper Trading Mode (Default - SAFE)

```bash
# Set in .env
PAPER=true

# Run multi-signal bot
python multi_signal_bot.py

# Or run via API server
python benson_system.py --mode api-server
```

#### Live Trading Mode (CAUTION)

```bash
# Set in .env
PAPER=false

# IMPORTANT: Validate first
python live_trading_bot.py  # Includes preflight checks

# The system will:
# 1. Verify real balance (no mock data)
# 2. Validate API credentials
# 3. Check exchange connectivity
# 4. Confirm live mode explicitly
```

#### Docker Deployment

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f benson-api

# Stop services
docker compose down
```

**Services**:
- `benson-api`: Main API server (port 8000)
- `benson-rsi`: RSI compatibility mode
- `benson-legacy`: Legacy bot (optional, profile: legacy)

---

## Configuration Management

### Configuration Hierarchy

1. **Environment Variables** (`.env`) - Highest priority
2. **YAML Configuration** (`config.yaml`) - Application settings
3. **Regime-Specific Configs** (`config/regime_*.yaml`) - Override defaults
4. **State Files** (JSON) - Runtime state persistence

### Environment Variables (`.env`)

```bash
# Exchange Configuration
EXCHANGE="kraken"                 # Exchange to use (kraken, binance, etc.)
PAPER="true"                      # Paper trading mode (true/false)
API_KEY="your_api_key_here"       # Exchange API key
API_SECRET="your_api_secret_here" # Exchange API secret

# Trading Parameters
SYMBOLS="BTC/USD,ETH/USD,SOL/USD,XRP/USD,LINK/USD"
TIMEFRAME="5m"                    # Candlestick timeframe
COOLDOWN_MINUTES="10"             # Cooldown between trades

# Optional: External APIs
CHAINALYSIS_API_KEY="..."         # For adoption tracker module
NEWS_API_KEY="..."                # For sentiment analysis module
```

### Main Configuration (`config.yaml`)

```yaml
# Exchange settings
exchange:
  name: kraken
  api_key: ${API_KEY}             # Environment variable substitution
  api_secret: ${API_SECRET}
  paper_trading: true

# Trading symbols (20+ cryptocurrencies)
symbols:
  - BTC/USD
  - ETH/USD
  - SOL/USD
  # ... more symbols

# Risk management
risk:
  initial_capital: 100000          # Starting capital
  max_positions: 20                # Maximum concurrent positions
  risk_per_trade: 0.06             # 6% max risk per trade
  max_drawdown: 0.25               # 25% max drawdown

# Signal modules
signals:
  rsi:
    enabled: true
    period: 14
    oversold: 30
    overbought: 70

  macd:
    enabled: true
    fast_period: 12
    slow_period: 26
    signal_period: 9

  # ... more signal configs

# Adaptive weights
adaptive_weights:
  enabled: true
  lookback_days: 7
  retrain_frequency: "daily"      # "daily", "hourly", "manual"

# System
polling_interval: 30               # Seconds between market checks
```

### Configuration Patterns

#### Environment Variable Substitution

YAML files support `${VAR_NAME}` syntax:

```yaml
api:
  key: ${API_KEY}
  secret: ${API_SECRET}
```

#### Regime-Specific Overrides

Different configurations for different market regimes:

```yaml
# config/regime_bull.yaml
risk:
  risk_per_trade: 0.08             # More aggressive in bull markets

# config/regime_bear.yaml
risk:
  risk_per_trade: 0.04             # More conservative in bear markets
```

#### State Persistence (JSON)

Runtime state saved to JSON files:

- `allocation_state.json`: Current portfolio allocation
- `budget_state.json`: Capital management state
- `system_status.json`: System health metrics
- `benson_signals.csv`: Signal history log

---

## Module Development Patterns

### Module Base Class

All signal modules inherit from the `Module` base class:

```python
from typing import Dict, Any

class Module:
    """Base class for all modules in the system."""

    VERSION = "1.0.0"  # Module version

    def get_schema(self) -> Dict[str, Any]:
        """
        Define input/output schema for validation.

        Returns:
            dict: Schema definition with 'input' and 'output' keys
        """
        raise NotImplementedError

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing logic.

        Args:
            data: Input data dictionary

        Returns:
            dict: Processed output data
        """
        raise NotImplementedError
```

### Creating a New Signal Module

**Template** (`modules/custom_signal_module.py`):

```python
from typing import Dict, Any
import pandas as pd
from core.module_manager import Module

class CustomSignalModule(Module):
    """
    Custom signal module description.

    Generates trading signals based on custom logic.
    """

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the module.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.name = "custom_signal"

        # Extract parameters from config
        self.threshold = self.config.get('threshold', 0.5)
        self.period = self.config.get('period', 14)

    def get_schema(self) -> Dict[str, Any]:
        """Define input/output schema."""
        return {
            'input': {
                'type': 'object',
                'properties': {
                    'symbol': {'type': 'string'},
                    'timeframe': {'type': 'string'},
                    'ohlcv': {'type': 'array'},  # OHLCV data
                },
                'required': ['symbol', 'ohlcv']
            },
            'output': {
                'type': 'object',
                'properties': {
                    'signal': {'type': 'string', 'enum': ['BUY', 'SELL', 'HOLD']},
                    'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
                    'indicator_value': {'type': 'number'},
                }
            }
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signal.

        Args:
            data: Input data with symbol, timeframe, and OHLCV data

        Returns:
            dict: Signal output with signal, confidence, and indicator value
        """
        try:
            symbol = data['symbol']
            ohlcv = data['ohlcv']

            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )

            # Calculate your custom indicator
            indicator_value = self._calculate_indicator(df)

            # Generate signal
            if indicator_value > self.threshold:
                signal = 'BUY'
                confidence = min(indicator_value / self.threshold, 1.0)
            elif indicator_value < -self.threshold:
                signal = 'SELL'
                confidence = min(abs(indicator_value) / self.threshold, 1.0)
            else:
                signal = 'HOLD'
                confidence = 0.5

            return {
                'signal': signal,
                'confidence': confidence,
                'indicator_value': indicator_value,
                'symbol': symbol,
                'timestamp': df.iloc[-1]['timestamp']
            }

        except Exception as e:
            return {
                'error': str(e),
                'signal': 'HOLD',
                'confidence': 0.0
            }

    def _calculate_indicator(self, df: pd.DataFrame) -> float:
        """
        Calculate custom indicator.

        Args:
            df: OHLCV DataFrame

        Returns:
            float: Indicator value
        """
        # Your custom calculation logic here
        close_prices = df['close'].values

        # Example: Simple momentum
        if len(close_prices) < self.period:
            return 0.0

        momentum = (close_prices[-1] - close_prices[-self.period]) / close_prices[-self.period]
        return momentum * 100
```

### Registering a Module

**Method 1: Automatic Discovery** (if in `modules/` directory):

```python
# In config.yaml
signals:
  custom_signal:
    enabled: true
    threshold: 0.6
    period: 20
```

**Method 2: Manual Registration**:

```python
from core.module_manager import ModuleManager
from modules.custom_signal_module import CustomSignalModule

# Initialize module manager
manager = ModuleManager()

# Register module
manager.register_module(
    name="custom_signal",
    module_class=CustomSignalModule,
    config={"threshold": 0.6, "period": 20}
)

# Execute module
result = manager.execute_module("custom_signal", input_data)
```

### Module Development Guidelines

1. **Always inherit from `Module` base class**
2. **Implement `get_schema()` for input/output validation**
3. **Implement `process()` with error handling**
4. **Use type hints** for better code clarity
5. **Include docstrings** for classes and methods
6. **Return consistent output format** (signal, confidence, metadata)
7. **Handle errors gracefully** (return HOLD signal on error)
8. **Log important events** for debugging

### Signal Output Format

All signal modules should return:

```python
{
    'signal': 'BUY' | 'SELL' | 'HOLD',       # Trading signal
    'confidence': float (0.0 to 1.0),         # Confidence score
    'indicator_value': float,                 # Raw indicator value
    'symbol': str,                            # Trading symbol
    'timestamp': int,                         # Unix timestamp
    'metadata': dict (optional),              # Additional context
    'error': str (optional)                   # Error message if failed
}
```

---

## Testing Strategy

### Test Organization

```
tests/
├── test_module_manager.py        # Module system tests
├── test_budget_manager.py        # Capital management tests
├── test_config_validation.py     # Configuration validation
├── test_rsi_scenarios.py         # RSI signal scenarios
├── test_full_bot.py              # End-to-end bot tests
├── test_regime_backtester.py     # Regime-specific backtesting
└── ml_pipeline/                  # ML pipeline tests
    ├── test_purged_kfold.py
    ├── test_triple_barrier_labeling.py
    └── test_ev_thresholding.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_budget_manager.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test function
pytest tests/test_budget_manager.py::test_position_sizing
```

### Testing Patterns

#### Unit Tests

```python
import pytest
from budget_manager import BudgetManager

def test_position_sizing():
    """Test Kelly Criterion position sizing."""
    manager = BudgetManager(initial_capital=100000)

    position_size = manager.calculate_position_size(
        win_probability=0.6,
        risk_amount=6000,
        current_price=50000
    )

    assert position_size > 0
    assert position_size <= manager.max_positions
```

#### Integration Tests

```python
def test_full_bot_workflow():
    """Test complete bot workflow."""
    bot = MultiSignalBot(config_path='config.yaml')

    # Fetch market data
    data = bot.fetch_market_data('BTC/USD')

    # Generate signals
    signals = bot.generate_signals(data)

    # Make decision
    decision = bot.make_decision(signals)

    assert decision['action'] in ['BUY', 'SELL', 'HOLD']
    assert 0 <= decision['confidence'] <= 1
```

#### Demo/Validation Scripts

Located in root directory:

- `multi_signal_demo.py`: Comprehensive multi-signal demonstration
- `run_global_macro_demo.py`: Global macro module validation
- `run_adaptive_weight_demo.py`: Adaptive weights demonstration
- `test_chainalysis_adoption.py`: Adoption tracker validation
- `test_kraken_paper_trading.py`: Paper trading validation

### Testing Best Practices

1. **Always test in paper mode first**: Set `PAPER=true` in `.env`
2. **Use real market data**: No mock data in live mode (enforced)
3. **Test all signal modules**: Ensure each module returns valid signals
4. **Validate configuration**: Use `test_config_validation.py`
5. **Backtest strategies**: Use backtester before live deployment
6. **Monitor performance**: Track win rate, Sharpe ratio, drawdown

---

## Git Workflow

### Branch Naming Convention

All development branches **must** follow this pattern:

```
claude/claude-md-{session_id}-{unique_id}
```

**Example**:
```
claude/claude-md-mhyubh397v8kzieg-01AULU4XukXFdojyqC8Xn24x
```

**Important**: Branches that don't start with `claude/` and end with matching session ID will fail with 403 HTTP code on push.

### Git Operations

#### Checking Out Development Branch

```bash
# If branch exists remotely
git fetch origin claude/claude-md-mhyubh397v8kzieg-01AULU4XukXFdojyqC8Xn24x
git checkout claude/claude-md-mhyubh397v8kzieg-01AULU4XukXFdojyqC8Xn24x

# If creating new branch
git checkout -b claude/claude-md-mhyubh397v8kzieg-01AULU4XukXFdojyqC8Xn24x
```

#### Committing Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat(module): add custom signal module with confidence scoring"

# View status
git status
```

**Commit Message Format**:

```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(signals): add Fibonacci retracement signal module
fix(budget): correct Kelly Criterion calculation for edge cases
docs(readme): update ProofPacks API documentation
refactor(core): optimize module loading performance
test(regime): add regime detection integration tests
```

#### Pushing Changes

```bash
# Push to specific branch with upstream tracking
git push -u origin claude/claude-md-mhyubh397v8kzieg-01AULU4XukXFdojyqC8Xn24x

# If push fails due to network error, retry with exponential backoff
# (Automatic retry: 2s, 4s, 8s, 16s - up to 4 times)
```

#### Fetching/Pulling Updates

```bash
# Fetch specific branch
git fetch origin claude/claude-md-mhyubh397v8kzieg-01AULU4XukXFdojyqC8Xn24x

# Pull updates
git pull origin claude/claude-md-mhyubh397v8kzieg-01AULU4XukXFdojyqC8Xn24x
```

### Git Safety Protocol

**NEVER**:
- Update git config
- Run destructive commands (force push, hard reset) without explicit user request
- Skip hooks (--no-verify, --no-gpg-sign) unless explicitly requested
- Force push to main/master branches
- Amend commits from other developers

**ALWAYS**:
- Check branch name matches required pattern before pushing
- Use descriptive commit messages
- Verify changes with `git status` and `git diff` before committing
- Check authorship before amending: `git log -1 --format='%an %ae'`

---

## Key Conventions

### Naming Conventions

#### Files
- **Snake_case**: `multi_signal_bot.py`, `budget_manager.py`
- **Suffixes**:
  - `_module.py` for signal modules
  - `_demo.py` for demonstration scripts
  - `_test.py` or `test_*.py` for tests

#### Classes
- **PascalCase**: `BudgetManager`, `RSIModule`, `MultiSignalAggregatorModule`
- **Suffix with purpose**: `Module` for signal modules, `Manager` for management classes

#### Functions/Methods
- **Snake_case**: `safe_fetch_ticker()`, `calculate_position_size()`, `execute_trade()`
- **Prefix with action**: `get_`, `fetch_`, `calculate_`, `execute_`, `validate_`

#### Constants
- **UPPER_SNAKE_CASE**: `DEFAULT_SIGNAL_MODULES`, `RUNTIME_DIR`, `MAX_POSITIONS`

### Code Style

**Configuration** (`pyproject.toml`):

```toml
[tool.black]
line-length = 140
target-version = ['py311']

[tool.ruff]
line-length = 140
target-version = "py311"
```

**Formatting**:
- **Line length**: 140 characters
- **Formatter**: black
- **Linter**: ruff, flake8

**Type Hints**:
```python
from typing import Dict, List, Optional, Any

def calculate_signal(
    data: Dict[str, Any],
    threshold: float = 0.5
) -> Optional[Dict[str, Any]]:
    """Calculate trading signal with type hints."""
    pass
```

### Documentation Style

**Module Docstrings**:
```python
"""
Module Name - Brief Description

Longer description of what this module does and how it works.
Includes key features and usage examples.

Example:
    >>> from modules.rsi_module import RSIModule
    >>> rsi = RSIModule(config={'period': 14})
    >>> result = rsi.process(data)
"""
```

**Function Docstrings**:
```python
def calculate_position_size(
    capital: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss: float
) -> float:
    """
    Calculate position size using Kelly Criterion.

    Args:
        capital: Total available capital
        risk_per_trade: Maximum risk as decimal (e.g., 0.06 for 6%)
        entry_price: Planned entry price
        stop_loss: Stop loss price

    Returns:
        float: Position size in units

    Raises:
        ValueError: If risk_per_trade is invalid

    Example:
        >>> calculate_position_size(100000, 0.06, 50000, 48000)
        0.15
    """
    pass
```

### Error Handling Pattern

```python
try:
    # Main logic
    result = process_data(data)
    return result

except KeyError as e:
    logger.error(f"Missing required field: {e}")
    return {'error': f"Missing field: {e}", 'signal': 'HOLD', 'confidence': 0.0}

except ValueError as e:
    logger.error(f"Invalid value: {e}")
    return {'error': f"Invalid value: {e}", 'signal': 'HOLD', 'confidence': 0.0}

except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {'error': str(e), 'signal': 'HOLD', 'confidence': 0.0}
```

### Logging Pattern

```python
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Log levels
logger.debug("Detailed diagnostic information")
logger.info("General informational message")
logger.warning("Warning about potential issues")
logger.error("Error that occurred but system continues")
logger.critical("Critical error that may stop system")

# Structured logging with context
logger.info(
    f"Signal generated: {signal} for {symbol} "
    f"(confidence={confidence:.2f}, indicator={value:.4f})"
)
```

---

## Common Tasks

### Task 1: Add a New Signal Module

1. **Create module file**: `modules/my_signal_module.py`
2. **Implement Module class**: Inherit from `Module`, implement `get_schema()` and `process()`
3. **Add to configuration**: Update `config.yaml` with module settings
4. **Test the module**: Create `test_my_signal.py`
5. **Run demo**: Create `run_my_signal_demo.py`
6. **Update documentation**: Add to README or create module-specific README

### Task 2: Modify Trading Parameters

1. **Open configuration**: Edit `config.yaml`
2. **Update parameters**:
   ```yaml
   risk:
     risk_per_trade: 0.08  # Increase from 6% to 8%
     max_positions: 15     # Decrease from 20 to 15
   ```
3. **Validate configuration**: Run `python debug_config_loader.py`
4. **Test in paper mode**: Verify changes work as expected
5. **Commit changes**: `git commit -m "chore(config): adjust risk parameters"`

### Task 3: Run Backtesting

1. **Prepare strategy configuration**: Create or use existing regime config
2. **Run backtester**:
   ```bash
   python -m apps.backtester.backtester \
     --strategy bull_market \
     --symbols BTC/USD,ETH/USD \
     --start-date 2024-01-01 \
     --end-date 2024-12-31
   ```
3. **Review results**: Check `strategies/bull_market/backtest_report.md`
4. **Analyze metrics**: Win rate, Sharpe ratio, max drawdown

### Task 4: Train Adaptive Weight Model

1. **Collect signal data**:
   ```bash
   python modules/adaptive_weight_module/signal_data_collector.py --days 30
   ```
2. **Train model**:
   ```bash
   python modules/adaptive_weight_module/weight_trainer.py
   ```
3. **Evaluate performance**: Check model metrics and validation scores
4. **Deploy model**: Model automatically saved to `models/` directory
5. **Enable in config**:
   ```yaml
   adaptive_weights:
     enabled: true
   ```

### Task 5: Monitor Live Trading

1. **Check system status**:
   ```bash
   cat system_status.json
   ```
2. **View current positions**:
   ```bash
   cat allocation_state.json
   ```
3. **Review budget state**:
   ```bash
   cat budget_state.json
   ```
4. **Analyze signal history**:
   ```bash
   python -c "import pandas as pd; print(pd.read_csv('benson_signals.csv').tail(20))"
   ```
5. **Run dashboard**:
   ```bash
   streamlit run dashboard.py
   ```

### Task 6: Add New ProofPack Template

1. **Create template file**: `proofpacks/templates/my_template.json`
2. **Define structure**:
   ```json
   {
     "template_id": "my_template",
     "version": "1.0.0",
     "fields": [
       {"name": "event_type", "required": true, "type": "string"},
       {"name": "timestamp", "required": true, "type": "integer"}
     ],
     "redaction_rules": {
       "pii_fields": ["customer_name", "email"]
     }
   }
   ```
3. **Update API**: Modify `src/api/proofpacks_api.py` to support new template
4. **Test API**:
   ```bash
   curl -X POST http://localhost:8000/proofpacks/run \
     -H "Content-Type: application/json" \
     -d @test_proofpack_payload.json
   ```

### Task 7: Deploy with Docker

1. **Build image**:
   ```bash
   docker build -t chainbridge:latest .
   ```
2. **Run container**:
   ```bash
   docker run -d \
     --name benson-api \
     -p 8000:8000 \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/.env:/app/.env \
     chainbridge:latest
   ```
3. **Check logs**:
   ```bash
   docker logs -f benson-api
   ```
4. **Stop container**:
   ```bash
   docker stop benson-api
   docker rm benson-api
   ```

---

## Safety & Best Practices

### Trading Safety

#### Paper Trading First

**ALWAYS** test in paper mode before live trading:

```bash
# In .env
PAPER=true
```

**Validation checklist**:
- [ ] Configuration is valid
- [ ] All signal modules return valid signals
- [ ] Budget manager calculates position sizes correctly
- [ ] Exchange adapter executes orders properly
- [ ] Risk limits are enforced
- [ ] Stop losses are set correctly

#### Live Trading Preflight Checks

The system enforces these checks automatically:

1. **Real balance verification**: No mock data allowed
2. **API credential validation**: Valid API keys
3. **Exchange connectivity**: Exchange is reachable
4. **Mode confirmation**: Explicit confirmation of live mode
5. **Risk parameter validation**: All risk limits are set

#### Emergency Procedures

**Force close all positions**:
```bash
python force_close_positions.py
```

**Liquidate specific amount**:
```bash
python immediate_liquidate_amount.py --symbol BTC/USD --amount 0.5
```

**Stop all trading**:
```bash
# Kill the bot process
pkill -f multi_signal_bot.py

# Or set emergency stop in config
echo '{"emergency_stop": true}' > system_status.json
```

### Code Safety

#### No Destructive Operations

**NEVER** run these without explicit user approval:
- `git push --force`
- `git reset --hard`
- `rm -rf` on important directories
- Modifying `.git/` directory
- Changing global git config

#### Data Validation

**ALWAYS** validate input data:

```python
def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
    # Validate required fields
    if 'symbol' not in data:
        return {'error': 'Missing symbol', 'signal': 'HOLD', 'confidence': 0.0}

    # Validate data types
    if not isinstance(data['ohlcv'], list):
        return {'error': 'Invalid OHLCV data', 'signal': 'HOLD', 'confidence': 0.0}

    # Validate data quality
    if len(data['ohlcv']) < self.min_data_points:
        return {'error': 'Insufficient data', 'signal': 'HOLD', 'confidence': 0.0}

    # Process...
```

#### Error Recovery

**Graceful degradation** on module failures:

```python
try:
    signal = module.process(data)
except Exception as e:
    logger.error(f"Module {module.name} failed: {e}")
    # Continue with other modules instead of crashing
    signal = {'signal': 'HOLD', 'confidence': 0.0, 'error': str(e)}
```

### Security Best Practices

#### API Key Management

**NEVER** commit API keys to git:

```bash
# In .gitignore
.env
*.secret
*_credentials.json
api_keys.txt
```

**Use environment variables**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

if not API_KEY or not API_SECRET:
    raise ValueError("Missing API credentials")
```

#### Secrets in Logs

**NEVER** log sensitive data:

```python
# Bad
logger.info(f"Using API key: {api_key}")

# Good
logger.info("API key loaded successfully")
```

### Performance Best Practices

#### Rate Limiting

Respect exchange rate limits:

```python
import time
import ccxt

exchange = ccxt.kraken({
    'enableRateLimit': True,  # Automatic rate limiting
    'rateLimit': 3000,        # Milliseconds between requests
})
```

#### Data Caching

Cache expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_expensive_indicator(symbol: str, timeframe: str) -> float:
    # Expensive calculation cached for repeated calls
    pass
```

#### Batch Processing

Process multiple symbols efficiently:

```python
# Bad: Sequential processing
for symbol in symbols:
    data = fetch_data(symbol)
    signal = generate_signal(data)

# Good: Batch processing
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(process_symbol, sym) for sym in symbols]
    results = [f.result() for f in futures]
```

---

## Troubleshooting

### Common Issues

#### Issue: Module not found

**Error**:
```
ModuleNotFoundError: No module named 'talib'
```

**Solution**:
```bash
# Install TA-Lib
pip install TA-Lib==0.6.7

# Or install all dependencies
pip install -r requirements.txt
```

#### Issue: Exchange connectivity error

**Error**:
```
ccxt.NetworkError: kraken GET https://api.kraken.com/0/public/Ticker failed
```

**Solution**:
1. Check internet connection
2. Verify exchange is not under maintenance
3. Check API credentials are correct
4. Verify `EXCHANGE` in `.env` matches configured exchange

#### Issue: Invalid configuration

**Error**:
```
ValidationError: 'signals.rsi.period' is not a valid integer
```

**Solution**:
```bash
# Validate configuration
python debug_config_loader.py

# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

#### Issue: Insufficient balance

**Error**:
```
InsufficientFunds: Not enough balance to execute trade
```

**Solution**:
1. Check current balance: `cat budget_state.json`
2. Verify `initial_capital` in `config.yaml` matches actual balance
3. Reduce `risk_per_trade` if position sizes are too large
4. Ensure you're not exceeding `max_positions`

#### Issue: Adaptive weights model not found

**Error**:
```
FileNotFoundError: Adaptive weight model not found
```

**Solution**:
```bash
# Train the model first
python modules/adaptive_weight_module/weight_trainer.py

# Or disable adaptive weights
# In config.yaml:
adaptive_weights:
  enabled: false
```

#### Issue: Paper trading shows "mock data"

**Error**:
```
WARNING: Mock data detected in paper trading mode
```

**Solution**:
This is expected in paper mode. The system uses simulated balance but **real market data**.

For live trading, this would be an error and trading would be blocked.

### Debug Mode

Enable verbose logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Getting Help

1. **Check documentation**: Review relevant `.md` files in `docs/`
2. **Run validation scripts**: Use `test_*.py` and `run_*_demo.py` scripts
3. **Check logs**: Review console output and log files
4. **Inspect state files**: Check JSON state files for current system state
5. **Review configuration**: Validate `config.yaml` and `.env`

### Useful Commands

```bash
# Check Python version
python --version

# List installed packages
pip list

# Verify CCXT exchanges
python -c "import ccxt; print(ccxt.exchanges)"

# Test exchange connectivity
python test_kraken_paper_trading.py

# Validate configuration
python debug_config_loader.py

# Check system status
cat system_status.json | python -m json.tool

# View recent signals
tail -n 50 benson_signals.csv

# Monitor live bot
tail -f logs/benson_bot.log  # If logging to file
```

---

## Additional Resources

### Documentation Files

| File | Description |
|------|-------------|
| `README.md` | Main project overview and setup |
| `ENTERPRISE_README.md` | Enterprise features and deployment |
| `TRADING_SYSTEM_QUICKSTART.md` | Quick start guide for trading system |
| `REGIME_MODEL_GUIDE.md` | Market regime detection guide |
| `README_ADAPTIVE_WEIGHT_MODEL.md` | Adaptive weights documentation |
| `README_GLOBAL_MACRO.md` | Global macro module guide |
| `README_NEW_LISTINGS.md` | New listings radar guide |
| `LIVE_TRADING_SAFETY.md` | Live trading safety guidelines |
| `proofpacks/PROOFPACK_GOVERNANCE.md` | ProofPacks governance model |

### Example Scripts

| Script | Purpose |
|--------|---------|
| `multi_signal_demo.py` | Multi-signal bot demonstration |
| `run_adaptive_weight_demo.py` | Adaptive weights demo |
| `run_global_macro_demo.py` | Global macro signals demo |
| `test_kraken_paper_trading.py` | Paper trading validation |
| `diagnostic_new_listings.py` | New listings diagnostics |
| `market_regime_trainer.py` | Train regime detection model |

### Key Contacts

- **Repository Owner**: BIGmindz
- **Main Maintainer**: Benson (CTO)
- **GitHub Issues**: https://github.com/BIGmindz/ChainBridge/issues

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-14 | 1.0.0 | Initial CLAUDE.md creation - comprehensive codebase documentation |

---

**End of CLAUDE.md**

For AI assistants: This file should be your primary reference when working with the ChainBridge repository. Always consult this guide for:
- Understanding the dual nature of the repository
- Following development patterns and conventions
- Executing common tasks
- Maintaining safety and best practices
- Navigating the codebase effectively

When in doubt, refer to the specific documentation files listed in Additional Resources for detailed information on particular features or systems.
