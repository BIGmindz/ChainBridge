PY=python
COMPOSE?=docker compose

.PHONY: help venv install run test lint fmt docker-build up down logs shell

help: ; @echo "Targets: venv install run test lint fmt docker-build up down logs shell"

venv:
	@[ -d .venv ] || python3 -m venv .venv
	@. .venv/bin/activate && pip install -U pip

install:
	@. .venv/bin/activate && pip install -r requirements.txt

run:
	@. .venv/bin/activate && $(PY) benson_rsi_bot.py

test:
	@. .venv/bin/activate && $(PY) -m pytest -q || true

lint:
	@. .venv/bin/activate && python -m pip install -q ruff && ruff check .

fmt:
	@. .venv/bin/activate && python -m pip install -q ruff && ruff format .

docker-build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

shell:
	$(COMPOSE) exec bot /bin/bash || true
