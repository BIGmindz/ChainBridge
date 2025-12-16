"""Lightweight auth stubs for OCC endpoints.

These stubs let the OCC APIs run in tests without integrating
with the real auth stack. Replace with real authentication when
available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Principal:
    """Represents the authenticated caller."""

    subject: str
    roles: List[str]


async def get_current_principal() -> Principal:
    """FastAPI dependency stub that returns a system principal.

    Tests rely on OCC endpoints being callable without real auth.
    """

    return Principal(subject="system", roles=["system"])
