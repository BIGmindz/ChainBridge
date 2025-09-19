#!/usr/bin/env python3
"""
Kraken Paper Trading Demo
========================

Comprehensive demo showing how to use the KrakenPaperLiveBot with ML integration.
This script demonstrates:
- Setting up the paper trading bot
- Configuring real-time price feeds
- Integrating with ML signals
- Risk management in action
- Performance tracking
- Trade journal export

Usage:
    python examples/kraken_paper_trading_demo.py [--config CONFIG_PATH] [--duration MINUTES]

Author: BIGmindz
Version: 1.0.0
"""

import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kraken_paper_live_bot import create_kraken_paper_bot


async def demo_basic_paper_trading():
    """
    Demo 1: Basic paper trading setup and manual trades
    """
    print("\n" + "="*60)
    print("DEMO 1: BASIC KRAKEN PAPER TRADING")
    print("="*60)
    
    # Create basic configuration
    config = {
        'initial_capital': 10000.0,
        'symbols': ['BTC/USD', 'ETH/USD'],
        'risk_management': {
            'max_position_size': 0.1,
            'max_drawdown_limit': 0.15
        },
        'logging': {
            'level': 'INFO'
        }
    }
    
    # Create paper trading bot
    bot = create_kraken_paper_bot(config_dict=config)
    
    print(f"✅ Bot initialized with ${bot.budget_manager.initial_capital:,.2f}")
    print(f"📈 Trading symbols: {', '.join(config['symbols'])}")
    
    # Simulate some price data (in real usage, this comes from exchange)
    bot.price_data['BTC/USD'] = type('PriceData', (), {
        'symbol': 'BTC/USD',
        'price': 45000.0,
        'bid': 44950.0,
        'ask': 45050.0,
        'volume_24h': 1500000,
        'timestamp': datetime.now(timezone.utc),
        'spread': 100.0
    })()
    
    bot.price_data['ETH/USD'] = type('PriceData', (), {
        'symbol': 'ETH/USD', 
        'price': 3200.0,
        'bid': 3195.0,
        'ask': 3205.0,
        'volume_24h': 800000,
        'timestamp': datetime.now(timezone.utc),
        'spread': 10.0
    })()
    
    print(f"📊 BTC/USD: ${bot.price_data['BTC/USD'].price:,.2f}")
    print(f"📊 ETH/USD: ${bot.price_data['ETH/USD'].price:,.2f}")
    
    # Demo opening positions
    print("\n🎯 Opening sample positions...")
    
    # Open BTC position
    btc_result = bot.open_position(
        symbol='BTC/USD',
        side='BUY',
        signal_confidence=0.75,
        volatility=0.04,
        tags=['demo', 'manual_trade']
    )
    
    if btc_result['success']:
        print(f"✅ BTC position opened: ID {btc_result['position_id']}")
        position = btc_result['position']
        print(f"   Entry: ${position.entry_price:,.2f}")
        print(f"   Stop Loss: ${position.stop_loss:,.2f}")
        print(f"   Take Profit: ${position.take_profit:,.2f}")
    
    # Open ETH position
    eth_result = bot.open_position(
        symbol='ETH/USD',
        side='BUY',
        signal_confidence=0.65,
        volatility=0.05,
        tags=['demo', 'manual_trade']
    )
    
    if eth_result['success']:
        print(f"✅ ETH position opened: ID {eth_result['position_id']}")
        position = eth_result['position']
        print(f"   Entry: ${position.entry_price:,.2f}")
        print(f"   Stop Loss: ${position.stop_loss:,.2f}")
        print(f"   Take Profit: ${position.take_profit:,.2f}")
    
    # Show initial dashboard
    print("\n📊 Initial Performance Dashboard:")
    dashboard = bot.get_performance_dashboard()
    print(f"   Portfolio Value: ${dashboard['account']['portfolio_value']:,.2f}")
    print(f"   Active Positions: {dashboard['positions']['active_count']}")
    print(f"   Available Capital: ${dashboard['account']['available_capital']:,.2f}")
    
    # Simulate price movements and updates
    print("\n📈 Simulating price movements...")
    
    # BTC goes up 5%
    new_btc_price = 47250.0
    bot.price_data['BTC/USD'].price = new_btc_price
    bot._update_positions_pnl('BTC/USD', new_btc_price)
    
    # ETH goes down 2%
    new_eth_price = 3136.0
    bot.price_data['ETH/USD'].price = new_eth_price
    bot._update_positions_pnl('ETH/USD', new_eth_price)
    
    print(f"📊 New BTC price: ${new_btc_price:,.2f} (+5%)")
    print(f"📊 New ETH price: ${new_eth_price:,.2f} (-2%)")
    
    # Show updated dashboard
    print("\n📊 Updated Performance Dashboard:")
    dashboard = bot.get_performance_dashboard()
    print(f"   Portfolio Value: ${dashboard['account']['portfolio_value']:,.2f}")
    print(f"   Total Return: ${dashboard['account']['total_return']:,.2f} ({dashboard['account']['total_return_pct']:+.2f}%)")
    
    # Show position details
    print("\n💼 Position Details:")
    for pos_info in dashboard['positions']['active_positions']:
        print(f"   {pos_info['symbol']} {pos_info['side']}: P&L ${pos_info['pnl']:+,.2f} ({pos_info['pnl_pct']:+.2f}%)")
    
    # Close positions
    print("\n🔄 Closing positions...")
    for position_id in list(bot.positions.keys()):
        close_result = bot.close_position(position_id, "DEMO_END")
        if close_result['success']:
            position = close_result['position']
            print(f"✅ Closed {position.symbol}: P&L ${position.pnl:+.2f} ({position.pnl_pct*100:+.2f}%)")
    
    # Export trade journal
    journal_path = bot.export_trade_journal()
    print(f"📋 Trade journal exported to: {journal_path}")
    
    return bot


