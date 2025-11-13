#!/usr/bin/env python3
"""
Tests for Enhanced Regime Detection Model
"""

import os
import sys
import unittest
import tempfile
import shutil
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from enhanced_regime_model import EnhancedRegimeModel
    from regime_model_utils import (
        RegimeModelLoader,
        create_sample_features,
        quick_predict,
    )
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


class TestEnhancedRegimeModel(unittest.TestCase):
    """Test cases for Enhanced Regime Model"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.model = EnhancedRegimeModel(model_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    def test_sample_data_generation(self) -> None:
        """Test sample data generation"""
        # Generate sample data
        data = self.model.generate_sample_data(n_samples=100)

        # Check data shape and content
        self.assertEqual(len(data), 100)
        self.assertIn("regime", data.columns)

        # Check all required features are present
        expected_features = [
            "rsi_14",
            "macd",
            "macd_signal",
            "macd_hist",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_width",
            "bb_position",
            "volume_ratio",
            "price_change_1h",
            "price_change_24h",
            "volatility_24h",
            "trend_strength",
            "momentum_rsi",
            "price_momentum",
            "volume_price_trend",
            "bb_squeeze",
        ]

        for feature in expected_features:
            self.assertIn(feature, data.columns)

        # Check regime distribution
        regimes = data["regime"].unique()  # type: ignore
        self.assertTrue(
            all(regime in ["bull", "bear", "sideways"] for regime in regimes)
        )

        # Check feature bounds
        self.assertTrue((data["rsi_14"] >= 0).all() and (data["rsi_14"] <= 100).all())
        self.assertTrue(
            (data["bb_position"] >= 0).all() and (data["bb_position"] <= 1).all()
        )
        self.assertTrue((data["volume_ratio"] > 0).all())
        self.assertTrue((data["volatility_24h"] > 0).all())

    def test_model_training(self) -> None:
        """Test model training functionality"""
        # Generate sample data
        data = self.model.generate_sample_data(n_samples=200)

        # Train model
        results = self.model.train_model(data)

        # Check training results
        self.assertIsNotNone(self.model.model)
        self.assertIsNotNone(self.model.label_encoder)
        self.assertIsNotNone(self.model.feature_scaler)
        self.assertIsNotNone(self.model.feature_columns)

        # Check results structure
        self.assertIn("train_accuracy", results)
        self.assertIn("test_accuracy", results)
        self.assertIn("cv_mean", results)
        self.assertIn("cv_std", results)

        # Check accuracy is reasonable
        self.assertGreater(results["train_accuracy"], 0.8)
        self.assertGreater(results["test_accuracy"], 0.7)

        # Check label encoder classes
        expected_classes = ["bear", "bull", "sideways"]
        self.assertEqual(set(self.model.label_encoder.classes_), set(expected_classes))

    def test_prediction(self) -> None:
        """Test prediction functionality"""
        # Generate and train
        data = self.model.generate_sample_data(n_samples=200)
        self.model.train_model(data)

        # Create test features
        test_features = pd.DataFrame(
            [
                {
                    "rsi_14": 65.0,
                    "macd": 0.02,
                    "macd_signal": 0.015,
                    "macd_hist": 0.005,
                    "bb_upper": 52000,
                    "bb_middle": 50000,
                    "bb_lower": 48000,
                    "bb_width": 4000,
                    "bb_position": 0.75,
                    "volume_ratio": 1.5,
                    "price_change_1h": 0.01,
                    "price_change_24h": 0.03,
                    "volatility_24h": 0.20,
                    "trend_strength": 0.7,
                    "momentum_rsi": 68.0,
                    "price_momentum": 0.15,
                    "volume_price_trend": 0.045,
                    "bb_squeeze": 0,
                }
            ]
        )

        # Make prediction
        regimes, probas = self.model.predict(test_features)

        # Check prediction format
        self.assertEqual(len(regimes), 1)
        self.assertIn(regimes[0], ["bull", "bear", "sideways"])
        self.assertEqual(probas.shape, (1, 3))
        self.assertAlmostEqual(probas[0].sum(), 1.0, places=6)  # type: ignore

    def test_single_prediction(self) -> None:
        """Test single prediction functionality"""
        # Generate and train
        data = self.model.generate_sample_data(n_samples=200)
        self.model.train_model(data)

        # Single prediction
        feature_dict = {
            "rsi_14": 30.0,
            "macd": -0.02,
            "macd_signal": -0.015,
            "macd_hist": -0.005,
            "bb_upper": 52000,
            "bb_middle": 50000,
            "bb_lower": 48000,
            "bb_width": 4000,
            "bb_position": 0.25,
            "volume_ratio": 2.0,
            "price_change_1h": -0.01,
            "price_change_24h": -0.05,
            "volatility_24h": 0.30,
            "trend_strength": -0.8,
            "momentum_rsi": 28.0,
            "price_momentum": -0.17,
            "volume_price_trend": -0.1,
            "bb_squeeze": 0,
        }

        result = self.model.predict_single(feature_dict)

        # Check result structure
        self.assertIn("regime", result)
        self.assertIn("confidence", result)
        self.assertIn("probabilities", result)
        self.assertIn("timestamp", result)

        self.assertIn(result["regime"], ["bull", "bear", "sideways"])
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_model_save_load(self) -> None:
        """Test model saving and loading"""
        # Generate and train
        data = self.model.generate_sample_data(n_samples=200)
        results = self.model.train_model(data)

        # Save model
        model_path = self.model.save_model()
        self.assertTrue(os.path.exists(model_path))

        # Create new model instance and load
        new_model = EnhancedRegimeModel(model_dir=self.temp_dir)
        success = new_model.load_model()

        self.assertTrue(success)
        self.assertIsNotNone(new_model.model)
        self.assertIsNotNone(new_model.label_encoder)

        # Test that loaded model can make predictions
        feature_dict = {
            "rsi_14": 50.0,
            "macd": 0.01,
            "macd_signal": 0.008,
            "macd_hist": 0.002,
            "bb_upper": 52000,
            "bb_middle": 50000,
            "bb_lower": 48000,
            "bb_width": 4000,
            "bb_position": 0.5,
            "volume_ratio": 1.2,
            "price_change_1h": 0.005,
            "price_change_24h": 0.01,
            "volatility_24h": 0.15,
            "trend_strength": 0.1,
            "momentum_rsi": 52.0,
            "price_momentum": 0.07,
            "volume_price_trend": 0.012,
            "bb_squeeze": 1,
        }

        result = new_model.predict_single(feature_dict)
        self.assertIn(result["regime"], ["bull", "bear", "sideways"])

    def test_feature_importance(self) -> None:
        """Test feature importance functionality"""
        # Generate and train
        data = self.model.generate_sample_data(n_samples=200)
        self.model.train_model(data)

        # Get feature importance
        importance = self.model.get_feature_importance()

        # Check structure
        self.assertEqual(len(importance), 18)  # Should have all features
        self.assertTrue(
            all(
                isinstance(v, (int, float, np.integer, np.floating))
                for v in importance.values()
            )
        )

        # Check that importance values are reasonable
        total_importance = sum(importance.values())  # type: ignore
        self.assertGreater(total_importance, 0)


class TestRegimeModelUtils(unittest.TestCase):
    """Test cases for Regime Model Utilities"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

        # Create a simple test model
        model = EnhancedRegimeModel(model_dir=self.temp_dir)
        data = model.generate_sample_data(n_samples=100)
        model.train_model(data)
        model.save_model()

        self.loader = RegimeModelLoader(model_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    def test_model_discovery(self) -> None:
        """Test model discovery functionality"""
        available = self.loader.list_available_models()
        self.assertIn("enhanced", available)

    def test_model_loading(self) -> None:
        """Test model loading functionality"""
        success = self.loader.load_model("enhanced")
        self.assertTrue(success)

        # Check model info
        info = self.loader.get_model_info("enhanced")
        self.assertIn("model_name", info)
        self.assertIn("regime_classes", info)
        self.assertIn("feature_columns", info)
        self.assertEqual(info["model_name"], "enhanced")
        self.assertEqual(len(info["feature_columns"]), 18)

    def test_prediction(self) -> None:
        """Test prediction functionality"""
        # Load model
        self.loader.load_model("enhanced")

        # Create sample features
        features = create_sample_features("bull")
        result = self.loader.predict_regime(features, "enhanced")

        # Check result structure
        self.assertIn("regime", result)
        self.assertIn("confidence", result)
        self.assertIn("probabilities", result)
        self.assertIn("model_used", result)

        self.assertIn(result["regime"], ["bull", "bear", "sideways"])
        self.assertEqual(result["model_used"], "enhanced")

    def test_sample_features_creation(self) -> None:
        """Test sample features creation"""
        for regime_type in ["bull", "bear", "sideways"]:
            features = create_sample_features(regime_type)

            # Check all required features are present
            expected_features = [
                "rsi_14",
                "macd",
                "macd_signal",
                "macd_hist",
                "bb_upper",
                "bb_middle",
                "bb_lower",
                "bb_width",
                "bb_position",
                "volume_ratio",
                "price_change_1h",
                "price_change_24h",
                "volatility_24h",
                "trend_strength",
                "momentum_rsi",
                "price_momentum",
                "volume_price_trend",
                "bb_squeeze",
            ]

            for feature in expected_features:
                self.assertIn(feature, features)

            # Check feature bounds
            self.assertGreaterEqual(features["rsi_14"], 0)
            self.assertLessEqual(features["rsi_14"], 100)
            self.assertGreaterEqual(features["bb_position"], 0)
            self.assertLessEqual(features["bb_position"], 1)
            self.assertGreater(features["volume_ratio"], 0)
            self.assertGreater(features["volatility_24h"], 0)

    def test_quick_predict(self) -> None:
        """Test quick predict functionality"""
        # Move model to default location for quick_predict
        default_dir = "ml_models"
        os.makedirs(default_dir, exist_ok=True)

        # Copy model file
        import shutil

        src_path = os.path.join(self.temp_dir, "enhanced_regime_model.pkl")
        dst_path = os.path.join(default_dir, "enhanced_regime_model.pkl")
        shutil.copy2(src_path, dst_path)

        try:
            features = create_sample_features("bull")
            result = quick_predict(features, "enhanced")
            self.assertIn(result, ["bull", "bear", "sideways"])
        finally:
            # Clean up
            if os.path.exists(dst_path):
                os.remove(dst_path)


class TestIntegration(unittest.TestCase):
    """Integration tests"""

    def test_end_to_end_workflow(self) -> None:
        """Test complete workflow from training to prediction"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Create and train model
            model = EnhancedRegimeModel(model_dir=temp_dir)
            data = model.generate_sample_data(n_samples=300)
            results = model.train_model(data)
            model.save_model()

            # 2. Load model with utilities
            loader = RegimeModelLoader(model_dir=temp_dir)
            success = loader.load_model("enhanced")
            self.assertTrue(success)

            # 3. Make predictions
            test_cases = [
                ("bull", create_sample_features("bull")),
                ("bear", create_sample_features("bear")),
                ("sideways", create_sample_features("sideways")),
            ]

            for expected_type, features in test_cases:
                result = loader.predict_regime(features, "enhanced")

                # Prediction should be reasonable
                self.assertIn(result["regime"], ["bull", "bear", "sideways"])
                self.assertGreaterEqual(result["confidence"], 0.0)
                self.assertLessEqual(result["confidence"], 1.0)

                # Probabilities should sum to 1
                prob_sum = sum(result["probabilities"].values())  # type: ignore
                self.assertAlmostEqual(prob_sum, 1.0, places=6)


def run_tests():
    """Run all tests"""
    print("🧪 Running Enhanced Regime Detection Model Tests")
    print("=" * 50)

    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_classes = [TestEnhancedRegimeModel, TestRegimeModelUtils, TestIntegration]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\n{'=' * 50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\n❌ ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
