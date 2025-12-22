"""ChainIQ Risk Replay Tests.

Validates the determinism guarantee from A10 Lock:
Given same inputs + model_version → byte-for-byte identical output.

════════════════════════════════════════════════════════════════════════════════
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
GID-10 — MAGGIE (ML & APPLIED AI)
PAC-MAGGIE-A10-RISK-MODEL-CANONICALIZATION-LOCK-01
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
════════════════════════════════════════════════════════════════════════════════

I. EXECUTING AGENT (MANDATORY)

EXECUTING AGENT: MAGGIE
GID: GID-10
EXECUTING COLOR: 🩷 PINK — ML & Applied AI Lane

⸻

II. TEST COVERAGE

- Replay produces identical scores
- Replay produces identical reason codes
- Replay produces identical factors
- Hash verification passes
- Model version mismatch detected

⸻

III. PROHIBITED ACTIONS

- Non-deterministic test behavior
- Skipping replay verification

⸻
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

# Import from canonical model spec
from app.models.canonical_model_spec import (
    RiskBand,
    RiskFactor,
    RiskInput,
    RiskOutput,
    ReplayResult,
    derive_risk_band,
    verify_replay,
)

# Import the actual risk engine for integration tests
from app.risk.engine import MODEL_VERSION, compute_risk_score
from app.risk.schemas import (
    CarrierProfile,
    LaneProfile,
    ShipmentFeatures,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_risk_input() -> RiskInput:
    """Create a sample risk input for testing."""
    return RiskInput(
        shipment_id="TEST-SHIP-001",
        value_usd=150000.0,
        is_hazmat=False,
        is_temp_control=True,
        expected_transit_days=12,
        carrier_id="CARR-001",
        carrier_incident_rate_90d=0.08,
        carrier_tenure_days=500,
        origin="USLA",
        destination="CNSH",
        lane_risk_index=0.65,
        border_crossing_count=2,
        recent_delay_events=1,
        iot_alert_count=0,
    )


@pytest.fixture
def sample_risk_output(sample_risk_input: RiskInput) -> RiskOutput:
    """Create a sample risk output for testing."""
    return RiskOutput(
        risk_score=72.0,
        risk_band=RiskBand.HIGH,
        confidence=0.85,
        reason_codes=["High Value (>$100k)", "Temp Control Risk", "Border Crossings (+10)"],
        top_factors=[
            RiskFactor(
                feature="lane_risk_index",
                contribution=39.0,
                direction="INCREASES_RISK",
                human_label="High lane risk index (0.65)",
            ),
            RiskFactor(
                feature="value_usd",
                contribution=15.0,
                direction="INCREASES_RISK",
                human_label="High cargo value ($150,000)",
            ),
        ],
        model_version="chainiq_v1_maggie",
        data_version="chainiq_data_v1_2025",
        assessed_at=datetime.now(timezone.utc).isoformat(),
        evaluation_id=str(uuid.uuid4()),
        input_hash=sample_risk_input.compute_hash(),
    )


# =============================================================================
# REPLAY DETERMINISM TESTS
# =============================================================================

class TestRiskReplayDeterminism:
    """Tests for risk replay determinism guarantee."""

    def test_identical_inputs_produce_identical_hash(self, sample_risk_input: RiskInput):
        """Same inputs should produce identical hash."""
        hash1 = sample_risk_input.compute_hash()
        hash2 = sample_risk_input.compute_hash()
        
        assert hash1 == hash2, "Input hash must be deterministic"
        assert len(hash1) == 64, "Hash should be SHA-256 (64 hex chars)"

    def test_different_inputs_produce_different_hash(self, sample_risk_input: RiskInput):
        """Different inputs should produce different hash."""
        input2 = RiskInput(
            shipment_id="TEST-SHIP-002",
            value_usd=200000.0,
            carrier_id="CARR-002",
        )
        
        hash1 = sample_risk_input.compute_hash()
        hash2 = input2.compute_hash()
        
        assert hash1 != hash2, "Different inputs must produce different hashes"

    def test_output_hash_is_deterministic(self, sample_risk_output: RiskOutput):
        """Output hash should be deterministic."""
        hash1 = sample_risk_output.compute_hash()
        hash2 = sample_risk_output.compute_hash()
        
        assert hash1 == hash2, "Output hash must be deterministic"

    def test_replay_verification_passes_for_identical_output(
        self, 
        sample_risk_input: RiskInput,
        sample_risk_output: RiskOutput,
    ):
        """Replay with identical output should verify successfully."""
        # Simulate replay producing identical output
        replay_output = RiskOutput(
            risk_score=sample_risk_output.risk_score,
            risk_band=sample_risk_output.risk_band,
            confidence=sample_risk_output.confidence,
            reason_codes=sample_risk_output.reason_codes.copy(),
            top_factors=sample_risk_output.top_factors.copy(),
            model_version=sample_risk_output.model_version,
            data_version=sample_risk_output.data_version,
            assessed_at=datetime.now(timezone.utc).isoformat(),  # Different timestamp OK
            evaluation_id=str(uuid.uuid4()),  # Different eval ID OK
            input_hash=sample_risk_input.compute_hash(),
        )
        
        result = verify_replay(sample_risk_input, sample_risk_output, replay_output)
        
        assert result.verified, "Replay should verify for identical outputs"
        assert result.outputs_match, "Output hashes should match"
        assert result.model_version_match, "Model versions should match"

    def test_replay_verification_fails_for_different_score(
        self,
        sample_risk_input: RiskInput,
        sample_risk_output: RiskOutput,
    ):
        """Replay with different score should fail verification."""
        replay_output = RiskOutput(
            risk_score=75.0,  # Different score!
            risk_band=RiskBand.HIGH,
            confidence=0.85,
            reason_codes=sample_risk_output.reason_codes.copy(),
            top_factors=sample_risk_output.top_factors.copy(),
            model_version=sample_risk_output.model_version,
            data_version=sample_risk_output.data_version,
            assessed_at=datetime.now(timezone.utc).isoformat(),
            evaluation_id=str(uuid.uuid4()),
            input_hash=sample_risk_input.compute_hash(),
        )
        
        result = verify_replay(sample_risk_input, sample_risk_output, replay_output)
        
        assert not result.outputs_match, "Different scores should not match"
        assert not result.verified, "Replay should fail verification"

    def test_replay_verification_fails_for_different_model_version(
        self,
        sample_risk_input: RiskInput,
        sample_risk_output: RiskOutput,
    ):
        """Replay with different model version should fail verification."""
        replay_output = RiskOutput(
            risk_score=sample_risk_output.risk_score,
            risk_band=sample_risk_output.risk_band,
            confidence=sample_risk_output.confidence,
            reason_codes=sample_risk_output.reason_codes.copy(),
            top_factors=sample_risk_output.top_factors.copy(),
            model_version="chainiq_v2_test",  # Different version!
            data_version=sample_risk_output.data_version,
            assessed_at=datetime.now(timezone.utc).isoformat(),
            evaluation_id=str(uuid.uuid4()),
            input_hash=sample_risk_input.compute_hash(),
        )
        
        result = verify_replay(sample_risk_input, sample_risk_output, replay_output)
        
        assert not result.model_version_match, "Model versions should not match"


# =============================================================================
# ENGINE REPLAY TESTS (Integration)
# =============================================================================

class TestEngineReplayDeterminism:
    """Integration tests for actual risk engine replay."""

    def test_engine_produces_identical_scores_for_identical_inputs(self):
        """Risk engine must produce identical scores for identical inputs."""
        shipment = ShipmentFeatures(
            value_usd=100000.0,
            is_hazmat=False,
            is_temp_control=True,
            expected_transit_days=8,
            iot_alert_count=0,
            recent_delay_events=1,
        )
        carrier = CarrierProfile(
            carrier_id="TEST-CARR",
            incident_rate_90d=0.03,
            tenure_days=400,
            on_time_rate=0.95,
        )
        lane = LaneProfile(
            origin="USLA",
            destination="CNSH",
            lane_risk_index=0.5,
            border_crossing_count=1,
        )
        
        # Score twice
        result1 = compute_risk_score(shipment, carrier, lane)
        result2 = compute_risk_score(shipment, carrier, lane)
        
        assert result1.score == result2.score, "Scores must be identical"
        assert result1.band == result2.band, "Bands must be identical"
        assert result1.reasons == result2.reasons, "Reasons must be identical"
        assert result1.model_version == result2.model_version, "Model versions must match"

    def test_engine_model_version_is_immutable(self):
        """Model version should be a constant."""
        assert MODEL_VERSION == "chainiq_v1_maggie", "Model version must be locked"
        
        # Score should always include version
        shipment = ShipmentFeatures(
            value_usd=50000.0,
            is_hazmat=False,
            is_temp_control=False,
            expected_transit_days=5,
            iot_alert_count=0,
            recent_delay_events=0,
        )
        carrier = CarrierProfile(
            carrier_id="TEST",
            incident_rate_90d=0.02,
            tenure_days=365,
            on_time_rate=0.98,
        )
        lane = LaneProfile(
            origin="A",
            destination="B",
            lane_risk_index=0.3,
            border_crossing_count=0,
        )
        
        result = compute_risk_score(shipment, carrier, lane)
        assert result.model_version == MODEL_VERSION

    def test_engine_is_deterministic_across_many_runs(self):
        """Run engine 100 times and verify all outputs identical."""
        shipment = ShipmentFeatures(
            value_usd=250000.0,
            is_hazmat=True,
            is_temp_control=True,
            expected_transit_days=15,
            iot_alert_count=2,
            recent_delay_events=3,
        )
        carrier = CarrierProfile(
            carrier_id="HIGH-RISK",
            incident_rate_90d=0.08,
            tenure_days=100,
            on_time_rate=0.85,
        )
        lane = LaneProfile(
            origin="HIGH",
            destination="RISK",
            lane_risk_index=0.9,
            border_crossing_count=3,
        )
        
        # Run 100 times
        results = [compute_risk_score(shipment, carrier, lane) for _ in range(100)]
        
        # All scores must be identical
        scores = [r.score for r in results]
        assert len(set(scores)) == 1, f"All scores must be identical, got {set(scores)}"
        
        # All bands must be identical
        bands = [r.band for r in results]
        assert len(set(bands)) == 1, "All bands must be identical"
        
        # All reasons must be identical
        reasons_sets = [tuple(r.reasons) for r in results]
        assert len(set(reasons_sets)) == 1, "All reasons must be identical"


# =============================================================================
# AUDIT TRAIL TESTS
# =============================================================================

class TestAuditTrailSupport:
    """Tests for audit trail and replay support."""

    def test_input_serialization_is_reversible(self, sample_risk_input: RiskInput):
        """Input should serialize and deserialize identically."""
        data = sample_risk_input.to_dict()
        
        # Verify all expected fields present
        assert "shipment_id" in data
        assert "value_usd" in data
        assert "carrier_incident_rate_90d" in data
        assert "lane_risk_index" in data
        
        # Verify JSON serializable
        json_str = json.dumps(data, sort_keys=True)
        parsed = json.loads(json_str)
        
        assert parsed == data, "JSON roundtrip must preserve data"

    def test_output_serialization_is_reversible(self, sample_risk_output: RiskOutput):
        """Output should serialize and deserialize identically."""
        data = sample_risk_output.to_dict()
        
        # Verify all expected fields present
        assert "risk_score" in data
        assert "risk_band" in data
        assert "reason_codes" in data
        assert "top_factors" in data
        assert "model_version" in data
        
        # Verify JSON serializable
        json_str = json.dumps(data, sort_keys=True)
        parsed = json.loads(json_str)
        
        assert parsed == data, "JSON roundtrip must preserve data"

    def test_replay_result_contains_all_verification_info(
        self,
        sample_risk_input: RiskInput,
        sample_risk_output: RiskOutput,
    ):
        """Replay result should contain complete verification info."""
        replay_output = RiskOutput(
            risk_score=sample_risk_output.risk_score,
            risk_band=sample_risk_output.risk_band,
            confidence=sample_risk_output.confidence,
            reason_codes=sample_risk_output.reason_codes.copy(),
            top_factors=sample_risk_output.top_factors.copy(),
            model_version=sample_risk_output.model_version,
            data_version=sample_risk_output.data_version,
            assessed_at=datetime.now(timezone.utc).isoformat(),
            evaluation_id=str(uuid.uuid4()),
            input_hash=sample_risk_input.compute_hash(),
        )
        
        result = verify_replay(sample_risk_input, sample_risk_output, replay_output)
        
        # All verification fields populated
        assert result.original_output_hash, "Original hash required"
        assert result.replay_output_hash, "Replay hash required"
        assert result.replay_timestamp, "Timestamp required"
        assert isinstance(result.inputs_match, bool)
        assert isinstance(result.outputs_match, bool)
        assert isinstance(result.model_version_match, bool)
        assert isinstance(result.verified, bool)


# END — Maggie (GID-10) — 🩷 PINK
