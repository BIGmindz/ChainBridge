"""
ChainBridge Terminal Gate Visibility — Canonical Output Renderer
════════════════════════════════════════════════════════════════════════════════

Every PAC execution produces deterministic, human-visible terminal output.
No silent execution permitted.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-TERMINAL-GATES-015
Effective Date: 2025-12-26

VISIBILITY INVARIANTS:
- INV-VIS-001: All PAG gates emit terminal output
- INV-VIS-002: Gate order is fixed (PAG-01 → PAG-07)
- INV-VIS-003: Tokens and symbols are canonical
- INV-VIS-004: No silent failures
- INV-VIS-005: All emissions are logged for audit

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from io import StringIO
from typing import Callable, Dict, List, Optional, TextIO, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL SYMBOLS — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

PASS_SYMBOL = "✅"
FAIL_SYMBOL = "❌"
PENDING_SYMBOL = "⏳"
SKIP_SYMBOL = "⏭️"

# Snapshot-specific symbols (PAC-018)
SNAPSHOT_RECEIVED_SYMBOL = "🧾"
SNAPSHOT_LOCKED_SYMBOL = "🔐"
SNAPSHOT_VERIFIED_SYMBOL = "🟩"
SNAPSHOT_DRIFT_SYMBOL = "⛔"
SNAPSHOT_REQUIRED_SYMBOL = "🟥"

BORDER_CHAR = "═"
BORDER_WIDTH = 60

GATE_HEADER = f"{BORDER_CHAR * BORDER_WIDTH}"
GATE_FOOTER = f"{BORDER_CHAR * BORDER_WIDTH}"


# ═══════════════════════════════════════════════════════════════════════════════
# GATE DEFINITIONS — CANONICAL ORDER
# ═══════════════════════════════════════════════════════════════════════════════

class GateID(Enum):
    """Canonical gate identifiers in fixed order."""
    
    PAG_01 = "PAG-01"
    PAG_02 = "PAG-02"
    PAG_03 = "PAG-03"
    PAG_04 = "PAG-04"
    PAG_05 = "PAG-05"
    PAG_06 = "PAG-06"
    PAG_07 = "PAG-07"


# Gate names — FIXED, do not modify order
GATE_NAMES: Dict[GateID, str] = {
    GateID.PAG_01: "Scope Definition",
    GateID.PAG_02: "Agent Selection",
    GateID.PAG_03: "Execution Constraints",
    GateID.PAG_04: "Required Outputs",
    GateID.PAG_05: "Governance Duty",
    GateID.PAG_06: "Terminal Visibility",
    GateID.PAG_07: "Attestation",
}


class GateStatus(Enum):
    """Gate evaluation status."""
    
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"
    SKIP = "SKIP"
    
    @property
    def symbol(self) -> str:
        """Get the canonical symbol for this status."""
        return {
            GateStatus.PASS: PASS_SYMBOL,
            GateStatus.FAIL: FAIL_SYMBOL,
            GateStatus.PENDING: PENDING_SYMBOL,
            GateStatus.SKIP: SKIP_SYMBOL,
        }[self]


# ═══════════════════════════════════════════════════════════════════════════════
# GATE RESULT — IMMUTABLE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GateResult:
    """Result of a single gate evaluation."""
    
    gate_id: GateID
    status: GateStatus
    message: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    @property
    def gate_name(self) -> str:
        """Get the canonical name for this gate."""
        return GATE_NAMES[self.gate_id]
    
    @property
    def passed(self) -> bool:
        """True if gate passed."""
        return self.status == GateStatus.PASS
    
    def format_line(self) -> str:
        """Format as canonical terminal line."""
        return f"{self.gate_id.value}  {self.gate_name:<25} {self.status.symbol} {self.status.value}"


@dataclass
class GateChecklistResult:
    """Result of full PAG-01 → PAG-07 checklist."""
    
    pac_id: str
    gates: List[GateResult] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    
    @property
    def all_passed(self) -> bool:
        """True if all gates passed."""
        return all(g.passed for g in self.gates)
    
    @property
    def failed_gates(self) -> List[GateResult]:
        """List of failed gates."""
        return [g for g in self.gates if g.status == GateStatus.FAIL]
    
    @property
    def pass_count(self) -> int:
        """Number of passed gates."""
        return sum(1 for g in self.gates if g.passed)
    
    @property
    def total_count(self) -> int:
        """Total number of gates evaluated."""
        return len(self.gates)
    
    def add_gate(self, gate: GateResult) -> None:
        """Add a gate result."""
        self.gates.append(gate)
    
    def complete(self) -> None:
        """Mark checklist as complete."""
        self.completed_at = datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# TERMINAL RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

class TerminalGateRenderer:
    """
    Canonical terminal output renderer for PAG gates.
    
    All output is deterministic and follows fixed format.
    No silent execution — all gates emit visible output.
    """
    
    def __init__(self, output: TextIO = None):
        self._output = output or sys.stdout
        self._buffer: List[str] = []
        self._capture_mode = False
    
    def _emit(self, text: str) -> None:
        """Emit text to output stream."""
        if self._capture_mode:
            self._buffer.append(text)
        else:
            print(text, file=self._output)
    
    def start_capture(self) -> None:
        """Start capturing output instead of printing."""
        self._capture_mode = True
        self._buffer.clear()
    
    def stop_capture(self) -> str:
        """Stop capturing and return captured output."""
        self._capture_mode = False
        result = "\n".join(self._buffer)
        self._buffer.clear()
        return result
    
    def get_captured(self) -> str:
        """Get captured output without stopping capture."""
        return "\n".join(self._buffer)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PAC LIFECYCLE EMISSIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def emit_pac_ingest(self, pac_id: str, issuer: str = "Jeffrey") -> None:
        """Emit PAC ingest notification."""
        self._emit("")
        self._emit(GATE_HEADER)
        self._emit(f"🟦 PAC RECEIVED: {pac_id}")
        self._emit(f"   ISSUER: {issuer}")
        self._emit(f"   TIMESTAMP: {datetime.now(timezone.utc).isoformat()}")
        self._emit(GATE_HEADER)
    
    def emit_pac_validated(self, pac_id: str) -> None:
        """Emit PAC validation success."""
        self._emit(f"🟩 PAC VALIDATED: {pac_id}")
    
    def emit_agent_dispatch(
        self,
        gid: str,
        agent_name: str,
        role: str,
        lane: str,
    ) -> None:
        """Emit agent dispatch notification."""
        self._emit("")
        self._emit(GATE_HEADER)
        self._emit(f"📤 DISPATCHING TO AGENT")
        self._emit(f"   GID: {gid}")
        self._emit(f"   NAME: {agent_name}")
        self._emit(f"   ROLE: {role}")
        self._emit(f"   LANE: {lane}")
        self._emit(GATE_HEADER)
    
    def emit_wrap_receipt(self, wrap_id: str, pac_id: str, gid: str) -> None:
        """Emit WRAP receipt notification."""
        self._emit("")
        self._emit(GATE_HEADER)
        self._emit(f"📥 WRAP RECEIVED")
        self._emit(f"   WRAP_ID: {wrap_id}")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   FROM: {gid}")
        self._emit(f"   TIMESTAMP: {datetime.now(timezone.utc).isoformat()}")
        self._emit(GATE_HEADER)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GATE CHECKLIST EMISSIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def emit_gate_checklist_start(self, pac_id: str) -> None:
        """Emit gate checklist start."""
        self._emit("")
        self._emit(GATE_HEADER)
        self._emit(f"📋 PAG GATE CHECKLIST — {pac_id}")
        self._emit(GATE_HEADER)
    
    def emit_gate_result(self, result: GateResult) -> None:
        """Emit single gate result."""
        self._emit(result.format_line())
        if result.message and result.status == GateStatus.FAIL:
            self._emit(f"   └─ {result.message}")
    
    def emit_gate_checklist(self, checklist: GateChecklistResult) -> None:
        """Emit full gate checklist."""
        self.emit_gate_checklist_start(checklist.pac_id)
        
        for gate in checklist.gates:
            self.emit_gate_result(gate)
        
        self._emit(GATE_HEADER)
        
        if checklist.all_passed:
            self._emit(f"✅ ALL GATES PASSED ({checklist.pass_count}/{checklist.total_count})")
        else:
            failed = len(checklist.failed_gates)
            self._emit(f"❌ GATES FAILED: {failed}/{checklist.total_count}")
            for fg in checklist.failed_gates:
                self._emit(f"   └─ {fg.gate_id.value}: {fg.message or 'No message'}")
        
        self._emit(GATE_HEADER)
    
    def emit_gate_table(self, results: List[Tuple[str, str, str]]) -> None:
        """
        Emit gate results as a table.
        
        results: List of (gate_id, gate_name, status) tuples
        """
        self._emit("")
        self._emit(GATE_HEADER)
        self._emit("| Gate   | Check                          | Status |")
        self._emit("|--------|--------------------------------|--------|")
        
        for gate_id, gate_name, status in results:
            status_symbol = PASS_SYMBOL if status == "PASS" else FAIL_SYMBOL
            self._emit(f"| {gate_id} | {gate_name:<30} | {status_symbol} {status} |")
        
        self._emit(GATE_HEADER)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BER EMISSIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def emit_ber_approved(
        self,
        ber_id: str,
        pac_id: str,
        wrap_id: str,
        issuer_gid: str = "GID-00",
    ) -> None:
        """Emit BER approval notification."""
        self._emit("")
        self._emit(GATE_HEADER)
        self._emit(f"🟩 BER ISSUED — APPROVED")
        self._emit(GATE_HEADER)
        self._emit(f"BER_ID:      {ber_id}")
        self._emit(f"PAC_ID:      {pac_id}")
        self._emit(f"WRAP_ID:     {wrap_id}")
        self._emit(f"ISSUER:      {issuer_gid} (BENSON)")
        self._emit(f"DISPOSITION: ✅ APPROVED")
        self._emit(f"TIMESTAMP:   {datetime.now(timezone.utc).isoformat()}")
        self._emit(f"LEDGER:      COMMITTED")
        self._emit(f"NEXT_STATE:  AWAITING_PAC")
        self._emit(GATE_HEADER)
    
    def emit_ber_rejected(
        self,
        pac_id: str,
        wrap_id: str,
        reason: str,
        failed_gates: List[str],
        issuer_gid: str = "GID-00",
    ) -> None:
        """Emit BER rejection notification."""
        self._emit("")
        self._emit(GATE_HEADER)
        self._emit(f"🟥 BER REJECTED — CORRECTIVE PAC REQUIRED")
        self._emit(GATE_HEADER)
        self._emit(f"PAC_ID:      {pac_id}")
        self._emit(f"WRAP_ID:     {wrap_id}")
        self._emit(f"ISSUER:      {issuer_gid} (BENSON)")
        self._emit(f"DISPOSITION: ❌ REJECTED")
        self._emit(f"REASON:      {reason}")
        self._emit(f"FAILED_GATES:")
        for gate in failed_gates:
            self._emit(f"   └─ {gate}")
        self._emit(f"NEXT_ACTION: CORRECTIVE_PAC_REQUIRED")
        self._emit(GATE_HEADER)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATUS EMISSIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def emit_status(self, status: str, mode: str, discipline: str) -> None:
        """Emit current status."""
        self._emit("")
        self._emit(GATE_HEADER)
        self._emit(f"STATUS:      {status}")
        self._emit(f"MODE:        {mode}")
        self._emit(f"DISCIPLINE:  {discipline}")
        self._emit(f"NEXT_ACTION: AWAITING_PAC")
        self._emit(GATE_HEADER)
    
    def emit_ready(self, gid: str = "GID-00", name: str = "BENSON") -> None:
        """Emit ready status."""
        self._emit("")
        self._emit(GATE_HEADER)
        self._emit(f"🟩 {name} ({gid}) — READY FOR PAC")
        self._emit(GATE_HEADER)


# ═══════════════════════════════════════════════════════════════════════════════
# GATE EVALUATOR — WITH TERMINAL OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

class TerminalGateEvaluator:
    """
    Gate evaluator with mandatory terminal output.
    
    Every evaluation emits visible terminal output.
    No silent execution permitted.
    """
    
    def __init__(self, renderer: TerminalGateRenderer = None):
        self._renderer = renderer or get_terminal_renderer()
        self._current_checklist: Optional[GateChecklistResult] = None
    
    def start_checklist(self, pac_id: str) -> GateChecklistResult:
        """Start a new gate checklist."""
        self._current_checklist = GateChecklistResult(pac_id=pac_id)
        return self._current_checklist
    
    def evaluate_gate(
        self,
        gate_id: GateID,
        condition: bool,
        fail_message: str = None,
    ) -> GateResult:
        """
        Evaluate a gate and emit result.
        
        Always emits terminal output.
        """
        status = GateStatus.PASS if condition else GateStatus.FAIL
        result = GateResult(
            gate_id=gate_id,
            status=status,
            message=fail_message if not condition else None,
        )
        
        # Emit immediately
        self._renderer.emit_gate_result(result)
        
        # Add to checklist if active
        if self._current_checklist:
            self._current_checklist.add_gate(result)
        
        return result
    
    def complete_checklist(self) -> GateChecklistResult:
        """Complete current checklist and emit summary."""
        if self._current_checklist:
            self._current_checklist.complete()
            
            # Emit summary
            self._renderer._emit(GATE_HEADER)
            if self._current_checklist.all_passed:
                self._renderer._emit(
                    f"✅ ALL GATES PASSED "
                    f"({self._current_checklist.pass_count}/{self._current_checklist.total_count})"
                )
            else:
                failed = len(self._current_checklist.failed_gates)
                self._renderer._emit(f"❌ GATES FAILED: {failed}")
            self._renderer._emit(GATE_HEADER)
        
        result = self._current_checklist
        self._current_checklist = None
        return result
    
    def run_standard_checklist(
        self,
        pac_id: str,
        checks: Dict[GateID, Tuple[bool, str]],
    ) -> GateChecklistResult:
        """
        Run standard PAG-01 → PAG-07 checklist.
        
        checks: Dict mapping GateID to (condition, fail_message)
        """
        self._renderer.emit_gate_checklist_start(pac_id)
        checklist = self.start_checklist(pac_id)
        
        # Evaluate in canonical order
        for gate_id in GateID:
            if gate_id in checks:
                condition, fail_msg = checks[gate_id]
                self.evaluate_gate(gate_id, condition, fail_msg)
            else:
                # Gate not specified → SKIP
                result = GateResult(
                    gate_id=gate_id,
                    status=GateStatus.SKIP,
                    message="Not evaluated",
                )
                self._renderer.emit_gate_result(result)
                checklist.add_gate(result)
        
        return self.complete_checklist()


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_renderer: Optional[TerminalGateRenderer] = None
_evaluator: Optional[TerminalGateEvaluator] = None


def get_terminal_renderer() -> TerminalGateRenderer:
    """Get the singleton terminal renderer."""
    global _renderer
    if _renderer is None:
        _renderer = TerminalGateRenderer()
    return _renderer


def get_gate_evaluator() -> TerminalGateEvaluator:
    """Get the singleton gate evaluator."""
    global _evaluator
    if _evaluator is None:
        _evaluator = TerminalGateEvaluator()
    return _evaluator


def reset_terminal_renderer() -> None:
    """Reset the singleton (for testing)."""
    global _renderer, _evaluator
    _renderer = None
    _evaluator = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def emit_pac_ingest(pac_id: str, issuer: str = "Jeffrey") -> None:
    """Emit PAC ingest notification."""
    get_terminal_renderer().emit_pac_ingest(pac_id, issuer)


def emit_agent_dispatch(gid: str, name: str, role: str, lane: str) -> None:
    """Emit agent dispatch notification."""
    get_terminal_renderer().emit_agent_dispatch(gid, name, role, lane)


def emit_wrap_receipt(wrap_id: str, pac_id: str, gid: str) -> None:
    """Emit WRAP receipt notification."""
    get_terminal_renderer().emit_wrap_receipt(wrap_id, pac_id, gid)


def emit_ber_approved(ber_id: str, pac_id: str, wrap_id: str) -> None:
    """Emit BER approval."""
    get_terminal_renderer().emit_ber_approved(ber_id, pac_id, wrap_id)


def emit_ber_rejected(pac_id: str, wrap_id: str, reason: str, failed_gates: List[str]) -> None:
    """Emit BER rejection."""
    get_terminal_renderer().emit_ber_rejected(pac_id, wrap_id, reason, failed_gates)


def run_gate_checklist(
    pac_id: str,
    checks: Dict[GateID, Tuple[bool, str]],
) -> GateChecklistResult:
    """Run standard gate checklist with terminal output."""
    return get_gate_evaluator().run_standard_checklist(pac_id, checks)


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-017: ORCHESTRATION ENGINE EMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════

def emit_orchestration_engine_engaged(
    mode: str = "ORCHESTRATION",
    discipline: str = "GOLD_STANDARD · FAIL-CLOSED",
) -> None:
    """
    Emit orchestration engine engagement notification.
    
    🧠 ORCHESTRATION ENGINE ENGAGED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit("🧠 ORCHESTRATION ENGINE ENGAGED")
    renderer._emit(f"   MODE: {mode}")
    renderer._emit(f"   DISCIPLINE: {discipline}")
    renderer._emit(GATE_HEADER)


