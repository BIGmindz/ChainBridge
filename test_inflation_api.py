#!/usr/bin/env python3
"""
Test the World Bank Inflation API functionality in the Global Macro Module.
This script demonstrates fetching inflation data for Argentina, Venezuela, and Brazil
and generating a crypto hedge signal when any country exceeds 20% annual inflation.
"""

from modules.global_macro_module import GlobalMacroModule

def test_inflation_api():
    """Test the inflation API and hedge signal generation"""
    print("\n🌎 WORLD BANK INFLATION API TEST")
    print("===============================")
    
    # Initialize the Global Macro Module
    macro = GlobalMacroModule()
    
    # Target countries for inflation monitoring
    target_countries = ['ARG', 'VEN', 'BRA', 'TUR', 'UKR']
    print(f"Target countries: {', '.join(target_countries)}")
    
    # Fetch inflation data from World Bank API (or cached data)
    try:
        inflation_data = macro.fetch_world_bank_inflation(target_countries)
        
        print("\n📊 INFLATION RATES FROM WORLD BANK:")
        print("----------------------------------")
        for country, rate in inflation_data.items():
            status = "🚨 CRISIS" if rate > 20 else "Normal"
            print(f"{country}: {rate:.1f}% - {status}")
        
        # Identify countries with inflation exceeding 20%
        high_inflation_countries = [c for c, r in inflation_data.items() if r > 20]
        
        print("\n📈 CRYPTO HEDGE SIGNAL ANALYSIS:")
        print("------------------------------")
        
        if high_inflation_countries:
            print(f"⚠️ HIGH INFLATION DETECTED in {', '.join(high_inflation_countries)}")
            
            # Calculate average inflation for high-inflation countries
            avg_crisis_inflation = sum(inflation_data[c] for c in high_inflation_countries) / len(high_inflation_countries)
            
            if avg_crisis_inflation > 100:
                hedge_signal = "STRONG_BUY"
                reason = "Hyperinflation crisis detected"
            else:
                hedge_signal = "BUY"
                reason = "High inflation exceeding 20% threshold"
                
            print(f"🔄 CRYPTO HEDGE SIGNAL: {hedge_signal}")
            print(f"📝 REASON: {reason}")
            
            # Calculate expected correlation with BTC
            print("\n🔗 EXPECTED BTC CORRELATION:")
            for country in high_inflation_countries:
                rate = inflation_data[country]
                # Simple model: higher inflation = higher correlation with crypto as hedge
                corr = min(0.3 + (rate / 200), 0.95)
                print(f"  {country} ({rate:.1f}%): {corr:.2f}")
        else:
            print("✓ No high inflation detected in target countries")
            print("🔄 CRYPTO HEDGE SIGNAL: NEUTRAL")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_inflation_api()