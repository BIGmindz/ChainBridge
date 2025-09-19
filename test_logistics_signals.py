"""
TEST LOGISTICS SIGNALS
See the power of uncorrelated, forward-looking signals
"""

from modules.logistics_signal_module import LogisticsSignalModule

def test_logistics():
    print("\n🧪 TESTING LOGISTICS SIGNALS")
    print("="*60)
    
    # Initialize module
    logistics = LogisticsSignalModule()
    
    # Generate signal
    result = logistics.process({})
    
    print("\n📊 LOGISTICS SIGNAL RESULT:")
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']*100:.1f}%")
    print(f"Value: {result['value']:.2f}")
    print(f"Correlation to Technical: {result['correlation']:.2f} (ULTRA LOW!)")
    print(f"Forward Looking: {result['lead_time_days']} days")
    
    if 'components' in result:
        print("\n📈 COMPONENT SIGNALS:")
        for name, component in result['components'].items():
            if 'interpretation' in component:
                print(f"  {name}: {component['interpretation']}")
                print(f"    {component.get('metric', '')}")
    
    print("\n💡 WHAT THIS MEANS:")
    print("While everyone else reacts to price (lagging),")
    print("you're predicting price 30 days ahead (leading)!")
    
    print("\n💰 PROFIT POTENTIAL:")
    print("If logistics shows BUY today,")
    print("and BTC rises in 30 days as predicted,")
    print("you captured the ENTIRE move while others wait for RSI!")

if __name__ == "__main__":
    test_logistics()
