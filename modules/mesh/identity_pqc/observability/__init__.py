#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      OBSERVABILITY - LOGGING                                 ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Structured logging utilities with key material redaction.

INV-SEC-P819-001: Private key material NEVER appears in logs.
"""

import logging
import re
from typing import Any, Dict, Optional

# Patterns that might indicate key material
KEY_PATTERNS = [
    (r'[A-Za-z0-9+/]{40,}={0,2}', 'BASE64_REDACTED'),  # Base64 encoded data
    (r'[0-9a-fA-F]{64,}', 'HEX_REDACTED'),  # Long hex strings
]


class SecureFormatter(logging.Formatter):
    """
    Logging formatter that redacts potential key material.
    
    This formatter scans log messages for patterns that might
    indicate cryptographic key material and redacts them.
    """
    
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        redact_keys: bool = True,
    ):
        super().__init__(fmt, datefmt)
        self.redact_keys = redact_keys
        self._patterns = [(re.compile(p), r) for p, r in KEY_PATTERNS]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional key redaction."""
        message = super().format(record)
        
        if self.redact_keys:
            message = self._redact_keys(message)
        
        return message
    
    def _redact_keys(self, message: str) -> str:
        """Redact potential key material from message."""
        for pattern, replacement in self._patterns:
            message = pattern.sub(f'[{replacement}]', message)
        return message


class IdentityLogger:
    """
    Secure logger for identity operations.
    
    Provides structured logging with automatic key redaction.
    """
    
    def __init__(
        self,
        name: str = "identity_pqc",
        level: int = logging.INFO,
        redact_keys: bool = True,
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.redact_keys = redact_keys
    
    def _safe_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safe copy of context with keys redacted."""
        safe = {}
        for key, value in context.items():
            if key in ('private_key', 'secret_key', 'private_key_bytes', 'sk'):
                safe[key] = '[REDACTED]'
            elif key in ('public_key', 'pk', 'signature', 'sig'):
                # Truncate for readability
                if isinstance(value, bytes):
                    safe[key] = f"<{len(value)} bytes>"
                elif isinstance(value, str) and len(value) > 32:
                    safe[key] = f"{value[:16]}...[{len(value)} chars]"
                else:
                    safe[key] = value
            else:
                safe[key] = value
        return safe
    
    def info(self, message: str, **context):
        """Log info message with context."""
        safe_context = self._safe_context(context)
        self.logger.info(f"{message} | {safe_context}" if context else message)
    
    def debug(self, message: str, **context):
        """Log debug message with context."""
        safe_context = self._safe_context(context)
        self.logger.debug(f"{message} | {safe_context}" if context else message)
    
    def warning(self, message: str, **context):
        """Log warning message with context."""
        safe_context = self._safe_context(context)
        self.logger.warning(f"{message} | {safe_context}" if context else message)
    
    def error(self, message: str, **context):
        """Log error message with context."""
        safe_context = self._safe_context(context)
        self.logger.error(f"{message} | {safe_context}" if context else message)
    
    def keygen_start(self, algorithm: str):
        """Log key generation start."""
        self.info("Key generation started", algorithm=algorithm)
    
    def keygen_complete(self, algorithm: str, public_key_size: int):
        """Log key generation completion."""
        self.info(
            "Key generation complete",
            algorithm=algorithm,
            public_key_size=public_key_size,
        )
    
    def sign_start(self, message_size: int, mode: str):
        """Log signing operation start."""
        self.debug("Signing started", message_size=message_size, mode=mode)
    
    def sign_complete(self, signature_size: int, mode: str):
        """Log signing operation completion."""
        self.debug("Signing complete", signature_size=signature_size, mode=mode)
    
    def verify_start(self, message_size: int, signature_size: int):
        """Log verification start."""
        self.debug(
            "Verification started",
            message_size=message_size,
            signature_size=signature_size,
        )
    
    def verify_complete(self, result: bool):
        """Log verification completion."""
        self.debug("Verification complete", valid=result)
    
    def identity_loaded(self, node_id: str, node_name: str):
        """Log identity load."""
        # Truncate node_id for safety
        self.info(
            "Identity loaded",
            node_id=f"{node_id[:16]}..." if len(node_id) > 16 else node_id,
            node_name=node_name,
        )
    
    def identity_saved(self, path: str, include_private: bool):
        """Log identity save."""
        self.info(
            "Identity saved",
            path=path,
            include_private_keys=include_private,
        )


# Default logger instance
_default_logger: Optional[IdentityLogger] = None


def get_logger() -> IdentityLogger:
    """Get the default identity logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = IdentityLogger()
    return _default_logger


def configure_logging(
    level: int = logging.INFO,
    redact_keys: bool = True,
    handler: Optional[logging.Handler] = None,
):
    """
    Configure identity logging.
    
    Args:
        level: Logging level
        redact_keys: Whether to redact potential key material
        handler: Custom handler (default: StreamHandler)
    """
    global _default_logger
    
    logger = logging.getLogger("identity_pqc")
    logger.setLevel(level)
    
    if handler is None:
        handler = logging.StreamHandler()
    
    formatter = SecureFormatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        redact_keys=redact_keys,
    )
    handler.setFormatter(formatter)
    
    logger.handlers = [handler]
    
    _default_logger = IdentityLogger(level=level, redact_keys=redact_keys)
