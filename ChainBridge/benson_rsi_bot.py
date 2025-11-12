# -*- coding: utf-8 -*-

import argparse
from typing import Any, List

try:
    import pandas as pd  # type: ignore

    has_pandas = True
except Exception:  # pragma: no cover - optional dependency in test environments
    # Minimal pandas shim so tests can call pd.Series([...]) when pandas
    # isn't installed in the environment. The shim produces a plain list-like
    # object which the fallback wilder_rsi implementation accepts.
    class _SeriesFallback(list[float]):
        def __init__(self, data: Any, *args: Any, **kwargs: Any) -> None:
            super().__init__(data)

        def astype(self, *_args: Any, **_kwargs: Any) -> "_SeriesFallback":
            return self

        def tolist(self) -> List[float]:  # type: ignore
            return list(self)  # type: ignore

    class _PdShim:
        Series = _SeriesFallback

    pd = _PdShim()
    has_pandas = False
import math
import os
import signal
import time  # noqa: F401
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # type: ignore

    has_yaml = True
except Exception:  # pragma: no cover - optional dependency in test environments
    yaml = None  # type: ignore
    has_yaml = False

import json
from typing import Dict, Tuple

"""
Benson RSI Bot (Coinbase-friendly)
- Config: config/config.yaml  (override with BENSON_CONFIG env var)
- Prints BUY/SELL/HOLD based on RSI
- Ctrl+C exits cleanly
- Flags:
    --once  : one cycle then exit
    --test  : run unit tests then exit
"""

# --------------------
# Helpers
# --------------------


def load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found at {path}")
    with open(path, "r") as f:
        content = f.read()
    # Substitute environment variables in the config content
    content = os.path.expandvars(content)
    if has_yaml and yaml is not None:
        return yaml.safe_load(content) or {}
    # Fallback: try JSON as a strict subset of YAML for tests
    try:
        return json.loads(content)
    except Exception:
        return {}


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")


def wilder_rsi(close: Any, length: int = 14) -> float:
    """Wilder's RSI. Accepts a pandas Series when available, or any sequence of floats.

    Args:
        close: Price series as pandas.Series or sequence of floats
        length: RSI period (default 14)

    Returns:
        float: RSI value between 0 and 100

    Raises:
        ValueError: If input data is invalid or insufficient
    """
    import math

    # Validate period
    if length < 1:
        raise ValueError("Period must be positive")

    # Normalize input to a list of floats
    try:
        if "has_pandas" in globals() and has_pandas and isinstance(close, pd.Series):
            vals = close.astype("float64").tolist()  # type: ignore
        else:
            vals = [float(x) for x in list(close)]  # type: ignore
    except (ValueError, TypeError):
        raise ValueError("Input must be numeric values")

    # Check for NaN values
    if any(math.isnan(x) for x in vals):  # type: ignore
        raise ValueError("Input contains NaN values")

    # Validate data length
    if len(vals) < max(2, length + 1):
        raise ValueError(f"Insufficient data for RSI calculation (need at least {length + 1} values)")

    # Compute price deltas
    deltas = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [(-d) if d < 0 else 0.0 for d in deltas]

    if len(gains) < length:
        return float("nan")  # type: ignore

    # Initial average gains/losses (simple average of first 'period' values)
    avg_gain = sum(gains[:length]) / length  # type: ignore
    avg_loss = sum(losses[:length]) / length  # type: ignore

    # Wilder smoothing for remaining values
    for i in range(length, len(gains)):
        gain = gains[i]
        loss = losses[i]
        avg_gain = (avg_gain * (length - 1) + gain) / length
        avg_loss = (avg_loss * (length - 1) + loss) / length

    # Defensive cases
    if avg_loss == 0 and avg_gain == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))  # type: ignore


def calculate_rsi_from_ohlcv(ohlcv: List[List[float]], period: int) -> float:
    """OHLCV rows: [ts, open, high, low, close, volume]."""
    if not ohlcv:
        return float("nan")  # type: ignore
    closes = [row[4] for row in ohlcv if len(row) >= 5]
    series = pd.Series(closes, dtype=float)
    if len(series) < period + 5:
        return float("nan")  # type: ignore
    return wilder_rsi(series, length=period)


