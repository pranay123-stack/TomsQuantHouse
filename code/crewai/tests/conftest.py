"""
Pytest configuration and shared fixtures for CrewAI Trading System Tests
"""
import asyncio
import pytest
import pytest_asyncio
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional, Generator
import tempfile
import os
import redis.asyncio as redis
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configure pytest
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Redis Mock Fixtures
@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=False)
    client.expire = AsyncMock(return_value=True)
    client.hset = AsyncMock(return_value=1)
    client.hget = AsyncMock(return_value=None)
    client.hgetall = AsyncMock(return_value={})
    client.lpush = AsyncMock(return_value=1)
    client.lrange = AsyncMock(return_value=[])
    client.sadd = AsyncMock(return_value=1)
    client.smembers = AsyncMock(return_value=set())
    client.close = AsyncMock()
    
    # For async context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    
    return client


@pytest.fixture
def mock_redis_connection():
    """Mock Redis connection"""
    return AsyncMock()


# Market Data Fixtures
@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
    
    data = pd.DataFrame({
        'Open': np.random.uniform(100, 110, len(dates)),
        'High': np.random.uniform(110, 120, len(dates)),
        'Low': np.random.uniform(90, 100, len(dates)),
        'Close': np.random.uniform(95, 115, len(dates)),
        'Volume': np.random.randint(1000000, 5000000, len(dates))
    }, index=dates)
    
    return data


@pytest.fixture
def mock_yfinance():
    """Mock yfinance module"""
    with patch('yfinance.download') as mock_download:
        mock_download.return_value = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0],
            'High': [105.0, 106.0, 107.0],
            'Low': [95.0, 96.0, 97.0],
            'Close': [104.0, 105.0, 106.0],
            'Volume': [1000000, 1200000, 1100000]
        }, index=pd.date_range('2024-01-01', periods=3))
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {
                'shortName': 'Test Company',
                'sector': 'Technology',
                'industry': 'Software',
                'marketCap': 1000000000,
                'beta': 1.2,
                'fiftyTwoWeekHigh': 110.0,
                'fiftyTwoWeekLow': 90.0,
                'forwardPE': 25.0,
                'trailingPE': 24.0,
                'priceToBook': 3.5
            }
            mock_ticker.return_value.financials = pd.DataFrame()
            mock_ticker.return_value.balance_sheet = pd.DataFrame()
            mock_ticker.return_value.cashflow = pd.DataFrame()
            
            yield mock_download


@pytest.fixture
def sample_news_data():
    """Sample news data for testing"""
    return [
        {
            'title': 'Test Company Reports Strong Q4 Earnings',
            'summary': 'Test Company exceeded earnings expectations for Q4',
            'sentiment': 'positive',
            'relevance': 0.85,
            'timestamp': datetime.now().isoformat()
        },
        {
            'title': 'Market Uncertainty Affects Tech Stocks',
            'summary': 'General market uncertainty impacts technology sector',
            'sentiment': 'negative',
            'relevance': 0.72,
            'timestamp': datetime.now().isoformat()
        }
    ]


# ML Model Fixtures
@pytest.fixture
def mock_sklearn_models():
    """Mock sklearn models for testing"""
    mock_model = Mock()
    mock_model.predict = Mock(return_value=np.array([105.0, 106.0, 107.0]))
    mock_model.predict_proba = Mock(return_value=np.array([[0.3, 0.7], [0.2, 0.8], [0.4, 0.6]]))
    mock_model.score = Mock(return_value=0.85)
    mock_model.feature_importances_ = np.array([0.2, 0.3, 0.1, 0.4])
    mock_model.coef_ = np.array([0.5, -0.2, 0.8])
    mock_model.intercept_ = 0.1
    
    # Mock preprocessing objects
    mock_scaler = Mock()
    mock_scaler.transform = Mock(return_value=np.array([[1.0, 2.0, 3.0]]))
    mock_scaler.inverse_transform = Mock(return_value=np.array([[105.0]]))
    
    mock_pca = Mock()
    mock_pca.transform = Mock(return_value=np.array([[1.0, 2.0]]))
    mock_pca.explained_variance_ratio_ = np.array([0.5, 0.3])
    
    return {'model': mock_model, 'scaler': mock_scaler, 'pca': mock_pca}


