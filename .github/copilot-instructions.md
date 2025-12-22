# ChainBridge Platform

ChainBridge is a multi-service supply chain management and payment orchestration platform. It includes backend APIs, ML-powered risk scoring (ChainIQ), payment processing (ChainPay), and an operator control dashboard (ChainBoard).

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information.

## Current System Architecture

### Entry Points:
- **api/server.py** - Main FastAPI gateway (API Gateway)
- **ChainBridge/chainiq-service/** - ML risk scoring service
- **ChainBridge/chainpay-service/** - Payment orchestration service
- **ChainBridge/chainboard-ui/** - React operator dashboard

### Key Features:
- Multi-service microservices architecture
- ML-powered trust and risk scoring (ChainIQ)
- Payment orchestration and settlement (ChainPay)
- Real-time operator control center (ChainBoard OCC)
- Proofpack generation and audit trails
- Agent governance framework (ALEX rules)

## Repository Structure

\`\`\`text
/
├── api/                       # API Gateway
│   ├── server.py              # FastAPI main application
│   └── chainboard_stub.py     # ChainBoard API stub
├── core/                      # Core business logic
│   ├── oc/                    # Operator Control modules
│   └── occ/                   # Operator Control Center
├── tests/                     # Test suite (pytest)
│   ├── agents/                # Agent governance tests
│   ├── chainboard/            # ChainBoard tests
│   ├── oc/                    # OC tests
│   ├── occ/                   # OCC tests
│   └── security/              # Security tests
├── ChainBridge/               # Nested services (separate import paths)
│   ├── chainiq-service/       # ML risk scoring
│   ├── chainpay-service/      # Payment processing
│   └── chainboard-ui/         # React dashboard
├── docs/                      # Documentation
├── .github/                   # CI workflows & governance
│   ├── workflows/             # GitHub Actions
│   └── ALEX_RULES.json        # Agent governance rules
├── pytest.ini                 # Pytest configuration
├── requirements.txt           # Python dependencies
├── Makefile                   # Build automation
└── docker-compose.yml         # Container orchestration
\`\`\`

## Working Effectively

### Bootstrap, Build, and Test the Repository:

\`\`\`bash
# Setup Python virtual environment
make venv

# Install dependencies
make install

# Run pytest tests
make test  # OR: pytest -q

# Lint code
make lint

# Format code
make fmt
\`\`\`

### Run the Development Stack:

\`\`\`bash
# One-command setup (fresh clone)
make setup

# Start local dev stack (API + UI)
make dev

# Start Docker dev stack
make dev-docker

# Start API server only
make api-server
\`\`\`

### Docker:

\`\`\`bash
make docker-build  # Build Docker images
make up            # Start containers
make down          # Stop containers
make logs          # View logs
make shell         # Access container shell
\`\`\`

## Validation

### Required Validation Steps:

- **ALWAYS run pytest** after making changes: \`pytest -q\`
- **ALWAYS run linting** before committing: \`make lint\`
- **Verify API health**: \`curl http://localhost:8000/health\`
- **Run specific test modules**: \`pytest tests/chainboard/ -v\`

### Test Organization:

| Directory | Purpose |
|-----------|---------|
| \`tests/agents/\` | ALEX governance rule tests |
| \`tests/chainboard/\` | ChainBoard API tests |
| \`tests/oc/\` | Operator Control tests |
| \`tests/occ/\` | OCC decision/artifact tests |
| \`tests/security/\` | Security and auth tests |

## Configuration

### Required Files:

- \`.env\` - Environment variables (copy from .env.example)
- \`.env.dev\` - Development environment (copy from .env.dev.example)
- \`.venv/\` - Python virtual environment (created by \`make venv\`)

### Key Configuration:

- API Gateway runs on port 8000
- ChainBoard UI runs on port 3000 (when started)
- ChainIQ service handles ML scoring
- ChainPay service handles payment orchestration

## Common Tasks

### Development Workflow:

\`\`\`bash
# 1. Setup (once)
make setup

# 2. Make changes to code

# 3. Validate changes
pytest -q            # All tests must pass
make lint            # Code must be clean

# 4. Ready to commit
\`\`\`

### Troubleshooting:

- **"ModuleNotFoundError"**: Run \`make install\` to install dependencies
- **Import errors in tests**: Ensure \`pytest.ini\` has \`pythonpath = .\`
- **Test collection issues**: Check \`pytest.ini\` has \`testpaths = tests\`
- **Nested ChainBridge imports**: The \`ChainBridge/\` folder has separate import paths; don't mix with root \`api/\`

## Agent Governance

ChainBridge uses an agent governance framework with ALEX rules defined in \`.github/ALEX_RULES.json\`. Key agents:

| Agent | GID | Role |
|-------|-----|------|
| BENSON | GID-00 | Orchestrator |
| DAN | GID-07 | DevOps/CI Lead |
| ATLAS | GID-11 | Repo Integrity Engineer |
| ALEX | - | Governance Enforcer |

## Time Expectations

- **Virtual environment setup**: ~10 seconds
- **Dependency installation**: ~60-90 seconds
- **Pytest suite**: ~30-60 seconds (478+ tests)
- **Linting**: ~2-5 seconds
- **Docker build**: ~2-3 minutes

**NEVER CANCEL** long-running installation commands.
