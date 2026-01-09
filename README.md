# ChainBridge – Enterprise Logistics & Settlement Platform

[![CI/CD](https://github.com/BIGmindz/ChainBridge/workflows/CI/CD/badge.svg)](https://github.com/BIGmindz/ChainBridge/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ChainBridge is an enterprise-grade logistics and settlement platform that combines freight management, tokenization, payment processing, and ML-driven risk scoring to optimize supply chain operations and financial settlements. Built with a microservices architecture, ChainBridge provides scalable, secure, and intelligent automation for logistics, payments, and compliance workflows.

## 🚀 Platform Overview

ChainBridge is built around four core microservices that work together to deliver end-to-end logistics automation:

### 🚛 ChainFreight – Shipment Lifecycle Management
- **Shipment tracking** from origin to destination
- **Freight tokenization** for fractional ownership and trading
- **Real-time status updates** and exception handling
- **Delivery confirmation** with proof of delivery
- Integration with ChainIQ for risk-based decision making

### 💰 ChainPay – Intelligent Payment Settlement
- **Risk-based conditional settlement** logic
- **Automated payment intents** tied to freight tokens
- **Multi-tier settlement delays**: LOW (immediate), MEDIUM (24h), HIGH (manual review)
- **Audit logging** of all settlement decisions
- Integration with freight risk scoring

### 👤 ChainBoard – Driver Identity & Onboarding
- **Driver registration** and compliance tracking
- **Profile management** with verification workflows
- **DOT and CDL validation**
- Future: Enterprise identity and organizational support

### 🧠 ChainIQ – ML-Powered Risk Scoring
- **Shipment risk assessment** (0.0-1.0 score)
- **Driver reliability analysis**
- **Route optimization** recommendations
- **Predictive analytics** for delivery reliability
- Adaptive ML models with multi-signal aggregation

## 🏗️ Architecture

ChainBridge follows a microservices architecture with the following design principles:

### Service Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                      ChainBridge Platform                    │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  ChainBoard  │ ChainFreight │   ChainPay   │    ChainIQ     │
│   :8000      │    :8002     │    :8003     │     :8001      │
├──────────────┼──────────────┼──────────────┼────────────────┤
│   Driver     │   Shipment   │   Payment    │  Risk Scoring  │
│   Identity   │   Tracking   │  Settlement  │   Analytics    │
│   Onboard    │   Tokens     │   Audit      │   Prediction   │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### Key Features

- ✅ **Microservices Architecture**: Independent, scalable services
- ✅ **RESTful APIs**: OpenAPI/Swagger documentation
- ✅ **Freight Tokenization**: Asset-backed tokens for trading and financing
- ✅ **Risk-Based Settlement**: Conditional payment logic with multi-tier delays
- ✅ **ML-Powered Scoring**: Adaptive risk assessment and optimization
- ✅ **Proof Pack Governance**: Customer-controlled evidence and compliance
- ✅ **Cloud-Native Design**: Containerized deployment with Docker
- ✅ **Database Flexibility**: SQLite (dev) / PostgreSQL (production)
- ✅ **Security First**: Environment-based secrets, TLS, tenant isolation

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip
- Docker (optional, for containerized deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/BIGmindz/ChainBridge.git
cd ChainBridge

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Services

#### Start All Services with Docker

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d
```

#### Start Individual Services

```bash
# ChainBoard (Driver Identity) - Port 8000
cd ChainBridge/chainboard-service && uvicorn app.main:app --reload --port 8000

# ChainIQ (Risk Scoring) - Port 8001
cd ChainBridge/chainiq-service && uvicorn app.main:app --reload --port 8001

# ChainFreight (Shipment Tracking) - Port 8002
cd ChainBridge/chainfreight-service && uvicorn app.main:app --reload --port 8002

# ChainPay (Payment Settlement) - Port 8003
cd ChainBridge/chainpay-service && uvicorn app.main:app --reload --port 8003
```

### API Documentation

Once services are running, access interactive API documentation:

- **ChainBoard**: http://localhost:8000/docs
- **ChainIQ**: http://localhost:8001/docs
- **ChainFreight**: http://localhost:8002/docs
- **ChainPay**: http://localhost:8003/docs

## 💼 Use Cases

### Freight Tokenization Workflow

```bash
# 1. Create a shipment in ChainFreight
curl -X POST http://localhost:8002/shipments \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name": "ACME Corp",
    "origin": "Los Angeles, CA",
    "destination": "Chicago, IL",
    "pickup_date": "2025-11-08T08:00:00",
    "planned_delivery_date": "2025-11-15T12:00:00",
    "cargo_value": 100000
  }'

# 2. Tokenize the shipment (includes ChainIQ risk scoring)
curl -X POST http://localhost:8002/shipments/1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "face_value": 100000.00,
    "currency": "USD"
  }'

# 3. Create payment intent (ChainPay)
curl -X POST http://localhost:8003/payment_intents \
  -H "Content-Type: application/json" \
  -d '{
    "freight_token_id": 1,
    "amount": 100000.00,
    "currency": "USD",
    "description": "Payment for shipment LA→CHI"
  }'

