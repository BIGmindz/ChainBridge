"""
ChainBridge Immune System Module
================================

PAC-SYS-P160-IMMUNE-INIT: The White Blood Cells of the Sovereign System.

This module provides autonomous remediation capabilities for the Trinity Gate
architecture. Where v1.0 (The Shield) blocks threats, v2.0 (The Immune System)
attempts to heal them before final rejection.

Core Components:
    - RemediationEngine: Orchestrates fix attempts for failed transactions
    - RemediationStrategy: Abstract base for pluggable fix strategies
    - RemediationPlan: Action plan for correcting transaction errors

Invariants:
    - INV-SYS-001: Human-in-the-Loop Fallback - If Immune System fails, Gate stays Closed
    - INV-SYS-002: No Auto-Approval - System can only fix inputs, never bypass gates

Usage:
    from modules.immune import RemediationEngine, RemediationPlan
    
    engine = RemediationEngine()
    plan = engine.diagnose(failed_receipt)
    if plan.can_remediate:
        corrected_data = plan.execute()

Author: Benson (GID-00)
Classification: SYSTEM_EVOLUTION
Attestation: MASTER-BER-P160-INIT
"""

from .remediator import (
    RemediationEngine,
    RemediationStrategy,
    RemediationPlan,
    RemediationResult,
    EscalationLevel,
)

from .strategies import MissingFieldStrategy, FormatCorrectionStrategy, DocumentRetryStrategy, WatchlistClearanceStrategy

__all__ = [
    "RemediationEngine",
    "RemediationStrategy", 
    "RemediationPlan",
    "RemediationResult",
    "EscalationLevel",
    "MissingFieldStrategy",
    "FormatCorrectionStrategy",
    "DocumentRetryStrategy",
    "WatchlistClearanceStrategy",
]

__version__ = "2.0.0-alpha"
__pac__ = "PAC-SYS-P160-IMMUNE-INIT"
__attestation__ = "MASTER-BER-P160-INIT"
