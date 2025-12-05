# Multi-Signal Crypto Trading System

A sophisticated Python cryptocurrency trading system using multiple signal aggregation, adaptive weights, and regime detection for BUY/SELL/HOLD decisions. The system supports multiple exchanges (Kraken, Binance) and includes real-time market analysis, risk management, and comprehensive monitoring capabilities.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Current System Architecture

### Entry Points:
- **main.py** - Canonical entry point for all trading operations (live, paper, backtest)
- **benson_rsi_bot.py** - Legacy entry point (deprecated in favor of main.py)
- **live_trading_bot.py** - Core live trading engine
- **integrated_trading_system.py** - Multi-signal aggregation system

### Key Features:
- Multi-signal aggregation with adaptive weights
- Market regime detection (bull/bear/sideways)
- Canonical RSI thresholds: BUY=35, SELL=64 (enforced across all modules)
- Live trading safety guards and confirmation requirements
- Real-time monitoring dashboards (Streamlit, Dash)
- Comprehensive backtesting and paper trading modes

## Repository Structure

``` text
/
├── main.py                    # Canonical entry point for all operations
├── live_trading_bot.py        # Core live trading engine
├── integrated_trading_system.py # Multi-signal aggregation system
├── benson_rsi_bot.py          # Legacy bot (deprecated)
├── dashboard.py               # Streamlit monitoring dashboard
├── animated_dashboard_new.py  # Advanced dashboard with animations
├── scripts/
│   ├── validate_thresholds.py # RSI threshold enforcement
│   └── live_ticker.py         # Real-time price monitoring
├── modules/
│   ├── adaptive_weight_module/ # Dynamic signal weighting
│   ├── market_regime_module/   # Bull/bear/sideways detection
│   └── risk_management/        # Position sizing and stops
├── strategies/
│   ├── bear/                  # Bear market configurations
│   ├── bull/                  # Bull market configurations
│   └── sideways/              # Sideways market configurations
├── docs/
│   └── RSI_THRESHOLD_POLICY.md # Governance documentation
├── config/config.yaml         # Main configuration
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
├── Makefile                  # Build automation
├── Dockerfile               # Container definition
├── docker-compose.yml        # Container orchestration
└── .github/copilot-instructions.md # This file
```

## Working Effectively

### Bootstrap, Build, and Test the Repository:

```bash
# Setup Python virtual environment - takes ~10 seconds
# May fail with TimeoutError in restricted network environments
make venv

# Install dependencies - takes 90+ seconds due to large packages (pandas, numpy, ccxt)
# NEVER CANCEL: Set timeout to 180+ seconds
# May fail with "Read timed out" errors in restricted network environments
make install

# Run built-in unit tests - takes ~1 second, all should pass
# Tests: RSI calculation, flatline/uptrend/downtrend scenarios, insufficient data handling
make test  # OR: python benson_rsi_bot.py --test

# Lint code - takes ~2 seconds
# NEVER CANCEL: Set timeout to 30+ seconds
make lint

# Format code
make fmt
```

### Run the Bot:

```bash
# ALWAYS run the bootstrapping steps first (venv + install)

# Run live trading (requires confirmation for safety)
# CRITICAL: Live trading requires explicit confirmation via --confirm-live flag
python3 main.py --mode live --confirm-live

# Run paper trading (safe for testing)
python3 main.py --mode paper

# Run backtesting
python3 main.py --mode backtest

# Legacy entry point (deprecated)
# python benson_rsi_bot.py --once
```

### Docker (Limited Support):

```bash
# Docker build - FAILS due to network restrictions in sandboxed environments
# Expected failure: SSL certificate verification errors when installing packages
# Document as: "Docker build fails due to firewall/certificate limitations in restricted environments"
make docker-build

# In unrestricted environments:
make up      # Start bot in Docker
make down    # Stop bot
make logs    # View logs
make shell   # Access bot container shell
```

## Validation

### Required Validation Steps:

- **ALWAYS run the built-in unit tests** after making changes: `python benson_rsi_bot.py --test`
- **ALWAYS run linting** before committing: `make lint`
- **Test data ingestion module**: `python -c "import data_ingestor; print(data_ingestor.fetch_all_alternative_data())"`
- **Verify configuration loading**: Check that config/config.yaml loads without errors
- **Test RSI calculations**: All 5 built-in tests must pass (flatline, uptrend, downtrend, edge cases)



### Manual Validation Scenarios:

