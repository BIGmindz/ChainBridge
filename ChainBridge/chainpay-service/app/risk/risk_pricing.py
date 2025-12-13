from dataclasses import dataclass
from enum import Enum


class RiskTier(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskProfile:
    coefficient: float
    tier: RiskTier
    fee_modifier: float
    settlement_delay_days: int
    collateral_ratio: float


class RiskPricingEngine:
    """
    Engine for calculating Fusion-Adjusted Risk Pricing.
    """

    def __init__(self):
        # Configuration for risk tiers
        self.tier_config = {
            RiskTier.LOW: {"max_coeff": 0.2, "fee_modifier": 1.0, "settlement_delay": 0, "collateral_ratio": 1.0},
            RiskTier.MEDIUM: {"max_coeff": 0.5, "fee_modifier": 1.2, "settlement_delay": 1, "collateral_ratio": 1.1},
            RiskTier.HIGH: {"max_coeff": 0.8, "fee_modifier": 1.5, "settlement_delay": 3, "collateral_ratio": 1.25},
            RiskTier.CRITICAL: {
                "max_coeff": float("inf"),
                "fee_modifier": 2.0,
                "settlement_delay": 7,  # Manual review implies delay
                "collateral_ratio": 1.5,
            },
        }

    def calculate_corridor_risk(self, base_risk: float, geopolitical_factor: float, seasonal_volatility: float) -> float:
        """
        Calculates the Corridor Risk Coefficient (Cr).
        Formula: Cr = Br * (1 + Gf + Sv)
        """
        return base_risk * (1 + geopolitical_factor + seasonal_volatility)

    def determine_risk_tier(self, coefficient: float) -> RiskTier:
        """
        Determines the Risk Tier based on the coefficient.
        """
        if coefficient <= self.tier_config[RiskTier.LOW]["max_coeff"]:
            return RiskTier.LOW
        elif coefficient <= self.tier_config[RiskTier.MEDIUM]["max_coeff"]:
            return RiskTier.MEDIUM
        elif coefficient <= self.tier_config[RiskTier.HIGH]["max_coeff"]:
            return RiskTier.HIGH
        else:
            return RiskTier.CRITICAL

    def get_risk_profile(self, base_risk: float, geopolitical_factor: float, seasonal_volatility: float) -> RiskProfile:
        """
        Generates a full Risk Profile for a given set of parameters.
        """
        coefficient = self.calculate_corridor_risk(base_risk, geopolitical_factor, seasonal_volatility)
        tier = self.determine_risk_tier(coefficient)
        config = self.tier_config[tier]

        return RiskProfile(
            coefficient=coefficient,
            tier=tier,
            fee_modifier=config["fee_modifier"],
            settlement_delay_days=config["settlement_delay"],
            collateral_ratio=config["collateral_ratio"],
        )

    def calculate_fusion_adjusted_apy(self, base_apy: float, risk_coefficient: float, drift_factor: float) -> float:
        """
        Calculates the Fusion-Adjusted APY.
        Formula: APYf = APYbase * (1 + Cr * Df)
        """
        return base_apy * (1 + risk_coefficient * drift_factor)
