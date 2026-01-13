"""
Test configuration and shared fixtures for the API integration testing suite.
"""
import os
import pytest
import asyncio
import aioredis
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock
import logging
from datetime import datetime, timedelta

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
class TestConfig:
    """Configuration for test environment"""
    
    # Redis configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    
    # Letta configuration
    LETTA_BASE_URL = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
    LETTA_API_KEY = os.getenv('LETTA_API_KEY', 'test-key')
    
    # Abacus.AI configuration
    ABACUS_API_URL = os.getenv('ABACUS_API_URL', 'https://api.abacus.ai')
    ABACUS_API_KEY = os.getenv('ABACUS_API_KEY', 'test-abacus-key')
    
    # QuantConnect configuration
    QUANTCONNECT_BASE_URL = os.getenv('QUANTCONNECT_BASE_URL', 'https://www.quantconnect.com/api')
    QUANTCONNECT_API_KEY = os.getenv('QUANTCONNECT_API_KEY', 'test-qc-key')
    
    # Cache settings
    PREDICTION_CACHE_TTL = 300  # 5 minutes
    FEATURE_CACHE_TTL = 3600    # 1 hour
    MARKET_DATA_CACHE_TTL = 300 # 5 minutes
    
    # Test data settings
    TEST_SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
    TEST_START_DATE = '2023-01-01'
    TEST_END_DATE = '2023-12-31'
    
    # Performance thresholds
    MAX_CACHE_RETRIEVAL_TIME = 0.1  # 100ms
    MAX_PREDICTION_TIME = 5.0       # 5 seconds
    MAX_HEALTH_CHECK_TIME = 2.0     # 2 seconds

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Create Redis client for testing"""
    try:
        client = aioredis.from_url(TestConfig.REDIS_URL)
        await client.ping()
        logger.info("Connected to Redis successfully")
        yield client
    except Exception as e:
        logger.warning(f"Redis not available: {e}. Using mock client.")
        yield Mock()
    finally:
        try:
            await client.close()
        except:
            pass

@pytest.fixture
def mock_letta_client():
    """Mock Letta client for testing"""
    client = Mock()
    client.send_message = AsyncMock(return_value="Mock response")
    client.get_memory = AsyncMock(return_value={"conversation": []})
    client.update_memory = AsyncMock(return_value=True)
    client.create_agent = AsyncMock(return_value={"agent_id": "test-agent-123"})
    return client

@pytest.fixture
def mock_abacus_client():
    """Mock Abacus.AI client for testing"""
    client = Mock()
    client.predict = AsyncMock(return_value={
        "prediction": 0.75,
        "confidence": 0.85,
        "timestamp": datetime.utcnow().isoformat(),
        "model_version": "v1.2.3"
    })
    client.train_model = AsyncMock(return_value={"model_id": "model-123", "status": "training"})
    client.get_model_status = AsyncMock(return_value={"status": "ready", "accuracy": 0.92})
    return client

@pytest.fixture
def mock_quantconnect_client():
    """Mock QuantConnect client for testing"""
    client = Mock()
    client.get_market_data = AsyncMock(return_value={
        "AAPL": {"price": 150.25, "volume": 1000000, "timestamp": datetime.utcnow()},
        "GOOGL": {"price": 2750.80, "volume": 500000, "timestamp": datetime.utcnow()}
    })
    client.get_algorithm_results = AsyncMock(return_value={"portfolio_value": 100000, "trades": []})
    return client

@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "symbol": "AAPL",
        "timestamp": datetime.utcnow(),
        "open": 149.50,
        "high": 151.00,
        "low": 149.25,
        "close": 150.75,
        "volume": 1200000,
        "adj_close": 150.75
    }

@pytest.fixture
def sample_features():
    """Sample feature set for testing"""
    return {
        "sma_20": 148.50,
        "sma_50": 145.25,
        "rsi": 65.2,
        "macd": 2.1,
        "bollinger_position": 0.75,
        "volume_ratio": 1.2,
        "price_momentum": 0.05,
        "volatility": 0.25
    }

@pytest.fixture
def sample_prediction():
    """Sample prediction for testing"""
    return {
        "symbol": "AAPL",
        "prediction": "BUY",
        "confidence": 0.85,
        "probability": 0.82,
        "price_target": 155.00,
        "stop_loss": 147.50,
        "timestamp": datetime.utcnow(),
        "model_version": "v1.2.3",
        "features_used": ["sma_20", "rsi", "macd", "volume_ratio"]
    }

@pytest.fixture
async def clean_redis(redis_client):
    """Clean Redis database before and after tests"""
    if hasattr(redis_client, 'flushdb'):
        await redis_client.flushdb()
    yield
    if hasattr(redis_client, 'flushdb'):
        await redis_client.flushdb()

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance benchmarking tests")
    config.addinivalue_line("markers", "e2e: End-to-end pipeline tests")
    config.addinivalue_line("markers", "slow: Tests that take longer than 5 seconds")
    config.addinivalue_line("markers", "redis: Tests requiring Redis service")
    config.addinivalue_line("markers", "letta: Tests requiring Letta service")
    config.addinivalue_line("markers", "abacus: Tests requiring Abacus.AI service")
    config.addinivalue_line("markers", "quantconnect: Tests requiring QuantConnect service")
    config.addinivalue_line("markers", "live: Tests that hit real services (not mocks)")
    config.addinivalue_line("markers", "mock: Tests using mocks/fixtures")