def _ema(series: List[float], period: int) -> float:
    """Compute the latest EMA value for a series with given period.

    Returns None if insufficient data.
    """
    if period <= 0:
        return 0.0
    if len(series) < period:
        return 0.0
    k = 2.0 / (period + 1.0)
    ema_val = sum(series[:period]) / period  # seed with SMA  # type: ignore
    for x in series[period:]:
        ema_val = (x - ema_val) * k + ema_val
    return float(ema_val)  # type: ignore


def calculate_macd_from_ohlcv(ohlcv: List[List[float]], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
    """Return (macd_line, signal_line, histogram). NaNs (float('nan')) when insufficient data.  # type: ignore

    Uses EMA with standard smoothing. Requires at least slow+signal values for stability.
    """
    if not ohlcv:
        return float("nan"), float("nan"), float("nan")  # type: ignore
    closes = [float(row[4]) for row in ohlcv if len(row) >= 5]  # type: ignore
    if len(closes) < max(slow + signal, slow + 5):
        return float("nan"), float("nan"), float("nan")  # type: ignore

    # Compute full EMA series for MACD stability
    def ema_series(vals: List[float], period: int) -> List[float]:
        if len(vals) < period:
            return []
        k = 2.0 / (period + 1.0)
        out: List[float] = []
        ema_val = sum(vals[:period]) / period  # type: ignore
        out.extend([float("nan")] * (period - 1))  # type: ignore
        out.append(float(ema_val))  # type: ignore
        for x in vals[period:]:
            ema_val = (x - ema_val) * k + ema_val
            out.append(float(ema_val))  # type: ignore
        return out

    fast_ema = ema_series(closes, fast)
    slow_ema = ema_series(closes, slow)
    if not fast_ema or not slow_ema:
        return float("nan"), float("nan"), float("nan")  # type: ignore
    macd_line_series = []
    for i in range(len(closes)):
        fe = fast_ema[i] if i < len(fast_ema) else float("nan")  # type: ignore
        se = slow_ema[i] if i < len(slow_ema) else float("nan")  # type: ignore
        if math.isnan(fe) or math.isnan(se):  # type: ignore
            macd_line_series.append(float("nan"))  # type: ignore
        else:
            macd_line_series.append(fe - se)  # type: ignore

    signal_series = []
    # Build signal EMA over macd_line_series (ignore leading NaNs)
    macd_clean = [x for x in macd_line_series if not math.isnan(x)]  # type: ignore
    if len(macd_clean) < signal:
        return float("nan"), float("nan"), float("nan")  # type: ignore
    k = 2.0 / (signal + 1.0)
    sig_val = sum(macd_clean[:signal]) / signal  # type: ignore
    # align signal_series lengths with macd_line_series by pre-padding NaNs
    leading_nans = len(macd_line_series) - len(macd_clean)
    signal_series.extend([float("nan")] * (leading_nans + signal - 1))  # type: ignore
    signal_series.append(float(sig_val))  # type: ignore
    for x in macd_clean[signal:]:
        sig_val = (x - sig_val) * k + sig_val
        signal_series.append(float(sig_val))  # type: ignore

    macd_line = macd_line_series[-1]
    signal_line = signal_series[-1] if signal_series else float("nan")  # type: ignore
    hist = macd_line - signal_line if not (math.isnan(macd_line) or math.isnan(signal_line)) else float("nan")  # type: ignore
    return float(macd_line), float(signal_line), float(hist)  # type: ignore


def calculate_bollinger_from_ohlcv(ohlcv: List[List[float]], period: int = 20, stddev: float = 2.0) -> Tuple[float, float, float]:
    """Return (lower, middle, upper) Bollinger Band values for the latest close.

    Returns NaNs when insufficient data.
    """
    if not ohlcv:
        return float("nan"), float("nan"), float("nan")  # type: ignore
    closes = [float(row[4]) for row in ohlcv if len(row) >= 5]  # type: ignore
    if len(closes) < period:
        return float("nan"), float("nan"), float("nan")  # type: ignore
    window = closes[-period:]
    mean = sum(window) / period  # type: ignore
    # population stddev to match many TA libs' default behavior
    var = sum((x - mean) ** 2 for x in window) / period  # type: ignore
    sd = math.sqrt(var)
    lower = mean - stddev * sd
    upper = mean + stddev * sd
    return float(lower), float(mean), float(upper)  # type: ignore


def backoff_sleep(attempt: int, base: float = 2.0, max_wait: float = 60.0):
    wait = min(max_wait, base ** max(1, attempt))
    time.sleep(wait)


def safe_fetch_ohlcv(exchange: Any, symbol: str, timeframe: str, limit: int = 200) -> Any:
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)