# 4. Settle payment (risk-based logic applies)
curl -X POST http://localhost:8003/payment_intents/1/settle \
  -H "Content-Type: application/json" \
  -d '{
    "settlement_notes": "Approved by finance team"
  }'
```

### Risk-Based Settlement Tiers

| Risk Level | Score Range | Settlement Action | Delay |
|-----------|-------------|-------------------|-------|
| **LOW** | 0.0 - 0.33 | Immediate approval | None |
| **MEDIUM** | 0.33 - 0.67 | Delayed approval | 24 hours |
| **HIGH** | 0.67 - 1.0 | Manual review required | Indefinite (requires override) |

## 🔐 Security & Governance

ChainBridge implements enterprise-grade security and governance controls:

### Security Features

- **Environment-Based Secrets**: All sensitive credentials stored in `.env` files (never committed)
- **TLS Encryption**: All service-to-service communication encrypted in transit
- **Tenant Isolation**: Multi-tenant architecture with strict data separation
- **Role-Based Access Control (RBAC)**: Fine-grained permissions per service
- **Customer KMS**: Option to use customer-managed encryption keys at rest
- **IP Allowlisting**: Restrict service access to authorized networks
- **SOC 2 Compliance Track**: Security audit trail and compliance reporting

### Proof Pack Governance

ChainBridge implements **customer-controlled, ChainBridge-executed** governance:

- **Data Controller (Customer)**: Defines proof pack templates, redaction rules, storage location, and retention policies
- **Processor (ChainBridge)**: Executes policies, assembles proof packs, routes payments, anchors hashes
- **Auditors/Insurers**: Read-only access to export bundles and audit trails

#### Key Governance Features

- **Template-Based Evidence**: Customer-defined templates for each lane, corridor, or risk tier
- **Redaction & Data Minimization**: Per-field control (`drop`, `mask`, or `hash`)
- **Customer-Owned Storage**: Primary storage in customer vaults (S3/Azure/GCS/on-prem)
- **Integrity Anchoring**: Manifest hashes anchored to public/neutral ledger (XRP Ledger)
- **Versioned Templates**: Change control with finance/compliance approval
- **Audit Logging**: Complete settlement decision log with timestamps and signatures

#### Runtime Modes

1. **Observe-only**: Generate proof packs without fund movement
2. **Simulated**: "Would-have-paid" testing runs
3. **Controlled live**: Single milestone (e.g., pickup 20%) with dual approval
4. **Full automation**: All milestones with exception alerts

See [Proof Pack Governance](./proofpacks/PROOFPACK_GOVERNANCE.md) for complete details.

### Environment Configuration

```bash
# Copy the environment template
cp .env.example .env

# Edit .env with your configuration
DATABASE_URL=postgresql://user:password@localhost/chainbridge
CHAINFREIGHT_URL=http://localhost:8002
CHAINIQ_URL=http://localhost:8001
CHAINBOARD_URL=http://localhost:8000
CHAINPAY_URL=http://localhost:8003

