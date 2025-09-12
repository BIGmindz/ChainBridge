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