@pytest.fixture
def sample_prediction_data():
    """Sample prediction data for testing"""
    return {
        'current_price': 105.0,
        'predicted_prices': [106.0, 107.0, 108.0],
        'confidence': 0.85,
        'feature_importance': {
            'volume': 0.25,
            'rsi': 0.30,
            'macd': 0.20,
            'bollinger_position': 0.25
        },
        'model_metrics': {
            'accuracy': 0.87,
            'precision': 0.85,
            'recall': 0.83,
            'f1_score': 0.84
        }
    }


# Trading Data Fixtures
@pytest.fixture
def sample_trade_data():
    """Sample trade data for testing"""
    return {
        'symbol': 'AAPL',
        'side': 'buy',
        'quantity': 100,
        'order_type': 'limit',
        'price': 105.50,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing"""
    return {
        'total_value': 100000.0,
        'positions': {
            'AAPL': {
                'quantity': 100,
                'avg_price': 100.0,
                'current_price': 105.0,
                'unrealized_pnl': 500.0,
                'weight': 10.5
            },
            'MSFT': {
                'quantity': 50,
                'avg_price': 300.0,
                'current_price': 310.0,
                'unrealized_pnl': 500.0,
                'weight': 15.5
            }
        },
        'cash': 85000.0,
        'leverage': 1.2,
        'risk_metrics': {
            'var': 0.05,
            'sharpe_ratio': 1.2,
            'max_drawdown': 0.15
        }
    }


# Configuration Fixtures
@pytest.fixture
def temp_config_dir():
    """Temporary directory for configuration files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test .env file
        env_content = """
# Test Environment Variables
OPENAI_API_KEY=test_key
ANTHROPIC_API_KEY=test_key
ALPHA_VANTAGE_API_KEY=test_key
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
API_HOST=localhost
API_PORT=8000
API_SECRET_KEY=test_secret_key
DEBUG=true
ENVIRONMENT=testing
        """
        
        with open(os.path.join(temp_dir, '.env'), 'w') as f:
            f.write(env_content.strip())
            
        # Create test config file
        config_content = json.dumps({
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'password': None
            },
            'api': {
                'host': 'localhost',
                'port': 8000,
                'secret_key': 'test_secret_key'
            },
            'trading': {
                'max_position_size': 0.1,
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.15,
                'risk_free_rate': 0.02
            },
            'approval': {
                'high_risk_threshold': 0.8,
                'medium_risk_threshold': 0.5,
                'high_value_threshold': 10000.0
            }
        }, indent=2)
        
        with open(os.path.join(temp_dir, 'config.json'), 'w') as f:
            f.write(config_content)
        
        yield temp_dir


# FastAPI Test Client Fixture
@pytest.fixture
def test_client():
    """Test client for FastAPI application"""
    from fastapi.testclient import TestClient
    return TestClient


# Approval Workflow Fixtures
@pytest.fixture
def sample_approval_request():
    """Sample approval request for testing"""
    return {
        'approval_id': 'appr_12345',
        'request_id': 'req_67890',
        'type': 'trade_execution',
        'priority': 'high',
        'requester': 'execution_trader',
        'details': {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 1000,
            'estimated_value': 105000.0,
            'risk_score': 0.85,
            'reason': 'High confidence ML signal with strong technical setup'
        },
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }


