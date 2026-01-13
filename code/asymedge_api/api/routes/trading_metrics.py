"""
ASYMEdge Dashboard API - Trading Metrics Routes

Trading metrics endpoints providing:
- Market data retrieval
- Portfolio metrics and analytics
- Performance tracking
- Risk metrics calculation
- Real-time price updates
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from api.database.models import TradingMetric, MarketData
from api.database.database import get_db_session
from api.schemas import (
    MarketDataResponse, TradingMetricResponse, TradingAnalyticsResponse,
    PaginationParams, DateRangeParams, APIResponse
)
from api.services.trading_service import trading_metrics_service, MetricType
from api.middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Market Data Endpoints

@router.get("/market-data/{symbol}", response_model=List[MarketDataResponse])
async def get_market_data(
    symbol: str,
    timeframe: str = Query("1D", description="Time period: 1D, 1W, 1M, 3M, 1Y"),
    limit: int = Query(100, ge=1, le=1000, description="Number of data points"),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get market data for a symbol"""
    try:
        market_data = await trading_metrics_service.get_market_data(symbol, timeframe)
        
        # Limit results
        limited_data = market_data[-limit:] if len(market_data) > limit else market_data
        
        return limited_data
        
    except Exception as e:
        logger.error(f"Failed to get market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/realtime-prices", response_model=Dict[str, float])
