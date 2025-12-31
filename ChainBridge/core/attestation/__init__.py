"""
Core Attestation Module — PAC-SAM-P01-ATTESTATION-PROVIDER-READINESS-01

Cryptographic attestation infrastructure for governance artifacts.

Authority: SAM (GID-06)
Dispatch: PAC-BENSON-EXEC-P62
Mode: SECURITY ANALYSIS
"""

from core.attestation.provider import (
    AttestationProvider,
    AttestationResult,
    AttestationError,
    AttestationStatus,
)
from core.attestation.offchain import OffChainAttestationProvider
from core.attestation.schemas import (
    AttestationRecord,
    AttestationChain,
    ArtifactAttestation,
)

__all__ = [
    # Protocol
    "AttestationProvider",
    "AttestationResult",
    "AttestationError",
    "AttestationStatus",
    # Implementations
    "OffChainAttestationProvider",
    # Schemas
    "AttestationRecord",
    "AttestationChain",
    "ArtifactAttestation",
]
