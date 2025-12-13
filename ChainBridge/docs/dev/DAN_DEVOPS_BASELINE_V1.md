# DAN DevOps Baseline V1

## Purpose

This document defines the first DevOps baseline for the ChainBridge monorepo:

- A normalized `.gitignore` so virtual environments, `node_modules`, caches, coverage reports, and OS junk do not pollute `git status`.
- A default test command that CI and local developers can share.
- A minimal GitHub Actions workflow that runs sanity tests on pushes and pull requests.

This is **V0.5: sanity CI**, intended as a foundation for future DAN PACs.

## Local Dev Instructions

### Python tests

From the monorepo root (where `ChainBridge/` lives):

```bash
cd ChainBridge
# (optional) activate your local venv if you use one
# source .venv/bin/activate

pytest -vv
```

If you prefer to scope to the main `tests/` package only:

```bash
cd ChainBridge
pytest -vv tests
```

These are the same shapes of commands that the basic CI workflow uses.

## CI Workflow Summary

Workflow file: `ChainBridge/.github/workflows/ci-basic.yml`

- **Name:** `CI - Basic`
- **Triggers:**
  - `push` to `main`, `develop`
  - `pull_request` targeting `main`, `develop`
- **Runtime:**
  - `ubuntu-latest`
  - Python `3.11`
- **Steps (high level):
  1. Check out the repository.
  2. Set up Python 3.11.
  3. Install dependencies using `requirements.txt` files (root and key services), each guarded with `|| true` so the workflow remains usable even if some optional files are missing.
  4. Change into `ChainBridge/` if it exists.
  5. If a `tests/` directory exists, run:
     - `pytest -vv` (falling back to `pytest -vv tests` if needed).

This ensures that **if tests exist**, they are executed on every push/PR to the main development branches.

## .gitignore Baseline

The `.gitignore` at both the monorepo root and inside `ChainBridge/` are normalized to ignore:

- **Python:** `__pycache__/`, `*.py[cod]`, `*.pyo`, `*.pyd`, `*.sqlite3`
- **Virtual environments:** `.venv/`, `venv/`, `.venv-lean/`
- **Node:** `node_modules/`, `dist/`, `build/`, `npm-debug.log*`, `yarn-debug.log*`, `yarn-error.log*`
- **Testing / coverage:** `.coverage`, `.coverage.*`, `htmlcov/`, `.pytest_cache/`, `coverage*/`, `reports*/`
- **Data & logs:** `logs/`, `data/`, `*.log`
- **OS junk:** `.DS_Store`, `Thumbs.db`

Project-specific artifacts (like `benson_metrics.json`, `multi_signal_trades.json`, etc.) are preserved.

## Future Extensions

These are recommended next steps for future DAN PACs:

- **Linting:** Add a `ruff` (or similar) lint job to CI, using the same Python 3.11 environment.
- **Coverage Gates:** Extend CI to enforce coverage thresholds for critical packages.
- **Service-specific Jobs:** Add separate jobs for `chainpay-service` and `chainiq-service` that run their dedicated test suites.
- **Frontend Build:** Add a job that installs Node dependencies and builds `chainboard-ui`.
- **Docker / Deployment:** Add Docker build and (eventually) push steps for selected services.

## Governance Link

Overall CI and tool governance are owned by **ALEX**. Once available, this baseline should reference `docs/governance/ALEX_TOOL_GOVERNANCE_V1.md` as the authoritative security and tooling policy document.

For now, this document acts as the local DevOps baseline that future governance docs can extend.
