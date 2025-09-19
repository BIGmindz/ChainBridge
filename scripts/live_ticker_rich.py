#!/usr/bin/env python3
"""Rich-based live ticker for budget_state.json + multi_signal_trades.json

This provides clearer typography and larger P&L emphasis. Falls back with
an informative error if `rich` is not installed.

Usage:
  pip install rich
  python3 scripts/live_ticker_rich.py --interval 1 --cycles 0
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

try:
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.console import Console
    from rich.align import Align
    from rich import box
except Exception:
    Live = None
    Table = None
    Panel = None
    Text = None
    Console = None
    Align = None
    box = None

if Console:
    console = Console()
else:
    console = None

DATA_BUDGET = Path("budget_state.json")
DATA_TRADES = Path("multi_signal_trades.json")

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def read_json_safe(path: Path):
    try:
        with path.open("r") as f:
            return json.load(f)
    except Exception:
        return None


def sparkline(data, width=12):
    if not data:
        return " " * width
    mn = min(data)
    mx = max(data)
    chars = SPARK_CHARS
    if mx == mn:
        return chars[len(chars)//2] * min(width, len(data))
    out = []
    for v in data[-width:]:
        idx = int((v - mn) / (mx - mn) * (len(chars) - 1))
        idx = max(0, min(idx, len(chars) - 1))
        out.append(chars[idx])
    return "".join(out).ljust(width)


def build_table(budget, trades, big=False, delta_up=0.5, delta_down=0.5, show_arrows=False, gradient=False):
    # Performance summary
    perf = (budget or {}).get("performance", {}) if budget else {}
    cap = perf.get("current_capital", (budget or {}).get("current_capital", 0.0))
    avail = perf.get("available_capital", (budget or {}).get("available_capital", 0.0))
    open_pos = perf.get("open_positions", len((budget or {}).get("positions", [])))
    total_trades = perf.get("total_trades", (budget or {}).get("total_trades", 0))

    # Build recent prices map (seed from trades and current positions)
    recent_prices = {}
    for t in (trades or []):
        sym = t.get("symbol")
        price = t.get("price")
        if sym and price is not None:
            recent_prices.setdefault(sym, []).append(float(price))
    # Also seed from current positions in budget for better sparklines
    for p in (budget or {}).get("positions", []):
        sym = p.get("symbol")
        cur = p.get("current_price") or p.get("entry_price")
        if sym and cur is not None:
            recent_prices.setdefault(sym, []).append(float(cur))

    table = Table.grid(expand=True)
    # Top header panel
    header_text = Text()
    header_text.append("HEDGE DASH", style="bold cyan")
    header_text.append(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", style="dim white")
    header = Panel(Align.center(header_text), style="bold white on black")

    # Summary: left column (Capital/Open), right column (Available/Trades)
    summary = Table.grid(expand=True)
    summary.add_column(ratio=1)
    summary.add_column(ratio=1)
    left_col = Text()
    left_col.append(Text(f"Capital: $ {cap:0.2f}\n", style="bold green"))
    left_col.append(Text(f"Open: {open_pos}", style="bold"))
    right_col = Text()
    right_col.append(Text(f"Available: $ {avail:0.2f}\n", style="yellow"))
    right_col.append(Text(f"Trades: {total_trades}", style="bold"))
    summary.add_row(left_col, Align.right(right_col))

    # Positions table
    pos_table = Table(box=box.SIMPLE_HEAVY, expand=True)
    pos_table.add_column("Symbol", style="bold cyan")
    pos_table.add_column("Entry", justify="right")
    pos_table.add_column("Current", justify="right")
    pos_table.add_column("Qty", justify="right")
    pos_table.add_column("P&L", justify="right")
    pos_table.add_column("Spark", justify="left")

    for p in (budget or {}).get("positions", []):
        sym = p.get("symbol", "-")
        entry = float(p.get("entry_price", 0.0))
        cur = float(p.get("current_price", entry))
        q = float(p.get("quantity", 0))
        pnl = float(p.get("pnl", 0.0))
        spark = sparkline(recent_prices.get(sym, []), width=16)

        # Compute delta and stage
        delta_pct = 0.0
        try:
            if entry != 0:
                delta_pct = (cur - entry) / abs(entry) * 100.0
        except Exception:
            delta_pct = 0.0

        # stage indicator (use configured thresholds)
        if delta_pct > delta_up:
            stage = "⚡"
        elif delta_pct < -delta_down:
            stage = "🛑"
        else:
            stage = "●"

    # P&L styling: big -> brighter/bolder, include sign
        if pnl > 0:
            pnl_style = "bold white on green" if big else "green"
            pnl_text = Text(f"+{pnl:0.2f}", style=pnl_style)
        elif pnl < 0:
            pnl_style = "bold white on red" if big else "red"
            pnl_text = Text(f"{pnl:0.2f}", style=pnl_style)
        else:
            pnl_text = Text(f"{pnl:0.2f}", style="yellow")

        # Color lifecycle columns: Entry (red), Current (threshold/gradient), Qty (green)
        entry_cell = Text(f"{entry:0.6f}", style="red")

        # current color/arrow
        # choose base color for current
        if delta_pct > delta_up:
            base_style = "green"
        elif delta_pct < -delta_down:
            base_style = "red"
        else:
            base_style = "yellow"

        # arrow handling
        arrow = ""
        if show_arrows:
            arrow = "▲ " if delta_pct > 0 else ("▼ " if delta_pct < 0 else "  ")

        current_text = Text(f"{arrow}{cur:0.6f}", style=base_style)

        # gradient: pick a stronger background based on magnitude buckets
        if gradient:
            mag = min(abs(delta_pct) / max(delta_up, delta_down, 1e-6), 1.0)
            if mag > 0.66:
                bg = f"bold white on {base_style}"
                current_text.stylize(bg)
            elif mag > 0.33:
                bg = f"white on {base_style}"
                current_text.stylize(bg)

        qty_style = "bold green" if q >= 50 else "green"
        qty_cell = Text(f"{q:0.2f}", style=qty_style)

        sym_cell = Text(f"{stage} {sym}", style="bold cyan")

        pos_table.add_row(sym_cell, entry_cell, current_text, qty_cell, pnl_text, spark)

    # Recent trades panel
    trades_panel = Table.grid()
    trades_panel.add_column()
    trades_panel.add_row(Text("Recent trades:", style="bold"))
    for t in (trades or [])[-6:]:
        ts = t.get("timestamp", "-")
        sym = t.get("symbol", "-")
        act = t.get("action", "-")
        price = t.get("price", 0.0)
        act_style = "green" if (act or "").upper() == "BUY" else "red"
        trades_panel.add_row(Text(f"{ts}  {sym:8}  {act:4}  @ ${price}", style=act_style))

    # Compose layout
    table.add_row(header)
    table.add_row(summary)
    table.add_row(pos_table)
    table.add_row(Panel(trades_panel, title="Audit", expand=True))
    return table


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--cycles", type=int, default=0)
    p.add_argument("--big", action="store_true", help="Emphasize P&L and header")
    p.add_argument("--delta-up", type=float, default=0.5, help="Percent threshold for 'up' status")
    p.add_argument("--delta-down", type=float, default=0.5, help="Percent threshold for 'down' status")
    p.add_argument("--show-arrows", action="store_true", help="Show ▲/▼ next to Current")
    p.add_argument("--gradient", action="store_true", help="Apply gradient background to Current cell based on delta")
    args = p.parse_args()

    if Live is None or console is None:
        print("The script requires the 'rich' package. Install with: pip install rich")
        raise SystemExit(1)

    cycles = 0
    with Live(console=console, refresh_per_second=4) as live:
        try:
            while True:
                budget = read_json_safe(DATA_BUDGET)
                trades = read_json_safe(DATA_TRADES) or []
                table = build_table(
                    budget,
                    trades,
                    big=args.big,
                    delta_up=args.delta_up,
                    delta_down=args.delta_down,
                    show_arrows=args.show_arrows,
                    gradient=args.gradient,
                )
                live.update(table)
                cycles += 1
                if args.cycles > 0 and cycles >= args.cycles:
                    break
                time.sleep(args.interval)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
