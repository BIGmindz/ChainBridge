# Repository Map

This document provides a detailed navigation guide for the BIGmindz/ChainBridge monorepo.

## 🗺️ High-Level Structure

```
BIGmindz/ChainBridge/
│
├── ChainBridge/              # ← FREIGHT & LOGISTICS PLATFORM
├── Root Level/               # ← BENSONBOT TRADING SYSTEM
├── docs/                     # Documentation
├── .github/                  # CI/CD and governance
└── [Configuration Files]     # Shared config
```

## 📦 Two Products, One Repo

### Product 1: ChainBridge (Freight Platform)
**Location**: `ChainBridge/` directory  
**Purpose**: Enterprise freight and logistics management  
**Tech Stack**: Python 3.11+, FastAPI, PostgreSQL, Docker  
**CI Workflow**: `.github/workflows/ci.yml` (path-filtered)

### Product 2: BensonBot (Trading Bot)
**Location**: Root level  
**Purpose**: Multi-signal ML-driven cryptocurrency trading  
**Tech Stack**: Python 3.11+, ccxt, pandas, scikit-learn  
**CI Workflow**: `.github/workflows/trading-bot-ci.yml` (path-filtered)

## 🏗️ Complete Directory Structure

```
BIGmindz/ChainBridge/
│
├── README.md                          # [ROOT] Monorepo overview
├── CONTRIBUTING.md                    # [ROOT] Contribution guidelines
├── .editorconfig                      # [ROOT] Editor configuration
├── .gitignore                         # [ROOT] Git ignore rules
├── .python-version                    # [ROOT] Python version (3.11)
├── pyproject.toml                     # [ROOT] Python project config
├── ruff.toml                          # [ROOT] Ruff linter config
│
├── .env.example                       # [BENSONBOT] Environment template
├── requirements.txt                   # [BENSONBOT] Core dependencies
├── requirements-dev.txt               # [BENSONBOT] Dev dependencies
├── requirements-enterprise.txt        # [BENSONBOT] Enterprise features
├── requirements-runtime.txt           # [BENSONBOT] Runtime only
├── requirements-listings.txt          # [BENSONBOT] New listings feature
├── requirements-dashboard.txt         # [BENSONBOT] Dashboard deps
├── viz_requirements.txt               # [BENSONBOT] Visualization
│
├── main.py                            # [BENSONBOT] Main entry point
├── benson_rsi_bot.py                  # [BENSONBOT] Legacy entry point
├── start_trading.sh                   # [BENSONBOT] Trading launcher
├── Dockerfile                         # [BENSONBOT] Container definition
├── Dockerfile.enterprise              # [BENSONBOT] Enterprise container
├── docker-compose.yml                 # [BENSONBOT] Container orchestration
├── Makefile                           # [BENSONBOT] Build automation
├── Makefile.dashboard                 # [BENSONBOT] Dashboard Makefile
│
├── src/                               # [BENSONBOT] Core source code
│   ├── core/
│   │   └── unified_trading_engine.py  # Main trading engine
│   ├── main.py                        # Alternative entry point
│   └── tests.py                       # Test suite
│
├── modules/                           # [BENSONBOT] Signal modules
│   ├── adaptive_weight_module/        # Dynamic signal weighting
│   ├── market_regime_module/          # Regime detection
│   ├── risk_management/               # Risk management
│   ├── logistics_signal_module.py     # Supply chain signals
│   └── [other signal modules]
│
├── strategies/                        # [BENSONBOT] Market strategies
│   ├── bull_market/                   # Bull market config
│   │   ├── config.yaml
│   │   └── backtest_report.md
│   ├── bear_market/                   # Bear market config
│   │   ├── config.yaml
│   │   └── backtest_report.md
│   ├── sideways_market/               # Sideways market config
│   │   ├── config.yaml
│   │   └── backtest_report.md
│   └── README.md                      # Strategy overview
│
├── apps/                              # [BENSONBOT] Applications
│   └── dashboard/                     # Monitoring dashboards
│       ├── monitor.py
│       └── README.md
│
├── scripts/                           # [BENSONBOT] Utility scripts
│   ├── validate_thresholds.py         # RSI threshold validation
│   ├── live_ticker.py                 # Price monitoring
│   ├── README.md
│   └── LIVE_TICKER_README.md
│
├── tests/                             # [BENSONBOT] Test suite
│   ├── __init__.py
│   └── [test files]
│
├── core/                              # [BENSONBOT] Core modules
│   ├── module_manager.py
│   ├── data_processor.py
│   └── pipeline.py
│
├── api/                               # [BENSONBOT] API layer
│   ├── server.py
│   └── __init__.py
│
├── tracking/                          # [BENSONBOT] Metrics
│   └── metrics_collector.py
│
├── utils/                             # [BENSONBOT] Utilities
│   └── feature_hygiene.py
│
├── tools/                             # [BENSONBOT] Tools
│   └── analyze_regime_detection.py
│
├── examples/                          # [BENSONBOT] Examples
│   └── regime_dashboard_demo.py
│
├── ml_models/                         # [BENSONBOT] ML models
├── market_metrics/                    # [BENSONBOT] Market data
├── sample_data/                       # [BENSONBOT] Sample data
├── reports/                           # [BENSONBOT] Trading reports
│   └── trading_performance_report.json
├── archived_logs/                     # [BENSONBOT] Log archive
├── static/                            # [BENSONBOT] Static files
├── assets/                            # [BENSONBOT] Assets
│
├── k8s/                               # [BENSONBOT] Kubernetes configs
├── proofpacks/                        # [BENSONBOT] Proof packages
│   └── PROOFPACK_GOVERNANCE.md
│
├── ChainBridge/                       # ↓↓↓ FREIGHT PLATFORM ↓↓↓
│   ├── README.md                      # [CHAINBRIDGE] Platform docs
│   ├── .gitignore                     # [CHAINBRIDGE] Git ignore
│   ├── pyproject.toml                 # [CHAINBRIDGE] Project config
│   ├── Dockerfile                     # [CHAINBRIDGE] Container
│   ├── Dockerfile.enterprise          # [CHAINBRIDGE] Enterprise
│   ├── Makefile                       # [CHAINBRIDGE] Build automation
│   │
│   ├── requirements.txt               # [CHAINBRIDGE] Dependencies
│   ├── requirements-dev.txt           # [CHAINBRIDGE] Dev deps
│   ├── requirements-enterprise.txt    # [CHAINBRIDGE] Enterprise
│   ├── requirements-runtime.txt       # [CHAINBRIDGE] Runtime
│   │
│   ├── chainiq-service/               # Intelligence service (Port 8001)
│   │   ├── app/                       # Service code
│   │   ├── README.md                  # Service documentation
│   │   └── requirements.txt           # Service dependencies
│   │
│   ├── chainpay-service/              # Payment service (Port 8002)
│   │   ├── app/                       # Service code
│   │   ├── tests/                     # Service tests
│   │   ├── pytest.ini                 # Pytest config
│   │   ├── README.md                  # Service documentation
│   │   └── requirements.txt           # Service dependencies
│   │
│   ├── chainfreight-service/          # Freight service (Port 8003)
│   │   ├── app/                       # Service code
│   │   ├── README.md                  # Service documentation
│   │   └── requirements.txt           # Service dependencies
│   │
│   ├── chainboard-service/            # Backend API (Port 8000)
│   │   ├── app/                       # Service code
│   │   └── README.md                  # Service documentation
│   │
│   ├── chainboard-ui/                 # Frontend UI (Port 3000)
│   │   ├── src/                       # React source
│   │   ├── public/                    # Static assets
│   │   └── README.md                  # UI documentation
│   │
│   ├── tests/                         # [CHAINBRIDGE] Integration tests
│   │   ├── test_gatekeeper.py         # Governance tests
│   │   └── [other test files]
│   │
│   ├── docs/                          # [CHAINBRIDGE] Documentation
│   │   └── governance/                # ALEX compliance docs
│   │
│   ├── scripts/                       # [CHAINBRIDGE] Utility scripts
│   │   └── README.md
│   │
│   ├── tools/                         # [CHAINBRIDGE] Tools
│   │   └── gatekeeper.py              # Governance CLI
│   │
│   ├── core/                          # [CHAINBRIDGE] Core modules
│   ├── models/                        # [CHAINBRIDGE] Database models
│   ├── api/                           # [CHAINBRIDGE] API layer
│   ├── data/                          # [CHAINBRIDGE] Data files
│   ├── cache/                         # [CHAINBRIDGE] Cache
│   ├── ml_models/                     # [CHAINBRIDGE] ML models
│   ├── ml_pipeline/                   # [CHAINBRIDGE] ML pipeline
│   ├── sample_data/                   # [CHAINBRIDGE] Sample data
│   ├── reports/                       # [CHAINBRIDGE] Reports
│   ├── market_metrics/                # [CHAINBRIDGE] Metrics
│   ├── tracking/                      # [CHAINBRIDGE] Tracking
│   ├── utils/                         # [CHAINBRIDGE] Utilities
│   ├── static/                        # [CHAINBRIDGE] Static files
│   └── assets/                        # [CHAINBRIDGE] Assets
│
├── docs/                              # [SHARED] Documentation
│   ├── bensonbot/                     # BensonBot documentation
│   │   └── README.md                  # Trading bot guide
│   ├── REPO_MAP.md                    # This file
│   ├── MARKET_REGIME_DETECTION.md     # [BENSONBOT] Regime detection
│   ├── REGIME_SPECIFIC_BACKTESTING.md # [BENSONBOT] Backtesting
│   ├── REGIME_BASED_STRATEGIES.md     # [BENSONBOT] Strategies
│   └── KRAKEN_PAPER_TRADING.md        # [BENSONBOT] Exchange guide
│
├── .github/                           # [SHARED] GitHub configuration
│   ├── workflows/
│   │   ├── trading-bot-ci.yml         # BensonBot CI (path-filtered)
│   │   └── ci.yml                     # ChainBridge CI (path-filtered)
│   ├── CODEOWNERS                     # Code ownership
│   ├── pull_request_template.md       # PR template (ALEX-aligned)
│   ├── SECURITY.md                    # Security policy
│   ├── copilot-instructions.md        # Copilot agent instructions
│   └── copilot.md                     # Legacy Copilot docs
│
├── .pre-commit-config.yaml            # [SHARED] Pre-commit hooks
├── .flake8                            # [SHARED] Flake8 config
├── .pylintrc                          # [SHARED] Pylint config
├── .markdownlint.json                 # [SHARED] Markdown lint
├── .markdownlintignore                # [SHARED] Markdown ignore
└── .dockerignore                      # [SHARED] Docker ignore
```

