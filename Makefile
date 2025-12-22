# ═══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE CORE MAKEFILE
# ═══════════════════════════════════════════════════════════════════════════════
#
# SCOPE LOCK: Targets outside governance/gateway/UI scope are FORBIDDEN.
# See: docs/governance/REPO_SCOPE_MANIFEST.md
#
# Multi-service supply chain management and payment orchestration platform.
# Includes: API Gateway, ChainIQ (ML risk scoring), ChainPay, ChainBoard
#
# Legacy RSI/crypto bot code is archived at: archive/legacy-rsi-bot/
# DO NOT add trading, bot, or crypto targets to this file.
#
# PAC Reference: PAC-REPO-SCOPE-LOCK-01
# Locked by: ATLAS (GID-11)
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# ALLOWED TARGETS (LOCKED)
# ═══════════════════════════════════════════════════════════════════════════════
# Only targets aligned with ChainBridge Core are permitted:
#   - Setup: venv, install, setup
#   - Development: test, lint, fmt, gatekeeper, scope-guard
#   - Quality: pre-commit-*, docs-*
#   - Docker: docker-build, up, down, logs, shell
#   - Stack: dev, dev-docker
# ═══════════════════════════════════════════════════════════════════════════════

PY = python
COMPOSE ?= docker compose

.PHONY: help venv install test lint fmt gatekeeper scope-guard scope-check claims-gate validate-claims \
        pre-commit-install pre-commit-run docs-lint docs-fix \
        docker-build up down logs shell dev dev-docker setup

# ═══════════════════════════════════════════════════════════════════════════════
# HELP
# ═══════════════════════════════════════════════════════════════════════════════

help:
	@echo "══════════════════════════════════════════════════════════════════"
	@echo "  ChainBridge Platform — Development Targets"
	@echo "══════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Setup:"
	@echo "    venv              Create Python virtual environment"
	@echo "    install           Install dependencies"
	@echo "    setup             One-command setup (venv + install)"
	@echo ""
	@echo "  Development:"
	@echo "    test              Run pytest tests"
	@echo "    lint              Run code linting (ruff)"
	@echo "    fmt               Format code (ruff)"
	@echo "    gatekeeper        Validate agent packet identity"
	@echo ""
	@echo "  Quality:"
	@echo "    pre-commit-install  Install pre-commit hooks"
	@echo "    pre-commit-run      Run pre-commit on all files"
	@echo "    docs-lint           Check markdown quality"
	@echo "    docs-fix            Normalize markdown fences"
	@echo "    scope-guard         Run repository scope validation"
	@echo "    claims-gate         Validate trust claims (PAC-ALEX-CLAIMS-GATE-01)"
	@echo ""
	@echo "  Docker:"
	@echo "    docker-build      Build Docker images"
	@echo "    up                Start containers"
	@echo "    down              Stop containers"
	@echo "    logs              View container logs"
	@echo "    shell             Open shell in container"
	@echo ""
	@echo "  Stack:"
	@echo "    dev               Start local dev stack (API + UI)"
	@echo "    dev-docker        Start Docker dev stack"
	@echo ""
	@echo "  Scope: docs/governance/REPO_SCOPE_MANIFEST.md"
	@echo ""
	@echo "══════════════════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════════════

venv:
	@[ -d .venv ] || python3 -m venv .venv
	@. .venv/bin/activate && pip install -U pip

install: venv
	@. .venv/bin/activate && pip install -r requirements.txt

setup: venv install
	@echo "✓ ChainBridge environment ready"

# ═══════════════════════════════════════════════════════════════════════════════
# DEVELOPMENT
# ═══════════════════════════════════════════════════════════════════════════════

test:
	@. .venv/bin/activate && $(PY) -m pytest -q

lint:
	@. .venv/bin/activate && python -m pip install -q ruff && ruff check .

fmt:
	@. .venv/bin/activate && python -m pip install -q ruff && ruff format .

# Gatekeeper: Validate agent packet identity (PAC-DAN-GATEKEEPER-02)
# Usage: make gatekeeper FILE=tests/fixtures/agent_outputs/valid_dan_packet.txt
gatekeeper:
ifndef FILE
	@echo "Usage: make gatekeeper FILE=<path-to-agent-packet>"
	@echo "Example: make gatekeeper FILE=tests/fixtures/agent_outputs/valid_dan_packet.txt"
	@exit 1
endif
	@. .venv/bin/activate && python scripts/gatekeeper/check_agent_output.py $(FILE)

# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY TOOLING
# ═══════════════════════════════════════════════════════════════════════════════

pre-commit-install:
	@. .venv/bin/activate && python -m pip install -q pre-commit && pre-commit install

pre-commit-run:
	@. .venv/bin/activate && python -m pip install -q pre-commit && pre-commit run --all-files --show-diff-on-failure

docs-lint:
	@. .venv/bin/activate && python scripts/normalize_markdown_fences.py >/dev/null && git diff --quiet || (echo "⚠ Markdown fences need normalization" && git --no-pager diff --name-only)
	@command -v npx >/dev/null 2>&1 && npx --yes markdownlint-cli '**/*.md' || echo "(markdownlint skipped: npx not available)"

docs-fix:
	@. .venv/bin/activate && python scripts/normalize_markdown_fences.py && git --no-pager diff || true

# Scope Guard: Validate repository scope boundaries
# Usage: make scope-guard OR make scope-check
scope-guard:
	@. .venv/bin/activate && python scripts/scope_guard/check_repo_scope.py

# Alias for scope-guard (common alternative name)
scope-check: scope-guard

# Claims Gate: Validate trust claims against governance rules (PAC-ALEX-CLAIMS-GATE-01)
# Enforces: forbidden phrases, claim bindings, future tense prohibition
claims-gate:
	@. .venv/bin/activate && python scripts/validate_trust_claims.py --root .

# Alias for claims-gate
validate-claims: claims-gate

# ═══════════════════════════════════════════════════════════════════════════════
# DOCKER
# ═══════════════════════════════════════════════════════════════════════════════

docker-build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

shell:
	$(COMPOSE) exec benson-api /bin/bash || true

# ═══════════════════════════════════════════════════════════════════════════════
# STACK (Local Development)
# ═══════════════════════════════════════════════════════════════════════════════

dev:
	@echo "Starting ChainBridge local dev stack..."
	@./scripts/dev/run_stack.sh

dev-docker:
	@echo "Starting ChainBridge Docker dev stack..."
	$(COMPOSE) --profile dev up --build