def safe_fetch_ticker(exchange: Any, symbol: str) -> float:
    t = exchange.fetch_ticker(symbol)
    price = t.get("last") or t.get("close") or t.get("bid") or t.get("ask")
    if price is None:
        raise RuntimeError(f"No price in ticker for {symbol}")
    return float(price)  # type: ignore


# --------------------
# Main bot
# --------------------


def run_bot(once: bool = False) -> None:
    print("[DBG] entered run_bot()")
    try:
        import ccxt  # type: ignore
    except Exception as exc:
        raise ImportError("The 'ccxt' package is required to run the live bot. Install with: pip install ccxt") from exc

    # Load .env (repo root or home) so EXCHANGE, PAPER, API_KEY, API_SECRET are available
    try:
        from dotenv import load_dotenv  # type: ignore

        loaded_env = False
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print("[ENV] Loaded .env from repo root")
            loaded_env = True
        home_env = Path.home() / ".env"
        if not loaded_env and home_env.exists():
            load_dotenv(dotenv_path=home_env)
            print("[ENV] Loaded .env from home directory")
    except Exception:
        pass

    config_path = os.getenv("BENSON_CONFIG", "config/config.yaml")
    if not os.path.exists(config_path):
        alt = "config.yaml"
        if os.path.exists(alt):
            config_path = alt
    print(f"[CFG] Using config at: {config_path}")
    cfg = load_config(config_path)

    # Prefer EXCHANGE env if provided
    try:
        import ccxt  # type: ignore
    except Exception:
        raise

    exchange_id = str(os.getenv("EXCHANGE", cfg.get("exchange", "coinbase"))).lower()
    if not hasattr(ccxt, exchange_id):
        raise ValueError(f"Unknown exchange id '{exchange_id}' — check your config")

    exchange_cls = getattr(ccxt, exchange_id)
    exchange = exchange_cls({"enableRateLimit": True})

    # Load markets and validate symbols
    exchange.load_markets()
    symbols = list(cfg.get("symbols", []))  # type: ignore
    if not symbols:
        symbols = ["BTC/USD", "ETH/USD"]

    invalid = [s for s in symbols if s not in exchange.symbols]
    if invalid:
        raise ValueError(f"Invalid symbols for {exchange_id}: {invalid}")

    timeframe = str(cfg.get("timeframe", "5m"))
    # RSI config
    rsi_cfg = dict(cfg.get("rsi", {}))
    rsi_period = int(rsi_cfg.get("period", 14))
    # Canonical RSI thresholds enforced (fallbacks 35/64 if config absent)
    buy_th = float(rsi_cfg.get("buy_threshold", 35))  # type: ignore
    sell_th = float(rsi_cfg.get("sell_threshold", 64))  # type: ignore
    # MACD config
    macd_cfg = dict(cfg.get("macd", {}))
    macd_fast = int(macd_cfg.get("fast", 12))
    macd_slow = int(macd_cfg.get("slow", 26))
    macd_signal_p = int(macd_cfg.get("signal", 9))
    macd_hist_th = float(macd_cfg.get("hist_threshold", 0.0))  # type: ignore
    # Bollinger config
    bb_cfg = dict(cfg.get("bollinger", {}))
    bb_period = int(bb_cfg.get("period", 20))
    bb_std = float(bb_cfg.get("stddev", 2.0))  # type: ignore
    # Signal toggles and decision policy
    sig_cfg = dict(cfg.get("signals", {}))
    use_rsi = bool(sig_cfg.get("use_rsi", True))
    use_macd = bool(sig_cfg.get("use_macd", True))
    use_boll = bool(sig_cfg.get("use_bollinger", True))
    dec_cfg = dict(cfg.get("decision", {}))
    mode = str(dec_cfg.get("mode", "consensus"))  # consensus|any
    consensus_min = int(dec_cfg.get("consensus_min", 2))

    cooldown_min = int(cfg.get("cooldown_minutes", 10))
    poll_seconds = int(cfg.get("poll_seconds", 60))
    log_path = str(cfg.get("csv_log", "benson_signals.csv"))

    last_signal = {s: "HOLD" for s in symbols}
    last_alert_ts = {s: 0.0 for s in symbols}
    cooldown_sec = cooldown_min * 60

    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("ts_utc,exchange,symbol,price,rsi,macd_hist,bb_pos,signal,timeframe\n")

    print("Benson Bot Starting...")
    print(f"Exchange: {exchange_id}")
    print(f"Monitoring ({len(symbols)}): {symbols}")
    print(f"Timeframe: {timeframe}")
    print(f"RSI: period={rsi_period} | Buy<{buy_th} | Sell>{sell_th}")
    if use_macd:
        print(f"MACD: fast={macd_fast} slow={macd_slow} signal={macd_signal_p} | hist_th={macd_hist_th}")
    if use_boll:
        print(f"Bollinger: period={bb_period} std={bb_std}")
    print(f"Cooldown: {cooldown_min} min")
    print("-" * 60)

    stop = {"flag": False}

    def handle_sigint(sig: int, frame: Any) -> None:
        stop["flag"] = True
        print("\nStopping gracefully...")

    signal.signal(signal.SIGINT, handle_sigint)

    attempt = 0

    while not stop["flag"]:
        try:
            for symbol in symbols:
                ohlcv = safe_fetch_ohlcv(exchange, symbol, timeframe, limit=300)
                price = safe_fetch_ticker(exchange, symbol)

                # Compute indicators
                rsi_val = calculate_rsi_from_ohlcv(ohlcv, rsi_period)
                # Calculate MACD indicators

                macd_line, macd_sig, macd_hist = calculate_macd_from_ohlcv(ohlcv, fast=macd_fast, slow=macd_slow, signal=macd_signal_p)
                bb_lower, bb_mid, bb_upper = calculate_bollinger_from_ohlcv(ohlcv, period=bb_period, stddev=bb_std)

                # Individual signals
                ind_signals: Dict[str, str] = {}
                if use_rsi:
                    if isinstance(rsi_val, float) and not math.isnan(rsi_val):  # type: ignore
                        if rsi_val < buy_th:
                            ind_signals["RSI"] = "BUY"
                        elif rsi_val > sell_th:
                            ind_signals["RSI"] = "SELL"
                        else:
                            ind_signals["RSI"] = "HOLD"
                    else:
                        ind_signals["RSI"] = "HOLD"

                if use_macd:
                    if not (math.isnan(macd_hist)):  # type: ignore
                        if macd_hist > macd_hist_th:
                            ind_signals["MACD"] = "BUY"
                        elif macd_hist < -macd_hist_th:
                            ind_signals["MACD"] = "SELL"
                        else:
                            ind_signals["MACD"] = "HOLD"
                    else:
                        ind_signals["MACD"] = "HOLD"

                if use_boll:
                    if not (math.isnan(bb_lower) or math.isnan(bb_upper)):  # type: ignore
                        if price <= bb_lower:
                            ind_signals["BOLL"] = "BUY"
                        elif price >= bb_upper:
                            ind_signals["BOLL"] = "SELL"
                        else:
                            ind_signals["BOLL"] = "HOLD"
                    else:
                        ind_signals["BOLL"] = "HOLD"

                # Aggregate decision
                buys = sum(1 for s in ind_signals.values() if s == "BUY")  # type: ignore
                sells = sum(1 for s in ind_signals.values() if s == "SELL")  # type: ignore
                # Track enabled indicators for confidence calculation

                total_enabled = len(ind_signals)

                print(f"Total enabled indicators: {total_enabled}")
                signal_out = "HOLD"
                if mode == "any":
                    if buys > 0 and buys >= sells:
                        signal_out = "BUY"
                    elif sells > 0 and sells > buys:
                        signal_out = "SELL"
                else:  # consensus
                    if buys >= consensus_min and buys > sells:
                        signal_out = "BUY"
                    elif sells >= consensus_min and sells > buys:
                        signal_out = "SELL"

                now = time.time()
                cooldown_ok = (now - last_alert_ts[symbol]) >= cooldown_sec
                changed = signal_out != last_signal[symbol]

                # Status line
                rsi_txt = f"RSI {rsi_val:5.2f}" if isinstance(rsi_val, float) and not math.isnan(rsi_val) else "RSI  n/a"  # type: ignore
                macd_txt = f"MACD {macd_hist:5.2f}" if not (math.isnan(macd_hist)) else "MACD  n/a"  # type: ignore
                bb_txt = (
                    f"BB [{bb_lower:.2f},{bb_mid:.2f},{bb_upper:.2f}]"
                    if not (math.isnan(bb_lower) or math.isnan(bb_mid) or math.isnan(bb_upper))  # type: ignore
                    else "BB n/a"
                )
                print(
                    f"[{utc_now_str()}] {symbol:>10}: ${price:,.2f} | {rsi_txt} | {macd_txt} | {bb_txt} | {signal_out}"
                    f"{' (new)' if changed else ''}"
                )

                # Alert only on new actionable signals and respecting cooldown
                if signal_out in ("BUY", "SELL") and changed and cooldown_ok:
                    print(f"SIGNAL: {signal_out} {symbol} @ ${price:,.2f} (RSI {rsi_val:0.2f})")
                    last_alert_ts[symbol] = now

                # Persist log line (include MACD and Bollinger summaries)
                with open(log_path, "a") as f:
                    rsi_str = f"{rsi_val:.4f}" if isinstance(rsi_val, float) and not math.isnan(rsi_val) else ""  # type: ignore
                    macd_str = f"{macd_hist:.4f}" if not math.isnan(macd_hist) else ""  # type: ignore
                    bbpos = ""
                    if not (math.isnan(bb_lower) or math.isnan(bb_upper)) and (bb_upper - bb_lower) > 0:  # type: ignore
                        bbpos_val = (price - bb_lower) / (bb_upper - bb_lower)
                        bbpos = f"{bbpos_val:.4f}"
                    f.write(f"{utc_now_str()},{exchange_id},{symbol},{price},{rsi_str},{macd_str},{bbpos},{signal_out},{timeframe}\n")

                last_signal[symbol] = signal_out

            attempt = 0
            if once:
                break
            print("-" * 60)
            time.sleep(poll_seconds)

        except Exception as e:
            attempt += 1
            print(f"Error (attempt {attempt}): {type(e).__name__}: {e}")
            backoff_sleep(attempt)

    print("Exit complete. Logs saved to:", log_path)