## 🚦 Navigation Guide

### I Want to Work on ChainBridge (Freight Platform)

```bash
# Navigate to ChainBridge
cd ChainBridge/

# Read platform documentation
cat README.md

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Work on a service
cd chainpay-service/
cat README.md
```

### I Want to Work on BensonBot (Trading Bot)

```bash
# Stay at root level
cd /path/to/repo

# Read trading bot documentation
cat docs/bensonbot/README.md

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python benson_rsi_bot.py --test

# Start trading (paper mode)
python main.py --mode paper
```

### I Want to Add Documentation

```bash
# ChainBridge documentation
cd ChainBridge/docs/

# BensonBot documentation
cd docs/bensonbot/

# General documentation
cd docs/
```

### I Want to Modify CI/CD

```bash
# BensonBot CI
.github/workflows/trading-bot-ci.yml

# ChainBridge CI
.github/workflows/ci.yml

# Both are path-filtered to prevent cross-triggering
```

## 🔍 Finding Specific Components

### ChainBridge Services

| Service | Directory | Port | README |
|---------|-----------|------|--------|
| ChainIQ | `ChainBridge/chainiq-service/` | 8001 | [Link](ChainBridge/chainiq-service/README.md) |
| ChainPay | `ChainBridge/chainpay-service/` | 8002 | [Link](ChainBridge/chainpay-service/README.md) |
| ChainFreight | `ChainBridge/chainfreight-service/` | 8003 | [Link](ChainBridge/chainfreight-service/README.md) |
| ChainBoard API | `ChainBridge/chainboard-service/` | 8000 | [Link](ChainBridge/chainboard-service/README.md) |
| ChainBoard UI | `ChainBridge/chainboard-ui/` | 3000 | [Link](ChainBridge/chainboard-ui/README.md) |

