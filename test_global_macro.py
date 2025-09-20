"""
TEST SCRIPT FOR GLOBAL MACRO MODULE
Tests the global macro signal module's ability to generate trading signals
based on worldwide crypto adoption, regulations, and macro stress indicators
"""

import json
import os
import sys
from datetime import datetime

# Add parent directory to path for importing modules
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from modules.global_macro_module import GlobalMacroModule


def main():
    print("=" * 60)
    print("GLOBAL MACRO SIGNAL MODULE TEST")
    print("=" * 60)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    # Initialize the GlobalMacroModule
    print("Initializing Global Macro Module...")
    macro_module = GlobalMacroModule()

    # Process empty data to get signals
    print("\nGenerating global macro signals...")
    result = macro_module.process({})

    # Print summary
    print("\n🌍 GLOBAL MACRO SIGNAL SUMMARY")
    print("=" * 40)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence'] * 100:.1f}%")
    print(f"Strength: {result['strength']:.2f}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"Lead Time: {result.get('lead_time_days', 'N/A')} days ahead")
    print(f"Correlation with technical: {result.get('correlation', 'N/A')}")

    # Print key insight
    print("\n💡 KEY INSIGHT:")
    print(f"{result.get('key_insight', 'No key insights available')}")

    # Print detailed component breakdown
    print("\n📊 COMPONENT BREAKDOWN:")
    components = result.get("components", {})

    for name, component in components.items():
        print(f"\n  {name.upper()}")
        print(f"  {'=' * (len(name) + 2)}")
        print(f"  - Interpretation: {component['data'].get('interpretation', 'N/A')}")
        print(f"  - Strength: {component['data'].get('strength', 0):.2f}")
        print(f"  - Confidence: {component['data'].get('confidence', 0) * 100:.1f}%")
        print(f"  - Weight: {component.get('weight', 0) * 100:.1f}%")

        # Print additional metrics if available
        for key, value in component["data"].items():
            if key not in ["strength", "confidence", "interpretation"]:
                if isinstance(value, (str, int, float)):
                    print(f"  - {key}: {value}")
                elif isinstance(value, list) and len(value) < 10:
                    print(f"  - {key}: {', '.join(str(v) for v in value)}")

    # Save result to file for reference
    with open("global_macro_test_result.json", "w") as f:
        # Convert datetime objects to strings for JSON serialization
        json_result = {k: (str(v) if isinstance(v, datetime) else v) for k, v in result.items()}
        json.dump(json_result, f, indent=2)

    print("\n" + "-" * 60)
    print("Results saved to global_macro_test_result.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
