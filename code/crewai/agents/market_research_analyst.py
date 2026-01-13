"""
Market Research Analyst Agent
Specializes in financial market analysis and research
"""
from typing import Dict, List, Optional, Any
from crewai import Agent
from crewai_tools import BaseTool
from utils.memory_manager import memory_manager
from cache.cache_manager import cache_manager, MarketDataCache
from config.settings import AgentPrompts
import yfinance as yf
import pandas as pd
import logging


class MarketDataTool(BaseTool):
    """Tool for fetching market data"""
    name: str = "Market Data Fetcher"
    description: str = "Fetches real-time and historical market data for symbols"
    
    def _run(self, symbol: str, period: str = "1y") -> Dict[str, Any]:
        """Fetch market data for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            # Calculate basic statistics
            current_price = data['Close'].iloc[-1]
            previous_price = data['Close'].iloc[-2]
            price_change = current_price - previous_price
            price_change_pct = (price_change / previous_price) * 100
            
            # Volume statistics
            avg_volume = data['Volume'].mean()
            current_volume = data['Volume'].iloc[-1]
            
            # Price statistics
            high_52w = data['High'].max()
            low_52w = data['Low'].min()
            
            return {
                "symbol": symbol,
                "current_price": float(current_price),
                "previous_price": float(previous_price),
                "price_change": float(price_change),
                "price_change_pct": float(price_change_pct),
                "avg_volume": int(avg_volume),
                "current_volume": int(current_volume),
                "high_52w": float(high_52w),
                "low_52w": float(low_52w),
                "timestamp": pd.Timestamp.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Error fetching market data for {symbol}: {e}")
            return {"error": str(e)}


class NewsSentimentTool(BaseTool):
    """Tool for analyzing news sentiment"""
    name: str = "News Sentiment Analyzer"
    description: str = "Analyzes news sentiment for market symbols"
    
    def _run(self, symbol: str) -> Dict[str, Any]:
        """Analyze news sentiment for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get recent news
            news = ticker.news
            if not news:
                return {"symbol": symbol, "sentiment": "neutral", "score": 0.0}
            
            # Simple sentiment analysis (in real implementation, use proper NLP)
            positive_words = ['gain', 'profit', 'growth', 'rise', 'bull', 'positive', 'upgrade', 'strong']
            negative_words = ['loss', 'decline', 'fall', 'bear', 'negative', 'downgrade', 'weak', 'concern']
            
            total_sentiment = 0
            article_count = len(news)
            
            for article in news:
                title = article.get('title', '').lower()
                summary = article.get('summary', '').lower()
                text = f"{title} {summary}"
                
                positive_count = sum(1 for word in positive_words if word in text)
                negative_count = sum(1 for word in negative_words if word in text)
                
                article_sentiment = (positive_count - negative_count) / max(len(text.split()), 1)
                total_sentiment += article_sentiment
            
            avg_sentiment = total_sentiment / article_count if article_count > 0 else 0
            
            # Classify sentiment
            if avg_sentiment > 0.1:
                sentiment = "positive"
            elif avg_sentiment < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            return {
                "symbol": symbol,
                "sentiment": sentiment,
                "score": float(avg_sentiment),
                "article_count": article_count,
                "news_headlines": [article.get('title', '') for article in news[:5]],
                "timestamp": pd.Timestamp.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Error analyzing news sentiment for {symbol}: {e}")
            return {"symbol": symbol, "sentiment": "neutral", "score": 0.0, "error": str(e)}


class EconomicDataTool(BaseTool):
    """Tool for fetching economic indicators"""
    name: str = "Economic Data Fetcher"
    description: str = "Fetches economic indicators and market indices"
    
    def _run(self, indicator: str = "^GSPC") -> Dict[str, Any]:
        """Fetch economic indicators"""
        try:
            ticker = yf.Ticker(indicator)
            data = ticker.history(period="1d")
            
            if data.empty:
                return {"error": f"No data available for {indicator}"}
            
            current_value = float(data['Close'].iloc[-1])
            previous_value = float(data['Close'].iloc[-2])
            change = current_value - previous_value
            change_pct = (change / previous_value) * 100
            
            return {
                "indicator": indicator,
                "current_value": current_value,
                "previous_value": previous_value,
                "change": change,
                "change_pct": change_pct,
                "timestamp": pd.Timestamp.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Error fetching economic data for {indicator}: {e}")
            return {"error": str(e)}


class MarketResearchAnalyst:
    """Market Research Analyst Agent"""
    
    def __init__(self, crew_id: str):
        self.crew_id = crew_id
        self.logger = logging.getLogger(__name__)
        self.market_cache = MarketDataCache(cache_manager)
        
        # Create tools
        self.tools = [
            MarketDataTool(),
            NewsSentimentTool(),
            EconomicDataTool()
        ]
        
        # Create agent
        self.agent = Agent(
            role="Market Research Analyst",
            goal="Conduct comprehensive market research and analysis to identify trading opportunities",
            backstory="""You are an experienced market research analyst with deep knowledge of financial markets, 
                        economic indicators, and market sentiment analysis. You excel at identifying trends, 
                        analyzing fundamental data, and providing actionable insights for trading decisions.""",
            tools=self.tools,
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True,
            cache=True,
            llm_config={
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        )
    
    async def analyze_market_conditions(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Analyze overall market conditions"""
        if not symbols:
            symbols = ["^GSPC", "^DJI", "^IXIC"]  # Major indices
        
        results = {}
        
        for symbol in symbols:
            try:
                # Get market data with caching
                market_data = await self.market_cache.get_price_data(symbol, "1d")
                if not market_data:
                    market_data = self.tools[0]._run(symbol)
                    await self.market_cache.cache_price_data(symbol, "1d", market_data)
                
                if "error" not in market_data:
                    results[symbol] = market_data
                    
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")
                results[symbol] = {"error": str(e)}
        
        # Store analysis in memory
        await memory_manager.store_crew_memory(
            self.crew_id, 
            "market_analysis", 
            {
                "symbols_analyzed": symbols,
                "analysis": results,
                "timestamp": pd.Timestamp.now().isoformat()
            }
        )
        
        return results
    
    async def research_company(self, symbol: str) -> Dict[str, Any]:
        """Research a specific company"""
        try:
            # Get cached company data first
            cached_data = await self.market_cache.get_price_data(symbol, "1d")
            
            if not cached_data:
                market_data = self.tools[0]._run(symbol, "2y")
                await self.market_cache.cache_price_data(symbol, "1d", market_data)
            else:
                market_data = cached_data
            
            # Get sentiment analysis
            sentiment_data = await self.market_cache.get_sentiment_data(symbol)
            if not sentiment_data:
                sentiment_data = self.tools[1]._run(symbol)
                await self.market_cache.cache_sentiment_data(symbol, sentiment_data)
            
            # Combine analysis
            analysis = {
                "symbol": symbol,
                "market_data": market_data,
                "sentiment": sentiment_data,
                "timestamp": pd.Timestamp.now().isoformat()
            }
            
            # Store in memory
            await memory_manager.store_agent_memory(
                self.crew_id, 
                "market_research_analyst", 
                f"company_research_{symbol}", 
                analysis
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error researching company {symbol}: {e}")
            return {"error": str(e)}
    
    async def analyze_sector_performance(self) -> Dict[str, Any]:
        """Analyze sector performance"""
        sector_symbols = {
            "Technology": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
            "Healthcare": ["JNJ", "PFE", "UNH", "ABBV", "MRK"],
            "Financial": ["JPM", "BAC", "WFC", "GS", "MS"],
            "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"]
        }
        
        sector_analysis = {}
        
        for sector, symbols in sector_symbols.items():
            sector_data = {}
            
            for symbol in symbols:
                try:
                    data = await self.market_cache.get_price_data(symbol, "1d")
                    if not data:
                        data = self.tools[0]._run(symbol, "1mo")
                        await self.market_cache.cache_price_data(symbol, "1d", data)
                    
                    if "error" not in data:
                        sector_data[symbol] = data
                        
                except Exception as e:
                    self.logger.error(f"Error analyzing {symbol}: {e}")
            
            if sector_data:
                # Calculate sector metrics
                avg_change = sum(d.get("price_change_pct", 0) for d in sector_data.values()) / len(sector_data)
                total_volume = sum(d.get("current_volume", 0) for d in sector_data.values())
                
                sector_analysis[sector] = {
                    "symbols": list(sector_data.keys()),
                    "average_change_pct": avg_change,
                    "total_volume": total_volume,
                    "performance": "positive" if avg_change > 0 else "negative" if avg_change < 0 else "neutral"
                }
        
        # Store in memory
        await memory_manager.store_crew_memory(
            self.crew_id, 
            "sector_analysis", 
            {
                "sectors": sector_analysis,
                "timestamp": pd.Timestamp.now().isoformat()
            }
        )
        
        return sector_analysis
    
    async def identify_opportunities(self, criteria: Dict[str, Any] = None) -> Dict[str, Any]:
        """Identify trading opportunities based on analysis"""
        # Default criteria
        if not criteria:
            criteria = {
                "min_volume": 1000000,
                "price_change_threshold": 2.0,
                "sentiment_threshold": 0.5
            }
        
        # Get recent market analysis
        market_analysis = await memory_manager.get_crew_memory(self.crew_id, "market_analysis")
        sector_analysis = await memory_manager.get_crew_memory(self.crew_id, "sector_analysis")
        
        opportunities = []
        
        # Analyze market data for opportunities
        if market_analysis and "analysis" in market_analysis:
            for symbol, data in market_analysis["analysis"].items():
                if "error" not in data:
                    # Check volume criteria
                    if data.get("current_volume", 0) >= criteria["min_volume"]:
                        # Check price change criteria
                        change_pct = abs(data.get("price_change_pct", 0))
                        if change_pct >= criteria["price_change_threshold"]:
                            opportunities.append({
                                "symbol": symbol,
                                "type": "high_volume_price_move",
                                "change_pct": data.get("price_change_pct"),
                                "volume": data.get("current_volume"),
                                "reason": f"Significant price movement ({change_pct:.2f}%) with high volume"
                            })
        
        # Analyze sector performance
        if sector_analysis and "sectors" in sector_analysis:
            for sector, data in sector_analysis["sectors"].items():
                if abs(data.get("average_change_pct", 0)) >= criteria["price_change_threshold"]:
                    opportunities.append({
                        "sector": sector,
                        "type": "sector_rotation",
                        "change_pct": data.get("average_change_pct"),
                        "reason": f"Sector showing strong movement ({data.get('average_change_pct', 0):.2f}%)"
                    })
        
        # Store opportunities in memory
        await memory_manager.store_crew_memory(
            self.crew_id, 
            "trading_opportunities", 
            {
                "opportunities": opportunities,
                "criteria": criteria,
                "timestamp": pd.Timestamp.now().isoformat()
            }
        )
        
        return {"opportunities": opportunities, "criteria": criteria}
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance"""
        return self.agent


# Example usage function
async def create_market_research_analyst(crew_id: str) -> MarketResearchAnalyst:
    """Factory function to create Market Research Analyst"""
    analyst = MarketResearchAnalyst(crew_id)
    
    # Initialize memory connections
    await memory_manager.connect()
    
    return analyst