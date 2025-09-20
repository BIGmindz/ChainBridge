"""
REGION-SPECIFIC CRYPTO TRADING MODULE
Maps your macro/adoption signals to EXACT cryptocurrencies
This is SURGICAL PRECISION trading - not spray and pray
"""

from datetime import datetime
from typing import Dict, List

import ccxt


class RegionSpecificCryptoModule:
    """
    Maps regional signals to specific cryptocurrencies
    Your SECRET WEAPON: Trade the RIGHT crypto for the RIGHT region
    """

    def __init__(self):
        self.name = "region_crypto_mapper"
        self.exchange = ccxt.kraken()

        # CRITICAL: Region → Crypto mapping based on REAL USE CASES
        self.region_crypto_map = {
            "BRAZIL": {
                "primary": ["TRX/USD", "SOL/USD", "XRP/USD"],
                "secondary": ["LINK/USD", "POL/USD"],
                "signals": ["stablecoin_adoption", "pix_integration", "inflation"],
                "weight": 0.25,
                "reasoning": "Stablecoin remittances + Nubank/Polygon + inflation hedge",
            },
            "INDIA": {
                "primary": ["POL/USD", "BTC/USD", "ETH/USD"],
                "secondary": ["USDT/USD", "USDC/USD"],
                "signals": ["adoption_growth", "fiu_compliance", "dev_activity"],
                "weight": 0.30,
                "reasoning": "#1 adoption + Polygon roots + regulatory normalization",
            },
            "JAPAN": {
                "primary": ["XRP/USD", "LINK/USD"],
                "secondary": ["BTC/USD", "ETH/USD"],
                "signals": ["sbi_ripple", "tokenization", "yen_stablecoins"],
                "weight": 0.20,
                "reasoning": "SBI-Ripple corridor + Chainlink RWA infrastructure",
            },
            "CENTRAL_AMERICA": {
                "primary": ["BTC/USD", "TRX/USD"],
                "secondary": ["SOL/USD", "XLM/USD"],
                "signals": ["el_salvador_btc", "remittance_flows"],
                "weight": 0.15,
                "reasoning": "Bitcoin legal tender + remittance corridors",
            },
            "LOGISTICS": {
                "primary": ["VET/USD", "XDC/USD"],
                "secondary": [],
                "signals": ["port_congestion", "supply_chain", "trade_finance"],
                "weight": 0.10,
                "reasoning": "Direct supply chain exposure",
            },
        }

        # Current portfolio allocations
        self.current_allocations = {}
        self.signal_history = []

    def process_regional_signals(self, macro_signals: Dict) -> Dict:
        """
        Process macro signals and map to specific cryptos
        THIS IS WHERE THE MAGIC HAPPENS
        """

        recommendations = {}
        total_confidence = 0

        for region, config in self.region_crypto_map.items():
            # Check if we have signals for this region
            region_confidence = self._analyze_region(region, macro_signals)

            if region_confidence > 0.5:  # Threshold for action
                # Get crypto recommendations
                cryptos = self._select_cryptos(region, region_confidence)

                for crypto in cryptos:
                    if crypto not in recommendations:
                        recommendations[crypto] = {
                            "action": "BUY",
                            "confidence": 0,
                            "regions": [],
                            "reasoning": [],
                        }

                    # Aggregate confidence
                    recommendations[crypto]["confidence"] += (
                        region_confidence * config["weight"]
                    )
                    recommendations[crypto]["regions"].append(region)
                    recommendations[crypto]["reasoning"].append(config["reasoning"])

                total_confidence += region_confidence * config["weight"]

        # Generate final trading signals
        trading_signals = self._generate_trading_signals(recommendations)

        return {
            "timestamp": datetime.now().isoformat(),
            "recommendations": trading_signals,
            "total_confidence": total_confidence,
            "active_regions": [
                r
                for r, c in self.region_crypto_map.items()
                if self._analyze_region(r, macro_signals) > 0.5
            ],
            "module": self.name,
        }

    def _analyze_region(self, region: str, macro_signals: Dict) -> float:
        """
        Analyze regional signals and return confidence
        """
        confidence = 0.0

        if region == "BRAZIL":
            # Check Brazil-specific signals
            if macro_signals.get("inflation_ARG", 0) > 100:  # Argentina spillover
                confidence += 0.3
            if macro_signals.get("stablecoin_growth_LATAM", 0) > 0.5:
                confidence += 0.4
            if macro_signals.get("brazil_vasp_positive", False):
                confidence += 0.3

        elif region == "INDIA":
            # India adoption signals
            if macro_signals.get("adoption_rank_IND", 0) == 1:
                confidence += 0.4
            if macro_signals.get("fiu_registrations", 0) > 2:
                confidence += 0.3
            if macro_signals.get("india_adoption_growth", 0) > 0.4:
                confidence += 0.3

        elif region == "JAPAN":
            # Japan institutional signals
            if macro_signals.get("sbi_ripple_news", False):
                confidence += 0.5
            if macro_signals.get("japan_tokenization", False):
                confidence += 0.3
            if macro_signals.get("yen_stablecoin_progress", False):
                confidence += 0.2

        elif region == "CENTRAL_AMERICA":
            # El Salvador and remittances
            if macro_signals.get("el_salvador_btc_news", False):
                confidence += 0.4
            if macro_signals.get("remittance_growth_CA", 0) > 0.1:
                confidence += 0.3
            if macro_signals.get("btc_reserve_news", False):
                confidence += 0.3

        elif region == "LOGISTICS":
            # Supply chain signals
            if macro_signals.get("port_congestion", 0) > 1.3:
                confidence += 0.4
            if macro_signals.get("supply_chain_stress", 0) > 1:
                confidence += 0.3
            if macro_signals.get("trade_finance_digitization", False):
                confidence += 0.3

        return min(confidence, 1.0)  # Cap at 1.0

    def _select_cryptos(self, region: str, confidence: float) -> List[str]:
        """
        Select which cryptos to trade based on region and confidence
        """
        config = self.region_crypto_map[region]

        if confidence > 0.7:
            # High confidence: trade primary targets
            return config["primary"]
        elif confidence > 0.5:
            # Medium confidence: trade first primary only
            return config["primary"][:1] if config["primary"] else []
        else:
            return []

    def _generate_trading_signals(self, recommendations: Dict) -> List[Dict]:
        """
        Generate actionable trading signals with position sizes
        """
        signals = []

        # Sort by confidence
        sorted_recs = sorted(
            recommendations.items(), key=lambda x: x[1]["confidence"], reverse=True
        )

        for crypto, data in sorted_recs[:5]:  # Top 5 only
            if data["confidence"] > 0.3:
                # Calculate position size based on confidence
                position_size = self._calculate_position_size(data["confidence"])

                signal = {
                    "symbol": crypto,
                    "action": data["action"],
                    "confidence": data["confidence"],
                    "position_size_pct": position_size,
                    "regions": data["regions"],
                    "reasoning": " + ".join(data["reasoning"][:2]),  # Top 2 reasons
                    "expected_holding_period": self._estimate_holding_period(
                        data["regions"]
                    ),
                }

                signals.append(signal)

        return signals

    def _calculate_position_size(self, confidence: float) -> float:
        """
        Kelly Criterion-inspired position sizing
        """
        base_size = 0.05  # 5% base

        if confidence > 0.8:
            return base_size * 2.0  # 10%
        elif confidence > 0.6:
            return base_size * 1.5  # 7.5%
        elif confidence > 0.4:
            return base_size * 1.0  # 5%
        else:
            return base_size * 0.5  # 2.5%

    def _estimate_holding_period(self, regions: List[str]) -> str:
        """
        Estimate optimal holding period based on signal type
        """
        if "LOGISTICS" in regions:
            return "30-45 days"  # Logistics are slow moving
        elif "JAPAN" in regions:
            return "14-30 days"  # Institutional flows
        elif "INDIA" in regions or "BRAZIL" in regions:
            return "7-14 days"  # Adoption momentum
        else:
            return "3-7 days"  # News-driven

    def get_portfolio_recommendations(self, current_prices: Dict) -> Dict:
        """
        Get complete portfolio allocation recommendations
        """
        recommendations = {
            "timestamp": datetime.now().isoformat(),
            "allocations": {},
            "total_positions": 0,
            "risk_level": "MODERATE",
        }

        # Brazil exposure (25% max)
        if self._check_brazil_signals():
            recommendations["allocations"]["TRX/USD"] = 0.10
            recommendations["allocations"]["SOL/USD"] = 0.08
            recommendations["allocations"]["XRP/USD"] = 0.07

        # India exposure (30% max)
        if self._check_india_signals():
            recommendations["allocations"]["POL/USD"] = 0.15
            recommendations["allocations"]["BTC/USD"] = 0.10
            recommendations["allocations"]["ETH/USD"] = 0.05

        # Japan exposure (20% max)
        if self._check_japan_signals():
            recommendations["allocations"]["XRP/USD"] = 0.10  # Can overlap
            recommendations["allocations"]["LINK/USD"] = 0.10

        # Logistics exposure (10% max)
        if self._check_logistics_signals():
            recommendations["allocations"]["VET/USD"] = 0.05
            recommendations["allocations"]["XDC/USD"] = 0.05

        # Calculate total
        recommendations["total_positions"] = len(recommendations["allocations"])
        total_allocation = sum(recommendations["allocations"].values())

        # Ensure we don't exceed 100%
        if total_allocation > 1.0:
            # Normalize
            for symbol in recommendations["allocations"]:
                recommendations["allocations"][symbol] /= total_allocation

        return recommendations

    def _check_brazil_signals(self) -> bool:
        """Check if Brazil signals are active"""
        # In production: check actual signal values
        return True  # Placeholder

    def _check_india_signals(self) -> bool:
        """Check if India signals are active"""
        return True  # Placeholder

    def _check_japan_signals(self) -> bool:
        """Check if Japan signals are active"""
        return True  # Placeholder

    def _check_logistics_signals(self) -> bool:
        """Check if logistics signals are active"""
        return False  # Placeholder - only on high congestion

    def process(self, data):
        """
        Process data for the multi-signal bot integration
        This method is required by the multi_signal_bot.py

        Args:
            data: Dict containing symbol and macro_signals

        Returns:
            Dict with signal and additional information
        """
        if not data or "symbol" not in data or "macro_signals" not in data:
            return {
                "signal": "HOLD",
                "strength": 0,
                "confidence": 0,
                "message": "Insufficient data for region-specific mapping",
            }

        # Process the regional signals using the existing method
        result = self.process_regional_signals(data["macro_signals"])

        # Find if this symbol is specifically recommended
        symbol = data["symbol"]
        symbol_base = symbol.split("/")[0]

        # Check recommendations for this specific symbol
        signal = "HOLD"
        strength = 0
        confidence = 0
        message = "No regional signals for this asset"

        for rec in result.get("recommendations", []):
            if symbol == rec["symbol"] or symbol_base in rec["symbol"]:
                signal = rec["action"]
                strength = rec["confidence"]
                confidence = rec["confidence"]
                message = rec["reasoning"]
                break

        return {
            "signal": signal,
            "strength": strength,
            "confidence": confidence,
            "message": message,
            "active_regions": result.get("active_regions", []),
            "total_confidence": result.get("total_confidence", 0),
        }


