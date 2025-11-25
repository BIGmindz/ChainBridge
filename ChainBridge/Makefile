PY=python
COMPOSE?=docker compose

.PHONY: help venv install run test lint fmt docker-build up down logs shell api-server rsi-compat system-test

help:
	@echo "ChainBridge - Freight + Payments Intelligence Platform"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  api-tests              - Run API health & echo tests"
	@echo "  api-tests-coverage     - API tests with coverage report"
	@echo "  iq-tests               - Run ChainIQ risk scoring + persistence tests"
	@echo "  iq-demo-seed           - Seed database with demo ChainIQ data"
	@echo "  pytest-all             - Run all tests"
	@echo "  coverage               - Full coverage report (fail if <70%)"
	@echo "  coverage-html          - Generate HTML coverage report"
	@echo "  quick-checks           - Fast sanity checks (RSI + integrator)"
	@echo ""
	@echo "Development:"
	@echo "  venv                   - Create Python virtual environment"
	@echo "  install                - Install dependencies"
	@echo "  api-server             - Start FastAPI server"
	@echo "  lint                   - Run code linting"
	@echo "  fmt                    - Format code"
	@echo "  pre-commit-install     - Install pre-commit hooks"
	@echo "  pre-commit-run         - Run pre-commit on all files"
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
.PHONY: venv-lean install-lean run-lean run-integrator-lean quick-checks pre-commit-install pre-commit-run

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
	  python scripts/integrator_smoke_test.py

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
