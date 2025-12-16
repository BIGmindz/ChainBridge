# ChainBridge & BensonBot - Repository Guide

This repository contains two major systems:
1. **BensonBot**: A sophisticated cryptocurrency trading bot with multi-signal aggregation (root level)
2. **ChainBridge**: A microservices platform for freight logistics and tokenization (ChainBridge/ subdirectory)

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Table of Contents
- [Repository Overview](#repository-overview)
- [BensonBot Trading System](#bensonbot-trading-system)
- [ChainBridge Microservices Platform](#chainbridge-microservices-platform)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Common Tasks](#common-tasks)

## Repository Overview

### Top-Level Structure

```text
/
├── main.py                         # BensonBot entry point
├── README.md                       # Main documentation
├── Makefile                        # Build automation
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Python project configuration
├── .python-version                 # Python 3.11.9
├── docker-compose.yml              # Container orchestration
├── .github/
│   ├── copilot-instructions.md     # This file
│   └── workflows/
│       ├── ci.yml                  # Basic CI/CD
│       └── trading-bot-ci.yml      # Comprehensive CI pipeline
├── ChainBridge/                    # Microservices platform (separate subdirectory)
│   ├── chainboard-service/         # Driver identity & onboarding (port 8000)
│   ├── chainiq-service/            # ML risk scoring engine (port 8001)
│   ├── chainfreight-service/       # Shipment & tokenization (port 8002)
│   ├── chainpay-service/           # Payment settlement (port 8003)
│   └── chainboard-ui/              # Frontend dashboard
├── modules/                        # BensonBot trading modules
│   ├── adaptive_weight_module/
│   ├── market_regime_module/
│   └── risk_management/
├── strategies/                     # Market regime strategies
│   ├── bear_market/
│   ├── bull_market/
│   └── sideways_market/
├── docs/                           # Documentation
│   ├── MARKET_REGIME_DETECTION.md
│   ├── REGIME_SPECIFIC_BACKTESTING.md
│   └── KRAKEN_PAPER_TRADING.md
├── scripts/                        # Utility scripts
├── tests/                          # Test suites
├── core/                           # Core system components
├── api/                            # REST API layer
└── proofpacks/                     # Governance documentation
```

### Technology Stack

**BensonBot (Root Level)**:
- Python 3.11+
- FastAPI (REST API)
- CCXT (exchange integration)
- TensorFlow/Keras (ML models)
- Pandas/NumPy (data processing)
- Streamlit/Dash (dashboards)
- SQLite (local storage)

**ChainBridge (Microservices)**:
- Python 3.11+
- FastAPI (all services)
- SQLAlchemy (ORM)
- SQLite/PostgreSQL (database)
- Pydantic (validation)
- OpenAPI/Swagger (documentation)

---

## BensonBot Trading System

### Overview

BensonBot is a sophisticated multi-signal cryptocurrency trading bot with:
- Multi-signal aggregation with adaptive weights
- Market regime detection (bull/bear/sideways)
- Canonical RSI thresholds: BUY=35, SELL=64 (enforced system-wide)
- Live trading safety guards and confirmation requirements
- Real-time monitoring dashboards (Streamlit, Dash)
- Comprehensive backtesting and paper trading modes

### Entry Points

- **main.py** - Canonical entry point for all trading operations (live, paper, backtest)
- **benson_rsi_bot.py** - Legacy entry point (deprecated in favor of main.py)
- **live_trading_bot.py** - Core live trading engine
- **integrated_trading_system.py** - Multi-signal aggregation system

### Key Components

**Trading Signal Modules**:
- RSI Module (Wilder's RSI calculation)
- MACD Module (Moving Average Convergence Divergence)
- Bollinger Bands Module (Volatility-based analysis)
- Volume Profile Module (Volume-based support/resistance)
- Sentiment Analysis Module (Alternative data sentiment)
- Logistics Signal Module (Supply chain metrics)

**Machine Learning**:
- Market Regime Detection (bull/bear/sideways identification)
- Adaptive Signal Weighting (dynamic weight adjustment)
- Sales Forecasting (ML-powered predictions)

**Risk Management**:
- Position Sizing (Kelly Criterion)
- Stop Loss/Take Profit
- Portfolio Tracking
- Dynamic Risk Adjustment

### Configuration

**Required Files**:
- `config/config.yaml` - Main bot configuration (exchange, symbols, thresholds)
- `.env` - API keys and environment variables (copy from .env.example)
- `.venv/` - Python virtual environment (created by `make venv`)

**Key Configuration Options**:
- Exchange: kraken (default), coinbase, binance, bybit
- Symbols: BTC/USD, ETH/USD, SOL/USD, etc.
- RSI thresholds: buy_threshold=35, sell_threshold=64 (canonical, enforced system-wide)
- Polling interval: poll_seconds (default 60)
- Risk management: stop_loss_pct, take_profit_pct

### Bootstrap, Build, and Test

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

### Running the Bot

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

### Validation Steps

**Required Validation**:
- **ALWAYS run unit tests** after changes: `python benson_rsi_bot.py --test`
- **ALWAYS run linting** before committing: `make lint`
- **Test data ingestion**: `python -c "import data_ingestor; print(data_ingestor.fetch_all_alternative_data())"`
- **Verify configuration**: Check that config/config.yaml loads without errors
- **Test RSI calculations**: All 5 built-in tests must pass

**What WORKS in Restricted Environments**:
- Virtual environment setup and dependency installation
- All unit tests (completely offline)
- Code linting and formatting
- Mock data ingestion functions
- Configuration file parsing
- RSI calculation algorithms

**What FAILS in Restricted Environments (Expected)**:
- Live bot execution (requires exchange API access)
- Docker build (certificate verification issues)
- Standalone test_rsi.py (requires Coinbase API access)
- make venv/make install (pip timeout errors when PyPI unreachable)

### Time Expectations

**CRITICAL - Always set appropriate timeouts and NEVER CANCEL:**
- Virtual environment setup: ~10 seconds (use 30s timeout)
- Dependency installation: ~90 seconds - NEVER CANCEL - Set timeout to 180+ seconds
- Unit tests: ~1 second (use 30s timeout)
- Linting: ~2 seconds (use 30s timeout)
- Bot startup: ~1 second before network failure (in restricted environments)
- Docker build: Fails at ~30 seconds due to network restrictions

---

## ChainBridge Microservices Platform

### Overview

ChainBridge is a freight logistics and tokenization platform consisting of four core microservices that work together to provide driver onboarding, ML-powered risk scoring, shipment management, and payment settlement.

### Microservices Architecture

```text
┌─────────────────────────────────┐
│   ChainBoard Service (8000)     │
│   Driver Identity & Onboarding  │
│   - Driver registration         │
│   - Profile management          │
│   - Verification & compliance   │
└─────────────────────────────────┘
                ↓
┌─────────────────────────────────┐
│   ChainIQ Service (8001)        │
│   ML Risk Scoring Engine        │
│   - Shipment risk scoring       │
│   - Driver reliability          │
│   - Anomaly detection           │
└─────────────────────────────────┘
                ↓
┌─────────────────────────────────┐
│   ChainFreight Service (8002)   │
│   Shipment & Tokenization       │
│   - Shipment lifecycle          │
│   - Freight tokenization        │
│   - ChainIQ integration         │
└─────────────────────────────────┘
                ↓
┌─────────────────────────────────┐
│   ChainPay Service (8003)       │
│   Risk-Based Payment Settlement │
│   - Payment intents             │
│   - Conditional settlement      │
│   - Audit logging               │
└─────────────────────────────────┘
```

### ChainBoard Service (Port 8000)

**Purpose**: Driver identity and onboarding

**Key Features**:
- Driver registration and profile management
- CDL and DOT number tracking
- Driver search and filtering
- Soft deletion (inactive status)

**Key Endpoints**:
- `POST /drivers` - Create driver
- `GET /drivers` - List drivers (paginated, filterable)
- `GET /drivers/{id}` - Get specific driver
- `PUT /drivers/{id}` - Update driver
- `DELETE /drivers/{id}` - Soft delete driver
- `GET /drivers/search` - Search by email or DOT number

**Running**:
```bash
cd ChainBridge/chainboard-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### ChainIQ Service (Port 8001)

**Purpose**: ML-powered risk scoring and decision engine

**Key Features**:
- Shipment risk scoring (0.0-1.0 scale)
- Risk categorization (low/medium/high)
- Driver reliability assessment
- Anomaly detection

**Key Endpoints**:
- `POST /score/shipment` - Score shipment risk
- `GET /health` - Service health check

**Risk Scoring**:
- **LOW** (0.0-0.33): Standard approval
- **MEDIUM** (0.33-0.67): Additional conditions
- **HIGH** (0.67-1.0): Detailed review required

**Running**:
```bash
cd ChainBridge/chainiq-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
# API docs: http://localhost:8001/docs
```

**Note**: Current implementation uses deterministic placeholder scoring. Real ML engine will integrate multi-signal aggregation from BensonBot's architecture.

### ChainFreight Service (Port 8002)

**Purpose**: Shipment lifecycle management and freight tokenization

**Key Features**:
- Shipment creation and tracking
- Status lifecycle management
- **Freight tokenization** (enables fractional ownership and trading)
- Automatic ChainIQ risk scoring integration
- Graceful degradation if ChainIQ unavailable

**Key Endpoints**:
- `POST /shipments` - Create shipment
- `GET /shipments` - List shipments (paginated, filterable by status)
- `GET /shipments/{id}` - Get specific shipment
- `PUT /shipments/{id}` - Update shipment
- `POST /shipments/{id}/tokenize` - Tokenize freight (calls ChainIQ for risk)
- `GET /shipments/{id}/token` - Get shipment's token
- `GET /tokens` - List all tokens
- `GET /tokens/{id}` - Get specific token

**Shipment Status Flow**:
```text
pending → picked_up → in_transit → delivered
                   ↘ cancelled
```

**Token Status Flow**:
```text
created → active → (locked) → redeemed | expired | cancelled
```

**Running**:
```bash
cd ChainBridge/chainfreight-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
# API docs: http://localhost:8002/docs
```

**Freight Tokenization Benefits**:
- Fractional ownership of high-value shipments
- Trading on secondary markets
- Collateral for working capital financing
- Blockchain integration (future: on-chain ERC-20 tokens)

### ChainPay Service (Port 8003)

**Purpose**: Risk-based conditional payment settlement

**Key Features**:
- Risk-aware payment intents tied to freight tokens
- Conditional settlement logic based on risk tier
- Automatic decision: LOW=immediate, MEDIUM=24h delay, HIGH=manual review
- Complete audit logging
- Fetches risk scores from ChainFreight tokens

**Key Endpoints**:
- `POST /payment_intents` - Create payment intent
- `POST /payment_intents/{id}/assess_risk` - View risk assessment
- `POST /payment_intents/{id}/settle` - Settle payment (applies risk logic)
- `POST /payment_intents/{id}/complete` - Complete settlement
- `GET /payment_intents` - List intents (filterable by status, risk_tier)
- `GET /payment_intents/{id}` - Get specific intent
- `GET /payment_intents/{id}/history` - Audit log

**Risk-Based Settlement Logic**:

| Risk Tier | Score Range | Settlement | Delay |
|-----------|-------------|-----------|-------|
| LOW | 0.0-0.33 | Immediate | None |
| MEDIUM | 0.33-0.67 | Delayed | 24 hours |
| HIGH | 0.67-1.0 | Manual Review | ∞ (requires force_approval) |

**Running**:
```bash
cd ChainBridge/chainpay-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
# API docs: http://localhost:8003/docs
```

**Settlement Workflow**:
1. Create payment intent (fetches token from ChainFreight)
2. Extract risk_score and risk_category from token
3. Map to settlement tier (LOW/MEDIUM/HIGH)
4. Apply conditional logic on settle request
5. Log all decisions to audit trail

### Running All Microservices Together

```bash
# Terminal 1: ChainBoard
cd ChainBridge/chainboard-service && uvicorn app.main:app --port 8000 --reload

# Terminal 2: ChainIQ
cd ChainBridge/chainiq-service && uvicorn app.main:app --port 8001 --reload

# Terminal 3: ChainFreight
cd ChainBridge/chainfreight-service && uvicorn app.main:app --port 8002 --reload

# Terminal 4: ChainPay
cd ChainBridge/chainpay-service && uvicorn app.main:app --port 8003 --reload
```

### Testing ChainBridge Services

**Full Integration Test**:
```bash
# 1. Create driver in ChainBoard
DRIVER=$(curl -s -X POST http://localhost:8000/drivers \
  -H "Content-Type: application/json" \
  -d '{"first_name":"John","last_name":"Doe","email":"john@example.com","phone":"555-1234","dot_number":"DOT123","cdl_number":"CDL789"}' \
  | jq -r '.id')

# 2. Create shipment in ChainFreight
SHIP=$(curl -s -X POST http://localhost:8002/shipments \
  -H "Content-Type: application/json" \
  -d '{"shipper_name":"ACME","origin":"LA","destination":"CHI","cargo_value":100000}' \
  | jq -r '.id')

# 3. Tokenize shipment (ChainFreight calls ChainIQ for risk score)
TOKEN=$(curl -s -X POST http://localhost:8002/shipments/$SHIP/tokenize \
  -H "Content-Type: application/json" \
  -d '{"face_value":100000,"currency":"USD"}' | jq -r '.id')

# 4. View token with risk score
curl -s http://localhost:8002/tokens/$TOKEN | jq .

# 5. Create payment intent in ChainPay (fetches token from ChainFreight)
PAYMENT=$(curl -s -X POST http://localhost:8003/payment_intents \
  -H "Content-Type: application/json" \
  -d '{"freight_token_id":'$TOKEN',"amount":100000,"currency":"USD"}' \
  | jq -r '.id')

# 6. Assess payment risk
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/assess_risk | jq .

# 7. Settle payment (applies risk-based conditional logic)
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/settle \
  -H "Content-Type: application/json" \
  -d '{"settlement_notes":"Approved"}' | jq .

# 8. Complete settlement
curl -s -X POST http://localhost:8003/payment_intents/$PAYMENT/complete | jq '.status'
```

### ChainBridge Database Architecture

**ChainBoard**: `chainboard.db` (SQLite)
- drivers table (id, first_name, last_name, email, phone, dot_number, cdl_number, is_active)

**ChainFreight**: `chainfreight.db` (SQLite)
- shipments table (id, shipper_name, origin, destination, status, dates, cargo_value)
- freight_tokens table (id, shipment_id, face_value, currency, status, risk_score, risk_category, recommended_action, token_address)

**ChainPay**: `chainpay.db` (SQLite)
- payment_intents table (id, freight_token_id, amount, currency, risk_score, risk_category, risk_tier, status, settlement timestamps, notes)
- settlement_logs table (id, payment_intent_id, action, reason, triggered_by, approved_by, created_at)

**Production**: All services support PostgreSQL via `DATABASE_URL` environment variable.

---

## Development Workflow

### Setup (One-Time)

```bash
# For BensonBot
make venv && make install

# For ChainBridge services (each service independently)
cd ChainBridge/<service-name>
pip install -r requirements.txt
```

### Making Changes

1. **Identify the Component**:
   - BensonBot changes: Root-level files (main.py, modules/, strategies/)
   - ChainBridge changes: ChainBridge/ subdirectory

2. **Make Code Changes**:
   - Follow existing patterns and architecture
   - Use type hints (Python 3.11+)
   - Update docstrings
   - Add/update tests as needed

3. **Test Changes**:
   ```bash
   # BensonBot
   python benson_rsi_bot.py --test
   make lint
   
   # ChainBridge services
   pytest tests/  # if tests exist
   # Test via API docs: http://localhost:<port>/docs
   ```

4. **Format and Lint**:
   ```bash
   make fmt   # Format code
   make lint  # Check code quality
   ```

5. **Documentation**:
   - Update relevant README files
   - Update this file if architecture changes
   - Add/update API documentation in docstrings

### Common Development Patterns

**BensonBot**:
- All trading modules follow the `Module` interface in `core/module_manager.py`
- Configuration uses `config/config.yaml` and environment variables
- RSI thresholds are canonical: BUY=35, SELL=64 (enforced)
- Use adaptive weighting for signal combination
- Market regime detection optimizes strategy selection

**ChainBridge**:
- All services use FastAPI with Pydantic schemas
- Database models use SQLAlchemy ORM
- Services communicate via HTTP REST APIs
- Graceful degradation when services unavailable
- Complete audit logging for compliance
- Risk scoring integrated at tokenization

---

## Testing

### BensonBot Testing

**Unit Tests**:
```bash
# Built-in RSI tests (5 scenarios)
python benson_rsi_bot.py --test

# Pytest suite
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=. --cov-report=xml
```

**Integration Tests**:
```bash
# Multi-signal demonstration
python benson_system.py --mode multi-signal-demo

# System tests
python benson_system.py --mode test
```

**Manual Testing**:
```bash
# Paper trading (safe, no real money)
python main.py --mode paper

# Backtest historical data
python main.py --mode backtest
```

### ChainBridge Testing

**Service Tests**:
```bash
cd ChainBridge/<service-name>

# Run service-specific tests
pytest tests/ -v

# Examples:
cd ChainBridge/chainpay-service
pytest tests/test_end_to_end_milestones.py -v
pytest tests/test_payment_rails.py -v
```

**API Testing**:
- Use Swagger UI at `http://localhost:<port>/docs`
- Interactive testing and documentation
- Try all endpoints with sample data

**Integration Testing**:
- See "Testing ChainBridge Services" section above
- Test full workflow across all 4 services
- Verify risk scoring propagation

### Test Coverage

- BensonBot: RSI calculation, signal modules, regime detection
- ChainBoard: Driver CRUD operations
- ChainIQ: Risk scoring algorithms
- ChainFreight: Shipment lifecycle, tokenization, ChainIQ integration
- ChainPay: Payment settlement, risk-based logic, audit logging

---

## CI/CD

### GitHub Actions Workflows

**`.github/workflows/ci.yml`** (Basic CI):
- Runs on push to main and pull requests
- Python 3.11 setup
- Install dependencies
- Run BensonBot unit tests (`python benson_rsi_bot.py --test`)
- Deploy on main branch

**`.github/workflows/trading-bot-ci.yml`** (Comprehensive):
- Security scanning (CodeQL)
- Code quality (black, pylint, flake8, mypy)
- Safety audit (bandit, safety)
- Configuration validation
- Unit and integration tests
- Coverage reporting (codecov)
- Markdown fence normalization
- Markdown linting
- Staging deployment (develop branch)
- Production deployment (main branch, manual approval)

### Running CI Checks Locally

```bash
# Code formatting
make fmt

# Linting
make lint

# Tests
make test

# Documentation quality
make docs-lint
make docs-fix

# Pre-commit hooks
make pre-commit-install
make pre-commit-run
```

### CI/CD Best Practices

- **Always run tests** before committing
- **Lint and format** code before PR
- **Update tests** when changing functionality
- **Document breaking changes** in PR description
- **Use conventional commits** for clear history
- **Tag releases** with semantic versioning

---

## Common Tasks

### BensonBot Tasks

**Development Workflow**:
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

**Select Volatile Cryptocurrencies**:
```bash
make select-dynamic  # Uses default settings
# OR
EXCHANGE=kraken TOP_N=30 TF=1h LB=24 make select-dynamic
```

**Run Trading Operations**:
```bash
# Paper trading (safe)
make run-once-paper

# Live trading (requires API keys)
make run-once-live

# Continuous live trading
make run-live
```

**Monitor Performance**:
```bash
# Start dashboard
./run_streamlit_dashboard.sh
# OR
streamlit run dashboard.py
```

### ChainBridge Tasks

**Add New Driver**:
```bash
curl -X POST http://localhost:8000/drivers \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Jane","last_name":"Smith","email":"jane@example.com","phone":"555-5678","dot_number":"DOT456","cdl_number":"CDL123"}'
```

**Create and Tokenize Shipment**:
```bash
# Create shipment
SHIP=$(curl -s -X POST http://localhost:8002/shipments \
  -H "Content-Type: application/json" \
  -d '{"shipper_name":"TestCo","origin":"LA","destination":"NY","cargo_value":50000}' \
  | jq -r '.id')

# Tokenize (gets risk score from ChainIQ)
curl -X POST http://localhost:8002/shipments/$SHIP/tokenize \
  -H "Content-Type: application/json" \
  -d '{"face_value":50000,"currency":"USD"}'
```

**Settle Payment**:
```bash
# Create payment intent
PAYMENT=$(curl -s -X POST http://localhost:8003/payment_intents \
  -H "Content-Type: application/json" \
  -d '{"freight_token_id":1,"amount":50000,"currency":"USD"}' \
  | jq -r '.id')

# Settle based on risk
curl -X POST http://localhost:8003/payment_intents/$PAYMENT/settle \
  -H "Content-Type: application/json" \
  -d '{"settlement_notes":"Approved by finance"}'
```

**Database Inspection**:
```bash
# ChainBoard drivers
sqlite3 ChainBridge/chainboard-service/chainboard.db "SELECT * FROM drivers;"

# ChainFreight tokens
sqlite3 ChainBridge/chainfreight-service/chainfreight.db "SELECT * FROM freight_tokens;"

# ChainPay settlements
sqlite3 ChainBridge/chainpay-service/chainpay.db "SELECT * FROM payment_intents;"
```

### Troubleshooting

**BensonBot**:
- **"NetworkError" or "ConnectionError"**: Expected in sandboxed environments - network restrictions prevent API access
- **"SSL: CERTIFICATE_VERIFY_FAILED"**: Expected in Docker builds - certificate chain issues
- **"Read timed out" during pip**: Expected in network-restricted environments - PyPI unreachable
- **"ModuleNotFoundError"**: Run `make install` to install dependencies
- **"FileNotFoundError: config/config.yaml"**: Configuration file missing
- **Unit test failures**: RSI calculation logic error - review wilder_rsi() function

**ChainBridge**:
- **Service won't start**: Check port availability (8000-8003), ensure dependencies installed
- **ChainIQ unavailable**: ChainFreight tokenization still works (graceful degradation), risk fields set to null
- **Payment settlement rejected**: High-risk tokens require `force_approval: true` in settle request
- **Database locked**: Only one process can access SQLite database at a time
- **Port already in use**: Kill existing process or use different port: `uvicorn app.main:app --port 8XXX`

**General**:
- **Import errors**: Ensure you're in correct directory and virtual environment activated
- **Permission denied**: Make scripts executable: `chmod +x script.sh`
- **Git conflicts**: Use `git status` and resolve conflicts before committing

---

## Security and Best Practices

### Secrets Management

- **NEVER commit API keys** or secrets to version control
- Use `.env` file for sensitive data (already in `.gitignore`)
- Copy `.env.example` to `.env` and fill in values
- Use environment variables: `${VARIABLE_NAME}` in config files
- Rotate API keys regularly
- Use paper trading (`PAPER=true`) for testing

### Code Quality

- **Type hints**: Always use Python type hints
- **Documentation**: Add docstrings to functions and classes
- **Error handling**: Return appropriate HTTP status codes, log errors
- **Validation**: Use Pydantic schemas for API request/response
- **Testing**: Write tests for new functionality
- **Linting**: Run `make lint` before committing
- **Formatting**: Use `make fmt` for consistent code style

### Database

- **SQLite for development**: Simple and fast
- **PostgreSQL for production**: Set `DATABASE_URL` environment variable
- **Migrations**: Use Alembic for schema changes in production
- **Backups**: Regular database backups in production
- **Soft deletes**: Prefer soft deletes (is_active flag) over hard deletes

### API Design

- **RESTful patterns**: Follow REST principles
- **Versioning**: Consider API versioning for breaking changes
- **Documentation**: FastAPI auto-generates OpenAPI docs at `/docs`
- **Error responses**: Consistent error format with detail message
- **Pagination**: Use skip/limit for list endpoints
- **Filtering**: Support query parameters for filtering

---

## Architecture Decisions

### Why Two Systems?

**BensonBot** was the original project - a sophisticated crypto trading bot with ML capabilities. **ChainBridge** repurposes the multi-signal aggregation and ML architecture for freight logistics.

**Shared Patterns**:
- Multi-signal aggregation (crypto signals → logistics signals)
- Adaptive weighting (market signals → risk factors)
- Regime detection (bull/bear/sideways → peak/off-peak seasons)
- Risk management (position sizing → payment settlement logic)

**Separation**:
- BensonBot: Root level, trading-focused
- ChainBridge: Subdirectory, microservices for logistics
- Each can be deployed independently
- Shared Python environment and tooling

### Future Enhancements

**BensonBot**:
- On-chain trading via DEX integration
- Advanced ML models (LSTM, transformers)
- Multi-exchange arbitrage
- Social trading features

**ChainBridge**:
- Real blockchain integration (ERC-20 freight tokens)
- ChainBoard UI full implementation
- Real-time GPS tracking
- Automated delivery confirmation
- Smart contract payment settlement
- Carrier API integrations
- Mobile apps for drivers

---

## Additional Resources

**Documentation**:
- [BensonBot README](../README.md)
- [ChainBridge README](../ChainBridge/README.md)
- [Market Regime Detection](../docs/MARKET_REGIME_DETECTION.md)
- [Regime-Specific Backtesting](../docs/REGIME_SPECIFIC_BACKTESTING.md)
- [Kraken Paper Trading](../docs/KRAKEN_PAPER_TRADING.md)
- [ProofPack Governance](../proofpacks/PROOFPACK_GOVERNANCE.md)

**Service READMEs**:
- [ChainBoard Service](../ChainBridge/chainboard-service/README.md)
- [ChainIQ Service](../ChainBridge/chainiq-service/README.md)
- [ChainFreight Service](../ChainBridge/chainfreight-service/README.md)
- [ChainPay Service](../ChainBridge/chainpay-service/README.md)

**External Links**:
- [Best Practices for Copilot Coding Agent](https://gh.io/copilot-coding-agent-tips)
- [GitHub Repository](https://github.com/BIGmindz/ChainBridge)

---

## Quick Reference

### Ports
- ChainBoard: 8000
- ChainIQ: 8001  
- ChainFreight: 8002
- ChainPay: 8003
- BensonBot API: 8000 (when running API server mode)

### Python Version
- 3.11.9 (specified in `.python-version`)

### Key Commands
```bash
# BensonBot
make help                    # Show all available commands
make venv                    # Create virtual environment
make install                 # Install dependencies
make test                    # Run tests
make lint                    # Lint code
make fmt                     # Format code
make quick-checks            # Fast validation (no TensorFlow)

# ChainBridge
cd ChainBridge/<service>     # Navigate to service
pip install -r requirements.txt  # Install deps
uvicorn app.main:app --port <port> --reload  # Run service
pytest tests/ -v             # Run tests
```

### Environment Variables
```bash
# BensonBot (.env)
API_KEY=<your_exchange_api_key>
API_SECRET=<your_exchange_api_secret>
EXCHANGE=kraken
PAPER=true

# ChainBridge (optional)
DATABASE_URL=postgresql://user:pass@localhost/dbname
CHAINFREIGHT_URL=http://localhost:8002
```

---

**Last Updated**: 2025-12-16
**Repository**: BIGmindz/ChainBridge
**Python Version**: 3.11.9
**License**: MIT


