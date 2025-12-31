"""
Metrics Extractor for ChainBridge Governance.

Authority: PAC-BENSON-P37-AGENT-PERFORMANCE-METRICS-BASELINE-AND-ENFORCEMENT-01

This module extracts and aggregates metrics from governance artifacts
for ledger recording and baseline comparison.
"""

import re
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MetricsRecord:
    """A single metrics record extracted from an artifact."""
    artifact_id: str
    agent_gid: str
    agent_name: str
    execution_lane: str
    timestamp: str

    # Required metrics
    execution_time_ms: int
    tasks_completed: int
    tasks_total: int
    quality_score: float
    scope_compliance: bool

    # Optional metrics
    files_created: Optional[int] = None
    files_modified: Optional[int] = None
    lines_added: Optional[int] = None
    lines_removed: Optional[int] = None
    errors_encountered: Optional[int] = None
    errors_resolved: Optional[int] = None
    ci_validation_passed: Optional[bool] = None

    # Lane-specific metrics
    lane_specific: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentBaseline:
    """Baseline metrics for an agent."""
    agent_gid: str
    agent_name: str
    execution_lane: str

    # Aggregated metrics
    avg_execution_time_ms: float
    avg_quality_score: float
    scope_compliance_rate: float
    task_completion_rate: float
    total_executions: int


