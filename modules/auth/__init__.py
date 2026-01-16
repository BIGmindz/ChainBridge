"""
ChainBridge Authentication Modules
==================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING v2.0.0
Enterprise authentication infrastructure modules.

SUB-MODULES:
  - blockchain: XRP Ledger audit anchoring
  - ml: ChainIQ ML risk scoring
  - integrations: SSO (SEEBURGER, Okta, Auth0)
  - pqc: Post-quantum cryptography
"""

from .blockchain import (
    XRPConfig,
    XRPNetwork,
    MerkleTree,
    AuditAnchor,
    AuditAnchorService,
    get_anchor_service,
    init_anchor_service,
)

from .ml import (
    MLConfig,
    ModelType,
    FeatureVector,
    MLPrediction,
    MLRiskScorer,
    get_ml_scorer,
    init_ml_scorer,
)

from .integrations import (
    SSOProtocol,
    SSOProvider,
    SSOConfig,
    SSOUser,
    SSOToken,
    BaseSSOProvider,
    OktaProvider,
    Auth0Provider,
    SEEBURGERProvider,
    SSOManager,
    create_okta_config,
    create_auth0_config,
    create_seeburger_config,
)

from .pqc import (
    PQCAlgorithm,
    KeyType,
    PQCConfig,
    PQCKeyPair,
    PQCSignature,
    PQCKeyGenerator,
    MLDSAKeyGenerator,
    MLKEMKeyGenerator,
    PQCTokenIssuer,
    PQCKeyManager,
    init_pqc,
    get_pqc_issuer,
    get_pqc_key_manager,
)

__all__ = [
    # Blockchain
    "XRPConfig",
    "XRPNetwork",
    "MerkleTree",
    "AuditAnchor",
    "AuditAnchorService",
    "get_anchor_service",
    "init_anchor_service",
    # ML
    "MLConfig",
    "ModelType",
    "FeatureVector",
    "MLPrediction",
    "MLRiskScorer",
    "get_ml_scorer",
    "init_ml_scorer",
    # SSO Integrations
    "SSOProtocol",
    "SSOProvider",
    "SSOConfig",
    "SSOUser",
    "SSOToken",
    "BaseSSOProvider",
    "OktaProvider",
    "Auth0Provider",
    "SEEBURGERProvider",
    "SSOManager",
    "create_okta_config",
    "create_auth0_config",
    "create_seeburger_config",
    # Post-Quantum Cryptography
    "PQCAlgorithm",
    "KeyType",
    "PQCConfig",
    "PQCKeyPair",
    "PQCSignature",
    "PQCKeyGenerator",
    "MLDSAKeyGenerator",
    "MLKEMKeyGenerator",
    "PQCTokenIssuer",
    "PQCKeyManager",
    "init_pqc",
    "get_pqc_issuer",
    "get_pqc_key_manager",
]