### BensonBot Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Main Entry | `main.py` | Canonical entry point (paper/live/backtest) |
| Legacy Entry | `benson_rsi_bot.py` | Legacy RSI bot with tests |
| Trading Engine | `src/core/unified_trading_engine.py` | Core trading logic |
| Signal Modules | `modules/` | RSI, MACD, Volume, Sentiment, etc. |
| Strategies | `strategies/` | Bull/Bear/Sideways configs |
| Risk Management | `modules/risk_management/` | Position sizing, stops |
| Regime Detection | `modules/market_regime_module/` | ML regime classifier |
| Dashboards | `apps/dashboard/` | Monitoring interfaces |
| Tests | `tests/` | Test suite |

### Configuration Files

| File | Purpose | Product |
|------|---------|---------|
| `requirements.txt` (root) | Core dependencies | BensonBot |
| `requirements.txt` (ChainBridge/) | Platform dependencies | ChainBridge |
| `.env.example` | Environment template | BensonBot |
| `config.yaml` (strategies/) | Strategy configs | BensonBot |
| `pyproject.toml` (root) | Python project | BensonBot |
| `pyproject.toml` (ChainBridge/) | Python project | ChainBridge |

### Testing Files

| File | Purpose | Product |
|------|---------|---------|
| `tests/` (root) | BensonBot tests | BensonBot |
| `ChainBridge/tests/` | Platform tests | ChainBridge |
| `ChainBridge/chainpay-service/tests/` | Service tests | ChainBridge |
| `benson_rsi_bot.py --test` | Built-in RSI tests | BensonBot |

