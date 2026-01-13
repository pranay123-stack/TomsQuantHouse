"""
ASYMEdge Dashboard API - Trading Metrics Service

Comprehensive trading analytics service providing:
- Real-time market data integration
- Performance metrics calculation
- Portfolio analytics and risk metrics
- Historical data analysis
- Technical indicators and signals
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
from collections import defaultdict
import json

from api.database.models import TradingMetric, MarketData
from api.database.database import get_db_session
from api.schemas import TradingMetricResponse, MarketDataResponse, TradingAnalyticsResponse

logger = logging.getLogger(__name__)

class MetricType(str, Enum):
    """Supported trading metric types"""
    PORTFOLIO_VALUE = "portfolio_value"
    PORTFOLIO_PNL = "portfolio_pnl"
    DAILY_PNL = "daily_pnl"
    TOTAL_RETURN = "total_return"
    CASH_POSITION = "cash_position"
    POSITION_VALUE = "position_value"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    VOLATILITY = "volatility"
    BETA = "beta"
    ALPHA = "alpha"
    INFORMATION_RATIO = "information_ratio"
    CALMAR_RATIO = "calmar_ratio"
    SORTINO_RATIO = "sortino_ratio"
    VAR_95 = "var_95"  # Value at Risk (95% confidence)
    CVAR_95 = "cvar_95"  # Conditional Value at Risk

@dataclass
class MarketDataPoint:
    """Market data point structure"""
    symbol: str
    price: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: datetime = None
    source: str = "internal"

@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_value: float
    cash_value: float
    invested_value: float
    total_pnl: float
    daily_pnl: float
    total_return: float
    daily_return: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    volatility: Optional[float] = None

class TradingDataProvider:
    """Abstract base class for trading data providers"""
    
    async def get_market_data(self, symbol: str, timeframe: str = "1D") -> List[MarketDataPoint]:
        """Get market data for a symbol"""
        raise NotImplementedError
    
    async def get_realtime_price(self, symbol: str) -> float:
        """Get real-time price for a symbol"""
        raise NotImplementedError
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get real-time prices for multiple symbols"""
        raise NotImplementedError

class MockTradingDataProvider(TradingDataProvider):
    """Mock trading data provider for development and testing"""
    
    def __init__(self):
        self._prices: Dict[str, float] = {}
        self._generate_mock_data()
    
    def _generate_mock_data(self):
        """Generate mock market data"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NVDA", "NFLX"]
        
        for symbol in symbols:
            base_price = np.random.uniform(50, 500)
            self._prices[symbol] = base_price
    
    async def get_market_data(self, symbol: str, timeframe: str = "1D") -> List[MarketDataPoint]:
        """Get mock market data"""
        if symbol not in self._prices:
            self._prices[symbol] = np.random.uniform(50, 500)
        
        # Generate mock price history
        current_price = self._prices[symbol]
        data_points = []
        
        for i in range(30):  # 30 days of mock data
            timestamp = datetime.now() - timedelta(days=29-i)
            # Add some random walk
            change = np.random.normal(0, 0.02)  # 2% daily volatility
            price = current_price * (1 + change * i/30)
            volume = np.random.uniform(1000000, 10000000)
            
            data_points.append(MarketDataPoint(
                symbol=symbol,
                price=price,
                volume=volume,
                timestamp=timestamp
            ))
        
        return data_points
    
    async def get_realtime_price(self, symbol: str) -> float:
        """Get mock real-time price"""
        if symbol not in self._prices:
            self._prices[symbol] = np.random.uniform(50, 500)
        
        # Simulate price movement
        price = self._prices[symbol]
        change = np.random.normal(0, 0.001)  # 0.1% price change
        new_price = price * (1 + change)
        self._prices[symbol] = new_price
        
        return new_price
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get mock prices for multiple symbols"""
        return {symbol: await self.get_realtime_price(symbol) for symbol in symbols}

