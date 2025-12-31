"""
GIE Proof Providers Package

Concrete proof provider implementations.
"""

from core.gie.proof.providers.space_and_time import (
    SpaceAndTimeProofProvider,
    SpaceAndTimeConfig,
    get_space_and_time_provider,
    reset_space_and_time_provider,
)

__all__ = [
    "SpaceAndTimeProofProvider",
    "SpaceAndTimeConfig",
    "get_space_and_time_provider",
    "reset_space_and_time_provider",
]
