#!/usr/bin/env python3
"""
Test script for Ensemble Voting ML System

This script tests the ensemble voting functionality by:
1. Loading the ensemble configuration
2. Testing model loading
3. Running sample predictions
4. Verifying voting mechanisms
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_ensemble_discovery():
    """Test that ensemble strategy is discovered correctly"""
    logger.info("🔍 Testing ensemble strategy discovery...")

    try:
        from strategy_launcher import discover_strategies
        strategies = discover_strategies()

        if 'ensemble_voting' in strategies:
            ensemble_info = strategies['ensemble_voting']
            logger.info("✅ Ensemble strategy discovered successfully")
            logger.info(f"   Config: {ensemble_info['config_path']}")
            logger.info(f"   Is Ensemble: {ensemble_info['is_ensemble']}")
            return True
        else:
            logger.error("❌ Ensemble strategy not found in discovery")
            return False
    except Exception as e:
        logger.error(f"❌ Error testing ensemble discovery: {e}")
        return False

def test_ensemble_module_loading():
    """Test that the ensemble voting module loads correctly"""
    logger.info("🔧 Testing ensemble module loading...")

    try:
        # Set up environment variables for ensemble
        os.environ['BENSON_IS_ENSEMBLE'] = 'true'
        os.environ['BENSON_ENSEMBLE_MODELS'] = 'strategies/bull_market/model.pkl,strategies/sideways_market/model.pkl'
        os.environ['BENSON_ENSEMBLE_SCALERS'] = 'strategies/bull_market/scaler.pkl,strategies/sideways_market/scaler.pkl'
        os.environ['BENSON_VOTING_MECHANISM'] = 'majority_vote'

        from modules.machine_learning_module import EnsembleVotingModule

        ensemble = EnsembleVotingModule()
        status = ensemble.get_status()

        logger.info("✅ Ensemble module loaded successfully")
        logger.info(f"   Active Models: {status['active_models']}")
        logger.info(f"   Voting Mechanism: {status['voting_mechanism']}")
        logger.info(f"   Is Ensemble: {status['is_ensemble']}")

        return status['active_models'] > 0

    except Exception as e:
        logger.error(f"❌ Error testing ensemble module: {e}")
        return False

def test_sample_prediction():
    """Test a sample prediction with the ensemble"""
    logger.info("🎯 Testing sample ensemble prediction...")

    try:
        # Set up environment variables
        os.environ['BENSON_IS_ENSEMBLE'] = 'true'
        os.environ['BENSON_ENSEMBLE_MODELS'] = 'strategies/bull_market/model.pkl,strategies/sideways_market/model.pkl'
        os.environ['BENSON_ENSEMBLE_SCALERS'] = 'strategies/bull_market/scaler.pkl,strategies/sideways_market/scaler.pkl'
        os.environ['BENSON_VOTING_MECHANISM'] = 'majority_vote'

        from modules.machine_learning_module import EnsembleVotingModule

        ensemble = EnsembleVotingModule()

        # Sample price data
        sample_price_data = {
            'close': 45000.0,
            'rsi_value': 65.0,
            'ob_imbalance': 0.1,
            'vol_imbalance': 0.05,
            'previous_price': 44500.0
        }

        # Get ensemble signal
        result = ensemble.get_signal(sample_price_data, 'BTC/USD')

        logger.info("✅ Sample prediction completed")
        logger.info(f"   Ensemble Signal: {result['signal']}")
        logger.info(f"   Confidence: {result['confidence']:.3f}")
        logger.info(f"   Model Count: {result.get('model_count', 0)}")

        if 'ensemble_votes' in result:
            logger.info(f"   Vote Breakdown: {result['ensemble_votes']}")

        # Test passes if we get a valid response structure
        has_signal = result['signal'] in ['BUY', 'SELL', 'HOLD']
        has_model_count = 'model_count' in result
        has_votes = 'ensemble_votes' in result

        return has_signal and has_model_count and has_votes

    except Exception as e:
        logger.error(f"❌ Error testing sample prediction: {e}")
        return False

def main():
    """Run all ensemble tests"""
    logger.info("🚀 Starting Ensemble Voting System Tests")
    logger.info("=" * 60)

    tests = [
        ("Strategy Discovery", test_ensemble_discovery),
        ("Module Loading", test_ensemble_module_loading),
        ("Sample Prediction", test_sample_prediction),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running: {test_name}")
        logger.info("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"Result: {status}")
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1

    logger.info("-" * 60)
    logger.info(f"Overall: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! Ensemble system is ready.")
        return True
    else:
        logger.warning("⚠️  Some tests failed. Check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)