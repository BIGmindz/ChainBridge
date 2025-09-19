Live Ticker README
===================

This folder provides two CLI tickers to monitor `budget_state.json` and
`multi_signal_trades.json` locally.

1) Plain ANSI ticker (no external deps)
--------------------------------------
File: `scripts/live_ticker.py`

Usage:

```bash
# Run indefinitely, update every second
python3 scripts/live_ticker.py --interval 1

# Run for 10 cycles and exit
python3 scripts/live_ticker.py --interval 0.5 --cycles 10

# Bigger header if you have pyfiglet installed
pip install pyfiglet
python3 scripts/live_ticker.py --big --interval 1
```

2) Rich-based ticker (recommended for larger/bolder P&L)
--------------------------------------------------------
File: `scripts/live_ticker_rich.py`

Requirements:

```bash
pip install rich
```

Usage:

```bash
# Run with big P&L emphasis
python3 scripts/live_ticker_rich.py --big --interval 1

# Run a short demo
python3 scripts/live_ticker_rich.py --big --interval 0.5 --cycles 4
```

Notes and tips
--------------
- The rich ticker provides better typography and clean numeric alignment. It is the recommended option if running locally in a terminal.
- Both tickers read `budget_state.json` and `multi_signal_trades.json` in the working directory. Ensure those files are up-to-date (the main bot saves them after runs).
- For production monitoring, consider running the rich ticker inside `tmux` or `screen`, or forwarding to a terminal multiplexer in your monitoring host.
- If you want the P&L numbers extremely large, consider using `pyfiglet` to render the single P&L value; I can add that as an option if you want big per-row numbers.


New CLI flags (both tickers)

--------------------------------------

- `--delta-up <float>`: percent threshold to mark a position as "up" (default `0.5`).
- `--delta-down <float>`: percent threshold to mark a position as "down" (default `0.5`).
- `--show-arrows`: show `▲`/`▼` next to the Current column to indicate direction.
- `--gradient`: apply a stronger background/ emphasis for larger deltas (plain ticker approximates with ANSI background; rich ticker uses richer styling).
- `--big`: (plain ticker) larger header with optional `pyfiglet`; (rich ticker) bolder P&L/header.


Examples

--------------------------------------

Plain ticker: arrows + gradient, 1s updates

```bash
python3 scripts/live_ticker.py --interval 1 --show-arrows --gradient
```

Plain ticker: tune thresholds to 1% up/down

```bash
python3 scripts/live_ticker.py --interval 1 --show-arrows --delta-up 1.0 --delta-down 1.0
```

Rich ticker: big header, arrows, gradient

```bash
pip install rich
python3 scripts/live_ticker_rich.py --big --interval 1 --show-arrows --gradient
```


Configuration notes

--------------------------------------

- Thresholds are percentages (e.g., `0.5` == 0.5%). Increase them if you want less sensitivity to small moves.
- The plain ticker uses ANSI approximations for gradient; the rich ticker supports richer color/background styles and is recommended for the best visual output.
