#!/usr/bin/env python3
"""Run a local preflight check using the bundled `scripts/test_markets.json`.

This avoids calling live exchange APIs in CI and provides a deterministic
preflight run to validate the minima-checking logic.
"""
import json
import sys
from pathlib import Path
try:
    from yaml import safe_load  # type: ignore
except Exception:
    safe_load = None

# Ensure repo root is on sys.path so we can import `src.*` modules when running
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.market_utils import get_minima_report, check_markets_have_minima  # noqa: E402


def load_config(path="config.yaml"):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    text = p.read_text()
    if safe_load:
        return safe_load(text)
    # Fallback: try JSON
    try:
        import json

        return json.loads(text)
    except Exception:
        raise


def run_preflight(markets_path: Path = None, config_path: Path = None, json_output: Path = None):
    repo_root = Path(__file__).resolve().parent.parent
    if markets_path is None:
        markets_path = repo_root / "scripts" / "test_markets.json"
    if config_path is None:
        config_path = repo_root / "config.yaml"

    cfg = load_config(config_path)
    symbols = cfg.get("symbols") or ["SOL/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "ATOM/USD"]

    markets = json.loads(Path(markets_path).read_text())

    report = get_minima_report(markets, symbols)

    if json_output:
        Path(json_output).write_text(json.dumps(report, indent=2))
        return report

    print("Local Preflight Minima Report:\n")
    for s, info in report.items():
        if info.get('found_as') is None:
            print(f"{s}: NOT FOUND")
        else:
            print(f"{s}: found_as={info.get('found_as')}, cost_min={info.get('cost_min')}, amount_min={info.get('amount_min')}")

    missing = check_markets_have_minima(markets, symbols)
    if missing:
        print(f"\nFAILED: missing minima -> {missing}")
        raise SystemExit(1)
    print("\nOK: All configured symbols have minima in the local test markets dump.")
    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run the local preflight minima check")
    parser.add_argument("--json-output", type=str, default=None, help="Write JSON report to path")
    args = parser.parse_args()

    run_preflight(json_output=args.json_output)


if __name__ == "__main__":
    main()
