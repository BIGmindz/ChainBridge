"""
Pipeline Core for Benson

This module provides the pipeline framework for chaining modules together
to create complex data processing and ML workflows.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .data_processor import DataProcessor
from .module_manager import ModuleManager


class PipelineStep:
    """Represents a single step in a processing pipeline."""

    def __init__(self, name: str, module_name: str, config: Dict[str, Any] = None):
        self.name = name
        self.module_name = module_name
        self.config = config or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "module_name": self.module_name,
            "config": self.config,
        }


class Pipeline:
    """Main pipeline orchestration engine."""

    def __init__(self, name: str, module_manager: ModuleManager):
        self.name = name
        self.module_manager = module_manager
        self.data_processor = DataProcessor()
        self.steps: List[PipelineStep] = []
        self.execution_history: List[Dict[str, Any]] = []

    def add_step(
        self, step_name: str, module_name: str, config: Dict[str, Any] = None
    ) -> "Pipeline":
        """Add a step to the pipeline. Returns self for chaining."""
        step = PipelineStep(step_name, module_name, config)
        self.steps.append(step)  # type: ignore
        return self

    def remove_step(self, step_name: str) -> bool:
        """Remove a step from the pipeline."""
        for i, step in enumerate(self.steps):
            if step.name == step_name:
                del self.steps[i]
                return True
        return False

    def get_step(self, step_name: str) -> Optional[PipelineStep]:
        """Get a step by name."""
        for step in self.steps:
            if step.name == step_name:
                return step
        return None

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the complete pipeline."""
        execution_id = (
            f"{self.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        execution_record = {
            "execution_id": execution_id,
            "pipeline_name": self.name,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "input_data": input_data.copy(),
            "steps_executed": [],
            "final_output": None,
            "status": "running",
            "error": None,
        }

        try:
            current_data = input_data.copy()

            for step in self.steps:
                step_start = datetime.now(timezone.utc).isoformat()

                # Execute the module for this step
                try:
                    module_output = self.module_manager.execute_module(
                        step.module_name, current_data
                    )

                    step_record = {
                        "step_name": step.name,
                        "module_name": step.module_name,
                        "start_time": step_start,
                        "end_time": datetime.now(timezone.utc).isoformat(),
                        "status": "completed",
                        "input_size": len(str(current_data)),
                        "output_size": len(str(module_output)),
                    }

                    # Update current_data with module output
                    if isinstance(module_output, dict):
                        current_data.update(module_output)
                    else:
                        current_data = module_output

                    execution_record["steps_executed"].append(step_record)  # type: ignore

                except Exception as e:
                    step_record = {
                        "step_name": step.name,
                        "module_name": step.module_name,
                        "start_time": step_start,
                        "end_time": datetime.now(timezone.utc).isoformat(),
                        "status": "failed",
                        "error": str(e),
                    }
                    execution_record["steps_executed"].append(step_record)  # type: ignore
                    raise e

            execution_record["final_output"] = current_data
            execution_record["status"] = "completed"
            execution_record["end_time"] = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            execution_record["status"] = "failed"
            execution_record["error"] = str(e)
            execution_record["end_time"] = datetime.now(timezone.utc).isoformat()

        finally:
            self.execution_history.append(execution_record)  # type: ignore

        if execution_record["status"] == "failed":
            raise RuntimeError(
                f"Pipeline execution failed: {execution_record['error']}"
            )

        return execution_record["final_output"]

    def validate_pipeline(self) -> Dict[str, Any]:
        """Validate that all modules in the pipeline are available and compatible."""
        validation_result = {
            "valid": True,
            "issues": [],
            "steps_checked": len(self.steps),
        }

        for step in self.steps:
            module = self.module_manager.get_module(step.module_name)
            if not module:
                validation_result["valid"] = False
                validation_result["issues"].append(f"Module '{step.module_name}' not found for step '{step.name}'")  # type: ignore

        return validation_result

    def get_pipeline_schema(self) -> Dict[str, Any]:
        """Get the combined schema for the entire pipeline."""
        schema = {"name": self.name, "steps": [], "total_steps": len(self.steps)}

        for step in self.steps:
            module = self.module_manager.get_module(step.module_name)
            step_schema = {
                "name": step.name,
                "module_name": step.module_name,
                "module_schema": module.get_schema() if module else None,
            }
            schema["steps"].append(step_schema)  # type: ignore

        return schema

    def to_dict(self) -> Dict[str, Any]:
        """Serialize pipeline to dictionary."""
        return {
            "name": self.name,
            "steps": [step.to_dict() for step in self.steps],  # type: ignore
            "execution_count": len(self.execution_history),
        }

    def save_to_file(self, filepath: str) -> None:
        """Save pipeline configuration to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)  # type: ignore

    @classmethod
    def load_from_file(cls, filepath: str, module_manager: ModuleManager) -> "Pipeline":
        """Load pipeline configuration from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)

        pipeline = cls(data["name"], module_manager)

        for step_data in data["steps"]:
            pipeline.add_step(
                step_data["name"], step_data["module_name"], step_data.get("config", {})
            )

        return pipeline

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        return self.execution_history[-limit:] if limit > 0 else self.execution_history

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the pipeline."""
        if not self.execution_history:
            return {"message": "No executions recorded"}

        successful_executions = [
            ex for ex in self.execution_history if ex["status"] == "completed"
        ]
        failed_executions = [
            ex for ex in self.execution_history if ex["status"] == "failed"
        ]

        metrics = {
            "total_executions": len(self.execution_history),
            "successful_executions": len(successful_executions),
            "failed_executions": len(failed_executions),
            "success_rate": (
                len(successful_executions) / len(self.execution_history)
                if self.execution_history
                else 0
            ),
            "avg_steps_per_execution": sum(len(ex["steps_executed"]) for ex in self.execution_history) / len(self.execution_history),  # type: ignore
        }

        return metrics