async def demo_ml_integration():
    """
    Demo 2: ML signal integration with automated trading
    """
    print("\n" + "="*60)
    print("DEMO 2: ML INTEGRATION WITH AUTOMATED TRADING")
    print("="*60)
    
    # Create ML-enabled configuration
    config = {
        'initial_capital': 25000.0,
        'symbols': ['BTC/USD', 'ETH/USD', 'ADA/USD'],
        'risk_management': {
            'max_position_size': 0.08,
            'correlation_threshold': 0.7,
            'max_drawdown_limit': 0.12
        },
        'ml_integration': {
            'confidence_threshold': 0.6,
            'cooldown_minutes': 15,
            'signal_weights': {
                'rsi': 0.25,
                'macd': 0.30,
                'sentiment': 0.25,
                'volume': 0.20
            }
        }
    }
    
    try:
        # Create ML trading system (would normally integrate with actual modules)
        bot = create_kraken_paper_bot(config_dict=config)
        
        # For demo purposes, create a mock ML integration
        ml_integration = MockMLIntegration(bot, config['ml_integration'])
        
        print("✅ ML Trading System initialized")
        print(f"💰 Capital: ${bot.budget_manager.initial_capital:,.2f}")
        print(f"🤖 ML Confidence Threshold: {config['ml_integration']['confidence_threshold']}")
        
        # Set up mock price data
        symbols = config['symbols']
        prices = {'BTC/USD': 44500.0, 'ETH/USD': 3150.0, 'ADA/USD': 0.45}
        
        for symbol in symbols:
            bot.price_data[symbol] = type('PriceData', (), {
                'symbol': symbol,
                'price': prices[symbol],
                'bid': prices[symbol] * 0.999,
                'ask': prices[symbol] * 1.001,
                'volume_24h': 1000000,
                'timestamp': datetime.now(timezone.utc),
                'spread': prices[symbol] * 0.002
            })()
            print(f"📊 {symbol}: ${prices[symbol]:,.4f}")
        
        # Run ML signal processing
        print("\n🧠 Processing ML signals...")
        
        # Simulate multiple signal processing cycles
        for cycle in range(3):
            print(f"\n--- Signal Processing Cycle {cycle + 1} ---")
            
            # Process signals for all symbols
            results = await ml_integration.process_trading_signals(symbols)
            
            # Display results
            for symbol, result in results.items():
                if 'decision' in result:
                    decision = result['decision']
                    print(f"{symbol}: {decision['action']} (confidence: {decision['confidence']:.2f})")
                    
                    if 'execution' in result and result['execution'].get('success'):
                        print(f"  ✅ Trade executed: Position {result['execution']['position_id']}")
                elif 'error' in result:
                    print(f"{symbol}: ❌ Error - {result['error']}")
            
            # Show performance after each cycle
            dashboard = bot.get_performance_dashboard()
            print(f"Portfolio Value: ${dashboard['account']['portfolio_value']:,.2f}")
            print(f"Active Positions: {dashboard['positions']['active_count']}")
            
            # Simulate time passing and price changes
            await asyncio.sleep(1)  # Short delay for demo
            
            # Update prices (simulate market movement)
            for symbol in symbols:
                old_price = bot.price_data[symbol].price
                # Random price movement ±2%
                import random
                change_pct = random.uniform(-0.02, 0.02)
                new_price = old_price * (1 + change_pct)
                bot.price_data[symbol].price = new_price
                bot._update_positions_pnl(symbol, new_price)
                
                if abs(change_pct) > 0.01:  # Only log significant moves
                    print(f"  📈 {symbol}: ${old_price:,.2f} → ${new_price:,.2f} ({change_pct*100:+.1f}%)")
        
        # Final performance report
        print("\n📈 FINAL PERFORMANCE REPORT")
        print("-" * 40)
        
        dashboard = bot.get_performance_dashboard()
        account = dashboard['account']
        performance = dashboard['performance']
        
        print(f"Initial Capital: ${account['initial_capital']:,.2f}")
        print(f"Final Portfolio: ${account['portfolio_value']:,.2f}")
        print(f"Total Return: ${account['total_return']:+,.2f} ({account['total_return_pct']:+.2f}%)")
        print(f"Total Trades: {performance['total_trades']}")
        print(f"Win Rate: {performance['win_rate']:.1f}%")
        
        if performance['total_trades'] > 0:
            print(f"Largest Win: ${performance['largest_win']:,.2f}")
            print(f"Largest Loss: ${performance['largest_loss']:,.2f}")
            print(f"Profit Factor: {performance['profit_factor']:.2f}")
        
        # Show ML performance
        ml_report = ml_integration.get_signal_performance_report()
        print("\n🧠 ML Signal Performance:")
        print(f"Active Modules: {ml_report['summary']['active_modules']}")
        print(f"Avg Success Rate: {ml_report['summary']['avg_success_rate']:.2f}")
        
        return bot
        
    except Exception as e:
        print(f"❌ Error in ML integration demo: {e}")
        return None