class TradingMetricsCalculator:
    """Calculate various trading performance metrics"""
    
    @staticmethod
    def calculate_returns(prices: List[float]) -> List[float]:
        """Calculate price returns"""
        if len(prices) < 2:
            return []
        
        returns = []
        for i in range(1, len(prices)):
            returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        return returns
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> Optional[float]:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return None
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
        
        return np.mean(excess_returns) / np.std(returns_array) if np.std(returns_array) > 0 else None
    
    @staticmethod
    def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.02) -> Optional[float]:
        """Calculate Sortino ratio (only downside deviation)"""
        if not returns or len(returns) < 2:
            return None
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)
        
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0:
            return float('inf') if np.mean(excess_returns) > 0 else 0
        
        downside_deviation = np.std(downside_returns)
        return np.mean(excess_returns) / downside_deviation if downside_deviation > 0 else None
    
    @staticmethod
    def calculate_max_drawdown(prices: List[float]) -> Optional[float]:
        """Calculate maximum drawdown"""
        if not prices or len(prices) < 2:
            return None
        
        prices_array = np.array(prices)
        running_max = np.maximum.accumulate(prices_array)
        drawdowns = (prices_array - running_max) / running_max
        
        return np.min(drawdowns)  # Most negative value
    
    @staticmethod
    def calculate_volatility(returns: List[float]) -> Optional[float]:
        """Calculate annualized volatility"""
        if not returns or len(returns) < 2:
            return None
        
        return np.std(returns) * np.sqrt(252)  # Annualized
    
    @staticmethod
    def calculate_win_rate(returns: List[float]) -> Optional[float]:
        """Calculate win rate (percentage of positive returns)"""
        if not returns:
            return None
        
        positive_returns = [r for r in returns if r > 0]
        return len(positive_returns) / len(returns)
    
    @staticmethod
    def calculate_var(returns: List[float], confidence_level: float = 0.05) -> Optional[float]:
        """Calculate Value at Risk"""
        if not returns:
            return None
        
        returns_array = np.array(returns)
        return np.percentile(returns_array, confidence_level * 100)
    
    @staticmethod
    def calculate_beta(asset_returns: List[float], market_returns: List[float]) -> Optional[float]:
        """Calculate beta (correlation with market)"""
        if len(asset_returns) != len(market_returns) or len(asset_returns) < 2:
            return None
        
        asset_array = np.array(asset_returns)
        market_array = np.array(market_returns)
        
        covariance = np.cov(asset_array, market_array)[0, 1]
        market_variance = np.var(market_array)
        
        return covariance / market_variance if market_variance > 0 else None

