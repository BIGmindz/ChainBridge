#!/usr/bin/env python3
"""Simple live ticker that reads `budget_state.json` and `multi_signal_trades.json`
and prints a small dashboard repeatedly. Intended for local monitoring / demo.

Usage:
  python scripts/live_ticker.py --interval 2 --cycles 0

Set `--cycles 0` to run indefinitely (Ctrl-C to stop).
"""

import argparse
import re
import shutil

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(s: str) -> int:
    """Return visible length of string without ANSI escape sequences."""
    if not s:
        return 0
    return len(ANSI_RE.sub("", str(s)))


import json
import os
import sys
import time
from datetime import datetime

try:
    import pyfiglet
except Exception:
    pyfiglet = None

# ANSI color helpers
CSI = "\x1b["


def color(code):
    return CSI + str(code) + "m"


RESET = color(0)
BOLD = color(1)
DIM = color(2)
GREEN = color(32)
YELLOW = color(33)
RED = color(31)
BLUE = color(34)
CYAN = color(36)
WHITE = color(37)
BG_GREEN = color("42")
BG_RED = color("41")
BG_YELLOW = color("43")


def read_json_safe(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def render(
    budget,
    trades,
    big=False,
    delta_up=0.5,
    delta_down=0.5,
    show_arrows=False,
    gradient=False,
):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    os.system("clear")
    header = f"🏦  HEDGE DASH • {now}"
    if big and pyfiglet:
        fig = pyfiglet.Figlet(font="slant")
        try:
            print(CYAN + fig.renderText("HEDGE DASH") + RESET)
        except Exception:
            print(BOLD + header + RESET)
        print(DIM + now + RESET)
    elif big:
        # Fallback big-ish header without pyfiglet
        print(BOLD + CYAN + header + RESET)
        print(DIM + now + RESET)
    else:
        print(header)
        print("─" * len(header))

    if not budget:
        print("⚠️  No budget state available (budget_state.json missing or invalid)")
        print("\n(Press Ctrl-C to quit)")
        return

    perf = budget.get("performance", {})
    cap = perf.get("current_capital", 0.0)
    avail = perf.get("available_capital", 0.0)
    open_pos = perf.get("open_positions", 0)
    total_trades = perf.get("total_trades", 0)

    # Top-line summary: left-align Capital, right-align Available using terminal width
    term_width = shutil.get_terminal_size(fallback=(100, 20)).columns
    left = f"💰 Capital: ${cap:10.2f}"
    right = f"Available: ${avail:10.2f}"

    left_vis = visible_len(left)
    right_vis = visible_len(right)
    total_vis = left_vis + right_vis + 2

    # If the terminal is too narrow for a single-line summary, fall back to two lines
    if total_vis >= term_width:
        print(left)
        # right-align the Available on its own line
        print(right.rjust(term_width))
        print(f"📈 Positions:   {open_pos:>3} open    |    Trades: {total_trades:>4}")
    else:
        spacer = max(2, term_width - left_vis - right_vis)
        print(left + " " * spacer + right)
        print(f"📈 Positions:   {open_pos:>3} open    |    Trades: {total_trades:>4}")
    print("")

    # Build recent prices per symbol from trades for sparklines
    recent_prices = {}
    for t in trades:
        sym = t.get("symbol")
        price = t.get("price")
        if sym and price is not None:
            recent_prices.setdefault(sym, []).append(float(price))

    def sparkline(data, width=8):
        if not data:
            return " " * width
        chars = "▁▂▃▄▅▆▇█"
        mn = min(data)
        mx = max(data)
        if mx == mn:
            return chars[len(chars) // 2] * min(width, len(data))
        out = []
        for v in data[-width:]:
            # guard division
            idx = int((v - mn) / (mx - mn) * (len(chars) - 1))
            idx = max(0, min(idx, len(chars) - 1))
            out.append(chars[idx])
        s = "".join(out)
        return s.ljust(width)

    # Define column widths and headers
    cols = [
        (13, "Symbol"),
        (13, "Entry"),
        (13, "Current"),
        (11, "Qty"),
        (13, "P&L"),
        (8, "Spark"),
    ]
    total_inner = sum(w for w, _ in cols) + (len(cols) - 1) * 1 + 2
    # build top border accordingly
    print("┌" + "─" * total_inner + "┐")
    # header row
    hdr_cells = []
    for w, title in cols:
        hdr_cells.append(f" {title.center(w)} ")
    print("│" + "│".join(hdr_cells) + "│")
    print("├" + "─" * total_inner + "┤")

    for p in budget.get("positions", []):
        sym = p.get("symbol", "-")
        entry = float(p.get("entry_price", 0.0))
        cur = float(p.get("current_price", entry))
        q = float(p.get("quantity", 0))
        pnl = float(p.get("pnl", 0.0))

        # Prepare plain cell content and pad to width BEFORE adding color
        sym_plain = f"{sym}".ljust(cols[0][0])
        entry_plain = f"${entry:0{cols[1][0] - 1}.6f}".rjust(cols[1][0])
        cur_plain = f"${cur:0{cols[2][0] - 1}.6f}".rjust(cols[2][0])
        qty_plain = f"{q:0{cols[3][0]}.2f}".rjust(cols[3][0])
        pnl_plain = f"{pnl:0{cols[4][0]}.2f}".rjust(cols[4][0])
        spark = sparkline(recent_prices.get(sym, []), width=cols[5][0])

        # Compute progress indicators
        delta_pct = 0.0
        try:
            if entry != 0:
                delta_pct = (cur - entry) / abs(entry) * 100.0
        except Exception:
            delta_pct = 0.0

        # Stage indicator (simple heuristic)
        if delta_pct > 0.5:
            stage = "⚡"  # accelerating
        elif delta_pct < -0.5:
            stage = "🛑"  # losing
        else:
            stage = "●"  # neutral

        # Now wrap with colors
        sym_s = BOLD + BLUE + f"{stage} {sym_plain}" + RESET
        entry_s = RED + entry_plain + RESET
        # Color current based on delta thresholds
        if delta_pct < -delta_down:
            cur_color = RED
        elif delta_pct > delta_up:
            cur_color = GREEN
        else:
            cur_color = YELLOW

        cur_val = cur_plain
        if show_arrows:
            arrow = "▲" if delta_pct > 0 else ("▼" if delta_pct < 0 else " ")
            cur_val = f"{arrow} {cur_plain}"

        if gradient:
            # simple gradient: stronger green/red background for larger magnitude
            min(abs(delta_pct) / max(delta_up, delta_down), 1.0)
            if delta_pct > 0:
                # green background (use BG_GREEN ANSI if available) - approximate with BOLD
                cur_s = BG_GREEN + BOLD + cur_val + RESET
            elif delta_pct < 0:
                cur_s = BG_RED + BOLD + cur_val + RESET
            else:
                cur_s = BOLD + cur_val + RESET
        else:
            cur_s = cur_color + cur_val + RESET
        # Emphasize qty for larger positions
        if q >= 50:
            qty_s = BOLD + GREEN + qty_plain + RESET
        else:
            qty_s = GREEN + qty_plain + RESET

        if pnl > 0:
            pnl_s = BG_GREEN + BOLD + pnl_plain + RESET
        elif pnl < 0:
            pnl_s = BG_RED + BOLD + pnl_plain + RESET
        else:
            pnl_s = BG_YELLOW + pnl_plain + RESET

        spark_s = CYAN + spark + RESET

        # compose row
        cells = [
            f" {sym_s} ",
            f" {entry_s} ",
            f" {cur_s} ",
            f" {qty_s} ",
            f" {pnl_s} ",
            f" {spark_s} ",
        ]
        print("│" + "│".join(cells) + "│")

    print("└" + "─" * total_inner + "┘")

    # Recent trades
    print("\nRecent trades:")
    if not trades:
        print("  (no trades in audit)")
    else:
        for t in trades[-5:]:
            ts = t.get("timestamp", "-")
            sym = t.get("symbol", "-")
            act = t.get("action", "-")
            price = t.get("price", 0.0)
            emoji = "🔼" if act.upper() == "BUY" else "🔽"
            # color action
            if act.upper() == "BUY":
                act_s = GREEN + act + RESET
            else:
                act_s = RED + act + RESET
            print(f"  {emoji} {ts:19}  {sym:8}  {act_s:8}  @ ${price}")

    print("\nPress Ctrl-C to quit — ticker updates every few seconds.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--interval", type=float, default=2.0, help="Seconds between updates")
    p.add_argument("--cycles", type=int, default=0, help="Number of cycles to run (0 = infinite)")
    p.add_argument(
        "--gui",
        action="store_true",
        help="Use alternate-screen GUI mode (clears screen, hides cursor)",
    )
    p.add_argument(
        "--big",
        action="store_true",
        help="Emphasize header and numbers (bigger, bolder output)",
    )
    p.add_argument("--delta-up", type=float, default=0.5, help="Percent threshold for 'up' status")
    p.add_argument(
        "--delta-down",
        type=float,
        default=0.5,
        help="Percent threshold for 'down' status",
    )
    p.add_argument("--show-arrows", action="store_true", help="Show ▲/▼ next to Current")
    p.add_argument(
        "--gradient",
        action="store_true",
        help="Apply simple gradient background to Current cell based on delta",
    )
    args = p.parse_args()

    cycles = 0
    try:
        if args.gui:
            # Enter alternate screen and hide cursor
            sys.stdout.write(CSI + "?1049h")
            sys.stdout.write(CSI + "?25l")
            sys.stdout.flush()

        while True:
            budget = read_json_safe("budget_state.json")
            trades = read_json_safe("multi_signal_trades.json") or []
            # bind flags into render via kwargs
            render(
                budget,
                trades,
                big=args.big,
                delta_up=args.delta_up,
                delta_down=args.delta_down,
                show_arrows=args.show_arrows,
                gradient=args.gradient,
            )
            cycles += 1
            if args.cycles > 0 and cycles >= args.cycles:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if args.gui:
            # Restore cursor and exit alternate screen
            sys.stdout.write(CSI + "?25h")
            sys.stdout.write(CSI + "?1049l")
            sys.stdout.flush()
        print("\nTicker stopped")


if __name__ == "__main__":
    main()
