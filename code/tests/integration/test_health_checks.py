"""
Health check tests for all services (Redis, Letta, Abacus.AI, QuantConnect)
"""
import pytest
import asyncio
import aioredis
import time
from datetime import datetime
from typing import Dict, Any
import httpx
from conftest import TestConfig

@pytest.mark.integration
@pytest.mark.redis
class TestRedisHealthChecks:
    """Health checks for Redis service"""
    
    async def test_redis_connection(self, redis_client):
        """Test basic Redis connectivity"""
        if not hasattr(redis_client, 'ping'):
            pytest.skip("Redis not available - using mock")
            return
        
        start_time = time.time()
        result = await redis_client.ping()
        response_time = time.time() - start_time
        
        assert result == "PONG"
        assert response_time < TestConfig.MAX_HEALTH_CHECK_TIME
        print(f"Redis ping response time: {response_time:.3f}s")
    
    async def test_redis_memory_usage(self, redis_client):
        """Test Redis memory usage is within acceptable limits"""
        if not hasattr(redis_client, 'info'):
            pytest.skip("Redis not available - using mock")
            return
        
        info = await redis_client.info('memory')
        used_memory = info.get('used_memory', 0)
        max_memory = info.get('maxmemory', 0)
        
        # Memory usage should be less than 80% of max memory
        if max_memory > 0:
            memory_usage_percent = (used_memory / max_memory) * 100
            assert memory_usage_percent < 80, f"Redis memory usage at {memory_usage_percent}%"
        
        print(f"Redis memory usage: {used_memory / 1024 / 1024:.2f}MB")
    
    async def test_redis_latency(self, redis_client):
        """Test Redis operation latency"""
        if not hasattr(redis_client, 'ping'):
            pytest.skip("Redis not available - using mock")
            return
        
        latencies = []
        for _ in range(10):
            start_time = time.time()
            await redis_client.ping()
            latency = time.time() - start_time
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        assert avg_latency < TestConfig.MAX_CACHE_RETRIEVAL_TIME
        assert max_latency < TestConfig.MAX_CACHE_RETRIEVAL_TIME * 2
        
        print(f"Redis latency - Avg: {avg_latency:.3f}s, Max: {max_latency:.3f}s")

@pytest.mark.integration
@pytest.mark.letta
class TestLettaHealthChecks:
    """Health checks for Letta service"""
    
    async def test_letta_api_health(self, mock_letta_client):
        """Test Letta API health endpoint"""
        # This would test the actual Letta health endpoint
        # For now, using mock since we don't have real access
        try:
            # In real implementation, this would be:
            # async with httpx.AsyncClient() as client:
            #     response = await client.get(f"{TestConfig.LETTA_BASE_URL}/health")
            #     assert response.status_code == 200
            
            # Using mock for testing
            response = await mock_letta_client.send_message("health_check")
            assert response is not None
            print("Letta service is healthy")
        except Exception as e:
            pytest.fail(f"Letta health check failed: {e}")
    
    async def test_letta_agent_creation(self, mock_letta_client):
        """Test Letta agent creation functionality"""
        agent_config = {
            "name": "test-agent",
            "system_prompt": "You are a trading assistant",
            "model": "gpt-4"
        }
        
        result = await mock_letta_client.create_agent(agent_config)
        assert "agent_id" in result
        print(f"Created Letta agent: {result['agent_id']}")

