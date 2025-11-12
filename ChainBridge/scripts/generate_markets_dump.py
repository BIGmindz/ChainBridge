#!/usr/bin/env python3
"""Fetch exchange markets and write to a JSON file.

This script requires network access and will use environment variables
`EXCHANGE`, `API_KEY`, and `API_SECRET` if present. It is intended for
maintainers to refresh the `scripts/test_markets.json` fixture.

Usage:
  EXCHANGE=kraken API_KEY=... API_SECRET=... python3 scripts/generate_markets_dump.py \
      --out /tmp/markets.json
"""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Fetch exchange markets and save JSON")
    parser.add_argument("--out", type=str, default=None, help="Output path for markets JSON")
    args = parser.parse_args()

    exchange_id = os.getenv("EXCHANGE", "kraken")
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")

    try:
        import ccxt
    except Exception:
        print("ccxt not installed. Install with: pip install ccxt")
        raise

    params = {}
    if api_key and api_secret:
        params["apiKey"] = api_key
        params["secret"] = api_secret

    ex_cls = getattr(ccxt, exchange_id)
    ex = ex_cls({})
    if api_key and api_secret:
        ex.apiKey = api_key
        ex.secret = api_secret

    print(f"Loading markets from {exchange_id}...")
    markets = ex.load_markets()

    out_path = Path(args.out) if args.out else Path("./scripts/markets_dump.json")
    out_path.write_text(json.dumps(markets, indent=2))
    print(f"Saved markets to: {out_path}")


if __name__ == "__main__":
    main()