1. **Basic Python Validation**: Run `python3 -c "import yaml, os; print('Core dependencies available')"`
2. **Unit Test Validation**: Run `python benson_rsi_bot.py --test` - expect all 5 tests to PASS
3. **Configuration Validation**: Verify config/config.yaml and .env.example contain required settings
4. **Data Ingestor Validation**: Test mock functions return expected geopolitical/sentiment scores
5. **File Structure Check**: Verify `.github/copilot-instructions.md` exists and contains comprehensive instructions
6. **Network-Dependent Features**: Bot startup will fail with NetworkError in restricted environments (expected)



### What WORKS in Restricted Environments:

- Virtual environment setup and dependency installation
- All unit tests (completely offline)
- Code linting and formatting
- Mock data ingestion functions
- Configuration file parsing
- RSI calculation algorithms



### What FAILS in Restricted Environments (Expected):

- Live bot execution (requires exchange API access)
- Docker build (certificate verification issues)
- Standalone test_rsi.py (requires Coinbase API access)
- **Virtual environment setup and dependency installation** (pip timeout errors in some network-restricted environments)
- **make venv/make install** may fail with "Read timed out" or "TimeoutError" when PyPI is unreachable



## Configuration

### Required Files:

- `config/config.yaml` - Main bot configuration (exchange, symbols, thresholds)
- `.env` - API keys and environment variables (copy from .env.example)
- `.venv/` - Python virtual environment (created by `make venv`)



### Key Configuration Options:

- Exchange: kraken (default), coinbase, binance, bybit
- Symbols: BTC/USD, ETH/USD, SOL/USD, etc.
- RSI thresholds: buy_threshold (canonical 35), sell_threshold (canonical 64) - ENFORCED SYSTEM-WIDE
- Polling interval: poll_seconds (default 60)
- Risk management: stop_loss_pct, take_profit_pct



## Common Tasks

### Development Workflow:

```bash
# 1. Setup (once)
make venv && make install

# 2. Make changes to code

# 3. Validate changes
python benson_rsi_bot.py --test  # Unit tests must pass
make lint                        # Code must be clean

# 4. Test functionality
python -c "import data_ingestor; print(data_ingestor.fetch_all_alternative_data())"

# 5. Ready to commit (all validations passing)
```

### Troubleshooting:

- **"NetworkError" or "ConnectionError"**: Expected in sandboxed environments - network restrictions prevent API access
- **"SSL: CERTIFICATE_VERIFY_FAILED"**: Expected in Docker builds - certificate chain issues in restricted environments
- **"Read timed out" or "TimeoutError" during pip operations**: Expected in network-restricted environments - PyPI unreachable
- **"ModuleNotFoundError"**: Run `make install` to install dependencies (if network allows)
- **"FileNotFoundError: config/config.yaml"**: Configuration file missing or path incorrect
- **Unit test failures**: RSI calculation logic error - review wilder_rsi() function



### Alternative Setup for Network-Restricted Environments:

If `make venv` and `make install` fail due to network issues:

```bash
# Use system Python if available with pre-installed packages
python3 --version  # Check if Python 3.11+ is available
pip3 list | grep -E "(pandas|numpy|ccxt|pyyaml)"  # Check for required packages

# Manual virtual environment (without pip upgrade)
python3 -m venv .venv --without-pip
# Use system packages if virtual environment setup fails entirely
```

## Repository Structure

```text
/
├── benson_rsi_bot.py      # Main bot application with built-in tests
├── data_ingestor.py       # Mock external data ingestion
├── test_rsi.py           # Standalone RSI test (requires network)
├── config/config.yaml    # Bot configuration
├── .env.example          # Environment template
├── requirements.txt      # Python dependencies
├── Makefile             # Build automation
├── Dockerfile           # Container definition
├── docker-compose.yml   # Container orchestration
└── .github/copilot.md   # Legacy contribution guide
```

### Key Functions and Classes:

- `wilder_rsi()` - RSI calculation using EMA smoothing
- `run_bot()` - Main trading loop with signal generation
- `load_config()` - YAML configuration parser
- `fetch_all_alternative_data()` - Mock data aggregator
- Built-in test suite with 5 RSI validation scenarios



## Time Expectations

**CRITICAL - Always set appropriate timeouts and NEVER CANCEL:**

- **Virtual environment setup**: ~10 seconds (use 30s timeout)
- **Dependency installation**: ~90 seconds - NEVER CANCEL - Set timeout to 180+ seconds
- **Unit tests**: ~1 second (use 30s timeout)
- **Linting**: ~2 seconds (use 30s timeout)
- **Bot startup**: ~1 second before network failure (in restricted environments)
- **Docker build**: Fails at ~30 seconds due to network restrictions



**NEVER CANCEL any build or long-running installation commands** - dependency installation involves large packages (pandas, numpy, ccxt) and requires patience.