class MockMLIntegration:
    """Mock ML integration for demo purposes"""
    
    def __init__(self, paper_bot, config):
        self.paper_bot = paper_bot
        self.config = config
        self.signal_count = 0
        self.signal_performance = {}
        
    async def process_trading_signals(self, symbols):
        """Generate mock ML signals"""
        import random
        results = {}
        
        for symbol in symbols:
            self.signal_count += 1
            
            # Generate mock signals with some randomness
            confidence = random.uniform(0.4, 0.9)
            action = random.choice(['BUY', 'SELL', 'HOLD', 'HOLD'])  # Bias toward HOLD
            
            if confidence >= self.config['confidence_threshold'] and action in ['BUY', 'SELL']:
                # Create mock decision
                decision = {
                    'action': action,
                    'confidence': confidence,
                    'volatility': random.uniform(0.02, 0.06),
                    'reason': f'Mock ML signal #{self.signal_count}',
                    'stop_loss_pct': 0.03 + random.uniform(-0.01, 0.01),
                    'take_profit_pct': 0.06 + random.uniform(-0.02, 0.02)
                }
                
                # Try to execute trade
                try:
                    execution = self.paper_bot.open_position(
                        symbol=symbol,
                        side=action,
                        signal_confidence=confidence,
                        volatility=decision['volatility'],
                        stop_loss_pct=decision['stop_loss_pct'],
                        take_profit_pct=decision['take_profit_pct'],
                        tags=['ml_demo', f'confidence_{confidence:.2f}']
                    )
                    
                    results[symbol] = {
                        'decision': decision,
                        'execution': execution
                    }
                except Exception as e:
                    results[symbol] = {
                        'decision': decision,
                        'error': str(e)
                    }
            else:
                results[symbol] = {
                    'decision': {
                        'action': 'HOLD',
                        'confidence': confidence,
                        'reason': 'Below threshold or HOLD signal'
                    }
                }
        
        return results
    
    def get_signal_performance_report(self):
        """Mock performance report"""
        return {
            'summary': {
                'active_modules': 4,
                'avg_success_rate': 0.67
            }
        }


