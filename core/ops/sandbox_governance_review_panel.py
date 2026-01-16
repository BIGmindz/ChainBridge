"""
Sandbox Governance Review Panel - OCC Integration
PAC-P752-GOV-SANDBOX-GOVERNANCE-EVOLUTION
TASK-05: OCC Sandbox Review Panel (GID-02)

Provides operator visibility for:
- Blocked attempt replay
- Proposed invariant diff
- Governance proposal review
- Evolution pipeline status

Core Law: Sandbox observes. Humans decide. Production evolves only through PAC.

INVARIANTS ENFORCED:
- INV-SDGE-002: All governance evolution requires explicit PAC approval
- INV-SDGE-003: Audit trail completeness mandatory
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


class SandboxGovernanceReviewPanel:
    """
    OCC panel for sandbox governance review.
    
    Shows:
    - PDO capture statistics
    - Detected patterns
    - Generated proposals
    - Review workflow
    - Evolution pipeline status
    """

    def __init__(self):
        self._last_refresh = None

    def get_sandbox_summary(
        self,
        pdo_stats: Optional[dict[str, Any]] = None,
        analysis_result: Optional[dict[str, Any]] = None,
        proposals: Optional[list[dict[str, Any]]] = None
    ) -> dict[str, Any]:
        """Get comprehensive sandbox summary for OCC."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "core_law": "Sandbox observes. Humans decide. Production evolves only through PAC.",
            
            "pdo_capture": {
                "total_records": pdo_stats.get("total_records", 0) if pdo_stats else 0,
                "blocked_attempts": pdo_stats.get("blocked_attempts", 0) if pdo_stats else 0,
                "approved_attempts": pdo_stats.get("approved_attempts", 0) if pdo_stats else 0,
                "block_rate": pdo_stats.get("block_rate", 0) if pdo_stats else 0
            },
            
            "pattern_analysis": {
                "patterns_detected": analysis_result.get("summary", {}).get("total_patterns", 0) if analysis_result else 0,
                "invariant_gaps": analysis_result.get("summary", {}).get("invariant_gaps", 0) if analysis_result else 0,
                "proof_ambiguities": analysis_result.get("summary", {}).get("proof_ambiguities", 0) if analysis_result else 0,
                "decision_inconsistencies": analysis_result.get("summary", {}).get("decision_inconsistencies", 0) if analysis_result else 0,
                "coverage_gaps": analysis_result.get("summary", {}).get("coverage_gaps", 0) if analysis_result else 0
            },
            
            "proposals": {
                "total": len(proposals) if proposals else 0,
                "pending_review": len([p for p in proposals if p.get("status") == "PENDING_REVIEW"]) if proposals else 0,
                "approved": len([p for p in proposals if p.get("status") == "APPROVED"]) if proposals else 0,
                "rejected": len([p for p in proposals if p.get("status") == "REJECTED"]) if proposals else 0
            },
            
            "evolution_pipeline": {
                "auto_enforcement": False,
                "pac_required": True,
                "human_approval_required": True
            }
        }

    def format_blocked_attempt_replay(self, pdo_record: dict[str, Any]) -> str:
        """Format a blocked attempt for replay display."""
        proof = pdo_record.get("proof", {})
        decision = pdo_record.get("decision", {})
        outcome = pdo_record.get("outcome", {})

        lines = [
            "┌" + "─" * 60 + "┐",
            "│" + "  BLOCKED ATTEMPT REPLAY".center(60) + "│",
            "├" + "─" * 60 + "┤",
            "│" + f"  PDO ID: {pdo_record.get('pdo_id', 'N/A')}".ljust(60) + "│",
            "│" + f"  Captured: {pdo_record.get('captured_at', 'N/A')}".ljust(60) + "│",
            "├" + "─" * 60 + "┤",
            "│" + "  PROOF:".ljust(60) + "│",
            "│" + f"    Type: {proof.get('proof_type', 'N/A')}".ljust(60) + "│",
            "│" + f"    Hash: {proof.get('hash', 'N/A')[:40]}...".ljust(60) + "│",
        ]

        # Evidence
        evidence = proof.get("evidence", {})
        for key, value in list(evidence.items())[:3]:
            lines.append("│" + f"    {key}: {str(value)[:40]}".ljust(60) + "│")

        lines.extend([
            "├" + "─" * 60 + "┤",
            "│" + "  DECISION:".ljust(60) + "│",
            "│" + f"    Type: {decision.get('decision_type', 'N/A')}".ljust(60) + "│",
            "│" + f"    Authority: {decision.get('authority', 'N/A')}".ljust(60) + "│",
            "│" + f"    Confidence: {decision.get('confidence', 'N/A')}".ljust(60) + "│",
        ])

        # Rules applied
        rules = decision.get("rules_applied", [])
        for rule in rules[:3]:
            lines.append("│" + f"    Rule: {rule[:50]}".ljust(60) + "│")

        lines.extend([
            "├" + "─" * 60 + "┤",
            "│" + "  OUTCOME:".ljust(60) + "│",
            "│" + f"    Type: {outcome.get('outcome_type', 'N/A')}".ljust(60) + "│",
            "│" + f"    Drift Score: {outcome.get('drift_score', 'N/A')}".ljust(60) + "│",
            "└" + "─" * 60 + "┘"
        ])

        return "\n".join(lines)

    def format_proposal_diff(self, proposal: dict[str, Any]) -> str:
        """Format a proposal for diff display."""
        lines = [
            "╔" + "═" * 70 + "╗",
            "║" + f"  PROPOSAL: {proposal.get('proposal_id', 'N/A')}".ljust(70) + "║",
            "╠" + "═" * 70 + "╣",
            "║" + f"  Type: {proposal.get('proposal_type', 'N/A')}".ljust(70) + "║",
            "║" + f"  Title: {proposal.get('title', 'N/A')[:60]}".ljust(70) + "║",
            "║" + f"  Priority: {proposal.get('priority', 'N/A')}".ljust(70) + "║",
            "║" + f"  Status: {proposal.get('status', 'N/A')}".ljust(70) + "║",
            "╠" + "═" * 70 + "╣",
        ]

        # Proposed invariant
        invariant = proposal.get("proposed_invariant")
        if invariant:
            lines.extend([
                "║" + "  PROPOSED INVARIANT:".ljust(70) + "║",
                "║" + f"    + ID: {invariant.get('invariant_id', 'N/A')}".ljust(70) + "║",
                "║" + f"    + Name: {invariant.get('name', 'N/A')}".ljust(70) + "║",
                "║" + f"    + Rule: {invariant.get('rule', 'N/A')[:50]}".ljust(70) + "║",
                "║" + f"    + Enforcement: {invariant.get('enforcement', 'N/A')}".ljust(70) + "║",
            ])

        # Proposed schema
        schema = proposal.get("proposed_schema")
        if schema:
            lines.extend([
                "║" + "  PROPOSED SCHEMA:".ljust(70) + "║",
                "║" + f"    + Type: {schema.get('proof_type', 'N/A')}".ljust(70) + "║",
                "║" + f"    + Required: {', '.join(schema.get('required_fields', [])[:5])}".ljust(70) + "║",
            ])

        lines.extend([
            "╠" + "═" * 70 + "╣",
            "║" + f"  Confidence: {proposal.get('confidence_score', 0):.2%}".ljust(70) + "║",
            "║" + f"  Requires PAC: YES (INV-SDGE-002)".ljust(70) + "║",
            "╚" + "═" * 70 + "╝"
        ])

        return "\n".join(lines)

    def render_streamlit(
        self,
        pdo_stats: Optional[dict[str, Any]] = None,
        analysis_result: Optional[dict[str, Any]] = None,
        proposals: Optional[list[dict[str, Any]]] = None,
        blocked_records: Optional[list[dict[str, Any]]] = None
    ) -> None:
        """Render panel in Streamlit."""
        if not STREAMLIT_AVAILABLE:
            return

        summary = self.get_sandbox_summary(pdo_stats, analysis_result, proposals)

        st.header("🔬 Sandbox Governance Evolution")
        st.caption(f"Core Law: {summary['core_law']}")

        # Pipeline status
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Auto-Enforcement", "❌ Disabled")
        with col2:
            st.metric("PAC Required", "✅ Yes")
        with col3:
            st.metric("Human Approval", "✅ Required")

        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Overview",
            "🔄 Blocked Attempts",
            "📋 Proposals",
            "📈 Patterns"
        ])

        with tab1:
            self._render_overview(summary)

        with tab2:
            self._render_blocked_attempts(blocked_records or [])

        with tab3:
            self._render_proposals(proposals or [])

        with tab4:
            self._render_patterns(analysis_result)

    def _render_overview(self, summary: dict[str, Any]) -> None:
        """Render overview tab."""
        st.subheader("PDO Capture Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        pdo = summary["pdo_capture"]
        col1.metric("Total Records", pdo["total_records"])
        col2.metric("Blocked", pdo["blocked_attempts"])
        col3.metric("Approved", pdo["approved_attempts"])
        col4.metric("Block Rate", f"{pdo['block_rate']:.1%}")

        st.subheader("Pattern Analysis")
        col1, col2, col3, col4 = st.columns(4)
        
        patterns = summary["pattern_analysis"]
        col1.metric("Total Patterns", patterns["patterns_detected"])
        col2.metric("Invariant Gaps", patterns["invariant_gaps"])
        col3.metric("Proof Ambiguities", patterns["proof_ambiguities"])
        col4.metric("Inconsistencies", patterns["decision_inconsistencies"])

        st.subheader("Proposal Queue")
        col1, col2, col3 = st.columns(3)
        
        props = summary["proposals"]
        col1.metric("Pending Review", props["pending_review"])
        col2.metric("Approved", props["approved"])
        col3.metric("Rejected", props["rejected"])

    def _render_blocked_attempts(self, blocked_records: list[dict[str, Any]]) -> None:
        """Render blocked attempts tab."""
        st.subheader("Blocked Attempt Replay")
        
        if not blocked_records:
            st.info("No blocked attempts to display")
            return

        for i, record in enumerate(blocked_records[:10]):
            with st.expander(f"PDO: {record.get('pdo_id', f'Record {i+1}')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Proof:**")
                    proof = record.get("proof", {})
                    st.json(proof.get("evidence", {}))
                
                with col2:
                    st.write("**Decision:**")
                    decision = record.get("decision", {})
                    st.write(f"Type: {decision.get('decision_type')}")
                    st.write(f"Reasoning: {decision.get('reasoning')}")
                    st.write("Rules Applied:")
                    for rule in decision.get("rules_applied", []):
                        st.write(f"  • {rule}")

    def _render_proposals(self, proposals: list[dict[str, Any]]) -> None:
        """Render proposals tab."""
        st.subheader("Governance Proposals")
        
        if not proposals:
            st.info("No proposals generated yet")
            return

        # Filter controls
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "PENDING_REVIEW", "APPROVED", "REJECTED"]
        )

        filtered = proposals
        if status_filter != "All":
            filtered = [p for p in proposals if p.get("status") == status_filter]

        for proposal in filtered:
            status = proposal.get("status", "DRAFT")
            status_icon = {
                "DRAFT": "📝",
                "PENDING_REVIEW": "⏳",
                "APPROVED": "✅",
                "REJECTED": "❌",
                "CONVERTED_TO_PAC": "🔄"
            }.get(status, "❓")

            with st.expander(f"{status_icon} {proposal.get('title', 'Untitled')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {proposal.get('proposal_id')}")
                    st.write(f"**Type:** {proposal.get('proposal_type')}")
                    st.write(f"**Priority:** {proposal.get('priority')}")
                    st.write(f"**Confidence:** {proposal.get('confidence_score', 0):.1%}")
                
                with col2:
                    st.write(f"**Status:** {status}")
                    if proposal.get("reviewed_by"):
                        st.write(f"**Reviewed by:** {proposal.get('reviewed_by')}")
                        st.write(f"**Decision:** {proposal.get('review_decision')}")

                st.write(f"**Description:** {proposal.get('description')}")

                # Show proposed changes
                if proposal.get("proposed_invariant"):
                    st.write("**Proposed Invariant:**")
                    st.json(proposal["proposed_invariant"])

                # Review actions (simulated)
                if status == "PENDING_REVIEW":
                    st.warning("⚠️ Requires human review before PAC conversion")

    def _render_patterns(self, analysis_result: Optional[dict[str, Any]]) -> None:
        """Render patterns tab."""
        st.subheader("Detected Patterns")
        
        if not analysis_result:
            st.info("No analysis results available")
            return

        patterns = analysis_result.get("patterns", [])
        
        if not patterns:
            st.success("No concerning patterns detected")
            return

        for pattern in patterns:
            severity = pattern.get("severity", "INFO")
            severity_color = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢",
                "INFO": "🔵"
            }.get(severity, "⚪")

            with st.expander(f"{severity_color} {pattern.get('pattern_type')}: {pattern.get('description', '')[:50]}"):
                st.write(f"**Severity:** {severity}")
                st.write(f"**Occurrences:** {pattern.get('occurrence_count', 0)}")
                st.write(f"**Confidence:** {pattern.get('confidence', 0):.1%}")
                
                st.write("**Recommendations:**")
                for rec in pattern.get("recommendations", []):
                    st.write(f"  • {rec}")


def render_sandbox_review_panel(
    pdo_stats: Optional[dict[str, Any]] = None,
    analysis_result: Optional[dict[str, Any]] = None,
    proposals: Optional[list[dict[str, Any]]] = None,
    blocked_records: Optional[list[dict[str, Any]]] = None
) -> None:
    """Convenience function to render sandbox review panel."""
    panel = SandboxGovernanceReviewPanel()
    
    if STREAMLIT_AVAILABLE:
        panel.render_streamlit(pdo_stats, analysis_result, proposals, blocked_records)
    else:
        summary = panel.get_sandbox_summary(pdo_stats, analysis_result, proposals)
        print(json.dumps(summary, indent=2))
