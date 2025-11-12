"""
Enterprise Secrets Management
Supports HashiCorp Vault, AWS Secrets Manager, and secure environment variables
with automatic rotation tracking and audit logging
"""

import os
import logging
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SecretMetadata:
    """Metadata about a secret"""

    name: str
    last_accessed: datetime
    last_rotated: Optional[datetime]
    access_count: int
    version: int


class SecretsProvider(ABC):
    """Abstract base class for secrets providers"""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret value"""
        pass

    @abstractmethod
    def rotate_secret(self, key: str, new_value: str) -> bool:
        """Rotate a secret to a new value"""
        pass

    @abstractmethod
    def list_secrets(self) -> list[str]:
        """List available secret keys"""
        pass


class VaultSecretsProvider(SecretsProvider):
    """HashiCorp Vault secrets provider"""

    def __init__(self, vault_addr: str, role_id: Optional[str] = None, token: Optional[str] = None):
        self.vault_addr = vault_addr
        self.role_id = role_id
        self.token = token
        self.client = None
        self._initialize()

    def _initialize(self):
        """Initialize Vault client"""
        try:
            import hvac

            self.client = hvac.Client(url=self.vault_addr)

            if self.token:
                self.client.token = self.token
            elif self.role_id:
                secret_id = os.getenv("VAULT_SECRET_ID")
                if not secret_id:
                    raise ValueError("VAULT_SECRET_ID required for AppRole auth")

                response = self.client.auth.approle.login(role_id=self.role_id, secret_id=secret_id)
                self.client.token = response["auth"]["client_token"]
            else:
                raise ValueError("Either token or role_id must be provided")

            logger.info(f"Vault client initialized: {self.vault_addr}")

        except ImportError:
            logger.error("hvac library not installed. Install with: pip install hvac")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Vault: {e}")
            raise

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve secret from Vault"""
        try:
            secret_path = f"trading/data/{key}"
            response = self.client.secrets.kv.v2.read_secret_version(path=secret_path)
            return response["data"]["data"].get("value")
        except Exception as e:
            logger.error(f"Failed to get secret {key} from Vault: {e}")
            return None

    def rotate_secret(self, key: str, new_value: str) -> bool:
        """Rotate secret in Vault"""
        try:
            secret_path = f"trading/data/{key}"
            self.client.secrets.kv.v2.create_or_update_secret(
                path=secret_path, secret={"value": new_value, "rotated_at": datetime.now().isoformat()}
            )
            logger.info(f"Rotated secret: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to rotate secret {key}: {e}")
            return False

    def list_secrets(self) -> list[str]:
        """List all secrets"""
        try:
            response = self.client.secrets.kv.v2.list_secrets(path="trading/data")
            return response["data"]["keys"]
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


class AWSSecretsProvider(SecretsProvider):
    """AWS Secrets Manager provider"""

    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = region_name
        self.client = None
        self._initialize()

    def _initialize(self):
        """Initialize AWS Secrets Manager client"""
        try:
            import boto3

            self.client = boto3.client("secretsmanager", region_name=self.region_name)
            logger.info(f"AWS Secrets Manager initialized: {self.region_name}")

        except ImportError:
            logger.error("boto3 library not installed. Install with: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS Secrets Manager: {e}")
            raise

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve secret from AWS"""
        try:
            response = self.client.get_secret_value(SecretId=f"trading/{key}")
            return response["SecretString"]
        except Exception as e:
            logger.error(f"Failed to get secret {key} from AWS: {e}")
            return None

    def rotate_secret(self, key: str, new_value: str) -> bool:
        """Rotate secret in AWS"""
        try:
            self.client.put_secret_value(SecretId=f"trading/{key}", SecretString=new_value)
            logger.info(f"Rotated secret: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to rotate secret {key}: {e}")
            return False

    def list_secrets(self) -> list[str]:
        """List all secrets"""
        try:
            response = self.client.list_secrets()
            return [s["Name"] for s in response["Secrets"] if s["Name"].startswith("trading/")]
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


class EnvironmentSecretsProvider(SecretsProvider):
    """Environment variables secrets provider (fallback)"""

    def __init__(self):
        logger.warning("Using environment variables for secrets (not recommended for production)")

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from environment"""
        return os.getenv(key)

    def rotate_secret(self, key: str, new_value: str) -> bool:
        """Environment secrets cannot be rotated programmatically"""
        logger.error("Cannot rotate environment secrets programmatically")
        return False

    def list_secrets(self) -> list[str]:
        """List all environment variables"""
        return list(os.environ.keys())


