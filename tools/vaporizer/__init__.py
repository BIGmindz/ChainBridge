"""
ChainBridge Vaporizer Tools
PAC-VAPORIZER-DEPLOY-27

Client-side Zero-PII hashing utility for partner banks.
"""

from .vaporizer import (
    VaporizerEngine,
    VaporizedRecord,
    CBHFile,
    SovereignSaltConfig,
    DataNormalizer,
    run_self_test,
    run_integrity_validation,
)

__all__ = [
    "VaporizerEngine",
    "VaporizedRecord",
    "CBHFile",
    "SovereignSaltConfig",
    "DataNormalizer",
    "run_self_test",
    "run_integrity_validation",
]

__version__ = "1.0.0"
__pac__ = "PAC-VAPORIZER-DEPLOY-27"
