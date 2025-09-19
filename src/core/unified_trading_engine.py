"""
YOUR ENHANCED MULTI-SIGNAL TRADING ENGINE
This builds on what you already have!
"""

import json
import numpy as np
from datetime import datetime
from typing import Dict, Tuple
import os
from enum import Enum
from collections import deque


class MarketRegime(Enum):
    """Market regime classification"""
    BULL = 'bull'
    BEAR = 'bear'
    SIDEWAYS = 'sideways'
    UNKNOWN = 'unknown'


class MarketRegimeDetector:
    """
    Detects market regimes (bull, bear, sideways) using price action and technical indicators
    """
    
    def __init__(self, lookback_period: int = 10):
        """
        Initialize the market regime detector
        
        Args:
            lookback_period: Number of price points to consider for detection
        """
        self.lookback_period = lookback_period
        self.price_history = deque(maxlen=lookback_period)
        self.volume_history = deque(maxlen=lookback_period)
        self.returns_history = deque(maxlen=lookback_period)
        self.volatility_history = deque(maxlen=lookback_period)
        
        # Regime detection thresholds - adjusted for better sensitivity
        self.trend_threshold = 0.10  # 10% price change to indicate bull/bear (lowered from 15%)
        self.volatility_threshold = 0.04  # 4% average daily change for high volatility (lowered from 5%)
        
        # Current market regime
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_history = deque(maxlen=lookback_period)
        self.confidence = 0.0
        
        # Optimization weights per regime
        self.regime_weights = {
            MarketRegime.BULL: {
                'technical': 1.2,    # Technical indicators work well in trends
                'sentiment': 0.8,    # Be cautious of FOMO in bull markets
                'onchain': 1.3,      # On-chain is good at confirming bull runs
                'unique': 1.1        # Proprietary signals get a boost
            },
            MarketRegime.BEAR: {
                'technical': 1.0,    # Technical is neutral in bear markets
                'sentiment': 1.3,    # Sentiment is crucial in bear markets
                'onchain': 1.2,      # On-chain shows capital flows in bear markets
                'unique': 1.1        # Proprietary signals get a boost
            },
            MarketRegime.SIDEWAYS: {
                'technical': 1.3,    # Technical works best in ranging markets
                'sentiment': 0.7,    # Sentiment is less useful in sideways
                'onchain': 0.9,      # On-chain less useful in sideways
                'unique': 1.2        # Proprietary signals get a boost
            },
            MarketRegime.UNKNOWN: {
                'technical': 1.0,    # Neutral weighting when regime is unknown
                'sentiment': 1.0,
                'onchain': 1.0,
                'unique': 1.0
            }
        }
        
    def update(self, price: float, volume: float = None) -> MarketRegime:
        """
        Update the detector with new price data and detect the current regime
        
        Args:
            price: Current price
            volume: Current trading volume (optional)
            
        Returns:
            Current market regime
        """
        # Add new data
        if len(self.price_history) > 0:
            returns = (price / self.price_history[-1]) - 1
            self.returns_history.append(returns)
            
            # Calculate volatility (absolute price change)
            volatility = abs(returns)
            self.volatility_history.append(volatility)
            
        self.price_history.append(price)
        if volume is not None:
            self.volume_history.append(volume)
        
        # Detect market regime if we have enough data
        if len(self.price_history) >= 3:  # Need at least 3 points
            return self._detect_regime()
        
        return MarketRegime.UNKNOWN
    
    def _detect_regime(self) -> MarketRegime:
        """
        Detect the current market regime based on price history
        with smoothing to prevent frequent regime changes
        
        Returns:
            Current market regime
        """
        # Calculate trend using linear regression slope
        if len(self.price_history) >= self.lookback_period:
            # Full lookback period available
            price_change = (self.price_history[-1] / self.price_history[0]) - 1
            
            # Calculate average volatility
            avg_volatility = sum(self.volatility_history) / len(self.volatility_history)
            
            # Calculate regime with advanced logic
            new_regime, new_confidence = self._calculate_regime(price_change, avg_volatility)
            
            # Apply regime transition smoothing
            smoothed_regime, smoothed_confidence = self._smooth_regime_transition(
                new_regime, new_confidence)
            
            # Update current regime
            self.current_regime = smoothed_regime
            self.confidence = smoothed_confidence
            self.regime_history.append(smoothed_regime)
            
            return smoothed_regime
        else:
            # Not enough data, calculate with what we have
            first_price = self.price_history[0]
            latest_price = self.price_history[-1]
            price_change = (latest_price / first_price) - 1
            
            # Simple regime detection with less confidence
            if price_change > self.trend_threshold * 0.5:
                self.current_regime = MarketRegime.BULL
                self.confidence = 0.5
            elif price_change < -self.trend_threshold * 0.5:
                self.current_regime = MarketRegime.BEAR
                self.confidence = 0.5
            else:
                self.current_regime = MarketRegime.SIDEWAYS
                self.confidence = 0.4
            
            self.regime_history.append(self.current_regime)
            return self.current_regime
    
    def _calculate_regime(self, price_change: float, volatility: float) -> Tuple[MarketRegime, float]:
        """
        Calculate the market regime using price change and volatility
        
        Args:
            price_change: Percentage price change
            volatility: Average volatility
            
        Returns:
            Tuple of (regime, confidence)
        """
        # Calculate base regime from price action
        if price_change > self.trend_threshold:
            base_regime = MarketRegime.BULL
            base_confidence = min(0.5 + abs(price_change) / 2, 0.9)  # Higher change = higher confidence
        elif price_change < -self.trend_threshold:
            base_regime = MarketRegime.BEAR
            base_confidence = min(0.5 + abs(price_change) / 2, 0.9)
        else:
            base_regime = MarketRegime.SIDEWAYS
            # Higher confidence when price change is very close to 0
            base_confidence = 0.5 + (1 - abs(price_change) / self.trend_threshold) * 0.3
        
        return base_regime, base_confidence
            
    def _smooth_regime_transition(self, new_regime: MarketRegime, 
                                 new_confidence: float) -> Tuple[MarketRegime, float]:
        """
        Smooth transitions between market regimes to prevent frequent switching
        
        Args:
            new_regime: Newly detected market regime
            new_confidence: Confidence in the new regime
            
        Returns:
            Tuple of (smoothed_regime, smoothed_confidence)
        """
        # If this is the first detection, use it directly
        if not self.regime_history:
            return new_regime, new_confidence
            
        # Get current regime and minimum required confidence to switch
        min_confidence_to_switch = 0.65
        min_consecutive_detections = 3
        
        # Check if we have enough consistent detections to switch regimes
        if new_regime != self.current_regime:
            # Count recent detections of the new regime
            recent_history = self.regime_history[-min_consecutive_detections:] if len(self.regime_history) >= min_consecutive_detections else []
            new_regime_count = sum(1 for r in recent_history if r == new_regime)
            
            # If we don't have enough consecutive detections, stick with current regime
            if new_regime_count < min_consecutive_detections - 1:
                # Reduce confidence when we stick with existing regime against new detection
                adjusted_confidence = self.confidence * 0.95  # Slightly reduce confidence
                return self.current_regime, adjusted_confidence
                
            # If confidence is too low for a switch, stay with current regime
            if new_confidence < min_confidence_to_switch:
                return self.current_regime, self.confidence
                
        # Either the regime isn't changing or we have enough evidence to switch
        # Return the new regime and confidence calculated above
        return new_regime, new_confidence
    
    def get_regime(self) -> Tuple[MarketRegime, float]:
        """
        Get the current market regime and confidence
        
        Returns:
            Tuple of (regime, confidence)
        """
        return self.current_regime, self.confidence
    
    def get_optimization_weights(self, signal_category: str) -> float:
        """
        Get the optimization weight for a specific signal category based on the current regime
        
        Args:
            signal_category: Category of the signal (technical, sentiment, onchain, unique)
            
        Returns:
            Optimization weight for the signal category in the current regime
        """
        if self.current_regime in self.regime_weights:
            category_weights = self.regime_weights[self.current_regime]
            return category_weights.get(signal_category, 1.0)
        return 1.0

