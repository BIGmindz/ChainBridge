"""
ChainBridge Session State — Terminal State Machine
════════════════════════════════════════════════════════════════════════════════

Defines session state machine for PAC execution.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-BER-LOOP-ENFORCEMENT-020
Effective Date: 2025-12-26

TERMINAL STATE RULES:
- Valid terminal states: BER_ISSUED, SESSION_COMPLETE, REJECTED
- Invalid terminal states: SESSION_INVALID
- Non-terminal states: PAC_RECEIVED, PAC_DISPATCHED, EXECUTING, WRAP_RECEIVED, BER_REQUIRED
- BER_REQUIRED is NON-TERMINAL (session cannot end here)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

# Re-export from ber_loop_enforcer for backward compatibility
from core.governance.ber_loop_enforcer import (
    SessionState,
    SessionRecord,
    VALID_TERMINAL_STATES,
    INVALID_TERMINAL_STATES,
    ALL_TERMINAL_STATES,
    NON_TERMINAL_STATES,
    is_terminal_state,
    is_valid_terminal_state,
    is_invalid_terminal_state,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_terminal_state(state: SessionState) -> bool:
    """
    Validate that a terminal state is valid.
    
    Returns True only for valid terminal states (BER_ISSUED, SESSION_COMPLETE, REJECTED).
    Returns False for invalid terminal states (SESSION_INVALID).
    Raises ValueError for non-terminal states.
    """
    if state in NON_TERMINAL_STATES:
        raise ValueError(
            f"State {state.value} is non-terminal. "
            f"Session cannot end in this state."
        )
    return state in VALID_TERMINAL_STATES


def require_valid_terminal(state: SessionState) -> None:
    """
    Require that state is a valid terminal state.
    
    Raises ValueError if not.
    """
    if not validate_terminal_state(state):
        raise ValueError(
            f"State {state.value} is not a valid terminal state. "
            f"Valid terminal states: {[s.value for s in VALID_TERMINAL_STATES]}"
        )


def can_transition_to_terminal(state: SessionState) -> bool:
    """
    Check if state can transition to a terminal state.
    
    Only BER_ISSUED and BER_REQUIRED (to SESSION_INVALID) can transition to terminal.
    """
    return state in {
        SessionState.BER_ISSUED,
        SessionState.BER_REQUIRED,  # Can go to SESSION_INVALID
        SessionState.REJECTED,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STATE TRANSITION VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════

# Valid state transitions
VALID_TRANSITIONS = {
    SessionState.PAC_RECEIVED: {
        SessionState.PAC_DISPATCHED,
        SessionState.REJECTED,
        SessionState.SESSION_INVALID,
    },
    SessionState.PAC_DISPATCHED: {
        SessionState.EXECUTING,
        SessionState.WRAP_RECEIVED,
        SessionState.SESSION_INVALID,
    },
    SessionState.EXECUTING: {
        SessionState.WRAP_RECEIVED,
        SessionState.SESSION_INVALID,
    },
    SessionState.WRAP_RECEIVED: {
        SessionState.BER_REQUIRED,
        SessionState.SESSION_INVALID,
    },
    SessionState.BER_REQUIRED: {
        SessionState.BER_ISSUED,
        SessionState.SESSION_INVALID,
    },
    SessionState.BER_ISSUED: {
        SessionState.SESSION_COMPLETE,
    },
    # Terminal states have no transitions
    SessionState.SESSION_COMPLETE: set(),
    SessionState.SESSION_INVALID: set(),
    SessionState.REJECTED: set(),
}


def is_valid_transition(from_state: SessionState, to_state: SessionState) -> bool:
    """Check if transition is valid."""
    return to_state in VALID_TRANSITIONS.get(from_state, set())


def require_valid_transition(from_state: SessionState, to_state: SessionState) -> None:
    """
    Require that transition is valid.
    
    Raises ValueError if not.
    """
    if not is_valid_transition(from_state, to_state):
        valid = VALID_TRANSITIONS.get(from_state, set())
        raise ValueError(
            f"Invalid transition: {from_state.value} → {to_state.value}. "
            f"Valid transitions from {from_state.value}: {[s.value for s in valid]}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# BER REQUIREMENT CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def requires_ber(state: SessionState) -> bool:
    """
    Check if state requires BER before completion.
    
    WRAP_RECEIVED and BER_REQUIRED both require BER.
    """
    return state in {SessionState.WRAP_RECEIVED, SessionState.BER_REQUIRED}


def ber_was_issued(state: SessionState) -> bool:
    """Check if BER was issued (state is BER_ISSUED or beyond)."""
    return state in {SessionState.BER_ISSUED, SessionState.SESSION_COMPLETE}


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Re-exports from ber_loop_enforcer
    "SessionState",
    "SessionRecord",
    "VALID_TERMINAL_STATES",
    "INVALID_TERMINAL_STATES",
    "ALL_TERMINAL_STATES",
    "NON_TERMINAL_STATES",
    "is_terminal_state",
    "is_valid_terminal_state",
    "is_invalid_terminal_state",
    
    # Validators
    "validate_terminal_state",
    "require_valid_terminal",
    "can_transition_to_terminal",
    
    # Transitions
    "VALID_TRANSITIONS",
    "is_valid_transition",
    "require_valid_transition",
    
    # BER checks
    "requires_ber",
    "ber_was_issued",
]
