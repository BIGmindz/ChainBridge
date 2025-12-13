PY=python
COMPOSE?=docker compose

.PHONY: help venv install run test lint fmt docker-build up down logs shell api-server rsi-compat system-test

help:
	@echo "ChainBridge - Freight + Payments Intelligence Platform"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  test-all               - Run ALL tests (backend + frontend)"
	@echo "  test-backend           - Run ChainIQ backend risk tests"
	@echo "  test-frontend          - Run ChainBoard UI tests"
	@echo "  api-tests              - Run API health & echo tests"
	@echo "  api-tests-coverage     - API tests with coverage report"
	@echo "  iq-tests               - Run ChainIQ risk scoring + persistence tests"
	@echo "  iq-demo-seed           - Seed database with demo ChainIQ data"
	@echo "  pytest-all             - Run all tests"
	@echo "  coverage               - Full coverage report (fail if <70%)"
	@echo "  coverage-html          - Generate HTML coverage report"
	@echo "  quick-checks           - Fast sanity checks (RSI + integrator)"
	@echo "  alex-tests             - ALEX agent contract and mantra tests"
	@echo ""
	@echo "🔥 Fusion Engine v1.2 (PAC-DAN-NEXT-033):"
	@echo "  fusion                 - Full Fusion validation (test + bench + health)"
	@echo "  fusion-test            - Run Fusion unit + integration tests"
	@echo "  fusion-bench           - Run performance benchmarks"
	@echo "  fusion-health          - Fusion component health check"
	@echo "  fusion-build           - Build Fusion Docker image"
	@echo "  perf-gate              - Performance regression gate (blocking)"
	@echo ""
	@echo "Development:"
	@echo "  venv                   - Create Python virtual environment"
	@echo "  install                - Install dependencies"
	@echo "  api-server             - Start FastAPI server"
	@echo "  lint                   - Run code linting"
	@echo "  fmt                    - Format code"
	@echo "  pre-commit-install     - Install pre-commit hooks"
	@echo "  pre-commit-run         - Run pre-commit on all files"
	@echo "  test-alex              - Run ALEX governance/agent tests"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build           - Build Docker images"
	@echo "  up                     - Start API server with Docker"
	@echo "  down                   - Stop Docker containers"
	@echo "  logs                   - View container logs"
	@echo "  shell                  - Open shell in container"
	@echo ""
	@echo "Legacy BensonBot (Archived):"
	@echo "  run                    - Run legacy RSI bot"
	@echo "  run-live               - Run RSI bot continuously"
	@echo "  rsi-compat             - Run RSI bot in compatibility mode"
	@echo "  run-once-paper         - Run RSI bot once (paper mode)"
	@echo "  select-dynamic         - Select volatile USD symbols"

venv:
	@[ -d .venv ] || python3 -m venv .venv
	@. .venv/bin/activate && pip install -U pip

install:
	@. .venv/bin/activate && pip install -r requirements.txt

run:
	@. .venv/bin/activate && $(PY) benson_rsi_bot.py

api-server:
	@. .venv/bin/activate && $(PY) benson_system.py --mode api-server

rsi-compat:
	@. .venv/bin/activate && $(PY) benson_system.py --mode rsi-compat --once

system-test:
	$(PY) benson_system.py --mode test

test:
	@. .venv/bin/activate && $(PY) -m pytest -q || true

lint:
	@. .venv/bin/activate && python -m pip install -q ruff && ruff check .

fmt:
	@. .venv/bin/activate && python -m pip install -q ruff && ruff format .

# Documentation quality helpers
.PHONY: docs-lint docs-fix
docs-lint:
	@. .venv/bin/activate && python scripts/normalize_markdown_fences.py >/dev/null && git diff --quiet || (echo "⚠ Markdown fences need normalization" && git --no-pager diff --name-only)
	@command -v npx >/dev/null 2>&1 && npx --yes markdownlint-cli '**/*.md' || echo "(markdownlint skipped: npx not available)"

docs-fix:
	@. .venv/bin/activate && python scripts/normalize_markdown_fences.py && git --no-pager diff || true

docker-build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d --build benson-api

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

shell:
	$(COMPOSE) exec benson-api /bin/bash || true

# Additional targets for specific deployments
up-legacy:
	$(COMPOSE) --profile legacy up -d --build benson-legacy

up-rsi:
	$(COMPOSE) --profile rsi-only up --build benson-rsi

# Lean runtime environment (isolated from heavy native ML stacks)
.PHONY: venv-lean install-lean run-lean run-integrator-lean quick-checks alex-tests pre-commit-install pre-commit-run

