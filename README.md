# BIGmindz Monorepo: ChainBridge + BensonBot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/BIGmindz/ChainBridge/workflows/Tests/badge.svg)](https://github.com/BIGmindz/ChainBridge/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**This is a monorepo containing two distinct products:**

1. **ChainBridge** - Freight and logistics microservices platform
2. **BensonBot** - Multi-signal ML-driven cryptocurrency trading bot

## 🏗️ Architecture Overview

### ChainBridge (Freight Platform)
Located in `ChainBridge/` directory. A comprehensive freight and logistics management platform with microservices architecture:

- **ChainIQ** - Intelligence and analytics service
- **ChainPay** - Payment processing and financial transactions
- **ChainFreight** - Freight management and tracking
- **ChainBoard** - Dashboard UI and service
- **Gatekeeper** - CLI validation and governance tool

**Purpose**: Enterprise-grade logistics management with ALEX governance compliance.

### BensonBot (Trading Bot)
Located at root level. A sophisticated multi-signal cryptocurrency trading system:

- **Core Files**: `main.py`, `benson_rsi_bot.py`, `start_trading.sh`
- **Trading Logic**: `src/`, `modules/`, `strategies/`
- **Signal Processing**: RSI, MACD, Volume, Sentiment, ML Regime Detection
- **Risk Management**: Kelly Criterion position sizing, stop-loss, take-profit

**Purpose**: Automated cryptocurrency trading with uncorrelated signal aggregation and adaptive market regime detection.

## 🚀 Quick Start

### Python Version Policy
**Both products require Python 3.11 or higher.**

Check your Python version:
```bash
python3 --version  # Should be 3.11 or higher
```

### ChainBridge Quick Start

```bash
# Navigate to ChainBridge directory
cd ChainBridge

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Service-specific testing
python -m pytest tests/test_gatekeeper.py -v
```

**[Full ChainBridge Documentation →](ChainBridge/README.md)**

### BensonBot Quick Start

```bash
# Create virtual environment (at root level)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run built-in tests
python -m src.tests
# Or: pytest src/tests.py -v

# Test main entry point (paper trading)
python -m src.main --mode paper
# Or: python src/main.py --mode paper

# Start trading system (paper trading)
./start_trading.sh --test
```

**[Full BensonBot Documentation →](docs/bensonbot/README.md)**

## 📁 Repository Structure

```
BIGmindz/ChainBridge/
│
├── ChainBridge/              # ← Freight & Logistics Platform
│   ├── chainiq-service/      # Intelligence service
│   ├── chainpay-service/     # Payment service
│   ├── chainfreight-service/ # Freight service
│   ├── chainboard-service/   # Backend service
│   ├── chainboard-ui/        # Frontend UI
│   ├── tests/                # ChainBridge tests
│   ├── docs/governance/      # ALEX compliance docs
│   └── README.md             # ChainBridge documentation
│
├── benson_rsi_bot.py         # ← BensonBot: Legacy entry point
├── main.py                   # ← BensonBot: Main entry point
├── start_trading.sh          # ← BensonBot: Trading system launcher
├── src/                      # ← BensonBot: Core trading engine
├── modules/                  # ← BensonBot: Signal modules
├── strategies/               # ← BensonBot: Market strategies
├── trading/                  # ← BensonBot: Trading logic
├── tests/                    # BensonBot tests
│
├── docs/
│   ├── bensonbot/            # BensonBot documentation
│   └── REPO_MAP.md           # Detailed structure map
│
├── .github/
│   ├── workflows/
│   │   ├── trading-bot-ci.yml      # BensonBot CI (path-filtered)
│   │   └── ci.yml                  # ChainBridge CI (path-filtered)
│   ├── CODEOWNERS            # Code ownership
│   ├── pull_request_template.md
│   └── SECURITY.md
│
├── CONTRIBUTING.md           # Contribution guidelines
├── .editorconfig             # Editor configuration
└── README.md                 # This file
```

## 🔄 CI/CD & Path Filtering

The CI/CD workflows are **strictly scoped** by path filters to prevent cross-contamination:

- **ChainBridge CI** (`ci.yml`) - Triggers only on changes to `ChainBridge/**`
- **BensonBot CI** (`trading-bot-ci.yml`) - Triggers only on changes to trading bot files

This ensures that changes to one product don't unnecessarily trigger CI for the other product.

## 📚 Documentation

### ChainBridge
- [ChainBridge README](ChainBridge/README.md) - Platform overview and architecture
- [Governance Docs](ChainBridge/docs/governance/) - ALEX compliance documentation
- Service-specific READMEs in each microservice directory

### BensonBot
- [BensonBot README](docs/bensonbot/README.md) - Trading bot overview
- [Market Regime Detection](docs/MARKET_REGIME_DETECTION.md) - ML regime detection
- [Regime-Specific Backtesting](docs/REGIME_SPECIFIC_BACKTESTING.md) - Strategy evaluation
- [Regime-Based Strategies](docs/REGIME_BASED_STRATEGIES.md) - Market-specific configurations

### General
- [Repository Map](docs/REPO_MAP.md) - Detailed structure guide
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute
- [Security Policy](.github/SECURITY.md) - Security reporting

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Branch naming conventions
- PR requirements and templates
- Testing requirements ("stop-the-line" policy)
- Code review process

## 🔒 Security

- Report vulnerabilities via [GitHub Security Advisories](https://github.com/BIGmindz/ChainBridge/security/advisories)
- See [SECURITY.md](.github/SECURITY.md) for full policy
- CodeQL scanning enabled for both products
- Dependabot alerts monitored

## 📜 License

MIT License - See individual product READMEs for details.

---

## 60-Second Onboarding

**New to the repo?**

1. **Identify your product**: ChainBridge (logistics) or BensonBot (trading)
2. **Navigate to the right place**: `cd ChainBridge/` or stay at root
3. **Read the product README**: Links above
4. **Set up environment**: Follow Quick Start for your product
5. **Run tests**: Verify your setup works

**Questions?** Check [REPO_MAP.md](docs/REPO_MAP.md) for detailed navigation.

---

**Built with ❤️ by [@BIGmindz](https://github.com/BIGmindz)**