def emit_persona_authority_rejected(
    claimed_persona: str,
    reason: str = "Persona strings have zero authority weight",
) -> None:
    """
    Emit persona authority rejection notification.
    
    ⛔ PERSONA AUTHORITY REJECTED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit("⛔ PERSONA AUTHORITY REJECTED")
    renderer._emit(f"   CLAIMED_PERSONA: \"{claimed_persona}\"")
    renderer._emit(f"   REASON: {reason}")
    renderer._emit("   ENFORCEMENT: CODE_ONLY")
    renderer._emit(GATE_HEADER)


def emit_system_governance_decision(
    decision: str,
    issuer: str = "ORCHESTRATION_ENGINE",
    authority: str = "SYSTEM_ORCHESTRATOR",
) -> None:
    """
    Emit system governance decision notification.
    
    🟩 SYSTEM GOVERNANCE DECISION ISSUED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit("🟩 SYSTEM GOVERNANCE DECISION ISSUED")
    renderer._emit(f"   DECISION: {decision}")
    renderer._emit(f"   ISSUER: {issuer} (not persona)")
    renderer._emit(f"   AUTHORITY: {authority}")
    renderer._emit(GATE_HEADER)


def emit_ber_authority_violation(
    attempted_issuer: str,
    required_authority: str = "ORCHESTRATION_ENGINE",
) -> None:
    """
    Emit BER authority violation notification.
    
    ⛔ BER AUTHORITY VIOLATION
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit("⛔ BER AUTHORITY VIOLATION")
    renderer._emit(f"   ATTEMPTED_ISSUER: {attempted_issuer}")
    renderer._emit(f"   REQUIRED_AUTHORITY: {required_authority}")
    renderer._emit("   RESULT: HARD FAIL — BER REJECTED")
    renderer._emit(GATE_HEADER)


def emit_wrap_authority_violation(
    attempted_issuer: str,
    required_authority: str = "AGENT (GID-XX)",
) -> None:
    """
    Emit WRAP authority violation notification.
    
    ⛔ WRAP AUTHORITY VIOLATION
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit("⛔ WRAP AUTHORITY VIOLATION")
    renderer._emit(f"   ATTEMPTED_ISSUER: {attempted_issuer}")
    renderer._emit(f"   REQUIRED_AUTHORITY: {required_authority}")
    renderer._emit("   RESULT: HARD FAIL — WRAP REJECTED")
    renderer._emit(GATE_HEADER)