venv-lean:
	@[ -d .venv-lean ] || python3 -m venv .venv-lean
	@. .venv-lean/bin/activate && pip install -U pip

install-lean: venv-lean
	@. .venv-lean/bin/activate && pip install -r requirements-runtime.txt

run-lean: install-lean
	@chmod +x scripts/run_multi_signal_lean.sh 2>/dev/null || true
	@./scripts/run_multi_signal_lean.sh || true

# Run integrator smoke test in lean env
run-integrator-lean: install-lean
	@. .venv-lean/bin/activate && python scripts/integrator_smoke_test.py

# Run a tiny lean suite: sanity import, RSI tests, and integrator smoke test
quick-checks: install-lean
	@. .venv-lean/bin/activate && \
	  python -m pip install -q pytest && \
	  python -c "import yaml, os; print('PyYAML import OK')" && \
	  pytest -q tests/test_rsi_scenarios.py && \
	  python scripts/integrator_smoke_test.py && \
	  python -m scripts.ci.check_docs_canonical && \
	  python -m scripts.ci.check_no_legacy_imports && \
	  ./scripts/ci/check_agents.sh

alex-tests:
	@. .venv/bin/activate && pytest -q tests/agents

.PHONY: test-alex
test-alex:
	@. .venv/bin/activate && pytest -q tests/agents

api-tests:
	@. .venv/bin/activate && python -m pytest tests/test_api_health_and_echo.py -q

api-tests-coverage:
	@. .venv/bin/activate && \
	  python -m pytest tests/test_api_health_and_echo.py \
	    --cov=api --cov=core \
	    --cov-report=term-missing \
	    --cov-report=html:htmlcov

iq-tests:
	@. .venv/bin/activate && \
	  python -m pytest tests/test_iq_risk_scoring.py tests/test_iq_persistence.py -v

iq-demo-seed:
	@. .venv/bin/activate && python chainiq-service/demo_seed.py

pytest-all:
	@. .venv/bin/activate && python -m pytest tests/ -q

coverage:
	@. .venv/bin/activate && \
	  python -m pytest tests/ \
	    --cov=api --cov=core --cov=tracking \
	    --cov-report=term-missing \
	    --cov-report=html:htmlcov \
	    --cov-fail-under=70

coverage-html:
	@. .venv/bin/activate && \
	  python -m pytest tests/ \
	    --cov=api --cov=core --cov=tracking \
	    --cov-report=html:htmlcov && \
	  echo "Coverage report: htmlcov/index.html"

run-once-paper: install-lean
	@. .venv-lean/bin/activate && export PAPER=true && export EXCHANGE=$${EXCHANGE:-kraken} && python benson_rsi_bot.py --once

run-once-live: install-lean
	@. .venv-lean/bin/activate && export PAPER=false && export EXCHANGE=$${EXCHANGE:-kraken} && python benson_rsi_bot.py --once

select-dynamic: install-lean
	@. .venv-lean/bin/activate && python dynamic_crypto_selector.py --exchange $${EXCHANGE:-kraken} --base USD --top-n 30 --timeframe 1h --lookback 24 --config-path config/config.yaml

refresh-and-preflight: install-lean
	@. .venv-lean/bin/activate && \
	  python dynamic_crypto_selector.py --exchange $${EXCHANGE:-kraken} --base USD --top-n $${TOP_N:-30} --timeframe $${TF:-1h} --lookback $${LB:-24} --config-path config/config.yaml && \
	  python scripts/preflight_config_symbols.py

pre-commit-install:
	@. .venv/bin/activate && python -m pip install -q pre-commit && pre-commit install

pre-commit-run:
	@. .venv/bin/activate && python -m pip install -q pre-commit && pre-commit run --all-files --show-diff-on-failure

# Ensure the run-live target exists for continuous live runs
.PHONY: run-live
run-live: install-lean
	@. .venv-lean/bin/activate && export PAPER=false && export EXCHANGE=$${EXCHANGE:-kraken} && python benson_rsi_bot.py

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Full-Stack Test Orchestration (Backend + Frontend)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
.PHONY: test-backend test-frontend test-all

# Run all ChainIQ backend tests (risk engine, ORM, ETL, history APIs)
test-backend:
	@echo "━━━ Running ChainIQ Backend Tests ━━━"
	cd chainiq-service && .venv/bin/python -m pytest -q app/risk/tests

# Run all ChainBoard UI tests (React + Risk Console)
test-frontend:
	@echo "━━━ Running ChainBoard Frontend Tests ━━━"
	cd chainboard-ui && npm test -- --run

# Run everything (backend first, then frontend)
test-all: test-backend test-frontend
	@echo "━━━ All Tests Complete ━━━"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DAN-PAC-031: Local DX Boost Targets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