# Integration function
def integrate_region_crypto_mapper():
    """
    Integrate region-specific crypto mapping with your bot
    """
    print(
        """
    ╔════════════════════════════════════════════════════════════════╗
    ║   REGION-SPECIFIC CRYPTO MAPPER ACTIVATED                     ║
    ║                                                                ║
    ║   Brazil → TRX, SOL, XRP (stablecoins)                       ║
    ║   India → POL, BTC, ETH (adoption)                           ║
    ║   Japan → XRP, LINK (institutional)                          ║
    ║   Central America → BTC, TRX (remittances)                   ║
    ║   Logistics → VET, XDC (supply chain)                        ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    )

    # Initialize mapper
    mapper = RegionSpecificCryptoModule()

    # Simulate macro signals
    test_signals = {
        "inflation_ARG": 142,
        "stablecoin_growth_LATAM": 0.63,
        "adoption_rank_IND": 1,
        "sbi_ripple_news": True,
        "port_congestion": 1.4,
        "el_salvador_btc_news": False,
    }

    # Get recommendations
    result = mapper.process_regional_signals(test_signals)

    print("\n🎯 TRADING RECOMMENDATIONS:")
    print("=" * 60)

    for rec in result["recommendations"]:
        print(f"\n📊 {rec['symbol']}")
        print(f"   Action: {rec['action']}")
        print(f"   Confidence: {rec['confidence'] * 100:.1f}%")
        print(f"   Position Size: {rec['position_size_pct'] * 100:.1f}% of portfolio")
        print(f"   Regions: {', '.join(rec['regions'])}")
        print(f"   Reasoning: {rec['reasoning']}")
        print(f"   Hold Period: {rec['expected_holding_period']}")

    print(f"\n✅ Active Regions: {', '.join(result['active_regions'])}")
    print(f"📈 Total Confidence: {result['total_confidence'] * 100:.1f}%")

    return mapper


if __name__ == "__main__":
    integrate_region_crypto_mapper()
