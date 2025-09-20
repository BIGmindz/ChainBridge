"""
Professional Kraken Paper Trading Module
========================================

A comprehensive paper trading implementation specifically designed for Kraken exchange
with real-time price feeds, advanced risk management, and performance tracking.

Features:
- Real-time price feed integration via CCXT
- Advanced order management system
- Position tracking with detailed P&L calculation
- Risk management with position sizing and correlation adjustments
- Performance metrics and trade analytics
- WebSocket simulation for live data
- Integration with ML decision engine

Author: BIGmindz
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import numpy as np

# Core component imports
try:
    from .exchange_adapter import ExchangeAdapter  # noqa: F401
except ImportError:
    pass

try:
    from budget_manager import BudgetManager
except ImportError:
    # Fallback for testing - create a mock BudgetManager
    class BudgetManager:
        def __init__(self, initial_capital=10000.0):
            self.initial_capital = initial_capital
            self.current_capital = initial_capital
            self.available_capital = initial_capital
            print(f"Mock BudgetManager initialized with ${initial_capital:,.2f}")

        def calculate_position_size(self, symbol, confidence, volatility):
            return {"size": self.available_capital * 0.05}  # 5% default

        def open_position(self, **kwargs):
            return {"success": True, "position": {"id": "mock_pos_1"}}


@dataclass
class TradingPosition:
    """Enhanced position data structure for detailed tracking"""

    id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    entry_price: float
    current_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    max_pnl: float = 0.0
    max_drawdown: float = 0.0
    fees_paid: float = 0.0
    tags: List[str] = field(default_factory=list)

    def update_price(self, new_price: float):
        """Update position with new price and recalculate P&L"""
        self.current_price = new_price

        if self.side == "BUY":
            self.pnl = (new_price - self.entry_price) * self.quantity
            self.pnl_pct = (new_price - self.entry_price) / self.entry_price
        else:  # SELL
            self.pnl = (self.entry_price - new_price) * self.quantity
            self.pnl_pct = (self.entry_price - new_price) / self.entry_price

        # Track maximum profit and drawdown
        if self.pnl > self.max_pnl:
            self.max_pnl = self.pnl

        drawdown = self.max_pnl - self.pnl
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown


@dataclass
class PriceData:
    """Real-time price data structure"""

    symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    timestamp: datetime
    spread: float

    @property
    def spread_pct(self) -> float:
        """Calculate spread percentage"""
        return (self.ask - self.bid) / self.bid if self.bid > 0 else 0.0


@dataclass
class PerformanceMetrics:
    """Comprehensive performance tracking"""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade_duration: float = 0.0
    fees_paid: float = 0.0

    def update_from_trade(self, pnl: float, duration_minutes: float):
        """Update metrics from a completed trade"""
        self.total_trades += 1
        self.total_pnl += pnl

        if pnl > 0:
            self.winning_trades += 1
            self.gross_profit += pnl
            if pnl > self.largest_win:
                self.largest_win = pnl
        else:
            self.losing_trades += 1
            self.gross_loss += abs(pnl)
            if abs(pnl) > self.largest_loss:
                self.largest_loss = abs(pnl)

        # Calculate derived metrics
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        self.profit_factor = self.gross_profit / self.gross_loss if self.gross_loss > 0 else float("inf")
        self.avg_win = self.gross_profit / self.winning_trades if self.winning_trades > 0 else 0
        self.avg_loss = self.gross_loss / self.losing_trades if self.losing_trades > 0 else 0


class KrakenAPIWrapper:
    """Clean API wrapper for Kraken with rate limiting and error handling"""

    def __init__(self, exchange, config: Dict[str, Any]):
        self.exchange = exchange
        self.config = config
        self.rate_limiter = {}  # Track API call rates
        self.logger = logging.getLogger(__name__)

        # Rate limiting settings
        self.max_calls_per_minute = config.get("rate_limit", 60)
        self.call_history = deque(maxlen=self.max_calls_per_minute)

    async def _rate_limit_check(self):
        """Ensure we don't exceed rate limits"""
        now = time.time()

        # Remove calls older than 1 minute
        while self.call_history and self.call_history[0] < now - 60:
            self.call_history.popleft()

        # If we're at the limit, wait
        if len(self.call_history) >= self.max_calls_per_minute:
            sleep_time = 60 - (now - self.call_history[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self.call_history.append(now)

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data with error handling"""
        await self._rate_limit_check()

        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "price": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "volume": ticker["quoteVolume"],
                "timestamp": datetime.fromtimestamp(ticker["timestamp"] / 1000, tz=timezone.utc),
                "spread": (ticker["ask"] - ticker["bid"] if ticker["ask"] and ticker["bid"] else 0),
            }
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise

    async def fetch_ohlcv(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> List[List]:
        """Fetch OHLCV data with error handling"""
        await self._rate_limit_check()

        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise


class WebSocketSimulator:
    """Simulate WebSocket feed for real-time price updates"""

    def __init__(self, api_wrapper: KrakenAPIWrapper, symbols: List[str]):
        self.api_wrapper = api_wrapper
        self.symbols = symbols
        self.subscribers = []
        self.is_running = False
        self.update_interval = 1.0  # seconds

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to price updates"""
        self.subscribers.append(callback)

    async def start(self):
        """Start the WebSocket simulation"""
        self.is_running = True
        while self.is_running:
            try:
                # Fetch latest prices for all symbols
                for symbol in self.symbols:
                    ticker_data = await self.api_wrapper.fetch_ticker(symbol)

                    # Notify all subscribers
                    for callback in self.subscribers:
                        try:
                            callback(ticker_data)
                        except Exception as e:
                            logging.error(f"Error in WebSocket callback: {e}")

                await asyncio.sleep(self.update_interval)

            except Exception as e:
                logging.error(f"Error in WebSocket simulation: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    def stop(self):
        """Stop the WebSocket simulation"""
        self.is_running = False


class KrakenPaperLiveBot:
    """
    Professional Kraken Paper Trading Bot

    A comprehensive paper trading engine that simulates live trading with:
    - Real-time price feeds
    - Advanced risk management
    - Position tracking and P&L calculation
    - Performance analytics
    - Integration with ML decision systems
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Kraken Paper Live Bot

        Args:
            config: Configuration dictionary containing:
                - exchange: Exchange configuration
                - symbols: List of trading pairs
                - risk_management: Risk parameters
                - performance_tracking: Performance settings
                - logging: Logging configuration
        """
        self.config = config
        self.logger = self._setup_logging()

        # Core components
        self.budget_manager = BudgetManager(initial_capital=config.get("initial_capital", 10000.0))

        # Trading state
        self.positions: Dict[str, TradingPosition] = {}
        self.price_data: Dict[str, PriceData] = {}
        self.performance = PerformanceMetrics()
        self.is_running = False

        # Risk management
        self.risk_config = config.get("risk_management", {})
        self.max_position_size = self.risk_config.get("max_position_size", 0.1)  # 10% of capital
        self.correlation_threshold = self.risk_config.get("correlation_threshold", 0.7)
        self.max_drawdown_limit = self.risk_config.get("max_drawdown_limit", 0.15)  # 15%

        # Performance tracking
        self.trade_journal = []
        self.daily_pnl_history = []

        self.logger.info(f"KrakenPaperLiveBot initialized with ${self.budget_manager.initial_capital:,.2f}")

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging system"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # Create formatters
        detailed_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s")

        # File handler for detailed logs
        file_handler = logging.FileHandler("kraken_paper_trading.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)

        # Console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    async def initialize_exchange(self, exchange):
        """Initialize exchange connection and API wrapper"""
        self.api_wrapper = KrakenAPIWrapper(exchange, self.config.get("api", {}))
        symbols = self.config.get("symbols", ["BTC/USD", "ETH/USD"])
        self.websocket_sim = WebSocketSimulator(self.api_wrapper, symbols)
        self.websocket_sim.subscribe(self._on_price_update)

        self.logger.info(f"Exchange initialized with symbols: {symbols}")

    def _on_price_update(self, ticker_data: Dict[str, Any]):
        """Handle real-time price updates"""
        symbol = ticker_data["symbol"]

        # Update price data
        self.price_data[symbol] = PriceData(
            symbol=symbol,
            price=ticker_data["price"],
            bid=ticker_data["bid"],
            ask=ticker_data["ask"],
            volume_24h=ticker_data["volume"],
            timestamp=ticker_data["timestamp"],
            spread=ticker_data["spread"],
        )

        # Update open positions
        self._update_positions_pnl(symbol, ticker_data["price"])

        # Check stop losses and take profits
        self._check_position_exits(symbol)

    def _update_positions_pnl(self, symbol: str, new_price: float):
        """Update P&L for positions in the given symbol"""
        for pos_id, position in self.positions.items():
            if position.symbol == symbol:
                position.update_price(new_price)

    def _check_position_exits(self, symbol: str):
        """Check and execute stop loss/take profit orders"""
        positions_to_close = []
        current_price = self.price_data[symbol].price

        for pos_id, position in self.positions.items():
            if position.symbol != symbol:
                continue

            should_close = False
            exit_reason = ""

            # Check stop loss
            if position.stop_loss:
                if position.side == "BUY" and current_price <= position.stop_loss:
                    should_close = True
                    exit_reason = "STOP_LOSS"
                elif position.side == "SELL" and current_price >= position.stop_loss:
                    should_close = True
                    exit_reason = "STOP_LOSS"

            # Check take profit
            if position.take_profit and not should_close:
                if position.side == "BUY" and current_price >= position.take_profit:
                    should_close = True
                    exit_reason = "TAKE_PROFIT"
                elif position.side == "SELL" and current_price <= position.take_profit:
                    should_close = True
                    exit_reason = "TAKE_PROFIT"

            if should_close:
                positions_to_close.append((pos_id, exit_reason))

        # Close positions
        for pos_id, reason in positions_to_close:
            self.close_position(pos_id, reason)

    def calculate_position_size(
        self,
        symbol: str,
        signal_confidence: float,
        volatility: float,
        correlation_adj: float = 1.0,
    ) -> float:
        """
        Calculate optimal position size based on multiple factors

        Args:
            symbol: Trading symbol
            signal_confidence: ML model confidence (0-1)
            volatility: Symbol volatility
            correlation_adj: Correlation adjustment factor

        Returns:
            Position size in base currency
        """
        # Get base position size from budget manager
        base_calc = self.budget_manager.calculate_position_size(symbol, signal_confidence, volatility)

        # Apply correlation adjustment
        adjusted_size = base_calc["size"] * correlation_adj

        # Apply maximum position size limit
        max_size = self.budget_manager.available_capital * self.max_position_size
        final_size = min(adjusted_size, max_size)

        self.logger.info(
            f"Position size calculation for {symbol}: "
            f"base=${base_calc['size']:.2f}, "
            f"correlation_adj={correlation_adj:.3f}, "
            f"final=${final_size:.2f}"
        )

        return final_size

    def open_position(
        self,
        symbol: str,
        side: str,
        signal_confidence: float,
        volatility: float = 0.02,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.06,
        tags: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Open a new trading position with comprehensive risk management

        Args:
            symbol: Trading pair (e.g., 'BTC/USD')
            side: 'BUY' or 'SELL'
            signal_confidence: ML model confidence (0-1)
            volatility: Historical volatility
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            tags: Optional tags for position categorization

        Returns:
            Position creation result
        """
        if not self.price_data.get(symbol):
            return {"success": False, "error": f"No price data for {symbol}"}

        current_price = self.price_data[symbol].price

        # Calculate correlation adjustment
        correlation_adj = self._calculate_correlation_adjustment(symbol)

        # Calculate position size
        position_size = self.calculate_position_size(symbol, signal_confidence, volatility, correlation_adj)

        if position_size <= 0:
            return {
                "success": False,
                "error": "Insufficient capital or position size too small",
            }

        # Calculate stop loss and take profit
        if side == "BUY":
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        else:  # SELL
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)

        # Use budget manager to open position
        budget_result = self.budget_manager.open_position(
            symbol=symbol,
            side=side,
            entry_price=current_price,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        if not budget_result.get("success", False):
            return budget_result

        # Create enhanced position tracking
        position_id = budget_result["position"]["id"]
        quantity = position_size / current_price

        position = TradingPosition(
            id=position_id,
            symbol=symbol,
            side=side,
            entry_price=current_price,
            current_price=current_price,
            quantity=quantity,
            entry_time=datetime.now(timezone.utc),
            stop_loss=stop_loss,
            take_profit=take_profit,
            tags=tags or [],
        )

        self.positions[position_id] = position

        # Log trade
        trade_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "OPEN",
            "position_id": position_id,
            "symbol": symbol,
            "side": side,
            "entry_price": current_price,
            "quantity": quantity,
            "position_size": position_size,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "signal_confidence": signal_confidence,
            "volatility": volatility,
            "correlation_adj": correlation_adj,
            "tags": tags,
        }

        self.trade_journal.append(trade_log)

        self.logger.info(
            f"Position opened: {side} {quantity:.6f} {symbol} @ ${current_price:.2f} "
            f"(Size: ${position_size:.2f}, SL: ${stop_loss:.2f}, TP: ${take_profit:.2f})"
        )

        return {
            "success": True,
            "position_id": position_id,
            "position": position,
            "trade_log": trade_log,
        }

    def close_position(self, position_id: str, reason: str = "MANUAL") -> Dict[str, Any]:
        """
        Close a trading position and update performance metrics

        Args:
            position_id: Unique position identifier
            reason: Reason for closing (MANUAL, STOP_LOSS, TAKE_PROFIT, etc.)

        Returns:
            Position closure result
        """
        if position_id not in self.positions:
            return {"success": False, "error": "Position not found"}

        position = self.positions[position_id]
        current_price = self.price_data[position.symbol].price

        # Update position with final price
        position.update_price(current_price)

        # Calculate trade duration
        duration = (datetime.now(timezone.utc) - position.entry_time).total_seconds() / 60  # minutes

        # Close position in budget manager
        budget_result = self.budget_manager.close_position(position_id, current_price, reason)

        # Update performance metrics
        self.performance.update_from_trade(position.pnl, duration)

        # Log trade closure
        trade_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "CLOSE",
            "position_id": position_id,
            "symbol": position.symbol,
            "side": position.side,
            "entry_price": position.entry_price,
            "exit_price": current_price,
            "quantity": position.quantity,
            "pnl": position.pnl,
            "pnl_pct": position.pnl_pct * 100,
            "duration_minutes": duration,
            "reason": reason,
            "max_pnl": position.max_pnl,
            "max_drawdown": position.max_drawdown,
        }

        self.trade_journal.append(trade_log)

        # Remove from active positions
        del self.positions[position_id]

        self.logger.info(
            f"Position closed: {position.side} {position.symbol} @ ${current_price:.2f} "
            f"(P&L: ${position.pnl:.2f} [{position.pnl_pct * 100:.2f}%], Reason: {reason})"
        )

        return {
            "success": True,
            "position": position,
            "trade_log": trade_log,
            "budget_result": budget_result,
        }

    def _calculate_correlation_adjustment(self, symbol: str) -> float:
        """
        Calculate position size adjustment based on portfolio correlation

        Higher correlation with existing positions = smaller position size
        """
        if not self.positions:
            return 1.0

        # Get symbols of existing positions
        existing_symbols = set(pos.symbol for pos in self.positions.values())

        if symbol in existing_symbols:
            # Already have position in this symbol, reduce size
            return 0.5

        # TODO: Implement actual correlation calculation using historical price data
        # For now, use simplified logic based on asset classes

        # Basic correlation rules (can be enhanced with historical data)
        crypto_majors = ["BTC/USD", "ETH/USD"]
        crypto_alts = ["ADA/USD", "DOT/USD", "LINK/USD"]

        correlation_penalty = 0.0

        for existing_symbol in existing_symbols:
            if (symbol in crypto_majors and existing_symbol in crypto_majors) or (symbol in crypto_alts and existing_symbol in crypto_alts):
                correlation_penalty += 0.2

        return max(0.3, 1.0 - correlation_penalty)

    def get_performance_dashboard(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance dashboard

        Returns:
            Dictionary containing all performance metrics and statistics
        """
        # Calculate current portfolio value
        portfolio_value = self.budget_manager.current_capital
        for position in self.positions.values():
            portfolio_value += position.pnl

        # Calculate daily P&L if we have trade history
        daily_returns = self._calculate_daily_returns()

        dashboard = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account": {
                "initial_capital": self.budget_manager.initial_capital,
                "current_capital": self.budget_manager.current_capital,
                "portfolio_value": portfolio_value,
                "available_capital": self.budget_manager.available_capital,
                "total_return": (portfolio_value - self.budget_manager.initial_capital),
                "total_return_pct": ((portfolio_value - self.budget_manager.initial_capital) / self.budget_manager.initial_capital * 100),
            },
            "positions": {
                "active_count": len(self.positions),
                "active_positions": [
                    {
                        "id": pos.id,
                        "symbol": pos.symbol,
                        "side": pos.side,
                        "entry_price": pos.entry_price,
                        "current_price": pos.current_price,
                        "pnl": pos.pnl,
                        "pnl_pct": pos.pnl_pct * 100,
                        "duration_hours": (datetime.now(timezone.utc) - pos.entry_time).total_seconds() / 3600,
                    }
                    for pos in self.positions.values()
                ],
            },
            "performance": {
                "total_trades": self.performance.total_trades,
                "winning_trades": self.performance.winning_trades,
                "losing_trades": self.performance.losing_trades,
                "win_rate": self.performance.win_rate * 100,
                "profit_factor": self.performance.profit_factor,
                "total_pnl": self.performance.total_pnl,
                "largest_win": self.performance.largest_win,
                "largest_loss": self.performance.largest_loss,
                "avg_win": self.performance.avg_win,
                "avg_loss": self.performance.avg_loss,
                "sharpe_ratio": self._calculate_sharpe_ratio(daily_returns),
                "max_drawdown": self.budget_manager.max_drawdown,
                "current_drawdown": self.budget_manager.current_drawdown,
            },
            "risk_metrics": {
                "max_drawdown_limit": self.max_drawdown_limit * 100,
                "current_risk_exposure": sum(abs(pos.pnl) for pos in self.positions.values()),
                "diversification_score": self._calculate_diversification_score(),
                "correlation_adjusted_exposure": sum(
                    abs(pos.pnl) * self._calculate_correlation_adjustment(pos.symbol) for pos in self.positions.values()
                ),
            },
        }

        return dashboard

    def _calculate_daily_returns(self) -> List[float]:
        """Calculate daily returns from trade history"""
        if len(self.trade_journal) < 2:
            return []

        # Group trades by day and calculate daily P&L
        daily_pnl = {}
        for trade in self.trade_journal:
            if trade["action"] == "CLOSE":
                date = trade["timestamp"][:10]  # YYYY-MM-DD
                if date not in daily_pnl:
                    daily_pnl[date] = 0.0
                daily_pnl[date] += trade["pnl"]

        return list(daily_pnl.values())

    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio from returns"""
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)
        avg_return = np.mean(returns_array)
        return_std = np.std(returns_array)

        if return_std == 0:
            return 0.0

        # Annualize the Sharpe ratio (assuming daily returns)
        daily_risk_free_rate = risk_free_rate / 365
        return (avg_return - daily_risk_free_rate) / return_std * np.sqrt(365)

    def _calculate_diversification_score(self) -> float:
        """Calculate portfolio diversification score (0-1)"""
        if not self.positions:
            return 1.0

        # Count unique symbols
        unique_symbols = set(pos.symbol for pos in self.positions.values())
        max_symbols = len(self.config.get("symbols", []))

        # Basic diversification score based on number of different symbols
        symbol_diversity = len(unique_symbols) / max(max_symbols, 1)

        # TODO: Enhance with correlation-based diversification measure

        return min(1.0, symbol_diversity)

    async def run_live_trading(self):
        """
        Start live paper trading with real-time price feeds

        This is the main trading loop that:
        1. Starts WebSocket price feeds
        2. Monitors positions
        3. Updates performance metrics
        4. Handles risk management
        """
        self.is_running = True
        self.logger.info("Starting live paper trading...")

        try:
            # Start WebSocket simulation
            websocket_task = asyncio.create_task(self.websocket_sim.start())

            # Main trading loop
            while self.is_running:
                # Update daily P&L tracking
                self._update_daily_pnl()

                # Check risk limits
                self._check_risk_limits()

                # Log performance periodically
                if len(self.positions) > 0:
                    dashboard = self.get_performance_dashboard()
                    self.logger.info(
                        f"Active positions: {len(self.positions)}, "
                        f"Portfolio value: ${dashboard['account']['portfolio_value']:,.2f}, "
                        f"Total return: {dashboard['account']['total_return_pct']:.2f}%"
                    )

                # Wait before next iteration
                await asyncio.sleep(30)  # Update every 30 seconds

        except Exception as e:
            self.logger.error(f"Error in live trading loop: {e}")
        finally:
            # Cleanup
            self.websocket_sim.stop()
            await websocket_task
            self.logger.info("Live paper trading stopped")

    def _update_daily_pnl(self):
        """Update daily P&L tracking"""
        today = datetime.now(timezone.utc).date()
        current_pnl = sum(pos.pnl for pos in self.positions.values())

        # Store daily P&L for performance calculation
        if not self.daily_pnl_history or self.daily_pnl_history[-1]["date"] != today:
            self.daily_pnl_history.append(
                {
                    "date": today,
                    "pnl": current_pnl,
                    "portfolio_value": self.budget_manager.current_capital + current_pnl,
                }
            )

    def _check_risk_limits(self):
        """Check and enforce risk management limits"""
        # Check maximum drawdown limit
        current_drawdown = self.budget_manager.current_drawdown
        if current_drawdown > self.max_drawdown_limit:
            self.logger.warning(f"Maximum drawdown limit exceeded: {current_drawdown:.2%} > {self.max_drawdown_limit:.2%}")
            # Close all positions to limit further losses
            self._emergency_close_all_positions()

    def _emergency_close_all_positions(self):
        """Emergency closure of all positions"""
        self.logger.critical("EMERGENCY: Closing all positions due to risk limits")

        positions_to_close = list(self.positions.keys())
        for position_id in positions_to_close:
            try:
                self.close_position(position_id, "EMERGENCY_RISK_LIMIT")
            except Exception as e:
                self.logger.error(f"Error closing position {position_id}: {e}")

    def stop_trading(self):
        """Stop live trading"""
        self.is_running = False
        self.logger.info("Stopping live paper trading...")

    def export_trade_journal(self, filename: str = None) -> str:
        """
        Export complete trade journal to JSON file

        Args:
            filename: Optional custom filename

        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kraken_paper_trade_journal_{timestamp}.json"

        export_data = {
            "metadata": {
                "bot_version": "1.0.0",
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "initial_capital": self.budget_manager.initial_capital,
                "final_portfolio_value": self.budget_manager.current_capital + sum(pos.pnl for pos in self.positions.values()),
            },
            "performance_summary": self.get_performance_dashboard(),
            "trade_history": self.trade_journal,
            "active_positions": [
                {
                    "id": pos.id,
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "quantity": pos.quantity,
                    "pnl": pos.pnl,
                    "pnl_pct": pos.pnl_pct,
                    "entry_time": pos.entry_time.isoformat(),
                    "stop_loss": pos.stop_loss,
                    "take_profit": pos.take_profit,
                    "max_pnl": pos.max_pnl,
                    "max_drawdown": pos.max_drawdown,
                    "tags": pos.tags,
                }
                for pos in self.positions.values()
            ],
        }

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        self.logger.info(f"Trade journal exported to {filename}")
        return filename


# Utility function for easy bot creation
def create_kraken_paper_bot(config_path: str = None, config_dict: Dict[str, Any] = None) -> KrakenPaperLiveBot:
    """
    Factory function to create KrakenPaperLiveBot instance

    Args:
        config_path: Path to YAML configuration file
        config_dict: Direct configuration dictionary

    Returns:
        Configured KrakenPaperLiveBot instance
    """
    import yaml

    if config_path:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    elif config_dict:
        config = config_dict
    else:
        # Default configuration
        config = {
            "initial_capital": 10000.0,
            "symbols": ["BTC/USD", "ETH/USD"],
            "risk_management": {
                "max_position_size": 0.1,
                "correlation_threshold": 0.7,
                "max_drawdown_limit": 0.15,
            },
            "api": {"rate_limit": 60},
        }

    return KrakenPaperLiveBot(config)