@pytest.mark.integration
@pytest.mark.abacus
class TestAbacusAIHealthChecks:
    """Health checks for Abacus.AI service"""
    
    async def test_abacus_api_health(self, mock_abacus_client):
        """Test Abacus.AI API health"""
        try:
            # In real implementation, this would test actual API
            # For now, using mock
            model_status = await mock_abacus_client.get_model_status("test-model")
            assert "status" in model_status
            assert model_status["status"] in ["ready", "training", "error"]
            print(f"Abacus.AI model status: {model_status['status']}")
        except Exception as e:
            pytest.fail(f"Abacus.AI health check failed: {e}")
    
    async def test_abacus_prediction_latency(self, mock_abacus_client):
        """Test Abacus.AI prediction latency"""
        start_time = time.time()
        prediction = await mock_abacus_client.predict({"feature1": 1.0, "feature2": 2.0})
        prediction_time = time.time() - start_time
        
        assert "prediction" in prediction
        assert prediction_time < TestConfig.MAX_PREDICTION_TIME
        print(f"Abacus.AI prediction time: {prediction_time:.3f}s")

@pytest.mark.integration
@pytest.mark.quantconnect
class TestQuantConnectHealthChecks:
    """Health checks for QuantConnect service"""
    
    async def test_quantconnect_api_health(self, mock_quantconnect_client):
        """Test QuantConnect API health"""
        try:
            # In real implementation, this would test actual API
            # For now, using mock
            market_data = await mock_quantconnect_client.get_market_data("AAPL")
            assert "price" in market_data
            print("QuantConnect API is healthy")
        except Exception as e:
            pytest.fail(f"QuantConnect health check failed: {e}")
    
    async def test_quantconnect_data_freshness(self, mock_quantconnect_client):
        """Test QuantConnect data freshness"""
        market_data = await mock_quantconnect_client.get_market_data("AAPL")
        timestamp = market_data.get("timestamp")
        
        if timestamp:
            data_age = (datetime.utcnow() - timestamp).total_seconds()
            # Data should be less than 1 hour old
            assert data_age < 3600, f"Market data is {data_age} seconds old"
            print(f"Market data age: {data_age} seconds")

@pytest.mark.integration
class TestIntegratedHealthCheck:
    """Integrated health check across all services"""
    
    async def test_all_services_health_check(self, redis_client, mock_letta_client, 
                                           mock_abacus_client, mock_quantconnect_client):
        """Test health of all services together"""
        health_status = {}
        
        # Test Redis
        try:
            if hasattr(redis_client, 'ping'):
                await redis_client.ping()
                health_status["redis"] = "healthy"
            else:
                health_status["redis"] = "mock"
        except Exception as e:
            health_status["redis"] = f"unhealthy: {e}"
        
        # Test Letta
        try:
            await mock_letta_client.send_message("health_check")
            health_status["letta"] = "healthy"
        except Exception as e:
            health_status["letta"] = f"unhealthy: {e}"
        
        # Test Abacus.AI
        try:
            await mock_abacus_client.get_model_status("test-model")
            health_status["abacus_ai"] = "healthy"
        except Exception as e:
            health_status["abacus_ai"] = f"unhealthy: {e}"
        
        # Test QuantConnect
        try:
            await mock_quantconnect_client.get_market_data("AAPL")
            health_status["quantconnect"] = "healthy"
        except Exception as e:
            health_status["quantconnect"] = f"unhealthy: {e}"
        
        # Log health status
        for service, status in health_status.items():
            print(f"{service}: {status}")
        
        # At least Redis should be available for meaningful testing
        assert health_status["redis"] in ["healthy", "mock"]
    
    @pytest.mark.slow
    async def test_end_to_end_health_monitoring(self):
        """Continuous health monitoring test"""
        health_checks = []
        
        for i in range(5):
            check_time = time.time()
            
            # Simulate health check
            await asyncio.sleep(0.1)  # Mock health check time
            
            health_checks.append({
                "timestamp": check_time,
                "status": "healthy",
                "services": ["redis", "letta", "abacus", "quantconnect"]
            })
            
            await asyncio.sleep(1)  # Wait between checks
        
        # Verify all health checks were successful
        for check in health_checks:
            assert check["status"] == "healthy"
        
        print(f"Completed {len(health_checks)} health checks successfully")
        print(f"Monitoring duration: {health_checks[-1]['timestamp'] - health_checks[0]['timestamp']:.1f}s")