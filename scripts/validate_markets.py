#!/usr/bin/env python3
"""Validate a local markets JSON file against configured symbols.

This script loads `config.yaml` to get the list of symbols and a local
markets JSON (saved via `exchange.markets` or similar). It calls
`src.market_utils.check_markets_have_minima` and prints a report.

Usage:
  python3 scripts/validate_markets.py /path/to/markets.json
"""
import json
import sys
from pathlib import Path

from yaml import safe_load

from src.market_utils import check_markets_have_minima


def load_config(path="config.yaml"):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return safe_load(p.read_text())


def load_markets(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Markets file not found: {path}")
    return json.loads(p.read_text())


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/validate_markets.py /path/to/markets.json")
        sys.exit(2)

    markets_path = sys.argv[1]
    config = load_config()
    symbols = config.get("symbols") or config.get("watchlist") or []

    markets = load_markets(markets_path)

    print(f"Loaded {len(symbols)} configured symbols from config.yaml")
    missing = check_markets_have_minima(markets, symbols)

    if not missing:
        print("All configured symbols have minima in the provided markets dump.")
        sys.exit(0)

    print("Symbols missing minima (or minima could not be detected):")
    for s in missing:
        print(f"  - {s}")
    sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Validate a local markets JSON file against configured symbols.

Usage: python scripts/validate_markets.py path/to/markets.json config.yaml
"""
import sys, json, yaml
from src.market_utils import check_markets_have_minima


def main():
    if len(sys.argv) < 3:
        print("Usage: validate_markets.py markets.json config.yaml")
        return 2

    markets_path = sys.argv[1]
    cfg_path = sys.argv[2]

    with open(markets_path, "r") as f:
        markets = json.load(f)

    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    symbols = cfg.get("symbols", [])
    missing = check_markets_have_minima(markets, symbols)
    if missing:
        print(f"Missing minima for symbols: {missing}")
        return 1
    print("All symbols have minima/limits present.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