# CrewAI Fixtures
@pytest.fixture
def mock_crewai():
    """Mock CrewAI components"""
    with patch('crewai.Agent') as mock_agent_class:
        mock_agent = Mock()
        mock_agent.name = "Mock Agent"
        mock_agent.role = "Mock Role"
        mock_agent.tools = []
        mock_agent.run = AsyncMock()
        mock_agent_class.return_value = mock_agent
        
        with patch('crewai.Task') as mock_task_class:
            mock_task = Mock()
            mock_task.description = "Mock Task"
            mock_task.expected_output = "Mock Output"
            mock_task.agent = mock_agent
            mock_task_class.return_value = mock_task
            
            with patch('crewai.Crew') as mock_crew_class:
                mock_crew = Mock()
                mock_crew.kickoff = AsyncMock(return_value="Mock Result")
                mock_crew_class.return_value = mock_crew
                
                yield {
                    'agent_class': mock_agent_class,
                    'task_class': mock_task_class,
                    'crew_class': mock_crew_class,
                    'agent': mock_agent,
                    'task': mock_task,
                    'crew': mock_crew
                }


# Database Fixtures
@pytest.fixture
def mock_database():
    """Mock database operations"""
    db_mock = Mock()
    db_mock.save_trade = AsyncMock(return_value=True)
    db_mock.get_trade = AsyncMock(return_value=sample_trade_data())
    db_mock.save_prediction = AsyncMock(return_value=True)
    db_mock.get_prediction = AsyncMock(return_value=sample_prediction_data())
    db_mock.save_risk_metric = AsyncMock(return_value=True)
    db_mock.get_risk_metric = AsyncMock(return_value={})
    
    return db_mock


# Async Test Helper Fixtures
@pytest.fixture
def async_timeout():
    """Timeout helper for async tests"""
    async def _timeout(seconds=10):
        await asyncio.wait_for(asyncio.sleep(0.01), timeout=seconds)
    return _timeout


@pytest.fixture
def mock_async_function():
    """Mock async function for testing"""
    async def _async_func(*args, **kwargs):
        await asyncio.sleep(0.01)  # Simulate async operation
        return {'status': 'success', 'args': args, 'kwargs': kwargs}
    return _async_func


# Performance Testing Fixtures
@pytest.fixture
def performance_monitor():
    """Performance monitoring for tests"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.time()
            
        def stop(self):
            self.end_time = time.time()
            return self.end_time - self.start_time
            
        def elapsed_time(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return PerformanceMonitor()


# Error Simulation Fixtures
@pytest.fixture
def error_scenarios():
    """Common error scenarios for testing"""
    return {
        'redis_connection_error': ConnectionError("Redis connection failed"),
        'api_rate_limit_error': Exception("API rate limit exceeded"),
        'insufficient_funds_error': Exception("Insufficient funds for trade"),
        'invalid_symbol_error': Exception("Invalid symbol provided"),
        'model_prediction_error': Exception("Model prediction failed"),
        'network_timeout_error': Exception("Network request timeout"),
        'json_parse_error': Exception("Failed to parse JSON response"),
        'authentication_error': Exception("Authentication failed")
    }


# Test Data Generators
@pytest.fixture
def generate_test_symbols():
    """Generate test stock symbols"""
    return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']


@pytest.fixture
def generate_test_dates():
    """Generate test date ranges"""
    return {
        'yesterday': datetime.now() - timedelta(days=1),
        'today': datetime.now(),
        'tomorrow': datetime.now() + timedelta(days=1),
        'last_week': datetime.now() - timedelta(days=7),
        'next_week': datetime.now() + timedelta(days=7)
    }


# Logging Fixtures
@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


# Cache Test Fixtures
@pytest.fixture
def cache_test_data():
    """Test data for cache testing"""
    return {
        'market_data': sample_market_data(),
        'predictions': sample_prediction_data(),
        'risk_metrics': {
            'var': 0.05,
            'beta': 1.2,
            'sharpe_ratio': 1.5
        },
        'execution_data': {
            'slippage': 0.02,
            'market_impact': 0.05,
            'liquidity_score': 0.8
        }
    }


# Cleanup Fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatically cleanup after each test"""
    yield
    # Add any cleanup logic here
    # This could include clearing caches, closing connections, etc.
    pass