# Security settings
KMS_KEY_ID=your-kms-key-id
ENABLE_TLS=true
ALLOWED_IPS=10.0.0.0/8,172.16.0.0/12
```

**⚠️ Never commit `.env` files to version control**

## 📊 Service Documentation

### ChainBoard (Driver Identity & Onboarding)

**Port**: 8000 | **Path**: `ChainBridge/chainboard-service/`

- Driver registration with DOT/CDL validation
- Profile management and compliance tracking
- Soft-delete support for inactive drivers
- Search by email or DOT number

[ChainBoard README](./ChainBridge/chainboard-service/README.md)

### ChainIQ (ML Risk Scoring Engine)

**Port**: 8001 | **Path**: `ChainBridge/chainiq-service/`

- Shipment risk scoring (0.0-1.0)
- Driver reliability assessment
- Route optimization recommendations
- Adaptive ML models with multi-signal aggregation
- Integration with ChainFreight for automatic risk assessment

[ChainIQ README](./ChainBridge/chainiq-service/README.md)

### ChainFreight (Shipment Lifecycle & Tokenization)

**Port**: 8002 | **Path**: `ChainBridge/chainfreight-service/`

- Shipment tracking and status management
- Freight tokenization for fractional ownership
- Integration with ChainIQ for risk scoring
- Delivery confirmation and exception handling
- Shipment lifecycle: `pending → picked_up → in_transit → delivered`

[ChainFreight README](./ChainBridge/chainfreight-service/README.md)

### ChainPay (Intelligent Payment Settlement)

**Port**: 8003 | **Path**: `ChainBridge/chainpay-service/`

- Risk-based conditional settlement logic
- Multi-tier payment delays (LOW/MEDIUM/HIGH risk)
- Freight token consumption and settlement
- Complete audit logging of decisions
- Settlement history and compliance reporting

[ChainPay README](./ChainBridge/chainpay-service/README.md)

## 🧪 Testing

ChainBridge includes comprehensive testing for all services and components.

### Running Tests

```bash
# Run unit tests
python -m pytest tests/

# Run specific service tests
cd ChainBridge/chainfreight-service
pytest tests/

# Run integration tests (requires all services running)
python -m pytest tests/integration/

# Run with coverage
pytest --cov=ChainBridge --cov-report=html
```

### CI/CD Pipeline

ChainBridge uses GitHub Actions for continuous integration:

- **Build**: Python 3.11+ virtual environment setup
- **Test**: Automated unit test execution
- **Deploy**: Automated deployment on main branch

See [.github/workflows/ci.yml](./.github/workflows/ci.yml) for details.

### Manual Service Testing

```bash
# Test ChainFreight health
curl http://localhost:8002/health

# Test ChainIQ risk scoring
curl -X POST http://localhost:8001/score/shipment \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "SHIP-12345",
    "origin": "Los Angeles, CA",
    "destination": "Chicago, IL"
  }'

# Test ChainBoard driver creation
curl -X POST http://localhost:8000/drivers \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "555-1234"
  }'
```

## 🐳 Docker Deployment

ChainBridge supports containerized deployment with Docker and Docker Compose.

### Using Docker Compose

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and restart specific service
docker-compose up --build chainfreight-service
```

### Individual Container Builds

```bash
# Build ChainBoard
docker build -t chainboard:latest -f ChainBridge/chainboard-service/Dockerfile .

# Build ChainFreight
docker build -t chainfreight:latest -f ChainBridge/chainfreight-service/Dockerfile .

# Build ChainPay
docker build -t chainpay:latest -f ChainBridge/chainpay-service/Dockerfile .

# Build ChainIQ
docker build -t chainiq:latest -f ChainBridge/chainiq-service/Dockerfile .
```

### Kubernetes Deployment

ChainBridge includes Kubernetes manifests for production deployment:

```bash
# Apply Kubernetes configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/chainfreight-deployment
```

See [k8s/](./k8s/) directory for complete Kubernetes configurations.

## 🛠️ Development

### Project Structure

```plaintext
ChainBridge/
├── ChainBridge/                    # Main package directory
│   ├── chainboard-service/         # Driver identity service
│   ├── chainfreight-service/       # Shipment tracking service
│   ├── chainpay-service/           # Payment settlement service
│   ├── chainiq-service/            # ML risk scoring service
│   ├── core/                       # Core system components
│   ├── api/                        # REST API server
│   └── ml_models/                  # Machine learning models
├── modules/                        # Pluggable analysis modules
│   ├── adaptive_weight_module/     # Dynamic signal weighting
│   ├── market_regime_module/       # Regime detection
│   └── risk_management/            # Risk assessment
├── strategies/                     # Strategy configurations
│   ├── bull/                       # Bull market strategies
│   ├── bear/                       # Bear market strategies
│   └── sideways/                   # Sideways strategies
├── proofpacks/                     # Governance and compliance
├── tests/                          # Test suite
├── k8s/                           # Kubernetes manifests
├── docs/                          # Documentation
├── .github/workflows/             # CI/CD pipelines
├── docker-compose.yml             # Container orchestration
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project configuration
└── README.md                      # This file
```

### Adding New Features

1. **Create Feature Branch**: `git checkout -b feature/your-feature`
2. **Implement Changes**: Follow existing patterns in service directories
3. **Write Tests**: Add tests in `tests/` directory
4. **Update Documentation**: Update relevant README files
5. **Run Tests**: `pytest tests/`
6. **Submit PR**: Create pull request for review

