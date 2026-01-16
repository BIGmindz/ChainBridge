"""
Control Plane Hardening Module
PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true

This module provides hardened control-plane primitives:
- Authority Lattice (AL): Multi-dimensional authority evaluation
- Leased Authority Primitive (LAP): Time-bound authority with automatic reversion
- Escalation Interface: Safe authority escalation patterns

CORE PRINCIPLE: Authority = Identity × Context × Hardware × Time
               Missing coordinate ⇒ authority = ZERO
"""

from core.control_plane.authority_lattice import (
    AuthorityLattice,
    AuthorityCoordinate,
    AuthorityLevel,
    LatticeNode,
)

from core.control_plane.leased_authority import (
    LeasedAuthority,
    AuthorityLease,
    LeaseState,
)

__all__ = [
    "AuthorityLattice",
    "AuthorityCoordinate",
    "AuthorityLevel",
    "LatticeNode",
    "LeasedAuthority",
    "AuthorityLease",
    "LeaseState",
]
