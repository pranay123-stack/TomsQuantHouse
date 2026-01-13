"""
Complete Example: Abacus.AI LEAN Integration
Demonstrates all components working together
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json

# Add paths for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import get_config, get_strategy_config
from data.abacus_ai_predictions import AbacusAIPredictionsData, get_abacus_data_instance
from config.redis_manager import get_redis_manager
from research.backtesting_framework import AbacusAIBacktestFramework, run_abacus_backtest
from algorithms.live_trading import get_trading_engine, AbacusAITradingEngine
from config.prediction_cache import get_prediction_cache
from AlgorithmImports import *
from algorithms.main import AbacusAILeanAlgorithm


class ExampleAbacusAIAlgorithm(AbacusAILeanAlgorithm):
    """
    Extended example algorithm demonstrating full Abacus.AI integration
    """
    
    def Initialize(self) -> None:
        """Initialize with custom configuration"""
        
        # Use custom configuration
        config = get_config('development', {
            'symbols': ['AAPL', 'GOOGL', 'MSFT'],
            'initial_capital': 100000,
            'enable_live_trading': False,
            'enable_redis': False,
            'min_confidence': 0.6,
            'max_position_size': 0.2
        })
        
        # Set algorithm parameters
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(datetime.now().date())
        self.SetCash(config.initial_capital)
        
        # Store configuration
        self.abacus_config = config
        
        # Initialize cache
        self.cache = get_prediction_cache(self, config.to_dict())
        
        # Initialize data sources
        self._initialize_extended_data_sources()
        
        # Add securities
        self._add_securities()
        
        # Custom scheduled events
        self._setup_custom_events()
        
        self.Debug("=== EXAMPLE ALGORITHM INITIALIZED ===")
        self.Debug(f"Configuration: {json.dumps(config.to_dict(), indent=2, default=str)}")
    
    def _initialize_extended_data_sources(self):
        """Initialize extended data sources"""
        try:
            # Initialize Abacus.AI data with cache
            self.abacus_data = get_abacus_data_instance(
                symbol='AAPL',
                algorithm=self,
                redis_host=self.abacus_config.redis_host,
                redis_port=self.abacus_config.redis_port
            )
            
            # Initialize Redis manager if enabled
            if self.abacus_config.enable_redis:
                try:
                    self.redis_manager = get_redis_manager(
                        host=self.abacus_config.redis_host,
                        port=self.abacus_config.redis_port
                    )
                    
                    # Subscribe to predictions
                    if self.abacus_config.enable_live_trading:
                        self.redis_manager.subscribe_to_predictions(
                            symbols=self.abacus_config.symbols,
                            callback=self._on_realtime_prediction
                        )
                    
                    self.Debug("Extended data sources initialized")
                    
                except Exception as e:
                    self.Debug(f"Redis initialization failed: {e}")
                    self.redis_manager = None
            
        except Exception as e:
            self.Debug(f"Extended data source initialization failed: {e}")
    
    def _setup_custom_events(self):
        """Setup custom algorithm events"""
        try:
            # Cache statistics report
            self.Schedule.On(
                self.DateRules.DayOfWeek(DayOfWeek.Monday),
                self.TimeRules.At(9, 0),
                self._report_cache_statistics
            )
            
            # Performance analysis
            self.Schedule.On(
                self.DateRules.DayOfWeek(DayOfWeek.Friday),
                self.TimeRules.At(16, 0),
                self._analyze_performance
            )
            
            # Cache optimization
            self.Schedule.On(
                self.DateRules.DayOfWeek(DayOfWeek.Sunday),
                self.TimeRules.At(2, 0),
                self._optimize_cache
            )
            
            self.Debug("Custom events configured")
            
        except Exception as e:
            self.Debug(f"Custom event setup failed: {e}")
    
    def _report_cache_statistics(self):
        """Report cache performance statistics"""
        try:
            stats = self.cache.get_cache_stats()
            self.Debug("=== CACHE STATISTICS ===")
            self.Debug(f"Cache Size: {stats['cache_size']}")
            self.Debug(f"Hit Rate: {stats['hit_rate']:.2%}")
            self.Debug(f"Total Requests: {stats['total_requests']}")
            self.Debug(f"Memory Usage: {stats['memory_usage_bytes']:,} bytes")
            self.Debug(f"Hits: {stats['hits']}, Misses: {stats['misses']}")
            self.Debug(f"Evictions: {stats['evictions']}")
            self.Debug(f"Errors: {stats['errors']}")
            self.Debug("=========================")
            
        except Exception as e:
            self.Debug(f"Cache statistics reporting failed: {e}")
    
    def _analyze_performance(self):
        """Analyze algorithm performance"""
        try:
            total_value = self.Portfolio.TotalPortfolioValue
            initial_value = self.abacus_config.initial_capital
            total_return = (total_value - initial_value) / initial_value
            
            # Calculate daily returns
            if hasattr(self, 'daily_returns') and self.daily_returns:
                returns_series = pd.Series(self.daily_returns)
                sharpe_ratio = returns_series.mean() / returns_series.std() * np.sqrt(252) if returns_series.std() > 0 else 0
            else:
                sharpe_ratio = 0
            
            self.Debug("=== PERFORMANCE ANALYSIS ===")
            self.Debug(f"Total Return: {total_return:.2%}")
            self.Debug(f"Sharpe Ratio: {sharpe_ratio:.3f}")
            self.Debug(f"Portfolio Value: ${total_value:,.2f}")
            self.Debug(f"Active Positions: {len([s for s in self.Portfolio if self.Portfolio[s].Quantity != 0])}")
            self.Debug(f"Cash: ${self.Portfolio.Cash:,.2f}")
            self.Debug("===========================")
            
        except Exception as e:
            self.Debug(f"Performance analysis failed: {e}")
    
    def _optimize_cache(self):
        """Optimize cache performance"""
        try:
            optimization_results = self.cache.optimize_cache()
            self.Debug(f"Cache optimization results: {optimization_results}")
            
        except Exception as e:
            self.Debug(f"Cache optimization failed: {e}")
    
    def _execute_trading_logic(self):
        """Enhanced trading logic with caching"""
        try:
            # Use cache for predictions
            portfolio_weights = {}
            total_score = 0
            
            for symbol in self.abacus_config.symbols:
                if symbol not in self.Securities:
                    continue
                
                # Generate cache key
                cache_key = self.cache.generate_cache_key(symbol, self.Time, '1d')
                
                # Get prediction with caching
                prediction = self.cache.get(
                    cache_key,
                    fallback_func=self.abacus_data.get_predictions,
                    symbol=symbol,
                    as_of_date=self.Time
                )
                
                if prediction:
                    # Evaluate signal
                    signal_strength = self._evaluate_cached_signal(symbol, prediction)
                    portfolio_weights[symbol] = signal_strength
                    total_score += abs(signal_strength)
            
            # Normalize weights and execute
            if total_score > 0:
                self._execute_cached_trades(portfolio_weights, total_score)
            
            self.Debug(f"Enhanced trading logic executed for {len(portfolio_weights)} symbols")
            
        except Exception as e:
            self.Debug(f"Enhanced trading logic failed: {e}")
    
    def _evaluate_cached_signal(self, symbol: str, prediction: dict) -> float:
        """Evaluate signal using cached prediction"""
        try:
            confidence = prediction.get('confidence', 0)
            direction = prediction.get('direction', 'neutral')
            sentiment = prediction.get('sentiment_score', 0)
            
            # Apply configuration filters
            if confidence < self.abacus_config.min_confidence:
                return 0
            
            if sentiment < self.abacus_config.sentiment_filter:
                return 0
            
            # Calculate signal strength
            if direction == 'up' and sentiment > 0:
                return confidence * (1 + sentiment * 0.5)
            elif direction == 'down' and sentiment < 0:
                return -confidence * (1 + abs(sentiment) * 0.5)
            else:
                return 0
                
        except Exception as e:
            self.Debug(f"Signal evaluation failed for {symbol}: {e}")
            return 0
    
    def _execute_cached_trades(self, portfolio_weights: dict, total_score: float):
        """Execute trades based on weighted portfolio"""
        try:
            total_portfolio_value = self.Portfolio.TotalPortfolioValue
            
            for symbol, signal_strength in portfolio_weights.items():
                if symbol not in self.Securities:
                    continue
                
                # Calculate target weight
                weight = (abs(signal_strength) / total_score) * self.abacus_config.max_position_size
                target_value = weight * total_portfolio_value
                
                # Get current position
                current_value = self.Portfolio[symbol].Quantity * self.Securities[symbol].Price
                
                # Calculate order quantity
                price = self.Securities[symbol].Price
                if price > 0:
                    quantity_change = int((target_value - current_value) / price)
                    
                    if abs(quantity_change) > 0:
                        # Use signal direction
                        if signal_strength > 0 and quantity_change < 0:
                            quantity_change = abs(quantity_change)
                            self.MarketOrder(symbol, quantity_change)
                            self.Debug(f"CACHED TRADE BUY: {quantity_change} {symbol}")
                        elif signal_strength < 0 and quantity_change > 0:
                            quantity_change = -quantity_change
                            self.MarketOrder(symbol, abs(quantity_change))
                            self.Debug(f"CACHED TRADE SELL: {quantity_change} {symbol}")
            
        except Exception as e:
            self.Debug(f"Cached trade execution failed: {e}")


def run_example_backtest():
    """Run comprehensive backtesting example"""
    print("=== RUNNING ABACUS.AI BACKTESTING EXAMPLE ===")
    
    try:
        # Get configuration for backtesting
        config = get_config('testing', {
            'symbols': ['AAPL', 'GOOGL', 'MSFT'],
            'start_date': '2024-01-01',
            'end_date': '2024-03-31',
            'initial_capital': 50000
        })
        
        # Create backtest framework
        backtester = AbacusAIBacktestFramework(config.symbols, config.initial_capital)
        
        # Load historical data
        start_date = datetime.strptime(config.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(config.end_date, '%Y-%m-%d')
        
        success = backtester.load_historical_predictions(start_date, end_date)
        if not success:
            print("Failed to load historical predictions")
            return
        
        # Configure strategy
        strategy_config = {
            'min_confidence': config.min_confidence,
            'max_position_size': config.max_position_size,
            'rebalance_frequency': config.rebalance_frequency,
            'stop_loss_pct': config.stop_loss_pct,
            'take_profit_pct': config.take_profit_pct,
            'sentiment_filter': config.sentiment_filter,
            'volatility_threshold': config.volatility_threshold
        }
        
        # Run backtest
        results = backtester.run_backtest(strategy_config)
        
        if results:
            print(f"Backtest Results:")
            print(f"Initial Capital: ${results.initial_capital:,.2f}")
            print(f"Final Value: ${results.final_portfolio_value:,.2f}")
            print(f"Total Return: {results.total_return:.2%}")
            print(f"Annual Return: {results.annual_return:.2%}")
            print(f"Sharpe Ratio: {results.sharpe_ratio:.3f}")
            print(f"Max Drawdown: {results.max_drawdown:.2%}")
            print(f"Total Trades: {results.total_trades}")
            print(f"Win Rate: {results.win_rate:.2%}")
            
            # Generate detailed report
            report = backtester.generate_report()
            print(report)
            
            # Plot results if matplotlib is available
            try:
                import matplotlib.pyplot as plt
                backtester.plot_results('backtest_results.png')
                print("Backtest results plotted to backtest_results.png")
            except ImportError:
                print("Matplotlib not available for plotting")
        else:
            print("Backtest failed")
        
    except Exception as e:
        print(f"Backtest example failed: {e}")


def demonstrate_cache_usage():
    """Demonstrate cache functionality"""
    print("\n=== CACHE DEMONSTRATION ===")
    
    try:
        # Create mock algorithm object for cache demonstration
        class MockAlgorithm:
            def __init__(self):
                self.object_store = None
            
            def Debug(self, message):
                print(f"MockAlgo: {message}")
        
        # Create cache
        algorithm = MockAlgorithm()
        cache = get_prediction_cache(algorithm, {'enable_stats': True})
        
        # Demonstrate basic caching
        print("1. Testing basic caching...")
        
        def mock_prediction_function(symbol, date):
            return {
                'symbol': symbol,
                'confidence': 0.75,
                'direction': 'up',
                'prediction': f'Prediction for {symbol} on {date}'
            }
        
        # Cache a prediction
        cache_key = cache.generate_cache_key('AAPL', datetime.now())
        cache.set(cache_key, {'confidence': 0.85, 'direction': 'up'})
        
        # Retrieve from cache
        cached_data = cache.get(cache_key)
        print(f"Cached data: {cached_data}")
        
        # Demonstrate fallback function
        fallback_data = cache.get(
            cache_key + '_fallback',
            fallback_func=mock_prediction_function,
            symbol='GOOGL',
            date=datetime.now()
        )
        print(f"Fallback data: {fallback_data}")
        
        # Show cache statistics
        stats = cache.get_cache_stats()
        print(f"Cache statistics: {stats}")
        
        print("Cache demonstration completed successfully")
        
    except Exception as e:
        print(f"Cache demonstration failed: {e}")


def demonstrate_redis_manager():
    """Demonstrate Redis manager functionality"""
    print("\n=== REDIS MANAGER DEMONSTRATION ===")
    
    try:
        # Initialize Redis manager
        redis_manager = get_redis_manager(host='localhost', port=6379)
        
        # Check health
        health = redis_manager.health_check()
        print(f"Redis health: {health}")
        
        if health['status'] == 'healthy':
            # Create sample prediction
            from config.redis_manager import PredictionMessage
            
            prediction = PredictionMessage(
                symbol='AAPL',
                timestamp=datetime.now().isoformat(),
                current_price=150.0,
                prediction_1d={'price': 152.0, 'confidence': 0.8, 'direction': 'up'},
                prediction_5d={'price': 155.0, 'confidence': 0.7, 'direction': 'up'},
                prediction_30d={'price': 160.0, 'confidence': 0.6, 'direction': 'up'},
                confidence=0.8,
                direction='up',
                volatility_prediction=0.25,
                sentiment_score=0.3,
                features={'momentum': 0.1, 'mean_reversion': -0.2}
            )
            
            # Publish prediction
            success = redis_manager.publish_prediction(prediction)
            print(f"Prediction published: {success}")
            
            # Retrieve latest prediction
            latest = redis_manager.get_latest_prediction('AAPL')
            if latest:
                print(f"Latest prediction for AAPL: {latest.direction}, confidence: {latest.confidence}")
            else:
                print("No latest prediction found")
        else:
            print("Redis not available - this is normal if Redis is not running")
        
    except Exception as e:
        print(f"Redis demonstration failed: {e}")


def main():
    """Main demonstration function"""
    print("Abacus.AI LEAN Integration - Complete Example")
    print("=" * 50)
    
    # Run backtest example
    run_example_backtest()
    
    # Demonstrate cache
    demonstrate_cache_usage()
    
    # Demonstrate Redis (if available)
    demonstrate_redis_manager()
    
    print("\n" + "=" * 50)
    print("All demonstrations completed!")
    print("\nTo run the actual LEAN algorithm:")
    print("1. Copy the main.py to your LEAN algorithms directory")
    print("2. Configure the config.py with your settings")
    print("3. Ensure Redis is running for real-time data")
    print("4. Set up your Abacus.AI API credentials")
    print("5. Run the algorithm with: quantconnect create ... && lean cloud deploy")


if __name__ == "__main__":
    main()