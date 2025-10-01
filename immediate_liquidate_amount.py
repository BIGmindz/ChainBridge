#!/usr/bin/env python3
"""Immediate USD Target Liquidation (multi-quote)

Sell non-stable spot balances into USD / USDT / USDC until a target USD notional
is liquidated. Largest USD value assets first to minimize order count.

Safety: requires FORCE_LIQUIDATE_NOW=1 to actually submit market sell orders.
Without it the script prints a plan (dry-run) and exits.
"""

import os
import sys
import time
import argparse
from typing import List, Dict, Tuple, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import ccxt  # type: ignore

KRAKEN_SYMBOL_MAP = {
    "XXBT": "BTC",
    "XBT": "BTC",
    "XETH": "ETH",
    "XDG": "DOGE",
    "XXRP": "XRP",
    "XLTC": "LTC",
    "XTRX": "TRX",
    "XADA": "ADA",
    "XXLM": "XLM",
    "XETC": "ETC",
}
STABLE = {"USD", "ZUSD", "USDT", "USDC", "USDG", "DAI", "TUSD"}


def norm(asset: str) -> str:
    return KRAKEN_SYMBOL_MAP.get(asset.upper(), asset.upper())


def load_exchange():
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit("Missing API_KEY/API_SECRET")
    ex = ccxt.kraken({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
    ex.load_markets()
    return ex


def fetch_assets(ex) -> List[Dict]:
    bal = ex.fetch_balance()
    assets = []
    for asset, info in bal.items():
        if not isinstance(info, dict):
            continue
        free_amt = info.get("free") or info.get("available") or 0
        if not free_amt:
            continue
        if asset in STABLE:
            continue
        assets.append({"raw": asset, "free": float(free_amt)})  # type: ignore
    return assets


def best_pair_price(ex, base: str) -> Tuple[Optional[float], Optional[str]]:
    for quote in ("USD", "USDT", "USDC"):
        pair = f"{base}/{quote}"
        if pair in ex.markets:
            try:
                t = ex.fetch_ticker(pair)
                px = t.get("last") or t.get("close") or t.get("bid") or t.get("ask")
                if px:
                    return float(px), pair  # type: ignore
            except Exception:
                pass
    return None, None


def build_plan(ex, assets: List[Dict], target: float):
    enriched = []
    skipped = []
    for a in assets:
        base = norm(a["raw"])
        price, pair = best_pair_price(ex, base)
        if not price:
            skipped.append(base)  # type: ignore
            continue
        usd_value = a["free"] * price
        enriched.append({"base": base, "pair": pair, "price": price, "free": a["free"], "usd_value": usd_value})  # type: ignore
    enriched.sort(key=lambda x: x["usd_value"], reverse=True)
    plan = []
    remaining = target
    for e in enriched:
        if remaining <= 0:
            break
        sell_value = min(e["usd_value"], remaining)
        qty = sell_value / e["price"]
        if qty <= 0:
            continue
        plan.append({"pair": e["pair"], "qty": qty, "sell_value": sell_value, "price": e["price"], "base": e["base"]})  # type: ignore
        remaining -= sell_value
    executed = target - remaining
    return plan, executed, skipped


def execute(ex, plan):
    for step in plan:
        try:
            order = ex.create_order(symbol=step["pair"], type="market", side="sell", amount=step["qty"])
            status = order.get("status") or order.get("info", {}).get("status")
            print(f"✅ Sold {step['qty']:.6f} {step['pair']} (status {status})")
            time.sleep(1.1)
        except Exception as e:
            print(f"❌ Failed {step['pair']}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Immediate USD target liquidation")
    ap.add_argument("--amount", type=float, required=True, help="Target USD value to liquidate")
    args = ap.parse_args()
    target = args.amount
    if target <= 0:
        print("Amount must be positive")
        return 1
    ex = load_exchange()
    print(f"🌐 Exchange time: {ex.iso8601(ex.milliseconds())}")
    assets = fetch_assets(ex)
    if not assets:
        print("No sellable assets (only stable or zero balances).")
        return 0
    plan, planned, skipped = build_plan(ex, assets, target)
    if not plan:
        print("No liquidation plan (no priced assets).")
        if skipped:
            print("Skipped:", ", ".join(sorted(set(skipped))))
        return 1
    print("\n📋 Liquidation Plan:")
    for step in plan:
        print(f" - {step['pair']}: sell ~${step['sell_value']:.2f} ({step['qty']:.6f} units) @ ~${step['price']:.4f}")
    print(f"Total planned: ${planned:.2f} (target ${target:.2f})")
    if skipped:
        print("⚠️ Skipped (no USD/USDT/USDC market):", ", ".join(sorted(set(skipped))))
    if not os.getenv("FORCE_LIQUIDATE_NOW"):
        print("\n⚠️ SAFETY STOP: set FORCE_LIQUIDATE_NOW=1 to execute market orders.")
        return 2
    print("\n🚀 Executing market sells...")
    execute(ex, plan)
    print("✅ Liquidation attempt complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
