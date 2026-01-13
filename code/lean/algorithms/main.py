"""
QuantConnect LEAN Algorithm Template for Abacus.AI ML Predictions
Main algorithm that consumes machine learning predictions and makes trading decisions
"""

from AlgorithmImports import *
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from data.abacus_ai_predictions import AbacusAIPredictionsData, get_abacus_data_instance
from config.redis_manager import get_redis_manager


class AbacusAILeanAlgorithm(QCAlgorithm):
    """Main algorithm template for Abacus.AI ML prediction integration"""
    
    def Initialize(self) -> None:
        """Initialize the algorithm"""
        
        # Algorithm settings
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(datetime.now().date())
        self.SetCash(100000)
        
        # Algorithm configuration
        self.config = {
            'symbols': ['AAPL', 'GOOGL', 'MSFT', 'AMZN'],  # Default symbols to trade
            'lookback_days': 30,  # Days of prediction history to use
            'min_confidence': 0.6,  # Minimum prediction confidence to act on
            'max_position_size': 0.25,  # Maximum position size (25% of portfolio)
            'rebalance_frequency': 1,  # Rebalance every N days
            'enable_live_trading': False,  # Enable for live trading
            'enable_redis': False,  # Enable Redis real-time predictions
            'enable_caching': True,  # Enable ObjectStore caching
            'enable_backtesting': True,  # Enable backtesting features
            'volatility_threshold': 0.3,  # Maximum volatility threshold
            'sentiment_filter': -0.5,  # Minimum sentiment score to trade
            'position_hold_days': 5,  # Days to hold positions before rebalancing
            'stop_loss_pct': 0.05,  # 5% stop loss
            'take_profit_pct': 0.15  # 15% take profit
        }
        
        # Algorithm state
        self.last_rebalance = datetime.now() - timedelta(days=999)
        self.positions = {}
        self.predictions_history = {}
        self.performance_metrics = {}
        self.error_count = 0
        self.max_errors = 10
        
        # Data sources
        self.abacus_data = None
        self.redis_manager = None
        
        # Initialize data sources
        self._initialize_data_sources()
        
        # Add securities
        self._add_securities()
        
        # Initialize prediction history
        self._initialize_prediction_history()
        
        # Set up scheduled events
        self._schedule_events()
        
        self.Debug("Abacus.AI LEAN Algorithm initialized")
        self.Debug(f"Configuration: {self.config}")
    
    def _initialize_data_sources(self):
        """Initialize Abacus.AI data sources"""
        try:
            # Initialize Abacus.AI predictions data
            self.abacus_data = get_abacus_data_instance(
                symbol='AAPL',  # Default symbol for initialization
                algorithm=self,
                redis_host='localhost',
                redis_port=6379
            )
            
            # Initialize Redis manager if enabled
            if self.config['enable_redis']:
                try:
                    self.redis_manager = get_redis_manager(
                        host='localhost',
                        port=6379,
                        db=0
                    )
                    
                    # Subscribe to real-time predictions
                    if self.config['enable_live_trading']:
                        self.redis_manager.subscribe_to_predictions(
                            symbols=self.config['symbols'],
                            callback=self._on_realtime_prediction
                        )
                    
                    self.Debug("Redis manager initialized successfully")
                    
                except Exception as e:
                    self.Debug(f"Redis initialization failed: {e}")
                    self.redis_manager = None
            
        except Exception as e:
            self.Debug(f"Data source initialization failed: {e}")
    
    def _add_securities(self):
        """Add securities to the algorithm"""
        try:
            for symbol in self.config['symbols']:
                try:
                    # Add equity
                    equity = self.AddEquity(symbol, Resolution.Daily)
                    
                    # Set data properties
                    if self.config['enable_caching']:
                        equity.SetDataNormalizationMode(DataNormalizationMode.Adjusted)
                    
                    self.Debug(f"Added security: {symbol}")
                    
                except Exception as e:
                    self.Debug(f"Failed to add security {symbol}: {e}")
                    continue
            
            self.Debug(f"Successfully added {len([s for s in self.config['symbols'] if s in [s.Symbol for s in self.Securities]])} securities")
            
        except Exception as e:
            self.Debug(f"Security addition failed: {e}")
    
    def _initialize_prediction_history(self):
        """Initialize prediction history for backtesting"""
        if not self.config['enable_backtesting']:
            return
        
        try:
            for symbol in self.config['symbols']:
                if symbol in self.Securities:
                    # Get historical predictions for backtesting
                    history = self.abacus_data.get_recent_predictions(symbol, self.config['lookback_days'])
                    if not history.empty:
                        self.predictions_history[symbol] = history
                        self.Debug(f"Loaded {len(history)} predictions for {symbol}")
            
            self.Debug(f"Initialized prediction history for {len(self.predictions_history)} symbols")
            
        except Exception as e:
            self.Debug(f"Prediction history initialization failed: {e}")
    
    def _schedule_events(self):
        """Schedule algorithm events"""
        try:
            # Rebalancing event
            if self.config['rebalance_frequency'] > 0:
                self.Schedule.On(
                    self.DateRules.Day(self.Time.day + self.config['rebalance_frequency']),
                    self.TimeRules.AfterMarketOpen("AAPL", 30),
                    self._rebalance_portfolio
                )
            
            # Cache cleanup event
            self.Schedule.On(
                self.DateRules.DayOfWeek(DayOfWeek.Sunday),
                self.TimeRules.At(2, 0),
                self._cleanup_cache
            )
            
            # Performance reporting event
            if self.config['enable_live_trading']:
                self.Schedule.On(
                    self.DateRules.DayOfWeek(DayOfWeek.Friday),
                    self.TimeRules.At(16, 0),
                    self._report_performance
                )
            
            self.Debug("Scheduled events configured")
            
        except Exception as e:
            self.Debug(f"Event scheduling failed: {e}")
    
    def OnData(self, data: Slice) -> None:
        """Process new market data"""
        try:
            if self.error_count > self.max_errors:
                self.Debug("Maximum error count reached. Stopping algorithm.")
                return
            
            # Process market data
            self._process_market_data(data)
            
            # Process predictions
            self._process_predictions(data.Time)
            
            # Execute trading logic
            if self._should_rebalance():
                self._execute_trading_logic()
            
        except Exception as e:
            self.error_count += 1
            self.Debug(f"OnData error (count: {self.error_count}): {e}")
    
    def _process_market_data(self, data: Slice):
        """Process incoming market data"""
        try:
            for symbol in self.config['symbols']:
                if symbol in data and data[symbol] is not None:
                    price = data[symbol].Close
                    
                    # Update position tracking
                    if symbol in self.positions:
                        self.positions[symbol]['current_price'] = price
                        
                        # Check stop loss and take profit
                        self._check_exit_criteria(symbol)
            
        except Exception as e:
            self.Debug(f"Market data processing error: {e}")
    
    def _process_predictions(self, current_time: datetime):
        """Process ML predictions for trading decisions"""
        try:
            for symbol in self.config['symbols']:
                if symbol not in self.Securities:
                    continue
                
                # Get latest prediction
                prediction = self.abacus_data.get_predictions(symbol, current_time)
                
                if prediction:
                    # Store prediction
                    if symbol not in self.predictions_history:
                        self.predictions_history[symbol] = []
                    
                    self.predictions_history[symbol].append({
                        'timestamp': current_time,
                        'prediction': prediction
                    })
                    
                    # Evaluate trading signal
                    self._evaluate_trading_signal(symbol, prediction)
                    
        except Exception as e:
            self.Debug(f"Prediction processing error: {e}")
    
    def _evaluate_trading_signal(self, symbol: str, prediction: dict):
        """Evaluate trading signal from ML prediction"""
        try:
            # Extract key prediction values
            prediction_1d = prediction.get('prediction_1d', {})
            confidence = prediction.get('confidence', 0)
            direction = prediction.get('direction', 'neutral')
            sentiment = prediction.get('sentiment_score', 0)
            volatility = prediction.get('volatility_prediction', 0)
            
            # Apply filters
            if confidence < self.config['min_confidence']:
                return
            
            if sentiment < self.config['sentiment_filter']:
                return
            
            if volatility > self.config['volatility_threshold']:
                return
            
            # Generate signal
            if direction == 'up' and sentiment > 0:
                signal = 1  # Buy signal
            elif direction == 'down' and sentiment < 0:
                signal = -1  # Sell signal
            else:
                signal = 0  # Hold
            
            # Store signal for trading
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'signal': 0,
                    'entry_price': None,
                    'entry_time': None,
                    'current_price': None,
                    'signal_strength': confidence,
                    'last_signal_time': None
                }
            
            self.positions[symbol].update({
                'signal': signal,
                'signal_strength': confidence,
                'last_signal_time': self.Time
            })
            
        except Exception as e:
            self.Debug(f"Signal evaluation error for {symbol}: {e}")
    
    def _should_rebalance(self) -> bool:
        """Check if portfolio should be rebalanced"""
        days_since_rebalance = (self.Time - self.last_rebalance).days
        return days_since_rebalance >= self.config['rebalance_frequency']
    
    def _execute_trading_logic(self):
        """Execute main trading logic"""
        try:
            # Update last rebalance time
            self.last_rebalance = self.Time
            
            # Analyze all symbols and generate portfolio
            portfolio_weights = self._generate_portfolio_weights()
            
            # Execute trades based on portfolio weights
            self._execute_portfolio_trades(portfolio_weights)
            
            # Update performance metrics
            self._update_performance_metrics()
            
            self.Debug(f"Portfolio rebalance completed at {self.Time}")
            
        except Exception as e:
            self.Debug(f"Trading logic execution error: {e}")
    
    def _generate_portfolio_weights(self) -> dict:
        """Generate portfolio weights based on predictions"""
        try:
            weights = {}
            total_score = 0
            
            # Calculate scores for each symbol
            for symbol in self.config['symbols']:
                if symbol not in self.Securities:
                    continue
                
                if symbol in self.positions:
                    position = self.positions[symbol]
                    signal = position.get('signal', 0)
                    strength = position.get('signal_strength', 0)
                    
                    # Calculate weighted score
                    score = signal * strength
                    
                    # Apply sentiment multiplier
                    if symbol in self.predictions_history and self.predictions_history[symbol]:
                        latest_prediction = self.predictions_history[symbol][-1]['prediction']
                        sentiment = latest_prediction.get('sentiment_score', 0)
                        score *= (1 + sentiment * 0.5)
                    
                    weights[symbol] = score
                    total_score += abs(score)
            
            # Normalize weights
            if total_score > 0:
                max_weight = self.config['max_position_size']
                for symbol in weights:
                    weights[symbol] = (weights[symbol] / total_score) * max_weight
            else:
                # Equal weights if no strong signals
                equal_weight = min(0.05, self.config['max_position_size'] / len(weights))
                for symbol in weights:
                    weights[symbol] = equal_weight
            
            return weights
            
        except Exception as e:
            self.Debug(f"Portfolio weight generation error: {e}")
            return {}
    
    def _execute_portfolio_trades(self, weights: dict):
        """Execute portfolio trades based on weights"""
        try:
            total_portfolio_value = self.Portfolio.TotalPortfolioValue
            
            for symbol, target_weight in weights.items():
                if symbol not in self.Securities:
                    continue
                
                current_weight = self.Portfolio[symbol].Value / total_portfolio_value
                target_value = target_weight * total_portfolio_value
                current_value = self.Portfolio[symbol].Quantity * self.Securities[symbol].Price
                
                # Calculate order quantity
                delta_value = target_value - current_value
                price = self.Securities[symbol].Price
                
                if price > 0:
                    order_quantity = int(delta_value / price)
                    
                    # Execute order if significant change
                    if abs(order_quantity) > 0:
                        quantity = abs(order_quantity)
                        if order_quantity > 0:
                            self.MarketOrder(symbol, quantity)
                            self.Debug(f"BUY {quantity} {symbol} at ${price:.2f}")
                        else:
                            self.MarketOrder(symbol, -quantity)
                            self.Debug(f"SELL {quantity} {symbol} at ${price:.2f}")
            
        except Exception as e:
            self.Debug(f"Trade execution error: {e}")
    
    def _check_exit_criteria(self, symbol: str):
        """Check stop loss and take profit criteria"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            current_price = position.get('current_price')
            entry_price = position.get('entry_price')
            
            if current_price and entry_price:
                # Check stop loss
                stop_loss_price = entry_price * (1 - self.config['stop_loss_pct'])
                if current_price <= stop_loss_price:
                    self.Liquidate(symbol, f"Stop loss triggered for {symbol}")
                    self.Debug(f"Stop loss executed for {symbol} at ${current_price:.2f}")
                    return
                
                # Check take profit
                take_profit_price = entry_price * (1 + self.config['take_profit_pct'])
                if current_price >= take_profit_price:
                    self.Liquidate(symbol, f"Take profit triggered for {symbol}")
                    self.Debug(f"Take profit executed for {symbol} at ${current_price:.2f}")
                    return
                
                # Check position age
                if position.get('entry_time'):
                    days_held = (self.Time - position['entry_time']).days
                    if days_held >= self.config['position_hold_days']:
                        self.Liquidate(symbol, f"Position age limit reached for {symbol}")
                        self.Debug(f"Position liquidated after {days_held} days for {symbol}")
        
        except Exception as e:
            self.Debug(f"Exit criteria check error for {symbol}: {e}")
    
    def _on_realtime_prediction(self, prediction):
        """Handle real-time prediction from Redis"""
        try:
            symbol = prediction.symbol
            
            if symbol in self.config['symbols']:
                # Update prediction cache
                if self.abacus_data:
                    cache_key = f"{symbol}_{prediction.timestamp}"
                    self.abacus_data.predictions_cache[cache_key] = prediction.__dict__
                
                # Immediate signal evaluation if in live trading mode
                if self.config['enable_live_trading']:
                    self._evaluate_live_trading_signal(symbol, prediction)
            
        except Exception as e:
            self.Debug(f"Real-time prediction handling error: {e}")
    
    def _evaluate_live_trading_signal(self, symbol: str, prediction):
        """Evaluate signal for live trading mode"""
        try:
            # High confidence immediate actions
            if prediction.confidence > 0.8:
                if symbol in self.Securities:
                    price = self.Securities[symbol].Price
                    
                    if prediction.direction == 'up' and prediction.sentiment_score > 0:
                        # Quick buy signal
                        quantity = int((self.Portfolio.TotalPortfolioValue * 0.05) / price)  # 5% position
                        if quantity > 0:
                            self.MarketOrder(symbol, quantity)
                            self.Debug(f"IMMEDIATE BUY {quantity} {symbol} at ${price:.2f}")
                    
                    elif prediction.direction == 'down' and prediction.sentiment_score < 0:
                        # Quick sell signal
                        if self.Portfolio[symbol].Quantity > 0:
                            self.Liquidate(symbol, "Negative prediction signal")
                            self.Debug(f"IMMEDIATE SELL {symbol}")
            
        except Exception as e:
            self.Debug(f"Live trading signal evaluation error: {e}")
    
    def _cleanup_cache(self):
        """Clean up prediction cache"""
        try:
            if self.abacus_data:
                self.abacus_data.clean_cache()
            self.Debug("Cache cleanup completed")
        except Exception as e:
            self.Debug(f"Cache cleanup error: {e}")
    
    def _update_performance_metrics(self):
        """Update algorithm performance metrics"""
        try:
            total_value = self.Portfolio.TotalPortfolioValue
            initial_value = self.config['cash'] if hasattr(self, 'config') else 100000
            total_return = (total_value - initial_value) / initial_value
            
            self.performance_metrics.update({
                'total_return': total_return,
                'total_portfolio_value': total_value,
                'cash': self.Portfolio.Cash,
                'holdings_count': len([s for s in self.Portfolio if self.Portfolio[s].Quantity > 0]),
                'last_update': self.Time
            })
            
        except Exception as e:
            self.Debug(f"Performance metrics update error: {e}")
    
    def _report_performance(self):
        """Report algorithm performance"""
        try:
            if self.performance_metrics:
                self.Debug("=== PERFORMANCE REPORT ===")
                self.Debug(f"Total Return: {self.performance_metrics.get('total_return', 0):.2%}")
                self.Debug(f"Portfolio Value: ${self.performance_metrics.get('total_portfolio_value', 0):,.2f}")
                self.Debug(f"Cash: ${self.performance_metrics.get('cash', 0):,.2f}")
                self.Debug(f"Active Holdings: {self.performance_metrics.get('holdings_count', 0)}")
                self.Debug(f"Timestamp: {self.performance_metrics.get('last_update', 'N/A')}")
                self.Debug("=========================")
            
        except Exception as e:
            self.Debug(f"Performance reporting error: {e}")
    
    def OnEndOfAlgorithm(self):
        """Final cleanup and reporting"""
        try:
            # Final performance report
            self._report_performance()
            
            # Cleanup resources
            if self.redis_manager:
                self.redis_manager.cleanup()
            
            # Save final state
            final_metrics = {
                'algorithm_ended': self.Time,
                'final_portfolio_value': self.Portfolio.TotalPortfolioValue,
                'performance_metrics': self.performance_metrics,
                'total_errors': self.error_count,
                'symbols_traded': list(self.positions.keys())
            }
            
            self.Debug(f"Algorithm ended with final metrics: {final_metrics}")
            
        except Exception as e:
            self.Debug(f"OnEndOfAlgorithm error: {e}")
    
    def OnError(self, errors):
        """Handle algorithm errors"""
        try:
            for error in errors:
                self.error_count += 1
                self.Debug(f"Algorithm error (count: {self.error_count}): {error}")
                
                if self.error_count > self.max_errors:
                    self.Debug("Maximum error count reached. Halting algorithm.")
                    self.Quit(f"Algorithm halted after {self.error_count} errors")
                    break
            
        except Exception as e:
            self.Debug(f"OnError handler error: {e}")
    
    def OnEndOfDay(self, symbol: str):
        """End of day processing"""
        try:
            # Update daily metrics
            if hasattr(self, 'Portfolio'):
                daily_value = self.Portfolio.TotalPortfolioValue
                self.Debug(f"End of day {self.Time.date()}: Portfolio value ${daily_value:,.2f}")
            
            # Clean up daily cache if needed
            if symbol == 'AAPL':  # Only run once per day
                self._cleanup_cache()
                
        except Exception as e:
            self.Debug(f"OnEndOfDay error for {symbol}: {e}")


# Algorithm entry point for LEAN
def main():
    """Main function for LEAN algorithm execution"""
    return AbacusAILeanAlgorithm()


# For direct testing
if __name__ == "__main__":
    algorithm = AbacusAILeanAlgorithm()
    print("Abacus.AI LEAN Algorithm template ready")