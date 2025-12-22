"""Proof Services Module.

════════════════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-01 — CODY (BACKEND ENGINEERING)
PAC-CODY-A6-BACKEND-GUARDRAILS-CORRECTION-AND-REALIGNMENT-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════════════════

I. EXECUTING AGENT (MANDATORY)

EXECUTING AGENT: CODY
GID: GID-01
EXECUTING COLOR: 🔵 BLUE — Backend Engineering Lane

⸻

Backend service layer for proof lineage validation.

⸻

PROHIBITED:
- Identity drift
- Color violation
- Lane bypass

════════════════════════════════════════════════════════════════════════════════
"""

from app.services.proof.lineage import (
    ProofLineageService,
    LineageValidationResult,
    LineageViolationType,
    validate_proof_lineage,
    enforce_forward_only_linkage,
    detect_lineage_mutation,
)

__all__ = [
    # Classes
    "ProofLineageService",
    "LineageValidationResult",
    "LineageViolationType",
    # Functions
    "validate_proof_lineage",
    "enforce_forward_only_linkage",
    "detect_lineage_mutation",
]


# ════════════════════════════════════════════════════════════════════════════════
# END — CODY (GID-01) — 🔵 BLUE
# 🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
# ════════════════════════════════════════════════════════════════════════════════