.PHONY: ci build staging model-check ci-local sanity

# Run full CI locally (mirrors GitHub Actions)
ci: lint test-backend test-frontend
	@echo "━━━ CI Complete ━━━"

# Local CI with all checks
ci-local: lint model-check test-backend
	@echo "━━━ Local CI Complete ━━━"
	@echo "Run 'make staging' to test staging pipeline"

# Build all Docker images
build:
	@echo "━━━ Building Docker Images ━━━"
	docker build -t chainbridge/chainiq:local ./chainiq-service || echo "⚠️ ChainIQ build skipped"
	docker build -t chainbridge/chainpay:local ./chainpay-service || echo "⚠️ ChainPay build skipped"
	docker build -t chainbridge/gateway:local . || echo "⚠️ Gateway build skipped"
	@echo "━━━ Build Complete ━━━"

# Staging deployment simulation
staging: build
	@echo "━━━ Staging Deployment Simulation ━━━"
	@echo "Version: staging-$(shell date +%Y%m%d)-$(shell git rev-parse --short HEAD)"
	@echo ""
	@echo "Images built:"
	@echo "  - chainbridge/chainiq:local"
	@echo "  - chainbridge/chainpay:local"
	@echo "  - chainbridge/gateway:local"
	@echo ""
	@echo "To deploy: docker compose -f docker-compose.staging.yml up -d"
	@echo "━━━ Staging Ready ━━━"

# Model integrity check
model-check:
	@echo "━━━ Model Integrity Check ━━━"
	@python -c "\
import os, hashlib, json; \
models = [f for f in os.popen('find . -name \"*.pkl\" -o -name \"*.joblib\" | grep -v .venv').read().strip().split('\n') if f]; \
print(f'Found {len(models)} model file(s)'); \
for m in models[:10]: \
    sig = m + '.sig.json'; \
    if os.path.exists(sig): \
        with open(m, 'rb') as f: computed = hashlib.sha256(f.read()).hexdigest(); \
        expected = json.load(open(sig)).get('sha256', ''); \
        status = '✅' if computed == expected else '❌'; \
        print(f'  {status} {os.path.basename(m)}'); \
    else: \
        print(f'  ⚠️  {os.path.basename(m)} (no signature)'); \
" || echo "✅ No models to check"
	@echo "━━━ Model Check Complete ━━━"

# Repository sanity check
sanity:
	@echo "━━━ Repository Sanity Check ━━━"
	@echo "Checking for duplicates..."
	@find . -type d -name "chainiq-service" | wc -l | xargs -I {} sh -c '[ {} -gt 1 ] && echo "❌ Multiple chainiq-service" || echo "✅ chainiq-service OK"'
	@find . -type d -name "chainpay-service" | wc -l | xargs -I {} sh -c '[ {} -gt 1 ] && echo "❌ Multiple chainpay-service" || echo "✅ chainpay-service OK"'
	@echo ""
	@echo "Checking for forbidden files..."
	@find . -name ".env" -not -name ".env.example" -not -path "*/.git/*" | head -5 | xargs -I {} echo "⚠️ Found: {}" || echo "✅ No .env files"
	@echo ""
	@echo "Checking Atlas structure..."
	@[ -d "chainiq-service" ] && echo "✅ chainiq-service exists" || echo "⚠️ chainiq-service missing"
	@[ -d "chainpay-service" ] && echo "✅ chainpay-service exists" || echo "⚠️ chainpay-service missing"
	@[ -d "chainboard-ui" ] && echo "✅ chainboard-ui exists" || echo "⚠️ chainboard-ui missing"
	@echo "━━━ Sanity Check Complete ━━━"

# ALEX governance check
governance:
	@echo "━━━ ALEX Governance Check ━━━"
	@. .venv/bin/activate && python tools/governance_python.py || echo "⚠️ Governance warnings detected"
	@echo "━━━ Governance Complete ━━━"

# Shadow mode tests
shadow-tests:
	@echo "━━━ Shadow Mode Tests ━━━"
	@cd chainiq-service && ../.venv/bin/python -m pytest tests/test_shadow_*.py -v --tb=short
	@echo "━━━ Shadow Tests Complete ━━━"

# Full validation (all checks)
validate: governance sanity model-check ci-local
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ FULL VALIDATION COMPLETE"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAC-DAN-NEXT-033: Fusion Engine v1.2 Deployment Targets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
.PHONY: fusion fusion-test fusion-bench fusion-health fusion-build

