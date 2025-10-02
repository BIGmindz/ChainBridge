# Lean Quick Checks and Dev Ergonomics

This repo supports fast, offline validations without heavy ML stacks.

## What’s included

- Lean virtualenv: `.venv-lean` (PyYAML + pytest)
- Quick checks: RSI scenario tests + integrator smoke test (TF-optional)
- Linting via Ruff with repo-aware config (`ruff.toml`)



## One-time setup

```sh
cd /Users/johnbozza/Multiple-signal-decision-bot
python3 -m venv .venv-lean
. .venv-lean/bin/activate
pip install -r requirements-runtime.txt
```

## Run the lean quick checks

```sh
make quick-checks
```

What it does:

- Verifies PyYAML import
- Runs `tests/test_rsi_scenarios.py`
- Runs `scripts/integrator_smoke_test.py` (returns equal/default weights if TF is absent)



## Lint and format

```sh
# Lint
make lint

# Format (optional)
. .venv/bin/activate && python -m pip install -q ruff && ruff format .
```

## Pre-commit (optional)

```sh
make venv && make install
make pre-commit-install
# To run on entire repo
make pre-commit-run
```

## CI

The GitHub Actions workflow runs:

- Unit tests: `python benson_rsi_bot.py --test` and `pytest`
- Lean quick checks: `make quick-checks`
- Lint (`ruff`) and type checks (`mypy`)



## Troubleshooting

- Externally managed system Python (PEP 668): always use a virtualenv (`.venv` or `.venv-lean`).
- If `make quick-checks` fails on the smoke test with a TF import error, that’s expected; it falls back to `status: "default_weights"`.
- Ensure `.venv-lean` is not tracked by Git (it is ignored via `.gitignore`).



## Files

- `requirements-runtime.txt` — minimal deps for quick checks
- `scripts/integrator_smoke_test.py` — lean smoke test for adaptive weights
- `ruff.toml` — lint configuration tailored to this repository
- `Makefile` — targets: `venv-lean`, `install-lean`, `run-integrator-lean`, `quick-checks`
