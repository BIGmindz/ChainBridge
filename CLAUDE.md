# ChainBridge Repository Guide for AI Assistants

**Last Updated:** 2025-11-14

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Directory Structure](#directory-structure)
3. [Core Architecture](#core-architecture)
4. [Key Modules & Responsibilities](#key-modules--responsibilities)
5. [Entry Points & How to Run](#entry-points--how-to-run)
6. [Configuration Management](#configuration-management)
7. [Dependencies & Tech Stack](#dependencies--tech-stack)
8. [Testing Strategy](#testing-strategy)
9. [Development Workflows](#development-workflows)
10. [Common Development Tasks](#common-development-tasks)
11. [Security & Authentication](#security--authentication)
12. [Deployment](#deployment)

---

## Project Overview

ChainBridge is a **dual-purpose system**:

1. **ProofPacks API** - A FastAPI service for managing cryptographically-signed proof packs for enterprise supply chain and logistics operations. It handles:
   - Shipment tokenization and verification
   - Event-driven proof pack creation and retrieval
   - HMAC-SHA256 response signing for integrity verification
   - Canonical JSON serialization for deterministic hashing

2. **Benson Trading System** - A multi-signal cryptocurrency trading bot with:
   - Market regime detection (bull/bear/sideways)
   - Multi-signal aggregation (technical, sentiment, on-chain, proprietary)
   - Risk management and capital allocation
   - Support for multiple crypto exchanges (Kraken, Binance, Bybit)
   - Paper trading and live trading modes
   - Modular architecture for signal modules

**PoC Focus:** USD ↔ MXN cross-border freight trading corridor with targets: P95 < 90s settlement, STP ≥ 95%, 80% audit prep time reduction.

---

## Directory Structure

```
ChainBridge/
├── src/                              # Primary source code (6,668 LOC)
│   ├── api/
│   │   └── proofpacks_api.py        # FastAPI router for ProofPack endpoints
│   ├── security/
│   │   ├── signing.py               # HMAC-SHA256 signing, canonical JSON
│   │   └── __init__.py
│   ├── bot/
│   │   ├── core/
│   │   │   ├── secrets_manager.py   # API credentials management
│   │   │   ├── observability.py     # Logging and monitoring
│   │   │   ├── resilient_data_fetcher.py
│   │   │   └── ...
│   │   └── main.py
│   ├── core/
│   │   ├── unified_trading_engine.py # Market regime detection
│   │   ├── pattern_engine.py
│   │   └── ...
│   ├── dashboard/
│   │   └── live_dashboard.py        # Real-time monitoring UI
│   ├── backtesting/
│   ├── exchange_adapter.py          # Exchange integration abstraction
│   ├── data_provider.py             # Market data fetching
│   ├── crypto_selector.py           # Dynamic symbol selection
│   ├── trading_mode.py              # Paper vs. Live mode switching
│   ├── signal_engine.py             # Signal aggregation
│   └── __init__.py

├── core/                            # Core modular framework
│   ├── module_manager.py            # Module registration and loading
│   ├── pipeline.py                  # Pipeline orchestration
│   ├── data_processor.py            # Data processing utilities
│   └── __init__.py

├── modules/                         # Signal analysis modules (25+ modules)
│   ├── rsi_module.py               # Relative Strength Index
│   ├── macd_module.py              # MACD indicator
│   ├── bollinger_bands_module.py   # Bollinger Bands
│   ├── volume_profile_module.py    # Volume Profile analysis
│   ├── sentiment_analysis_module.py # Sentiment signals
│   ├── global_macro_module.py      # Macro-economic indicators
│   ├── logistics_signal_module.py  # Logistics-specific signals
│   ├── adoption_tracker_module.py  # Adoption metrics
│   ├── new_listings_radar_module.py# Exchange listings detector
│   ├── region_specific_crypto_module.py
│   ├── multi_signal_aggregator_module.py
│   ├── adaptive_weight_module/     # Adaptive weighting system
│   ├── machine_learning_module/    # ML models
│   └── __init__.py

├── tests/                          # Unit and integration tests (13 test files)
│   ├── test_rsi_scenarios.py
│   ├── test_ev_thresholding.py
│   ├── test_purged_kfold.py
│   ├── test_config_validation.py
│   ├── test_module_manager.py
│   └── ...

├── scripts/                        # Utility and automation scripts
│   ├── integrator_smoke_test.py
│   ├── normalize_markdown_fences.py
│   ├── preflight_config_symbols.py
│   ├── run_multi_signal_lean.sh
│   └── ...

├── proofpacks/                     # ProofPacks API governance
│   └── PROOFPACK_GOVERNANCE.md    # Customer control and compliance doc

├── config/                         # Configuration templates
│   ├── config.yaml                 # Main trading config
│   ├── kraken_paper_trading.yaml   # Exchange-specific config
│   ├── regime_bull.yaml            # Market regime configs
│   ├── regime_bear.yaml
│   ├── regime_sideways.yaml
│   └── ...

├── apps/                           # Legacy app services
│   ├── backtester/
│   └── dashboard/

├── chainiq-service/                # Risk scoring service
└── chainboard-service/             # Monitoring service

├── strategies/                     # Pre-trained strategy models
│   ├── bull_market/
│   ├── bear_market/
│   └── sideways_market/

├── tracking/                       # Metrics collection
│   └── metrics_collector.py

├── utils/                          # Utility modules

├── docs/                           # Documentation and ADRs

├── main.py                         # FastAPI application entry point
├── benson_system.py                # Main bot orchestration (entry point)
├── benson_rsi_bot.py              # Legacy RSI bot (entry point)
├── multi_signal_bot.py             # Multi-signal bot variant
├── live_trading_bot.py             # Live trading entry point

├── Makefile                        # Build and development targets
├── docker-compose.yml              # Service orchestration
├── Dockerfile                      # Multi-stage container build
├── requirements.txt                # Main dependencies
├── requirements-runtime.txt        # Lean runtime deps
├── requirements-dev.txt            # Development deps
├── requirements-enterprise.txt     # Enterprise features

├── .env.example                    # Configuration template
├── config.yaml                     # Default configuration
├── .pre-commit-config.yaml         # Pre-commit hooks
├── pyproject.toml                  # Python project metadata
├── .flake8                         # Flake8 linting config
├── .pylintrc                       # Pylint configuration
└── README.md                       # Project README
```

---

## Core Architecture

### 1. **ProofPacks API Tier** (FastAPI)

**Location:** `src/api/proofpacks_api.py` + `src/security/signing.py`

**Purpose:** Cryptographically-sealed proof bundles for supply chain compliance.

**Key Components:**
- **Endpoints:**
  - `POST /proofpacks/run` - Create a new proof pack from shipment events
  - `GET /proofpacks/{pack_id}` - Retrieve a proof pack with signature verification
  
- **Signing Strategy:**
  - Algorithm: HMAC-SHA256
  - Key: `SIGNING_SECRET` from environment
  - Headers: `X-Signature`, `X-Signature-Alg`, `X-Signature-KeyId`, `X-Signature-Timestamp`
  - Deterministic JSON serialization (sorted keys, no spaces)

- **Models:**
  - `ProofEvent` - Single event in a proof pack
  - `ProofPackRequest` - Request to create a proof pack
  - Manifest includes: shipment ID, event history, risk score, policy version, generated timestamp

- **Storage:**
  - Runtime directory: `proofpacks/runtime/`
  - Retention: Customer-configurable (default 7 days)
  - Format: Deterministic JSON with SHA-256 manifest hash

### 2. **Benson Trading Bot Tier** (Multi-Signal)

**Location:** `benson_system.py`, `benson_rsi_bot.py`, `multi_signal_bot.py`

**Purpose:** Multi-signal cryptocurrency trading with regime detection.

**Core Concepts:**
- **Market Regime Detection** (via `src/core/unified_trading_engine.py`)
  - BULL: Price change > 10%, uptrend momentum
  - BEAR: Price change < -10%, downtrend momentum
  - SIDEWAYS: Low volatility, no clear trend
  - Unknown: Insufficient data

- **Signal Weighting per Regime:**
  - BULL: Technical (1.2x), Sentiment (0.8x), On-chain (1.3x), Proprietary (1.1x)
  - BEAR: Technical (1.0x), Sentiment (1.3x), On-chain (1.2x), Proprietary (1.1x)
  - SIDEWAYS: Technical (1.3x), Sentiment (0.7x), On-chain (0.9x), Proprietary (1.2x)

- **Signal Aggregation:**
  - Layer 1 (Technical): RSI, MACD, Bollinger Bands, Volume Profile, Sentiment
  - Layer 2 (Logistics): Logistics signals
  - Layer 3 (Macro): Global macro, adoption tracker, regional crypto mapping
  - Layer 4 (New Listings): New exchange listings radar

### 3. **Modular Signal Architecture**

**Location:** `core/module_manager.py`, `core/pipeline.py`, `modules/`

**Design Pattern:**
```python
class Module(ABC):
    def process(self, data: Dict) -> Dict:        # Process input
    def get_schema(self) -> Dict:                 # Declare input/output
    def validate_input(self, data: Dict) -> bool  # Validate inputs
```

**Module Manager:**
- Dynamically loads modules from paths (e.g., `modules.rsi_module`)
- Registers modules by class name (e.g., `RSIModule`)
- Executes modules with validation
- Lists and queries module metadata

**Pipeline Framework:**
- Chains modules together in sequence
- Passes output of one module as input to next
- Records execution history
- Supports step removal and insertion

### 4. **Configuration Management**

**Files (in order of precedence):**
1. Environment variables (highest)
2. `.env` file (if present)
3. `config/config.yaml` (or override via `BENSON_CONFIG`)
4. Defaults in code

**Key Config Sections:**
- `exchange`: Kraken, Binance, Bybit
- `symbols`: List of trading pairs (BTC/USD, ETH/USD, SOL/USD, etc.)
- `timeframe`: Candle interval (1m, 5m, 15m, 1h, 4h)
- `rsi`: RSI period, buy/sell thresholds
- `trading`: Position size, max open trades, slippage
- `risk`: Capital limits, max risk per trade, cooldown
- `adaptive_weights`: Signal layer configuration
- `budget_management`: Kelly criterion, compound settings

---

## Key Modules & Responsibilities

### Trading & Risk Modules

| Module | File | Purpose |
|--------|------|---------|
| **RSI Module** | `modules/rsi_module.py` | Relative Strength Index signals (overbought/oversold) |
| **MACD Module** | `modules/macd_module.py` | Moving Average Convergence Divergence |
| **Bollinger Bands** | `modules/bollinger_bands_module.py` | Volatility and price range analysis |
| **Volume Profile** | `modules/volume_profile_module.py` | Volume-weighted price analysis |
| **Sentiment** | `modules/sentiment_analysis_module.py` | Market sentiment scoring |
| **ADX Module** | `modules/adx_module.py` | Average Directional Index (trend strength) |
| **VWAP Module** | `modules/vwap_module.py` | Volume-Weighted Average Price |
| **Williams %R** | `modules/williams_r_module.py` | Williams R momentum indicator |

### Specialized Modules

| Module | File | Purpose |
|--------|------|---------|
| **Global Macro** | `modules/global_macro_module.py` | Macro-economic indicators (inflation, GDP, rates) |
| **Adoption Tracker** | `modules/adoption_tracker_module.py` | Crypto adoption metrics |
| **Logistics Signals** | `modules/logistics_signal_module.py` | Supply chain & logistics-specific signals |
| **New Listings Radar** | `modules/new_listings_radar_module.py` | Exchange listing detection & analysis |
| **Region Crypto** | `modules/region_specific_crypto_module.py` | Regional adoption & geo-specific signals |
| **Ichimoku Cloud** | `modules/ichimoku_cloud_module.py` | Ichimoku Kinko Hyo cloud indicator |
| **Fibonacci** | `modules/fibonacci_retracement_module.py` | Fibonacci support/resistance levels |
| **Parabolic SAR** | `modules/parabolic_sar_module.py` | Stop and Reverse trend following |

### Infrastructure Modules

| Module | File | Purpose |
|--------|------|---------|
| **Module Manager** | `core/module_manager.py` | Plugin system for signal modules |
| **Pipeline** | `core/pipeline.py` | Chains modules for processing |
| **Data Processor** | `core/data_processor.py` | Normalizes and cleans market data |
| **Metrics Collector** | `tracking/metrics_collector.py` | Tracks business KPIs and usage |
| **Secrets Manager** | `src/bot/core/secrets_manager.py` | API credential encryption/decryption |
| **Observability** | `src/bot/core/observability.py` | Structured logging and correlation IDs |
| **Signing** | `src/security/signing.py` | HMAC-SHA256 response signing |

### Bot Entry Points

| Bot | File | Purpose | Mode |
|-----|------|---------|------|
| **Benson System** | `benson_system.py` | Main orchestrator with multiple modes | api-server, rsi-compat, test |
| **RSI Bot** | `benson_rsi_bot.py` | Legacy RSI-only bot (backward compatible) | Once or continuous |
| **Multi-Signal Bot** | `multi_signal_bot.py` | Advanced multi-signal trading | Live or paper |
| **Live Trading Bot** | `live_trading_bot.py` | Production live trading | Live only |

---

## Entry Points & How to Run

### 1. **ProofPacks API Server**
```bash
# Via Python
python main.py

# Via Benson System wrapper
python benson_system.py --mode api-server --port 8000

# Via Make
make api-server

# Via Docker
docker compose up benson-api
```
**Access:** `http://localhost:8000`  
**Endpoints:** `POST /proofpacks/run`, `GET /proofpacks/{pack_id}`

### 2. **RSI Trading Bot (Legacy)**
```bash
# Single execution (paper trading)
PAPER=true python benson_rsi_bot.py --once

# Continuous execution
PAPER=false python benson_rsi_bot.py

# Via Make (lean environment)
make run-once-paper
make run-once-live
make run-live
```

### 3. **Benson System (Multi-Mode)**
```bash
# API server mode
python benson_system.py --mode api-server --port 8000

# RSI compatibility mode (once)
python benson_system.py --mode rsi-compat --once

# System test mode
python benson_system.py --mode test
```

### 4. **Multi-Signal Bot**
```bash
# Paper trading
PAPER=true python multi_signal_bot.py

# Live trading
PAPER=false python multi_signal_bot.py
```

### 5. **Quick Sanity Checks**
```bash
# Lean environment quick checks (imports + RSI tests + integrator)
make quick-checks

# Run pytest tests
make test

# Code linting
make lint

# Format code
make fmt
```

---

## Configuration Management

### Environment Variables

**Critical Variables:**
```bash
# Exchange & Trading
EXCHANGE=kraken              # kraken, binance, bybit
PAPER=true                  # true=paper, false=live
API_KEY=...                 # Exchange API key
API_SECRET=...              # Exchange API secret

# ProofPacks Security
SIGNING_SECRET=dev-secret   # HMAC signing key (change in prod!)

# Bot Behavior
SYMBOLS=BTC/USD,ETH/USD     # Trading pairs
TIMEFRAME=5m                # Candle interval
COOLDOWN_MINUTES=10         # Trading cooldown
POLL_SECONDS=30             # Data polling interval

# Risk Management
INITIAL_CAPITAL=107.41      # Starting capital (USD)
MAX_RISK_PER_TRADE=0.06     # Risk limit (6%)
MAX_OPEN_TRADES=1           # Max concurrent trades
POSITION_SIZE_USD=50        # Per-trade size
```

### Configuration Files

**Main Config:** `config/config.yaml`
```yaml
exchange: kraken
symbols:
  - BTC/USD
  - ETH/USD
  - SOL/USD
  # ... more symbols
timeframe: 5m
rsi:
  period: 14
  buy_threshold: 35
  sell_threshold: 64
trading:
  max_open_trades: 1
  position_size_usd: 50
  slippage_bps: 5
risk:
  max_risk_per_trade: 0.06
  cooldown_minutes: 5
adaptive_weights:
  enabled: true
  signal_layers:
    LAYER_1_TECHNICAL:
      - RSI
      - MACD
      - BollingerBands
    LAYER_2_LOGISTICS:
      - LogisticsSignal
    LAYER_3_GLOBAL_MACRO:
      - GlobalMacro
    LAYER_4_ADOPTION:
      - NewListingsRadar
```

**Exchange-Specific:** `config/kraken_paper_trading.yaml`  
**Regime Configs:** `config/regime_bull.yaml`, `config/regime_bear.yaml`, `config/regime_sideways.yaml`

**Loading:**
```python
import yaml
config = yaml.safe_load(open('config/config.yaml'))
config = os.path.expandvars(config)  # Substitute ${VARIABLE}
```

---

## Dependencies & Tech Stack

### Core Stack
- **Python:** 3.11 (minimum)
- **Async Framework:** FastAPI, Starlette, Uvicorn
- **Data Processing:** pandas, numpy, scipy, scikit-learn
- **Technical Analysis:** TA-Lib, LightGBM, statsmodels
- **ML/DL:** TensorFlow 2.20, Keras, hmmlearn
- **Exchange API:** CCXT (unified exchange interface)
- **Config:** PyYAML
- **HTTP:** aiohttp, requests
- **Visualization:** Matplotlib, Plotly, Altair, Seaborn
- **Web UI:** Streamlit, Dash, Plotly
- **Serialization:** Pydantic, msgpack

### Development Tools
- **Testing:** pytest
- **Linting:** ruff, flake8
- **Formatting:** ruff format, black
- **Pre-commit:** pre-commit hooks (see `.pre-commit-config.yaml`)
- **CI/CD:** GitHub Actions (if configured)
- **Containerization:** Docker (multi-stage), Docker Compose

### Optional Dependencies
- **Docs:** markdownlint
- **Security:** GPG for signed commits (recommended)
- **Observability:** Prometheus metrics, Grafana dashboards

### Dependency Management

**Main Requirements:** `requirements.txt` (~131 packages)  
**Lean Runtime:** `requirements-runtime.txt` (excludes TensorFlow, grpc, etc.)  
**Development:** `requirements-dev.txt`  
**Enterprise:** `requirements-enterprise.txt`

**Virtual Environment Targets:**
```bash
make venv                    # Create .venv with full deps
make venv-lean              # Create .venv-lean (lightweight)
make install                # Install into .venv
make install-lean           # Install into .venv-lean
```

---

## Testing Strategy

### Test Organization

**Location:** `tests/` directory (13 test modules, 100+ test cases)

**Test Files by Category:**

| File | Purpose |
|------|---------|
| `test_rsi_scenarios.py` | RSI indicator edge cases |
| `test_ev_thresholding.py` | Expected value thresholding |
| `test_purged_kfold.py` | K-fold cross-validation (financial data aware) |
| `test_triple_barrier_labeling.py` | Triple barrier labeling for ML |
| `test_config_validation.py` | Configuration schema validation |
| `test_module_manager.py` | Module loading and registration |
| `test_region_specific_crypto_module.py` | Regional signal testing |
| `test_ev_thresholding.py` | Threshold optimization |
| `test_market_minima.py` | Market minimum detection |
| `test_budget_manager.py` | Capital allocation logic |

### Test Execution

```bash
# Run all tests
make test

# Run lean quick checks (tests + integrator)
make quick-checks

# Run specific test
pytest tests/test_rsi_scenarios.py -v

# Run with coverage
pytest --cov=src tests/

# Run smoke test
python scripts/integrator_smoke_test.py
```

### Testing Patterns

**Unit Tests:**
- Module-level logic (indicators, calculations)
- Configuration validation
- Data processor transformations

**Integration Tests:**
- Module manager loading
- Pipeline execution
- Exchange adapter communication

**Smoke Tests:**
- Import verification
- Configuration loading
- End-to-end flow validation

### Pre-Commit Testing

**Hook:** `lean-quick-checks`  
Automatically runs before commits:
1. `pytest -q tests/test_rsi_scenarios.py`
2. `python scripts/integrator_smoke_test.py`

---

## Development Workflows

### 1. **Standard Development Flow**

```bash
# 1. Create feature branch
git checkout -b feat/my-signal-module

# 2. Create venv and install deps
make venv install

# 3. Make your changes (src/, tests/, docs/)

# 4. Run tests and linting locally
make test
make lint
make fmt

# 5. Verify with lean quick checks
make quick-checks

# 6. Commit and push
git add -A
git commit -m "feat(modules): add new signal module"
git push origin feat/my-signal-module

# 7. Open PR (pre-commit hooks will run)
```

### 2. **Adding a New Signal Module**

**Steps:**
1. Create `modules/my_signal_module.py`
2. Inherit from `core.module_manager.Module`
3. Implement `process()` and `get_schema()`
4. Add to `modules/__init__.py` if needed
5. Register in `config.yaml` under `adaptive_weights.signal_layers`
6. Add tests in `tests/`
7. Run `make quick-checks`

**Template:**
```python
from core.module_manager import Module
from typing import Dict, Any

class MySignalModule(Module):
    VERSION = "1.0.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process price data and return signal."""
        # Implement your signal logic
        return {
            "signal": "BUY",  # BUY, SELL, HOLD
            "confidence": 0.85,
            "value": 42.0,
        }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {"price_data": "List[Dict]"},
            "output": {"signal": "str", "confidence": "float"},
        }
```

### 3. **Adding Tests**

```bash
# Create test file: tests/test_my_feature.py
pytest tests/test_my_feature.py -v

# Check coverage
pytest --cov=src tests/
```

### 4. **Configuration & Environment**

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env

# Load in your shell
set -a
source .env
set +a
```

### 5. **Docker Development**

```bash
# Build image
make docker-build

# Start API server
make up

# View logs
make logs

# Shell into container
make shell

# Stop
make down
```

### 6. **Code Quality**

```bash
# Lint
make lint          # ruff check

# Format
make fmt           # ruff format

# Check docs
make docs-lint     # markdown checks
make docs-fix      # normalize markdown

# Pre-commit install
make pre-commit-install
make pre-commit-run
```

---

## Common Development Tasks

### Task: Debug a Signal Module

```bash
# 1. Load module and test data
python -c "
from core.module_manager import ModuleManager
mm = ModuleManager()
mm.load_module('modules.rsi_module', {'period': 14})
result = mm.execute_module('RSIModule', {'price_data': [...]})
print(result)
"

# 2. Check logs
tail -f logs/benson.log

# 3. Run specific test
pytest tests/test_rsi_scenarios.py::test_rsi_overbought -v
```

### Task: Run Backtest

```bash
# Using regime-specific trainer
python regime_specific_trainer.py --symbol BTC/USD --regime bull

# Using backtester
python -c "
from src.backtesting import Backtester
bt = Backtester('config/config.yaml')
results = bt.run('2024-01-01', '2024-12-31')
print(results)
"
```

### Task: Profile Performance

```bash
# Check execution time
python -m cProfile -s cumtime benson_rsi_bot.py --once

# Check memory usage
python -m memory_profiler benson_rsi_bot.py --once
```

### Task: Monitor Live System

```bash
# View real-time metrics
streamlit run src/dashboard/live_dashboard.py

# Or use Dash
python run_enhanced_dashboard.py

# Check system health
curl http://localhost:8000/health
```

### Task: Export Metrics

```bash
# Get trading metrics
curl http://localhost:8000/metrics

# Export to CSV
python analyze_trading_performance.py

# View in dashboard
make run-live
```

---

## Security & Authentication

### ProofPacks API Signing

**Implementation:** `src/security/signing.py`

**Algorithm:** HMAC-SHA256

**Key Components:**
```python
# Secret from environment
SIGNING_SECRET = os.getenv("SIGNING_SECRET", "dev-secret").encode("utf-8")
ALLOWED_SKEW = datetime.timedelta(minutes=5)

# Signature computation
ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
body = canonical_json_bytes(response_obj)
signature = hmac.new(SIGNING_SECRET, ts.encode() + b"\n" + body, hashlib.sha256)
```

**Response Headers:**
- `X-Signature`: Base64-encoded HMAC-SHA256 digest
- `X-Signature-Alg`: "HMAC-SHA256"
- `X-Signature-KeyId`: Key identifier (default: "proofpacks-v1")
- `X-Signature-Timestamp`: ISO 8601 UTC timestamp

**Verification:**
```python
from src.security.signing import verify_headers, compute_sig

# In request handler
sig, ts = verify_headers(x_signature, x_signature_timestamp)
computed = compute_sig(ts, body_bytes)
assert sig == computed
```

### Secrets Management

**Storage:** `src/bot/core/secrets_manager.py`

**Best Practices:**
1. Never commit `.env` files or API keys
2. Use environment variables for all secrets
3. Rotate keys regularly in production
4. Use encrypted secret stores (Vault, AWS Secrets Manager, etc.)

**Loading Credentials:**
```python
from src.bot.core.secrets_manager import SecretsManager

sm = SecretsManager()
api_key = sm.get_secret("API_KEY")
api_secret = sm.get_secret("API_SECRET")
```

### Data Privacy (ProofPacks)

**Principles:**
- Data minimization: tokenize only required fields
- Selective hashing: sensitive fields hashed, not encrypted
- Tenant isolation: per-customer namespaces
- Redaction: configurable per pack template

**Configuration:**
```yaml
proofpack_template:
  redaction:
    - field: carrier_name
      action: mask          # mask, hash, or drop
    - field: pnl_amount
      action: hash
```

---

## Deployment

### Local Development

```bash
# 1. Setup
make venv install

# 2. Configure
cp .env.example .env
nano .env

# 3. Run API server
make api-server

# 4. In another terminal, run bot
PAPER=true python benson_rsi_bot.py
```

### Docker (Single Machine)

```bash
# Build and start
make docker-build
make up

# Logs
make logs

# Stop
make down
```

### Docker Compose Services

**Configuration:** `docker-compose.yml`

**Services:**
- `benson-api`: Main API server (port 8000)
- `benson-rsi`: RSI bot (profile: rsi-only)
- `benson-legacy`: Legacy bot (profile: legacy)

**Start Specific Service:**
```bash
docker compose up -d benson-api
docker compose --profile rsi-only up -d benson-rsi
```

### Kubernetes Deployment

**Charts:** `k8s/` directory (if present)

**Helm Values:**
```bash
helm install chainbridge ./k8s --values values.yaml
```

### Environment Considerations

**Development:**
```bash
APP_ENV=dev
LOGGING_LEVEL=DEBUG
PAPER=true
```

**Staging:**
```bash
APP_ENV=staging
LOGGING_LEVEL=INFO
PAPER=true
```

**Production:**
```bash
APP_ENV=prod
LOGGING_LEVEL=WARNING
PAPER=false
# Use vault for SIGNING_SECRET, API_KEY, API_SECRET
```

### Health Checks

**ProofPacks API:**
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status": "healthy", "version": "1.0.0"}
```

### Monitoring & Observability

**Metrics Endpoint:**
```bash
curl http://localhost:8000/metrics
```

**Logging:**
- Format: Structured JSON with correlation IDs
- Level: Configurable via `LOGGING_LEVEL` env
- File: `logs/benson.log`

**Dashboard:**
```bash
streamlit run src/dashboard/live_dashboard.py
```

---

## Troubleshooting

### Common Issues

**Issue: Module not found**
```
ImportError: No module named 'modules.rsi_module'
```
**Solution:**
1. Check module exists: `ls modules/rsi_module.py`
2. Verify in `PYTHONPATH`: `python -c "import sys; print(sys.path)"`
3. Check `modules/__init__.py` imports

**Issue: Config not loading**
```
FileNotFoundError: Config not found at config/config.yaml
```
**Solution:**
1. Check file exists: `ls config/config.yaml`
2. Check BENSON_CONFIG env: `echo $BENSON_CONFIG`
3. Use absolute path if relative fails

**Issue: Exchange connection fails**
```
ccxt.ExchangeError: Insufficient API key
```
**Solution:**
1. Verify API_KEY and API_SECRET in `.env`
2. Check API key permissions on exchange
3. Verify exchange is not in maintenance

**Issue: Tests fail with pandas import error**
```
ImportError: No module named 'pandas'
```
**Solution:**
```bash
# Use lean environment or install full deps
make install          # Full deps
make install-lean     # Minimal deps (includes fallback)
```

### Debug Mode

```bash
# Verbose logging
export LOGGING_LEVEL=DEBUG
python benson_rsi_bot.py --once

# Show config loading
python debug_config_loader.py

# Check module loading
python -m pytest tests/test_module_manager.py -v
```

---

## Quick Reference

### Make Targets

```bash
make help                      # Show all targets
make venv install run         # Development quick start
make test lint fmt            # Code quality
make docker-build up down     # Docker operations
make quick-checks             # Lean sanity checks
make run-once-paper           # Single paper trade
make run-live                 # Continuous live trades
make docs-lint docs-fix       # Markdown checks
```

### Common Commands

```bash
# Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Testing
pytest tests/ -v
pytest tests/test_rsi_scenarios.py::test_name -v

# Linting
ruff check .
ruff format .

# Git workflow
git checkout -b feat/feature-name
git add .
git commit -m "feat(module): description"
git push origin feat/feature-name
```

### Configuration Checklist

- [ ] Copy `.env.example` to `.env`
- [ ] Fill in `API_KEY` and `API_SECRET`
- [ ] Set `EXCHANGE` (kraken, binance, bybit)
- [ ] Update `SYMBOLS` list
- [ ] Set `PAPER=true` for testing
- [ ] Verify `config/config.yaml` exists
- [ ] Check `SIGNING_SECRET` for API (change from dev-secret)

---

## Additional Resources

**Documentation Files:**
- `README.md` - Project overview and quick start
- `ENTERPRISE_README.md` - Enterprise deployment guide
- `proofpacks/PROOFPACK_GOVERNANCE.md` - Proof pack compliance
- `REGIME_MODEL_GUIDE.md` - Market regime model details
- `MODULAR_ARCHITECTURE.md` - Module architecture deep dive
- `TRADING_SYSTEM_DOCUMENTATION.md` - Trading system details

**Code Examples:**
- `scripts/integrator_smoke_test.py` - Integration test template
- `examples/` - Example configurations and data

**Related Repositories:**
- ChainIQ Service: `chainiq-service/` (Risk scoring)
- ChainBoard Service: `chainboard-service/` (Monitoring)

---

**Document Version:** 1.0 | **Last Updated:** 2025-11-14 | **Python:** 3.11+ | **Status:** Maintained
