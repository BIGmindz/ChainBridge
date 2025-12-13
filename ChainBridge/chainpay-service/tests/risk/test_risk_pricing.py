import pytest

from app.risk.risk_pricing import RiskPricingEngine, RiskTier


@pytest.fixture
def risk_engine():
    return RiskPricingEngine()


def test_calculate_corridor_risk(risk_engine):
    # Scenario A: Stable Route
    # Br=0.05, Gf=0.0, Sv=0.05
    # Cr = 0.05 * (1 + 0.0 + 0.05) = 0.0525
    cr = risk_engine.calculate_corridor_risk(0.05, 0.0, 0.05)
    assert cr == pytest.approx(0.0525)

    # Scenario B: Volatile Route
    # Br=0.3, Gf=0.4, Sv=0.1
    # Cr = 0.3 * (1 + 0.4 + 0.1) = 0.45
    cr = risk_engine.calculate_corridor_risk(0.3, 0.4, 0.1)
    assert cr == pytest.approx(0.45)


def test_determine_risk_tier(risk_engine):
    assert risk_engine.determine_risk_tier(0.1) == RiskTier.LOW
    assert risk_engine.determine_risk_tier(0.2) == RiskTier.LOW
    assert risk_engine.determine_risk_tier(0.21) == RiskTier.MEDIUM
    assert risk_engine.determine_risk_tier(0.5) == RiskTier.MEDIUM
    assert risk_engine.determine_risk_tier(0.51) == RiskTier.HIGH
    assert risk_engine.determine_risk_tier(0.8) == RiskTier.HIGH
    assert risk_engine.determine_risk_tier(0.81) == RiskTier.CRITICAL


def test_get_risk_profile(risk_engine):
    # Scenario A: Stable Route -> Low Tier
    profile = risk_engine.get_risk_profile(0.05, 0.0, 0.05)
    assert profile.tier == RiskTier.LOW
    assert profile.fee_modifier == 1.0
    assert profile.settlement_delay_days == 0
    assert profile.collateral_ratio == 1.0

    # Scenario B: Volatile Route -> Medium Tier
    profile = risk_engine.get_risk_profile(0.3, 0.4, 0.1)
    assert profile.tier == RiskTier.MEDIUM
    assert profile.fee_modifier == 1.2
    assert profile.settlement_delay_days == 1
    assert profile.collateral_ratio == 1.1


def test_calculate_fusion_adjusted_apy(risk_engine):
    # APYbase=5%, Cr=0.45, Df=1.0
    # APYf = 5 * (1 + 0.45 * 1.0) = 7.25
    apy = risk_engine.calculate_fusion_adjusted_apy(5.0, 0.45, 1.0)
    assert apy == pytest.approx(7.25)
