"""
Bollinger Bands Module

This module implements Bollinger Bands calculation and signal generation, providing
a volatility-based signal that is uncorrelated to RSI and MACD.
"""

from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import math
from core.module_manager import Module


class BollingerBandsModule(Module):
    """Bollinger Bands calculation and signal generation module."""
    
    VERSION = "1.0.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.period = config.get('period', 20) if config else 20
        self.std_multiplier = config.get('std_multiplier', 2.0) if config else 2.0
        self.squeeze_threshold = config.get('squeeze_threshold', 0.1) if config else 0.1
        
    def get_schema(self) -> Dict[str, Any]:
        return {
            'input': {
                'price_data': 'list of price records with close prices',
                'period': 'integer (optional, default: 20)',
                'std_multiplier': 'float (optional, default: 2.0)',
                'squeeze_threshold': 'float (optional, default: 0.1)'
            },
            'output': {
                'upper_band': 'float',
                'middle_band': 'float (SMA)',
                'lower_band': 'float',
                'band_width': 'float',
                'percent_b': 'float',
                'signal': 'string (BUY/SELL/HOLD)',
                'confidence': 'float (0-1)',
                'volatility_state': 'string (SQUEEZE/EXPANSION/NORMAL)',
                'position_in_bands': 'string (ABOVE_UPPER/BELOW_LOWER/WITHIN_BANDS)',
                'metadata': {
                    'period_used': 'integer',
                    'std_multiplier_used': 'float',
                    'data_points': 'integer'
                }
            }
        }
        
    def calculate_bollinger_bands(self, prices: pd.Series, period: int, 
                                 std_multiplier: float) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Returns:
            Tuple of (Upper Band, Middle Band/SMA, Lower Band, Band Width)
        """
        # Middle Band = Simple Moving Average
        middle_band = prices.rolling(window=period).mean()
        
        # Standard Deviation
        std_dev = prices.rolling(window=period).std()
        
        # Upper and Lower Bands
        upper_band = middle_band + (std_dev * std_multiplier)
        lower_band = middle_band - (std_dev * std_multiplier)
        
        # Band Width (normalized)
        band_width = (upper_band - lower_band) / middle_band
        
        return upper_band, middle_band, lower_band, band_width
        
    def calculate_percent_b(self, price: float, upper_band: float, 
                           middle_band: float, lower_band: float) -> float:
        """
        Calculate %B (Percent B) - position within the bands.
        
        %B = (Price - Lower Band) / (Upper Band - Lower Band)
        
        Values:
        - > 1: Above upper band
        - 0.8-1: Near upper band
        - 0.2-0.8: Within bands
        - 0-0.2: Near lower band
        - < 0: Below lower band
        """
        if upper_band == lower_band:  # Avoid division by zero
            return 0.5
            
        return (price - lower_band) / (upper_band - lower_band)
        
    def detect_squeeze(self, band_width_current: float, band_width_history: pd.Series, 
                      threshold: float) -> bool:
        """
        Detect Bollinger Band squeeze (low volatility period).
        
        A squeeze occurs when band width is at or near historical lows.
        """
        if len(band_width_history) < 20:  # Need enough history
            return False
            
        # Get the 20-period percentile of band width
        historical_low = band_width_history.rolling(window=20).quantile(threshold)
        
        return band_width_current <= historical_low.iloc[-1]
        
    def generate_signal(self, current_price: float, upper_band: float, 
                       middle_band: float, lower_band: float, percent_b: float,
                       previous_percent_b: float, band_width: float,
                       is_squeeze: bool, price_trend: str) -> Tuple[str, float, str, str]:
        """
        Generate trading signal based on Bollinger Bands analysis.
        
        Returns:
            Tuple of (signal, confidence, volatility_state, position_in_bands)
        """
        if any(math.isnan(x) for x in [current_price, upper_band, middle_band, lower_band]):
            return 'HOLD', 0.0, 'NORMAL', 'WITHIN_BANDS'
            
        signal = 'HOLD'
        confidence = 0.0
        
        # Determine position relative to bands
        if percent_b > 1.0:
            position_in_bands = 'ABOVE_UPPER'
        elif percent_b < 0.0:
            position_in_bands = 'BELOW_LOWER'
        else:
            position_in_bands = 'WITHIN_BANDS'
            
        # Determine volatility state
        if is_squeeze:
            volatility_state = 'SQUEEZE'
        elif band_width > band_width * 1.5:  # Relative expansion check
            volatility_state = 'EXPANSION'
        else:
            volatility_state = 'NORMAL'
            
        # Signal Generation Logic
        
        # 1. Band Touch/Bounce Strategy
        if percent_b <= 0.05:  # Price near or below lower band
            if previous_percent_b < percent_b:  # Price bouncing back up
                signal = 'BUY'
                confidence = min(1.0, (0.05 - percent_b) * 20)  # Higher confidence for deeper penetration
                
        elif percent_b >= 0.95:  # Price near or above upper band
            if previous_percent_b > percent_b:  # Price falling back down
                signal = 'SELL'
                confidence = min(1.0, (percent_b - 0.95) * 20)
                
        # 2. Squeeze Breakout Strategy
        elif volatility_state == 'SQUEEZE':
            # During squeeze, wait for breakout direction
            if percent_b > 0.6 and price_trend == 'UPWARD':
                signal = 'BUY'
                confidence = 0.6  # Moderate confidence during squeeze
            elif percent_b < 0.4 and price_trend == 'DOWNWARD':
                signal = 'SELL'
                confidence = 0.6
                
        # 3. Mean Reversion Strategy (when not in squeeze)
        elif volatility_state != 'SQUEEZE':
            if 0.7 < percent_b < 0.95:  # Price in upper region, potential reversal
                signal = 'SELL'
                confidence = min(0.8, (percent_b - 0.7) * 4)
            elif 0.05 < percent_b < 0.3:  # Price in lower region, potential reversal
                signal = 'BUY'
                confidence = min(0.8, (0.3 - percent_b) * 4)
                
        # 4. Middle Band Cross Strategy
        if signal == 'HOLD':
            if current_price > middle_band and percent_b > 0.5:
                if previous_percent_b <= 0.5:  # Just crossed above middle band
                    signal = 'BUY'
                    confidence = 0.4
            elif current_price < middle_band and percent_b < 0.5:
                if previous_percent_b >= 0.5:  # Just crossed below middle band
                    signal = 'SELL'
                    confidence = 0.4
                    
        return signal, confidence, volatility_state, position_in_bands
        
    def calculate_price_trend(self, prices: List[float], window: int = 5) -> str:
        """Calculate short-term price trend."""
        if len(prices) < window:
            return 'NEUTRAL'
            
        recent_prices = prices[-window:]
        if len(recent_prices) < 2:
            return 'NEUTRAL'
            
        # Simple linear trend
        x = list(range(len(recent_prices)))
        y = recent_prices
        
        # Calculate slope
        n = len(recent_prices)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 'NEUTRAL'
            
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Determine trend based on slope
        threshold = abs(sum(y)) / len(y) * 0.001  # 0.1% of average price as threshold
        
        if slope > threshold:
            return 'UPWARD'
        elif slope < -threshold:
            return 'DOWNWARD'
        else:
            return 'NEUTRAL'
            
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process price data and generate Bollinger Bands signals."""
        price_data = data.get('price_data', [])
        if not price_data:
            raise ValueError("price_data is required")
            
        # Extract configuration
        period = data.get('period', self.period)
        std_multiplier = data.get('std_multiplier', self.std_multiplier)
        squeeze_threshold = data.get('squeeze_threshold', self.squeeze_threshold)
        
        try:
            # Extract close prices from price data
            if isinstance(price_data[0], dict):
                closes = []
                for record in price_data:
                    if 'close' in record:
                        closes.append(float(record['close']))
                    elif 'price' in record:
                        closes.append(float(record['price']))
                    else:
                        raise ValueError("No 'close' or 'price' field found in price data")
            elif isinstance(price_data[0], (list, tuple)):
                # Data is in OHLCV format - use close price (index 4)
                closes = [float(row[4]) for row in price_data if len(row) >= 5]
            else:
                # Assume it's a list of close prices
                closes = [float(price) for price in price_data]
                
            # Need enough data for Bollinger Bands calculation
            min_periods = max(period + 10, 30)  # Need extra for standard deviation
            if len(closes) < min_periods:
                return {
                    'upper_band': float('nan'),
                    'middle_band': float('nan'),
                    'lower_band': float('nan'),
                    'band_width': float('nan'),
                    'percent_b': float('nan'),
                    'signal': 'HOLD',
                    'confidence': 0.0,
                    'volatility_state': 'NORMAL',
                    'position_in_bands': 'WITHIN_BANDS',
                    'current_price': closes[-1] if closes else float('nan'),
                    'metadata': {
                        'period_used': period,
                        'std_multiplier_used': std_multiplier,
                        'data_points': len(closes),
                        'min_required': min_periods,
                        'error': 'Insufficient data points for Bollinger Bands calculation'
                    }
                }
                
            # Calculate Bollinger Bands
            close_series = pd.Series(closes, dtype=float)
            upper_band, middle_band, lower_band, band_width = self.calculate_bollinger_bands(
                close_series, period, std_multiplier
            )
            
            # Get current values
            current_price = closes[-1]
            upper_current = float(upper_band.iloc[-1])
            middle_current = float(middle_band.iloc[-1])
            lower_current = float(lower_band.iloc[-1])
            width_current = float(band_width.iloc[-1])
            
            # Calculate %B
            percent_b_current = self.calculate_percent_b(
                current_price, upper_current, middle_current, lower_current
            )
            
            # Get previous %B for trend analysis
            if len(closes) >= 2:
                prev_price = closes[-2]
                if len(upper_band) >= 2:
                    upper_prev = float(upper_band.iloc[-2])
                    middle_prev = float(middle_band.iloc[-2])
                    lower_prev = float(lower_band.iloc[-2])
                    percent_b_prev = self.calculate_percent_b(
                        prev_price, upper_prev, middle_prev, lower_prev
                    )
                else:
                    percent_b_prev = percent_b_current
            else:
                percent_b_prev = percent_b_current
                
            # Detect squeeze
            is_squeeze = self.detect_squeeze(width_current, band_width, squeeze_threshold)
            
            # Calculate price trend
            price_trend = self.calculate_price_trend(closes)
            
            # Generate signal
            signal, confidence, volatility_state, position_in_bands = self.generate_signal(
                current_price, upper_current, middle_current, lower_current,
                percent_b_current, percent_b_prev, width_current, is_squeeze, price_trend
            )
            
            result = {
                'upper_band': upper_current,
                'middle_band': middle_current,
                'lower_band': lower_current,
                'band_width': width_current,
                'percent_b': percent_b_current,
                'signal': signal,
                'confidence': confidence,
                'volatility_state': volatility_state,
                'position_in_bands': position_in_bands,
                'current_price': current_price,
                'analysis': {
                    'price_vs_middle': 'ABOVE' if current_price > middle_current else 'BELOW',
                    'band_squeeze_detected': is_squeeze,
                    'price_trend': price_trend,
                    'band_width_percentile': min(100, width_current * 1000),  # Rough percentile estimate
                    'reversal_probability': abs(0.5 - percent_b_current) * 2  # Distance from middle
                },
                'metadata': {
                    'period_used': period,
                    'std_multiplier_used': std_multiplier,
                    'squeeze_threshold_used': squeeze_threshold,
                    'data_points': len(closes),
                    'calculation_window': min_periods,
                    'module_info': {
                        'name': self.name,
                        'version': self.version,
                        'signal_type': 'volatility_indicator'
                    }
                }
            }
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Failed to process Bollinger Bands calculation: {str(e)}")
            
    def backtest_strategy(self, historical_data: List[Dict[str, Any]], 
                         initial_balance: float = 10000) -> Dict[str, Any]:
        """Simple backtesting functionality for Bollinger Bands strategy."""
        if not historical_data:
            raise ValueError("Historical data is required for backtesting")
            
        balance = initial_balance
        position = 0
        trades = []
        signals_history = []
        
        min_periods = max(self.period + 10, 30)
        
        for i in range(min_periods, len(historical_data)):
            window_data = historical_data[:i+1]
            result = self.process({'price_data': window_data})
            
            if math.isnan(result['upper_band']):
                continue
                
            signal = result['signal']
            price = result['current_price']
            confidence = result['confidence']
            
            signals_history.append({
                'date': i,
                'price': price,
                'upper_band': result['upper_band'],
                'middle_band': result['middle_band'],
                'lower_band': result['lower_band'],
                'percent_b': result['percent_b'],
                'signal': signal,
                'confidence': confidence,
                'volatility_state': result['volatility_state']
            })
            
            # Trade on medium to high confidence signals
            if confidence >= 0.4:
                if signal == 'BUY' and position == 0:
                    position = balance / price
                    balance = 0
                    trades.append({
                        'type': 'BUY',
                        'price': price,
                        'percent_b': result['percent_b'],
                        'volatility_state': result['volatility_state'],
                        'confidence': confidence,
                        'position': position
                    })
                elif signal == 'SELL' and position > 0:
                    balance = position * price
                    pnl = balance - initial_balance
                    trades.append({
                        'type': 'SELL',
                        'price': price,
                        'percent_b': result['percent_b'],
                        'volatility_state': result['volatility_state'],
                        'confidence': confidence,
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
            'volatility_trades': len([t for t in trades if t.get('volatility_state') == 'EXPANSION']),
            'squeeze_trades': len([t for t in trades if t.get('volatility_state') == 'SQUEEZE']),
            'signal_accuracy': self._calculate_signal_accuracy(signals_history),
            'trades': trades,
            'signals_history': signals_history[-10:]  # Last 10 signals for inspection
        }
        
    def _calculate_signal_accuracy(self, signals_history: List[Dict]) -> float:
        """Calculate the accuracy of signals based on price movement after signal."""
        if len(signals_history) < 2:
            return 0.0
            
        correct_signals = 0
        total_actionable_signals = 0
        
        for i in range(len(signals_history) - 1):
            current_signal = signals_history[i]
            next_signal = signals_history[i + 1]
            
            if current_signal['signal'] in ['BUY', 'SELL']:
                total_actionable_signals += 1
                price_change = next_signal['price'] - current_signal['price']
                
                if current_signal['signal'] == 'BUY' and price_change > 0:
                    correct_signals += 1
                elif current_signal['signal'] == 'SELL' and price_change < 0:
                    correct_signals += 1
                    
        return correct_signals / total_actionable_signals if total_actionable_signals > 0 else 0.0