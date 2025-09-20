#!/usr/bin/env python3
import json
from datetime import datetime
from decimal import Decimal

BUDGET_FILE = "budget_state.json"
TRADES_FILE = "multi_signal_trades.json"

TARGET_SYMBOLS = ["PRO/USD", "KIN/USD"]


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def close_positions():
    budget = load_json(BUDGET_FILE)
    trades = load_json(TRADES_FILE)

    positions = budget.get("positions", [])
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    closed_any = False
    total_realized = Decimal("0")

    new_positions = []
    for pos in positions:
        if pos.get("status") == "OPEN" and pos.get("symbol") in TARGET_SYMBOLS:
            symbol = pos["symbol"]
            entry_price = Decimal(str(pos.get("entry_price", 0)))
            quantity = Decimal(str(pos.get("quantity", 0)))
            take_profit = pos.get("take_profit")
            if take_profit and take_profit > 0:
                sell_price = Decimal(str(take_profit))
            else:
                # fallback: small profit over entry
                sell_price = (entry_price * Decimal("1.01")).quantize(Decimal("0.00000001"))

            pnl = (sell_price - entry_price) * quantity
            pnl_f = float(pnl)

            # Create SELL trade record
            sell_trade = {
                "timestamp": now,
                "symbol": symbol,
                "action": "SELL",
                "price": float(sell_price),
                "size": pos.get("size"),
                "quantity": float(quantity),
                "confidence": None,
                "signals": {},
                "id": f"{pos.get('id')}_CLOSE",
                "closed_from_id": pos.get("id"),
                "realized_pnl": pnl_f,
            }
            trades.append(sell_trade)

            # Update budget numbers
            budget["available_capital"] = round(budget.get("available_capital", 0) + pos.get("size") + pnl_f, 2)
            budget["current_capital"] = round(budget.get("current_capital", 0) + pnl_f, 2)

            # Update performance
            perf = budget.get("performance", {})
            perf["total_pnl"] = round(perf.get("total_pnl", 0) + pnl_f, 2)
            perf["total_trades"] = perf.get("total_trades", 0) + 1
            if pnl_f > 0:
                perf["winning_trades"] = perf.get("winning_trades", 0) + 1
            else:
                perf["losing_trades"] = perf.get("losing_trades", 0) + 1
            # recompute win rate
            wins = perf.get("winning_trades", 0)
            total = perf.get("total_trades", 1)
            perf["win_rate"] = round((wins / total) * 100, 2)

            budget["performance"] = perf

            total_realized += pnl
            closed_any = True
            print(f"Closed {symbol} at {sell_price} for PnL {pnl_f}")
            # Do not add this pos to new_positions (removes it)
        else:
            new_positions.append(pos)

    if not closed_any:
        print("No matching open positions found to close.")
        return

    budget["positions"] = new_positions
    budget["trade_history"] = budget.get("trade_history", []) + [t for t in trades if t.get("action") == "SELL"]
    budget["timestamp"] = datetime.utcnow().isoformat()

    save_json(BUDGET_FILE, budget)
    save_json(TRADES_FILE, trades)

    print("\nSummary:")
    print(f"  Positions closed: {len(TARGET_SYMBOLS)} (attempted)")
    print(f"  Total realized PnL: {float(total_realized):.8f}")
    print(f"  Updated {BUDGET_FILE} and {TRADES_FILE}")


if __name__ == "__main__":
    close_positions()
