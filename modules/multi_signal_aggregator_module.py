"""
Multi-Signal Aggregator Module

This module combines signals from multiple uncorrelated indicators (RSI, MACD, Bollinger Bands, 
Volume Profile, Sentiment Analysis) using weighted aggregation and correlation analysis to make 
final trading decisions.
"""

from typing import Dict, Any, List, Tuple, Optional
import math
import numpy as np
from core.module_manager import Module


class MultiSignalAggregatorModule(Module):
    """Multi-signal aggregation and decision-making module."""
    
    VERSION = "1.0.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.signal_weights = config.get('signal_weights', {
            'RSI': 0.20,
            'MACD': 0.25,
            'BollingerBands': 0.20,
            'VolumeProfile': 0.15,
            'SentimentAnalysis': 0.20
        }) if config else {
            'RSI': 0.20,
            'MACD': 0.25,
            'BollingerBands': 0.20,
            'VolumeProfile': 0.15,
            'SentimentAnalysis': 0.20
        }
        self.consensus_threshold = config.get('consensus_threshold', 0.6) if config else 0.6
        self.confidence_multiplier = config.get('confidence_multiplier', 1.2) if config else 1.2
        self.min_signals_required = config.get('min_signals_required', 2) if config else 2
        
    def get_schema(self) -> Dict[str, Any]:
        return {
            'input': {
                'signals': 'dict of individual signal results from each module',
                'price_data': 'current price data for context',
                'signal_weights': 'dict (optional, custom weights for each signal)',
                'consensus_threshold': 'float (optional, minimum consensus for strong signals)',
                'include_correlation_analysis': 'boolean (optional, default: true)'
            },
            'output': {
                'final_signal': 'string (BUY/SELL/HOLD)',
                'final_confidence': 'float (0-1)',
                'consensus_score': 'float (0-1)',
                'signal_strength': 'string (STRONG/MODERATE/WEAK)',
                'individual_signals': 'dict (processed individual signals)',
                'signal_consensus': {
                    'buy_signals': 'integer',
                    'sell_signals': 'integer', 
                    'hold_signals': 'integer',
                    'total_signals': 'integer'
                },
                'correlation_analysis': {
                    'signal_correlation_matrix': 'dict (if enabled)',
                    'diversification_score': 'float',
                    'independence_verified': 'boolean'
                },
                'decision_factors': 'list of factors influencing the final decision',
                'risk_assessment': {
                    'overall_risk': 'string (LOW/MEDIUM/HIGH)',
                    'conflicting_signals': 'boolean',
                    'signal_divergence': 'float'
                },
                'metadata': {
                    'signals_processed': 'integer',
                    'weights_used': 'dict'
                }
            }
        }
        
    def normalize_signal_to_score(self, signal: str, confidence: float) -> float:
        """
        Convert signal/confidence pair to a numerical score.
        
        Returns:
            Score between -1 (strong sell) and 1 (strong buy)
        """
        if signal == 'BUY':
            return confidence
        elif signal == 'SELL':
            return -confidence
        else:  # HOLD
            return 0.0
            
    def calculate_signal_consensus(self, signal_scores: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate consensus among signals.
        
        Returns:
            Dictionary with consensus statistics
        """
        buy_count = 0
        sell_count = 0
        hold_count = 0
        
        buy_confidence_sum = 0.0
        sell_confidence_sum = 0.0
        
        for module, signal_data in signal_scores.items():
            signal = signal_data['signal']
            confidence = signal_data['confidence']
            
            if signal == 'BUY':
                buy_count += 1
                buy_confidence_sum += confidence
            elif signal == 'SELL':
                sell_count += 1
                sell_confidence_sum += confidence
            else:
                hold_count += 1
                
        total_signals = buy_count + sell_count + hold_count
        
        # Calculate consensus scores
        buy_consensus = (buy_count / total_signals) if total_signals > 0 else 0
        sell_consensus = (sell_count / total_signals) if total_signals > 0 else 0
        
        # Overall consensus score (how much agreement there is)
        max_consensus = max(buy_consensus, sell_consensus, hold_count / total_signals if total_signals > 0 else 0)
        
        return {
            'buy_signals': buy_count,
            'sell_signals': sell_count,
            'hold_signals': hold_count,
            'total_signals': total_signals,
            'buy_consensus': buy_consensus,
            'sell_consensus': sell_consensus,
            'overall_consensus': max_consensus,
            'avg_buy_confidence': (buy_confidence_sum / buy_count) if buy_count > 0 else 0,
            'avg_sell_confidence': (sell_confidence_sum / sell_count) if sell_count > 0 else 0
        }
        
    def calculate_weighted_score(self, signal_scores: Dict[str, Dict[str, Any]], 
                               weights: Dict[str, float]) -> float:
        """
        Calculate weighted aggregate score from individual signals.
        
        Returns:
            Weighted score between -1 and 1
        """
        weighted_sum = 0.0
        total_weight = 0.0
        
        for module, signal_data in signal_scores.items():
            if module in weights:
                score = self.normalize_signal_to_score(signal_data['signal'], signal_data['confidence'])
                weight = weights[module]
                
                weighted_sum += score * weight
                total_weight += weight
                
        return weighted_sum / total_weight if total_weight > 0 else 0.0
        
    def analyze_signal_correlation(self, signal_scores: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze correlation between signals to verify they are uncorrelated.
        
        Returns:
            Dictionary with correlation analysis
        """
        # Convert signals to numerical scores for correlation analysis
        scores = {}
        modules = list(signal_scores.keys())
        
        for module, signal_data in signal_scores.items():
            scores[module] = self.normalize_signal_to_score(signal_data['signal'], signal_data['confidence'])
            
        # Calculate pairwise correlations
        correlation_matrix = {}
        correlations = []
        
        for i, module1 in enumerate(modules):
            correlation_matrix[module1] = {}
            for j, module2 in enumerate(modules):
                if i == j:
                    correlation = 1.0
                else:
                    # Simple correlation approximation (would need historical data for true correlation)
                    score1 = scores[module1]
                    score2 = scores[module2]
                    
                    # If signals agree strongly, correlation is higher
                    if abs(score1) > 0.5 and abs(score2) > 0.5:
                        if (score1 > 0 and score2 > 0) or (score1 < 0 and score2 < 0):
                            correlation = 0.7  # Positive correlation
                        else:
                            correlation = -0.3  # Negative correlation
                    else:
                        correlation = 0.1  # Low correlation
                        
                correlation_matrix[module1][module2] = correlation
                if i < j:  # Only count each pair once
                    correlations.append(abs(correlation))
                    
        # Calculate diversification score (lower correlation = better diversification)
        avg_correlation = sum(correlations) / len(correlations) if correlations else 0
        diversification_score = max(0, 1 - avg_correlation)  # Higher score = better diversification
        
        # Check if signals are sufficiently independent
        independence_verified = avg_correlation < 0.5  # Threshold for independence
        
        return {
            'signal_correlation_matrix': correlation_matrix,
            'average_correlation': avg_correlation,
            'diversification_score': diversification_score,
            'independence_verified': independence_verified,
            'correlation_pairs': len(correlations)
        }
        
    def assess_risk(self, signal_scores: Dict[str, Dict[str, Any]], 
                   consensus: Dict[str, Any], final_confidence: float) -> Dict[str, Any]:
        """
        Assess overall risk of the trading decision.
        
        Returns:
            Risk assessment dictionary
        """
        # Check for conflicting signals
        conflicting_signals = (consensus['buy_signals'] > 0 and consensus['sell_signals'] > 0)
        
        # Calculate signal divergence (how much signals disagree)
        signal_scores_list = [
            self.normalize_signal_to_score(data['signal'], data['confidence']) 
            for data in signal_scores.values()
        ]
        
        if len(signal_scores_list) > 1:
            signal_std = np.std(signal_scores_list)
            signal_divergence = min(1.0, signal_std / 0.5)  # Normalize to 0-1 scale
        else:
            signal_divergence = 0.0
            
        # Determine overall risk level
        if conflicting_signals and signal_divergence > 0.5:
            overall_risk = 'HIGH'
        elif signal_divergence > 0.3 or final_confidence < 0.4:
            overall_risk = 'MEDIUM'  
        else:
            overall_risk = 'LOW'
            
        return {
            'overall_risk': overall_risk,
            'conflicting_signals': conflicting_signals,
            'signal_divergence': signal_divergence,
            'confidence_level': 'HIGH' if final_confidence > 0.7 else 'MEDIUM' if final_confidence > 0.4 else 'LOW'
        }
        
    def generate_decision_factors(self, signal_scores: Dict[str, Dict[str, Any]], 
                                consensus: Dict[str, Any], final_signal: str) -> List[str]:
        """
        Generate human-readable factors that influenced the decision.
        
        Returns:
            List of decision factor descriptions
        """
        factors = []
        
        # Consensus factors
        if consensus['overall_consensus'] > 0.7:
            factors.append(f"Strong consensus: {consensus['buy_signals'] + consensus['sell_signals']} out of {consensus['total_signals']} signals agree")
            
        # Individual signal contributions
        strong_signals = []
        for module, data in signal_scores.items():
            if data['confidence'] > 0.6 and data['signal'] != 'HOLD':
                strong_signals.append(f"{module}: {data['signal']} ({data['confidence']:.2f} confidence)")
                
        if strong_signals:
            factors.append(f"Strong individual signals: {'; '.join(strong_signals)}")
            
        # Signal type diversity
        signal_types = set()
        for module, data in signal_scores.items():
            if 'metadata' in data and 'module_info' in data['metadata']:
                signal_type = data['metadata']['module_info'].get('signal_type', 'unknown')
                signal_types.add(signal_type)
                
        if len(signal_types) > 2:
            factors.append(f"Diverse signal types: {len(signal_types)} different analytical approaches")
            
        # Final decision reasoning
        if final_signal == 'BUY':
            factors.append("Net bullish sentiment across multiple indicators")
        elif final_signal == 'SELL':
            factors.append("Net bearish sentiment across multiple indicators")
        else:
            factors.append("Mixed or weak signals suggest holding position")
            
        return factors
        
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process multiple signals and generate aggregated trading decision."""
        signals = data.get('signals', {})
        if not signals:
            raise ValueError("signals dictionary is required")
            
        # Extract configuration
        signal_weights = data.get('signal_weights', self.signal_weights)
        consensus_threshold = data.get('consensus_threshold', self.consensus_threshold)
        include_correlation = data.get('include_correlation_analysis', True)
        price_data = data.get('price_data')
        
        try:
            # Validate and filter signals
            valid_signals = {}
            for module, signal_data in signals.items():
                if isinstance(signal_data, dict) and 'signal' in signal_data and 'confidence' in signal_data:
                    valid_signals[module] = signal_data
                    
            if len(valid_signals) < self.min_signals_required:
                return {
                    'final_signal': 'HOLD',
                    'final_confidence': 0.0,
                    'consensus_score': 0.0,
                    'signal_strength': 'WEAK',
                    'individual_signals': valid_signals,
                    'signal_consensus': {
                        'buy_signals': 0,
                        'sell_signals': 0,
                        'hold_signals': 0,
                        'total_signals': len(valid_signals)
                    },
                    'correlation_analysis': {},
                    'decision_factors': ['Insufficient signals for reliable decision'],
                    'risk_assessment': {
                        'overall_risk': 'HIGH',
                        'conflicting_signals': False,
                        'signal_divergence': 0.0
                    },
                    'metadata': {
                        'signals_processed': len(valid_signals),
                        'weights_used': signal_weights,
                        'error': f'Only {len(valid_signals)} signals provided, minimum {self.min_signals_required} required'
                    }
                }
                
            # Calculate consensus
            consensus = self.calculate_signal_consensus(valid_signals)
            
            # Calculate weighted score
            weighted_score = self.calculate_weighted_score(valid_signals, signal_weights)
            
            # Determine final signal and confidence
            final_confidence = abs(weighted_score)
            
            if weighted_score > 0.1 and consensus['overall_consensus'] >= consensus_threshold:
                final_signal = 'BUY'
                if consensus['buy_consensus'] > 0.6:
                    final_confidence *= self.confidence_multiplier
            elif weighted_score < -0.1 and consensus['overall_consensus'] >= consensus_threshold:
                final_signal = 'SELL'  
                if consensus['sell_consensus'] > 0.6:
                    final_confidence *= self.confidence_multiplier
            else:
                final_signal = 'HOLD'
                final_confidence *= 0.5  # Reduce confidence for hold signals
                
            # Ensure confidence stays within bounds
            final_confidence = max(0.0, min(1.0, final_confidence))
            
            # Determine signal strength
            if final_confidence >= 0.7 and consensus['overall_consensus'] >= 0.7:
                signal_strength = 'STRONG'
            elif final_confidence >= 0.4:
                signal_strength = 'MODERATE'
            else:
                signal_strength = 'WEAK'
                
            # Correlation analysis (if enabled)
            correlation_analysis = {}
            if include_correlation:
                correlation_analysis = self.analyze_signal_correlation(valid_signals)
                
                # Adjust confidence based on diversification
                diversification_bonus = correlation_analysis.get('diversification_score', 0) * 0.1
                final_confidence = min(1.0, final_confidence + diversification_bonus)
                
            # Risk assessment
            risk_assessment = self.assess_risk(valid_signals, consensus, final_confidence)
            
            # Generate decision factors
            decision_factors = self.generate_decision_factors(valid_signals, consensus, final_signal)
            
            result = {
                'final_signal': final_signal,
                'final_confidence': final_confidence,
                'consensus_score': consensus['overall_consensus'],
                'weighted_score': weighted_score,
                'signal_strength': signal_strength,
                'individual_signals': valid_signals,
                'signal_consensus': {
                    'buy_signals': consensus['buy_signals'],
                    'sell_signals': consensus['sell_signals'],
                    'hold_signals': consensus['hold_signals'],
                    'total_signals': consensus['total_signals']
                },
                'correlation_analysis': correlation_analysis,
                'decision_factors': decision_factors,
                'risk_assessment': risk_assessment,
                'current_price': price_data.get('close') if price_data else None,
                'trading_recommendation': {
                    'action': final_signal,
                    'strength': signal_strength,
                    'risk_level': risk_assessment['overall_risk'],
                    'position_size_suggestion': self._suggest_position_size(final_confidence, risk_assessment['overall_risk'])
                },
                'metadata': {
                    'signals_processed': len(valid_signals),
                    'weights_used': signal_weights,
                    'consensus_threshold_used': consensus_threshold,
                    'min_signals_met': len(valid_signals) >= self.min_signals_required,
                    'module_info': {
                        'name': self.name,
                        'version': self.version,
                        'signal_type': 'multi_signal_aggregation'
                    }
                }
            }
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Failed to process multi-signal aggregation: {str(e)}")
            
    def _suggest_position_size(self, confidence: float, risk_level: str) -> str:
        """Suggest position size based on confidence and risk."""
        if risk_level == 'HIGH':
            return 'SMALL (10-25%)'
        elif risk_level == 'MEDIUM':
            if confidence > 0.7:
                return 'MEDIUM (25-50%)'
            else:
                return 'SMALL (10-25%)'
        else:  # LOW risk
            if confidence > 0.8:
                return 'LARGE (50-75%)'
            elif confidence > 0.6:
                return 'MEDIUM (25-50%)'
            else:
                return 'SMALL (10-25%)'
                
    def backtest_multi_signal_strategy(self, historical_data: List[Dict[str, Any]], 
                                     signal_history: Dict[str, List[Dict[str, Any]]], 
                                     initial_balance: float = 10000) -> Dict[str, Any]:
        """
        Backtest the multi-signal aggregation strategy.
        
        Args:
            historical_data: Historical price data
            signal_history: Historical signals from each module
            initial_balance: Starting balance
            
        Returns:
            Backtesting results
        """
        if not historical_data or not signal_history:
            raise ValueError("Historical data and signal history are required for backtesting")
            
        balance = initial_balance
        position = 0
        trades = []
        signals_history = []
        
        # Find the minimum length across all signal histories
        min_length = min(len(historical_data), min(len(signals) for signals in signal_history.values()))
        
        for i in range(min_length):
            # Collect signals from all modules for this time period
            current_signals = {}
            for module, module_signals in signal_history.items():
                if i < len(module_signals):
                    current_signals[module] = module_signals[i]
                    
            if len(current_signals) < self.min_signals_required:
                continue
                
            # Process aggregated signal
            result = self.process({
                'signals': current_signals,
                'price_data': historical_data[i]
            })
            
            signal = result['final_signal']
            price = historical_data[i].get('close', historical_data[i].get('price', 0))
            confidence = result['final_confidence']
            
            signals_history.append({
                'date': i,
                'price': price,
                'final_signal': signal,
                'confidence': confidence,
                'consensus_score': result['consensus_score'],
                'individual_signals': len(current_signals)
            })
            
            # Trade on moderate to high confidence signals
            if confidence >= 0.5:
                if signal == 'BUY' and position == 0:
                    position = balance / price
                    balance = 0
                    trades.append({
                        'type': 'BUY',
                        'price': price,
                        'confidence': confidence,
                        'consensus_score': result['consensus_score'],
                        'position': position
                    })
                elif signal == 'SELL' and position > 0:
                    balance = position * price
                    pnl = balance - initial_balance
                    trades.append({
                        'type': 'SELL',
                        'price': price,
                        'confidence': confidence,
                        'consensus_score': result['consensus_score'],
                        'pnl': pnl
                    })
                    position = 0
                    
        # Calculate final portfolio value
        final_price = historical_data[-1]['close'] if 'close' in historical_data[-1] else historical_data[-1]['price']
        final_value = balance + (position * final_price)
        
        return {
            'initial_balance': initial_balance,
            'final_value': final_value,
            'total_return': final_value - initial_balance,
            'return_percentage': ((final_value - initial_balance) / initial_balance) * 100,
            'total_trades': len(trades),
            'total_signals': len(signals_history),
            'high_confidence_trades': len([t for t in trades if t.get('confidence', 0) > 0.7]),
            'high_consensus_trades': len([t for t in trades if t.get('consensus_score', 0) > 0.6]),
            'signal_accuracy': self._calculate_signal_accuracy(signals_history, [p['close'] if 'close' in p else p['price'] for p in historical_data]),
            'trades': trades,
            'signals_history': signals_history[-10:]  # Last 10 signals for inspection
        }
        
    def _calculate_signal_accuracy(self, signals_history: List[Dict], prices: List[float]) -> float:
        """Calculate the accuracy of aggregated signals."""
        if len(signals_history) < 2:
            return 0.0
            
        correct_signals = 0
        total_actionable_signals = 0
        
        for i, signal_data in enumerate(signals_history):
            if i >= len(prices) - 1:
                break
                
            if signal_data['final_signal'] in ['BUY', 'SELL']:
                total_actionable_signals += 1
                current_price = prices[i]
                future_price = prices[min(i + 5, len(prices) - 1)]
                price_change = future_price - current_price
                
                if signal_data['final_signal'] == 'BUY' and price_change > 0:
                    correct_signals += 1
                elif signal_data['final_signal'] == 'SELL' and price_change < 0:
                    correct_signals += 1
                    
        return correct_signals / total_actionable_signals if total_actionable_signals > 0 else 0.0