def emit_self_approval_blocked(
    agent_gid: str,
) -> None:
    """
    Emit self-approval blocked notification.
    
    ⛔ SELF-APPROVAL BLOCKED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit("⛔ SELF-APPROVAL BLOCKED")
    renderer._emit(f"   AGENT: {agent_gid}")
    renderer._emit("   REASON: Agents may never self-approve")
    renderer._emit("   RESULT: HARD FAIL — BER REJECTED")
    renderer._emit(GATE_HEADER)


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-021: BER EMISSION ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def emit_ber_emitted(
    pac_id: str,
    ber_status: str,
    artifact_id: str,
) -> None:
    """
    Emit BER emitted notification (INV-BER-007 satisfied).
    
    ✅ BER EMITTED — EXTERNAL VISIBILITY ACHIEVED
    """
    renderer = get_terminal_renderer()
    symbol = PASS_SYMBOL if ber_status == "APPROVE" else "⚠️"
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit(f"✅ BER EMITTED — EXTERNAL VISIBILITY ACHIEVED {symbol}")
    renderer._emit(f"   PAC_ID: {pac_id}")
    renderer._emit(f"   DECISION: {ber_status}")
    renderer._emit(f"   ARTIFACT_ID: {artifact_id}")
    renderer._emit(f"   ISSUER: GID-00 (ORCHESTRATION_ENGINE)")
    renderer._emit(f"   CONSTRAINT: INV-BER-007 ✓ SATISFIED")
    renderer._emit(f"   STATE: BER_EMITTED")
    renderer._emit(GATE_HEADER)


def emit_ber_not_emitted_violation(
    pac_id: str,
    reason: str = None,
) -> None:
    """
    Emit BER not emitted violation notification (INV-BER-007 violated).
    
    🟥 BER NOT EMITTED — SESSION TERMINATED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit(f"🟥 BER NOT EMITTED — SESSION TERMINATED {FAIL_SYMBOL}")
    renderer._emit(f"   PAC_ID: {pac_id}")
    if reason:
        renderer._emit(f"   REASON: {reason}")
    renderer._emit(f"   STATE: SESSION_INVALID")
    renderer._emit(f"   VIOLATION: INV-BER-007 (BER_ISSUED_NOT_EMITTED)")
    renderer._emit(GATE_HEADER)


