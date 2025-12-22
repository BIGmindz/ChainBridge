"""ChainBridge Security Module.

Implements threat hardening for the A1-A5 locked architecture.
Assumes malicious inputs, compromised runtimes, and hostile integrations.

DOCTRINE: All attacks MUST fail closed with observable audit trail.

Modules:
- pdo_verifier: PDO tampering defense
- proof_integrity: Proof artifact cryptographic integrity
- settlement_guard: Settlement attack prevention
- runtime_threats: Runtime escape prevention

Author: Sam (GID-06) — Security & Threat Engineer
"""
from chainbridge.security.pdo_verifier import (
    AttackDetectionResult,
    AttackType,
    PDOAuthoritySpoofError,
    PDOReplayError,
    PDOTamperingError,
    PDOVerifier,
)
from chainbridge.security.proof_integrity import (
    IntegrityCheckResult,
    IntegrityViolationType,
    ProofHashCollisionError,
    ProofIntegrityChecker,
    ProofLineageTruncationError,
    ProofOutOfOrderError,
)
from chainbridge.security.runtime_threats import (
    InjectionType,
    MutationType,
    ProofMutationAttemptError,
    RuntimePrivilegeEscalationError,
    RuntimeThreatGuard,
    RuntimeThreatType,
    SettlementInjectionError,
    ThreatDetectionResult,
    UnauthorizedAgentDecisionError,
)
from chainbridge.security.settlement_guard import (
    CROOverrideRequest,
    DoubleSettlementError,
    SettlementAttackType,
    SettlementGuard,
    SettlementGuardResult,
    SettlementLockError,
    SettlementRaceConditionError,
    UnauthorizedCROOverrideError,
)

__all__ = [
    # PDO Verifier
    "PDOVerifier",
    "PDOTamperingError",
    "PDOReplayError",
    "PDOAuthoritySpoofError",
    "AttackType",
    "AttackDetectionResult",
    # Proof Integrity
    "ProofIntegrityChecker",
    "ProofHashCollisionError",
    "ProofLineageTruncationError",
    "ProofOutOfOrderError",
    "IntegrityViolationType",
    "IntegrityCheckResult",
    # Settlement Guard
    "SettlementGuard",
    "DoubleSettlementError",
    "SettlementRaceConditionError",
    "UnauthorizedCROOverrideError",
    "SettlementLockError",
    "SettlementAttackType",
    "SettlementGuardResult",
    "CROOverrideRequest",
    # Runtime Threats
    "RuntimeThreatGuard",
    "UnauthorizedAgentDecisionError",
    "ProofMutationAttemptError",
    "SettlementInjectionError",
    "RuntimePrivilegeEscalationError",
    "RuntimeThreatType",
    "ThreatDetectionResult",
    "MutationType",
    "InjectionType",
]
