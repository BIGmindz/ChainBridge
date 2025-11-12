"""
Enterprise Observability Stack
Structured logging, Prometheus metrics, and distributed tracing
"""

import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from contextlib import contextmanager
from functools import wraps

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not installed. Metrics disabled. Install with: pip install prometheus-client")


class StructuredLogger:
    """Structured JSON logger for ELK stack"""

    def __init__(self, name: str, log_file: Optional[Path] = None):
        self.logger = logging.getLogger(name)
        self.log_file = log_file or Path(f"logs/{name}.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure handler
        handler = logging.FileHandler(self.log_file)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _log(self, level: str, message: str, **kwargs):
        """Log structured JSON message"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            "logger": self.logger.name,
            **kwargs,
        }

        self.logger.log(getattr(logging, level.upper()), json.dumps(log_entry))

    def info(self, message: str, **kwargs):
        self._log("info", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log("warning", message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log("error", message, **kwargs)

    def debug(self, message: str, **kwargs):
        self._log("debug", message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log("critical", message, **kwargs)


class TradingMetrics:
    """Prometheus metrics for trading bot"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled and PROMETHEUS_AVAILABLE

        if not self.enabled:
            return

        # Trading Metrics
        self.orders_total = Counter("bot_orders_total", "Total orders placed", ["side", "symbol", "status"])

        self.order_latency = Histogram("bot_order_latency_seconds", "Order placement latency", buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0])

        self.capital_utilization = Gauge("bot_capital_utilization_pct", "Percentage of capital deployed")

        self.realized_pnl = Gauge("bot_realized_pnl_usd", "Realized profit and loss in USD")

        self.unrealized_pnl = Gauge("bot_unrealized_pnl_usd", "Unrealized profit and loss in USD")

        self.active_positions = Gauge("bot_active_positions", "Number of open positions")

        # Signal Metrics
        self.signal_generation_time = Histogram(
            "bot_signal_generation_seconds", "Time to generate signals", ["module"], buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )

        self.signal_confidence = Histogram(
            "bot_signal_confidence",
            "Signal confidence distribution",
            ["module", "signal_type"],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )

        self.signal_errors = Counter("bot_signal_errors_total", "Signal generation errors", ["module", "error_type"])

        # System Health
        self.exchange_api_errors = Counter("bot_exchange_api_errors_total", "Exchange API errors", ["exchange", "endpoint", "status_code"])

        self.circuit_breaker_state = Gauge(
            "bot_circuit_breaker_state", "Circuit breaker state (0=closed, 1=half-open, 2=open)", ["endpoint"]
        )

        self.data_source_status = Gauge("bot_data_source_status", "Data source health (0=down, 1=degraded, 2=healthy)", ["source"])

        # Bot Info
        self.bot_info = Info("bot_info", "Bot version and configuration info")

    def record_order(self, side: str, symbol: str, status: str):
        """Record order placement"""
        if self.enabled:
            self.orders_total.labels(side=side, symbol=symbol, status=status).inc()

    def record_order_latency(self, latency_seconds: float):
        """Record order placement latency"""
        if self.enabled:
            self.order_latency.observe(latency_seconds)

    def update_capital_utilization(self, utilization_pct: float):
        """Update capital utilization gauge"""
        if self.enabled:
            self.capital_utilization.set(utilization_pct)

    def update_pnl(self, realized: float, unrealized: float):
        """Update P&L gauges"""
        if self.enabled:
            self.realized_pnl.set(realized)
            self.unrealized_pnl.set(unrealized)

    def update_active_positions(self, count: int):
        """Update active positions count"""
        if self.enabled:
            self.active_positions.set(count)

    def record_signal_generation(self, module: str, duration_seconds: float):
        """Record signal generation time"""
        if self.enabled:
            self.signal_generation_time.labels(module=module).observe(duration_seconds)

    def record_signal_confidence(self, module: str, signal_type: str, confidence: float):
        """Record signal confidence"""
        if self.enabled:
            self.signal_confidence.labels(module=module, signal_type=signal_type).observe(confidence)

    def record_signal_error(self, module: str, error_type: str):
        """Record signal generation error"""
        if self.enabled:
            self.signal_errors.labels(module=module, error_type=error_type).inc()

    def record_exchange_error(self, exchange: str, endpoint: str, status_code: int):
        """Record exchange API error"""
        if self.enabled:
            self.exchange_api_errors.labels(exchange=exchange, endpoint=endpoint, status_code=str(status_code)).inc()

    def update_circuit_breaker(self, endpoint: str, state: str):
        """Update circuit breaker state"""
        if self.enabled:
            state_map = {"closed": 0, "half_open": 1, "open": 2}
            self.circuit_breaker_state.labels(endpoint=endpoint).set(state_map.get(state, 0))

    def update_data_source_status(self, source: str, status: str):
        """Update data source health status"""
        if self.enabled:
            status_map = {"down": 0, "degraded": 1, "healthy": 2}
            self.data_source_status.labels(source=source).set(status_map.get(status, 0))