async def demo_risk_management():
    """
    Demo 3: Advanced risk management features
    """
    print("\n" + "="*60)
    print("DEMO 3: ADVANCED RISK MANAGEMENT")
    print("="*60)
    
    # Create configuration with strict risk limits
    config = {
        'initial_capital': 50000.0,
        'symbols': ['BTC/USD', 'ETH/USD'],
        'risk_management': {
            'max_position_size': 0.15,  # 15% max per position
            'correlation_threshold': 0.8,
            'max_drawdown_limit': 0.10  # 10% max drawdown
        }
    }
    
    bot = create_kraken_paper_bot(config_dict=config)
    
    print("✅ Risk Management Demo initialized")
    print(f"💰 Capital: ${bot.budget_manager.initial_capital:,.2f}")
    print(f"⚠️  Max Drawdown Limit: {config['risk_management']['max_drawdown_limit']*100}%")
    print(f"📏 Max Position Size: {config['risk_management']['max_position_size']*100}%")
    
    # Set initial prices
    bot.price_data['BTC/USD'] = type('PriceData', (), {
        'symbol': 'BTC/USD',
        'price': 50000.0,
        'bid': 49950.0,
        'ask': 50050.0,
        'volume_24h': 2000000,
        'timestamp': datetime.now(timezone.utc),
        'spread': 100.0
    })()
    
    bot.price_data['ETH/USD'] = type('PriceData', (), {
        'symbol': 'ETH/USD',
        'price': 4000.0,
        'bid': 3995.0,
        'ask': 4005.0,
        'volume_24h': 1500000,
        'timestamp': datetime.now(timezone.utc),
        'spread': 10.0
    })()
    
    print(f"📊 Initial BTC: ${bot.price_data['BTC/USD'].price:,.2f}")
    print(f"📊 Initial ETH: ${bot.price_data['ETH/USD'].price:,.2f}")
    
    # Demo correlation-based position sizing
    print("\n🔄 Testing correlation-based position sizing...")
    
    # Open first BTC position (should get full size)
    btc1_result = bot.open_position('BTC/USD', 'BUY', 0.8, 0.04, tags=['risk_demo', 'first_btc'])
    if btc1_result['success']:
        position1 = btc1_result['position']
        print(f"✅ First BTC position: ${position1.entry_price * position1.quantity:,.2f}")
    
    # Try to open second BTC position (should get reduced size due to correlation)
    btc2_result = bot.open_position('BTC/USD', 'BUY', 0.8, 0.04, tags=['risk_demo', 'second_btc'])
    if btc2_result['success']:
        position2 = btc2_result['position']
        print(f"✅ Second BTC position: ${position2.entry_price * position2.quantity:,.2f} (correlation-adjusted)")
    else:
        print(f"❌ Second BTC position rejected: {btc2_result.get('error', 'Unknown error')}")
    
    # Open ETH position (different asset class)
    eth_result = bot.open_position('ETH/USD', 'BUY', 0.75, 0.05, tags=['risk_demo', 'eth'])
    if eth_result['success']:
        position_eth = eth_result['position']
        print(f"✅ ETH position: ${position_eth.entry_price * position_eth.quantity:,.2f}")
    
    # Show diversification score
    dashboard = bot.get_performance_dashboard()
    print(f"📊 Diversification Score: {dashboard['risk_metrics']['diversification_score']:.2f}")
    
    # Simulate market crash to test drawdown limits
    print("\n💥 Simulating market crash...")
    
    # Crash BTC by 15%
    crash_btc_price = 50000.0 * 0.85
    bot.price_data['BTC/USD'].price = crash_btc_price
    bot._update_positions_pnl('BTC/USD', crash_btc_price)
    
    # Crash ETH by 12%
    crash_eth_price = 4000.0 * 0.88
    bot.price_data['ETH/USD'].price = crash_eth_price
    bot._update_positions_pnl('ETH/USD', crash_eth_price)
    
    print(f"📉 BTC crashed to: ${crash_btc_price:,.2f} (-15%)")
    print(f"📉 ETH dropped to: ${crash_eth_price:,.2f} (-12%)")
    
    # Check risk limits
    dashboard = bot.get_performance_dashboard()
    current_drawdown = dashboard['account']['total_return_pct'] / 100
    
    print(f"⚠️  Current Drawdown: {current_drawdown:.2%}")
    print(f"🛑 Max Drawdown Limit: {config['risk_management']['max_drawdown_limit']:.2%}")
    
    if abs(current_drawdown) > config['risk_management']['max_drawdown_limit']:
        print("🚨 DRAWDOWN LIMIT EXCEEDED - EMERGENCY STOP TRIGGERED")
        bot._emergency_close_all_positions()
        print("✅ All positions closed for risk management")
    
    # Final risk report
    print("\n📊 Final Risk Management Report:")
    dashboard = bot.get_performance_dashboard()
    print(f"   Portfolio Value: ${dashboard['account']['portfolio_value']:,.2f}")
    print(f"   Total Return: {dashboard['account']['total_return_pct']:+.2f}%")
    print(f"   Max Drawdown: {dashboard['performance']['max_drawdown']:.2%}")
    print(f"   Risk Exposure: ${dashboard['risk_metrics']['current_risk_exposure']:,.2f}")
    
    return bot


