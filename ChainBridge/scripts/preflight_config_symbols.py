#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def maybe_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore

        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
    except Exception:
        pass


def load_config_yaml(path: Path) -> Dict[str, Any]:
    import yaml  # type: ignore

    raw = path.read_text(encoding="utf-8")
    expanded = os.path.expandvars(raw)
    data = yaml.safe_load(expanded) or {}
    if not isinstance(data, dict):
        raise TypeError("config must be a dictionary")
    return data


def build_exchange() -> "object":
    import ccxt  # type: ignore

    exchange_id = os.getenv("EXCHANGE", "kraken").lower()
    if not hasattr(ccxt, exchange_id):
        raise SystemExit(
            f"Unknown exchange id '{exchange_id}' – set EXCHANGE env or .env"
        )
    exchange_cls = getattr(ccxt, exchange_id)
    return exchange_cls({"enableRateLimit": True})


def main() -> None:
    maybe_load_dotenv()

    cfg_path = REPO_ROOT / "config" / "config.yaml"
    cfg = load_config_yaml(cfg_path)
    symbols: List[str] = list(cfg.get("symbols") or [])  # type: ignore
    if not symbols:
        print("No symbols in config; nothing to preflight.")
        return

    from src.exchange_adapter import ExchangeAdapter

    exchange = build_exchange()
    quote_amount = float(os.getenv("PREFLIGHT_USD", "25"))  # type: ignore

    adapter = ExchangeAdapter(
        exchange=exchange,
        config={
            "amount_is_quote": True,
            "default_order_type_buy": "market",
            "default_order_type_sell": "market",
            "skip_balance_check": True,
        },
    )

    report: Dict[str, Dict[str, Any]] = {}
    for sym in symbols:
        entry: Dict[str, Any] = {}
        try:
            entry["buy"] = adapter.preflight_order(
                sym, "buy", quote_amount, price=None, order_type="market"
            )
        except Exception as e:
            entry["buy_error"] = str(e)
        try:
            entry["sell"] = adapter.preflight_order(
                sym, "sell", quote_amount, price=None, order_type="market"
            )
        except Exception as e:
            entry["sell_error"] = str(e)
        report[sym] = entry

    out = REPO_ROOT / "preflight_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote preflight report to {out}")
    total = len(symbols)
    ok_buy = sum(1 for v in report.values() if isinstance(v.get("buy"), dict))  # type: ignore
    ok_sell = sum(1 for v in report.values() if isinstance(v.get("sell"), dict))  # type: ignore
    print(f"Summary: {total} symbols | BUY ok: {ok_buy} | SELL ok: {ok_sell}")


if __name__ == "__main__":
    main()
