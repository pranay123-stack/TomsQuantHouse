"""
Performance benchmarking tests for prediction caching and retrieval
"""
import pytest
import asyncio
import json
import time
import statistics
from datetime import datetime
from typing import List, Dict, Any
from conftest import TestConfig

@pytest.mark.performance
@pytest.mark.integration
class TestPredictionCachingPerformance:
    """Performance benchmarks for prediction caching system"""
    
    async def test_prediction_cache_hit_performance(self, redis_client, mock_abacus_client, clean_redis):
        """Benchmark cache hit performance for predictions"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        symbol = "AAPL"
        features = {"feature1": 1.0, "feature2": 2.0, "feature3": 0.5}
        cache_key = f"prediction:{symbol}:{hash(str(features))}"
        
        # Generate and cache prediction
        prediction = await mock_abacus_client.predict(features)
        prediction_data = {
            "prediction": prediction,
            "features": features,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await redis_client.setex(
            cache_key,
            TestConfig.PREDICTION_CACHE_TTL,
            json.dumps(prediction_data)
        )
        
        # Benchmark cache hits
        cache_hit_times = []
        num_hits = 50
        
        for _ in range(num_hits):
            start_time = time.time()
            cached_data = await redis_client.get(cache_key)
            hit_time = time.time() - start_time
            
            assert cached_data is not None
            cache_hit_times.append(hit_time)
        
        # Calculate statistics
        self._log_cache_performance_stats("Prediction Cache Hits", cache_hit_times)
        
        # Assertions
        avg_hit_time = statistics.mean(cache_hit_times)
        max_hit_time = max(cache_hit_times)
        
        assert avg_hit_time < TestConfig.MAX_CACHE_RETRIEVAL_TIME
        assert max_hit_time < TestConfig.MAX_CACHE_RETRIEVAL_TIME * 2
    
    async def test_prediction_cache_miss_performance(self, redis_client, mock_abacus_client, clean_redis):
        """Benchmark cache miss performance (includes prediction generation)"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        cache_miss_times = []
        num_misses = 20
        
        for i in range(num_misses):
            symbol = f"TEST{i:03d}"
            features = {
                "feature1": float(i) / 100,
                "feature2": float(i + 1) / 100,
                "feature3": float(i + 2) / 100
            }
            cache_key = f"prediction:{symbol}:{hash(str(features))}"
            
            start_time = time.time()
            
            # Check cache (should miss)
            cached_data = await redis_client.get(cache_key)
            
            if not cached_data:
                # Generate prediction and cache it
                prediction = await mock_abacus_client.predict(features)
                prediction_data = {
                    "prediction": prediction,
                    "features": features,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await redis_client.setex(
                    cache_key,
                    TestConfig.PREDICTION_CACHE_TTL,
                    json.dumps(prediction_data)
                )
            
            miss_time = time.time() - start_time
            cache_miss_times.append(miss_time)
            
            # Clean up
            await redis_client.delete(cache_key)
        
        # Calculate statistics
        self._log_cache_performance_stats("Prediction Cache Misses", cache_miss_times)
        
        # Cache miss should be slower due to prediction generation
        avg_miss_time = statistics.mean(cache_miss_times)
        max_miss_time = max(cache_miss_times)
        
        assert avg_miss_time < TestConfig.MAX_PREDICTION_TIME
        assert max_miss_time < TestConfig.MAX_PREDICTION_TIME * 1.5
    
    async def test_concurrent_cache_access(self, redis_client, clean_redis):
        """Benchmark concurrent cache access performance"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        async def cache_access_worker(worker_id: int, num_ops: int) -> List[float]:
            """Worker function for concurrent cache access"""
            times = []
            
            for i in range(num_ops):
                symbol = f"WORKER{worker_id:03d}"
                cache_key = f"concurrent:{symbol}:{i}"
                data = json.dumps({
                    "worker_id": worker_id,
                    "operation": i,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                start_time = time.time()
                await redis_client.setex(cache_key, 60, data)
                retrieved = await redis_client.get(cache_key)
                operation_time = time.time() - start_time
                
                assert retrieved is not None
                times.append(operation_time)
                
                # Clean up
                await redis_client.delete(cache_key)
            
            return times
        
        # Run concurrent workers
        num_workers = 5
        ops_per_worker = 20
        
        start_time = time.time()
        worker_tasks = [
            cache_access_worker(worker_id, ops_per_worker)
            for worker_id in range(num_workers)
        ]
        
        all_times = await asyncio.gather(*worker_tasks)
        total_time = time.time() - start_time
        
        # Flatten all times
        concurrent_times = [time for worker_times in all_times for time in worker_times]
        
        # Calculate statistics
        self._log_cache_performance_stats("Concurrent Cache Access", concurrent_times)
        
        total_operations = num_workers * ops_per_worker
        throughput = total_operations / total_time
        
        print(f"Concurrent access summary:")
        print(f"  Workers: {num_workers}")
        print(f"  Operations per worker: {ops_per_worker}")
        print(f"  Total operations: {total_operations}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Throughput: {throughput:.2f} ops/sec")
        
        # Performance assertions
        avg_time = statistics.mean(concurrent_times)
        assert avg_time < TestConfig.MAX_CACHE_RETRIEVAL_TIME * 2  # Allow for concurrency overhead
        
        # Throughput should be reasonable
        assert throughput > 10  # At least 10 ops/sec per worker on average
    
    async def test_cache_memory_efficiency(self, redis_client, clean_redis):
        """Test cache memory efficiency with large datasets"""
        if not hasattr(redis_client, 'info'):
            pytest.skip("Redis info not available - using mock")
        
        # Create large dataset
        num_entries = 1000
        entry_size = 1024  # 1KB per entry
        
        # Start memory usage
        initial_info = await redis_client.info('memory')
        initial_memory = initial_info.get('used_memory', 0)
        
        # Add entries
        for i in range(num_entries):
            symbol = f"BULK{i:04d}"
            features = {
                f"feature_{j}": float(j) / 100.0
                for j in range(10)  # 10 features per entry
            }
            
            cache_key = f"bulk:{symbol}"
            prediction = {"prediction": 0.75, "confidence": 0.85}
            
            data = {
                "features": features,
                "prediction": prediction,
                "timestamp": datetime.utcnow().isoformat(),
                "large_field": "x" * 500  # Add some bulk
            }
            
            await redis_client.setex(
                cache_key,
                TestConfig.PREDICTION_CACHE_TTL,
                json.dumps(data)
            )
        
        # Check memory usage after
        final_info = await redis_client.info('memory')
        final_memory = final_info.get('used_memory', 0)
        memory_increase = final_memory - initial_memory
        
        expected_size = num_entries * entry_size
        efficiency_ratio = memory_increase / expected_size
        
        print(f"Memory efficiency test:")
        print(f"  Entries: {num_entries}")
        print(f"  Entry size (estimated): {entry_size} bytes")
        print(f"  Expected total: {expected_size} bytes")
        print(f"  Actual increase: {memory_increase} bytes")
        print(f"  Efficiency ratio: {efficiency_ratio:.2f}")
        
        # Memory overhead should be reasonable (less than 3x expected)
        assert efficiency_ratio < 3.0
        
        # Clean up
        for i in range(num_entries):
            symbol = f"BULK{i:04d}"
            cache_key = f"bulk:{symbol}"
            await redis_client.delete(cache_key)
    
    async def test_cache_ttl_expiration_performance(self, redis_client, clean_redis):
        """Test cache TTL expiration performance"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        # Create entries with short TTL
        num_entries = 100
        ttl_seconds = 2
        
        creation_times = []
        
        for i in range(num_entries):
            symbol = f"TTL{i:03d}"
            cache_key = f"ttl_test:{symbol}"
            data = json.dumps({"entry": i, "timestamp": datetime.utcnow().isoformat()})
            
            start_time = time.time()
            await redis_client.setex(cache_key, ttl_seconds, data)
            creation_time = time.time() - start_time
            
            creation_times.append(creation_time)
        
        # Wait for expiration
        await asyncio.sleep(ttl_seconds + 0.5)
        
        # Check how many entries expired
        expired_count = 0
        for i in range(num_entries):
            symbol = f"TTL{i:03d}"
            cache_key = f"ttl_test:{symbol}"
            remaining = await redis_client.get(cache_key)
            if remaining is None:
                expired_count += 1
        
        expiration_rate = expired_count / num_entries
        
        print(f"TTL expiration test:")
        print(f"  Entries created: {num_entries}")
        print(f"  TTL: {ttl_seconds}s")
        print(f"  Expired entries: {expired_count}")
        print(f"  Expiration rate: {expiration_rate:.2%}")
        print(f"  Avg creation time: {statistics.mean(creation_times):.4f}s")
        
        # Most entries should have expired
        assert expiration_rate > 0.8
    
    async def test_cache_cluster_simulation(self, redis_client, clean_redis):
        """Simulate cache cluster behavior"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        # Simulate different cache "shards"
        num_shards = 4
        operations_per_shard = 25
        
        shard_performance = {}
        
        for shard_id in range(num_shards):
            shard_times = []
            
            for i in range(operations_per_shard):
                cache_key = f"shard{shard_id}:entry{i:03d}"
                data = json.dumps({
                    "shard": shard_id,
                    "entry": i,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                start_time = time.time()
                await redis_client.setex(cache_key, 60, data)
                retrieved = await redis_client.get(cache_key)
                operation_time = time.time() - start_time
                
                assert retrieved is not None
                shard_times.append(operation_time)
                
                # Clean up
                await redis_client.delete(cache_key)
            
            shard_performance[f"shard_{shard_id}"] = statistics.mean(shard_times)
        
        print(f"Cache cluster simulation:")
        for shard, avg_time in shard_performance.items():
            print(f"  {shard}: {avg_time:.4f}s")
        
        # All shards should have similar performance
        times = list(shard_performance.values())
        max_variance = max(times) - min(times)
        avg_time = statistics.mean(times)
        
        print(f"  Average across shards: {avg_time:.4f}s")
        print(f"  Max variance: {max_variance:.4f}s")
        
        # Variance should be small compared to average
        assert max_variance < avg_time * 0.5
        
        # All shard times should be under threshold
        for shard_time in times:
            assert shard_time < TestConfig.MAX_CACHE_RETRIEVAL_TIME * 2
    
    def _log_cache_performance_stats(self, operation_type: str, times: List[float]):
        """Log performance statistics for cache operations"""
        if not times:
            return
        
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        
        # Calculate percentiles
        sorted_times = sorted(times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)
        p95_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_time
        p99_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_time
        
        print(f"\n{operation_type} Performance:")
        print(f"  Operations: {len(times)}")
        print(f"  Average: {avg_time:.4f}s")
        print(f"  Median: {median_time:.4f}s")
        print(f"  Min: {min_time:.4f}s")
        print(f"  Max: {max_time:.4f}s")
        print(f"  Std Dev: {std_dev:.4f}s")
        print(f"  95th percentile: {p95_time:.4f}s")
        print(f"  99th percentile: {p99_time:.4f}s")