"""
ChainIQ Metrics Module

Provides metrics tracking for ChainIQ ML endpoints.
Includes both in-memory counters (for legacy debug endpoint) and
Prometheus metrics for production monitoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prometheus_client import Counter, Histogram


@dataclass
class IqMetrics:
    """
    Minimal in-process metrics holder for ChainIQ ML endpoints.

    This is intentionally simple and in-memory. Used by /iq/ml/debug/metrics.
    For production monitoring, use the Prometheus metrics below.

    Attributes:
        risk_calls_total: Count of calls to /iq/ml/risk-score
        anomaly_calls_total: Count of calls to /iq/ml/anomaly
    """

    risk_calls_total: int = field(default=0)
    anomaly_calls_total: int = field(default=0)


# Global singleton instance (for legacy debug endpoint)
metrics = IqMetrics()


# ═══════════════════════════════════════════════════════════════════════════
# PROMETHEUS METRICS
# ═══════════════════════════════════════════════════════════════════════════

IQ_RISK_CALLS = Counter(
    "chainiq_risk_requests_total",
    "Total number of risk-score requests processed by ChainIQ",
    ["corridor"],
)

IQ_ANOMALY_CALLS = Counter(
    "chainiq_anomaly_requests_total",
    "Total number of anomaly-score requests processed by ChainIQ",
    ["corridor"],
)

IQ_RISK_LATENCY = Histogram(
    "chainiq_risk_request_duration_seconds",
    "Histogram of risk-score request durations in seconds",
    ["corridor"],
)

IQ_ANOMALY_LATENCY = Histogram(
    "chainiq_anomaly_request_duration_seconds",
    "Histogram of anomaly-score request durations in seconds",
    ["corridor"],
)
