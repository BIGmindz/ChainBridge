# ChainBridge Import Safety System

## Why Import Safety Matters

ChainBridge enforces strict Python import safety to prevent environment drift, broken dependencies, and accidental use of system Python. This is required for ALEX governance and enterprise reliability.

## Why Fallback Exists

Some vendor libraries (e.g., older FastAPI, Pydantic, or plugins) still require `importlib_metadata` even on Python 3.11+. The import safety shim ensures:
- Always uses `importlib.metadata` if available
- Falls back to `importlib_metadata` backport if needed
- Unified API for version(), packages(), etc.

## How Developers Validate Environment

- Always activate `.venv` before running any service or tests
- Run `python scripts/validate_imports.py` to check all required imports
- Use the pre-commit hook `.githooks/pre-commit-import-safety` to block commits if imports are broken
- CI runs import validation on every push

## How CI Catches Drift

- `.github/workflows/python-ci.yml` and `kafka-ci.yml` run `python scripts/validate_imports.py` before tests
- If any import fails, CI exits non-zero and blocks the build
- Early detection prevents broken deployments

## Summary
- No more `ModuleNotFoundError` for `importlib_metadata`
- All services use the import safety shim
- Environment drift is caught early
- Developers and CI are protected

**Always use `.venv/bin/python` and validate imports before pushing or committing!**
