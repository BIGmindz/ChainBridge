# ChainBridge - Freight & Logistics Microservices Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ChainBridge is an enterprise-grade freight and logistics management platform built with a microservices architecture. The platform provides comprehensive solutions for supply chain management, payment processing, freight tracking, and business intelligence.

## 🏗️ What is ChainBridge?

ChainBridge is a modular freight management ecosystem consisting of the following microservices:

### Core Services

#### 🧠 ChainIQ Service
**Intelligence & Analytics Engine**
- Real-time analytics and reporting
- Supply chain optimization
- Predictive insights and forecasting
- Data aggregation and processing

**Port**: 8001  
**Directory**: `chainiq-service/`

#### 💰 ChainPay Service
**Payment Processing & Financial Management**
- Secure payment transactions
- Invoice management
- Multi-currency support
- Financial reporting and reconciliation
- Integration with payment gateways

**Port**: 8002  
**Directory**: `chainpay-service/`

#### 🚛 ChainFreight Service
**Freight Management & Tracking**
- Shipment tracking and monitoring
- Route optimization
- Carrier management
- Load planning and optimization
- Real-time status updates

**Port**: 8003  
**Directory**: `chainfreight-service/`

#### 📊 ChainBoard Service
**Backend API & Orchestration**
- Central API gateway
- Service coordination
- Data aggregation
- Business logic orchestration

**Port**: 8000  
**Directory**: `chainboard-service/`

#### 🎨 ChainBoard UI
**Frontend Dashboard**
- User-friendly web interface
- Real-time dashboards
- Interactive reports
- Mobile-responsive design

**Port**: 3000  
**Directory**: `chainboard-ui/`

### 🛡️ Gatekeeper CLI
**Validation & Governance Tool**

Command-line tool for:
- Configuration validation
- Governance compliance checks (ALEX framework)
- Pre-deployment verification
- Security audits

## 🏛️ Architecture

ChainBridge follows a microservices architecture with the following design principles:

- **Service Independence**: Each service is independently deployable
- **API-First Design**: RESTful APIs for all inter-service communication
- **Event-Driven**: Asynchronous messaging where appropriate
- **Containerized**: Docker support for all services
- **Scalable**: Horizontal scaling capabilities
- **Secure**: Authentication, authorization, and encryption

### Service Communication

```
┌─────────────────┐
│  ChainBoard UI  │ (Port 3000)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ChainBoard API  │ (Port 8000) ← API Gateway
└────────┬────────┘
         │
    ┌────┼────┬────────┐
    ▼    ▼    ▼        ▼
┌───────┐ ┌────────┐ ┌──────────┐
│ChainIQ│ │ChainPay│ │ChainFreight│
│ 8001  │ │ 8002   │ │   8003     │
└───────┘ └────────┘ └──────────┘
```

## 🚀 Local Development

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Docker & Docker Compose (optional, for containerized deployment)
- Git

### Setup Instructions

1. **Clone and Navigate**
   ```bash
   cd ChainBridge
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

4. **Configuration**
   - Copy environment template: `cp .env.example .env`
   - Update `.env` with your configuration
   - Review `config/` directory for service-specific settings

5. **Database Setup** (if applicable)
   ```bash
   # Initialize databases for services
   # Add specific commands as services develop
   ```

### Running Services

#### Individual Services

```bash
# ChainIQ Service
cd chainiq-service
python -m app.main

# ChainPay Service
cd chainpay-service
python -m app.main

# ChainFreight Service
cd chainfreight-service
python -m app.main

# ChainBoard Service
cd chainboard-service
python -m app.main

# ChainBoard UI
cd chainboard-ui
npm install  # First time only
npm start
```

#### Docker Compose (All Services)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## 🧪 Testing

### Run All Tests

```bash
# From ChainBridge directory
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Gatekeeper Validation

The Gatekeeper CLI ensures governance compliance and configuration validity:

```bash
# Run Gatekeeper validation tests
python -m pytest tests/test_gatekeeper.py -v

# Validate specific service configuration
python tools/gatekeeper.py --validate chainpay-service

# Full governance compliance check
python tools/gatekeeper.py --compliance-check
```

### Service-Specific Tests

