"""
Live Trading Integration for Abacus.AI ML Predictions
Handles real-time trading execution with proper error handling and risk management
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import logging
from dataclasses import dataclass
from enum import Enum
import queue

from AlgorithmImports import *
from data.abacus_ai_predictions import AbacusAIPredictionsData
from config.redis_manager import AbacusRedisManager


class TradingStatus(Enum):
    """Trading status enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class TradeOrder:
    """Trade order data structure"""
    symbol: str
    quantity: int
    order_type: str
    timestamp: datetime
    prediction_confidence: float
    prediction_direction: str
    reasoning: str


@dataclass
class RiskMetrics:
    """Risk management metrics"""
    current_drawdown: float
    daily_pnl: float
    total_pnl: float
    var_1d: float  # Value at Risk 1-day
    max_position_size: float
    leverage_ratio: float
    portfolio_concentration: float


class AbacusAITradingEngine:
    """Live trading engine for Abacus.AI ML predictions"""
    
    def __init__(self, algorithm: QCAlgorithm, symbols: List[str], config: Dict[str, Any]):
        """
        Initialize trading engine
        
        Args:
            algorithm: Reference to main algorithm
            symbols: List of symbols to trade
            config: Trading configuration
        """
        self.algorithm = algorithm
        self.symbols = symbols
        self.config = config
        self.status = TradingStatus.STOPPED
        
        # Trading state
        self.orders_queue = queue.Queue()
        self.executed_orders = []
        self.risk_metrics = RiskMetrics(0, 0, 0, 0, 0, 0, 0)
        self.position_limits = {}
        self.last_update = None
        
        # Data sources
        self.abacus_data = None
        self.redis_manager = None
        
        # Threading and async
        self.trading_thread = None
        self.running = False
        self.lock = threading.Lock()
        
        # Error handling
        self.error_count = 0
        self.max_errors = 10
        self.retry_attempts = 3
        
        # Performance tracking
        self.performance_history = []
        self.daily_stats = {}
        
        # Risk management
        self.max_daily_loss = config.get('max_daily_loss', 0.02)  # 2% daily loss limit
        self.max_portfolio_risk = config.get('max_portfolio_risk', 0.1)  # 10% max portfolio risk
        self.position_sizing_model = config.get('position_sizing', 'kelly')
        
        self.Debug("Abacus.AI Trading Engine initialized")
    
    def start_trading(self) -> bool:
        """Start live trading engine"""
        try:
            with self.lock:
                if self.status != TradingStatus.STOPPED:
                    self.Debug(f"Trading engine already {self.status}")
                    return False
                
                self.status = TradingStatus.STARTING
                self.running = True
                
                # Initialize data sources
                if not self._initialize_data_sources():
                    self.status = TradingStatus.ERROR
                    return False
                
                # Initialize risk management
                self._initialize_risk_management()
                
                # Start trading thread
                self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
                self.trading_thread.start()
                
                self.status = TradingStatus.RUNNING
                self.Debug("Trading engine started successfully")
                return True
                
        except Exception as e:
            self.status = TradingStatus.ERROR
            self.Debug(f"Failed to start trading engine: {e}")
            return False
    
    def stop_trading(self) -> bool:
        """Stop live trading engine"""
        try:
            with self.lock:
                if self.status == TradingStatus.STOPPED:
                    return True
                
                self.status = TradingStatus.STOPPING
                self.running = False
                
                # Wait for trading thread to finish
                if self.trading_thread and self.trading_thread.is_alive():
                    self.trading_thread.join(timeout=5)
                
                # Clean up resources
                self._cleanup()
                
                self.status = TradingStatus.STOPPED
                self.Debug("Trading engine stopped")
                return True
                
        except Exception as e:
            self.Debug(f"Error stopping trading engine: {e}")
            return False
    
    def pause_trading(self) -> bool:
        """Pause trading operations"""
        try:
            with self.lock:
                if self.status == TradingStatus.RUNNING:
                    self.status = TradingStatus.PAUSED
                    self.Debug("Trading engine paused")
                    return True
            return False
        except Exception as e:
            self.Debug(f"Error pausing trading: {e}")
            return False
    
    def resume_trading(self) -> bool:
        """Resume trading operations"""
        try:
            with self.lock:
                if self.status == TradingStatus.PAUSED:
                    self.status = TradingStatus.RUNNING
                    self.Debug("Trading engine resumed")
                    return True
            return False
        except Exception as e:
            self.Debug(f"Error resuming trading: {e}")
            return False
    
    def _initialize_data_sources(self) -> bool:
        """Initialize data sources for trading"""
        try:
            # Initialize Abacus.AI data source
            self.abacus_data = self.algorithm.GetDataForSymbol('AAPL')  # Placeholder
            
            # Initialize Redis manager for real-time data
            if self.config.get('enable_redis', False):
                try:
                    self.redis_manager = AbacusRedisManager(
                        host=self.config.get('redis_host', 'localhost'),
                        port=self.config.get('redis_port', 6379)
                    )
                    
                    # Subscribe to prediction updates
                    self.redis_manager.subscribe_to_predictions(
                        symbols=self.symbols,
                        callback=self._on_prediction_update
                    )
                    
                    self.Debug("Redis data source initialized")
                    
                except Exception as e:
                    self.Debug(f"Redis initialization failed: {e}")
                    self.redis_manager = None
            
            return True
            
        except Exception as e:
            self.Debug(f"Data source initialization failed: {e}")
            return False
    
    def _initialize_risk_management(self):
        """Initialize risk management parameters"""
        try:
            # Initialize position limits
            for symbol in self.symbols:
                self.position_limits[symbol] = {
                    'max_quantity': self.config.get('max_position_pct', 0.05) * 100000 / 100,  # Max $ value
                    'max_value_pct': self.config.get('max_position_pct', 0.05),  # % of portfolio
                    'min_confidence': self.config.get('min_confidence', 0.7),
                    'max_daily_trades': self.config.get('max_daily_trades', 10)
                }
            
            self.Debug("Risk management initialized")
            
        except Exception as e:
            self.Debug(f"Risk management initialization failed: {e}")
    
    def _trading_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                if self.status == TradingStatus.PAUSED:
                    time.sleep(1)
                    continue
                
                # Process prediction updates
                self._process_predictions()
                
                # Process order queue
                self._process_order_queue()
                
                # Update risk metrics
                self._update_risk_metrics()
                
                # Check for risk breaches
                if self._check_risk_breaches():
                    self._handle_risk_breach()
                
                # Sleep to prevent high CPU usage
                time.sleep(1)
                
            except Exception as e:
                self.error_count += 1
                self.Debug(f"Trading loop error (count: {self.error_count}): {e}")
                
                if self.error_count >= self.max_errors:
                    self.status = TradingStatus.ERROR
                    self.Debug("Trading engine stopped due to excessive errors")
                    break
                
                time.sleep(5)  # Wait before retrying
    
    def _on_prediction_update(self, prediction):
        """Handle real-time prediction updates"""
        try:
            if self.status != TradingStatus.RUNNING:
                return
            
            symbol = prediction.symbol
            
            if symbol not in self.symbols:
                return
            
            # Create order based on prediction
            order = self._create_order_from_prediction(prediction)
            if order:
                self.orders_queue.put(order)
                self.Debug(f"Order queued for {symbol}: {order.quantity} shares")
            
        except Exception as e:
            self.Debug(f"Prediction update handling failed: {e}")
    
    def _create_order_from_prediction(self, prediction) -> Optional[TradeOrder]:
        """Create trading order from ML prediction"""
        try:
            symbol = prediction.symbol
            confidence = prediction.confidence
            direction = prediction.direction
            sentiment = prediction.sentiment_score
            
            # Check confidence threshold
            min_confidence = self.position_limits[symbol]['min_confidence']
            if confidence < min_confidence:
                return None
            
            # Check sentiment filter
            if sentiment < self.config.get('sentiment_filter', -0.5):
                return None
            
            # Determine signal strength
            if confidence > 0.85 and abs(sentiment) > 0.7:
                signal_strength = 'strong'
                quantity_multiplier = 1.0
            elif confidence > 0.7 and abs(sentiment) > 0.4:
                signal_strength = 'medium'
                quantity_multiplier = 0.5
            else:
                signal_strength = 'weak'
                quantity_multiplier = 0.25
            
            # Calculate position size
            current_price = self.algorithm.Securities[symbol].Price
            portfolio_value = self.algorithm.Portfolio.TotalPortfolioValue
            
            base_position_size = portfolio_value * self.config.get('max_position_pct', 0.05)
            adjusted_position_size = base_position_size * quantity_multiplier
            
            if direction == 'up' and sentiment > 0:
                quantity = int(adjusted_position_size / current_price)
                order_type = 'buy'
            elif direction == 'down' and sentiment < 0:
                # Sell existing position or short
                if self.algorithm.Portfolio[symbol].Quantity > 0:
                    quantity = -self.algorithm.Portfolio[symbol].Quantity
                    order_type = 'sell'
                else:
                    quantity = int(adjusted_position_size / current_price)
                    order_type = 'sell_short'
            else:
                return None  # No clear signal
            
            # Apply quantity limits
            max_quantity = self.position_limits[symbol]['max_quantity']
            quantity = max(-max_quantity, min(quantity, max_quantity))
            
            if abs(quantity) == 0:
                return None
            
            # Create order
            reasoning = f"{signal_strength} signal: {direction} direction, {confidence:.2f} confidence, {sentiment:.2f} sentiment"
            
            return TradeOrder(
                symbol=symbol,
                quantity=quantity,
                order_type=order_type,
                timestamp=datetime.now(),
                prediction_confidence=confidence,
                prediction_direction=direction,
                reasoning=reasoning
            )
            
        except Exception as e:
            self.Debug(f"Order creation failed: {e}")
            return None
    
    def _process_predictions(self):
        """Process ML predictions and generate signals"""
        try:
            current_time = datetime.now()
            
            for symbol in self.symbols:
                if symbol not in self.algorithm.Securities:
                    continue
                
                # Get latest prediction
                if self.abacus_data:
                    prediction = self.abacus_data.get_predictions(symbol, current_time)
                else:
                    # Get from Redis if available
                    if self.redis_manager:
                        prediction_data = self.redis_manager.get_latest_prediction(symbol)
                        if prediction_data:
                            prediction = prediction_data.__dict__
                        else:
                            continue
                    else:
                        continue
                
                if prediction:
                    # Create order if strong signal
                    order = self._create_order_from_prediction(prediction)
                    if order and self._should_execute_order(order):
                        self.orders_queue.put(order)
            
        except Exception as e:
            self.Debug(f"Prediction processing failed: {e}")
    
    def _should_execute_order(self, order: TradeOrder) -> bool:
        """Check if order should be executed based on risk and timing"""
        try:
            symbol = order.symbol
            
            # Check daily trade limit
            today = datetime.now().date()
            if today not in self.daily_stats:
                self.daily_stats[today] = {'trades': 0, 'pnl': 0}
            
            if self.daily_stats[today]['trades'] >= self.position_limits[symbol]['max_daily_trades']:
                return False
            
            # Check if we already have a recent order for this symbol
            recent_orders = [o for o in self.executed_orders 
                           if o.symbol == symbol and 
                           (datetime.now() - o.timestamp).seconds < 1800]  # 30 minutes
            
            if len(recent_orders) > 0:
                return False
            
            # Check minimum order size
            current_price = self.algorithm.Securities[symbol].Price
            order_value = abs(order.quantity * current_price)
            min_order_value = self.config.get('min_order_value', 100)
            
            if order_value < min_order_value:
                return False
            
            return True
            
        except Exception as e:
            self.Debug(f"Order execution check failed: {e}")
            return False
    
    def _process_order_queue(self):
        """Process queued orders for execution"""
        try:
            while not self.orders_queue.empty() and self.status == TradingStatus.RUNNING:
                try:
                    order = self.orders_queue.get_nowait()
                    
                    # Execute order with retries
                    if self._execute_order(order):
                        self.executed_orders.append(order)
                        
                        # Update daily stats
                        today = datetime.now().date()
                        if today not in self.daily_stats:
                            self.daily_stats[today] = {'trades': 0, 'pnl': 0}
                        self.daily_stats[today]['trades'] += 1
                    
                except queue.Empty:
                    break
                except Exception as e:
                    self.Debug(f"Order processing error: {e}")
                    time.sleep(0.1)  # Brief pause on error
            
        except Exception as e:
            self.Debug(f"Order queue processing failed: {e}")
    
    def _execute_order(self, order: TradeOrder) -> bool:
        """Execute trading order with error handling"""
        try:
            symbol = order.symbol
            quantity = order.quantity
            
            # Final risk check
            if not self._final_risk_check(order):
                self.Debug(f"Order rejected due to risk check: {symbol}")
                return False
            
            # Execute order
            for attempt in range(self.retry_attempts):
                try:
                    if quantity > 0:
                        order_id = self.algorithm.MarketOrder(symbol, quantity)
                    else:
                        order_id = self.algorithm.MarketOrder(symbol, abs(quantity))
                    
                    self.Debug(f"Order executed: {order.symbol} {order.quantity} shares at ${self.algorithm.Securities[symbol].Price:.2f}")
                    self.algorithm.Debug(f"Trade executed - {order.reasoning}")
                    
                    return True
                    
                except Exception as e:
                    if attempt < self.retry_attempts - 1:
                        self.Debug(f"Order execution attempt {attempt + 1} failed: {e}, retrying...")
                        time.sleep(1)
                    else:
                        self.Debug(f"Order execution failed after {self.retry_attempts} attempts: {e}")
                        return False
            
            return False
            
        except Exception as e:
            self.Debug(f"Order execution failed: {e}")
            return False
    
    def _final_risk_check(self, order: TradeOrder) -> bool:
        """Final risk check before order execution"""
        try:
            symbol = order.symbol
            
            # Check position limits
            current_position = self.algorithm.Portfolio[symbol].Quantity + order.quantity
            current_value = abs(current_position * self.algorithm.Securities[symbol].Price)
            portfolio_value = self.algorithm.Portfolio.TotalPortfolioValue
            
            if current_value > portfolio_value * self.position_limits[symbol]['max_value_pct']:
                return False
            
            # Check daily P&L limit
            today = datetime.now().date()
            if today in self.daily_stats:
                current_daily_pnl = self.daily_stats[today]['pnl']
                max_daily_loss_amount = portfolio_value * self.max_daily_loss
                
                if current_daily_pnl < -max_daily_loss_amount:
                    return False
            
            return True
            
        except Exception as e:
            self.Debug(f"Risk check failed: {e}")
            return False
    
    def _update_risk_metrics(self):
        """Update risk metrics"""
        try:
            portfolio_value = self.algorithm.Portfolio.TotalPortfolioValue
            
            # Calculate current drawdown
            if hasattr(self, 'peak_portfolio_value'):
                self.risk_metrics.current_drawdown = (self.peak_portfolio_value - portfolio_value) / self.peak_portfolio_value
            else:
                self.risk_metrics.current_drawdown = 0
            
            if portfolio_value > getattr(self, 'peak_portfolio_value', 0):
                self.peak_portfolio_value = portfolio_value
            
            # Calculate daily P&L
            today = datetime.now().date()
            if today in self.daily_stats:
                self.risk_metrics.daily_pnl = self.daily_stats[today]['pnl']
            
            # Update other metrics
            self.risk_metrics.total_pnl = portfolio_value - self.config.get('initial_capital', 100000)
            
            self.last_update = datetime.now()
            
        except Exception as e:
            self.Debug(f"Risk metrics update failed: {e}")
    
    def _check_risk_breaches(self) -> bool:
        """Check for risk management breaches"""
        try:
            # Check drawdown limit
            if self.risk_metrics.current_drawdown < -self.config.get('max_drawdown', 0.15):  # 15% max drawdown
                return True
            
            # Check daily loss limit
            if self.risk_metrics.daily_pnl < -self.algorithm.Portfolio.TotalPortfolioValue * self.max_daily_loss:
                return True
            
            return False
            
        except Exception as e:
            self.Debug(f"Risk breach check failed: {e}")
            return False
    
    def _handle_risk_breach(self):
        """Handle risk management breach"""
        try:
            self.Debug("Risk breach detected - pausing trading")
            
            # Pause trading
            self.pause_trading()
            
            # Liquidate positions if severe breach
            if self.risk_metrics.current_drawdown < -0.2:  # 20% drawdown
                self.Debug("Severe risk breach - liquidating all positions")
                for symbol in self.symbols:
                    if self.algorithm.Portfolio[symbol].Quantity != 0:
                        self.algorithm.Liquidate(symbol, "Risk management liquidation")
            
            # Send alert
            self._send_risk_alert()
            
        except Exception as e:
            self.Debug(f"Risk breach handling failed: {e}")
    
    def _send_risk_alert(self):
        """Send risk management alert"""
        try:
            alert_message = f"""
RISK ALERT - Abacus.AI Trading Engine
Time: {datetime.now()}
Status: {self.status.value}
Current Drawdown: {self.risk_metrics.current_drawdown:.2%}
Daily P&L: ${self.risk_metrics.daily_pnl:,.2f}
Total P&L: ${self.risk_metrics.total_pnl:,.2f}

Portfolio Value: ${self.algorithm.Portfolio.TotalPortfolioValue:,.2f}
Positions: {len([s for s in self.algorithm.Portfolio if self.algorithm.Portfolio[s].Quantity != 0])}
            """
            
            self.algorithm.Debug(alert_message)
            
            # Store alert in Redis for monitoring
            if self.redis_manager:
                alert_key = f"risk_alerts:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.redis_manager.redis_client.setex(alert_key, 3600, alert_message)
            
        except Exception as e:
            self.Debug(f"Risk alert failed: {e}")
    
    def _cleanup(self):
        """Clean up resources"""
        try:
            # Close Redis connection
            if self.redis_manager:
                self.redis_manager.cleanup()
            
            # Clear queues
            while not self.orders_queue.empty():
                try:
                    self.orders_queue.get_nowait()
                except queue.Empty:
                    break
            
            self.Debug("Trading engine cleanup completed")
            
        except Exception as e:
            self.Debug(f"Cleanup failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current trading status and metrics"""
        try:
            return {
                'status': self.status.value,
                'running': self.running,
                'symbols_trading': self.symbols,
                'executed_orders': len(self.executed_orders),
                'error_count': self.error_count,
                'risk_metrics': {
                    'current_drawdown': self.risk_metrics.current_drawdown,
                    'daily_pnl': self.risk_metrics.daily_pnl,
                    'total_pnl': self.risk_metrics.total_pnl,
                    'last_update': self.last_update
                },
                'daily_stats': dict(self.daily_stats),
                'last_update': datetime.now()
            }
            
        except Exception as e:
            self.Debug(f"Status retrieval failed: {e}")
            return {'status': 'error', 'error': str(e)}


# Global trading engine instance
_global_trading_engine = None

def get_trading_engine(algorithm: QCAlgorithm, symbols: List[str], config: Dict[str, Any]) -> AbacusAITradingEngine:
    """Get or create global trading engine instance"""
    global _global_trading_engine
    if _global_trading_engine is None or _global_trading_engine.status == TradingStatus.STOPPED:
        _global_trading_engine = AbacusAITradingEngine(algorithm, symbols, config)
    return _global_trading_engine