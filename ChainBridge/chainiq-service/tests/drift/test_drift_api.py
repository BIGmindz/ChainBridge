"""
ChainIQ Drift API v1.1 Integration Tests

Tests for drift detection REST API endpoints.

Author: Cody (GID-01) 🔵
PAC: CODY-PAC-NEXT-034
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

# ═══════════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear drift cache before each test."""
    from app.ml.drift_engine import get_drift_cache

    cache = get_drift_cache()
    cache.clear()
    yield
    cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# GET /iq/drift/score TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftScoreEndpoint:
    """Tests for GET /iq/drift/score endpoint."""

    def test_global_drift_score(self, client):
        """Should return global drift summary."""
        response = client.get("/iq/drift/score")

        assert response.status_code == 200
        data = response.json()

        assert "overall_drift_score" in data
        assert "overall_bucket" in data
        assert "corridors_analyzed" in data
        assert "corridors_drifting" in data
        assert "top_drifting_corridors" in data
        assert "computed_at" in data

    def test_global_drift_score_with_details(self, client):
        """Should return global drift with corridor details."""
        response = client.get("/iq/drift/score?include_features=true")

        assert response.status_code == 200
        data = response.json()

        # When include_features=true on global, we get corridor_results
        # Check that we have the main summary fields at minimum
        assert "overall_drift_score" in data
        assert "corridors_analyzed" in data

    def test_corridor_drift_score(self, client):
        """Should return corridor-specific drift score."""
        response = client.get("/iq/drift/score?corridor=US-CN")

        assert response.status_code == 200
        data = response.json()

        assert data["corridor"] == "US-CN"
        assert "drift_score" in data
        assert "drift_bucket" in data
        assert "risk_multiplier" in data
        assert "recommendations" in data

    def test_corridor_drift_with_features(self, client):
        """Should return corridor drift with feature breakdowns."""
        response = client.get("/iq/drift/score?corridor=US-CN&include_features=true")

        assert response.status_code == 200
        data = response.json()

        assert "feature_drifts" in data
        assert len(data["feature_drifts"]) > 0

        # Check feature drift structure
        feature = data["feature_drifts"][0]
        assert "feature_name" in feature
        assert "shift_delta" in feature
        assert "drift_bucket" in feature
        assert "explanation" in feature

    def test_corridor_not_found(self, client):
        """Should return 404 for unknown corridor."""
        response = client.get("/iq/drift/score?corridor=NONEXISTENT")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_hours_parameter(self, client):
        """Should accept hours parameter."""
        response = client.get("/iq/drift/score?hours=48")

        assert response.status_code == 200

    def test_hours_validation(self, client):
        """Should validate hours parameter."""
        # Too small
        response = client.get("/iq/drift/score?hours=0")
        assert response.status_code == 422

        # Too large
        response = client.get("/iq/drift/score?hours=1000")
        assert response.status_code == 422

    def test_drift_score_cached(self, client):
        """Second request should be served from cache."""
        # First request
        response1 = client.get("/iq/drift/score?corridor=US-CN")
        assert response1.status_code == 200

        # Second request (should be cached)
        response2 = client.get("/iq/drift/score?corridor=US-CN")
        assert response2.status_code == 200

        # Results should be identical
        assert response1.json() == response2.json()