class ObservabilityManager:
    """
    Centralized observability manager
    Combines structured logging, metrics, and tracing
    """

    def __init__(self, service_name: str = "trading-bot", metrics_port: int = 9090, enable_metrics: bool = True):
        self.service_name = service_name
        self.logger = StructuredLogger(service_name)
        self.metrics = TradingMetrics(enabled=enable_metrics)

        # Start Prometheus metrics server
        if enable_metrics and PROMETHEUS_AVAILABLE:
            try:
                start_http_server(metrics_port)
                self.logger.info(f"Metrics server started on port {metrics_port}")
            except Exception as e:
                self.logger.error(f"Failed to start metrics server: {e}")

    @contextmanager
    def measure_operation(self, operation_name: str, **context):
        """Context manager to measure operation duration and log results"""
        start_time = time.time()

        try:
            self.logger.info(f"{operation_name} started", **context)
            yield

            duration = time.time() - start_time
            self.logger.info(f"{operation_name} completed", duration_seconds=duration, **context)

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"{operation_name} failed", error=str(e), error_type=type(e).__name__, duration_seconds=duration, **context)
            raise

    def log_trade(self, symbol: str, side: str, amount: float, price: float, order_id: str, status: str):
        """Log trade execution with metrics"""
        self.logger.info(
            "Trade executed",
            symbol=symbol,
            side=side,
            amount=amount,
            price=price,
            order_id=order_id,
            status=status,
            total_value=amount * price,
        )

        self.metrics.record_order(side, symbol, status)

    def log_signal(
        self, module: str, symbol: str, signal_type: str, confidence: float, duration_seconds: float, metadata: Optional[Dict] = None
    ):
        """Log signal generation with metrics"""
        self.logger.info(
            "Signal generated",
            module=module,
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            duration_seconds=duration_seconds,
            **(metadata or {}),
        )

        self.metrics.record_signal_generation(module, duration_seconds)
        self.metrics.record_signal_confidence(module, signal_type, confidence)

    def log_portfolio_snapshot(
        self, total_value: float, realized_pnl: float, unrealized_pnl: float, active_positions: int, capital_utilization: float
    ):
        """Log portfolio snapshot with metrics"""
        self.logger.info(
            "Portfolio snapshot",
            total_value=total_value,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            active_positions=active_positions,
            capital_utilization_pct=capital_utilization,
        )

        self.metrics.update_pnl(realized_pnl, unrealized_pnl)
        self.metrics.update_active_positions(active_positions)
        self.metrics.update_capital_utilization(capital_utilization)


def timing_decorator(observability: ObservabilityManager, operation_name: str):
    """Decorator to automatically time and log function execution"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with observability.measure_operation(operation_name, function=func.__name__):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Global observability instance
_global_observability: Optional[ObservabilityManager] = None


def get_observability() -> ObservabilityManager:
    """Get or create global observability manager"""
    global _global_observability

    if _global_observability is None:
        _global_observability = ObservabilityManager()

    return _global_observability


def init_observability(service_name: str = "trading-bot", metrics_port: int = 9090, enable_metrics: bool = True) -> ObservabilityManager:
    """Initialize global observability manager"""
    global _global_observability
    _global_observability = ObservabilityManager(service_name=service_name, metrics_port=metrics_port, enable_metrics=enable_metrics)
    return _global_observability
