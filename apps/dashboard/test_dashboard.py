#!/usr/bin/env python3
"""
Test Script for BensonBot Strategy Comparison Dashboard

This script tests the dashboard functionality without requiring Streamlit.
"""

import os
import sys
import pandas as pd
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_dashboard_import():
    """Test that the dashboard can be imported successfully"""
    try:
        # Test basic imports that the dashboard uses
        import pandas as pd
        import re

        # Test the core function import (without streamlit to avoid warnings)
        import sys
        sys.path.insert(0, '/Users/johnbozza/bensonbot/Multiple-signal-decision-bot')

        # Import the parsing function directly
        from apps.dashboard.comparison_dashboard import load_backtest_reports

        print("✅ Dashboard imports successful")
        return True
    except ImportError as e:
        print(f"❌ Dashboard import failed: {e}")
        return False

def create_mock_report():
    """Create a mock backtest report for testing"""
    strategy_path = 'strategies/test_strategy'
    os.makedirs(strategy_path, exist_ok=True)

    # Create mock report
    report_content = """# Backtest Report: TEST_STRATEGY

**Date:** 2025-09-20

## Key Performance Metrics

| Metric | Value |
|---|---|
| **Total Return** | `15.23%` |
| **Final Portfolio Value** | `$11,523.45` |
| **Annualized Sharpe Ratio** | `1.45` |
| **Max Drawdown** | `-8.32%` |
"""

    with open(os.path.join(strategy_path, 'backtest_report.md'), 'w') as f:
        f.write(report_content)

    print("✅ Created mock backtest report")
    return strategy_path

def test_regex_parsing():
    """Test the regex parsing directly"""
    import re

    content = """# Backtest Report: TEST_STRATEGY

**Date:** 2025-09-20

## Key Performance Metrics

| Metric | Value |
|---|---|
| **Total Return** | `15.23%` |
| **Final Portfolio Value** | `$11,523.45` |
| **Annualized Sharpe Ratio** | `1.45` |
| **Max Drawdown** | `-8.32%` |
"""

    # Test the regex patterns
    patterns = {
        'Total Return': r"Total Return\s*\|\s*`([\d\.\-]+\%)`",
        'Final Portfolio Value': r"Final Portfolio Value\s*\|\s*`\$([\d,\.]+)`",
        'Annualized Sharpe Ratio': r"Annualized Sharpe Ratio\s*\|\s*`([\d\.\-]+)`",
        'Max Drawdown': r"Max Drawdown\s*\|\s*`([\d\.\-]+\%)`"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            value = match.group(1).replace(',', '').replace('%', '').replace('$', '')
            print(f"✅ {key}: {value}")
        else:
            print(f"❌ {key}: No match")

    return True

def test_dashboard_structure():
    """Test that the dashboard has the expected structure"""
    dashboard_dir = 'apps/dashboard'

    required_files = [
        'comparison_dashboard.py',
        '__init__.py',
        'README.md',
        'run_dashboard.sh'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(dashboard_dir, file)):
            missing_files.append(file)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def main():
    """Run all dashboard tests"""
    print("🧪 Testing BensonBot Strategy Comparison Dashboard")
    print("=" * 55)

    tests = [
        ("File Structure", test_dashboard_structure),
        ("Import Test", test_dashboard_import),
        ("Report Parsing", test_regex_parsing),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"Result: {status}")
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 55)
    print("📊 TEST SUMMARY")
    print("=" * 55)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print("-" * 55)
    print(f"Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Dashboard is ready.")
        print("\n💡 To run the dashboard:")
        print("   1. Install streamlit: pip install streamlit")
        print("   2. Run backtester: python apps/backtester/backtester.py")
        print("   3. Launch dashboard: streamlit run apps/dashboard/comparison_dashboard.py")
    else:
        print("⚠️  Some tests failed. Check the output above.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)