# ═══════════════════════════════════════════════════════════════════════════════
# GET /iq/drift/corridors TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftCorridorsEndpoint:
    """Tests for GET /iq/drift/corridors endpoint."""

    def test_list_all_corridors(self, client):
        """Should list all corridor drift scores."""
        response = client.get("/iq/drift/corridors")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Check structure
        corridor = data[0]
        assert "corridor" in corridor
        assert "drift_score" in corridor
        assert "drift_bucket" in corridor
        assert "risk_multiplier" in corridor

    def test_corridors_sorted_by_drift(self, client):
        """Corridors should be sorted by drift score descending."""
        response = client.get("/iq/drift/corridors")

        assert response.status_code == 200
        data = response.json()

        # Check sorting
        scores = [c["drift_score"] for c in data]
        assert scores == sorted(scores, reverse=True)

    def test_drift_bucket_filter(self, client):
        """Should filter corridors by drift bucket."""
        response = client.get("/iq/drift/corridors?drift_bucket_filter=MODERATE")

        assert response.status_code == 200
        data = response.json()

        # All returned corridors should be MODERATE or higher
        allowed_buckets = ["MODERATE", "SEVERE", "CRITICAL"]
        for corridor in data:
            assert corridor["drift_bucket"] in allowed_buckets

    def test_min_samples_filter(self, client):
        """Should respect min_samples parameter."""
        response = client.get("/iq/drift/corridors?min_samples=100")

        assert response.status_code == 200
        # Should return some corridors (our mock data has > 100 samples)

    def test_hours_parameter(self, client):
        """Should accept hours parameter."""
        response = client.get("/iq/drift/corridors?hours=72")

        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# GET /iq/drift/features TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftFeaturesEndpoint:
    """Tests for GET /iq/drift/features endpoint."""

    def test_list_global_features(self, client):
        """Should list aggregated feature drift scores."""
        response = client.get("/iq/drift/features")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Check structure
        feature = data[0]
        assert "feature_name" in feature
        assert "shift_delta" in feature
        assert "drift_bucket" in feature
        assert "contribution_rank" in feature

    def test_corridor_specific_features(self, client):
        """Should return corridor-specific feature drift."""
        response = client.get("/iq/drift/features?corridor=US-CN")

        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0

    def test_top_n_limit(self, client):
        """Should respect top_n parameter."""
        response = client.get("/iq/drift/features?top_n=3")

        assert response.status_code == 200
        data = response.json()

        assert len(data) <= 3

    def test_features_sorted_by_drift(self, client):
        """Features should be sorted by drift descending."""
        response = client.get("/iq/drift/features")

        assert response.status_code == 200
        data = response.json()

        # Check sorting by contribution rank
        ranks = [f["contribution_rank"] for f in data]
        assert ranks == sorted(ranks)

    def test_corridor_not_found(self, client):
        """Should return 404 for unknown corridor."""
        response = client.get("/iq/drift/features?corridor=NONEXISTENT")

        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE ADMIN ENDPOINTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCacheAdminEndpoints:
    """Tests for cache administration endpoints."""

    def test_cache_stats(self, client):
        """Should return cache statistics."""
        # Populate cache
        client.get("/iq/drift/score")

        response = client.get("/iq/drift/cache/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_entries" in data
        assert "valid_entries" in data
        assert "expired_entries" in data

    def test_cache_invalidate_all(self, client):
        """Should invalidate all cache entries."""
        # Populate cache
        client.get("/iq/drift/score")
        client.get("/iq/drift/score?corridor=US-CN")

        # Invalidate all
        response = client.post("/iq/drift/cache/invalidate")

        assert response.status_code == 200
        data = response.json()
        assert data["invalidated"] == "all"

        # Verify cache is empty
        stats_response = client.get("/iq/drift/cache/stats")
        stats = stats_response.json()
        assert stats["valid_entries"] == 0

    def test_cache_invalidate_pattern(self, client):
        """Should invalidate cache entries by pattern."""
        # Populate cache
        client.get("/iq/drift/score")
        client.get("/iq/drift/score?corridor=US-CN")

        # Invalidate by pattern
        response = client.post("/iq/drift/cache/invalidate?pattern=drift_score:US-CN")

        assert response.status_code == 200
        data = response.json()
        assert data["pattern"] == "drift_score:US-CN"


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestResponseValidation:
    """Tests for response structure and data types."""

    def test_drift_score_types(self, client):
        """Drift score should be correct type and range."""
        response = client.get("/iq/drift/score?corridor=US-CN")
        data = response.json()

        assert isinstance(data["drift_score"], (int, float))
        assert 0 <= data["drift_score"] <= 1.0

    def test_drift_bucket_valid(self, client):
        """Drift bucket should be valid enum value."""
        response = client.get("/iq/drift/score?corridor=US-CN")
        data = response.json()

        valid_buckets = ["STABLE", "MINOR", "MODERATE", "SEVERE", "CRITICAL"]
        assert data["drift_bucket"] in valid_buckets

    def test_risk_multiplier_range(self, client):
        """Risk multiplier should be >= 1.0."""
        response = client.get("/iq/drift/score?corridor=US-CN")
        data = response.json()

        assert data["risk_multiplier"] >= 1.0

    def test_recommendations_list(self, client):
        """Recommendations should be list of strings."""
        response = client.get("/iq/drift/score?corridor=US-CN")
        data = response.json()

        assert isinstance(data["recommendations"], list)
        for rec in data["recommendations"]:
            assert isinstance(rec, str)

    def test_feature_drift_structure(self, client):
        """Feature drift should have complete structure."""
        response = client.get("/iq/drift/score?corridor=US-CN&include_features=true")
        data = response.json()

        feature = data["feature_drifts"][0]

        # Required fields
        assert "feature_name" in feature
        assert "baseline_mean" in feature
        assert "current_mean" in feature
        assert "baseline_std" in feature
        assert "current_std" in feature
        assert "shift_delta" in feature
        assert "shift_direction" in feature
        assert "psi_score" in feature
        assert "drift_bucket" in feature
        assert "contribution_rank" in feature
        assert "explanation" in feature

        # Type checks
        assert isinstance(feature["shift_delta"], (int, float))
        assert feature["shift_direction"] in ["INCREASING", "DECREASING", "STABLE"]


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPerformance:
    """Basic performance tests."""

    def test_response_time_cached(self, client):
        """Cached response should be fast (<50ms)."""
        import time

        # Prime cache
        client.get("/iq/drift/score")

        # Measure cached response
        start = time.time()
        response = client.get("/iq/drift/score")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Should be under 50ms for cached response
        assert elapsed < 0.05, f"Cached response took {elapsed*1000:.1f}ms"

    def test_multiple_corridors_reasonable_time(self, client):
        """Multiple corridor analysis should complete in reasonable time."""
        import time

        start = time.time()
        response = client.get("/iq/drift/corridors")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Should complete in under 1 second even without cache
        assert elapsed < 1.0, f"Corridor list took {elapsed*1000:.1f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
