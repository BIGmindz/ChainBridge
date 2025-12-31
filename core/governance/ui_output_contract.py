"""
UI Output Contract

Enforces bounded, checkpoint-only UI emissions.
Per PAC-JEFFREY-DRAFT-GOVERNANCE-UI-OUTPUT-CONTRACT-025.

Agent: GID-01 (Cody) — Senior Backend Engineer

Invariants:
- INV-UI-001: Bounded output (≤120 chars)
- INV-UI-002: Checkpoint-only emissions
- INV-UI-003: Hash-only references
- INV-UI-004: No agent narration
- INV-UI-005: Deterministic ordering
- INV-UI-006: Fail-closed on violation
"""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

UI_OUTPUT_CONFIG = {
    "max_emission_length": 120,
    "max_hash_display_length": 12,
    "max_agent_list_display": 8,
    "fail_closed": True,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class UIEmissionType(Enum):
    """
    Allowed UI emission types (STRICT ENUM).
    
    Per UI_OUTPUT_CONTRACT_v1.md — only these types may be emitted.
    """
    PAC_RECEIVED = "PAC_RECEIVED"
    AGENTS_DISPATCHED = "AGENTS_DISPATCHED"
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    CHECKPOINT_REACHED = "CHECKPOINT_REACHED"
    WRAP_HASH_RECEIVED = "WRAP_HASH_RECEIVED"
    ALL_WRAPS_RECEIVED = "ALL_WRAPS_RECEIVED"
    BER_ISSUED = "BER_ISSUED"
    PDO_EMITTED = "PDO_EMITTED"
    ERROR_SIGNAL = "ERROR_SIGNAL"
    WARNING_SIGNAL = "WARNING_SIGNAL"


class ForbiddenContentType(Enum):
    """Types of content forbidden from UI emission."""
    TASK_LOG = "TASK_LOG"
    TODO_UPDATE = "TODO_UPDATE"
    FILE_LISTING = "FILE_LISTING"
    DIFF_OUTPUT = "DIFF_OUTPUT"
    FULL_PAYLOAD = "FULL_PAYLOAD"
    AGENT_NARRATION = "AGENT_NARRATION"
    PROGRESS_PERCENTAGE = "PROGRESS_PERCENTAGE"
    INTERMEDIATE_RESULT = "INTERMEDIATE_RESULT"
    STACK_TRACE = "STACK_TRACE"
    DEBUG_LOG = "DEBUG_LOG"


# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOLS
# ═══════════════════════════════════════════════════════════════════════════════

EMISSION_SYMBOLS: Dict[UIEmissionType, str] = {
    UIEmissionType.PAC_RECEIVED: "🟦",
    UIEmissionType.AGENTS_DISPATCHED: "🚀",
    UIEmissionType.AGENT_STARTED: "⏳",
    UIEmissionType.AGENT_COMPLETED: "✓",
    UIEmissionType.CHECKPOINT_REACHED: "⏳",
    UIEmissionType.WRAP_HASH_RECEIVED: "📦",
    UIEmissionType.ALL_WRAPS_RECEIVED: "📦📦",
    UIEmissionType.BER_ISSUED: "🟩",
    UIEmissionType.PDO_EMITTED: "🧿",
    UIEmissionType.ERROR_SIGNAL: "🔴",
    UIEmissionType.WARNING_SIGNAL: "🟡",
}


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class UIContractViolation(Exception):
    """
    Raised when UI Output Contract is violated.
    
    Per INV-UI-006: Fail-closed on violation.
    """
    pass


class UnboundedOutputError(UIContractViolation):
    """Raised when output exceeds length bounds."""
    pass


class ForbiddenEmissionError(UIContractViolation):
    """Raised when forbidden content is detected."""
    pass


class InvalidEmissionTypeError(UIContractViolation):
    """Raised when emission type is not in allowed enum."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class UIEmission:
    """
    A validated UI emission.
    
    Per INV-UI-002: Only checkpoint-type emissions allowed.
    """
    emission_type: UIEmissionType
    message: str
    hash_ref: Optional[str] = None
    agent_gid: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def render(self) -> str:
        """
        Render emission to display string.
        
        Format: {SYMBOL} {TYPE}: {MESSAGE} [{HASH_REF}]
        """
        symbol = EMISSION_SYMBOLS.get(self.emission_type, "•")
        
        parts = [symbol, f"{self.emission_type.value}:", self.message]
        
        if self.hash_ref:
            # Truncate hash for display (INV-UI-003)
            truncated = truncate_hash(self.hash_ref)
            parts.append(f"[{truncated}]")
        
        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "emission_type": self.emission_type.value,
            "message": self.message,
            "hash_ref": self.hash_ref,
            "agent_gid": self.agent_gid,
            "timestamp": self.timestamp,
            "rendered": self.render(),
        }


@dataclass
class EmissionLog:
    """
    Log of all UI emissions for audit trail.
    
    Per INV-CKPT-005: All checkpoints logged to telemetry.
    """
    entry_id: str
    emission: UIEmission
    validated: bool
    emitted_at: str


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def truncate_hash(hash_value: str, max_length: int = 12) -> str:
    """
    Truncate hash for display.
    
    Per INV-UI-003: Hash-only references, truncated for display.
    """
    if not hash_value:
        return ""
    
    # Remove prefix like "sha256:"
    if ":" in hash_value:
        prefix, actual_hash = hash_value.split(":", 1)
        if len(actual_hash) > max_length:
            return f"{prefix}:{actual_hash[:max_length]}..."
        return hash_value
    
    if len(hash_value) > max_length:
        return f"{hash_value[:max_length]}..."
    
    return hash_value


def format_agent_list(agents: List[str], max_display: int = 8) -> str:
    """
    Format agent list with bounded display.
    
    Shows up to max_display agents, then "+N more".
    """
    if len(agents) <= max_display:
        return ", ".join(agents)
    
    displayed = agents[:max_display]
    remaining = len(agents) - max_display
    return f"{', '.join(displayed)} +{remaining} more"


# ═══════════════════════════════════════════════════════════════════════════════
# FORBIDDEN CONTENT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns that indicate forbidden content
FORBIDDEN_PATTERNS = [
    (r"^\s*[-*]\s+.*$", ForbiddenContentType.TODO_UPDATE),  # Bullet lists
    (r"^\s*\d+\.\s+.*$", ForbiddenContentType.TODO_UPDATE),  # Numbered lists
    (r"^[+\-]{3,}", ForbiddenContentType.DIFF_OUTPUT),  # Diff markers
    (r"^@@.*@@", ForbiddenContentType.DIFF_OUTPUT),  # Diff hunks
    (r"Traceback \(most recent", ForbiddenContentType.STACK_TRACE),
    (r"File \".*\", line \d+", ForbiddenContentType.STACK_TRACE),
    (r"\d+%\s*(complete|done|progress)", ForbiddenContentType.PROGRESS_PERCENTAGE),
    (r"DEBUG:", ForbiddenContentType.DEBUG_LOG),
    (r"\.py$|\.tsx?$|\.js$", ForbiddenContentType.FILE_LISTING),  # File extensions in isolation
]


def contains_forbidden_content(text: str) -> Optional[ForbiddenContentType]:
    """
    Check if text contains forbidden content.
    
    Returns the type of forbidden content if found, None otherwise.
    """
    for pattern, content_type in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            return content_type
    return None


def is_unbounded_output(text: str) -> bool:
    """
    Check if output appears unbounded.
    
    Heuristics:
    - Multiple lines
    - Contains code blocks
    - Contains file paths
    - Exceeds length limit
    """
    if len(text) > UI_OUTPUT_CONFIG["max_emission_length"]:
        return True
    
    if text.count("\n") > 2:
        return True
    
    if "```" in text:
        return True
    
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_ui_emission(emission: UIEmission) -> bool:
    """
    Validate emission against UI Output Contract.
    
    Per INV-UI-006: Fail-closed — raises on violation, not returns False.
    
    Checks:
    1. Emission type is allowed (INV-UI-002)
    2. Length is bounded (INV-UI-001)
    3. No forbidden content
    4. Hash-only references (INV-UI-003)
    
    Returns True if valid.
    Raises UIContractViolation if invalid.
    """
    # Check 1: Emission type is allowed
    if not isinstance(emission.emission_type, UIEmissionType):
        raise InvalidEmissionTypeError(
            f"Invalid emission type: {emission.emission_type}"
        )
    
    # Check 2: Render and check length
    rendered = emission.render()
    max_length = UI_OUTPUT_CONFIG["max_emission_length"]
    
    if len(rendered) > max_length:
        raise UnboundedOutputError(
            f"Emission exceeds {max_length} chars: {len(rendered)} chars"
        )
    
    # Check 3: No forbidden content in message
    forbidden = contains_forbidden_content(emission.message)
    if forbidden:
        raise ForbiddenEmissionError(
            f"Forbidden content detected: {forbidden.value}"
        )
    
    # Check 4: If hash_ref provided, verify it looks like a hash
    if emission.hash_ref:
        if not (
            emission.hash_ref.startswith("sha256:") or
            emission.hash_ref.startswith("sha3:") or
            emission.hash_ref.startswith("sxt:") or
            re.match(r"^[a-fA-F0-9]{32,}$", emission.hash_ref)
        ):
            # Allow BER/PDO IDs as refs too
            if not re.match(r"^(BER|PDO|WRAP)-", emission.hash_ref):
                raise ForbiddenEmissionError(
                    f"Invalid hash reference format: {emission.hash_ref}"
                )
    
    return True


def reject_unbounded_output(output: Any) -> None:
    """
    Reject any attempt to emit unbounded output.
    
    Per INV-UI-006: FAIL-CLOSED — does not truncate, does not modify.
    
    Raises UnboundedOutputError unconditionally.
    """
    output_type = type(output).__name__
    output_preview = str(output)[:50] + "..." if len(str(output)) > 50 else str(output)
    
    raise UnboundedOutputError(
        f"Unbounded output rejected: {output_type} — {output_preview}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# UI OUTPUT CONTRACT ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════

class UIOutputContract:
    """
    Enforces the UI Output Contract.
    
    All UI emissions must pass through this contract.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the contract enforcer."""
        self._config = {**UI_OUTPUT_CONFIG, **(config or {})}
        self._lock = threading.RLock()
        self._emission_log: List[EmissionLog] = []
        self._entry_counter = 0
        self._emissions_this_session: int = 0

    @property
    def config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    def emit(self, emission: UIEmission) -> str:
        """
        Validate and emit a UI signal.
        
        Returns the rendered emission string if valid.
        Raises UIContractViolation if invalid.
        """
        with self._lock:
            # Validate against contract
            validate_ui_emission(emission)
            
            # Log emission
            self._entry_counter += 1
            log_entry = EmissionLog(
                entry_id=f"UI-EMIT-{self._entry_counter:06d}",
                emission=emission,
                validated=True,
                emitted_at=datetime.utcnow().isoformat() + "Z",
            )
            self._emission_log.append(log_entry)
            self._emissions_this_session += 1
            
            return emission.render()

    def create_emission(
        self,
        emission_type: UIEmissionType,
        message: str,
        hash_ref: Optional[str] = None,
        agent_gid: Optional[str] = None,
    ) -> UIEmission:
        """
        Create and validate a UI emission.
        
        Convenience method that creates and validates in one call.
        """
        emission = UIEmission(
            emission_type=emission_type,
            message=message,
            hash_ref=hash_ref,
            agent_gid=agent_gid,
        )
        
        # Validate before returning
        validate_ui_emission(emission)
        
        return emission

    def emit_pac_received(self, pac_id: str) -> str:
        """Emit PAC_RECEIVED checkpoint."""
        emission = self.create_emission(
            UIEmissionType.PAC_RECEIVED,
            f"{pac_id} validated",
        )
        return self.emit(emission)

    def emit_agents_dispatched(self, agents: List[str]) -> str:
        """Emit AGENTS_DISPATCHED checkpoint."""
        agent_list = format_agent_list(agents)
        emission = self.create_emission(
            UIEmissionType.AGENTS_DISPATCHED,
            f"{len(agents)} agents ({agent_list})",
        )
        return self.emit(emission)

    def emit_agent_started(self, agent_gid: str, lane: str) -> str:
        """Emit AGENT_STARTED checkpoint."""
        emission = self.create_emission(
            UIEmissionType.AGENT_STARTED,
            f"{agent_gid} — {lane} lane",
            agent_gid=agent_gid,
        )
        return self.emit(emission)

    def emit_agent_completed(
        self,
        agent_gid: str,
        test_count: Optional[int] = None,
    ) -> str:
        """Emit AGENT_COMPLETED checkpoint."""
        message = agent_gid
        if test_count is not None:
            message = f"{agent_gid} — {test_count} tests passed"
        
        emission = self.create_emission(
            UIEmissionType.AGENT_COMPLETED,
            message,
            agent_gid=agent_gid,
        )
        return self.emit(emission)

    def emit_wrap_received(self, agent_gid: str, wrap_hash: str) -> str:
        """Emit WRAP_HASH_RECEIVED checkpoint."""
        emission = self.create_emission(
            UIEmissionType.WRAP_HASH_RECEIVED,
            agent_gid,
            hash_ref=wrap_hash,
            agent_gid=agent_gid,
        )
        return self.emit(emission)

    def emit_all_wraps_received(self, count: int) -> str:
        """Emit ALL_WRAPS_RECEIVED checkpoint."""
        emission = self.create_emission(
            UIEmissionType.ALL_WRAPS_RECEIVED,
            f"{count}/{count} WRAPs verified",
        )
        return self.emit(emission)

    def emit_ber_issued(self, status: str, ber_id: str) -> str:
        """Emit BER_ISSUED checkpoint."""
        emission = self.create_emission(
            UIEmissionType.BER_ISSUED,
            f"{status} — all invariants satisfied",
            hash_ref=ber_id,
        )
        return self.emit(emission)

    def emit_pdo_emitted(self, pdo_id: str, pdo_hash: str) -> str:
        """Emit PDO_EMITTED checkpoint."""
        emission = self.create_emission(
            UIEmissionType.PDO_EMITTED,
            pdo_id,
            hash_ref=pdo_hash,
        )
        return self.emit(emission)

    def emit_error(self, error_type: str, description: str) -> str:
        """Emit ERROR_SIGNAL checkpoint."""
        emission = self.create_emission(
            UIEmissionType.ERROR_SIGNAL,
            f"{error_type} — {description}",
        )
        return self.emit(emission)

    def get_emission_count(self) -> int:
        """Get total emissions this session."""
        with self._lock:
            return self._emissions_this_session

    def get_emission_log(self) -> List[EmissionLog]:
        """Get full emission log for audit."""
        with self._lock:
            return list(self._emission_log)

    def calculate_max_emissions(self, agent_count: int) -> int:
        """
        Calculate maximum allowed emissions for agent count.
        
        Formula: 4 + 3N (per CHECKPOINT_EMISSION_RULES_v1.md)
        """
        return 4 + (3 * agent_count)

    def reset_session(self) -> None:
        """Reset session counter (for testing)."""
        with self._lock:
            self._emissions_this_session = 0


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_global_contract: Optional[UIOutputContract] = None
_global_lock = threading.Lock()


def get_ui_contract(config: Optional[Dict[str, Any]] = None) -> UIOutputContract:
    """Get or create global UI output contract."""
    global _global_contract
    
    with _global_lock:
        if _global_contract is None:
            _global_contract = UIOutputContract(config=config)
        return _global_contract


def reset_ui_contract() -> None:
    """Reset global contract (for testing)."""
    global _global_contract
    
    with _global_lock:
        _global_contract = None