### Code Quality Standards

```bash
# Format code with Black
black ChainBridge/ --line-length 140

# Sort imports with isort
isort ChainBridge/ --profile black

# Lint with Ruff
ruff check ChainBridge/

# Type checking with Pylance (VS Code)
# Configure in .vscode/settings.json
```

Configuration files:
- **Black/isort/Ruff**: `pyproject.toml`
- **Pre-commit hooks**: `.pre-commit-config.yaml`
- **Flake8**: `.flake8`
- **Pylint**: `.pylintrc`

## 🌟 Key Features

### Freight Management
- ✅ **End-to-End Shipment Tracking**: From origin to destination with real-time updates
- ✅ **Freight Tokenization**: Asset-backed tokens for fractional ownership and trading
- ✅ **Delivery Confirmation**: Proof of delivery with automated status updates
- ✅ **Exception Handling**: Automated incident detection and management

### Payment & Settlement
- ✅ **Risk-Based Settlement**: Multi-tier conditional payment logic
- ✅ **Automated Payment Intents**: Tied to freight tokens with risk assessment
- ✅ **Audit Logging**: Complete settlement decision history
- ✅ **Flexible Settlement Delays**: LOW (immediate), MEDIUM (24h), HIGH (manual)

### Risk & Intelligence
- ✅ **ML-Powered Risk Scoring**: 0.0-1.0 risk assessment for shipments
- ✅ **Driver Reliability Analysis**: Historical performance tracking
- ✅ **Route Optimization**: Predictive analytics for best routes
- ✅ **Adaptive Learning**: Multi-signal aggregation with dynamic weights

### Compliance & Governance
- ✅ **Proof Pack System**: Customer-controlled evidence and compliance
- ✅ **Template-Based Governance**: Versioned templates with approval workflows
- ✅ **Data Minimization**: Per-field redaction controls
- ✅ **Integrity Anchoring**: Cryptographic hashes on public ledgers

### Platform & Architecture
- ✅ **Microservices Design**: Independent, scalable services
- ✅ **RESTful APIs**: OpenAPI/Swagger documentation
- ✅ **Cloud-Native**: Containerized with Docker/Kubernetes support
- ✅ **Database Flexibility**: SQLite (dev) / PostgreSQL (production)
- ✅ **Security First**: TLS, RBAC, tenant isolation, KMS integration

## 🤝 Contributing

We welcome contributions to ChainBridge! Please follow these guidelines:

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**: `git clone https://github.com/YOUR_USERNAME/ChainBridge.git`
3. **Create a feature branch**: `git checkout -b feature/your-feature-name`
4. **Make your changes** following our code standards
5. **Write tests** for new functionality
6. **Run the test suite**: `pytest tests/`
7. **Commit your changes**: `git commit -m "Add feature: your feature description"`
8. **Push to your fork**: `git push origin feature/your-feature-name`
9. **Submit a pull request** to the main repository

### Code Standards

- **Type Hints**: Always use full type hints for function parameters and return values
- **Pydantic Schemas**: Use separate request/response models for API endpoints
- **Documentation**: Add docstrings to all classes and functions
- **Error Handling**: Return appropriate HTTP status codes with descriptive messages
- **Dependency Injection**: Use FastAPI's `Depends()` pattern for database sessions
- **Testing**: Maintain or improve code coverage with unit and integration tests

### Development Workflow

1. Install pre-commit hooks: `pre-commit install`
2. Format code before committing: `black ChainBridge/ && isort ChainBridge/`
3. Run linters: `ruff check ChainBridge/`
4. Run tests: `pytest tests/ --cov=ChainBridge`
5. Update documentation if adding new features

### Areas for Contribution

- 🆕 **New Features**: Additional microservices or integrations
- 🐛 **Bug Fixes**: Identify and fix issues
- 📚 **Documentation**: Improve guides, examples, and API docs
- 🧪 **Testing**: Expand test coverage
- ⚡ **Performance**: Optimization and scaling improvements
- 🔒 **Security**: Security enhancements and vulnerability fixes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Copyright © 2025 BIGmindz - ChainBridge Platform**

---

## 📞 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/BIGmindz/ChainBridge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/BIGmindz/ChainBridge/discussions)
- **Documentation**: [GitHub Wiki](https://github.com/BIGmindz/ChainBridge/wiki)

---

**Get started with ChainBridge today and transform your logistics operations with intelligent automation, risk-based settlement, and enterprise-grade governance.**
