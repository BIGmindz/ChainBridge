"""
Shard Visibility Panel - OCC Integration for Execution Sharding
PAC-P750-SWARM-EXECUTION-SHARDING-DOCTRINE-AND-IMPLEMENTATION
TASK-04 & TASK-05: Bind shards to Heartbeat + Task Manifest & Expose shard visibility in OCC

Provides:
- Real-time shard status visualization
- Resource utilization monitoring
- Authority decision queue display
- Heartbeat integration
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from pathlib import Path

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False


def get_shard_manager():
    """Import shard manager lazily."""
    from ChainBridge.core.execution.shard_manager import get_shard_manager as _get
    return _get()


def get_shard_policy_enforcer():
    """Import policy enforcer lazily."""
    from ChainBridge.core.execution.shard_policy import get_shard_policy_enforcer as _get
    return _get()


class ShardVisibilityPanel:
    """
    OCC panel for shard execution visibility.
    
    Displays:
    - Active shards and their status
    - Resource utilization per shard
    - Recomposition progress
    - Policy violations and SCRAM status
    """

    def __init__(self):
        self._last_refresh = None

    def get_shard_summary(self) -> dict[str, Any]:
        """Get comprehensive shard summary for OCC."""
        manager = get_shard_manager()
        enforcer = get_shard_policy_enforcer()

        heartbeat = manager.get_manager_heartbeat()
        scram_status = enforcer.get_scram_status()
        violation_summary = enforcer.get_violation_summary()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "authority": "BENSON (GID-00)",
            "core_law": "Authority is singular. Execution may shard. Judgment MUST NOT shard.",
            
            "shard_metrics": {
                "active": heartbeat["active_shards"],
                "completed": heartbeat["completed_shards"],
                "failed": heartbeat["failed_shards"],
                "total": heartbeat["total_shards"]
            },
            
            "health": {
                "status": "SCRAM" if scram_status["active"] else heartbeat["aggregate_status"],
                "scram_active": scram_status["active"],
                "scram_reason": scram_status["reason"],
                "blocked_shards": len(scram_status["blocked_shards"])
            },
            
            "violations": violation_summary,
            
            "active_shards": manager.get_active_shards()
        }

    def format_for_display(self, summary: dict[str, Any]) -> str:
        """Format summary for text display."""
        lines = [
            "═" * 60,
            "  EXECUTION SHARDING - OCC VISIBILITY PANEL",
            "═" * 60,
            f"  Core Law: {summary['core_law']}",
            f"  Authority: {summary['authority']}",
            "─" * 60,
            "",
            "  SHARD METRICS",
            f"    Active:    {summary['shard_metrics']['active']}",
            f"    Completed: {summary['shard_metrics']['completed']}",
            f"    Failed:    {summary['shard_metrics']['failed']}",
            f"    Total:     {summary['shard_metrics']['total']}",
            "",
            "  HEALTH STATUS",
            f"    Status:      {summary['health']['status']}",
            f"    SCRAM:       {'🔴 ACTIVE' if summary['health']['scram_active'] else '🟢 CLEAR'}",
        ]

        if summary['health']['scram_reason']:
            lines.append(f"    Reason:      {summary['health']['scram_reason']}")

        lines.extend([
            "",
            "  VIOLATIONS",
            f"    Total:       {summary['violations']['total_violations']}",
            f"    Blocked:     {summary['violations']['blocked_shards']}",
        ])

        if summary['active_shards']:
            lines.extend([
                "",
                "  ACTIVE SHARDS",
                "  ─────────────"
            ])
            for shard in summary['active_shards'][:5]:  # Show top 5
                lines.append(f"    {shard['shard_id']}: {shard['status']}")

        lines.extend([
            "",
            "═" * 60,
            f"  Updated: {summary['timestamp']}",
            "═" * 60
        ])

        return "\n".join(lines)

    def render_streamlit(self) -> None:
        """Render panel in Streamlit."""
        if not STREAMLIT_AVAILABLE:
            return

        summary = self.get_shard_summary()

        st.header("⚡ Execution Sharding Panel")
        st.caption(f"Core Law: {summary['core_law']}")

        # Health indicator
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status = summary['health']['status']
            color = "🔴" if status == "SCRAM" else "🟡" if status == "DEGRADED" else "🟢"
            st.metric("Status", f"{color} {status}")
        
        with col2:
            st.metric("Active Shards", summary['shard_metrics']['active'])
        
        with col3:
            st.metric("Completed", summary['shard_metrics']['completed'])

        # SCRAM alert
        if summary['health']['scram_active']:
            st.error(f"⚠️ SCRAM ACTIVE: {summary['health']['scram_reason']}")

        # Shard metrics
        st.subheader("Shard Metrics")
        metrics = summary['shard_metrics']
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Active", metrics['active'])
        col2.metric("Completed", metrics['completed'])
        col3.metric("Failed", metrics['failed'])
        col4.metric("Total", metrics['total'])

        # Progress bar
        if metrics['total'] > 0:
            progress = metrics['completed'] / metrics['total']
            st.progress(progress, text=f"Completion: {progress*100:.1f}%")

        # Active shards table
        if summary['active_shards']:
            st.subheader("Active Shards")
            shard_data = []
            for s in summary['active_shards']:
                shard_data.append({
                    "Shard ID": s['shard_id'],
                    "Task": s['task_id'],
                    "Status": s['status'],
                    "Heartbeats": s['heartbeat_count']
                })
            st.dataframe(shard_data, use_container_width=True)

        # Violations
        if summary['violations']['total_violations'] > 0:
            st.subheader("⚠️ Policy Violations")
            st.json(summary['violations'])

        st.caption(f"Last updated: {summary['timestamp']}")


def generate_shard_heartbeat_binding() -> dict[str, Any]:
    """
    Generate heartbeat binding configuration for shards.
    
    Integrates with P744-P746 heartbeat system.
    """
    return {
        "binding_type": "SHARD_HEARTBEAT",
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        
        "shard_heartbeat_config": {
            "frequency_ms": 5000,
            "fields": [
                "shard_id",
                "status",
                "progress_percent",
                "resource_usage.memory_mb",
                "resource_usage.cpu_percent",
                "work_unit.work_id"
            ],
            "destination": "SHARD_MANAGER"
        },
        
        "manager_heartbeat_config": {
            "frequency_ms": 10000,
            "fields": [
                "active_shards",
                "completed_shards",
                "failed_shards",
                "aggregate_status",
                "authority"
            ],
            "destination": "OCC"
        },
        
        "task_manifest_binding": {
            "shard_as_subtask": true,
            "parent_task_reference": "required",
            "pac_reference": "required",
            "visibility_level": "FULL"
        },
        
        "invariants": [
            "Shard heartbeats flow to ShardManager only",
            "Manager heartbeats flow to OCC",
            "No lateral heartbeat communication"
        ]
    }


def generate_task_manifest_integration() -> dict[str, Any]:
    """
    Generate task manifest integration for shards.
    
    Shards appear as bounded subtasks in task progression.
    """
    return {
        "integration_type": "SHARD_TASK_MANIFEST",
        "version": "1.0.0",
        
        "shard_task_schema": {
            "type": "SHARD_SUBTASK",
            "properties": {
                "shard_id": {"type": "string", "required": True},
                "parent_task_id": {"type": "string", "required": True},
                "pac_reference": {"type": "string", "required": True},
                "work_unit_hash": {"type": "string", "required": True},
                "status": {
                    "type": "enum",
                    "values": ["PENDING", "RUNNING", "COMPLETED", "FAILED", "TIMEOUT", "TERMINATED"]
                },
                "bounds": {
                    "max_time_seconds": {"type": "number"},
                    "max_memory_mb": {"type": "number"}
                }
            }
        },
        
        "visibility_rules": {
            "show_in_task_tree": True,
            "show_resource_usage": True,
            "show_progress": True,
            "aggregate_to_parent": True
        },
        
        "authority_display": {
            "judgment_pending_indicator": True,
            "authority_badge": "BENSON (GID-00)",
            "shard_execution_only_marker": True
        }
    }


# Singleton instance
_visibility_panel: Optional[ShardVisibilityPanel] = None


def get_shard_visibility_panel() -> ShardVisibilityPanel:
    """Get global visibility panel instance."""
    global _visibility_panel
    if _visibility_panel is None:
        _visibility_panel = ShardVisibilityPanel()
    return _visibility_panel


def render_shard_panel() -> None:
    """Convenience function to render shard panel."""
    panel = get_shard_visibility_panel()
    if STREAMLIT_AVAILABLE:
        panel.render_streamlit()
    else:
        summary = panel.get_shard_summary()
        print(panel.format_for_display(summary))
