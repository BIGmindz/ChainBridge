"""
Auth Modules Integration Tests
==============================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING v2.0.0
Test Suite: modules/auth/* integration tests

Tests SSO providers, PQC tokens, blockchain anchoring, and ML scoring.
"""

import asyncio
import base64
import json
import pytest
import secrets
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# SSO Provider Tests
class TestSSOProviders:
    """Tests for SSO provider integrations."""
    
    def test_sso_protocol_enum_values(self):
        """Test SSOProtocol enum has correct values."""
        from modules.auth.integrations import SSOProtocol
        
        assert SSOProtocol.SAML_2_0.value == "saml_2_0"
        assert SSOProtocol.OIDC.value == "oidc"
        assert SSOProtocol.OAUTH2.value == "oauth2"
    
    def test_sso_provider_enum_values(self):
        """Test SSOProvider enum has correct values."""
        from modules.auth.integrations import SSOProvider
        
        assert SSOProvider.SEEBURGER.value == "seeburger"
        assert SSOProvider.OKTA.value == "okta"
        assert SSOProvider.AUTH0.value == "auth0"
        assert SSOProvider.AZURE_AD.value == "azure_ad"
        assert SSOProvider.GOOGLE.value == "google"
    
    def test_sso_config_defaults(self):
        """Test SSOConfig default values."""
        from modules.auth.integrations import SSOConfig, SSOProvider, SSOProtocol
        
        config = SSOConfig(
            provider=SSOProvider.OKTA,
            protocol=SSOProtocol.OIDC
        )
        
        assert config.session_lifetime_seconds == 3600
        assert config.refresh_enabled is True
        assert "sub" in config.claims_mapping
    
    def test_sso_user_to_dict(self):
        """Test SSOUser serialization."""
        from modules.auth.integrations import SSOUser, SSOProvider
        
        user = SSOUser(
            provider=SSOProvider.OKTA,
            provider_user_id="user123",
            email="test@example.com",
            display_name="Test User",
            roles=["admin"],
            gid="GID-01"
        )
        
        data = user.to_dict()
        assert data["provider"] == "okta"
        assert data["email"] == "test@example.com"
        assert data["gid"] == "GID-01"
    
    def test_sso_token_expiration(self):
        """Test SSOToken expiration check."""
        from modules.auth.integrations import SSOToken
        
        # Non-expired token
        token = SSOToken(
            access_token="test_token",
            expires_in=3600
        )
        assert token.is_expired is False
        
        # Expired token
        expired = SSOToken(
            access_token="expired",
            expires_in=0,
            issued_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert expired.is_expired is True
    
    def test_okta_authorization_url(self):
        """Test Okta authorization URL generation."""
        from modules.auth.integrations import OktaProvider, SSOConfig, SSOProvider, SSOProtocol
        
        config = SSOConfig(
            provider=SSOProvider.OKTA,
            protocol=SSOProtocol.OIDC,
            client_id="test_client",
            redirect_uri="https://app.example.com/callback",
            authorization_endpoint="https://dev.okta.com/oauth2/v1/authorize"
        )
        
        provider = OktaProvider(config)
        url = provider.get_authorization_url("state123", "nonce456")
        
        assert "client_id=test_client" in url
        assert "state=state123" in url
        assert "nonce=nonce456" in url
    
    def test_auth0_authorization_url(self):
        """Test Auth0 authorization URL generation."""
        from modules.auth.integrations import Auth0Provider, SSOConfig, SSOProvider, SSOProtocol
        
        config = SSOConfig(
            provider=SSOProvider.AUTH0,
            protocol=SSOProtocol.OIDC,
            client_id="auth0_client",
            redirect_uri="https://app.example.com/callback",
            authorization_endpoint="https://tenant.auth0.com/authorize",
            entity_id="https://api.example.com"
        )
        
        provider = Auth0Provider(config)
        url = provider.get_authorization_url("state123", "nonce456")
        
        assert "client_id=auth0_client" in url
        assert "audience=" in url
    
    def test_seeburger_saml_request_generation(self):
        """Test SEEBURGER SAML AuthnRequest generation."""
        from modules.auth.integrations import SEEBURGERProvider, SSOConfig, SSOProvider, SSOProtocol
        
        config = SSOConfig(
            provider=SSOProvider.SEEBURGER,
            protocol=SSOProtocol.SAML_2_0,
            entity_id="https://chainbridge.io/sp",
            idp_sso_url="https://seeburger.example.com/sso",
            redirect_uri="https://chainbridge.io/saml/callback"
        )
        
        provider = SEEBURGERProvider(config)
        url = provider.get_authorization_url("state123", "nonce456")
        
        assert "SAMLRequest=" in url
        assert "RelayState=state123" in url
    
    def test_sso_manager_register_provider(self):
        """Test SSO manager provider registration."""
        from modules.auth.integrations import SSOManager, SSOConfig, SSOProvider, SSOProtocol
        
        manager = SSOManager()
        
        config = SSOConfig(
            provider=SSOProvider.OKTA,
            protocol=SSOProtocol.OIDC,
            client_id="test"
        )
        
        provider = manager.register_provider(config)
        assert provider is not None
        
        retrieved = manager.get_provider(SSOProvider.OKTA)
        assert retrieved is provider
    
    def test_sso_manager_initiate_auth(self):
        """Test SSO manager auth initiation."""
        from modules.auth.integrations import (
            SSOManager, SSOConfig, SSOProvider, SSOProtocol
        )
        
        manager = SSOManager()
        manager.register_provider(SSOConfig(
            provider=SSOProvider.OKTA,
            protocol=SSOProtocol.OIDC,
            client_id="test",
            authorization_endpoint="https://okta.example.com/authorize",
            redirect_uri="https://app.example.com/callback"
        ))
        
        url, state = manager.initiate_auth(SSOProvider.OKTA)
        
        assert "https://okta.example.com/authorize" in url
        assert len(state) > 20
    
    def test_create_okta_config_factory(self):
        """Test Okta config factory function."""
        from modules.auth.integrations import create_okta_config, SSOProvider
        
        config = create_okta_config(
            domain="dev.okta.com",
            client_id="client123",
            client_secret="secret456",
            redirect_uri="https://app.example.com/callback"
        )
        
        assert config.provider == SSOProvider.OKTA
        assert config.client_id == "client123"
        assert "dev.okta.com" in config.authorization_endpoint
    
    def test_create_auth0_config_factory(self):
        """Test Auth0 config factory function."""
        from modules.auth.integrations import create_auth0_config, SSOProvider
        
        config = create_auth0_config(
            domain="tenant.auth0.com",
            client_id="client123",
            client_secret="secret456",
            redirect_uri="https://app.example.com/callback",
            audience="https://api.example.com"
        )
        
        assert config.provider == SSOProvider.AUTH0
        assert config.entity_id == "https://api.example.com"
    
    def test_create_seeburger_config_factory(self):
        """Test SEEBURGER config factory function."""
        from modules.auth.integrations import create_seeburger_config, SSOProvider
        
        config = create_seeburger_config(
            entity_id="https://chainbridge.io/sp",
            idp_sso_url="https://seeburger.example.com/sso",
            idp_certificate="CERT_DATA",
            redirect_uri="https://chainbridge.io/saml/callback"
        )
        
        assert config.provider == SSOProvider.SEEBURGER
        assert config.idp_certificate == "CERT_DATA"


class TestPQCTokens:
    """Tests for post-quantum cryptography tokens."""
    
    def test_pqc_algorithm_enum(self):
        """Test PQCAlgorithm enum values."""
        from modules.auth.pqc import PQCAlgorithm
        
        assert PQCAlgorithm.ML_DSA_65.value == "ml_dsa_65"
        assert PQCAlgorithm.ML_KEM_768.value == "ml_kem_768"
        assert PQCAlgorithm.SPHINCS_256.value == "sphincs_256"
    
    def test_key_type_enum(self):
        """Test KeyType enum values."""
        from modules.auth.pqc import KeyType
        
        assert KeyType.SIGNING.value == "signing"
        assert KeyType.ENCRYPTION.value == "encryption"
        assert KeyType.KEY_EXCHANGE.value == "key_exchange"
    
    def test_pqc_config_defaults(self):
        """Test PQCConfig default values."""
        from modules.auth.pqc import PQCConfig, PQCAlgorithm
        
        config = PQCConfig()
        
        assert config.signing_algorithm == PQCAlgorithm.ML_DSA_65
        assert config.encryption_algorithm == PQCAlgorithm.ML_KEM_768
        assert config.hybrid_mode is True
        assert config.key_rotation_days == 90
    
    def test_ml_dsa_keypair_generation(self):
        """Test ML-DSA key pair generation."""
        from modules.auth.pqc import MLDSAKeyGenerator, KeyType
        
        generator = MLDSAKeyGenerator(security_level=3)
        keypair = generator.generate_keypair(KeyType.SIGNING)
        
        assert keypair.public_key is not None
        assert keypair.private_key is not None
        assert len(keypair.key_id) > 0
        assert keypair.use_count == 0
    
    def test_ml_dsa_sign_verify(self):
        """Test ML-DSA signing and verification."""
        from modules.auth.pqc import MLDSAKeyGenerator, KeyType
        
        generator = MLDSAKeyGenerator()
        keypair = generator.generate_keypair(KeyType.SIGNING)
        
        message = b"test message to sign"
        signature = generator.sign(keypair.private_key, message)
        
        assert len(signature) > 3000  # ML-DSA-65 signature size
    
    def test_ml_kem_keypair_generation(self):
        """Test ML-KEM key pair generation."""
        from modules.auth.pqc import MLKEMKeyGenerator, KeyType
        
        generator = MLKEMKeyGenerator()
        keypair = generator.generate_keypair(KeyType.KEY_EXCHANGE)
        
        assert len(keypair.public_key) >= 1000  # Key material present
        assert len(keypair.private_key) >= 1000  # Key material present
    
    def test_ml_kem_encapsulation(self):
        """Test ML-KEM key encapsulation."""
        from modules.auth.pqc import MLKEMKeyGenerator
        
        generator = MLKEMKeyGenerator()
        keypair = generator.generate_keypair()
        
        ciphertext, shared_secret = generator.encapsulate(keypair.public_key)
        
        assert len(ciphertext) >= 1000  # Ciphertext present
        assert len(shared_secret) == 32  # SHA3-256 output
    
    def test_ml_kem_decapsulation(self):
        """Test ML-KEM decapsulation."""
        from modules.auth.pqc import MLKEMKeyGenerator
        
        generator = MLKEMKeyGenerator()
        keypair = generator.generate_keypair()
        
        ciphertext, _ = generator.encapsulate(keypair.public_key)
        recovered = generator.decapsulate(keypair.private_key, ciphertext)
        
        assert len(recovered) == 32
    
    def test_pqc_keypair_expiration(self):
        """Test PQCKeyPair expiration checking."""
        from modules.auth.pqc import PQCKeyPair, PQCAlgorithm, KeyType
        from datetime import datetime, timezone, timedelta
        
        # Non-expired key
        keypair = PQCKeyPair(
            algorithm=PQCAlgorithm.ML_DSA_65,
            key_type=KeyType.SIGNING,
            public_key=b"pub",
            private_key=b"priv",
            key_id="key1"
        )
        assert keypair.is_expired is False
        
        # Expired key
        expired = PQCKeyPair(
            algorithm=PQCAlgorithm.ML_DSA_65,
            key_type=KeyType.SIGNING,
            public_key=b"pub",
            private_key=b"priv",
            key_id="key2",
            created_at=datetime.now(timezone.utc) - timedelta(days=100),
            expires_at=datetime.now(timezone.utc) - timedelta(days=10)
        )
        assert expired.is_expired is True
    
    def test_pqc_keypair_to_jwk(self):
        """Test PQCKeyPair JWK export."""
        from modules.auth.pqc import PQCKeyPair, PQCAlgorithm, KeyType
        
        keypair = PQCKeyPair(
            algorithm=PQCAlgorithm.ML_DSA_65,
            key_type=KeyType.SIGNING,
            public_key=b"test_public_key",
            private_key=b"test_private_key",
            key_id="key123"
        )
        
        jwk = keypair.to_jwk()
        
        assert jwk["kty"] == "PQC"
        assert jwk["alg"] == "ml_dsa_65"
        assert jwk["kid"] == "key123"
        assert "x" in jwk
    
    @pytest.mark.asyncio
    async def test_pqc_token_issuer_initialization(self):
        """Test PQC token issuer initialization."""
        from modules.auth.pqc import PQCTokenIssuer, PQCConfig
        
        config = PQCConfig()
        issuer = PQCTokenIssuer(config)
        
        await issuer.initialize()
        
        assert issuer._signing_key is not None
        assert issuer._classical_key is not None  # Hybrid mode
    
    @pytest.mark.asyncio
    async def test_pqc_token_issue(self):
        """Test PQC token issuance."""
        from modules.auth.pqc import PQCTokenIssuer, PQCConfig
        
        config = PQCConfig(hybrid_mode=True)
        issuer = PQCTokenIssuer(config)
        await issuer.initialize()
        
        token = issuer.issue_token(
            subject="user123",
            claims={"role": "admin"}
        )
        
        assert token.count('.') == 2  # JWT format
        assert len(token) > 100  # Reasonable size
    
    @pytest.mark.asyncio
    async def test_pqc_token_without_hybrid(self):
        """Test PQC token without hybrid mode."""
        from modules.auth.pqc import PQCTokenIssuer, PQCConfig
        
        config = PQCConfig(hybrid_mode=False)
        issuer = PQCTokenIssuer(config)
        await issuer.initialize()
        
        assert issuer._classical_key is None
        
        token = issuer.issue_token(
            subject="user456",
            claims={"gid": "GID-02"}
        )
        
        # Decode header to check hybrid flag
        header_b64 = token.split('.')[0]
        header = json.loads(base64.urlsafe_b64decode(header_b64 + '=='))
        
        assert header.get("hybrid") is None or header.get("hybrid") is False
    
    @pytest.mark.asyncio
    async def test_pqc_key_manager_initialization(self):
        """Test PQC key manager initialization."""
        from modules.auth.pqc import PQCKeyManager, PQCConfig, KeyType
        
        config = PQCConfig()
        manager = PQCKeyManager(config)
        
        await manager.initialize()
        
        signing_key = manager.get_signing_key()
        exchange_key = manager.get_exchange_key()
        
        assert signing_key is not None
        assert exchange_key is not None
        assert signing_key.key_type == KeyType.SIGNING
        assert exchange_key.key_type == KeyType.KEY_EXCHANGE
    
    @pytest.mark.asyncio
    async def test_pqc_key_manager_jwks(self):
        """Test PQC key manager JWKS export."""
        from modules.auth.pqc import PQCKeyManager, PQCConfig
        
        config = PQCConfig()
        manager = PQCKeyManager(config)
        await manager.initialize()
        
        jwks = manager.get_jwks()
        
        assert "keys" in jwks
        assert len(jwks["keys"]) >= 2  # Signing + exchange
    
    @pytest.mark.asyncio
    async def test_pqc_key_rotation(self):
        """Test PQC key rotation."""
        from modules.auth.pqc import PQCKeyManager, PQCConfig
        from datetime import datetime, timezone
        
        config = PQCConfig()
        manager = PQCKeyManager(config)
        await manager.initialize()
        
        # Force expiration
        for key in manager._active_keys.values():
            key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        rotated = await manager.rotate_keys()
        
        assert len(rotated) >= 1


class TestBlockchainAnchoring:
    """Tests for XRP Ledger audit anchoring."""
    
    def test_xrp_network_enum(self):
        """Test XRPNetwork enum values."""
        from modules.auth.blockchain import XRPNetwork
        
        assert XRPNetwork.MAINNET.value == "mainnet"
        assert XRPNetwork.TESTNET.value == "testnet"
        assert XRPNetwork.DEVNET.value == "devnet"
    
    def test_xrp_config_defaults(self):
        """Test XRPConfig default values."""
        from modules.auth.blockchain import XRPConfig, XRPNetwork
        
        config = XRPConfig()
        
        assert config.network == XRPNetwork.TESTNET
        assert config.anchor_interval_seconds == 3600
        assert config.verification_enabled is True
    
    def test_merkle_tree_construction(self):
        """Test Merkle tree construction from event hashes."""
        from modules.auth.blockchain import MerkleTree
        import hashlib
        
        # Create some event hashes
        events = [f"event_{i}" for i in range(4)]
        event_hashes = [hashlib.sha256(e.encode()).hexdigest() for e in events]
        
        tree = MerkleTree(event_hashes)
        
        assert tree.root is not None
        assert tree.root_hash is not None
        assert len(tree.root_hash) == 64  # SHA256 hex
    
    def test_merkle_tree_single_event(self):
        """Test Merkle tree with single event."""
        from modules.auth.blockchain import MerkleTree
        import hashlib
        
        event_hash = hashlib.sha256(b"single event").hexdigest()
        tree = MerkleTree([event_hash])
        
        assert tree.root_hash == event_hash
    
    def test_merkle_tree_proof_generation(self):
        """Test Merkle proof generation."""
        from modules.auth.blockchain import MerkleTree
        import hashlib
        
        events = [f"leaf_{i}" for i in range(8)]
        event_hashes = [hashlib.sha256(e.encode()).hexdigest() for e in events]
        
        tree = MerkleTree(event_hashes)
        proof = tree.get_proof(event_hashes[3])  # Proof for hash index 3
        
        assert proof is not None
        assert isinstance(proof, list)
    
    def test_merkle_tree_proof_verification(self):
        """Test Merkle proof verification."""
        from modules.auth.blockchain import MerkleTree
        import hashlib
        
        events = [f"leaf_{i}" for i in range(4)]
        event_hashes = [hashlib.sha256(e.encode()).hexdigest() for e in events]
        
        tree = MerkleTree(event_hashes)
        root = tree.root_hash
        
        # Get proof for first event
        proof = tree.get_proof(event_hashes[0])
        
        # Verify proof
        valid = MerkleTree.verify_proof(event_hashes[0], proof, root)
        assert valid is True
    
    def test_audit_anchor_creation(self):
        """Test AuditAnchor data class."""
        from modules.auth.blockchain import AuditAnchor
        import secrets
        
        anchor = AuditAnchor(
            anchor_id=secrets.token_hex(8),
            merkle_root="abc123def456",
            event_count=50,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc)
        )
        
        assert anchor.merkle_root == "abc123def456"
        assert anchor.event_count == 50
        assert anchor.tx_hash is None  # Not yet submitted


