#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
GOVERNANCE LEDGER WRITER
PAC-ALEX-G1-PHASE-2-GOVERNANCE-LEDGER-AND-PAC-REGISTRY-01
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
══════════════════════════════════════════════════════════════════════════════

PURPOSE:
    Canonical, append-only ledger for all governance artifacts.
    Records PACs, WRAPs, Corrections, and Positive Closures.
    Enables auditability, lineage tracking, and enterprise reporting.

AUTHORITY: ALEX (GID-08)
MODE: FAIL_CLOSED

INVARIANTS:
    - Append-only (no deletions, no overwrites)
    - Monotonic sequencing (no gaps)
    - Every entry has timestamp + authority
    - History is immutable

══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Any


# ============================================================================
# PATHS
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
LEDGER_DIR = REPO_ROOT / "docs" / "governance" / "ledger"
LEDGER_PATH = LEDGER_DIR / "GOVERNANCE_LEDGER.json"


# ============================================================================
# ENUMS
# ============================================================================

class EntryType(Enum):
    """Types of ledger entries."""
    PAC_ISSUED = "PAC_ISSUED"
    PAC_EXECUTED = "PAC_EXECUTED"
    WRAP_SUBMITTED = "WRAP_SUBMITTED"
    WRAP_ACCEPTED = "WRAP_ACCEPTED"
    WRAP_REJECTED = "WRAP_REJECTED"
    CORRECTION_OPENED = "CORRECTION_OPENED"
    CORRECTION_CLOSED = "CORRECTION_CLOSED"
    POSITIVE_CLOSURE_ACKNOWLEDGED = "POSITIVE_CLOSURE_ACKNOWLEDGED"
    VALIDATION_PASS = "VALIDATION_PASS"
    VALIDATION_FAIL = "VALIDATION_FAIL"
    # G2 Learning Ledger Entry Types
    CORRECTION_APPLIED = "CORRECTION_APPLIED"
    BLOCK_ENFORCED = "BLOCK_ENFORCED"
    LEARNING_EVENT = "LEARNING_EVENT"
    # BSRG-01 Entry Type (PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01)
    BSRG_REVIEW = "BSRG_REVIEW"
    # PAC Reservation Entry Types (PAC-ALEX-P42-GOVERNANCE-PAC-SEQUENCE-ENFORCEMENT-AND-RESERVATION-LOCK-01)
    PAC_RESERVATION_CREATED = "PAC_RESERVATION_CREATED"
    PAC_RESERVATION_CONSUMED = "PAC_RESERVATION_CONSUMED"
    PAC_RESERVATION_EXPIRED = "PAC_RESERVATION_EXPIRED"


class ArtifactType(Enum):
    """Types of governance artifacts."""
    PAC = "PAC"
    WRAP = "WRAP"
    CORRECTION = "CORRECTION"
    POSITIVE_CLOSURE = "POSITIVE_CLOSURE"


class ArtifactStatus(Enum):
    """Status of artifacts."""
    ISSUED = "ISSUED"
    EXECUTED = "EXECUTED"
    BLOCKED = "BLOCKED"
    CLOSED = "CLOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class PacState(Enum):
    """
    PAC State Machine (PAC-BENSON-P44).

    State transitions are ONE-WAY:
    ISSUED → EXECUTED → CLOSED

    A PAC cannot reach CLOSED without a valid WRAP binding.
    """
    ISSUED = "ISSUED"      # PAC created, not yet executed
    EXECUTED = "EXECUTED"  # PAC execution complete, awaiting WRAP
    CLOSED = "CLOSED"      # PAC has WRAP bound, immutable


# Valid PAC state transitions (one-way only)
VALID_PAC_TRANSITIONS = {
    PacState.ISSUED: [PacState.EXECUTED],
    PacState.EXECUTED: [PacState.CLOSED],
    PacState.CLOSED: [],  # Terminal state — no transitions allowed
}


class ClosureType(Enum):
    """Types of closure."""
    NONE = "NONE"
    CORRECTION = "CORRECTION"
    POSITIVE = "POSITIVE"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LedgerEntry:
    """A single ledger entry."""
    sequence: int
    timestamp: str  # ISO-8601
    entry_type: str
    agent_gid: str
    agent_name: str
    artifact_type: str
    artifact_id: str
    artifact_status: str
    parent_artifact: Optional[str] = None
    closure_type: str = "NONE"
    validation_result: Optional[str] = None
    error_codes: Optional[list] = None
    notes: Optional[str] = None
    file_path: Optional[str] = None
    # G2 Learning Ledger fields
    training_signal: Optional[dict] = None
    closure_class: Optional[str] = None
    authority_gid: Optional[str] = None
    violations_resolved: Optional[list] = None
    # Hash-chain immutability fields (PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01)
    prev_hash: Optional[str] = None  # SHA256 of previous entry
    entry_hash: Optional[str] = None  # SHA256 of this entry (computed without entry_hash)
    # BSRG-01 specific fields
    artifact_sha256: Optional[str] = None  # SHA256 of artifact content
    bsrg_gate_id: Optional[str] = None
    bsrg_status: Optional[str] = None
    bsrg_failed_items: Optional[list] = None
    bsrg_checklist_results: Optional[dict] = None
    validation_version: Optional[str] = None
    # PAC-BENSON-P44: State Lock & WRAP Binding fields
    pac_state: Optional[str] = None  # ISSUED | EXECUTED | CLOSED
    wrap_binding: Optional[dict] = None  # {wrap_id, wrap_hash, pac_hash, bound_at}


@dataclass
class LedgerMetadata:
    """Ledger metadata."""
    version: str
    created_at: str
    authority: str
    format: str
    schema_version: str


@dataclass
class SequenceState:
    """Sequence tracking state."""
    next_sequence: int
    last_entry_timestamp: Optional[str]
    total_entries: int


@dataclass
class PacSequenceState:
    """
    PAC Sequence State Registry.

    PAC-BENSON-P42-PAC_SEQUENCE_AND_WRAP_DEPENDENCY_ENFORCEMENT-01

    Tracks:
    - last_issued_pac: Most recent PAC issued per agent
    - last_closed_wrap: Most recent WRAP accepted per agent
    - Enforces: P[n+1] can only be issued if WRAP-P[n] is accepted
    """
    agent_gid: str
    agent_name: str
    last_issued_pac: Optional[str] = None  # e.g., "PAC-BENSON-P41-..."
    last_issued_pac_number: Optional[int] = None  # e.g., 41
    last_closed_wrap: Optional[str] = None  # e.g., "WRAP-BENSON-P41-..."
    last_closed_wrap_number: Optional[int] = None  # e.g., 41
    wrap_pending: bool = False  # True if last PAC has no WRAP yet
    sequence_valid: bool = True  # False if out-of-sync


# ============================================================================
# AGENT REGISTRY (FOR VALIDATION)
# ============================================================================

AGENT_REGISTRY = {
    "GID-00": "BENSON",
    "GID-01": "SONNY",
    "GID-02": "MAGGIE",
    "GID-03": "CODY",
    "GID-04": "DAN",
    "GID-05": "CARTER",
    "GID-06": "SAM",
    "GID-07": "DAN",
    "GID-08": "ALEX",
    "GID-09": "TINA",
    "GID-10": "MAGGIE",
    "GID-11": "ATLAS",
    "GID-12": "RUBY",
}


# ============================================================================
# LEDGER WRITER CLASS
# ============================================================================

