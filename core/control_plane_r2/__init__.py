"""
Control Plane Replacement R2
PAC-JEFFREY-CTRLPLANE-REPLACEMENT-R2-001

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true
SUPERSEDES: PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001

This module provides hardened control-plane primitives (R2):
- Escalation State Machine (ESM): Formal state-based authority transitions
- Unified Lease Lifecycle Controller: No renewals, clean expiration only
- Drift Sentinel: Governance-as-signal for canonical state enforcement

CORE PRINCIPLE: Authority is STATE, not ATTRIBUTE.
               Transitions are EXPLICIT, never implicit.
               Renewal is FORBIDDEN — only fresh grants.
"""

from core.control_plane_r2.escalation_state_machine import (
    EscalationStateMachine,
    ESMState,
    ESMTransition,
    TransitionResult,
)

from core.control_plane_r2.unified_lease_controller import (
    UnifiedLeaseController,
    Lease,
    LeaseTermination,
)

from core.control_plane_r2.drift_sentinel import (
    DriftSentinel,
    DriftSignal,
    DriftSeverity,
)

__all__ = [
    "EscalationStateMachine",
    "ESMState",
    "ESMTransition",
    "TransitionResult",
    "UnifiedLeaseController",
    "Lease",
    "LeaseTermination",
    "DriftSentinel",
    "DriftSignal",
    "DriftSeverity",
]
