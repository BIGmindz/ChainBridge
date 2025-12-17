"""
Core Governance Module — ALEX Runtime Enforcement

This module implements hard runtime enforcement of the Agent Capability Manifest (ACM).
ALEX (GID-08) is the sole authority for evaluating and denying agent intents.

Enforcement principles:
- Default Deny: Absence of permission = rejection
- No Prompt Reliance: Enforcement is code-only
- No Silent Failure: Every denial emits a structured audit record
- No Capability Inference: Only explicit ACM entries count
- No APPROVE Path: Humans only, never agents
- No Mutation Without EXECUTE: READ/PROPOSE cannot mutate state
- No Drift: Enforcement logic references manifests directly
"""

from core.governance.acm_evaluator import ACMDecision, ACMEvaluator, DenialReason, EvaluationResult
from core.governance.acm_loader import ACMLoader, ACMLoadError, ACMValidationError

__all__ = [
    "ACMLoader",
    "ACMLoadError",
    "ACMValidationError",
    "ACMEvaluator",
    "ACMDecision",
    "EvaluationResult",
    "DenialReason",
]
