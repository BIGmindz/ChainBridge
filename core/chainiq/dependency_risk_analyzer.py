"""
Dependency-Aware Risk Attribution Engine

Extends PDO Risk Explainer with cross-agent dependency attribution.
Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-LOAD-024.

Agent: GID-10 (Maggie) — ML & Applied AI Lead

Invariant: INV-RISK-010 - Risk explanations must reference upstream agent outputs
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.chainiq.pdo_risk_explainer import (
    RiskExplanation,
    RiskFactor,
    RiskLevel,
    FactorDirection,
    PDORiskExplainer,
    get_risk_explainer,
)
from core.governance.pdo_dependency_graph import (
    PDODependencyGraph,
    DependencyNode,
    DependencyEdge,
    DependencyType,
    NodeStatus,
    get_dependency_graph,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEPENDENCY_RISK_CONFIG = {
    "upstream_risk_weight": 0.3,       # How much upstream risk affects downstream
    "blocked_dependency_risk": 0.9,    # Risk score for blocked dependencies
    "pending_dependency_penalty": 0.1, # Added risk for pending dependencies
    "max_propagation_depth": 5,        # Max depth for risk propagation
}


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyRiskError(Exception):
    """Base exception for dependency-aware risk errors."""
    pass


class UpstreamNotExplainedError(DependencyRiskError):
    """Raised when upstream PDO lacks risk explanation."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class UpstreamRiskContribution:
    """
    Risk contribution from an upstream dependency.
    
    Per INV-RISK-010: References upstream agent output.
    """
    upstream_pdo_id: str
    upstream_agent_gid: str
    upstream_risk_score: float
    upstream_risk_level: RiskLevel
    dependency_type: DependencyType
    contribution_weight: float
    propagated_risk: float
    explanation_summary: str


