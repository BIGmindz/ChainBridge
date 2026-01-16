"""
Negative Capability OCC Panel — Blocked Outcome Visualization
PAC-P751-NEGATIVE-CAPABILITY-DEMO
TASK-05: Render OCC visualization (reason, rule, authority)

Provides operator-visible explanation of:
- What was blocked
- Why it was blocked
- Which governance rules applied
- Who (what authority) rendered the decision
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


class BlockedOutcomePanel:
    """
    OCC panel for blocked outcome visualization.
    
    Shows:
    - Blocked instruction summary
    - Block reasons with governance rule mapping
    - Authority decision trail
    - Proof artifacts
    """

    def __init__(self):
        self._last_blocked_outcome: Optional[dict[str, Any]] = None

    def set_blocked_outcome(self, outcome: dict[str, Any]) -> None:
        """Set the blocked outcome to display."""
        self._last_blocked_outcome = outcome

    def format_for_display(self, outcome: dict[str, Any]) -> str:
        """Format blocked outcome for text display."""
        instruction = outcome.get("instruction", {})
        blocked = outcome.get("blocked_outcome", {})
        evaluation = outcome.get("evaluation", {})

        lines = [
            "╔" + "═" * 70 + "╗",
            "║" + "  🛑 BLOCKED OUTCOME — GOVERNANCE ENFORCEMENT".center(70) + "║",
            "╠" + "═" * 70 + "╣",
            "║" + f"  PAC Reference: {outcome.get('pac_reference', 'N/A')}".ljust(70) + "║",
            "║" + f"  Authority: {outcome.get('authority', 'N/A')}".ljust(70) + "║",
            "╠" + "═" * 70 + "╣",
            "║" + "  INSTRUCTION BLOCKED:".ljust(70) + "║",
            "║" + f"    ID: {instruction.get('instruction_id', 'N/A')}".ljust(70) + "║",
            "║" + f"    Amount: ${instruction.get('amount_usd', 0):,.2f}".ljust(70) + "║",
            "║" + f"    Counterparty: {instruction.get('counterparty_name', 'N/A')}".ljust(70) + "║",
            "║" + f"    Jurisdiction: {instruction.get('destination_jurisdiction', 'N/A')}".ljust(70) + "║",
            "╠" + "═" * 70 + "╣",
            "║" + "  BLOCK REASONS:".ljust(70) + "║",
        ]

        for reason in blocked.get("block_reasons", []):
            lines.append("║" + f"    ⛔ {reason}".ljust(70) + "║")

        lines.extend([
            "╠" + "═" * 70 + "╣",
            "║" + "  GOVERNANCE RULES APPLIED:".ljust(70) + "║",
        ])

        for check in evaluation.get("invariants_checked", []):
            invariant = check.get("invariant", "")
            result = check.get("result", "")
            lines.append("║" + f"    [{result}] {invariant}".ljust(70) + "║")

        lines.extend([
            "╠" + "═" * 70 + "╣",
            "║" + "  OUTCOME STATUS:".ljust(70) + "║",
            "║" + f"    Settlement Prevented: {'✅ YES' if blocked.get('settlement_prevented') else '❌ NO'}".ljust(70) + "║",
            "║" + f"    Ledger Unchanged: {'✅ YES' if blocked.get('ledger_unchanged') else '❌ NO'}".ljust(70) + "║",
            "║" + f"    Drift Score: {evaluation.get('drift_score', 'N/A')}".ljust(70) + "║",
            "╠" + "═" * 70 + "╣",
            "║" + "  PROOF:".ljust(70) + "║",
            "║" + f"    Hash: {blocked.get('proof_hash', 'N/A')}".ljust(70) + "║",
            "╚" + "═" * 70 + "╝"
        ])

        return "\n".join(lines)

    def render_streamlit(self, outcome: dict[str, Any]) -> None:
        """Render blocked outcome in Streamlit."""
        if not STREAMLIT_AVAILABLE:
            return

        instruction = outcome.get("instruction", {})
        blocked = outcome.get("blocked_outcome", {})
        evaluation = outcome.get("evaluation", {})
        demo_result = outcome.get("demo_result", {})

        st.header("🛑 Blocked Outcome — Governance Enforcement")
        st.caption(f"PAC Reference: {outcome.get('pac_reference', 'N/A')}")

        # Status indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Status", "🛑 BLOCKED")
        with col2:
            settlement = "✅ Prevented" if blocked.get("settlement_prevented") else "❌ Executed"
            st.metric("Settlement", settlement)
        with col3:
            ledger = "✅ Unchanged" if blocked.get("ledger_unchanged") else "❌ Mutated"
            st.metric("Ledger", ledger)
        with col4:
            drift = evaluation.get("drift_score", 1.0)
            drift_status = "✅ Zero" if drift == 0.0 else f"⚠️ {drift}"
            st.metric("Drift", drift_status)

        # Blocked instruction details
        st.subheader("📋 Blocked Instruction")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**ID:** {instruction.get('instruction_id', 'N/A')}")
            st.write(f"**Amount:** ${instruction.get('amount_usd', 0):,.2f}")
            st.write(f"**Initiator:** {instruction.get('initiator', 'N/A')}")
        with col2:
            st.write(f"**Counterparty:** {instruction.get('counterparty_name', 'N/A')}")
            st.write(f"**Jurisdiction:** {instruction.get('destination_jurisdiction', 'N/A')}")
            st.write(f"**Rail:** {instruction.get('payment_rail', 'N/A')}")

        # Block reasons
        st.subheader("⛔ Block Reasons")
        for reason in blocked.get("block_reasons", []):
            st.error(f"🚫 {reason}")

        # Governance rules applied
        st.subheader("📜 Governance Rules Applied")
        for check in evaluation.get("invariants_checked", []):
            with st.expander(f"**{check.get('invariant', '')}** — {check.get('check', '')}"):
                st.write(f"**Result:** {check.get('result', '')}")
                st.write(f"**Reason:** {check.get('reason', '')}")

        # Explanation
        st.subheader("📝 Explanation")
        st.info(blocked.get("explanation", "No explanation provided"))

        # Proof
        st.subheader("🔐 Proof Artifact")
        st.code(blocked.get("proof_hash", "No proof hash"), language="text")

        # Authority
        st.subheader("👤 Authority")
        st.write(f"Decision rendered by: **{blocked.get('authority', 'N/A')}**")
        st.write(f"Blocked at: {blocked.get('blocked_at', 'N/A')}")

        # Invariants enforced
        st.subheader("⚖️ Invariants Enforced")
        invariants = outcome.get("invariants_enforced", [])
        for inv in invariants:
            st.success(f"✅ {inv}")

    def generate_occ_summary(self, outcome: dict[str, Any]) -> dict[str, Any]:
        """Generate OCC summary for dashboard integration."""
        blocked = outcome.get("blocked_outcome", {})
        evaluation = outcome.get("evaluation", {})
        demo_result = outcome.get("demo_result", {})

        return {
            "panel_type": "BLOCKED_OUTCOME",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "BLOCKED",
            
            "summary": {
                "pac_reference": outcome.get("pac_reference"),
                "instruction_blocked": True,
                "settlement_prevented": blocked.get("settlement_prevented", False),
                "ledger_unchanged": blocked.get("ledger_unchanged", False),
                "drift_score": evaluation.get("drift_score", 1.0),
                "block_reason_count": len(blocked.get("block_reasons", []))
            },
            
            "governance_compliance": {
                "control_over_autonomy": True,
                "proof_over_execution": True,
                "fail_closed": True,
                "human_authority_final": True
            },
            
            "proof_hash": blocked.get("proof_hash"),
            "authority": blocked.get("authority"),
            
            "invariants_verified": outcome.get("invariants_enforced", [])
        }


def render_blocked_outcome_panel(outcome: dict[str, Any]) -> None:
    """Convenience function to render blocked outcome panel."""
    panel = BlockedOutcomePanel()
    
    if STREAMLIT_AVAILABLE:
        panel.render_streamlit(outcome)
    else:
        print(panel.format_for_display(outcome))


def get_blocked_outcome_summary(outcome: dict[str, Any]) -> dict[str, Any]:
    """Get OCC summary for blocked outcome."""
    panel = BlockedOutcomePanel()
    return panel.generate_occ_summary(outcome)