class MetricsExtractor:
    """
    Extract metrics from governance artifacts.

    Supports:
    - PAC artifacts with METRICS blocks
    - WRAP artifacts with METRICS blocks
    - Ledger integration for recording
    """

    REQUIRED_FIELDS = [
        "execution_time_ms",
        "tasks_completed",
        "tasks_total",
        "quality_score",
        "scope_compliance",
    ]

    def __init__(self):
        self.records: List[MetricsRecord] = []

    def extract_from_content(self, content: str) -> Optional[MetricsRecord]:
        """
        Extract metrics from artifact content.

        Returns MetricsRecord or None if no valid METRICS block found.
        """
        # Extract artifact ID
        artifact_id = self._extract_artifact_id(content)
        if not artifact_id:
            return None

        # Extract agent info
        agent_info = self._extract_agent_info(content)

        # Extract METRICS block
        metrics = self._extract_metrics_block(content)
        if not metrics:
            return None

        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            if field not in metrics:
                return None

        # Build record
        record = MetricsRecord(
            artifact_id=artifact_id,
            agent_gid=agent_info.get("gid", "UNKNOWN"),
            agent_name=agent_info.get("name", "UNKNOWN"),
            execution_lane=agent_info.get("execution_lane", "UNKNOWN"),
            timestamp=datetime.utcnow().isoformat() + "Z",
            execution_time_ms=int(metrics.get("execution_time_ms", 0)),
            tasks_completed=int(metrics.get("tasks_completed", 0)),
            tasks_total=int(metrics.get("tasks_total", 1)),
            quality_score=float(metrics.get("quality_score", 0.0)),
            scope_compliance=bool(metrics.get("scope_compliance", False)),
            files_created=metrics.get("files_created"),
            files_modified=metrics.get("files_modified"),
            lines_added=metrics.get("lines_added"),
            lines_removed=metrics.get("lines_removed"),
            errors_encountered=metrics.get("errors_encountered"),
            errors_resolved=metrics.get("errors_resolved"),
            ci_validation_passed=metrics.get("ci_validation_passed"),
            lane_specific=metrics.get("lane_specific", {}),
        )

        self.records.append(record)
        return record

    def extract_from_file(self, file_path: Path) -> Optional[MetricsRecord]:
        """Extract metrics from a file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            return self.extract_from_content(content)
        except Exception:
            return None

    def extract_from_directory(self, dir_path: Path) -> List[MetricsRecord]:
        """Extract metrics from all artifacts in a directory."""
        records = []

        for file_path in dir_path.glob("**/*.md"):
            record = self.extract_from_file(file_path)
            if record:
                records.append(record)

        return records

    def compute_agent_baseline(self, agent_gid: str) -> Optional[AgentBaseline]:
        """Compute baseline metrics for an agent from recorded data."""
        agent_records = [r for r in self.records if r.agent_gid == agent_gid]

        if not agent_records:
            return None

        # Compute aggregates
        total = len(agent_records)
        avg_time = sum(r.execution_time_ms for r in agent_records) / total
        avg_quality = sum(r.quality_score for r in agent_records) / total
        scope_rate = sum(1 for r in agent_records if r.scope_compliance) / total

        task_completion = sum(r.tasks_completed for r in agent_records) / sum(r.tasks_total for r in agent_records)

        return AgentBaseline(
            agent_gid=agent_gid,
            agent_name=agent_records[0].agent_name,
            execution_lane=agent_records[0].execution_lane,
            avg_execution_time_ms=avg_time,
            avg_quality_score=avg_quality,
            scope_compliance_rate=scope_rate,
            task_completion_rate=task_completion,
            total_executions=total,
        )

    def compute_lane_baseline(self, execution_lane: str) -> Dict[str, float]:
        """Compute baseline metrics for an execution lane."""
        lane_records = [r for r in self.records if r.execution_lane == execution_lane]

        if not lane_records:
            return {}

        total = len(lane_records)
        return {
            "avg_execution_time_ms": sum(r.execution_time_ms for r in lane_records) / total,
            "avg_quality_score": sum(r.quality_score for r in lane_records) / total,
            "scope_compliance_rate": sum(1 for r in lane_records if r.scope_compliance) / total,
            "total_executions": total,
        }

    def to_ledger_format(self, record: MetricsRecord) -> Dict[str, Any]:
        """Convert record to ledger-compatible format."""
        return {
            "artifact_id": record.artifact_id,
            "agent_gid": record.agent_gid,
            "agent_name": record.agent_name,
            "execution_lane": record.execution_lane,
            "timestamp": record.timestamp,
            "metrics": {
                "execution_time_ms": record.execution_time_ms,
                "tasks_completed": record.tasks_completed,
                "tasks_total": record.tasks_total,
                "quality_score": record.quality_score,
                "scope_compliance": record.scope_compliance,
            },
            "optional_metrics": {
                k: v for k, v in {
                    "files_created": record.files_created,
                    "files_modified": record.files_modified,
                    "lines_added": record.lines_added,
                    "lines_removed": record.lines_removed,
                    "errors_encountered": record.errors_encountered,
                    "errors_resolved": record.errors_resolved,
                    "ci_validation_passed": record.ci_validation_passed,
                }.items() if v is not None
            },
        }

    def _extract_artifact_id(self, content: str) -> Optional[str]:
        """Extract PAC or WRAP ID from content."""
        # PAC pattern
        pac_match = re.search(r'(PAC-[A-Z]+-[A-Z0-9]+-[A-Z0-9-]+)', content)
        if pac_match:
            return pac_match.group(1)

        # WRAP pattern
        wrap_match = re.search(r'(WRAP-[A-Z]+-G\d+-[A-Z0-9-]+)', content)
        if wrap_match:
            return wrap_match.group(1)

        return None

    def _extract_agent_info(self, content: str) -> Dict[str, str]:
        """Extract agent information from content."""
        info = {}

        # Extract from AGENT_ACTIVATION_ACK
        gid_match = re.search(r'gid:\s*["\']?(GID-\d+)["\']?', content, re.IGNORECASE)
        if gid_match:
            info["gid"] = gid_match.group(1)

        name_match = re.search(r'agent_name:\s*["\']?([A-Z][A-Za-z]+)["\']?', content, re.IGNORECASE)
        if name_match:
            info["name"] = name_match.group(1).upper()

        lane_match = re.search(r'execution_lane:\s*["\']?([A-Z_]+)["\']?', content, re.IGNORECASE)
        if lane_match:
            info["execution_lane"] = lane_match.group(1).upper()

        return info

    def _extract_metrics_block(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract METRICS block from content."""
        # Pattern 1: YAML code block
        yaml_pattern = r"```(?:yaml|yml)?\s*\n(METRICS:\s*.*?)```"
        match = re.search(yaml_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                parsed = yaml.safe_load(match.group(1))
                if isinstance(parsed, dict) and "METRICS" in parsed:
                    return parsed.get("METRICS", parsed)
                return parsed
            except yaml.YAMLError:
                pass

        # Pattern 2: Inline YAML
        inline_pattern = r"^METRICS:\s*\n((?:[ \t]+[^\n]+\n?)+)"
        match = re.search(inline_pattern, content, re.MULTILINE | re.IGNORECASE)
        if match:
            try:
                full_yaml = f"METRICS:\n{match.group(1)}"
                parsed = yaml.safe_load(full_yaml)
                if isinstance(parsed, dict):
                    return parsed.get("METRICS", parsed)
                return parsed
            except yaml.YAMLError:
                pass

        return None


def main():
    """CLI entry point for metrics extraction."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Extract metrics from governance artifacts")
    parser.add_argument("path", help="File or directory path")
    parser.add_argument("--format", choices=["json", "yaml"], default="json", help="Output format")
    parser.add_argument("--baseline", help="Compute baseline for agent GID")

    args = parser.parse_args()

    extractor = MetricsExtractor()
    path = Path(args.path)

    if path.is_file():
        record = extractor.extract_from_file(path)
        if record:
            print(json.dumps(extractor.to_ledger_format(record), indent=2))
        else:
            print("No valid METRICS block found")
    elif path.is_dir():
        records = extractor.extract_from_directory(path)
        print(f"Extracted {len(records)} metrics records")

        if args.baseline:
            baseline = extractor.compute_agent_baseline(args.baseline)
            if baseline:
                print(f"\nBaseline for {baseline.agent_name} ({baseline.agent_gid}):")
                print(f"  Avg Execution Time: {baseline.avg_execution_time_ms:.0f}ms")
                print(f"  Avg Quality Score: {baseline.avg_quality_score:.2f}")
                print(f"  Scope Compliance Rate: {baseline.scope_compliance_rate:.1%}")
                print(f"  Task Completion Rate: {baseline.task_completion_rate:.1%}")
                print(f"  Total Executions: {baseline.total_executions}")


if __name__ == "__main__":
    main()