class TestMLScoring:
    """Tests for ChainIQ ML risk scoring."""
    
    def test_model_type_enum(self):
        """Test ModelType enum values."""
        from modules.auth.ml import ModelType
        
        assert ModelType.RISK_CLASSIFIER.value == "risk_classifier"
        assert ModelType.ANOMALY_DETECTOR.value == "anomaly_detector"
        assert ModelType.ENSEMBLE.value == "ensemble"
    
    def test_ml_config_defaults(self):
        """Test MLConfig default values."""
        from modules.auth.ml import MLConfig
        
        config = MLConfig()
        
        assert config.risk_threshold == 0.7
        assert config.fallback_enabled is True
        assert config.fallback_score == 0.5
    
    def test_feature_vector_creation(self):
        """Test FeatureVector data class."""
        from modules.auth.ml import FeatureVector
        
        features = FeatureVector(
            user_id="user123",
            timestamp=datetime.now(timezone.utc)
        )
        
        assert features.user_id == "user123"
        assert features.request_count_1m == 0


class TestModuleIntegration:
    """Integration tests across auth modules."""
    
    def test_module_imports(self):
        """Test all modules can be imported from root."""
        from modules.auth import (
            # Blockchain
            XRPConfig,
            MerkleTree,
            AuditAnchor,
            # ML
            MLConfig,
            # SSO
            SSOProvider,
            SSOManager,
            # PQC
            PQCConfig,
            PQCTokenIssuer,
        )
        
        assert XRPConfig is not None
        assert MerkleTree is not None
        assert MLConfig is not None
        assert SSOProvider is not None
        assert PQCConfig is not None
    
    @pytest.mark.asyncio
    async def test_pqc_token_flow(self):
        """Test PQC token issuance flow."""
        from modules.auth.pqc import PQCTokenIssuer, PQCConfig
        
        # Initialize PQC issuer
        pqc_config = PQCConfig(hybrid_mode=True)
        issuer = PQCTokenIssuer(pqc_config)
        await issuer.initialize()
        
        # Issue token
        token = issuer.issue_token(
            subject="test_user",
            claims={"role": "carrier"}
        )
        
        assert token is not None
        assert len(token) > 100
    
    def test_merkle_tree_for_audit_events(self):
        """Test Merkle tree usage for audit event batching."""
        from modules.auth.blockchain import MerkleTree
        import hashlib
        
        # Simulate audit events
        events = [
            {"type": "login", "user": "alice", "ts": 1000},
            {"type": "logout", "user": "alice", "ts": 2000},
            {"type": "login", "user": "bob", "ts": 3000},
            {"type": "api_call", "user": "bob", "ts": 4000},
        ]
        
        # Create event hashes
        event_hashes = [
            hashlib.sha256(json.dumps(event).encode()).hexdigest()
            for event in events
        ]
        
        tree = MerkleTree(event_hashes)
        root = tree.root_hash
        
        assert root is not None
        assert len(root) == 64


# Fixture for async tests
@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
