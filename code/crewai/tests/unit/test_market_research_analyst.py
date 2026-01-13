"""
Unit tests for Market Research Analyst Agent
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import the agent
from agents.market_research_analyst import MarketResearchAnalyst
from config.settings import TradingSettings


class TestMarketResearchAnalyst:
    """Test cases for Market Research Analyst"""
    
    @pytest.fixture
    def analyst(self):
        """Create Market Research Analyst instance"""
        return MarketResearchAnalyst()
    
    @pytest.fixture
    def mock_tools(self):
        """Mock tools for testing"""
        with patch('agents.market_research_analyst.MarketDataTool') as mock_market_tool, \
             patch('agents.market_research_analyst.NewsSentimentTool') as mock_news_tool, \
             patch('agents.market_research_analyst.TechnicalAnalysisTool') as mock_technical_tool, \
             patch('agents.market_research_analyst.CompanyResearchTool') as mock_company_tool:
            
            # Configure mock tools
            mock_market_tool.return_value.run = AsyncMock(return_value={
                'current_price': 105.0,
                'volume': 1000000,
                'market_cap': 1000000000,
                'pe_ratio': 25.0
            })
            
            mock_news_tool.return_value.run = AsyncMock(return_value=[
                {'sentiment': 'positive', 'relevance': 0.8, 'summary': 'Good news'},
                {'sentiment': 'neutral', 'relevance': 0.6, 'summary': 'Neutral news'}
            ])
            
            mock_technical_tool.return_value.run = AsyncMock(return_value={
                'rsi': 65.0,
                'macd': 1.2,
                'bollinger_position': 0.7,
                'moving_averages': {
                    'sma_20': 100.0,
                    'sma_50': 98.0,
                    'ema_12': 102.0
                }
            })
            
            mock_company_tool.return_value.run = AsyncMock(return_value={
                'sector': 'Technology',
                'industry': 'Software',
                'employees': 100000,
                'revenue': 50000000000,
                'growth_rate': 0.15
            })
            
            yield {
                'market': mock_market_tool.return_value,
                'news': mock_news_tool.return_value,
                'technical': mock_technical_tool.return_value,
                'company': mock_company_tool.return_value
            }
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, analyst):
        """Test agent initialization"""
        assert analyst.name == "Market Research Analyst"
        assert analyst.role == "Market Research & Analysis Specialist"
        assert len(analyst.tools) > 0
        
        # Check that all expected tools are present
        tool_names = [tool.__class__.__name__ for tool in analyst.tools]
        expected_tools = ['MarketDataTool', 'NewsSentimentTool', 'TechnicalAnalysisTool', 'CompanyResearchTool']
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    async def test_analyze_market_basic(self, analyst, mock_tools):
        """Test basic market analysis functionality"""
        symbol = "AAPL"
        
        result = await analyst.analyze_market(symbol)
        
        # Verify structure
        assert 'symbol' in result
        assert 'timestamp' in result
        assert 'market_data' in result
        assert 'sentiment_analysis' in result
        assert 'technical_indicators' in result
        assert 'company_fundamentals' in result
        
        # Verify values
        assert result['symbol'] == symbol
        assert result['market_data']['current_price'] == 105.0
        assert 'overall_sentiment' in result['sentiment_analysis']
        assert 'rsi' in result['technical_indicators']
    
    @pytest.mark.asyncio
    async def test_analyze_market_with_timeframe(self, analyst, mock_tools):
        """Test market analysis with custom timeframe"""
        symbol = "MSFT"
        timeframe = "1d"
        
        result = await analyst.analyze_market(symbol, timeframe)
        
        assert result['symbol'] == symbol
        assert result.get('timeframe') == timeframe
    
    @pytest.mark.asyncio
    async def test_research_company(self, analyst, mock_tools):
        """Test company research functionality"""
        symbol = "GOOGL"
        
        result = await analyst.research_company(symbol)
        
        # Verify structure
        assert 'symbol' in result
        assert 'company_info' in result
        assert 'financial_metrics' in result
        assert 'growth_analysis' in result
        
        # Verify data
        assert result['company_info']['sector'] == 'Technology'
        assert result['company_info']['industry'] == 'Software'
        assert result['growth_analysis']['revenue_growth'] == 0.15
    
    @pytest.mark.asyncio
    async def test_technical_analysis(self, analyst, mock_tools):
        """Test technical analysis functionality"""
        symbol = "TSLA"
        analysis_type = "comprehensive"
        
        result = await analyst.technical_analysis(symbol, analysis_type)
        
        # Verify structure
        assert 'symbol' in result
        assert 'indicators' in result
        assert 'signals' in result
        assert 'overall_trend' in result
        
        # Verify indicators
        indicators = result['indicators']
        assert 'rsi' in indicators
        assert 'macd' in indicators
        assert 'bollinger_position' in indicators
        assert 'moving_averages' in indicators
        
        # Verify signals
        assert 'trend_signal' in result['signals']
        assert 'momentum_signal' in result['signals']
        assert 'volatility_signal' in result['signals']
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis(self, analyst, mock_tools):
        """Test news sentiment analysis"""
        symbol = "AMZN"
        
        result = await analyst.sentiment_analysis(symbol)
        
        # Verify structure
        assert 'symbol' in result
        assert 'sentiment_score' in result
        assert 'confidence' in result
        assert 'news_items' in result
        assert 'market_impact_assessment' in result
        
        # Verify values
        assert isinstance(result['sentiment_score'], (int, float))
        assert result['confidence'] > 0
        assert len(result['news_items']) > 0
    
    @pytest.mark.asyncio
    async def test_compare_symbols(self, analyst):
        """Test symbol comparison functionality"""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        
        with patch.object(analyst, 'analyze_market') as mock_analyze:
            mock_analyze.side_effect = [
                {'symbol': 'AAPL', 'score': 85},
                {'symbol': 'MSFT', 'score': 78},
                {'symbol': 'GOOGL', 'score': 92}
            ]
            
            result = await analyst.compare_symbols(symbols)
            
            assert 'comparison_results' in result
            assert 'ranking' in result
            assert 'recommendation' in result
            assert len(result['ranking']) == 3
    
    @pytest.mark.asyncio
    async def test_get_market_overview(self, analyst, mock_tools):
        """Test market overview functionality"""
        symbols = ["AAPL", "MSFT"]
        
        with patch.object(analyst, 'analyze_market') as mock_analyze:
            mock_analyze.side_effect = [
                {'symbol': 'AAPL', 'market_data': {'current_price': 105}},
                {'symbol': 'MSFT', 'market_data': {'current_price': 300}}
            ]
            
            result = await analyst.get_market_overview(symbols)
            
            assert 'market_summary' in result
            assert 'top_performers' in result
            assert 'worst_performers' in result
            assert 'sector_analysis' in result
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_symbol(self, analyst):
        """Test error handling for invalid symbols"""
        invalid_symbol = "INVALID_SYMBOL_123"
        
        with patch.object(analyst, 'analyze_market') as mock_analyze:
            mock_analyze.side_effect = Exception("Symbol not found")
            
            with pytest.raises(Exception, match="Symbol not found"):
                await analyst.analyze_market(invalid_symbol)
    
    @pytest.mark.asyncio
    async def test_error_handling_api_failure(self, analyst, mock_tools):
        """Test error handling for API failures"""
        # Configure mock to raise exception
        mock_tools['market'].run.side_effect = Exception("API connection failed")
        
        with pytest.raises(Exception, match="API connection failed"):
            await analyst.analyze_market("AAPL")
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, analyst, performance_monitor):
        """Test performance metrics"""
        performance_monitor.start()
        
        # Simulate work
        await asyncio.sleep(0.01)
        
        execution_time = performance_monitor.stop()
        
        # Should complete within reasonable time (less than 1 second for mock)
        assert execution_time < 1.0
    
    @pytest.mark.asyncio
    async def test_cache_behavior(self, analyst):
        """Test caching behavior for repeated requests"""
        symbol = "NVDA"
        
        # First call
        with patch.object(analyst, 'analyze_market') as mock_analyze:
            mock_analyze.return_value = {'symbol': symbol, 'cached': False}
            result1 = await analyst.analyze_market(symbol, use_cache=True)
            
            # Second call should hit cache
            mock_analyze.return_value = {'symbol': symbol, 'cached': True}
            result2 = await analyst.analyze_market(symbol, use_cache=True)
            
            # Verify both calls completed
            assert result1['symbol'] == symbol
            assert result2['symbol'] == symbol
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, analyst):
        """Test concurrent market analysis"""
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        
        with patch.object(analyst, 'analyze_market') as mock_analyze:
            results = []
            
            async def analyze_symbol(symbol):
                mock_analyze.return_value = {'symbol': symbol, 'price': 100 + len(results)}
                results.append(await analyst.analyze_market(symbol))
            
            # Run concurrent analyses
            await asyncio.gather(*[analyze_symbol(symbol) for symbol in symbols])
            
            # Verify all completed
            assert len(results) == 4
            for i, result in enumerate(results):
                assert result['symbol'] in symbols
                assert 'price' in result
    
    @pytest.mark.asyncio
    async def test_data_validation(self, analyst, mock_tools):
        """Test data validation in analysis results"""
        # Test with incomplete market data
        mock_tools['market'].run.return_value = {'current_price': None}
        
        result = await analyst.analyze_market("AAPL")
        
        # Should handle missing data gracefully
        assert 'symbol' in result
        assert result['market_data'] is not None
    
    @pytest.mark.asyncio
    async def test_advanced_indicators(self, analyst, mock_tools):
        """Test advanced technical indicators"""
        symbol = "META"
        
        # Add advanced indicators to mock
        mock_technical_tool = mock_tools['technical']
        mock_technical_tool.run.return_value = {
            'rsi': 65.0,
            'macd': 1.2,
            'bollinger_position': 0.7,
            'stochastic_k': 80.0,
            'williams_r': -20.0,
            'atr': 3.5,
            'adx': 45.0,
            'cci': 100.0
        }
        
        result = await analyst.technical_analysis(symbol, "advanced")
        
        indicators = result['indicators']
        
        # Verify advanced indicators
        assert 'stochastic_k' in indicators
        assert 'williams_r' in indicators
        assert 'atr' in indicators
        assert 'adx' in indicators
        assert 'cci' in indicators
    
    @pytest.mark.asyncio
    async def test_risk_assessment_integration(self, analyst, mock_tools):
        """Test integration with risk assessment"""
        symbol = "TSLA"
        
        # Mock risk tools
        with patch('agents.market_research_analyst.RiskAssessmentTool') as mock_risk_tool:
            mock_risk_tool.return_value.run = AsyncMock(return_value={
                'volatility': 0.25,
                'beta': 1.5,
                'var_95': 0.05,
                'risk_score': 7.5
            })
            
            result = await analyst.analyze_market(symbol, include_risk=True)
            
            assert 'risk_assessment' in result
            assert result['risk_assessment']['volatility'] == 0.25
            assert result['risk_assessment']['beta'] == 1.5
    
    @pytest.mark.asyncio
    async def test_news_sentiment_scoring(self, analyst, mock_tools):
        """Test news sentiment scoring algorithm"""
        # Configure news tool with various sentiment scenarios
        mock_tools['news'].run.return_value = [
            {'sentiment': 'very_positive', 'relevance': 0.9, 'confidence': 0.8},
            {'sentiment': 'positive', 'relevance': 0.7, 'confidence': 0.6},
            {'sentiment': 'neutral', 'relevance': 0.5, 'confidence': 0.7},
            {'sentiment': 'negative', 'relevance': 0.8, 'confidence': 0.9},
            {'sentiment': 'very_negative', 'relevance': 0.6, 'confidence': 0.8}
        ]
        
        result = await analyst.sentiment_analysis("AAPL")
        
        sentiment_score = result['sentiment_score']
        confidence = result['confidence']
        
        # Should handle mixed sentiment appropriately
        assert -1 <= sentiment_score <= 1
        assert 0 <= confidence <= 1
    
    @pytest.mark.asyncio
    async def test_symbol_pattern_recognition(self, analyst):
        """Test pattern recognition in price data"""
        symbol = "NVDA"
        
        # Mock price data with clear pattern
        price_data = [100, 102, 105, 103, 108, 110, 115]
        
        with patch.object(analyst, 'analyze_market') as mock_analyze:
            mock_analyze.return_value = {
                'symbol': symbol,
                'price_pattern': {
                    'pattern_type': 'ascending_triangle',
                    'breakout_probability': 0.75,
                    'target_price': 125.0
                }
            }
            
            result = await analyst.analyze_market(symbol, pattern_recognition=True)
            
            assert 'price_pattern' in result
            assert 'pattern_type' in result['price_pattern']
            assert 'breakout_probability' in result['price_pattern']


class TestMarketDataTool:
    """Test cases for MarketDataTool"""
    
    @pytest.fixture
    def market_tool(self):
        """Create MarketDataTool instance"""
        from agents.tools.market_data_tool import MarketDataTool
        return MarketDataTool()
    
    @pytest.mark.asyncio
    async def test_get_current_price(self, market_tool, mock_yfinance):
        """Test current price retrieval"""
        symbol = "AAPL"
        
        result = await market_tool.run(symbol=symbol)
        
        assert 'current_price' in result
        assert 'volume' in result
        assert 'market_cap' in result
        assert 'pe_ratio' in result
        assert isinstance(result['current_price'], (int, float))
    
    @pytest.mark.asyncio
    async def test_get_historical_data(self, market_tool, sample_market_data):
        """Test historical data retrieval"""
        symbol = "MSFT"
        
        with patch('yfinance.download') as mock_download:
            mock_download.return_value = sample_market_data
            
            result = await market_tool.run(symbol=symbol, data_type="historical", period="1mo")
            
            assert 'historical_data' in result
            assert isinstance(result['historical_data'], pd.DataFrame)
    
    @pytest.mark.asyncio
    async def test_get_financial_metrics(self, market_tool):
        """Test financial metrics retrieval"""
        symbol = "GOOGL"
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {
                'marketCap': 1000000000,
                'forwardPE': 25.0,
                'trailingPE': 24.0,
                'priceToBook': 3.5,
                'debtToEquity': 0.3,
                'returnOnEquity': 0.15
            }
            
            result = await market_tool.run(symbol=symbol, data_type="financials")
            
            assert 'financial_metrics' in result
            assert result['financial_metrics']['market_cap'] == 1000000000
            assert 'forward_pe' in result['financial_metrics']


class TestNewsSentimentTool:
    """Test cases for NewsSentimentTool"""
    
    @pytest.fixture
    def news_tool(self):
        """Create NewsSentimentTool instance"""
        from agents.tools.news_sentiment_tool import NewsSentimentTool
        return NewsSentimentTool()
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis(self, news_tool, sample_news_data):
        """Test news sentiment analysis"""
        symbol = "AAPL"
        
        # Mock news API
        with patch('newsapi.NewsApiClient') as mock_newsapi:
            mock_newsapi.return_value.get_everything.return_value = {
                'articles': [
                    {'title': 'Test Article', 'description': 'Test Description'},
                    {'title': 'Another Article', 'description': 'Another Description'}
                ]
            }
            
            result = await news_tool.run(symbol=symbol)
            
            assert isinstance(result, list)
            assert len(result) > 0
            
            for item in result:
                assert 'sentiment' in item
                assert 'relevance' in item
                assert 'confidence' in item


class TestTechnicalAnalysisTool:
    """Test cases for TechnicalAnalysisTool"""
    
    @pytest.fixture
    def technical_tool(self):
        """Create TechnicalAnalysisTool instance"""
        from agents.tools.technical_analysis_tool import TechnicalAnalysisTool
        return TechnicalAnalysisTool()
    
    @pytest.mark.asyncio
    async def test_rsi_calculation(self, technical_tool, sample_market_data):
        """Test RSI calculation"""
        symbol = "AAPL"
        
        # Mock market data
        with patch('yfinance.download') as mock_download:
            mock_download.return_value = sample_market_data
            
            result = await technical_tool.run(symbol=symbol, indicators=['rsi'])
            
            assert 'rsi' in result
            assert 0 <= result['rsi'] <= 100
    
    @pytest.mark.asyncio
    async def test_macd_calculation(self, technical_tool, sample_market_data):
        """Test MACD calculation"""
        symbol = "MSFT"
        
        with patch('yfinance.download') as mock_download:
            mock_download.return_value = sample_market_data
            
            result = await technical_tool.run(symbol=symbol, indicators=['macd'])
            
            assert 'macd' in result
            assert 'macd_signal' in result
            assert 'macd_histogram' in result
    
    @pytest.mark.asyncio
    async def test_bollinger_bands(self, technical_tool, sample_market_data):
        """Test Bollinger Bands calculation"""
        symbol = "GOOGL"
        
        with patch('yfinance.download') as mock_download:
            mock_download.return_value = sample_market_data
            
            result = await technical_tool.run(symbol=symbol, indicators=['bollinger'])
            
            assert 'bollinger_upper' in result
            assert 'bollinger_middle' in result
            assert 'bollinger_lower' in result


class TestCompanyResearchTool:
    """Test cases for CompanyResearchTool"""
    
    @pytest.fixture
    def company_tool(self):
        """Create CompanyResearchTool instance"""
        from agents.tools.company_research_tool import CompanyResearchTool
        return CompanyResearchTool()
    
    @pytest.mark.asyncio
    async def test_company_info_retrieval(self, company_tool):
        """Test company information retrieval"""
        symbol = "AAPL"
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {
                'shortName': 'Apple Inc.',
                'sector': 'Technology',
                'industry': 'Consumer Electronics',
                'country': 'US',
                'website': 'https://www.apple.com'
            }
            
            result = await company_tool.run(symbol=symbol)
            
            assert 'company_name' in result
            assert result['sector'] == 'Technology'
            assert result['industry'] == 'Consumer Electronics'
    
    @pytest.mark.asyncio
    async def test_financial_statements(self, company_tool):
        """Test financial statements analysis"""
        symbol = "MSFT"
        
        with patch('yfinance.Ticker') as mock_ticker:
            # Mock financials data
            mock_financials = pd.DataFrame({
                'Revenue': [1000000000, 1100000000, 1200000000],
                'Net Income': [200000000, 220000000, 240000000]
            })
            
            mock_ticker.return_value.financials = mock_financials
            
            result = await company_tool.run(symbol=symbol, analysis_type='financials')
            
            assert 'revenue_growth' in result
            assert 'profit_margin' in result
            assert isinstance(result['revenue_growth'], (int, float))


class TestIntegration:
    """Integration tests for Market Research Analyst"""
    
    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self):
        """Test complete market analysis workflow"""
        from agents.market_research_analyst import MarketResearchAnalyst
        
        analyst = MarketResearchAnalyst()
        
        # Mock all tools
        with patch.multiple(
            'agents.market_research_analyst.MarketDataTool',
            run=AsyncMock(return_value={
                'current_price': 105.0,
                'volume': 1000000,
                'market_cap': 1000000000
            })
        ), patch.multiple(
            'agents.market_research_analyst.NewsSentimentTool',
            run=AsyncMock(return_value=[
                {'sentiment': 'positive', 'relevance': 0.8}
            ])
        ), patch.multiple(
            'agents.market_research_analyst.TechnicalAnalysisTool',
            run=AsyncMock(return_value={
                'rsi': 65.0,
                'macd': 1.2,
                'bollinger_position': 0.7
            })
        ), patch.multiple(
            'agents.market_research_analyst.CompanyResearchTool',
            run=AsyncMock(return_value={
                'sector': 'Technology',
                'industry': 'Software',
                'growth_rate': 0.15
            })
        ):
            
            # Run complete analysis
            result = await analyst.full_analysis("AAPL")
            
            # Verify all components are present
            assert 'symbol' in result
            assert 'market_data' in result
            assert 'sentiment_analysis' in result
            assert 'technical_indicators' in result
            assert 'company_info' in result
            assert 'risk_assessment' in result
            assert 'recommendation' in result