# --------------------
# CLI entrypoint
# --------------------


def main():
    print("[DBG] entered main()")
    parser = argparse.ArgumentParser(description="Benson RSI Bot")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--test", action="store_true", help="Run unit tests and exit")
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    run_bot(once=args.once)


# --------------------
# Tests
# --------------------


def test_rsi_flatline():
    s = pd.Series([100] * 20, dtype=float)
    rsi = wilder_rsi(s, 14)
    assert 45 <= rsi <= 55, f"Expected RSI near 50, got {rsi}"


def test_rsi_uptrend():
    s = pd.Series(range(1, 30), dtype=float)
    rsi = wilder_rsi(s, 14)
    assert rsi > 60, f"Expected RSI > 60, got {rsi}"


def test_rsi_downtrend():
    s = pd.Series(range(30, 1, -1), dtype=float)
    rsi = wilder_rsi(s, 14)
    assert rsi < 40, f"Expected RSI < 40, got {rsi}"


def test_rsi_no_losses_near_max():
    s = pd.Series(range(1, 60), dtype=float)
    rsi = wilder_rsi(s, 14)
    assert rsi >= 95 or math.isclose(rsi, 100.0, rel_tol=0.01), f"Expected RSI near 100, got {rsi}"


def test_insufficient_ohlcv_returns_nan():
    short_ohlcv: List[List[float]] = [[0, 0, 0, 0, 100.0, 0.0] for _ in range(10)]
    rsi_val = calculate_rsi_from_ohlcv(short_ohlcv, period=14)
    assert isinstance(rsi_val, float) and math.isnan(rsi_val), f"Expected NaN, got {rsi_val}"  # type: ignore


def run_tests():
    tests = [
        test_rsi_flatline,
        test_rsi_uptrend,
        test_rsi_downtrend,
        test_rsi_no_losses_near_max,
        test_insufficient_ohlcv_returns_nan,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as ae:
            failures += 1
            print(f"FAIL: {t.__name__}: {ae}")
        except Exception as e:
            failures += 1
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
    if failures:
        raise SystemExit(f"Tests failed: {failures}")
    print("All tests passed.")


# Canonical RSI thresholds (centralized)
RSI_BUY_THRESHOLD = 35
RSI_SELL_THRESHOLD = 64


if __name__ == "__main__":
    main()
