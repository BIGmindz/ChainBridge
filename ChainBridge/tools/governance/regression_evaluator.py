"""
Regression Evaluator for ChainBridge Governance.

PAC Reference: PAC-ATLAS-P41-GOVERNANCE-REGRESSION-AND-DRIFT-ENFORCEMENT-INTEGRATION-01
Agent: ATLAS (GID-05) | 🔵 BLUE
Authority: BENSON (GID-00)

Purpose:
  - Load agent baselines from GOVERNANCE_AGENT_BASELINES.md
  - Compare live execution metrics against baseline P50/P95 thresholds
  - Emit GS_094 on hard regression detection
  - Enforce FAIL_CLOSED on regression

Pattern: GOVERNANCE_MUST_NOT_DECAY
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum


class RegressionSeverity(Enum):
    """Regression severity levels."""
    NONE = "NONE"
    MINOR = "MINOR"           # Below P50 (acceptable → warning)
    MODERATE = "MODERATE"     # Below P25 (warning → escalation)
    SEVERE = "SEVERE"         # Below P10 (hard failure → block)
    CRITICAL = "CRITICAL"     # More than 50% below P50 (immediate block)


@dataclass
class BaselineThresholds:
    """Baseline thresholds for a single metric."""
    metric_name: str
    P50: float
    P75: float
    P90: float
    P95: Optional[float] = None
    unit: str = "unknown"
    minimum: Optional[float] = None
    maximum: Optional[float] = None


@dataclass
class AgentBaseline:
    """Complete baseline for an agent role."""
    role_id: str
    representative_agent: str
    speed_metrics: Dict[str, BaselineThresholds] = field(default_factory=dict)
    accuracy_metrics: Dict[str, BaselineThresholds] = field(default_factory=dict)
    scope_discipline_metrics: Dict[str, BaselineThresholds] = field(default_factory=dict)
    governance_compliance_metrics: Dict[str, BaselineThresholds] = field(default_factory=dict)
    failure_quality_metrics: Dict[str, BaselineThresholds] = field(default_factory=dict)


@dataclass
class RegressionResult:
    """Result of regression evaluation."""
    metric_name: str
    current_value: float
    baseline_p50: float
    baseline_p95: Optional[float]
    severity: RegressionSeverity
    deviation_pct: float
    should_block: bool
    error_code: Optional[str] = None
    message: str = ""


@dataclass
class RegressionReport:
    """Complete regression evaluation report."""
    agent_gid: str
    agent_name: str
    execution_lane: str
    total_metrics_evaluated: int
    regressions: List[RegressionResult]
    has_blocking_regression: bool
    execution_time_ms: int = 0

    @property
    def summary(self) -> str:
        """Generate summary string."""
        if not self.regressions:
            return f"✓ PASS: {self.agent_name} ({self.agent_gid}) — No regressions detected"
        blocking = [r for r in self.regressions if r.should_block]
        if blocking:
            return f"✗ FAIL: {self.agent_name} ({self.agent_gid}) — {len(blocking)} blocking regressions (GS_094)"
        return f"⚠ WARN: {self.agent_name} ({self.agent_gid}) — {len(self.regressions)} minor regressions"


class BaselineLoader:
    """
    Load agent baselines from GOVERNANCE_AGENT_BASELINES.md at runtime.
    """

    # Role to GID mapping for binding
    ROLE_TO_GID = {
        "BACKEND": "GID-01",
        "FRONTEND": "GID-07",
        "SECURITY": "GID-06",
        "ML_AI": "GID-10",
        "STRATEGY": "GID-05",
        "QUALITY_ASSURANCE": "GID-08",
    }

    # GID to role mapping
    GID_TO_ROLE = {v: k for k, v in ROLE_TO_GID.items()}

    def __init__(self, baselines_path: Optional[Path] = None):
        """Initialize loader with path to baselines file."""
        if baselines_path is None:
            # Default path relative to this file
            self_path = Path(__file__).parent
            baselines_path = self_path.parent.parent / "docs" / "governance" / "GOVERNANCE_AGENT_BASELINES.md"
        self.baselines_path = baselines_path
        self.baselines: Dict[str, AgentBaseline] = {}
        self._loaded = False

    def load(self) -> Dict[str, AgentBaseline]:
        """
        Load and parse all baselines from the markdown file.

        Returns:
            Dict mapping role_id to AgentBaseline
        """
        if self._loaded:
            return self.baselines

        if not self.baselines_path.exists():
            raise FileNotFoundError(f"Baselines file not found: {self.baselines_path}")

        content = self.baselines_path.read_text(encoding="utf-8")

        # Extract all YAML code blocks
        yaml_blocks = re.findall(r"```yaml\s*\n(.*?)```", content, re.DOTALL)

        for block in yaml_blocks:
            try:
                parsed = yaml.safe_load(block)
                if parsed and isinstance(parsed, dict):
                    self._process_yaml_block(parsed)
            except yaml.YAMLError:
                continue

        self._loaded = True
        return self.baselines

    def _process_yaml_block(self, data: Dict[str, Any]) -> None:
        """Process a single YAML block from the baselines file."""
        # Check for role baselines (e.g., BACKEND_BASELINES, FRONTEND_BASELINES)
        for key, value in data.items():
            if key.endswith("_BASELINES") and isinstance(value, dict):
                role_id = value.get("role_id")
                if not role_id:
                    continue

                baseline = AgentBaseline(
                    role_id=role_id,
                    representative_agent=value.get("representative_agent", ""),
                )

                # Extract speed metrics
                if "speed_metrics" in value:
                    baseline.speed_metrics = self._extract_metrics(value["speed_metrics"])

                # Extract accuracy metrics
                if "accuracy_metrics" in value:
                    baseline.accuracy_metrics = self._extract_metrics(value["accuracy_metrics"])

                # Extract scope discipline metrics
                if "scope_discipline_metrics" in value:
                    baseline.scope_discipline_metrics = self._extract_metrics(value["scope_discipline_metrics"])

                # Extract governance compliance metrics
                if "governance_compliance_metrics" in value:
                    baseline.governance_compliance_metrics = self._extract_metrics(value["governance_compliance_metrics"])

                # Extract failure quality metrics
                if "failure_quality_metrics" in value:
                    baseline.failure_quality_metrics = self._extract_metrics(value["failure_quality_metrics"])

                self.baselines[role_id] = baseline

    def _extract_metrics(self, metrics_data: Dict[str, Any]) -> Dict[str, BaselineThresholds]:
        """Extract baseline thresholds from metrics data."""
        result = {}
        for metric_name, metric_values in metrics_data.items():
            if isinstance(metric_values, dict) and "P50" in metric_values:
                threshold = BaselineThresholds(
                    metric_name=metric_name,
                    P50=float(metric_values.get("P50", 0)),
                    P75=float(metric_values.get("P75", 0)),
                    P90=float(metric_values.get("P90", 0)),
                    P95=float(metric_values["P95"]) if "P95" in metric_values else None,
                    unit=metric_values.get("unit", "unknown"),
                    minimum=float(metric_values["minimum"]) if "minimum" in metric_values else None,
                    maximum=float(metric_values["maximum"]) if "maximum" in metric_values else None,
                )
                result[metric_name] = threshold
        return result

    def get_baseline_for_gid(self, gid: str) -> Optional[AgentBaseline]:
        """Get baseline for a specific agent GID."""
        if not self._loaded:
            self.load()

        role = self.GID_TO_ROLE.get(gid)
        if role:
            return self.baselines.get(role)
        return None

    def get_baseline_for_role(self, role_id: str) -> Optional[AgentBaseline]:
        """Get baseline for a specific role."""
        if not self._loaded:
            self.load()
        return self.baselines.get(role_id)


class RegressionEvaluator:
    """
    Evaluate live metrics against baselines for regression detection.

    Enforcement:
      - MINOR regression: Warning only (no block)
      - MODERATE regression: Escalation signal (optional block)
      - SEVERE regression: FAIL_CLOSED (mandatory block, GS_094)
      - CRITICAL regression: FAIL_CLOSED (mandatory block, GS_094)
    """

    # Thresholds for regression severity determination
    SEVERITY_THRESHOLDS = {
        "MINOR": 0.0,      # Any deviation below P50
        "MODERATE": 0.25,  # 25% below P50
        "SEVERE": 0.50,    # 50% below P50
        "CRITICAL": 0.75,  # 75% below P50
    }

    def __init__(self, baseline_loader: Optional[BaselineLoader] = None):
        """Initialize evaluator with baseline loader."""
        self.loader = baseline_loader or BaselineLoader()
        self.loader.load()

    def evaluate(
        self,
        agent_gid: str,
        agent_name: str,
        execution_lane: str,
        metrics: Dict[str, float],
    ) -> RegressionReport:
        """
        Evaluate metrics against baseline for regression.

        Args:
            agent_gid: Agent GID (e.g., "GID-01")
            agent_name: Agent name (e.g., "Cody")
            execution_lane: Execution lane (e.g., "BACKEND")
            metrics: Dict of metric_name -> current_value

        Returns:
            RegressionReport with all evaluation results
        """
        baseline = self.loader.get_baseline_for_gid(agent_gid)
        if not baseline:
            # No baseline found — cannot evaluate regression
            return RegressionReport(
                agent_gid=agent_gid,
                agent_name=agent_name,
                execution_lane=execution_lane,
                total_metrics_evaluated=0,
                regressions=[],
                has_blocking_regression=False,
            )

        regressions = []
        total_evaluated = 0

        # Evaluate all metric categories
        for category_name, category_metrics in [
            ("speed", baseline.speed_metrics),
            ("accuracy", baseline.accuracy_metrics),
            ("scope_discipline", baseline.scope_discipline_metrics),
            ("governance_compliance", baseline.governance_compliance_metrics),
            ("failure_quality", baseline.failure_quality_metrics),
        ]:
            for metric_name, threshold in category_metrics.items():
                if metric_name in metrics:
                    total_evaluated += 1
                    result = self._evaluate_single_metric(
                        metric_name=metric_name,
                        current_value=metrics[metric_name],
                        threshold=threshold,
                        category=category_name,
                    )
                    if result.severity != RegressionSeverity.NONE:
                        regressions.append(result)

        has_blocking = any(r.should_block for r in regressions)

        return RegressionReport(
            agent_gid=agent_gid,
            agent_name=agent_name,
            execution_lane=execution_lane,
            total_metrics_evaluated=total_evaluated,
            regressions=regressions,
            has_blocking_regression=has_blocking,
        )

    def _evaluate_single_metric(
        self,
        metric_name: str,
        current_value: float,
        threshold: BaselineThresholds,
        category: str,
    ) -> RegressionResult:
        """
        Evaluate a single metric against its baseline.

        For most metrics, lower is worse (accuracy, compliance).
        For some metrics, higher is worse (violations, time).
        """
        # Determine if metric is inverted (higher is worse)
        inverted_metrics = {
            "pac_completion_time",
            "iterations_to_valid",
            "correction_cycles",
            "lane_violations",
            "tool_violations",
            "scope_drift_events",
            "authority_overreach",
            "self_corrections",
            "external_corrections",
            "correction_ratio",
            "silent_failure_rate",
        }

        is_inverted = metric_name in inverted_metrics

        # Check hard limits first
        if threshold.maximum is not None and current_value > threshold.maximum:
            return RegressionResult(
                metric_name=metric_name,
                current_value=current_value,
                baseline_p50=threshold.P50,
                baseline_p95=threshold.P95,
                severity=RegressionSeverity.CRITICAL,
                deviation_pct=1.0,
                should_block=True,
                error_code="GS_094",
                message=f"{metric_name}: {current_value} exceeds maximum {threshold.maximum}",
            )

        if threshold.minimum is not None and current_value < threshold.minimum:
            return RegressionResult(
                metric_name=metric_name,
                current_value=current_value,
                baseline_p50=threshold.P50,
                baseline_p95=threshold.P95,
                severity=RegressionSeverity.CRITICAL,
                deviation_pct=1.0,
                should_block=True,
                error_code="GS_094",
                message=f"{metric_name}: {current_value} below minimum {threshold.minimum}",
            )

        # Calculate deviation from P50
        if is_inverted:
            # Higher values are worse (e.g., time, violations)
            if threshold.P50 == 0:
                # Any non-zero is regression for zero-tolerance metrics
                if current_value > 0:
                    return RegressionResult(
                        metric_name=metric_name,
                        current_value=current_value,
                        baseline_p50=threshold.P50,
                        baseline_p95=threshold.P95,
                        severity=RegressionSeverity.CRITICAL,
                        deviation_pct=1.0,
                        should_block=True,
                        error_code="GS_094",
                        message=f"{metric_name}: {current_value} > 0 (zero-tolerance metric)",
                    )
                deviation_pct = 0.0
            else:
                deviation_pct = (current_value - threshold.P50) / threshold.P50
        else:
            # Lower values are worse (e.g., accuracy, compliance)
            if threshold.P50 == 0:
                deviation_pct = 0.0 if current_value == 0 else 1.0
            else:
                deviation_pct = (threshold.P50 - current_value) / threshold.P50

        # Determine severity based on deviation
        if deviation_pct <= 0:
            severity = RegressionSeverity.NONE
        elif deviation_pct < self.SEVERITY_THRESHOLDS["MODERATE"]:
            severity = RegressionSeverity.MINOR
        elif deviation_pct < self.SEVERITY_THRESHOLDS["SEVERE"]:
            severity = RegressionSeverity.MODERATE
        elif deviation_pct < self.SEVERITY_THRESHOLDS["CRITICAL"]:
            severity = RegressionSeverity.SEVERE
        else:
            severity = RegressionSeverity.CRITICAL

        # Determine if should block
        should_block = severity in (RegressionSeverity.SEVERE, RegressionSeverity.CRITICAL)
        error_code = "GS_094" if should_block else None

        # Build message
        if severity == RegressionSeverity.NONE:
            message = f"{metric_name}: {current_value} meets baseline P50={threshold.P50}"
        else:
            direction = "above" if is_inverted else "below"
            message = f"{metric_name}: {current_value} is {deviation_pct:.1%} {direction} baseline P50={threshold.P50}"

        return RegressionResult(
            metric_name=metric_name,
            current_value=current_value,
            baseline_p50=threshold.P50,
            baseline_p95=threshold.P95,
            severity=severity,
            deviation_pct=deviation_pct,
            should_block=should_block,
            error_code=error_code,
            message=message,
        )


def evaluate_regression(
    agent_gid: str,
    agent_name: str,
    execution_lane: str,
    metrics: Dict[str, float],
) -> Tuple[bool, List[str]]:
    """
    Convenience function for gate_pack.py integration.

    Returns:
        Tuple of (has_regression, error_messages)
    """
    evaluator = RegressionEvaluator()
    report = evaluator.evaluate(
        agent_gid=agent_gid,
        agent_name=agent_name,
        execution_lane=execution_lane,
        metrics=metrics,
    )

    errors = []
    if report.has_blocking_regression:
        for r in report.regressions:
            if r.should_block:
                errors.append(f"[GS_094] {r.message}")

    return (report.has_blocking_regression, errors)


def main():
    """CLI entry point for regression evaluation."""
    import argparse
    import json
    import time

    parser = argparse.ArgumentParser(
        description="Evaluate metrics against baselines for regression detection"
    )
    parser.add_argument("--gid", required=True, help="Agent GID (e.g., GID-01)")
    parser.add_argument("--name", required=True, help="Agent name (e.g., Cody)")
    parser.add_argument("--lane", required=True, help="Execution lane (e.g., BACKEND)")
    parser.add_argument(
        "--metrics",
        required=True,
        help="JSON string of metrics (e.g., '{\"first_pass_validity\": 0.5}')",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args()

    try:
        metrics = json.loads(args.metrics)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid metrics JSON: {e}")
        return 1

    start_time = time.time()

    evaluator = RegressionEvaluator()
    report = evaluator.evaluate(
        agent_gid=args.gid,
        agent_name=args.name,
        execution_lane=args.lane,
        metrics=metrics,
    )
    report.execution_time_ms = int((time.time() - start_time) * 1000)

    if args.format == "json":
        output = {
            "agent_gid": report.agent_gid,
            "agent_name": report.agent_name,
            "execution_lane": report.execution_lane,
            "total_metrics_evaluated": report.total_metrics_evaluated,
            "has_blocking_regression": report.has_blocking_regression,
            "execution_time_ms": report.execution_time_ms,
            "regressions": [
                {
                    "metric_name": r.metric_name,
                    "current_value": r.current_value,
                    "baseline_p50": r.baseline_p50,
                    "severity": r.severity.value,
                    "deviation_pct": r.deviation_pct,
                    "should_block": r.should_block,
                    "error_code": r.error_code,
                    "message": r.message,
                }
                for r in report.regressions
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 70)
        print("REGRESSION EVALUATION REPORT")
        print("=" * 70)
        print(f"Agent: {report.agent_name} ({report.agent_gid})")
        print(f"Lane: {report.execution_lane}")
        print(f"Metrics Evaluated: {report.total_metrics_evaluated}")
        print(f"Execution Time: {report.execution_time_ms}ms")
        print("-" * 70)

        if not report.regressions:
            print("✓ NO REGRESSIONS DETECTED")
        else:
            for r in report.regressions:
                icon = "✗" if r.should_block else "⚠"
                print(f"{icon} [{r.severity.value}] {r.message}")

        print("-" * 70)
        print(report.summary)
        print("=" * 70)

    return 1 if report.has_blocking_regression else 0


if __name__ == "__main__":
    exit(main())
