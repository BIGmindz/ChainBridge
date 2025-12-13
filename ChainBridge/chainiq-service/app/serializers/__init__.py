"""
ChainIQ Serializers Package

Pydantic models for API request/response serialization.
"""

from .drift_explain import (
    CacheStatsResponse,
    CorridorDriftDetailResponse,
    CorridorDriftResponse,
    CorridorListRequest,
    DriftScoreRequest,
    FeatureDriftResponse,
    FeatureListRequest,
    GlobalDriftDetailResponse,
    GlobalDriftSummaryResponse,
    serialize_corridor_drift,
    serialize_feature_drift,
    serialize_global_drift,
)

__all__ = [
    # Feature-level
    "FeatureDriftResponse",
    # Corridor-level
    "CorridorDriftResponse",
    "CorridorDriftDetailResponse",
    # Global
    "GlobalDriftSummaryResponse",
    "GlobalDriftDetailResponse",
    # Requests
    "DriftScoreRequest",
    "CorridorListRequest",
    "FeatureListRequest",
    # Cache
    "CacheStatsResponse",
    # Serializers
    "serialize_feature_drift",
    "serialize_corridor_drift",
    "serialize_global_drift",
]