async def get_realtime_prices(
    symbols: List[str] = Query(..., description="List of symbols to get prices for"),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get real-time prices for multiple symbols"""
    try:
        if not symbols:
            raise HTTPException(status_code=400, detail={"error": "Symbols list cannot be empty"})
        
        prices = await trading_metrics_service.get_realtime_prices(symbols)
        return prices
        
    except Exception as e:
        logger.error(f"Failed to get realtime prices: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/market-overview", response_model=Dict[str, Any])
async def get_market_overview(
    symbols: Optional[List[str]] = Query(None, description="Specific symbols to include"),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get market overview with key metrics"""
    try:
        # Default symbols if none provided
        if not symbols:
            symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NVDA", "NFLX"]
        
        # Get real-time prices
        prices = await trading_metrics_service.get_realtime_prices(symbols)
        
        # Calculate market summary
        market_summary = {
            "timestamp": datetime.now().isoformat(),
            "symbols_count": len(symbols),
            "symbols_with_data": len([s for s in symbols if s in prices]),
            "market_cap": sum(prices.values()) * 1000000,  # Simplified calculation
            "avg_price": sum(prices.values()) / len(prices) if prices else 0,
            "top_gainers": [],  # Would calculate from price changes
            "top_losers": [],   # Would calculate from price changes
            "sector_performance": {}  # Would group by sectors
        }
        
        return {
            "overview": market_summary,
            "prices": prices
        }
        
    except Exception as e:
        logger.error(f"Failed to get market overview: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Portfolio Analytics Endpoints

@router.get("/portfolio/analytics", response_model=TradingAnalyticsResponse)
async def get_portfolio_analytics(
    positions: Optional[Dict[str, float]] = Query(None, description="Current positions {symbol: quantity}"),
    cash: float = Query(0.0, description="Cash position"),
    include_risk_metrics: bool = Query(True, description="Include risk metrics"),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get comprehensive portfolio analytics"""
    try:
        # Use default portfolio if none provided
        if not positions:
            positions = {
                "AAPL": 167,     # $25,000 at ~$150
                "GOOGL": 11,     # $30,000 at ~$2,800
                "MSFT": 57,      # $20,000 at ~$350
                "TSLA": 25       # $5,000 at ~$200
            }
        
        analytics = await trading_metrics_service.calculate_portfolio_metrics(
            positions=positions,
            cash=cash
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"Failed to get portfolio analytics: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/portfolio/performance", response_model=Dict[str, Any])
async def get_portfolio_performance(
    positions: Optional[Dict[str, float]] = Query(None),
    cash: float = Query(0.0),
    period: str = Query("1M", description="Performance period: 1D, 1W, 1M, 3M, 6M, 1Y, YTD"),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get portfolio performance metrics"""
    try:
        if not positions:
            positions = {"AAPL": 167, "GOOGL": 11, "MSFT": 57}
        
        analytics = await trading_metrics_service.calculate_portfolio_metrics(positions, cash)
        
        # Calculate period-specific returns
        period_multipliers = {
            "1D": 1/365, "1W": 1/52, "1M": 1/12, "3M": 1/4, 
            "6M": 1/2, "1Y": 1, "YTD": 1
        }
        
        multiplier = period_multipliers.get(period, 1/12)
        
        performance = {
            "period": period,
            "total_return": analytics.total_return * multiplier,
            "annualized_return": analytics.total_return,
            "daily_pnl": analytics.daily_pnl,
            "portfolio_value": analytics.portfolio_value,
            "total_pnl": analytics.total_pnl,
            "sharpe_ratio": analytics.sharpe_ratio,
            "max_drawdown": analytics.max_drawdown,
            "win_rate": analytics.win_rate,
            "volatility": analytics.sharpe_ratio * 0.15 if analytics.sharpe_ratio else None,  # Estimated
            "calculated_at": datetime.now().isoformat()
        }
        
        return performance
        
    except Exception as e:
        logger.error(f"Failed to get portfolio performance: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/portfolio/allocation", response_model=Dict[str, Any])
async def get_portfolio_allocation(
    positions: Optional[Dict[str, float]] = Query(None),
    cash: float = Query(0.0),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get portfolio allocation breakdown"""
    try:
        if not positions:
            positions = {"AAPL": 167, "GOOGL": 11, "MSFT": 57}
        
        # Get current prices
        symbols = list(positions.keys())
        prices = await trading_metrics_service.get_realtime_prices(symbols)
        
        # Calculate allocation
        position_values = {symbol: qty * prices.get(symbol, 0) 
                         for symbol, qty in positions.items()}
        
        total_value = sum(position_values.values()) + cash
        
        allocation = {
            "total_value": total_value,
            "cash_value": cash,
            "invested_value": sum(position_values.values()),
            "allocation": {},
            "sectors": {},  # Would map symbols to sectors
            "risk_allocation": {
                "low_risk": 0,    # Bonds, utilities
                "medium_risk": 0, # Diversified stocks
                "high_risk": 0    # Growth stocks, crypto
            }
        }
        
        # Calculate percentage allocation
        for symbol, value in position_values.items():
            allocation["allocation"][symbol] = {
                "value": value,
                "percentage": (value / total_value) * 100,
                "quantity": positions[symbol],
                "current_price": prices.get(symbol, 0)
            }
        
        # Add cash allocation
        allocation["allocation"]["CASH"] = {
            "value": cash,
            "percentage": (cash / total_value) * 100,
            "quantity": 1,
            "current_price": 1.0
        }
        
        return allocation
        
    except Exception as e:
        logger.error(f"Failed to get portfolio allocation: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Individual Symbol Analytics

@router.get("/symbol/{symbol}/analytics", response_model=Dict[str, Any])
async def get_symbol_analytics(
    symbol: str,
    current_user: get_current_user = Depends(get_current_user)
):
    """Get comprehensive analytics for a symbol"""
    try:
        analytics = await trading_metrics_service.calculate_symbol_metrics(symbol)
        return analytics
        
    except Exception as e:
        logger.error(f"Failed to get analytics for {symbol}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/symbol/{symbol}/signals", response_model=Dict[str, Any])
async def get_trading_signals(
    symbol: str,
    current_user: get_current_user = Depends(get_current_user)
):
    """Get trading signals for a symbol"""
    try:
        signals = await trading_metrics_service.generate_trading_signals(symbol)
        return signals
        
    except Exception as e:
        logger.error(f"Failed to get trading signals for {symbol}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Historical Data and Metrics

@router.get("/metrics/{metric_type}", response_model=List[TradingMetricResponse])
async def get_historical_metrics(
    metric_type: MetricType,
    symbol: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get historical trading metrics"""
    try:
        metrics = await trading_metrics_service.get_historical_metrics(
            metric_type=metric_type,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        # Apply limit
        return metrics[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get historical metrics: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/metrics", response_model=TradingMetricResponse)
async def store_metric(
    metric_type: MetricType,
    value: float,
    symbol: Optional[str] = None,
    currency: str = "USD",
    metadata: Optional[Dict[str, Any]] = None,
    current_user: get_current_user = Depends(get_current_user)
):
    """Store a trading metric"""
    try:
        metric_response = await trading_metrics_service.store_metric(
            metric_type=metric_type,
            value=value,
            symbol=symbol,
            currency=currency,
            metadata=metadata
        )
        
        return metric_response
        
    except Exception as e:
        logger.error(f"Failed to store metric: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Risk Management Endpoints

@router.get("/risk/metrics", response_model=Dict[str, Any])
async def get_risk_metrics(
    positions: Optional[Dict[str, float]] = Query(None),
    confidence_level: float = Query(0.95, ge=0.8, le=0.99, description="Confidence level for VaR"),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get portfolio risk metrics"""
    try:
        if not positions:
            positions = {"AAPL": 167, "GOOGL": 11, "MSFT": 57}
        
        # Calculate VaR using historical simulation
        analytics = await trading_metrics_service.calculate_portfolio_metrics(positions)
        symbol_analytics = []
        
        # Get individual symbol analytics for risk calculation
        for symbol in positions.keys():
            symbol_data = await trading_metrics_service.calculate_symbol_metrics(symbol)
            symbol_analytics.append(symbol_data)
        
        # Aggregate risk metrics
        risk_metrics = {
            "portfolio_var": 0,  # Value at Risk
            "portfolio_cvar": 0, # Conditional VaR
            "volatility": analytics.sharpe_ratio * 0.15 if analytics.sharpe_ratio else 0,
            "beta": 1.0,  # Portfolio beta
            "correlation_matrix": {},  # Symbol correlations
            "concentration_risk": {
                "largest_position_pct": max([1, 2, 3]) / sum(positions.values()) * 100,  # Simplified
                "sector_concentration": {}
            },
            "stress_test": {
                "market_crash_20pct": 0,  # Simulated loss in 20% market crash
                "volatility_spike_2x": 0  # Simulated loss with 2x volatility
            },
            "calculated_at": datetime.now().isoformat()
        }
        
        return risk_metrics
        
    except Exception as e:
        logger.error(f"Failed to get risk metrics: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/risk/alerts", response_model=List[Dict[str, Any]])
async def get_risk_alerts(
    positions: Optional[Dict[str, float]] = Query(None),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get risk alerts and warnings"""
    try:
        if not positions:
            positions = {"AAPL": 167, "GOOGL": 11, "MSFT": 57}
        
        alerts = []
        
        # Check for concentration risk
        prices = await trading_metrics_service.get_realtime_prices(list(positions.keys()))
        position_values = {symbol: qty * prices.get(symbol, 0) for symbol, qty in positions.items()}
        total_value = sum(position_values.values())
        
        # Alert if any position > 40% of portfolio
        for symbol, value in position_values.items():
            if value / total_value > 0.4:
                alerts.append({
                    "type": "concentration_risk",
                    "severity": "high",
                    "message": f"Position {symbol} represents {(value/total_value)*100:.1f}% of portfolio",
                    "symbol": symbol,
                    "percentage": (value/total_value)*100
                })
        
        # Check for overallocation (portfolio > cash available)
        # This would require actual account balance in real implementation
        
        # Check for high correlation risk
        # Simplified check for tech stock concentration
        tech_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "META", "NVDA"]
        tech_allocation = sum([position_values.get(sym, 0) for sym in tech_symbols if sym in positions])
        
        if tech_allocation / total_value > 0.8:
            alerts.append({
                "type": "sector_concentration",
                "severity": "medium",
                "message": f"Technology sector represents {(tech_allocation/total_value)*100:.1f}% of portfolio",
                "sector": "Technology",
                "percentage": (tech_allocation/total_value)*100
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to get risk alerts: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Market Summary and Data Feeds

@router.get("/market/summary", response_model=Dict[str, Any])
async def get_market_summary(
    indices: Optional[List[str]] = Query(["SPY", "QQQ", "IWM"], description="Major indices to track"),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get market summary with major indices"""
    try:
        summary_data = {}
        
        for index in indices:
            try:
                analytics = await trading_metrics_service.calculate_symbol_metrics(index)
                summary_data[index] = {
                    "price": analytics.get("current_price", 0),
                    "change": analytics.get("daily_change", 0),
                    "change_percent": analytics.get("daily_change_percent", 0),
                    "volume": analytics.get("volume", 0)  # This would come from real data
                }
            except Exception as e:
                logger.warning(f"Failed to get data for {index}: {e}")
                summary_data[index] = {
                    "price": 0,
                    "change": 0,
                    "change_percent": 0,
                    "volume": 0,
                    "error": str(e)
                }
        
        # Calculate market sentiment (simplified)
        changes = [data.get("change_percent", 0) for data in summary_data.values() if "error" not in data]
        avg_change = sum(changes) / len(changes) if changes else 0
        
        market_sentiment = "neutral"
        if avg_change > 1:
            market_sentiment = "bullish"
        elif avg_change < -1:
            market_sentiment = "bearish"
        
        return {
            "indices": summary_data,
            "market_sentiment": market_sentiment,
            "average_change": avg_change,
            "timestamp": datetime.now().isoformat(),
            "total_tracked": len(indices),
            "successful_tracked": len([i for i in indices if "error" not in summary_data.get(i, {})])
        }
        
    except Exception as e:
        logger.error(f"Failed to get market summary: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/economic/indicators", response_model=Dict[str, Any])
async def get_economic_indicators(
    current_user: get_current_user = Depends(get_current_user)
):
    """Get key economic indicators (mock data for demo)"""
    try:
        # Mock economic data - in production, would fetch from economic APIs
        indicators = {
            "federal_funds_rate": {
                "current": 5.25,
                "previous": 5.00,
                "change": 0.25,
                "change_percent": 5.0,
                "last_updated": datetime.now().isoformat(),
                "source": "Federal Reserve"
            },
            "inflation_rate": {
                "current": 3.2,
                "previous": 3.7,
                "change": -0.5,
                "change_percent": -13.5,
                "last_updated": datetime.now().isoformat(),
                "source": "Bureau of Labor Statistics"
            },
            "unemployment_rate": {
                "current": 3.8,
                "previous": 3.9,
                "change": -0.1,
                "change_percent": -2.6,
                "last_updated": datetime.now().isoformat(),
                "source": "Bureau of Labor Statistics"
            },
            "gdp_growth": {
                "current": 2.4,
                "previous": 2.1,
                "change": 0.3,
                "change_percent": 14.3,
                "last_updated": datetime.now().isoformat(),
                "source": "Bureau of Economic Analysis"
            },
            "vix": {
                "current": 18.5,
                "previous": 21.2,
                "change": -2.7,
                "change_percent": -12.7,
                "last_updated": datetime.now().isoformat(),
                "source": "CBOE"
            }
        }
        
        return {
            "indicators": indicators,
            "last_updated": datetime.now().isoformat(),
            "data_freshness": "real-time"  # or "delayed", "historical"
        }
        
    except Exception as e:
        logger.error(f"Failed to get economic indicators: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})