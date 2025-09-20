"""
Metrics Collector for Business Impact Tracking

This module collects and tracks usage metrics, adoption rates, ROI,
and other business impact indicators for the Benson system.
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict


class MetricsCollector:
    """Collects and manages business impact and usage metrics."""

    def __init__(self, metrics_file: str = None):
        self.metrics_file = metrics_file or "benson_metrics.json"
        self.metrics = {
            "system": {
                "startup_time": datetime.now(timezone.utc).isoformat(),
                "total_requests": 0,
                "total_errors": 0,
                "uptime_seconds": 0,
            },
            "modules": defaultdict(
                lambda: {
                    "executions": 0,
                    "total_execution_time": 0.0,
                    "avg_execution_time": 0.0,
                    "errors": 0,
                    "first_used": None,
                    "last_used": None,
                    "input_data_volume": 0,
                    "output_data_volume": 0,
                }
            ),
            "pipelines": defaultdict(
                lambda: {
                    "executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "total_execution_time": 0.0,
                    "avg_execution_time": 0.0,
                    "avg_steps_per_execution": 0.0,
                    "created_at": None,
                    "last_executed": None,
                }
            ),
            "business_impact": {
                "total_signals_generated": 0,
                "total_forecasts_generated": 0,
                "data_processed_mb": 0.0,
                "cost_savings_estimated": 0.0,
                "automation_hours_saved": 0.0,
            },
            "adoption": {
                "unique_modules_used": set(),
                "unique_pipelines_used": set(),
                "daily_active_modules": defaultdict(set),
                "feature_usage": Counter(),
            },
            "errors": {
                "by_type": Counter(),
                "by_module": Counter(),
                "by_pipeline": Counter(),
                "recent_errors": [],
            },
        }

        # Load existing metrics if file exists
        self._load_metrics()

    def _load_metrics(self):
        """Load metrics from file if it exists."""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, "r") as f:
                    stored_metrics = json.load(f)

                # Merge stored metrics with current structure
                if "system" in stored_metrics:
                    self.metrics["system"].update(stored_metrics["system"])
                if "modules" in stored_metrics:
                    for module_name, module_metrics in stored_metrics[
                        "modules"
                    ].items():
                        self.metrics["modules"][module_name].update(module_metrics)
                if "pipelines" in stored_metrics:
                    for pipeline_name, pipeline_metrics in stored_metrics[
                        "pipelines"
                    ].items():
                        self.metrics["pipelines"][pipeline_name].update(
                            pipeline_metrics
                        )

            except Exception as e:
                print(f"Warning: Could not load metrics file: {e}")

    def _save_metrics(self):
        """Save metrics to file."""
        try:
            # Convert sets to lists for JSON serialization
            metrics_copy = json.loads(json.dumps(self.metrics, default=str))

            # Handle special cases
            if "adoption" in metrics_copy:
                if "unique_modules_used" in metrics_copy["adoption"]:
                    metrics_copy["adoption"]["unique_modules_used"] = list(
                        self.metrics["adoption"]["unique_modules_used"]
                    )
                if "unique_pipelines_used" in metrics_copy["adoption"]:
                    metrics_copy["adoption"]["unique_pipelines_used"] = list(
                        self.metrics["adoption"]["unique_pipelines_used"]
                    )

            with open(self.metrics_file, "w") as f:
                json.dump(metrics_copy, f, indent=2, default=str)

        except Exception as e:
            print(f"Warning: Could not save metrics: {e}")

    def track_module_execution(
        self, module_name: str, execution_time: float, input_size: int, output_size: int
    ):
        """Track a module execution."""
        now = datetime.now(timezone.utc).isoformat()

        module_metrics = self.metrics["modules"][module_name]
        module_metrics["executions"] += 1
        module_metrics["total_execution_time"] += execution_time
        module_metrics["avg_execution_time"] = (
            module_metrics["total_execution_time"] / module_metrics["executions"]
        )
        module_metrics["input_data_volume"] += input_size
        module_metrics["output_data_volume"] += output_size
        module_metrics["last_used"] = now

        if module_metrics["first_used"] is None:
            module_metrics["first_used"] = now

        # Track adoption
        self.metrics["adoption"]["unique_modules_used"].add(module_name)
        today = datetime.now(timezone.utc).date().isoformat()
        self.metrics["adoption"]["daily_active_modules"][today].add(module_name)

        # Track system totals
        self.metrics["system"]["total_requests"] += 1

        # Estimate business impact
        self._estimate_automation_savings(module_name, execution_time)

        self._save_metrics()

    def track_pipeline_execution(
        self, pipeline_name: str, execution_time: float, steps_count: int, success: bool
    ):
        """Track a pipeline execution."""
        now = datetime.now(timezone.utc).isoformat()

        pipeline_metrics = self.metrics["pipelines"][pipeline_name]
        pipeline_metrics["executions"] += 1
        pipeline_metrics["total_execution_time"] += execution_time

        if success:
            pipeline_metrics["successful_executions"] += 1
        else:
            pipeline_metrics["failed_executions"] += 1

        pipeline_metrics["avg_execution_time"] = (
            pipeline_metrics["total_execution_time"] / pipeline_metrics["executions"]
        )

        # Update average steps per execution
        current_avg_steps = pipeline_metrics["avg_steps_per_execution"] or 0
        pipeline_metrics["avg_steps_per_execution"] = (
            current_avg_steps * (pipeline_metrics["executions"] - 1) + steps_count
        ) / pipeline_metrics["executions"]

        pipeline_metrics["last_executed"] = now

        # Track adoption
        self.metrics["adoption"]["unique_pipelines_used"].add(pipeline_name)

        # Track system totals
        self.metrics["system"]["total_requests"] += 1

        self._save_metrics()

    def track_module_registration(self, module_name: str, module_path: str):
        """Track when a new module is registered."""
        now = datetime.now(timezone.utc).isoformat()

        if module_name not in self.metrics["modules"]:
            self.metrics["modules"][module_name] = {
                "executions": 0,
                "total_execution_time": 0.0,
                "avg_execution_time": 0.0,
                "errors": 0,
                "first_used": None,
                "last_used": None,
                "input_data_volume": 0,
                "output_data_volume": 0,
                "registered_at": now,
                "module_path": module_path,
            }

        self.metrics["adoption"]["feature_usage"]["module_registration"] += 1
        self._save_metrics()

    def track_pipeline_creation(self, pipeline_name: str, steps_count: int):
        """Track when a new pipeline is created."""
        now = datetime.now(timezone.utc).isoformat()

        if pipeline_name not in self.metrics["pipelines"]:
            self.metrics["pipelines"][pipeline_name]["created_at"] = now
            self.metrics["pipelines"][pipeline_name]["steps_count"] = steps_count

        self.metrics["adoption"]["feature_usage"]["pipeline_creation"] += 1
        self._save_metrics()

    def track_error(self, error_type: str, component: str, error_message: str):
        """Track an error occurrence."""
        now = datetime.now(timezone.utc).isoformat()

        self.metrics["errors"]["by_type"][error_type] += 1
        self.metrics["system"]["total_errors"] += 1

        if error_type == "module_execution":
            self.metrics["modules"][component]["errors"] += 1
            self.metrics["errors"]["by_module"][component] += 1
        elif error_type == "pipeline_execution":
            self.metrics["errors"]["by_pipeline"][component] += 1

        # Store recent errors (keep last 100)
        error_record = {
            "timestamp": now,
            "type": error_type,
            "component": component,
            "message": error_message[:500],  # Truncate long error messages
        }

        self.metrics["errors"]["recent_errors"].append(error_record)
        if len(self.metrics["errors"]["recent_errors"]) > 100:
            self.metrics["errors"]["recent_errors"] = self.metrics["errors"][
                "recent_errors"
            ][-100:]

        self._save_metrics()

    def track_business_impact(
        self, impact_type: str, value: float, metadata: Dict[str, Any] = None
    ):
        """Track business impact metrics."""
        if impact_type == "signal_generated":
            self.metrics["business_impact"]["total_signals_generated"] += 1
        elif impact_type == "forecast_generated":
            self.metrics["business_impact"]["total_forecasts_generated"] += 1
        elif impact_type == "data_processed":
            self.metrics["business_impact"]["data_processed_mb"] += value / (
                1024 * 1024
            )
        elif impact_type == "cost_savings":
            self.metrics["business_impact"]["cost_savings_estimated"] += value

        self._save_metrics()

    def _estimate_automation_savings(self, module_name: str, execution_time: float):
        """Estimate automation time savings based on module type."""
        # Simple heuristic: assume automation saves manual work
        time_savings_multiplier = {
            "csv_ingestion": 10.0,  # 10 minutes of manual work per execution
            "rsi_module": 5.0,  # 5 minutes of manual analysis
            "sales_forecasting": 30.0,  # 30 minutes of manual forecasting
        }

        base_module_name = module_name.lower().replace("module", "").strip()
        multiplier = time_savings_multiplier.get(
            base_module_name, 5.0
        )  # Default 5 minutes

        # Convert to hours
        hours_saved = multiplier / 60.0
        self.metrics["business_impact"]["automation_hours_saved"] += hours_saved

    def get_module_metrics(self) -> Dict[str, Any]:
        """Get all module metrics."""
        return dict(self.metrics["modules"])

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get all pipeline metrics."""
        return dict(self.metrics["pipelines"])

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics."""
        # Calculate uptime
        startup_time = datetime.fromisoformat(self.metrics["system"]["startup_time"])
        uptime = (datetime.now(timezone.utc) - startup_time).total_seconds()
        self.metrics["system"]["uptime_seconds"] = uptime

        return self.metrics["system"]

    def get_business_impact_metrics(self) -> Dict[str, Any]:
        """Get business impact metrics."""
        return self.metrics["business_impact"]

    def get_adoption_metrics(self) -> Dict[str, Any]:
        """Get adoption and usage metrics."""
        adoption = self.metrics["adoption"].copy()

        # Convert sets to lists and counts for JSON serialization
        adoption["unique_modules_used"] = len(adoption["unique_modules_used"])
        adoption["unique_pipelines_used"] = len(adoption["unique_pipelines_used"])

        # Calculate daily active modules for last 7 days
        daily_counts = []
        for i in range(7):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat()
            count = len(adoption["daily_active_modules"].get(date, set()))
            daily_counts.append({"date": date, "active_modules": count})

        adoption["daily_active_modules"] = daily_counts
        adoption["feature_usage"] = dict(adoption["feature_usage"])

        return adoption

    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error and reliability metrics."""
        errors = self.metrics["errors"].copy()
        errors["by_type"] = dict(errors["by_type"])
        errors["by_module"] = dict(errors["by_module"])
        errors["by_pipeline"] = dict(errors["by_pipeline"])

        # Calculate error rates
        total_requests = self.metrics["system"]["total_requests"]
        if total_requests > 0:
            errors["overall_error_rate"] = (
                self.metrics["system"]["total_errors"] / total_requests
            )
        else:
            errors["overall_error_rate"] = 0.0

        return errors

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics combined."""
        return {
            "system": self.get_system_metrics(),
            "modules": self.get_module_metrics(),
            "pipelines": self.get_pipeline_metrics(),
            "business_impact": self.get_business_impact_metrics(),
            "adoption": self.get_adoption_metrics(),
            "errors": self.get_error_metrics(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_roi_report(self) -> Dict[str, Any]:
        """Generate a ROI (Return on Investment) report."""
        impact = self.metrics["business_impact"]

        # Simple ROI calculation based on automation savings
        automation_hours = impact["automation_hours_saved"]
        estimated_hourly_rate = 50.0  # $50/hour assumption

        cost_savings = automation_hours * estimated_hourly_rate

        # Assume system operational cost (very basic estimate)
        uptime_hours = self.metrics["system"]["uptime_seconds"] / 3600
        operational_cost = uptime_hours * 0.10  # $0.10/hour assumption

        roi_percentage = (
            (cost_savings - operational_cost) / max(operational_cost, 1)
        ) * 100

        return {
            "automation_hours_saved": automation_hours,
            "estimated_cost_savings": cost_savings,
            "estimated_operational_cost": operational_cost,
            "net_benefit": cost_savings - operational_cost,
            "roi_percentage": roi_percentage,
            "total_signals_generated": impact["total_signals_generated"],
            "total_forecasts_generated": impact["total_forecasts_generated"],
            "data_processed_mb": impact["data_processed_mb"],
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
        }
