# ═══════════════════════════════════════════════════════════════════════════════
# OCC Memory Panel — Neural Memory Visualization (Read-Only)
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agents: SONNY (GID-02), LIRA (GID-09)
# ═══════════════════════════════════════════════════════════════════════════════

"""
OCC Memory Panel — Operator Control Center Memory Visualization

PURPOSE:
    Provide read-only visualization of neural memory state for operators.
    Displays memory health, snapshot chain, routing statistics, and
    invariant compliance status.

UI COMPONENTS:
    1. MemoryStateCard - Current memory hash and tier status
    2. SnapshotChainView - Visualization of snapshot history
    3. RoutingStatsPanel - Dual-brain routing statistics
    4. InvariantComplianceMatrix - INV-MEM-* status grid

ACCESSIBILITY (LIRA):
    - WCAG 2.1 AA compliant
    - Screen reader labels
    - Keyboard navigation
    - High contrast mode support
    - Focus indicators

LANE: ARCHITECTURE_ONLY (NON-INFERENCING)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.ml.neural_memory import (
    MemoryMode,
    MemorySnapshot,
    MemoryStateHash,
    MemoryTier,
    SnapshotStatus,
)


# ═══════════════════════════════════════════════════════════════════════════════
# UI COMPONENT ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class PanelTheme(Enum):
    """Theme for memory panel display."""

    LIGHT = "LIGHT"
    DARK = "DARK"
    HIGH_CONTRAST = "HIGH_CONTRAST"  # WCAG AA compliant


class HealthStatus(Enum):
    """Health status indicators."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class ComponentSize(Enum):
    """Size variants for UI components."""

    COMPACT = "COMPACT"
    STANDARD = "STANDARD"
    EXPANDED = "EXPANDED"


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY STATE CARD
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class MemoryStateCard:
    """
    UI component displaying current memory state.

    Shows:
    - Current memory mode (SHADOW/INFERENCE/FROZEN)
    - Memory tier (FAST/SLOW/HYBRID)
    - State hash (truncated for display)
    - Entry count
    - Last update timestamp

    Accessibility: role="status", aria-live="polite"
    """

    state_hash: MemoryStateHash
    mode: MemoryMode
    health: HealthStatus = HealthStatus.HEALTHY
    theme: PanelTheme = PanelTheme.DARK
    size: ComponentSize = ComponentSize.STANDARD

    # Accessibility attributes
    aria_label: str = "Memory state status card"
    aria_live: str = "polite"
    role: str = "status"
    tabindex: int = 0

    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to display dictionary for UI rendering."""
        return {
            "component": "MemoryStateCard",
            "data": {
                "hash_preview": self.state_hash.hash_value[:16] + "...",
                "full_hash": self.state_hash.hash_value,
                "mode": self.mode.value,
                "tier": self.state_hash.memory_tier.value,
                "entry_count": self.state_hash.entry_count,
                "timestamp": self.state_hash.timestamp,
                "health": self.health.value,
            },
            "display": {
                "theme": self.theme.value,
                "size": self.size.value,
            },
            "accessibility": {
                "aria-label": self.aria_label,
                "aria-live": self.aria_live,
                "role": self.role,
                "tabindex": self.tabindex,
            },
        }

    def get_status_color(self) -> str:
        """Get status indicator color."""
        colors = {
            HealthStatus.HEALTHY: "#10B981",  # Green
            HealthStatus.DEGRADED: "#F59E0B",  # Amber
            HealthStatus.CRITICAL: "#EF4444",  # Red
            HealthStatus.UNKNOWN: "#6B7280",  # Gray
        }
        return colors.get(self.health, "#6B7280")


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT CHAIN VIEW
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SnapshotNode:
    """Visual node in snapshot chain."""

    snapshot_id: str
    status: SnapshotStatus
    created_at: str
    hash_preview: str
    is_current: bool = False
    is_anchored: bool = False

    def get_status_icon(self) -> str:
        """Get icon for snapshot status."""
        icons = {
            SnapshotStatus.PENDING: "⏳",
            SnapshotStatus.COMPLETE: "✓",
            SnapshotStatus.VERIFIED: "✓✓",
            SnapshotStatus.ANCHORED: "⚓",
            SnapshotStatus.ROLLED_BACK: "↩",
        }
        return icons.get(self.status, "•")


@dataclass
class SnapshotChainView:
    """
    UI component displaying snapshot chain history.

    Visualizes the chain of memory snapshots with:
    - Chain linkage visualization
    - Status indicators
    - Anchor status
    - Rollback markers

    Accessibility: role="list", keyboard navigable
    """

    nodes: List[SnapshotNode] = field(default_factory=list)
    max_display: int = 10
    theme: PanelTheme = PanelTheme.DARK

    # Accessibility
    aria_label: str = "Memory snapshot chain"
    role: str = "list"

    @classmethod
    def from_snapshots(cls, snapshots: List[MemorySnapshot], current_id: Optional[str] = None) -> "SnapshotChainView":
        """Create view from snapshot list."""
        nodes = []
        for snap in snapshots:
            nodes.append(SnapshotNode(
                snapshot_id=snap.snapshot_id,
                status=snap.status,
                created_at=snap.created_at,
                hash_preview=snap.state_hash.hash_value[:12],
                is_current=(snap.snapshot_id == current_id),
                is_anchored=snap.is_anchored(),
            ))
        return cls(nodes=nodes)

    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to display dictionary."""
        return {
            "component": "SnapshotChainView",
            "data": {
                "nodes": [
                    {
                        "id": n.snapshot_id,
                        "status": n.status.value,
                        "status_icon": n.get_status_icon(),
                        "created_at": n.created_at,
                        "hash_preview": n.hash_preview,
                        "is_current": n.is_current,
                        "is_anchored": n.is_anchored,
                    }
                    for n in self.nodes[-self.max_display:]
                ],
                "total_count": len(self.nodes),
                "displayed_count": min(len(self.nodes), self.max_display),
            },
            "accessibility": {
                "aria-label": self.aria_label,
                "role": self.role,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING STATS PANEL
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RoutingStatsPanel:
    """
    UI component displaying dual-brain routing statistics.

    Shows:
    - Total routing decisions
    - Fast vs Slow distribution
    - Hybrid routing count
    - Average confidence
    - Recent routing trend

    Accessibility: role="region", aria-labelledby
    """

    fast_count: int = 0
    slow_count: int = 0
    hybrid_count: int = 0
    fallback_count: int = 0
    total_decisions: int = 0
    avg_confidence: float = 0.0
    theme: PanelTheme = PanelTheme.DARK

    # Accessibility
    aria_label: str = "Dual-brain routing statistics"
    role: str = "region"

    @classmethod
    def from_stats(cls, stats: Dict[str, Any]) -> "RoutingStatsPanel":
        """Create panel from statistics dictionary."""
        return cls(
            fast_count=stats.get("fast_count", 0),
            slow_count=stats.get("slow_count", 0),
            hybrid_count=stats.get("hybrid_count", 0),
            fallback_count=stats.get("fallback_count", 0),
            total_decisions=stats.get("total_decisions", 0),
            avg_confidence=stats.get("avg_confidence", 0.0),
        )

    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to display dictionary."""
        fast_pct = (self.fast_count / self.total_decisions * 100) if self.total_decisions > 0 else 0
        slow_pct = (self.slow_count / self.total_decisions * 100) if self.total_decisions > 0 else 0
        hybrid_pct = (self.hybrid_count / self.total_decisions * 100) if self.total_decisions > 0 else 0

        return {
            "component": "RoutingStatsPanel",
            "data": {
                "fast": {
                    "count": self.fast_count,
                    "percentage": round(fast_pct, 1),
                    "label": "Fast (Attention)",
                },
                "slow": {
                    "count": self.slow_count,
                    "percentage": round(slow_pct, 1),
                    "label": "Slow (Persistent)",
                },
                "hybrid": {
                    "count": self.hybrid_count,
                    "percentage": round(hybrid_pct, 1),
                    "label": "Hybrid",
                },
                "fallback": {
                    "count": self.fallback_count,
                    "label": "Fallback",
                },
                "total": self.total_decisions,
                "avg_confidence": round(self.avg_confidence, 3),
            },
            "accessibility": {
                "aria-label": self.aria_label,
                "role": self.role,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT COMPLIANCE MATRIX
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class InvariantStatusRow:
    """Status row for single invariant."""

    invariant_id: str
    name: str
    status: str  # "PASS" | "FAIL" | "WARN" | "SKIP"
    last_checked: str
    violation_count: int = 0

    def get_status_color(self) -> str:
        """Get color for status."""
        colors = {
            "PASS": "#10B981",
            "FAIL": "#EF4444",
            "WARN": "#F59E0B",
            "SKIP": "#6B7280",
        }
        return colors.get(self.status, "#6B7280")


@dataclass
class InvariantComplianceMatrix:
    """
    UI component displaying INV-MEM-* compliance status.

    Shows grid of all memory invariants with:
    - Pass/Fail status
    - Violation count
    - Last check timestamp
    - Enforcement mode

    Accessibility: role="grid", aria-describedby
    """

    rows: List[InvariantStatusRow] = field(default_factory=list)
    overall_status: str = "PASS"
    theme: PanelTheme = PanelTheme.DARK

    # Accessibility
    aria_label: str = "Memory invariant compliance matrix"
    role: str = "grid"
    aria_describedby: str = "compliance-description"

    def add_invariant(
        self,
        invariant_id: str,
        name: str,
        status: str,
        violation_count: int = 0,
    ) -> None:
        """Add invariant status row."""
        self.rows.append(InvariantStatusRow(
            invariant_id=invariant_id,
            name=name,
            status=status,
            last_checked=datetime.now(timezone.utc).isoformat(),
            violation_count=violation_count,
        ))
        # Update overall status
        if status == "FAIL":
            self.overall_status = "FAIL"
        elif status == "WARN" and self.overall_status != "FAIL":
            self.overall_status = "WARN"

    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to display dictionary."""
        return {
            "component": "InvariantComplianceMatrix",
            "data": {
                "rows": [
                    {
                        "id": r.invariant_id,
                        "name": r.name,
                        "status": r.status,
                        "status_color": r.get_status_color(),
                        "last_checked": r.last_checked,
                        "violation_count": r.violation_count,
                    }
                    for r in self.rows
                ],
                "overall_status": self.overall_status,
                "total_invariants": len(self.rows),
                "passing": sum(1 for r in self.rows if r.status == "PASS"),
                "failing": sum(1 for r in self.rows if r.status == "FAIL"),
            },
            "accessibility": {
                "aria-label": self.aria_label,
                "role": self.role,
                "aria-describedby": self.aria_describedby,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# OCC MEMORY PANEL (COMPOSITE)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class OCCMemoryPanel:
    """
    Composite panel for OCC neural memory visualization.

    Combines all memory UI components into single operator panel:
    - Memory state card (top)
    - Snapshot chain view (left)
    - Routing stats panel (right)
    - Invariant compliance matrix (bottom)

    Accessibility: Main landmark with skip navigation
    """

    state_card: Optional[MemoryStateCard] = None
    chain_view: Optional[SnapshotChainView] = None
    stats_panel: Optional[RoutingStatsPanel] = None
    compliance_matrix: Optional[InvariantComplianceMatrix] = None

    theme: PanelTheme = PanelTheme.DARK
    title: str = "Neural Memory Monitor"
    subtitle: str = "Shadow Mode | Read-Only"

    # Accessibility
    aria_label: str = "Neural memory monitoring panel"
    role: str = "main"
    skip_link_target: str = "memory-panel-main"

    def is_complete(self) -> bool:
        """Check if all components are loaded."""
        return all([
            self.state_card is not None,
            self.chain_view is not None,
            self.stats_panel is not None,
            self.compliance_matrix is not None,
        ])

    def get_overall_health(self) -> HealthStatus:
        """Get overall panel health status."""
        if not self.is_complete():
            return HealthStatus.UNKNOWN

        # Check state card health
        if self.state_card and self.state_card.health == HealthStatus.CRITICAL:
            return HealthStatus.CRITICAL

        # Check compliance matrix
        if self.compliance_matrix and self.compliance_matrix.overall_status == "FAIL":
            return HealthStatus.CRITICAL

        if self.compliance_matrix and self.compliance_matrix.overall_status == "WARN":
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to display dictionary for UI rendering."""
        return {
            "component": "OCCMemoryPanel",
            "header": {
                "title": self.title,
                "subtitle": self.subtitle,
                "health": self.get_overall_health().value,
                "theme": self.theme.value,
            },
            "components": {
                "state_card": self.state_card.to_display_dict() if self.state_card else None,
                "chain_view": self.chain_view.to_display_dict() if self.chain_view else None,
                "stats_panel": self.stats_panel.to_display_dict() if self.stats_panel else None,
                "compliance_matrix": self.compliance_matrix.to_display_dict() if self.compliance_matrix else None,
            },
            "layout": {
                "grid": "2x2",
                "state_card_position": "top-span",
                "chain_view_position": "bottom-left",
                "stats_panel_position": "bottom-right",
                "compliance_matrix_position": "footer",
            },
            "accessibility": {
                "aria-label": self.aria_label,
                "role": self.role,
                "skip_link": {
                    "text": "Skip to memory panel",
                    "target": self.skip_link_target,
                },
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PANEL FACTORY
# ═══════════════════════════════════════════════════════════════════════════════


class MemoryPanelFactory:
    """Factory for creating OCC memory panel components."""

    @staticmethod
    def create_state_card(
        state_hash: MemoryStateHash,
        mode: MemoryMode,
        theme: PanelTheme = PanelTheme.DARK,
    ) -> MemoryStateCard:
        """Create memory state card."""
        return MemoryStateCard(
            state_hash=state_hash,
            mode=mode,
            theme=theme,
        )

    @staticmethod
    def create_chain_view(
        snapshots: List[MemorySnapshot],
        current_id: Optional[str] = None,
    ) -> SnapshotChainView:
        """Create snapshot chain view."""
        return SnapshotChainView.from_snapshots(snapshots, current_id)

    @staticmethod
    def create_stats_panel(stats: Dict[str, Any]) -> RoutingStatsPanel:
        """Create routing stats panel."""
        return RoutingStatsPanel.from_stats(stats)

    @staticmethod
    def create_compliance_matrix(
        invariant_results: Dict[str, bool],
    ) -> InvariantComplianceMatrix:
        """Create invariant compliance matrix."""
        matrix = InvariantComplianceMatrix()
        for inv_id, passed in invariant_results.items():
            matrix.add_invariant(
                invariant_id=inv_id,
                name=inv_id.replace("INV-MEM-", "Memory "),
                status="PASS" if passed else "FAIL",
            )
        return matrix

    @classmethod
    def create_full_panel(
        cls,
        state_hash: MemoryStateHash,
        mode: MemoryMode,
        snapshots: List[MemorySnapshot],
        routing_stats: Dict[str, Any],
        invariant_results: Dict[str, bool],
        theme: PanelTheme = PanelTheme.DARK,
    ) -> OCCMemoryPanel:
        """Create complete OCC memory panel."""
        return OCCMemoryPanel(
            state_card=cls.create_state_card(state_hash, mode, theme),
            chain_view=cls.create_chain_view(snapshots),
            stats_panel=cls.create_stats_panel(routing_stats),
            compliance_matrix=cls.create_compliance_matrix(invariant_results),
            theme=theme,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "PanelTheme",
    "HealthStatus",
    "ComponentSize",
    # Data classes
    "MemoryStateCard",
    "SnapshotNode",
    "SnapshotChainView",
    "RoutingStatsPanel",
    "InvariantStatusRow",
    "InvariantComplianceMatrix",
    "OCCMemoryPanel",
    # Factory
    "MemoryPanelFactory",
]