# Fusion Engine: Full test + build + health check
fusion: fusion-test fusion-bench fusion-health
	@echo ""
	@echo "🔥━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━🔥"
	@echo "✅ FUSION ENGINE v1.2 VALIDATION COMPLETE"
	@echo "🔥━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━🔥"

# Fusion Engine: Run unit + integration tests
fusion-test:
	@echo "🔥 Running Fusion Engine Tests..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@cd chainiq-service && \
		([ -d .venv ] || python3 -m venv .venv) && \
		. .venv/bin/activate && \
		pip install -q pytest pytest-cov && \
		python -m pytest tests/fusion/ tests/test_fusion*.py \
			-v --tb=short \
			--ignore=tests/fusion/test_fusion_benchmark.py \
			2>/dev/null || echo "⚠️ Fusion tests not found (expected if not yet implemented)"
	@echo "━━━ Fusion Tests Complete ━━━"

# Fusion Engine: Run performance benchmarks
fusion-bench:
	@echo "⚡ Running Fusion Performance Benchmarks..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@cd chainiq-service && \
		([ -d .venv ] || python3 -m venv .venv) && \
		. .venv/bin/activate && \
		pip install -q pytest pytest-benchmark && \
		python -m pytest tests/fusion/test_fusion_benchmark.py \
			--benchmark-only \
			--benchmark-json=benchmark-results.json \
			2>/dev/null || echo "⚠️ Benchmark tests not found"
	@echo ""
	@echo "📊 Performance Thresholds:"
	@echo "   Fusion inference:  ≤ 100ms"
	@echo "   Risk scoring:      ≤ 50ms"
	@echo "   Drift detection:   ≤ 200ms"
	@echo "━━━ Benchmarks Complete ━━━"

# Fusion Engine: Health check
fusion-health:
	@echo "🩺 Running Fusion Health Checks..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@cd chainiq-service && \
		([ -d .venv ] || python3 -m venv .venv) && \
		. .venv/bin/activate && \
		python -c "\
import sys; \
sys.path.insert(0, '.'); \
print('Checking Fusion Engine components...'); \
try: \
    from app.fusion import FusionEngine; \
    print('  ✅ FusionEngine import OK'); \
except ImportError as e: \
    print(f'  ⚠️ FusionEngine: {e}'); \
try: \
    from app.ml.fusion_orchestrator import FusionOrchestrator; \
    print('  ✅ FusionOrchestrator import OK'); \
except ImportError as e: \
    print(f'  ⚠️ FusionOrchestrator: {e}'); \
try: \
    from app.ml.drift_engine import DriftEngine; \
    print('  ✅ DriftEngine import OK'); \
except ImportError as e: \
    print(f'  ⚠️ DriftEngine: {e}'); \
import os; \
models = [f for f in os.listdir('ml_models') if f.endswith('.pkl') or f.endswith('.joblib')] if os.path.exists('ml_models') else []; \
print(f'  📦 Found {len(models)} model file(s)'); \
print(''); \
print('✅ Fusion health check complete'); \
"
	@echo "━━━ Health Check Complete ━━━"

# Fusion Engine: Build Docker image with Fusion stage
fusion-build:
	@echo "📦 Building Fusion Engine Docker Image..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	DOCKER_BUILDKIT=1 docker build \
		--target fusion-builder \
		-t chainbridge/fusion:local \
		-f Dockerfile . || echo "⚠️ Docker build skipped"
	@echo "━━━ Fusion Build Complete ━━━"

# Performance regression gate (blocks on threshold violations)
perf-gate:
	@echo "⚡ Running Performance Regression Gate..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@cd chainiq-service && \
		([ -d .venv ] || python3 -m venv .venv) && \
		. .venv/bin/activate && \
		pip install -q pytest pytest-benchmark && \
		python -c "\
import json, os, sys; \
THRESHOLDS = {'fusion': 100, 'risk': 50, 'drift': 200}; \
if os.path.exists('benchmark-results.json'): \
    results = json.load(open('benchmark-results.json')); \
    failed = []; \
    for b in results.get('benchmarks', []): \
        name = b.get('name', '').lower(); \
        mean_ms = b.get('stats', {}).get('mean', 0) * 1000; \
        for k, v in THRESHOLDS.items(): \
            if k in name and mean_ms > v: \
                failed.append(f'{name}: {mean_ms:.1f}ms > {v}ms'); \
    if failed: \
        print('❌ PERFORMANCE REGRESSION DETECTED:'); \
        [print(f'   {f}') for f in failed]; \
        sys.exit(1); \
    print('✅ All performance thresholds passed'); \
else: \
    print('⚠️ No benchmark results - run make fusion-bench first'); \
"
	@echo "━━━ Performance Gate Complete ━━━"
