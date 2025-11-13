"""
QUICK TEST SCRIPT FOR REGION MODULE
Run this to verify everything is working
"""

from modules.region_specific_crypto_module import RegionSpecificCryptoModule


def test_region_module() -> None:
    print("Testing Region-Specific Crypto Module...")

    # Initialize
    mapper = RegionSpecificCryptoModule()

    # Test signals showing different scenarios
    test_scenarios = [
        {
            "name": "Brazil Inflation Crisis",
            "signals": {
                "inflation_ARG": 200,
                "stablecoin_growth_LATAM": 0.8,
                "brazil_vasp_positive": True,
                # Adding additional signals to meet threshold
                "adoption_rank_IND": 0,  # Not India
                "sbi_ripple_news": False,
                "port_congestion": 0.9,
            },
        },
        {
            "name": "India Adoption Surge",
            "signals": {
                "adoption_rank_IND": 1,
                "india_adoption_growth": 0.6,
                "fiu_registrations": 5,
                # Adding additional signals to meet threshold
                "inflation_ARG": 50,  # Lower Argentina inflation
                "stablecoin_growth_LATAM": 0.2,
                "sbi_ripple_news": False,
            },
        },
        {
            "name": "Japan Institutional Entry",
            "signals": {
                "sbi_ripple_news": True,
                "japan_tokenization": True,
                "yen_stablecoin_progress": True,
                # Adding additional signals to meet threshold
                "adoption_rank_IND": 2,  # Not top adoption
                "inflation_ARG": 40,
                "port_congestion": 0.8,
            },
        },
    ]

    for scenario in test_scenarios:
        print(f"\n📊 Testing: {scenario['name']}")
        print("-" * 40)

        result = mapper.process_regional_signals(scenario["signals"])

        if result["recommendations"]:
            top_rec = result["recommendations"][0]
            print(f"Top Pick: {top_rec['symbol']}")
            print(f"Confidence: {top_rec['confidence'] * 100:.0f}%")
            print(f"Position Size: {top_rec['position_size_pct'] * 100:.0f}%")
        else:
            print("No strong signals")


if __name__ == "__main__":
    test_region_module()
