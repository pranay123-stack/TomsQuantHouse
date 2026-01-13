"""
Integration tests for Memory Manager and Cache Manager
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Import the managers
from utils.memory_manager import CrewMemoryManager
from cache.cache_manager import CacheManager


class TestCrewMemoryManager:
    """Test cases for Crew Memory Manager"""
    
    @pytest.fixture
    def memory_manager(self, mock_redis_client):
        """Create CrewMemoryManager instance with mocked Redis"""
        with patch('utils.memory_manager.redis.from_url') as mock_from_url:
            mock_from_url.return_value = mock_redis_client
            
            # Create manager with test config
            manager = CrewMemoryManager(
                redis_url="redis://localhost:6379/0",
                namespace="test_crew"
            )
            
            # Set the mocked client
            manager.redis_client = mock_redis_client
            
            return manager
    
    @pytest.mark.asyncio
    async def test_initialization(self, memory_manager):
        """Test memory manager initialization"""
        assert memory_manager.redis_url == "redis://localhost:6379/0"
        assert memory_manager.namespace == "test_crew"
        assert memory_manager.redis_client is not None
        
        # Test Redis connection
        await memory_manager.redis_client.ping()
        assert True  # If we get here, connection succeeded
    
    @pytest.mark.asyncio
    async def test_store_crew_memory(self, memory_manager):
        """Test storing crew-wide memory"""
        memory_data = {
            'analysis_results': {
                'symbol': 'AAPL',
                'market_sentiment': 'positive',
                'price_target': 150.0
            },
            'agent_insights': {
                'market_research': 'Strong fundamentals',
                'ml_prediction': 'Bullish momentum',
                'risk_assessment': 'Low risk profile'
            },
            'workflow_context': {
                'current_workflow': 'market_analysis',
                'completed_agents': ['market_research', 'ml_prediction'],
                'timestamp': datetime.now().isoformat()
            }
        }
        
        result = await memory_manager.store_crew_memory(
            key="market_analysis_session",
            data=memory_data,
            ttl=3600  # 1 hour
        )
        
        # Verify storage
        assert result['success'] is True
        assert result['key'] == "test_crew:market_analysis_session"
        
        # Verify Redis was called correctly
        memory_manager.redis_client.set.assert_called_once()
        
        # Get the stored data and verify
        args, kwargs = memory_manager.redis_client.set.call_args
        assert args[0] == "test_crew:market_analysis_session"
        assert json.loads(args[1]) == memory_data
        assert kwargs['ex'] == 3600
    
    @pytest.mark.asyncio
    async def test_retrieve_crew_memory(self, memory_manager):
        """Test retrieving crew memory"""
        test_data = {
            'symbol': 'MSFT',
            'analysis_timestamp': datetime.now().isoformat(),
            'confidence_score': 0.85
        }
        
        # Mock Redis get to return test data
        memory_manager.redis_client.get.return_value = json.dumps(test_data)
        
        result = await memory_manager.retrieve_crew_memory("market_research_session")
        
        # Verify retrieval
        assert result['success'] is True
        assert result['data'] == test_data
        assert result['key'] == "test_crew:market_research_session"
        
        # Verify Redis was called correctly
        memory_manager.redis_client.get.assert_called_with("test_crew:market_research_session")
    
    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_memory(self, memory_manager):
        """Test retrieving non-existent memory"""
        # Mock Redis get to return None
        memory_manager.redis_client.get.return_value = None
        
        result = await memory_manager.retrieve_crew_memory("nonexistent_session")
        
        # Verify graceful handling
        assert result['success'] is True
        assert result['data'] is None
        assert result['key'] == "test_crew:nonexistent_session"
    
    @pytest.mark.asyncio
    async def test_get_agent_context(self, memory_manager):
        """Test getting agent-specific context"""
        agent_data = {
            'agent_name': 'ml_prediction_engineer',
            'current_tasks': ['price_prediction', 'signal_generation'],
            'shared_knowledge': {
                'market_data': {'current_price': 105.0, 'volume': 1000000},
                'risk_parameters': {'max_position': 1000, 'stop_loss': 0.05}
            },
            'last_update': datetime.now().isoformat()
        }
        
        # Mock the stored data
        memory_manager.redis_client.get.return_value = json.dumps(agent_data)
        
        result = await memory_manager.get_agent_context('ml_prediction_engineer')
        
        # Verify context retrieval
        assert result['success'] is True
        assert result['agent_name'] == 'ml_prediction_engineer'
        assert len(result['current_tasks']) == 2
        assert 'market_data' in result['shared_knowledge']
    
    @pytest.mark.asyncio
    async def test_share_insights(self, memory_manager):
        """Test sharing insights between agents"""
        insights_data = {
            'insight_type': 'market_analysis',
            'source_agent': 'market_research_analyst',
            'target_agents': ['ml_prediction_engineer', 'chief_risk_officer'],
            'insights': {
                'market_trend': 'bullish',
                'support_level': 100.0,
                'resistance_level': 110.0,
                'volatility': 0.25
            },
            'relevance_score': 0.85,
            'timestamp': datetime.now().isoformat()
        }
        
        # Mock Redis operations
        memory_manager.redis_client.lpush = AsyncMock(return_value=1)
        memory_manager.redis_client.lrange = AsyncMock(return_value=[])
        
        result = await memory_manager.share_insights(
            insight_type='market_analysis',
            insights=insights_data['insights'],
            source_agent='market_research_analyst',
            target_agents=['ml_prediction_engineer', 'chief_risk_officer']
        )
        
        # Verify sharing
        assert result['success'] is True
        assert result['shared_with'] == ['ml_prediction_engineer', 'chief_risk_officer']
        assert result['insight_type'] == 'market_analysis'
    
    @pytest.mark.asyncio
    async def test_get_workflow_history(self, memory_manager):
        """Test retrieving workflow history"""
        history_data = [
            {
                'workflow_id': 'wf_001',
                'symbol': 'AAPL',
                'status': 'completed',
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                'workflow_id': 'wf_002',
                'symbol': 'MSFT',
                'status': 'completed',
                'timestamp': (datetime.now() - timedelta(hours=1)).isoformat()
            }
        ]
        
        # Mock Redis list operations
        memory_manager.redis_client.lrange.return_value = [
            json.dumps(item) for item in history_data
        ]
        
        result = await memory_manager.get_workflow_history(limit=10)
        
        # Verify history retrieval
        assert result['success'] is True
        assert len(result['history']) == 2
        assert result['history'][0]['workflow_id'] == 'wf_001'
        assert result['history'][1]['workflow_id'] == 'wf_002'
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_memory(self, memory_manager):
        """Test cleaning up expired memory"""
        # Mock Redis key scanning and deletion
        memory_manager.redis_client.scan_iter = Mock(return_value=[
            'test_crew:expired_key_1',
            'test_crew:expired_key_2',
            'test_crew:active_key_1'
        ])
        
        memory_manager.redis_client.ttl = Mock(side_effect=[-1, -2, 3600])  # -1 = no expiry, -2 = expired, 3600 = active
        memory_manager.redis_client.delete = AsyncMock(return_value=2)
        
        result = await memory_manager.cleanup_expired_memory()
        
        # Verify cleanup
        assert result['success'] is True
        assert result['expired_keys_removed'] == 2
        assert result['active_keys_preserved'] == 1
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, memory_manager):
        """Test memory leak prevention mechanisms"""
        # Test large data handling
        large_data = {
            'large_array': np.random.random(10000).tolist(),
            'market_data': {f'symbol_{i}': {'price': i * 10} for i in range(100)},
            'timestamp': datetime.now().isoformat()
        }
        
        # Test with memory limit exceeded
        memory_manager.max_memory_size = 1024  # 1KB limit
        
        result = await memory_manager.store_crew_memory(
            key="large_data_test",
            data=large_data
        )
        
        # Should handle large data gracefully
        assert result['success'] is False
        assert 'memory_limit_exceeded' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_memory_operations(self, memory_manager):
        """Test concurrent memory operations"""
        operations = []
        
        async def store_and_retrieve(key_suffix):
            # Store data
            test_data = {
                'key': key_suffix,
                'timestamp': datetime.now().isoformat(),
                'data': f'test_data_{key_suffix}'
            }
            
            store_result = await memory_manager.store_crew_memory(
                key=f"concurrent_test_{key_suffix}",
                data=test_data
            )
            
            # Retrieve data
            retrieve_result = await memory_manager.retrieve_crew_memory(f"concurrent_test_{key_suffix}")
            
            return {
                'store_success': store_result['success'],
                'retrieve_success': retrieve_result['success'],
                'data_match': retrieve_result['data'] == test_data if retrieve_result['success'] else False
            }
        
        # Run concurrent operations
        results = await asyncio.gather(*[
            store_and_retrieve(i) for i in range(10)
        ])
        
        # Verify all operations succeeded
        assert len(results) == 10
        for result in results:
            assert result['store_success'] is True
            assert result['retrieve_success'] is True
            assert result['data_match'] is True


class TestCacheManager:
    """Test cases for Cache Manager"""
    
    @pytest.fixture
    def cache_manager(self, mock_redis_client):
        """Create CacheManager instance with mocked Redis"""
        with patch('cache.cache_manager.redis.from_url') as mock_from_url:
            mock_from_url.return_value = mock_redis_client
            
            # Create manager with test config
            manager = CacheManager(
                redis_url="redis://localhost:6379/1",
                default_ttl=300,  # 5 minutes
                max_cache_size=1024
            )
            
            # Set the mocked client
            manager.redis_client = mock_redis_client
            
            return manager
    
    @pytest.mark.asyncio
    async def test_initialization(self, cache_manager):
        """Test cache manager initialization"""
        assert cache_manager.redis_url == "redis://localhost:6379/1"
        assert cache_manager.default_ttl == 300
        assert cache_manager.max_cache_size == 1024
        assert cache_manager.redis_client is not None
        
        # Test Redis connection
        await cache_manager.redis_client.ping()
        assert True  # If we get here, connection succeeded
    
    @pytest.mark.asyncio
    async def test_get_cached_market_data(self, cache_manager):
        """Test caching and retrieving market data"""
        cache_key = "market_data:AAPL:1d"
        test_data = {
            'symbol': 'AAPL',
            'price': 105.50,
            'volume': 1000000,
            'timestamp': datetime.now().isoformat(),
            'cache_hit': True
        }
        
        # Test cache miss
        cache_manager.redis_client.get.return_value = None
        result = await cache_manager.get_cached("market_data", "AAPL", timeframe="1d")
        
        assert result['cache_hit'] is False
        assert result['data'] is None
        
        # Store data and test cache hit
        cache_manager.redis_client.get.return_value = json.dumps(test_data)
        result = await cache_manager.get_cached("market_data", "AAPL", timeframe="1d")
        
        assert result['cache_hit'] is True
        assert result['data'] == test_data
        assert result['cache_key'] == cache_key
    
    @pytest.mark.asyncio
    async def test_set_cache_with_different_strategies(self, cache_manager):
        """Test setting cache with different strategies"""
        test_data = {
            'predictions': [106.0, 107.0, 108.0],
            'confidence': 0.85,
            'model_type': 'random_forest'
        }
        
        # Test setting cache with default TTL
        cache_manager.redis_client.set = AsyncMock(return_value=True)
        
        result = await cache_manager.set_cache(
            cache_type="ml_predictions",
            key="AAPL_prediction",
            data=test_data,
            ttl=900  # 15 minutes
        )
        
        assert result['success'] is True
        assert result['ttl'] == 900
        assert result['key'] == "ml_predictions:AAPL_prediction"
        
        # Verify Redis set was called with correct arguments
        cache_manager.redis_client.set.assert_called_with(
            "ml_predictions:AAPL_prediction",
            json.dumps(test_data),
            ex=900
        )
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_manager):
        """Test cache invalidation by patterns"""
        # Mock Redis scan and delete operations
        cache_manager.redis_client.scan_iter = Mock(return_value=[
            "market_data:AAPL:1d",
            "market_data:AAPL:1h", 
            "market_data:MSFT:1d",
            "ml_predictions:AAPL",
            "risk_metrics:AAPL"
        ])
        
        cache_manager.redis_client.delete = AsyncMock(return_value=5)
        
        # Test pattern-based invalidation
        result = await cache_manager.invalidate_cache("AAPL", pattern="market_data:*")
        
        assert result['success'] is True
        assert result['invalidated_keys'] == 2  # Only AAPL market data
        assert result['pattern'] == "market_data:*"
        
        # Test exact key invalidation
        result = await cache_manager.invalidate_cache("exact_key")
        
        assert result['success'] is True
        assert result['invalidated_keys'] == 0  # No matches for exact key
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_manager):
        """Test cache statistics and performance metrics"""
        # Mock Redis info
        memory_info = {
            'used_memory': 1024000,  # 1MB
            'used_memory_human': '1MB',
            'keyspace_hits': 150,
            'keyspace_misses': 30,
            'expired_keys': 25,
            'evicted_keys': 5
        }
        
        cache_manager.redis_client.info.return_value = memory_info
        
        # Mock scan for key counts
        cache_manager.redis_client.scan_iter = Mock(return_value=[
            'market_data:AAPL',
            'ml_predictions:MSFT',
            'risk_metrics:AAPL'
        ] * 10)  # 30 total keys
        
        result = await cache_manager.get_cache_stats()
        
        # Verify stats
        assert result['success'] is True
        assert result['memory_usage']['used_memory'] == 1024000
        assert result['hit_rate'] == 150 / (150 + 30)  # 83.33%
        assert result['key_count'] == 30
        assert result['expired_keys'] == 25
        assert result['evicted_keys'] == 5
    
    @pytest.mark.asyncio
    async def test_intelligent_cache_warming(self, cache_manager):
        """Test intelligent cache warming based on patterns"""
        warming_config = {
            'symbols': ['AAPL', 'MSFT', 'GOOGL'],
            'data_types': ['market_data', 'ml_predictions'],
            'timeframes': ['1d', '1h'],
            'preload_factor': 0.8
        }
        
        # Mock cache misses that trigger warming
        cache_manager.redis_client.get.side_effect = [None] * len(warming_config['symbols']) * len(warming_config['data_types'])
        cache_manager.redis_client.set = AsyncMock(return_value=True)
        
        # Mock data source for warming
        async def mock_data_loader(data_type, symbol, timeframe):
            return {
                'data_type': data_type,
                'symbol': symbol,
                'timeframe': timeframe,
                'warmed': True,
                'timestamp': datetime.now().isoformat()
            }
        
        result = await cache_manager.warm_cache(warming_config, mock_data_loader)
        
        # Verify warming results
        assert result['success'] is True
        assert result['warmed_keys'] == len(warming_config['symbols']) * len(warming_config['data_types'])
        assert result['warming_strategy'] == 'predictive'
        
        # Verify warming was called for all combinations
        expected_calls = len(warming_config['symbols']) * len(warming_config['data_types'])
        assert cache_manager.redis_client.set.call_count >= expected_calls
    
    @pytest.mark.asyncio
    async def test_cache_partitioning(self, cache_manager):
        """Test cache partitioning by type"""
        # Test different cache types with different TTL strategies
        cache_types = {
            'market_data': {'ttl': 300, 'priority': 'high'},
            'ml_predictions': {'ttl': 900, 'priority': 'medium'},
            'risk_metrics': {'ttl': 600, 'priority': 'high'},
            'execution_plans': {'ttl': 1800, 'priority': 'low'}
        }
        
        for cache_type, config in cache_types.items():
            test_data = {'type': cache_type, 'data': f'test_{cache_type}'}
            
            cache_manager.redis_client.set = AsyncMock(return_value=True)
            
            result = await cache_manager.set_cache(
                cache_type=cache_type,
                key=f"{cache_type}_test",
                data=test_data
            )
            
            assert result['success'] is True
            assert result['ttl'] == config['ttl']
            assert result['priority'] == config['priority']
    
    @pytest.mark.asyncio
    async def test_cache_compression(self, cache_manager):
        """Test cache data compression for large payloads"""
        # Create large data that benefits from compression
        large_data = {
            'market_series': [np.random.random(1000).tolist() for _ in range(10)],
            'predictions': [np.random.random(500).tolist() for _ in range(5)],
            'metadata': {'symbols': [f'SYM_{i}' for i in range(100)]}
        }
        
        cache_manager.redis_client.set = AsyncMock(return_value=True)
        
        result = await cache_manager.set_cache(
            cache_type="large_data",
            key="compression_test",
            data=large_data,
            compress=True
        )
        
        assert result['success'] is True
        assert result['compressed'] is True
        assert result['original_size'] > result['compressed_size']
        
        # Test retrieval with decompression
        cache_manager.redis_client.get.return_value = json.dumps(large_data)
        
        result = await cache_manager.get_cached("large_data", "compression_test", decompress=True)
        
        assert result['success'] is True
        assert result['decompressed'] is True
        assert result['data'] == large_data
    
    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self, cache_manager):
        """Test concurrent cache access and locking"""
        async def concurrent_cache_operation(operation_id):
            # Mix of read and write operations
            test_data = {'id': operation_id, 'data': f'concurrent_data_{operation_id}'}
            
            # Write operation
            await cache_manager.set_cache(
                cache_type="concurrent_test",
                key=f"concurrent_key_{operation_id}",
                data=test_data
            )
            
            # Read operation
            result = await cache_manager.get_cached(
                cache_type="concurrent_test",
                key=f"concurrent_key_{operation_id}"
            )
            
            return {
                'operation_id': operation_id,
                'write_success': True,
                'read_success': result['success'],
                'data_match': result['data'] == test_data if result['success'] else False
            }
        
        # Execute concurrent operations
        results = await asyncio.gather(*[
            concurrent_cache_operation(i) for i in range(20)
        ])
        
        # Verify all concurrent operations succeeded
        assert len(results) == 20
        for result in results:
            assert result['write_success'] is True
            assert result['read_success'] is True
            assert result['data_match'] is True
    
    @pytest.mark.asyncio
    async def test_cache_eviction_policies(self, cache_manager):
        """Test cache eviction when memory limits are reached"""
        # Simulate cache with size limit
        cache_manager.max_cache_size = 1024  # 1KB limit
        
        # Create data that would exceed the limit
        large_data_list = []
        for i in range(10):
            data = {
                'id': i,
                'large_field': 'x' * 100,  # 100 characters
                'timestamp': datetime.now().isoformat()
            }
            large_data_list.append(data)
            
            # Each set should trigger eviction
            cache_manager.redis_client.set = AsyncMock(return_value=True)
            cache_manager.redis_client.delete = AsyncMock(return_value=1)  # Mock eviction
            
            result = await cache_manager.set_cache(
                cache_type="eviction_test",
                key=f"eviction_key_{i}",
                data=data
            )
            
            if i >= 1:  # After first insertion, should trigger eviction
                assert result['evicted_keys'] >= 1
    
    @pytest.mark.asyncio
    async def test_cache_performance_monitoring(self, cache_manager):
        """Test cache performance monitoring and optimization"""
        # Simulate cache operations with timing
        operations = []
        
        for i in range(10):
            # Mix of hits and misses
            if i % 3 == 0:
                # Cache miss
                cache_manager.redis_client.get.return_value = None
                await asyncio.sleep(0.001)  # Simulate database fetch time
                data = {'id': i, 'fetched': True}
                cache_manager.redis_client.set = AsyncMock(return_value=True)
                await cache_manager.set_cache('test_type', f'key_{i}', data)
                operations.append('miss')
            else:
                # Cache hit
                test_data = {'id': i, 'cached': True}
                cache_manager.redis_client.get.return_value = json.dumps(test_data)
                await asyncio.sleep(0.0001)  # Simulate cache read time
                result = await cache_manager.get_cached('test_type', f'key_{i}')
                operations.append('hit')
        
        # Get performance metrics
        result = await cache_manager.get_performance_metrics()
        
        # Verify metrics
        assert result['success'] is True
        assert 'hit_rate' in result
        assert 'average_latency' in result
        assert 'operations_count' in result
        
        hit_rate = result['hit_rate']
        assert 0 <= hit_rate <= 1
        
        # Verify operation count
        assert result['operations_count'] == len(operations)
        
        # Verify latency is reasonable
        assert result['average_latency'] >= 0
        assert result['average_latency'] < 0.01  # Less than 10ms average
    
    @pytest.mark.asyncio
    async def test_cache_data_validation(self, cache_manager):
        """Test cache data validation and corruption handling"""
        # Test with valid data
        valid_data = {
            'symbol': 'AAPL',
            'price': 105.50,
            'timestamp': datetime.now().isoformat()
        }
        
        cache_manager.redis_client.get.return_value = json.dumps(valid_data)
        
        result = await cache_manager.get_cached("market_data", "AAPL")
        
        assert result['success'] is True
        assert result['data'] == valid_data
        
        # Test with corrupted/invalid JSON
        cache_manager.redis_client.get.return_value = "invalid json data"
        
        result = await cache_manager.get_cached("market_data", "AAPL_corrupted")
        
        assert result['success'] is False
        assert 'invalid_json' in result['error'].lower()
        
        # Test with malformed data structure
        malformed_data = {'valid_json': 'but_wrong_structure'}
        cache_manager.redis_client.get.return_value = json.dumps(malformed_data)
        
        result = await cache_manager.get_cached("market_data", "AAPL_malformed")
        
        assert result['success'] is False
        assert 'data_validation' in result['error'].lower()


class TestIntegrationMemoryCache:
    """Integration tests for memory and cache manager interaction"""
    
    @pytest.mark.asyncio
    async def test_memory_cache_workflow_integration(self):
        """Test integration between memory and cache managers"""
        # This would test a real workflow where memory and cache work together
        pass  # Implementation would require actual Redis instances
    
    @pytest.mark.asyncio
    async def test_concurrent_memory_cache_operations(self):
        """Test concurrent operations across memory and cache"""
        # This would test concurrent access patterns
        pass  # Implementation would require coordination testing