class SecretsManager:
    """
    Enterprise secrets manager with:
    - Multi-provider support (Vault, AWS, Environment)
    - Audit logging
    - Automatic rotation tracking
    - Secret access monitoring
    """

    def __init__(self, provider: Optional[SecretsProvider] = None, audit_log_path: Optional[Path] = None):
        self.provider = provider or self._auto_detect_provider()
        self.audit_log_path = audit_log_path or Path("logs/audit/secrets_audit.jsonl")
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_cache: Dict[str, SecretMetadata] = {}

    def _auto_detect_provider(self) -> SecretsProvider:
        """Auto-detect best available secrets provider"""

        # Try Vault first
        vault_addr = os.getenv("VAULT_ADDR")
        if vault_addr:
            try:
                vault_token = os.getenv("VAULT_TOKEN")
                vault_role = os.getenv("VAULT_ROLE_ID")
                return VaultSecretsProvider(vault_addr, role_id=vault_role, token=vault_token)
            except Exception as e:
                logger.warning(f"Failed to initialize Vault: {e}")

        # Try AWS Secrets Manager
        if os.getenv("AWS_REGION"):
            try:
                return AWSSecretsProvider(region_name=os.getenv("AWS_REGION"))
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Secrets Manager: {e}")

        # Fallback to environment variables
        logger.warning("Using environment variables for secrets (INSECURE)")
        return EnvironmentSecretsProvider()

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret with audit logging and metadata tracking

        Args:
            key: Secret key
            default: Default value if secret not found

        Returns:
            Secret value or default
        """
        try:
            value = self.provider.get_secret(key)

            if value is None:
                value = default

            # Update metadata
            self._update_metadata(key)

            # Audit log (without exposing the value)
            self._audit_log("get_secret", key, success=value is not None)

            return value

        except Exception as e:
            logger.error(f"Failed to get secret {key}: {e}")
            self._audit_log("get_secret", key, success=False, error=str(e))
            return default

    def get_exchange_credentials(self, exchange: str) -> Dict[str, str]:
        """Get exchange API credentials"""
        api_key = self.get_secret(f"{exchange.upper()}_API_KEY") or self.get_secret("API_KEY")
        api_secret = self.get_secret(f"{exchange.upper()}_SECRET") or self.get_secret("API_SECRET")

        if not api_key or not api_secret:
            raise ValueError(f"Missing credentials for exchange: {exchange}")

        return {"apiKey": api_key, "secret": api_secret}

    def rotate_secret(self, key: str, new_value: str) -> bool:
        """Rotate secret with audit logging"""
        try:
            success = self.provider.rotate_secret(key, new_value)

            if success:
                # Update metadata
                if key in self.metadata_cache:
                    self.metadata_cache[key].last_rotated = datetime.now()
                    self.metadata_cache[key].version += 1

            self._audit_log("rotate_secret", key, success=success)
            return success

        except Exception as e:
            logger.error(f"Failed to rotate secret {key}: {e}")
            self._audit_log("rotate_secret", key, success=False, error=str(e))
            return False

    def check_rotation_needed(self, key: str, max_age_days: int = 30) -> bool:
        """Check if secret needs rotation based on age"""
        if key not in self.metadata_cache:
            return False

        metadata = self.metadata_cache[key]
        if metadata.last_rotated is None:
            return True

        age = datetime.now() - metadata.last_rotated
        return age > timedelta(days=max_age_days)

    def get_secret_metadata(self, key: str) -> Optional[SecretMetadata]:
        """Get metadata about a secret"""
        return self.metadata_cache.get(key)

    def _update_metadata(self, key: str):
        """Update secret access metadata"""
        if key not in self.metadata_cache:
            self.metadata_cache[key] = SecretMetadata(name=key, last_accessed=datetime.now(), last_rotated=None, access_count=1, version=1)
        else:
            metadata = self.metadata_cache[key]
            metadata.last_accessed = datetime.now()
            metadata.access_count += 1

    def _audit_log(self, action: str, key: str, success: bool, error: Optional[str] = None):
        """Write to audit log"""
        try:
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "key": key,
                "key_hash": hashlib.sha256(key.encode()).hexdigest()[:16],
                "success": success,
                "error": error,
                "user": os.getenv("USER", "unknown"),
            }

            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps(audit_entry) + "\n")

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")


# Global secrets manager instance
_global_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create global secrets manager"""
    global _global_secrets_manager

    if _global_secrets_manager is None:
        _global_secrets_manager = SecretsManager()

    return _global_secrets_manager


def init_secrets_manager(provider: Optional[SecretsProvider] = None) -> SecretsManager:
    """Initialize global secrets manager with specific provider"""
    global _global_secrets_manager
    _global_secrets_manager = SecretsManager(provider=provider)
    return _global_secrets_manager
