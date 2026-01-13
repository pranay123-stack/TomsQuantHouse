"""
Integration tests for Redis-QuantConnect-Abacus.AI data flow
"""
import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from conftest import TestConfig

@pytest.mark.integration
@pytest.mark.redis
@pytest.mark.abacus
class TestDataFlowIntegration:
    """Test complete data flow between Redis, QuantConnect, and Abacus.AI"""
    
    async def test_market_data_to_redis_flow(self, redis_client, mock_quantconnect_client, clean_redis):
        """Test flow of market data from QuantConnect to Redis cache"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "AAPL"
        market_data = await mock_quantconnect_client.get_market_data(symbol)
        
        # Store market data in Redis
        cache_key = f"market_data:{symbol}:latest"
        cache_data = json.dumps({
            "data": market_data,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "quantconnect"
        })
        
        await redis_client.setex(
            cache_key, 
            TestConfig.MARKET_DATA_CACHE_TTL, 
            cache_data
        )
        
        # Retrieve and verify data
        cached_data = await redis_client.get(cache_key)
        assert cached_data is not None
        
        parsed_data = json.loads(cached_data)
        assert parsed_data["source"] == "quantconnect"
        assert parsed_data["data"]["symbol"] == symbol
        
        print(f"Market data cached successfully for {symbol}")
    
    async def test_features_to_redis_flow(self, redis_client, clean_redis):
        """Test flow of computed features to Redis cache"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "AAPL"
        features = {
            "sma_20": 148.50,
            "sma_50": 145.25,
            "rsi": 65.2,
            "macd": 2.1,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store features in Redis
        cache_key = f"features:{symbol}:latest"
        await redis_client.setex(
            cache_key,
            TestConfig.FEATURE_CACHE_TTL,
            json.dumps(features)
        )
        
        # Verify storage
        cached_features = await redis_client.get(cache_key)
        assert cached_features is not None
        
        parsed_features = json.loads(cached_features)
        assert "sma_20" in parsed_features
        assert parsed_features["sma_20"] == 148.50
        
        print(f"Features cached successfully for {symbol}")
    
    async def test_prediction_cache_flow(self, redis_client, mock_abacus_client, clean_redis):
        """Test prediction caching and retrieval"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "AAPL"
        features = {"feature1": 1.0, "feature2": 2.0}
        
        # Generate prediction
        prediction = await mock_abacus_client.predict(features)
        
        # Cache prediction
        cache_key = f"prediction:{symbol}:{hash(str(features))}"
        prediction_data = {
            "prediction": prediction,
            "features": features,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_hit": False
        }
        
        await redis_client.setex(
            cache_key,
            TestConfig.PREDICTION_CACHE_TTL,
            json.dumps(prediction_data)
        )
        
        # Retrieve cached prediction
        cached_prediction = await redis_client.get(cache_key)
        assert cached_prediction is not None
        
        cached_data = json.loads(cached_prediction)
        assert cached_data["prediction"]["prediction"] == 0.75
        
        print(f"Prediction cached and retrieved for {symbol}")
    
    async def test_cached_prediction_retrieval(self, redis_client, clean_redis):
        """Test retrieval of previously cached predictions"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "AAPL"
        features = {"feature1": 1.0, "feature2": 2.0}
        cache_key = f"prediction:{symbol}:{hash(str(features))}"
        
        # Pre-populate cache
        cached_prediction = {
            "prediction": {"prediction": 0.80, "confidence": 0.90},
            "features": features,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_hit": True
        }
        
        await redis_client.setex(
            cache_key,
            TestConfig.PREDICTION_CACHE_TTL,
            json.dumps(cached_prediction)
        )
        
        # Retrieve cached prediction
        retrieved = await redis_client.get(cache_key)
        assert retrieved is not None
        
        data = json.loads(retrieved)
        assert data["cache_hit"] is True
        assert data["prediction"]["prediction"] == 0.80
        
        print("Cached prediction retrieved successfully")
    
    async def test_multi_symbol_data_flow(self, redis_client, mock_quantconnect_client, clean_redis):
        """Test data flow for multiple symbols simultaneously"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbols = TestConfig.TEST_SYMBOLS[:3]  # Test with first 3 symbols
        cache_operations = []
        
        # Process multiple symbols
        for symbol in symbols:
            market_data = await mock_quantconnect_client.get_market_data(symbol)
            
            cache_key = f"market_data:{symbol}:latest"
            cache_data = json.dumps({
                "data": market_data,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "quantconnect"
            })
            
            start_time = time.time()
            await redis_client.setex(cache_key, TestConfig.MARKET_DATA_CACHE_TTL, cache_data)
            operation_time = time.time() - start_time
            
            cache_operations.append({
                "symbol": symbol,
                "operation_time": operation_time,
                "success": True
            })
        
        # Verify all symbols are cached
        for symbol in symbols:
            cache_key = f"market_data:{symbol}:latest"
            cached_data = await redis_client.get(cache_key)
            assert cached_data is not None
        
        # Check performance
        avg_operation_time = sum(op["operation_time"] for op in cache_operations) / len(cache_operations)
        assert avg_operation_time < TestConfig.MAX_CACHE_RETRIEVAL_TIME
        
        print(f"Multi-symbol data flow completed. Avg time: {avg_operation_time:.3f}s")
    
    async def test_cache_invalidation_flow(self, redis_client, clean_redis):
        """Test cache invalidation scenarios"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "AAPL"
        
        # Set initial data
        cache_key = f"market_data:{symbol}:latest"
        await redis_client.setex(
            cache_key,
            TestConfig.PREDICTION_CACHE_TTL,
            json.dumps({"data": "initial", "timestamp": datetime.utcnow().isoformat()})
        )
        
        # Verify initial data exists
        initial_data = await redis_client.get(cache_key)
        assert initial_data is not None
        
        # Invalidate cache
        await redis_client.delete(cache_key)
        
        # Verify data is removed
        invalid_data = await redis_client.get(cache_key)
        assert invalid_data is None
        
        print("Cache invalidation working correctly")
    
    @pytest.mark.slow
    async def test_cache_expiration_flow(self, redis_client, clean_redis):
        """Test cache expiration behavior"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "AAPL"
        cache_key = f"test_expiry:{symbol}"
        
        # Set data with 1 second expiry
        await redis_client.setex(cache_key, 1, "test_data")
        
        # Verify data exists immediately
        data_immediate = await redis_client.get(cache_key)
        assert data_immediate is not None
        
        # Wait for expiry
        await asyncio.sleep(1.1)
        
        # Verify data has expired
        data_after_expiry = await redis_client.get(cache_key)
        assert data_after_expiry is None
        
        print("Cache expiration working correctly")

@pytest.mark.integration
@pytest.mark.performance
class TestDataFlowPerformance:
    """Performance tests for data flow operations"""
    
    async def test_cache_write_performance(self, redis_client, clean_redis):
        """Test performance of cache write operations"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        write_times = []
        num_operations = 100
        
        for i in range(num_operations):
            symbol = f"TEST{i:03d}"
            cache_key = f"perf_test:{symbol}"
            data = json.dumps({"value": i, "timestamp": datetime.utcnow().isoformat()})
            
            start_time = time.time()
            await redis_client.setex(cache_key, 60, data)
            operation_time = time.time() - start_time
            
            write_times.append(operation_time)
        
        # Calculate statistics
        avg_time = sum(write_times) / len(write_times)
        max_time = max(write_times)
        min_time = min(write_times)
        
        print(f"Cache write performance:")
        print(f"  Operations: {num_operations}")
        print(f"  Average: {avg_time:.4f}s")
        print(f"  Min: {min_time:.4f}s")
        print(f"  Max: {max_time:.4f}s")
        
        # Performance assertions
        assert avg_time < TestConfig.MAX_CACHE_RETRIEVAL_TIME
        assert max_time < TestConfig.MAX_CACHE_RETRIEVAL_TIME * 2
        
        # Clean up test data
        for i in range(num_operations):
            symbol = f"TEST{i:03d}"
            cache_key = f"perf_test:{symbol}"
            await redis_client.delete(cache_key)
    
    async def test_cache_read_performance(self, redis_client, clean_redis):
        """Test performance of cache read operations"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        # Pre-populate cache
        num_entries = 100
        for i in range(num_entries):
            symbol = f"TEST{i:03d}"
            cache_key = f"read_perf:{symbol}"
            data = json.dumps({"value": i, "timestamp": datetime.utcnow().isoformat()})
            await redis_client.setex(cache_key, 60, data)
        
        read_times = []
        num_reads = 100
        
        for i in range(num_reads):
            symbol = f"TEST{i % num_entries:03d}"
            cache_key = f"read_perf:{symbol}"
            
            start_time = time.time()
            await redis_client.get(cache_key)
            operation_time = time.time() - start_time
            
            read_times.append(operation_time)
        
        # Calculate statistics
        avg_time = sum(read_times) / len(read_times)
        max_time = max(read_times)
        min_time = min(read_times)
        
        print(f"Cache read performance:")
        print(f"  Operations: {num_reads}")
        print(f"  Average: {avg_time:.4f}s")
        print(f"  Min: {min_time:.4f}s")
        print(f"  Max: {max_time:.4f}s")
        
        # Performance assertions
        assert avg_time < TestConfig.MAX_CACHE_RETRIEVAL_TIME
        assert max_time < TestConfig.MAX_CACHE_RETRIEVAL_TIME * 2
        
        # Clean up test data
        for i in range(num_entries):
            symbol = f"TEST{i:03d}"
            cache_key = f"read_perf:{symbol}"
            await redis_client.delete(cache_key)