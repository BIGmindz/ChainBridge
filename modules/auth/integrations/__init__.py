"""
SSO Integration Module Exports
==============================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING v2.0.0
Module: Single Sign-On Integrations
"""

from .sso_providers import (
    # Enums
    SSOProtocol,
    SSOProvider,
    
    # Config and Data Classes
    SSOConfig,
    SSOUser,
    SSOToken,
    
    # Base Provider
    BaseSSOProvider,
    
    # Provider Implementations
    OktaProvider,
    Auth0Provider,
    SEEBURGERProvider,
    
    # Manager
    SSOManager,
    
    # Factory Functions
    create_okta_config,
    create_auth0_config,
    create_seeburger_config,
)

__all__ = [
    # Enums
    "SSOProtocol",
    "SSOProvider",
    
    # Config and Data Classes
    "SSOConfig",
    "SSOUser",
    "SSOToken",
    
    # Base Provider
    "BaseSSOProvider",
    
    # Provider Implementations
    "OktaProvider",
    "Auth0Provider",
    "SEEBURGERProvider",
    
    # Manager
    "SSOManager",
    
    # Factory Functions
    "create_okta_config",
    "create_auth0_config",
    "create_seeburger_config",
]
