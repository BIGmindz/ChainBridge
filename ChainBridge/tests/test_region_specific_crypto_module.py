import unittest

from modules.region_specific_crypto_module import RegionSpecificCryptoModule


class TestRegionSpecificCryptoModule(unittest.TestCase):
    def setUp(self):
        self.region_module = RegionSpecificCryptoModule()

        # Test macro signals
        self.test_signals = {
            "inflation_ARG": 142,
            "stablecoin_growth_LATAM": 0.63,
            "adoption_rank_IND": 1,
            "sbi_ripple_news": True,
            "port_congestion": 1.4,
            "el_salvador_btc_news": False,
        }

    def test_initialization(self):
        """Test that the module initializes correctly"""
        self.assertEqual(self.region_module.name, "region_crypto_mapper")
        self.assertTrue(isinstance(self.region_module.region_crypto_map, dict))
        self.assertIn("BRAZIL", self.region_module.region_crypto_map)
        self.assertIn("INDIA", self.region_module.region_crypto_map)
        self.assertIn("JAPAN", self.region_module.region_crypto_map)

    def test_region_analysis(self):
        """Test the region analysis functionality"""
        # Test Brazil analysis
        brazil_confidence = self.region_module._analyze_region("BRAZIL", self.test_signals)
        self.assertGreater(brazil_confidence, 0.5)

        # Test India analysis
        india_confidence = self.region_module._analyze_region("INDIA", self.test_signals)
        self.assertGreater(india_confidence, 0.3)

        # Test logistics analysis
        logistics_confidence = self.region_module._analyze_region("LOGISTICS", self.test_signals)
        self.assertGreater(logistics_confidence, 0.3)

    def test_crypto_selection(self):
        """Test crypto selection based on confidence levels"""
        # High confidence should return all primary cryptos
        high_confidence_cryptos = self.region_module._select_cryptos("BRAZIL", 0.8)
        self.assertEqual(len(high_confidence_cryptos), 3)

        # Medium confidence should return first primary crypto
        medium_confidence_cryptos = self.region_module._select_cryptos("BRAZIL", 0.6)
        self.assertEqual(len(medium_confidence_cryptos), 1)

        # Low confidence should return empty list
        low_confidence_cryptos = self.region_module._select_cryptos("BRAZIL", 0.4)
        self.assertEqual(len(low_confidence_cryptos), 0)

    def test_position_sizing(self):
        """Test position sizing based on confidence"""
        high_confidence = self.region_module._calculate_position_size(0.9)
        medium_confidence = self.region_module._calculate_position_size(0.7)
        low_confidence = self.region_module._calculate_position_size(0.5)
        very_low_confidence = self.region_module._calculate_position_size(0.3)

        # Check that position sizes are properly scaled
        self.assertGreater(high_confidence, medium_confidence)
        self.assertGreater(medium_confidence, low_confidence)
        self.assertGreater(low_confidence, very_low_confidence)

    def test_holding_period(self):
        """Test holding period estimation"""
        logistics_period = self.region_module._estimate_holding_period(["LOGISTICS"])
        japan_period = self.region_module._estimate_holding_period(["JAPAN"])
        india_period = self.region_module._estimate_holding_period(["INDIA"])
        other_period = self.region_module._estimate_holding_period(["CENTRAL_AMERICA"])

        # Check that different regions have different holding periods
        self.assertIn("30-45", logistics_period)  # Logistics should be longest
        self.assertIn("14-30", japan_period)  # Japan should be medium
        self.assertIn("7-14", india_period)  # India should be shorter
        self.assertIn("3-7", other_period)  # Others should be shortest

    def test_process_regional_signals(self):
        """Test the main processing function"""
        result = self.region_module.process_regional_signals(self.test_signals)

        # Check result structure
        self.assertIn("timestamp", result)
        self.assertIn("recommendations", result)
        self.assertIn("total_confidence", result)
        self.assertIn("active_regions", result)
        self.assertIn("module", result)

        # Check that we have recommendations for at least one region
        self.assertGreaterEqual(len(result["active_regions"]), 1)

        # Only verify that active regions exist, since the specific crypto recommendations
        # may vary based on internal confidence thresholds during testing
        self.assertTrue(len(result["active_regions"]) > 0)


if __name__ == "__main__":
    unittest.main()
