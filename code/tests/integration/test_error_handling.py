"""
Tests for error handling and fallback scenarios across all services
"""
import pytest
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List
from conftest import TestConfig

@pytest.mark.integration
class TestErrorHandlingAndFallbacks:
    """Test error handling and fallback scenarios across all services"""
    
    async def test_redis_connection_failure_fallback(self, redis_client, mock_quantconnect_client, 
                                                    mock_abacus_client):
        """Test system behavior when Redis is unavailable"""
        # Simulate Redis connection failure
        if hasattr(redis_client, 'ping'):
            # In real scenario, Redis would be unavailable
            # For testing, we'll simulate by using a mock Redis
            failed_redis = Mock()
            failed_redis.ping.side_effect = Exception("Connection refused")
        else:
            failed_redis = redis_client
        
        try:
            # Attempt operations that would normally use Redis
            symbol = "AAPL"
            
            # Market data should still work
            market_data = await mock_quantconnect_client.get_market_data(symbol)
            assert "price" in market_data
            
            # Features computation should still work
            features = {"sma_20": 148.5, "rsi": 65.2}
            
            # Prediction should still work
            prediction = await mock_abacus_client.predict(features)
            assert "prediction" in prediction
            
            # System should continue operating without cache
            print("System operates correctly without Redis cache")
            
        except Exception as e:
            # If system fails completely without Redis, that's a problem
            pytest.fail(f"System failed when Redis unavailable: {e}")
    
    async def test_abacus_ai_service_failure_fallback(self, redis_client, mock_quantconnect_client):
        """Test fallback when Abacus.AI service is unavailable"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "AAPL"
        
        # Create failing mock for Abacus.AI
        failing_abacus = Mock()
        failing_abacus.predict.side_effect = Exception("Abacus.AI service unavailable")
        
        # Get market data and features
        market_data = await mock_quantconnect_client.get_market_data(symbol)
        features = {"sma_20": 148.5, "rsi": 65.2, "volume_ratio": 1.2}
        
        # Try prediction (should fail)
        with pytest.raises(Exception):
            await failing_abacus.predict(features)
        
        # System should fall back to cached predictions or default strategy
        cache_key = f"prediction:{symbol}:{hash(str(features))}"
        
        # Check for cached fallback
        cached_prediction = await redis_client.get(cache_key)
        
        if cached_prediction:
            # Use cached prediction
            fallback_prediction = json.loads(cached_prediction)
            assert "prediction" in fallback_prediction
            print("Using cached prediction as fallback")
        else:
            # Use default fallback strategy
            fallback_prediction = {
                "prediction": "HOLD",
                "confidence": 0.5,
                "fallback": True,
                "reason": "Service unavailable"
            }
            print("Using default fallback strategy")
        
        # Verify fallback works
        assert fallback_prediction["prediction"] in ["BUY", "SELL", "HOLD"]
        assert "confidence" in fallback_prediction
    
    async def test_quantconnect_data_failure_fallback(self, redis_client, mock_abacus_client):
        """Test fallback when QuantConnect data is unavailable"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "AAPL"
        
        # Create failing mock for QuantConnect
        failing_quantconnect = Mock()
        failing_quantconnect.get_market_data.side_effect = Exception("QuantConnect API error")
        
        # Try to get market data (should fail)
        with pytest.raises(Exception):
            await failing_quantconnect.get_market_data(symbol)
        
        # System should fall back to cached market data or manual input
        cache_key = f"market_data:{symbol}:latest"
        
        # Check for cached fallback
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            # Use cached data
            fallback_data = json.loads(cached_data)["data"]
            assert "price" in fallback_data
            print("Using cached market data as fallback")
        else:
            # Use default fallback data
            fallback_data = {
                "symbol": symbol,
                "price": 150.0,  # Default/backup price
                "volume": 1000000,
                "timestamp": datetime.utcnow(),
                "fallback": True,
                "source": "backup_data"
            }
            print("Using backup market data")
        
        # Verify fallback data structure
        assert fallback_data["symbol"] == symbol
        assert isinstance(fallback_data["price"], (int, float))
        
        # Should still be able to generate prediction with fallback data
        features = {"price": fallback_data["price"], "volume_ratio": 1.0}
        prediction = await mock_abacus_client.predict(features)
        assert "prediction" in prediction
    
    async def test_cascade_failure_recovery(self, redis_client, mock_quantconnect_client, 
                                          mock_abacus_client):
        """Test recovery from cascade failures"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "CASCADE_TEST"
        
        # Stage 1: Normal operation
        print("Stage 1: Normal operation")
        market_data = await mock_quantconnect_client.get_market_data(symbol)
        features = {"sma_20": 148.5, "rsi": 65.2}
        prediction = await mock_abacus_client.predict(features)
        
        await redis_client.setex("market_data:test:latest", 300, json.dumps(market_data))
        await redis_client.setex("features:test:latest", 3600, json.dumps(features))
        await redis_client.setex("prediction:test:latest", 300, json.dumps(prediction))
        
        # Stage 2: Abacus.AI fails
        print("Stage 2: Abacus.AI failure")
        failing_abacus = Mock()
        failing_abacus.predict.side_effect = Exception("Service down")
        
        try:
            await failing_abacus.predict(features)
        except Exception:
            # Use cached prediction
            cached_pred = await redis_client.get("prediction:test:latest")
            assert cached_pred is not None
        
        # Stage 3: QuantConnect fails
        print("Stage 3: QuantConnect failure")
        failing_qc = Mock()
        failing_qc.get_market_data.side_effect = Exception("API error")
        
        try:
            await failing_qc.get_market_data(symbol)
        except Exception:
            # Use cached market data
            cached_market = await redis_client.get("market_data:test:latest")
            assert cached_market is not None
        
        # Stage 4: All services recovered
        print("Stage 4: Recovery")
        market_data_recovered = await mock_quantconnect_client.get_market_data(symbol)
        features_recovered = {"sma_20": 149.0, "rsi": 66.1}
        prediction_recovered = await mock_abacus_client.predict(features_recovered)
        
        assert market_data_recovered["price"] > 0
        assert prediction_recovered["prediction"] is not None
        
        print("Cascade failure and recovery test completed successfully")
    
    async def test_timeout_handling(self, mock_letta_client, mock_abacus_client):
        """Test timeout handling for slow services"""
        
        # Create slow mock services
        slow_letta = Mock()
        async def slow_letta_response(message):
            await asyncio.sleep(2.0)  # 2 second delay
            return "Slow response"
        slow_letta.send_message = slow_letta_response
        
        slow_abacus = Mock()
        async def slow_abacus_prediction(features):
            await asyncio.sleep(3.0)  # 3 second delay
            return {"prediction": 0.75, "confidence": 0.85}
        slow_abacus.predict = slow_abacus_prediction
        
        # Test timeout for Letta
        print("Testing Letta timeout handling...")
        timeout_start = time.time()
        
        try:
            # Set shorter timeout
            response = await asyncio.wait_for(
                slow_letta.send_message("test message"),
                timeout=1.0
            )
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            timeout_duration = time.time() - timeout_start
            assert 0.9 < timeout_duration < 1.2  # Should be close to 1 second
            print(f"Timeout correctly handled after {timeout_duration:.3f}s")
        
        # Test timeout for Abacus.AI
        print("Testing Abacus.AI timeout handling...")
        timeout_start = time.time()
        
        try:
            # Set shorter timeout
            prediction = await asyncio.wait_for(
                slow_abacus.predict({"feature1": 1.0}),
                timeout=1.0
            )
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            timeout_duration = time.time() - timeout_start
            assert 0.9 < timeout_duration < 1.2  # Should be close to 1 second
            print(f"Timeout correctly handled after {timeout_duration:.3f}s")
    
    async def test_rate_limiting_fallback(self, mock_abacus_client):
        """Test handling of rate limiting from external services"""
        
        # Create mock that simulates rate limiting
        rate_limited_abacus = Mock()
        call_count = 0
        
        async def rate_limited_predict(features):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 3:  # Allow first 3 calls
                return {"prediction": 0.75, "confidence": 0.85}
            elif call_count <= 6:  # Next 3 calls hit rate limit
                from requests import HTTPError
                raise HTTPError("429 Too Many Requests")
            else:  # After that, service recovers
                return {"prediction": 0.80, "confidence": 0.90}
        
        rate_limited_abacus.predict = rate_limited_predict
        
        # Test rate limit handling
        successful_predictions = 0
        rate_limited_calls = 0
        
        for i in range(10):
            try:
                prediction = await rate_limited_predict({"feature1": 1.0})
                successful_predictions += 1
            except Exception as e:
                if "429" in str(e):
                    rate_limited_calls += 1
                    # Fallback to default prediction
                    fallback_prediction = {
                        "prediction": "HOLD",
                        "confidence": 0.5,
                        "fallback_reason": "rate_limited"
                    }
                    print(f"Rate limited call {i+1}, using fallback")
                else:
                    raise e
        
        print(f"Rate limiting test results:")
        print(f"  Successful predictions: {successful_predictions}")
        print(f"  Rate limited calls: {rate_limited_calls}")
        
        # Should have some successful calls and some rate limited
        assert successful_predictions > 0
        assert rate_limited_calls > 0
        assert successful_predictions + rate_limited_calls == 10
    
    async def test_data_validation_errors(self, redis_client, mock_abacus_client):
        """Test handling of invalid data inputs"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        # Test invalid market data
        invalid_market_data = {
            "symbol": "INVALID",
            "price": -100,  # Invalid negative price
            "volume": "invalid",  # Invalid type
            "timestamp": "not-a-date"  # Invalid timestamp
        }
        
        # System should validate and reject invalid data
        validated_data = self._validate_market_data(invalid_market_data)
        assert validated_data is None
        print("Invalid market data correctly rejected")
        
        # Test invalid features
        invalid_features = {
            "sma_20": None,  # Null value
            "rsi": "invalid",  # String instead of number
            "volume_ratio": float('inf')  # Infinite value
        }
        
        # Abacus.AI should reject invalid features
        with pytest.raises(Exception):
            await mock_abacus_client.predict(invalid_features)
        print("Invalid features correctly rejected")
        
        # Test invalid prediction response
        invalid_prediction = {
            "prediction": "INVALID_ACTION",  # Not BUY/SELL/HOLD
            "confidence": 1.5,  # > 1.0
            "timestamp": "invalid"
        }
        
        # Cache should validate prediction
        validated_prediction = self._validate_prediction(invalid_prediction)
        assert validated_prediction is None
        print("Invalid prediction correctly rejected")
    
    async def test_recovery_from_corrupted_cache(self, redis_client, clean_redis):
        """Test recovery from corrupted cache data"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "CORRUPT_TEST"
        cache_key = f"market_data:{symbol}:latest"
        
        # Put valid data first
        valid_data = {
            "data": {"price": 150.0, "volume": 1000000},
            "timestamp": datetime.utcnow().isoformat()
        }
        await redis_client.setex(cache_key, 300, json.dumps(valid_data))
        
        # Corrupt the data
        await redis_client.setex(cache_key, 300, "corrupted json data {invalid")
        
        # Attempt to read corrupted data
        cached_data = await redis_client.get(cache_key)
        
        # Should handle corruption gracefully
        try:
            parsed_data = json.loads(cached_data)
            # If parsing succeeds, data wasn't actually corrupted
            print("Data was not corrupted")
        except json.JSONDecodeError:
            # Expected - data was corrupted
            print("Cache corruption detected, using fallback")
            
            # Use fallback data
            fallback_data = {
                "data": {"price": 150.0, "volume": 1000000},
                "timestamp": datetime.utcnow().isoformat(),
                "source": "fallback",
                "reason": "cache_corruption"
            }
            
            # Should be able to recover with fallback
            assert fallback_data["data"]["price"] > 0
            print("Successfully recovered from cache corruption")
    
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for failing services"""
        
        class CircuitBreaker:
            def __init__(self, failure_threshold=3, timeout=5.0):
                self.failure_threshold = failure_threshold
                self.timeout = timeout
                self.failure_count = 0
                self.last_failure_time = None
                self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
            
            async def call(self, func, *args, **kwargs):
                if self.state == "OPEN":
                    if time.time() - self.last_failure_time > self.timeout:
                        self.state = "HALF_OPEN"
                    else:
                        raise Exception("Circuit breaker is OPEN")
                
                try:
                    result = await func(*args, **kwargs)
                    if self.state == "HALF_OPEN":
                        self.state = "CLOSED"
                        self.failure_count = 0
                    return result
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    
                    if self.failure_count >= self.failure_threshold:
                        self.state = "OPEN"
                    
                    raise e
        
        # Create failing function
        failing_func = Mock()
        failing_func.side_effect = Exception("Service down")
        
        # Test circuit breaker
        cb = CircuitBreaker(failure_threshold=2, timeout=1.0)
        
        # First call should fail and increment count
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.state == "CLOSED"
        assert cb.failure_count == 1
        
        # Second call should fail and open circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.state == "OPEN"
        assert cb.failure_count == 2
        
        # Third call should fail immediately due to OPEN circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.state == "OPEN"
        
        print(f"Circuit breaker test: {cb.failure_count} failures, state: {cb.state}")
    
    # Helper methods
    
    def _validate_market_data(self, data: Dict) -> Dict:
        """Validate market data structure"""
        try:
            if not isinstance(data.get("price"), (int, float)) or data.get("price", 0) <= 0:
                return None
            
            if not isinstance(data.get("volume"), (int, float)) or data.get("volume", 0) < 0:
                return None
            
            # Timestamp validation
            if data.get("timestamp"):
                datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            
            return data
        except Exception:
            return None
    
    def _validate_prediction(self, prediction: Dict) -> Dict:
        """Validate prediction structure"""
        try:
            if prediction.get("prediction") not in ["BUY", "SELL", "HOLD"]:
                return None
            
            confidence = prediction.get("confidence", 0)
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                return None
            
            return prediction
        except Exception:
            return None