class GovernanceLedger:
    """
    Governance Ledger — Append-only record of all governance artifacts.

    Invariants:
    - No deletions
    - No overwrites
    - Monotonic sequencing
    - Every entry timestamped
    - Hash-chained (tamper-evident)
    """

    # Validation tool version for audit trail
    VALIDATION_VERSION = "1.1.0-BSRG"

    def __init__(self, ledger_path: Optional[Path] = None):
        self.ledger_path = ledger_path or LEDGER_PATH
        self.ledger_data = self._load_ledger()

    def _load_ledger(self) -> dict:
        """Load ledger from disk."""
        if not self.ledger_path.exists():
            return self._create_empty_ledger()

        with open(self.ledger_path, "r") as f:
            return json.load(f)

    def _create_empty_ledger(self) -> dict:
        """Create empty ledger structure."""
        return {
            "ledger_metadata": {
                "version": "1.1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "authority": "ALEX (GID-08)",
                "format": "APPEND_ONLY_HASH_CHAINED",
                "schema_version": "1.1.0",
                "hash_algorithm": "SHA256"
            },
            "sequence_state": {
                "next_sequence": 1,
                "last_entry_timestamp": None,
                "total_entries": 0,
                "last_entry_hash": None
            },
            "agent_sequences": {},
            "entries": []
        }

    def _save_ledger(self):
        """Save ledger to disk (append-only semantics enforced)."""
        # Ensure directory exists
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.ledger_path, "w") as f:
            json.dump(self.ledger_data, f, indent=2)

    def _get_next_sequence(self) -> int:
        """Get and increment sequence number."""
        seq = self.ledger_data["sequence_state"]["next_sequence"]
        self.ledger_data["sequence_state"]["next_sequence"] = seq + 1
        return seq

    def _get_last_entry_hash(self) -> Optional[str]:
        """Get hash of the last entry (for chain linking)."""
        entries = self.ledger_data.get("entries", [])
        if not entries:
            return None
        return entries[-1].get("entry_hash")

    def _compute_entry_hash(self, entry_dict: dict) -> str:
        """
        Compute SHA256 hash of entry for chain integrity.

        Uses deterministic JSON serialization (sorted keys).
        Excludes entry_hash field from computation.
        """
        import hashlib

        # Create copy without entry_hash for hashing
        hash_dict = {k: v for k, v in entry_dict.items() if k != "entry_hash"}

        # Deterministic serialization
        canonical_json = json.dumps(hash_dict, sort_keys=True, separators=(',', ':'))

        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def _update_agent_sequences(self, gid: str, artifact_type: str):
        """Update per-agent sequence counters."""
        if gid not in self.ledger_data["agent_sequences"]:
            self.ledger_data["agent_sequences"][gid] = {
                "pac_count": 0,
                "wrap_count": 0,
                "correction_count": 0,
                "positive_closure_count": 0
            }

        if artifact_type == "PAC":
            self.ledger_data["agent_sequences"][gid]["pac_count"] += 1
        elif artifact_type == "WRAP":
            self.ledger_data["agent_sequences"][gid]["wrap_count"] += 1
        elif artifact_type == "CORRECTION":
            self.ledger_data["agent_sequences"][gid]["correction_count"] += 1
        elif artifact_type == "POSITIVE_CLOSURE":
            self.ledger_data["agent_sequences"][gid]["positive_closure_count"] = \
                self.ledger_data["agent_sequences"][gid].get("positive_closure_count", 0) + 1

    # ========================================================================
    # PUBLIC API — WRITE OPERATIONS
    # ========================================================================

    def record_pac_issued(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """Record a PAC being issued."""
        entry = self._create_entry(
            entry_type=EntryType.PAC_ISSUED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=ArtifactType.PAC.value,
            artifact_id=artifact_id,
            artifact_status=ArtifactStatus.ISSUED.value,
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        self._update_agent_sequences(agent_gid, "PAC")
        return entry

    def record_pac_executed(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """Record a PAC being executed."""
        entry = self._create_entry(
            entry_type=EntryType.PAC_EXECUTED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=ArtifactType.PAC.value,
            artifact_id=artifact_id,
            artifact_status=ArtifactStatus.EXECUTED.value,
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        return entry

    def record_wrap_submitted(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        parent_pac_id: str,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """Record a WRAP being submitted."""
        entry = self._create_entry(
            entry_type=EntryType.WRAP_SUBMITTED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=ArtifactType.WRAP.value,
            artifact_id=artifact_id,
            artifact_status=ArtifactStatus.ISSUED.value,
            parent_artifact=parent_pac_id,
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        self._update_agent_sequences(agent_gid, "WRAP")
        return entry

    def record_wrap_accepted(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        ratified_by: str,
        file_path: Optional[str] = None,
        notes: Optional[str] = None,
        authority_override: bool = False
    ) -> LedgerEntry:
        """
        Record a WRAP being accepted.

        PAC-BENSON-P48: BENSON EXECUTION AUTHORITY ENFORCEMENT
        ═══════════════════════════════════════════════════════════════════════
        Only GID-00 (Benson) may emit WRAP_ACCEPTED entries.
        Agent-originated WRAPs are blocked. All work must flow through
        BENSON_EXECUTION runtime which validates and generates canonical WRAPs.

        Args:
            artifact_id: WRAP artifact ID
            agent_gid: GID of the agent whose work is being accepted
            agent_name: Name of the agent
            ratified_by: Authority ratifying the WRAP (must be BENSON/GID-00)
            file_path: Optional file path
            notes: Optional notes
            authority_override: INTERNAL ONLY - bypass for migration scripts

        Raises:
            ValueError: If ratified_by is not Benson (GID-00)
        """
        # ═══════════════════════════════════════════════════════════════════════
        # PAC-BENSON-P48: BENSON-ONLY WRAP AUTHORITY ENFORCEMENT
        # ═══════════════════════════════════════════════════════════════════════
        # HARD BLOCK: Only Benson (GID-00) may ratify/accept WRAPs
        # Agent-originated WRAP_ACCEPTED entries are FORBIDDEN
        benson_identifiers = ["BENSON", "GID-00", "BENSON (GID-00)"]
        ratifier_normalized = ratified_by.upper().strip()

        is_benson_authority = any(
            ident in ratifier_normalized for ident in benson_identifiers
        )

        if not is_benson_authority and not authority_override:
            raise ValueError(
                f"GS_120: WRAP_AUTHORITY_VIOLATION — Only Benson (GID-00) may emit WRAP_ACCEPTED. "
                f"Attempted authority: '{ratified_by}'. "
                f"Agent work must be submitted as EXECUTION_RESULT for Benson validation."
            )
        # ═══════════════════════════════════════════════════════════════════════

        entry = self._create_entry(
            entry_type=EntryType.WRAP_ACCEPTED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=ArtifactType.WRAP.value,
            artifact_id=artifact_id,
            artifact_status=ArtifactStatus.ACCEPTED.value,
            file_path=file_path,
            notes=f"Ratified by: {ratified_by}. {notes or ''}"
        )
        # Set authority_gid on entry object (Benson authority always recorded)
        entry.authority_gid = "GID-00"
        self._append_entry(entry)
        return entry

    def record_correction_opened(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        parent_artifact: str,
        error_codes: list,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """Record a correction being opened."""
        entry = self._create_entry(
            entry_type=EntryType.CORRECTION_OPENED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=ArtifactType.CORRECTION.value,
            artifact_id=artifact_id,
            artifact_status=ArtifactStatus.ISSUED.value,
            parent_artifact=parent_artifact,
            closure_type=ClosureType.CORRECTION.value,
            error_codes=error_codes,
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        self._update_agent_sequences(agent_gid, "CORRECTION")
        return entry

    def record_correction_closed(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        parent_artifact: str,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """Record a correction being closed."""
        entry = self._create_entry(
            entry_type=EntryType.CORRECTION_CLOSED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=ArtifactType.CORRECTION.value,
            artifact_id=artifact_id,
            artifact_status=ArtifactStatus.CLOSED.value,
            parent_artifact=parent_artifact,
            closure_type=ClosureType.CORRECTION.value,
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        return entry

    def record_positive_closure(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        parent_artifact: str,
        closure_authority: str,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """Record a positive closure acknowledgment."""
        entry = self._create_entry(
            entry_type=EntryType.POSITIVE_CLOSURE_ACKNOWLEDGED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=ArtifactType.POSITIVE_CLOSURE.value,
            artifact_id=artifact_id,
            artifact_status=ArtifactStatus.CLOSED.value,
            parent_artifact=parent_artifact,
            closure_type=ClosureType.POSITIVE.value,
            file_path=file_path,
            notes=f"Closure Authority: {closure_authority}. {notes or ''}"
        )
        self._append_entry(entry)
        self._update_agent_sequences(agent_gid, "POSITIVE_CLOSURE")
        return entry

    def record_validation_pass(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        artifact_type: str,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """Record a validation pass event."""
        entry = self._create_entry(
            entry_type=EntryType.VALIDATION_PASS.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            artifact_status=ArtifactStatus.EXECUTED.value,
            validation_result="PASS",
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        return entry

    def record_validation_fail(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        artifact_type: str,
        error_codes: list,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """Record a validation failure event."""
        entry = self._create_entry(
            entry_type=EntryType.VALIDATION_FAIL.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            artifact_status=ArtifactStatus.BLOCKED.value,
            validation_result="FAIL",
            error_codes=error_codes,
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        return entry

    # ========================================================================
    # G2 LEARNING LEDGER OPERATIONS
    # ========================================================================

    def record_correction_applied(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        pac_id: str,
        wrap_id: str,
        authority_gid: str,
        violations_resolved: list,
        training_signal: Optional[dict] = None,
        closure_class: Optional[str] = None,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """
        Record a correction being applied — LEARNING EVENT.

        This is a learning signal that records when an agent's work
        was corrected and they incorporated the feedback.
        """
        entry = self._create_learning_entry(
            entry_type=EntryType.CORRECTION_APPLIED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_id=artifact_id,
            pac_id=pac_id,
            wrap_id=wrap_id,
            authority_gid=authority_gid,
            violations_resolved=violations_resolved,
            training_signal=training_signal,
            closure_class=closure_class or "CORRECTION",
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        self._update_learning_stats(agent_gid, "corrections_learned")
        return entry

    def record_block_enforced(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        pac_id: str,
        authority_gid: str,
        error_codes: list,
        training_signal: Optional[dict] = None,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """
        Record a governance block being enforced — LEARNING EVENT.

        This is a learning signal that records when an agent's work
        was blocked by governance gates.
        """
        entry = self._create_learning_entry(
            entry_type=EntryType.BLOCK_ENFORCED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_id=artifact_id,
            pac_id=pac_id,
            wrap_id=None,
            authority_gid=authority_gid,
            violations_resolved=None,
            training_signal=training_signal,
            closure_class="BLOCK",
            error_codes=error_codes,
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        self._update_learning_stats(agent_gid, "blocks_received")
        return entry

    def record_learning_event(
        self,
        artifact_id: str,
        agent_gid: str,
        agent_name: str,
        pac_id: str,
        wrap_id: Optional[str],
        authority_gid: str,
        training_signal: dict,
        closure_class: str,
        violations_resolved: Optional[list] = None,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """
        Record a generic learning event.

        This is the universal learning signal that can capture
        any type of governance-triggered learning.
        """
        entry = self._create_learning_entry(
            entry_type=EntryType.LEARNING_EVENT.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_id=artifact_id,
            pac_id=pac_id,
            wrap_id=wrap_id,
            authority_gid=authority_gid,
            violations_resolved=violations_resolved,
            training_signal=training_signal,
            closure_class=closure_class,
            file_path=file_path,
            notes=notes
        )
        self._append_entry(entry)
        self._update_learning_stats(agent_gid, "learning_events")
        return entry

    def _create_learning_entry(
        self,
        entry_type: str,
        agent_gid: str,
        agent_name: str,
        artifact_id: str,
        pac_id: str,
        wrap_id: Optional[str],
        authority_gid: str,
        violations_resolved: Optional[list],
        training_signal: Optional[dict],
        closure_class: str,
        error_codes: Optional[list] = None,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """Create a learning ledger entry with extended fields."""
        return LedgerEntry(
            sequence=self._get_next_sequence(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry_type=entry_type,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type="LEARNING_EVENT",
            artifact_id=artifact_id,
            artifact_status="RECORDED",
            parent_artifact=pac_id,
            closure_type=closure_class,
            validation_result=None,
            error_codes=error_codes,
            notes=f"WRAP: {wrap_id or 'N/A'}. {notes or ''}",
            file_path=file_path,
            training_signal=training_signal,
            closure_class=closure_class,
            authority_gid=authority_gid,
            violations_resolved=violations_resolved
        )

    def _update_learning_stats(self, agent_gid: str, stat_type: str):
        """Update per-agent learning statistics."""
        if agent_gid not in self.ledger_data["agent_sequences"]:
            self.ledger_data["agent_sequences"][agent_gid] = {
                "pac_count": 0,
                "wrap_count": 0,
                "correction_count": 0,
                "positive_closure_count": 0
            }

        # Initialize learning stats if not present
        if "learning_stats" not in self.ledger_data["agent_sequences"][agent_gid]:
            self.ledger_data["agent_sequences"][agent_gid]["learning_stats"] = {
                "corrections_learned": 0,
                "blocks_received": 0,
                "learning_events": 0
            }

        self.ledger_data["agent_sequences"][agent_gid]["learning_stats"][stat_type] = \
            self.ledger_data["agent_sequences"][agent_gid]["learning_stats"].get(stat_type, 0) + 1

    def get_learning_events_by_agent(self, agent_gid: str) -> list:
        """Get all learning events for a specific agent."""
        learning_types = [
            EntryType.CORRECTION_APPLIED.value,
            EntryType.BLOCK_ENFORCED.value,
            EntryType.LEARNING_EVENT.value,
            EntryType.POSITIVE_CLOSURE_ACKNOWLEDGED.value
        ]
        return [
            e for e in self.ledger_data["entries"]
            if e.get("agent_gid") == agent_gid and e.get("entry_type") in learning_types
        ]

    def get_agent_learning_summary(self, agent_gid: str) -> dict:
        """Get learning summary for an agent."""
        events = self.get_learning_events_by_agent(agent_gid)
        stats = self.ledger_data["agent_sequences"].get(agent_gid, {}).get("learning_stats", {})

        return {
            "agent_gid": agent_gid,
            "total_learning_events": len(events),
            "corrections_learned": stats.get("corrections_learned", 0),
            "blocks_received": stats.get("blocks_received", 0),
            "positive_closures": len([e for e in events if e.get("entry_type") == EntryType.POSITIVE_CLOSURE_ACKNOWLEDGED.value]),
            "events": events
        }

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    def _create_entry(
        self,
        entry_type: str,
        agent_gid: str,
        agent_name: str,
        artifact_type: str,
        artifact_id: str,
        artifact_status: str,
        parent_artifact: Optional[str] = None,
        closure_type: str = "NONE",
        validation_result: Optional[str] = None,
        error_codes: Optional[list] = None,
        notes: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> LedgerEntry:
        """Create a ledger entry."""
        return LedgerEntry(
            sequence=self._get_next_sequence(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry_type=entry_type,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            artifact_status=artifact_status,
            parent_artifact=parent_artifact,
            closure_type=closure_type,
            validation_result=validation_result,
            error_codes=error_codes,
            notes=notes,
            file_path=file_path
        )

    def _append_entry(self, entry: LedgerEntry):
        """
        Append entry to ledger (immutable, hash-chained).

        Hash Chain Implementation:
        1. Get prev_hash from last entry
        2. Create entry dict without entry_hash
        3. Compute entry_hash from canonical JSON
        4. Store entry with both hashes
        5. Update sequence state with new hash
        """
        # Get hash of previous entry for chain linking
        prev_hash = self._get_last_entry_hash()
        entry.prev_hash = prev_hash

        # Convert to dict
        entry_dict = asdict(entry)

        # Compute entry hash (without entry_hash field)
        entry_hash = self._compute_entry_hash(entry_dict)
        entry_dict["entry_hash"] = entry_hash

        # Append to ledger
        self.ledger_data["entries"].append(entry_dict)
        self.ledger_data["sequence_state"]["last_entry_timestamp"] = entry.timestamp
        self.ledger_data["sequence_state"]["total_entries"] = len(self.ledger_data["entries"])
        self.ledger_data["sequence_state"]["last_entry_hash"] = entry_hash

        self._save_ledger()

    # ========================================================================
    # BSRG-01 OPERATIONS (PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01)
    # ========================================================================

    def record_bsrg_review(
        self,
        artifact_id: str,
        artifact_sha256: str,
        reviewer: str,
        reviewer_gid: str,
        bsrg_gate_id: str,
        status: str,
        failed_items: list = None,
        checklist_results: dict = None,
        file_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """
        Record a BSRG (Benson Self-Review Gate) review result.

        This creates a tamper-evident audit trail entry for PAC reviews.

        Args:
            artifact_id: The PAC ID being reviewed
            artifact_sha256: SHA256 hash of artifact content
            reviewer: Reviewer name (must be BENSON)
            reviewer_gid: Reviewer GID (must be GID-00)
            bsrg_gate_id: Gate ID (must be BSRG-01)
            status: PASS or FAIL
            failed_items: List of items that failed (if any)
            checklist_results: Dict of checklist item results
            file_path: Path to the artifact file
            notes: Optional notes

        Returns:
            The created LedgerEntry
        """
        entry = LedgerEntry(
            sequence=self._get_next_sequence(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry_type=EntryType.BSRG_REVIEW.value,
            agent_gid=reviewer_gid,
            agent_name=reviewer,
            artifact_type="PAC",
            artifact_id=artifact_id,
            artifact_status="REVIEWED",
            parent_artifact=None,
            closure_type="NONE",
            validation_result=status,
            error_codes=failed_items if status == "FAIL" else None,
            notes=notes,
            file_path=file_path,
            training_signal={
                "signal_type": "BSRG_REVIEW_RECORDED",
                "pattern": "SELF_REVIEW_GATE_ENFORCEMENT",
                "learning": [
                    "BSRG-01 provides tamper-evident review audit",
                    f"Review status: {status}",
                    f"Artifact: {artifact_id}"
                ]
            } if status == "PASS" else {
                "signal_type": "BSRG_REVIEW_BLOCKED",
                "pattern": "SELF_REVIEW_GATE_ENFORCEMENT",
                "learning": [
                    "BSRG-01 blocked invalid PAC",
                    f"Failed items: {failed_items[:3] if failed_items else []}",
                ]
            },
            closure_class="BSRG_REVIEW",
            authority_gid="GID-00",  # BENSON
            violations_resolved=None,
            artifact_sha256=artifact_sha256,
            bsrg_gate_id=bsrg_gate_id,
            bsrg_status=status,
            bsrg_failed_items=failed_items or [],
            bsrg_checklist_results=checklist_results or {},
            validation_version=self.VALIDATION_VERSION
        )

        self._append_entry(entry)
        self._update_bsrg_stats(reviewer_gid, status)
        return entry

    def _update_bsrg_stats(self, agent_gid: str, status: str):
        """Update BSRG statistics for agent."""
        if agent_gid not in self.ledger_data["agent_sequences"]:
            self.ledger_data["agent_sequences"][agent_gid] = {
                "pac_count": 0,
                "wrap_count": 0,
                "correction_count": 0,
                "positive_closure_count": 0
            }

        # Initialize BSRG stats if not present
        if "bsrg_stats" not in self.ledger_data["agent_sequences"][agent_gid]:
            self.ledger_data["agent_sequences"][agent_gid]["bsrg_stats"] = {
                "reviews_passed": 0,
                "reviews_failed": 0,
                "total_reviews": 0
            }

        stats = self.ledger_data["agent_sequences"][agent_gid]["bsrg_stats"]
        stats["total_reviews"] += 1
        if status == "PASS":
            stats["reviews_passed"] += 1
        else:
            stats["reviews_failed"] += 1

    def get_bsrg_reviews(self, artifact_id: Optional[str] = None) -> list:
        """Get BSRG review entries, optionally filtered by artifact."""
        entries = [
            e for e in self.ledger_data["entries"]
            if e.get("entry_type") == EntryType.BSRG_REVIEW.value
        ]

        if artifact_id:
            entries = [e for e in entries if e.get("artifact_id") == artifact_id]

        return entries

    # ========================================================================
    # PAC RESERVATION OPERATIONS (PAC-ALEX-P42-GOVERNANCE-PAC-SEQUENCE-ENFORCEMENT-AND-RESERVATION-LOCK-01)
    # ========================================================================

    def reserve_pac_number(
        self,
        pac_number: int,
        reserved_for_agent_gid: str,
        reserved_for_agent_name: str,
        authority_gid: str,
        authority_name: str,
        expires_in_hours: int = 24,
        notes: Optional[str] = None
    ) -> LedgerEntry:
        """
        Reserve a PAC number for a specific agent.

        Rules:
        - PAC numbers must be reserved before emission
        - Reservations are single-use (consumed on PAC issuance)
        - Reservations expire after expires_in_hours (max 24h)
        - Only BENSON or delegated authorities can reserve

        Args:
            pac_number: The PAC phase number to reserve (e.g., 42 for P42)
            reserved_for_agent_gid: GID of agent allowed to emit PAC
            reserved_for_agent_name: Name of agent allowed to emit PAC
            authority_gid: GID of reserving authority
            authority_name: Name of reserving authority
            expires_in_hours: Hours until reservation expires (max 24)
            notes: Optional notes

        Returns:
            The created LedgerEntry for the reservation
        """
        from datetime import timedelta

        # Enforce max expiration of 24 hours
        expires_in_hours = min(expires_in_hours, 24)

        # Calculate expiration timestamp
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        # Check if this number is already reserved and not consumed/expired
        existing = self.get_active_reservation(pac_number)
        if existing:
            raise ValueError(
                f"PAC number P{pac_number} already has active reservation for "
                f"{existing.get('reserved_for_agent_name')} ({existing.get('reserved_for_agent_gid')})"
            )

        entry = LedgerEntry(
            sequence=self._get_next_sequence(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry_type=EntryType.PAC_RESERVATION_CREATED.value,
            agent_gid=reserved_for_agent_gid,
            agent_name=reserved_for_agent_name,
            artifact_type="PAC_RESERVATION",
            artifact_id=f"PAC-RESERVATION-P{pac_number:02d}",
            artifact_status="RESERVED",
            parent_artifact=None,
            closure_type="NONE",
            validation_result=None,
            error_codes=None,
            notes=notes or f"Reserved P{pac_number} for {reserved_for_agent_name}",
            file_path=None,
            training_signal={
                "signal_type": "PAC_NUMBER_RESERVED",
                "pattern": "PAC_SEQUENCE_IS_LAW",
                "learning": [
                    f"PAC number P{pac_number} reserved for {reserved_for_agent_name}",
                    f"Authority: {authority_name} ({authority_gid})",
                    f"Expires: {expires_at.isoformat()}"
                ]
            },
            closure_class="RESERVATION",
            authority_gid=authority_gid,
            violations_resolved=None
        )

        # Add reservation-specific fields to entry dict before appending
        entry_dict = asdict(entry)
        entry_dict["pac_number"] = pac_number
        entry_dict["reserved_for_agent_gid"] = reserved_for_agent_gid
        entry_dict["reserved_for_agent_name"] = reserved_for_agent_name
        entry_dict["expires_at"] = expires_at.isoformat()
        entry_dict["reservation_status"] = "ACTIVE"

        # Get prev_hash and compute entry_hash
        entry_dict["prev_hash"] = self._get_last_entry_hash()
        entry_dict["entry_hash"] = self._compute_entry_hash(entry_dict)

        # Append directly to ledger
        self.ledger_data["entries"].append(entry_dict)
        self.ledger_data["sequence_state"]["last_entry_timestamp"] = entry.timestamp
        self.ledger_data["sequence_state"]["total_entries"] = len(self.ledger_data["entries"])
        self.ledger_data["sequence_state"]["last_entry_hash"] = entry_dict["entry_hash"]

        self._save_ledger()

        return entry

    def consume_reservation(
        self,
        pac_number: int,
        pac_id: str,
        agent_gid: str,
        agent_name: str
    ) -> LedgerEntry:
        """
        Consume a PAC reservation when PAC is issued.

        Args:
            pac_number: The PAC phase number (e.g., 42 for P42)
            pac_id: The full PAC ID being issued
            agent_gid: GID of agent issuing the PAC
            agent_name: Name of agent issuing the PAC

        Returns:
            The created LedgerEntry for consumption

        Raises:
            ValueError: If no active reservation exists or reservation doesn't match
        """
        reservation = self.get_active_reservation(pac_number)
        if not reservation:
            raise ValueError(
                f"No active reservation for PAC number P{pac_number}. "
                "Reserve PAC number before emission."
            )

        # Validate reservation matches agent
        if reservation.get("reserved_for_agent_gid") != agent_gid:
            raise ValueError(
                f"Reservation for P{pac_number} is for {reservation.get('reserved_for_agent_name')} "
                f"({reservation.get('reserved_for_agent_gid')}), not {agent_name} ({agent_gid})"
            )

        entry = LedgerEntry(
            sequence=self._get_next_sequence(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry_type=EntryType.PAC_RESERVATION_CONSUMED.value,
            agent_gid=agent_gid,
            agent_name=agent_name,
            artifact_type="PAC_RESERVATION",
            artifact_id=f"PAC-RESERVATION-P{pac_number:02d}",
            artifact_status="CONSUMED",
            parent_artifact=pac_id,
            closure_type="NONE",
            validation_result=None,
            error_codes=None,
            notes=f"Reservation P{pac_number} consumed by {pac_id}",
            file_path=None,
            training_signal={
                "signal_type": "PAC_RESERVATION_CONSUMED",
                "pattern": "PAC_SEQUENCE_IS_LAW",
                "learning": [
                    f"PAC number P{pac_number} consumed by {pac_id}",
                    f"Issued by: {agent_name} ({agent_gid})"
                ]
            },
            closure_class="RESERVATION_CONSUMED",
            authority_gid=agent_gid,
            violations_resolved=None
        )

        # Add reservation-specific fields
        entry_dict = asdict(entry)
        entry_dict["pac_number"] = pac_number
        entry_dict["consumed_by_pac_id"] = pac_id
        entry_dict["reservation_status"] = "CONSUMED"
        entry_dict["original_reservation_sequence"] = reservation.get("sequence")

        # Get prev_hash and compute entry_hash
        entry_dict["prev_hash"] = self._get_last_entry_hash()
        entry_dict["entry_hash"] = self._compute_entry_hash(entry_dict)

        # Append directly to ledger
        self.ledger_data["entries"].append(entry_dict)
        self.ledger_data["sequence_state"]["last_entry_timestamp"] = entry.timestamp
        self.ledger_data["sequence_state"]["total_entries"] = len(self.ledger_data["entries"])
        self.ledger_data["sequence_state"]["last_entry_hash"] = entry_dict["entry_hash"]

        self._save_ledger()

        return entry

    def get_active_reservation(self, pac_number: int) -> Optional[dict]:
        """
        Get active (not consumed, not expired) reservation for a PAC number.

        Args:
            pac_number: The PAC phase number to check

        Returns:
            The reservation entry dict if active, None otherwise
        """
        # Find all reservation entries for this PAC number
        reservations = [
            e for e in self.ledger_data["entries"]
            if e.get("entry_type") == EntryType.PAC_RESERVATION_CREATED.value
            and e.get("pac_number") == pac_number
        ]

        if not reservations:
            return None

        # Get the most recent reservation
        reservation = reservations[-1]

        # Check if consumed
        consumed = [
            e for e in self.ledger_data["entries"]
            if e.get("entry_type") == EntryType.PAC_RESERVATION_CONSUMED.value
            and e.get("pac_number") == pac_number
            and e.get("original_reservation_sequence") == reservation.get("sequence")
        ]

        if consumed:
            return None  # Reservation was consumed

        # Check if expired
        expires_at_str = reservation.get("expires_at")
        if expires_at_str:
            from datetime import datetime
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                return None  # Reservation expired

        return reservation

    def get_all_reservations(self) -> list:
        """Get all reservation entries (created, consumed, expired)."""
        return [
            e for e in self.ledger_data["entries"]
            if e.get("entry_type") in [
                EntryType.PAC_RESERVATION_CREATED.value,
                EntryType.PAC_RESERVATION_CONSUMED.value,
                EntryType.PAC_RESERVATION_EXPIRED.value
            ]
        ]

    def get_next_available_pac_number(self) -> int:
        """
        Get the next available PAC number for reservation.

        Scans issued PACs to find the highest P## number used.

        Returns:
            The next available PAC number
        """
        max_pac_number = 0

        for entry in self.ledger_data["entries"]:
            artifact_id = entry.get("artifact_id", "")
            # Match PAC-AGENT-P##-* pattern
            import re
            match = re.search(r'PAC-[A-Z]+-P(\d+)-', artifact_id)
            if match:
                pac_num = int(match.group(1))
                max_pac_number = max(max_pac_number, pac_num)

        # Also check reservations
        for entry in self.ledger_data["entries"]:
            if entry.get("entry_type") == EntryType.PAC_RESERVATION_CREATED.value:
                pac_num = entry.get("pac_number", 0)
                max_pac_number = max(max_pac_number, pac_num)

        return max_pac_number + 1

    def validate_pac_sequence(self, pac_id: str, agent_gid: str) -> dict:
        """
        Validate that a PAC can be issued based on sequence rules.

        Args:
            pac_id: The full PAC ID to validate
            agent_gid: The GID of the agent issuing the PAC

        Returns:
            dict with 'valid', 'error_code', 'message' keys
        """
        import re

        # Extract P## from PAC ID
        match = re.search(r'PAC-[A-Z]+-P(\d+)-', pac_id)
        if not match:
            return {
                "valid": False,
                "error_code": "GS_096",
                "message": f"Cannot extract PAC number from ID: {pac_id}"
            }

        pac_number = int(match.group(1))

        # Check for active reservation
        reservation = self.get_active_reservation(pac_number)

        if not reservation:
            # No reservation — check if this is the next sequential number
            next_available = self.get_next_available_pac_number()

            if pac_number < next_available:
                return {
                    "valid": False,
                    "error_code": "GS_096",
                    "message": f"PAC sequence violation: P{pac_number} < next available P{next_available}"
                }
            elif pac_number > next_available:
                return {
                    "valid": False,
                    "error_code": "GS_097",
                    "message": f"PAC reservation required: P{pac_number} not reserved. Next available: P{next_available}"
                }
        else:
            # Reservation exists — validate it matches
            if reservation.get("reserved_for_agent_gid") != agent_gid:
                return {
                    "valid": False,
                    "error_code": "GS_098",
                    "message": (
                        f"PAC reservation invalid: P{pac_number} reserved for "
                        f"{reservation.get('reserved_for_agent_name')} ({reservation.get('reserved_for_agent_gid')})"
                    )
                }

        return {
            "valid": True,
            "error_code": None,
            "message": f"PAC sequence valid: P{pac_number}"
        }

    def get_pacs_awaiting_wrap(self, agent_gid: Optional[str] = None) -> list:
        """
        Get all PACs that have been issued/executed but have no corresponding WRAP.

        PAC-BENSON-P42-SEQUENTIAL-PAC-WRAP-GATING-AND-CAUSAL-ADVANCEMENT-ENFORCEMENT-01

        A PAC is considered OPEN until a corresponding WRAP_SUBMITTED or WRAP_ACCEPTED
        entry exists with matching parent_artifact.

        Args:
            agent_gid: Optional filter by agent

        Returns:
            List of PAC artifact IDs without corresponding WRAPs
        """
        import re

        # Collect all issued/executed PACs
        pacs_issued = {}
        for entry in self.ledger_data["entries"]:
            if entry.get("entry_type") in [
                EntryType.PAC_ISSUED.value,
                EntryType.PAC_EXECUTED.value
            ]:
                artifact_id = entry.get("artifact_id", "")
                if artifact_id and artifact_id.startswith("PAC-"):
                    if agent_gid is None or entry.get("agent_gid") == agent_gid:
                        pacs_issued[artifact_id] = entry

        # Collect all WRAPs (submitted or accepted)
        wrapped_pacs = set()
        for entry in self.ledger_data["entries"]:
            if entry.get("entry_type") in [
                EntryType.WRAP_SUBMITTED.value,
                EntryType.WRAP_ACCEPTED.value
            ]:
                parent_pac = entry.get("parent_artifact")
                if parent_pac:
                    wrapped_pacs.add(parent_pac)

        # PACs awaiting WRAP = issued - wrapped
        open_pacs = []
        for pac_id in pacs_issued:
            if pac_id not in wrapped_pacs:
                open_pacs.append(pac_id)

        return sorted(open_pacs)

    def validate_causal_advancement(self, pac_id: str, agent_gid: str) -> dict:
        """
        Validate that causal advancement rules allow this PAC to be issued.

        PAC-BENSON-P42-SEQUENTIAL-PAC-WRAP-GATING-AND-CAUSAL-ADVANCEMENT-ENFORCEMENT-01

        Rules:
        1. No new PAC may be issued if a prior PAC for this agent lacks a WRAP
        2. PAC numbers must advance sequentially (Pn → Pn+1)

        Args:
            pac_id: The full PAC ID to validate
            agent_gid: The GID of the issuing agent

        Returns:
            dict with 'valid', 'error_code', 'message', 'blocking_pac' keys
        """
        import re

        # Extract P## from PAC ID
        match = re.search(r'PAC-([A-Z]+)-P(\d+)-', pac_id)
        if not match:
            return {
                "valid": False,
                "error_code": "GS_097",
                "message": f"Cannot extract PAC number from ID: {pac_id}",
                "blocking_pac": None
            }

        agent_name = match.group(1)
        pac_number = int(match.group(2))

        # Check for open PACs by this agent
        open_pacs = self.get_pacs_awaiting_wrap(agent_gid)

        if open_pacs:
            # Extract P## numbers from open PACs
            open_pac_numbers = []
            for open_pac in open_pacs:
                open_match = re.search(r'PAC-[A-Z]+-P(\d+)-', open_pac)
                if open_match:
                    open_pac_numbers.append((int(open_match.group(1)), open_pac))

            # Sort by P## number
            open_pac_numbers.sort(key=lambda x: x[0])

            if open_pac_numbers:
                # Check if any prior PAC is blocking
                for open_num, open_pac_id in open_pac_numbers:
                    if open_num < pac_number:
                        return {
                            "valid": False,
                            "error_code": "GS_096",
                            "message": (
                                f"Missing WRAP for prior PAC: {open_pac_id}. "
                                f"Cannot issue P{pac_number} until P{open_num} has a WRAP."
                            ),
                            "blocking_pac": open_pac_id
                        }

        # Check sequential advancement
        highest_pac = self._get_highest_pac_number_for_agent(agent_gid)

        if highest_pac is not None and pac_number != highest_pac + 1:
            if pac_number <= highest_pac:
                return {
                    "valid": False,
                    "error_code": "GS_097",
                    "message": f"PAC number out of sequence: P{pac_number} ≤ highest P{highest_pac}",
                    "blocking_pac": None
                }
            elif pac_number > highest_pac + 1:
                return {
                    "valid": False,
                    "error_code": "GS_097",
                    "message": (
                        f"PAC number gap: Cannot skip from P{highest_pac} to P{pac_number}. "
                        f"Next expected: P{highest_pac + 1}"
                    ),
                    "blocking_pac": None
                }

        return {
            "valid": True,
            "error_code": None,
            "message": f"Causal advancement valid: P{pac_number}",
            "blocking_pac": None
        }

    def _get_highest_pac_number_for_agent(self, agent_gid: str) -> Optional[int]:
        """Get the highest PAC P## number issued by an agent."""
        import re

        max_num = None
        for entry in self.ledger_data["entries"]:
            if entry.get("agent_gid") == agent_gid:
                artifact_id = entry.get("artifact_id", "")
                match = re.search(r'PAC-[A-Z]+-P(\d+)-', artifact_id)
                if match:
                    pac_num = int(match.group(1))
                    if max_num is None or pac_num > max_num:
                        max_num = pac_num

        return max_num

    def bind_wrap_to_pac(self, wrap_id: str, pac_id: str) -> dict:
        """
        Record the binding of a WRAP to its originating PAC.

        PAC-BENSON-P42-SEQUENTIAL-PAC-WRAP-GATING-AND-CAUSAL-ADVANCEMENT-ENFORCEMENT-01

        This closes the PAC (marks it as no longer OPEN).

        Args:
            wrap_id: The WRAP artifact ID
            pac_id: The parent PAC artifact ID

        Returns:
            dict with 'success', 'message' keys
        """
        import re

        # Validate WRAP↔PAC number match
        wrap_match = re.search(r'WRAP-([A-Z]+)-P(\d+)-', wrap_id)
        pac_match = re.search(r'PAC-([A-Z]+)-P(\d+)-', pac_id)

        if not wrap_match or not pac_match:
            return {
                "success": False,
                "error_code": "GS_098",
                "message": "Cannot extract P## from WRAP or PAC ID"
            }

        wrap_agent = wrap_match.group(1)
        wrap_pnum = int(wrap_match.group(2))
        pac_agent = pac_match.group(1)
        pac_pnum = int(pac_match.group(2))

        # Enforce same agent
        if wrap_agent != pac_agent:
            return {
                "success": False,
                "error_code": "GS_098",
                "message": f"WRAP/PAC agent mismatch: WRAP={wrap_agent}, PAC={pac_agent}"
            }

        # Enforce same P## number
        if wrap_pnum != pac_pnum:
            return {
                "success": False,
                "error_code": "GS_098",
                "message": f"WRAP/PAC number mismatch: WRAP=P{wrap_pnum}, PAC=P{pac_pnum}"
            }

        return {
            "success": True,
            "error_code": None,
            "message": f"WRAP {wrap_id} successfully bound to PAC {pac_id}"
        }

    # ========================================================================
    # PAC SEQUENCE STATE REGISTRY
    # PAC-BENSON-P42-PAC_SEQUENCE_AND_WRAP_DEPENDENCY_ENFORCEMENT-01
    # ========================================================================

    def get_pac_sequence_state(self, agent_gid: str) -> PacSequenceState:
        """
        Get the PAC sequence state for an agent.

        PAC-BENSON-P42-PAC_SEQUENCE_AND_WRAP_DEPENDENCY_ENFORCEMENT-01

        Computes:
        - last_issued_pac: Most recent PAC issued
        - last_closed_wrap: Most recent WRAP accepted
        - wrap_pending: Whether last PAC needs WRAP

        Args:
            agent_gid: Agent GID

        Returns:
            PacSequenceState dataclass
        """
        import re

        agent_name = AGENT_REGISTRY.get(agent_gid, "UNKNOWN")

        # Scan ledger for this agent's PACs and WRAPs
        last_pac_id = None
        last_pac_num = None
        last_wrap_id = None
        last_wrap_num = None

        for entry in self.ledger_data["entries"]:
            if entry.get("agent_gid") != agent_gid:
                continue

            artifact_id = entry.get("artifact_id", "")
            entry_type = entry.get("entry_type", "")

            # Track PACs
            if entry_type in [EntryType.PAC_ISSUED.value, EntryType.PAC_EXECUTED.value]:
                match = re.search(r'PAC-[A-Z]+-P(\d+)-', artifact_id)
                if match:
                    pac_num = int(match.group(1))
                    if last_pac_num is None or pac_num > last_pac_num:
                        last_pac_num = pac_num
                        last_pac_id = artifact_id

            # Track WRAPs (only ACCEPTED count as closed)
            if entry_type == EntryType.WRAP_ACCEPTED.value:
                match = re.search(r'WRAP-[A-Z]+-P(\d+)-', artifact_id)
                if match:
                    wrap_num = int(match.group(1))
                    if last_wrap_num is None or wrap_num > last_wrap_num:
                        last_wrap_num = wrap_num
                        last_wrap_id = artifact_id

        # Determine if WRAP is pending
        wrap_pending = False
        if last_pac_num is not None:
            if last_wrap_num is None or last_wrap_num < last_pac_num:
                wrap_pending = True

        # Validate sequence
        sequence_valid = True
        if last_pac_num is not None and last_wrap_num is not None:
            # Allow 0 or 1 gap (current PAC may be awaiting WRAP)
            if last_pac_num - last_wrap_num > 1:
                sequence_valid = False

        return PacSequenceState(
            agent_gid=agent_gid,
            agent_name=agent_name,
            last_issued_pac=last_pac_id,
            last_issued_pac_number=last_pac_num,
            last_closed_wrap=last_wrap_id,
            last_closed_wrap_number=last_wrap_num,
            wrap_pending=wrap_pending,
            sequence_valid=sequence_valid
        )

    def validate_pac_issuance_allowed(self, pac_id: str, agent_gid: str) -> dict:
        """
        Validate if a new PAC can be issued per strict sequence rules.

        PAC-BENSON-P42-PAC_SEQUENCE_AND_WRAP_DEPENDENCY_ENFORCEMENT-01

        Rules:
        1. PAC numbers MUST be strictly sequential (P[n] → P[n+1])
        2. PAC issuance is BLOCKED if prior PAC WRAP not accepted
        3. No manual override except BENSON (GID-00)

        Args:
            pac_id: The PAC ID being issued
            agent_gid: The issuing agent's GID

        Returns:
            dict with 'allowed', 'error_code', 'message'
        """
        import re

        # Extract P## from PAC ID
        match = re.search(r'PAC-([A-Z]+)-P(\d+)-', pac_id)
        if not match:
            return {
                "allowed": False,
                "error_code": "GS_110",
                "message": f"Cannot extract PAC number from ID: {pac_id}"
            }

        pac_agent = match.group(1)
        pac_number = int(match.group(2))

        # Get current sequence state
        state = self.get_pac_sequence_state(agent_gid)

        # Rule 1: Sequential numbering
        if state.last_issued_pac_number is not None:
            expected_next = state.last_issued_pac_number + 1
            if pac_number != expected_next:
                return {
                    "allowed": False,
                    "error_code": "GS_110",
                    "message": (
                        f"PAC sequence violation — non-sequential PAC number. "
                        f"Expected P{expected_next}, got P{pac_number}. "
                        f"Last issued: {state.last_issued_pac}"
                    )
                }

        # Rule 2: Prior WRAP must be accepted
        if state.wrap_pending:
            # Check if BENSON (GID-00) override
            if agent_gid != "GID-00":
                return {
                    "allowed": False,
                    "error_code": "GS_111",
                    "message": (
                        f"PAC issuance blocked — prior WRAP not accepted. "
                        f"Last PAC: {state.last_issued_pac} (P{state.last_issued_pac_number}) "
                        f"requires WRAP before P{pac_number} can be issued."
                    )
                }

        return {
            "allowed": True,
            "error_code": None,
            "message": f"PAC issuance allowed: P{pac_number}"
        }

    def validate_wrap_binding(self, wrap_id: str, pac_reference: str) -> dict:
        """
        Validate WRAP↔PAC binding per strict rules.

        PAC-BENSON-P42-PAC_SEQUENCE_AND_WRAP_DEPENDENCY_ENFORCEMENT-01

        Rules:
        1. WRAP must reference exact PAC ID
        2. One PAC ↔ One WRAP (1:1)
        3. Numbers must match (WRAP-P## ↔ PAC-P##)

        Args:
            wrap_id: The WRAP artifact ID
            pac_reference: The PAC ID referenced by the WRAP

        Returns:
            dict with 'valid', 'error_code', 'message'
        """
        import re

        # Extract P## from both
        wrap_match = re.search(r'WRAP-([A-Z]+)-P(\d+)-', wrap_id)
        pac_match = re.search(r'PAC-([A-Z]+)-P(\d+)-', pac_reference)

        if not wrap_match:
            return {
                "valid": False,
                "error_code": "GS_112",
                "message": f"Cannot extract WRAP number from ID: {wrap_id}"
            }

        if not pac_match:
            return {
                "valid": False,
                "error_code": "GS_112",
                "message": f"Cannot extract PAC number from reference: {pac_reference}"
            }

        wrap_agent = wrap_match.group(1)
        wrap_num = int(wrap_match.group(2))
        pac_agent = pac_match.group(1)
        pac_num = int(pac_match.group(2))

        # Validate agent match
        if wrap_agent != pac_agent:
            return {
                "valid": False,
                "error_code": "GS_112",
                "message": (
                    f"WRAP/PAC mismatch — invalid binding. "
                    f"Agent mismatch: WRAP={wrap_agent}, PAC={pac_agent}"
                )
            }

        # Validate number match
        if wrap_num != pac_num:
            return {
                "valid": False,
                "error_code": "GS_112",
                "message": (
                    f"WRAP/PAC mismatch — invalid binding. "
                    f"Number mismatch: WRAP=P{wrap_num}, PAC=P{pac_num}"
                )
            }

        return {
            "valid": True,
            "error_code": None,
            "message": f"WRAP {wrap_id} validly binds to PAC {pac_reference}"
        }

    # ========================================================================
    # PAC↔WRAP SEQUENTIAL DEPENDENCY VALIDATION
    # PAC-ALEX-P43-PAC-WRAP-SEQUENTIAL-GATE-IMPLEMENTATION-01
    # ========================================================================

    def validate_pac_wrap_sequential(self, pac_id: str, agent_gid: str) -> dict:
        """
        Validate PAC↔WRAP sequential dependency.

        PAC-ALEX-P43-PAC-WRAP-SEQUENTIAL-GATE-IMPLEMENTATION-01

        Rule: PAC P(N) requires WRAP P(N-1) to be ACCEPTED in the ledger.

        Exceptions:
        1. First PAC for an agent (N=1 or no prior PACs) is allowed
        2. BENSON (GID-00) can bypass this check

        Args:
            pac_id: The PAC ID being validated (e.g., "PAC-ALEX-P43-...")
            agent_gid: The GID of the agent issuing the PAC

        Returns:
            dict with keys:
            - 'valid': bool — True if sequential dependency satisfied
            - 'error_code': str or None — GS_111 on violation
            - 'message': str — Human-readable explanation
            - 'required_wrap_number': int or None — P## of required WRAP
        """
        import re

        # Extract P## from PAC ID
        match = re.search(r'PAC-([A-Z]+)-P(\d+)-', pac_id)
        if not match:
            return {
                "valid": False,
                "error_code": "GS_111",
                "message": f"Cannot extract PAC number from ID: {pac_id}",
                "required_wrap_number": None
            }

        agent_name = match.group(1)
        pac_number = int(match.group(2))

        # Exception 1: First PAC for agent (no prior WRAP required)
        # If pac_number == 1, this is the first PAC
        if pac_number == 1:
            return {
                "valid": True,
                "error_code": None,
                "message": f"First PAC (P1) for agent {agent_name} — no prior WRAP required",
                "required_wrap_number": None
            }

        # Exception 2: BENSON (GID-00) override
        if agent_gid == "GID-00":
            return {
                "valid": True,
                "error_code": None,
                "message": f"BENSON (GID-00) override — sequential check bypassed",
                "required_wrap_number": None
            }

        # Rule: PAC P(N) requires WRAP P(N-1) to be ACCEPTED
        required_wrap_number = pac_number - 1

        # Query ledger for WRAP_ACCEPTED entries for this agent with P(N-1)
        wrap_accepted = False
        for entry in self.ledger_data["entries"]:
            if entry.get("entry_type") != EntryType.WRAP_ACCEPTED.value:
                continue
            if entry.get("agent_gid") != agent_gid:
                continue

            artifact_id = entry.get("artifact_id", "")
            wrap_match = re.search(r'WRAP-[A-Z]+-P(\d+)-', artifact_id)
            if wrap_match:
                wrap_num = int(wrap_match.group(1))
                if wrap_num == required_wrap_number:
                    wrap_accepted = True
                    break

        if not wrap_accepted:
            return {
                "valid": False,
                "error_code": "GS_111",
                "message": (
                    f"PAC issuance blocked — prior WRAP not accepted. "
                    f"PAC P{pac_number} requires WRAP P{required_wrap_number} to be ACCEPTED. "
                    f"Agent: {agent_name} ({agent_gid})"
                ),
                "required_wrap_number": required_wrap_number
            }

        return {
            "valid": True,
            "error_code": None,
            "message": f"Sequential dependency satisfied — WRAP P{required_wrap_number} is ACCEPTED",
            "required_wrap_number": required_wrap_number
        }

    def get_all_pac_sequence_states(self) -> dict:
        """
        Get PAC sequence state for all agents.

        Returns:
            dict mapping agent_gid → PacSequenceState
        """
        states = {}
        for gid in AGENT_REGISTRY:
            state = self.get_pac_sequence_state(gid)
            # Only include agents with activity
            if state.last_issued_pac_number is not None:
                states[gid] = {
                    "agent_name": state.agent_name,
                    "last_issued_pac": state.last_issued_pac,
                    "last_issued_pac_number": state.last_issued_pac_number,
                    "last_closed_wrap": state.last_closed_wrap,
                    "last_closed_wrap_number": state.last_closed_wrap_number,
                    "wrap_pending": state.wrap_pending,
                    "sequence_valid": state.sequence_valid
                }
        return states

    # ========================================================================
    # PAC STATE MACHINE & WRAP BINDING
    # PAC-BENSON-P44-GOVERNANCE-LEDGER-WRAP-BINDING-AND-STATE-LOCK-01
    # ========================================================================

    def get_pac_state(self, pac_id: str) -> Optional[str]:
        """
        Get the current state of a PAC from the ledger.

        Returns:
            PacState value (ISSUED, EXECUTED, CLOSED) or None if not found
        """
        # Find latest entry for this PAC
        latest_entry = None
        latest_seq = -1

        for entry in self.ledger_data["entries"]:
            if entry.get("artifact_id") == pac_id:
                seq = entry.get("sequence", 0)
                if seq > latest_seq:
                    latest_seq = seq
                    latest_entry = entry

        if not latest_entry:
            return None

        # Determine state from entry type
        entry_type = latest_entry.get("entry_type", "")
        pac_state = latest_entry.get("pac_state")

        if pac_state:
            return pac_state

        # Infer from entry type
        if entry_type == EntryType.PAC_ISSUED.value:
            return PacState.ISSUED.value
        elif entry_type == EntryType.PAC_EXECUTED.value:
            return PacState.EXECUTED.value
        elif entry_type == EntryType.POSITIVE_CLOSURE_ACKNOWLEDGED.value:
            return PacState.CLOSED.value

        return PacState.ISSUED.value

    def validate_pac_state_transition(self, pac_id: str, new_state: str) -> dict:
        """
        Validate a PAC state transition.

        PAC-BENSON-P44: State transitions are ONE-WAY:
        ISSUED → EXECUTED → CLOSED

        Args:
            pac_id: The PAC artifact ID
            new_state: The proposed new state

        Returns:
            dict with 'valid', 'error_code', 'message', 'current_state'
        """
        current_state = self.get_pac_state(pac_id)

        if current_state is None:
            # New PAC — only ISSUED is valid
            if new_state != PacState.ISSUED.value:
                return {
                    "valid": False,
                    "error_code": "GS_115",
                    "message": f"New PAC must start in ISSUED state, not {new_state}",
                    "current_state": None
                }
            return {
                "valid": True,
                "error_code": None,
                "message": "New PAC can be created in ISSUED state",
                "current_state": None
            }

        # Get valid transitions
        try:
            current_state_enum = PacState(current_state)
        except ValueError:
            return {
                "valid": False,
                "error_code": "GS_115",
                "message": f"Invalid current state: {current_state}",
                "current_state": current_state
            }

        try:
            new_state_enum = PacState(new_state)
        except ValueError:
            return {
                "valid": False,
                "error_code": "GS_115",
                "message": f"Invalid target state: {new_state}",
                "current_state": current_state
            }

        valid_transitions = VALID_PAC_TRANSITIONS.get(current_state_enum, [])

        if new_state_enum not in valid_transitions:
            return {
                "valid": False,
                "error_code": "GS_115",
                "message": (
                    f"PAC_STATE_REGRESSION — Illegal PAC state transition detected. "
                    f"Cannot transition from {current_state} to {new_state}. "
                    f"Valid transitions: {[s.value for s in valid_transitions] or 'NONE (terminal)'}"
                ),
                "current_state": current_state
            }

        return {
            "valid": True,
            "error_code": None,
            "message": f"State transition {current_state} → {new_state} is valid",
            "current_state": current_state
        }

    def get_wrap_binding_for_pac(self, pac_id: str) -> Optional[dict]:
        """
        Get the WRAP binding for a PAC if one exists.

        Returns:
            dict with wrap_id, wrap_hash, pac_hash, bound_at or None
        """
        for entry in self.ledger_data["entries"]:
            if entry.get("parent_artifact") == pac_id:
                entry_type = entry.get("entry_type", "")
                if entry_type == EntryType.WRAP_ACCEPTED.value:
                    return {
                        "wrap_id": entry.get("artifact_id"),
                        "wrap_hash": entry.get("artifact_sha256"),
                        "pac_hash": entry.get("wrap_binding", {}).get("pac_hash") if entry.get("wrap_binding") else None,
                        "bound_at": entry.get("timestamp")
                    }
        return None

    def is_wrap_already_bound(self, wrap_id: str) -> bool:
        """
        Check if a WRAP is already bound to a PAC.

        Prevents duplicate bindings (one WRAP ↔ one PAC).
        """
        for entry in self.ledger_data["entries"]:
            if entry.get("artifact_id") == wrap_id:
                entry_type = entry.get("entry_type", "")
                if entry_type == EntryType.WRAP_ACCEPTED.value:
                    return True
        return False

    def validate_pac_closure(self, pac_id: str) -> dict:
        """
        Validate if a PAC can be closed.

        PAC-BENSON-P44: PAC cannot reach CLOSED without valid WRAP binding.

        Args:
            pac_id: The PAC artifact ID

        Returns:
            dict with 'can_close', 'error_code', 'message', 'wrap_binding'
        """
        # Check current state
        current_state = self.get_pac_state(pac_id)

        if current_state != PacState.EXECUTED.value:
            return {
                "can_close": False,
                "error_code": "GS_115",
                "message": (
                    f"PAC cannot close from state {current_state}. "
                    f"Must be in EXECUTED state first."
                ),
                "wrap_binding": None
            }

        # Check for WRAP binding
        wrap_binding = self.get_wrap_binding_for_pac(pac_id)

        if not wrap_binding:
            return {
                "can_close": False,
                "error_code": "GS_113",
                "message": "PAC_NOT_CLOSED_NO_WRAP — PAC cannot close without a valid WRAP.",
                "wrap_binding": None
            }

        return {
            "can_close": True,
            "error_code": None,
            "message": f"PAC can close. WRAP binding: {wrap_binding['wrap_id']}",
            "wrap_binding": wrap_binding
        }

    def validate_wrap_hash_binding(
        self,
        wrap_id: str,
        wrap_hash: str,
        pac_id: str,
        pac_hash: str
    ) -> dict:
        """
        Validate cryptographic binding between WRAP and PAC.

        PAC-BENSON-P44: WRAP must reference PAC_ID, PAC_HASH, and SEQUENCE.

        Args:
            wrap_id: The WRAP artifact ID
            wrap_hash: SHA256 of WRAP content
            pac_id: The PAC artifact ID
            pac_hash: SHA256 of PAC content (from WRAP's pac_hash field)

        Returns:
            dict with 'valid', 'error_code', 'message'
        """
        import re

        # Validate IDs match
        wrap_match = re.search(r'WRAP-([A-Z]+)-P(\d+)-', wrap_id)
        pac_match = re.search(r'PAC-([A-Z]+)-P(\d+)-', pac_id)

        if not wrap_match or not pac_match:
            return {
                "valid": False,
                "error_code": "GS_114",
                "message": "Cannot extract agent/sequence from WRAP or PAC ID"
            }

        wrap_agent, wrap_num = wrap_match.group(1), int(wrap_match.group(2))
        pac_agent, pac_num = pac_match.group(1), int(pac_match.group(2))

        if wrap_agent != pac_agent or wrap_num != pac_num:
            return {
                "valid": False,
                "error_code": "GS_114",
                "message": (
                    f"WRAP_PAC_HASH_MISMATCH — WRAP does not cryptographically bind to PAC. "
                    f"Agent/sequence mismatch: WRAP={wrap_agent}-P{wrap_num}, PAC={pac_agent}-P{pac_num}"
                )
            }

        # Verify PAC exists in ledger with matching hash
        pac_entries = self.get_entries_by_artifact(pac_id)
        if not pac_entries:
            return {
                "valid": False,
                "error_code": "GS_114",
                "message": f"PAC {pac_id} not found in ledger — cannot bind WRAP"
            }

        # Check if WRAP references correct PAC hash (if provided)
        if pac_hash:
            ledger_pac_hash = None
            for entry in pac_entries:
                if entry.get("artifact_sha256"):
                    ledger_pac_hash = entry.get("artifact_sha256")
                    break

            if ledger_pac_hash and pac_hash != ledger_pac_hash:
                return {
                    "valid": False,
                    "error_code": "GS_114",
                    "message": (
                        f"WRAP_PAC_HASH_MISMATCH — WRAP does not cryptographically bind to PAC. "
                        f"Hash mismatch: WRAP claims {pac_hash[:16]}..., ledger has {ledger_pac_hash[:16]}..."
                    )
                }

        # Check for duplicate binding
        if self.is_wrap_already_bound(wrap_id):
            return {
                "valid": False,
                "error_code": "GS_114",
                "message": f"WRAP {wrap_id} is already bound — duplicate binding rejected"
            }

        return {
            "valid": True,
            "error_code": None,
            "message": f"WRAP {wrap_id} cryptographically binds to PAC {pac_id}"
        }

    def record_wrap_binding(
        self,
        wrap_id: str,
        wrap_hash: str,
        pac_id: str,
        pac_hash: str,
        agent_gid: str,
        agent_name: str
    ) -> Optional[LedgerEntry]:
        """
        Record a WRAP binding to PAC in the ledger.

        This atomically:
        1. Validates the binding
        2. Records WRAP_ACCEPTED entry
        3. Updates PAC state to CLOSED

        Returns:
            LedgerEntry if successful, None if validation fails
        """
        # Validate binding first
        binding_result = self.validate_wrap_hash_binding(wrap_id, wrap_hash, pac_id, pac_hash)
        if not binding_result["valid"]:
            return None

        # Create binding entry
        entry = self.record_wrap(
            artifact_id=wrap_id,
            agent_gid=agent_gid,
            agent_name=agent_name,
            parent_pac=pac_id,
            status="accepted",
            ratified_by="BENSON (GID-00)"
        )

        # Update entry with binding info
        if entry and entry.sequence:
            # Find and update the entry in ledger_data
            for ledger_entry in self.ledger_data["entries"]:
                if ledger_entry.get("sequence") == entry.sequence:
                    ledger_entry["wrap_binding"] = {
                        "wrap_id": wrap_id,
                        "wrap_hash": wrap_hash,
                        "pac_hash": pac_hash,
                        "bound_at": entry.timestamp
                    }
                    ledger_entry["pac_state"] = PacState.CLOSED.value
                    break

            self._save_ledger()

        return entry

    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================

    def get_all_entries(self) -> list:
        """Get all ledger entries."""
        return self.ledger_data["entries"]

    def get_entries_by_agent(self, agent_gid: str) -> list:
        """Get entries for a specific agent."""
        return [
            e for e in self.ledger_data["entries"]
            if e.get("agent_gid") == agent_gid
        ]

    def get_entries_by_type(self, entry_type: str) -> list:
        """Get entries by type."""
        return [
            e for e in self.ledger_data["entries"]
            if e.get("entry_type") == entry_type
        ]

    def get_entries_by_artifact(self, artifact_id: str) -> list:
        """Get all entries related to an artifact."""
        return [
            e for e in self.ledger_data["entries"]
            if e.get("artifact_id") == artifact_id or e.get("parent_artifact") == artifact_id
        ]

    def get_agent_statistics(self) -> dict:
        """Get statistics per agent."""
        return self.ledger_data["agent_sequences"]

    def get_sequence_state(self) -> dict:
        """Get current sequence state."""
        return self.ledger_data["sequence_state"]

    # ========================================================================
    # VALIDATION OPERATIONS
    # ========================================================================

    def validate_sequence_continuity(self) -> dict:
        """
        Validate that sequence numbers are continuous with no gaps.

        Returns validation result.
        """
        entries = self.ledger_data["entries"]
        issues = []

        for i, entry in enumerate(entries):
            expected_seq = i + 1
            actual_seq = entry.get("sequence", 0)

            if actual_seq != expected_seq:
                issues.append({
                    "type": "SEQUENCE_GAP",
                    "expected": expected_seq,
                    "actual": actual_seq,
                    "entry_type": entry.get("entry_type"),
                    "artifact_id": entry.get("artifact_id")
                })

        return {
            "valid": len(issues) == 0,
            "total_entries": len(entries),
            "issues": issues
        }

    def validate_hash_chain(self) -> dict:
        """
        Validate the integrity of the hash chain.

        Detects:
        - Modified entries (hash mismatch)
        - Broken chain (prev_hash mismatch)
        - Missing hashes (legacy entries before hash-chain)

        Returns validation result with detailed issues.
        """
        entries = self.ledger_data["entries"]
        issues = []
        prev_hash = None
        entries_with_hashes = 0

        for i, entry in enumerate(entries):
            entry_hash = entry.get("entry_hash")
            entry_prev_hash = entry.get("prev_hash")

            # Skip entries without hashes (legacy entries before v1.1.0)
            if entry_hash is None:
                continue

            entries_with_hashes += 1

            # Recompute hash to verify integrity
            computed_hash = self._compute_entry_hash(entry)
            if computed_hash != entry_hash:
                issues.append({
                    "type": "HASH_MISMATCH",
                    "sequence": entry.get("sequence"),
                    "expected_hash": computed_hash,
                    "actual_hash": entry_hash,
                    "entry_type": entry.get("entry_type"),
                    "artifact_id": entry.get("artifact_id"),
                    "severity": "CRITICAL"
                })

            # Verify chain linkage
            if prev_hash is not None and entry_prev_hash != prev_hash:
                issues.append({
                    "type": "CHAIN_BROKEN",
                    "sequence": entry.get("sequence"),
                    "expected_prev_hash": prev_hash,
                    "actual_prev_hash": entry_prev_hash,
                    "entry_type": entry.get("entry_type"),
                    "artifact_id": entry.get("artifact_id"),
                    "severity": "CRITICAL"
                })

            prev_hash = entry_hash

        return {
            "valid": len(issues) == 0,
            "total_entries": len(entries),
            "entries_with_hashes": entries_with_hashes,
            "chain_intact": len([i for i in issues if i["type"] == "CHAIN_BROKEN"]) == 0,
            "no_tampering_detected": len([i for i in issues if i["type"] == "HASH_MISMATCH"]) == 0,
            "issues": issues
        }

    def validate_ledger_integrity(self) -> dict:
        """
        Comprehensive ledger integrity validation.

        Combines sequence continuity and hash chain validation.
        Returns overall integrity status.
        """
        sequence_result = self.validate_sequence_continuity()
        hash_result = self.validate_hash_chain()

        overall_valid = sequence_result["valid"] and hash_result["valid"]

        return {
            "valid": overall_valid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence_validation": sequence_result,
            "hash_chain_validation": hash_result,
            "summary": {
                "total_entries": sequence_result["total_entries"],
                "sequence_issues": len(sequence_result.get("issues", [])),
                "hash_issues": len(hash_result.get("issues", [])),
                "verdict": "INTEGRITY_VERIFIED" if overall_valid else "TAMPERING_DETECTED"
            }
        }

    def generate_audit_report(self) -> dict:
        """Generate comprehensive audit report."""
        entries = self.ledger_data["entries"]

        # Count by type
        type_counts = {}
        for entry in entries:
            t = entry.get("entry_type", "UNKNOWN")
            type_counts[t] = type_counts.get(t, 0) + 1

        # Count by agent
        agent_counts = {}
        for entry in entries:
            gid = entry.get("agent_gid", "UNKNOWN")
            agent_counts[gid] = agent_counts.get(gid, 0) + 1

        # Count by artifact type
        artifact_counts = {}
        for entry in entries:
            at = entry.get("artifact_type", "UNKNOWN")
            artifact_counts[at] = artifact_counts.get(at, 0) + 1

        # Validation results
        validation_pass = len([e for e in entries if e.get("validation_result") == "PASS"])
        validation_fail = len([e for e in entries if e.get("validation_result") == "FAIL"])

        # Corrections
        corrections_opened = len([e for e in entries if e.get("entry_type") == "CORRECTION_OPENED"])
        corrections_closed = len([e for e in entries if e.get("entry_type") == "CORRECTION_CLOSED"])

        # Positive closures
        positive_closures = len([e for e in entries if e.get("entry_type") == "POSITIVE_CLOSURE_ACKNOWLEDGED"])

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_entries": len(entries),
            "sequence_continuity": self.validate_sequence_continuity(),
            "entry_type_distribution": type_counts,
            "agent_distribution": agent_counts,
            "artifact_type_distribution": artifact_counts,
            "validation_summary": {
                "pass": validation_pass,
                "fail": validation_fail,
                "pass_rate": f"{(validation_pass / max(validation_pass + validation_fail, 1)) * 100:.1f}%"
            },
            "correction_summary": {
                "opened": corrections_opened,
                "closed": corrections_closed,
                "open": corrections_opened - corrections_closed
            },
            "positive_closures": positive_closures
        }


# ============================================================================
# ARTIFACT ID PARSER
# ============================================================================

def parse_artifact_id(artifact_id: str) -> dict:
    """
    Parse artifact ID into components.

    Format: PAC-{AGENT}-{G{GENERATION}}-{PHASE}-{SEQUENCE}
    Example: PAC-ALEX-G1-PHASE-2-GOVERNANCE-LEDGER-01
    """
    result = {
        "artifact_type": None,
        "agent_name": None,
        "generation": None,
        "phase": None,
        "description": None,
        "sequence": None,
        "valid": False
    }

    # Try PAC format
    pac_match = re.match(
        r"(PAC|WRAP|CORRECTION)-([A-Z]+)-G(\d+)(?:-PHASE-(\d+))?-(.+?)(?:-(\d+))?$",
        artifact_id
    )

    if pac_match:
        result["artifact_type"] = pac_match.group(1)
        result["agent_name"] = pac_match.group(2)
        result["generation"] = int(pac_match.group(3))
        result["phase"] = int(pac_match.group(4)) if pac_match.group(4) else None
        result["description"] = pac_match.group(5)
        result["sequence"] = int(pac_match.group(6)) if pac_match.group(6) else None
        result["valid"] = True

    return result


def extract_gid_from_agent(agent_name: str) -> Optional[str]:
    """Look up GID from agent name."""
    for gid, name in AGENT_REGISTRY.items():
        if name.upper() == agent_name.upper():
            return gid
    return None


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """CLI for governance ledger."""
    parser = argparse.ArgumentParser(
        description="Governance Ledger Writer — Append-only governance artifact registry"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Record PAC
    pac_parser = subparsers.add_parser("record-pac", help="Record a PAC")
    pac_parser.add_argument("--artifact-id", required=True, help="PAC ID")
    pac_parser.add_argument("--agent-gid", required=True, help="Agent GID")
    pac_parser.add_argument("--agent-name", required=True, help="Agent name")
    pac_parser.add_argument("--status", choices=["issued", "executed"], default="issued")
    pac_parser.add_argument("--file-path", help="File path")
    pac_parser.add_argument("--notes", help="Notes")

    # Record WRAP
    wrap_parser = subparsers.add_parser("record-wrap", help="Record a WRAP")
    wrap_parser.add_argument("--artifact-id", required=True, help="WRAP ID")
    wrap_parser.add_argument("--agent-gid", required=True, help="Agent GID")
    wrap_parser.add_argument("--agent-name", required=True, help="Agent name")
    wrap_parser.add_argument("--parent-pac", required=True, help="Parent PAC ID")
    wrap_parser.add_argument("--status", choices=["submitted", "accepted", "rejected"], default="submitted")
    wrap_parser.add_argument("--ratified-by", help="Ratified by (for accepted)")
    wrap_parser.add_argument("--file-path", help="File path")
    wrap_parser.add_argument("--notes", help="Notes")

    # Record validation
    val_parser = subparsers.add_parser("record-validation", help="Record validation result")
    val_parser.add_argument("--artifact-id", required=True, help="Artifact ID")
    val_parser.add_argument("--agent-gid", required=True, help="Agent GID")
    val_parser.add_argument("--agent-name", required=True, help="Agent name")
    val_parser.add_argument("--artifact-type", required=True, choices=["PAC", "WRAP", "CORRECTION"])
    val_parser.add_argument("--result", required=True, choices=["pass", "fail"])
    val_parser.add_argument("--error-codes", nargs="*", help="Error codes (for fail)")
    val_parser.add_argument("--file-path", help="File path")
    val_parser.add_argument("--notes", help="Notes")

    # Record positive closure
    pc_parser = subparsers.add_parser("record-positive-closure", help="Record positive closure")
    pc_parser.add_argument("--artifact-id", required=True, help="Artifact ID")
    pc_parser.add_argument("--agent-gid", required=True, help="Agent GID")
    pc_parser.add_argument("--agent-name", required=True, help="Agent name")
    pc_parser.add_argument("--parent-artifact", required=True, help="Parent artifact ID")
    pc_parser.add_argument("--closure-authority", required=True, help="Closure authority")
    pc_parser.add_argument("--file-path", help="File path")
    pc_parser.add_argument("--notes", help="Notes")

    # Query commands
    query_parser = subparsers.add_parser("query", help="Query ledger")
    query_parser.add_argument("--by-agent", help="Filter by agent GID")
    query_parser.add_argument("--by-type", help="Filter by entry type")
    query_parser.add_argument("--by-artifact", help="Filter by artifact ID")
    query_parser.add_argument("--format", choices=["json", "text"], default="text")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate audit report")
    report_parser.add_argument("--format", choices=["json", "text"], default="text")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate ledger integrity")
    validate_parser.add_argument("--format", choices=["json", "text"], default="text")

    # Record BSRG command (PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01)
    bsrg_parser = subparsers.add_parser("record-bsrg", help="Record BSRG review result")
    bsrg_parser.add_argument("--artifact-id", required=True, help="PAC artifact ID")
    bsrg_parser.add_argument("--artifact-sha256", required=True, help="SHA256 hash of artifact content")
    bsrg_parser.add_argument("--status", required=True, choices=["PASS", "FAIL"], help="Review status")
    bsrg_parser.add_argument("--failed-items", nargs="*", help="Items that failed (for FAIL status)")
    bsrg_parser.add_argument("--file-path", help="Path to artifact file")
    bsrg_parser.add_argument("--notes", help="Optional notes")

    args = parser.parse_args()

    ledger = GovernanceLedger()

    if args.command == "record-pac":
        if args.status == "issued":
            entry = ledger.record_pac_issued(
                artifact_id=args.artifact_id,
                agent_gid=args.agent_gid,
                agent_name=args.agent_name,
                file_path=args.file_path,
                notes=args.notes
            )
        else:
            entry = ledger.record_pac_executed(
                artifact_id=args.artifact_id,
                agent_gid=args.agent_gid,
                agent_name=args.agent_name,
                file_path=args.file_path,
                notes=args.notes
            )
        print(f"✅ Recorded PAC: {args.artifact_id} (sequence: {entry.sequence})")

    elif args.command == "record-wrap":
        if args.status == "submitted":
            entry = ledger.record_wrap_submitted(
                artifact_id=args.artifact_id,
                agent_gid=args.agent_gid,
                agent_name=args.agent_name,
                parent_pac_id=args.parent_pac,
                file_path=args.file_path,
                notes=args.notes
            )
        elif args.status == "accepted":
            entry = ledger.record_wrap_accepted(
                artifact_id=args.artifact_id,
                agent_gid=args.agent_gid,
                agent_name=args.agent_name,
                ratified_by=args.ratified_by or "BENSON (GID-00)",
                file_path=args.file_path,
                notes=args.notes
            )
        print(f"✅ Recorded WRAP: {args.artifact_id} (sequence: {entry.sequence})")

    elif args.command == "record-validation":
        if args.result == "pass":
            entry = ledger.record_validation_pass(
                artifact_id=args.artifact_id,
                agent_gid=args.agent_gid,
                agent_name=args.agent_name,
                artifact_type=args.artifact_type,
                file_path=args.file_path,
                notes=args.notes
            )
        else:
            entry = ledger.record_validation_fail(
                artifact_id=args.artifact_id,
                agent_gid=args.agent_gid,
                agent_name=args.agent_name,
                artifact_type=args.artifact_type,
                error_codes=args.error_codes or [],
                file_path=args.file_path,
                notes=args.notes
            )
        print(f"✅ Recorded validation {args.result.upper()}: {args.artifact_id} (sequence: {entry.sequence})")

    elif args.command == "record-positive-closure":
        entry = ledger.record_positive_closure(
            artifact_id=args.artifact_id,
            agent_gid=args.agent_gid,
            agent_name=args.agent_name,
            parent_artifact=args.parent_artifact,
            closure_authority=args.closure_authority,
            file_path=args.file_path,
            notes=args.notes
        )
        print(f"✅ Recorded positive closure: {args.artifact_id} (sequence: {entry.sequence})")

    elif args.command == "query":
        if args.by_agent:
            entries = ledger.get_entries_by_agent(args.by_agent)
        elif args.by_type:
            entries = ledger.get_entries_by_type(args.by_type)
        elif args.by_artifact:
            entries = ledger.get_entries_by_artifact(args.by_artifact)
        else:
            entries = ledger.get_all_entries()

        if args.format == "json":
            print(json.dumps(entries, indent=2))
        else:
            print(f"\n=== LEDGER QUERY RESULTS ({len(entries)} entries) ===\n")
            for entry in entries:
                print(f"[{entry['sequence']:04d}] {entry['timestamp'][:19]} | {entry['entry_type']:30} | {entry['agent_gid']:7} | {entry['artifact_id']}")

    elif args.command == "report":
        report = ledger.generate_audit_report()

        if args.format == "json":
            print(json.dumps(report, indent=2))
        else:
            print("\n" + "=" * 70)
            print("GOVERNANCE LEDGER AUDIT REPORT")
            print("=" * 70)
            print(f"\nGenerated: {report['generated_at']}")
            print(f"Total Entries: {report['total_entries']}")
            print(f"\nSequence Continuity: {'✅ VALID' if report['sequence_continuity']['valid'] else '❌ INVALID'}")

            print("\n--- Entry Type Distribution ---")
            for t, count in report['entry_type_distribution'].items():
                print(f"  {t}: {count}")

            print("\n--- Agent Distribution ---")
            for gid, count in report['agent_distribution'].items():
                print(f"  {gid}: {count}")

            print("\n--- Validation Summary ---")
            vs = report['validation_summary']
            print(f"  Pass: {vs['pass']}")
            print(f"  Fail: {vs['fail']}")
            print(f"  Pass Rate: {vs['pass_rate']}")

            print("\n--- Correction Summary ---")
            cs = report['correction_summary']
            print(f"  Opened: {cs['opened']}")
            print(f"  Closed: {cs['closed']}")
            print(f"  Open: {cs['open']}")

            print(f"\n--- Positive Closures: {report['positive_closures']} ---")
            print("=" * 70)

    elif args.command == "validate":
        result = ledger.validate_ledger_integrity()

        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print("\n" + "=" * 70)
            print("GOVERNANCE LEDGER INTEGRITY VALIDATION")
            print("=" * 70)
            print(f"\nTimestamp: {result['timestamp']}")
            print(f"\n--- Overall Status ---")
            print(f"  Verdict: {result['summary']['verdict']}")
            print(f"  Valid: {'✅ YES' if result['valid'] else '❌ NO'}")

            print(f"\n--- Sequence Validation ---")
            seq = result['sequence_validation']
            print(f"  Total Entries: {seq['total_entries']}")
            print(f"  Sequence Valid: {'✅' if seq['valid'] else '❌'}")
            if seq.get('issues'):
                for issue in seq['issues'][:5]:
                    print(f"    ⚠ {issue['type']}: seq {issue.get('expected')} expected, got {issue.get('actual')}")

            print(f"\n--- Hash Chain Validation ---")
            hc = result['hash_chain_validation']
            print(f"  Entries with Hashes: {hc['entries_with_hashes']}")
            print(f"  Chain Intact: {'✅' if hc['chain_intact'] else '❌'}")
            print(f"  No Tampering: {'✅' if hc['no_tampering_detected'] else '❌'}")
            if hc.get('issues'):
                for issue in hc['issues'][:5]:
                    print(f"    ⚠ [{issue['severity']}] {issue['type']}: seq {issue.get('sequence')} - {issue.get('artifact_id', 'N/A')}")

            print("=" * 70)

        sys.exit(0 if result["valid"] else 1)

    elif args.command == "record-bsrg":
        entry = ledger.record_bsrg_review(
            artifact_id=args.artifact_id,
            artifact_sha256=args.artifact_sha256,
            reviewer="BENSON",
            reviewer_gid="GID-00",
            bsrg_gate_id="BSRG-01",
            status=args.status,
            failed_items=args.failed_items or [],
            checklist_results={},
            file_path=args.file_path,
            notes=args.notes
        )
        print(f"✅ Recorded BSRG review: {args.artifact_id} - {args.status} (sequence: {entry.sequence})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
