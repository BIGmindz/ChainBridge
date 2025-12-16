PY?=20 20 12 61 79 80 81 701 33 98 100 204 250 395 398 399 400CURDIR)/.venv/bin/python
COMPOSE?=docker compose

.PHONY: help venv install run test lint fmt docker-build up down logs shell api-server rsi-compat system-test dev dev-docker setup gatekeeper

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
	@echo "  gatekeeper   - Validate agent output packet (FILE=...)"

gatekeeper:
	$(PY) scripts/gatekeeper/check_agent_output.py $(FILE)

PY ?= $(CURDIR)/.venv/bin/python
.PHONY: quick-checks
quick-checks:
	.venv/bin/python -m pytest -q tests/agents
