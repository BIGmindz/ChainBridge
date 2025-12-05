"""Serialization helpers for tokens."""

from __future__ import annotations

from typing import Any, Dict

from .base_token import BaseToken
from .registry import TokenRegistry


def serialize(token: BaseToken) -> Dict[str, Any]:
    """Serialize a token into a DB-friendly JSON payload."""
    return token.to_dict()


def deserialize(payload: Dict[str, Any]) -> BaseToken:
    """Rehydrate a token from its serialized representation."""
    token_type = payload.get("type")
    token_cls = TokenRegistry.get(token_type)
    return token_cls.from_dict(payload)


__all__ = ["serialize", "deserialize"]
