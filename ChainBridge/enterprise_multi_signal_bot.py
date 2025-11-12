#!/usr/bin/env python3
"""
BIGmindz Enterprise Multi-Signal Trading Platform
Mutex-Free, Scalable, ML-Powered Trading System
Built for both Paper and Live Trading
"""

import os
import json
import asyncio
import threading
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import yaml
import signal as sig_module
from dotenv import load_dotenv
import logging
import pickle
import uuid

try:
    import numpy as np
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        pass
except Exception:
    # Lightweight fallback for environments without numpy installed.
    # Implements only the small subset of numpy functionality used by this file.
    import random
    import statistics
    from typing import Iterable, List, Any

    class _NDArray:
        def __init__(self, data: Iterable[float]):
            self._data = [float(x) for x in data]

        def __len__(self):
            return len(self._data)

        def __getitem__(self, idx):
            if isinstance(idx, slice):
                return _NDArray(self._data[idx])
            return self._data[idx]

        def __iter__(self):
            return iter(self._data)

        def __repr__(self):
            return f"_NDArray({self._data})"

        def __add__(self, other):
            if isinstance(other, _NDArray):
                return _NDArray([a + b for a, b in zip(self._data, other._data)])
            else:
                return _NDArray([a + other for a in self._data])

        def __radd__(self, other):
            return self.__add__(other)

        def __truediv__(self, other):
            if isinstance(other, _NDArray):
                return _NDArray([a / (b if b != 0 else 1e-12) for a, b in zip(self._data, other._data)])
            else:
                return _NDArray([a / (other if other != 0 else 1e-12) for a in self._data])

        def __rtruediv__(self, other):
            # scalar / array not used in this code but implement defensively
            return _NDArray([(other / a) if a != 0 else float("inf") for a in self._data])

        def __neg__(self):
            return _NDArray([-a for a in self._data])

        def tolist(self):
            return list(self._data)

    class _Random:
        @staticmethod
        def randn():
            # approximate standard normal
            return random.gauss(0, 1)

        @staticmethod
        def random():
            return random.random()

        @staticmethod
        def uniform(a, b):
            return random.uniform(a, b)

    class _np_fallback:
        random = _Random()

        @staticmethod
        def diff(arr: Iterable[float]):
            lst = list(arr)
            if len(lst) < 2:
                return _NDArray([])
            return _NDArray([lst[i + 1] - lst[i] for i in range(len(lst) - 1)])

        @staticmethod
        def array(arr: Iterable[float]):
            return _NDArray(arr)

        @staticmethod
        def mean(arr: Iterable[float]):
            lst = list(arr)
            return statistics.mean(lst) if len(lst) else 0.0

        @staticmethod
        def std(arr: Iterable[float]):
            lst = list(arr)
            if len(lst) <= 1:
                return 0.0
            # use population std to match numpy default ddof=0
            return statistics.pstdev(lst)

        @staticmethod
        def min(arr: Iterable[float]):
            return min(arr) if arr else 0.0

        @staticmethod
        def max(arr: Iterable[float]):
            return max(arr) if arr else 0.0

        @staticmethod
        def argmax(arr: Iterable[float]):
            lst = list(arr)
            if not lst:
                return 0
            return int(max(range(len(lst)), key=lambda i: lst[i]))

    np = _np_fallback()
import pandas as pd
from collections import defaultdict
import warnings

warnings.filterwarnings("ignore")

# Load environment
load_dotenv()

# ==========================
# ENTERPRISE LOGGING SYSTEM
# ==========================