def emit_drafting_surface_in_ber_flow(
    pac_id: str,
    surface_id: str,
) -> None:
    """
    Emit drafting surface in BER flow violation (INV-BER-008 violated).
    
    ⛔ DRAFTING SURFACE IN BER FLOW — PROHIBITED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit(f"⛔ DRAFTING SURFACE IN BER FLOW — PROHIBITED {FAIL_SYMBOL}")
    renderer._emit(f"   PAC_ID: {pac_id}")
    renderer._emit(f"   SURFACE_ID: {surface_id}")
    renderer._emit(f"   VIOLATION: INV-BER-008 (DRAFTING_SURFACE_PROHIBITED)")
    renderer._emit(f"   AUTHORITY: ONLY ORCHESTRATION_ENGINE MAY EMIT BER")
    renderer._emit(f"   RESULT: HARD FAIL — BER REJECTED")
    renderer._emit(GATE_HEADER)


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-020: PDO ARTIFACT EMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════

def emit_proof_locked(
    pac_id: str,
    wrap_id: str,
    proof_hash: str,
) -> None:
    """
    Emit proof locked notification (WRAP data locked for PDO).
    
    🧾 PROOF LOCKED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit(f"🧾 PROOF LOCKED")
    renderer._emit(f"   PAC_ID: {pac_id}")
    renderer._emit(f"   WRAP_ID: {wrap_id}")
    renderer._emit(f"   PROOF_HASH: {proof_hash[:16]}...")
    renderer._emit(f"   LOCKED_AT: {datetime.now(timezone.utc).isoformat()}")
    renderer._emit(GATE_HEADER)