```bash
# ChainIQ Tests
pytest chainiq-service/tests/ -v

# ChainPay Tests
pytest chainpay-service/tests/ -v

# ChainFreight Tests
pytest chainfreight-service/tests/ -v

# ChainBoard Tests
pytest chainboard-service/tests/ -v
```

### Integration Tests

```bash
# Run integration tests across services
pytest tests/integration/ -v

# Test service communication
pytest tests/integration/test_service_communication.py -v
```

## 📊 Governance & Compliance

ChainBridge follows the **ALEX governance framework** for enterprise compliance:

- **A**ccess Control - Role-based access management
- **L**ogging & Audit - Comprehensive audit trails
- **E**ncryption - Data encryption at rest and in transit
- **X**-Factor Validation - Multi-layer validation and verification

### Governance Documentation

Located in `docs/governance/`:
- Compliance policies
- Security guidelines
- Audit procedures
- Change management protocols

**Key Documents:**
- `docs/governance/ALEX_FRAMEWORK.md` - Core governance principles
- `docs/governance/SECURITY_POLICY.md` - Security requirements
- `docs/governance/AUDIT_PROCEDURES.md` - Audit guidelines

## 🏗️ Project Structure

```
ChainBridge/
├── chainiq-service/          # Intelligence service
│   ├── app/                  # Service code
│   ├── tests/                # Unit tests
│   ├── README.md             # Service docs
│   └── requirements.txt      # Dependencies
│
├── chainpay-service/         # Payment service
│   ├── app/                  # Service code
│   ├── tests/                # Unit tests
│   ├── README.md             # Service docs
│   └── requirements.txt      # Dependencies
│
├── chainfreight-service/     # Freight service
│   ├── app/                  # Service code
│   ├── tests/                # Unit tests
│   ├── README.md             # Service docs
│   └── requirements.txt      # Dependencies
│
├── chainboard-service/       # Backend API
│   ├── app/                  # Service code
│   ├── tests/                # Unit tests
│   └── README.md             # Service docs
│
├── chainboard-ui/            # Frontend UI
│   ├── src/                  # React/UI code
│   ├── public/               # Static assets
│   └── README.md             # UI docs
│
├── tests/                    # Integration tests
│   ├── integration/          # Cross-service tests
│   └── test_gatekeeper.py    # Governance tests
│
├── docs/
│   └── governance/           # ALEX compliance docs
│
├── tools/
│   └── gatekeeper.py         # Governance CLI
│
├── config/                   # Configuration files
├── scripts/                  # Utility scripts
├── docker-compose.yml        # Container orchestration
└── README.md                 # This file
```

## 🔧 Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feat/chainbridge-<description>
   ```

2. **Make Changes**
   - Follow service-specific patterns
   - Add tests for new functionality
   - Update documentation

3. **Test Locally**
   ```bash
   pytest tests/ -v
   python tools/gatekeeper.py --validate
   ```

4. **Commit & Push**
   ```bash
   git add .
   git commit -m "feat(chainpay): add invoice validation"
   git push origin feat/chainbridge-<description>
   ```

5. **Create Pull Request**
   - Use PR template
   - Link related issues
   - Request review

## 📚 Additional Documentation

- [ChainIQ Service README](chainiq-service/README.md)
- [ChainPay Service README](chainpay-service/README.md)
- [ChainFreight Service README](chainfreight-service/README.md)
- [ChainBoard Service README](chainboard-service/README.md)
- [ChainBoard UI README](chainboard-ui/README.md)
- [Governance Documentation](docs/governance/)

## 🤝 Contributing

See the root [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Coding standards
- PR requirements
- Testing guidelines
- Review process

**ChainBridge-specific guidelines:**
- Use `feat/chainbridge-*` branch naming
- All services must have tests
- Gatekeeper validation must pass
- ALEX compliance required

## 🔒 Security

- Report vulnerabilities via [GitHub Security Advisories](https://github.com/BIGmindz/ChainBridge/security/advisories)
- See [SECURITY.md](../.github/SECURITY.md) for full policy
- CodeQL scanning enabled
- Regular dependency audits

## 📜 License

MIT License - Part of the BIGmindz ChainBridge project.

---

**Questions?** Check the [Repository Map](../docs/REPO_MAP.md) or open an issue.

**Parent Repo:** [BIGmindz/ChainBridge](https://github.com/BIGmindz/ChainBridge)