## 🎯 Common Tasks

### Run All Tests

```bash
# BensonBot tests
python benson_rsi_bot.py --test
pytest tests/ -v

# ChainBridge tests
cd ChainBridge/
pytest tests/ -v
python -m pytest tests/test_gatekeeper.py -v
```

### Start Development Environment

```bash
# BensonBot (root level)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ChainBridge (in ChainBridge/ dir)
cd ChainBridge/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Deploy/Run

```bash
# BensonBot paper trading
python main.py --mode paper

# ChainBridge services (Docker)
cd ChainBridge/
docker-compose up -d
```

## 🔐 Governance & Security

### Code Ownership

See `.github/CODEOWNERS` for ownership mapping.

### Security Policy

See `.github/SECURITY.md` for:
- Vulnerability reporting
- Supported versions
- Dependabot alerts policy

### Contribution Guidelines

See `CONTRIBUTING.md` for:
- Branch naming conventions
- PR requirements
- Testing policies
- Code review process

## 📚 Documentation Links

### ChainBridge
- [Platform Overview](ChainBridge/README.md)
- [Governance](ChainBridge/docs/governance/)
- Service READMEs (in each service directory)

### BensonBot
- [Trading Bot Guide](docs/bensonbot/README.md)
- [Market Regime Detection](docs/MARKET_REGIME_DETECTION.md)
- [Backtesting Guide](docs/REGIME_SPECIFIC_BACKTESTING.md)
- [Strategy Guide](docs/REGIME_BASED_STRATEGIES.md)

### General
- [Root README](README.md) - Monorepo overview
- [Contributing](CONTRIBUTING.md) - How to contribute
- [Security](.github/SECURITY.md) - Security policy
- [Repository Map](docs/REPO_MAP.md) - This file

## ❓ FAQ

**Q: Why are there two separate products in one repo?**  
A: This is an intentional monorepo structure. ChainBridge and BensonBot are maintained together but remain strictly separated via path filtering and directory structure.

**Q: Which Python version should I use?**  
A: Python 3.11 or higher is required for both products.

**Q: Why do CI workflows have path filters?**  
A: Path filters ensure changes to ChainBridge don't trigger BensonBot CI and vice versa, preventing unnecessary CI runs.

**Q: Can I move files between ChainBridge/ and root?**  
A: No. The directory structure must remain stable to preserve path filtering and avoid breaking CI/CD.

**Q: Where do I add new documentation?**  
A: ChainBridge docs go in `ChainBridge/docs/`, BensonBot docs go in `docs/bensonbot/`, and shared docs go in `docs/`.

**Q: How do I know which tests to run?**  
A: Run BensonBot tests from root, ChainBridge tests from `ChainBridge/` directory.

---

**Need help navigating?** Open an issue or contact [@BIGmindz](https://github.com/BIGmindz).

**Last Updated**: December 2024