def emit_decision_issued(
    pac_id: str,
    ber_id: str,
    decision: str,
) -> None:
    """
    Emit decision issued notification (BER decision for PDO).
    
    🧠 DECISION ISSUED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit(f"🧠 DECISION ISSUED")
    renderer._emit(f"   PAC_ID: {pac_id}")
    renderer._emit(f"   BER_ID: {ber_id}")
    renderer._emit(f"   DECISION: {decision}")
    renderer._emit(f"   ISSUED_AT: {datetime.now(timezone.utc).isoformat()}")
    renderer._emit(GATE_HEADER)


def emit_pdo_emitted(
    pdo_id: str,
    pac_id: str,
    outcome_status: str,
    pdo_hash: str,
) -> None:
    """
    Emit PDO emitted notification (full PDO artifact created).
    
    🧿 PDO EMITTED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit(f"🧿 PDO EMITTED {PASS_SYMBOL}")
    renderer._emit(f"   PDO_ID: {pdo_id}")
    renderer._emit(f"   PAC_ID: {pac_id}")
    renderer._emit(f"   OUTCOME: {outcome_status}")
    renderer._emit(f"   PDO_HASH: {pdo_hash[:16]}...")
    renderer._emit(f"   EMITTED_AT: {datetime.now(timezone.utc).isoformat()}")
    renderer._emit(GATE_HEADER)


