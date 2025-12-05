"""
Minimal metrics collector stub for ChainBridge API server.

This is a placeholder implementation that allows the API server to start
without crashing. Metrics are collected in-memory but not persisted.

Future enhancements:
- Persist metrics to database
- Export to Prometheus/StatsD
- Add alerting thresholds
- Time-series analysis
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List


class MetricsCollector:
    """
    Lightweight metrics collection for API operations.

    Tracks:
    - Module registrations and executions
    - Pipeline creations and executions
    - Errors and business impact
    - System performance
    """

    def __init__(self) -> None:
        """Initialize empty metrics storage."""
        self.module_metrics: Dict[str, Any] = defaultdict(
            lambda: {
                "registrations": 0,
                "executions": 0,
                "errors": 0,
                "last_execution": None,
            }
        )
        self.pipeline_metrics: Dict[str, Any] = defaultdict(
            lambda: {
                "creations": 0,
                "executions": 0,
                "errors": 0,
                "last_execution": None,
            }
        )
        self.error_log: List[Dict[str, Any]] = []
        self.business_impact: Dict[str, float] = defaultdict(float)

    def track_module_registration(self, module_name: str, module_path: str) -> None:
        """Record a module registration."""
        self.module_metrics[module_name]["registrations"] += 1
        self.module_metrics[module_name]["path"] = module_path

    def track_module_execution(self, module_name: str, execution_time: float, success: bool = True) -> None:
        """Record a module execution."""
        self.module_metrics[module_name]["executions"] += 1
        self.module_metrics[module_name]["last_execution"] = datetime.now(timezone.utc).isoformat()
        self.module_metrics[module_name]["last_execution_time"] = execution_time
        if not success:
            self.module_metrics[module_name]["errors"] += 1

    def track_pipeline_creation(self, pipeline_name: str, module_sequence: List[str]) -> None:
        """Record a pipeline creation."""
        self.pipeline_metrics[pipeline_name]["creations"] += 1
        self.pipeline_metrics[pipeline_name]["modules"] = module_sequence

    def track_pipeline_execution(self, pipeline_name: str, execution_time: float, success: bool = True) -> None:
        """Record a pipeline execution."""
        self.pipeline_metrics[pipeline_name]["executions"] += 1
        self.pipeline_metrics[pipeline_name]["last_execution"] = datetime.now(timezone.utc).isoformat()
        self.pipeline_metrics[pipeline_name]["last_execution_time"] = execution_time
        if not success:
            self.pipeline_metrics[pipeline_name]["errors"] += 1

    def track_error(self, operation: str, context: str, error_message: str) -> None:
        """Record an error occurrence."""
        self.error_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": operation,
                "context": context,
                "error": error_message,
            }
        )

    def track_business_impact(self, operation: str, impact: float) -> None:
        """Record business impact metric."""
        self.business_impact[operation] += impact

    def get_all_metrics(self) -> Dict[str, Any]:
        """Return all collected metrics."""
        return {
            "modules": dict(self.module_metrics),
            "pipelines": dict(self.pipeline_metrics),
            "errors": self.error_log[-100:],  # Last 100 errors
            "business_impact": dict(self.business_impact),
        }

    def get_module_metrics(self) -> Dict[str, Any]:
        """Return module-specific metrics."""
        return dict(self.module_metrics)

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Return pipeline-specific metrics."""
        return dict(self.pipeline_metrics)
