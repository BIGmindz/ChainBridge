PY=python
COMPOSE?=docker compose

.PHONY: help venv install run test lint fmt docker-build up down logs shell api-server rsi-compat system-test

help:
	@echo "Benson Multi-Signal Decision Bot - Modular Architecture"
	@echo ""
	@echo "Available targets:"
	@echo "  venv         - Create Python virtual environment"
	@echo "  install      - Install dependencies" 
	@echo "  run          - Run legacy RSI bot"
	@echo "  run-live     - Run RSI bot continuously (PAPER=false) using lean env"
	@echo "  api-server   - Start API server"
	@echo "  rsi-compat   - Run RSI bot in compatibility mode"
	@echo "  system-test  - Run comprehensive system tests"
	@echo "  test         - Run pytest tests"
	@echo "  lint         - Run code linting"
	@echo "  fmt          - Format code"
	@echo "  docker-build - Build Docker images"
	@echo "  up           - Start API server with Docker"
	@echo "  down         - Stop Docker containers"
	@echo "  logs         - View container logs"
	@echo "  shell        - Open shell in container"
	@echo "  venv-lean    - Create lean runtime venv (no TF/grpc/absl)"
	@echo "  install-lean - Install minimal runtime deps into .venv-lean"
	@echo "  run-lean     - Run multi-signal test via lean env"
	@echo "  run-integrator-lean - Run integrator smoke test via lean env"
	@echo "  quick-checks - Run lean quick checks (tests + integrator)"
	@echo "  pre-commit-install - Install pre-commit and register hooks"
	@echo "  pre-commit-run     - Run pre-commit on all files"
	@echo "  run-once-paper     - Run RSI bot once (PAPER=true) using lean env"
	@echo "  run-once-live      - Run RSI bot once (PAPER=false) using lean env"
	@echo "  preflight-order    - Preview normalized order params (no placement)"
	@echo "  select-dynamic     - Select top volatile USD symbols and update config"
	@echo "  refresh-and-preflight - Refresh symbols dynamically and preflight all"
	@echo "  docs-lint    - Check markdown fences + markdownlint (non-fatal)"
	@echo "  docs-fix     - Normalize fences and show pending changes"

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