def emit_pdo_creation_failed(
    pac_id: str,
    reason: str,
) -> None:
    """
    Emit PDO creation failure notification.
    
    🟥 PDO CREATION FAILED
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit(f"🟥 PDO CREATION FAILED {FAIL_SYMBOL}")
    renderer._emit(f"   PAC_ID: {pac_id}")
    renderer._emit(f"   REASON: {reason}")
    renderer._emit(f"   RESULT: BER VALID BUT NO PDO — GOVERNANCE WARNING")
    renderer._emit(GATE_HEADER)


def emit_pdo_authority_violation(
    attempted_issuer: str,
    pac_id: str,
) -> None:
    """
    Emit PDO authority violation notification.
    
    ⛔ PDO AUTHORITY VIOLATION
    """
    renderer = get_terminal_renderer()
    renderer._emit("")
    renderer._emit(GATE_HEADER)
    renderer._emit(f"⛔ PDO AUTHORITY VIOLATION {FAIL_SYMBOL}")
    renderer._emit(f"   ATTEMPTED_ISSUER: {attempted_issuer}")
    renderer._emit(f"   PAC_ID: {pac_id}")
    renderer._emit(f"   REQUIRED_AUTHORITY: GID-00 (ORCHESTRATION_ENGINE)")
    renderer._emit(f"   VIOLATION: INV-PDO-002 (ONLY_GID00_MAY_CREATE_PDO)")
    renderer._emit(f"   RESULT: HARD FAIL — PDO REJECTED")
    renderer._emit(GATE_HEADER)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Constants
    "PASS_SYMBOL",
    "FAIL_SYMBOL",
    "PENDING_SYMBOL",
    "SKIP_SYMBOL",
    "BORDER_CHAR",
    "BORDER_WIDTH",
    
    # Enums
    "GateID",
    "GateStatus",
    "GATE_NAMES",
    
    # Data classes
    "GateResult",
    "GateChecklistResult",
    
    # Classes
    "TerminalGateRenderer",
    "TerminalGateEvaluator",
    
    # Singleton access
    "get_terminal_renderer",
    "get_gate_evaluator",
    "reset_terminal_renderer",
    
    # Convenience functions
    "emit_pac_ingest",
    "emit_agent_dispatch",
    "emit_wrap_receipt",
    "emit_ber_approved",
    "emit_ber_rejected",
    "run_gate_checklist",
    
    # PAC-017: Orchestration Engine Emissions
    "emit_orchestration_engine_engaged",
    "emit_persona_authority_rejected",
    "emit_system_governance_decision",
    "emit_ber_authority_violation",
    "emit_wrap_authority_violation",
    "emit_self_approval_blocked",
    
    # PAC-021: BER Emission Enforcement
    "emit_ber_emitted",
    "emit_ber_not_emitted_violation",
    "emit_drafting_surface_in_ber_flow",
    
    # PAC-020: PDO Artifact Emissions
    "emit_proof_locked",
    "emit_decision_issued",
    "emit_pdo_emitted",
    "emit_pdo_creation_failed",
    "emit_pdo_authority_violation",
]
