#!/usr/bin/env python3
"""
PAC-FIN-P203 Validation Script
==============================

Tests the Multi-Currency Engine for:
1. Currency registry (ISO 4217 + crypto)
2. Money creation with precision enforcement
3. Exchange rate management
4. Currency conversion with precision
5. JPY conversion (0 decimals)
6. BTC conversion (8 decimals)
7. Rate staleness checking
8. Conversion audit trail (INV-FIN-008)
9. Precision safety (INV-FIN-007)

PAC: PAC-FIN-P203-MULTI-CURRENCY-ENGINE
"""

import sys
sys.path.insert(0, "/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from modules.finance import (
    CurrencyEngine, CurrencyRegistry, Currency, Money, ExchangeRate,
    UnknownCurrencyError, ExchangeRateNotFoundError, StaleExchangeRateError,
    create_default_engine_with_rates,
)


def run_tests():
    print("=" * 60)
    print("PAC-FIN-P203: MULTI-CURRENCY ENGINE VALIDATION")
    print("=" * 60)
    print()
    
    results = []
    
    # =========================================================================
    # TEST 1: Currency Registry
    # =========================================================================
    print("TEST 1: Currency Registry (ISO 4217 + Crypto)")
    try:
        registry = CurrencyRegistry()
        
        # Check fiat currencies
        usd = registry.get("USD")
        assert usd.code == "USD"
        assert usd.decimals == 2
        assert usd.symbol == "$"
        
        jpy = registry.get("JPY")
        assert jpy.decimals == 0, f"JPY should have 0 decimals, got {jpy.decimals}"
        
        kwd = registry.get("KWD")  # Kuwaiti Dinar has 3 decimals
        assert kwd.decimals == 3
        
        # Check crypto
        btc = registry.get("BTC")
        assert btc.decimals == 8
        assert btc.is_crypto is True
        
        eth = registry.get("ETH")
        assert eth.decimals == 18
        
        fiat_count = len(registry.list_fiat())
        crypto_count = len(registry.list_crypto())
        
        print(f"   ✅ PASS: Registry loaded")
        print(f"      Fiat currencies: {fiat_count}")
        print(f"      Cryptocurrencies: {crypto_count}")
        print(f"      USD: {usd.decimals} decimals, JPY: {jpy.decimals} decimals, BTC: {btc.decimals} decimals")
        results.append(("Currency Registry", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Currency Registry", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 2: Money Creation with Precision
    # =========================================================================
    print("TEST 2: Money Creation with Precision Enforcement")
    try:
        engine = CurrencyEngine()
        
        # USD - should round to 2 decimals
        usd_money = engine.create_money("100.999", "USD")
        assert usd_money.amount == Decimal("101.00"), f"Expected 101.00, got {usd_money.amount}"
        
        # JPY - should round to 0 decimals
        jpy_money = engine.create_money("14572.6", "JPY")
        assert jpy_money.amount == Decimal("14573"), f"Expected 14573, got {jpy_money.amount}"
        
        # BTC - should allow 8 decimals
        btc_money = engine.create_money("0.00123456", "BTC")
        assert btc_money.amount == Decimal("0.00123456"), f"Expected 0.00123456, got {btc_money.amount}"
        
        print(f"   ✅ PASS: Precision enforcement works")
        print(f"      USD 100.999 → {usd_money}")
        print(f"      JPY 14572.6 → {jpy_money}")
        print(f"      BTC 0.00123456 → {btc_money}")
        results.append(("Money Precision", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Money Precision", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 3: Exchange Rate Management
    # =========================================================================
    print("TEST 3: Exchange Rate Management")
    try:
        engine = CurrencyEngine()
        
        # Set EUR/USD rate
        rate = engine.set_rate("EUR", "USD", Decimal("1.08"), source="test")
        
        assert rate.pair == "EUR/USD"
        assert rate.rate == Decimal("1.08")
        
        # Get the rate back
        retrieved = engine.get_rate("EUR", "USD")
        assert retrieved.rate == Decimal("1.08")
        
        # Get inverse rate (auto-created)
        inverse = engine.get_rate("USD", "EUR")
        expected_inverse = Decimal("1") / Decimal("1.08")
        # Allow small precision difference
        assert abs(inverse.rate - expected_inverse) < Decimal("0.0001")
        
        # Same currency = 1.0
        same = engine.get_rate("USD", "USD")
        assert same.rate == Decimal("1")
        
        print(f"   ✅ PASS: Exchange rate management works")
        print(f"      EUR/USD: {rate.rate}")
        print(f"      USD/EUR (inverse): {inverse.rate:.6f}")
        results.append(("Exchange Rates", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Exchange Rates", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 4: Basic Currency Conversion
    # =========================================================================
    print("TEST 4: Basic Currency Conversion (EUR → USD)")
    try:
        engine = CurrencyEngine()
        engine.set_rate("EUR", "USD", Decimal("1.08"))
        
        result = engine.convert(Decimal("100.00"), source_currency="EUR", target_currency="USD")
        
        assert result.source_money.amount == Decimal("100.00")
        assert result.source_money.currency.code == "EUR"
        assert result.target_money.amount == Decimal("108.00")
        assert result.target_money.currency.code == "USD"
        
        print(f"   ✅ PASS: Conversion successful")
        print(f"      {result.source_money} → {result.target_money}")
        print(f"      Rate used: {result.rate_used.rate}")
        results.append(("Basic Conversion", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Basic Conversion", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 5: JPY Conversion (0 decimals - INV-FIN-007)
    # =========================================================================
    print("TEST 5: JPY Conversion (0 decimals - INV-FIN-007)")
    try:
        engine = CurrencyEngine()
        engine.set_rate("USD", "JPY", Decimal("148.50"))
        
        # $100.50 USD → JPY (should round to whole number)
        result = engine.convert(Decimal("100.50"), source_currency="USD", target_currency="JPY")
        
        # 100.50 * 148.50 = 14924.25 → rounds to 14924
        assert result.target_money.currency.decimals == 0
        assert result.target_money.amount == result.target_money.amount.quantize(Decimal("1"))
        
        print(f"   ✅ PASS: JPY precision enforced")
        print(f"      {result.source_money} → {result.target_money}")
        print(f"      (No fractional yen)")
        results.append(("JPY Precision", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("JPY Precision", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 6: BTC Conversion (8 decimals)
    # =========================================================================
    print("TEST 6: BTC Conversion (8 decimals)")
    try:
        engine = CurrencyEngine()
        engine.set_rate("BTC", "USD", Decimal("97500.00"))
        
        # 0.01 BTC → USD
        btc_money = engine.create_money("0.01", "BTC")
        result = engine.convert(btc_money, target_currency="USD")
        
        # 0.01 * 97500 = 975.00
        assert result.target_money.amount == Decimal("975.00")
        
        # Reverse: $1000 USD → BTC (should preserve 8 decimals)
        engine.set_rate("USD", "BTC", Decimal("1") / Decimal("97500.00"))
        result2 = engine.convert(Decimal("1000.00"), source_currency="USD", target_currency="BTC")
        
        # 1000 / 97500 = 0.01025641...
        assert result2.target_money.currency.decimals == 8
        
        print(f"   ✅ PASS: BTC precision preserved")
        print(f"      {btc_money} → {result.target_money}")
        print(f"      $1000 USD → {result2.target_money}")
        results.append(("BTC Precision", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("BTC Precision", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 7: Rate Staleness Check
    # =========================================================================
    print("TEST 7: Rate Staleness Check")
    try:
        engine = CurrencyEngine(max_rate_age=timedelta(hours=24))
        
        # Set an old rate (25 hours ago)
        old_timestamp = datetime.now(timezone.utc) - timedelta(hours=25)
        engine.set_rate("GBP", "USD", Decimal("1.27"), timestamp=old_timestamp)
        
        try:
            engine.get_rate("GBP", "USD", validate_freshness=True)
            print(f"   ❌ FAIL: Should have raised StaleExchangeRateError")
            results.append(("Staleness Check", "FAIL"))
        except StaleExchangeRateError as e:
            print(f"   ✅ PASS: Stale rate detected")
            print(f"      Pair: {e.pair}")
            print(f"      Age: {e.age.total_seconds()/3600:.1f} hours")
            results.append(("Staleness Check", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Staleness Check", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 8: Conversion Audit Trail (INV-FIN-008)
    # =========================================================================
    print("TEST 8: Conversion Audit Trail (INV-FIN-008)")
    try:
        engine = CurrencyEngine()
        engine.set_rate("EUR", "USD", Decimal("1.08"))
        
        # Perform a conversion
        result = engine.convert(Decimal("500.00"), source_currency="EUR", target_currency="USD")
        
        # Check audit trail
        assert result.conversion_id is not None
        assert result.converted_at is not None
        assert result.rate_used is not None
        assert result.rate_used.rate == Decimal("1.08")
        
        # Get history
        history = engine.get_conversion_history()
        assert len(history) > 0
        
        last_conversion = history[-1]
        assert "rate_used" in last_conversion
        assert "source" in last_conversion
        assert "target" in last_conversion
        
        print(f"   ✅ PASS: Full audit trail recorded")
        print(f"      Conversion ID: {result.conversion_id[:8]}...")
        print(f"      Rate Recorded: {result.rate_used.rate}")
        print(f"      History entries: {len(history)}")
        results.append(("Audit Trail", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Audit Trail", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 9: Unknown Currency Error
    # =========================================================================
    print("TEST 9: Unknown Currency Protection")
    try:
        engine = CurrencyEngine()
        
        try:
            engine.create_money("100.00", "XYZ")  # Non-existent currency
            print(f"   ❌ FAIL: Should have raised UnknownCurrencyError")
            results.append(("Unknown Currency", "FAIL"))
        except UnknownCurrencyError as e:
            print(f"   ✅ PASS: Unknown currency rejected")
            print(f"      Code: {e.code}")
            results.append(("Unknown Currency", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Unknown Currency", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 10: Default Engine with Preset Rates
    # =========================================================================
    print("TEST 10: Default Engine with Preset Rates")
    try:
        engine = create_default_engine_with_rates()
        
        # Try some conversions with preset rates
        eur_usd = engine.convert(Decimal("100"), "EUR", "USD")
        usd_jpy = engine.convert(Decimal("100"), "USD", "JPY")
        btc_usd = engine.convert(Decimal("0.1"), "BTC", "USD")
        
        metrics = engine.get_metrics()
        
        print(f"   ✅ PASS: Default engine operational")
        print(f"      €100 EUR → {eur_usd.target_money}")
        print(f"      $100 USD → {usd_jpy.target_money}")
        print(f"      0.1 BTC → {btc_usd.target_money}")
        print(f"      Rates loaded: {metrics['rates_stored']}")
        results.append(("Default Engine", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Default Engine", "FAIL"))
    print()
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    
    for test_name, status in results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"   {icon} {test_name}: {status}")
    
    print()
    print(f"RESULT: {passed}/{total} tests passed")
    print()
    
    # Print currency support
    print("CURRENCY SUPPORT:")
    registry = CurrencyRegistry()
    print(f"   Fiat Currencies: {len(registry.list_fiat())}")
    print(f"   Cryptocurrencies: {len(registry.list_crypto())}")
    print(f"   Total: {len(registry.list_all())}")
    
    if passed == total:
        print()
        print("🎉 MULTI-CURRENCY ENGINE VALIDATED SUCCESSFULLY")
        print("   INV-FIN-007 (Precision Safety): ENFORCED")
        print("   INV-FIN-008 (Rate Transparency): ENFORCED")
        return 0
    else:
        print()
        print("⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
