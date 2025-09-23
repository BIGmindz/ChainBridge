#!/usr/bin/env python3
"""
Integration Example: Enhanced Regime Detection with Existing Bot
Shows how to integrate the enhanced regime detection model with the existing trading bot
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from regime_model_utils import RegimeModelLoader, create_sample_features
    from market_regime_controller import MarketRegimeController
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the repository root directory")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedRegimeIntegration:
    """
    Integration layer between enhanced regime model and existing bot systems
    """
    
    def __init__(self):
        self.enhanced_loader = RegimeModelLoader()
        self.original_controller = MarketRegimeController()
        self.current_regime = None
        self.regime_history = []
        
        # Load enhanced model if available
        self.enhanced_available = self._initialize_enhanced_model()
    
    def _initialize_enhanced_model(self) -> bool:
        """Initialize enhanced model if available"""
        try:
            available_models = self.enhanced_loader.list_available_models()
            if 'enhanced' in available_models:
                success = self.enhanced_loader.load_model('enhanced')
                if success:
                    logger.info("✅ Enhanced regime model loaded and available")
                    return True
                else:
                    logger.warning("⚠️  Failed to load enhanced model, falling back to original")
                    return False
            else:
                logger.info("ℹ️  Enhanced model not found, using original controller")
                return False
        except Exception as e:
            logger.error(f"Error initializing enhanced model: {e}")
            return False
    
    def get_current_regime(self, market_features: Dict) -> Dict:
        """
        Get current market regime using the best available model
        
        Args:
            market_features: Dictionary with market feature values
            
        Returns:
            Dictionary with regime information
        """
        result = {
            'regime': 'unknown',
            'confidence': 0.0,
            'source': 'fallback',
            'timestamp': datetime.now().isoformat(),
            'enhanced_available': self.enhanced_available
        }
        
        if self.enhanced_available:
            # Try enhanced model first
            try:
                enhanced_result = self.enhanced_loader.predict_regime(market_features, 'enhanced')
                result.update({
                    'regime': enhanced_result['regime'],
                    'confidence': enhanced_result['confidence'],
                    'probabilities': enhanced_result['probabilities'],
                    'source': 'enhanced_model'
                })
                
                # Store in history
                self.current_regime = result['regime']
                self.regime_history.append(result)
                
                # Keep only last 100 regime predictions
                if len(self.regime_history) > 100:
                    self.regime_history = self.regime_history[-100:]
                
                logger.info(f"🎯 Enhanced regime: {result['regime']} (confidence: {result['confidence']:.3f})")
                return result
                
            except Exception as e:
                logger.error(f"Enhanced model prediction failed: {e}")
                # Fall through to original controller
        
        # Use original controller as fallback
        try:
            original_regime = self.original_controller.detect_regime()
            if original_regime:
                result.update({
                    'regime': original_regime,
                    'confidence': 0.5,  # Default confidence for original
                    'source': 'original_controller'
                })
                logger.info(f"📊 Original regime: {original_regime}")
            else:
                # Final fallback
                fallback_regime = self._fallback_regime_detection(market_features)
                result.update({
                    'regime': fallback_regime,
                    'confidence': 0.3,
                    'source': 'fallback_rules'
                })
                logger.info(f"🔄 Fallback regime: {fallback_regime}")
        
        except Exception as e:
            logger.error(f"Original controller failed: {e}")
            # Use simple fallback
            fallback_regime = self._fallback_regime_detection(market_features)
            result.update({
                'regime': fallback_regime,
                'confidence': 0.3,
                'source': 'fallback_rules'
            })
        
        return result
    
    def _fallback_regime_detection(self, features: Dict) -> str:
        """
        Simple fallback regime detection using basic rules
        
        Args:
            features: Market feature dictionary
            
        Returns:
            Regime string
        """
        try:
            # Use simple rules based on available features
            rsi = features.get('rsi_14', 50)
            price_change = features.get('price_change_24h', 0)
            trend_strength = features.get('trend_strength', 0)
            
            # Simple rule-based classification
            if rsi > 70 and price_change > 0.02 and trend_strength > 0.5:
                return 'bull'
            elif rsi < 30 and price_change < -0.02 and trend_strength < -0.5:
                return 'bear'
            else:
                return 'sideways'
                
        except Exception:
            return 'sideways'  # Most conservative default
    
    def get_regime_strength(self) -> float:
        """
        Get current regime strength based on recent history
        
        Returns:
            Regime strength (0-1)
        """
        if not self.regime_history:
            return 0.5
        
        # Look at last 10 predictions
        recent = self.regime_history[-10:]
        if not recent:
            return 0.5
        
        # Calculate consistency
        current_regime = recent[-1]['regime']
        consistent_count = sum(1 for r in recent if r['regime'] == current_regime)
        consistency = consistent_count / len(recent)
        
        # Calculate average confidence
        avg_confidence = sum(r['confidence'] for r in recent) / len(recent)
        
        # Combine consistency and confidence
        strength = (consistency * 0.6) + (avg_confidence * 0.4)
        
        return min(1.0, max(0.0, strength))
    
    def adapt_strategy_for_regime(self, regime: str, confidence: float) -> Dict:
        """
        Adapt trading strategy parameters based on current regime
        
        Args:
            regime: Current market regime
            confidence: Confidence in the regime prediction
            
        Returns:
            Dictionary with adjusted strategy parameters
        """
        base_params = {
            'position_size_multiplier': 1.0,
            'stop_loss_multiplier': 1.0,
            'take_profit_multiplier': 1.0,
            'signal_threshold_adjustment': 0.0,
            'max_positions': 3
        }
        
        # Only adjust if confidence is reasonable
        if confidence < 0.5:
            return base_params
        
        regime_adjustments = {
            'bull': {
                'position_size_multiplier': 1.2,
                'stop_loss_multiplier': 0.8,
                'take_profit_multiplier': 1.3,
                'signal_threshold_adjustment': -0.1,
                'max_positions': 5
            },
            'bear': {
                'position_size_multiplier': 0.6,
                'stop_loss_multiplier': 1.2,
                'take_profit_multiplier': 0.8,
                'signal_threshold_adjustment': 0.1,
                'max_positions': 2
            },
            'sideways': {
                'position_size_multiplier': 0.8,
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.0,
                'signal_threshold_adjustment': 0.05,
                'max_positions': 3
            }
        }
        
        adjustments = regime_adjustments.get(regime, {})
        
        # Apply confidence weighting
        confidence_weight = min(1.0, confidence)
        
        for param, adjustment in adjustments.items():
            if param.endswith('_multiplier'):
                # Interpolate between base (1.0) and target value
                base_params[param] = 1.0 + (adjustment - 1.0) * confidence_weight
            elif param == 'signal_threshold_adjustment':
                base_params[param] = adjustment * confidence_weight
            else:
                base_params[param] = adjustment
        
        return base_params
    
    def get_integration_status(self) -> Dict:
        """Get status of the regime integration system"""
        return {
            'enhanced_available': self.enhanced_available,
            'current_regime': self.current_regime,
            'regime_strength': self.get_regime_strength(),
            'history_length': len(self.regime_history),
            'last_update': self.regime_history[-1]['timestamp'] if self.regime_history else None
        }


def demonstrate_integration():
    """
    Demonstrate the integration with sample market scenarios
    """
    print("🔗 ENHANCED REGIME INTEGRATION DEMO")
    print("="*40)
    
    # Initialize integration
    integration = EnhancedRegimeIntegration()
    
    # Show integration status
    status = integration.get_integration_status()
    print(f"📊 Integration Status:")
    print(f"   Enhanced Model Available: {status['enhanced_available']}")
    print(f"   Current Regime: {status['current_regime']}")
    print(f"   History Length: {status['history_length']}")
    
    # Test with different market scenarios
    scenarios = [
        ('Strong Bull Market', create_sample_features('bull')),
        ('Strong Bear Market', create_sample_features('bear')),
        ('Sideways Market', create_sample_features('sideways')),
    ]
    
    print(f"\n🧪 TESTING MARKET SCENARIOS:")
    print("-" * 40)
    
    for scenario_name, features in scenarios:
        print(f"\n📈 {scenario_name}:")
        
        # Get regime prediction
        regime_result = integration.get_current_regime(features)
        
        print(f"   Regime: {regime_result['regime']}")
        print(f"   Confidence: {regime_result['confidence']:.3f}")
        print(f"   Source: {regime_result['source']}")
        
        # Get strategy adjustments
        strategy_params = integration.adapt_strategy_for_regime(
            regime_result['regime'], 
            regime_result['confidence']
        )
        
        print(f"   Strategy Adjustments:")
        print(f"     Position Size: {strategy_params['position_size_multiplier']:.2f}x")
        print(f"     Stop Loss: {strategy_params['stop_loss_multiplier']:.2f}x")
        print(f"     Take Profit: {strategy_params['take_profit_multiplier']:.2f}x")
        print(f"     Max Positions: {strategy_params['max_positions']}")
    
    # Show regime strength after testing
    final_strength = integration.get_regime_strength()
    print(f"\n📊 Final Regime Strength: {final_strength:.3f}")
    
    print(f"\n✅ Integration demo completed successfully!")


def main():
    """Main demonstration function"""
    try:
        demonstrate_integration()
        return 0
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)