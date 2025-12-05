"""Token registry + factory."""

from __future__ import annotations

from typing import Dict, Type

from .at02 import AT02Token
from .base_token import BaseToken, TokenValidationError
from .cct01 import CCT01Token
from .dt01 import DT01Token
from .it01 import IT01Token
from .mt01 import MT01Token
from .pt01 import PT01Token
from .qt01 import QT01Token
from .st01 import ST01Token


class TokenRegistry:
    """In-memory registry mapping token types to their implementations."""

    _registry: Dict[str, Type[BaseToken]] = {}

    @classmethod
    def register(cls, token_cls: Type[BaseToken]) -> None:
        cls._registry[token_cls.TOKEN_TYPE] = token_cls

    @classmethod
    def get(cls, token_type: str) -> Type[BaseToken]:
        try:
            return cls._registry[token_type]
        except KeyError as exc:
            raise TokenValidationError(f"Unknown token_type: {token_type}") from exc


for token_cls in (
    ST01Token,
    QT01Token,
    MT01Token,
    AT02Token,
    IT01Token,
    PT01Token,
    DT01Token,
    CCT01Token,
):
    TokenRegistry.register(token_cls)


def create_token(token_type: str, **kwargs) -> BaseToken:
    """Factory helper."""
    token_cls = TokenRegistry.get(token_type)
    return token_cls(**kwargs)
