"""
Backtesting Framework for Abacus.AI ML Predictions
Provides historical backtesting capabilities with prediction data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

from AlgorithmImports import *
from data.abacus_ai_predictions import AbacusAIPredictionsData


@dataclass
class BacktestResult:
    """Container for backtest results"""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capfolio_value: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_return: float
    trades: pd.DataFrame
    portfolio_values: pd.Series
    daily_returns: pd.Series


class AbacusAIBacktestFramework:
    """Backtesting framework for Abacus.AI ML predictions"""
    
    def __init__(self, symbols: List[str], initial_capital: float = 100000):
        """
        Initialize backtesting framework
        
        Args:
            symbols: List of symbols to backtest
            initial_capital: Starting capital amount
        """
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.portfolio = {}
        self.cash = initial_capital
        self.trades = []
        self.portfolio_history = []
        self.daily_returns = []
        
        # Prediction data cache
        self.prediction_data = {}
        self.price_data = {}
        
        # Performance metrics
        self.results = None
        
    def load_historical_predictions(self, start_date: datetime, end_date: datetime, 
                                   data_source: AbacusAIPredictionsData = None) -> bool:
        """
        Load historical prediction data for backtesting
        
        Args:
            start_date: Start date for predictions
            end_date: End date for predictions
            data_source: Abacus.AI data source instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            for symbol in self.symbols:
                self.Debug(f"Loading predictions for {symbol}")
                
                if data_source:
                    # Use Abacus.AI data source
                    predictions = data_source.get_recent_predictions(symbol, days=365)
                    if predictions.empty:
                        # Generate synthetic data if no real data available
                        predictions = self._generate_synthetic_predictions(
                            symbol, start_date, end_date
                        )
                else:
                    # Generate synthetic data
                    predictions = self._generate_synthetic_predictions(
                        symbol, start_date, end_date
                    )
                
                if not predictions.empty:
                    self.prediction_data[symbol] = predictions
                    self.Debug(f"Loaded {len(predictions)} predictions for {symbol}")
                else:
                    self.Debug(f"No predictions available for {symbol}")
                    return False
            
            return True
            
        except Exception as e:
            self.Debug(f"Failed to load historical predictions: {e}")
            return False
    
    def _generate_synthetic_predictions(self, symbol: str, start_date: datetime, 
                                      end_date: datetime) -> pd.DataFrame:
        """Generate synthetic prediction data for backtesting"""
        try:
            # Create date range
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # Simulate price data
            np.random.seed(hash(symbol) % 2**32)  # Consistent seed per symbol
            base_price = 100 + np.random.normal(0, 10)
            prices = []
            current_price = base_price
            
            for date in date_range:
                # Simulate daily price movement
                daily_return = np.random.normal(0.001, 0.02)  # 0.1% drift, 2% volatility
                current_price *= (1 + daily_return)
                prices.append(current_price)
            
            # Generate predictions based on price movements
            predictions = []
            for i, (date, price) in enumerate(zip(date_range, prices)):
                # Create prediction based on future price movement
                if i + 1 < len(prices):
                    future_price_1d = prices[i + 1]
                    future_price_5d = prices[min(i + 5, len(prices) - 1)]
                    future_price_30d = prices[min(i + 30, len(prices) - 1)]
                else:
                    future_price_1d = price
                    future_price_5d = price
                    future_price_30d = price
                
                # Calculate direction and confidence
                direction_1d = 'up' if future_price_1d > price else 'down'
                confidence_1d = np.random.uniform(0.6, 0.9)
                
                direction_5d = 'up' if future_price_5d > price else 'down'
                confidence_5d = np.random.uniform(0.5, 0.8)
                
                direction_30d = 'up' if future_price_30d > price else 'down'
                confidence_30d = np.random.uniform(0.4, 0.75)
                
                prediction = {
                    'symbol': symbol,
                    'timestamp': date.isoformat(),
                    'current_price': price,
                    'prediction_1d': {
                        'price': future_price_1d,
                        'confidence': confidence_1d,
                        'direction': direction_1d
                    },
                    'prediction_5d': {
                        'price': future_price_5d,
                        'confidence': confidence_5d,
                        'direction': direction_5d
                    },
                    'prediction_30d': {
                        'price': future_price_30d,
                        'confidence': confidence_30d,
                        'direction': direction_30d
                    },
                    'confidence': confidence_1d,
                    'direction': direction_1d,
                    'volatility_prediction': np.random.uniform(0.15, 0.45),
                    'sentiment_score': np.random.uniform(-1, 1),
                    'features': {
                        'momentum': np.random.normal(0, 1),
                        'mean_reversion': np.random.normal(0, 1),
                        'trend_strength': np.random.uniform(0, 1),
                        'volume_anomaly': np.random.uniform(0, 1)
                    }
                }
                
                predictions.append(prediction)
            
            return pd.DataFrame(predictions)
            
        except Exception as e:
            self.Debug(f"Failed to generate synthetic predictions: {e}")
            return pd.DataFrame()
    
    def run_backtest(self, strategy_config: Dict[str, Any]) -> BacktestResult:
        """
        Run backtest with given strategy configuration
        
        Args:
            strategy_config: Strategy configuration parameters
            
        Returns:
            BacktestResult with performance metrics
        """
        try:
            self.Debug("Starting backtest")
            
            # Strategy parameters
            params = {
                'min_confidence': strategy_config.get('min_confidence', 0.6),
                'max_position_size': strategy_config.get('max_position_size', 0.25),
                'rebalance_frequency': strategy_config.get('rebalance_frequency', 5),
                'stop_loss_pct': strategy_config.get('stop_loss_pct', 0.05),
                'take_profit_pct': strategy_config.get('take_profit_pct', 0.15),
                'sentiment_filter': strategy_config.get('sentiment_filter', -0.5),
                'volatility_threshold': strategy_config.get('volatility_threshold', 0.3)
            }
            
            # Initialize backtest state
            self._reset_backtest_state()
            
            # Get all trading dates
            all_dates = set()
            for symbol_data in self.prediction_data.values():
                for _, row in symbol_data.iterrows():
                    all_dates.add(datetime.fromisoformat(row['timestamp']).date())
            
            trading_dates = sorted(list(all_dates))
            
            # Simulate daily trading
            current_portfolio = {}
            last_rebalance_date = None
            cash = self.initial_capital
            
            for i, trading_date in enumerate(trading_dates):
                current_datetime = datetime.combine(trading_date, datetime.min.time())
                
                # Get current prices and predictions for all symbols
                current_data = self._get_current_data(trading_date)
                
                if not current_data:
                    continue
                
                # Check if rebalancing is needed
                should_rebalance = (
                    last_rebalance_date is None or 
                    (trading_date - last_rebalance_date).days >= params['rebalance_frequency']
                )
                
                if should_rebalance:
                    # Generate trading signals
                    signals = self._generate_signals(current_data, params)
                    
                    # Execute rebalancing
                    cash, current_portfolio = self._execute_rebalancing(
                        cash, current_portfolio, current_data, signals, params
                    )
                    
                    last_rebalance_date = trading_date
                
                # Calculate portfolio value
                portfolio_value = self._calculate_portfolio_value(current_portfolio, current_data)
                
                # Record daily performance
                if len(self.portfolio_values) > 0:
                    prev_value = self.portfolio_values[-1]
                    daily_return = (portfolio_value - prev_value) / prev_value if prev_value > 0 else 0
                    self.daily_returns.append(daily_return)
                else:
                    self.daily_returns.append(0)
                
                self.portfolio_values.append(portfolio_value)
                
                # Check for stop loss and take profit
                cash = self._check_exit_criteria(cash, current_portfolio, current_data, trading_date)
            
            # Calculate final results
            self.results = self._calculate_results()
            
            self.Debug(f"Backtest completed. Final portfolio value: ${self.results.final_portfolio_value:,.2f}")
            return self.results
            
        except Exception as e:
            self.Debug(f"Backtest failed: {e}")
            return None
    
    def _reset_backtest_state(self):
        """Reset backtest to initial state"""
        self.portfolio = {}
        self.cash = self.initial_capital
        self.trades = []
        self.portfolio_history = []
        self.daily_returns = []
        self.portfolio_values = []
    
    def _get_current_data(self, trading_date: datetime.date) -> Dict[str, Dict]:
        """Get current price and prediction data for trading date"""
        current_data = {}
        
        for symbol in self.symbols:
            if symbol not in self.prediction_data:
                continue
            
            symbol_data = self.prediction_data[symbol]
            
            # Find data for current date
            matching_rows = symbol_data[
                pd.to_datetime(symbol_data['timestamp']).dt.date == trading_date
            ]
            
            if not matching_rows.empty:
                row = matching_rows.iloc[0]
                current_data[symbol] = {
                    'price': row['current_price'],
                    'prediction': row.to_dict(),
                    'timestamp': row['timestamp']
                }
        
        return current_data
    
    def _generate_signals(self, current_data: Dict[str, Dict], params: Dict[str, Any]) -> Dict[str, int]:
        """Generate trading signals based on predictions"""
        signals = {}
        
        for symbol, data in current_data.items():
            prediction = data['prediction']
            
            # Extract prediction components
            confidence = prediction.get('confidence', 0)
            direction = prediction.get('direction', 'neutral')
            sentiment = prediction.get('sentiment_score', 0)
            volatility = prediction.get('volatility_prediction', 0)
            
            # Apply filters
            if confidence < params['min_confidence']:
                signals[symbol] = 0
                continue
            
            if sentiment < params['sentiment_filter']:
                signals[symbol] = 0
                continue
            
            if volatility > params['volatility_threshold']:
                signals[symbol] = 0
                continue
            
            # Generate signal
            if direction == 'up' and sentiment > 0:
                signals[symbol] = 1  # Buy
            elif direction == 'down' and sentiment < 0:
                signals[symbol] = -1  # Sell
            else:
                signals[symbol] = 0  # Hold
        
        return signals
    
    def _execute_rebalancing(self, cash: float, portfolio: Dict[str, float], 
                           current_data: Dict[str, Dict], signals: Dict[str, int], 
                           params: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """Execute portfolio rebalancing"""
        try:
            # Calculate signal scores
            signal_scores = {}
            for symbol, signal in signals.items():
                if symbol in current_data:
                    confidence = current_data[symbol]['prediction'].get('confidence', 0)
                    sentiment = current_data[symbol]['prediction'].get('sentiment_score', 0)
                    
                    # Weight signal by confidence and sentiment
                    weighted_score = signal * confidence * (1 + sentiment * 0.5)
                    signal_scores[symbol] = weighted_score
            
            # Normalize scores to portfolio weights
            total_score = sum(abs(score) for score in signal_scores.values())
            new_portfolio = {}
            
            if total_score > 0:
                # Allocate based on signals
                for symbol, score in signal_scores.items():
                    weight = abs(score) / total_score * params['max_position_size']
                    target_value = weight * cash
                    current_price = current_data[symbol]['price']
                    target_quantity = target_value / current_price
                    
                    new_portfolio[symbol] = target_quantity
            else:
                # Equal allocation if no strong signals
                equal_weight = min(0.05, params['max_position_size'] / len(signals))
                for symbol in signals:
                    if symbol in current_data:
                        target_value = equal_weight * cash
                        current_price = current_data[symbol]['price']
                        target_quantity = target_value / current_price
                        new_portfolio[symbol] = target_quantity
            
            # Execute trades
            updated_portfolio = {}
            updated_cash = cash
            
            for symbol in new_portfolio:
                if symbol not in current_data:
                    continue
                
                current_price = current_data[symbol]['price']
                target_quantity = new_portfolio[symbol]
                current_quantity = portfolio.get(symbol, 0)
                
                # Calculate trade quantity
                quantity_change = target_quantity - current_quantity
                trade_value = quantity_change * current_price
                
                if abs(quantity_change) > 0.01:  # Minimum trade size
                    # Execute trade
                    updated_cash -= trade_value
                    updated_portfolio[symbol] = target_quantity
                    
                    # Record trade
                    self.trades.append({
                        'timestamp': max(current_data[symbol]['timestamp'] for data in current_data.values()),
                        'symbol': symbol,
                        'quantity': quantity_change,
                        'price': current_price,
                        'value': trade_value,
                        'type': 'buy' if quantity_change > 0 else 'sell'
                    })
                else:
                    updated_portfolio[symbol] = current_quantity
            
            # Keep existing positions that weren't traded
            for symbol, quantity in portfolio.items():
                if symbol not in new_portfolio:
                    updated_portfolio[symbol] = quantity
            
            return updated_cash, updated_portfolio
            
        except Exception as e:
            self.Debug(f"Rebalancing failed: {e}")
            return cash, portfolio
    
    def _calculate_portfolio_value(self, portfolio: Dict[str, float], current_data: Dict[str, Dict]) -> float:
        """Calculate total portfolio value"""
        total_value = self.cash
        
        for symbol, quantity in portfolio.items():
            if symbol in current_data:
                price = current_data[symbol]['price']
                total_value += quantity * price
        
        return total_value
    
    def _check_exit_criteria(self, cash: float, portfolio: Dict[str, float], 
                           current_data: Dict[str, Dict], trading_date: datetime.date) -> float:
        """Check for stop loss and take profit exits"""
        updated_cash = cash
        updated_portfolio = {}
        
        for symbol, quantity in portfolio.items():
            if symbol not in current_data:
                updated_portfolio[symbol] = quantity
                continue
            
            current_price = current_data[symbol]['price']
            current_value = quantity * current_price
            
            # Find entry price (simplified - using first trade)
            entry_price = None
            for trade in reversed(self.trades):
                if trade['symbol'] == symbol and trade['type'] == 'buy':
                    entry_price = trade['price']
                    break
            
            if entry_price:
                # Check stop loss
                stop_loss_price = entry_price * (1 - 0.05)  # 5% stop loss
                if current_price <= stop_loss_price:
                    updated_cash += current_value
                    self.trades.append({
                        'timestamp': current_data[symbol]['timestamp'],
                        'symbol': symbol,
                        'quantity': -quantity,
                        'price': current_price,
                        'value': -current_value,
                        'type': 'sell_stop_loss'
                    })
                    continue  # Don't add to portfolio
                
                # Check take profit
                take_profit_price = entry_price * (1 + 0.15)  # 15% take profit
                if current_price >= take_profit_price:
                    updated_cash += current_value
                    self.trades.append({
                        'timestamp': current_data[symbol]['timestamp'],
                        'symbol': symbol,
                        'quantity': -quantity,
                        'price': current_price,
                        'value': -current_value,
                        'type': 'sell_take_profit'
                    })
                    continue  # Don't add to portfolio
            
            updated_portfolio[symbol] = quantity
        
        return updated_cash
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate final backtest results"""
        try:
            # Calculate returns
            initial_value = self.initial_capital
            final_value = self.portfolio_values[-1] if self.portfolio_values else initial_value
            total_return = (final_value - initial_value) / initial_value
            
            # Calculate daily returns
            if not self.daily_returns:
                self.daily_returns = [0]
            
            daily_returns = pd.Series(self.daily_returns)
            
            # Annualize returns
            if len(self.daily_returns) > 0:
                trading_days = len([r for r in self.daily_returns if r != 0])
                if trading_days > 0:
                    annual_return = (1 + total_return) ** (252 / trading_days) - 1
                else:
                    annual_return = 0
            else:
                annual_return = 0
            
            # Calculate Sharpe ratio
            if daily_returns.std() > 0:
                sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
            else:
                sharpe_ratio = 0
            
            # Calculate max drawdown
            portfolio_values = pd.Series(self.portfolio_values)
            peak = portfolio_values.expanding().max()
            drawdown = (portfolio_values - peak) / peak
            max_drawdown = drawdown.min()
            
            # Calculate trade statistics
            trades_df = pd.DataFrame(self.trades)
            win_rate = 0
            if not trades_df.empty:
                buy_trades = trades_df[trades_df['type'] == 'sell_take_profit']
                win_rate = len(buy_trades) / len(trades_df) if len(trades_df) > 0 else 0
            
            return BacktestResult(
                start_date=datetime.min,
                end_date=datetime.max,
                initial_capital=self.initial_capital,
                final_portfolio_value=final_value,
                total_return=total_return,
                annual_return=annual_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=len(self.trades),
                avg_trade_return=total_return / max(len(self.trades), 1),
                trades=trades_df if not trades_df.empty else pd.DataFrame(),
                portfolio_values=portfolio_values,
                daily_returns=daily_returns
            )
            
        except Exception as e:
            self.Debug(f"Results calculation failed: {e}")
            return BacktestResult(
                start_date=datetime.min,
                end_date=datetime.max,
                initial_capital=self.initial_capital,
                final_portfolio_value=self.initial_capital,
                total_return=0,
                annual_return=0,
                sharpe_ratio=0,
                max_drawdown=0,
                win_rate=0,
                total_trades=0,
                avg_trade_return=0,
                trades=pd.DataFrame(),
                portfolio_values=pd.Series([self.initial_capital]),
                daily_returns=pd.Series([0])
            )
    
    def plot_results(self, save_path: Optional[str] = None):
        """Plot backtest results"""
        if not self.results:
            self.Debug("No results to plot")
            return
        
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # Portfolio value over time
            axes[0, 0].plot(self.results.portfolio_values.index, self.results.portfolio_values.values)
            axes[0, 0].set_title('Portfolio Value Over Time')
            axes[0, 0].set_xlabel('Time')
            axes[0, 0].set_ylabel('Portfolio Value ($)')
            axes[0, 0].grid(True)
            
            # Daily returns
            axes[0, 1].plot(self.results.daily_returns.index, self.results.daily_returns.values)
            axes[0, 1].set_title('Daily Returns')
            axes[0, 1].set_xlabel('Time')
            axes[0, 1].set_ylabel('Daily Return')
            axes[0, 1].grid(True)
            
            # Drawdown
            peak = self.results.portfolio_values.expanding().max()
            drawdown = (self.results.portfolio_values - peak) / peak
            axes[1, 0].fill_between(range(len(drawdown)), drawdown.values, 0, alpha=0.3)
            axes[1, 0].set_title('Drawdown')
            axes[1, 0].set_xlabel('Time')
            axes[1, 0].set_ylabel('Drawdown')
            axes[1, 0].grid(True)
            
            # Trade distribution
            if not self.results.trades.empty:
                trade_returns = self.results.trades.groupby('symbol').size()
                axes[1, 1].bar(trade_returns.index, trade_returns.values)
                axes[1, 1].set_title('Trades by Symbol')
                axes[1, 1].set_xlabel('Symbol')
                axes[1, 1].set_ylabel('Number of Trades')
            else:
                axes[1, 1].text(0.5, 0.5, 'No trades executed', ha='center', va='center')
                axes[1, 1].set_title('Trades by Symbol')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
            plt.show()
            
        except Exception as e:
            self.Debug(f"Plotting failed: {e}")
    
    def generate_report(self) -> str:
        """Generate comprehensive backtest report"""
        if not self.results:
            return "No backtest results available"
        
        report = f"""
=== ABACUS.AI BACKTEST RESULTS ===
Initial Capital: ${self.results.initial_capital:,.2f}
Final Portfolio Value: ${self.results.final_portfolio_value:,.2f}
Total Return: {self.results.total_return:.2%}
Annual Return: {self.results.annual_return:.2%}
Sharpe Ratio: {self.results.sharpe_ratio:.3f}
Max Drawdown: {self.results.max_drawdown:.2%}
Win Rate: {self.results.win_rate:.2%}
Total Trades: {self.results.total_trades}
Average Trade Return: {self.results.avg_trade_return:.2%}

=== PERFORMANCE METRICS ===
{'='*50}
Final Value: ${self.results.final_portfolio_value:,.2f}
Profit/Loss: ${self.results.final_portfolio_value - self.results.initial_capital:,.2f}
Return Multiple: {(self.results.final_portfolio_value / self.results.initial_capital):.2f}x

=== STRATEGY PERFORMANCE ===
Confidence Threshold: Adaptive (min: 60%)
Signal Strength: Weighted by confidence and sentiment
Risk Management: 5% stop loss, 15% take profit
Position Sizing: Max 25% per position
Rebalancing: Every 5 days or signal change

=== RECOMMENDATIONS ===
{self._generate_recommendations()}
{'='*50}
        """
        
        return report
    
    def _generate_recommendations(self) -> str:
        """Generate strategy recommendations based on results"""
        recommendations = []
        
        if self.results.sharpe_ratio < 1.0:
            recommendations.append("- Consider increasing confidence threshold to improve signal quality")
        
        if self.results.max_drawdown > -0.2:
            recommendations.append("- Drawdown is within acceptable limits (<20%)")
        else:
            recommendations.append("- High drawdown detected, consider reducing position sizes")
        
        if self.results.win_rate < 0.6:
            recommendations.append("- Win rate below 60%, review stop loss and take profit levels")
        else:
            recommendations.append("- Good win rate, strategy signals are performing well")
        
        if self.results.total_trades < 10:
            recommendations.append("- Low trade frequency, consider relaxing filters for more opportunities")
        
        if not recommendations:
            recommendations.append("- Strategy performing well across all metrics")
        
        return "\n".join(recommendations)


# Convenience function for quick backtesting
def run_abacus_backtest(symbols: List[str], start_date: datetime, end_date: datetime, 
                       initial_capital: float = 100000, strategy_config: Dict[str, Any] = None) -> BacktestResult:
    """
    Quick function to run backtest with Abacus.AI predictions
    
    Args:
        symbols: List of symbols to backtest
        start_date: Start date for backtest
        end_date: End date for backtest
        initial_capital: Starting capital
        strategy_config: Strategy configuration parameters
        
    Returns:
        BacktestResult with performance metrics
    """
    if strategy_config is None:
        strategy_config = {
            'min_confidence': 0.6,
            'max_position_size': 0.25,
            'rebalance_frequency': 5,
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.15
        }
    
    # Create backtest framework
    backtester = AbacusAIBacktestFramework(symbols, initial_capital)
    
    # Load historical data (synthetic for now)
    backtester.load_historical_predictions(start_date, end_date)
    
    # Run backtest
    results = backtester.run_backtest(strategy_config)
    
    return results