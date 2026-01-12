"""
ChainBridge Governance as a Service (GaaS) Module
================================================

The Universal Gasket for Multi-Tenant Sovereignty.

This module provides process-isolated tenant instances that share
hardware but not memory. Each tenant gets:
- Dedicated Sovereign Node process
- Isolated ledger storage
- Private cryptographic keys
- Bounded resource quotas

Architecture:
    GaaSController (Warden) → TenantJail (Isolation) → SovereignProcess

Invariants:
    INV-GAAS-001: Memory space of Tenant A is inaccessible to Tenant B
    INV-GAAS-002: No tenant can starve the host system

PAC Reference: PAC-STRAT-P900-GAAS
Version: 1.0.0
"""

__version__ = "1.0.0"
__pac__ = "PAC-STRAT-P900-GAAS"

from .isolation import TenantJail, IsolationConfig, ResourceLimits
from .controller import GaaSController, TenantState, TenantConfig

__all__ = [
    "GaaSController",
    "TenantJail",
    "TenantConfig",
    "TenantState",
    "IsolationConfig",
    "ResourceLimits",
]
