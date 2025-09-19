 # Preflight & Minima Enforcement: dry-preflight, diagnostics, auto-close hardening, and maintainer scripts

## Summary

- Add robust preflight checks that detect exchange minima (cost/amount) and prevent live runs when minima/limits are missing.
- Add `--dry-preflight` CLI flag to `multi_signal_bot.py` with `--markets-file` support for offline validation.
- Add diagnostic minima reporting (human readable and JSON) via `src/market_utils.get_minima_report`.
- Implement maintainers' helper scripts:
  - `scripts/validate_markets.py` — validate a local markets dump against configured symbols.
  - `scripts/run_preflight_local.py` — deterministic preflight runner (supports `--json-output` and exposes `run_preflight()` for tests).
  - `scripts/test_markets.json` — small fixture for CI/local validation.
  - `scripts/generate_markets_dump.py` — convenience script to fetch `exchange.load_markets()` (requires API/network).
- Add focused tests covering market minima detection, preflight JSON output, and import checks.

## Rationale

This change prevents accidental live orders being placed below exchange minimums and provides deterministic preflight validation that runs quickly in CI without network access. The diagnostics accelerate incident response and symbol mapping for different exchange naming conventions.

## Files of interest

- `multi_signal_bot.py` — `--dry-preflight` flag and diagnostic printing
- `src/market_utils.py` — minima detection and diagnostic report
- `scripts/*` — validation, generator, and preflight runner
- `tests/*` — focused tests for minima and preflight

## Testing performed locally

- Focused tests run locally: `pytest -q tests/test_market_minima.py tests/test_budget_manager.py tests/test_validate_markets_import.py tests/test_run_preflight_local.py` → 12 passed.
- `scripts/run_preflight_local.py` executed successfully against bundled `scripts/test_markets.json`.

## Notes for reviewers

- Review `src/market_utils.py` for variant matching (slash vs hyphen, alias base mapping like BTC/XBT). Consider additional exchange-specific mappings if needed.
- `multi_signal_bot.py` is conservative in live mode: it aborts if required minima are missing. The `--dry-preflight` helper prints diagnostics and exits with appropriate status codes for CI or local checks.
- The CI workflow was prepared but not pushed to the branch with workflow changes due to repository restrictions on PAT scopes. The branch `copilot/ctofix-minima-auto-close-no-workflow` contains all code changes and helper scripts; maintainers can re-add the workflow file in a follow-up PR or supply a token with `workflow` scope.

## Follow-ups (separate PRs suggested)

- Add a JSON output comparator in CI to fail PRs if critical symbols lack minima.
- Add a protected job to refresh `scripts/test_markets.json` periodically using `scripts/generate_markets_dump.py` (requires secure API keys).
- Extend `get_minima_report` to include precision and step sizes to assist sizing logic.

## How to open the PR

Open a PR from the branch: `copilot/ctofix-minima-auto-close-no-workflow` → `main` and paste this description as the PR body. Quick link (open in browser):
<https://github.com/BIGmindz/Multiple-signal-decision-bot/pull/new/copilot/ctofix-minima-auto-close-no-workflow>

## Runtime Fixes & Validation

- Hotfix: removed an inner `import json` that shadowed the module-level
  `json` name and caused an UnboundLocalError when saving trades/metrics.
- Validation: ran a single-cycle paper run which opened three paper
  positions, saved `budget_state.json` and `multi_signal_trades.json`, and
  reported the surfaced starting capital: `Starting Capital: $107.41`.