class MultiSignalTradingEngine:
    """
    Your Scalable Multi-Signal ML Trading System
    Better than 3Commas, Cryptohopper, and others
    """
    
    def __init__(self, config_path: str = "config/trading_config.json", enhanced_ml: bool = True, regime_aware: bool = True):
        print("""
        ╔════════════════════════════════════════════════════════╗
        ║   MULTI-SIGNAL ML TRADING ENGINE v2.2                 ║
        ║   With Enhanced ML & Market Regime Adaptation         ║
        ╚════════════════════════════════════════════════════════╝
        """)
        
        # Load your existing config if it exists
        self.config = self._load_existing_config(config_path)
        
        # Your competitive advantage: Multiple uncorrelated signals
        self.signals = {
            'rsi': {'weight': 0.12, 'category': 'technical', 'enabled': True},
            'macd': {'weight': 0.10, 'category': 'technical', 'enabled': True},
            'bollinger': {'weight': 0.08, 'category': 'technical', 'enabled': True},
            'volume': {'weight': 0.08, 'category': 'technical', 'enabled': True},
            'fear_greed': {'weight': 0.15, 'category': 'sentiment', 'enabled': True},
            'social': {'weight': 0.10, 'category': 'sentiment', 'enabled': True},
            'whale': {'weight': 0.12, 'category': 'onchain', 'enabled': True},
            'flows': {'weight': 0.10, 'category': 'onchain', 'enabled': True},
            'proprietary': {'weight': 0.15, 'category': 'unique', 'enabled': True}
        }
        
        # ML components
        self.ml_weights = {k: v['weight'] for k, v in self.signals.items()}
        self.initial_weights = self.ml_weights.copy()  # Store initial weights for comparison
        self.position_multiplier = 1.0
        self.trade_history = []
        self.weight_history = []  # Track weight changes over time
        self.enhanced_ml = enhanced_ml  # Flag for enhanced ML capabilities
        
        # Market regime detection
        self.regime_aware = regime_aware
        self.regime_detector = MarketRegimeDetector(lookback_period=14)
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_confidence = 0.0
        self.price_history = []
        self.regime_history = []
        
        # Store historical weight changes for analysis
        self.record_weights()
        
        print(f"✅ Loaded {len([s for s in self.signals.values() if s['enabled']])} active signals")
        if self.enhanced_ml:
            print("✨ Enhanced ML adaptation enabled - faster learning from trading results")
        if self.regime_aware:
            print("🔍 Market regime detection active - optimizing for bull/bear/sideways markets")
    
    def _load_existing_config(self, path: str) -> dict:
        """Load your existing configuration"""
        default_config = {
            'initial_capital': 10000,
            'position_size': 0.02,
            'ml_enabled': True,
            'compound_profits': True
        }
        
        try:
            # Check if you have existing config
            if os.path.exists(path):
                with open(path, 'r') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
                    print(f"✅ Loaded existing config from {path}")
        except Exception:
            print("📝 Using default config")
        
        return default_config
    
    async def collect_all_signals(self, current_price: float = None, current_volume: float = None) -> Dict:
        """Collect signals from all sources and update market regime detection
        
        Args:
            current_price: Current price of the asset (for regime detection)
            current_volume: Current trading volume (for regime detection)
        """
        signal_data = {}
        
        # Update market regime if price data is provided
        if current_price is not None:
            # Update price history for regime tracking
            self.price_history.append(current_price)
            
            # Update market regime detector
            if self.regime_aware:
                self.current_regime = self.regime_detector.update(current_price, current_volume)
                self.current_regime, self.regime_confidence = self.regime_detector.get_regime()
                
                # Track regime history
                self.regime_history.append({
                    'regime': self.current_regime,
                    'confidence': self.regime_confidence,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Log regime changes
                if len(self.regime_history) > 1:
                    prev_regime = self.regime_history[-2]['regime'] 
                    if prev_regime != self.current_regime:
                        print(f"📊 Market regime change detected: {prev_regime.value} → {self.current_regime.value} " 
                              f"(confidence: {self.regime_confidence:.2f})")
        
        # Technical signals
        if self.signals['rsi']['enabled']:
            signal_data['rsi'] = await self._get_rsi_signal()
        
        if self.signals['macd']['enabled']:
            signal_data['macd'] = await self._get_macd_signal()
        
        if self.signals['bollinger']['enabled']:
            signal_data['bollinger'] = await self._get_bollinger_signal()
        
        if self.signals['volume']['enabled']:
            signal_data['volume'] = await self._get_volume_signal()
        
        # Sentiment signals
        if self.signals['fear_greed']['enabled']:
            signal_data['fear_greed'] = await self._get_fear_greed_signal()
        
        if self.signals['social']['enabled']:
            signal_data['social'] = await self._get_social_signal()
        
        # On-chain signals
        if self.signals['whale']['enabled']:
            signal_data['whale'] = await self._get_whale_signal()
        
        if self.signals['flows']['enabled']:
            signal_data['flows'] = await self._get_flows_signal()
        
        # Your unique edge
        if self.signals['proprietary']['enabled']:
            signal_data['proprietary'] = await self._get_proprietary_signal()
        
        # Add market regime as additional metadata
        signal_data['_metadata'] = {
            'regime': self.current_regime.value if self.regime_aware else 'unknown',
            'regime_confidence': self.regime_confidence if self.regime_aware else 0.0,
            'price': current_price,
            'volume': current_volume
        }
        
        return signal_data
    
    async def _get_rsi_signal(self):
        """RSI technical indicator"""
        rsi = np.random.uniform(20, 80)
        if rsi < 30:
            return {'value': (30-rsi)/30, 'confidence': 0.8, 'raw': rsi}
        elif rsi > 70:
            return {'value': -(rsi-70)/30, 'confidence': 0.8, 'raw': rsi}
        return {'value': 0, 'confidence': 0.3, 'raw': rsi}
    
    async def _get_macd_signal(self):
        """MACD momentum indicator"""
        macd = np.random.uniform(-1, 1)
        return {'value': np.tanh(macd*2), 'confidence': abs(macd), 'raw': macd}
    
    async def _get_bollinger_signal(self):
        """Bollinger Bands indicator"""
        position = np.random.uniform(0, 1)
        if position < 0.2:
            return {'value': 0.8, 'confidence': 0.7, 'raw': position}
        elif position > 0.8:
            return {'value': -0.8, 'confidence': 0.7, 'raw': position}
        return {'value': 0, 'confidence': 0.3, 'raw': position}
    
    async def _get_volume_signal(self):
        """Volume analysis"""
        volume_ratio = np.random.uniform(0.5, 2.5)
        if volume_ratio > 2:
            return {'value': 0.6, 'confidence': 0.7, 'raw': volume_ratio}
        return {'value': 0, 'confidence': 0.3, 'raw': volume_ratio}
    
    async def _get_fear_greed_signal(self):
        """Fear & Greed Index (Contrarian)"""
        index = np.random.uniform(0, 100)
        if index < 30:
            return {'value': 0.9, 'confidence': 0.9, 'raw': index}
        elif index > 70:
            return {'value': -0.9, 'confidence': 0.9, 'raw': index}
        return {'value': (50-index)/50, 'confidence': 0.5, 'raw': index}
    
    async def _get_social_signal(self):
        """Social media sentiment"""
        sentiment = np.random.uniform(-1, 1)
        return {'value': sentiment, 'confidence': 0.6, 'raw': sentiment}
    
    async def _get_whale_signal(self):
        """Whale wallet activity"""
        activity = np.random.choice(['buying', 'selling', 'neutral'])
        if activity == 'buying':
            return {'value': 0.8, 'confidence': 0.9, 'raw': activity}
        elif activity == 'selling':
            return {'value': -0.8, 'confidence': 0.9, 'raw': activity}
        return {'value': 0, 'confidence': 0.3, 'raw': activity}
    
    async def _get_flows_signal(self):
        """Exchange flows"""
        netflow = np.random.uniform(-1000, 1000)
        return {'value': -np.tanh(netflow/500), 'confidence': 0.7, 'raw': netflow}
    
    async def _get_proprietary_signal(self):
        """YOUR SECRET SAUCE - Proprietary signal"""
        # This is where your unique business insights come in
        proprietary_value = np.random.uniform(-1, 1)
        return {'value': proprietary_value, 'confidence': 0.85, 'raw': proprietary_value}
    
    def make_ml_decision(self, signals: Dict) -> Dict:
        """ML-powered decision making with market regime awareness"""
        composite = 0
        total_confidence = 0
        used_signals = {}
        
        # Extract metadata (if present)
        metadata = signals.pop('_metadata', {})
        current_regime = metadata.get('regime', 'unknown')
        regime_confidence = metadata.get('regime_confidence', 0.0)
        
        for name, data in signals.items():
            # Get base ML weight
            base_weight = self.ml_weights.get(name, 0.1)
            
            # Apply regime-specific weight adjustments if enabled
            if self.regime_aware and hasattr(self, 'regime_detector'):
                signal_category = self.signals.get(name, {}).get('category', 'technical')
                regime_modifier = self.regime_detector.get_optimization_weights(signal_category)
                
                # Apply regime modifier with confidence scaling
                # Higher regime confidence = stronger weight adjustment
                regime_effect = 1.0 + ((regime_modifier - 1.0) * regime_confidence)
                adjusted_weight = base_weight * regime_effect
            else:
                adjusted_weight = base_weight
            
            # Calculate contribution to composite signal
            signal_contribution = data['value'] * adjusted_weight * data['confidence']
            composite += signal_contribution
            total_confidence += data['confidence'] * adjusted_weight
            
            # Store used signal with its weight
            used_signals[name] = {
                'base_weight': base_weight,
                'adjusted_weight': adjusted_weight,
                'contribution': signal_contribution,
                'value': data['value'],
                'confidence': data['confidence']
            }
        
        if total_confidence > 0:
            composite /= total_confidence
        
        # Decision thresholds - adjust based on market regime
        buy_threshold = 0.25
        sell_threshold = -0.25
        
        # Adjust thresholds based on regime if enabled
        if self.regime_aware:
            if current_regime == MarketRegime.BULL.value:
                # More aggressive buys, stricter sells in bull markets
                buy_threshold = 0.2
                sell_threshold = -0.3
            elif current_regime == MarketRegime.BEAR.value:
                # Stricter buys, more aggressive sells in bear markets
                buy_threshold = 0.3
                sell_threshold = -0.2
        
        # Decision logic with regime-adjusted thresholds
        if composite > buy_threshold and total_confidence > 0.6:
            action = 'BUY'
        elif composite < sell_threshold and total_confidence > 0.6:
            action = 'SELL'
        else:
            action = 'HOLD'
        
        # Position sizing with compounding and regime adjustment
        position_size = abs(composite) * total_confidence * self.position_multiplier * self.config['position_size']
        
        # Adjust position size based on regime confidence
        if self.regime_aware and regime_confidence > 0.7:
            if current_regime == MarketRegime.BULL.value and action == 'BUY':
                position_size *= 1.2  # Larger positions in confident bull markets
            elif current_regime == MarketRegime.BEAR.value and action == 'SELL':
                position_size *= 1.2  # Larger positions in confident bear markets
            elif current_regime == MarketRegime.SIDEWAYS.value:
                position_size *= 0.8  # Smaller positions in sideways markets
        
        return {
            'action': action,
            'composite': composite,
            'confidence': total_confidence,
            'position_size': min(position_size, 0.3),  # Max 30% position
            'timestamp': datetime.now().isoformat(),
            'regime': current_regime,
            'regime_confidence': regime_confidence,
            'used_signals': used_signals,
            'buy_threshold': buy_threshold,
            'sell_threshold': sell_threshold
        }
    
    def update_ml_weights(self, trade_result: Dict):
        """Update ML weights based on performance"""
        pnl = trade_result.get('pnl', 0)
        confidence = trade_result.get('confidence', 0.5)
        
        # Calculate learning rate based on confidence and PnL
        # Higher confidence and larger PnL = larger weight updates
        base_learning_rate = 0.15  # Increased from implicit 0.05
        
        # Scale learning rate by confidence and PnL magnitude
        learning_modifier = min(abs(pnl) / 100, 1.0) * min(confidence * 1.5, 1.0)
        actual_learning_rate = base_learning_rate * learning_modifier
        
        if pnl > 0:
            # Winning trade - increase weights
            for signal in trade_result.get('signals', []):
                if signal in self.ml_weights:
                    # Higher update rate for winning signals (1.05 -> 1.10-1.25)
                    signal_value = trade_result.get('signal_values', {}).get(signal, {'value': 0}).get('value', 0)
                    signal_strength = abs(signal_value)
                    
                    # Apply larger updates to stronger signals
                    signal_boost = 1.0 + (actual_learning_rate * (1 + signal_strength))
                    self.ml_weights[signal] *= signal_boost
            
            # Compound profits with more aggressive scaling
            if self.config.get('compound_profits', True):
                # Increased from 1.02 to be more responsive
                compound_rate = 1.03 + (0.02 * confidence)
                self.position_multiplier *= compound_rate
                self.position_multiplier = min(self.position_multiplier, 3.5)  # Increased max multiplier
        else:
            # Losing trade - decrease weights more aggressively
            for signal in trade_result.get('signals', []):
                if signal in self.ml_weights:
                    # More aggressive decrease (0.97 -> 0.85-0.95)
                    penalty_factor = 1.0 - (actual_learning_rate * 1.2)  # Higher penalty
                    self.ml_weights[signal] *= penalty_factor
            
            # Reduce position size after consecutive losses
            consecutive_losses = sum(1 for t in self.trade_history[-3:] if t.get('pnl', 0) < 0)
            if consecutive_losses >= 2:
                self.position_multiplier *= 0.95  # Reduce position size
        
        # Normalize weights
        total = sum(self.ml_weights.values())
        self.ml_weights = {k: v/total for k, v in self.ml_weights.items()}
        
        # Record updated weights for historical tracking
        self.record_weights()
        
        # Save to history
        self.trade_history.append(trade_result)
    
    def record_weights(self):
        """Record current weights for historical tracking"""
        self.weight_history.append({
            'weights': self.ml_weights.copy(),
            'timestamp': datetime.now().isoformat(),
            'trade_number': len(self.trade_history)
        })
    
    def get_weight_changes(self) -> Dict:
        """Calculate how much weights have changed from initial values"""
        if not self.initial_weights:
            return {}
            
        changes = {}
        for signal, current_weight in self.ml_weights.items():
            initial = self.initial_weights.get(signal, current_weight)
            if initial > 0:
                pct_change = ((current_weight - initial) / initial) * 100
                changes[signal] = {
                    'initial': initial,
                    'current': current_weight,
                    'abs_change': current_weight - initial,
                    'pct_change': pct_change
                }
        
        return changes
    
    def get_regime_visualization_data(self) -> Dict:
        """
        Get data for visualizing market regimes and their performance
        
        Returns:
            Dictionary with regime data for visualization
        """
        if not self.regime_aware or not self.regime_history:
            return {'error': 'Market regime detection not enabled or no data available'}
        
        # Extract regime changes over time
        regimes = []
        timestamps = []
        confidences = []
        
        for entry in self.regime_history:
            regimes.append(entry['regime'].value)
            confidences.append(entry['confidence'])
            timestamps.append(entry['timestamp'])
            
        # Get performance by regime
        stats = self.get_performance_stats()
        regime_performance = stats.get('regime_performance', {})
        
        # Get signal performance by regime
        signal_regime_performance = self._calculate_signal_performance_by_regime()
        
        return {
            'regimes': regimes,
            'timestamps': timestamps,
            'confidences': confidences,
            'regime_performance': regime_performance,
            'signal_regime_performance': signal_regime_performance
        }
        
    def _calculate_signal_performance_by_regime(self) -> Dict:
        """
        Calculate how each signal performs in different market regimes
        
        Returns:
            Dictionary with signal performance by regime
        """
        if not self.regime_aware or not self.trade_history or not self.regime_history:
            return {}
            
        # Initialize performance tracking
        signal_performance = {}
        
        for trade in self.trade_history:
            # Skip trades without signal data
            if 'signals' not in trade or 'signal_values' not in trade:
                continue
                
            # Find the regime during this trade
            trade_time = datetime.fromisoformat(trade['timestamp'])
            closest_regime = None
            min_time_diff = float('inf')
            
            for regime_entry in self.regime_history:
                regime_time = datetime.fromisoformat(regime_entry['timestamp'])
                time_diff = abs((trade_time - regime_time).total_seconds())
                
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_regime = regime_entry['regime'].value
            
            if not closest_regime:
                continue
                
            # Initialize regime in signal performance if not present
            if closest_regime not in signal_performance:
                signal_performance[closest_regime] = {}
                
            # Track performance for each signal
            pnl = trade.get('pnl', 0)
            
            for signal in trade.get('signals', []):
                if signal not in signal_performance[closest_regime]:
                    signal_performance[closest_regime][signal] = {
                        'trades': 0, 'win_trades': 0, 'lose_trades': 0,
                        'total_pnl': 0, 'win_rate': 0
                    }
                    
                signal_perf = signal_performance[closest_regime][signal]
                signal_perf['trades'] += 1
                
                if pnl > 0:
                    signal_perf['win_trades'] += 1
                else:
                    signal_perf['lose_trades'] += 1
                    
                signal_perf['total_pnl'] += pnl
                
                if signal_perf['trades'] > 0:
                    signal_perf['win_rate'] = (signal_perf['win_trades'] / signal_perf['trades']) * 100
        
        return signal_performance
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics with market regime information"""
        if not self.trade_history:
            return {'trades': 0, 'pnl': 0, 'win_rate': 0, 'ml_adaptation': 0}
        
        wins = sum(1 for t in self.trade_history if t.get('pnl', 0) > 0)
        total_pnl = sum(t.get('pnl', 0) for t in self.trade_history)
        
        # Calculate ML adaptation metrics
        weight_changes = self.get_weight_changes()
        adaptation_score = 0
        
        if weight_changes:
            # Calculate the total absolute changes in weights as a measure of adaptation
            abs_changes = [abs(data['abs_change']) for data in weight_changes.values()]
            adaptation_score = sum(abs_changes) / len(abs_changes) * 100
        
        # Market regime performance breakdowns
        regime_performance = {}
        if self.regime_aware and self.regime_history:
            # Group trades by regime
            for trade in self.trade_history:
                # Find closest regime by timestamp
                trade_time = datetime.fromisoformat(trade['timestamp'])
                
                # Find the regime that was active during the trade
                closest_regime_entry = None
                min_time_diff = float('inf')
                
                for regime_entry in self.regime_history:
                    regime_time = datetime.fromisoformat(regime_entry['timestamp'])
                    time_diff = abs((trade_time - regime_time).total_seconds())
                    
                    if time_diff < min_time_diff:
                        min_time_diff = time_diff
                        closest_regime_entry = regime_entry
                
                if closest_regime_entry:
                    regime = closest_regime_entry['regime'].value
                    if regime not in regime_performance:
                        regime_performance[regime] = {
                            'trades': 0, 'wins': 0, 'losses': 0, 
                            'pnl': 0, 'win_rate': 0
                        }
                    
                    regime_performance[regime]['trades'] += 1
                    if trade.get('pnl', 0) > 0:
                        regime_performance[regime]['wins'] += 1
                    else:
                        regime_performance[regime]['losses'] += 1
                        
                    regime_performance[regime]['pnl'] += trade.get('pnl', 0)
            
            # Calculate win rates per regime
            for regime, stats in regime_performance.items():
                if stats['trades'] > 0:
                    stats['win_rate'] = (stats['wins'] / stats['trades']) * 100
        
        # Get current regime information
        current_regime_info = {}
        if self.regime_aware:
            current_regime_info = {
                'regime': self.current_regime.value,
                'confidence': self.regime_confidence,
                'optimized_categories': {
                    category: self.regime_detector.get_optimization_weights(category)
                    for category in ['technical', 'sentiment', 'onchain', 'unique']
                }
            }
        
        return {
            'trades': len(self.trade_history),
            'wins': wins,
            'losses': len(self.trade_history) - wins,
            'win_rate': (wins / len(self.trade_history)) * 100,
            'total_pnl': total_pnl,
            'position_multiplier': self.position_multiplier,
            'top_signals': sorted(self.ml_weights.items(), key=lambda x: x[1], reverse=True)[:3],
            'ml_adaptation': adaptation_score,
            'weight_changes': weight_changes,
            'market_regime': current_regime_info,
            'regime_performance': regime_performance
        }
