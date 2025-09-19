Usage: Validate markets dump

This folder contains helper scripts for maintainers.

- `validate_markets.py`: Load a local markets JSON (export of `exchange.markets`) and
  check that configured symbols in `config.yaml` have detectable minima via
  `src.market_utils.check_markets_have_minima`.

Example:
```bash
.venv/bin/python3 scripts/validate_markets.py /path/to/markets.json
```

This script is intended for offline validation and does not require network access.

Refreshing the markets fixture
------------------------------

If you need to refresh the `scripts/test_markets.json` fixture with a live
dump from an exchange, use `scripts/generate_markets_dump.py`. This requires
network access and (optionally) API credentials in environment variables:

```bash
EXCHANGE=kraken API_KEY=... API_SECRET=... \
  .venv/bin/python3 scripts/generate_markets_dump.py --out ./scripts/test_markets.json
```

Only maintainers with network access should run this; CI does not execute this script.