async def main():
    """Main demo function"""
    parser = argparse.ArgumentParser(description='Kraken Paper Trading Demo')
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--demo', type=str, choices=['basic', 'ml', 'risk', 'all'], 
                       default='all', help='Which demo to run')
    parser.add_argument('--duration', type=int, default=5, 
                       help='Demo duration in minutes')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 KRAKEN PAPER TRADING COMPREHENSIVE DEMO")
    print("="*60)
    print(f"Demo Mode: {args.demo}")
    print(f"Duration: {args.duration} minutes")
    print("="*60)
    
    try:
        if args.demo in ['basic', 'all']:
            _bot1 = await demo_basic_paper_trading()
            
        if args.demo in ['ml', 'all']:
            _bot2 = await demo_ml_integration()
            
        if args.demo in ['risk', 'all']:
            _bot3 = await demo_risk_management()
        
        print("\n" + "="*60)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        print("\n📋 Key Features Demonstrated:")
        print("  ✅ Professional paper trading setup")
        print("  ✅ Real-time price feed simulation") 
        print("  ✅ ML signal integration")
        print("  ✅ Advanced risk management")
        print("  ✅ Position tracking and P&L")
        print("  ✅ Performance analytics")
        print("  ✅ Correlation-based sizing")
        print("  ✅ Drawdown protection")
        print("  ✅ Trade journal export")
        
        print("\n🎯 Ready for Production Integration!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())