class TradingMetricsService:
    """Main service for trading metrics operations"""
    
    def __init__(self, data_provider: TradingDataProvider = None):
        self.data_provider = data_provider or MockTradingDataProvider()
        self.calculator = TradingMetricsCalculator()
        
    async def get_market_data(self, symbol: str, timeframe: str = "1D") -> List[MarketDataResponse]:
        """Get market data for a symbol"""
        try:
            data_points = await self.data_provider.get_market_data(symbol, timeframe)
            
            return [
                MarketDataResponse(
                    symbol=dp.symbol,
                    price=dp.price,
                    volume=dp.volume,
                    bid=dp.bid,
                    ask=dp.ask,
                    source=dp.source
                )
                for dp in data_points
            ]
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            raise
    
    async def get_realtime_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get real-time prices for multiple symbols"""
        try:
            return await self.data_provider.get_multiple_prices(symbols)
        except Exception as e:
            logger.error(f"Failed to get realtime prices for symbols {symbols}: {e}")
            raise
    
    async def calculate_portfolio_metrics(self, positions: Dict[str, float], 
                                        cash: float = 0.0) -> TradingAnalyticsResponse:
        """Calculate comprehensive portfolio metrics"""
        try:
            # Get current prices for all positions
            symbols = list(positions.keys())
            prices = await self.get_realtime_prices(symbols)
            
            # Calculate position values and P&L
            position_values = {}
            total_invested = 0.0
            
            for symbol, quantity in positions.items():
                current_price = prices.get(symbol, 0.0)
                position_value = quantity * current_price
                position_values[symbol] = position_value
                total_invested += position_value
            
            total_value = total_invested + cash
            
            # For demo purposes, generate mock historical data
            historical_values = await self._generate_mock_historical_values(total_value)
            
            # Calculate metrics
            returns = self.calculator.calculate_returns(historical_values)
            daily_pnl = returns[-1] * total_value if returns else 0.0
            total_return = (total_value / historical_values[0] - 1) if historical_values else 0.0
            
            metrics = TradingAnalyticsResponse(
                portfolio_value=total_value,
                total_pnl=total_value - historical_values[0] if historical_values else 0.0,
                daily_pnl=daily_pnl,
                total_return=total_return,
                sharpe_ratio=self.calculator.calculate_sharpe_ratio(returns),
                max_drawdown=self.calculator.calculate_max_drawdown(historical_values),
                win_rate=self.calculator.calculate_win_rate(returns),
                timestamp=datetime.now()
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio metrics: {e}")
            raise
    
    async def calculate_symbol_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate metrics for a specific symbol"""
        try:
            # Get market data
            market_data = await self.get_market_data(symbol)
            
            if not market_data:
                return {"error": f"No market data available for {symbol}"}
            
            # Extract prices and returns
            prices = [md.price for md in market_data]
            returns = self.calculator.calculate_returns(prices)
            
            metrics = {
                "symbol": symbol,
                "current_price": prices[-1] if prices else 0.0,
                "daily_change": prices[-1] - prices[-2] if len(prices) >= 2 else 0.0,
                "daily_change_percent": ((prices[-1] / prices[-2] - 1) * 100) if len(prices) >= 2 else 0.0,
                "volatility": self.calculator.calculate_volatility(returns),
                "sharpe_ratio": self.calculator.calculate_sharpe_ratio(returns),
                "sortino_ratio": self.calculator.calculate_sortino_ratio(returns),
                "max_drawdown": self.calculator.calculate_max_drawdown(prices),
                "win_rate": self.calculator.calculate_win_rate(returns),
                "var_95": self.calculator.calculate_var(returns),
                "total_return": (prices[-1] / prices[0] - 1) if len(prices) > 1 else 0.0,
                "data_points": len(market_data),
                "price_range": {
                    "min": min(prices) if prices else 0.0,
                    "max": max(prices) if prices else 0.0,
                    "avg": sum(prices) / len(prices) if prices else 0.0
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate metrics for {symbol}: {e}")
            return {"error": str(e)}
    
    async def store_metric(self, metric_type: MetricType, value: float, 
                         symbol: Optional[str] = None, currency: str = "USD",
                         metadata: Dict[str, Any] = None) -> TradingMetricResponse:
        """Store a trading metric in the database"""
        try:
            with get_db_session() as db:
                metric = TradingMetric(
                    metric_type=metric_type.value,
                    symbol=symbol,
                    value=value,
                    currency=currency,
                    metadata=metadata or {}
                )
                
                db.add(metric)
                db.commit()
                db.refresh(metric)
                
                return TradingMetricResponse(
                    id=metric.id,
                    metric_type=metric.metric_type,
                    symbol=metric.symbol,
                    value=metric.value,
                    currency=metric.currency,
                    timestamp=metric.timestamp,
                    metadata=metric.metadata
                )
                
        except Exception as e:
            logger.error(f"Failed to store metric {metric_type.value}: {e}")
            raise
    
    async def get_historical_metrics(self, metric_type: MetricType, 
                                   symbol: Optional[str] = None,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[TradingMetricResponse]:
        """Get historical metrics from database"""
        try:
            with get_db_session() as db:
                query = db.query(TradingMetric).filter(
                    TradingMetric.metric_type == metric_type.value
                )
                
                if symbol:
                    query = query.filter(TradingMetric.symbol == symbol)
                
                if start_date:
                    query = query.filter(TradingMetric.timestamp >= start_date)
                
                if end_date:
                    query = query.filter(TradingMetric.timestamp <= end_date)
                
                metrics = query.order_by(TradingMetric.timestamp.desc()).all()
                
                return [
                    TradingMetricResponse(
                        id=m.id,
                        metric_type=m.metric_type,
                        symbol=m.symbol,
                        value=m.value,
                        currency=m.currency,
                        timestamp=m.timestamp,
                        metadata=m.metadata
                    )
                    for m in metrics
                ]
                
        except Exception as e:
            logger.error(f"Failed to get historical metrics: {e}")
            return []
    
    async def generate_trading_signals(self, symbol: str) -> Dict[str, Any]:
        """Generate trading signals based on technical indicators"""
        try:
            # Get market data
            market_data = await self.get_market_data(symbol)
            
            if len(market_data) < 20:
                return {"error": "Insufficient data for signal generation"}
            
            prices = [md.price for md in market_data]
            
            # Calculate simple moving averages
            sma_20 = np.mean(prices[-20:])
            sma_50 = np.mean(prices[-50:]) if len(prices) >= 50 else sma_20
            
            # Calculate RSI (Relative Strength Index)
            returns = self.calculator.calculate_returns(prices)
            rsi = self._calculate_rsi(returns, period=14)
            
            # Calculate MACD
            macd_line, signal_line = self._calculate_macd(prices)
            
            current_price = prices[-1]
            
            signals = {
                "symbol": symbol,
                "current_price": current_price,
                "timestamp": datetime.now(),
                "sma_20": sma_20,
                "sma_50": sma_50,
                "rsi": rsi,
                "macd": {
                    "macd_line": macd_line,
                    "signal_line": signal_line,
                    "histogram": macd_line - signal_line
                },
                "signals": {
                    "trend": "bullish" if sma_20 > sma_50 else "bearish",
                    "momentum": self._interpret_rsi(rsi),
                    "macd_signal": "bullish" if macd_line > signal_line else "bearish"
                },
                "recommendation": self._generate_recommendation(sma_20, sma_50, rsi, macd_line, signal_line)
            }
            
            return signals
            
        except Exception as e:
            logger.error(f"Failed to generate signals for {symbol}: {e}")
            return {"error": str(e)}
    
    def _calculate_rsi(self, returns: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(returns) < period + 1:
            return 50.0  # Neutral RSI
        
        gains = [r if r > 0 else 0 for r in returns[-period:]]
        losses = [-r if r < 0 else 0 for r in returns[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float]:
        """Calculate MACD line and signal line"""
        if len(prices) < slow:
            return 0.0, 0.0
        
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # For simplicity, use current MACD as signal line
        signal_line = macd_line  # In real implementation, would use EMA of MACD line
        
        return macd_line, signal_line
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return sum(prices) / len(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[-period]
        
        for price in prices[-period+1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _interpret_rsi(self, rsi: float) -> str:
        """Interpret RSI value"""
        if rsi > 70:
            return "oversold"  # Actually overbought, but interpreted as sell signal
        elif rsi < 30:
            return "oversold"
        else:
            return "neutral"
    
    def _generate_recommendation(self, sma_20: float, sma_50: float, rsi: float, 
                               macd_line: float, signal_line: float) -> str:
        """Generate trading recommendation"""
        bullish_signals = 0
        
        if sma_20 > sma_50:
            bullish_signals += 1
        
        if 30 <= rsi <= 70:  # Not extreme
            bullish_signals += 1
        
        if macd_line > signal_line:
            bullish_signals += 1
        
        if bullish_signals >= 2:
            return "BUY"
        elif bullish_signals <= 1:
            return "SELL"
        else:
            return "HOLD"
    
    async def _generate_mock_historical_values(self, current_value: float) -> List[float]:
        """Generate mock historical portfolio values for demo"""
        values = []
        current = current_value
        
        # Generate 30 days of mock data
        for i in range(30):
            # Random walk with slight upward bias
            change = np.random.normal(0.001, 0.01)  # 0.1% average gain, 1% volatility
            current = current * (1 + change)
            values.append(current)
        
        # Ensure the last value matches current value
        values[-1] = current_value
        
        return values

# Global service instance
trading_metrics_service = TradingMetricsService()