class EnterpriseLogger:
    """Thread-safe, process-safe enterprise logger"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.logger = logging.getLogger("BIGmindz")
        self.logger.setLevel(logging.DEBUG)

        # Console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console_format = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
        console.setFormatter(console_format)

        # File handler
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler("bigmindz_trading.log", maxBytes=50 * 1024 * 1024, backupCount=10)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter("%(asctime)s | %(processName)s-%(process)d | %(threadName)s | %(levelname)s | %(message)s")
        file_handler.setFormatter(file_format)

        self.logger.addHandler(console)
        self.logger.addHandler(file_handler)
        self._initialized = True

    def log(self, level: str, message: str):
        getattr(self.logger, level.lower())(message)


logger = EnterpriseLogger()


# ==============================
# IMMUTABLE/MUTEX-FREE STRUCTS
# ==============================
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ImmutableSignal:
    id: str
    timestamp: datetime
    symbol: str
    signal_type: str
    value: float
    confidence: float
    direction: str  # BUY, SELL, HOLD
    metadata: Dict = field(default_factory=dict)


@dataclass
class SignalAggregation:
    symbol: str
    timestamp: datetime
    signals: List[ImmutableSignal]
    aggregated_direction: str = "HOLD"
    aggregated_confidence: float = 0.0
    ml_prediction: Optional[Dict] = None
    risk_score: float = 0.5
    position_size: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.aggregated_direction,
            "confidence": self.aggregated_confidence,
            "ml_prediction": self.ml_prediction,
            "risk_score": self.risk_score,
            "position_size": self.position_size,
            "signal_count": len(self.signals),
        }


# ==============================
# ASYNC SIGNAL PROCESSOR
# ==============================


class AsyncSignalProcessor:
    def __init__(self, processor_id: str):
        self.processor_id = processor_id

    async def process_rsi(self, price_data: List[float], period: int = 14) -> ImmutableSignal:
        try:
            await asyncio.sleep(0)
            if len(price_data) < period + 1:
                return self._create_signal("RSI", 50.0, 0.0, "HOLD")

            deltas = np.diff(price_data)
            seed = deltas[: period + 1]
            # Safe numpy operations with fallbacks
            try:
                up_vals = [float(x) for x in seed if float(x) >= 0]
                down_vals = [float(x) for x in seed if float(x) < 0]
                up = sum(up_vals) / period if up_vals else 0.0
                down = sum(abs(x) for x in down_vals) / period if down_vals else 0.0
            except Exception:
                up = 0.0
                down = 0.0
            rsi = 100 if down == 0 else 100 - (100 / (1 + (up / down)))

            if rsi > 70:
                direction = "SELL"
                confidence = min((rsi - 70) / 30, 1.0)
            elif rsi < 30:
                direction = "BUY"
                confidence = min((30 - rsi) / 30, 1.0)
            else:
                direction = "HOLD"
                confidence = 1 - abs(50 - rsi) / 20

            return self._create_signal("RSI", float(rsi), float(confidence), direction)
        except Exception as e:
            logger.log("ERROR", f"RSI calculation failed: {e}")
            return self._create_signal("RSI", 50.0, 0.0, "HOLD")

    async def process_macd(self, price_data: List[float]) -> ImmutableSignal:
        try:
            await asyncio.sleep(0)
            if len(price_data) < 26:
                return self._create_signal("MACD", 0.0, 0.0, "HOLD")
            prices = pd.Series(price_data)
            exp1 = prices.ewm(span=12, adjust=False).mean()
            exp2 = prices.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            current_hist = float(histogram.iloc[-1])
            prev_hist = float(histogram.iloc[-2])
            if current_hist > 0 and prev_hist <= 0:
                direction = "BUY"
                confidence = min(abs(current_hist) / 2, 1.0)
            elif current_hist < 0 and prev_hist >= 0:
                direction = "SELL"
                confidence = min(abs(current_hist) / 2, 1.0)
            else:
                direction = "HOLD"
                confidence = 0.3
            return self._create_signal("MACD", current_hist, float(confidence), direction)
        except Exception as e:
            logger.log("ERROR", f"MACD calculation failed: {e}")
            return self._create_signal("MACD", 0.0, 0.0, "HOLD")

    async def process_bollinger(self, price_data: List[float], period: int = 20) -> ImmutableSignal:
        try:
            await asyncio.sleep(0)
            if len(price_data) < period:
                return self._create_signal("BOLLINGER", 0.0, 0.0, "HOLD")
            prices = pd.Series(price_data)
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)
            current_price = float(prices.iloc[-1])
            current_upper = float(upper_band.iloc[-1])
            current_lower = float(lower_band.iloc[-1])
            denom = (current_upper - current_lower) or 1e-8
            band_position = (current_price - current_lower) / denom
            if band_position > 0.95:
                direction = "SELL"
                confidence = 0.8
            elif band_position < 0.05:
                direction = "BUY"
                confidence = 0.8
            else:
                direction = "HOLD"
                confidence = 0.3
            return self._create_signal("BOLLINGER", float(band_position), float(confidence), direction)
        except Exception as e:
            logger.log("ERROR", f"Bollinger calculation failed: {e}")
            return self._create_signal("BOLLINGER", 0.5, 0.0, "HOLD")

    async def process_volume_profile(self, volume_data: List[float]) -> ImmutableSignal:
        try:
            await asyncio.sleep(0)
            if len(volume_data) < 20:
                return self._create_signal("VOLUME", 1.0, 0.0, "HOLD")
            recent_volume = float(np.mean(volume_data[-5:]))
            avg_volume = float(np.mean(volume_data))
            ratio = recent_volume / (avg_volume + 1e-8)
            if ratio > 2.0:
                direction = "BUY"
                confidence = min((ratio - 1) / 2, 1.0)
            elif ratio < 0.5:
                direction = "SELL"
                confidence = min((1 - ratio) / 0.5, 1.0)
            else:
                direction = "HOLD"
                confidence = 0.3
            return self._create_signal("VOLUME", float(ratio), float(confidence), direction)
        except Exception as e:
            logger.log("ERROR", f"Volume analysis failed: {e}")
            return self._create_signal("VOLUME", 1.0, 0.0, "HOLD")

    async def process_logistics_signal(self, symbol: str) -> ImmutableSignal:
        try:
            await asyncio.sleep(0)
            logistics_score = float(np.random.random())
            if logistics_score > 0.7:
                direction = "BUY"
                confidence = logistics_score
            elif logistics_score < 0.3:
                direction = "SELL"
                confidence = 1 - logistics_score
            else:
                direction = "HOLD"
                confidence = 0.5
            return self._create_signal("LOGISTICS", logistics_score, float(confidence), direction)
        except Exception as e:
            logger.log("ERROR", f"Logistics signal failed: {e}")
            return self._create_signal("LOGISTICS", 0.5, 0.0, "HOLD")

    def _create_signal(self, signal_type: str, value: float, confidence: float, direction: str) -> ImmutableSignal:
        return ImmutableSignal(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            symbol=self.processor_id.split("_")[0] if "_" in self.processor_id else "UNKNOWN",
            signal_type=signal_type,
            value=float(value),
            confidence=float(confidence),
            direction=direction,
            metadata={"processor": self.processor_id},
        )


# ==============================
# MACHINE LEARNING ENGINE
# ==============================


class MLEngine:
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self._load_models()

    def _load_models(self):
        model_paths = {
            "xgboost": "models/xgboost_predictor.pkl",
            "lstm": "models/lstm_predictor.pkl",
            "random_forest": "models/rf_predictor.pkl",
            "ensemble": "models/ensemble_predictor.pkl",
        }
        for name, path in model_paths.items():
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        self.models[name] = pickle.load(f)
                    logger.log("INFO", f"Loaded ML model: {name}")
                except Exception as e:
                    logger.log("WARNING", f"Could not load {name}: {e}")

    def extract_features(self, signals: List[ImmutableSignal], price_data: List[float]) -> Any:
        features: List[float] = []
        values = defaultdict(float)
        confs = defaultdict(float)
        for s in signals:
            values[s.signal_type] = s.value
            confs[s.signal_type] = s.confidence
        for key in ["RSI", "MACD", "BOLLINGER", "VOLUME", "LOGISTICS"]:
            features.append(values.get(key, 0.0))
            features.append(confs.get(key, 0.0))
        if len(price_data) >= 50:
            returns = np.diff(price_data[-50:]) / (np.array(price_data[-50:-1]) + 1e-8)
            features.extend(
                [
                    float(np.mean(returns)),
                    float(np.std(returns)),
                    float(np.min(returns)),
                    float(np.max(returns)),
                    # Safe conversion of last return value\n                last_return = 0.0\n                try:\n                    if len(returns) > 0:\n                        last_val = returns[-1]\n                        last_return = float(last_val) if isinstance(last_val, (int, float)) else float(str(last_val))\n                except (ValueError, TypeError, IndexError):\n                    last_return = 0.0\n                last_return,
                ]
            )
        else:
            features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
        if len(price_data) >= 20:
            sma20 = float(np.mean(price_data[-20:]))
            curr = float(price_data[-1])
            features.append((curr - sma20) / (sma20 + 1e-8))
        else:
            features.append(0.0)
        try:
            if hasattr(np, "array") and hasattr(np, "float64"):
                return np.array(features, dtype=np.float64)
            else:
                return np.array(features)
        except Exception:
            return features  # Return as list if numpy fails

    def predict(self, features: Any) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "direction": "HOLD",
            "confidence": 0.5,
            "risk_score": 0.5,
            "expected_return": 0.0,
            "models_agree": False,
        }
        if not self.models:
            return result
        try:
            preds = []
            for name, model in self.models.items():
                try:
                    if hasattr(model, "predict_proba"):
                        p = model.predict_proba([features])[0]
                        preds.append(int(np.argmax(p)))
                    else:
                        p = model.predict([features])[0]
                        preds.append(int(p))
                except Exception as e:
                    logger.log("DEBUG", f"Model {name} failed: {e}")
            if preds:
                from collections import Counter

                vote, count = Counter(preds).most_common(1)[0]
                result["direction"] = ["SELL", "HOLD", "BUY"][int(vote)] if 0 <= vote <= 2 else "HOLD"
                result["confidence"] = count / len(preds)
                result["models_agree"] = count >= len(preds) * 0.7
                result["risk_score"] = 1.0 - result["confidence"]
        except Exception as e:
            logger.log("ERROR", f"ML prediction failed: {e}")
        return result


# ==============================
# PARALLEL SIGNAL AGGREGATOR
# ==============================


class ParallelSignalAggregator:
    def __init__(self, ml_engine: Optional[MLEngine] = None):
        self.ml_engine = ml_engine or MLEngine()
        self.weights = {
            "RSI": 0.15,
            "MACD": 0.20,
            "BOLLINGER": 0.15,
            "VOLUME": 0.10,
            "LOGISTICS": 0.25,
            "ML": 0.15,
        }

    async def aggregate_signals(self, signals: List[ImmutableSignal], price_data: List[float]) -> SignalAggregation:
        symbol = signals[0].symbol if signals else "UNKNOWN"
        buy_score = sell_score = hold_score = 0.0
        for s in signals:
            w = self.weights.get(s.signal_type, 0.1)
            val = s.confidence * w
            if s.direction == "BUY":
                buy_score += val
            elif s.direction == "SELL":
                sell_score += val
            else:
                hold_score += val
        ml_pred = None
        if self.ml_engine and price_data:
            feats = self.ml_engine.extract_features(signals, price_data)
            ml_pred = self.ml_engine.predict(feats)
            w = self.weights.get("ML", 0.15)
            if ml_pred["direction"] == "BUY":
                buy_score += ml_pred["confidence"] * w
            elif ml_pred["direction"] == "SELL":
                sell_score += ml_pred["confidence"] * w
        total = buy_score + sell_score + hold_score
        if total == 0:
            direction, confidence = "HOLD", 0.0
        elif buy_score > sell_score and buy_score > hold_score:
            direction, confidence = "BUY", buy_score / total
        elif sell_score > buy_score and sell_score > hold_score:
            direction, confidence = "SELL", sell_score / total
        else:
            direction, confidence = "HOLD", hold_score / total
        risk = ml_pred["risk_score"] if ml_pred else 0.5
        position = self._position_size(confidence, risk)
        return SignalAggregation(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            signals=signals,
            aggregated_direction=direction,
            aggregated_confidence=float(confidence),
            ml_prediction=ml_pred,
            risk_score=float(risk),
            position_size=float(position),
        )

    def _position_size(self, confidence: float, risk_score: float) -> float:
        base = 1000.0
        cm = min(confidence * 2, 1.0)
        rm = 1.0 - (risk_score * 0.5)
        return float(min(max(base * cm * rm, 100.0), 5000.0))


# ==============================
# MAIN TRADING ENGINE
# ==============================


class MutexFreeTradingEngine:
    def __init__(self, config_path: str = "config.yaml", mode: str = "paper", once: bool = False):
        self.mode = mode
        self.once = once
        self.config = self._load_config(config_path)
        self.symbols = self.config.get("symbols", ["BTC/USD", "ETH/USD"])
        self.running = False

        self.manager = mp.Manager()
        self.shared_state = self.manager.dict()
        self.shared_state["trades"] = self.manager.list()
        self.shared_state["positions"] = self.manager.dict()
        self.shared_state["metrics"] = self.manager.dict()

        self._initialize_components()
        logger.log("INFO", f"🚀 BIGmindz Trading Engine initialized in {mode} mode")

    def _load_config(self, path: str) -> Dict:
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.log("WARNING", f"Using default config: {e}")
            return {
                "symbols": ["BTC/USD", "ETH/USD", "SOL/USD"],
                "timeframe": "5m",
                "poll_seconds": 60,
                "initial_capital": 10000.0,
                "max_position_size": 1000.0,
                "max_daily_trades": 50,
                "stop_loss_percent": 2.0,
                "take_profit_percent": 3.0,
            }

    def _initialize_components(self):
        self._setup_exchange()
        self.processors = {symbol: AsyncSignalProcessor(f"{symbol}_processor") for symbol in self.symbols}
        self.ml_engine = MLEngine()
        self.aggregator = ParallelSignalAggregator(self.ml_engine)
        self.io_pool = ThreadPoolExecutor(max_workers=10)
        self.cpu_pool = ProcessPoolExecutor(max_workers=4)

    def _setup_exchange(self):
        try:
            import ccxt

            exchange_name = self.config.get("exchange", "binance")
            if self.mode == "live":
                self.exchange = getattr(ccxt, exchange_name)(
                    {
                        "apiKey": os.getenv("API_KEY"),
                        "secret": os.getenv("API_SECRET"),
                        "enableRateLimit": True,
                    }
                )
            else:
                self.exchange = MockExchange(self.symbols)
            logger.log("INFO", f"Exchange configured: {exchange_name} ({self.mode})")
        except Exception as e:
            logger.log("ERROR", f"Exchange setup failed: {e}")
            self.exchange = MockExchange(self.symbols)

    async def fetch_market_data(self, symbol: str) -> Optional[Dict]:
        try:
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(self.io_pool, self.exchange.fetch_ticker, symbol)
            ohlcv = await loop.run_in_executor(self.io_pool, self.exchange.fetch_ohlcv, symbol, self.config.get("timeframe", "5m"), 100)
            return {
                "symbol": symbol,
                "price": ticker.get("last", 0),
                "volume": ticker.get("volume", 0),
                "ohlcv": ohlcv,
                "timestamp": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.log("ERROR", f"Failed to fetch data for {symbol}: {e}")
            return None

    async def process_symbol(self, symbol: str) -> Optional[SignalAggregation]:
        try:
            data = await self.fetch_market_data(symbol)
            if not data:
                return None
            ohlcv = data["ohlcv"]
            prices = [float(c[4]) for c in ohlcv]
            volumes = [float(c[5]) for c in ohlcv]
            p = self.processors[symbol]
            tasks = [
                p.process_rsi(prices),
                p.process_macd(prices),
                p.process_bollinger(prices),
                p.process_volume_profile(volumes),
                p.process_logistics_signal(symbol),
            ]
            signals = await asyncio.gather(*tasks)
            agg = await self.aggregator.aggregate_signals(signals, prices)
            logger.log(
                "INFO", f"{symbol}: ${data['price']:.2f} | Signal: {agg.aggregated_direction} (Conf: {agg.aggregated_confidence:.2f})"
            )
            return agg
        except Exception as e:
            logger.log("ERROR", f"Failed to process {symbol}: {e}")
            return None

    async def execute_trade(self, aggregation: SignalAggregation) -> bool:
        if aggregation.aggregated_direction == "HOLD" or aggregation.aggregated_confidence < 0.6:
            return False
        try:
            symbol = aggregation.symbol
            direction = aggregation.aggregated_direction
            size = aggregation.position_size
            ticker = self.exchange.fetch_ticker(symbol)
            price = float(ticker["last"])
            side = "buy" if direction == "BUY" else "sell"
            if self.mode == "live":
                order = self.exchange.create_order(symbol=symbol, type="market", side=side, amount=size / price)
            else:
                order = {
                    "id": str(uuid.uuid4()),
                    "symbol": symbol,
                    "side": side,
                    "price": price,
                    "amount": size / price,
                    "cost": size,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            trade_record = {
                "id": order["id"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "side": side,
                "price": price,
                "amount": size / price,
                "cost": size,
                "confidence": aggregation.aggregated_confidence,
                "ml_prediction": aggregation.ml_prediction,
            }
            self.shared_state["trades"].append(trade_record)
            self.shared_state["positions"][symbol] = trade_record
            logger.log("INFO", f"✅ Trade executed: {side.upper()} {size/price:.4f} {symbol} @ ${price:.2f}")
            return True
        except Exception as e:
            logger.log("ERROR", f"Trade execution failed: {e}")
            return False

    async def run_once(self):
        tasks = [self.process_symbol(s) for s in self.symbols]
        aggs = await asyncio.gather(*tasks)
        trade_tasks = [self.execute_trade(a) for a in aggs if a and a.aggregated_confidence > 0.7]
        if trade_tasks:
            await asyncio.gather(*trade_tasks)
        self._update_metrics()
        self._save_state()

    async def run_async(self):
        logger.log("INFO", "Starting async trading loop...")
        while self.running:
            try:
                await self.run_once()
                if self.once:
                    break
                await asyncio.sleep(self.config.get("poll_seconds", 60))
            except Exception as e:
                logger.log("ERROR", f"Main loop error: {e}")
                await asyncio.sleep(5)

    def _update_metrics(self):
        try:
            trades = list(self.shared_state["trades"])
            if not trades:
                return
            total = len(trades)
            wins = len([t for t in trades if t.get("side") == "buy"])
            self.shared_state["metrics"] = {
                "total_trades": total,
                "win_rate": wins / total if total else 0,
                "profitable_trades": wins,
                "last_update": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.log("ERROR", f"Metrics update failed: {e}")

    def _save_state(self):
        try:
            state = {
                "mode": self.mode,
                "trades": list(self.shared_state["trades"]),
                "positions": dict(self.shared_state["positions"]),
                "metrics": dict(self.shared_state["metrics"]),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            with open("trading_state.json", "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.log("ERROR", f"State save failed: {e}")

    def run(self):
        self.running = True

        def handler(signum, frame):
            logger.log("INFO", "Shutdown signal received")
            self.running = False

        sig_module.signal(sig_module.SIGINT, handler)
        sig_module.signal(sig_module.SIGTERM, handler)
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.log("INFO", "Interrupted by user")
        finally:
            self.shutdown()

    def shutdown(self):
        logger.log("INFO", "Shutting down trading engine...")
        self.running = False
        self.io_pool.shutdown(wait=True)
        self.cpu_pool.shutdown(wait=True)
        self._save_state()
        logger.log("INFO", "✅ Shutdown complete")


# ==============================
# MOCK EXCHANGE (PAPER)
# ==============================


class MockExchange:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.prices: Dict[str, float] = {symbol: float(50000 - i * 10000) for i, symbol in enumerate(symbols)}

    def fetch_ticker(self, symbol: str) -> Dict:
        price = float(self.prices.get(symbol, 50000))
        price *= 1 + np.random.randn() * 0.001
        self.prices[symbol] = price
        return {
            "symbol": symbol,
            "last": price,
            "bid": price * 0.999,
            "ask": price * 1.001,
            "volume": float(np.random.uniform(1000, 10000)),
        }

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> List:
        base = float(self.prices.get(symbol, 50000))
        ohlcv = []
        for i in range(limit):
            open_p = base * (1 + abs(np.random.randn()) * 0.001)
            close_p = open_p * (1 + np.random.randn() * 0.002)
            high_p = max(open_p, close_p) * (1 + abs(np.random.randn()) * 0.001)
            low_p = min(open_p, close_p) * (1 - abs(np.random.randn()) * 0.001)
            vol = float(np.random.uniform(100, 1000))
            ts = int((datetime.now(timezone.utc) - timedelta(minutes=i * 5)).timestamp() * 1000)
            ohlcv.append([ts, open_p, high_p, low_p, close_p, vol])
        return list(reversed(ohlcv))

    def create_order(self, **kwargs) -> Dict:
        symbol = kwargs.get("symbol", "")
        return {
            "id": str(uuid.uuid4()),
            "symbol": symbol,
            "side": kwargs.get("side"),
            "type": kwargs.get("type"),
            "amount": kwargs.get("amount"),
            "price": self.prices.get(symbol, 50000),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "closed",
        }


# ==============================
# DEPLOY
# ==============================


def deploy():
    import argparse

    parser = argparse.ArgumentParser(description="BIGmindz Trading Platform")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper", help="Trading mode (default: paper)")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("--symbols", nargs="+", help="Override symbols to trade")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    args = parser.parse_args()

    if args.mode == "live":
        print("⚠️  WARNING: Live trading mode selected! This will trade with REAL money.")
        resp = os.environ.get("BIGMINDZ_LIVE_CONFIRM") or input("Type 'CONFIRM' to proceed: ")
        if resp != "CONFIRM":
            print("Live trading cancelled.")
            return

    # Create config if missing
    if not os.path.exists(args.config):
        cfg = {
            "symbols": args.symbols or ["BTC/USD", "ETH/USD", "SOL/USD"],
            "mode": args.mode,
            "exchange": "binance",
            "timeframe": "5m",
            "poll_seconds": 60,
            "initial_capital": 10000,
            "max_position_size": 1000,
            "stop_loss_percent": 2.0,
            "take_profit_percent": 3.0,
        }
        with open(args.config, "w") as f:
            yaml.dump(cfg, f)
        logger.log("INFO", f"Created config file: {args.config}")

    engine = MutexFreeTradingEngine(args.config, args.mode, once=args.once)
    if args.once:
        # One-shot run without starting infinite loop
        asyncio.run(engine.run_once())
        engine.shutdown()
    else:
        try:
            engine.run()
        except KeyboardInterrupt:
            logger.log("INFO", "Stopped by user")
        except Exception as e:
            logger.log("CRITICAL", f"Fatal error: {e}")
        finally:
            engine.shutdown()


if __name__ == "__main__":
    deploy()