@dataclass(frozen=True)
class DependencyAwareExplanation:
    """
    Extended risk explanation with dependency attribution.
    
    Implements INV-RISK-010: Must reference upstream agent outputs.
    """
    # Base explanation
    base_explanation: RiskExplanation
    
    # Dependency-specific additions
    upstream_contributions: Tuple[UpstreamRiskContribution, ...]
    dependency_adjusted_score: float
    dependency_risk_summary: str
    
    # Propagation metadata
    propagation_depth: int
    has_blocked_upstream: bool
    has_pending_upstream: bool
    
    # Timestamps
    dependency_analysis_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "base_explanation": self.base_explanation.to_dict(),
            "upstream_contributions": [
                {
                    "upstream_pdo_id": c.upstream_pdo_id,
                    "upstream_agent_gid": c.upstream_agent_gid,
                    "upstream_risk_score": c.upstream_risk_score,
                    "upstream_risk_level": c.upstream_risk_level.value,
                    "dependency_type": c.dependency_type.value,
                    "contribution_weight": c.contribution_weight,
                    "propagated_risk": c.propagated_risk,
                    "explanation_summary": c.explanation_summary,
                }
                for c in self.upstream_contributions
            ],
            "dependency_adjusted_score": self.dependency_adjusted_score,
            "dependency_risk_summary": self.dependency_risk_summary,
            "propagation_depth": self.propagation_depth,
            "has_blocked_upstream": self.has_blocked_upstream,
            "has_pending_upstream": self.has_pending_upstream,
            "dependency_analysis_at": self.dependency_analysis_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY RISK ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyRiskAnalyzer:
    """
    Analyzes risk with awareness of cross-agent dependencies.
    
    Per INV-RISK-010: Ensures explanations reference upstream agent outputs.
    """
    
    def __init__(
        self,
        risk_explainer: Optional[PDORiskExplainer] = None,
        dependency_graph: Optional[PDODependencyGraph] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the dependency risk analyzer."""
        self._risk_explainer = risk_explainer or get_risk_explainer()
        self._dependency_graph = dependency_graph or get_dependency_graph()
        self._config = {**DEPENDENCY_RISK_CONFIG, **(config or {})}
        self._lock = threading.RLock()
        
        # Cache for upstream explanations
        self._upstream_cache: Dict[str, RiskExplanation] = {}

    @property
    def config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    def analyze_upstream_risks(
        self,
        pdo_id: str,
        depth: int = 0,
    ) -> List[UpstreamRiskContribution]:
        """
        Analyze risk contributions from upstream dependencies.
        
        Per INV-RISK-010: Traces risk through dependency chain.
        """
        with self._lock:
            if depth >= self._config["max_propagation_depth"]:
                return []
            
            contributions: List[UpstreamRiskContribution] = []
            
            # Get upstream dependencies
            try:
                upstream_nodes = self._dependency_graph.get_dependencies(pdo_id)
            except Exception:
                return []
            
            for upstream_node in upstream_nodes:
                upstream_id = upstream_node.pdo_id
                
                # Get edge info for dependency type
                edges = self._dependency_graph.get_edges()
                edge = next(
                    (e for e in edges 
                     if e.upstream_pdo_id == upstream_id 
                     and e.downstream_pdo_id == pdo_id),
                    None
                )
                dep_type = edge.dependency_type if edge else DependencyType.DATA
                
                # Check upstream status
                status = self._dependency_graph.get_node_status(upstream_id)
                
                # Get or compute upstream risk
                upstream_explanation = self._get_upstream_explanation(upstream_id)
                
                if upstream_explanation:
                    upstream_risk = upstream_explanation.risk_score
                    upstream_level = upstream_explanation.risk_level
                    summary = upstream_explanation.summary
                elif status == NodeStatus.BLOCKED:
                    upstream_risk = self._config["blocked_dependency_risk"]
                    upstream_level = RiskLevel.CRITICAL
                    summary = f"Upstream {upstream_id} is BLOCKED"
                elif status == NodeStatus.PENDING:
                    upstream_risk = self._config["pending_dependency_penalty"]
                    upstream_level = RiskLevel.MEDIUM
                    summary = f"Upstream {upstream_id} is PENDING (incomplete)"
                else:
                    upstream_risk = 0.0
                    upstream_level = RiskLevel.LOW
                    summary = f"Upstream {upstream_id} has no risk data"
                
                # Calculate propagated risk
                weight = self._config["upstream_risk_weight"]
                propagated = upstream_risk * weight
                
                contribution = UpstreamRiskContribution(
                    upstream_pdo_id=upstream_id,
                    upstream_agent_gid=upstream_node.agent_gid,
                    upstream_risk_score=upstream_risk,
                    upstream_risk_level=upstream_level,
                    dependency_type=dep_type,
                    contribution_weight=weight,
                    propagated_risk=propagated,
                    explanation_summary=summary,
                )
                contributions.append(contribution)
                
                # Recursively analyze upstream of upstream
                nested = self.analyze_upstream_risks(upstream_id, depth + 1)
                # Scale nested contributions by distance
                for nested_contrib in nested:
                    scaled = UpstreamRiskContribution(
                        upstream_pdo_id=nested_contrib.upstream_pdo_id,
                        upstream_agent_gid=nested_contrib.upstream_agent_gid,
                        upstream_risk_score=nested_contrib.upstream_risk_score,
                        upstream_risk_level=nested_contrib.upstream_risk_level,
                        dependency_type=nested_contrib.dependency_type,
                        contribution_weight=nested_contrib.contribution_weight * 0.5,
                        propagated_risk=nested_contrib.propagated_risk * 0.5,
                        explanation_summary=f"[via {upstream_id}] {nested_contrib.explanation_summary}",
                    )
                    contributions.append(scaled)
            
            return contributions

    def _get_upstream_explanation(self, pdo_id: str) -> Optional[RiskExplanation]:
        """Get risk explanation for upstream PDO."""
        # Check cache first
        if pdo_id in self._upstream_cache:
            return self._upstream_cache[pdo_id]
        
        # Query from risk explainer
        explanation = self._risk_explainer.query(pdo_id)
        if explanation:
            self._upstream_cache[pdo_id] = explanation
        
        return explanation

    def cache_upstream_explanation(
        self,
        pdo_id: str,
        explanation: RiskExplanation,
    ) -> None:
        """Cache an upstream explanation for use in dependency analysis."""
        with self._lock:
            self._upstream_cache[pdo_id] = explanation

    def generate_dependency_aware_explanation(
        self,
        pdo_id: str,
        pdo_hash: str,
        base_risk_score: Optional[float] = None,
        signal_ids: Optional[List[str]] = None,
        custom_factors: Optional[List[RiskFactor]] = None,
    ) -> DependencyAwareExplanation:
        """
        Generate a risk explanation with dependency attribution.
        
        Per INV-RISK-010: Must reference upstream agent outputs.
        """
        with self._lock:
            # Generate base explanation
            base_explanation = self._risk_explainer.explain(
                pdo_id=pdo_id,
                pdo_hash=pdo_hash,
                risk_score=base_risk_score,
                signal_ids=signal_ids,
                custom_factors=custom_factors,
            )
            
            # Analyze upstream contributions
            upstream_contributions = self.analyze_upstream_risks(pdo_id)
            
            # Calculate dependency-adjusted score
            base_score = base_explanation.risk_score
            upstream_risk = sum(c.propagated_risk for c in upstream_contributions)
            adjusted_score = min(1.0, base_score + upstream_risk)
            
            # Check for blocked/pending upstream
            has_blocked = any(
                c.upstream_risk_level == RiskLevel.CRITICAL 
                and "BLOCKED" in c.explanation_summary
                for c in upstream_contributions
            )
            has_pending = any(
                "PENDING" in c.explanation_summary
                for c in upstream_contributions
            )
            
            # Calculate propagation depth
            max_depth = 0
            for c in upstream_contributions:
                depth = c.explanation_summary.count("[via ")
                max_depth = max(max_depth, depth + 1)
            
            # Generate dependency risk summary
            summary = self._generate_dependency_summary(
                upstream_contributions,
                has_blocked,
                has_pending,
            )
            
            return DependencyAwareExplanation(
                base_explanation=base_explanation,
                upstream_contributions=tuple(upstream_contributions),
                dependency_adjusted_score=adjusted_score,
                dependency_risk_summary=summary,
                propagation_depth=max_depth,
                has_blocked_upstream=has_blocked,
                has_pending_upstream=has_pending,
            )

    def _generate_dependency_summary(
        self,
        contributions: List[UpstreamRiskContribution],
        has_blocked: bool,
        has_pending: bool,
    ) -> str:
        """Generate human-readable summary of dependency risks."""
        if not contributions:
            return "No upstream dependencies."
        
        lines = [f"Analyzed {len(contributions)} upstream dependencies."]
        
        if has_blocked:
            lines.append("⚠️ CRITICAL: One or more upstream dependencies are BLOCKED.")
        
        if has_pending:
            lines.append("⏳ Some upstream dependencies are still PENDING.")
        
        # Top contributors
        sorted_contribs = sorted(
            contributions,
            key=lambda c: c.propagated_risk,
            reverse=True,
        )[:3]
        
        if sorted_contribs:
            lines.append("Top risk contributors:")
            for c in sorted_contribs:
                lines.append(
                    f"  • {c.upstream_pdo_id} ({c.upstream_agent_gid}): "
                    f"{c.propagated_risk:.2f} risk propagated"
                )
        
        return "\n".join(lines)

    def get_dependency_risk_factor(
        self,
        pdo_id: str,
    ) -> Optional[RiskFactor]:
        """
        Generate a single RiskFactor summarizing dependency risk.
        
        Can be included in standard risk explanations.
        """
        contributions = self.analyze_upstream_risks(pdo_id)
        
        if not contributions:
            return None
        
        total_propagated = sum(c.propagated_risk for c in contributions)
        has_blocked = any(
            "BLOCKED" in c.explanation_summary for c in contributions
        )
        
        direction = (
            FactorDirection.ABOVE if total_propagated > 0.3
            else FactorDirection.WITHIN_RANGE
        )
        
        return RiskFactor(
            factor_id=f"FACTOR-DEP-{pdo_id}",
            signal_id="DEPENDENCY_CHAIN",
            signal_name="Upstream Dependency Risk",
            value=total_propagated,
            threshold=0.3,
            weight=1.5 if has_blocked else 1.0,
            direction=direction,
            contribution=total_propagated,
            explanation=f"Risk propagated from {len(contributions)} upstream dependencies",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_global_analyzer: Optional[DependencyRiskAnalyzer] = None
_global_lock = threading.Lock()


def get_dependency_risk_analyzer(
    config: Optional[Dict[str, Any]] = None,
) -> DependencyRiskAnalyzer:
    """Get or create the global dependency risk analyzer."""
    global _global_analyzer
    
    with _global_lock:
        if _global_analyzer is None:
            _global_analyzer = DependencyRiskAnalyzer(config=config)
        return _global_analyzer


def reset_dependency_risk_analyzer() -> None:
    """Reset the global analyzer (for testing)."""
    global _global_analyzer
    
    with _global_lock:
        _global_analyzer = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def explain_with_dependencies(
    pdo_id: str,
    pdo_hash: str,
    base_risk_score: Optional[float] = None,
) -> DependencyAwareExplanation:
    """
    Generate dependency-aware risk explanation.
    
    Usage:
        explanation = explain_with_dependencies(
            pdo_id="PDO-B",
            pdo_hash="hash123",
            base_risk_score=0.5,
        )
    """
    analyzer = get_dependency_risk_analyzer()
    return analyzer.generate_dependency_aware_explanation(
        pdo_id=pdo_id,
        pdo_hash=pdo_hash,
        base_risk_score=base_risk_score,
    )
